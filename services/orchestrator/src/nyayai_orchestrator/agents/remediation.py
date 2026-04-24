"""Remediation agent — Gemini 3 Flash.

Why LLM?
--------
The mitigation math is classical: Fairlearn's
:class:`~fairlearn.reductions.ExponentiatedGradient` with a
:class:`~fairlearn.reductions.DemographicParity` constraint is a reductions
algorithm with a closed-form stopping criterion. An ``if``-statement can fit
the model, recompute metrics, and even decide "yes, DP went from 0.42 to
0.94". What it **cannot** do is write the two paragraphs a compliance officer
actually needs: "here is why we picked Demographic Parity over Equalized
Odds for this audit", "here are the residual risks of reductions-based
mitigation (intersectional DP isn't constrained, small subgroup variance may
still exceed bound)", and — critically — "here is the one-line change in the
training pipeline to reproduce this lift in your repo". That last item is
plain-language code-patch narration across an arbitrary Python training
script the LLM has never seen. Gemini 3 Flash does it cheaply and at
throughput; the authoritative numbers remain owned by the classical
remediation tool and are passed in verbatim — the LLM is forbidden from
inventing them. This is the same "classical math, LLM narrates" contract
the Narrator uses.
"""

from __future__ import annotations

import json

from pydantic import ValidationError

from ..guardrails import ModelArmorHook, SDPHook
from ..llm.base import ChatMessage, GeminiClient
from ..schemas import RemediationPlan
from ..tools.remediation_tool import RemediationOutcome

REMEDIATION_SYSTEM_PROMPT = """You are the Remediation agent inside NyayaAI. \
You receive the deterministic output of a Fairlearn-based mitigation pass \
(before/after demographic-parity ratios, accuracy delta, target protected \
attribute) and write a plain-language plan that a model owner can act on.

Context on the mitigation:
  * Technique: fairlearn.reductions.ExponentiatedGradient with a \
DemographicParity constraint (difference_bound = epsilon). This is a \
reductions meta-algorithm — it reweights training examples and fits a \
sequence of LogisticRegression classifiers whose randomised average \
satisfies the parity constraint up to epsilon.
  * Tradeoff: Demographic Parity is the most aggressive fairness constraint; \
it enforces equal positive-prediction rates across groups. Expect a small \
accuracy drop versus the baseline (typically 1-4 percentage points). If the \
underlying base rates are legitimately different (for a given business \
context), Equalized Odds may be a better fit — flag that as a risk.
  * Not covered: intersectional parity (e.g. SC women) is not constrained by \
this reduction; residual disparity on intersectional slices is possible.

Hard rules:
  1. You NEVER invent numbers. ``before_dp_ratio``, ``after_dp_ratio`` and \
``accuracy_delta_pp`` come from the classical tool — quote them exactly.
  2. ``code_patch_summary`` must be a concrete 3-6 line change description \
(in prose, not diff format) for a typical scikit-learn training script: \
import the mitigator, wrap the estimator, pass ``sensitive_features=A_train`` \
at fit time, use ``.predict`` at inference time. Do not invent API names.
  3. ``risks`` must include at least: residual intersectional disparity, \
baseline accuracy impact, and sensitivity to sensitive-feature quality.
  4. ``summary`` is at most 3 short paragraphs; ombudsman-readable.
  5. Only emit valid JSON matching the RemediationPlan schema. No prose \
outside JSON, no markdown fences."""


def _build_user_prompt(outcome: RemediationOutcome) -> str:
    payload = {
        "audit_id": outcome.audit_id,
        "mitigation_name": outcome.mitigation_name,
        "target_attribute": outcome.target_attribute,
        "target_column": outcome.target_column,
        "before_dp_ratio": round(outcome.before_dp_ratio, 4),
        "after_dp_ratio": round(outcome.after_dp_ratio, 4),
        "baseline_accuracy": round(outcome.baseline_accuracy, 4),
        "remediated_accuracy": round(outcome.remediated_accuracy, 4),
        "accuracy_delta_pp": outcome.accuracy_delta_pp,
        "epsilon": outcome.epsilon,
        "n_train": outcome.n_train,
        "n_test": outcome.n_test,
    }
    return (
        "Classical remediation tool output (authoritative; do not modify numbers):\n"
        f"{json.dumps(payload, indent=2, sort_keys=True, default=str)}\n\n"
        "Write the RemediationPlan JSON now. Restate before_dp_ratio, "
        "after_dp_ratio, and accuracy_delta_pp *exactly* as given above."
    )


_REMEDIATION_SCHEMA: dict = {
    "title": "RemediationPlan",
    "type": "object",
    "required": [
        "audit_id",
        "mitigation_name",
        "summary",
        "before_dp_ratio",
        "after_dp_ratio",
        "accuracy_delta_pp",
        "risks",
        "code_patch_summary",
    ],
    "properties": {
        "audit_id": {"type": "string"},
        "mitigation_name": {"type": "string"},
        "summary": {"type": "string"},
        "before_dp_ratio": {"type": "number"},
        "after_dp_ratio": {"type": "number"},
        "accuracy_delta_pp": {"type": "number"},
        "risks": {"type": "array", "items": {"type": "string"}},
        "code_patch_summary": {"type": "string"},
        "target_attribute": {
            "type": "string",
            "enum": [
                "caste",
                "religion",
                "gender",
                "region",
                "urban_rural",
                "language",
                "disability",
                "age_band",
            ],
        },
        "disclaimer": {"type": "string"},
    },
}


def run_remediation_agent(
    outcome: RemediationOutcome,
    *,
    client: GeminiClient,
    model: str,
    armor: ModelArmorHook,
    sdp: SDPHook,
) -> RemediationPlan:
    """Run the Remediation agent and return a validated :class:`RemediationPlan`.

    Numbers are stamped from ``outcome`` *after* the LLM returns — this is
    the hard invariant from the agent-patterns skill: the LLM is never the
    source of truth for a fairness metric.
    """
    raw_messages = [
        ChatMessage(role="system", content=REMEDIATION_SYSTEM_PROMPT),
        ChatMessage(role="user", content=_build_user_prompt(outcome)),
    ]
    messages = sdp.redact(raw_messages)
    messages = armor.pre_call(messages)

    response = client.generate_structured(
        model=model,
        messages=messages,
        response_schema=_REMEDIATION_SCHEMA,
        temperature=0.2,
        max_output_tokens=4096,
    )

    verdict = armor.post_call(response.text)
    if not verdict.allowed:
        raise RuntimeError(f"Model Armor blocked Remediation output: {verdict.reason}")

    try:
        plan = RemediationPlan.model_validate(response.parsed)
    except ValidationError as e:
        raise RuntimeError(f"Remediation agent emitted invalid RemediationPlan: {e}") from e

    # Hard invariants: the LLM never owns numbers or the audit_id.
    # Re-stamp from the classical tool's outcome so hallucinations can't leak
    # into the report.
    plan = plan.model_copy(
        update={
            "audit_id": outcome.audit_id,
            "mitigation_name": outcome.mitigation_name,
            "before_dp_ratio": max(0.0, min(1.0, float(outcome.before_dp_ratio))),
            "after_dp_ratio": max(0.0, min(1.0, float(outcome.after_dp_ratio))),
            "accuracy_delta_pp": max(-100.0, min(100.0, float(outcome.accuracy_delta_pp))),
            "target_attribute": outcome.target_attribute,
        }
    )
    return plan
