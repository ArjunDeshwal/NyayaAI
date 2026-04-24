# ProPublica COMPAS (two-year recidivism) — dataset card

## Summary

ProPublica's COMPAS analytic cohort is the canonical US-context recidivism
benchmark for algorithmic fairness research. NyayaAI uses it, alongside UCI
Adult, as a reproducibility anchor: our fairness engine must reproduce
ProPublica's headline false-positive-rate disparity (Black vs White) within
tolerance, or we have a bug in `packages/fairlearn-extensions/`.

- **6,172 rows** (after the ProPublica-canonical analytic-cohort filter).
- **Seed 42** is the canonical reproduction seed.
- **Task**: binary classification — does a defendant who received a COMPAS
  risk screen in Broward County between 2013 and 2014 re-appear on a new
  criminal charge within two years of the screen?
- **Sensitive attributes**: `race` (6 categories in raw CSV, 4 above the
  `min_slice_n=100` floor we enforce), `sex` (Male / Female in the source).
- **Predictor**: the proprietary Northpointe COMPAS `decile_score` (1-10,
  integer). ProPublica's convention — adopted by almost every
  follow-up paper — is to binarise at `decile_score >= 5` ("medium or high
  risk"). We store both the raw integer and a normalized
  `decile_score_normalized = decile_score / 10.0` so the NyayaAI CLI
  (which constrains `--threshold` to `[0, 1]`) can consume it directly
  at `--threshold 0.5`.

## Provenance

Downloaded from the canonical ProPublica GitHub repository:
`https://raw.githubusercontent.com/propublica/compas-analysis/master/compas-scores-two-years.csv`

- **Original data owner**: Broward County (FL) Sheriff's Office (criminal
  history + jail records) joined with COMPAS risk scores obtained by
  ProPublica under a Florida Sunshine public-records request.
- **Curation**: Jeff Larson, Surya Mattu, Lauren Kirchner, Julia Angwin
  (ProPublica, May 2016).
- **Published replication notebook**: `Compas Analysis.ipynb` in the same
  repo, which is the source of the canonical filter we apply.

## Licence

**US public records / public domain.** The underlying Broward County jail
records are Florida public records (Chapter 119 F.S.) and not subject to
copyright. ProPublica redistribute the derived CSV under their standard
public-interest-journalism policy; they explicitly invite reuse for
independent reproducibility work (see the ProPublica methodology note
"How We Analyzed the COMPAS Recidivism Algorithm").

## Canonical filter

We apply the exact filter from ProPublica's replication notebook:

| Filter | Rationale |
|---|---|
| `days_b_screening_arrest BETWEEN -30 AND 30` | Drops rows where the charge date is far from the screening date (charge likely refers to a different incident). |
| `is_recid != -1` | Drops rows where recidivism is unknown. |
| `c_charge_degree != "O"` | Drops "ordinary traffic" (no valid charge degree in the data dictionary). |
| `score_text != "N/A"` | Drops missing risk labels. |

Applied in order this reproduces the 6,172-row cohort reported in the
ProPublica article. Any row missing `race`, `sex`, `two_year_recid` or
`decile_score` is also dropped (there are none in this filtered slice).

## Columns (emitted parquet)

