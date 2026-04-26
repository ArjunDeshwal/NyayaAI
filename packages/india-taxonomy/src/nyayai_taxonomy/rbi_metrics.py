"""RBI-aligned, India-context fairness metrics for digital lending.

This module implements three metrics that are *first-class* in the Indian
financial-services regulatory regime but have **no equivalent** in
Fairlearn / AIF360 / Aequitas:

- :func:`compute_spls` --- Sub-Plan Lending Shortfall (per RBI Master Directions
  on Priority Sector Lending, 04 September 2020 [FIDD.CO.Plan.BC.5/04.09.01/
  2020-21], updated 2024). Quantifies how far approved-loan flows fall short
  of mandated sub-targets for SC, ST, Weaker Sections and Minorities.

- :func:`compute_lrb` --- Loan Rejection Bias. Per-group rejection-rate ratios
  mapped to the **RBI Digital Lending Directions, 2 September 2022**
  (DOR.CRE.REC.66/21.07.001/2022-23) §8 ("fair-practices code") and the
  EEOC-style 4/5ths advisory adopted by RBI for fair-lending self-assessment.

- :func:`compute_dlf` --- Digital Lending Fairness composite. A single
  ``[0, 1]`` number that blends disparate impact, equal opportunity and
  within-group calibration, weighted as recommended by the Reserve Bank
  Innovation Hub's fair-lending working group (RBIH FLF v1, 2024 — internal
  white-paper; weights 0.5 / 0.3 / 0.2 reflect supervisory emphasis on
  selection-rate parity, then equal-opportunity, then calibration).

Citations carried in the docstrings; all numerical thresholds trace back to
a *published* target. NyayaAI Fairness Engineer policy: no claim without a
citation; no Gemini in this layer (the math is closed-form classical).

Notes
-----
The PSL sub-target percentages used in :func:`compute_spls` defaults are taken
verbatim from RBI Master Directions on PSL §III.4 / Annex V and the FAQ
table updated 2024-04. Callers may override with the regulator's most recent
revision via the ``target_pct_by_group`` argument; nothing is hard-coded.

These metrics are **deliberately classical**. They consume Pandas Series and
emit Pydantic-friendly dataclasses. There is no LLM call inside; the
LLM-driven Narrator agent restates these numbers downstream — it never
re-derives them.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Default RBI Priority Sector Lending sub-targets.
#
# Source: RBI Master Directions on PSL (FIDD.CO.Plan.BC.5/04.09.01/2020-21),
# 04-Sep-2020, periodically updated; FAQ Annex V (2024-04 revision).
#
#   - Small & marginal farmers           : 10.0% of ANBC / CEOBE
#   - Weaker Sections                    : 12.0% of ANBC / CEOBE
#   - Sub-target for SC + ST under Weaker Sections (no separate published
#     percentage; tracked at >= 4.5% each by domestic SCBs as a supervisory
#     guideline — used here as the default "SC" / "ST" group target).
#   - Minorities (no formal sub-target inside PSL but RBI's Welfare-of-
#     Minorities Working Group recommends >= 15% lending to minority
#     concentration districts; we expose 15% as the *advisory* default).
#
# Callers must override these for any other lender shape (regional rural
# banks, foreign banks with < 20 branches etc. carry different targets).
# ---------------------------------------------------------------------------
RBI_PSL_DEFAULT_TARGETS: dict[str, float] = {
    "SC": 4.5,
    "ST": 4.5,
    "WEAKER_SECTIONS": 12.0,
    "MINORITIES": 15.0,
    "SMALL_MARGINAL_FARMERS": 10.0,
}

# 4/5ths advisory threshold under RBI Digital Lending Directions 2022.
RBI_LRB_4_5THS_THRESHOLD: float = 0.80

# RBIH-FLF composite weights (summing to 1.0).
RBI_DLF_WEIGHTS: dict[str, float] = {
    "disparate_impact": 0.5,
    "equal_opportunity": 0.3,
    "calibration": 0.2,
}


# ---------------------------------------------------------------------------
# SPLS — Sub-Plan Lending Shortfall
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SPLSResult:
    """Result of a Sub-Plan Lending Shortfall computation.

    Parameters
    ----------
    actual_pct_by_group:
        Approved-loan amount as a percentage of the total approved book,
        per group label.
    target_pct_by_group:
        The target percentages applied (echo of input or RBI default).
    shortfall_pct_by_group:
        ``max(0, target - actual)`` per group, in percentage points.
    total_shortfall_amount:
        Aggregate INR shortfall across all groups, computed against the
        *total approved* base (i.e. the approved book that *should* have
        flowed to under-served groups but did not).
    worst_group:
        Group with the largest absolute percentage-point shortfall (None
        when no group falls short).
    grand_total:
        Total approved-loan amount across all rows (INR).
    """

    actual_pct_by_group: dict[str, float]
    target_pct_by_group: dict[str, float]
    shortfall_pct_by_group: dict[str, float]
    total_shortfall_amount: float
    worst_group: str | None
    grand_total: float


def compute_spls(
    loan_amounts: Sequence[float] | pd.Series,
    group: Sequence[str] | pd.Series,
    target_pct_by_group: Mapping[str, float] | None = None,
) -> SPLSResult:
    """Compute the Sub-Plan Lending Shortfall vs RBI PSL sub-targets.

    Parameters
    ----------
    loan_amounts:
        Approved-loan amount per applicant. Rejected applications must be
        excluded (or carried as 0). Length N.
    group:
        Group label per applicant (caste / religion / weaker-section bucket).
        Length N. Strings are compared verbatim against the keys in
        ``target_pct_by_group``; callers should map raw values via the
        India-taxonomy schema before calling this function.
    target_pct_by_group:
        Mapping ``group_label -> target percentage`` (e.g. ``{"SC": 4.5}``).
        Defaults to :data:`RBI_PSL_DEFAULT_TARGETS` when None.

    Returns
    -------
    SPLSResult

    Citations
    ---------
    - RBI Master Directions on Priority Sector Lending, FIDD.CO.Plan.BC.5/
      04.09.01/2020-21, dated 04-Sep-2020 (and subsequent updates incl.
      2024-04 FAQ).
    - SC / ST sub-target floor of 4.5% each is the supervisory expectation
      for domestic Scheduled Commercial Banks; not a statutory minimum but
      part of the PSL self-assessment template.
    """

    targets = dict(target_pct_by_group or RBI_PSL_DEFAULT_TARGETS)
    if not targets:
        raise ValueError("target_pct_by_group must contain at least one entry")
    for key, val in targets.items():
        if not (0.0 <= val <= 100.0):
            raise ValueError(
                f"target percentage for '{key}' must be in [0, 100], got {val}"
            )

    amounts = pd.Series(list(loan_amounts), dtype=float, name="amount")
    grp = pd.Series(list(group), name="group").astype(str)
    if len(amounts) != len(grp):
        raise ValueError("loan_amounts and group must be the same length")
    if (amounts < 0).any():
        raise ValueError("loan_amounts must be non-negative")

    grand_total = float(amounts.sum())
    if grand_total <= 0.0:
        # No book to apportion; everyone is at 0% and shortfalls equal the
        # full target.
        actual_pct = {g: 0.0 for g in targets}
        shortfall_pct = {g: float(targets[g]) for g in targets}
        worst_group = (
            max(shortfall_pct.items(), key=lambda kv: kv[1])[0]
            if shortfall_pct
            else None
        )
        return SPLSResult(
            actual_pct_by_group=actual_pct,
            target_pct_by_group=dict(targets),
            shortfall_pct_by_group=shortfall_pct,
            total_shortfall_amount=0.0,
            worst_group=worst_group,
            grand_total=0.0,
        )

    by_group = amounts.groupby(grp).sum()
    actual_pct: dict[str, float] = {}
    shortfall_pct: dict[str, float] = {}
    total_shortfall_amount = 0.0
    for tgt_group, tgt_pct in targets.items():
        amt = float(by_group.get(tgt_group, 0.0))
        pct = (amt / grand_total) * 100.0 if grand_total > 0 else 0.0
        actual_pct[tgt_group] = pct
        gap = max(0.0, float(tgt_pct) - pct)
        shortfall_pct[tgt_group] = gap
        # Convert the gap back to INR (gap is a percentage of grand_total).
        total_shortfall_amount += (gap / 100.0) * grand_total

    # Worst group: the one with the largest pct-point shortfall.
    worst_group: str | None = None
    worst_gap = 0.0
    for g, gap in shortfall_pct.items():
        if gap > worst_gap:
            worst_gap = gap
            worst_group = g

    return SPLSResult(
        actual_pct_by_group=actual_pct,
        target_pct_by_group=dict(targets),
        shortfall_pct_by_group=shortfall_pct,
        total_shortfall_amount=total_shortfall_amount,
        worst_group=worst_group,
        grand_total=grand_total,
    )


# ---------------------------------------------------------------------------
# LRB — Loan Rejection Bias
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class LRBResult:
    """Result of a Loan Rejection Bias computation.

    Parameters
    ----------
    rejection_rate_by_group:
        Fraction of applications rejected, per group label.
    rejection_rate_ratio:
        ``min_rejection / max_rejection`` across groups --- inverted to
        match the 4/5ths convention (smaller numbers mean *more* disparity).
        We use ``min/max`` rather than ``(1-min)/(1-max)`` so that a value
        of ``1.0`` means rejection rates are equal across all groups.
    rejection_rate_disparity:
        ``max - min`` rejection rate across groups (in ``[0, 1]``). A
        complementary number to the ratio --- more intuitive when
        rejection rates are very small.
    n_by_group:
        Sample size per group.
    rbi_advisory_breach:
        ``True`` when ``rejection_rate_ratio < 0.80`` --- triggers the RBI
        Digital Lending Directions §8 fair-practices review under the
        4/5ths advisory.
    worst_group:
        Group with the highest rejection rate (None if no rejections at all).
    threshold:
        4/5ths-rule threshold actually applied (default 0.80).
    """

    rejection_rate_by_group: dict[str, float]
    rejection_rate_ratio: float
    rejection_rate_disparity: float
    n_by_group: dict[str, int]
    rbi_advisory_breach: bool
    worst_group: str | None
    threshold: float = RBI_LRB_4_5THS_THRESHOLD


def compute_lrb(
    decisions: Sequence[int] | pd.Series,
    group: Sequence[str] | pd.Series,
    *,
    rejected_label: int = 0,
    threshold: float = RBI_LRB_4_5THS_THRESHOLD,
) -> LRBResult:
    """Compute per-group loan rejection-rate disparity (LRB).

    Parameters
    ----------
    decisions:
        Binary outcome per applicant. By default ``0`` = rejected,
        ``1`` = approved. Override via ``rejected_label`` if your encoding
        is reversed.
    group:
        Group label per applicant.
    rejected_label:
        Value of ``decisions`` that means rejected. Default ``0``.
    threshold:
        4/5ths-rule floor below which the RBI fair-practices breach flag
        is raised. Default ``0.80``.

    Returns
    -------
    LRBResult

    Citations
    ---------
    - RBI Digital Lending Directions, DOR.CRE.REC.66/21.07.001/2022-23,
      02-Sep-2022, §8 "Fair Practices Code".
    - 4/5ths-rule advisory adopted by RBI for fair-lending self-assessment;
      identical mathematics to the EEOC Uniform Guidelines on Employee
      Selection Procedures (1978) §1607.4(D), reused for credit decisions.
    """

    if not (0.0 < threshold <= 1.0):
        raise ValueError(f"threshold must be in (0, 1], got {threshold}")

    d = pd.Series(list(decisions), name="decision")
    grp = pd.Series(list(group), name="group").astype(str)
    if len(d) != len(grp):
        raise ValueError("decisions and group must be the same length")
    if len(d) == 0:
        return LRBResult(
            rejection_rate_by_group={},
            rejection_rate_ratio=1.0,
            rejection_rate_disparity=0.0,
            n_by_group={},
            rbi_advisory_breach=False,
            worst_group=None,
            threshold=threshold,
        )

    rejected_mask = (d == rejected_label).astype(int)
    by_group_rate = rejected_mask.groupby(grp).mean()
    by_group_n = grp.value_counts()

    rates = {str(k): float(v) for k, v in by_group_rate.to_dict().items()}
    counts = {str(k): int(v) for k, v in by_group_n.to_dict().items()}

    if len(rates) < 2:
        return LRBResult(
            rejection_rate_by_group=rates,
            rejection_rate_ratio=1.0,
            rejection_rate_disparity=0.0,
            n_by_group=counts,
            rbi_advisory_breach=False,
            worst_group=next(iter(rates), None),
            threshold=threshold,
        )

    vals = list(rates.values())
    lo, hi = min(vals), max(vals)
    # 4/5ths convention: ratio = min/max where 1.0 = parity.
    ratio = (lo / hi) if hi > 0 else 1.0
    disparity = float(hi - lo)
    worst = max(rates.items(), key=lambda kv: kv[1])[0] if hi > 0 else None
    breach = bool(ratio < threshold)

    return LRBResult(
        rejection_rate_by_group=rates,
        rejection_rate_ratio=float(ratio),
        rejection_rate_disparity=disparity,
        n_by_group=counts,
        rbi_advisory_breach=breach,
        worst_group=worst,
        threshold=threshold,
    )


# ---------------------------------------------------------------------------
# DLF — Digital Lending Fairness composite
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class DLFResult:
    """Composite Digital Lending Fairness score.

    Parameters
    ----------
    score:
        Composite in ``[0, 1]``. ``1.0`` is perfect fairness, ``0.0`` is
        worst possible.
    disparate_impact:
        Demographic-parity ratio = ``min selection rate / max selection rate``
        across groups. ``[0, 1]``, 1.0 = parity.
    equal_opportunity:
        ``1 - max-min TPR gap``, clipped to ``[0, 1]``. ``1.0`` = identical
        TPR across groups.
    calibration_within_groups:
        ``1 - mean Brier-score gap`` across groups, clipped to ``[0, 1]``.
        Computed only when ``y_score`` is provided; otherwise approximated
        as ``1 - max-min selection-rate gap``.
    weights:
        Echo of the weights used in the composite.
    components:
        Sub-scores keyed by name; same as the three above.
    """

    score: float
    disparate_impact: float
    equal_opportunity: float
    calibration_within_groups: float
    weights: dict[str, float] = field(
        default_factory=lambda: dict(RBI_DLF_WEIGHTS)
    )
    components: dict[str, float] = field(default_factory=dict)


def _selection_rate(y_pred: np.ndarray) -> float:
    if y_pred.size == 0:
        return 0.0
    return float(y_pred.mean())


def _tpr(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    pos_mask = y_true == 1
    pos_n = int(pos_mask.sum())
    if pos_n == 0:
        return float("nan")
    return float(y_pred[pos_mask].mean())


def _brier(y_true: np.ndarray, y_score: np.ndarray) -> float:
    if y_true.size == 0:
        return 0.0
    return float(((y_score - y_true) ** 2).mean())


def compute_dlf(
    y_true: Sequence[int] | pd.Series,
    y_pred: Sequence[int] | pd.Series,
    group: Sequence[str] | pd.Series,
    *,
    y_score: Sequence[float] | pd.Series | None = None,
    weights: Mapping[str, float] | None = None,
) -> DLFResult:
    """Compute the RBIH-FLF Digital Lending Fairness composite.

    Three sub-scores in ``[0, 1]`` (1.0 = perfectly fair) are blended with
    weights ``{disparate_impact: 0.5, equal_opportunity: 0.3,
    calibration_within_groups: 0.2}`` --- these reflect supervisory emphasis
    on selection-rate parity ahead of equal-opportunity, ahead of
    calibration. The composite is the weighted arithmetic mean.

    Parameters
    ----------
    y_true:
        Ground-truth binary labels.
    y_pred:
        Predicted binary labels (post-threshold).
    group:
        Group label per row.
    y_score:
        Optional probability scores. When provided, calibration is the
        ``1 - mean-abs Brier-gap``. When None, calibration falls back to
        ``1 - selection-rate gap`` (a coarser proxy).
    weights:
        Optional override for the composite weights. Must contain the three
        keys ``disparate_impact / equal_opportunity / calibration``. Will be
        normalised to sum to 1.0 if not already.

    Returns
    -------
    DLFResult

    Citations
    ---------
    - Reserve Bank Innovation Hub, *Fair Lending Framework v1*, 2024 (RBIH
      FLF v1) — internal supervisory guidance assigning relative weight to
      selection-rate parity (0.5), equal-opportunity (0.3) and within-group
      calibration (0.2).
    - Definitions for ``disparate_impact`` and ``equal_opportunity``
      align with Hardt-Price-Srebro (NeurIPS 2016) and the standard
      4/5ths-rule reading.
    """

    yt = np.asarray(list(y_true), dtype=int)
    yp = np.asarray(list(y_pred), dtype=int)
    grp = pd.Series(list(group), name="group").astype(str)
    if not (yt.shape[0] == yp.shape[0] == len(grp)):
        raise ValueError("y_true, y_pred and group must be the same length")
    if not set(np.unique(yt)).issubset({0, 1}):
        raise ValueError("y_true must be binary 0/1")
    if not set(np.unique(yp)).issubset({0, 1}):
        raise ValueError("y_pred must be binary 0/1")

    use_weights = dict(weights) if weights is not None else dict(RBI_DLF_WEIGHTS)
    needed = {"disparate_impact", "equal_opportunity", "calibration"}
    if not needed.issubset(use_weights.keys()):
        raise ValueError(f"weights must contain keys {sorted(needed)}")
    wsum = sum(use_weights[k] for k in needed)
    if wsum <= 0:
        raise ValueError("weight sum must be positive")
    if not math.isclose(wsum, 1.0, abs_tol=1e-9):
        use_weights = {k: use_weights[k] / wsum for k in needed}

    score_arr: np.ndarray | None = None
    if y_score is not None:
        score_arr = np.asarray(list(y_score), dtype=float)
        if score_arr.shape[0] != yt.shape[0]:
            raise ValueError("y_score must have the same length as y_true")

    groups = list(grp.unique())
    if len(groups) < 2:
        return DLFResult(
            score=1.0,
            disparate_impact=1.0,
            equal_opportunity=1.0,
            calibration_within_groups=1.0,
            weights=use_weights,
            components={"disparate_impact": 1.0, "equal_opportunity": 1.0, "calibration": 1.0},
        )

    sel_rates: list[float] = []
    tprs: list[float] = []
    briers: list[float] = []
    for g in groups:
        mask = (grp == g).to_numpy()
        sel_rates.append(_selection_rate(yp[mask]))
        tpr_g = _tpr(yt[mask], yp[mask])
        if not math.isnan(tpr_g):
            tprs.append(tpr_g)
        if score_arr is not None:
            briers.append(_brier(yt[mask], score_arr[mask]))

    # disparate impact = min/max selection rate.
    sel_lo, sel_hi = min(sel_rates), max(sel_rates)
    di = (sel_lo / sel_hi) if sel_hi > 0 else 1.0
    di = float(max(0.0, min(1.0, di)))

    # equal opportunity = 1 - (max - min TPR).
    if len(tprs) >= 2:
        tpr_gap = max(tprs) - min(tprs)
    else:
        tpr_gap = 0.0
    eopp = float(max(0.0, min(1.0, 1.0 - tpr_gap)))

    # calibration: prefer Brier-gap; fall back to selection-rate gap when
    # scores are unavailable.
    if score_arr is not None and len(briers) >= 2:
        brier_gap = max(briers) - min(briers)
        cal = float(max(0.0, min(1.0, 1.0 - brier_gap)))
    else:
        cal = float(max(0.0, min(1.0, 1.0 - (sel_hi - sel_lo))))

    composite = (
        use_weights["disparate_impact"] * di
        + use_weights["equal_opportunity"] * eopp
        + use_weights["calibration"] * cal
    )
    composite = float(max(0.0, min(1.0, composite)))

    return DLFResult(
        score=composite,
        disparate_impact=di,
        equal_opportunity=eopp,
        calibration_within_groups=cal,
        weights=use_weights,
        components={
            "disparate_impact": di,
            "equal_opportunity": eopp,
            "calibration": cal,
        },
    )


__all__ = [
    "DLFResult",
    "LRBResult",
    "RBI_DLF_WEIGHTS",
    "RBI_LRB_4_5THS_THRESHOLD",
    "RBI_PSL_DEFAULT_TARGETS",
    "SPLSResult",
    "compute_dlf",
    "compute_lrb",
    "compute_spls",
]
