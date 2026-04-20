# SECURITY — Control Matrix

Operational security controls. For vulnerability reporting see root `/SECURITY.md`.

Owner: `infra-security-engineer`.

## Identity & access

- Workload Identity Federation only — zero service-account keys in the repo or CI.
- IAM roles: `auditor`, `reviewer`, `admin`, `citizen`, `ombudsman`, `support`. Defined in `infra/terraform/modules/iam/`.
- Break-glass: admin role requires 2-person GitHub environment approval for prod.
- Session: 12h max; re-auth for admin actions.

## Network

- VPC Service Controls perimeter around every fairness workload and BigQuery dataset.
- Identity-Aware Proxy in front of admin surfaces.
- Egress restricted to Google APIs + named allow-list.

## Data

- CMEK on every GCS bucket, BQ dataset, Firestore DB, Pub/Sub topic.
- Sensitive Data Protection (formerly Cloud DLP) templates for Indian PII: Aadhaar, PAN, voter ID, phone, UPI, GSTIN, caste-marker surnames.
- Pseudonymisation before any cross-agent tool call.
- Audit log hash-chain (SHA-256) for each report; signed with a KMS key.

## Model security

- Model Armor applied to every Gemini prompt (input + output).
- System prompts are versioned and signed; prompt-injection red-team suite gates every release.
- No user-controlled tool arguments without Pydantic/Zod validation.

## Supply chain

- Snyk + OSV scan on every PR; high-severity blocks merge.
- Renovate bot for dependency updates.
- SLSA Level 2 provenance on container builds.
- pnpm + uv lockfiles committed.

## Secrets

- Google Secret Manager for runtime secrets.
- gitleaks pre-commit hook + CI scan.
- No secrets in env files committed to the repo (`.env.example` only).

## Monitoring

- Cloud Logging sinks to a dedicated security project.
- Alerts: failed auth spike, VPC-SC violation, DLP finding, IAM policy drift.
