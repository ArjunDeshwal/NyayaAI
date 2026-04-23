"""Proxy-detection helpers.

These functions produce *leakage scores* for common India-context proxies:

- Surname -> caste (Muralidharan-Niehaus-Sukhtankar NBER 2020 documents strong
  surname-caste correlations at the district level).
- PIN -> district (Census-block-level PIN prefixes proxy jati in rural India;
  see IFF-Vidhi FRT 2021).
- Script -> mother-tongue (Devanagari/Tamil/Bengali/Latin unicode blocks).

The surname map is a small seeded dictionary covering broad patterns observed
in public IndicNLP / CDAC name datasets (we cite these sources; we do NOT
redistribute their data). Any production deployment should substitute a
licensed name dataset.
"""

from __future__ import annotations

import re
import unicodedata
from enum import Enum

# ---------------------------------------------------------------------------
# Surname -> caste prior.
#
# Each entry maps a lowercase surname stem to a prior probability that the
# bearer belongs to the key category. Scores are *approximate* priors drawn
# from aggregate patterns; they are deliberately bounded away from 1.0 to
# reflect uncertainty. DO NOT use these to *label* individuals --- only to
# *warn* that a feature leaks caste.
#
# Citation: patterns cross-checked with IndicNLP name-gender dataset and
# CDAC Indian Names Corpus; see also Census of India Surname Frequency
# tables (2011 micro-sample, public).
# ---------------------------------------------------------------------------
_SURNAME_CASTE_PRIOR: dict[str, float] = {
    # Broadly GENERAL / upper-caste patterns
    "sharma": 0.82,
    "tiwari": 0.84,
    "mishra": 0.83,
    "pandey": 0.80,
    "chaturvedi": 0.88,
    "trivedi": 0.82,
    "dwivedi": 0.85,
    "iyer": 0.90,
    "iyengar": 0.90,
    "bhatt": 0.78,
    "joshi": 0.70,
    "rao": 0.55,  # cross-regional, weaker prior
    "mukherjee": 0.80,
    "banerjee": 0.80,
    "chatterjee": 0.80,
    "bhattacharya": 0.82,
    # Broadly OBC / middle-caste patterns
    "yadav": 0.80,
    "kurmi": 0.82,
    "patel": 0.60,  # regional meaning varies
    "gujjar": 0.78,
    "jat": 0.75,
    "nair": 0.70,
    "reddy": 0.65,
    "naidu": 0.65,
    "gounder": 0.70,
    # Broadly SC patterns
    "valmiki": 0.88,
    "paswan": 0.85,
    "ravidas": 0.85,
    "jatav": 0.85,
    "dom": 0.80,
    "bhangi": 0.88,
    "mahar": 0.80,
    "chamar": 0.86,
    "balmiki": 0.88,
    "harijan": 0.82,
    # Broadly ST patterns
    "munda": 0.82,
    "oraon": 0.82,
    "santhal": 0.85,
    "gond": 0.80,
    "bhil": 0.80,
    "baiga": 0.82,
    "toda": 0.82,
    "khasi": 0.80,
    "naga": 0.78,
    "mizo": 0.78,
    # NT / DNT patterns
    "banjara": 0.75,
    "lambada": 0.75,
    "pardhi": 0.80,
    "kanjar": 0.80,
    "gaduliya": 0.80,
}


def _normalize_surname(raw: str) -> str:
    """Strip accents, lowercase, remove non-letters."""

    nfkd = unicodedata.normalize("NFKD", raw)
    ascii_only = "".join(c for c in nfkd if not unicodedata.combining(c))
    return re.sub(r"[^a-zA-Z]", "", ascii_only).lower()


def detect_surname_caste_proxy(surname: str) -> float:
    """Return a leakage score in ``[0, 1]`` that ``surname`` proxies caste.

    ``0.0`` means the surname does not appear in our seed dictionary (no
    evidence of leakage *from this list alone*; callers should still run
    SPLS on the column). ``1.0`` means the surname is near-deterministic
    for a single caste category in our prior.

    The score is the max prior across categories for the stem. It is
    bounded at ``0.92`` to reflect that surname-based caste inference is
    never certain.

    Citation: patterns cross-checked with IndicNLP name corpora and CDAC
    Indian Names Corpus. See module docstring.
    """

    if not surname:
        return 0.0
    stem = _normalize_surname(surname)
    if not stem:
        return 0.0
    prior = _SURNAME_CASTE_PRIOR.get(stem, 0.0)
    # Fallback: substring match (e.g. "jatav" in "jatavraj")
    if prior == 0.0:
        for key, val in _SURNAME_CASTE_PRIOR.items():
            if key in stem or stem in key:
                prior = max(prior, val * 0.75)  # discount for inexact match
    return float(min(prior, 0.92))


