"""Planner agent — Gemini 3.1 Pro.

Why LLM?
--------
Selecting protected attributes and slices from a user's free-text goal plus a
raw dataset schema is *not* a rule-based problem. ``region=state`` can be a
caste proxy in some districts (Muralidharan 2020); ``school_name`` can be a
religion proxy; ``first_name`` can be a gender proxy. A deterministic
``if/elif`` over column names would silently miss those proxy-variables and
ship a non-compliant plan. The Planner needs natural-language reasoning over
schema + goal + regulatory regime to emit an :class:`AuditPlan` that a
compliance officer would sign off. That reasoning is exactly what Gemini 3.1
Pro's long-context + instruction-following is built for.
"""

from __future__ import annotations

import json

from pydantic import ValidationError

from ..guardrails import ModelArmorHook, SDPHook
from ..llm.base import ChatMessage, GeminiClient
from ..schemas import AuditPlan, AuditRequest

# ---------------------------------------------------------------------------
# Prompt
# ---------------------------------------------------------------------------

PLANNER_SYSTEM_PROMPT = """You are the Planner agent inside NyayaAI, an \
India-aware bias auditor for public-interest AI. Given a free-text audit goal, \
a model card, a dataset schema, and a regulatory regime, you produce a \
structured audit plan.

Rules:
  1. Consider proxy variables (surname, PIN, school name, mother-tongue) when \
selecting protected attributes — do not limit yourself to columns literally named \
"caste" or "religion".
  2. Every plan MUST include at least one single-attribute slice AND at least \
one intersectional slice (two or more attributes).
  3. Keep the plan to at most 8 steps and at most 10 minutes of estimated audit time.
  4. If the goal is out of scope (not a fairness-audit request), respond with the \
single step ``kind: policy_check`` and rationale explaining the refusal.
  5. Only emit valid JSON matching the response schema. No prose, no markdown \
fences, no trailing commas."""


def _build_user_prompt(request: AuditRequest) -> str:
    # We serialise the request as JSON so the model sees typed structure.
    # In production this is what SDP redacts; in dev SDP is a no-op.
    payload = request.model_dump(mode="json")
    return (
        "Audit request (structured):\n"
        f"{json.dumps(payload, indent=2, sort_keys=True)}\n\n"
        "Return the AuditPlan JSON now."
    )


# ---------------------------------------------------------------------------
# Response schema (kept minimal — full validation is Pydantic's job)
# ---------------------------------------------------------------------------

_AUDIT_PLAN_SCHEMA: dict = {
    "title": "AuditPlan",
    "type": "object",
    "required": ["audit_id", "steps", "slices", "rationale", "estimated_minutes"],
    "properties": {
        "audit_id": {"type": "string"},
        "steps": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["step_id", "kind", "description", "target_attributes"],
                "properties": {
                    "step_id": {"type": "string"},
                    "kind": {
                        "type": "string",
                        "enum": [
                            "metric",
                            "slice",
                            "counterfactual_placeholder",
                            "policy_check",
                        ],
                    },
                    "description": {"type": "string"},
                    "target_attributes": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                },
            },
        },
        "slices": {
            "type": "array",
            "items": {"type": "array", "items": {"type": "string"}},
        },
        "rationale": {"type": "string"},
        "estimated_minutes": {"type": "integer"},
    },
}


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def run_planner(
    request: AuditRequest,
    *,
    client: GeminiClient,
    model: str,
    armor: ModelArmorHook,
    sdp: SDPHook,
) -> AuditPlan:
    """Run the Planner agent and return a validated :class:`AuditPlan`."""
    raw_messages = [
        ChatMessage(role="system", content=PLANNER_SYSTEM_PROMPT),
        ChatMessage(role="user", content=_build_user_prompt(request)),
    ]

    # Redact PII first (no-op in prototype), then Model-Armor check.
    messages = sdp.redact(raw_messages)
    messages = armor.pre_call(messages)

    response = client.generate_structured(
        model=model,
        messages=messages,
        response_schema=_AUDIT_PLAN_SCHEMA,
        temperature=0.1,
        max_output_tokens=2048,
    )

    verdict = armor.post_call(response.text)
    if not verdict.allowed:
        raise RuntimeError(f"Model Armor blocked Planner output: {verdict.reason}")

    try:
        plan = AuditPlan.model_validate(response.parsed)
    except ValidationError as e:
        raise RuntimeError(f"Planner emitted invalid AuditPlan: {e}") from e

    # Hard invariant: audit_id must match the request.
    if plan.audit_id != request.audit_id:
        plan = plan.model_copy(update={"audit_id": request.audit_id})
    return plan
