"""Watcher agent (prototype) — Gemini 3.1 Flash-Lite.

Why LLM?
--------
The *probe* (numerical drift detection) is classical and lives elsewhere.
What the Watcher needs Gemini for is the **semantic** part: deciding
whether an observed shift is a real fairness regression or a benign traffic
change, and producing a one-line human-readable alert body with suggested
first response. Flash-Lite is the cheapest tier appropriate for a polling
loop. In the prototype this is a rule-based-behind-an-LLM-interface: we
keep the :class:`DriftFlag` contract stable so swapping in the real LLM
call at finals time is a one-line change.
"""

from __future__ import annotations

import json

from pydantic import ValidationError

from ..guardrails import ModelArmorHook, SDPHook
from ..llm.base import ChatMessage, GeminiClient
from ..schemas import AuditResult, DriftFlag

WATCHER_SYSTEM_PROMPT = """You are the Watcher agent inside NyayaAI. You \
receive a snapshot of an audit result (metrics per slice) and classify drift \
as one of: none, minor, major.

Heuristics:
  * A disparate-impact ratio below 0.8 (the US EEOC 4/5ths rule and the RBI \
advisory threshold) → major.
  * 0.8 ≤ DI < 0.85 → minor.
  * DI ≥ 0.85 AND no slice has a demographic-parity difference above 0.1 → none.
  * Missing metrics (empty result) → level ``none`` with reason stating the \
absence.

Only emit valid JSON matching the DriftFlag schema. No prose outside JSON."""


def _build_user_prompt(result: AuditResult) -> str:
    payload = result.model_dump(mode="json")
    return (
        "Audit snapshot (structured):\n"
        f"{json.dumps(payload, indent=2, sort_keys=True, default=str)}\n\n"
        "Return the DriftFlag JSON now."
    )


_DRIFT_SCHEMA: dict = {
    "title": "DriftFlag",
    "type": "object",
    "required": ["audit_id", "level", "reason"],
    "properties": {
        "audit_id": {"type": "string"},
        "level": {"type": "string", "enum": ["none", "minor", "major"]},
        "reason": {"type": "string"},
        "triggering_metrics": {"type": "array", "items": {"type": "string"}},
        "confidence": {"type": "number"},
    },
}


def run_watcher(
    result: AuditResult,
    *,
    client: GeminiClient,
    model: str,
    armor: ModelArmorHook,
    sdp: SDPHook,
) -> DriftFlag:
    """Run the Watcher agent and return a validated :class:`DriftFlag`."""
    raw_messages = [
        ChatMessage(role="system", content=WATCHER_SYSTEM_PROMPT),
        ChatMessage(role="user", content=_build_user_prompt(result)),
    ]
    messages = sdp.redact(raw_messages)
    messages = armor.pre_call(messages)

    response = client.generate_structured(
        model=model,
        messages=messages,
        response_schema=_DRIFT_SCHEMA,
        temperature=0.0,
        max_output_tokens=512,
    )

    verdict = armor.post_call(response.text)
    if not verdict.allowed:
        raise RuntimeError(f"Model Armor blocked Watcher output: {verdict.reason}")

    try:
        flag = DriftFlag.model_validate(response.parsed)
    except ValidationError as e:
        raise RuntimeError(f"Watcher emitted invalid DriftFlag: {e}") from e

    if flag.audit_id != result.audit_id:
        flag = flag.model_copy(update={"audit_id": result.audit_id})
    return flag
