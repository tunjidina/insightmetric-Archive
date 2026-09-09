"""
InsightMetric - data agent (live mode, RSS).

Same pipeline shape as collect.py; only the first step differs:

    fetch_raw_items(day)  ->  aggregate(items)  ->  score_sentiment()  ->  label_recurrence()  ->  save()

Live mode reads public RSS feeds (no keys), clusters headlines into topics by
keyword overlap, and appends one day of rows to the existing dataset. Raw
feed responses are cached under data/raw/<date>/ so a day can be re-run
offline and reproduced exactly.

Run:  python src/collect_live.py                 # collect today, append, relabel, save
      python src/collect_live.py --dry-run       # print today's trends, save nothing
      python src/collect_live.py --offline       # rebuild today from cached feeds only
"""
from __future__ import annotations

import argparse
import re
import sys
from collections import Counter
from datetime import date, datetime, timezone
from pathlib import Path

import feedparser
import pandas as pd
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

sys.path.insert(0, str(Path(__file__).resolve().parent))
from collect import COLUMNS, DATA_DIR, make_trend_id  # noqa: E402

RAW_DIR = DATA_DIR / "raw"
TRENDS_PER_DAY = 10
MIN_SHARED_KEYWORDS = 2        # headlines sharing >= this many keywords are the same topic ...
MIN_CLUSTER_JACCARD = 0.2      # ... provided the overlap is also a fair share of both headlines
FUZZY_MATCH = 0.4              # Jaccard on keyword sets for day-to-day topic matching
INCLUDE_GITHUB = True          # merge GitHub releases (src/github_releases.py) into the day's headlines

# ---------------------------------------------------------------------------
# Sources: all free, public, no authentication. Add or remove freely.
# ---------------------------------------------------------------------------
FEEDS = {
    "hackernews":  "https://hnrss.org/frontpage",
    "techcrunch":  "https://techcrunch.com/feed/",
    "theverge":    "https://www.theverge.com/rss/index.xml",
    "arstechnica": "https://feeds.arstechnica.com/arstechnica/technology-lab",
    "wired":       "https://www.wired.com/feed/rss",
}

# Category lexicon: first category whose terms appear in the topic's keywords wins,
# scored by number of matching terms. Extend as the feed mix evolves.
CATEGORY_TERMS = {
    # Order matters only for ties: the first category listed wins. AI is last because "ai"
    # appears in headlines from every other category and would otherwise absorb them.
    "Cybersecurity": {"security", "breach", "breaches", "hack", "hacked", "hacking", "hacker", "hackers", "ransomware", "malware", "vulnerability",
                      "vulnerabilities", "exploit", "exploited", "exploitation", "zero-day", "phishing", "passkeys", "encryption", "encrypted", "cyber",
                      "snooping", "spying", "spyware", "surveillance", "leak", "leaked", "logging", "patch", "patches", "cve", "flaw", "flaws",
                      "attack", "attacks", "attackers", "hijack", "hijacked", "stole", "stolen", "heist", "exfiltrate", "exfiltrates", "malicious",
                      "spam", "spammers", "smuggling", "fingerprint", "vpn", "nsa", "rsa", "keys", "certificate", "arrest", "arrested", "infecting",
                      "infected", "scam", "fraud", "credentials", "password", "passwords"},
    "Chips":         {"chip", "chips", "semiconductor", "nvidia", "gpu", "gpus", "cpu", "cpus", "tsmc", "intel", "amd", "arm", "qualcomm", "silicon",
                      "foundry", "wafer", "processor", "processors", "mali", "nm"},
    "Cloud":         {"cloud", "aws", "azure", "datacenter", "datacenters", "datacentre", "data-center", "center", "centers", "centre", "centres",
                      "outage", "outages", "kubernetes", "serverless", "saas", "servers", "vmware", "broadcom", "migration", "compute", "cdn",
                      "cloudflare", "storage", "hosting"},
    "Gadgets":       {"iphone", "pixel", "phone", "phones", "smartphone", "laptop", "headset", "smartwatch", "glasses", "console", "tablet", "earbuds",
                      "foldable", "fold", "camera", "e-reader", "tv", "tvs", "airpods", "homepod", "ring", "wearable", "device", "devices", "hardware",
                      "apple", "samsung", "xiaomi", "xbox", "playstation", "nintendo", "controller", "strap"},
    "Apps":          {"app", "apps", "android", "ios", "whatsapp", "instagram", "tiktok", "youtube", "spotify", "browser", "browsers", "social",
                      "alarm", "codepen", "store", "libreoffice", "emacs", "jellyfin", "open-source", "download", "downloads",
                      "vscode", "cpython", "duckdb", "pandas", "streamlit", "scikit-learn"},
    "Startups":      {"startup", "startups", "funding", "raises", "raised", "raising", "valuation", "series", "vc", "unicorn", "acquires", "acquisition",
                      "ipo", "financing", "stealth", "public", "round", "seed", "lands", "investors", "stake", "billion"},
    "Policy":        {"regulation", "regulators", "eu", "antitrust", "lawsuit", "sue", "sues", "suing", "settlement", "judge", "court", "ruling", "ban",
                      "banned", "law", "bill", "senate", "senator", "commission", "privacy", "tariff", "tariffs", "trademark", "comply", "mandate",
                      "requirements", "repairability", "lobbying", "authorities", "sovereign"},
    "AI":            {"ai", "llm", "llms", "model", "models", "openai", "anthropic", "gemini", "claude", "codex", "grok", "gpt", "gpt-6", "agi",
                      "chatbot", "agent", "agents", "machine", "neural", "generative", "copilot", "siri", "inference", "vllm", "decoding", "robotaxi",
                      "cybercab", "waymo", "autonomous", "robot", "robots", "mistral", "hermes", "pytorch", "transformers", "ollama",
                      "langchain", "llama.cpp"},
}
MONEY = re.compile(r"^\d+(\.\d+)?[mb]$")     # "3b", "340m", "1.2b" -> funding-round signal

