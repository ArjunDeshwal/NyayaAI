"""NyayaAI agent orchestrator (prototype).

Prototype scope — only three agents wired end-to-end:
    * Planner   (Gemini 3.1 Pro)    — maps audit goal to a structured plan.
    * Narrator  (Gemini 3 Flash)    — synthesises the plain-English report.
    * Watcher   (Gemini 3.1 Flash-Lite) — stub drift-flag classifier.

Counterfactual, Root-Cause and Remediation agents are finals scope and are
intentionally not implemented here.

The Fairness Metrics agent is classical (Fairlearn) and lives in
``services/fairness``; this package consumes it as a tool, never as an LLM.
"""

from .orchestrator import run_audit
from .schemas import (
    AuditPlan,
    AuditReport,
    AuditRequest,
    AuditResult,
    DriftFlag,
    RemediationPlan,
    ReportNarrative,
)

__all__ = [
    "AuditPlan",
    "AuditReport",
    "AuditRequest",
    "AuditResult",
    "DriftFlag",
    "RemediationPlan",
    "ReportNarrative",
    "run_audit",
]
