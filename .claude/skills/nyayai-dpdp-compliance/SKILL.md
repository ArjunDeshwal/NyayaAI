---
name: nyayai-dpdp-compliance
description: NyayaAI project skill. Use when mapping audit output to Indian DPDP Act 2023 Rule 13 DPIA requirements or EU AI Act Articles 9/10/13/14/15, when writing the Narrator agent's report templates, when a PR touches PII handling, or when the user asks about compliance, DPIA, data-protection impact, or EU AI Act conformity. Covers the full compliance mapping table shipped in /docs/COMPLIANCE.md.
---

# DPDP + EU AI Act Compliance Mapping

The auto-generated audit PDF is a GSC differentiator and NyayaAI's commercial hook. This skill is the canonical mapping from audit artifact to regulatory requirement.

## Regimes covered

1. **DPDP Act 2023 + DPDP Rules 2025** (notified 13 Nov 2025; full enforcement 12 May 2027).
2. **EU AI Act** (prohibitions in force 2 Feb 2025; GPAI obligations 2 Aug 2025; high-risk obligations 2 Aug 2026).
3. **RBI Digital Lending Directions** (8 May 2025) — audit-ready but not mandated.
4. **NITI Aayog #AIForAll principles** (reference, not regulation).

## DPDP Rule 13 DPIA mapping

Every audit PDF must contain these sections with the following content sourced from the audit:

| DPIA Section | Source in NyayaAI audit |
|---|---|
| (a) Purpose and nature of processing | User-supplied `audit.purpose` + model card metadata |
| (b) Categories of personal data | Protected-attribute enumeration (India taxonomy) + detected PII categories from SDP scan |
| (c) Risks to Data Principals | Top 5 slices by DP/EO gap; top 5 proxy features by SPLS |
| (d) Safeguards & mitigation | Remediation agent output; post-remediation metrics |
| (e) Residual risk | Gap between post-remediation metrics and regulatory thresholds |
| (f) Consultation with Data Protection Officer | Placeholder for user signoff — left blank; UI captures signature |

**DPDP Rule 12 breach notification** is a separate flow (not in DPIA): if the Watcher agent detects a drift breach, the Pub/Sub breach-notifier microservice drafts a 72-hour notification to DPB.

## EU AI Act Article mapping

| Article | Obligation | NyayaAI artifact |
|---|---|---|
| Art. 9 — Risk management | Continuous risk-management system | Watcher agent's drift-monitoring mode + risk register section of PDF |
| Art. 10 — Data & data governance | Quality/representativeness of training data; examination for bias | Counterfactual coverage report + dataset bias analysis by Root-Cause agent |
| Art. 13 — Transparency | Provide info to deployers on capabilities & limitations | Auto-generated model card (one per audited model) |
| Art. 14 — Human oversight | Measures for natural person oversight | "Reviewer approval" UI gate before remediation PR merges |
| Art. 15 — Accuracy, robustness, cybersecurity | Appropriate levels, resilience to errors, cybersec | Robustness + counterfactual stability metrics; Model Armor evidence |

When the user sets `audit.regimes = ["DPDP", "EU_AI_ACT"]`, the Narrator agent emits both the DPIA and a conformity-report annex.

## Required PII redaction (SDP templates)

Before any LLM call, run SDP with these infoTypes (DPDP-aligned):

- `INDIA_AADHAAR_INDIVIDUAL` (12-digit Aadhaar with checksum)
- `INDIA_PAN_INDIVIDUAL`
- `PHONE_NUMBER` (E.164 India rules)
- `EMAIL_ADDRESS`
- `DATE_OF_BIRTH`
- `STREET_ADDRESS`
- `PERSON_NAME` (warn-only, not redact — too lossy for audits)
- Custom: `INDIA_VOTER_ID`, `INDIA_RATION_CARD`

Redaction mode: `REPLACE_WITH_INFO_TYPE`. Original value is preserved only in the classical fairness engine (which runs inside VPC-SC and doesn't call LLMs).

## Documents to generate per audit

1. **Primary Audit PDF** — bilingual (EN + one of HI/TA/BN). DPIA + metric tables + narrative.
2. **EU AI Act Conformity Annex** — if regime includes `EU_AI_ACT`.
3. **Machine-readable report** — JSON for downstream tooling.
4. **Model card** — Markdown + Protobuf (Google Model Card Toolkit schema).
5. **Reproducibility bundle** — dataset fingerprint (no data), model fingerprint, audit config, random seeds.

## Signing & tamper-evidence

- Each audit PDF is hash-signed (SHA-256) and the hash is committed to a public append-only log (Cloud Storage with object-retention locks) — prevents silent edits.
- If the user is DPDP-SDF (Significant Data Fiduciary), the audit PDF's metadata should note "SDF-applicable: true" and retention default flips to 7 years.

## Don't

- Don't claim the audit is a "certified DPIA" — only a DPO can certify. Use language "DPIA template aligned with DPDP Rule 13".
- Don't auto-submit to the DPB portal — P2 roadmap item only.
- Don't generate the EU AI Act conformity annex if the user's deployment region excludes the EU — avoid misleading compliance theatre.

## Citations for the Narrator agent's footnotes

- DPDP Act 2023: https://www.meity.gov.in/data-protection-framework
- DPDP Rules 2025 (notified 13 Nov 2025): https://www.dpdpa.com/dpdprules/
- EU AI Act text: https://eur-lex.europa.eu/eli/reg/2024/1689/oj
- RBI Digital Lending Directions 2025: https://rbi.org.in/

## See also

- `IMPLEMENTATION_PLAN.md` §9 Security, privacy, compliance
- `docs/COMPLIANCE.md` (generated from this skill + the plan)
- `.claude/skills/nyayai-bias-metrics/SKILL.md` — for the metrics referenced in each regulation
