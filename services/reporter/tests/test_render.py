"""Tests for the reporter.

Runs fully in-process; no network calls, no Gemini.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone

import pytest
from nyayai_orchestrator.schemas import (
    AuditPlan,
    AuditReport,
    AuditRequest,
    AuditResult,
    AuditStep,
    DatasetDescriptor,
    DriftFlag,
    ModelCard,
    Recommendation,
    ReportNarrative,
    SliceMetric,
    SliceParagraph,
)

from nyayai_reporter import render_html, render_json, write_all


@pytest.fixture
def sample_report() -> AuditReport:
    request = AuditRequest(
        audit_id="audit_001",
        goal="Audit MUDRA-Lite loan-approval model for caste + gender disparity.",
        regime="DPDP",
        model=ModelCard(
            model_id="mudra_lite_v1",
            task="binary_classification",
            description="Prototype loan scorer",
        ),
        dataset=DatasetDescriptor(
            name="mudra-lite",
            row_count=10000,
            columns=["applicant_id", "age", "gender", "caste_disclosed", "approved"],
            candidate_protected_columns=["gender", "caste_disclosed"],
        ),
        requested_attributes=["caste", "gender"],
    )
    plan = AuditPlan(
        audit_id="audit_001",
        steps=[
            AuditStep(
                step_id="s1",
                kind="metric",
                description="Demographic parity on caste",
                target_attributes=["caste"],
            )
        ],
        slices=[["caste", "gender"]],
        rationale="Caste and gender are the primary DPDP-protected axes for PDS-adjacent credit models.",
        estimated_minutes=4,
    )
    result = AuditResult(
        audit_id="audit_001",
        plan=plan,
        metrics=[
            SliceMetric(
                slice_key="caste=SC",
                metric="demographic_parity_ratio",
                value=0.61,
                sample_size=1850,
            ),
            SliceMetric(
                slice_key="caste=ST",
                metric="demographic_parity_ratio",
                value=0.58,
                sample_size=820,
            ),
            SliceMetric(
                slice_key="gender=FEMALE",
                metric="demographic_parity_ratio",
                value=0.70,
                sample_size=4700,
            ),
            SliceMetric(
                slice_key="overall",
                metric="equalized_odds_difference",
                value=0.21,
                sample_size=10000,
            ),
        ],
        overall_disparate_impact=0.61,
        timestamp=datetime(2026, 4, 21, 12, 0, tzinfo=timezone.utc),
    )
    narrative = ReportNarrative(
        audit_id="audit_001",
        summary=(
            "The model fails the 4/5ths rule on caste (DI 0.61) and narrowly passes "
            "on gender (0.70). Recommend Fairlearn ExponentiatedGradient reductions "
            "before redeployment."
        ),
        per_slice=[
            SliceParagraph(
                slice_key="caste=SC",
                paragraph="SC applicants are approved at 61% the rate of General applicants at the same income.",
            ),
            SliceParagraph(
                slice_key="gender=FEMALE",
                paragraph="Women are approved at 70% the rate of men; interacts with caste for SC women.",
            ),
        ],
        recommendations=[
            Recommendation(
                title="Apply reductions-based mitigation",
                detail="Use Fairlearn ExponentiatedGradient with DemographicParity constraint; expected DI ~0.94 at cost of 0.4pp accuracy.",
                severity="action_required",
            ),
            Recommendation(
                title="Review surname features",
                detail="SPLS = 0.78 indicates surname is leaking caste; drop or hash.",
                severity="advisory",
            ),
        ],
    )
    drift = DriftFlag(
        audit_id="audit_001",
        level="major",
        reason="Disparate impact < 0.80 on caste slice",
        triggering_metrics=["caste=SC:demographic_parity_ratio"],
        confidence=0.95,
    )
    return AuditReport(
        request=request,
        plan=plan,
        result=result,
        narrative=narrative,
        drift=drift,
    )


def test_render_json_parses(sample_report: AuditReport) -> None:
    out = render_json(sample_report)
    parsed = json.loads(out)
    assert parsed["request"]["audit_id"] == "audit_001"
    assert parsed["result"]["overall_disparate_impact"] == 0.61


def test_render_html_contains_expected_sections(sample_report: AuditReport) -> None:
    html = render_html(sample_report)
    assert "NyayaAI" in html
    assert "audit_001" in html
    assert "0.610" in html  # DI formatted
    assert "FAILS 4/5ths rule" in html
    assert "DPDP" in html
    assert "Rule 13" in html
    assert "caste=SC" in html
    assert "ExponentiatedGradient" in html
    # disclaimer present
    assert "Gemini 3 Flash" in html
    # no deprecated names snuck in
    for deprecated in ["PaLM", "Bard", "Cloud DLP", "firebase_vertexai", "Agentspace", "Imagen 3"]:
        assert deprecated not in html


def test_html_escapes_user_input(sample_report: AuditReport) -> None:
    sample_report.narrative.summary = "<script>alert(1)</script>harm"
    html = render_html(sample_report)
    assert "<script>alert(1)</script>" not in html
    assert "&lt;script&gt;" in html


def test_write_all_produces_json_and_html(sample_report: AuditReport, tmp_path) -> None:
    paths = write_all(sample_report, tmp_path)
    assert paths["json"].exists()
    assert paths["html"].exists()
    # PDF is optional (weasyprint may not be installed in the test env)
