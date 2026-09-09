"""
Exploratory analysis for the InsightMetric dataset.

Produces four figures in outputs/ and prints the summary tables used in the article.

Run:  python src/eda.py
"""
from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from brand import ACCENT as COLOUR  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "tech_trends.parquet"
OUT = ROOT / "outputs"


def load() -> pd.DataFrame:
    return pd.read_parquet(DATA)


def sentiment_distribution(df: pd.DataFrame) -> None:
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.hist(df["sentiment_score"], bins=20, color=COLOUR, edgecolor="white")
    ax.axvline(0, color="grey", lw=1, ls="--")
    ax.set(title="Sentiment score distribution (VADER compound)", xlabel="sentiment_score", ylabel="trend-days")
    fig.tight_layout(); fig.savefig(OUT / "eda_sentiment.png", dpi=150); plt.close(fig)
    print("\nSentiment by category (mean):")
    print(df.groupby("category", observed=True)["sentiment_score"].mean().round(3).sort_values().to_string())


def keyword_frequency(df: pd.DataFrame, top_n: int = 20) -> pd.Series:
    """Weight each keyword by the keyword_frequency of the trend it belongs to."""
    counts: Counter = Counter()
    for kws, freq in zip(df["keywords"], df["keyword_frequency"]):
        for kw in kws.split("|"):
            counts[kw] += int(freq)
    top = pd.Series(counts).sort_values(ascending=False).head(top_n)
    fig, ax = plt.subplots(figsize=(7, 5))
    ax.barh(top.index[::-1], top.values[::-1], color=COLOUR)
    ax.set(title=f"Top {top_n} keywords by weighted frequency", xlabel="weighted mentions")
    fig.tight_layout(); fig.savefig(OUT / "eda_keywords.png", dpi=150); plt.close(fig)
    print("\nTop keywords:"); print(top.head(10).to_string())
    return top


def category_counts(df: pd.DataFrame) -> None:
    counts = df["category"].value_counts()
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.bar(counts.index.astype(str), counts.values, color=COLOUR)
    ax.set(title="Trend-days per category", ylabel="rows")
    plt.setp(ax.get_xticklabels(), rotation=30, ha="right")
    fig.tight_layout(); fig.savefig(OUT / "eda_categories.png", dpi=150); plt.close(fig)
    print("\nCategory counts:"); print(counts.to_string())


def recurrence_patterns(df: pd.DataFrame) -> None:
    lab = df.dropna(subset=["recurred_next_day"]).copy()
    lab["recurred_next_day"] = lab["recurred_next_day"].astype(int)
    print(f"\nOverall recurrence rate: {lab['recurred_next_day'].mean():.1%}")

    # Streak length: how many consecutive days a topic stayed in the list.
    streaks = []
    for _topic, g in df.sort_values("date").groupby("topic"):
        run = 0; prev = None
        for d in g["date"]:
            run = run + 1 if prev is not None and (d - prev).days == 1 else 1
            prev = d
            streaks.append(run)
    streak_counts = pd.Series(streaks).value_counts().sort_index()

    fig, axes = plt.subplots(1, 2, figsize=(11, 4))
    by_src = lab.groupby("source_count")["recurred_next_day"].mean()
    axes[0].bar(by_src.index, by_src.values, color=COLOUR)
    axes[0].set(title="Recurrence rate by source_count", xlabel="source_count", ylabel="P(recurs tomorrow)", ylim=(0, 1))
    axes[1].bar(streak_counts.index, streak_counts.values, color=COLOUR)
    axes[1].set(title="Distribution of consecutive-day streaks", xlabel="days in a row", ylabel="count")
    fig.tight_layout(); fig.savefig(OUT / "eda_recurrence.png", dpi=150); plt.close(fig)

    print("\nRecurrence rate by source_count:"); print(by_src.round(3).to_string())
    print("\nRecurrence rate by category:")
    print(lab.groupby("category", observed=True)["recurred_next_day"].mean().round(3).sort_values(ascending=False).to_string())
    print("\nRecurrence rate by sentiment bucket:")
    bucket = pd.cut(lab["sentiment_score"], [-1, -0.3, 0.3, 1], labels=["negative", "neutral", "positive"])
    print(lab.groupby(bucket, observed=True)["recurred_next_day"].mean().round(3).to_string())


if __name__ == "__main__":
    OUT.mkdir(exist_ok=True)
    df = load()
    print(f"{len(df)} rows, {df['date'].nunique()} days, {df['topic'].nunique()} distinct topics")
    sentiment_distribution(df)
    keyword_frequency(df)
    category_counts(df)
    recurrence_patterns(df)
    print(f"\nFigures written to {OUT}")
