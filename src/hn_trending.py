"""
Hacker News trending topics.

Uses the already-approved Hacker News front-page feed (hnrss.org/frontpage): each
item carries points, comment count and submission time, which is enough to
measure engagement and velocity (points per hour) without any further API.

Produces two logs:
  data/hn_stories.parquet   one row per story (points/comments updated on later runs)
  data/hn_trending.parquet  one row per (date, keyword): stories, points, comments, velocity

and attaches hn_points / hn_comments to Hacker News items so collect_live.py can
carry them into the trend dataset.

Run:  python src/hn_trending.py                  # today, from the cached feed or live
      python src/hn_trending.py --offline        # cached feed only
"""
from __future__ import annotations

import argparse
import re
import sys
from datetime import date, datetime, timezone
from pathlib import Path

import feedparser
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from collect import DATA_DIR  # noqa: E402

RAW_DIR = DATA_DIR / "raw"
STORIES_PATH = DATA_DIR / "hn_stories.parquet"
TRENDING_PATH = DATA_DIR / "hn_trending.parquet"
FEED_URL = "https://hnrss.org/frontpage"
TOP_KEYWORDS = 15

POINTS = re.compile(r"Points:\s*(\d+)")
COMMENTS = re.compile(r"#\s*Comments:\s*(\d+)")
HN_ID = re.compile(r"item\?id=(\d+)")


def _download(url: str, timeout: int = 20) -> bytes:
    from urllib.request import Request, urlopen
    req = Request(url, headers={"User-Agent": "daily-tech-trends/0.1 (personal research; RSS reader)"})
    with urlopen(req, timeout=timeout) as resp:
        return resp.read()


def _keywords_of(text: str) -> set[str]:
    """Same tokeniser as the trend collector, so HN keywords line up with trend keywords."""
    from collect_live import keywords_of
    return keywords_of(text)


# ---------------------------------------------------------------------------
# 1. parse the front page
# ---------------------------------------------------------------------------
def parse_front_page(day: date, offline: bool = False, now: datetime | None = None) -> pd.DataFrame:
    """One row per front-page story with engagement metrics. Shares the collector's cache file."""
    cache = RAW_DIR / day.isoformat(); cache.mkdir(parents=True, exist_ok=True)
    path = cache / "hackernews.xml"
    if path.exists():
        raw = path.read_bytes()
    elif offline:
        print(f"  [skip] hackernews: no cached copy for {day}")
        return pd.DataFrame()
    else:
        raw = _download(FEED_URL); path.write_bytes(raw)
    parsed = feedparser.parse(raw)
    now = now or datetime.now(timezone.utc)
    rows = []
    for e in parsed.entries:
        summary = e.get("summary", "") or ""
        pts = POINTS.search(summary); com = COMMENTS.search(summary); hid = HN_ID.search(e.get("comments", "") or summary)
        published = datetime(*e.published_parsed[:6], tzinfo=timezone.utc) if e.get("published_parsed") else pd.NaT
        age_h = max((now - published).total_seconds() / 3600, 0.25) if published is not pd.NaT else float("nan")
        points = int(pts.group(1)) if pts else 0
        rows.append({
            "date": pd.Timestamp(day),
            "hn_id": int(hid.group(1)) if hid else None,
            "title": (e.get("title") or "").strip(),
            "url": e.get("link", ""),
            "comments_url": e.get("comments", ""),
            "points": points,
            "comments": int(com.group(1)) if com else 0,
            "published_at": published,
            "age_hours": round(age_h, 2),
            "points_per_hour": round(points / age_h, 2) if age_h == age_h else float("nan"),
            "keywords": "|".join(sorted(_keywords_of(e.get("title") or ""))),
        })
    df = pd.DataFrame(rows)
    if len(df):
        # Engagement score: points, plus discussion, plus a bonus for stories still accelerating.
        df["score"] = (df["points"] + 0.5 * df["comments"] + 5 * df["points_per_hour"].fillna(0)).round(1)
    print(f"  hackernews: {len(df)} front-page stories, {int(df['points'].sum()) if len(df) else 0} points in total")
    return df


