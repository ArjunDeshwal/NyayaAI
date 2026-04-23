from __future__ import annotations

from typing import Literal

from nyayai_orchestrator.schemas import ProtectedAttribute
from pydantic import BaseModel, Field


class AuditSubmission(BaseModel):
    """Inline JSON body used with the /audit/by-uri endpoint.

    The /audit/upload endpoint accepts a multipart file upload instead.
    """

    dataset_name: str = Field(min_length=1, max_length=200)
    dataset_uri: str = Field(
        description="Path or gs:// URI to a parquet/CSV file readable by the API container.",
    )
    goal: str = Field(min_length=5, max_length=2000)
    regime: Literal["DPDP", "EU_AI_ACT", "RBI"] = "DPDP"
    model_id: str = "unknown"
    model_task: Literal["binary_classification", "multiclass", "regression", "ranking"] = (
        "binary_classification"
    )
    protected_columns: list[str]
    outcome_column: str
    model_score_column: str | None = None
    requested_attributes: list[ProtectedAttribute] = Field(default_factory=list)


class AuditResponse(BaseModel):
    audit_id: str
    status: Literal["completed", "failed"]
    overall_disparate_impact: float | None
    drift_level: Literal["none", "minor", "major"] | None
    report_json_url: str
    report_html_url: str
    report_pdf_url: str | None = None
