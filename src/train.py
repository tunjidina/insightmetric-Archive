"""
Train and evaluate a logistic regression that predicts whether a trend
will appear again tomorrow.

Split is chronological (older days train, newest days test) because the
question is forward-looking; a random split would leak tomorrow's rows into
training and inflate the metrics.

Run:  python src/train.py
"""
from __future__ import annotations

import json
from pathlib import Path

import joblib
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, f1_score, roc_auc_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from brand import ACCENT, CONTRAST
from features import FEATURES, TARGET, build_features, split_xy

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "tech_trends.parquet"
MODELS = ROOT / "models"
OUT = ROOT / "outputs"
TEST_DAYS = 10


MIN_LABELLED_ROWS = 40


def chronological_split(feat: pd.DataFrame, test_days: int = TEST_DAYS):
    labelled = feat.dropna(subset=[TARGET])
    if len(labelled) < MIN_LABELLED_ROWS:
        raise SystemExit(f"Only {len(labelled)} labelled rows; need at least {MIN_LABELLED_ROWS} to train. Collect more days first.")
    days = sorted(labelled["date"].unique())
    test_days = min(test_days, max(1, len(days) // 4))      # short histories: hold out a quarter of the days
    cutoff = days[-test_days]
    train, test = labelled[labelled["date"] < cutoff], labelled[labelled["date"] >= cutoff]
    return split_xy(train), split_xy(test), cutoff


def build_model() -> Pipeline:
    return Pipeline([
        ("scale", StandardScaler()),
        ("clf", LogisticRegression(C=1.0, max_iter=1000, class_weight="balanced")),
    ])


def evaluate(model: Pipeline, X, y) -> dict:
    proba = model.predict_proba(X)[:, 1]
    pred = (proba >= 0.5).astype(int)
    return {
        "accuracy": round(accuracy_score(y, pred), 3),
        "f1": round(f1_score(y, pred), 3),
        "roc_auc": round(roc_auc_score(y, proba), 3),
        "confusion_matrix": confusion_matrix(y, pred).tolist(),
        "report": classification_report(y, pred, output_dict=True),
    }


def feature_importance(model: Pipeline) -> pd.DataFrame:
    """Standardised coefficients: one unit = one standard deviation of the feature,
    so magnitudes are comparable. Sign gives direction."""
    coefs = model.named_steps["clf"].coef_[0]
    imp = pd.DataFrame({"feature": FEATURES, "coefficient": coefs})
    imp["abs"] = imp["coefficient"].abs()
    return imp.sort_values("abs", ascending=False).drop(columns="abs").reset_index(drop=True)


def plot_importance(imp: pd.DataFrame) -> None:
    fig, ax = plt.subplots(figsize=(7, 5))
    colours = np.where(imp["coefficient"] >= 0, ACCENT, CONTRAST)
    ax.barh(imp["feature"][::-1], imp["coefficient"][::-1], color=colours[::-1])
    ax.axvline(0, color="grey", lw=1)
    ax.set(title="Logistic regression coefficients (standardised features)", xlabel="coefficient (log-odds per 1 SD)")
    fig.tight_layout(); fig.savefig(OUT / "model_importance.png", dpi=150); plt.close(fig)


if __name__ == "__main__":
    MODELS.mkdir(exist_ok=True); OUT.mkdir(exist_ok=True)
    feat = build_features(pd.read_parquet(DATA))
    (X_tr, y_tr), (X_te, y_te), cutoff = chronological_split(feat)
    print(f"Train: {len(X_tr)} rows  |  Test: {len(X_te)} rows (from {pd.Timestamp(cutoff).date()})")
    print(f"Baseline (always predict majority class): {max(y_te.mean(), 1 - y_te.mean()):.3f} accuracy")

    model = build_model().fit(X_tr, y_tr)
    metrics = evaluate(model, X_te, y_te)
    print(f"\nTest accuracy: {metrics['accuracy']}   F1: {metrics['f1']}   ROC-AUC: {metrics['roc_auc']}")
    print("Confusion matrix [[TN, FP], [FN, TP]]:", metrics["confusion_matrix"])

    imp = feature_importance(model)
    print("\nFeature importance (standardised coefficients):"); print(imp.to_string(index=False))
    plot_importance(imp)

    # Refit on all labelled data for deployment in the app.
    X_all, y_all = split_xy(feat)
    final = build_model().fit(X_all, y_all)
    joblib.dump(final, MODELS / "recurrence_model.joblib")
    (MODELS / "metrics.json").write_text(json.dumps(metrics, indent=2))
    imp.to_csv(OUT / "feature_importance.csv", index=False)
    print(f"\nSaved model -> {MODELS / 'recurrence_model.joblib'}")
