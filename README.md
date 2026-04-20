# NyayaAI — Agentic Bias Auditor for Public-Interest AI in India

> **Google Solution Challenge 2026 · Theme: Unbiased AI Decision · Track: Open Innovation**
>
> UN SDG **10.3** (eliminate discriminatory practices) · **16.6** · **16.7** · **5.b** · **9.c**
>
> Apache-2.0 · asia-south1 (Mumbai) · [`nyayai.app`](https://nyayai.app) (coming soon)

**NyayaAI** is the first agentic, multi-modal, India-aware bias auditor. Seven specialist Gemini agents *plan* an audit, *synthesize* counterfactual populations, *measure* fairness, *explain* root causes, *remediate* by opening a GitHub PR, *narrate* a DPDP Rule 13 DPIA and EU AI Act conformity annex in four Indian languages, and *watch* production models for drift.

Built by a 4-person team for citizens, policy officers, and compliance teams who need algorithmic fairness auditable — not just discussed.

---

## Why this matters

- **15.1M people** affected by Aadhaar-based PDS exclusion in Jharkhand alone (Muralidharan, Niehaus & Sukhtankar, NBER 2020).
- **1.86M ration cards** cancelled by Telangana's Samagra Vedika algorithm with no appeal mechanism (Amnesty, 2024).
- **26,000 families** wrongly accused by the Dutch childcare-benefits algorithm (Amnesty, 2021).
- **200M patients** were scored by a biased US care-management algorithm — fixable when audited (Obermeyer et al., *Science*, 2019).

Existing tools don't solve it. Fairlearn and AIF360 are Python libraries unusable by a policy officer. Arize/Fiddler/Credo AI are $10k+/yr enterprise SaaS. **None** carry India protected attributes (caste, religion, mother-tongue, region) as first-class. **None** emit DPDP-Rule-13-compliant reports. **None** are citizen-facing.

---

## How it works

```
Upload model + data  →  Planner  →  Counterfactual  →  Fairness Metrics
                                                            │
                         Narrator  ←  Remediation  ←  Root-Cause
                         (bilingual PDF,           (opens a GitHub PR
                          DPDP Rule 13,             with mitigated model)
                          EU AI Act annex)

Watcher (post-deploy)  →  Pub/Sub alerts on fairness drift
```

See [`IMPLEMENTATION_PLAN.md`](IMPLEMENTATION_PLAN.md) for full architecture, agent cards, and 35-day build plan.

## Google technologies

| Layer | Services |
|---|---|
| LLMs | Gemini 3.1 Pro · Gemini 3 Flash · **Gemini Nano 4** (on-device via AICore) |
| Generative | Imagen 4 · Chirp TTS · Google Speech-to-Text |
| Agents | **Agent Development Kit (ADK)** · Vertex AI **Agent Engine** · Firebase Genkit (evals) |
| Responsible AI | Vertex AI Model Evaluation (Fairness) · Vertex Explainable AI · LIT · **Model Armor** · **Sensitive Data Protection** |
| App | Flutter · Firebase AI Logic (`firebase_ai`) · Firebase Auth / Firestore / Hosting / App Check · Google Maps Platform |
| Data | BigQuery · Cloud Storage (CMEK) · Pub/Sub · Vertex AI Pipelines · Vertex AI Model Registry |
| Security | Cloud Run · VPC Service Controls · Cloud KMS · Identity-Aware Proxy · Secret Manager · Cloud Audit Logs |

## Quickstart

```bash
git clone https://github.com/nyayai/nyayai
cd nyayai
./scripts/bootstrap.sh
make benchmark/mudra-lite    # reproduces the 0.61 → 0.94 DI demo locally
```

Full setup in [`CONTRIBUTING.md`](CONTRIBUTING.md).

## Repository layout

```
apps/              Flutter (web + Android + iOS) and admin console
services/          api · orchestrator (ADK agents) · fairness · watcher · reporter
packages/          contracts (schemas) · india-taxonomy · fairlearn-extensions
benchmarks/        uci-adult · compas · obermeyer-repro · mudra-lite · indian-bhed
infra/terraform/   VPC-SC perimeter, KMS, IAM, data plane, Cloud Run, Vertex
docs/              COMPLIANCE · SECURITY · ACCESSIBILITY · MODEL_CARDS · architecture
```

## Compliance

NyayaAI audit reports auto-map to DPDP Act 2023 Rule 13 DPIA and EU AI Act Articles 9/10/13/14/15. See [`docs/COMPLIANCE.md`](docs/COMPLIANCE.md).

## Accessibility

WCAG 2.2 AA · TalkBack + VoiceOver verified · 7:1 high-contrast mode · voice input in **EN / HI / TA / BN** via Google Speech-to-Text · offline mode via Gemini Nano 4 on supported Android devices · low-bandwidth mode.

## Security

VPC Service Controls perimeter · CMEK on all data · Sensitive Data Protection PII redaction before every LLM call · Model Armor on every LLM entry point · differential privacy on small-subgroup metrics · Cloud Audit Logs (3-year retention) · asia-south1 (Mumbai) data residency.

## Benchmarks (reproducible)

| Dataset | Before NyayaAI | After NyayaAI |
|---|---|---|
| MUDRA-Lite (synthetic loan model) | DI ratio 0.61 · EO gap 23.4% | DI 0.94 · EO 3.8% · accuracy Δ −0.4pp |
| UCI Adult | DI 0.36 | DI 0.91 |
| COMPAS | EO gap 21% | EO gap 5% |
| Obermeyer-repro | high-risk enrolment 17.7% | 46.5% |
| **Audit time** | ~2 weeks manual | **6 minutes** |

Run locally with `make benchmark`. Reports published under [`/benchmarks/*/report.md`](benchmarks/).

## Roadmap

MeitY IndiaAI Safe & Trusted AI pilot · RBI Digital Lending audit-as-a-service · EU AI Act compliance SaaS · federated evaluation · public transparency registry. See [`IMPLEMENTATION_PLAN.md`](IMPLEMENTATION_PLAN.md) §24.

## Team

Four students. Roles in [`CONTRIBUTING.md`](CONTRIBUTING.md).

## License

Apache-2.0. See [`LICENSE`](LICENSE).
