"""Thin wrappers around Fairlearn's group-fairness metrics.

Fairlearn ships demographic_parity_*, equalized_odds_*, etc. already. This
module only standardizes the *return shape* into a Pydantic-friendly
dataclass and adds an *intersectional* grouping wrapper that uses
:class:`fairlearn.metrics.MetricFrame` with a tuple of sensitive columns.

We do NOT reimplement the underlying math.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field

import numpy as np
import pandas as pd
from fairlearn.metrics import (
    MetricFrame,
    demographic_parity_difference,
    demographic_parity_ratio,
    equalized_odds_difference,
    false_positive_rate,
    false_positive_rate_difference,
    selection_rate,
    true_positive_rate,
)


@dataclass(frozen=True)
class GroupFairnessResult:
    demographic_parity_difference: float
    demographic_parity_ratio: float
    equalized_odds_difference: float
    equal_opportunity_difference: float  # TPR gap only
    false_positive_rate_difference: float
    selection_rate_by_group: dict[str, float]
    tpr_by_group: dict[str, float]
    fpr_by_group: dict[str, float]
    n_by_group: dict[str, int]
    excluded_groups: dict[str, int] = field(default_factory=dict)


@dataclass(frozen=True)
class IntersectionalResult:
    metrics_by_slice: dict[tuple[str, ...], dict[str, float]]
    n_by_slice: dict[tuple[str, ...], int]
    sensitive_columns: tuple[str, ...] = field(default=())


def _equal_opportunity_difference(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    sensitive: pd.Series,
) -> float:
    """TPR gap = max - min of true-positive-rate across groups.

    Fairlearn does not export a single-call ``equal_opportunity_difference``
    (as of 0.12), so we compute it via MetricFrame on ``true_positive_rate``.
    """

    frame = MetricFrame(
        metrics={"tpr": true_positive_rate},
        y_true=y_true,
        y_pred=y_pred,
        sensitive_features=sensitive,
    )
    by_group = frame.by_group["tpr"].dropna()
    if by_group.empty:
        return 0.0
    return float(by_group.max() - by_group.min())


def compute_group_fairness(
    y_true: Sequence[int] | np.ndarray | pd.Series,
    y_pred: Sequence[int] | np.ndarray | pd.Series,
    sensitive: Sequence | pd.Series,
    *,
    min_group_n: int = 1,
) -> GroupFairnessResult:
    """Standard single-attribute group-fairness bundle.

    Parameters
    ----------
    y_true, y_pred:
        Binary ground-truth and predicted labels.
    sensitive:
        One sensitive column (e.g. caste or gender).
    min_group_n:
        Drop groups with fewer than this many rows before computing DP/EO/TPR
        aggregates. Small groups (n<20) produce spurious 0.0 / 1.0 ratios that
        dominate the worst-case aggregation. Excluded groups are reported in
        ``excluded_groups`` so the Narrator can disclose them.
    """

    y_true_a = np.asarray(list(y_true), dtype=int)
    y_pred_a = np.asarray(list(y_pred), dtype=int)
    s = pd.Series(list(sensitive), name="group").astype(str)

    if not (len(y_true_a) == len(y_pred_a) == len(s)):
        raise ValueError("y_true, y_pred, sensitive must all be the same length")

    excluded: dict[str, int] = {}
    if min_group_n > 1:
        counts = s.value_counts()
        small = counts[counts < min_group_n]
        if not small.empty:
            excluded = {str(g): int(n) for g, n in small.items()}
            keep_mask = ~s.isin(small.index).to_numpy()
            y_true_a = y_true_a[keep_mask]
            y_pred_a = y_pred_a[keep_mask]
            s = s[keep_mask].reset_index(drop=True)
            if len(s) == 0 or s.nunique() < 2:
                # Not enough data to compute group fairness after filtering.
                return GroupFairnessResult(
                    demographic_parity_difference=float("nan"),
                    demographic_parity_ratio=float("nan"),
                    equalized_odds_difference=float("nan"),
                    equal_opportunity_difference=float("nan"),
                    false_positive_rate_difference=float("nan"),
                    selection_rate_by_group={},
                    tpr_by_group={},
                    fpr_by_group={},
                    n_by_group={},
                    excluded_groups=excluded,
                )

    dp_diff = float(demographic_parity_difference(y_true=y_true_a, y_pred=y_pred_a, sensitive_features=s))
    dp_ratio = float(demographic_parity_ratio(y_true=y_true_a, y_pred=y_pred_a, sensitive_features=s))
    eo_diff = float(equalized_odds_difference(y_true=y_true_a, y_pred=y_pred_a, sensitive_features=s))
    fpr_diff = float(
        false_positive_rate_difference(y_true=y_true_a, y_pred=y_pred_a, sensitive_features=s)
    )
    eopp_diff = _equal_opportunity_difference(y_true_a, y_pred_a, s)

    sel_frame = MetricFrame(
        metrics={"sel": selection_rate, "tpr": true_positive_rate, "fpr": false_positive_rate},
        y_true=y_true_a,
        y_pred=y_pred_a,
        sensitive_features=s,
    )
    selection_by_group = {str(k): float(v) for k, v in sel_frame.by_group["sel"].to_dict().items()}
    tpr_by_group = {
        str(k): (float(v) if not np.isnan(v) else float("nan"))
        for k, v in sel_frame.by_group["tpr"].to_dict().items()
    }
    fpr_by_group = {
        str(k): (float(v) if not np.isnan(v) else float("nan"))
        for k, v in sel_frame.by_group["fpr"].to_dict().items()
    }
    n_by_group = {str(k): int(v) for k, v in s.value_counts().to_dict().items()}

    return GroupFairnessResult(
        demographic_parity_difference=dp_diff,
        demographic_parity_ratio=dp_ratio,
        equalized_odds_difference=eo_diff,
        equal_opportunity_difference=eopp_diff,
        false_positive_rate_difference=fpr_diff,
        selection_rate_by_group=selection_by_group,
        tpr_by_group=tpr_by_group,
        fpr_by_group=fpr_by_group,
        n_by_group=n_by_group,
        excluded_groups=excluded,
    )


def compute_intersectional_fairness(
    y_true: Sequence[int] | np.ndarray | pd.Series,
    y_pred: Sequence[int] | np.ndarray | pd.Series,
    sensitive_df: pd.DataFrame,
    *,
    min_slice_n: int = 1,
) -> IntersectionalResult:
    """Compute per-slice fairness metrics over a tuple of sensitive columns.

    Uses :class:`fairlearn.metrics.MetricFrame` --- one MetricFrame call
    per metric, all grouped by the *same* multi-column sensitive frame.
    The slice key is the column-value tuple (e.g. ``("SC", "FEMALE",
    "RURAL")``).

    Parameters
    ----------
    y_true, y_pred:
        Binary labels.
    sensitive_df:
        DataFrame whose columns are the sensitive attributes to cross.
    min_slice_n:
        Slices smaller than this are omitted from the result.

    Returns
    -------
    IntersectionalResult
    """

    y_true_a = np.asarray(list(y_true), dtype=int)
    y_pred_a = np.asarray(list(y_pred), dtype=int)
    if len(y_true_a) != len(y_pred_a) or len(y_true_a) != len(sensitive_df):
        raise ValueError("y_true, y_pred and sensitive_df must be the same length")

    cols = tuple(sensitive_df.columns.tolist())
    if not cols:
        raise ValueError("sensitive_df must have at least one column")

    frame = MetricFrame(
        metrics={
            "selection_rate": selection_rate,
            "tpr": true_positive_rate,
            "fpr": false_positive_rate,
        },
        y_true=y_true_a,
        y_pred=y_pred_a,
        sensitive_features=sensitive_df.astype(str),
    )

    # MetricFrame.by_group has a MultiIndex when there are 2+ sensitive columns.
    by_group_df = frame.by_group
    counts = sensitive_df.astype(str).value_counts()

    metrics_by_slice: dict[tuple[str, ...], dict[str, float]] = {}
    n_by_slice: dict[tuple[str, ...], int] = {}

    for idx, row in by_group_df.iterrows():
        key = idx if isinstance(idx, tuple) else (idx,)
        key_str: tuple[str, ...] = tuple(str(k) for k in key)
        n = int(counts.get(key, 0))
        if n < min_slice_n:
            continue
        metrics_by_slice[key_str] = {
            metric: (float(row[metric]) if not pd.isna(row[metric]) else float("nan"))
            for metric in row.index
        }
        n_by_slice[key_str] = n

    return IntersectionalResult(
        metrics_by_slice=metrics_by_slice,
        n_by_slice=n_by_slice,
        sensitive_columns=cols,
    )
