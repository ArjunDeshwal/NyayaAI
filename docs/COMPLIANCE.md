# COMPLIANCE — DPDP Rule 13 + EU AI Act Control Matrix

Owner: `compliance-auditor` subagent. Regenerated on every audit run (`make compliance-report`).

## DPDP Act 2023 + DPDP Rules 2025

Rules notified 2025-11-13; enforcement of core operative rules by 2027-05-12. NyayaAI treats Rule 13 (Significant Data Fiduciary DPIA) as the floor because our clients are.

| DPDP requirement | NyayaAI control | Evidence artifact |
|---|---|---|
| Notice (§5) | Plain-language consent screen (English + 4 languages), purpose-specific | `apps/flutter/lib/features/consent/` |
| Purpose limitation (§7) | Purpose recorded per-audit; Fairness agent refuses to process outside declared purpose | `services/orchestrator/src/agents/planner.py` |
| Data minimisation (§8(3)) | Only protected + outcome columns; raw PII never leaves client VPC when Sensitive Data Protection pseudonymisation is enabled | `services/fairness/src/ingest/` |
| Accuracy (§8(3)) | Dataset card required; schema validation; reject if >5% nulls on protected attrs | `benchmarks/*/dataset.card.md` |
| Storage limitation (§8(7)) | BQ table-retention + GCS object-retention 395 days default | `infra/terraform/modules/bigquery/` |
| Security safeguards (§8(5)) | CMEK, VPC-SC, IAM least-privilege, Model Armor, Workload Identity Federation | `docs/SECURITY.md` |
| Breach notification (§8(6)) | 72h pipeline → Board + affected principals; Cloud Logging sink | `services/watcher/` |
| Grievance (§8(10)) | Grievance Officer email + Ombudsman role in IAM | `CODEOWNERS`, `infra/terraform/modules/iam/` |
| Rule 13 DPIA | Auto-generated DPIA PDF per audit | `services/reporter/src/templates/dpia.html` |
| Rule 14 audits | Annual third-party audit hooks | `docs/COMPLIANCE.md#annual-audit` |

## EU AI Act (Regulation (EU) 2024/1689)

High-risk obligations enforceable 2026-08-02. Mapping:

| Article | Requirement | NyayaAI control |
|---|---|---|
| Art. 9 | Risk management system | Risk register auto-attached to every report |
| Art. 10 | Data governance: representativeness, bias examination | India-taxonomy checks + SPLS/LRB/DLF metrics |
| Art. 13 | Transparency + instructions for use | Model card per agent in `docs/MODEL_CARDS/` |
| Art. 14 | Human oversight | Reviewer approval gate before report sign-off |
| Art. 15 | Accuracy, robustness, cybersecurity | Genkit eval ≥95%, red-team suite, Model Armor |

## SDG sub-targets

Primary: **10.3** (ensure equal opportunity, eliminate discriminatory practices). Secondary: **16.6** (effective, accountable institutions), **5.5** (women's participation).

## Annual audit

External audit by a CERT-In empanelled auditor. Report filed with Data Protection Board within 30 days.
