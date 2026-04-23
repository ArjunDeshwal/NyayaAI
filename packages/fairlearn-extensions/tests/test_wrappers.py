"""Tests for the Fairlearn wrappers."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
from hypothesis import given
from hypothesis import strategies as st

from nyayai_fairlearn_ext.wrappers import (
    compute_group_fairness,
    compute_intersectional_fairness,
)


def _make_biased(n: int = 400, seed: int = 0) -> tuple[np.ndarray, np.ndarray, pd.Series]:
    rng = np.random.default_rng(seed)
    group = rng.choice(["A", "B"], size=n)
    # Group A gets positive 70%; group B gets positive 30%.
    y_pred = np.where(
        group == "A",
        rng.binomial(1, 0.7, size=n),
        rng.binomial(1, 0.3, size=n),
    )
    y_true = rng.binomial(1, 0.5, size=n)
    return y_true, y_pred, pd.Series(group)


def test_group_fairness_detects_disparity() -> None:
    y_true, y_pred, s = _make_biased(seed=1)
    res = compute_group_fairness(y_true, y_pred, s)
    assert res.demographic_parity_difference > 0.2
    assert res.demographic_parity_ratio < 0.8
    assert set(res.selection_rate_by_group.keys()) == {"A", "B"}
    assert res.n_by_group["A"] + res.n_by_group["B"] == 400


def test_group_fairness_parity() -> None:
    # Same selection rate in both groups.
    n = 200
    group = np.array(["A"] * n + ["B"] * n)
    y_pred = np.array(([1, 0] * (n // 2)) * 2)
    y_true = y_pred.copy()
    res = compute_group_fairness(y_true, y_pred, pd.Series(group))
    assert res.demographic_parity_difference == pytest.approx(0.0, abs=1e-9)
    assert res.demographic_parity_ratio == pytest.approx(1.0, abs=1e-9)


def test_group_fairness_length_mismatch() -> None:
    with pytest.raises(ValueError):
        compute_group_fairness([0, 1], [0, 1, 1], ["A", "B", "B"])


def test_intersectional_fairness_slicing() -> None:
    rng = np.random.default_rng(2)
    n = 600
    caste = rng.choice(["GENERAL", "SC"], size=n)
    gender = rng.choice(["MALE", "FEMALE"], size=n)
    y_pred = np.where((caste == "GENERAL") & (gender == "MALE"), 1, 0)
    y_true = rng.binomial(1, 0.5, size=n)

    df = pd.DataFrame({"caste": caste, "gender": gender})
    res = compute_intersectional_fairness(y_true, y_pred, df)
    assert res.sensitive_columns == ("caste", "gender")
    # Four expected slices.
    assert set(res.metrics_by_slice.keys()) == {
        ("GENERAL", "MALE"),
        ("GENERAL", "FEMALE"),
        ("SC", "MALE"),
        ("SC", "FEMALE"),
    }
    # The GENERAL × MALE slice has selection rate 1.0, the others 0.0.
    assert res.metrics_by_slice[("GENERAL", "MALE")]["selection_rate"] == pytest.approx(1.0)
    assert res.metrics_by_slice[("SC", "FEMALE")]["selection_rate"] == pytest.approx(0.0)


def test_intersectional_min_slice_n_drops_small() -> None:
    df = pd.DataFrame(
        {
            "caste": ["GENERAL"] * 98 + ["SC"] * 2,
            "gender": ["MALE"] * 50 + ["FEMALE"] * 48 + ["MALE", "FEMALE"],
        }
    )
    y = np.ones(100, dtype=int)
    res = compute_intersectional_fairness(y, y, df, min_slice_n=5)
    # SC × MALE and SC × FEMALE each have n=1; they should be dropped.
    assert all(k[0] == "GENERAL" for k in res.metrics_by_slice)


def test_intersectional_requires_at_least_one_column() -> None:
    with pytest.raises(ValueError):
        compute_intersectional_fairness([0, 1], [0, 1], pd.DataFrame())


# ----- Property tests -----


@given(seed=st.integers(min_value=0, max_value=1000))
def test_dp_difference_antisymmetric_under_group_swap(seed: int) -> None:
    """Swapping group labels must negate DP difference up to sign."""

    rng = np.random.default_rng(seed)
    n = 200
    group = rng.choice(["A", "B"], size=n)
    y_pred = rng.binomial(1, 0.6, size=n)
    y_true = rng.binomial(1, 0.5, size=n)

    res_a = compute_group_fairness(y_true, y_pred, pd.Series(group))

    # Swap labels A <-> B.
    swapped = pd.Series(np.where(group == "A", "B", "A"))
    res_b = compute_group_fairness(y_true, y_pred, swapped)

    # |diff| is invariant; ratio is invariant (Fairlearn returns min/max).
    assert res_a.demographic_parity_difference == pytest.approx(
        res_b.demographic_parity_difference, abs=1e-9
    )
    assert res_a.demographic_parity_ratio == pytest.approx(
        res_b.demographic_parity_ratio, abs=1e-9
    )


@given(seed=st.integers(min_value=0, max_value=1000))
def test_dp_difference_in_range(seed: int) -> None:
    rng = np.random.default_rng(seed)
    n = 100
    group = rng.choice(["A", "B"], size=n)
    y_pred = rng.binomial(1, 0.5, size=n)
    y_true = rng.binomial(1, 0.5, size=n)
    res = compute_group_fairness(y_true, y_pred, pd.Series(group))
    assert -1.0 <= res.demographic_parity_difference <= 1.0
    assert 0.0 <= res.demographic_parity_ratio <= 1.0
    assert 0.0 <= res.equalized_odds_difference <= 1.0


@given(seed=st.integers(min_value=0, max_value=1000))
def test_dp_scale_invariance(seed: int) -> None:
    """Duplicating every row must leave DP metrics unchanged."""

    rng = np.random.default_rng(seed)
    n = 100
    group = rng.choice(["A", "B"], size=n)
    y_pred = rng.binomial(1, 0.5, size=n)
    y_true = rng.binomial(1, 0.5, size=n)

    r1 = compute_group_fairness(y_true, y_pred, pd.Series(group))
    r2 = compute_group_fairness(
        np.concatenate([y_true, y_true]),
        np.concatenate([y_pred, y_pred]),
        pd.Series(np.concatenate([group, group])),
    )
    assert r1.demographic_parity_difference == pytest.approx(
        r2.demographic_parity_difference, abs=1e-9
    )
    assert r1.demographic_parity_ratio == pytest.approx(r2.demographic_parity_ratio, abs=1e-9)
