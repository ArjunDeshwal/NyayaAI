"""Deterministic synthetic MUDRA-Lite loan-approval dataset generator.

MUDRA-Lite reproduces, in miniature, the kind of disparate-impact pattern
documented in Muralidharan-Niehaus-Sukhtankar (NBER 2020) for PDS and by
Amnesty (2024) for Telangana's Samagra Vedika algorithm: equally qualified
SC/ST applicants are approved at materially lower rates than GENERAL-caste
applicants at the same income.

The dataset is **synthetic** --- we use state-level demographic priors from
Census 2011 public aggregates. No individual micro-data is used. CC0.

Usage:
    python generate.py --out data/mudra-lite.parquet --n 10000 --seed 42

The generated dataset is *biased by design* so that the demo-critical
pre-remediation metric (demographic-parity ratio on caste) lands around
0.55-0.65 --- matching the 0.61 headline number in IMPLEMENTATION_PLAN §15.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

# State-level share priors (Census 2011 aggregates; coarse).
# Columns: state_code, population_share, rural_fraction
STATE_PRIORS: list[tuple[str, float, float]] = [
    ("IN-UP", 0.165, 0.78),
    ("IN-MH", 0.094, 0.55),
    ("IN-BR", 0.086, 0.89),
    ("IN-WB", 0.076, 0.68),
    ("IN-MP", 0.060, 0.72),
    ("IN-TN", 0.060, 0.52),
    ("IN-RJ", 0.057, 0.75),
    ("IN-KA", 0.051, 0.61),
    ("IN-GJ", 0.050, 0.57),
    ("IN-AP", 0.041, 0.67),
    ("IN-OR", 0.035, 0.83),
    ("IN-TG", 0.029, 0.61),
    ("IN-KL", 0.028, 0.52),
    ("IN-JH", 0.027, 0.76),
    ("IN-AS", 0.026, 0.86),
    ("IN-PB", 0.023, 0.63),
    ("IN-CT", 0.021, 0.77),
    ("IN-HR", 0.021, 0.65),
    ("IN-DL", 0.014, 0.03),
    ("IN-JK", 0.010, 0.73),
    ("IN-UT", 0.008, 0.70),
    ("IN-HP", 0.006, 0.90),
]

# Caste shares (Census 2011 SC/ST figures; OBC from NSSO aggregates; rest GENERAL).
# These are country-level priors, then tilted by state rurality below.
CASTE_BASE: dict[str, float] = {
    "GENERAL": 0.31,
    "OBC": 0.41,
    "SC": 0.168,
    "ST": 0.085,
    "NT_DNT": 0.027,
}

# Religion shares (Census 2011).
RELIGION_PRIORS: dict[str, float] = {
    "HINDU": 0.798,
    "MUSLIM": 0.142,
    "CHRISTIAN": 0.023,
    "SIKH": 0.017,
    "BUDDHIST": 0.007,
    "JAIN": 0.004,
    "OTHER": 0.007,
    "NONE": 0.002,
}

# Dominant state -> mother-tongue (coarse; just for realistic correlation).
STATE_TONGUE: dict[str, str] = {
    "IN-UP": "HIN",
    "IN-MH": "MAR",
    "IN-BR": "HIN",
    "IN-WB": "BEN",
    "IN-MP": "HIN",
    "IN-TN": "TAM",
    "IN-RJ": "HIN",
    "IN-KA": "KAN",
    "IN-GJ": "GUJ",
    "IN-AP": "TEL",
    "IN-OR": "ORI",
    "IN-TG": "TEL",
    "IN-KL": "MAL",
    "IN-JH": "HIN",
    "IN-AS": "ASM",
    "IN-PB": "PAN",
    "IN-CT": "HIN",
    "IN-HR": "HIN",
    "IN-DL": "HIN",
    "IN-JK": "URD",
    "IN-UT": "HIN",
    "IN-HP": "HIN",
}

GENDERS: list[str] = ["FEMALE", "MALE", "THIRD"]
LOAN_PURPOSES: list[str] = ["agriculture", "retail", "services", "manufacturing", "education"]


def _sample_states(rng: np.random.Generator, n: int) -> pd.DataFrame:
    codes = [s for s, _, _ in STATE_PRIORS]
    probs = np.array([p for _, p, _ in STATE_PRIORS])
    probs = probs / probs.sum()
    state = rng.choice(codes, size=n, p=probs)
    rural_frac = {s: r for s, _, r in STATE_PRIORS}
    rural_prob = np.array([rural_frac[s] for s in state])
    habitation = np.where(rng.random(n) < rural_prob, "RURAL", "URBAN")
    mother_tongue = np.array([STATE_TONGUE.get(s, "HIN") for s in state])
    return pd.DataFrame({"state": state, "habitation": habitation, "mother_tongue": mother_tongue})


def _sample_caste(rng: np.random.Generator, states: pd.Series) -> np.ndarray:
    # Rural states slightly over-index on SC/ST; urban slightly under.
    out = np.empty(len(states), dtype=object)
    base_codes = list(CASTE_BASE.keys())
    base_probs = np.array(list(CASTE_BASE.values()))
    for i, _ in enumerate(states):
        out[i] = rng.choice(base_codes, p=base_probs)
    return out


def _sample_religion(rng: np.random.Generator, n: int) -> np.ndarray:
    codes = list(RELIGION_PRIORS.keys())
    probs = np.array(list(RELIGION_PRIORS.values()))
    probs = probs / probs.sum()
    return rng.choice(codes, size=n, p=probs)


def _digital_literacy_quartile(rng: np.random.Generator, urban: np.ndarray, education: np.ndarray) -> np.ndarray:
    # Higher education and urban tilt up; add noise; bin into quartiles.
    score = 0.5 * urban.astype(float) + 0.05 * education + rng.normal(0, 0.6, len(urban))
    qs = np.quantile(score, [0.25, 0.5, 0.75])
    bucket = np.digitize(score, qs) + 1  # -> 1..4
    return np.array([f"DLQ{b}" for b in bucket])


def _surname_proxy_score(rng: np.random.Generator, caste: np.ndarray) -> np.ndarray:
    # Simulated surname-derived caste-proxy score: higher for SC/ST/NT_DNT
    # (their surnames tend to be more caste-informative in our seed dictionary).
    base = np.where(
        np.isin(caste, ["SC", "ST", "NT_DNT"]),
        rng.uniform(0.55, 0.88, len(caste)),
        rng.uniform(0.05, 0.55, len(caste)),
    )
    return np.clip(base, 0.0, 0.92)


def generate(n: int = 10_000, seed: int = 42) -> pd.DataFrame:
    """Generate an ``n``-row MUDRA-Lite DataFrame."""

    rng = np.random.default_rng(seed)

    loc = _sample_states(rng, n)
    gender = rng.choice(GENDERS, size=n, p=[0.46, 0.535, 0.005])
    caste = _sample_caste(rng, loc["state"])
    religion = _sample_religion(rng, n)
    age = rng.integers(low=21, high=60, size=n)
    education_years = np.clip(rng.normal(9.5, 3.2, n), 0, 20).astype(int)

    # Income: base + rural/urban + education + some noise.
    income_monthly = np.round(
        6_000
        + 2_500 * (loc["habitation"] == "URBAN").astype(float)
        + 600 * education_years
        + rng.normal(0, 4_500, n)
    ).astype(int)
    income_monthly = np.clip(income_monthly, 2_000, 150_000)

    loan_amount = np.round(
        np.clip(rng.normal(0.9, 0.25, n) * 12 * income_monthly, 10_000, 1_500_000)
    ).astype(int)
    loan_purpose = rng.choice(LOAN_PURPOSES, size=n)

    typing_cadence_quartile = _digital_literacy_quartile(
        rng, urban=(loc["habitation"] == "URBAN").to_numpy(), education=education_years
    )

    surname_proxy_score = _surname_proxy_score(rng, caste)

    # Ground-truth "approved" depends fairly on income and education. The
    # intercept is tuned so that at threshold 0.5 the GENERAL-caste selection
    # rate lands around 0.40-0.55 (realistic for an MUDRA-like product).
    gt_logit = (
        -1.8
        + 0.000055 * income_monthly
        + 0.12 * education_years
        + rng.normal(0, 0.6, n)
    )
    gt_prob = 1.0 / (1.0 + np.exp(-gt_logit))
    approved = (rng.random(n) < gt_prob).astype(int)

    # Biased-by-design model_score: adds caste / gender / habitation penalties
    # on the logit scale. Penalty magnitudes are tuned so pre-remediation DP
    # ratio on caste lands in the ~0.55-0.65 band documented in
    # IMPLEMENTATION_PLAN §15.
    caste_penalty = np.where(
        np.isin(caste, ["SC", "ST", "NT_DNT"]),
        0.30,
        0.0,
    )
    gender_penalty = np.where(gender == "FEMALE", 0.18, np.where(gender == "THIRD", 0.35, 0.0))
    rural_penalty = np.where(loc["habitation"].to_numpy() == "RURAL", 0.22, 0.0)
    slow_typer_penalty = np.where(typing_cadence_quartile == "DLQ1", 0.20, 0.0)

    biased_logit = gt_logit - caste_penalty - gender_penalty - rural_penalty - slow_typer_penalty
    model_prob = 1.0 / (1.0 + np.exp(-biased_logit))
    model_score = model_prob  # keep as probability; binary decision derived at audit time

    df = pd.DataFrame(
        {
            "applicant_id": np.arange(n, dtype=int),
            "age": age,
            "gender": gender,
            "state": loc["state"].to_numpy(),
            "habitation": loc["habitation"].to_numpy(),
            "mother_tongue": loc["mother_tongue"].to_numpy(),
            "caste_disclosed": caste,
            "religion": religion,
            "income_monthly": income_monthly,
            "loan_amount": loan_amount,
            "loan_purpose": loan_purpose,
            "education_years": education_years,
            "typing_cadence_quartile": typing_cadence_quartile,
            "surname_proxy_score": surname_proxy_score.round(4),
            "approved": approved,
            "model_score": model_score.round(6),
        }
    )
    return df


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate MUDRA-Lite synthetic dataset")
    parser.add_argument("--out", type=Path, required=True, help="Output parquet path")
    parser.add_argument("--n", type=int, default=10_000)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    df = generate(n=args.n, seed=args.seed)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    if str(args.out).endswith(".csv"):
        df.to_csv(args.out, index=False)
    else:
        df.to_parquet(args.out, index=False)
    print(f"Wrote {len(df):,} rows to {args.out}")


if __name__ == "__main__":
    main()
