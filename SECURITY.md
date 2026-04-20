# Security Policy

NyayaAI handles sensitive data for compliance audits. Security is non-negotiable.

## Supported versions

Only `main` and the latest tagged release receive security fixes during the GSC 2026 build window.

## Reporting a vulnerability

**Do not file a public GitHub issue.**

Email `security@nyayai.app` with:
- Affected component
- Reproduction steps
- Impact assessment
- Suggested remediation (if any)

We respond within 48 hours.

## Scope

In scope:
- Data exfiltration from NyayaAI-hosted infrastructure.
- Bypass of Model Armor, Sensitive Data Protection (SDP), VPC Service Controls, or CMEK.
- Bypass of Firebase App Check.
- Auth/RBAC bypass (`nyayai.auditor` → `nyayai.admin`, etc.).
- Prompt-injection that causes exfiltration or privilege escalation.
- Compromise of a signed audit PDF's hash in the retention-locked Cloud Storage log.

Out of scope:
- DoS through uploaded multi-gigabyte datasets (rate-limiting is the planned mitigation).
- Social engineering of the core team.
- Issues in third-party services (Vertex AI, Firebase) — report to Google directly.

## Controls summary

See `docs/SECURITY.md` for the full control matrix (VPC-SC, CMEK, SDP, Model Armor, differential privacy, Cloud Audit Logs, WIF, etc.).

## Responsible disclosure

We credit reporters on `/docs/SECURITY.md` after a fix is shipped, unless anonymity is requested.
