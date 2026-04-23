"""Surname-Proxy Leakage Score (SPLS).

**Why this metric exists:** Muralidharan, Niehaus & Sukhtankar (NBER w26744,
2020) documented that surnames and village PINs leak caste in India-context
data. A feature set that *claims* to be caste-blind can still reproduce
caste-correlated outcomes if any column proxies caste. Fairlearn has no
native notion of proxy leakage --- SPLS fills that gap.

**Definition:** SPLS is the 5-fold cross-validated ROC-AUC of a logistic
classifier trained to predict the protected attribute from features that
the user claims are *not* themselves the protected attribute. An AUC close
to 0.5 means the feature set is near-chance at recovering the protected
attribute (low leakage). An AUC close to 1.0 means the protected attribute
is fully recoverable from "non-protected" features (severe leakage).

**Threshold:** The default warning threshold is 0.55. Any score at or
above this level should trigger a proxy warning in the audit report.

**Do NOT** use SPLS to *label* individual rows with a protected attribute.
It is a dataset-level diagnostic.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedKFold, cross_val_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler


@dataclass(frozen=True)
class SPLSResult:
    """Result of a Surname-Proxy Leakage Score computation."""

    score: float  # cross-validated ROC-AUC in [0, 1]
    threshold: float  # warning threshold used
    leaks: bool  # score >= threshold
    n_rows: int
    n_features: int
    protected_cardinality: int
    note: str = ""


def _build_pipeline(X: pd.DataFrame) -> Pipeline:
    """Build a one-hot + standard-scaler + logistic pipeline."""

    cat_cols = X.select_dtypes(include=["object", "category", "bool"]).columns.tolist()
    num_cols = [c for c in X.columns if c not in cat_cols]

    transformers: list[tuple[str, object, list[str]]] = []
    if cat_cols:
        transformers.append(
            (
                "cat",
                OneHotEncoder(handle_unknown="ignore", sparse_output=False),
                cat_cols,
            )
        )
    if num_cols:
        transformers.append(("num", StandardScaler(), num_cols))

    # If no columns at all, degenerate pipeline (shouldn't happen in practice).
    pre = ColumnTransformer(transformers) if transformers else "passthrough"

    return Pipeline(
        steps=[
            ("pre", pre),
            (
                "clf",
                LogisticRegression(
                    max_iter=1000,
                    solver="lbfgs",
                    random_state=0,
                ),
            ),
        ]
    )


def surname_proxy_leakage_score(
    X: pd.DataFrame,
    protected: pd.Series,
    *,
    threshold: float = 0.55,
    n_splits: int = 5,
    random_state: int = 0,
) -> SPLSResult:
    """Compute the Surname-Proxy Leakage Score on a feature block.

    Parameters
    ----------
    X:
        DataFrame of supposedly-non-protected features.
    protected:
        Series aligned with ``X`` containing the protected-attribute labels
        (any dtype; will be treated categorically).
    threshold:
        SPLS value at or above which the feature block is considered to
        leak the protected attribute. Default ``0.55``.
    n_splits:
        Folds for cross-validation. Default 5. Falls back to 3 or 2 when
        any class has fewer members than ``n_splits``.
    random_state:
        Seed for the CV splitter.

    Returns
    -------
    SPLSResult

    Notes
    -----
    - For binary protected attributes the metric is vanilla ROC-AUC.
    - For multi-class protected attributes we use the one-vs-rest macro AUC
      (``roc_auc_ovr``). Both are in ``[0, 1]`` with 0.5 = chance.
    - The score can occasionally dip below 0.5 on very small datasets due
      to CV noise; we clip to ``[0, 1]``.
    """

    if len(X) != len(protected):
        raise ValueError("X and protected must have the same length")
    if len(X) == 0:
        return SPLSResult(
            score=0.0,
            threshold=threshold,
            leaks=False,
            n_rows=0,
            n_features=X.shape[1],
            protected_cardinality=0,
            note="empty input",
        )

    y = pd.Series(protected).astype("category")
    classes = y.cat.categories
    if len(classes) < 2:
        return SPLSResult(
            score=0.5,
            threshold=threshold,
            leaks=False,
            n_rows=len(X),
            n_features=X.shape[1],
            protected_cardinality=int(len(classes)),
            note="single-class protected attribute; SPLS undefined, returning 0.5",
        )

    # Drop any all-null columns to keep the pipeline happy.
    X_clean = X.copy()
    X_clean = X_clean.dropna(axis=1, how="all")
    # Fill remaining NaNs with a sentinel.
    for col in X_clean.columns:
        if X_clean[col].dtype.kind in {"O", "b"} or str(X_clean[col].dtype) == "category":
            X_clean[col] = X_clean[col].astype(object).fillna("__NA__")
        else:
            X_clean[col] = X_clean[col].fillna(X_clean[col].median())

    # Clamp fold count so every class has at least n_splits members.
    min_class_count = int(y.value_counts().min())
    effective_splits = max(2, min(n_splits, min_class_count))
    if min_class_count < 2:
        return SPLSResult(
            score=0.5,
            threshold=threshold,
            leaks=False,
            n_rows=len(X),
            n_features=X_clean.shape[1],
            protected_cardinality=int(len(classes)),
            note=f"rare class with count {min_class_count}; SPLS returns 0.5",
        )

    pipe = _build_pipeline(X_clean)
    cv = StratifiedKFold(n_splits=effective_splits, shuffle=True, random_state=random_state)

    scoring = "roc_auc" if len(classes) == 2 else "roc_auc_ovr"
    try:
        scores = cross_val_score(pipe, X_clean, y.cat.codes, cv=cv, scoring=scoring)
    except Exception as exc:  # pragma: no cover - defensive
        return SPLSResult(
            score=0.5,
            threshold=threshold,
            leaks=False,
            n_rows=len(X),
            n_features=X_clean.shape[1],
            protected_cardinality=int(len(classes)),
            note=f"SPLS fit failed: {exc!s}",
        )

    mean_auc = float(np.clip(scores.mean(), 0.0, 1.0))
    return SPLSResult(
        score=mean_auc,
        threshold=threshold,
        leaks=mean_auc >= threshold,
        n_rows=len(X),
        n_features=X_clean.shape[1],
        protected_cardinality=int(len(classes)),
        note=f"{effective_splits}-fold CV {scoring}",
    )
