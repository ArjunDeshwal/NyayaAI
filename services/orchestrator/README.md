# services/orchestrator — ADK multi-agent system

Six LLM-backed agents coordinated by an ADK orchestrator. Owner subagent: `agent-architect`.

| Agent | Model | Role |
|---|---|---|
| Planner | gemini-3.1-pro-preview | Drafts the audit plan |
| Counterfactual | gemini-3-flash-preview + imagen-4 | Generates synthetic test populations |
| Root-Cause | gemini-3.1-pro-preview + Vertex XAI + SHAP + LIT | Explains why bias exists |
| Remediation | gemini-3.1-pro-preview + Fairlearn reductions | Applies mitigation; opens a GitHub PR |
| Narrator | gemini-3.1-pro-preview + imagen-4 + Chirp | Generates bilingual audit PDF |
| Watcher | gemini-3-flash-preview | Post-deploy drift monitoring |

The seventh agent — **Fairness Metrics** — is deliberately classical (Python) and lives in `services/fairness/`. Don't add LLMs there.

## Stack

- Python 3.12 · FastAPI
- Agent Development Kit (`adk`)
- Vertex AI Agent Engine (runtime)
- Firebase Genkit (TypeScript) for evals — `evals/`
- Model Armor on every call
- Sensitive Data Protection (SDP) pre-LLM

## Layout

```
src/
  agents/       One file per agent
  tools/        Typed tool functions (Pydantic in/out)
  config/       Model IDs, Model Armor, SDP templates
evals/          TypeScript Genkit eval harness + goldens
tests/          Unit + integration
```

## Run

```bash
uv sync
uv run uvicorn src.main:app --reload
```

## Evals

```bash
cd evals && pnpm install && pnpm run eval
```

Gate: ≥95% pass rate on all goldens.
