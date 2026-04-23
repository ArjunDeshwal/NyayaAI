"""Tests for Digital-Literacy Fairness."""

from __future__ import annotations

import numpy as np
import pytest
from hypothesis import given
from hypothesis import strategies as st

from nyayai_fairlearn_ext.metrics.dlf import digital_literacy_fairness


def test_dlf_perfect_parity() -> None:
    # 50% positive rate in every quartile.
    outcomes = [1, 0] * 40
    quartile = (["DLQ1"] * 2 + ["DLQ2"] * 2 + ["DLQ3"] * 2 + ["DLQ4"] * 2) * 10
    res = digital_literacy_fairness(outcomes, quartile)
    assert res.dp_ratio == pytest.approx(1.0, abs=1e-6)
    assert res.dp_difference == pytest.approx(0.0, abs=1e-6)
    assert res.fails_4_5ths_rule is False


def test_dlf_large_disparity() -> None:
    # 100% positive in DLQ4, 10% in DLQ1 -> DP ratio = 0.1 -> fails 4/5ths.
    rng = np.random.default_rng(0)
    q = ["DLQ1"] * 100 + ["DLQ4"] * 100
    y = list(rng.binomial(1, 0.1, 100)) + [1] * 100
    res = digital_literacy_fairness(y, q)
    assert res.dp_ratio < 0.8
    assert res.fails_4_5ths_rule is True


def test_dlf_empty_input() -> None:
    res = digital_literacy_fairness([], [])
    assert res.dp_ratio == 1.0
    assert res.dp_difference == 0.0


def test_dlf_non_binary_raises() -> None:
    with pytest.raises(ValueError):
        digital_literacy_fairness([0, 1, 2], ["DLQ1", "DLQ2", "DLQ3"])


def test_dlf_length_mismatch_raises() -> None:
    with pytest.raises(ValueError):
        digital_literacy_fairness([0, 1, 1], ["DLQ1", "DLQ2"])


# ----- Property tests -----


@given(n=st.integers(min_value=10, max_value=50))
def test_dlf_ratio_in_unit_interval(n: int) -> None:
    rng = np.random.default_rng(n)
    y = rng.binomial(1, 0.5, size=4 * n).tolist()
    q = (["DLQ1"] * n + ["DLQ2"] * n + ["DLQ3"] * n + ["DLQ4"] * n)
    res = digital_literacy_fairness(y, q)
    assert 0.0 <= res.dp_ratio <= 1.0
    assert -1.0 <= res.dp_difference <= 1.0


@given(n=st.integers(min_value=20, max_value=40))
def test_dlf_scale_invariant_under_group_size(n: int) -> None:
    # Duplicating every row should leave DLF unchanged (scale invariance).
    rng = np.random.default_rng(n)
    y = rng.binomial(1, 0.6, size=4 * n).tolist()
    q = (["DLQ1"] * n + ["DLQ2"] * n + ["DLQ3"] * n + ["DLQ4"] * n)

    res1 = digital_literacy_fairness(y, q)
    res2 = digital_literacy_fairness(y + y, q + q)
    assert res1.dp_ratio == pytest.approx(res2.dp_ratio, abs=1e-9)
    assert res1.dp_difference == pytest.approx(res2.dp_difference, abs=1e-9)
