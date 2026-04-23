"""Bridge from the orchestrator to ``services/reporter``.

Prototype ships an in-process stub that assembles an :class:`AuditReport`
(no PDF rendering). The real reporter (DPDP Rule 13 DPIA sections, EU AI
Act Art. 9/10/15 annex, bilingual output) is wired in by the
compliance-auditor subagent.
"""

from __future__ import annotations

from pydantic import BaseModel

from ..schemas import (
    AuditPlan,
    AuditReport,
    AuditRequest,
    AuditResult,
    DriftFlag,
    ReportNarrative,
)


class ReportRenderInput(BaseModel):
    request: AuditRequest
    plan: AuditPlan
    result: AuditResult
    narrative: ReportNarrative
    drift: DriftFlag


class ReportRenderOutput(BaseModel):
    report: AuditReport
    artifact_uri: str | None = None  # populated once services/reporter exists


def render_report(payload: ReportRenderInput) -> ReportRenderOutput:
    """Assemble the final :class:`AuditReport`.

    This prototype stitches the structured pieces together. The production
    reporter will also render PDF / HTML / MP3 via Chirp and write them to
    Cloud Storage (CMEK-encrypted, asia-south1).
    """
    report = AuditReport(
        request=payload.request,
        plan=payload.plan,
        result=payload.result,
        narrative=payload.narrative,
        drift=payload.drift,
    )
    return ReportRenderOutput(report=report, artifact_uri=None)
