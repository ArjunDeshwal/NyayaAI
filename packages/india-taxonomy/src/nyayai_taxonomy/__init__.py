"""NyayaAI India-context protected-attribute taxonomy.

This package is the *single source of truth* for India-specific protected
attributes used throughout the NyayaAI fairness stack. Every protected-attribute
column in any dataset must be mapped to one of the enums in :mod:`schema`
before metric computation.

See ``.claude/skills/nyayai-india-taxonomy/SKILL.md`` for the canonical spec.
"""

from nyayai_taxonomy.mapper import ColumnMapper, MappingHit
from nyayai_taxonomy.proxies import (
    Script,
    detect_script,
    detect_surname_caste_proxy,
    pin_to_district,
)
from nyayai_taxonomy.rbi_metrics import (
    RBI_DLF_WEIGHTS,
    RBI_LRB_4_5THS_THRESHOLD,
    RBI_PSL_DEFAULT_TARGETS,
    DLFResult,
    LRBResult,
    SPLSResult,
    compute_dlf,
    compute_lrb,
    compute_spls,
)
from nyayai_taxonomy.schema import (
    AgeCohort,
    Caste,
    Disability,
    DigitalLiteracy,
    Gender,
    Habitation,
    MotherTongue,
    ProtectedAttributeSet,
    Region,
    Religion,
)

__all__ = [
    "AgeCohort",
    "Caste",
    "ColumnMapper",
    "DLFResult",
    "Disability",
    "DigitalLiteracy",
    "Gender",
    "Habitation",
    "LRBResult",
    "MappingHit",
    "MotherTongue",
    "ProtectedAttributeSet",
    "RBI_DLF_WEIGHTS",
    "RBI_LRB_4_5THS_THRESHOLD",
    "RBI_PSL_DEFAULT_TARGETS",
    "Region",
    "Religion",
    "SPLSResult",
    "Script",
    "compute_dlf",
    "compute_lrb",
    "compute_spls",
    "detect_script",
    "detect_surname_caste_proxy",
    "pin_to_district",
]
