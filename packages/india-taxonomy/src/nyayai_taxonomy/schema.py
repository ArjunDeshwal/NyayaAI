"""Pydantic enums and models for India-context protected attributes.

Sources:
- Constitution of India Schedules (caste categories; Mandal Commission groupings)
- Census of India Language Atlas (22 scheduled mother-tongue codes + English)
- ISO 3166-2:IN (state codes)
- MoPR Local Government Directory (district codes; string-typed here)
- RPwD Act 2016 Schedule (21 specified disabilities; collapsed to 7 broad categories)
- Transgender Persons (Protection of Rights) Act 2019 (gender recognition; THIRD is legal)

Do NOT hard-code caste/religion strings elsewhere in the codebase --- always
import the enums from this module.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class Caste(str, Enum):
    """Caste categories per Constitution of India + Mandal Commission.

    NT_DNT (Nomadic Tribes / Denotified Tribes) is frequently omitted from
    datasets but is a distinct protected category in multiple state welfare
    schemes and must not be silently merged into OBC or ST.
    """

    GENERAL = "GENERAL"
    OBC = "OBC"
    SC = "SC"
    ST = "ST"
    NT_DNT = "NT_DNT"
    UNKNOWN = "UNKNOWN"


class Religion(str, Enum):
    """Religion categories per Census of India."""

    HINDU = "HINDU"
    MUSLIM = "MUSLIM"
    CHRISTIAN = "CHRISTIAN"
    SIKH = "SIKH"
    BUDDHIST = "BUDDHIST"
    JAIN = "JAIN"
    PARSI = "PARSI"
    OTHER = "OTHER"
    NONE = "NONE"
    UNKNOWN = "UNKNOWN"


class Habitation(str, Enum):
    RURAL = "RURAL"
    URBAN = "URBAN"
    PERI_URBAN = "PERI_URBAN"
    UNKNOWN = "UNKNOWN"


# ISO 3166-2:IN state/UT codes (36 subdivisions as of 2026).
_IN_STATE_CODES: tuple[str, ...] = (
    "IN-AN",  # Andaman and Nicobar Islands
    "IN-AP",  # Andhra Pradesh
    "IN-AR",  # Arunachal Pradesh
    "IN-AS",  # Assam
    "IN-BR",  # Bihar
    "IN-CH",  # Chandigarh
    "IN-CT",  # Chhattisgarh
    "IN-DH",  # Dadra and Nagar Haveli and Daman and Diu
    "IN-DL",  # Delhi
    "IN-GA",  # Goa
    "IN-GJ",  # Gujarat
    "IN-HR",  # Haryana
    "IN-HP",  # Himachal Pradesh
    "IN-JK",  # Jammu and Kashmir
    "IN-JH",  # Jharkhand
    "IN-KA",  # Karnataka
    "IN-KL",  # Kerala
    "IN-LA",  # Ladakh
    "IN-LD",  # Lakshadweep
    "IN-MP",  # Madhya Pradesh
    "IN-MH",  # Maharashtra
    "IN-MN",  # Manipur
    "IN-ML",  # Meghalaya
    "IN-MZ",  # Mizoram
    "IN-NL",  # Nagaland
    "IN-OR",  # Odisha
    "IN-PY",  # Puducherry
    "IN-PB",  # Punjab
    "IN-RJ",  # Rajasthan
    "IN-SK",  # Sikkim
    "IN-TN",  # Tamil Nadu
    "IN-TG",  # Telangana
    "IN-TR",  # Tripura
    "IN-UP",  # Uttar Pradesh
    "IN-UT",  # Uttarakhand
    "IN-WB",  # West Bengal
    "IN-UNKNOWN",
)

# Build a dynamic Enum so callers can iterate / validate.
Region = Enum(  # type: ignore[misc]
    "Region",
    {code.replace("-", "_"): code for code in _IN_STATE_CODES},
    type=str,
)
Region.__doc__ = "ISO 3166-2:IN state / Union Territory codes."


class MotherTongue(str, Enum):
    """22 Scheduled Languages (Eighth Schedule) + English + Other/Unknown.

    Codes use ISO-639-3-inspired short forms used by Census of India.
    """

    ASM = "ASM"  # Assamese
    BEN = "BEN"  # Bengali
    BOD = "BOD"  # Bodo
    DOG = "DOG"  # Dogri
    ENG = "ENG"  # English (non-scheduled but 1st-language for millions)
    GUJ = "GUJ"  # Gujarati
    HIN = "HIN"  # Hindi
    KAN = "KAN"  # Kannada
    KAS = "KAS"  # Kashmiri
    KOK = "KOK"  # Konkani
    MAI = "MAI"  # Maithili
    MAL = "MAL"  # Malayalam
    MAR = "MAR"  # Marathi
    MEI = "MEI"  # Manipuri (Meitei)
    NEP = "NEP"  # Nepali
    ORI = "ORI"  # Odia
    PAN = "PAN"  # Punjabi
    SAN = "SAN"  # Sanskrit
    SAT = "SAT"  # Santali
    SND = "SND"  # Sindhi
    TAM = "TAM"  # Tamil
    TEL = "TEL"  # Telugu
    URD = "URD"  # Urdu
    OTHER = "OTHER"
    UNKNOWN = "UNKNOWN"


class Gender(str, Enum):
    """Gender categories.

    THIRD is a first-class legal category per the Transgender Persons
    (Protection of Rights) Act, 2019. Never treat gender as binary.
    """

    FEMALE = "FEMALE"
    MALE = "MALE"
    THIRD = "THIRD"
    UNKNOWN = "UNKNOWN"


class AgeCohort(str, Enum):
    AGE_LT_18 = "AGE_LT_18"
    AGE_18_25 = "AGE_18_25"
    AGE_26_45 = "AGE_26_45"
    AGE_46_60 = "AGE_46_60"
    AGE_GT_60 = "AGE_GT_60"
    UNKNOWN = "UNKNOWN"


class Disability(str, Enum):
    """Broad disability categories per RPwD Act 2016 Schedule.

    The Act lists 21 specified disabilities; we collapse them to 7 canonical
    groups for fairness slicing. Datasets with finer-grained codes should
    carry the raw code alongside and map to this enum for aggregation.
    """

    NONE = "NONE"
    VISUAL = "VISUAL"
    HEARING = "HEARING"
    LOCOMOTOR = "LOCOMOTOR"
    INTELLECTUAL = "INTELLECTUAL"
    PSYCHOSOCIAL = "PSYCHOSOCIAL"
    MULTIPLE = "MULTIPLE"
    OTHER = "OTHER"
    UNKNOWN = "UNKNOWN"


class DigitalLiteracy(str, Enum):
    """Digital-literacy quartiles.

    Derived (never self-reported on ingest) from device class, OS locale,
    typing cadence, and prior app sessions. Used for the DLF custom metric.
    """

    DLQ1 = "DLQ1"  # lowest quartile
    DLQ2 = "DLQ2"
    DLQ3 = "DLQ3"
    DLQ4 = "DLQ4"  # highest quartile
    UNKNOWN = "UNKNOWN"


def bin_age(age: int | float) -> AgeCohort:
    """Bin a raw age value to an :class:`AgeCohort`.

    Do NOT call this at ingest time if consent is fresh --- keep raw age
    in the VPC-SC perimeter and bin only just-in-time for metric computation.
    """

    if age < 0:
        return AgeCohort.UNKNOWN
    if age < 18:
        return AgeCohort.AGE_LT_18
    if age < 26:
        return AgeCohort.AGE_18_25
    if age < 46:
        return AgeCohort.AGE_26_45
    if age < 61:
        return AgeCohort.AGE_46_60
    return AgeCohort.AGE_GT_60


class ProtectedAttributeSet(BaseModel):
    """Composition of all protected attributes for one subject.

    Every field is optional; ``UNKNOWN`` is a legal value for each enum.
    Used as the canonical row shape by the fairness service after
    taxonomy mapping.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    caste: Caste = Field(default=Caste.UNKNOWN)
    religion: Religion = Field(default=Religion.UNKNOWN)
    region_state: Region = Field(default=Region["IN_UNKNOWN"])
    habitation: Habitation = Field(default=Habitation.UNKNOWN)
    mother_tongue: MotherTongue = Field(default=MotherTongue.UNKNOWN)
    gender: Gender = Field(default=Gender.UNKNOWN)
    age_cohort: AgeCohort = Field(default=AgeCohort.UNKNOWN)
    disability: Disability = Field(default=Disability.UNKNOWN)
    digital_literacy: DigitalLiteracy = Field(default=DigitalLiteracy.UNKNOWN)

    def as_slice_key(self) -> dict[str, str]:
        """Return a flat ``{attr: value}`` dict suitable for a slice key."""

        return {
            "caste": self.caste.value,
            "religion": self.religion.value,
            "region_state": self.region_state.value,
            "habitation": self.habitation.value,
            "mother_tongue": self.mother_tongue.value,
            "gender": self.gender.value,
            "age_cohort": self.age_cohort.value,
            "disability": self.disability.value,
            "digital_literacy": self.digital_literacy.value,
        }


# Default intersectional slices computed on every audit.
# Rationale: highest-risk subgroups from Muralidharan 2020, IFF-Vidhi 2021, Amnesty 2024.
DEFAULT_INTERSECTIONAL_SLICES: tuple[tuple[str, ...], ...] = (
    ("habitation", "gender", "caste"),
    ("habitation", "religion", "age_cohort"),
    ("disability", "habitation"),
    ("mother_tongue", "digital_literacy"),
    ("gender",),
    ("age_cohort", "digital_literacy"),
)
