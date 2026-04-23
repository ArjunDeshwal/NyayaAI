"""LLM client abstraction for NyayaAI.

Two implementations:
    * :class:`~nyayai_orchestrator.llm.stub.StubGeminiClient` — deterministic
      canned responses keyed by prompt hash. Used by every test and by local
      dev when no Vertex creds are present.
    * :class:`~nyayai_orchestrator.llm.vertex.VertexGeminiClient` — real
      ``google-genai`` / Vertex AI client. Imported *lazily*; package import
      never crashes if creds are missing.

The selection is driven by ``NYAYAI_LLM_BACKEND`` (``stub`` | ``vertex``).
"""

from .base import ChatMessage, GeminiClient, GeminiResponse
from .factory import build_client

__all__ = ["ChatMessage", "GeminiClient", "GeminiResponse", "build_client"]
