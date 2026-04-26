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
    train_baseline: bool = Field(
        default=False,
        description=(
            "When True, train an ephemeral LogisticRegression baseline on "
            "the dataset (excluding protected columns), use its predict_proba "
            "as the model_score, and run counterfactual + root-cause "
            "analyses against it. The trained model is never persisted, "
            "logged, or sent to the LLM. Used by /audit/sample where the "
            "user did not bring their own model_score."
        ),
    )

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
    """SPLS / LRB / DLF results surfaced at the top of the report.

    The legacy ``spls / dlf / lrb`` slots carry the *fairlearn-extensions*
    flavour metrics (surname-leakage, selection-rate-by-quartile,
    linguistic-register-shift). The newer RBI-aligned variants
    (``rbi_spls / rbi_lrb / rbi_dlf``) are populated when the dataset
    carries loan-amount / decision columns and the regime is RBI.
    """

    model_config = ConfigDict(extra="forbid")

    spls: dict[str, Any] | None = None
    dlf: dict[str, Any] | None = None
    lrb: dict[str, Any] | None = None
    rbi_spls: dict[str, Any] | None = None
    rbi_lrb: dict[str, Any] | None = None
    rbi_dlf: dict[str, Any] | None = None


class CounterfactualReport(BaseModel):
    """Counterfactual-flips report surfaced inside an :class:`AuditResult`."""

    model_config = ConfigDict(extra="forbid")

    protected_column: str
    protected_values: list[str]
    flip_rate_by_pair: dict[str, float]  # serialised as "g_before->g_after"
    directional_flip_rate: float = Field(ge=0.0, le=1.0)
    examples: list[dict[str, Any]] = Field(default_factory=list, max_length=5)
    sample_size_used: int = Field(ge=0)


class RootCauseReport(BaseModel):
    """Root-cause (permutation feature importance under DP-loss) report."""

    model_config = ConfigDict(extra="forbid")

    protected_column: str
    rankings: list[dict[str, Any]] = Field(default_factory=list, max_length=12)
    proxy_features: list[str] = Field(default_factory=list, max_length=10)
    baseline_dp_gap: float = Field(ge=0.0, le=1.0)
    baseline_accuracy: float | None = None
    proxy_threshold: float = Field(ge=0.0, le=1.0, default=0.05)
    n_repeats: int = Field(ge=0, default=0)


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

    # New optional extensions populated when ``train_baseline=True`` or
    # additional inputs are available. Default-None so existing callers
    # see no behaviour change.
    counterfactual: CounterfactualReport | None = None
    root_cause: RootCauseReport | None = None

    warnings: list[str] = Field(default_factory=list)
    determinism_hash: str = Field(
        ...,
        description="SHA-256 of the sorted metric dict; guards against accidental drift.",
    )
