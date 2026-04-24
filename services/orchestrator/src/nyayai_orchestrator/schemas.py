"""Pydantic contracts shared across NyayaAI orchestrator agents.

These are the *only* structured outputs the LLM agents are allowed to emit.
Schema parity with ``packages/contracts`` is enforced by tests; when the
contracts package stabilises we will re-export from there.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field, NonNegativeFloat, field_validator

# ---------------------------------------------------------------------------
# Input
# ---------------------------------------------------------------------------

ProtectedAttribute = Literal[
    "caste",
    "religion",
    "gender",
    "region",
    "urban_rural",
    "language",
    "disability",
    "age_band",
]

RegulatoryRegime = Literal["DPDP", "EU_AI_ACT", "RBI"]


class ModelCard(BaseModel):
    """Minimal model descriptor for the Planner."""

    model_id: str
    task: Literal["binary_classification", "multiclass", "regression", "ranking"]
    description: str = ""


class DatasetDescriptor(BaseModel):
    """Minimal dataset descriptor for the Planner (no PII, schema only).

    ``source_uri``/``outcome_column``/``model_score_column`` are populated when
    the fairness engine needs to actually read the dataset. They are never
    shown to the Planner LLM — only the column list and row count are.
    """

    name: str
    row_count: int = Field(ge=0)
    columns: list[str]
    candidate_protected_columns: list[str] = Field(default_factory=list)
    source_uri: str | None = None
    outcome_column: str | None = None
    model_score_column: str | None = None
    decision_threshold: float = Field(default=0.5, ge=0.0, le=1.0)


class AuditRequest(BaseModel):
    """Top-level input to the orchestrator."""

    audit_id: str
    goal: str = Field(min_length=5, max_length=2000)
    regime: RegulatoryRegime = "DPDP"
    model: ModelCard
    dataset: DatasetDescriptor
    requested_attributes: list[ProtectedAttribute] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Planner output
# ---------------------------------------------------------------------------


class AuditStep(BaseModel):
    """One unit of work the fairness engine will execute."""

    step_id: str
    kind: Literal["metric", "slice", "counterfactual_placeholder", "policy_check"]
    description: str
    target_attributes: list[ProtectedAttribute] = Field(default_factory=list)


class AuditPlan(BaseModel):
    """Planner agent output — the audit script."""

    audit_id: str
    steps: list[AuditStep] = Field(min_length=1, max_length=32)
    slices: list[list[ProtectedAttribute]] = Field(
        description="Each inner list is an intersectional slice, e.g. ['caste','gender'].",
        default_factory=list,
    )
    rationale: str = Field(min_length=10, max_length=2000)
    estimated_minutes: int = Field(ge=1, le=120)

    @field_validator("slices")
    @classmethod
    def _slices_non_empty_subsets(
        cls, v: list[list[ProtectedAttribute]]
    ) -> list[list[ProtectedAttribute]]:
        for s in v:
            if not s:
                raise ValueError("slice tuple must not be empty")
        return v


# ---------------------------------------------------------------------------
# Fairness-tool output (consumed by Narrator, Watcher)
# ---------------------------------------------------------------------------


class SliceMetric(BaseModel):
    """One fairness number for one slice."""

    slice_key: str  # e.g. "caste=SC", or "caste=SC,gender=F"
    metric: Literal[
        "demographic_parity_difference",
        "demographic_parity_ratio",
        "equal_opportunity_difference",
        "equalized_odds_difference",
        "disparate_impact",
        "subgroup_auc",
        "selection_rate",
    ]
    value: float
    ci_low: float | None = None
    ci_high: float | None = None
    sample_size: int = Field(ge=0)


class AuditResult(BaseModel):
    """Output of the classical fairness engine, consumed by the Narrator."""

    audit_id: str
    plan: AuditPlan
    metrics: list[SliceMetric]
    overall_disparate_impact: float | None = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ---------------------------------------------------------------------------
# Narrator output
# ---------------------------------------------------------------------------


class SliceParagraph(BaseModel):
    slice_key: str
    paragraph: str = Field(min_length=10, max_length=2000)


class Recommendation(BaseModel):
    title: str = Field(min_length=3, max_length=200)
    detail: str = Field(min_length=10, max_length=1000)
    severity: Literal["info", "advisory", "action_required"]


class ReportNarrative(BaseModel):
    audit_id: str
    summary: str = Field(min_length=20, max_length=3000)
    per_slice: list[SliceParagraph]
    recommendations: list[Recommendation] = Field(max_length=10)
    disclaimer: str = Field(
        default=(
            "This narrative is generated by Gemini 3 Flash for summarisation only. "
            "The authoritative fairness numbers live in the classical Fairness Metrics "
            "service. Recommendations are non-binding."
        )
    )


# ---------------------------------------------------------------------------
# Watcher output
# ---------------------------------------------------------------------------


class DriftFlag(BaseModel):
    audit_id: str
    level: Literal["none", "minor", "major"]
    reason: str = Field(min_length=5, max_length=500)
    triggering_metrics: list[str] = Field(default_factory=list)
    confidence: NonNegativeFloat = Field(ge=0.0, le=1.0, default=0.5)


# ---------------------------------------------------------------------------
# Remediation agent output
# ---------------------------------------------------------------------------


class RemediationPlan(BaseModel):
    """Plain-language summary + numerics for a post-audit mitigation pass.

    The authoritative numbers (``before_dp_ratio``, ``after_dp_ratio``,
    ``accuracy_delta_pp``) come from the classical remediation tool — the LLM
    never invents them. The LLM writes only ``summary``, ``risks`` and
    ``code_patch_summary``.
    """

    audit_id: str
    mitigation_name: str = Field(min_length=3, max_length=120)
    summary: str = Field(min_length=20, max_length=3000)
    before_dp_ratio: float = Field(ge=0.0, le=1.0)
    after_dp_ratio: float = Field(ge=0.0, le=1.0)
    # Percentage points. Negative = accuracy dropped; positive = improved.
    accuracy_delta_pp: float = Field(ge=-100.0, le=100.0)
    risks: list[str] = Field(default_factory=list, max_length=10)
    code_patch_summary: str = Field(min_length=10, max_length=2000)
    target_attribute: ProtectedAttribute | None = None
    disclaimer: str = Field(
        default=(
            "Remediation metrics are produced by a classical Fairlearn "
            "ExponentiatedGradient retrain on the audited dataset. The "
            "accompanying narrative is generated by Gemini 3 Flash and is "
            "non-binding advisory text; the authoritative numbers live in the "
            "classical Fairness Metrics service."
        )
    )


# ---------------------------------------------------------------------------
# Top-level assembled report
# ---------------------------------------------------------------------------


class AuditReport(BaseModel):
    request: AuditRequest
    plan: AuditPlan
    result: AuditResult
    narrative: ReportNarrative
    drift: DriftFlag
    remediation: RemediationPlan | None = None
    produced_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
