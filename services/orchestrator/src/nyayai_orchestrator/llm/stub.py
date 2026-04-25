"""Deterministic canned-response Gemini client.

Used by every unit test and by local dev when real credentials are absent.
Responses are keyed by a hash of ``(model, last_user_message)`` so the same
prompt always yields the same structured output — critical for reproducible
Genkit-style eval goldens.

The canned library covers the three prototype agents (Planner, Narrator,
Watcher). Unknown prompts return a minimal valid payload for the requested
schema rather than raising; that keeps tests resilient to prompt tweaks.
"""

from __future__ import annotations

import hashlib
import json
import re
from typing import Any

from .base import ChatMessage, GeminiClient, GeminiResponse


def _prompt_fingerprint(model: str, messages: list[ChatMessage]) -> str:
    last_user = next(
        (m.content for m in reversed(messages) if m.role == "user"),
        "",
    )
    h = hashlib.sha256()
    h.update(model.encode())
    h.update(b"\x1f")
    h.update(last_user.encode())
    return h.hexdigest()[:16]


def _extract_audit_id(messages: list[ChatMessage]) -> str:
    for m in messages:
        match = re.search(r'"audit_id"\s*:\s*"([^"]+)"', m.content)
        if match:
            return match.group(1)
    return "audit-unknown"


def _extract_attributes(messages: list[ChatMessage]) -> list[str]:
    for m in messages:
        if "requested_attributes" in m.content:
            match = re.search(r'"requested_attributes"\s*:\s*\[([^\]]*)\]', m.content)
            if match:
                inner = match.group(1)
                attrs = re.findall(r'"([^"]+)"', inner)
                if attrs:
                    return attrs
    return ["caste", "gender"]


def _canned_plan(messages: list[ChatMessage]) -> dict[str, Any]:
    audit_id = _extract_audit_id(messages)
    attrs = _extract_attributes(messages)
    primary = attrs[0] if attrs else "caste"
    secondary = attrs[1] if len(attrs) > 1 else "gender"
    slices: list[list[str]] = [[primary]]
    if secondary != primary:
        slices.append([secondary])
        slices.append([primary, secondary])
    return {
        "audit_id": audit_id,
        "steps": [
            {
                "step_id": "s1",
                "kind": "policy_check",
                "description": "Confirm DPDP Rule 13 DPIA obligations apply.",
                "target_attributes": [],
            },
            {
                "step_id": "s2",
                "kind": "metric",
                "description": "Compute demographic parity and equal opportunity per slice.",
                "target_attributes": attrs,
            },
            {
                "step_id": "s3",
                "kind": "slice",
                "description": "Evaluate intersectional slice to surface compounded disparity.",
                "target_attributes": attrs[:2],
            },
        ],
        "slices": slices,
        "rationale": (
            "Selected attributes cover the highest-risk protected dimensions for the "
            "stated goal; intersectional slice guards against Simpson-style hiding of "
            "compounded disparity."
        ),
        "estimated_minutes": 6,
    }


def _canned_narrative(messages: list[ChatMessage]) -> dict[str, Any]:
    audit_id = _extract_audit_id(messages)
    # Pull every slice_key we can find in the payload.
    raw = " ".join(m.content for m in messages)
    slice_keys = re.findall(r'"slice_key"\s*:\s*"([^"]+)"', raw)
    if not slice_keys:
        slice_keys = ["caste=SC", "gender=F"]
    unique: list[str] = []
    for k in slice_keys:
        if k not in unique:
            unique.append(k)
    per_slice = [
        {
            "slice_key": k,
            "paragraph": (
                f"Slice {k} shows a measurable selection-rate gap relative to the "
                "majority reference group. Gap magnitude and confidence interval are "
                "reported by the Fairness Metrics service; this paragraph is a "
                "plain-language restatement, not a new computation."
            ),
        }
        for k in unique[:6]
    ]
    return {
        "audit_id": audit_id,
        "summary": (
            "The audit found statistically meaningful disparities on at least one "
            "protected slice. Authoritative numbers are in the metrics table; this "
            "summary restates them for a non-technical reader."
        ),
        "summary_hi": (
            "इस ऑडिट में कम से कम एक संरक्षित समूह पर सांख्यिकीय रूप से अर्थपूर्ण असमानताएँ पाई गई हैं। "
            "आधिकारिक मीट्रिक नीचे की तालिका में हैं; यह सारांश गैर-तकनीकी पाठक के लिए उन्हें दोहराता है।"
        ),
        "per_slice": per_slice,
        "recommendations": [
            {
                "title": "Review upstream label provenance",
                "detail": (
                    "Historical-label bias is the most common root cause of the "
                    "observed disparity; commission a label-audit before re-training."
                ),
                "severity": "advisory",
            },
            {
                "title": "Enable continuous fairness monitoring",
                "detail": (
                    "Schedule the Watcher agent against the production endpoint at "
                    "daily cadence to catch drift early."
                ),
                "severity": "action_required",
            },
        ],
        "disclaimer": (
            "This narrative is generated by Gemini 3 Flash for summarisation only. "
            "The authoritative fairness numbers live in the classical Fairness "
            "Metrics service. Recommendations are non-binding."
        ),
    }


def _extract_float(raw: str, key: str) -> float | None:
    m = re.search(rf'"{key}"\s*:\s*([0-9eE+.\-]+)', raw)
    if not m:
        return None
    try:
        return float(m.group(1))
    except ValueError:
        return None


