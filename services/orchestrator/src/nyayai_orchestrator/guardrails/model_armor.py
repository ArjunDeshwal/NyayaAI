"""Model Armor pre/post-call hook interface.

The hook runs on *every* LLM call (CLAUDE.md hard-rule #3). Prototype ships a
NoOp implementation — production wires the real template below.

Wiring the real Model Armor template
------------------------------------
1. Create a template in the GCP console (Security → Model Armor) with:
     * ``pi_and_jailbreak_filter`` = ENABLED (high confidence)
     * ``malicious_uri_filter`` = ENABLED
     * ``sdp.basic_config.filter_enforcement`` = ENABLED  (inbound & outbound)
2. Export its resource name:
       ``projects/<p>/locations/asia-south1/templates/<t>``
3. Set ``NYAYAI_MODEL_ARMOR_TEMPLATE`` to that value.
4. Replace :class:`NoOpArmor` in ``orchestrator.py`` with a real
   ``VertexModelArmor`` that calls
   ``modelarmor.v1.ModelArmorClient.sanitize_user_prompt`` for pre-call and
   ``sanitize_model_response`` for post-call.

Never bypass this hook — tests use the MA sandbox endpoint, staging and prod
run enforcement mode.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from ..llm.base import ChatMessage


@dataclass(frozen=True)
class ArmorVerdict:
    """Outcome of a Model Armor check."""

    allowed: bool
    reason: str = ""
    categories: tuple[str, ...] = ()


class ModelArmorHook(ABC):
    """Abstract pre/post-call guardrail."""

    @abstractmethod
    def pre_call(self, messages: list[ChatMessage]) -> list[ChatMessage]:
        """Inspect (and optionally rewrite) the outbound prompt.

        Implementations should raise :class:`ModelArmorBlocked` when the
        prompt is rejected; callers should treat that as a hard stop.
        """

    @abstractmethod
    def post_call(self, output_text: str) -> ArmorVerdict:
        """Inspect the model output for data-leak / policy violations."""


class ModelArmorBlocked(RuntimeError):
    """Raised when Model Armor blocks a prompt or response."""


class NoOpArmor(ModelArmorHook):
    """Pass-through. Prototype-only. Must be replaced before staging."""

    def pre_call(self, messages: list[ChatMessage]) -> list[ChatMessage]:
        return messages

    def post_call(self, output_text: str) -> ArmorVerdict:
        return ArmorVerdict(allowed=True, reason="noop")
