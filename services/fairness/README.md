# services/fairness — Classical Fairness Metrics Service

Deterministic, non-LLM fairness computation. Wraps Fairlearn + Vertex AI Model Evaluation Fairness. Owner subagent: `fairness-engineer`.

## Why no Gemini here?

GSC rubric explicitly asks "could a simpler approach have worked?" — this is exactly the layer where the answer is yes. Fairness math is deterministic. Keeping it classical is a rubric win.

LLM-narrated explanations belong to the Root-Cause agent (in `services/orchestrator/`), not here.

## Metrics

See [`.claude/skills/nyayai-bias-metrics/SKILL.md`](../../.claude/skills/nyayai-bias-metrics/SKILL.md) for the full suite.

- Group fairness: DP diff/ratio, EO, EOpp, DI (4/5ths), selection rate, subgroup AUC
- Calibration: ECE, Brier, reliability diagrams
- Individual fairness: counterfactual stability (from Agent 2 outputs)
- Intersectional slices (caste × gender × rural/urban × language × age × disability)
- **Custom India metrics** (in `packages/fairlearn-extensions/`):
  - **SPLS** — Surname-Proxy Leakage Score
  - **LRB** — Linguistic-Register Bias
  - **DLF** — Digital-Literacy Fairness

## Differential privacy

When a subgroup has `n < 100`, subgroup metrics are DP-protected (Google DP library, ε ≤ 1.0).

## Stack

- Python 3.12 · FastAPI on Cloud Run (asia-south1)
- `fairlearn` 0.12.x · `scikit-learn` 1.6.x · `pandas` · `polars`
- `captum` (PyTorch XAI) · `shap` · `lit_nlp` (programmatic)
- `google-cloud-dlp` (Sensitive Data Protection)
- `dp_accounting` / Google DP lib

## Run

```bash
uv sync
uv run uvicorn src.main:app --reload
uv run pytest -q
```

## Benchmarks

Run all: `make benchmark` from repo root.

Each benchmark reproduces a published result within ±0.01 of the literature value as a sanity check.
