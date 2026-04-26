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


class CounterfactualExample(BaseModel):
    """One anonymised counterfactual flip for the Narrator's consumption.

    PII / candidate-protected columns must be redacted in
    ``feature_snapshot``; the counterfactual tool enforces this.
    """

    row_index: int
    protected_value_before: str
    protected_value_after: str
    probability_before: float = Field(ge=0.0, le=1.0)
    probability_after: float = Field(ge=0.0, le=1.0)
    decision_before: int
    decision_after: int
    feature_snapshot: dict[str, str]


class CounterfactualSummary(BaseModel):
    """Top-level counterfactual-flips report attached to one audit."""

    audit_id: str
    protected_attribute: ProtectedAttribute
    directional_flip_rate: float = Field(ge=0.0, le=1.0)
    flip_rate_by_pair: dict[str, float]  # serialised as "SC->GENERAL"
    examples: list[CounterfactualExample] = Field(default_factory=list, max_length=5)
    sample_size_used: int = Field(ge=0)


class FeatureContribution(BaseModel):
    """One feature's contribution to disparity and accuracy.

    ``contribution_to_disparity`` is ``baseline_dp_gap - permuted_dp_gap``;
    *positive* means the feature is *causing* the gap (permuting it shrinks
    the gap), *negative* means the feature is masking the gap.
    """

    feature_name: str
    contribution_to_disparity: float
    contribution_to_accuracy: float


class RootCauseSummary(BaseModel):
    """Top-level root-cause report attached to one audit."""

    audit_id: str
    protected_attribute: ProtectedAttribute
    rankings: list[FeatureContribution] = Field(default_factory=list, max_length=12)
    proxy_features: list[str] = Field(default_factory=list, max_length=10)
    baseline_dp_gap: float = Field(ge=0.0, le=1.0)


class SPLSResultModel(BaseModel):
    """Sub-Plan Lending Shortfall (SPLS) result.

    Source: RBI Master Directions on Priority Sector Lending, 04-Sep-2020,
    FIDD.CO.Plan.BC.5/04.09.01/2020-21 (and 2024-04 FAQ).
    """

    actual_pct_by_group: dict[str, float]
    target_pct_by_group: dict[str, float]
    shortfall_pct_by_group: dict[str, float]
    total_shortfall_amount: float
    worst_group: str | None = None
    grand_total: float = Field(ge=0.0)


class LRBResultModel(BaseModel):
    """Loan Rejection Bias result.

    Source: RBI Digital Lending Directions, 02-Sep-2022,
    DOR.CRE.REC.66/21.07.001/2022-23 §8.
    """

    rejection_rate_by_group: dict[str, float]
    rejection_rate_ratio: float = Field(ge=0.0, le=1.0)
    rejection_rate_disparity: float = Field(ge=0.0, le=1.0)
    n_by_group: dict[str, int]
    rbi_advisory_breach: bool
    worst_group: str | None = None
    threshold: float = Field(ge=0.0, le=1.0, default=0.80)


class DLFResultModel(BaseModel):
    """Digital Lending Fairness composite (RBIH-FLF v1, 2024).

    Composite weights default to ``{disparate_impact: 0.5,
    equal_opportunity: 0.3, calibration: 0.2}``.
    """

    score: float = Field(ge=0.0, le=1.0)
    disparate_impact: float = Field(ge=0.0, le=1.0)
    equal_opportunity: float = Field(ge=0.0, le=1.0)
    calibration_within_groups: float = Field(ge=0.0, le=1.0)
    weights: dict[str, float] = Field(default_factory=dict)
    components: dict[str, float] = Field(default_factory=dict)


class IndiaMetricBundle(BaseModel):
    """Bundle of India-specific metrics surfaced at the top of the report."""

    audit_id: str
    spls: SPLSResultModel | None = None
    lrb: LRBResultModel | None = None
    dlf: DLFResultModel | None = None


class AuditResult(BaseModel):
    """Output of the classical fairness engine, consumed by the Narrator."""

    audit_id: str
    plan: AuditPlan
    metrics: list[SliceMetric]
    overall_disparate_impact: float | None = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    # Optional extensions — None on simple uploads, populated when
    # ``train_baseline=True`` runs (e.g. /audit/sample). Defaults preserve
    # backwards compatibility with all existing tests / callers.
    counterfactual: CounterfactualSummary | None = None
    root_cause: RootCauseSummary | None = None
    intersectional: list[SliceMetric] = Field(default_factory=list)
    india_metrics: IndiaMetricBundle | None = None


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
    summary_hi: str | None = Field(
        default=None,
        max_length=3000,
        description=(
            "Hindi (Devanagari) translation of ``summary``. The Narrator emits "
            "this in the same call so the Flutter UI can render a one-click "
            "EN / HI toggle on the result card with no second round-trip."
        ),
    )
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
# Counterfactual narrator output
# ---------------------------------------------------------------------------


class CounterfactualNarrative(BaseModel):
    """Plain-language interpretation of a :class:`CounterfactualSummary`.

    The flip math is owned by the classical
    :func:`compute_counterfactual_flips` routine in
    ``packages/fairlearn-extensions``. This narrative restates the numbers
    and adds India-context interpretation; it never invents flip rates.
    """

    audit_id: str
    headline: str = Field(min_length=10, max_length=300)
    interpretation: str = Field(min_length=20, max_length=2000)
    severity: Literal["info", "advisory", "action_required"]
    example_takeaways: list[str] = Field(default_factory=list, max_length=5)
    disclaimer: str = Field(
        default=(
            "Counterfactual flip rates are computed by the classical Fairness "
            "Metrics service. The interpretation is generated by Gemini 3 Flash "
            "and is non-binding advisory text."
        )
    )


# ---------------------------------------------------------------------------
# Root-cause narrator output
# ---------------------------------------------------------------------------


class FeatureExplanation(BaseModel):
    """One feature's plain-language root-cause line.

    ``contribution_to_disparity`` is restated verbatim from the classical
    permutation-importance computation; the LLM only writes
    ``plain_explanation``.
    """

    feature_name: str
    contribution_to_disparity: float
    plain_explanation: str = Field(min_length=10, max_length=400)


class RootCauseNarrative(BaseModel):
    """Plain-language interpretation of a :class:`RootCauseSummary`."""

    audit_id: str
    headline: str = Field(min_length=10, max_length=300)
    top_drivers: list[FeatureExplanation] = Field(min_length=1, max_length=5)
    proxy_warnings: list[str] = Field(default_factory=list, max_length=8)
    suggested_actions: list[str] = Field(default_factory=list, max_length=5)
    disclaimer: str = Field(
        default=(
            "Feature contributions are computed via permutation feature "
            "importance against the demographic-parity gap. Plain-language "
            "explanations are generated by Gemini 3 Flash and are non-binding "
            "advisory text."
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

    ``improved`` is the ground-truth verdict of the classical keep-or-discard
    gate: when False, the narrator must not claim improvement and the
    accompanying numbers reflect the original (un-mitigated) model.
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
    # True iff the classical gate accepted the mitigation (meaningful DP lift
    # without tanking accuracy). When False, the original model is retained
    # and ``after_dp_ratio`` is stamped equal to ``before_dp_ratio``.
    improved: bool = False
    # Group cardinality of the target attribute the tool evaluated (helps the
    # narrator explain why a high-cardinality target was skipped).
    target_group_count: int | None = Field(default=None, ge=0)
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
    counterfactual_narrative: CounterfactualNarrative | None = None
    root_cause_narrative: RootCauseNarrative | None = None
    produced_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
