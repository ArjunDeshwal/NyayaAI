"""LLM agents for the NyayaAI orchestrator prototype.

Agents shipped:

    * :mod:`.planner`     — Gemini 3.1 Pro,  ambiguous goal → structured plan.
    * :mod:`.narrator`    — Gemini 3 Flash,  metrics → plain-language summary.
    * :mod:`.watcher`     — Gemini 3 Flash,  metrics snapshot → drift flag.
    * :mod:`.remediation` — Gemini 3 Flash,  classical-remediation numbers →
      plain-language mitigation plan with code-patch summary. Conditional on
      the main fairness audit tripping the 4/5ths threshold.

Counterfactual and Root-Cause (agents 2 and 4 in the plan) remain out of
scope for this package.
"""

from .narrator import run_narrator
from .planner import run_planner
from .remediation import run_remediation_agent
from .watcher import run_watcher

__all__ = [
    "run_narrator",
    "run_planner",
    "run_remediation_agent",
    "run_watcher",
]
