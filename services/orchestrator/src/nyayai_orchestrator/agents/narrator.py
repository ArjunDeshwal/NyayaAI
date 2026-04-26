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
from ..schemas import (
    AuditResult,
    CounterfactualNarrative,
    ReportNarrative,
    RootCauseNarrative,
)

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
  5. Always emit a ``summary_hi`` field — a faithful Devanagari-Hindi \
translation of ``summary``. Do not transliterate; produce natural Hindi prose. \
Keep technical terms like "demographic parity ratio" in English in parentheses \
the first time they appear. Length: similar to the English ``summary``.
  6. When the user prompt includes ``counterfactual_findings`` or \
``root_cause_findings``, weave one sentence each into the ``summary``. Do \
not duplicate the dedicated sections; only foreshadow them so the reader \
sees the headline finding in the executive summary.
  7. Only emit valid JSON matching the response schema. No prose outside \
JSON, no markdown fences."""


_NARRATIVE_MAX_SLICES = 12


def _condense_for_narrator(result: AuditResult) -> dict:
    """Narrator narrative must stay under 8k-ish tokens of output; to do that
    we feed it a *condensed* view — all per-attribute DP ratios (cheap) plus
    the K intersectional slices with the largest selection-rate spread (the
    "worst" ones a human would want explained). 54 raw metrics produces 54
    paragraphs, which always truncates."""
    payload = result.model_dump(mode="json")

    metrics = payload.get("metrics", [])
    per_attr = [m for m in metrics if m["slice_key"].startswith("attribute=")]
    inter = [m for m in metrics if not m["slice_key"].startswith("attribute=")]
    # Group intersectional by slice_key so each slice contributes once.
    by_slice: dict[str, dict] = {}
    for m in inter:
        by_slice.setdefault(m["slice_key"], {"slice_key": m["slice_key"], "metrics": {}, "n": m["sample_size"]})
        by_slice[m["slice_key"]]["metrics"][m["metric"]] = m["value"]

    # Rank intersectional slices by |selection_rate - overall_rate|.
    overall_rate = next(
        (m["value"] for m in inter if m["metric"] == "selection_rate"),
        0.5,
    )

    def _spread(entry: dict) -> float:
        sr = entry["metrics"].get("selection_rate")
        if sr is None:
            return 0.0
        return abs(float(sr) - float(overall_rate))

    worst = sorted(by_slice.values(), key=_spread, reverse=True)[:_NARRATIVE_MAX_SLICES]

    return {
        "audit_id": payload["audit_id"],
        "overall_disparate_impact": payload.get("overall_disparate_impact"),
        "per_attribute_metrics": per_attr,
        "worst_intersectional_slices": worst,
    }


def _build_user_prompt(
    result: AuditResult,
    counterfactual_narrative: CounterfactualNarrative | None = None,
    root_cause_narrative: RootCauseNarrative | None = None,
) -> str:
    payload = _condense_for_narrator(result)
    if counterfactual_narrative is not None:
        payload["counterfactual_findings"] = {
            "headline": counterfactual_narrative.headline,
            "severity": counterfactual_narrative.severity,
        }
    if root_cause_narrative is not None:
        payload["root_cause_findings"] = {
            "headline": root_cause_narrative.headline,
            "top_features": [
                {
                    "feature_name": d.feature_name,
                    "contribution_to_disparity": d.contribution_to_disparity,
                }
                for d in root_cause_narrative.top_drivers[:3]
            ],
        }
    return (
        "Audit result (condensed: per-attribute metrics + worst intersectional slices):\n"
        f"{json.dumps(payload, indent=2, sort_keys=True, default=str)}\n\n"
        "Write exactly one paragraph per slice in worst_intersectional_slices "
        "(so at most 12 paragraphs in per_slice). If counterfactual_findings or "
        "root_cause_findings are present, foreshadow them in one sentence each "
        "inside ``summary`` (do not invent new sections). Return the "
        "ReportNarrative JSON now."
    )


_NARRATIVE_SCHEMA: dict = {
    "title": "ReportNarrative",
    "type": "object",
    "required": ["audit_id", "summary", "summary_hi", "per_slice", "recommendations"],
    "properties": {
        "audit_id": {"type": "string"},
        "summary": {"type": "string"},
        "summary_hi": {"type": "string"},
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
    counterfactual_narrative: CounterfactualNarrative | None = None,
    root_cause_narrative: RootCauseNarrative | None = None,
) -> ReportNarrative:
    """Run the Narrator agent and return a validated :class:`ReportNarrative`.

    ``counterfactual_narrative`` and ``root_cause_narrative`` are optional
    upstream findings; when supplied, the Narrator's summary foreshadows
    them so a reader sees the headline before drilling into the dedicated
    sections.
    """
    raw_messages = [
        ChatMessage(role="system", content=NARRATOR_SYSTEM_PROMPT),
        ChatMessage(
            role="user",
            content=_build_user_prompt(
                result,
                counterfactual_narrative=counterfactual_narrative,
                root_cause_narrative=root_cause_narrative,
            ),
        ),
    ]
    messages = sdp.redact(raw_messages)
    messages = armor.pre_call(messages)

    response = client.generate_structured(
        model=model,
        messages=messages,
        response_schema=_NARRATIVE_SCHEMA,
        temperature=0.3,
        max_output_tokens=8192,
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
