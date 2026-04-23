"""Bridge from the orchestrator to the classical Fairness Metrics service.

Hard rule (CLAUDE.md): Gemini must NEVER be added to ``services/fairness/``
— it's deterministic Fairlearn math. This tool is the single call-site from
the agent world into that world, and does the schema translation:

  orchestrator.AuditRequest + AuditPlan
     ↓ (this module)
  nyayai_fairness.AuditRequest  →  nyayai_fairness.AuditResult
     ↓ (this module, flattening)
  orchestrator.AuditResult

Import is lazy so orchestrator tests can run without the fairness package
installed and cleanly assert :class:`FairnessUnavailable`.
"""

from __future__ import annotations

from typing import Any

from ..schemas import (
    AuditPlan,
    AuditRequest,
    AuditResult,
    ProtectedAttribute,
    SliceMetric,
)


class FairnessUnavailable(RuntimeError):
    """Raised when the ``services/fairness`` package cannot be imported
    or cannot execute an audit. Orchestrator callers must handle this and
    fail the audit with a user-visible message (not a stack trace)."""


_ORCH_METRIC_ALIASES: dict[str, str] = {
    "demographic_parity_difference": "demographic_parity_difference",
    "demographic_parity_ratio": "demographic_parity_ratio",
    "equalized_odds_difference": "equalized_odds_difference",
    "equal_opportunity_difference": "equal_opportunity_difference",
    "disparate_impact": "disparate_impact",
    "selection_rate": "selection_rate",
    "subgroup_auc": "subgroup_auc",
}


def _format_slice_key(key: dict[str, str]) -> str:
    return ",".join(f"{k}={v}" for k, v in sorted(key.items()))


def _flatten_metrics(fairness_result: Any) -> tuple[list[SliceMetric], float | None]:
    """Flatten the fairness package's structured result into a list of
    :class:`SliceMetric` rows plus an overall disparate-impact number.
    """
    out: list[SliceMetric] = []

    # Per-attribute: each attribute becomes one row per supported metric.
    for attr, metric_map in fairness_result.per_attribute_metrics.items():
        n = int(fairness_result.n_rows)
        for mname, mval in metric_map.items():
            if mname not in _ORCH_METRIC_ALIASES:
                continue
            out.append(
                SliceMetric(
                    slice_key=f"attribute={attr}",
                    metric=_ORCH_METRIC_ALIASES[mname],  # type: ignore[arg-type]
                    value=float(mval),
                    sample_size=n,
                )
            )

    # Intersectional slices: one row per (slice, rate-like metric).
    for s in fairness_result.slice_metrics:
        key = _format_slice_key(s.slice_key)
        for mname, mval in s.metrics.items():
            if mname not in _ORCH_METRIC_ALIASES:
                continue
            out.append(
                SliceMetric(
                    slice_key=key,
                    metric=_ORCH_METRIC_ALIASES[mname],  # type: ignore[arg-type]
                    value=float(mval),
                    sample_size=int(s.n),
                )
            )

    # Overall DI = minimum demographic_parity_ratio across protected attributes
    # (worst case). Falls back to None if no rate was computable.
    di_values = [
        m["demographic_parity_ratio"]
        for m in fairness_result.per_attribute_metrics.values()
        if "demographic_parity_ratio" in m
    ]
    overall_di = float(min(di_values)) if di_values else None

    return out, overall_di


def run_fairness_audit(request: AuditRequest, plan: AuditPlan) -> AuditResult:
    """Execute the fairness audit described by ``plan`` against ``request``.

    This is a real call into the classical Fairlearn-backed engine. It is
    deterministic math — there is no LLM here. Do not mock this in
    integration tests; unit tests may patch it at the orchestrator seam.
    """
    try:
        from nyayai_fairness.audit import run_audit as _run  # type: ignore[import-not-found]
        from nyayai_fairness.schemas import (  # type: ignore[import-not-found]
            AuditRequest as FairnessAuditRequest,
        )
    except ImportError as e:
        raise FairnessUnavailable(
            "services/fairness is not installed. Install the nyayai-fairness "
            "package (uv sync should handle the workspace editable install)."
        ) from e

    ds = request.dataset
    if ds.source_uri is None:
        raise FairnessUnavailable(
            "AuditRequest.dataset.source_uri is required to run the fairness engine."
        )
    if ds.outcome_column is None:
        raise FairnessUnavailable(
            "AuditRequest.dataset.outcome_column is required to run the fairness engine."
        )
    if not ds.candidate_protected_columns:
        raise FairnessUnavailable(
            "AuditRequest.dataset.candidate_protected_columns must be non-empty."
        )

    # Map planned ProtectedAttribute slices to actual column names.
    # If the plan's slice references a semantic attribute that isn't in
    # candidate_protected_columns, skip it silently — the fairness engine's
    # defaults will take over.
    intersectional: list[list[str]] = []
    candidates = set(ds.candidate_protected_columns)
    for tup in plan.slices:
        cols = [_semantic_to_column(a, candidates) for a in tup]
        cols = [c for c in cols if c is not None]
        if cols:
            intersectional.append(cols)

    fairness_req = FairnessAuditRequest(
        dataset_uri=ds.source_uri,
        protected_columns=ds.candidate_protected_columns,
        outcome_column=ds.outcome_column,
        model_score_column=ds.model_score_column,
        decision_threshold=ds.decision_threshold,
        intersectional_slices=intersectional or None,
    )

    try:
        fairness_result = _run(fairness_req)
    except Exception as e:  # noqa: BLE001 — keep the shape stable for callers
        raise FairnessUnavailable(
            f"Fairness audit failed: {type(e).__name__}: {e}"
        ) from e

    metrics, overall_di = _flatten_metrics(fairness_result)

    return AuditResult(
        audit_id=request.audit_id,
        plan=plan,
        metrics=metrics,
        overall_disparate_impact=overall_di,
    )


def _semantic_to_column(
    attr: ProtectedAttribute, candidates: set[str]
) -> str | None:
    """Best-effort map from semantic attribute to a column name in the dataset."""
    if attr in candidates:
        return attr
    synonyms = {
        "caste": ["caste", "caste_disclosed", "jati"],
        "religion": ["religion", "dharma"],
        "gender": ["gender", "sex"],
        "region": ["region", "state", "district"],
        "urban_rural": ["habitation", "urban_rural", "rural_urban"],
        "language": ["language", "mother_tongue", "matrubhasha"],
        "disability": ["disability", "divyang"],
        "age_band": ["age_band", "age_cohort", "age"],
    }.get(attr, [])
    for s in synonyms:
        if s in candidates:
            return s
    return None
