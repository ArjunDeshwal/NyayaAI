"""Tests for nyayai_taxonomy.schema."""

from __future__ import annotations

import pytest
from hypothesis import given
from hypothesis import strategies as st

from nyayai_taxonomy.schema import (
    DEFAULT_INTERSECTIONAL_SLICES,
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
    bin_age,
)


def test_caste_enum_has_all_required_members() -> None:
    assert {m.value for m in Caste} == {"GENERAL", "OBC", "SC", "ST", "NT_DNT", "UNKNOWN"}


def test_religion_has_seven_plus_unknown() -> None:
    # 7 religions + OTHER + NONE + UNKNOWN = 10
    assert len(list(Religion)) == 10
    names = {m.value for m in Religion}
    for required in ("HINDU", "MUSLIM", "CHRISTIAN", "SIKH", "BUDDHIST", "JAIN", "PARSI"):
        assert required in names


def test_gender_respects_transgender_act_2019() -> None:
    # THIRD must be a first-class value.
    assert Gender.THIRD.value == "THIRD"
    assert len(list(Gender)) == 4


def test_mother_tongue_covers_22_scheduled_plus_english_plus_extras() -> None:
    # 22 scheduled + ENG + OTHER + UNKNOWN = 25
    assert len(list(MotherTongue)) == 25


def test_region_covers_all_iso_3166_in_states() -> None:
    codes = {m.value for m in Region}
    # 28 states + 8 UTs + unknown = 37
    assert len(codes) == 37
    for code in codes - {"IN-UNKNOWN"}:
        assert code.startswith("IN-")


def test_protected_attribute_set_defaults_to_unknown() -> None:
    p = ProtectedAttributeSet()
    assert p.caste == Caste.UNKNOWN
    assert p.religion == Religion.UNKNOWN
    assert p.gender == Gender.UNKNOWN
    assert p.age_cohort == AgeCohort.UNKNOWN


def test_protected_attribute_set_slice_key_round_trip() -> None:
    p = ProtectedAttributeSet(
        caste=Caste.SC,
        religion=Religion.HINDU,
        gender=Gender.FEMALE,
        habitation=Habitation.RURAL,
        age_cohort=AgeCohort.AGE_26_45,
        disability=Disability.NONE,
        digital_literacy=DigitalLiteracy.DLQ1,
        mother_tongue=MotherTongue.HIN,
    )
    sk = p.as_slice_key()
    assert sk["caste"] == "SC"
    assert sk["gender"] == "FEMALE"
    assert sk["habitation"] == "RURAL"
    assert set(sk.keys()) == {
        "caste",
        "religion",
        "region_state",
        "habitation",
        "mother_tongue",
        "gender",
        "age_cohort",
        "disability",
        "digital_literacy",
    }


def test_default_slices_cover_high_risk_cases() -> None:
    slice_set = {tuple(s) for s in DEFAULT_INTERSECTIONAL_SLICES}
    # rural × female × caste
    assert ("habitation", "gender", "caste") in slice_set
    # mother_tongue × digital literacy
    assert ("mother_tongue", "digital_literacy") in slice_set


# ----- Property tests -----


@given(age=st.integers(min_value=0, max_value=150))
def test_bin_age_is_total_and_in_enum(age: int) -> None:
    result = bin_age(age)
    assert isinstance(result, AgeCohort)


@given(age=st.integers(min_value=-100, max_value=-1))
def test_bin_age_negative_is_unknown(age: int) -> None:
    assert bin_age(age) == AgeCohort.UNKNOWN


@given(age=st.integers(min_value=0, max_value=17))
def test_bin_age_children(age: int) -> None:
    assert bin_age(age) == AgeCohort.AGE_LT_18


@given(age=st.integers(min_value=61, max_value=150))
def test_bin_age_elderly(age: int) -> None:
    assert bin_age(age) == AgeCohort.AGE_GT_60


def test_protected_attribute_set_is_frozen() -> None:
    p = ProtectedAttributeSet()
    with pytest.raises(Exception):  # pydantic raises ValidationError on mutation
        p.caste = Caste.SC  # type: ignore[misc]


def test_protected_attribute_set_rejects_extras() -> None:
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        ProtectedAttributeSet(surprise="boom")  # type: ignore[call-arg]
