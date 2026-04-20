# benchmarks — Reproducible Audit Reports

NyayaAI dogfoods itself: we run the tool on well-known datasets and commit the reports. This is a direct theme-match for GSC 2026 ("Unbiased AI Decision") and a strong technical-credibility signal.

## Datasets

| Folder | Source | Purpose |
|---|---|---|
| `uci-adult/` | UCI Machine Learning Repository, Adult (Census Income) | Canonical fairness benchmark — verify we reproduce published values |
| `compas/` | ProPublica's release | Criminal-risk-score benchmark — matches their 2016 finding |
| `obermeyer-repro/` | Re-implementation of Obermeyer et al., *Science* 2019, on public proxy data | Reproduces the "fix raises Black enrolment 17.7% → 46.5%" finding |
| `mudra-lite/` | Synthetic — built from public Census 2011 district demographics | NyayaAI demo-video centerpiece: DI 0.61 → 0.94 |
| `indian-bhed/` | Khandelwal et al., FAccT 2024 templates | Caste/religion LLM-bias probe |

## Running

```bash
make benchmark                # all
make benchmark.uci-adult      # one
```

Each folder contains:
- `run.sh` — reproducible entrypoint
- `dataset.card.md` — provenance, license, limitations
- `report.md` — committed gold report (regenerated on every run; CI gates on numeric stability)
- `report.json` — machine-readable
- `artifacts/` — generated PDFs, charts
