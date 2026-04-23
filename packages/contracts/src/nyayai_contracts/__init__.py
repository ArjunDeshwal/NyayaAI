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
    DatasetDescriptor,
    DriftFlag,
    ModelCard,
    ProtectedAttribute,
    Recommendation,
    RegulatoryRegime,
    ReportNarrative,
    SliceMetric,
    SliceParagraph,
)

__all__ = [
    "AuditPlan",
    "AuditReport",
    "AuditRequest",
    "AuditResult",
    "AuditStep",
    "DatasetDescriptor",
    "DriftFlag",
    "ModelCard",
    "ProtectedAttribute",
    "Recommendation",
    "RegulatoryRegime",
    "ReportNarrative",
    "SliceMetric",
    "SliceParagraph",
]
