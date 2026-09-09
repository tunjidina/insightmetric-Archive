"""
Feature engineering shared by training and the Streamlit app.

Keeping this in one module guarantees the app scores new rows with exactly
the transformations the model was trained on.
"""
from __future__ import annotations

import pandas as pd

CATEGORIES = ["AI", "Apps", "Cybersecurity", "Gadgets", "Cloud", "Chips", "Startups", "Policy", "Other"]  # Other: live-mode fallback
CATEGORY_CODE = {c: i for i, c in enumerate(CATEGORIES)}

NUMERIC_FEATURES = [
    "sentiment_score",   # VADER compound, [-1, 1]
    "sentiment_abs",     # emotional intensity regardless of direction
    "keyword_count",     # number of distinct keywords attached to the trend
    "keyword_frequency", # weighted keyword mentions that day
    "source_count",      # distinct sources covering it
    "hn_points",         # Hacker News points (0 when the topic was not on HN, and always 0 in mock data)
    "description_length",
    "rank",
    "days_seen_before",  # how many prior days this topic already appeared (momentum)
]
CATEGORY_FEATURES = [f"cat_{c}" for c in CATEGORIES]
FEATURES = NUMERIC_FEATURES + CATEGORY_FEATURES
TARGET = "recurrence_label"


def build_features(df: pd.DataFrame) -> pd.DataFrame:
    """Return a copy of `df` with model features appended. Works on the full
    history or on a single day's rows (days_seen_before then needs history)."""
    out = df.sort_values(["date", "rank"]).copy()
    out["sentiment_abs"] = out["sentiment_score"].abs()
    out["keyword_count"] = out["keywords"].str.count(r"\|") + 1
    out["description_length"] = out["description"].str.len()
    out["category_encoded"] = out["category"].astype(str).map(CATEGORY_CODE).astype(int)
    out["days_seen_before"] = out.groupby("topic").cumcount()
    for c in CATEGORIES:  # one-hot; ordinal codes would impose a false ordering on categories
        out[f"cat_{c}"] = (out["category"].astype(str) == c).astype(int)
    out[TARGET] = out["recurred_next_day"]
    return out


def split_xy(feat: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series]:
    labelled = feat.dropna(subset=[TARGET])
    return labelled[FEATURES], labelled[TARGET].astype(int)
