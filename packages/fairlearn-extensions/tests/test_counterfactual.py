"""Tests for counterfactual flips."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from nyayai_fairlearn_ext.counterfactual import compute_counterfactual_flips


class _ProtectedThresholdModel:
    """Toy model that classifies purely on the protected attribute.

    Returns probability 0.9 when the protected column equals
    ``positive_value`` and 0.1 otherwise. Used to demonstrate that
    flipping the protected attribute *must* flip the decision.
    """

    def __init__(self, protected_column: str, positive_value: str) -> None:
        self.protected_column = protected_column
        self.positive_value = positive_value

    def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
        col = X[self.protected_column].astype(str)
        p = np.where(col == self.positive_value, 0.9, 0.1)
        return np.column_stack([1 - p, p])


class _IncomeOnlyModel:
    """Model that ignores the protected column entirely."""

    def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
        # Threshold on income.
        scores = (X["income"].astype(float) - 20_000.0) / 20_000.0
        scores = np.clip(scores, 0.0, 1.0)
        return np.column_stack([1 - scores, scores])


def _toy_frame(n: int = 200, seed: int = 0) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    df = pd.DataFrame(
        {
            "caste": rng.choice(
                ["GENERAL", "OBC", "SC", "ST"], size=n, p=[0.4, 0.3, 0.2, 0.1]
            ),
            "income": rng.integers(5_000, 50_000, size=n).astype(float),
            "age": rng.integers(18, 65, size=n).astype(float),
            "applicant_pii": [f"row-{i}" for i in range(n)],
        }
    )
    return df


def test_counterfactual_pure_protected_model_flips_almost_everything() -> None:
    """A model that purely thresholds on protected → directional flip ≈ 1.0."""

    df = _toy_frame(n=400, seed=42)
    model = _ProtectedThresholdModel("caste", "GENERAL")

    res = compute_counterfactual_flips(
        model,
        df,
        protected_column="caste",
        protected_values=["GENERAL", "OBC", "SC", "ST"],
        threshold=0.5,
        sample_size=200,
        seed=13,
    )
    # Every row's decision flips when re-labelled to/from GENERAL.
    # Flips happen for any pair (g, g') where g == "GENERAL" XOR g' == "GENERAL".
    # Pairs not crossing the GENERAL boundary → no flip.
    # We expect directional_flip_rate to be substantially > 0.4 (not exactly
    # 1.0 because non-crossing pairs contribute zero).
    assert res.directional_flip_rate > 0.4
    # Pairs crossing the GENERAL boundary should flip 100%.
    for src in ("OBC", "SC", "ST"):
        assert res.flip_rate_by_pair[(src, "GENERAL")] == pytest.approx(1.0, abs=1e-9)
        assert res.flip_rate_by_pair[("GENERAL", src)] == pytest.approx(1.0, abs=1e-9)
    assert res.protected_column == "caste"
    assert res.sample_size_used > 0


def test_counterfactual_caste_invariant_model_yields_zero_flips() -> None:
    df = _toy_frame(n=300, seed=1)
    model = _IncomeOnlyModel()

    res = compute_counterfactual_flips(
        model,
        df,
        protected_column="caste",
        protected_values=["GENERAL", "OBC", "SC", "ST"],
        sample_size=200,
        seed=7,
    )
    assert res.directional_flip_rate == pytest.approx(0.0, abs=1e-9)
    assert all(v == 0.0 for v in res.flip_rate_by_pair.values())
    # No examples emitted because no flips occurred.
    assert res.examples == []


def test_counterfactual_examples_are_redacted() -> None:
    df = _toy_frame(n=200, seed=2)
    model = _ProtectedThresholdModel("caste", "GENERAL")

    res = compute_counterfactual_flips(
        model,
        df,
        protected_column="caste",
        protected_values=["GENERAL", "SC"],
        sample_size=100,
        seed=3,
        redact_columns=["applicant_pii"],
    )
    assert res.examples, "expected at least one flip example"
    for ex in res.examples:
        assert ex.feature_snapshot["applicant_pii"] == "[REDACTED]"
        # income / age remain visible because they were not redacted.
        assert "income" in ex.feature_snapshot
        # Protected column itself is conveyed via before/after, not in snapshot.
        assert "caste" not in ex.feature_snapshot


def test_counterfactual_rejects_single_protected_value() -> None:
    df = _toy_frame(n=50)
    with pytest.raises(ValueError):
        compute_counterfactual_flips(
            _IncomeOnlyModel(),
            df,
            protected_column="caste",
            protected_values=["GENERAL"],
        )


def test_counterfactual_rejects_unknown_column() -> None:
    df = _toy_frame(n=50)
    with pytest.raises(ValueError):
        compute_counterfactual_flips(
            _IncomeOnlyModel(),
            df,
            protected_column="unknown",
            protected_values=["A", "B"],
        )


def test_counterfactual_is_seeded_deterministic() -> None:
    df = _toy_frame(n=200, seed=8)
    model = _ProtectedThresholdModel("caste", "GENERAL")
    a = compute_counterfactual_flips(
        model, df, protected_column="caste",
        protected_values=["GENERAL", "OBC", "SC", "ST"],
        seed=99,
    )
    b = compute_counterfactual_flips(
        model, df, protected_column="caste",
        protected_values=["GENERAL", "OBC", "SC", "ST"],
        seed=99,
    )
    assert a.flip_rate_by_pair == b.flip_rate_by_pair
    assert a.directional_flip_rate == b.directional_flip_rate
    assert [ex.row_index for ex in a.examples] == [ex.row_index for ex in b.examples]
