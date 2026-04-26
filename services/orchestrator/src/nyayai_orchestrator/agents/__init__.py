"""LLM agents for the NyayaAI orchestrator.

Agents shipped:

    * :mod:`.planner`        — Gemini 3.1 Pro,  ambiguous goal → structured plan.
    * :mod:`.counterfactual` — Gemini 3 Flash,  flip math → individual-fairness narrative.
    * :mod:`.root_cause`     — Gemini 3 Flash,  feature attribution → proxy-feature narrative.
    * :mod:`.narrator`       — Gemini 3 Flash,  metrics + above → plain-language summary.
    * :mod:`.watcher`        — Gemini 3 Flash,  metrics snapshot → drift flag.
    * :mod:`.remediation`    — Gemini 3 Flash,  classical-remediation numbers →
      plain-language mitigation plan with code-patch summary. Conditional on
      the main fairness audit tripping the 4/5ths threshold.

Counterfactual + Root-Cause are conditional on ``train_baseline=True`` —
they need a real ``predict_proba`` and a permutation-importance pass that
the upload path doesn't supply.
"""

from .counterfactual import run_counterfactual_agent
from .narrator import run_narrator
from .planner import run_planner
from .remediation import run_remediation_agent
from .root_cause import run_root_cause_agent
from .watcher import run_watcher

__all__ = [
    "run_counterfactual_agent",
    "run_narrator",
    "run_planner",
    "run_remediation_agent",
    "run_root_cause_agent",
    "run_watcher",
]
