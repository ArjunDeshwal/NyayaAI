"""Root-Cause analysis --- which feature drives the protected-attribute gap.

**Why this metric exists:** The Narrator agent needs to explain *why* a
disparity exists, not just *that* it exists. Permutation feature importance
is the standard interpretability tool for tabular models (Breiman 2001,
formalised for sklearn by Strobl-Boulesteix-Zeileis-Hothorn 2007), but the
out-of-the-box loss is *accuracy*. For fairness diagnosis we want a different
loss: **change in demographic-parity gap**.

**Definition:** For each non-protected feature ``f``:

1. Score the model and measure the demographic-parity gap (``max - min`` of
   group selection-rates) → ``dp_gap_baseline``.
2. Permute column ``f`` (i.i.d. shuffle) ``n_repeats`` times. Re-score; for
   each replicate measure the new gap.
3. ``contribution_to_disparity(f)`` = ``mean(dp_gap_baseline - dp_gap_after)``.
   A *positive* contribution means permuting ``f`` *reduces* the gap — i.e.
   ``f`` was *causing* the disparity. A near-zero or negative contribution
   means ``f`` is not the source.

We also report ``contribution_to_accuracy`` (Δ accuracy when permuted), the
standard sklearn permutation importance — useful to triangulate "this feature
is critical for accuracy AND drives bias" (a hard call) vs "this feature is
useless for accuracy AND drives bias" (an easy delete).

**Proxy features:** features whose ``contribution_to_disparity`` exceeds 0.05
(absolute) are flagged. Pincode proxying caste is the textbook example.

The math is closed-form classical. No LLM here.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pandas as pd

# Default proxy threshold — features whose permutation reduces the DP gap by
# more than this many absolute points are surfaced as "bias proxies" for the
# Narrator to discuss.
_DEFAULT_PROXY_THRESHOLD: float = 0.05


@dataclass(frozen=True)
class FeatureContribution:
    """One feature's contribution to disparity and accuracy."""

    feature_name: str
    contribution_to_disparity: float
    contribution_to_accuracy: float


@dataclass(frozen=True)
class RootCauseResult:
    """Result of a root-cause analysis."""

    feature_rankings: list[FeatureContribution]
    proxy_features: list[str]
    baseline_dp_gap: float
    baseline_accuracy: float
    protected_column: str
    proxy_threshold: float = _DEFAULT_PROXY_THRESHOLD
    n_repeats: int = 0
    seed: int = 13
    feature_universe: list[str] = field(default_factory=list)


def _selection_rate_gap(decisions: np.ndarray, groups: np.ndarray) -> float:
    """``max - min`` of per-group selection rate. NaN-safe."""
    if decisions.size == 0:
        return 0.0
    rates: list[float] = []
    for g in np.unique(groups):
        mask = groups == g
        n = int(mask.sum())
        if n == 0:
            continue
        rates.append(float(decisions[mask].mean()))
    if len(rates) < 2:
        return 0.0
    return float(max(rates) - min(rates))


def _decisions_from_model(model: Any, X: pd.DataFrame, threshold: float) -> np.ndarray:
    """Score the model on X and threshold to a hard decision."""
    if hasattr(model, "predict_proba"):
        proba = np.asarray(model.predict_proba(X), dtype=float)
        if proba.ndim == 2 and proba.shape[1] >= 2:
            scores = proba[:, 1]
        else:
            scores = proba.ravel()
        return (scores >= threshold).astype(int)
    # Fallback: predict() returns hard decisions already.
    return np.asarray(model.predict(X), dtype=int)


