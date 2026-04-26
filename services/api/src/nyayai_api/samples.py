"""Pre-bundled sample datasets the demo can run with one click.

Three benchmarks live on disk inside the container under ``/app/benchmarks``
because the Dockerfile copies the ``benchmarks/`` tree at build time. The
Flutter UI hits ``GET /samples`` to populate three preset buttons; clicking
one calls ``POST /audit/sample`` which hands the matching parquet to the
orchestrator without making the user upload anything.

We intentionally do NOT expose raw paths to the client — the client only
sees a slug ("mudra-lite") and the API resolves it to a path here. Path
traversal stops at this whitelist.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

# Directory inside the container that holds the bundled benchmarks. The
# Dockerfile copies the whole repo's benchmarks/ tree under /app/benchmarks/.
# Local dev reads from the repo root.
_LOCAL_BENCHMARKS = Path(__file__).resolve().parents[4] / "benchmarks"
_CONTAINER_BENCHMARKS = Path("/app/benchmarks")


def _resolve(relative: str) -> Path:
    if _CONTAINER_BENCHMARKS.exists():
        return _CONTAINER_BENCHMARKS / relative
    return _LOCAL_BENCHMARKS / relative


@dataclass(frozen=True)
class Sample:
    """A bundled sample dataset the user can run with one click."""

    id: str
    name: str
    description: str
    region: str  # "India" or "USA" — used to colour the preset chip
    parquet_path: Path
    row_count: int
    protected_columns: tuple[str, ...]
    outcome_column: str
    model_score_column: str | None
    decision_threshold: float
    default_goal: str
    default_regime: str
    default_model_id: str
    default_requested_attributes: tuple[str, ...]


SAMPLES: dict[str, Sample] = {
    "mudra-lite": Sample(
        id="mudra-lite",
        name="MUDRA-Lite (synthetic Indian micro-loan)",
        description=(
            "2,000-row synthetic Indian micro-loan dataset with caste, "
            "religion, mother-tongue and rural/urban habitation labels. "
            "Designed to expose surname-proxy leakage and caste-correlated "
            "denials."
        ),
        region="India",
        parquet_path=_resolve("mudra-lite/data/mudra-lite.parquet"),
        row_count=2000,
        protected_columns=(
            "gender",
            "state",
            "mother_tongue",
            "caste_disclosed",
            "religion",
        ),
        outcome_column="approved",
        model_score_column="model_score",
        decision_threshold=0.5,
        default_goal=(
            "Audit the MUDRA-Lite lending model for caste, religion, region "
            "and language bias under DPDP Act 2023 Rule 13 and the RBI "
            "Digital Lending Directions. Include intersectional slices "
            "where caste combines with gender."
        ),
        default_regime="DPDP",
        default_model_id="mudra-lite-gbm-v1",
        default_requested_attributes=("caste", "religion", "gender", "region", "language"),
    ),
    "uci-adult": Sample(
        id="uci-adult",
        name="UCI Adult (US census income)",
        description=(
            "48,842-row US Census income dataset; the canonical fairness "
            "reproducibility anchor. Sex / race DP differences match "
            "Bellamy et al. 2018 (AIF360) and Agarwal et al. 2018 "
            "(Fairlearn) within ±0.02."
        ),
        region="USA",
        parquet_path=_resolve("uci-adult/data/adult.parquet"),
        row_count=48842,
        protected_columns=("sex", "race"),
        outcome_column="income_high",
        model_score_column="model_score",
        decision_threshold=0.5,
        default_goal=(
            "Reproduce the canonical UCI Adult fairness benchmark under EU "
            "AI Act Article 10 (data governance). Surface sex and race "
            "demographic-parity differences."
        ),
        default_regime="EU_AI_ACT",
        default_model_id="adult-lr-v1",
        default_requested_attributes=("gender",),
    ),
    "compas": Sample(
        id="compas",
        name="ProPublica COMPAS (US recidivism)",
        description=(
            "6,172-row ProPublica COMPAS dataset; reproduces both the "
            "Angwin 2016 FPR disparity (Black 42% vs White 22%) and the "
            "Northpointe 2016 PPV calibration. Demonstrates the "
            "Chouldechova 2017 impossibility result on a single audit."
        ),
        region="USA",
        parquet_path=_resolve("compas/data/compas.parquet"),
        row_count=6172,
        protected_columns=("race", "sex"),
        outcome_column="two_year_recid",
        model_score_column="decile_score_normalized",
        decision_threshold=0.5,
        default_goal=(
            "Reproduce the ProPublica COMPAS audit. Surface false-positive "
            "rate and predictive-parity gaps across race; expose the "
            "Chouldechova impossibility tradeoff for the report."
        ),
        default_regime="EU_AI_ACT",
        default_model_id="compas-decile-v1",
        default_requested_attributes=("gender",),
    ),
}


def list_samples() -> list[dict]:
    """Public metadata for the GET /samples endpoint."""
    out: list[dict] = []
    for s in SAMPLES.values():
        out.append(
            {
                "id": s.id,
                "name": s.name,
                "description": s.description,
                "region": s.region,
                "row_count": s.row_count,
                "protected_columns": list(s.protected_columns),
                "outcome_column": s.outcome_column,
                "model_score_column": s.model_score_column,
                "decision_threshold": s.decision_threshold,
                "default_goal": s.default_goal,
                "default_regime": s.default_regime,
                "default_model_id": s.default_model_id,
                "default_requested_attributes": list(s.default_requested_attributes),
                "available": s.parquet_path.exists(),
            }
        )
    return out


def get_sample(sample_id: str) -> Sample | None:
    return SAMPLES.get(sample_id)
