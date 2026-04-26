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
    CounterfactualExample,
    CounterfactualSummary,
    DLFResultModel,
    FeatureContribution,
    IndiaMetricBundle,
    LRBResultModel,
    ProtectedAttribute,
    RootCauseSummary,
    SliceMetric,
    SPLSResultModel,
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
    # (worst case). NaN ratios (attribute had no groups after small-group
    # filtering) are skipped; if none remain, report None.
    import math
    di_values = [
        float(m["demographic_parity_ratio"])
        for m in fairness_result.per_attribute_metrics.values()
        if "demographic_parity_ratio" in m
        and not math.isnan(float(m["demographic_parity_ratio"]))
    ]
    overall_di = min(di_values) if di_values else None

    return out, overall_di


def _intersectional_metrics(fairness_result: Any) -> list[SliceMetric]:
    """Slice rows where the slice spans more than one protected attribute."""
    out: list[SliceMetric] = []
    for s in fairness_result.slice_metrics:
        if len(s.slice_key) < 2:
            continue
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
    return out


_COLUMN_TO_SEMANTIC_FALLBACK: dict[str, ProtectedAttribute] = {
    "caste": "caste",
    "caste_disclosed": "caste",
    "jati": "caste",
    "religion": "religion",
    "dharma": "religion",
    "gender": "gender",
    "sex": "gender",
    "region": "region",
    "state": "region",
    "district": "region",
    "habitation": "urban_rural",
    "urban_rural": "urban_rural",
    "rural_urban": "urban_rural",
    "language": "language",
    "mother_tongue": "language",
    "matrubhasha": "language",
    "disability": "disability",
    "divyang": "disability",
    "age_band": "age_band",
    "age_cohort": "age_band",
    "age": "age_band",
}


def _column_to_attribute(column: str) -> ProtectedAttribute:
    """Best-effort mapping of a column name to the ProtectedAttribute literal.

    Returns ``"caste"`` as a safe fallback (the most common India-context
    primary protected column) when the column is not in the known map.
    """
    return _COLUMN_TO_SEMANTIC_FALLBACK.get(column, "caste")


def _project_counterfactual(
    fairness_result: Any, audit_id: str
) -> CounterfactualSummary | None:
    cf = getattr(fairness_result, "counterfactual", None)
    if cf is None:
        return None
    examples = [
        CounterfactualExample(
            row_index=int(ex["row_index"]),
            protected_value_before=str(ex["protected_value_before"]),
            protected_value_after=str(ex["protected_value_after"]),
            probability_before=float(
                max(0.0, min(1.0, ex["probability_before"]))
            ),
            probability_after=float(
                max(0.0, min(1.0, ex["probability_after"]))
            ),
            decision_before=int(ex["decision_before"]),
            decision_after=int(ex["decision_after"]),
            feature_snapshot={
                str(k): str(v) for k, v in ex["feature_snapshot"].items()
            },
        )
        for ex in (cf.examples or [])[:5]
    ]
    return CounterfactualSummary(
        audit_id=audit_id,
        protected_attribute=_column_to_attribute(cf.protected_column),
        directional_flip_rate=float(
            max(0.0, min(1.0, cf.directional_flip_rate))
        ),
        flip_rate_by_pair={k: float(v) for k, v in cf.flip_rate_by_pair.items()},
        examples=examples,
        sample_size_used=int(cf.sample_size_used),
    )


def _project_root_cause(
    fairness_result: Any, audit_id: str
) -> RootCauseSummary | None:
    rc = getattr(fairness_result, "root_cause", None)
    if rc is None:
        return None
    rankings = [
        FeatureContribution(
            feature_name=str(r["feature_name"]),
            contribution_to_disparity=float(r["contribution_to_disparity"]),
            contribution_to_accuracy=float(r["contribution_to_accuracy"])
            if r["contribution_to_accuracy"] == r["contribution_to_accuracy"]
            else 0.0,
        )
        for r in (rc.rankings or [])[:12]
    ]
    return RootCauseSummary(
        audit_id=audit_id,
        protected_attribute=_column_to_attribute(rc.protected_column),
        rankings=rankings,
        proxy_features=list(rc.proxy_features)[:10],
        baseline_dp_gap=float(max(0.0, min(1.0, rc.baseline_dp_gap))),
    )


