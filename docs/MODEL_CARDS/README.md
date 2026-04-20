# MODEL_CARDS — One Card per Gemini-Backed Agent

Owner: `agent-architect`. Follows Google's model-card schema + EU AI Act Art. 13.

## Required cards

- `planner.md` — Planner Agent (Gemini 3.1 Pro)
- `counterfactual.md` — Counterfactual Agent (Gemini 3 Flash)
- `root-cause.md` — Root-Cause Agent (Gemini 3.1 Pro + SHAP tool)
- `remediation.md` — Remediation Agent (Gemini 3.1 Pro)
- `narrator.md` — Narrator Agent (Gemini 3 Flash + Chirp TTS)
- `watcher.md` — Watcher Agent (Gemini 3.1 Flash-Lite)

The Fairness Metrics agent is intentionally classical (Fairlearn + our custom metrics); no model card needed — see `packages/fairlearn-extensions/README.md`.

## Card contents (minimum)

1. Model ID and version
2. Intended use + out-of-scope use
3. Training data (Google-managed) and evaluation data (ours)
4. Metrics: Genkit eval score, red-team pass rate, latency p50/p95
5. Limitations (hallucination rate on OOD datasets, language coverage)
6. Ethical considerations (protected-attribute inference, Model Armor posture)
7. Release notes
