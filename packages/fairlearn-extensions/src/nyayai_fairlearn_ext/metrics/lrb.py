"""Linguistic-Register Bias (LRB).

**Why this metric exists:** NLP pipelines trained on pure-English corpora
systematically under-serve code-mixed Hindi-English ("Hinglish") and
transliterated Indic inputs typical of Indian mobile keyboards. Khandelwal
et al. *Indian-BhED* (FAccT 2024) documents stereotype gaps. LRB quantifies
the *outcome shift* across three linguistic registers of semantically
identical content.

**Definition:** Given a callable ``predict_fn`` that maps a list of strings
to a list of scalar scores, and three parallel lists

- ``english`` (pure English)
- ``code_mixed`` (Hinglish / code-mixed Hindi-English in Latin script)
- ``transliterated`` (Indic content in non-Latin script, e.g. Devanagari)

LRB computes the mean absolute pairwise shift of scores across registers:

    LRB = mean_i ( max_{a,b} | pred(text_i, register=a) - pred(text_i, register=b) | )

Range: ``[0, 1]`` when ``predict_fn`` returns scores in ``[0, 1]``; in
general bounded by the dynamic range of the predictor.

A well-calibrated model treats semantic equals identically across scripts;
LRB close to 0 is the target. Threshold 0.05 emits a warning.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass

import numpy as np

PredictFn = Callable[[Sequence[str]], Sequence[float]]


@dataclass(frozen=True)
class LRBResult:
    score: float  # mean max-pairwise shift
    per_pair_mean: dict[str, float]  # "en_vs_mix", "en_vs_trans", "mix_vs_trans"
    n_items: int
    registers: tuple[str, ...] = ("english", "code_mixed", "transliterated")
    threshold: float = 0.05
    shift_warning: bool = False


def _to_array(values: Sequence[float]) -> np.ndarray:
    arr = np.asarray(list(values), dtype=float)
    return arr


def linguistic_register_bias(
    predict_fn: PredictFn,
    english: Sequence[str],
    code_mixed: Sequence[str],
    transliterated: Sequence[str],
    *,
    threshold: float = 0.05,
) -> LRBResult:
    """Compute Linguistic-Register Bias.

    Parameters
    ----------
    predict_fn:
        Callable taking a list of strings and returning a list of scalar
        scores of equal length. Must be deterministic with respect to its
        input (the test suite relies on this).
    english, code_mixed, transliterated:
        Parallel sequences of semantically identical texts. Must all be
        the same length.
    threshold:
        LRB value at or above which the ``shift_warning`` flag is set.

    Returns
    -------
    LRBResult
    """

    n = len(english)
    if not (len(code_mixed) == n == len(transliterated)):
        raise ValueError(
            "english, code_mixed and transliterated must be the same length; "
            f"got {len(english)}, {len(code_mixed)}, {len(transliterated)}"
        )
    if n == 0:
        return LRBResult(
            score=0.0,
            per_pair_mean={"en_vs_mix": 0.0, "en_vs_trans": 0.0, "mix_vs_trans": 0.0},
            n_items=0,
            threshold=threshold,
            shift_warning=False,
        )

    raw_eng = list(predict_fn(list(english)))
    raw_mix = list(predict_fn(list(code_mixed)))
    raw_trans = list(predict_fn(list(transliterated)))

    if not (len(raw_eng) == len(raw_mix) == len(raw_trans) == n):
        raise ValueError(
            "predict_fn must return a sequence of the same length as its input; "
            f"got lengths {len(raw_eng)}, {len(raw_mix)}, {len(raw_trans)} for n={n}"
        )

    eng_scores = _to_array(raw_eng)
    mix_scores = _to_array(raw_mix)
    trans_scores = _to_array(raw_trans)

    d_em = np.abs(eng_scores - mix_scores)
    d_et = np.abs(eng_scores - trans_scores)
    d_mt = np.abs(mix_scores - trans_scores)

    per_item_max_shift = np.maximum.reduce([d_em, d_et, d_mt])
    score = float(per_item_max_shift.mean())

    per_pair_mean = {
        "en_vs_mix": float(d_em.mean()),
        "en_vs_trans": float(d_et.mean()),
        "mix_vs_trans": float(d_mt.mean()),
    }

    return LRBResult(
        score=score,
        per_pair_mean=per_pair_mean,
        n_items=n,
        threshold=threshold,
        shift_warning=score >= threshold,
    )
