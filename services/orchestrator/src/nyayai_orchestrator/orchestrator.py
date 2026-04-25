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
import time
from dataclasses import dataclass
from typing import Any, Callable

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

# Event emitter contract: the orchestrator calls ``emit(phase, status, **kwargs)``
# at the start and end of each agent step. The HTTP gateway uses this to stream
# progress to the Flutter UI's agent timeline. ``phase`` is one of
# {"planner","fairness","narrator","watcher","remediation","complete"}; status
# is one of {"started","done","skipped","error"}.
EventEmitter = Callable[..., None]


def _noop_emit(*_args: Any, **_kwargs: Any) -> None:
    return None

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
    emit: EventEmitter = _noop_emit,
) -> AuditReport:
    """Run the full agent pipeline end to end.

    Pass an ``emit`` callable to stream per-agent progress to the UI; defaults
    to a no-op so existing call sites stay unchanged.
    """
    d = deps or build_default_deps()

    def _phase(name: str) -> "_PhaseTimer":
        return _PhaseTimer(emit, name)

    with _phase("planner"):
        plan = run_planner(
            request,
            client=d.client,
            model=d.config.models.planner,
            armor=d.armor,
            sdp=d.sdp,
        )

    with _phase("fairness"):
        # Classical fairness tool (not an LLM).
        result = run_fairness_audit(request, plan)

    with _phase("narrator"):
        narrative = run_narrator(
            result,
            client=d.client,
            model=d.config.models.narrator,
            armor=d.armor,
            sdp=d.sdp,
        )

    with _phase("watcher"):
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
        emit("remediation", "started")
        t0 = time.time()
        try:
            outcome = run_remediation(request, result)
            remediation_plan = run_remediation_agent(
                outcome,
                client=d.client,
                model=d.config.models.remediation,
                armor=d.armor,
                sdp=d.sdp,
            )
            emit(
                "remediation",
                "done",
                elapsed_ms=int((time.time() - t0) * 1000),
                improved=outcome.improved,
                target_attribute=outcome.target_attribute,
                before_dp_ratio=outcome.before_dp_ratio,
                after_dp_ratio=outcome.after_dp_ratio,
            )
        except RemediationUnavailable as e:
            # Remediation is best-effort; never fail the whole audit for it.
            _log.warning("remediation skipped: %s", e)
            emit(
                "remediation",
                "skipped",
                elapsed_ms=int((time.time() - t0) * 1000),
                reason=str(e),
            )
    else:
        emit("remediation", "skipped", reason="audit passed 4/5ths rule (no mitigation needed)")

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


class _PhaseTimer:
    """Context manager that emits start/done events around an agent phase.

    Implementation detail: a tiny class instead of a try/finally lets us keep
    ``run_audit`` readable while still timing every step. ``done`` events
    include ``elapsed_ms`` so the UI can render real timing badges.
    """

    __slots__ = ("_emit", "_phase", "_t0")

    def __init__(self, emit: EventEmitter, phase: str) -> None:
        self._emit = emit
        self._phase = phase
        self._t0 = 0.0

    def __enter__(self) -> "_PhaseTimer":
        self._t0 = time.time()
        self._emit(self._phase, "started")
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        elapsed_ms = int((time.time() - self._t0) * 1000)
        if exc_type is None:
            self._emit(self._phase, "done", elapsed_ms=elapsed_ms)
        else:
            self._emit(
                self._phase,
                "error",
                elapsed_ms=elapsed_ms,
                error_type=exc_type.__name__,
                error_message=str(exc)[:200],
            )
