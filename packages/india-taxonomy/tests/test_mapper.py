"""Tests for nyayai_taxonomy.mapper."""

from __future__ import annotations

import pytest
from hypothesis import given
from hypothesis import strategies as st

from nyayai_taxonomy.mapper import CANONICAL_ATTRS, ColumnMapper


@pytest.fixture
def mapper() -> ColumnMapper:
    return ColumnMapper()


def test_exact_english_names(mapper: ColumnMapper) -> None:
    assert mapper.map_column("caste").canonical_attr == "caste"
    assert mapper.map_column("gender").canonical_attr == "gender"
    assert mapper.map_column("religion").canonical_attr == "religion"


def test_hindi_and_transliterated_synonyms(mapper: ColumnMapper) -> None:
    assert mapper.map_column("jati").canonical_attr == "caste"
    assert mapper.map_column("dharma").canonical_attr == "religion"
    assert mapper.map_column("matrubhasha").canonical_attr == "mother_tongue"
    assert mapper.map_column("ling").canonical_attr == "gender"


def test_devanagari_synonyms(mapper: ColumnMapper) -> None:
    assert mapper.map_column("जाति").canonical_attr == "caste"
    assert mapper.map_column("धर्म").canonical_attr == "religion"


def test_case_and_separator_insensitive(mapper: ColumnMapper) -> None:
    assert mapper.map_column("Caste_Category").canonical_attr == "caste"
    assert mapper.map_column("SOCIAL CATEGORY").canonical_attr == "caste"
    assert mapper.map_column("mother-tongue").canonical_attr == "mother_tongue"


def test_unknown_column_returns_none(mapper: ColumnMapper) -> None:
    hit = mapper.map_column("applicant_id")
    assert hit.canonical_attr is None


def test_fuzzy_match_typo(mapper: ColumnMapper) -> None:
    hit = mapper.map_column("gendre")  # typo
    assert hit.canonical_attr == "gender"
    assert hit.match_kind == "fuzzy"


def test_map_columns_batch(mapper: ColumnMapper) -> None:
    res = mapper.map_columns(["jati", "dharma", "applicant_id", "age"])
    assert res["jati"].canonical_attr == "caste"
    assert res["dharma"].canonical_attr == "religion"
    assert res["applicant_id"].canonical_attr is None
    assert res["age"].canonical_attr == "age_cohort"


def test_confidence_range_exact(mapper: ColumnMapper) -> None:
    hit = mapper.map_column("caste")
    assert hit.confidence == 1.0
    assert hit.match_kind == "exact"


def test_threshold_validation() -> None:
    with pytest.raises(ValueError):
        ColumnMapper(fuzzy_threshold=1.5)
    with pytest.raises(ValueError):
        ColumnMapper(fuzzy_threshold=-0.1)


@given(src=st.text(max_size=40))
def test_mapper_never_raises(src: str) -> None:
    hit = ColumnMapper().map_column(src)
    assert hit.canonical_attr is None or hit.canonical_attr in CANONICAL_ATTRS
    assert 0.0 <= hit.confidence <= 1.0


@given(
    src=st.sampled_from(
        [
            "caste",
            "religion",
            "gender",
            "age",
            "mother_tongue",
            "region_state",
            "habitation",
            "disability",
            "digital_literacy",
        ]
    )
)
def test_exact_canonical_always_matches(src: str) -> None:
    hit = ColumnMapper().map_column(src)
    assert hit.canonical_attr is not None
    assert hit.confidence == 1.0
