"""StubGeminiClient contract tests."""

from __future__ import annotations

from nyayai_orchestrator.llm.base import ChatMessage
from nyayai_orchestrator.llm.stub import StubGeminiClient


def test_stub_is_deterministic_for_same_prompt() -> None:
    client = StubGeminiClient()
    messages = [
        ChatMessage(role="system", content="be a planner"),
        ChatMessage(role="user", content='{"audit_id": "aud-x", "requested_attributes": ["caste", "gender"]}'),
    ]
    schema = {"title": "AuditPlan", "type": "object"}

    r1 = client.generate_structured(model="gemini-3.1-pro", messages=messages, response_schema=schema)
    r2 = client.generate_structured(model="gemini-3.1-pro", messages=messages, response_schema=schema)

    assert r1.parsed == r2.parsed
    assert r1.text == r2.text
    assert r1.parsed["audit_id"] == "aud-x"


def test_stub_routes_on_schema_title() -> None:
    client = StubGeminiClient()
    messages = [ChatMessage(role="user", content='{"audit_id":"aud-1"}')]

    plan = client.generate_structured(
        model="m", messages=messages, response_schema={"title": "AuditPlan"}
    ).parsed
    narrative = client.generate_structured(
        model="m", messages=messages, response_schema={"title": "ReportNarrative"}
    ).parsed
    drift = client.generate_structured(
        model="m", messages=messages, response_schema={"title": "DriftFlag"}
    ).parsed

    assert "steps" in plan and "slices" in plan
    assert "per_slice" in narrative and "recommendations" in narrative
    assert drift["level"] in ("none", "minor", "major")


def test_stub_unknown_schema_returns_fingerprint() -> None:
    client = StubGeminiClient()
    out = client.generate_structured(
        model="m",
        messages=[ChatMessage(role="user", content="hi")],
        response_schema={"title": "SomethingElse"},
    )
    assert out.parsed["_stub"] is True
    assert out.parsed["_schema_title"] == "SomethingElse"
