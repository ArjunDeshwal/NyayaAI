"""Top-level orchestrator.

``run_audit(request)`` runs:

    Planner (LLM)
      ↓
    Fairness Metrics tool   ← classical Fairlearn, not an LLM
      ↓
    Narrator (LLM)
      ↓
    Watcher (LLM)
      ↓
    Report tool (assembles AuditReport)

Sub-agents never call each other directly — everything routes through this
function, matching the ADK hierarchical pattern documented in
``.claude/skills/nyayai-adk-agent-patterns/SKILL.md``.
"""

from __future__ import annotations

from dataclasses import dataclass

from .agents import run_narrator, run_planner, run_watcher
from .config import OrchestratorConfig, load_config
from .guardrails import ModelArmorHook, NoOpArmor, NoOpSDP, SDPHook
from .llm.base import GeminiClient
from .llm.factory import build_client
from .schemas import AuditReport, AuditRequest
from .tools.fairness_tool import run_fairness_audit
from .tools.report_tool import ReportRenderInput, render_report


@dataclass
class OrchestratorDeps:
    """Dependency bundle — handy for tests, which inject a stub client."""

    config: OrchestratorConfig
    client: GeminiClient
    armor: ModelArmorHook
    sdp: SDPHook


def build_default_deps(config: OrchestratorConfig | None = None) -> OrchestratorDeps:
    cfg = config or load_config()
    return OrchestratorDeps(
        config=cfg,
        client=build_client(cfg),
        armor=NoOpArmor(),
        sdp=NoOpSDP(),
    )


def run_audit(
    request: AuditRequest,
    *,
    deps: OrchestratorDeps | None = None,
) -> AuditReport:
    """Run the full three-agent prototype pipeline end to end."""
    d = deps or build_default_deps()

    plan = run_planner(
        request,
        client=d.client,
        model=d.config.models.planner,
        armor=d.armor,
        sdp=d.sdp,
    )

    # Classical fairness tool (not an LLM).
    result = run_fairness_audit(request, plan)

    narrative = run_narrator(
        result,
        client=d.client,
        model=d.config.models.narrator,
        armor=d.armor,
        sdp=d.sdp,
    )

    drift = run_watcher(
        result,
        client=d.client,
        model=d.config.models.watcher,
        armor=d.armor,
        sdp=d.sdp,
    )

    rendered = render_report(
        ReportRenderInput(
            request=request,
            plan=plan,
            result=result,
            narrative=narrative,
            drift=drift,
        )
    )
    return rendered.report
