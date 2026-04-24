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
    Remediation (conditional: classical tool + LLM narrative)
      ↓
    Report tool (assembles AuditReport)

Sub-agents never call each other directly — everything routes through this
function, matching the ADK hierarchical pattern documented in
``.claude/skills/nyayai-adk-agent-patterns/SKILL.md``.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from .agents import run_narrator, run_planner, run_remediation_agent, run_watcher
from .config import OrchestratorConfig, load_config
from .guardrails import ModelArmorHook, NoOpArmor, NoOpSDP, SDPHook
from .llm.base import GeminiClient
from .llm.factory import build_client
from .schemas import AuditReport, AuditRequest, RemediationPlan
from .tools.fairness_tool import run_fairness_audit
from .tools.remediation_tool import RemediationUnavailable, run_remediation
from .tools.report_tool import ReportRenderInput, render_report

_log = logging.getLogger(__name__)

# 4/5ths rule (EEOC; mirrored by the RBI advisory). Remediation fires below this.
FOURFIFTHS_THRESHOLD = 0.8


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

    # Conditional Remediation pass. Only fire when the audit fails the
    # 4/5ths rule; a passing audit doesn't need a mitigation narrative
    # (and we'd just confuse judges and reviewers with a no-op section).
    remediation_plan: RemediationPlan | None = None
    overall_di = result.overall_disparate_impact
    if overall_di is not None and overall_di < FOURFIFTHS_THRESHOLD:
        try:
            outcome = run_remediation(request, result)
            remediation_plan = run_remediation_agent(
                outcome,
                client=d.client,
                model=d.config.models.remediation,
                armor=d.armor,
                sdp=d.sdp,
            )
        except RemediationUnavailable as e:
            # Remediation is best-effort; never fail the whole audit for it.
            _log.warning("remediation skipped: %s", e)

    rendered = render_report(
        ReportRenderInput(
            request=request,
            plan=plan,
            result=result,
            narrative=narrative,
            drift=drift,
            remediation=remediation_plan,
        )
    )
    return rendered.report
