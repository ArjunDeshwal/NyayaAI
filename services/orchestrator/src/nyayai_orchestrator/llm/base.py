"""Abstract Gemini client interface.

Agents MUST go through this interface — never import ``google.genai`` or
``vertexai`` directly in agent code. That keeps tests hermetic and lets us
swap backends via env.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Literal


Role = Literal["system", "user", "assistant"]


@dataclass(frozen=True)
class ChatMessage:
    role: Role
    content: str


@dataclass(frozen=True)
class GeminiResponse:
    """Wraps a single structured response from Gemini.

    ``parsed`` is the decoded JSON (dict / list / scalar) when the caller
    supplied a ``response_schema``; otherwise the raw text lives in ``text``.
    """

    text: str
    parsed: Any = None
    model: str = ""
    usage: dict[str, int] = field(default_factory=dict)


class GeminiClient(ABC):
    """Abstract LLM client. Implementations MUST be safe to construct
    without network / credentials at package-import time."""

    @abstractmethod
    def generate_structured(
        self,
        *,
        model: str,
        messages: list[ChatMessage],
        response_schema: dict[str, Any],
        temperature: float = 0.2,
        max_output_tokens: int = 2048,
    ) -> GeminiResponse:
        """Run a single structured-output call.

        ``response_schema`` is a JSON-schema-ish dict. Agents always use the
        structured path; free-text generation is deliberately not exposed on
        this interface so we cannot forget to validate.
        """