| Column | Type | Notes |
|---|---|---|
| `race` | string | African-American / Caucasian / Hispanic / Other / Asian / Native American — **sensitive** |
| `sex` | string | Male / Female — **sensitive** |
| `two_year_recid` | int | Binary target: 1 if re-arrested within 2 years of screen |
| `decile_score_normalized` | float | `decile_score / 10.0`, in `[0.1, 1.0]` — used by the audit engine as `model_score` |
| `decile_score` | int | Raw Northpointe COMPAS score, 1-10 |
| `age` | int | Years at time of screen |
| `age_cat` | string | Less than 25 / 25 - 45 / Greater than 45 |
| `priors_count` | int | Prior convictions |
| `c_charge_degree` | string | F (felony) / M (misdemeanour) |
| `score_text` | string | Low / Medium / High (Northpointe's own bucket of decile_score) |
| `days_b_screening_arrest` | int | Gap (days) between screen and arrest; kept for provenance |
| `is_recid` | int | Raw recidivism flag pre-two-year constraint |

## Intended uses

- Regression test for NyayaAI's fairness engine: the Angwin et al. 2016
  Black vs White FPR (~45% vs ~23%) is the most-cited reproducible number
  in algorithmic-fairness research.
- Tutorial fixture for a classroom demo of Chouldechova's 2017
  impossibility result: the COMPAS score simultaneously satisfies PPV
  parity (Northpointe's defense) and violates FPR parity (ProPublica's
  critique) because base rates differ.
- Sanity anchor when changing internals of `packages/fairlearn-extensions/`
  alongside UCI Adult and MUDRA-Lite.

## Not intended for

- Training any production system.
- Claims about recidivism in 2026 or outside Broward County, Florida.
- Comparing to India-context benchmarks such as MUDRA-Lite — the
  attribute taxonomy (caste, religion, habitation) is absent here.
- Arguing whether COMPAS is "biased" in an absolute sense; we report the
  group-fairness numbers and let the reader reconcile them with
  Chouldechova's impossibility result (§"Caveats" below).

## Known limitations / biases

- **Measurement bias (recidivism is arrest, not re-offense).** The target
  `two_year_recid` is whether a defendant was *re-arrested* within two
  years, not whether they re-offended. Black defendants are historically
  over-policed in Broward County; the target therefore inherits the
  selection bias of arrest patterns. This is the single most important
  caveat in all COMPAS research and must be surfaced in any audit report.
- **Selection bias.** The cohort is restricted to defendants who (a)
  received a COMPAS screen at booking and (b) had a complete 2-year
  followup. Defendants released or transferred quickly are
  under-represented.
- **Construct validity.** "Recidivism risk" is defined by Northpointe's
  137-question instrument; ground-truth re-arrest and COMPAS risk are
  not independent — both are conditioned on contact with the criminal
  justice system.
- **Race categories are self-reported or officer-assigned** in the
  Broward records; the distinction is not documented. `Asian` (n=31) and
  `Native American` (n=11) are too small for stable per-group metrics
  and are excluded from aggregate DP/EO/FPR via `--min-slice-n 100`; the
  engine emits a warning listing both.
- **Class imbalance is mild** (~45.5% positive label, which is why the
  accuracy ceiling of ~66% is unimpressive).
- **Definitional gap between Northpointe and ProPublica.** Northpointe's
  "fairness" target is Predictive Parity (PPV equalised across groups).
  ProPublica's is Equalised Odds (FPR + FNR). Chouldechova (2017) proved
  these are mutually incompatible when base rates differ, which they do
  here (Black base rate 0.52, White 0.39). Our REPORT surfaces *both*.

## Reproducibility

```
uv run python benchmarks/compas/fetch.py \
    --out benchmarks/compas/data/compas.parquet --seed 42
```

Seed is a no-op on the data side (we do not train a model; the predictor
is Northpointe's published score). Seed is preserved for API symmetry
with UCI Adult and MUDRA-Lite and is used downstream by the DP layer for
small-slice noise injection. Any change to this file, `fetch.py`, or the
pinned Fairlearn / scikit-learn / numpy / pandas versions invalidates the
literature-comparison numbers in `REPORT.md`.

## References

- Angwin, J., Larson, J., Mattu, S., & Kirchner, L. (2016).
  *Machine Bias.* ProPublica, 23 May 2016.
- Larson, J., Mattu, S., Kirchner, L., & Angwin, J. (2016).
  *How We Analyzed the COMPAS Recidivism Algorithm.* ProPublica
  methodology note, 23 May 2016.
- Dieterich, W., Mendoza, C., & Brennan, T. (2016).
  *COMPAS Risk Scales: Demonstrating Accuracy Equity and Predictive
  Parity.* Northpointe technical response, 8 July 2016.
- Chouldechova, A. (2017). *Fair prediction with disparate impact: A
  study of bias in recidivism prediction instruments.* Big Data, 5(2).
- Corbett-Davies, S., Pierson, E., Feller, A., Goel, S., & Huq, A. (2017).
  *Algorithmic decision making and the cost of fairness.* KDD 2017.
- Kleinberg, J., Mullainathan, S., & Raghavan, M. (2017).
  *Inherent Trade-Offs in the Fair Determination of Risk Scores.*
  ITCS 2017.
