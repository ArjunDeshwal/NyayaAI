"""Tests for nyayai_taxonomy.proxies."""

from __future__ import annotations

from hypothesis import given
from hypothesis import strategies as st

from nyayai_taxonomy.proxies import (
    Script,
    detect_script,
    detect_surname_caste_proxy,
    pin_to_district,
)


def test_surname_proxy_known_general() -> None:
    assert detect_surname_caste_proxy("Sharma") > 0.7
    assert detect_surname_caste_proxy("SHARMA") > 0.7  # case invariant


def test_surname_proxy_known_sc() -> None:
    assert detect_surname_caste_proxy("Valmiki") > 0.7
    assert detect_surname_caste_proxy("Jatav") > 0.7


def test_surname_proxy_unknown_returns_zero() -> None:
    assert detect_surname_caste_proxy("ZzzQqq") == 0.0


def test_surname_proxy_empty_returns_zero() -> None:
    assert detect_surname_caste_proxy("") == 0.0


def test_surname_proxy_bounded() -> None:
    for name in ["Sharma", "Iyer", "Valmiki", "Santhal", "Banjara"]:
        v = detect_surname_caste_proxy(name)
        assert 0.0 <= v <= 0.92


@given(surname=st.text(alphabet=st.characters(min_codepoint=33, max_codepoint=126), min_size=0, max_size=30))
def test_surname_proxy_always_in_range(surname: str) -> None:
    v = detect_surname_caste_proxy(surname)
    assert 0.0 <= v <= 0.92


@given(surname=st.text(alphabet=st.characters(min_codepoint=33, max_codepoint=126), min_size=1, max_size=20))
def test_surname_proxy_case_invariant(surname: str) -> None:
    assert detect_surname_caste_proxy(surname) == detect_surname_caste_proxy(surname.upper())
    assert detect_surname_caste_proxy(surname) == detect_surname_caste_proxy(surname.lower())


def test_pin_to_district_valid() -> None:
    assert pin_to_district("110001") == "New Delhi"
    assert pin_to_district("400001") == "Mumbai"
    assert pin_to_district("560001") == "Bengaluru Urban"


def test_pin_to_district_malformed_returns_none() -> None:
    assert pin_to_district("abc") is None
    assert pin_to_district("12345") is None  # too short
    assert pin_to_district("1234567") is None  # too long
    assert pin_to_district(None) is None


def test_pin_to_district_accepts_int() -> None:
    assert pin_to_district(110001) == "New Delhi"


def test_pin_to_district_unknown_prefix() -> None:
    assert pin_to_district("999999") is None


@given(pin=st.integers(min_value=100000, max_value=999999))
def test_pin_to_district_never_raises(pin: int) -> None:
    result = pin_to_district(pin)
    assert result is None or isinstance(result, str)


def test_detect_script_devanagari() -> None:
    assert detect_script("नमस्ते दुनिया") == Script.DEVANAGARI


def test_detect_script_tamil() -> None:
    assert detect_script("வணக்கம் உலகம்") == Script.TAMIL


def test_detect_script_bengali() -> None:
    assert detect_script("নমস্কার বিশ্ব") == Script.BENGALI


def test_detect_script_latin() -> None:
    assert detect_script("Hello world") == Script.LATIN


def test_detect_script_mixed_is_mixed() -> None:
    # 50/50 Devanagari/Latin -> MIXED (neither >= 60%).
    assert detect_script("नमस्ते hello") == Script.MIXED


def test_detect_script_empty_is_unknown() -> None:
    assert detect_script("") == Script.UNKNOWN
    assert detect_script("   !!!  ") == Script.UNKNOWN


@given(text=st.text(max_size=200))
def test_detect_script_total(text: str) -> None:
    # Function must never raise, always returns a Script enum.
    result = detect_script(text)
    assert isinstance(result, Script)
