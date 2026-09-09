"""
InsightMetric - data agent (mock mode).

The agent has the same shape a live agent would have:

    fetch_raw_items(day)  ->  aggregate(items)  ->  score_sentiment()  ->  label_recurrence()  ->  save()

In mock mode `fetch_raw_items` synthesises headline-like items instead of
reading RSS feeds. Swapping in a live source means replacing that one
function; everything downstream is unchanged.

Run:  python src/collect.py --days 45 --seed 42
"""
from __future__ import annotations

import argparse
import hashlib
import math
import random
import re
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pandas as pd
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

DATA_DIR = Path(__file__).resolve().parents[1] / "data"
CATEGORIES = ["AI", "Apps", "Cybersecurity", "Gadgets", "Cloud", "Chips", "Startups", "Policy"]
SOURCES = ["hackernews", "techcrunch", "theverge", "arstechnica", "wired", "reuters_tech"]
TRENDS_PER_DAY = 10

# ---------------------------------------------------------------------------
# Topic pool: (topic, category, keywords). A real agent would discover these
# by clustering headlines; the mock draws from a fixed pool so that the same
# topic can genuinely recur across days.
# ---------------------------------------------------------------------------
TOPIC_POOL = [
    ("On-device LLM inference", "AI", "llm|on-device|inference|npu|edge"),
    ("AI agent frameworks", "AI", "agents|framework|orchestration|tools"),
    ("Open-weight model release", "AI", "open-weights|release|benchmark|model"),
    ("AI coding assistants", "AI", "copilot|code|assistant|developer"),
    ("Multimodal video models", "AI", "video|multimodal|generation|diffusion"),
    ("AI in customer support", "AI", "support|chatbot|automation|deflection"),
    ("Small language models", "AI", "slm|small-model|efficiency|distillation"),
    ("Retrieval-augmented search", "AI", "rag|retrieval|search|embeddings"),
    ("Super-app payments push", "Apps", "super-app|payments|wallet|fintech"),
    ("Messaging app encryption update", "Apps", "messaging|encryption|e2ee|privacy"),
    ("Subscription fatigue backlash", "Apps", "subscription|pricing|churn|backlash"),
    ("App store fee changes", "Apps", "app-store|fees|commission|developers"),
    ("Short-video algorithm changes", "Apps", "short-video|algorithm|feed|creators"),
    ("Passkey adoption surge", "Cybersecurity", "passkeys|fido|passwordless"),
    ("Ransomware hits hospital chain", "Cybersecurity", "ransomware|hospital|breach|extortion|healthcare"),
    ("Zero-day in VPN appliances", "Cybersecurity", "zero-day|vpn|patch|exploit"),
    ("Supply-chain package attack", "Cybersecurity", "supply-chain|npm|malware|package"),
    ("Deepfake fraud warnings", "Cybersecurity", "deepfake|fraud|voice|scam"),
    ("Foldable phone recall", "Gadgets", "foldable|recall|hinge|display"),
    ("Smart glasses launch", "Gadgets", "smart-glasses|wearable|ar|display"),
    ("E-ink tablet refresh", "Gadgets", "e-ink|tablet|reader"),
    ("Handheld gaming PC wave", "Gadgets", "handheld|gaming|pc|battery"),
    ("Smartwatch health sensors", "Gadgets", "smartwatch|health|sensor|wearable"),
    ("Cloud egress fee cuts", "Cloud", "egress|fees|cloud|pricing"),
    ("Multi-cloud outage postmortem", "Cloud", "outage|postmortem|availability|region|sla"),
    ("Serverless GPU offerings", "Cloud", "serverless|gpu|inference|scaling"),
    ("Sovereign cloud regions", "Cloud", "sovereign|region|data-residency|compliance"),
    ("3nm chip yields improve", "Chips", "3nm|yield|foundry"),
    ("AI accelerator startup funding", "Chips", "accelerator|funding|asic|inference"),
    ("Memory price spike", "Chips", "dram|hbm|memory|prices"),
    ("RISC-V laptop prototypes", "Chips", "risc-v|laptop|open-isa|prototype"),
    ("Export controls on GPUs", "Chips", "export-controls|gpu|sanctions|china"),
    ("Mega-round for robotics startup", "Startups", "robotics|funding|humanoid|series-c"),
    ("Fintech layoffs wave", "Startups", "layoffs|fintech|restructuring"),
    ("Climate-tech accelerator cohort", "Startups", "climate-tech|accelerator|cohort|seed"),
    ("Unicorn down-round", "Startups", "down-round|valuation|unicorn|funding"),
    ("EU AI Act enforcement", "Policy", "eu|ai-act|enforcement|compliance"),
    ("Antitrust ruling on search", "Policy", "antitrust|search|ruling"),
    ("Data-centre energy caps", "Policy", "data-centre|energy|grid|regulation"),
    ("Right-to-repair legislation", "Policy", "right-to-repair|legislation|parts|consumers"),
    ("Age-verification mandates", "Policy", "age-verification|mandate|platforms|privacy"),
]