def compute_root_cause(
    model: Any,
    X: pd.DataFrame,
    y_pred: np.ndarray | pd.Series,
    protected_column: str,
    *,
    n_repeats: int = 10,
    seed: int = 13,
    top_k: int = 8,
    proxy_threshold: float = _DEFAULT_PROXY_THRESHOLD,
    threshold: float = 0.5,
    y_true: np.ndarray | pd.Series | None = None,
) -> RootCauseResult:
    """Permutation feature importance under a *fairness* loss.

    Parameters
    ----------
    model:
        Fitted estimator with ``predict_proba`` (preferred) or ``predict``.
    X:
        Feature frame the model was trained on. Must include
        ``protected_column``. Not mutated.
    y_pred:
        Baseline predicted hard decisions (post-threshold) on ``X``. Used
        to compute the baseline DP gap. The model is re-scored after each
        permutation to compute the new gap.
    protected_column:
        Sensitive attribute column name. Excluded from the feature universe.
    n_repeats:
        Number of permutation replicates per feature. Higher = lower
        variance, slower.
    seed:
        Seed for the column permuter.
    top_k:
        Truncate the returned ``feature_rankings`` to the top ``top_k``
        features by absolute disparity contribution.
    proxy_threshold:
        Absolute contribution above which a feature is flagged as a proxy.
        Default ``0.05`` (== 5 percentage-point reduction in the DP gap when
        the feature is shuffled out).
    threshold:
        Decision threshold to apply to ``predict_proba`` outputs. Default
        ``0.5``. Ignored when the model exposes only ``predict``.
    y_true:
        Optional ground-truth labels. When supplied, accuracy contribution
        is the standard sklearn permutation importance: baseline accuracy
        minus permuted accuracy. When None, accuracy contribution is set to
        ``NaN`` for all features.

    Returns
    -------
    RootCauseResult

    Notes
    -----
    Categorical columns are permuted directly; the model is responsible for
    its own preprocessing (we simply shuffle the column and call
    ``predict_proba`` again). Numeric columns are also shuffled directly —
    standard permutation importance.
    """

    if protected_column not in X.columns:
        raise ValueError(
            f"protected_column '{protected_column}' not found in X.columns"
        )
    if n_repeats < 1:
        raise ValueError("n_repeats must be >= 1")
    if top_k < 1:
        raise ValueError("top_k must be >= 1")

    rng = np.random.default_rng(seed)
    y_pred_arr = np.asarray(list(y_pred), dtype=int)
    if y_pred_arr.shape[0] != len(X):
        raise ValueError("y_pred must have the same length as X")
    groups = X[protected_column].astype(str).to_numpy()
    baseline_gap = _selection_rate_gap(y_pred_arr, groups)

    y_true_arr: np.ndarray | None = None
    if y_true is not None:
        y_true_arr = np.asarray(list(y_true), dtype=int)
        if y_true_arr.shape[0] != len(X):
            raise ValueError("y_true must have the same length as X")
        baseline_acc = float((y_pred_arr == y_true_arr).mean())
    else:
        baseline_acc = float("nan")

    feature_universe = [c for c in X.columns if c != protected_column]
    contributions: list[FeatureContribution] = []

    for feat in feature_universe:
        disparity_deltas: list[float] = []
        accuracy_deltas: list[float] = []
        for _ in range(n_repeats):
            X_perm = X.copy()
            permuted_col = X_perm[feat].to_numpy().copy()
            rng.shuffle(permuted_col)
            X_perm[feat] = permuted_col
            try:
                new_pred = _decisions_from_model(model, X_perm, threshold)
            except (ValueError, KeyError, TypeError):
                # Pipeline may reject the perm; record zero deltas.
                disparity_deltas.append(0.0)
                accuracy_deltas.append(0.0)
                continue
            new_gap = _selection_rate_gap(new_pred, groups)
            disparity_deltas.append(baseline_gap - new_gap)
            if y_true_arr is not None:
                new_acc = float((new_pred == y_true_arr).mean())
                accuracy_deltas.append(baseline_acc - new_acc)

        d_disp = float(np.mean(disparity_deltas)) if disparity_deltas else 0.0
        d_acc = (
            float(np.mean(accuracy_deltas))
            if accuracy_deltas
            else float("nan")
        )
        contributions.append(
            FeatureContribution(
                feature_name=feat,
                contribution_to_disparity=d_disp,
                contribution_to_accuracy=d_acc,
            )
        )

    # Rank by absolute disparity contribution, truncate.
    contributions.sort(key=lambda fc: -abs(fc.contribution_to_disparity))
    top = contributions[:top_k]
    proxies = [
        fc.feature_name
        for fc in contributions
        if abs(fc.contribution_to_disparity) >= proxy_threshold
    ]

    return RootCauseResult(
        feature_rankings=top,
        proxy_features=proxies,
        baseline_dp_gap=float(baseline_gap),
        baseline_accuracy=baseline_acc,
        protected_column=protected_column,
        proxy_threshold=float(proxy_threshold),
        n_repeats=int(n_repeats),
        seed=int(seed),
        feature_universe=list(feature_universe),
    )


__all__ = [
    "FeatureContribution",
    "RootCauseResult",
    "compute_root_cause",
]
