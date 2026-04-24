"""Typed tool contracts for agent ⇄ service calls.

Each tool has a Pydantic input, Pydantic output, and a single-paragraph
docstring that the LLM sees verbatim as the tool description.
"""

from .fairness_tool import FairnessUnavailable, run_fairness_audit
from .remediation_tool import (
    RemediationOutcome,
    RemediationUnavailable,
    run_remediation,
)
from .report_tool import ReportRenderInput, ReportRenderOutput, render_report

__all__ = [
    "FairnessUnavailable",
    "RemediationOutcome",
    "RemediationUnavailable",
    "ReportRenderInput",
    "ReportRenderOutput",
    "render_report",
    "run_fairness_audit",
    "run_remediation",
]
