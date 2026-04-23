"""Pydantic schemas for the fairness service."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class AuditRequest(BaseModel):
    """Input to :func:`nyayai_fairness.audit.run_audit`."""

    model_config = ConfigDict(extra="forbid")

    dataset_uri: str = Field(..., description="Local path or s3/gs URI to parquet or CSV.")
    protected_columns: list[str] = Field(
        ...,
        description="Column names to treat as protected attributes.",
        min_length=1,
    )
    outcome_column: str = Field(..., description="Ground-truth binary column (0/1).")
    model_score_column: str | None = Field(
        default=None,
        description=(
            "Column containing the model's probability score. If omitted, the "
            "outcome column is used and selection-rate parity becomes trivially 1.0."
        ),
    )
    decision_threshold: float = Field(default=0.5, ge=0.0, le=1.0)
    intersectional_slices: list[list[str]] | None = Field(
        default=None,
        description=(
            "If None, uses the default India-context intersectional slices "
            "(habitation × gender × caste, etc.)."
        ),
    )
    min_slice_n: int = Field(default=1, ge=1)
    dp_k_anonymity: int = Field(
        default=100,
        ge=1,
        description="Slices below this n are marked DP-protected.",
    )
    seed: int = Field(default=42)

    @field_validator("protected_columns")
    @classmethod
    def _unique(cls, v: list[str]) -> list[str]:
        if len(set(v)) != len(v):
            raise ValueError("protected_columns must be unique")
        return v


class SliceReport(BaseModel):
    """Metrics for a single slice."""

    model_config = ConfigDict(extra="forbid")

    slice_key: dict[str, str]
    n: int
    metrics: dict[str, float]
    dp_protected: bool = False


class CustomIndiaMetrics(BaseModel):
    """SPLS / LRB / DLF results surfaced at the top of the report."""

    model_config = ConfigDict(extra="forbid")

    spls: dict[str, Any] | None = None
    dlf: dict[str, Any] | None = None
    lrb: dict[str, Any] | None = None


class AuditResult(BaseModel):
    """Deterministic output of a fairness audit."""

    model_config = ConfigDict(extra="forbid")

    audit_id: str
    computed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    dataset_uri: str
    protected_columns: list[str]
    outcome_column: str
    model_score_column: str | None
    decision_threshold: float
    n_rows: int

    global_metrics: dict[str, float]
    per_attribute_metrics: dict[str, dict[str, float]]
    slice_metrics: list[SliceReport]
    custom_india_metrics: CustomIndiaMetrics

    warnings: list[str] = Field(default_factory=list)
    determinism_hash: str = Field(
        ...,
        description="SHA-256 of the sorted metric dict; guards against accidental drift.",
    )
