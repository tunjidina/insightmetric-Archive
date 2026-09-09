#!/usr/bin/env bash
# File the starter backlog on GitHub.
#
#   gh auth login                                  # once
#   ./scripts/create_issues.sh <owner>/<repo>
#   ./scripts/create_issues.sh <owner>/<repo> --dry-run
#
# docs/issues.md is the single source of truth: this script parses it, so edit the
# markdown rather than this file. Labels are created idempotently; issues are NOT —
# running this twice files everything twice.
set -euo pipefail

REPO="${1:-}"
DRY_RUN="${2:-}"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SRC="$ROOT/docs/issues.md"

if [ -z "$REPO" ]; then
  echo "usage: $0 <owner>/<repo> [--dry-run]" >&2
  exit 1
fi
if [ ! -f "$SRC" ]; then
  echo "error: $SRC not found" >&2
  exit 1
fi
if [ "$DRY_RUN" != "--dry-run" ] && ! command -v gh >/dev/null; then
  echo "error: the GitHub CLI (gh) is not installed — see https://cli.github.com" >&2
  echo "       (re-run with --dry-run to check the parse without it)" >&2
  exit 1
fi

WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

# Split docs/issues.md into one title/labels/body triple per issue.
python3 - "$SRC" "$WORK" <<'PY'
import re, sys
from pathlib import Path

src, work = Path(sys.argv[1]), Path(sys.argv[2])
text = src.read_text(encoding="utf-8")

# Each issue is "## <n>. <title>", then a "**Labels:** ..." line, then the body.
blocks = re.split(r"^## (\d+)\. (.+)$", text, flags=re.M)[1:]
count = 0
for num, title, body in zip(blocks[0::3], blocks[1::3], blocks[2::3]):
    labels = ""
    m = re.search(r"^\*\*Labels:\*\* (.+)$", body, flags=re.M)
    if m:
        labels = ",".join(l.strip().strip("`") for l in m.group(1).split(","))
        body = body[:m.start()] + body[m.end():]
    body = body.strip().rstrip("-").strip()
    stem = work / f"{int(num):02d}"
    stem.with_suffix(".title").write_text(title.strip(), encoding="utf-8")
    stem.with_suffix(".labels").write_text(labels, encoding="utf-8")
    stem.with_suffix(".body").write_text(body + "\n", encoding="utf-8")
    count += 1
PY

COUNT="$(ls "$WORK"/*.title 2>/dev/null | wc -l | tr -d ' ')"
echo "Parsed $COUNT issues from docs/issues.md"

# Labels, with colours: area labels blue-grey, meta labels green.
create_label () {  # name, colour, description
  gh label create "$1" --repo "$REPO" --color "$2" --description "$3" 2>/dev/null \
    || gh label edit  "$1" --repo "$REPO" --color "$2" --description "$3" >/dev/null 2>&1 \
    || true
}

if [ "$DRY_RUN" != "--dry-run" ]; then
  echo "Creating labels..."
  create_label "clustering"      "3B6EA8" "Grouping headlines into topics"
  create_label "lexicon"         "3B6EA8" "Category terms and vocabulary"
  create_label "releases"        "3B6EA8" "GitHub release monitoring"
  create_label "ui"              "3B6EA8" "Streamlit application"
  create_label "model"           "3B6EA8" "Features, training, evaluation"
  create_label "tooling"         "6E7781" "Scripts and developer tooling"
  create_label "testing"         "6E7781" "Tests and test infrastructure"
  create_label "enhancement"     "1BAF7A" "New capability or improvement"
  create_label "documentation"   "1BAF7A" "Docs and explanatory writing"
  create_label "good first issue" "EDA100" "Self-contained, good entry point"
  create_label "help wanted"     "EDA100" "Open for anyone to pick up"
fi

for t in "$WORK"/*.title; do
  stem="${t%.title}"
  title="$(cat "$t")"
  labels="$(cat "$stem.labels")"
  if [ "$DRY_RUN" = "--dry-run" ]; then
    printf '  [dry-run] %-60s  [%s]\n' "$title" "$labels"
  else
    gh issue create --repo "$REPO" \
      --title "$title" \
      --body-file "$stem.body" \
      --label "$labels"
  fi
done

if [ "$DRY_RUN" = "--dry-run" ]; then
  echo "Dry run complete — nothing was created."
else
  echo "Done. $COUNT issues filed on $REPO."
fi
