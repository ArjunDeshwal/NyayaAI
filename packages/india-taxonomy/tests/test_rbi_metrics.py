"""Tests for the RBI-aligned India fairness metrics (SPLS / LRB / DLF)."""

from __future__ import annotations

import math

import numpy as np
import pandas as pd
import pytest
from hypothesis import given
from hypothesis import strategies as st

from nyayai_taxonomy.rbi_metrics import (
    RBI_DLF_WEIGHTS,
    RBI_LRB_4_5THS_THRESHOLD,
    RBI_PSL_DEFAULT_TARGETS,
    compute_dlf,
    compute_lrb,
    compute_spls,
)


# ---------------------------------------------------------------------------
# SPLS — Sub-Plan Lending Shortfall
# ---------------------------------------------------------------------------


def test_spls_known_answer_sc_at_2_percent_target_4_5() -> None:
    """SC at 2% with target 4.5% → shortfall 2.5 percentage points.

    Build a 100-row book of INR 10,000 each. SC owns 20 rows
    (so SC share = 20%), but SC's *amount* is 1/10 of the others, making
    SC's share-of-amount 1.96%. We round-trip the math with explicit
    weights so the computed SC pct lands at ≈ 2.0%.
    """

    # 200 rows total: 4 SC rows of INR 10_000 (40_000),
    # 196 GENERAL rows of INR 10_000 (1_960_000). Total = 2_000_000.
    # SC pct = 40_000 / 2_000_000 = 2.0%.
    amounts = [10_000.0] * 4 + [10_000.0] * 196
    groups = ["SC"] * 4 + ["GENERAL"] * 196

    res = compute_spls(amounts, groups, target_pct_by_group={"SC": 4.5})
    assert math.isclose(res.actual_pct_by_group["SC"], 2.0, abs_tol=0.01)
    assert math.isclose(res.shortfall_pct_by_group["SC"], 2.5, abs_tol=0.01)
    assert res.worst_group == "SC"
    assert res.grand_total == pytest.approx(2_000_000.0, abs=1.0)
    # 2.5% of 2_000_000 = 50_000 INR shortfall.
    assert math.isclose(res.total_shortfall_amount, 50_000.0, abs_tol=1.0)


def test_spls_no_shortfall_when_actual_meets_target() -> None:
    # SC owns 5% of the book, target is 4.5% → zero shortfall.
    amounts = [100.0] * 100
    groups = ["SC"] * 5 + ["GENERAL"] * 95
    res = compute_spls(amounts, groups, target_pct_by_group={"SC": 4.5})
    assert res.shortfall_pct_by_group["SC"] == 0.0
    assert res.total_shortfall_amount == 0.0
    assert res.worst_group is None


def test_spls_uses_default_targets_when_omitted() -> None:
    amounts = [100.0] * 100
    groups = ["SC"] * 1 + ["GENERAL"] * 99  # SC pct = 1%, target = 4.5%
    res = compute_spls(amounts, groups)
    # Default targets include SC at 4.5%.
    assert res.target_pct_by_group["SC"] == RBI_PSL_DEFAULT_TARGETS["SC"]
    assert res.shortfall_pct_by_group["SC"] > 3.0


def test_spls_rejects_negative_amounts() -> None:
    with pytest.raises(ValueError):
        compute_spls([-1.0, 2.0], ["SC", "GENERAL"], target_pct_by_group={"SC": 4.5})


def test_spls_rejects_mismatched_lengths() -> None:
    with pytest.raises(ValueError):
        compute_spls([1.0, 2.0, 3.0], ["SC", "GENERAL"], target_pct_by_group={"SC": 4.5})


def test_spls_zero_grand_total_returns_full_target_shortfall() -> None:
    # Empty book: every targeted group is 100% short.
    res = compute_spls(
        [0.0, 0.0, 0.0],
        ["SC", "ST", "GENERAL"],
        target_pct_by_group={"SC": 4.5, "ST": 4.5},
    )
    assert res.grand_total == 0.0
    assert res.shortfall_pct_by_group["SC"] == 4.5
    assert res.shortfall_pct_by_group["ST"] == 4.5


# ---------------------------------------------------------------------------
# LRB — Loan Rejection Bias
# ---------------------------------------------------------------------------


def test_lrb_detects_4_5ths_breach() -> None:
    # SC: 80% rejected (8 of 10). GENERAL: 20% rejected (2 of 10).
    # ratio = 0.20 / 0.80 = 0.25 → < 0.80 → breach.
    decisions = [0] * 8 + [1] * 2 + [0] * 2 + [1] * 8  # 0=rejected
    groups = ["SC"] * 10 + ["GENERAL"] * 10
    res = compute_lrb(decisions, groups)
    assert res.rbi_advisory_breach is True
    assert res.rejection_rate_ratio == pytest.approx(0.25, abs=1e-6)
    assert res.worst_group == "SC"
    assert res.threshold == RBI_LRB_4_5THS_THRESHOLD


def test_lrb_no_breach_when_rates_close() -> None:
    # 50/50 rejection in both groups → ratio = 1.0.
    decisions = ([0, 1] * 5) + ([0, 1] * 5)
    groups = ["A"] * 10 + ["B"] * 10
    res = compute_lrb(decisions, groups)
    assert res.rejection_rate_ratio == pytest.approx(1.0, abs=1e-9)
    assert res.rbi_advisory_breach is False


