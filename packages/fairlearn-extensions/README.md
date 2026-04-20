# packages/fairlearn-extensions — NyayaAI's Custom India Metrics

Metrics that Fairlearn doesn't have. Owner subagent: `fairness-engineer`.

## Metrics

1. **SPLS — Surname-Proxy Leakage Score**
   AUC of a classifier trained to predict the protected attribute (usually caste) from features the user claims are "not protected." Target: ≤0.55 (near chance).

2. **LRB — Linguistic-Register Bias**
   Mean outcome shift across three linguistic registers of identical content: pure English, code-mixed Hindi-English, transliterated Hindi. Uses Counterfactual agent's text outputs.

3. **DLF — Digital-Literacy Fairness**
   Outcome parity across typing-cadence quartiles. Protects against models that silently penalize slow typists (elderly, disabled, rural).

## Invariants (property tests, Hypothesis)

- Symmetry under group swap (DP difference).
- Ratios in [0,1]; differences in [-1,1].
- Scale-invariance for rate-based metrics.

## Not here

- Standard DP/EO/DI metrics — those are Fairlearn's; we wrap, don't reimplement.
- Explainability (SHAP/XAI) — those live in the Root-Cause agent.
