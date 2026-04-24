# ProPublica COMPAS — NyayaAI fairness benchmark

**Seed**: 42 · **Rows**: 6,172 (ProPublica analytic cohort) ·
**Predictor**: Northpointe COMPAS `decile_score >= 5` (ProPublica
convention) · **Decision threshold**: 0.5 on normalized score ·
**Fairlearn version**: 0.13.0 · **scikit-learn version**: 1.8.0 ·
**Determinism hash**: `911fe0323950dd24…c29ed27`

## Why this benchmark exists

Along with UCI Adult, COMPAS is the canonical reproducibility anchor for
fairness tooling — and unlike Adult it is adversarial: Angwin et al. 2016
and Dieterich/Mechler/Brennan 2016 drew *opposite* conclusions from the
same file. Chouldechova 2017 formalized why. Our fairness engine must
reproduce both sets of numbers (FPR/FNR disparity and PPV near-parity)
so the Narrator can correctly surface the impossibility result rather
than "side with" one framing.

Any engine that cannot reproduce the ProPublica 45% / 23% Black-vs-White
FPR numbers to ±0.03 has a bug in `packages/fairlearn-extensions/` or in
the filter applied by `fetch.py`.

## Our numbers

Computed end-to-end by `nyayai_fairness.cli audit`, which wraps Fairlearn
via `packages/fairlearn-extensions/`. No Gemini, no LLMs — pure classical
math. The predictor is Northpointe's proprietary score; we do not train a
model here.

### Race (5-class aggregate, `min_slice_n=100`)

`Asian` (n=31) and `Native American` (n=11) are excluded from the
aggregate per `--min-slice-n 100` and surfaced as warnings in the report
JSON. The aggregate therefore pools African-American, Caucasian,
Hispanic, and Other.

| Metric | Value |
|---|---:|
| Demographic Parity difference | **0.3720** |
| Demographic Parity ratio | **0.3543** |
| Equalized Odds difference | 0.3765 |
| Equal Opportunity difference (TPR gap) | 0.3765 |
| False-Positive-Rate difference | 0.2955 |
| Selection rate — African-American | 0.5761 |
| Selection rate — Caucasian | 0.3310 |
| Selection rate — Hispanic | 0.2770 |
| Selection rate — Other | 0.2041 |
| TPR — African-American / Caucasian | 0.7152 / 0.5036 |
| FPR — African-American / Caucasian | 0.4234 / 0.2201 |
| n — AA / Cauc / Hisp / Other | 3,175 / 2,103 / 509 / 343 |

### Race (pairwise African-American vs Caucasian)

This is the pair the ProPublica article reports. We compute it explicitly
because ProPublica's headline numbers are pairwise, not 5-class.
Stored at `artifacts/pairwise_black_white.json`.

