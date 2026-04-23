"""Column-name mapper.

Takes arbitrary column names from user-supplied datasets and maps them to the
canonical enum *names* declared in :mod:`nyayai_taxonomy.schema`.

Strategy:

1. Exact match against a handcrafted dictionary of synonyms in English,
   Hindi/Devanagari, and common transliterations (``jati -> caste``,
   ``dharma -> religion``, ...).
2. Fuzzy match (RapidFuzz) against the canonical attribute names.

The mapper returns confidence in ``[0.0, 1.0]`` so callers can gate on a
threshold (default 0.80) and emit a warning for borderline matches rather
than silently mis-mapping a column.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from rapidfuzz import fuzz

# Canonical attribute names that downstream code understands.
CANONICAL_ATTRS: tuple[str, ...] = (
    "caste",
    "religion",
    "region_state",
    "habitation",
    "mother_tongue",
    "gender",
    "age_cohort",
    "disability",
    "digital_literacy",
)

# Handcrafted synonym dictionary. Keys are the *canonical* names; values are
# lowercased synonym terms we expect to see in real-world Indian datasets.
_SYNONYMS: dict[str, tuple[str, ...]] = {
    "caste": (
        "caste",
        "jati",
        "jaati",
        "varna",
        "caste_category",
        "caste_group",
        "social_category",
        "community",
        "category",
        "jati_group",
        "जाति",
    ),
    "religion": (
        "religion",
        "dharma",
        "mazhab",
        "faith",
        "religious_affiliation",
        "धर्म",
    ),
    "region_state": (
        "state",
        "state_code",
        "pradesh",
        "rajya",
        "state_name",
        "region",
        "iso_state",
        "राज्य",
    ),
    "habitation": (
        "habitation",
        "rural_urban",
        "urbanisation",
        "urbanization",
        "urban_rural",
        "area_type",
        "settlement",
        "rural_or_urban",
    ),
    "mother_tongue": (
        "mother_tongue",
        "mothertongue",
        "primary_language",
        "native_language",
        "matrubhasha",
        "language",
        "lang",
        "मातृभाषा",
    ),
    "gender": (
        "gender",
        "sex",
        "ling",
        "linga",
        "gender_identity",
        "लिंग",
    ),
    "age_cohort": (
        "age",
        "age_bucket",
        "age_band",
        "age_group",
        "age_cohort",
        "umra",
        "umar",
        "आयु",
    ),
    "disability": (
        "disability",
        "divyang",
        "divyangjan",
        "pwd",
        "impairment",
        "disability_type",
        "रूप से विकलांग",
    ),
    "digital_literacy": (
        "digital_literacy",
        "dl_quartile",
        "typing_cadence_quartile",
        "computer_literacy",
        "tech_literacy",
        "device_literacy",
    ),
}


def _normalize(name: str) -> str:
    # Lowercase, collapse separators, strip whitespace.
    s = name.strip().lower()
    s = re.sub(r"[\s\-./]+", "_", s)
    s = re.sub(r"[^a-z0-9_ऀ-෿]", "", s)  # keep Indic scripts
    return s


@dataclass(frozen=True)
class MappingHit:
    """Result of mapping one user column to a canonical attribute."""

    source_column: str
    canonical_attr: str | None
    confidence: float  # 0.0 .. 1.0
    match_kind: str  # "exact" | "fuzzy" | "none"


class ColumnMapper:
    """Map user-supplied column names to canonical protected-attribute names.

    Parameters
    ----------
    fuzzy_threshold:
        Confidence floor for a fuzzy match to be returned. Default ``0.80``.
    """

    def __init__(self, fuzzy_threshold: float = 0.80) -> None:
        if not 0.0 <= fuzzy_threshold <= 1.0:
            raise ValueError("fuzzy_threshold must be in [0, 1]")
        self.fuzzy_threshold = fuzzy_threshold
        # Invert the synonym dict for exact lookup.
        self._exact: dict[str, str] = {}
        for canonical, synonyms in _SYNONYMS.items():
            for syn in synonyms:
                self._exact[_normalize(syn)] = canonical
            # The canonical name itself is always a hit.
            self._exact[_normalize(canonical)] = canonical

    def map_column(self, source: str) -> MappingHit:
        """Map a single column name."""

        norm = _normalize(source)
        if not norm:
            return MappingHit(source, None, 0.0, "none")
        if norm in self._exact:
            return MappingHit(source, self._exact[norm], 1.0, "exact")
        # Fuzzy fallback: score against every synonym, take best.
        best_attr: str | None = None
        best_score = 0.0
        for canonical, synonyms in _SYNONYMS.items():
            for syn in synonyms:
                ratio = fuzz.token_set_ratio(norm, _normalize(syn)) / 100.0
                if ratio > best_score:
                    best_score = ratio
                    best_attr = canonical
        if best_attr is not None and best_score >= self.fuzzy_threshold:
            return MappingHit(source, best_attr, best_score, "fuzzy")
        return MappingHit(source, None, best_score, "none")

    def map_columns(self, sources: list[str]) -> dict[str, MappingHit]:
        """Map a list of columns; returns ``{source: MappingHit}``."""

        return {c: self.map_column(c) for c in sources}
