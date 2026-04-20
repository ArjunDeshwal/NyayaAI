# NyayaAI — Guidance for Claude Code

This file is auto-loaded into every Claude Code session. Keep it short. Deep details live in `IMPLEMENTATION_PLAN.md`, `.claude/skills/`, and `.claude/agents/`.

## What this is

NyayaAI is a GSC 2026 submission: an agentic, India-aware bias auditor for public-interest AI. See [`IMPLEMENTATION_PLAN.md`](IMPLEMENTATION_PLAN.md) for the full 25-section plan.

## Read these before acting

- Always: the section of `IMPLEMENTATION_PLAN.md` relevant to the task.
- If touching fairness metrics: `.claude/skills/nyayai-bias-metrics/SKILL.md` + `.claude/skills/nyayai-india-taxonomy/SKILL.md`.
- If touching LLM agents: `.claude/skills/nyayai-adk-agent-patterns/SKILL.md`.
- If touching compliance / PII / audit reports: `.claude/skills/nyayai-dpdp-compliance/SKILL.md`.
- If writing anything a judge will read: `.claude/skills/nyayai-gsc-submission/SKILL.md`.

## Delegate to the right subagent

| Domain | Subagent |
|---|---|
| Fairness metrics, benchmarks, Fairlearn wrapping | `fairness-engineer` |
| ADK agents, prompts, Genkit evals, tool contracts | `agent-architect` |
| Flutter app, a11y, voice, Nano offline, releases | `flutter-engineer` |
| DPDP / EU AI Act, PII, audit PDFs | `compliance-auditor` |
| README, deck, video, portal, NGO emails | `gsc-submission-reviewer` |
| Narrative, demo scenario, outreach, pilots | `product-research-lead` |
| Terraform, IAM, VPC-SC, CI/CD, secrets | `infra-security-engineer` |

## Hard rules

1. **Use correct 2026 Google names.** See `.claude/skills/nyayai-gsc-submission/SKILL.md` deprecation table. An outdated name in user-visible content is a blocker.
2. **Fairness engine is classical, not LLM.** Don't add Gemini to `services/fairness/`.
3. **Every LLM call goes through Model Armor + Sensitive Data Protection.** Never bypass.
4. **India taxonomy schema is the source of truth** for protected attributes. Don't hard-code caste/religion strings.
5. **Four-person team attribution** on every submission artifact.
6. **The demo video is sacred.** Engineering decisions serve the 96-second video.

## Project stack (current)

- Gemini 3.1 Pro · Gemini 3 Flash · Gemini Nano 4 (AICore Dev Preview)
- Imagen 4 · Chirp · Google Speech-to-Text
- Agent Development Kit (Python) · Vertex AI Agent Engine · Firebase Genkit (TS, for evals)
- Vertex AI Model Evaluation (Fairness) · Vertex Explainable AI · LIT · Model Armor · Sensitive Data Protection
- Flutter · Firebase AI Logic (`firebase_ai`) · Firebase Auth/Firestore/Hosting/App Check
- BigQuery · Cloud Storage (CMEK) · Pub/Sub · Vertex AI Pipelines · Vertex AI Model Registry
- Cloud Run · VPC Service Controls · Cloud KMS · Identity-Aware Proxy · Secret Manager
- asia-south1 (Mumbai) primary; asia-south2 (Delhi) DR
- Apache-2.0

## Don't

- Don't create documentation files (`*.md`) unless the task explicitly requires it.
- Don't add emojis unless explicitly requested.
- Don't use deprecated names (PaLM, Bard, Gemini 1.x, Cloud DLP, Agent Builder alone, `firebase_vertexai`, `google_generative_ai` Dart, Agentspace, Imagen 3).
- Don't mock the fairness engine in integration tests — always use real Fairlearn on real (possibly synthetic) data.
- Don't push anywhere without asking — destructive/shared actions require explicit confirmation.
