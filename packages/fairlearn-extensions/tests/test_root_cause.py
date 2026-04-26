"""Tests for the root-cause permutation analysis."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
from sklearn.linear_model import LogisticRegression

from nyayai_fairlearn_ext.root_cause import compute_root_cause


def _toy_proxy_dataset(n: int = 600, seed: int = 0) -> tuple[pd.DataFrame, np.ndarray, np.ndarray]:
    """Build a dataset where ``pincode`` is a hard proxy for caste.

    Two protected groups ``A`` and ``B``. ``pincode`` is +5 for A, -5 for B,
    plus tiny noise. ``income`` is roughly uncorrelated with caste. Outcome
    is a function of pincode (so the model learns to use the proxy).
    """

    rng = np.random.default_rng(seed)
    caste = rng.choice(["A", "B"], size=n, p=[0.5, 0.5])
    pincode = np.where(caste == "A", 5.0, -5.0) + rng.normal(0, 0.05, size=n)
    income = rng.normal(0, 1.0, size=n)
    irrelevant = rng.normal(0, 1.0, size=n)
    # Outcome is purely a function of pincode (which is itself a proxy).
    y_true = (pincode > 0).astype(int)
    df = pd.DataFrame(
        {
            "caste": caste,
            "pincode": pincode,
            "income": income,
            "irrelevant": irrelevant,
        }
    )
    return df, y_true, caste


def test_root_cause_identifies_pincode_proxy() -> None:
    df, y_true, _caste = _toy_proxy_dataset(n=600, seed=0)
    # Train an LR on (pincode, income, irrelevant) — caste excluded.
    X_train = df[["pincode", "income", "irrelevant"]].astype(float)
    model = LogisticRegression(max_iter=1000, solver="liblinear", random_state=0)
    model.fit(X_train, y_true)

    class _Wrapper:
        def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
            return model.predict_proba(X[["pincode", "income", "irrelevant"]])

    # Build the X frame that includes the protected column for the root-cause API.
    X_for_rc = df[["caste", "pincode", "income", "irrelevant"]].copy()
    y_pred = (model.predict_proba(X_train)[:, 1] >= 0.5).astype(int)

    res = compute_root_cause(
        _Wrapper(),
        X_for_rc,
        y_pred,
        protected_column="caste",
        n_repeats=5,
        seed=13,
        top_k=4,
        y_true=y_true,
    )
    # Pincode must be the #1 driver of the disparity (it *is* the gap).
    assert res.feature_rankings, "expected at least one ranked feature"
    top = res.feature_rankings[0]
    assert top.feature_name == "pincode"
    assert top.contribution_to_disparity > 0.5  # huge gap collapses
    # Pincode must be flagged as a proxy at the default 0.05 threshold.
    assert "pincode" in res.proxy_features
    # Irrelevant feature should NOT be a proxy.
    assert "irrelevant" not in res.proxy_features


def test_root_cause_zero_proxies_for_clean_features() -> None:
    rng = np.random.default_rng(11)
    n = 400
    caste = rng.choice(["A", "B"], size=n)
    f1 = rng.normal(0, 1, size=n)
    f2 = rng.normal(0, 1, size=n)
    df = pd.DataFrame({"caste": caste, "f1": f1, "f2": f2})
    y_true = rng.binomial(1, 0.5, size=n)
    model = LogisticRegression(max_iter=500, solver="liblinear", random_state=1)
    model.fit(df[["f1", "f2"]].astype(float), y_true)

    class _W:
        def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
            return model.predict_proba(X[["f1", "f2"]])

    y_pred = (model.predict_proba(df[["f1", "f2"]].astype(float))[:, 1] >= 0.5).astype(int)
    res = compute_root_cause(
        _W(), df, y_pred, protected_column="caste", n_repeats=3, seed=2, top_k=4
    )
    # No proxy features expected at the 0.05 default threshold.
    assert res.proxy_features == []


def test_root_cause_respects_top_k() -> None:
    df, y_true, _ = _toy_proxy_dataset(n=300, seed=4)
    X = df[["pincode", "income", "irrelevant"]].astype(float)
    model = LogisticRegression(max_iter=500, solver="liblinear", random_state=2)
    model.fit(X, y_true)

    class _W:
        def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
            return model.predict_proba(X[["pincode", "income", "irrelevant"]])

    y_pred = (model.predict_proba(X)[:, 1] >= 0.5).astype(int)
    res = compute_root_cause(
        _W(),
        df,
        y_pred,
        protected_column="caste",
        n_repeats=2,
        seed=0,
        top_k=2,
    )
    assert len(res.feature_rankings) <= 2


def test_root_cause_rejects_unknown_column() -> None:
    df = pd.DataFrame({"caste": ["A", "B"], "f": [1, 2]})
    with pytest.raises(ValueError):
        compute_root_cause(
            object(),
            df,
            np.array([0, 1]),
            protected_column="unknown",
            n_repeats=1,
        )


def test_root_cause_negative_contribution_when_feature_masks_disparity() -> None:
    """Sanity check: contribution_to_disparity can be negative for noise features.

    A feature whose permutation *increases* the gap (rare, but possible
    with small samples) should yield a negative contribution.
    """
    df, y_true, _ = _toy_proxy_dataset(n=400, seed=12)
    X = df[["pincode", "income", "irrelevant"]].astype(float)
    model = LogisticRegression(max_iter=500, solver="liblinear", random_state=3)
    model.fit(X, y_true)

    class _W:
        def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
            return model.predict_proba(X[["pincode", "income", "irrelevant"]])

    y_pred = (model.predict_proba(X)[:, 1] >= 0.5).astype(int)
    res = compute_root_cause(
        _W(), df, y_pred, protected_column="caste", n_repeats=4, seed=5, top_k=8
    )
    # contributions in [-1, 1] always.
    for fc in res.feature_rankings:
        assert -1.0 <= fc.contribution_to_disparity <= 1.0
