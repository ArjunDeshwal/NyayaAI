"""Digital-Literacy Fairness (DLF).

**Why this metric exists:** Several production models silently penalize
slow typists --- a population heavily correlated with elderly, disabled
and rural users --- by using typing-cadence as a fraud or engagement
feature. DLF is outcome parity across typing-cadence quartiles (DLQ1..
DLQ4). It is a specialization of demographic parity where the protected
attribute is :class:`nyayai_taxonomy.DigitalLiteracy`.

**Definition:** DLF reports the min/max selection rate across digital
literacy quartiles, the DP *ratio* (``min/max``), and the DP *difference*
(``max - min``). Computed with Fairlearn's :class:`MetricFrame`; we do not
reimplement selection-rate math.

Threshold: DP ratio < 0.8 fails the 4/5ths rule and sets ``fails_rule``.
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
    selection_rate,
)


@dataclass(frozen=True)
class DLFResult:
    dp_ratio: float
    dp_difference: float
    selection_rate_by_quartile: dict[str, float]
    n_by_quartile: dict[str, int]
    fails_4_5ths_rule: bool
    threshold: float = 0.8
    quartile_levels: tuple[str, ...] = field(
        default=("DLQ1", "DLQ2", "DLQ3", "DLQ4")
    )


def digital_literacy_fairness(
    outcomes: Sequence[int] | pd.Series | np.ndarray,
    quartile: Sequence[str] | pd.Series,
    *,
    threshold: float = 0.8,
) -> DLFResult:
    """Compute Digital-Literacy Fairness.

    Parameters
    ----------
    outcomes:
        Binary outcomes (0/1) per subject. Length N.
    quartile:
        Digital-literacy quartile label per subject. Accepts strings such
        as ``"DLQ1"..."DLQ4"`` or any hashable label --- the metric is
        agnostic. Length N.
    threshold:
        DP ratio floor below which the 4/5ths-rule flag is tripped.

    Returns
    -------
    DLFResult
    """

    y = np.asarray(list(outcomes), dtype=int)
    q = pd.Series(list(quartile), name="quartile").astype(str)
    if len(y) != len(q):
        raise ValueError("outcomes and quartile must be the same length")
    if len(y) == 0:
        return DLFResult(
            dp_ratio=1.0,
            dp_difference=0.0,
            selection_rate_by_quartile={},
            n_by_quartile={},
            fails_4_5ths_rule=False,
            threshold=threshold,
        )
    if not set(np.unique(y)).issubset({0, 1}):
        raise ValueError("outcomes must be binary 0/1")

    frame = MetricFrame(
        metrics={"selection_rate": selection_rate},
        y_true=y,
        y_pred=y,  # using outcomes directly as predictions for group rate
        sensitive_features=q,
    )
    by_group = frame.by_group["selection_rate"].to_dict()
    counts = q.value_counts().to_dict()

    # Synthesize a y_pred that is just y so fairlearn's DP functions work:
    y_pred = y
    y_true = y
    try:
        ratio = float(demographic_parity_ratio(y_true=y_true, y_pred=y_pred, sensitive_features=q))
    except Exception:
        ratio = 1.0
    try:
        diff = float(
            demographic_parity_difference(y_true=y_true, y_pred=y_pred, sensitive_features=q)
        )
    except Exception:
        diff = 0.0

    return DLFResult(
        dp_ratio=ratio,
        dp_difference=diff,
        selection_rate_by_quartile={str(k): float(v) for k, v in by_group.items()},
        n_by_quartile={str(k): int(v) for k, v in counts.items()},
        fails_4_5ths_rule=ratio < threshold,
        threshold=threshold,
    )