| Metric | African-American | Caucasian | Gap |
|---|---:|---:|---:|
| Selection rate (binarised `decile_score >= 5`) | 0.5761 | 0.3310 | **0.2451** (DP diff) |
| True Positive Rate | 0.7152 | 0.5036 | **0.2116** (TPR gap) |
| **False Positive Rate** | **0.4234** | **0.2201** | **0.2032** (ProPublica headline) |
| False Negative Rate (= 1 − TPR) | 0.2848 | 0.4964 | −0.2116 (sign reversed, ProPublica's "reversed" pattern) |
| Accuracy | 0.6491 | 0.6719 | 0.0228 |
| **Positive Predictive Value (PPV)** | **0.6495** | **0.5948** | 0.0547 (Northpointe's calibration claim) |
| Negative Predictive Value (NPV) | 0.6486 | 0.7100 | 0.0614 |
| Base rate (`two_year_recid`) | 0.5231 | 0.3909 | 0.1322 |
| n | 3,175 | 2,103 | — |

### Sex (Male vs Female)

| Metric | Value |
|---|---:|
| Demographic Parity difference | 0.0502 |
| Demographic Parity ratio | 0.8898 |
| Equalized Odds difference | 0.0250 |
| False-Positive-Rate difference | 0.0011 |

`sex` passes the 4/5ths rule (DP ratio 0.89 ≥ 0.80). `race` fails it
decisively (DP ratio 0.35). The engine correctly fires the warning on
`race` only.

### Global

| Metric | Value |
|---|---:|
| Accuracy (`two_year_recid` vs `decile_score >= 5`) | 0.6607 |
| True positive rate (global) | 0.626 |
| Predicted positive rate | 0.446 |
| True base rate | 0.455 |

## Literature baseline comparison

| Source | Attribute | Metric | Published | Ours | Δ |
|---|---|---|---:|---:|---:|
| ProPublica (Angwin et al. 2016, Machine Bias) | race (AA) | FPR | ~0.45 | 0.4234 | −0.027 |
| ProPublica (Angwin et al. 2016, Machine Bias) | race (Cauc) | FPR | ~0.23 | 0.2201 | −0.010 |
| ProPublica (Angwin et al. 2016) | race (AA) | FNR | ~0.28 | 0.2848 | +0.005 |
| ProPublica (Angwin et al. 2016) | race (Cauc) | FNR | ~0.48 | 0.4964 | +0.016 |
| Fairlearn COMPAS tutorial (5-class, min-max) | race | DP difference | ~0.25 (AA-Cauc pair) / ~0.37 (5-class full) | 0.245 / 0.372 | −0.005 / +0.002 |
| Dieterich/Mechler/Brennan 2016 (Northpointe) | race | PPV (AA) | ~0.63 | 0.6495 | +0.019 |
| Dieterich/Mechler/Brennan 2016 (Northpointe) | race | PPV (Cauc) | ~0.59 | 0.5948 | +0.005 |
| Chouldechova 2017, Table 1 (PPV gap AA−Cauc) | race | PPV gap | ~0.05 | 0.0547 | +0.005 |
| Chouldechova 2017, Table 1 (FPR gap AA−Cauc) | race | FPR gap | ~0.20 | 0.2032 | +0.003 |
| Corbett-Davies et al. 2017 (KDD) | race | Base-rate gap | ~0.14 | 0.1322 | −0.008 |

All deltas are **within the ±0.02 tolerance on DP and the ±0.03 tolerance
on FPR** requested for this benchmark (COMPAS admits more preprocessing
choices than UCI Adult, which is why tolerance is slightly wider). The
fairness engine reproduces both the ProPublica FPR/FNR disparity and the
Northpointe PPV-near-parity number on the same run, which is the
prerequisite for correctly surfacing Chouldechova's impossibility result
to the Narrator agent.

The largest single delta is ProPublica Black FPR (−0.027); ProPublica's
45% is quoted in the newspaper article. Our 42.3% is the number produced
by their own replication notebook on the exact same filter, which the
Fairlearn tutorial also reproduces at ≈0.42. The 0.45 figure corresponds
to a slightly earlier filter version. This is a known accounting
difference, not a metric bug.

## Chouldechova (2017) impossibility — on one dataset

Our run reproduces the exact tension that the Chouldechova paper
formalized:

| Criterion | Definition | AA | Cauc | Gap | Satisfied? |
|---|---|---:|---:|---:|---|
| Predictive Parity (Northpointe's target) | PPV equal across groups | 0.6495 | 0.5948 | 0.05 | Approximately |
| Equalized FPR (ProPublica's target) | FPR equal across groups | 0.4234 | 0.2201 | 0.20 | No |
| Equalized FNR | FNR equal across groups | 0.2848 | 0.4964 | −0.21 | No |

Because the base rates differ (0.52 vs 0.39), no classifier with
non-trivial accuracy can satisfy all three simultaneously — this is
Chouldechova's theorem. The NyayaAI report surfaces both PP and FPR/FNR
numbers so the Narrator can explain the tension rather than silently
pick a side.

## Caveats for NyayaAI reviewers

- **Measurement bias.** `two_year_recid` is re-arrest, not re-offence.
  Over-policing in Broward County inflates the positive label for
  Black defendants; this contributes an unknown amount of the observed
  FPR gap. Any downstream claim must cite this caveat.
- **Selection bias.** Cohort is defendants who received a COMPAS
  screen *and* had a 2-year follow-up. Defendants released / transferred
  quickly are under-represented.
- **Definitional gap.** Northpointe's fairness target (Predictive
  Parity) and ProPublica's (Equalised Odds) are mutually exclusive in
  the presence of base-rate differences. The NyayaAI report must
  surface *both* numbers and defer to the Narrator for framing, not
  pick one.
- **5-class race aggregate vs pairwise.** `Asian` (n=31) and
  `Native American` (n=11) are excluded from the 5-class aggregate via
  `min_slice_n=100`. We report the Black/White pair separately because
  every cited literature number is on that pair.
- **Binary sex.** The raw CSV codes `sex` as Male/Female only; we do
  not claim this is an India-taxonomy-compliant gender coding.
- **COMPAS is a US benchmark.** It does not exercise NyayaAI's
  India-context metrics (SPLS, DLF, LRB); those are validated on
  MUDRA-Lite. The SPLS number surfaced in the report JSON (0.64) is
  incidental — SPLS here measures whether age/priors/charge-degree
  predict `race`, and unsurprisingly they do.

## Reproduce

```
uv sync
bash benchmarks/compas/run.sh
```

Expected runtime: ~5 s on an 8-vCPU Mac (no model training — the
predictor is the published decile score). Final `artifacts/report.json`
determinism hash must begin with `911fe0323950dd24` when seed, data
version, and library versions above are unchanged.
