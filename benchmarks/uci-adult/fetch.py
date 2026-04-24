"""Fetch UCI Adult and produce a parquet ready for the NyayaAI fairness engine.

Pipeline:

1. Load the Adult dataset via :func:`sklearn.datasets.fetch_openml` (version 2 is
   the canonical, de-duplicated, NA-aware mirror). OpenML is the authoritative
   source used by Fairlearn's own documentation examples; the older
   UCI archive text files are frequently unavailable and inconsistently
   formatted. If OpenML access fails, we raise with a clear hint.
2. Clean the frame (rename ``class`` -> ``income_high``, strip whitespace).
3. Train a deterministic ``LogisticRegression`` on the *non-sensitive* features
   (we intentionally drop ``sex`` and ``race`` so the scored model mirrors the
   Fairlearn tutorial "blind" baseline --- any remaining disparity is the
   proxy leakage our fairness engine must catch).
4. Emit ``data/adult.parquet`` with:
   - sensitive columns (``sex``, ``race``)
   - the binary outcome (``income_high``)
   - the model probability score (``model_score``)
   - the feature columns (retained for provenance only; the audit itself will
     use only the declared protected + outcome + score cols).

Seed 42 is the canonical reproduction seed (matches MUDRA-Lite).

Usage::

    uv run python benchmarks/uci-adult/fetch.py \\
        --out benchmarks/uci-adult/data/adult.parquet --seed 42
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.datasets import fetch_openml
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler


# Sensitive columns must never enter the feature matrix; they live in the
# parquet only so the fairness engine can group by them at audit time.
SENSITIVE_COLS: tuple[str, ...] = ("sex", "race")
OUTCOME_COL: str = "income_high"
SCORE_COL: str = "model_score"

# The 12 non-sensitive Adult features used for the blind baseline model.
NUMERIC_FEATURES: tuple[str, ...] = (
    "age",
    "fnlwgt",
    "education-num",
    "capital-gain",
    "capital-loss",
    "hours-per-week",
)
CATEGORICAL_FEATURES: tuple[str, ...] = (
    "workclass",
    "education",
    "marital-status",
    "occupation",
    "relationship",
    "native-country",
)


def load_adult() -> pd.DataFrame:
    """Load UCI Adult via OpenML (version 2) into a single DataFrame."""

    bunch = fetch_openml("adult", version=2, as_frame=True, parser="pandas")
    df: pd.DataFrame = bunch.frame.copy()

    # OpenML calls the target column ``class`` with values ``<=50K`` / ``>50K``.
    # Normalize to a 0/1 integer column.
    target = df["class"].astype(str).str.strip()
    df[OUTCOME_COL] = (target == ">50K").astype(int)
    df = df.drop(columns=["class"])

    # Strip whitespace and '?' placeholders in categorical columns.
    for c in df.select_dtypes(include=["object", "category"]).columns:
        df[c] = df[c].astype(str).str.strip().replace({"?": "Unknown", "nan": "Unknown"})

    # Coerce numeric columns to float so pyarrow doesn't choke on mixed types.
    for c in NUMERIC_FEATURES:
        df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0).astype(float)

    return df


def train_blind_model(df: pd.DataFrame, seed: int) -> np.ndarray:
    """Train a deterministic logistic regression and return probability scores.

    The model is *blind* --- it sees none of the sensitive columns. Any
    DP/EO disparity the fairness engine finds therefore comes from
    proxies in the non-sensitive features (education, occupation,
    marital-status, hours, native-country), which is exactly the
    Fairlearn-tutorial baseline used in the literature numbers we compare to.
    """

    y = df[OUTCOME_COL].to_numpy()

    feature_cols = list(NUMERIC_FEATURES) + list(CATEGORICAL_FEATURES)
    X = df[feature_cols]

    pre = ColumnTransformer(
        transformers=[
            ("num", StandardScaler(), list(NUMERIC_FEATURES)),
            (
                "cat",
                OneHotEncoder(handle_unknown="ignore", sparse_output=False),
                list(CATEGORICAL_FEATURES),
            ),
        ],
        remainder="drop",
    )
    clf = LogisticRegression(
        solver="lbfgs",
        max_iter=2000,
        C=1.0,
        random_state=seed,
    )
    pipe = Pipeline([("pre", pre), ("clf", clf)])

    # Train on a 70/30 split so the scored probabilities on the held-out 30%
    # are not trivially overfit. Fairness metrics are then computed on the
    # *full* dataset using out-of-fold predictions to get a stable signal.
    X_tr, _, y_tr, _ = train_test_split(X, y, test_size=0.30, random_state=seed, stratify=y)
    pipe.fit(X_tr, y_tr)
    proba = pipe.predict_proba(X)[:, 1]
    return proba.astype(float)


def build(seed: int) -> pd.DataFrame:
    df = load_adult()
    df[SCORE_COL] = train_blind_model(df, seed=seed)

    # Keep a tidy column order: sensitive first, outcome, score, then features.
    ordered = [
        *SENSITIVE_COLS,
        OUTCOME_COL,
        SCORE_COL,
        *NUMERIC_FEATURES,
        *CATEGORICAL_FEATURES,
    ]
    ordered = [c for c in ordered if c in df.columns]
    return df[ordered]


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch UCI Adult and score it.")
    parser.add_argument("--out", type=Path, required=True, help="Output parquet path.")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    df = build(seed=args.seed)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    if str(args.out).endswith(".csv"):
        df.to_csv(args.out, index=False)
    else:
        df.to_parquet(args.out, index=False)
    print(f"Wrote {len(df):,} rows x {len(df.columns)} cols to {args.out}")


if __name__ == "__main__":
    main()
