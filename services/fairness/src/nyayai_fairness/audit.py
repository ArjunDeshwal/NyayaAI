"""Core fairness-audit pipeline.

Deterministic, classical. No Gemini. No LLM calls. No network.

Pipeline:

1. :func:`ingest.ingest` loads the dataset and emits proxy warnings.
2. Derive a binary decision from ``model_score`` (or use the outcome column).
3. Standard Fairlearn metrics per protected attribute (wrappers).
4. Intersectional slicing per requested slice tuple.
5. India-context custom metrics (SPLS + DLF; LRB requires text triples and
   is skipped unless they are provided via future extension).
6. Differential-privacy suppression for slices below k-anonymity.
7. Assemble a deterministic :class:`~nyayai_fairness.schemas.AuditResult`.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import asdict, is_dataclass
from typing import Any

import numpy as np
import pandas as pd

from nyayai_fairlearn_ext import (
    compute_group_fairness,
    compute_intersectional_fairness,
    digital_literacy_fairness,
    surname_proxy_leakage_score,
)
from nyayai_fairness.dp import DPConfig, protect_rate
from nyayai_fairness.ingest import ingest
from nyayai_fairness.schemas import (
    AuditRequest,
    AuditResult,
    CustomIndiaMetrics,
    SliceReport,
)

# Default intersectional slices keyed by *column name convention* in the
# input DataFrame. Callers can override via AuditRequest.intersectional_slices.
_DEFAULT_SLICES: tuple[tuple[str, ...], ...] = (
    ("habitation", "gender", "caste_disclosed"),
    ("habitation", "religion"),
    ("mother_tongue", "typing_cadence_quartile"),
    ("gender",),
)


def _to_jsonable(obj: Any) -> Any:
    if is_dataclass(obj):
        return _to_jsonable(asdict(obj))
    if isinstance(obj, dict):
        return {str(k): _to_jsonable(v) for k, v in obj.items()}
    if isinstance(obj, list | tuple):
        return [_to_jsonable(v) for v in obj]
    if isinstance(obj, np.generic):
        return obj.item()
    return obj


def _determinism_hash(payload: dict[str, Any]) -> str:
    """SHA-256 of a canonically-serialized payload."""

    text = json.dumps(payload, sort_keys=True, default=str, separators=(",", ":"))
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _derive_decision(
    df: pd.DataFrame, score_col: str | None, outcome_col: str, threshold: float
) -> np.ndarray:
    if score_col is None:
        return df[outcome_col].astype(int).to_numpy()
    scores = df[score_col].astype(float).to_numpy()
    return (scores >= threshold).astype(int)


def run_audit(req: AuditRequest) -> AuditResult:
    """Execute the full fairness pipeline and return a :class:`AuditResult`."""

    rng = np.random.default_rng(req.seed)
    ingest_out = ingest(
        req.dataset_uri,
        protected_columns=req.protected_columns,
        outcome_column=req.outcome_column,
        model_score_column=req.model_score_column,
    )
    df = ingest_out.df
    warnings: list[str] = list(ingest_out.warnings)

    y_true = df[req.outcome_column].astype(int).to_numpy()
    y_pred = _derive_decision(df, req.model_score_column, req.outcome_column, req.decision_threshold)

    # ----- 1. Global selection rate
    global_metrics: dict[str, float] = {
        "n_rows": float(len(df)),
        "positive_rate_true": float(y_true.mean()),
        "positive_rate_pred": float(y_pred.mean()),
        "agreement": float((y_true == y_pred).mean()),
    }

    # ----- 2. Per-attribute group fairness (wrappers around Fairlearn).
    per_attribute_metrics: dict[str, dict[str, float]] = {}
    for col in req.protected_columns:
        gf = compute_group_fairness(y_true, y_pred, df[col])
        per_attribute_metrics[col] = {
            "demographic_parity_difference": gf.demographic_parity_difference,
            "demographic_parity_ratio": gf.demographic_parity_ratio,
            "equalized_odds_difference": gf.equalized_odds_difference,
            "equal_opportunity_difference": gf.equal_opportunity_difference,
            "false_positive_rate_difference": gf.false_positive_rate_difference,
        }
        if gf.demographic_parity_ratio < 0.8:
            warnings.append(
                f"attribute '{col}' fails the 4/5ths rule: DP ratio = "
                f"{gf.demographic_parity_ratio:.3f} < 0.80"
            )

    # ----- 3. Intersectional slicing
    slice_specs = [tuple(s) for s in (req.intersectional_slices or _DEFAULT_SLICES)]
    slice_reports: list[SliceReport] = []
    dp_config = DPConfig(k_anonymity=req.dp_k_anonymity, seed=req.seed)

    for cols in slice_specs:
        missing = [c for c in cols if c not in df.columns]
        if missing:
            warnings.append(
                f"slice {cols} skipped: missing columns {missing}"
            )
            continue
        sens_df = df[list(cols)].astype(str)
        inter = compute_intersectional_fairness(
            y_true, y_pred, sens_df, min_slice_n=req.min_slice_n
        )
        for key, metrics in inter.metrics_by_slice.items():
            n = inter.n_by_slice[key]
            slice_key = {col: val for col, val in zip(cols, key, strict=True)}
            # Apply DP suppression / noise on rate metrics if small.
            dp_metrics: dict[str, float] = {}
            suppressed = False
            for mname, mval in metrics.items():
                protected_val, was_sup = protect_rate(float(mval), n, dp_config, rng)
                dp_metrics[mname] = protected_val
                suppressed = suppressed or was_sup
            slice_reports.append(
                SliceReport(
                    slice_key=slice_key,
                    n=n,
                    metrics=dp_metrics,
                    dp_protected=suppressed,
                )
            )

    # ----- 4. India-context custom metrics
    india = _compute_india_custom(df, req)

    # ----- 5. Assemble result (deterministic).
    payload_for_hash: dict[str, Any] = {
        "global": global_metrics,
        "per_attribute": per_attribute_metrics,
        "slices": [
            {"key": s.slice_key, "n": s.n, "m": s.metrics, "dp": s.dp_protected}
            for s in slice_reports
        ],
        "india": india.model_dump(),
        "seed": req.seed,
    }
    det_hash = _determinism_hash(payload_for_hash)

    return AuditResult(
        audit_id=f"audit-{uuid.uuid4().hex[:12]}",
        dataset_uri=req.dataset_uri,
        protected_columns=req.protected_columns,
        outcome_column=req.outcome_column,
        model_score_column=req.model_score_column,
        decision_threshold=req.decision_threshold,
        n_rows=len(df),
        global_metrics=global_metrics,
        per_attribute_metrics=per_attribute_metrics,
        slice_metrics=slice_reports,
        custom_india_metrics=india,
        warnings=warnings,
        determinism_hash=det_hash,
    )


def _compute_india_custom(df: pd.DataFrame, req: AuditRequest) -> CustomIndiaMetrics:
    """Compute SPLS on the first protected column + DLF if a quartile col exists."""

    spls: dict[str, Any] | None = None
    dlf: dict[str, Any] | None = None

    primary = req.protected_columns[0]
    # Features are everything other than the protected columns, outcome, and model score.
    feature_cols = [
        c
        for c in df.columns
        if c not in set(req.protected_columns)
        and c != req.outcome_column
        and c != req.model_score_column
    ]
    # Drop ids and free-text that don't contribute numerically.
    feature_cols = [c for c in feature_cols if c.lower() not in {"applicant_id", "id"}]
    if feature_cols:
        X = df[feature_cols].copy()
        spls_res = surname_proxy_leakage_score(X, df[primary], random_state=req.seed)
        spls = _to_jsonable(spls_res)

    # DLF: look for any column that fuzzy-matches "digital_literacy" / "typing_cadence".
    candidate = next(
        (c for c in df.columns if c.lower() in {"typing_cadence_quartile", "digital_literacy"}),
        None,
    )
    if candidate is not None:
        y_outcome = df[req.outcome_column].astype(int)
        dlf_res = digital_literacy_fairness(y_outcome, df[candidate])
        dlf = _to_jsonable(dlf_res)

    return CustomIndiaMetrics(spls=spls, dlf=dlf, lrb=None)
