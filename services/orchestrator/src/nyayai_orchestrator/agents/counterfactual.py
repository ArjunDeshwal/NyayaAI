"""Counterfactual agent — Gemini 3 Flash.

Why LLM?
--------
The flip math is classical (already done by
:func:`nyayai_fairlearn_ext.compute_counterfactual_flips`). What the LLM
adds is the **interpretation**: turning "flip rate SC->GENERAL = 0.18"
into "we found that 18% of SC applicants would have received a different
decision had they been labelled GENERAL — this is direct caste-correlated
discrimination, not a proxy effect". Severity is derived classically; the
LLM only writes prose.

Per CLAUDE.md, every LLM call goes through Model Armor + SDP. This agent
emits a strict JSON schema and never invents flip rates — it restates the
numbers it was given.
"""

from __future__ import annotations

import json

from pydantic import ValidationError

from ..guardrails import ModelArmorHook, SDPHook
from ..llm.base import ChatMessage, GeminiClient
from ..schemas import CounterfactualNarrative, CounterfactualSummary

COUNTERFACTUAL_SYSTEM_PROMPT = """You are the Counterfactual agent inside \
NyayaAI. You receive a CounterfactualSummary — a structured report of \
individual-fairness flip rates produced when the protected attribute on \
each sampled row is swapped to every other value and the model is re-scored.

Your job is to interpret the numbers in plain language for a non-technical \
reader (policy officer, NGO reviewer). The flip math is owned by the \
classical fairness service; you must NEVER invent a flip rate.

Rules:
  1. Restate ``directional_flip_rate`` and the dominant entries of \
``flip_rate_by_pair`` faithfully. Cite percentages exactly to one decimal.
  2. Headline must lead with the most striking number. Examples of good \
shapes:
     - "18.0% of SC applicants flip from denied to approved when re-labelled \
GENERAL"
     - "Counterfactual stability: only 2.4% of decisions change when caste \
is swapped"
  3. Severity is supplied to you (info / advisory / action_required). Use it \
verbatim — do not change it.
  4. Interpretation paragraph (1–2 paragraphs, max 2000 chars) must \
distinguish:
     - **Direct discrimination** if flips are high and the protected \
attribute itself is the trigger (i.e. removing it would zero out the flips).
     - **Proxy discrimination** if flips are low — the protected attribute \
is not the proximate cause; correlated features (root-cause analysis) are. \
Direct readers to the Root-Cause section.
  5. Each example_takeaway is a single sentence reproducing the example's \
feature snapshot exactly: "Same applicant (income ₹X, urban): denied as SC, \
approved as GENERAL". Render numeric income with the rupee glyph if the \
field is named 'income' or contains 'income' in its key. Keep the order of \
examples as given.
  6. Only emit valid JSON matching the response schema. No prose outside \
JSON. No markdown fences."""


def _classify_severity(directional_flip_rate: float) -> str:
    """Classical severity rule. The LLM cannot override this."""
    if directional_flip_rate >= 0.15:
        return "action_required"
    if directional_flip_rate >= 0.05:
        return "advisory"
    return "info"


def _build_user_prompt(
    summary: CounterfactualSummary, severity: str
) -> str:
    payload = summary.model_dump(mode="json")
    payload["__severity_override"] = severity
    return (
        "CounterfactualSummary (structured input — restate these numbers, "
        "do not recompute):\n"
        f"{json.dumps(payload, indent=2, sort_keys=True, default=str)}\n\n"
        f"Use severity={severity!r} verbatim in your output. Return the "
        "CounterfactualNarrative JSON now."
    )


_COUNTERFACTUAL_SCHEMA: dict = {
    "title": "CounterfactualNarrative",
    "type": "object",
    "required": [
        "audit_id",
        "headline",
        "interpretation",
        "severity",
        "example_takeaways",
    ],
    "properties": {
        "audit_id": {"type": "string"},
        "headline": {"type": "string"},
        "interpretation": {"type": "string"},
        "severity": {
            "type": "string",
            "enum": ["info", "advisory", "action_required"],
        },
        "example_takeaways": {
            "type": "array",
            "items": {"type": "string"},
            "maxItems": 5,
        },
        "disclaimer": {"type": "string"},
    },
}


def run_counterfactual_agent(
    summary: CounterfactualSummary,
    *,
    client: GeminiClient,
    model: str,
    armor: ModelArmorHook,
    sdp: SDPHook,
) -> CounterfactualNarrative:
    """Run the Counterfactual narrator and return a validated narrative.

    Severity is classified classically by ``directional_flip_rate``; the LLM
    is instructed to use it verbatim and the result is re-stamped post-call
    to guarantee the contract.
    """
    severity = _classify_severity(summary.directional_flip_rate)

    raw_messages = [
        ChatMessage(role="system", content=COUNTERFACTUAL_SYSTEM_PROMPT),
        ChatMessage(role="user", content=_build_user_prompt(summary, severity)),
    ]
    messages = sdp.redact(raw_messages)
    messages = armor.pre_call(messages)

    response = client.generate_structured(
        model=model,
        messages=messages,
        response_schema=_COUNTERFACTUAL_SCHEMA,
        temperature=0.2,
        max_output_tokens=2048,
    )

    verdict = armor.post_call(response.text)
    if not verdict.allowed:
        raise RuntimeError(
            f"Model Armor blocked Counterfactual output: {verdict.reason}"
        )

    try:
        narrative = CounterfactualNarrative.model_validate(response.parsed)
    except ValidationError as e:
        raise RuntimeError(
            f"Counterfactual emitted invalid CounterfactualNarrative: {e}"
        ) from e

    # Re-stamp the audit_id + severity so the LLM cannot drift them.
    updates: dict = {}
    if narrative.audit_id != summary.audit_id:
        updates["audit_id"] = summary.audit_id
    if narrative.severity != severity:
        updates["severity"] = severity  # type: ignore[assignment]
    if updates:
        narrative = narrative.model_copy(update=updates)
    return narrative