# ---------------------------------------------------------------------------
# 2. trending keywords: engagement aggregated over the stories that carry them
# ---------------------------------------------------------------------------
MIN_STORIES = 2   # a keyword is a theme only if it spans at least this many stories
THEME_TOKEN = re.compile(r"^[a-z][a-z\-]{2,}$")   # words only: no numbers, versions, money amounts, contractions


def trending_keywords(stories: pd.DataFrame, top_n: int = TOP_KEYWORDS, min_stories: int = MIN_STORIES) -> pd.DataFrame:
    """Cross-story themes: keywords shared by several front-page stories, scored by the
    engagement of the stories that carry them. A keyword unique to one story is that
    story, not a theme, so it is excluded."""
    if stories.empty:
        return pd.DataFrame()
    ex = stories.assign(keyword=stories["keywords"].str.split("|")).explode("keyword").reset_index(drop=True)
    ex = ex[ex["keyword"].astype(str).str.match(THEME_TOKEN)].sort_values("points", ascending=False)
    agg = (ex.groupby(["date", "keyword"])
             .agg(stories=("hn_id", "nunique"), total_points=("points", "sum"), total_comments=("comments", "sum"),
                  max_velocity=("points_per_hour", "max"), top_story=("title", "first"))   # first = highest points
             .reset_index())
    agg = agg[agg["stories"] >= min_stories]
    agg["score"] = (agg["total_points"] + 0.5 * agg["total_comments"] + 5 * agg["max_velocity"].fillna(0)).round(1)
    return (agg.sort_values(["date", "score"], ascending=[True, False])
               .groupby("date").head(top_n).reset_index(drop=True))


# ---------------------------------------------------------------------------
# 3. persistence
# ---------------------------------------------------------------------------
def _upsert(path: Path, new: pd.DataFrame, keys: list[str]) -> pd.DataFrame:
    if path.exists():
        old = pd.read_parquet(path)
        df = pd.concat([old, new], ignore_index=True).drop_duplicates(keys, keep="last")
    else:
        df = new
    df = df.sort_values(keys).reset_index(drop=True)
    df.to_parquet(path, index=False); df.to_csv(path.with_suffix(".csv"), index=False)
    return df


def update_logs(stories: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    if stories.empty:
        return pd.DataFrame(), pd.DataFrame()
    all_stories = _upsert(STORIES_PATH, stories, ["hn_id"])
    all_trending = _upsert(TRENDING_PATH, trending_keywords(stories), ["date", "keyword"])
    return all_stories, all_trending


# ---------------------------------------------------------------------------
# 4. bridge into the trend pipeline
# ---------------------------------------------------------------------------
def engagement_by_title(stories: pd.DataFrame) -> dict[str, tuple[int, int]]:
    """title -> (points, comments), used by collect_live to enrich hackernews items."""
    return {r.title: (int(r.points), int(r.comments)) for r in stories.itertuples()}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", type=date.fromisoformat, default=date.today())
    ap.add_argument("--offline", action="store_true")
    args = ap.parse_args()
    print(f"Hacker News front page for {args.date} ({'offline' if args.offline else 'live'})")
    stories = parse_front_page(args.date, offline=args.offline)
    if stories.empty:
        sys.exit("Nothing parsed.")
    all_stories, all_trending = update_logs(stories)
    pd.set_option("display.width", 220); pd.set_option("display.max_colwidth", 60)
    print("\nTrending stories (by engagement score):")
    print(stories.sort_values("score", ascending=False)[["score", "points", "comments", "points_per_hour", "title"]].head(10).to_string(index=False))
    today = all_trending[all_trending["date"] == pd.Timestamp(args.date)].sort_values("score", ascending=False)
    print(f"\nCross-story themes (keywords in >= {MIN_STORIES} stories):")
    print(today[["keyword", "stories", "total_points", "total_comments", "max_velocity", "top_story"]].to_string(index=False) if len(today) else "  none today")
    print(f"\nLogs: {len(all_stories)} stories, {len(all_trending)} keyword-days -> {DATA_DIR}")
