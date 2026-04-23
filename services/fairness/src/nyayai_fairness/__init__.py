"""NyayaAI fairness service (Agent 3).

This module is **deliberately classical**: no Gemini, no LLM calls. It wraps
Fairlearn + :mod:`nyayai_fairlearn_ext` and produces a deterministic,
reproducible :class:`schemas.AuditResult`.

Why no LLM here: the GSC rubric explicitly asks "could a simpler approach
have worked?" --- fairness math is deterministic. LLM-narrated explanations
belong to the Root-Cause agent in ``services/orchestrator/``.
"""

from nyayai_fairness.audit import run_audit
from nyayai_fairness.schemas import (
    AuditRequest,
    AuditResult,
    CustomIndiaMetrics,
    SliceReport,
)

__all__ = [
    "AuditRequest",
    "AuditResult",
    "CustomIndiaMetrics",
    "SliceReport",
    "run_audit",
]
