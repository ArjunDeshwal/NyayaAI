"""Shared type contracts.

For the prototype we re-export from :mod:`nyayai_orchestrator.schemas`.
Finals milestone will move the canonical schemas here and regenerate
TypeScript + Dart bindings off this module.
"""

from nyayai_orchestrator.schemas import (
    AuditPlan,
    AuditReport,
    AuditRequest,
    AuditResult,
    AuditStep,
    CounterfactualExample,
    CounterfactualSummary,
    DatasetDescriptor,
    DLFResultModel,
    DriftFlag,
    FeatureContribution,
    IndiaMetricBundle,
    LRBResultModel,
    ModelCard,
    ProtectedAttribute,
    Recommendation,
    RegulatoryRegime,
    ReportNarrative,
    RootCauseSummary,
    SliceMetric,
    SliceParagraph,
    SPLSResultModel,
)

__all__ = [
    "AuditPlan",
    "AuditReport",
    "AuditRequest",
    "AuditResult",
    "AuditStep",
    "CounterfactualExample",
    "CounterfactualSummary",
    "DLFResultModel",
    "DatasetDescriptor",
    "DriftFlag",
    "FeatureContribution",
    "IndiaMetricBundle",
    "LRBResultModel",
    "ModelCard",
    "ProtectedAttribute",
    "Recommendation",
    "RegulatoryRegime",
    "ReportNarrative",
    "RootCauseSummary",
    "SPLSResultModel",
    "SliceMetric",
    "SliceParagraph",
]
