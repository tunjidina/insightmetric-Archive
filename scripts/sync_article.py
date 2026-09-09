#!/usr/bin/env python3
"""
Keep the code listings in docs/article.md identical to the source they quote.

The article embeds the whole project. Every listing is introduced by a bold path on its
own line — **src/collect.py**, or **Daily_Trends.py** (main page) — followed by a fenced
python block. This script replaces the contents of each of those blocks with the file the
heading names, so the article cannot drift from the code again.

    python scripts/sync_article.py --check    # exit 1 if anything is stale, change nothing
    python scripts/sync_article.py            # rewrite the listings in place

Prose is never touched. If a listing changes enough that the surrounding paragraph is
wrong, --check tells you which files moved so you know what to re-read.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ARTICLE = ROOT / "docs" / "article.md"

# **path/to/file.py** or **path/to/file.py** (an aside), then an optional blank line,
# then a ```python fence. Only python fences are managed; mermaid and shell stay put.
BLOCK = re.compile(
    r"(^\*\*(?P<path>[\w./_-]+\.py)\*\*(?P<aside>[^\n]*)\n+```python\n)"
    r"(?P<body>.*?)"
    r"(?P<fence>^```$)",
    re.M | re.S,
)


def sync(check: bool) -> int:
    text = ARTICLE.read_text()
    stale: list[str] = []
    missing: list[str] = []

    def replace(m: re.Match) -> str:
        path = ROOT / m.group("path")
        if not path.exists():
            missing.append(m.group("path"))
            return m.group(0)
        current = path.read_text().rstrip("\n") + "\n"
        if current != m.group("body"):
            stale.append(m.group("path"))
        return m.group(1) + current + m.group("fence")

    updated = BLOCK.sub(replace, text)
    listings = len(BLOCK.findall(text))

    if missing:
        print("ERROR: the article quotes files that no longer exist:")
        for p in missing:
            print(f"  {p}")
        return 2

    print(f"{listings} listings checked")
    if not stale:
        print("All listings match the source.")
        return 0

    print(f"{len(stale)} stale:")
    for p in stale:
        print(f"  {p}")
    if check:
        print("\nRun without --check to update them.")
        return 1
    ARTICLE.write_text(updated)
    print(f"\nUpdated {ARTICLE.relative_to(ROOT)}.")
    return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="report drift without writing")
    sys.exit(sync(ap.parse_args().check))
