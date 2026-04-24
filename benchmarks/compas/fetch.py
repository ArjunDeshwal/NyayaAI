"""Fetch ProPublica COMPAS and produce a parquet ready for the NyayaAI fairness engine.

Pipeline:

1. Download ``compas-scores-two-years.csv`` from the ProPublica
   ``compas-analysis`` GitHub repository. This is the canonical file used in
   Angwin et al. (*Machine Bias*, ProPublica, 2016) and reproduced in every
   downstream paper on COMPAS fairness.
2. Apply the ProPublica-canonical filter:

   * ``days_b_screening_arrest`` between -30 and 30 (drops rows where the
     charge date is far from the screening date and the screen clearly
     refers to a different event).
   * ``is_recid != -1`` (drops rows missing recidivism data).
   * ``c_charge_degree != "O"`` (drops "ordinary traffic" which has no
     valid charge degree in their data dictionary).
   * ``score_text != "N/A"``.

   This is the same filter Jeff Larson's replication notebook applies to
   produce the 6,172-row analytic cohort reported in the ProPublica story.
3. Build binary outcome ``two_year_recid`` (already 0/1 in the source) and
   a binary prediction from ``decile_score >= 5``. ProPublica's convention:
   scores 1-4 are "low risk", 5-7 "medium", 8-10 "high"; pooling
   medium+high as the positive prediction yields their headline FPR/FNR
   disparities. This is NOT our model --- it is Northpointe's proprietary
   COMPAS score treated as a black box predictor we are auditing.
4. Emit ``data/compas.parquet`` with:
   - sensitive columns (``race``, ``sex``)
   - outcome (``two_year_recid``)
   - raw integer score (``decile_score`` ranging 1-10) for provenance.
   - ``decile_score_normalized = decile_score / 10.0`` so the NyayaAI audit
     engine (which constrains ``decision_threshold`` to ``[0, 1]``) can
     derive the decision at ``--threshold 0.5`` == ``decile_score >= 5``.
   - selected provenance columns (age, priors, charge degree) for dataset
     card traceability.

Seed 42 is the canonical reproduction seed.

Usage::

    uv run python benchmarks/compas/fetch.py \\
        --out benchmarks/compas/data/compas.parquet --seed 42
"""

from __future__ import annotations

import argparse
import io
from pathlib import Path
from urllib.request import Request, urlopen

import pandas as pd


COMPAS_URL = (
    "https://raw.githubusercontent.com/propublica/compas-analysis/"
    "master/compas-scores-two-years.csv"
)

SENSITIVE_COLS: tuple[str, ...] = ("race", "sex")
OUTCOME_COL: str = "two_year_recid"
RAW_SCORE_COL: str = "decile_score"
NORMALIZED_SCORE_COL: str = "decile_score_normalized"
PROVENANCE_COLS: tuple[str, ...] = (
    "age",
    "age_cat",
    "priors_count",
    "c_charge_degree",
    "score_text",
    "days_b_screening_arrest",
    "is_recid",
)


def load_compas_raw() -> pd.DataFrame:
    """Download the canonical ProPublica CSV.

    We pull from the GitHub raw URL (stable since 2016). No authentication is
    required; the file is ~6 MB. We stream via ``urllib`` to avoid an extra
    ``requests`` dependency in the benchmark bootstrap.
    """

    req = Request(COMPAS_URL, headers={"User-Agent": "nyayai-fairness-benchmark/1.0"})
    with urlopen(req, timeout=60) as resp:  # noqa: S310 (URL is a constant)
        raw = resp.read()
    return pd.read_csv(io.BytesIO(raw))


def propublica_filter(df: pd.DataFrame) -> pd.DataFrame:
    """Apply the ProPublica-canonical analytic-cohort filter."""

    # Copy to avoid SettingWithCopy warnings.
    out = df.copy()
    out = out[out["days_b_screening_arrest"].between(-30, 30, inclusive="both")]
    out = out[out["is_recid"] != -1]
    out = out[out["c_charge_degree"] != "O"]
    out = out[out["score_text"] != "N/A"]
    # Drop any rows missing the outcome or score.
    out = out.dropna(subset=[OUTCOME_COL, RAW_SCORE_COL, "race", "sex"])
    return out.reset_index(drop=True)


def build(seed: int) -> pd.DataFrame:
    del seed  # Determinism is data-side; no training step here.
    raw = load_compas_raw()
    filtered = propublica_filter(raw)

    keep = list(SENSITIVE_COLS) + [OUTCOME_COL, RAW_SCORE_COL] + list(PROVENANCE_COLS)
    keep = [c for c in keep if c in filtered.columns]
    out = filtered[keep].copy()

    # Make outcome a clean 0/1 int and score a clean int.
    out[OUTCOME_COL] = out[OUTCOME_COL].astype(int)
    out[RAW_SCORE_COL] = out[RAW_SCORE_COL].astype(int)

    # Normalize the decile score into [0.1, 1.0] so the NyayaAI audit
    # engine (which constrains ``decision_threshold`` to [0, 1]) can use it
    # directly. ``>= 0.5`` is exactly ``decile_score >= 5`` (ProPublica's
    # medium-or-high-risk convention).
    out[NORMALIZED_SCORE_COL] = out[RAW_SCORE_COL].astype(float) / 10.0

    # Normalize strings.
    for c in ("race", "sex", "age_cat", "c_charge_degree", "score_text"):
        if c in out.columns:
            out[c] = out[c].astype(str).str.strip()

    # Tidy column order: sensitive, outcome, scores, provenance.
    ordered = (
        list(SENSITIVE_COLS)
        + [OUTCOME_COL, NORMALIZED_SCORE_COL, RAW_SCORE_COL]
        + [c for c in PROVENANCE_COLS if c in out.columns]
    )
    ordered = [c for c in ordered if c in out.columns]
    return out[ordered]


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch ProPublica COMPAS two-year dataset.")
    parser.add_argument("--out", type=Path, required=True, help="Output parquet path.")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    df = build(seed=args.seed)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    if str(args.out).endswith(".csv"):
        df.to_csv(args.out, index=False)
    else:
        df.to_parquet(args.out, index=False)
    print(f"Wrote {len(df):,} rows x {len(df.columns)} cols to {args.out}")


if __name__ == "__main__":
    main()
