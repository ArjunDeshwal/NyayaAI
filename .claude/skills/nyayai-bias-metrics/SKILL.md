---
name: nyayai-bias-metrics
description: NyayaAI project skill. Use when running, implementing, wrapping, or reviewing fairness/bias metrics (demographic parity, equalized odds, disparate impact, calibration, counterfactual fairness, intersectional slicing). Covers Fairlearn wrapping, Vertex AI Model Evaluation Fairness, and NyayaAI's custom India-context metrics (surname-proxy leakage, linguistic-register bias, digital-literacy fairness). Invoke when user asks to add a metric, compute fairness on a model, debug a metric, or write tests for the fairness engine.
---

# NyayaAI Bias Metrics

Authoritative guide to NyayaAI's fairness-metric layer. **Read this before touching `services/fairness/` or `packages/fairlearn-extensions/`.**

## Scope

NyayaAI's Fairness Metrics agent (Agent 3 in `IMPLEMENTATION_PLAN.md` §6) is the only non-LLM agent — it's deterministic classical math. Keeping it classical is a rubric decision: LLM judges penalize overuse of LLMs for tasks a library can do. Do not "improve" this by adding Gemini here.

## Metric suite (all P0)

### Group fairness (classification)

| Metric | Fairlearn call | Notes |
|---|---|---|
| Demographic Parity Difference | `demographic_parity_difference` | Report alongside DP Ratio |
| Demographic Parity Ratio | `demographic_parity_ratio` | 4/5ths rule threshold 0.8 |
| Equalized Odds Difference | `equalized_odds_difference` | Max of TPR & FPR gaps |
| Equal Opportunity Difference | Custom — TPR gap only | True-positive-rate parity only |
| Disparate Impact | DP ratio; alias in report for legal audiences | Same math |
| Selection Rate | `selection_rate` per slice | Always included |

### Calibration

- Expected Calibration Error (ECE) — ours: 15-bin quantile; also report subgroup ECE.
- Brier score overall + per slice.
- Reliability diagrams shipped as SVG in report.

### Individual fairness

- **Counterfactual Individual Fairness**: percentage of units whose prediction flips when only the protected attribute changes (using Counterfactual agent's output). Threshold: ≥95% stable.

### Intersectional slicing (MANDATORY for India)

Always compute these slices by default:
- `rural × female × SC/ST`
- `urban × Muslim × 18–25`
- `disabled × rural`
- `Hindi-mother-tongue × low-income`
- `third-gender × any`
- `elderly × digital-literacy-q1`

Report cell-level CIs (bootstrap, 1000 resamples). When subgroup `n < 100`, apply differential privacy via `from dp_accounting import ...` with ε ≤ 1.0 and mark the cell `DP-protected`.

### Custom India metrics (shipped in `packages/fairlearn-extensions/`)

1. **Surname-proxy leakage score (SPLS)** — AUC of a classifier trained to predict `caste` from supposedly non-caste features. Target: SPLS ≤ 0.55 (near chance). Inputs: `df, protected_col, nonprotected_cols`.
2. **Linguistic-register bias (LRB)** — measures mean outcome shift between identical content in pure-English vs code-mixed Hindi-English vs transliterated Hindi. Requires Counterfactual agent's text output.
3. **Digital-literacy fairness (DLF)** — outcome parity across typing-cadence quartiles; proxy for computer-literacy.

All three should have:
- Pure-python implementation (no Gemini).
- Property-based tests (Hypothesis): symmetry, scale-invariance, bounds.
- Docstring citing why this metric exists (regulatory or academic source).

## Wrapping policy

- **Wrap Fairlearn; don't reimplement.** If Fairlearn has it, use their function and decorate with our CI/DP layer.
- **Wrap Vertex AI Model Evaluation Fairness** for classification when the model lives in Vertex — cheaper than re-fetching predictions.
- AIF360 is abandoned — do **not** take a dependency on it.
- What-If Tool is superseded — LIT only, programmatic API (`lit_nlp`).

## Output contract

Every metric run produces a `MetricsReport` Pydantic model:

```python
class SliceMetric(BaseModel):
    slice_key: dict[str, str]       # e.g. {"caste":"SC","gender":"F","rural":"true"}
    n: int
    metrics: dict[str, float]        # {"dp_diff": 0.23, "ece": 0.08, ...}
    ci_95: dict[str, tuple[float,float]]
    dp_protected: bool = False

class MetricsReport(BaseModel):
    model_id: str
    dataset_id: str
    audit_id: str
    computed_at: datetime
    protected_attrs: list[str]
    global_metrics: dict[str, float]
    slice_metrics: list[SliceMetric]
    custom_india_metrics: dict[str, float]  # SPLS, LRB, DLF
    warnings: list[str]
```

## Test requirements (gate for CI)

- Unit tests reproduce literature baseline numbers on UCI Adult and COMPAS within 0.01 absolute error.
- Property test: DP difference is anti-symmetric under group swap.
- Property test: ratios in [0,1]; differences in [-1,1].
- Integration test: full run on MUDRA-Lite 50K-row synthetic loan dataset completes in <60s on 8 vCPU.
- Snapshot test: MUDRA-Lite report JSON matches committed golden.

## Do not

- Do not add Gemini "for explanation" — that is the Root-Cause agent's job (Agent 4).
- Do not compute causal fairness (mediation analysis) in P0 — future work.
- Do not treat "caste" as a default column name — use the India-taxonomy schema loader.
- Do not return raw predictions; return aggregated + DP-protected metrics only.

## See also

- `packages/india-taxonomy/` — protected-attribute schema
- `IMPLEMENTATION_PLAN.md` §6 Agent 3, §7 India taxonomy
- `.claude/skills/nyayai-india-taxonomy/SKILL.md`