OTHER = "Other"    # anything the lexicon cannot place (general-interest items on tech feeds)

CATEGORY_TERMS = {cat: {t if not (len(t) > 4 and t.endswith("s") and not t.endswith(("ss", "us", "is", "ies", "news"))) else t[:-1]
                        for t in terms} for cat, terms in CATEGORY_TERMS.items()}

STOPWORDS = set("""a an the and or of to in on for with at by from as is are was were be been this that these those it its
into over under after before about against between during without within up down out off than then their there they them
we you your our his her him he she who what which when where why how not no new says said say will can could would should
may might just more most some any all each every one two three first last next year years week month day today tomorrow
via amid vs get gets got make makes made take takes took use uses used using own big top best worst still now
again across here there back away also even ever only really very much many few lot lots things thing show
but yet so if while though because don't doesn't isn't won't can't it's see everything something nothing anything
coming latest apparently reportedly probably keep keeps working confirms confirm says said secret other another
these those into like look looks getting going come comes went hits hit report reports
break breaks broke record records announce announces announced reveals reveal push pushes put putting trying tries
wants want inside future business company companies people work workers think twice new newest expect expected
caught giving full under active real right wrong good bad big small has had have having well nobody time times
way ways let lets mob game games test tests released release version minor major""".split())


# ---------------------------------------------------------------------------
# 1. fetch
# ---------------------------------------------------------------------------
def fetch_raw_items(day: date, offline: bool = False) -> list[dict]:
    """Read every feed (or its cached copy) and return headline items."""
    cache = RAW_DIR / day.isoformat()
    cache.mkdir(parents=True, exist_ok=True)
    items: list[dict] = []
    for source, url in FEEDS.items():
        path = cache / f"{source}.xml"
        if path.exists():
            parsed = feedparser.parse(path.read_bytes())
        elif offline:
            print(f"  [skip] {source}: no cached copy for {day}")
            continue
        else:
            try:
                raw = _download(url)
            except Exception as exc:  # network errors should not abort the other feeds
                print(f"  [warn] {source}: {exc}")
                continue
            path.write_bytes(raw)                      # cache raw bytes so the day is reproducible
            parsed = feedparser.parse(raw)
            if parsed.get("bozo") and not parsed.entries:
                print(f"  [warn] {source}: unparseable feed ({parsed.get('bozo_exception')})")
                continue
        for e in parsed.entries:
            title = (e.get("title") or "").strip()
            if title:
                items.append({"source": source, "title": title,
                              "summary": re.sub("<[^>]+>", " ", e.get("summary", "") or "")[:300],
                              "link": e.get("link", "")})
    # Hacker News engagement (points / comments) rides along on hackernews items and is
    # logged separately by hn_trending.py; it is derived from the same cached feed.
    try:
        import hn_trending as hn
        stories = hn.parse_front_page(day, offline=True)          # feed already cached above
        hn.update_logs(stories)
        engagement = hn.engagement_by_title(stories)
        for it in items:
            if it["source"] == "hackernews":
                it["hn_points"], it["hn_comments"] = engagement.get(it["title"], (0, 0))
    except Exception as exc:
        print(f"  [warn] hn engagement: {exc}")

    # GitHub releases join as a sixth source when enabled (see github_releases.WATCHLIST).
    if INCLUDE_GITHUB:
        try:
            import github_releases as gh
            rel = gh.update_log(gh.fetch_releases(day, offline=offline))
            gh_items = gh.as_headline_items(gh.releases_on(day, rel))
            items.extend(gh_items)
            print(f"  github: {len(gh_items)} release headline(s) added")
        except Exception as exc:  # release monitoring must never break news collection
            print(f"  [warn] github releases: {exc}")
    print(f"  fetched {len(items)} headlines from {len({i['source'] for i in items})} sources")
    return items


