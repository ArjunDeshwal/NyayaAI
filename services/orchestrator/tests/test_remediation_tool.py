"""Unit tests for the classical remediation tool.

No Gemini; no mocking of Fairlearn. Synthetic 500-row dataset where the
model_score is deliberately biased against a protected group; the remediated
DP ratio must strictly exceed the baseline DP ratio.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from nyayai_orchestrator.schemas import (
    AuditPlan,
    AuditRequest,
    AuditResult,
    AuditStep,
    DatasetDescriptor,
    ModelCard,
    SliceMetric,
)
from nyayai_orchestrator.tools.remediation_tool import (
    RemediationUnavailable,
    run_remediation,
)


def _synthetic_frame(n: int = 500, seed: int = 7) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    gender = rng.choice(["F", "M"], size=n, p=[0.5, 0.5])
    income = rng.normal(25_000, 5_000, size=n).clip(5_000, 80_000)
    education = rng.integers(6, 16, size=n)
    # Approved: base signal on income + education + noise (gender-neutral).
    gt_logit = -2.0 + 0.00006 * income + 0.15 * education + rng.normal(0, 0.4, n)
    approved = (1.0 / (1.0 + np.exp(-gt_logit)) > 0.5).astype(int)
    # Intentionally biased model_score: large penalty for F.
    biased_logit = gt_logit - np.where(gender == "F", 1.2, 0.0)
    model_score = 1.0 / (1.0 + np.exp(-biased_logit))
    return pd.DataFrame(
        {
            "gender": gender,
            "income": income.astype(int),
            "education_years": education,
            "approved": approved,
            "model_score": model_score,
        }
    )


def _write(df: pd.DataFrame, tmp_path: Path) -> Path:
    p = tmp_path / "syn.parquet"
    df.to_parquet(p, index=False)
    return p


def _plan(audit_id: str) -> AuditPlan:
    return AuditPlan(
        audit_id=audit_id,
        steps=[
            AuditStep(
                step_id="s1",
                kind="metric",
                description="DP on gender.",
                target_attributes=["gender"],
            )
        ],
        slices=[["gender"]],
        rationale="Single-attribute audit on gender to exercise remediation.",
        estimated_minutes=3,
    )


def _request_for(path: Path) -> AuditRequest:
    return AuditRequest(
        audit_id="aud-rem-001",
        goal="Remediate gender disparity in synthetic approval model.",
        regime="DPDP",
        model=ModelCard(
            model_id="syn-v1",
            task="binary_classification",
            description="Synthetic approval classifier with seeded gender bias.",
        ),
        dataset=DatasetDescriptor(
            name="synthetic",
            row_count=500,
            columns=["gender", "income", "education_years", "approved", "model_score"],
            candidate_protected_columns=["gender"],
            source_uri=str(path),
            outcome_column="approved",
            model_score_column="model_score",
            decision_threshold=0.5,
        ),
        requested_attributes=["gender"],
    )


def _result_with_dp(request: AuditRequest, plan: AuditPlan, dp_ratio: float) -> AuditResult:
    """Synthesise an AuditResult with a low DP ratio so the remediation tool
    picks ``gender`` as the worst attribute."""
    return AuditResult(
        audit_id=request.audit_id,
        plan=plan,
        metrics=[
            SliceMetric(
                slice_key="attribute=gender",
                metric="demographic_parity_ratio",
                value=dp_ratio,
                sample_size=500,
            ),
            SliceMetric(
                slice_key="attribute=gender",
                metric="demographic_parity_difference",
                value=0.35,
                sample_size=500,
            ),
        ],
        overall_disparate_impact=dp_ratio,
    )


def test_remediation_tool_lifts_dp_ratio(tmp_path: Path) -> None:
    df = _synthetic_frame(n=500, seed=7)
    path = _write(df, tmp_path)
    request = _request_for(path)
    plan = _plan(request.audit_id)
    # Seed an input AuditResult with a deliberately-low DP ratio.
    result = _result_with_dp(request, plan, dp_ratio=0.45)

    outcome = run_remediation(request, result, epsilon=0.05, random_state=7)

    # Sanity on structure.
    assert outcome.audit_id == request.audit_id
    assert outcome.target_column == "gender"
    assert outcome.target_attribute == "gender"
    assert outcome.n_test > 0
    assert outcome.n_train > 0
    assert outcome.mitigation_name.startswith("fairlearn.reductions.ExponentiatedGradient")

    # The authoritative numbers must move in the right direction.
    # Baseline LR has no bias constraint, so its DP ratio is typically < 0.8
    # on the seeded bias. The remediated DP ratio must strictly exceed it.
    assert 0.0 < outcome.before_dp_ratio <= 1.0
    assert outcome.after_dp_ratio > outcome.before_dp_ratio, (
        f"remediation did not improve DP ratio: "
        f"before={outcome.before_dp_ratio:.3f} after={outcome.after_dp_ratio:.3f}"
    )

    # Accuracy shouldn't collapse completely; a mild drop is acceptable.
    assert outcome.baseline_accuracy > 0.5
    assert outcome.remediated_accuracy > 0.4  # reductions can trade a few points
    # accuracy_delta_pp is (remediated - baseline) * 100, typically negative.
    assert outcome.accuracy_delta_pp == pytest.approx(
        (outcome.remediated_accuracy - outcome.baseline_accuracy) * 100.0, abs=0.05
    )


def test_remediation_requires_source_uri(tmp_path: Path) -> None:
    df = _synthetic_frame(n=200, seed=1)
    path = _write(df, tmp_path)
    req = _request_for(path)
    # Strip the source_uri to force the error.
    broken = req.model_copy(
        update={
            "dataset": req.dataset.model_copy(update={"source_uri": None}),
        }
    )
    plan = _plan(req.audit_id)
    result = _result_with_dp(broken, plan, dp_ratio=0.4)
    with pytest.raises(RemediationUnavailable):
        run_remediation(broken, result)


def test_remediation_skips_high_cardinality_target(tmp_path: Path) -> None:
    """Attribute with >10 groups should be refused by the shape rule even
    when its DP ratio is the worst — the reductions solver over-steers on
    such targets (production regression: state with 28 groups took DP from
    0.608 to 0.342). Tool must emit improved=False with a truthful reason."""
    rng = np.random.default_rng(11)
    n = 2_000
    # 25-group region attribute with non-trivial bias.
    region = rng.choice([f"R{i:02d}" for i in range(25)], size=n)
    income = rng.normal(20_000, 4_000, size=n).clip(5_000, 80_000)
    education = rng.integers(6, 16, size=n)
    # Base logit + a small region-specific bias on a subset.
    region_bias = np.where(np.isin(region, ["R00", "R01", "R02"]), -1.5, 0.0)
    base = -2.0 + 0.00006 * income + 0.15 * education + region_bias
    approved = (1.0 / (1.0 + np.exp(-base + rng.normal(0, 0.3, n))) > 0.5).astype(int)
    model_score = 1.0 / (1.0 + np.exp(-base))
    df = pd.DataFrame(
        {
            "region": region,
            "income": income.astype(int),
            "education_years": education,
            "approved": approved,
            "model_score": model_score,
        }
    )
    path = _write(df, tmp_path)
    req = AuditRequest(
        audit_id="aud-rem-hc",
        goal="Remediate region disparity on a 25-group region attribute.",
        regime="DPDP",
        model=ModelCard(model_id="syn-v1", task="binary_classification"),
        dataset=DatasetDescriptor(
            name="synthetic-25region",
            row_count=n,
            columns=list(df.columns),
            candidate_protected_columns=["region"],
            source_uri=str(path),
            outcome_column="approved",
            model_score_column="model_score",
            decision_threshold=0.5,
        ),
        requested_attributes=["region"],
    )
    plan = AuditPlan(
        audit_id=req.audit_id,
        steps=[
            AuditStep(
                step_id="s1",
                kind="metric",
                description="DP on region.",
                target_attributes=["region"],
            )
        ],
        slices=[["region"]],
        rationale="Audit high-cardinality region attribute.",
        estimated_minutes=3,
    )
    result = AuditResult(
        audit_id=req.audit_id,
        plan=plan,
        metrics=[
            SliceMetric(
                slice_key="attribute=region",
                metric="demographic_parity_ratio",
                value=0.40,
                sample_size=n,
            )
        ],
        overall_disparate_impact=0.40,
    )
    outcome = run_remediation(req, result, random_state=11)
    assert outcome.improved is False, (
        f"expected improved=False on 25-group target, got {outcome.improved}"
    )
    # Original model retained -> after mirrors before, no accuracy change claimed.
    assert outcome.after_dp_ratio == pytest.approx(outcome.before_dp_ratio)
    assert outcome.accuracy_delta_pp == pytest.approx(0.0)
    assert outcome.reason  # non-empty truthful reason
    assert outcome.target_group_count is not None and outcome.target_group_count >= 20


def test_remediation_falls_back_when_no_dp_metric(tmp_path: Path) -> None:
    df = _synthetic_frame(n=500, seed=3)
    path = _write(df, tmp_path)
    req = _request_for(path)
    plan = _plan(req.audit_id)
    # Result with no demographic_parity_ratio rows — tool must fall back to
    # the first candidate column.
    result = AuditResult(
        audit_id=req.audit_id,
        plan=plan,
        metrics=[
            SliceMetric(
                slice_key="attribute=gender",
                metric="selection_rate",
                value=0.3,
                sample_size=500,
            )
        ],
        overall_disparate_impact=None,
    )
    outcome = run_remediation(req, result, random_state=3)
    assert outcome.target_column == "gender"
    # No before-DP signal was available; tool stamps 0.0 as the before value.
    # After-DP from the re-audit must still be a real number.
    assert 0.0 <= outcome.after_dp_ratio <= 1.0
