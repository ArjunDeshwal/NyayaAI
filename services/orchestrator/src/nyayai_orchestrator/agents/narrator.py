"""Narrator agent — Gemini 3 Flash.

Why LLM?
--------
Compliance narrative is not templated. Every audit has a different set of
slices, a different root-cause profile, and a different remediation
recommendation. A string-template approach ("{metric} is {value} for
{slice}") produces text that is technically correct but reads like a shell
script — ombudsmen and NGO reviewers do not use it. Gemini 3 Flash does the
plain-language synthesis across slices (including intersectional ones)
cheaply and at throughput. The authoritative numbers remain owned by the
classical Fairness Metrics service; the Narrator only *restates* them.
"""

from __future__ import annotations

import json

from pydantic import ValidationError

from ..guardrails import ModelArmorHook, SDPHook
from ..llm.base import ChatMessage, GeminiClient
from ..schemas import AuditResult, ReportNarrative

NARRATOR_SYSTEM_PROMPT = """You are the Narrator agent inside NyayaAI. You \
translate a fairness audit result (numbers, slices, thresholds) into a plain-\
language report for a non-technical reader such as a policy officer or NGO \
reviewer.

Rules:
  1. You never invent metric numbers. Restate the numbers the audit result \
supplies; never compute new ones.
  2. Produce one paragraph per slice in ``result.metrics`` (dedup by slice_key). \
Each paragraph explains *what* the number means in plain language, not what the \
metric formula is.
  3. Recommendations must be non-binding and framed as advisory. Do not claim \
legal effect.
  4. If the audit result is empty (no metrics), return a single summary \
paragraph explaining that no slices were evaluated and recommend re-planning.
  5. Only emit valid JSON matching the response schema. No prose outside JSON, \
no markdown fences."""


def _build_user_prompt(result: AuditResult) -> str:
    payload = result.model_dump(mode="json")
    return (
        "Audit result (structured):\n"
        f"{json.dumps(payload, indent=2, sort_keys=True, default=str)}\n\n"
        "Return the ReportNarrative JSON now."
    )


_NARRATIVE_SCHEMA: dict = {
    "title": "ReportNarrative",
    "type": "object",
    "required": ["audit_id", "summary", "per_slice", "recommendations"],
    "properties": {
        "audit_id": {"type": "string"},
        "summary": {"type": "string"},
        "per_slice": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["slice_key", "paragraph"],
                "properties": {
                    "slice_key": {"type": "string"},
                    "paragraph": {"type": "string"},
                },
            },
        },
        "recommendations": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["title", "detail", "severity"],
                "properties": {
                    "title": {"type": "string"},
                    "detail": {"type": "string"},
                    "severity": {
                        "type": "string",
                        "enum": ["info", "advisory", "action_required"],
                    },
                },
            },
        },
        "disclaimer": {"type": "string"},
    },
}


def run_narrator(
    result: AuditResult,
    *,
    client: GeminiClient,
    model: str,
    armor: ModelArmorHook,
    sdp: SDPHook,
) -> ReportNarrative:
    """Run the Narrator agent and return a validated :class:`ReportNarrative`."""
    raw_messages = [
        ChatMessage(role="system", content=NARRATOR_SYSTEM_PROMPT),
        ChatMessage(role="user", content=_build_user_prompt(result)),
    ]
    messages = sdp.redact(raw_messages)
    messages = armor.pre_call(messages)

    response = client.generate_structured(
        model=model,
        messages=messages,
        response_schema=_NARRATIVE_SCHEMA,
        temperature=0.3,
        max_output_tokens=2048,
    )

    verdict = armor.post_call(response.text)
    if not verdict.allowed:
        raise RuntimeError(f"Model Armor blocked Narrator output: {verdict.reason}")

    try:
        narrative = ReportNarrative.model_validate(response.parsed)
    except ValidationError as e:
        raise RuntimeError(f"Narrator emitted invalid ReportNarrative: {e}") from e

    if narrative.audit_id != result.audit_id:
        narrative = narrative.model_copy(update={"audit_id": result.audit_id})
    return narrative
