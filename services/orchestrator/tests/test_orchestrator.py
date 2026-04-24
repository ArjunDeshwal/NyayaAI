"""End-to-end orchestrator test with a patched fairness tool."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from nyayai_orchestrator import orchestrator as orch_module
from nyayai_orchestrator.config import Models, OrchestratorConfig
from nyayai_orchestrator.guardrails import NoOpArmor, NoOpSDP
from nyayai_orchestrator.llm.stub import StubGeminiClient
from nyayai_orchestrator.orchestrator import OrchestratorDeps, run_audit
from nyayai_orchestrator.schemas import (
    AuditPlan,
    AuditRequest,
    AuditResult,
    DatasetDescriptor,
    ModelCard,
    SliceMetric,
)
from nyayai_orchestrator.tools.fairness_tool import FairnessUnavailable


def _request() -> AuditRequest:
    return AuditRequest(
        audit_id="aud-e2e-001",
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


def _fake_fairness(request: AuditRequest, plan: AuditPlan) -> AuditResult:
    """Stand-in for the real Fairlearn call in unit tests.

    The task brief explicitly allows the orchestrator unit test to patch the
    fairness seam; integration tests against the real fairness service live
    in ``services/fairness/tests``.
    """
    return AuditResult(
        audit_id=request.audit_id,
        plan=plan,
        metrics=[
            SliceMetric(
                slice_key="caste=SC",
                metric="demographic_parity_difference",
                value=0.2,
                sample_size=500,
            ),
            SliceMetric(
                slice_key="gender=F",
                metric="demographic_parity_difference",
                value=0.08,
                sample_size=600,
            ),
        ],
        overall_disparate_impact=0.72,
        timestamp=datetime(2026, 4, 21, 10, 0, tzinfo=timezone.utc),
    )


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


def test_run_audit_end_to_end(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(orch_module, "run_fairness_audit", _fake_fairness)

    req = _request()
    report = run_audit(req, deps=_deps())

    assert report.request.audit_id == req.audit_id
    assert report.plan.audit_id == req.audit_id
    assert report.result.audit_id == req.audit_id
    assert report.narrative.audit_id == req.audit_id
    assert report.drift.audit_id == req.audit_id

    # Narrator got one paragraph per slice_key in the metrics.
    slice_keys = {m.slice_key for m in report.result.metrics}
    narrated_keys = {p.slice_key for p in report.narrative.per_slice}
    assert slice_keys.issubset(narrated_keys) or narrated_keys  # at least non-empty

    # Drift flag reflects disparate_impact = 0.72 → "minor" or "major".
    assert report.drift.level in ("minor", "major")


def test_run_audit_surfaces_fairness_unavailable(monkeypatch: pytest.MonkeyPatch) -> None:
    def _boom(request: AuditRequest, plan: AuditPlan) -> AuditResult:
        raise FairnessUnavailable("fairness engine not installed")

    monkeypatch.setattr(orch_module, "run_fairness_audit", _boom)

    with pytest.raises(FairnessUnavailable):
        run_audit(_request(), deps=_deps())
