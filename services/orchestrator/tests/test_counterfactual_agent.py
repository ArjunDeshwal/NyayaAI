"""Counterfactual agent unit tests.

Uses the StubGeminiClient so tests are hermetic. The flip math itself lives
in ``packages/fairlearn-extensions`` and has its own tests; here we only
exercise the LLM narrator wrapper around it: severity classification,
re-stamping invariants, schema validation.
"""

from __future__ import annotations

import pytest

from nyayai_orchestrator.agents import run_counterfactual_agent
from nyayai_orchestrator.agents.counterfactual import _classify_severity
from nyayai_orchestrator.guardrails import NoOpArmor, NoOpSDP
from nyayai_orchestrator.llm.stub import StubGeminiClient
from nyayai_orchestrator.schemas import (
    CounterfactualExample,
    CounterfactualSummary,
)


def _summary(rate: float, audit_id: str = "aud-cf-001") -> CounterfactualSummary:
    return CounterfactualSummary(
        audit_id=audit_id,
        protected_attribute="caste",
        directional_flip_rate=rate,
        flip_rate_by_pair={"SC->GENERAL": rate, "ST->GENERAL": rate * 0.8},
        examples=[
            CounterfactualExample(
                row_index=42,
                protected_value_before="SC",
                protected_value_after="GENERAL",
                probability_before=0.31,
                probability_after=0.62,
                decision_before=0,
                decision_after=1,
                feature_snapshot={"income": "35000", "city_tier": "tier-2"},
            ),
            CounterfactualExample(
                row_index=77,
                protected_value_before="ST",
                protected_value_after="GENERAL",
                probability_before=0.28,
                probability_after=0.55,
                decision_before=0,
                decision_after=1,
                feature_snapshot={"income": "22000", "city_tier": "tier-3"},
            ),
        ],
        sample_size_used=200,
    )


@pytest.mark.parametrize(
    "rate,expected",
    [
        (0.0, "info"),
        (0.04, "info"),
        (0.05, "advisory"),
        (0.149, "advisory"),
        (0.15, "action_required"),
        (0.42, "action_required"),
    ],
)
def test_severity_classification(rate: float, expected: str) -> None:
    assert _classify_severity(rate) == expected


def test_run_counterfactual_emits_valid_narrative() -> None:
    summary = _summary(0.18)
    out = run_counterfactual_agent(
        summary,
        client=StubGeminiClient(),
        model="gemini-3-flash",
        armor=NoOpArmor(),
        sdp=NoOpSDP(),
    )
    assert out.audit_id == summary.audit_id
    assert out.severity == "action_required"
    assert "18.0%" in out.headline or "18" in out.headline
    assert len(out.interpretation) >= 20
    # Examples in the prompt have decision_before=0, decision_after=1 → both
    # are "approved" flips and should yield non-empty takeaways.
    assert len(out.example_takeaways) >= 1


def test_run_counterfactual_low_rate_classified_info() -> None:
    summary = _summary(0.02)
    out = run_counterfactual_agent(
        summary,
        client=StubGeminiClient(),
        model="gemini-3-flash",
        armor=NoOpArmor(),
        sdp=NoOpSDP(),
    )
    assert out.severity == "info"
    # Restamping invariant: severity is forced to classical answer regardless
    # of LLM drift.


def test_severity_restamped_even_if_llm_returns_wrong() -> None:
    """If a future stub or model returned the wrong severity, the agent must
    re-stamp it from the classical classifier."""
    from nyayai_orchestrator.llm.base import ChatMessage, GeminiResponse

    class WrongSeverityClient(StubGeminiClient):
        def generate_structured(self, **kwargs):  # type: ignore[override]
            base = super().generate_structured(**kwargs)
            parsed = dict(base.parsed)
            # Force the wrong severity.
            parsed["severity"] = "info"
            import json
            return GeminiResponse(
                text=json.dumps(parsed, sort_keys=True),
                parsed=parsed,
                model=kwargs["model"],
                usage={"prompt_tokens": 0, "candidates_tokens": 0},
            )

    summary = _summary(0.40)  # action_required by classical rule
    out = run_counterfactual_agent(
        summary,
        client=WrongSeverityClient(),
        model="gemini-3-flash",
        armor=NoOpArmor(),
        sdp=NoOpSDP(),
    )
    assert out.severity == "action_required"
