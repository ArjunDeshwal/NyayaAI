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
attribute, and a boolean ``improved`` verdict from the classical keep-or-\
discard gate) and write a plain-language plan that a model owner can act on.

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

Two modes — pick based on ``improved``:

  IMPROVED = true (the gate accepted the mitigation):
    * ``mitigation_name`` = "fairlearn.reductions.ExponentiatedGradient+DemographicParity"
    * Summary describes what Demographic Parity does and quotes the number lift.
    * ``code_patch_summary`` is the concrete 3-6 line change (import the \
mitigator, wrap the estimator, pass ``sensitive_features=A_train`` at fit \
time, use ``.predict`` at inference).
    * ``risks`` covers residual intersectional disparity, baseline accuracy \
impact, sensitive-feature quality.

  IMPROVED = false (the gate rejected this run — original model retained):
    * ``mitigation_name`` = "none (original model retained)".
    * Summary must plainly state that the epsilon sweep did not find a \
policy meeting the DP-lift or accuracy floor, quote the ``reason`` verbatim, \
and recommend the team try Equalized Odds, a richer base estimator, or a \
lower-cardinality target. DO NOT claim any improvement.
    * ``code_patch_summary`` describes an *alternative* next step (try \
``EqualizedOdds()`` or ``GradientBoostingClassifier`` as the base), NOT a \
patch that applies the failed mitigation.
    * ``risks`` must include: "this run did not deliver fairness lift; model \
stays at baseline" and the original intersectional/accuracy caveats. \
Severity signals stay conservative.

Hard rules (both modes):
  1. You NEVER invent numbers. ``before_dp_ratio``, ``after_dp_ratio`` and \
``accuracy_delta_pp`` come from the classical tool — quote them exactly. \
When ``improved`` is false, ``after_dp_ratio`` equals ``before_dp_ratio``; \
do not round away that equality.
  2. ``summary`` is at most 3 short paragraphs; ombudsman-readable.
  3. Only emit valid JSON matching the RemediationPlan schema. No prose \
outside JSON, no markdown fences."""


def _build_user_prompt(outcome: RemediationOutcome) -> str:
    payload = {
        "audit_id": outcome.audit_id,
        "mitigation_name": (
            outcome.mitigation_name
            if outcome.improved
            else "none (original model retained)"
        ),
        "target_attribute": outcome.target_attribute,
        "target_column": outcome.target_column,
        "target_group_count": outcome.target_group_count,
        "before_dp_ratio": round(outcome.before_dp_ratio, 4),
        "after_dp_ratio": round(outcome.after_dp_ratio, 4),
        "baseline_accuracy": round(outcome.baseline_accuracy, 4),
        "remediated_accuracy": round(outcome.remediated_accuracy, 4),
        "accuracy_delta_pp": outcome.accuracy_delta_pp,
        "epsilon": outcome.epsilon,
        "n_train": outcome.n_train,
        "n_test": outcome.n_test,
        "improved": outcome.improved,
        "gate_reason": outcome.reason,
    }
    return (
        "Classical remediation tool output (authoritative; do not modify numbers):\n"
        f"{json.dumps(payload, indent=2, sort_keys=True, default=str)}\n\n"
        "Write the RemediationPlan JSON now. Respect the ``improved`` flag — "
        "use the IMPROVED=true path only when it is true; otherwise use the "
        "IMPROVED=false path and quote ``gate_reason`` in the summary. "
        "Restate before_dp_ratio, after_dp_ratio, and accuracy_delta_pp "
        "*exactly* as given above."
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

    # Hard invariants: the LLM never owns numbers, the audit_id, or the
    # improved verdict. Re-stamp from the classical tool's outcome so
    # hallucinations can't leak into the report.
    authoritative_name = (
        outcome.mitigation_name
        if outcome.improved
        else "none (original model retained)"
    )
    plan = plan.model_copy(
        update={
            "audit_id": outcome.audit_id,
            "mitigation_name": authoritative_name,
            "before_dp_ratio": max(0.0, min(1.0, float(outcome.before_dp_ratio))),
            "after_dp_ratio": max(0.0, min(1.0, float(outcome.after_dp_ratio))),
            "accuracy_delta_pp": max(-100.0, min(100.0, float(outcome.accuracy_delta_pp))),
            "target_attribute": outcome.target_attribute,
            "improved": outcome.improved,
            "target_group_count": outcome.target_group_count,
        }
    )
    return plan
