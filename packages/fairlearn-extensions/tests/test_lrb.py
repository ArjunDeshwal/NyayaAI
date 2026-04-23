"""Tests for Linguistic-Register Bias."""

from __future__ import annotations

from collections.abc import Sequence

import pytest
from hypothesis import given
from hypothesis import strategies as st

from nyayai_fairlearn_ext.metrics.lrb import linguistic_register_bias


def _fair_predictor(texts: Sequence[str]) -> list[float]:
    # Returns a constant score regardless of script/register -> LRB = 0.
    return [0.7 for _ in texts]


def _biased_predictor(texts: Sequence[str]) -> list[float]:
    # Penalises non-Latin content.
    out: list[float] = []
    for t in texts:
        latin_frac = (
            sum(1 for c in t if "a" <= c.lower() <= "z") / max(1, len(t))
        )
        out.append(0.9 if latin_frac > 0.5 else 0.3)
    return out


def test_lrb_fair_predictor_is_zero() -> None:
    res = linguistic_register_bias(
        _fair_predictor,
        english=["hello world"],
        code_mixed=["hello duniya"],
        transliterated=["नमस्ते दुनिया"],
    )
    assert res.score == 0.0
    assert res.shift_warning is False


def test_lrb_biased_predictor_nonzero() -> None:
    res = linguistic_register_bias(
        _biased_predictor,
        english=["hello world"],
        code_mixed=["hello duniya"],
        transliterated=["नमस्ते दुनिया"],
    )
    assert res.score > 0.0
    assert res.shift_warning is True


def test_lrb_length_mismatch_raises() -> None:
    with pytest.raises(ValueError):
        linguistic_register_bias(
            _fair_predictor,
            english=["a", "b"],
            code_mixed=["x"],
            transliterated=["y", "z"],
        )


def test_lrb_empty_input() -> None:
    res = linguistic_register_bias(_fair_predictor, [], [], [])
    assert res.score == 0.0
    assert res.n_items == 0


# ----- Property tests -----


@given(n=st.integers(min_value=1, max_value=20))
def test_lrb_symmetry_under_register_relabeling(n: int) -> None:
    english = [f"en-{i}" for i in range(n)]
    mix = [f"mix-{i}" for i in range(n)]
    trans = [f"trans-{i}" for i in range(n)]

    # Constant predictor: LRB is invariant under any permutation of the
    # three register lists.
    r1 = linguistic_register_bias(_fair_predictor, english, mix, trans)
    r2 = linguistic_register_bias(_fair_predictor, trans, mix, english)
    assert r1.score == r2.score == 0.0


@given(n=st.integers(min_value=1, max_value=10))
def test_lrb_always_non_negative(n: int) -> None:
    english = ["hello"] * n
    mix = ["hi"] * n
    trans = ["नमस्ते"] * n
    res = linguistic_register_bias(_biased_predictor, english, mix, trans)
    assert res.score >= 0.0


@given(n=st.integers(min_value=1, max_value=10))
def test_lrb_bounded_by_predictor_range(n: int) -> None:
    # _biased_predictor returns scores in [0.3, 0.9], so max pairwise shift <= 0.6.
    english = ["english only " * 3] * n
    mix = ["hello duniya"] * n
    trans = ["नमस्ते"] * n
    res = linguistic_register_bias(_biased_predictor, english, mix, trans)
    assert 0.0 <= res.score <= 0.6 + 1e-9


def test_lrb_predict_fn_must_preserve_length() -> None:
    def bad_predictor(texts: Sequence[str]) -> list[float]:
        return [0.5]  # wrong length

    with pytest.raises(ValueError):
        linguistic_register_bias(
            bad_predictor,
            english=["a", "b"],
            code_mixed=["c", "d"],
            transliterated=["e", "f"],
        )
