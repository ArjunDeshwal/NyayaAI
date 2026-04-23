"""Sensitive Data Protection pseudonymiser interface.

Any payload that reaches an LLM must first pass through SDP with the
India-context templates (Aadhaar, PAN, phone, email, IFSC, GSTIN, …). The
redacted string is what Gemini sees; the original values stay inside the
VPC-SC fairness service.

In the prototype we ship :class:`NoOpSDP` so the wiring exists; swap in a
real ``VertexSDP`` backed by ``google-cloud-dlp`` (renamed to Sensitive
Data Protection — never use the old name "Cloud DLP" in user-facing text)
for staging and prod.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from ..llm.base import ChatMessage


class SDPHook(ABC):
    """Abstract SDP redactor."""

    @abstractmethod
    def redact(self, messages: list[ChatMessage]) -> list[ChatMessage]:
        """Return messages with PII pseudonymised."""


class NoOpSDP(SDPHook):
    """Pass-through. Prototype-only. Replace with the real SDP template
    resource before any real user data goes through the pipeline."""

    def redact(self, messages: list[ChatMessage]) -> list[ChatMessage]:
        return messages
