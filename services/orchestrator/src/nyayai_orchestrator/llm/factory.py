"""Factory for :class:`GeminiClient` — reads config, returns stub or vertex."""

from __future__ import annotations

from ..config import OrchestratorConfig, load_config
from .base import GeminiClient
from .stub import StubGeminiClient


def build_client(config: OrchestratorConfig | None = None) -> GeminiClient:
    """Return the configured Gemini client.

    Selection rules:
        * ``NYAYAI_LLM_BACKEND=stub`` (default) → :class:`StubGeminiClient`.
        * ``NYAYAI_LLM_BACKEND=vertex``         → :class:`VertexGeminiClient`
          (imported lazily; the package import above this one never pulls in
          ``google-genai``).
    """
    cfg = config or load_config()
    if cfg.backend == "stub":
        return StubGeminiClient()
    # Lazy import to keep package import safe without the vertex extra.
    from .vertex import VertexGeminiClient

    return VertexGeminiClient(project=cfg.project, location=cfg.location)
