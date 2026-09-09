"""
GitHub release monitoring for the InsightMetric data agent.

Reads each watched repository's public release Atom feed
(https://github.com/<owner>/<repo>/releases.atom - free, no authentication),
keeps a structured log of releases in data/releases.parquet, and hands the
day's releases to collect_live.py as headline items from source "github" so
that a big release can cluster with the news coverage it generates.

Raw feed responses are cached under data/raw/<date>/github__<owner>__<repo>.xml,
so --offline reproduces a day exactly, as with the news feeds.

Run:  python src/github_releases.py               # fetch, log, print today's releases
      python src/github_releases.py --offline     # from cached feeds only
      python src/github_releases.py --days 7      # show releases from the last week
"""
from __future__ import annotations

import argparse
import re
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import unquote

import feedparser
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from collect import DATA_DIR  # noqa: E402

RAW_DIR = DATA_DIR / "raw"
RELEASES_PATH = DATA_DIR / "releases.parquet"

# Repositories to watch. Keep it to projects whose releases are news in your
# world; every entry costs one request a day.
WATCHLIST = [
    "streamlit/streamlit",
    "pandas-dev/pandas",
    "scikit-learn/scikit-learn",
    "pytorch/pytorch",
    "huggingface/transformers",
    "vllm-project/vllm",
    "ollama/ollama",
    "langchain-ai/langchain",
    "ggml-org/llama.cpp",
    "microsoft/vscode",
    "python/cpython",
    "duckdb/duckdb",
]

SEMVER = re.compile(r"v?(\d+)\.(\d+)(?:\.(\d+))?")
PRERELEASE = re.compile(r"(alpha|beta|rc\d*|dev|pre|nightly|\.a\d|\.b\d|a\d+$|b\d+$)", re.I)
# Tags with a path separator are CI refs (pytorch: viable/strict/<ts>, trunk/<sha>), not releases.
NOISE = re.compile(r"/|^(?:viable|trunk|ciflow|nightly)")
HEADLINE_KINDS = {"major", "minor"}   # which non-pre-release kinds become trend headlines; patches are logged only


def feed_url(repo: str) -> str:
    return f"https://github.com/{repo}/releases.atom"


def _download(url: str, timeout: int = 20) -> bytes:
    from urllib.request import Request, urlopen
    req = Request(url, headers={"User-Agent": "daily-tech-trends/0.1 (personal research; release monitor)"})
    with urlopen(req, timeout=timeout) as resp:
        return resp.read()


def classify(tag: str) -> tuple[str, bool]:
    """Return (kind, is_prerelease). kind is major / minor / patch / other."""
    pre = bool(PRERELEASE.search(tag))
    m = SEMVER.search(tag)
    if not m:
        return "other", pre
    _major, minor, patch = m.group(1), m.group(2), m.group(3)
    if patch and patch != "0":
        return "patch", pre
    if minor != "0":
        return "minor", pre
    return "major", pre


# ---------------------------------------------------------------------------
# 1. fetch
# ---------------------------------------------------------------------------
def fetch_releases(day: date, offline: bool = False) -> pd.DataFrame:
    """All releases visible in the watched feeds on `day` (feeds hold ~10 most recent)."""
    cache = RAW_DIR / day.isoformat()
    cache.mkdir(parents=True, exist_ok=True)
    rows = []
    for repo in WATCHLIST:
        path = cache / f"github__{repo.replace('/', '__')}.xml"
        if path.exists():
            parsed = feedparser.parse(path.read_bytes())
        elif offline:
            print(f"  [skip] {repo}: no cached copy for {day}")
            continue
        else:
            try:
                raw = _download(feed_url(repo))
            except Exception as exc:
                print(f"  [warn] {repo}: {exc}")
                continue
            path.write_bytes(raw)
            parsed = feedparser.parse(raw)
        for e in parsed.entries:
            tag = unquote((e.get("link", "").rsplit("/tag/", 1)[-1] or e.get("title", "")).strip())
            if NOISE.search(tag):
                continue
            title = (e.get("title") or tag).strip()
            published = e.get("updated") or e.get("published")
            try:
                published_at = datetime(*e.updated_parsed[:6], tzinfo=timezone.utc) if e.get("updated_parsed") else pd.to_datetime(published, utc=True)
            except Exception:
                published_at = pd.NaT
            kind, pre = classify(tag)
            notes = re.sub("<[^>]+>", " ", e.get("summary", "") or e.get("content", [{}])[0].get("value", ""))
            rows.append({
                "repo": repo,
                "tag": tag,
                "title": title,
                "published_at": published_at,
                "kind": kind,
                "is_prerelease": pre,
                "notes_length": len(notes.strip()),
                "url": e.get("link", ""),
            })
    df = pd.DataFrame(rows)
    if not df.empty:
        df["published_at"] = pd.to_datetime(df["published_at"], utc=True)
        df["release_date"] = df["published_at"].dt.date
    print(f"  fetched {len(df)} releases across {df['repo'].nunique() if len(df) else 0} repos")
    return df


