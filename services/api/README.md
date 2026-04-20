# services/api — Edge API Gateway

Cloud Run FastAPI service at the edge. Everything client-facing enters here.

Responsibilities:
- Firebase Auth + MFA verification
- IAM RBAC enforcement
- App Check token verification
- **Model Armor** inbound shield on all LLM-bound payloads
- **Sensitive Data Protection** redaction before forwarding to LLM services
- Rate limiting + Cloud Armor WAF integration
- Dispatch to orchestrator / fairness / reporter / watcher

Owner: `infra-security-engineer`, `agent-architect` (for Model Armor config).

## Stack

- Python 3.12 · FastAPI
- Cloud Run (internal VPC connector) · asia-south1

## Run

```bash
uv sync
uv run uvicorn src.main:app --reload
```
