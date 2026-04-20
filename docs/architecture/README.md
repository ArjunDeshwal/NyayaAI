# architecture — Diagrams

Mermaid sources committed; PNG renders committed next to them so LLM judges' OCR reads the picture.

## Files

- `system-context.mmd` / `.png` — NyayaAI in its ecosystem (citizen, auditor, reviewer, government, NGO)
- `agents.mmd` / `.png` — 7-agent orchestration
- `data-flow.mmd` / `.png` — Dataset ingestion → metric compute → report
- `security.mmd` / `.png` — VPC-SC perimeter, IAM roles, Model Armor, CMEK
- `deployment.mmd` / `.png` — Cloud Run + Vertex Agent Engine + Firestore + BQ

Regenerate PNGs with `make architecture`.
