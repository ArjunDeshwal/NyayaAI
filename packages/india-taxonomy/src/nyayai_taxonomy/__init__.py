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
    "Disability",
    "DigitalLiteracy",
    "Gender",
    "Habitation",
    "MappingHit",
    "MotherTongue",
    "ProtectedAttributeSet",
    "Region",
    "Religion",
    "Script",
    "detect_script",
    "detect_surname_caste_proxy",
    "pin_to_district",
]