# Description templates by tone. VADER scores the resulting text, so the
# sentiment column is computed the same way it would be in live mode.
TEMPLATES = {
    "positive": [
        "{topic}: analysts praise strong momentum as adoption accelerates across the industry.",
        "{topic} gains traction, with early users reporting impressive results and rapid growth.",
        "{topic} wins broad support after a successful rollout and encouraging benchmarks.",
    ],
    "neutral": [
        "{topic} is drawing coverage this week as several outlets report on the latest developments.",
        "{topic}: companies outline plans and timelines while observers wait for more detail.",
        "{topic} moves forward as vendors publish updated documentation and roadmaps.",
    ],
    "negative": [
        "{topic} sparks concern after critics warn of serious risks, delays and mounting costs.",
        "{topic}: frustrated users and regulators criticise a troubled, poorly handled rollout.",
        "{topic} faces backlash amid reports of failures, security worries and angry customers.",
    ],
}


@dataclass
class RawItem:
    """One headline-like item as a source would return it."""
    topic: str
    category: str
    keywords: str
    source: str
    text: str


def slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def make_trend_id(day: date, topic: str) -> str:
    return hashlib.sha1(f"{day.isoformat()}:{slug(topic)}".encode()).hexdigest()[:12]


def sigmoid(x: float) -> float:
    return 1 / (1 + math.exp(-x))


