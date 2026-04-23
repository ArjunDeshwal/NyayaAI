"""Typed tool contracts for agent ⇄ service calls.

Each tool has a Pydantic input, Pydantic output, and a single-paragraph
docstring that the LLM sees verbatim as the tool description.
"""

from .fairness_tool import FairnessUnavailable, run_fairness_audit
from .report_tool import ReportRenderInput, ReportRenderOutput, render_report

__all__ = [
    "FairnessUnavailable",
    "ReportRenderInput",
    "ReportRenderOutput",
    "render_report",
    "run_fairness_audit",
]
