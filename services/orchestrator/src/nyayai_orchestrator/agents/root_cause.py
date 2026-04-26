"""Root-Cause agent — Gemini 3 Flash.

Why LLM?
--------
Classical permutation feature importance produces numbers ("feature
'pincode' has contribution_to_disparity = 0.21"). Turning that into "Pincode
is the strongest carrier of caste-correlated bias — likely because urban
versus rural lending patterns and historical residential segregation make
pincode a near-perfect proxy for caste in Tier-2 / Tier-3 cities" requires
India-context reasoning that templated text cannot produce. The LLM does
this synthesis at low cost; the contribution numbers themselves are
stamped through verbatim from the classical tool.

Per CLAUDE.md, every LLM call goes through Model Armor + SDP. This agent
emits a strict JSON schema and never invents feature contributions.
"""

from __future__ import annotations

import json

from pydantic import ValidationError

from ..guardrails import ModelArmorHook, SDPHook
from ..llm.base import ChatMessage, GeminiClient
from ..schemas import (
    FeatureContribution,
    FeatureExplanation,
    RootCauseNarrative,
    RootCauseSummary,
)

ROOT_CAUSE_SYSTEM_PROMPT = """You are the Root-Cause agent inside NyayaAI. \
You receive a RootCauseSummary — a ranked list of feature contributions to \
demographic-parity disparity, computed by classical permutation feature \
importance against the DP gap.

Your job is to explain *why* the top features carry bias in the Indian \
context. Common India-specific proxies for caste/religion/region:
  - **pincode** — residential segregation by caste persists in many Tier-2 \
and Tier-3 cities; pincode therefore correlates strongly with caste.
  - **surname / last_name** — surname is a near-deterministic caste signal in \
many Indian linguistic communities.
  - **school_name / education_institution** — government vs private vs \
language-medium schools track caste and class lines.
  - **language / mother_tongue** — proxies for region and sometimes religion.
  - **employment_sector / occupation** — informal-sector employment is \
disproportionately Dalit, Adivasi, and Muslim.
  - **father_occupation** — explicitly inherited and almost a direct caste \
indicator in rural data.
  - **address / city_tier** — same dynamics as pincode at coarser granularity.

Rules:
  1. Restate each top driver's ``contribution_to_disparity`` exactly as \
given. Do NOT invent or recompute.
  2. For each top driver (up to 5), write one sentence in \
``plain_explanation`` explaining what social structure makes this feature \
carry bias. Cite the dataset name when relevant.
  3. ``proxy_warnings`` is one short line per feature in \
``summary.proxy_features`` saying what social structure makes it a proxy. \
Do NOT add features the summary did not flag as proxies.
  4. ``suggested_actions`` are concrete and executable: "Drop or hash the \
pincode column", "Replace surname with a one-way hash before training", \
"Add a district-level fairness constraint forbidding pincode usage below \
the district level". 3-5 items, each under 200 chars.
  5. Only emit valid JSON matching the response schema. No prose outside \
JSON. No markdown fences."""


def _build_user_prompt(
    summary: RootCauseSummary, dataset_name: str
) -> str:
    payload = summary.model_dump(mode="json")
    payload["__dataset_name"] = dataset_name
    return (
        "RootCauseSummary (structured input — restate these numbers, do not "
        "recompute):\n"
        f"{json.dumps(payload, indent=2, sort_keys=True, default=str)}\n\n"
        "Return the RootCauseNarrative JSON now. Each top_drivers entry must "
        "preserve feature_name + contribution_to_disparity exactly; only "
        "plain_explanation is your prose."
    )


_ROOT_CAUSE_SCHEMA: dict = {
    "title": "RootCauseNarrative",
    "type": "object",
    "required": ["audit_id", "headline", "top_drivers"],
    "properties": {
        "audit_id": {"type": "string"},
        "headline": {"type": "string"},
        "top_drivers": {
            "type": "array",
            "minItems": 1,
            "maxItems": 5,
            "items": {
                "type": "object",
                "required": [
                    "feature_name",
                    "contribution_to_disparity",
                    "plain_explanation",
                ],
                "properties": {
                    "feature_name": {"type": "string"},
                    "contribution_to_disparity": {"type": "number"},
                    "plain_explanation": {"type": "string"},
                },
            },
        },
        "proxy_warnings": {
            "type": "array",
            "items": {"type": "string"},
            "maxItems": 8,
        },
        "suggested_actions": {
            "type": "array",
            "items": {"type": "string"},
            "maxItems": 5,
        },
        "disclaimer": {"type": "string"},
    },
}


def _restamp_top_drivers(
    narrative: RootCauseNarrative, summary: RootCauseSummary
) -> RootCauseNarrative:
    """Force the LLM's ``contribution_to_disparity`` to match the classical
    rankings. The LLM owns ``plain_explanation`` only; numbers are
    authoritative from the tool."""
    by_name: dict[str, FeatureContribution] = {
        r.feature_name: r for r in summary.rankings
    }
    fixed: list[FeatureExplanation] = []
    for driver in narrative.top_drivers:
        canonical = by_name.get(driver.feature_name)
        if canonical is None:
            # LLM hallucinated a feature name — keep it but zero the number.
            fixed.append(driver.model_copy(update={"contribution_to_disparity": 0.0}))
            continue
        if (
            abs(driver.contribution_to_disparity - canonical.contribution_to_disparity)
            > 1e-6
        ):
            fixed.append(
                driver.model_copy(
                    update={
                        "contribution_to_disparity": canonical.contribution_to_disparity
                    }
                )
            )
        else:
            fixed.append(driver)
    return narrative.model_copy(update={"top_drivers": fixed})


def run_root_cause_agent(
    summary: RootCauseSummary,
    dataset_name: str,
    *,
    client: GeminiClient,
    model: str,
    armor: ModelArmorHook,
    sdp: SDPHook,
) -> RootCauseNarrative:
    """Run the Root-Cause narrator and return a validated narrative.

    The LLM's contribution_to_disparity values are re-stamped post-call to
    match the classical permutation-importance output. The LLM owns only
    plain_explanation, proxy_warnings, suggested_actions, and the headline.
    """
    raw_messages = [
        ChatMessage(role="system", content=ROOT_CAUSE_SYSTEM_PROMPT),
        ChatMessage(role="user", content=_build_user_prompt(summary, dataset_name)),
    ]
    messages = sdp.redact(raw_messages)
    messages = armor.pre_call(messages)

    response = client.generate_structured(
        model=model,
        messages=messages,
        response_schema=_ROOT_CAUSE_SCHEMA,
        temperature=0.2,
        max_output_tokens=2048,
    )

    verdict = armor.post_call(response.text)
    if not verdict.allowed:
        raise RuntimeError(
            f"Model Armor blocked Root-Cause output: {verdict.reason}"
        )

    try:
        narrative = RootCauseNarrative.model_validate(response.parsed)
    except ValidationError as e:
        raise RuntimeError(
            f"Root-Cause emitted invalid RootCauseNarrative: {e}"
        ) from e

    if narrative.audit_id != summary.audit_id:
        narrative = narrative.model_copy(update={"audit_id": summary.audit_id})
    return _restamp_top_drivers(narrative, summary)
