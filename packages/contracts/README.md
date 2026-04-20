# packages/contracts — Shared Schemas

Single source of truth for every data structure that crosses a service boundary.

- Pydantic v2 for Python consumers (`services/*`, `packages/fairlearn-extensions`)
- Dart classes for Flutter (`apps/flutter`) — generated via `openapi-generator`
- Zod schemas for TypeScript (`services/orchestrator/evals`, `apps/admin`) — generated

## Core types

- `AuditPlan` — Planner agent output
- `CounterfactualBatch` — Counterfactual agent output
- `MetricsReport` · `SliceMetric` — Fairness agent output
- `RootCauseReport` — Root-Cause agent output
- `RemediationPR` — Remediation agent output
- `AuditBundle` — Narrator input (everything combined)

## Workflow

1. Edit Python Pydantic model in `src/`.
2. `make contracts.sync` regenerates Dart + TS.
3. Commit all three. Drift across languages is a CI failure.
