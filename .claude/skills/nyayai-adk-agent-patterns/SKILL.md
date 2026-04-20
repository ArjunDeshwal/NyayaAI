---
name: nyayai-adk-agent-patterns
description: NyayaAI project skill. Use when implementing, debugging, or modifying any of the 7 ADK agents (Planner, Counterfactual, Fairness Metrics, Root-Cause, Remediation, Narrator, Watcher) or the orchestrator that coordinates them. Invoke when adding a new tool to an agent, writing prompts, wiring Genkit evals, or reviewing agent code. Covers model selection rules, tool-contract schema, Model Armor integration, Genkit eval patterns, and the "why LLM?" justification per agent.
---

# NyayaAI Agent Implementation Patterns

Authoritative guide to `services/orchestrator/` — the ADK multi-agent system. **Read before editing any agent or adding a tool.**

## Agent roster

| Agent | Model | Kind |
|---|---|---|
| 1. Planner | `gemini-3.1-pro-preview` | LLM reasoning |
| 2. Counterfactual | `gemini-3-flash-preview` + Imagen 4 | LLM generation |
| 3. Fairness Metrics | Python (Fairlearn + custom) | **Classical, NOT LLM** |
| 4. Root-Cause | `gemini-3.1-pro-preview` + Vertex XAI + SHAP + LIT | LLM synthesis |
| 5. Remediation | `gemini-3.1-pro-preview` + Fairlearn | LLM + classical |
| 6. Narrator | `gemini-3.1-pro-preview` + Imagen 4 + Chirp | LLM generation |
| 7. Watcher | `gemini-3-flash-preview` (or `3.1-flash-lite` for polls) | LLM (cheap) |

## Model-selection rules

- **Reasoning / multi-step / long context** → Gemini 3.1 Pro (~1.05M ctx).
- **Throughput / cheap batch / polling** → Gemini 3 Flash.
- **Cheapest polls** → Gemini 3.1 Flash-Lite.
- **On-device / offline / rural citizen portal** → Gemini Nano 4 via AICore.
- **Image generation / counterfactual faces** → Imagen 4 Ultra (max quality) or Fast (batch).
- **TTS** → Chirp (multi-lingual: EN/HI/TA/BN).
- **STT** → Google Speech-to-Text streaming.

Do NOT use Gemini 1.x (deprecated), PaLM (decommissioned), or the shut-down `gemini-3-pro-preview`.

## Why-LLM justification (per agent)

Every agent must have a one-paragraph "Why is this an LLM?" section in its code docstring to satisfy the GSC rubric's "could a simpler approach have worked?" check. The Fairness Metrics agent's docstring must explicitly say "this is not an LLM because this is deterministic math". Judges look for this.

## ADK patterns

### Hierarchical agents

```python
from adk import Agent, transfer_to_agent

planner = Agent(
    name="planner",
    model="gemini-3.1-pro-preview",
    description="Plans a fairness audit.",
    tools=[list_dataset_columns, describe_model, check_policy_requirements, estimate_cost],
    instruction=PLANNER_INSTRUCTION,
)

orchestrator = Agent(
    name="orchestrator",
    model="gemini-3.1-pro-preview",
    sub_agents=[planner, counterfactual, fairness, root_cause, remediation, narrator, watcher],
    instruction=ORCHESTRATOR_INSTRUCTION,
)
```

Orchestrator delegates with `transfer_to_agent(...)`. Do not let a sub-agent invoke a sibling directly — always route through the orchestrator for tracing and policy enforcement.

### Tool contracts (mandatory)

Every tool is a typed Python function with a Pydantic input model and a clear output model. No `**kwargs`. No untyped dicts.

```python
class CheckPolicyRequirementsInput(BaseModel):
    regime: Literal["DPDP", "EU_AI_ACT", "RBI"]

class PolicyRequirements(BaseModel):
    mandatory_sections: list[str]
    protected_attrs_required: list[str]
    thresholds: dict[str, float]

def check_policy_requirements(input: CheckPolicyRequirementsInput) -> PolicyRequirements:
    ...
```

