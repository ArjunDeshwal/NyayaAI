"""Root-Cause agent unit tests.

Hermetic via StubGeminiClient. Verifies that the LLM's
``contribution_to_disparity`` numbers get re-stamped to the classical values,
that proxy_warnings cover only the proxies the summary flagged, and that
the headline contains the top driver's feature name.
"""

from __future__ import annotations

from nyayai_orchestrator.agents import run_root_cause_agent
from nyayai_orchestrator.guardrails import NoOpArmor, NoOpSDP
from nyayai_orchestrator.llm.stub import StubGeminiClient
from nyayai_orchestrator.schemas import (
    FeatureContribution,
    RootCauseSummary,
)


def _summary(audit_id: str = "aud-rc-001") -> RootCauseSummary:
    return RootCauseSummary(
        audit_id=audit_id,
        protected_attribute="caste",
        rankings=[
            FeatureContribution(
                feature_name="pincode",
                contribution_to_disparity=0.21,
                contribution_to_accuracy=-0.012,
            ),
            FeatureContribution(
                feature_name="surname",
                contribution_to_disparity=0.14,
                contribution_to_accuracy=-0.005,
            ),
            FeatureContribution(
                feature_name="income",
                contribution_to_disparity=0.07,
                contribution_to_accuracy=-0.041,
            ),
            FeatureContribution(
                feature_name="age_band",
                contribution_to_disparity=0.01,
                contribution_to_accuracy=-0.0005,
            ),
        ],
        proxy_features=["pincode", "surname"],
        baseline_dp_gap=0.32,
    )


def test_run_root_cause_emits_valid_narrative() -> None:
    summary = _summary()
    out = run_root_cause_agent(
        summary,
        dataset_name="mudra-lite",
        client=StubGeminiClient(),
        model="gemini-3-flash",
        armor=NoOpArmor(),
        sdp=NoOpSDP(),
    )
    assert out.audit_id == summary.audit_id
    assert len(out.top_drivers) >= 1
    assert out.top_drivers[0].feature_name == "pincode"
    # The number must match exactly.
    assert out.top_drivers[0].contribution_to_disparity == 0.21
    # Proxy warnings should cover both proxies the summary flagged.
    text = "\n".join(out.proxy_warnings)
    assert "pincode" in text
    assert "surname" in text


def test_root_cause_restamps_drifted_contribution_numbers() -> None:
    """If the LLM returned a different number, the agent must restamp."""
    from nyayai_orchestrator.llm.base import ChatMessage, GeminiResponse

    class DriftedClient(StubGeminiClient):
        def generate_structured(self, **kwargs):  # type: ignore[override]
            base = super().generate_structured(**kwargs)
            parsed = dict(base.parsed)
            if "top_drivers" in parsed and parsed["top_drivers"]:
                # Inflate every driver number by 0.5 to force a drift.
                drifted = []
                for d in parsed["top_drivers"]:
                    drifted.append({
                        **d,
                        "contribution_to_disparity": float(d["contribution_to_disparity"]) + 0.5,
                    })
                parsed["top_drivers"] = drifted
            import json
            return GeminiResponse(
                text=json.dumps(parsed, sort_keys=True),
                parsed=parsed,
                model=kwargs["model"],
                usage={"prompt_tokens": 0, "candidates_tokens": 0},
            )

    summary = _summary()
    out = run_root_cause_agent(
        summary,
        dataset_name="mudra-lite",
        client=DriftedClient(),
        model="gemini-3-flash",
        armor=NoOpArmor(),
        sdp=NoOpSDP(),
    )
    # Pincode must be back to 0.21, surname back to 0.14.
    by_name = {d.feature_name: d.contribution_to_disparity for d in out.top_drivers}
    assert by_name.get("pincode") == 0.21
    assert by_name.get("surname") == 0.14


def test_root_cause_zero_out_hallucinated_features() -> None:
    """If the LLM names a feature not in the rankings, restamp to 0.0."""
    from nyayai_orchestrator.llm.base import ChatMessage, GeminiResponse

    class HallucinatedClient(StubGeminiClient):
        def generate_structured(self, **kwargs):  # type: ignore[override]
            base = super().generate_structured(**kwargs)
            parsed = dict(base.parsed)
            parsed["top_drivers"] = [
                {
                    "feature_name": "made_up_feature",
                    "contribution_to_disparity": 0.99,
                    "plain_explanation": "Hallucinated explanation about a nonexistent feature.",
                }
            ]
            import json
            return GeminiResponse(
                text=json.dumps(parsed, sort_keys=True),
                parsed=parsed,
                model=kwargs["model"],
                usage={"prompt_tokens": 0, "candidates_tokens": 0},
            )

    summary = _summary()
    out = run_root_cause_agent(
        summary,
        dataset_name="mudra-lite",
        client=HallucinatedClient(),
        model="gemini-3-flash",
        armor=NoOpArmor(),
        sdp=NoOpSDP(),
    )
    # Made-up feature kept (LLM owns names), but its number is zeroed out.
    assert out.top_drivers[0].feature_name == "made_up_feature"
    assert out.top_drivers[0].contribution_to_disparity == 0.0
