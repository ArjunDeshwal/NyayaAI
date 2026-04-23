"""LLM agents for the NyayaAI orchestrator prototype.

Only three agents are shipped in the prototype:

    * :mod:`.planner`  — Gemini 3.1 Pro, ambiguous-goal → structured plan.
    * :mod:`.narrator` — Gemini 3 Flash, metrics → plain-language summary.
    * :mod:`.watcher`  — Gemini 3.1 Flash-Lite, metrics snapshot → drift flag.

Counterfactual, Root-Cause, and Remediation (agents 2, 4, 5 in the plan)
are finals scope and intentionally out of this package.
"""

from .narrator import run_narrator
from .planner import run_planner
from .watcher import run_watcher

__all__ = ["run_narrator", "run_planner", "run_watcher"]