def _project_india_metrics(
    fairness_result: Any, audit_id: str
) -> IndiaMetricBundle | None:
    cim = getattr(fairness_result, "custom_india_metrics", None)
    if cim is None:
        return None
    spls = cim.rbi_spls
    lrb = cim.rbi_lrb
    dlf = cim.rbi_dlf
    if spls is None and lrb is None and dlf is None:
        return None
    spls_model = (
        SPLSResultModel(
            actual_pct_by_group={
                str(k): float(v) for k, v in spls["actual_pct_by_group"].items()
            },
            target_pct_by_group={
                str(k): float(v) for k, v in spls["target_pct_by_group"].items()
            },
            shortfall_pct_by_group={
                str(k): float(v) for k, v in spls["shortfall_pct_by_group"].items()
            },
            total_shortfall_amount=float(spls["total_shortfall_amount"]),
            worst_group=spls.get("worst_group"),
            grand_total=float(max(0.0, spls["grand_total"])),
        )
        if spls is not None
        else None
    )
    lrb_model = (
        LRBResultModel(
            rejection_rate_by_group={
                str(k): float(v) for k, v in lrb["rejection_rate_by_group"].items()
            },
            rejection_rate_ratio=float(
                max(0.0, min(1.0, lrb["rejection_rate_ratio"]))
            ),
            rejection_rate_disparity=float(
                max(0.0, min(1.0, lrb["rejection_rate_disparity"]))
            ),
            n_by_group={str(k): int(v) for k, v in lrb["n_by_group"].items()},
            rbi_advisory_breach=bool(lrb["rbi_advisory_breach"]),
            worst_group=lrb.get("worst_group"),
            threshold=float(max(0.0, min(1.0, lrb.get("threshold", 0.80)))),
        )
        if lrb is not None
        else None
    )
    dlf_model = (
        DLFResultModel(
            score=float(max(0.0, min(1.0, dlf["score"]))),
            disparate_impact=float(max(0.0, min(1.0, dlf["disparate_impact"]))),
            equal_opportunity=float(max(0.0, min(1.0, dlf["equal_opportunity"]))),
            calibration_within_groups=float(
                max(0.0, min(1.0, dlf["calibration_within_groups"]))
            ),
            weights={str(k): float(v) for k, v in dlf.get("weights", {}).items()},
            components={
                str(k): float(v) for k, v in dlf.get("components", {}).items()
            },
        )
        if dlf is not None
        else None
    )
    return IndiaMetricBundle(
        audit_id=audit_id,
        spls=spls_model,
        lrb=lrb_model,
        dlf=dlf_model,
    )


def run_fairness_audit(
    request: AuditRequest,
    plan: AuditPlan,
    *,
    train_baseline: bool = False,
) -> AuditResult:
    """Execute the fairness audit described by ``plan`` against ``request``.

    This is a real call into the classical Fairlearn-backed engine. It is
    deterministic math — there is no LLM here. Do not mock this in
    integration tests; unit tests may patch it at the orchestrator seam.

    ``train_baseline`` (default False, set True by the /audit/sample path)
    asks the fairness engine to train an ephemeral LogisticRegression
    baseline so counterfactual flips and root-cause analyses can run. The
    trained model is never persisted, never logged, never sent to any LLM.
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
        if len(tup) < 2:
            # The orchestrator-level intersectional contract is "two or more
            # attributes per slice"; single-attribute slices are surfaced as
            # per-attribute metrics, not intersectional.
            continue
        cols = [_semantic_to_column(a, candidates) for a in tup]
        cols = [c for c in cols if c is not None]
        if len(cols) >= 2:
            intersectional.append(cols)

    fairness_req = FairnessAuditRequest(
        dataset_uri=ds.source_uri,
        protected_columns=ds.candidate_protected_columns,
        outcome_column=ds.outcome_column,
        model_score_column=ds.model_score_column,
        decision_threshold=ds.decision_threshold,
        intersectional_slices=intersectional or None,
        # Drop subgroups with n<20 before aggregating DP / EO across groups.
        # A 6-row JAIN subgroup with 0 positives would otherwise dominate the
        # worst-case DP ratio and bury the real caste/religion signal.
        min_slice_n=20,
        train_baseline=bool(train_baseline),
    )

    try:
        fairness_result = _run(fairness_req)
    except Exception as e:  # noqa: BLE001 — keep the shape stable for callers
        raise FairnessUnavailable(
            f"Fairness audit failed: {type(e).__name__}: {e}"
        ) from e

    metrics, overall_di = _flatten_metrics(fairness_result)
    intersectional_rows = _intersectional_metrics(fairness_result)
    counterfactual = _project_counterfactual(fairness_result, request.audit_id)
    root_cause = _project_root_cause(fairness_result, request.audit_id)
    india_metrics = _project_india_metrics(fairness_result, request.audit_id)

    return AuditResult(
        audit_id=request.audit_id,
        plan=plan,
        metrics=metrics,
        overall_disparate_impact=overall_di,
        intersectional=intersectional_rows,
        counterfactual=counterfactual,
        root_cause=root_cause,
        india_metrics=india_metrics,
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
