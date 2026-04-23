"""API smoke tests.

Uses FastAPI's TestClient. The orchestrator runs with the stub LLM backend
(NYAYAI_LLM_BACKEND=stub, set by autouse fixture) so no GCP creds are needed.
"""

from __future__ import annotations

import os
from pathlib import Path

import pandas as pd
import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("NYAYAI_LLM_BACKEND", "stub")

from nyayai_api import create_app  # noqa: E402


@pytest.fixture()
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("NYAYAI_API_ARTIFACTS_DIR", str(tmp_path / "artifacts"))
    monkeypatch.setenv("NYAYAI_LLM_BACKEND", "stub")
    import nyayai_api.settings as _settings

    _settings._settings = None
    app = create_app()
    return TestClient(app)


@pytest.fixture()
def mudra_csv(tmp_path: Path) -> Path:
    """Tiny hand-built dataset with a known caste-gender disparity."""
    rng = range(200)
    rows = []
    for i in rng:
        caste = "SC" if i % 4 == 0 else ("ST" if i % 7 == 0 else "GENERAL")
        gender = "FEMALE" if i % 3 == 0 else "MALE"
        approved = (
            1 if (caste == "GENERAL" and gender == "MALE") else (1 if i % 5 == 0 else 0)
        )
        rows.append(
            {
                "applicant_id": f"a{i}",
                "income": 10000 + (i * 37) % 90000,
                "caste_disclosed": caste,
                "gender": gender,
                "approved": approved,
                "habitation": "urban" if i % 2 == 0 else "rural",
                "mother_tongue": "HIN",
                "typing_cadence_quartile": (i % 4) + 1,
            }
        )
    df = pd.DataFrame(rows)
    p = tmp_path / "mudra_tiny.csv"
    df.to_csv(p, index=False)
    return p


def test_health(client: TestClient) -> None:
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["service"] == "nyayai-api"


def test_audit_by_uri_end_to_end(client: TestClient, mudra_csv: Path) -> None:
    body = {
        "dataset_name": "mudra-tiny",
        "dataset_uri": str(mudra_csv),
        "goal": "Audit tiny MUDRA-like dataset for caste/gender disparity",
        "regime": "DPDP",
        "model_id": "test-lender-v0",
        "model_task": "binary_classification",
        "protected_columns": ["caste_disclosed", "gender"],
        "outcome_column": "approved",
        "model_score_column": None,
        "requested_attributes": ["caste", "gender"],
    }
    r = client.post("/audit/by-uri", json=body)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["status"] == "completed"
    assert data["audit_id"].startswith("audit_")
    # overall DI should exist and fail the 4/5ths rule on our biased fake data
    assert data["overall_disparate_impact"] is not None
    assert data["overall_disparate_impact"] < 0.8

    # Report files should be downloadable
    rj = client.get(f"/reports/{data['audit_id']}/json")
    assert rj.status_code == 200
    assert "audit_id" in rj.text
    rh = client.get(f"/reports/{data['audit_id']}/html")
    assert rh.status_code == 200
    assert "NyayaAI" in rh.text


def test_missing_column_400(client: TestClient, mudra_csv: Path) -> None:
    body = {
        "dataset_name": "x",
        "dataset_uri": str(mudra_csv),
        "goal": "check validation path",
        "protected_columns": ["caste_disclosed"],
        "outcome_column": "no_such_column",
    }
    r = client.post("/audit/by-uri", json=body)
    assert r.status_code == 400


def test_missing_file_404(client: TestClient) -> None:
    body = {
        "dataset_name": "x",
        "dataset_uri": "/nonexistent/path.csv",
        "goal": "check file not found path",
        "protected_columns": ["caste_disclosed"],
        "outcome_column": "approved",
    }
    r = client.post("/audit/by-uri", json=body)
    assert r.status_code == 404


def test_path_traversal_blocked(client: TestClient) -> None:
    r = client.get("/reports/..%2Fetc%2Fpasswd/json")
    assert r.status_code in (400, 404)
