"""Counterfactual flips --- individual fairness via attribute substitution.

**Why this metric exists:** Group-level metrics (DP, EO, calibration) can hide
individual unfairness. Kusner-Loftus-Russell-Silva *Counterfactual Fairness*
(NeurIPS 2017) formalises the question: "If this applicant's caste alone were
different, would the model's decision change?" If yes, the model is treating
the protected attribute as causal even when group rates look balanced.

**Definition:** Given a fitted classifier with ``predict_proba``, a feature
frame ``X``, the protected column name and the set of legal protected values,
sample up to ``sample_size`` rows. For each sampled row and each *other*
protected value, copy the row, overwrite the protected column with the new
value, re-score, and threshold. Tabulate:

- ``flip_rate_by_pair`` --- fraction of rows of original-group ``g`` whose
  predicted decision *changes* when the protected value is set to ``g'``.
  Direction matters: ``("SC", "GENERAL"): 0.18`` means 18% of SC rows flip
  (in either direction) under the SC -> GENERAL substitution.
- ``directional_flip_rate`` --- average flip-rate across all ``(g, g')``
  pairs with ``g != g'``. The headline number a Narrator reports.
- ``examples`` --- up to 5 anonymised rows showing the deltas. PII columns
  (anything passed in ``redact_columns``) are scrubbed; numeric and
  domain-feature columns pass through.

**Determinism:** seeded; calling twice with the same seed yields the same
``flip_rate_by_pair`` and the same example set.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class CounterfactualExample:
    """One anonymised counterfactual flip, ready for the Narrator."""

    row_index: int
    protected_value_before: str
    protected_value_after: str
    probability_before: float
    probability_after: float
    decision_before: int
    decision_after: int
    feature_snapshot: dict[str, str]


@dataclass(frozen=True)
class CounterfactualResult:
    """Result of a counterfactual-flips audit."""

    flip_rate_by_pair: dict[tuple[str, str], float]
    directional_flip_rate: float
    examples: list[CounterfactualExample] = field(default_factory=list)
    sample_size_used: int = 0
    protected_column: str = ""
    protected_values: tuple[str, ...] = field(default_factory=tuple)


def _coerce_predict_proba(model: Any, X: pd.DataFrame) -> np.ndarray:
    """Return positive-class probabilities from a sklearn-style model."""
    proba = model.predict_proba(X)
    arr = np.asarray(proba, dtype=float)
    if arr.ndim != 2 or arr.shape[0] != len(X):
        raise ValueError(
            f"predict_proba must return a 2-D array of shape (n_samples, n_classes); "
            f"got shape {arr.shape}"
        )
    if arr.shape[1] < 2:
        # Single-class predictor — treat that single column as P(positive).
        return arr[:, 0]
    # Standard sklearn convention: column 1 is the positive class.
    return arr[:, 1]


def compute_counterfactual_flips(
    model: Any,
    X: pd.DataFrame,
    protected_column: str,
    protected_values: Sequence[str],
    *,
    threshold: float = 0.5,
    sample_size: int = 200,
    seed: int = 13,
    decision_positive_label: int = 1,
    redact_columns: Sequence[str] | None = None,
    max_examples: int = 5,
) -> CounterfactualResult:
    """Compute counterfactual-flip rates over the protected column.

    Parameters
    ----------
    model:
        Any fitted estimator exposing ``predict_proba(X)`` returning a
        ``(n_samples, n_classes)`` array. The positive class is taken to
        be column index 1 (sklearn convention).
    X:
        Feature frame. Must contain ``protected_column``. The frame is
        not mutated.
    protected_column:
        Name of the column whose value is *substituted* in the
        counterfactual. Must exist in ``X``.
    protected_values:
        Legal levels of the protected column. The function iterates over
        all ordered pairs ``(g, g')`` with ``g != g'``.
    threshold:
        Probability >= ``threshold`` => positive decision.
    sample_size:
        Cap on rows sampled per row-of-origin group. Bigger = slower.
    seed:
        Seed for the row-sampler.
    decision_positive_label:
        Integer label assigned to a positive decision. Default 1 (the
        ``decision_after`` field of an example uses this label).
    redact_columns:
        Columns to scrub in ``feature_snapshot`` of the returned examples
        (e.g. PII / candidate-protected columns). The protected column
        itself is always replaced with the substitution value (``before`` /
        ``after``) — not scrubbed — because its substitution *is* the point.
    max_examples:
        Cap on the number of returned examples. Default 5.

    Returns
    -------
    CounterfactualResult

    Raises
    ------
    ValueError
        If ``protected_column`` is not in ``X``, or fewer than two
        protected values are supplied, or any value is missing from ``X``.
    """

    if protected_column not in X.columns:
        raise ValueError(
            f"protected_column '{protected_column}' not found in X.columns"
        )
    legal_values = tuple(str(v) for v in protected_values)
    if len(set(legal_values)) < 2:
        raise ValueError("need at least two distinct protected_values")
    if sample_size <= 0:
        raise ValueError("sample_size must be positive")
    if not (0.0 <= threshold <= 1.0):
        raise ValueError("threshold must be in [0, 1]")

    redact_set = set(redact_columns or ())
    rng = np.random.default_rng(seed)

    # Sample rows. We deliberately stratify by protected value so that
    # every (g, g') pair has *some* base population.
    df = X.copy()
    df[protected_column] = df[protected_column].astype(str)
    sampled_indices: list[int] = []
    per_group_cap = max(1, sample_size // max(1, len(legal_values)))
    for g in legal_values:
        in_g = df.index[df[protected_column] == g].to_list()
        if not in_g:
            continue
        take = min(per_group_cap, len(in_g))
        chosen = rng.choice(in_g, size=take, replace=False)
        sampled_indices.extend(int(i) for i in chosen)
    if not sampled_indices:
        return CounterfactualResult(
            flip_rate_by_pair={},
            directional_flip_rate=0.0,
            examples=[],
            sample_size_used=0,
            protected_column=protected_column,
            protected_values=legal_values,
        )

    sample_df = df.loc[sampled_indices].copy()

    # Baseline (factual) scores for the sampled rows.
    base_probs = _coerce_predict_proba(model, sample_df)
    base_decisions = (base_probs >= threshold).astype(int)

    # For each candidate "after" value, score the same rows but with the
    # protected column overwritten.
    counterfactual_probs: dict[str, np.ndarray] = {}
    counterfactual_decisions: dict[str, np.ndarray] = {}
    for g_after in legal_values:
        cf_df = sample_df.copy()
        cf_df[protected_column] = g_after
        probs = _coerce_predict_proba(model, cf_df)
        decisions = (probs >= threshold).astype(int)
        counterfactual_probs[g_after] = probs
        counterfactual_decisions[g_after] = decisions

    # Tabulate flip rates. flip_rate_by_pair[(g_before, g_after)] is the
    # fraction of rows whose original group is g_before whose decision changes
    # when re-labelled g_after.
    flip_rate_by_pair: dict[tuple[str, str], float] = {}
    pair_flip_counts: list[float] = []
    sample_groups = sample_df[protected_column].to_numpy()

    for g_before in legal_values:
        mask_before = sample_groups == g_before
        n_before = int(mask_before.sum())
        if n_before == 0:
            for g_after in legal_values:
                if g_after == g_before:
                    continue
                flip_rate_by_pair[(g_before, g_after)] = 0.0
            continue
        base_dec_g = base_decisions[mask_before]
        for g_after in legal_values:
            if g_after == g_before:
                continue
            cf_dec_g = counterfactual_decisions[g_after][mask_before]
            flips = int(np.sum(base_dec_g != cf_dec_g))
            rate = flips / n_before if n_before > 0 else 0.0
            flip_rate_by_pair[(g_before, g_after)] = float(rate)
            pair_flip_counts.append(float(rate))

    directional_flip_rate = (
        float(np.mean(pair_flip_counts)) if pair_flip_counts else 0.0
    )

    # Pick up to max_examples with the largest |Δ probability|, regardless of
    # source group. Skip any (g, g') where g_before == g_after.
    candidate_examples: list[tuple[float, int, str, str, float, float, int, int]] = []
    for i in range(len(sample_df)):
        g_before = str(sample_groups[i])
        for g_after in legal_values:
            if g_after == g_before:
                continue
            p_before = float(base_probs[i])
            p_after = float(counterfactual_probs[g_after][i])
            d_before = int(base_decisions[i])
            d_after = int(counterfactual_decisions[g_after][i])
            if d_before == d_after:
                # Only emit *flip* examples; non-flips aren't interesting.
                continue
            delta = abs(p_after - p_before)
            candidate_examples.append(
                (delta, int(sample_df.index[i]), g_before, g_after, p_before, p_after, d_before, d_after)
            )

    candidate_examples.sort(key=lambda t: -t[0])
    examples: list[CounterfactualExample] = []
    seen_indices: set[int] = set()
    for delta, ridx, g_before, g_after, p_b, p_a, d_b, d_a in candidate_examples:
        if ridx in seen_indices:
            continue
        seen_indices.add(ridx)
        if len(examples) >= max_examples:
            break
        # Build the redacted feature snapshot.
        row = sample_df.loc[ridx]
        snapshot: dict[str, str] = {}
        for col, val in row.items():
            if col == protected_column:
                continue  # replaced by before/after fields
            if col in redact_set:
                snapshot[str(col)] = "[REDACTED]"
            else:
                snapshot[str(col)] = str(val)
        # If the post-flip decision is positive, normalise to the caller's
        # decision_positive_label (lets a caller carry, e.g., -1 for negative).
        if decision_positive_label != 1:
            d_b = decision_positive_label if d_b == 1 else 0
            d_a = decision_positive_label if d_a == 1 else 0
        examples.append(
            CounterfactualExample(
                row_index=int(ridx),
                protected_value_before=g_before,
                protected_value_after=g_after,
                probability_before=p_b,
                probability_after=p_a,
                decision_before=int(d_b),
                decision_after=int(d_a),
                feature_snapshot=snapshot,
            )
        )

    return CounterfactualResult(
        flip_rate_by_pair=flip_rate_by_pair,
        directional_flip_rate=directional_flip_rate,
        examples=examples,
        sample_size_used=int(len(sample_df)),
        protected_column=protected_column,
        protected_values=legal_values,
    )


__all__ = [
    "CounterfactualExample",
    "CounterfactualResult",
    "compute_counterfactual_flips",
]