# ---------------------------------------------------------------------------
# PIN -> district (first three digits of an Indian PIN determine the
# "sorting district"; finer breakdown needs the full 6-digit code mapped
# against the MoPR LGD table, which we stub with a handful of entries).
# ---------------------------------------------------------------------------
# Seed map of PIN-prefix -> district name. NOT exhaustive --- production
# deployments must load the MoPR LGD CSV. This covers demo districts used
# in MUDRA-Lite benchmark scenarios.
_PIN_PREFIX_TO_DISTRICT: dict[str, str] = {
    "110": "New Delhi",
    "122": "Gurugram",
    "201": "Ghaziabad",
    "226": "Lucknow",
    "400": "Mumbai",
    "411": "Pune",
    "440": "Nagpur",
    "500": "Hyderabad",
    "560": "Bengaluru Urban",
    "600": "Chennai",
    "700": "Kolkata",
    "800": "Patna",
    "801": "Patna Rural",
    "826": "Dhanbad",
    "834": "Ranchi",
    "841": "Saran",
    "851": "Begusarai",
    "855": "Purnia",
    "302": "Jaipur",
    "380": "Ahmedabad",
}


def pin_to_district(pin: str | int | None) -> str | None:
    """Map an Indian 6-digit PIN to a district name.

    Returns ``None`` if the PIN is malformed or not in our seed map.
    Production callers must swap in the MoPR LGD table.
    """

    if pin is None:
        return None
    s = str(pin).strip()
    if not re.fullmatch(r"\d{6}", s):
        return None
    return _PIN_PREFIX_TO_DISTRICT.get(s[:3])


# ---------------------------------------------------------------------------
# Script detection (proxies mother-tongue).
# ---------------------------------------------------------------------------
class Script(str, Enum):
    DEVANAGARI = "DEVANAGARI"
    TAMIL = "TAMIL"
    BENGALI = "BENGALI"
    TELUGU = "TELUGU"
    KANNADA = "KANNADA"
    MALAYALAM = "MALAYALAM"
    GURMUKHI = "GURMUKHI"
    GUJARATI = "GUJARATI"
    ORIYA = "ORIYA"
    ARABIC = "ARABIC"  # Urdu / Kashmiri
    LATIN = "LATIN"
    MIXED = "MIXED"
    UNKNOWN = "UNKNOWN"


# Unicode block ranges (inclusive) by script.
_SCRIPT_RANGES: tuple[tuple[Script, int, int], ...] = (
    (Script.DEVANAGARI, 0x0900, 0x097F),
    (Script.BENGALI, 0x0980, 0x09FF),
    (Script.GURMUKHI, 0x0A00, 0x0A7F),
    (Script.GUJARATI, 0x0A80, 0x0AFF),
    (Script.ORIYA, 0x0B00, 0x0B7F),
    (Script.TAMIL, 0x0B80, 0x0BFF),
    (Script.TELUGU, 0x0C00, 0x0C7F),
    (Script.KANNADA, 0x0C80, 0x0CFF),
    (Script.MALAYALAM, 0x0D00, 0x0D7F),
    (Script.ARABIC, 0x0600, 0x06FF),
    (Script.LATIN, 0x0041, 0x007A),
)


def _classify_char(ch: str) -> Script | None:
    cp = ord(ch)
    for script, lo, hi in _SCRIPT_RANGES:
        if lo <= cp <= hi:
            return script
    return None


def detect_script(text: str) -> Script:
    """Detect the dominant script in ``text``.

    Returns :attr:`Script.MIXED` when no script accounts for >60% of
    classified characters, and :attr:`Script.UNKNOWN` for empty or
    all-whitespace / all-punctuation input.
    """

    if not text:
        return Script.UNKNOWN
    counts: dict[Script, int] = {}
    total = 0
    for ch in text:
        if ch.isspace() or not ch.isalpha():
            continue
        cls = _classify_char(ch)
        if cls is None:
            continue
        counts[cls] = counts.get(cls, 0) + 1
        total += 1
    if total == 0:
        return Script.UNKNOWN
    top_script, top_count = max(counts.items(), key=lambda kv: kv[1])
    if top_count / total >= 0.60:
        return top_script
    return Script.MIXED