def _download(url: str, timeout: int = 20) -> bytes:
    from urllib.request import Request, urlopen
    req = Request(url, headers={"User-Agent": "daily-tech-trends/0.1 (personal research; RSS reader)"})
    with urlopen(req, timeout=timeout) as resp:
        return resp.read()


# ---------------------------------------------------------------------------
# 2. aggregate: headlines -> topics
# ---------------------------------------------------------------------------
def _norm(tok: str) -> str:
    """Light normalisation: strip punctuation and a plural 's' so model/models cluster together."""
    tok = tok.strip(".-'")
    if tok.endswith("'s"):
        tok = tok[:-2]
    if len(tok) > 4 and tok.endswith("s") and not tok.endswith(("ss", "us", "is", "ies", "news")):
        tok = tok[:-1]
    return tok


SHORT_OK = {"ai", "eu", "us", "uk", "vr", "ar", "5g", "tv", "os", "cd", "x", "ev", "gpu", "ipo", "llm", "app"}


def keywords_of(text: str) -> set[str]:
    toks = (_norm(t) for t in re.findall(r"[a-z0-9][a-z0-9\-\.']*", text.lower()))
    return {t for t in toks if t not in STOPWORDS and (len(t) > 2 or t in SHORT_OK or MONEY.match(t)) and not t.isdigit()}


def cluster(items: list[dict]) -> list[list[int]]:
    """Union-find over headlines: join two if they share >= MIN_SHARED_KEYWORDS keywords."""
    kws = [keywords_of(it["title"]) for it in items]
    parent = list(range(len(items)))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]; i = parent[i]
        return i

    for i in range(len(items)):
        for j in range(i + 1, len(items)):
            shared = len(kws[i] & kws[j])
            if shared >= MIN_SHARED_KEYWORDS and shared / len(kws[i] | kws[j]) >= MIN_CLUSTER_JACCARD:
                parent[find(i)] = find(j)
    groups: dict[int, list[int]] = {}
    for i in range(len(items)):
        groups.setdefault(find(i), []).append(i)
    return list(groups.values())


def _shorten(text: str, n: int) -> str:
    text = text.strip()
    if len(text) <= n:
        return text.rstrip(" .:-")
    cut = text[:n].rsplit(" ", 1)[0]
    return cut.rstrip(" .:,;-") + "…"


def categorise(keywords: Counter) -> str:
    scores = {cat: sum(keywords[t] for t in terms if t in keywords) for cat, terms in CATEGORY_TERMS.items()}
    if any(MONEY.match(k) for k in keywords):
        scores["Startups"] += 2                # a money amount in a headline is a strong funding-round signal
    best = max(scores, key=scores.get)        # ties resolve in CATEGORY_TERMS order
    return best if scores[best] > 0 else OTHER


