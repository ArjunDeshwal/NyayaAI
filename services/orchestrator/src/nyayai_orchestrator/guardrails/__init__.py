"""Guardrails: Model Armor (prompt-injection / jailbreak filter) and SDP
(Sensitive Data Protection pseudonymiser).

Every LLM call in production runs:

    raw_messages  →  SDP.redact  →  ModelArmor.pre_call
                                →  GeminiClient.generate_structured
                                →  ModelArmor.post_call
                                →  Pydantic validate

In the prototype we ship NoOp implementations so the pipeline is wired end
to end; the real templates are plugged in by infra-security-engineer.
"""

from .model_armor import ModelArmorHook, NoOpArmor
from .sdp import NoOpSDP, SDPHook

__all__ = ["ModelArmorHook", "NoOpArmor", "SDPHook", "NoOpSDP"]
