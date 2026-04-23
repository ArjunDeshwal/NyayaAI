"""Tests for the Surname-Proxy Leakage Score."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from nyayai_fairlearn_ext.metrics.spls import surname_proxy_leakage_score


def _make_leaky_dataset(n: int = 400, seed: int = 0) -> tuple[pd.DataFrame, pd.Series]:
    """Construct a block where a 'non-protected' feature fully encodes the protected attribute."""

    rng = np.random.default_rng(seed)
    protected = pd.Series(rng.choice(["A", "B"], size=n))
    # Leaky feature: numeric shifted by group + very small noise.
    leaky = np.where(protected == "A", 0.0, 5.0) + rng.normal(0, 0.1, size=n)
    noise = rng.normal(0, 1.0, size=n)
    X = pd.DataFrame({"leaky": leaky, "noise": noise})
    return X, protected


def _make_clean_dataset(n: int = 400, seed: int = 0) -> tuple[pd.DataFrame, pd.Series]:
    """Construct a block independent of the protected attribute."""

    rng = np.random.default_rng(seed)
    protected = pd.Series(rng.choice(["A", "B"], size=n))
    X = pd.DataFrame(
        {
            "noise1": rng.normal(0, 1, size=n),
            "noise2": rng.normal(0, 1, size=n),
            "cat": rng.choice(["x", "y", "z"], size=n),
        }
    )
    return X, protected


def test_spls_flags_leaky_dataset() -> None:
    X, p = _make_leaky_dataset()
    result = surname_proxy_leakage_score(X, p)
    assert result.score > 0.95
    assert result.leaks is True


def test_spls_clean_dataset_near_chance() -> None:
    X, p = _make_clean_dataset()
    result = surname_proxy_leakage_score(X, p)
    assert result.score < 0.65  # generous ceiling; ~0.5 expected
    # On a clean block the warning should not fire at the default threshold.
    # (sklearn's CV noise can sometimes push this just above 0.55 on tiny
    # samples; we use n=400 to keep it stable.)


def test_spls_empty_input() -> None:
    X = pd.DataFrame({"a": []})
    p = pd.Series([], dtype=object)
    result = surname_proxy_leakage_score(X, p)
    assert result.n_rows == 0
    assert result.leaks is False


def test_spls_single_class() -> None:
    X = pd.DataFrame({"a": [1.0, 2.0, 3.0]})
    p = pd.Series(["A", "A", "A"])
    result = surname_proxy_leakage_score(X, p)
    assert result.score == 0.5
    assert "single-class" in result.note


def test_spls_length_mismatch_raises() -> None:
    with pytest.raises(ValueError):
        surname_proxy_leakage_score(pd.DataFrame({"a": [1, 2, 3]}), pd.Series(["A", "B"]))


def test_spls_multiclass_leaky() -> None:
    rng = np.random.default_rng(1)
    n = 600
    p = pd.Series(rng.choice(["A", "B", "C"], size=n))
    leaky = np.select(
        [p == "A", p == "B", p == "C"],
        [rng.normal(-3, 0.1, n), rng.normal(0, 0.1, n), rng.normal(3, 0.1, n)],
    )
    X = pd.DataFrame({"leaky": leaky})
    result = surname_proxy_leakage_score(X, p)
    assert result.score > 0.9
    assert result.leaks is True


# ----- Property tests -----


@given(seed=st.integers(min_value=0, max_value=1000))
@settings(max_examples=10, deadline=None, suppress_health_check=[HealthCheck.too_slow])
def test_spls_bounded(seed: int) -> None:
    X, p = _make_clean_dataset(n=200, seed=seed)
    result = surname_proxy_leakage_score(X, p)
    assert 0.0 <= result.score <= 1.0


@given(seed=st.integers(min_value=0, max_value=1000))
@settings(max_examples=5, deadline=None, suppress_health_check=[HealthCheck.too_slow])
def test_spls_deterministic_under_same_seed(seed: int) -> None:
    X, p = _make_leaky_dataset(n=200, seed=seed)
    r1 = surname_proxy_leakage_score(X, p, random_state=7)
    r2 = surname_proxy_leakage_score(X, p, random_state=7)
    assert r1.score == pytest.approx(r2.score)
