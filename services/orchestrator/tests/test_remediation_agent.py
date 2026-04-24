"""Remediation agent + orchestrator integration test.

Uses the StubGeminiClient so the test is hermetic. The classical remediation
tool is patched at the orchestrator seam; the LLM narrative path and the
number re-stamping invariant are what we actually exercise here.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from nyayai_orchestrator import orchestrator as orch_module
from nyayai_orchestrator.agents import run_remediation_agent
from nyayai_orchestrator.config import Models, OrchestratorConfig
from nyayai_orchestrator.guardrails import NoOpArmor, NoOpSDP
from nyayai_orchestrator.llm.stub import StubGeminiClient
from nyayai_orchestrator.orchestrator import OrchestratorDeps, run_audit
from nyayai_orchestrator.schemas import (
    AuditPlan,
    AuditRequest,
    AuditResult,
    AuditStep,
    DatasetDescriptor,
    ModelCard,
    SliceMetric,
)
from nyayai_orchestrator.tools.remediation_tool import RemediationOutcome


def _deps() -> OrchestratorDeps:
    cfg = OrchestratorConfig(
        backend="stub",
        models=Models(
            planner="gemini-3.1-pro",
            narrator="gemini-3-flash",
            watcher="gemini-3.1-flash-lite",
            remediation="gemini-3-flash",
        ),
        model_armor_template=None,
        sdp_template=None,
        project=None,
        location="asia-south1",
    )
    return OrchestratorDeps(
        config=cfg,
        client=StubGeminiClient(),
        armor=NoOpArmor(),
        sdp=NoOpSDP(),
    )


def _request() -> AuditRequest:
    return AuditRequest(
        audit_id="aud-rem-agent-001",
        goal="Audit MUDRA loan model for caste + gender disparity.",
        regime="DPDP",
        model=ModelCard(
            model_id="mudra-v3",
            task="binary_classification",
            description="Loan classifier.",
        ),
        dataset=DatasetDescriptor(
            name="mudra-lite",
            row_count=1000,
            columns=["age", "gender", "caste", "approved"],
            candidate_protected_columns=["gender", "caste"],
        ),
        requested_attributes=["caste", "gender"],
    )


def _result_failing(request: AuditRequest) -> AuditResult:
    plan = AuditPlan(
        audit_id=request.audit_id,
        steps=[
            AuditStep(
                step_id="s1",
                kind="metric",
                description="DP",
                target_attributes=["caste", "gender"],
            )
        ],
        slices=[["caste"], ["gender"]],
        rationale="single-attribute audit.",
        estimated_minutes=3,
    )
    return AuditResult(
        audit_id=request.audit_id,
        plan=plan,
        metrics=[
            SliceMetric(
                slice_key="attribute=caste",
                metric="demographic_parity_ratio",
                value=0.42,
                sample_size=1000,
            )
        ],
        overall_disparate_impact=0.42,
        timestamp=datetime(2026, 4, 21, 10, 0, tzinfo=timezone.utc),
    )


def _result_passing(request: AuditRequest) -> AuditResult:
    plan = AuditPlan(
        audit_id=request.audit_id,
        steps=[
            AuditStep(
                step_id="s1",
                kind="metric",
                description="DP",
                target_attributes=["caste"],
            )
        ],
        slices=[["caste"]],
        rationale="single-attribute audit.",
        estimated_minutes=2,
    )
    return AuditResult(
        audit_id=request.audit_id,
        plan=plan,
        metrics=[
            SliceMetric(
                slice_key="attribute=caste",
                metric="demographic_parity_ratio",
                value=0.95,
                sample_size=1000,
            )
        ],
        overall_disparate_impact=0.95,
        timestamp=datetime(2026, 4, 21, 10, 0, tzinfo=timezone.utc),
    )


def _outcome(audit_id: str) -> RemediationOutcome:
    return RemediationOutcome(
        audit_id=audit_id,
        mitigation_name="fairlearn.reductions.ExponentiatedGradient+DemographicParity",
        target_attribute="caste",
        target_column="caste_disclosed",
        before_dp_ratio=0.424,
        after_dp_ratio=0.94,
        baseline_accuracy=0.81,
        remediated_accuracy=0.79,
        accuracy_delta_pp=-2.0,
        epsilon=0.05,
        n_train=7000,
        n_test=3000,
        post_metrics=[],
    )


def test_remediation_agent_restamps_numbers_from_outcome() -> None:
    outcome = _outcome("aud-rem-agent-001")
    plan = run_remediation_agent(
        outcome,
        client=StubGeminiClient(),
        model="gemini-3-flash",
        armor=NoOpArmor(),
        sdp=NoOpSDP(),
    )
    assert plan.audit_id == "aud-rem-agent-001"
    assert plan.mitigation_name == outcome.mitigation_name
    # Authoritative numbers must match the classical tool exactly.
    assert plan.before_dp_ratio == pytest.approx(outcome.before_dp_ratio)
    assert plan.after_dp_ratio == pytest.approx(outcome.after_dp_ratio)
    assert plan.accuracy_delta_pp == pytest.approx(outcome.accuracy_delta_pp)
    assert plan.target_attribute == outcome.target_attribute
    assert len(plan.risks) >= 3
    assert "fairlearn" in plan.code_patch_summary.lower()
    assert "Fairness Metrics service" in plan.disclaimer


def test_orchestrator_runs_remediation_when_audit_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    req = _request()

    # Patch the fairness tool to return a failing audit.
    monkeypatch.setattr(
        orch_module, "run_fairness_audit", lambda request, plan: _result_failing(request)
    )
    # Patch the classical remediation tool; no Fairlearn needed in this test.
    monkeypatch.setattr(
        orch_module, "run_remediation", lambda request, result: _outcome(request.audit_id)
    )

    report = run_audit(req, deps=_deps())

    assert report.remediation is not None
    assert report.remediation.audit_id == req.audit_id
    assert report.remediation.before_dp_ratio == pytest.approx(0.424)
    assert report.remediation.after_dp_ratio == pytest.approx(0.94)
    assert report.remediation.accuracy_delta_pp == pytest.approx(-2.0)


def test_orchestrator_skips_remediation_when_audit_passes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    req = _request()

    monkeypatch.setattr(
        orch_module, "run_fairness_audit", lambda request, plan: _result_passing(request)
    )

    # The remediation tool must not be called when DI >= 0.8. We prove that
    # by making it raise if touched.
    def _boom(request: AuditRequest, result: AuditResult) -> RemediationOutcome:
        raise AssertionError("remediation should not run when 4/5ths passes")

    monkeypatch.setattr(orch_module, "run_remediation", _boom)

    report = run_audit(req, deps=_deps())
    assert report.remediation is None


def test_orchestrator_recovers_when_remediation_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    req = _request()

    monkeypatch.setattr(
        orch_module, "run_fairness_audit", lambda request, plan: _result_failing(request)
    )

    from nyayai_orchestrator.tools.remediation_tool import RemediationUnavailable

    def _unavailable(request: AuditRequest, result: AuditResult) -> RemediationOutcome:
        raise RemediationUnavailable("fairlearn not installed (simulated)")

    monkeypatch.setattr(orch_module, "run_remediation", _unavailable)

    report = run_audit(req, deps=_deps())
    # The audit itself must still succeed.
    assert report.remediation is None
    assert report.narrative.audit_id == req.audit_id