def aggregate(items: list[dict], day: date) -> list[dict]:
    if not items:
        return []
    all_kw = Counter(k for it in items for k in keywords_of(it["title"]))   # day-wide keyword frequency
    # Tokens on a quarter or more of the day's headlines ("ai" on a tech feed) carry no
    # information about a specific trend, so they do not count toward keyword_frequency.
    ubiquitous = {k for k, c in all_kw.items() if c >= 0.25 * len(items)}
    rows = []
    for idx in cluster(items):
        group = [items[i] for i in idx]
        sources = sorted({g["source"] for g in group})
        kw = Counter(k for g in group for k in keywords_of(g["title"]))
        top_kw = [k for k, _ in kw.most_common(5)]
        # Topic name = shortest headline in the cluster (readable); description = its summary,
        # falling back to a second source's headline, then the title itself.
        lead = min(group, key=lambda g: len(g["title"]))
        others = [g["title"] for g in group if g["source"] != lead["source"]]
        description = (lead["summary"].strip() or (others[0] if others else lead["title"]))[:200]
        rows.append({
            "date": day,
            "topic": _shorten(lead["title"], 60),
            "description": description,
            "category": categorise(kw),
            "keywords": "|".join(top_kw),
            "keyword_frequency": int(sum(all_kw[k] for k in top_kw if k not in ubiquitous)),
            "source_count": len(sources),
            "sources": "|".join(sources),
            "hn_points": max((g.get("hn_points", 0) for g in group), default=0),
            "_size": len(group),
        })
    # Rank: breadth of coverage first, then cluster size, then keyword frequency. Keep the top N.
    rows.sort(key=lambda r: (-r["source_count"], -r["_size"], -r["keyword_frequency"]))
    rows = rows[:TRENDS_PER_DAY]
    for i, r in enumerate(rows, start=1):
        r["rank"] = i
        r["trend_id"] = make_trend_id(day, r["topic"])
        r.pop("_size")
    return rows


# ---------------------------------------------------------------------------
# 3. sentiment  (identical to mock mode)
# ---------------------------------------------------------------------------
def score_sentiment(rows: list[dict]) -> list[dict]:
    analyzer = SentimentIntensityAnalyzer()
    for r in rows:
        text = f"{r['topic']}. {r['description']}"          # headline + summary: headlines alone are too terse for VADER
        r["sentiment_score"] = round(analyzer.polarity_scores(text)["compound"], 3)
    return rows


# ---------------------------------------------------------------------------
# 4. labelling with fuzzy topic matching (real topics are never string-identical day to day)
# ---------------------------------------------------------------------------
def label_recurrence_fuzzy(df: pd.DataFrame, threshold: float = FUZZY_MATCH) -> pd.DataFrame:
    df = df.sort_values(["date", "rank"]).copy()
    by_day = {d: [set(k.split("|")) for k in g["keywords"]] for d, g in df.groupby("date")}
    days = sorted(by_day)
    nxt = {d: days[i + 1] if i + 1 < len(days) else None for i, d in enumerate(days)}
    labels = []
    for d, kw in zip(df["date"], df["keywords"]):
        n = nxt[d]
        if n is None or (n - d).days != 1:
            labels.append(pd.NA); continue
        mine = set(kw.split("|"))
        labels.append(int(any(len(mine & o) / len(mine | o) >= threshold for o in by_day[n])))
    df["recurred_next_day"] = pd.array(labels, dtype="Int8")
    return df


# ---------------------------------------------------------------------------
# 5. persistence
# ---------------------------------------------------------------------------
def append_and_save(new_rows: list[dict], day: date) -> pd.DataFrame:
    new = pd.DataFrame(new_rows)
    new["date"] = pd.to_datetime(new["date"])
    new["collected_at"] = datetime.now(timezone.utc)
    path = DATA_DIR / "tech_trends.parquet"
    if path.exists():
        old = pd.read_parquet(path)
        old = old[old["date"] != pd.Timestamp(day)]        # re-running a day replaces it
        df = pd.concat([old, new], ignore_index=True)
    else:
        df = new
    df = label_recurrence_fuzzy(df)
    df["category"] = df["category"].astype("category")
    df = df[COLUMNS].sort_values(["date", "rank"]).reset_index(drop=True)
    df.to_csv(DATA_DIR / "tech_trends.csv", index=False)
    df.to_parquet(path, index=False)
    return df


def collect_day(day: date, offline: bool = False) -> list[dict]:
    items = fetch_raw_items(day, offline=offline)
    rows = aggregate(items, day)
    return score_sentiment(rows)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", type=date.fromisoformat, default=date.today())
    ap.add_argument("--dry-run", action="store_true", help="print trends, do not save")
    ap.add_argument("--offline", action="store_true", help="use cached feeds only; no network")
    args = ap.parse_args()

    print(f"Collecting {args.date} ({'offline' if args.offline else 'live'})")
    rows = collect_day(args.date, offline=args.offline)
    if not rows:
        sys.exit("No headlines collected.")
    show = pd.DataFrame(rows)[["rank", "topic", "category", "sentiment_score", "source_count", "keyword_frequency", "hn_points", "sources"]]
    print(show.to_string(index=False))
    if args.dry_run:
        print("\n(dry run: nothing saved)")
    else:
        df = append_and_save(rows, args.date)
        print(f"\nDataset now {len(df)} rows across {df['date'].nunique()} days -> {DATA_DIR}")