# ---------------------------------------------------------------------------
# 2. log (append, dedupe on repo+tag)
# ---------------------------------------------------------------------------
def update_log(new: pd.DataFrame) -> pd.DataFrame:
    if RELEASES_PATH.exists():
        old = pd.read_parquet(RELEASES_PATH)
        df = pd.concat([old, new], ignore_index=True)
    else:
        df = new
    if df.empty:                                                       # nothing fetched and no log yet
        return df
    df["tag"] = df["tag"].astype(str).map(unquote)                    # older logs stored URL-encoded tags
    df = df[~df["tag"].str.contains(NOISE, regex=True)]               # scrub CI refs logged by earlier versions
    df = df.drop_duplicates(["repo", "tag"], keep="last").sort_values("published_at", ascending=False).reset_index(drop=True)
    RELEASES_PATH.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(RELEASES_PATH, index=False)
    df.to_csv(RELEASES_PATH.with_suffix(".csv"), index=False)
    return df


# ---------------------------------------------------------------------------
# 3. bridge into the trend pipeline
# ---------------------------------------------------------------------------
def releases_on(day: date, df: pd.DataFrame, lookback_days: int = 1) -> pd.DataFrame:
    """Releases published on `day` or within `lookback_days` before it (feeds are read once a day,
    so a release published late yesterday belongs to today's collection)."""
    if df.empty or "release_date" not in df.columns:
        return df
    lo = day - timedelta(days=lookback_days)
    return df[(df["release_date"] >= lo) & (df["release_date"] <= day)]


def as_headline_items(rel: pd.DataFrame) -> list[dict]:
    """Shape releases like news headlines so collect_live.aggregate() can cluster them
    with coverage from the other feeds. Pre-releases and patch releases are logged but not
    promoted: a release candidate or a bug-fix build is rarely news."""
    items = []
    if rel.empty or "is_prerelease" not in rel.columns:      # first run: no log and nothing fetched
        return items
    keep = rel[~rel["is_prerelease"] & rel["kind"].isin(HEADLINE_KINDS)]
    for r in keep.itertuples():
        # Monorepos tag packages as "<package>==<version>": use the package as the name.
        name = r.tag.split("==")[0] if "==" in r.tag else r.repo.split("/")[-1]
        items.append({
            "source": "github",
            # Keep the title to name + tag: generic words like "released" would make every
            # release cluster with every other release.
            "title": f"{name} {r.tag} released",
            "summary": f"{r.repo} published {r.tag} on GitHub ({r.kind} release).",
            "link": r.url,
        })
    return items


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", type=date.fromisoformat, default=date.today())
    ap.add_argument("--offline", action="store_true")
    ap.add_argument("--days", type=int, default=1, help="show releases from the last N days")
    args = ap.parse_args()
    print(f"Fetching release feeds for {args.date} ({'offline' if args.offline else 'live'})")
    fetched = fetch_releases(args.date, offline=args.offline)
    if fetched.empty:
        sys.exit("No releases fetched.")
    log = update_log(fetched)
    recent = releases_on(args.date, log, lookback_days=args.days)
    pd.set_option("display.width", 200)
    print(recent[["release_date", "repo", "tag", "kind", "is_prerelease", "notes_length"]].to_string(index=False) if len(recent) else "No releases in window.")
    print(f"\nLog now holds {len(log)} releases -> {RELEASES_PATH}")