def test_lrb_handles_single_group() -> None:
    res = compute_lrb([0, 1, 0, 1], ["A", "A", "A", "A"])
    assert res.rejection_rate_ratio == 1.0
    assert res.rbi_advisory_breach is False


def test_lrb_rejects_invalid_threshold() -> None:
    with pytest.raises(ValueError):
        compute_lrb([0, 1], ["A", "B"], threshold=1.5)


def test_lrb_supports_inverted_label() -> None:
    # Encoding flipped: 1 = rejected.
    decisions = [1, 1, 0, 0]
    groups = ["A", "A", "B", "B"]
    res = compute_lrb(decisions, groups, rejected_label=1)
    assert res.rejection_rate_by_group["A"] == 1.0
    assert res.rejection_rate_by_group["B"] == 0.0


# ---------------------------------------------------------------------------
# DLF — Digital Lending Fairness composite
# ---------------------------------------------------------------------------


def test_dlf_perfect_fairness_yields_score_one() -> None:
    # Construct A and B to have identical selection rates AND identical TPRs.
    n = 100
    y_true = np.array([1] * 50 + [0] * 50, dtype=int)
    y_pred = y_true.copy()
    groups = ["A"] * 25 + ["B"] * 25 + ["A"] * 25 + ["B"] * 25
    res = compute_dlf(y_true, y_pred, groups)
    assert res.score == pytest.approx(1.0, abs=1e-9)
    assert res.disparate_impact == pytest.approx(1.0, abs=1e-9)
    assert res.equal_opportunity == pytest.approx(1.0, abs=1e-9)


def test_dlf_full_disparity_yields_low_score() -> None:
    # Group A: all approved. Group B: all rejected.
    n = 100
    y_true = np.ones(n, dtype=int)
    y_pred = np.array([1] * 50 + [0] * 50)
    groups = ["A"] * 50 + ["B"] * 50
    res = compute_dlf(y_true, y_pred, groups)
    assert res.disparate_impact == pytest.approx(0.0, abs=1e-9)
    assert res.equal_opportunity == pytest.approx(0.0, abs=1e-9)
    # Composite = 0.5*0 + 0.3*0 + 0.2*(1 - 1) = 0.0
    assert res.score == pytest.approx(0.0, abs=1e-9)


def test_dlf_uses_default_weights() -> None:
    n = 50
    y_true = np.ones(n, dtype=int)
    y_pred = y_true.copy()
    groups = ["A"] * 25 + ["B"] * 25
    res = compute_dlf(y_true, y_pred, groups)
    assert res.weights == pytest.approx(RBI_DLF_WEIGHTS)


def test_dlf_rejects_non_binary_labels() -> None:
    with pytest.raises(ValueError):
        compute_dlf([0, 1, 2], [0, 1, 1], ["A", "B", "B"])


def test_dlf_with_y_score_uses_brier_calibration() -> None:
    # Constant scores in both groups → calibration is good.
    n = 60
    y_true = np.zeros(n, dtype=int)
    y_pred = np.zeros(n, dtype=int)
    y_score = np.full(n, 0.1, dtype=float)
    groups = ["A"] * 30 + ["B"] * 30
    res = compute_dlf(y_true, y_pred, groups, y_score=y_score)
    # Brier score is identical in both groups → cal = 1.0.
    assert res.calibration_within_groups == pytest.approx(1.0, abs=1e-9)


def test_dlf_normalises_weights_when_not_summing_to_one() -> None:
    n = 40
    y_true = np.ones(n, dtype=int)
    y_pred = y_true.copy()
    groups = ["A"] * 20 + ["B"] * 20
    res = compute_dlf(
        y_true,
        y_pred,
        groups,
        weights={"disparate_impact": 2.0, "equal_opportunity": 1.0, "calibration": 1.0},
    )
    # Sum of weights normalises to 1.
    assert math.isclose(sum(res.weights.values()), 1.0, abs_tol=1e-9)


# ---------------------------------------------------------------------------
# Property tests
# ---------------------------------------------------------------------------


@given(
    pct_a=st.floats(min_value=0.0, max_value=100.0, allow_nan=False),
    pct_b=st.floats(min_value=0.0, max_value=100.0, allow_nan=False),
)
def test_lrb_ratio_is_in_unit_interval(pct_a: float, pct_b: float) -> None:
    n = 100
    decisions = (
        [0] * int(round(n * pct_a / 100.0))
        + [1] * (n - int(round(n * pct_a / 100.0)))
        + [0] * int(round(n * pct_b / 100.0))
        + [1] * (n - int(round(n * pct_b / 100.0)))
    )
    groups = ["A"] * n + ["B"] * n
    res = compute_lrb(decisions, groups)
    assert 0.0 <= res.rejection_rate_ratio <= 1.0
    assert 0.0 <= res.rejection_rate_disparity <= 1.0


@given(seed=st.integers(min_value=0, max_value=999))
def test_dlf_score_in_unit_interval(seed: int) -> None:
    rng = np.random.default_rng(seed)
    n = 60
    y_true = rng.binomial(1, 0.5, size=n)
    y_pred = rng.binomial(1, 0.5, size=n)
    groups = rng.choice(["A", "B", "C"], size=n)
    res = compute_dlf(y_true, y_pred, pd.Series(groups))
    assert 0.0 <= res.score <= 1.0
    assert 0.0 <= res.disparate_impact <= 1.0
    assert 0.0 <= res.equal_opportunity <= 1.0
