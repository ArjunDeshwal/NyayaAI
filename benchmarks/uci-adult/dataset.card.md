# UCI Adult — dataset card

## Summary

UCI Adult (also known as "Census Income") is the canonical US-context
classification benchmark for fairness research. NyayaAI uses it as a
reproducibility check: our fairness engine must land within published
tolerance of Fairlearn / AIF360 baseline numbers, or we have a bug.

- **48,842 rows** (canonical full train+test, OpenML version 2, de-duplicated).
- **Seed 42** is the canonical reproduction seed.
- **Task**: binary classification — does an individual earn more than $50K/yr
  based on 1994 Census extract features?
- **Sensitive attributes**: `sex` (Male / Female), `race` (5 categories).
- **Baseline model**: a *blind* logistic regression (sensitive attributes
  removed from features) — this mirrors the Fairlearn tutorial baseline so
  our numbers are directly comparable to published literature.

## Provenance

Loaded from **OpenML** (dataset id 1590, version 2) via
[`sklearn.datasets.fetch_openml`](https://scikit-learn.org/stable/modules/generated/sklearn.datasets.fetch_openml.html).
OpenML mirrors the original UCI archive upload (Kohavi 1996) and is the
authoritative source used by Fairlearn's own documentation examples. The
older UCI archive text files are frequently unavailable and inconsistently
formatted across versions.

- **Original release**: Kohavi & Becker, 1996, extracted from the 1994 US
  Census Bureau Current Population Survey.
- **OpenML mirror**: https://www.openml.org/d/1590

## Licence

**Public Domain** (US federal data — 1994 Census extract is not
copyrightable under 17 U.S.C. § 105). OpenML redistribution is unrestricted.

## Columns

| Column | Type | Notes |
|---|---|---|
| `sex` | string | Male / Female — **sensitive** |
| `race` | string | White / Black / Asian-Pac-Islander / Amer-Indian-Eskimo / Other — **sensitive** |
| `income_high` | int | Binary target: 1 if > $50K/yr else 0 |
| `model_score` | float | Blind-LR probability of `income_high=1` |
| `age` | float | Years |
| `fnlwgt` | float | Census final weight |
| `education-num` | float | Years of education (ordinal) |
| `capital-gain` | float | USD |
| `capital-loss` | float | USD |
| `hours-per-week` | float | Worked hours / week |
| `workclass` | string | Private / Self-emp / Gov / etc. |
| `education` | string | Bachelors / HS-grad / etc. |
| `marital-status` | string | 7 categories |
| `occupation` | string | 14 categories |
| `relationship` | string | 6 categories |
| `native-country` | string | 42 countries (mostly US) |

## Intended uses

- Regression test for NyayaAI's fairness engine: the Adult-sex DP difference
  is a classical reproducible number (Fairlearn / AIF360 publish values).
- Tutorial fixture for classroom fairness demos.
- Sanity anchor when changing internals of `packages/fairlearn-extensions/`.

## Not intended for

- Making claims about income inequality in 2026 (data is from 1994).
- Training any production system — it encodes 1990s US labour-market
  stereotypes and has well-documented construct-validity problems
  (Ding et al., *Retiring Adult*, NeurIPS 2021).
- Comparing against India-context benchmarks such as MUDRA-Lite — the
  attribute taxonomy (caste, religion, habitation) is absent here.

## Known limitations

- **Construct validity**: the "> $50K" threshold is a 1994 US artifact;
  Ding et al. 2021 show that moving the threshold changes the
  privileged / unprivileged ordering.
- **Class imbalance**: ~24% positive label.
- **Racial group sizes are uneven**: White ≈ 41,762; Other ≈ 406. Small
  groups produce high-variance rates; we set `min_slice_n=30` when running
  the audit to guard against tiny-cell artifacts (`Amer-Indian-Eskimo` has
  n=470 overall but its intersectional slices are small).
- **`sex` is coded binary** (Male / Female). This is a 1994 artefact and
  does not reflect NyayaAI's own India-taxonomy stance that gender has a
  first-class `THIRD` value (Transgender Persons Act 2019). The blind
  baseline here is NOT a statement about gender coding; it is faithful to
  the published benchmark.

## Reproducibility

```
uv run python benchmarks/uci-adult/fetch.py \
    --out benchmarks/uci-adult/data/adult.parquet --seed 42
```

Any change to this file, `fetch.py`, or the pinned scikit-learn / numpy /
pandas / Fairlearn versions invalidates the literature-comparison numbers
in `REPORT.md`.

## References

- Kohavi, R. (1996). *Scaling Up the Accuracy of Naive-Bayes Classifiers:
  A Decision-Tree Hybrid.* KDD-96.
- Bellamy, R. K. E. *et al.* (2018). *AI Fairness 360: An extensible toolkit
  for detecting, understanding, and mitigating unwanted algorithmic bias.*
  IBM arXiv:1810.01943.
- Agarwal, A. *et al.* (2018). *A Reductions Approach to Fair Classification.*
  ICML 2018 (arXiv:1803.02453).
- Ding, F. *et al.* (2021). *Retiring Adult: New Datasets for Fair Machine
  Learning.* NeurIPS 2021.