def _canned_remediation(messages: list[ChatMessage]) -> dict[str, Any]:
    """Stub RemediationPlan. Numbers are re-stamped from the tool output by
    :func:`run_remediation_agent`, so the values we emit here are
    placeholders — only shape matters for tests."""
    audit_id = _extract_audit_id(messages)
    raw = " ".join(m.content for m in messages)
    before = _extract_float(raw, "before_dp_ratio") or 0.5
    after = _extract_float(raw, "after_dp_ratio") or 0.9
    delta = _extract_float(raw, "accuracy_delta_pp")
    if delta is None:
        delta = -1.0
    # Target attribute: grab the string-valued field if present.
    target_match = re.search(
        r'"target_attribute"\s*:\s*"([a-z_]+)"', raw
    )
    target = target_match.group(1) if target_match else None

    return {
        "audit_id": audit_id,
        "mitigation_name": "fairlearn.reductions.ExponentiatedGradient+DemographicParity",
        "summary": (
            "Re-training the classifier under a Demographic Parity reduction "
            "closed the selection-rate gap on the worst-case protected "
            "attribute while holding accuracy within a small margin of the "
            "baseline. The numbers above are the authoritative deltas; this "
            "text restates them in plain language for non-technical reviewers."
        ),
        "before_dp_ratio": max(0.0, min(1.0, before)),
        "after_dp_ratio": max(0.0, min(1.0, after)),
        "accuracy_delta_pp": max(-100.0, min(100.0, delta)),
        "risks": [
            "Demographic Parity does not constrain intersectional slices; "
            "SC-women or rural-Muslim residuals may persist.",
            "Baseline accuracy drops by a few percentage points; validate "
            "against the minimum performance SLA before deployment.",
            "Mitigation quality depends on the quality of the sensitive "
            "feature at train time; noisy or self-reported labels will "
            "attenuate the effect.",
        ],
        "code_patch_summary": (
            "Import ExponentiatedGradient and DemographicParity from "
            "fairlearn.reductions, wrap your existing LogisticRegression in "
            "ExponentiatedGradient(estimator=..., constraints=DemographicParity"
            "(difference_bound=0.05)), and pass sensitive_features=<protected_col> "
            "to the .fit() call. Inference calls .predict unchanged."
        ),
        "target_attribute": target,
        "disclaimer": (
            "Remediation metrics are produced by a classical Fairlearn "
            "ExponentiatedGradient retrain on the audited dataset. The "
            "accompanying narrative is generated by Gemini 3 Flash and is "
            "non-binding advisory text; the authoritative numbers live in "
            "the classical Fairness Metrics service."
        ),
    }


def _canned_drift(messages: list[ChatMessage]) -> dict[str, Any]:
    audit_id = _extract_audit_id(messages)
    raw = " ".join(m.content for m in messages)
    # Look for disparate_impact value to decide level.
    di_match = re.search(r'"overall_disparate_impact"\s*:\s*([0-9eE+.\-]+|null)', raw)
    level = "none"
    reason = "Metrics are within configured thresholds; no drift observed."
    triggering: list[str] = []
    if di_match and di_match.group(1) != "null":
        try:
            di = float(di_match.group(1))
        except ValueError:
            di = 1.0
        if di < 0.7:
            level = "major"
            reason = (
                f"Overall disparate-impact ratio {di:.2f} is below the 0.8 (4/5ths) "
                "threshold; immediate review recommended."
            )
            triggering = ["disparate_impact"]
        elif di < 0.85:
            level = "minor"
            reason = (
                f"Overall disparate-impact ratio {di:.2f} is below the 0.85 advisory "
                "threshold but above the 0.8 hard floor."
            )
            triggering = ["disparate_impact"]
    return {
        "audit_id": audit_id,
        "level": level,
        "reason": reason,
        "triggering_metrics": triggering,
        "confidence": 0.9 if level != "none" else 0.6,
    }


def _looks_like_schema(schema: dict[str, Any], name: str) -> bool:
    title = (schema.get("title") or "").lower()
    return name.lower() in title


class StubGeminiClient(GeminiClient):
    """Offline, deterministic Gemini stand-in.

    Routes on the declared ``title`` of the response schema (``AuditPlan``,
    ``ReportNarrative``, ``DriftFlag``) so the three prototype agents work
    without touching the network.
    """

    def generate_structured(
        self,
        *,
        model: str,
        messages: list[ChatMessage],
        response_schema: dict[str, Any],
        temperature: float = 0.2,
        max_output_tokens: int = 2048,
    ) -> GeminiResponse:
        if _looks_like_schema(response_schema, "AuditPlan"):
            parsed = _canned_plan(messages)
        elif _looks_like_schema(response_schema, "ReportNarrative"):
            parsed = _canned_narrative(messages)
        elif _looks_like_schema(response_schema, "DriftFlag"):
            parsed = _canned_drift(messages)
        elif _looks_like_schema(response_schema, "RemediationPlan"):
            parsed = _canned_remediation(messages)
        else:
            # Minimal echo: return the schema title so callers see it's a stub.
            parsed = {
                "_stub": True,
                "_schema_title": response_schema.get("title", "unknown"),
                "_prompt_fingerprint": _prompt_fingerprint(model, messages),
            }
        text = json.dumps(parsed, sort_keys=True)
        return GeminiResponse(
            text=text,
            parsed=parsed,
            model=model,
            usage={"prompt_tokens": 0, "candidates_tokens": 0},
        )
