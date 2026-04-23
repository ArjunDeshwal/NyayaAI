"""Real Gemini client over Vertex AI / ``google-genai``.

Import safety
-------------
The ``google.genai`` SDK is imported **lazily** inside ``_lazy_client`` so
that ``import nyayai_orchestrator`` never fails in an environment without
the SDK or without credentials — the stub backend must remain usable on a
laptop with zero GCP setup.

Wiring to real Vertex
---------------------
In staging / prod, set::

    NYAYAI_LLM_BACKEND=vertex
    NYAYAI_GCP_PROJECT=<project-id>
    NYAYAI_GCP_LOCATION=asia-south1
    NYAYAI_MODEL_ARMOR_TEMPLATE=projects/<p>/locations/asia-south1/templates/<t>

The Model Armor hook (:mod:`nyayai_orchestrator.guardrails.model_armor`) is
invoked *around* :meth:`generate_structured`; this client never has to know
about prompt-injection filtering itself. The route is:

    agent  →  ModelArmor.pre_call  →  VertexGeminiClient.generate_structured
           →  ModelArmor.post_call →  Pydantic validate  →  agent
"""

from __future__ import annotations

import json
from typing import Any

from .base import ChatMessage, GeminiClient, GeminiResponse


class VertexGeminiClient(GeminiClient):
    """Vertex AI / google-genai backed client.

    Constructing this class does not open a network connection; the SDK is
    only imported inside :meth:`_lazy_client`. This means tests that accidentally
    resolve to the vertex backend still fail with a clear message instead of a
    cryptic credentials error at collect time.
    """

    def __init__(self, *, project: str | None, location: str) -> None:
        if not project:
            raise RuntimeError(
                "VertexGeminiClient requires NYAYAI_GCP_PROJECT to be set. "
                "For local dev, use NYAYAI_LLM_BACKEND=stub."
            )
        self._project = project
        self._location = location
        self._client: Any | None = None

    def _lazy_client(self) -> Any:
        if self._client is not None:
            return self._client
        try:
            from google import genai  # type: ignore[import-not-found]
        except ImportError as e:  # pragma: no cover - exercised only in real env
            raise RuntimeError(
                "google-genai is not installed. Install the 'vertex' extra: "
                "pip install 'nyayai-orchestrator[vertex]'."
            ) from e
        self._client = genai.Client(
            vertexai=True, project=self._project, location=self._location
        )
        return self._client

    def generate_structured(
        self,
        *,
        model: str,
        messages: list[ChatMessage],
        response_schema: dict[str, Any],
        temperature: float = 0.2,
        max_output_tokens: int = 2048,
    ) -> GeminiResponse:  # pragma: no cover - requires live Vertex
        client = self._lazy_client()

        # google-genai accepts system instructions and chat contents separately.
        system_parts = [m.content for m in messages if m.role == "system"]
        contents = [
            {"role": "user" if m.role == "user" else "model", "parts": [{"text": m.content}]}
            for m in messages
            if m.role != "system"
        ]

        response = client.models.generate_content(
            model=model,
            contents=contents,
            config={
                "system_instruction": "\n\n".join(system_parts) or None,
                "response_mime_type": "application/json",
                "response_schema": response_schema,
                "temperature": temperature,
                "max_output_tokens": max_output_tokens,
            },
        )

        text = getattr(response, "text", "") or ""
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError as e:
            raise RuntimeError(
                f"Vertex returned non-JSON under response_schema: {text[:200]!r}"
            ) from e

        usage_obj = getattr(response, "usage_metadata", None)
        usage = {
            "prompt_tokens": getattr(usage_obj, "prompt_token_count", 0) or 0,
            "candidates_tokens": getattr(usage_obj, "candidates_token_count", 0) or 0,
        }
        return GeminiResponse(text=text, parsed=parsed, model=model, usage=usage)
