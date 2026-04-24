# UCI Adult — NyayaAI fairness benchmark

**Seed**: 42 · **Rows**: 48,842 · **Model**: blind logistic regression
(no sensitive attributes in features) · **Decision threshold**: 0.5 ·
**Fairlearn version**: 0.13.0 · **scikit-learn version**: 1.8.0
**Determinism hash**: `e821e5e38d34f26e…ed20438`

## Why this benchmark exists

UCI Adult is the canonical reproducibility anchor for fairness tooling.
Both AIF360 (Bellamy et al. 2018) and the Fairlearn reductions paper
(Agarwal et al. 2018) publish baseline metrics on it. Our fairness engine
must land within published tolerance or we have a bug in
`packages/fairlearn-extensions/`.

## Our numbers

Computed end-to-end by `nyayai_fairness.cli audit`, which wraps Fairlearn
via `packages/fairlearn-extensions/`. No Gemini, no LLMs — pure classical
math.

### Sex (Male / Female)

| Metric | Value |
|---|---:|
| Demographic Parity difference | **0.1729** |
| Demographic Parity ratio | **0.3114** |
| Equalized Odds difference | 0.0790 |
| Equal Opportunity difference (TPR gap) | 0.0790 |
| False-Positive-Rate difference | 0.0716 |
| Selection rate — Male | 0.2511 |
| Selection rate — Female | 0.0782 |
| n Male / n Female | 32,650 / 16,192 |

### Race (5 categories)

| Metric | Value |
|---|---:|
| Demographic Parity difference | **0.1577** |
| Demographic Parity ratio | **0.3401** |
| Equalized Odds difference | 0.1655 |
| Equal Opportunity difference (TPR gap) | 0.1655 |
| False-Positive-Rate difference | 0.0639 |
| Selection rate — White | 0.2059 |
| Selection rate — Asian-Pac-Islander | 0.2390 |
| Selection rate — Black | 0.0920 |
| Selection rate — Amer-Indian-Eskimo | 0.0851 |
| Selection rate — Other | 0.0813 |

### Global

| Metric | Value |
|---|---:|
| Accuracy (y_true vs y_pred) | 0.854 |
| True positive rate (global) | 0.239 |
| Predicted positive rate | 0.194 |

Both `sex` and `race` **fail the 4/5ths rule** (DP ratio < 0.80 → the
disparate-impact legal threshold): the engine correctly fires this warning.

## Literature baseline comparison

| Source | Attribute | Metric | Published | Ours | Δ |
|---|---|---|---:|---:|---:|
| Fairlearn tutorial (LR, unmitigated) | sex | DP difference | ~0.18 | 0.173 | −0.007 |
| Agarwal et al. 2018 Table 3 (LR) | sex | DP difference | ~0.188 | 0.173 | −0.015 |
| Bellamy et al. 2018 (AIF360, LR) | sex | Statistical-parity difference | ~0.19 | 0.173 | −0.017 |
| Fairlearn tutorial (LR, unmitigated) | sex | DP ratio | ~0.31 | 0.311 | +0.001 |
| Agarwal et al. 2018 Table 3 (LR) | race | DP difference (White vs Black) | ~0.10 | 0.114 | +0.014 |
| Fairlearn MetricFrame (5-class race, full min-max) | race | DP difference | ~0.15-0.16 | 0.158 | ~0 |

All deltas are within the ±0.02 tolerance requested. The fairness engine
reproduces published Adult numbers. The small shift vs Agarwal 2018 sex DP
difference (−0.015) is within the range attributable to OpenML v2 vs v1,
solver defaults (`lbfgs`), and the 70/30 stratified train/score split.

## Caveats for NyayaAI reviewers

- Adult is a US benchmark. It does not exercise our India-context metrics
  (SPLS, DLF, LRB). Those are validated on MUDRA-Lite.
- `sex` is binary-coded here; NyayaAI's taxonomy treats `THIRD` as
  first-class. We preserve the binary coding only to match the literature.
- We use a *blind* model (no sensitive features). Disparities here come
  from proxies (occupation, marital-status, hours-per-week).
- Ding et al. 2021 (*Retiring Adult*) show that moving the income
  threshold flips privileged/unprivileged orderings. Adult is a
  reproducibility anchor, not a sociologically meaningful benchmark.

## Reproduce

```
uv sync
bash benchmarks/uci-adult/run.sh
```

Expected runtime: ~30 s on an 8-vCPU Mac. Final `artifacts/report.json`
determinism hash must start with `e821e5e38d34f26e` when seed, data
version, and library versions above are unchanged.
