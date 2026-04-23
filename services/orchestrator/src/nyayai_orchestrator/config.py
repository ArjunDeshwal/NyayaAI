"""Environment-driven configuration for the NyayaAI orchestrator.

All model IDs live here, never inline in agent code (see
``.claude/skills/nyayai-adk-agent-patterns/SKILL.md``). Swap backends with
``NYAYAI_LLM_BACKEND=stub|vertex``.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Literal

LLMBackend = Literal["stub", "vertex"]


# Canonical 2026 model IDs. Never use deprecated names (PaLM, Bard, Gemini 1.x,
# `gemini-3-pro-preview`) — an outdated ID is a GSC blocker.
DEFAULT_PLANNER_MODEL = "gemini-3.1-pro"
DEFAULT_NARRATOR_MODEL = "gemini-3-flash"
DEFAULT_WATCHER_MODEL = "gemini-3.1-flash-lite"


@dataclass(frozen=True)
class Models:
    planner: str
    narrator: str
    watcher: str


@dataclass(frozen=True)
class OrchestratorConfig:
    backend: LLMBackend
    models: Models
    # Reference to a Model Armor template in the project. In dev we pass-through
    # via NoOpArmor; in staging/prod the real template id must be set.
    model_armor_template: str | None
    # SDP template id (same story).
    sdp_template: str | None
    project: str | None
    location: str


def _env(name: str, default: str | None = None) -> str | None:
    v = os.environ.get(name)
    return v if v not in (None, "") else default


def load_config() -> OrchestratorConfig:
    backend_raw = (_env("NYAYAI_LLM_BACKEND", "stub") or "stub").lower()
    if backend_raw not in ("stub", "vertex"):
        raise ValueError(
            f"NYAYAI_LLM_BACKEND must be 'stub' or 'vertex', got {backend_raw!r}"
        )
    backend: LLMBackend = backend_raw  # type: ignore[assignment]

    return OrchestratorConfig(
        backend=backend,
        models=Models(
            planner=_env("NYAYAI_MODEL_PLANNER", DEFAULT_PLANNER_MODEL) or DEFAULT_PLANNER_MODEL,
            narrator=_env("NYAYAI_MODEL_NARRATOR", DEFAULT_NARRATOR_MODEL)
            or DEFAULT_NARRATOR_MODEL,
            watcher=_env("NYAYAI_MODEL_WATCHER", DEFAULT_WATCHER_MODEL) or DEFAULT_WATCHER_MODEL,
        ),
        model_armor_template=_env("NYAYAI_MODEL_ARMOR_TEMPLATE"),
        sdp_template=_env("NYAYAI_SDP_TEMPLATE"),
        project=_env("NYAYAI_GCP_PROJECT"),
        location=_env("NYAYAI_GCP_LOCATION", "asia-south1") or "asia-south1",
    )