Tool docstrings become the LLM-visible tool description — keep them precise, one paragraph.

### Structured outputs

Agents that produce structured data (Planner → AuditPlan, Fairness → MetricsReport) must use Gemini's structured-output (`response_schema`) feature, not free-text parsing. Schema lives in `packages/contracts/`.

## Model Armor integration

Every LLM call goes through a Model Armor-shielded router. Specifically:
- **Inbound (user upload)** — dataset rows may contain prompt-injection in free-text columns. Model Armor `floor_settings.malicious_uri_filter` + `pi_and_jailbreak_filter` ON.
- **Outbound (agent-to-user)** — check for data leakage of training samples.
- Config in `services/api/model_armor.yaml`.

Do not bypass Model Armor, even in tests. Tests use the MA sandbox endpoint.

## Sensitive Data Protection (SDP) pre-processor

Any dataset row that reaches an LLM must first pass through SDP redaction with the India-context templates (see `nyayai-dpdp-compliance`). The redacted payload is what Gemini sees; the original value stays in the VPC-SC-perimeter fairness service only.

## Genkit eval harness (TypeScript)

Agent regression gate. Every agent has ≥30 goldens. Genkit's `@genkit-ai/evaluator` with a held-out Gemini 3.1 Pro as judge.

```ts
import { genkit } from 'genkit';
import { gemini31Pro } from '@genkit-ai/vertexai';

const ai = genkit({ plugins: [vertexAI()] });

const plannerEval = ai.defineFlow(
  { name: 'plannerEval', input: ..., output: ... },
  async (input) => runPlannerAgent(input),
);
```

**Why TypeScript Genkit and not Python:** Python Genkit is still Preview (0.5.0 as of Feb 2026, breaking changes possible). We use TS for evals and Python ADK for production agents.

Goldens are versioned in `services/orchestrator/evals/goldens/`. CI gates on ≥95% pass rate.

## Counterfactual-agent invariant

A counterfactual that changes more than the protected attribute is a bug, not a feature. Validation:

```python
def validate_counterfactual(original: Row, generated: Row, protected: str) -> bool:
    diffs = {k for k in original.keys() if original[k] != generated[k]}
    return diffs.issubset({protected})
```

For text/image counterfactuals, we accept small appearance changes but run a reverse-classifier ("can a model tell which is the counterfactual?") — target ≤55% accuracy.

## Observability

- Every agent call emits an OTLP span → Cloud Trace.
- Span attributes: `agent.name`, `model.id`, `tokens.in`, `tokens.out`, `cost.usd`, `latency_ms`.
- Spans aggregated into Firestore per `audit_id` and streamed into the Flutter UI — **judges see the live agent trace in the demo**; keep the trace output legible.

## Testing

- Unit test each tool with mocked Gemini.
- Contract test (Pydantic validators) for every structured input/output.
- Integration test: full orchestrator run on MUDRA-Lite dataset end-to-end, <7 min wall-clock.
- Eval test: Genkit goldens ≥95% pass, CI-gated.

## Do not

- Do not add a new agent without a "Why LLM?" justification in its docstring.
- Do not call one sub-agent from another directly — route through orchestrator.
- Do not bypass Model Armor or SDP in any code path that might reach production.
- Do not use Python Genkit for production flows (preview).
- Do not hard-code model IDs inline — use `config.models.reasoning` / `config.models.flash` from `services/orchestrator/config.py`.

## See also

- `IMPLEMENTATION_PLAN.md` §5, §6, §11, §15, §16
- `.claude/skills/nyayai-bias-metrics/SKILL.md` (for what Agent 3 does)
- `.claude/skills/nyayai-dpdp-compliance/SKILL.md` (for what Agent 6 emits)
