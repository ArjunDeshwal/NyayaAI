"""Per-agent unit tests with the stub Gemini backend."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from nyayai_orchestrator.agents import run_narrator, run_planner, run_watcher
from nyayai_orchestrator.guardrails import NoOpArmor, NoOpSDP
from nyayai_orchestrator.llm.stub import StubGeminiClient
from nyayai_orchestrator.schemas import (
    AuditPlan,
    AuditRequest,
    AuditResult,
    AuditStep,
    DatasetDescriptor,
    ModelCard,
    SliceMetric,
)


def _sample_request() -> AuditRequest:
    return AuditRequest(
        audit_id="aud-test-001",
        goal="Audit MUDRA loan model for caste and gender bias.",
        regime="DPDP",
        model=ModelCard(
            model_id="mudra-v3",
            task="binary_classification",
            description="Loan approval classifier.",
        ),
        dataset=DatasetDescriptor(
            name="mudra-lite",
            row_count=1000,
            columns=["age", "gender", "caste", "state", "approved"],
            candidate_protected_columns=["gender", "caste"],
        ),
        requested_attributes=["caste", "gender"],
    )


def _sample_result(plan: AuditPlan | None = None) -> AuditResult:
    if plan is None:
        plan = AuditPlan(
            audit_id="aud-test-001",
            steps=[
                AuditStep(
                    step_id="s1",
                    kind="metric",
                    description="DP difference",
                    target_attributes=["caste", "gender"],
                )
            ],
            slices=[["caste"], ["gender"], ["caste", "gender"]],
            rationale="Cover single and intersectional slices.",
            estimated_minutes=5,
        )
    return AuditResult(
        audit_id="aud-test-001",
        plan=plan,
        metrics=[
            SliceMetric(
                slice_key="caste=SC",
                metric="demographic_parity_difference",
                value=0.18,
                sample_size=4000,
            ),
            SliceMetric(
                slice_key="gender=F",
                metric="demographic_parity_difference",
                value=0.09,
                sample_size=22000,
            ),
            SliceMetric(
                slice_key="caste=SC,gender=F",
                metric="disparate_impact",
                value=0.62,
                sample_size=1180,
            ),
        ],
        overall_disparate_impact=0.68,
        timestamp=datetime(2026, 4, 21, 10, 0, tzinfo=timezone.utc),
    )


@pytest.fixture
def client() -> StubGeminiClient:
    return StubGeminiClient()


def test_planner_emits_valid_plan(client: StubGeminiClient) -> None:
    req = _sample_request()
    plan = run_planner(
        req,
        client=client,
        model="gemini-3.1-pro",
        armor=NoOpArmor(),
        sdp=NoOpSDP(),
    )
    assert plan.audit_id == req.audit_id
    assert len(plan.steps) >= 2
    assert any(len(s) >= 2 for s in plan.slices), "intersectional slice required"
    assert plan.estimated_minutes <= 10


def test_narrator_emits_valid_narrative(client: StubGeminiClient) -> None:
    result = _sample_result()
    narrative = run_narrator(
        result,
        client=client,
        model="gemini-3-flash",
        armor=NoOpArmor(),
        sdp=NoOpSDP(),
    )
    assert narrative.audit_id == result.audit_id
    assert len(narrative.per_slice) >= 3
    assert "Fairness Metrics service" in narrative.disclaimer
    assert narrative.recommendations  # non-empty


def test_watcher_flags_major_when_disparate_impact_low(client: StubGeminiClient) -> None:
    result = _sample_result()  # overall_disparate_impact = 0.68
    flag = run_watcher(
        result,
        client=client,
        model="gemini-3.1-flash-lite",
        armor=NoOpArmor(),
        sdp=NoOpSDP(),
    )
    assert flag.audit_id == result.audit_id
    assert flag.level == "major"
    assert "disparate_impact" in flag.triggering_metrics


def test_watcher_flags_none_when_disparate_impact_ok(client: StubGeminiClient) -> None:
    result = _sample_result()
    result = result.model_copy(update={"overall_disparate_impact": 0.95})
    flag = run_watcher(
        result,
        client=client,
        model="gemini-3.1-flash-lite",
        armor=NoOpArmor(),
        sdp=NoOpSDP(),
    )
    assert flag.level == "none"