class MockTrendAgent:
    """Synthesises daily trends with realistic 'heat' and recurrence dynamics."""

    def __init__(self, seed: int = 42):
        self.rng = random.Random(seed)
        self.analyzer = SentimentIntensityAnalyzer()
        self.yesterday: list[dict] = []  # rows from the previous day (drives carry-over)

    # -- 1. fetch ----------------------------------------------------------
    def fetch_raw_items(self, day: date) -> list[RawItem]:
        """Mock stand-in for reading RSS feeds / APIs for `day`."""
        chosen: list[tuple] = []
        # Carry over yesterday's trends according to their latent recurrence probability.
        for row in self.yesterday:
            if self.rng.random() < row["_p_recur"]:
                chosen.append((row["topic"], row["category"], row["keywords"]))
        # Top up with fresh topics from the pool.
        used = {c[0] for c in chosen}
        fresh = [t for t in TOPIC_POOL if t[0] not in used]
        self.rng.shuffle(fresh)
        chosen.extend(fresh[: TRENDS_PER_DAY - len(chosen)])

        items: list[RawItem] = []
        for topic, category, keywords in chosen:
            heat = self.rng.betavariate(2, 3)  # latent popularity in [0, 1]
            n_sources = 1 + int(round(heat * (len(SOURCES) - 1)))
            tone = self.rng.choices(["positive", "neutral", "negative"], weights=[0.4, 0.35, 0.25])[0]
            text = self.rng.choice(TEMPLATES[tone]).format(topic=topic)
            for src in self.rng.sample(SOURCES, n_sources):
                items.append(RawItem(topic, category, keywords, src, text))
        return items

    # -- 2. aggregate --------------------------------------------------------
    def aggregate(self, items: list[RawItem], day: date) -> list[dict]:
        """Collapse raw items into one row per topic."""
        by_topic: dict[str, list[RawItem]] = {}
        for it in items:
            by_topic.setdefault(it.topic, []).append(it)

        rows = []
        for topic, group in by_topic.items():
            sources = sorted({g.source for g in group})
            # keyword_frequency: keyword mentions across the day's headlines (mocked as
            # proportional to source coverage plus noise).
            kw_freq = max(1, int(len(sources) * self.rng.uniform(2.0, 4.5)))
            rows.append({
                "date": day,
                "topic": topic,
                "description": group[0].text,
                "category": group[0].category,
                "keywords": group[0].keywords,
                "keyword_frequency": kw_freq,
                "source_count": len(sources),
                "sources": "|".join(sources),
                "hn_points": 0,          # Hacker News engagement; only live mode can observe it
            })
        # Rank by coverage, then keyword frequency.
        rows.sort(key=lambda r: (-r["source_count"], -r["keyword_frequency"]))
        for i, r in enumerate(rows, start=1):
            r["rank"] = i
            r["trend_id"] = make_trend_id(day, r["topic"])
        return rows

    # -- 3. sentiment --------------------------------------------------------
    def score_sentiment(self, rows: list[dict]) -> list[dict]:
        for r in rows:
            r["sentiment_score"] = round(self.analyzer.polarity_scores(r["description"])["compound"], 3)
        return rows

    # -- latent recurrence (mock only) -----------------------------------------
    def _attach_recurrence_propensity(self, rows: list[dict]) -> list[dict]:
        """Hidden generative rule: louder, more-covered, more emotive trends persist.
        This is what the model in train.py tries to recover."""
        for r in rows:
            z = (-2.2
                 + 0.55 * r["source_count"]
                 + 0.06 * r["keyword_frequency"]
                 + 0.9 * abs(r["sentiment_score"])
                 - 0.15 * r["rank"]
                 + self.rng.gauss(0, 0.6))
            r["_p_recur"] = sigmoid(z)
        return rows

    # -- 4. run one day ---------------------------------------------------------
    def collect_day(self, day: date) -> list[dict]:
        items = self.fetch_raw_items(day)
        rows = self.aggregate(items, day)
        rows = self.score_sentiment(rows)
        rows = self._attach_recurrence_propensity(rows)
        collected_at = datetime.combine(day, datetime.min.time(), tzinfo=timezone.utc) + timedelta(hours=6)
        for r in rows:
            r["collected_at"] = collected_at
        self.yesterday = rows
        return rows


# ---------------------------------------------------------------------------
# Labelling and persistence (identical in live and mock mode)
# ---------------------------------------------------------------------------
def label_recurrence(df: pd.DataFrame) -> pd.DataFrame:
    """recurred_next_day = 1 if the same topic appears on date + 1 day."""
    key = set(zip(df["date"], df["topic"]))
    next_day = df["date"] + pd.Timedelta(days=1)
    last_day = df["date"].max()
    label = [1 if (d, t) in key else 0 for d, t in zip(next_day, df["topic"])]
    df = df.copy()
    df["recurred_next_day"] = pd.array(label, dtype="Int8")
    df.loc[df["date"] == last_day, "recurred_next_day"] = pd.NA  # not yet observable
    return df


COLUMNS = ["trend_id", "date", "collected_at", "topic", "description", "category",
           "sentiment_score", "keyword_frequency", "keywords", "source_count", "sources",
           "hn_points", "rank", "recurred_next_day"]


def build_dataset(days: int, seed: int, end: date | None = None) -> pd.DataFrame:
    end = end or date.today()
    agent = MockTrendAgent(seed=seed)
    rows: list[dict] = []
    for i in range(days):
        rows.extend(agent.collect_day(end - timedelta(days=days - 1 - i)))
    df = pd.DataFrame(rows).drop(columns=["_p_recur"])
    df["date"] = pd.to_datetime(df["date"])
    df = label_recurrence(df)
    df["category"] = df["category"].astype("category")
    return df[COLUMNS].sort_values(["date", "rank"]).reset_index(drop=True)


def save(df: pd.DataFrame, out_dir: Path = DATA_DIR) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    df.to_csv(out_dir / "tech_trends.csv", index=False)
    df.to_parquet(out_dir / "tech_trends.parquet", index=False)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=45)
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()
    df = build_dataset(args.days, args.seed)
    save(df)
    print(f"Saved {len(df)} rows across {df['date'].nunique()} days -> {DATA_DIR}")
    print(df.head(5).to_string())
