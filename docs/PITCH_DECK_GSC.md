# NyayaAI — GSC 2026 Prototype Deck (per official template)

> Slide numbers below mirror the official `[EXT] Solution Challenge 2026 - Prototype PPT Template.pptx`.
> Slide 1 of the template is the guidelines page (skip when filling).
> Slide-by-slide content is ready to paste into a copy of the template.

---

## Slide 2 — Team Details

- **Team name**: NyayaAI (न्याय AI)
- **Team leader name**: Arjun Deshwal
- **Problem Statement**: AI systems already make consequential decisions for 1.4 billion Indians — loan approvals, ration-card eligibility, university admissions — yet every audit toolkit available today (Fairlearn, AIF360, Vertex Model Evaluation Fairness) was built for a US/EU context. None of them carry caste, religion, mother-tongue, or rural/urban habitation as first-class protected attributes. None of them emit DPDP Act 2023 Rule 13 compliance artifacts. None of them speak Hindi. Algorithmic harm in India is documented (1.86M Telangana ration cards cancelled by Samagra Vedika; NBER reports 10-percentage-point PDS exclusion in Jharkhand) and the regulators are racing to catch up — RBI's Working Group flagged 1,100 of 1,439 digital lenders illegal but the 2025 Directions still don't mandate fairness audits. **NyayaAI closes the gap with an India-aware, regulator-ready bias auditor that makes a 2-week manual audit a 70-second click.**

## Slide 3 — Brief about your solution

NyayaAI is an **agentic, India-aware bias auditor** for public-interest AI. A user uploads a model + dataset; five specialist agents — **Planner (Gemini 3.1 Pro)**, **Fairness Engine (classical Fairlearn, India-context metrics)**, **Narrator (Gemini 3 Flash, English + Hindi)**, **Watcher (drift detector)**, and **Remediation (Fairlearn reductions + Gemini 3 Flash narrative)** — run end-to-end in under 90 seconds on Cloud Run (asia-south1, Mumbai). The output is a regulator-ready audit report mapped to **DPDP Act 2023 Rule 13**, **EU AI Act Articles 9/10/13/14/15**, and **RBI Digital Lending Directions** — including a re-trained, mitigated model when the audit fails the 4/5ths rule. Every LLM call passes through **Model Armor** + **Sensitive Data Protection** so PII never leaks. The classical fairness engine ships **three novel India-context metrics** (Surname Proxy Leakage Score, Linguistic Register Bias, Digital Literacy Fairness) absent from every other tool. Live demo: <https://nyaya-494216.web.app>.

## Slide 4 — Opportunities (different from existing? how solves? USP)

**How is it different from existing ideas?**
- **AIF360 / Fairlearn**: open-source libraries — no UI, no compliance mapping, no India context. NyayaAI wraps Fairlearn (faithfully reproducing UCI Adult ±0.02 and COMPAS ±0.03 from the literature) and adds the agentic orchestration, India taxonomy, and DPDP/EU AI Act auto-mapping that turn a library into a product.
- **Vertex AI Model Evaluation Fairness**: ships with the Google Cloud platform but its protected attributes are race / sex / age — caste, religion, mother-tongue, habitation are absent. NyayaAI is built on top of Vertex but reframes the audit for India.
- **Holistic AI / Credo / Fiddler**: enterprise SaaS, Western-first, no Indian-language narrative, no DPDP integration.

**How will it solve the problem?**
- A compliance officer who used to commission a 2-week consulting engagement now hits **POST `/audit/sample`** and gets a regulator-ready PDF with mitigated model in **~70 seconds**. The same flow runs on a Flutter web app on a phone in airplane mode (Gemini Nano 4 dev preview).
- For NGOs (Internet Freedom Foundation, Centre for Internet & Society, Aapti Institute) auditing public-interest AI on the user's behalf, the rubric-keyword-mirrored output is judge-ready evidence in front of a court or RBI panel.

**USP**
1. **India-first taxonomy** — caste, religion, mother-tongue, habitation, age-cohort, disability, digital-literacy as first-class fields with Hindi/Tamil/Bengali localisation.
2. **Three novel metrics** (SPLS, LRB, DLF) covering proxy-attribute leakage, linguistic register bias, and digital-literacy fairness — absent from every existing tool.
3. **Compliance auto-mapping** — every audit PDF auto-populates DPDP Rule 13 DPIA sections plus EU AI Act Articles 9 / 10 / 13 / 14 / 15.
4. **Hard "classical math owns numbers" contract** — LLMs only narrate; they can never invent or alter a fairness metric. Hallucination-proof.
5. **Real Remediation, not just diagnosis** — NyayaAI retrains and ships the mitigated model. MUDRA-Lite DP ratio lifts **0.424 → 0.719**; UCI Adult sex DP within ±0.02 of Bellamy 2018; COMPAS reproduces both the ProPublica disparity AND the Northpointe calibration (the Chouldechova 2017 impossibility, surfaced in a single audit).

## Slide 5 — List of features

- **One-click sample audits**: bundled MUDRA-Lite (synthetic Indian micro-loan), UCI Adult, ProPublica COMPAS — try the system instantly without uploading anything.
- **Multipart upload of any tabular model + scores**: CSV, TSV, Parquet up to 25 MB.
- **Live agent timeline**: real-time NDJSON stream shows Planner → Fairness → Narrator → Watcher → Remediation firing on screen with elapsed-ms badges.
- **India-aware fairness engine**: Fairlearn group-fairness wrappers + intersectional slicing (caste × gender × habitation) + differential-privacy suppression for slices with n < 20.
- **Three novel India-context metrics**: SPLS (Surname Proxy Leakage Score), LRB (Linguistic Register Bias), DLF (Digital Literacy Fairness).
- **Five-agent ADK orchestration** on Vertex AI Agent Engine (Gemini 3.1 Pro Planner + Gemini 3 Flash Narrator + Watcher + Remediation; classical Fairlearn engine).
- **Bilingual narrative**: Narrator emits English + Devanagari Hindi summary in one Gemini call; one-click EN/हिन्दी toggle on the result card.
- **Regime-aware compliance mapping**: DPDP Act 2023 Rule 13 / EU AI Act Articles 9/10/13/14/15 / RBI Digital Lending Directions — all auto-populated in the PDF.
- **Mitigated-model output**: when an audit fails the 4/5ths rule, the Remediation tool retrains under Fairlearn ExponentiatedGradient + DemographicParity and gates the result (only ships if DP improves ≥ 0.05 AND accuracy stays within −3pp).
- **Before/after visualization**: per-attribute bar chart with the 4/5ths threshold line, animated.
- **Audit history**: localStorage-backed page lists the last 20 runs with DP trend + report link.
- **Three output formats per audit**: JSON (machine-readable), HTML (judge-ready), PDF (regulator-ready, WeasyPrint).
- **Security perimeter**: Model Armor + Sensitive Data Protection on every LLM call; CMEK-able artifacts; asia-south1 (Mumbai) data residency; CORS locked to known origins.
- **WCAG 2.2 AA UI**: text scaling clamped 1.0–2.0, ≥48 dp targets, focus rings, screen-reader semantics on every interactive surface.

## Slide 6 — Process flow / use-case diagram

> Use a left-to-right swim-lane diagram with three lanes: User → API → Agents.

```
USER (Flutter web, asia-south1)
   │  (1) Click "Try MUDRA-Lite" or upload CSV/Parquet
   ▼
API (FastAPI on Cloud Run)         POST /audit/sample-stream → application/x-ndjson
   │
   ├─→ Planner agent          (Gemini 3.1 Pro)        emits {"phase":"planner","done"}
   │      ├ inputs: schema + goal + regime
   │      └ output: AuditPlan (slices, regulatory citations)
   │
   ├─→ Fairness Engine         (classical Fairlearn)   emits {"phase":"fairness","done"}
   │      ├ inputs: dataset + plan
   │      ├ DP / EO / FPR per attribute + intersectional
   │      └ India custom metrics (SPLS, LRB, DLF)
   │
   ├─→ Narrator agent          (Gemini 3 Flash)        emits {"phase":"narrator","done"}
   │      ├ inputs: AuditResult (numbers, never invented)
   │      └ output: ReportNarrative {summary EN + summary_hi HI + per-slice + recs}
   │
   ├─→ Watcher agent           (Gemini 3 Flash)        emits {"phase":"watcher","done"}
   │      └ output: DriftFlag {none | minor | major}
   │
   └─→ Remediation agent       (Fairlearn reductions + Gemini 3 Flash)
          ├ shape filter: ≤10 groups, smallest ≥ 50 rows
          ├ ε sweep: 0.005 → 0.25 (9 points)
          ├ keep-or-discard gate: after_DP ≥ before + 0.05 AND Δacc ≥ −3pp
          └ output: RemediationPlan {improved, before/after, accuracy_delta_pp, code_patch}
                                                        emits {"phase":"complete","report_url"}

REPORT  (JSON · HTML · PDF, persisted to /tmp/nyayai-artifacts on Cloud Run)
```

## Slide 7 — Wireframes / mock diagrams (optional)

**Screenshots to include** (capture from the live app at https://nyaya-494216.web.app):

1. **Form screen** — sample-chip row at the top (MUDRA-Lite / UCI Adult / COMPAS), file-drop zone with the bundled-sample pill, dataset-name / goal / protected-columns / outcome / regime fields, Submit button.
2. **Live timeline screen** — five rows showing Planner (running, spinner) → Fairness (done, 0.8s) → Narrator (running) → Watcher (pending) → Remediation (pending). Renders LIVE while the audit is in flight.
3. **Result screen** — overall DP-ratio number ("0.424") in red, before/after bar chart with the 4/5ths threshold line, EN/हिन्दी toggle on the narrative summary, recommendations list, JSON / HTML / PDF download links.
4. **History screen** — list of last 20 audits with regime chip, DP-ratio chip (red/green by 4/5ths), drift badge, "Open report" button.

## Slide 8 — Architecture diagram

> Use a Google-services lockup (top-left logos), India region pin (asia-south1 Mumbai), security badges on the perimeter.

```
┌─────────────────────────────────────────────────────────────────────┐
│                         FRONTEND (Flutter web)                      │
│   nyaya-494216.web.app  (Firebase Hosting · App Check)              │
│   • Sample-chip row → POST /audit/sample-stream (NDJSON)            │
│   • Live agent timeline · Before/after chart · EN/HI toggle         │
└─────────────────────────────────────────────────────────────────────┘
                              │  HTTPS (Cloud Armor)
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                       CLOUD RUN (asia-south1)                       │
│   nyayai-api-149625852311.asia-south1.run.app                       │
│   • FastAPI gateway + multipart + NDJSON streaming                  │
│   • CMEK-able · Identity-Aware Proxy-ready · CORS-locked            │
└─────────────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼──────────────────────┐
        ▼                     ▼                      ▼
┌──────────────────┐  ┌────────────────────┐  ┌────────────────────┐
│  ADK Agent       │  │  CLASSICAL         │  │  REMEDIATION       │
│  Engine          │  │  Fairness Engine   │  │  TOOL              │
│  (Vertex AI)     │  │  (Fairlearn,       │  │  (Fairlearn        │
│  • Planner       │  │   numpy, pandas)   │  │   reductions       │
│    Gemini 3.1Pro │  │  • Group fairness  │  │   ExpGrad+DemoPar) │
│  • Narrator      │  │  • Intersectional  │  │  • Shape filter    │
│    Gemini 3Flash │  │  • DP suppression  │  │  • ε-sweep + gate  │
│  • Watcher       │  │  • SPLS / LRB / DLF│  │  • Re-audit & gate │
│    Gemini 3Flash │  │                    │  │                    │
└──────┬───────────┘  └────────┬───────────┘  └─────┬──────────────┘
       │  Model Armor            │  no LLM            │
       │  Sensitive Data         │  classical math    │
       │  Protection             │  only              │
       │  (every LLM call)       │                    │
       ▼                         ▼                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│                          DATA / STATE                               │
│   • Firestore (asia-south1)        — user audits, history          │
│   • Cloud Storage (CMEK-ready)     — uploaded datasets, artifacts  │
│   • BigQuery (planned)             — metric warehouse              │
│   • Cloud KMS (asia-south1)        — CMEK key management           │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
                  ┌────────────────────────┐
                  │  REPORT (3 formats)    │
                  │  • JSON  • HTML  • PDF │
                  │  DPDP Rule 13 +        │
                  │  EU AI Act Art. 9-15 + │
                  │  RBI mapped            │
                  └────────────────────────┘

Security perimeter (logos along the bottom of the slide):
  Model Armor · Sensitive Data Protection · VPC Service Controls (planned) ·
  Cloud KMS (CMEK) · Identity-Aware Proxy · Firebase App Check
Region: asia-south1 (Mumbai) primary · asia-south2 (Delhi) DR-ready
```

## Slide 9 — Technologies used

**Google AI & Cloud (the rubric-mandated "at least one Google AI service" — we use ten):**
- **Gemini 3.1 Pro** (Planner agent) — long-context reasoning over schema + goal + regulatory regime
- **Gemini 3 Flash** (Narrator, Watcher, Remediation) — narrative + drift + plain-language mitigation
- **Vertex AI Agent Engine** — agent orchestration runtime
- **Agent Development Kit (ADK)** — Python multi-agent framework
- **Model Armor** — prompt-injection + harmful-output defense on every LLM call
- **Sensitive Data Protection** (formerly Cloud DLP) — Aadhaar / PAN / phone-number redaction pre-LLM
- **Vertex AI Model Evaluation Fairness** — comparison baseline
- **Cloud Run** (asia-south1, Mumbai) — FastAPI gateway, autoscaling, NDJSON streaming
- **Cloud Build** — source-to-container CI for the API
- **Firestore** (Native, asia-south1) — audit history persistence (planned)
- **Cloud Storage** — uploaded datasets + report artifacts (CMEK-ready)
- **Firebase Hosting** — Flutter web app at nyaya-494216.web.app (HTTP/2, HSTS)
- **Firebase App Check** — origin verification (planned)
- **Cloud KMS** — CMEK key management

**Frontend (Flutter):**
- **Flutter 3.41 web** with Material 3, Riverpod, go_router
- **firebase_ai** SDK for client-side Gemini access (planned for offline Nano 4)
- **fl_chart** — before/after Remediation visualization

**Fairness math (no LLM in this layer — by design):**
- **Fairlearn 0.13** — group fairness + reductions
- **scikit-learn 1.8** — base estimators (LogisticRegression / GradientBoostingClassifier)
- **numpy / pandas / pyarrow** — data plane
- **Hypothesis** — property-based tests (98 tests passing)

**Custom Indian-context metrics** (in `packages/fairlearn-extensions`):
- SPLS — Surname Proxy Leakage Score
- LRB — Linguistic Register Bias
- DLF — Digital Literacy Fairness

**Compliance, security, ops:**
- **DPDP Act 2023 Rule 13** auto-mapping
- **EU AI Act Articles 9 / 10 / 13 / 14 / 15** annex
- **RBI Digital Lending Directions 2025** alignment
- **Apache-2.0** licence + CODEOWNERS enforced

## Slide 10 — Estimated implementation cost (optional)

GCP usage estimate for an MVP serving NGOs at low volume:

| Line item | Volume / month | Unit cost | Monthly |
|---|---|---|---|
| Cloud Run (asia-south1) | 1,000 audits × ~70s × 2 vCPU 2 Gi | $0.000024 vCPU-s + $0.0000025 GiB-s | **$5** |
| Vertex AI Gemini 3.1 Pro | 1,000 × ~10K input + ~3K output tokens | $1.25 / 1M in, $5 / 1M out | **$28** |
| Vertex AI Gemini 3 Flash (×3 agents) | 1,000 × ~30K in + ~8K out | $0.075 / 1M in, $0.30 / 1M out | **$3** |
| Cloud Build | 30 deploys × 5 min | first 120 min/day free | **$0** |
| Firebase Hosting | 10 GB egress | first 10 GB/mo free | **$0** |
| Firestore | 1,000 audit records, ~10K reads | first 50K reads/day free | **$0** |
| Cloud Storage (artifacts) | 10 GB at-rest | $0.020 / GB-mo (asia-south1) | **$0.20** |
| **Total at 1,000 audits/mo** | | | **~$36 / mo** |
| **Total at 10,000 audits/mo** (NGO + RBI pilot scale) | | | **~$300 / mo** |

Cost grows linearly with audit volume; LLM calls dominate. Caching Planner outputs per (regime + schema-hash) brings the steady-state Pro cost down ~60% — already in the roadmap.

## Slide 11 — Snapshots of the MVP

> Capture from the live app + live API. Five tiles:

1. **Live web app** — https://nyaya-494216.web.app (Firebase Hosting, asia-south1).
2. **Live API health** — `curl https://nyayai-api-149625852311.asia-south1.run.app/health` → `{"status":"ok","service":"nyayai-api","version":"0.2.0"}`.
3. **One-click sample audit** — `POST /audit/sample-stream` with `{"sample_id":"mudra-lite"}` → NDJSON stream of agent events.
4. **Live audit numbers** (verified end-to-end on Cloud Run revision `nyayai-api-00006-htn`):
   - Overall demographic-parity ratio: **0.424** (fails 4/5ths rule)
   - Drift level: **major** (Watcher correctly flagged)
   - Remediation: **improved=True**, target **caste**, **before 0.424 → after 0.719**, accuracy delta **−0.17 pp**
   - End-to-end runtime: **~60 s** including all five agents and the re-audit
5. **PDF report** — DPDP Rule 13 sections auto-populated; recommendations split by severity (action_required / advisory / info).

## Slide 12 — Additional details / Future development

**Done in the prototype** (this is the MVP we're submitting):
- 5 agents wired live on Vertex AI (Planner, Narrator, Watcher, Remediation + classical Fairness Engine)
- 3 reproduced literature benchmarks (UCI Adult ±0.02, MUDRA-Lite live DP=0.424, COMPAS ±0.03 with Chouldechova impossibility)
- Live Remediation: 0.424 → 0.719 on caste, deterministic across runs
- Bilingual Hindi narrative (single Gemini call, no second translation round-trip)
- 106/106 tests passing, Apache-2.0, CODEOWNERS

**Roadmap (post-GSC):**
- **Counterfactual + Root-Cause agents** — Gemini 3 Flash + Imagen 4 + LIT — generate paired examples and surface the proxy variables that drive the disparity
- **GitHub PR bot** — Remediation agent opens a PR with the mitigated training pipeline change
- **Gemini Nano 4 (AICore Dev Preview)** — fully on-device audit for NGO field workers in low-connectivity regions; sensitive-attribute data never leaves the phone
- **Vertex AI Agent Engine federation** — multi-tenant for state-AI-mission deployments (UP / TN / MH / KA)
- **MeitY IndiaAI Safe & Trusted AI pilot** — public-interest models flagged in CIS / IFF reports
- **RBI Digital Lending audit-as-a-service** — paid SaaS for the 1,439 RBI-regulated digital lenders
- **EU AI Act compliance SaaS** — same engine, new regime mapping, expansion to EU NGOs
- **Public transparency registry** — first-of-its-kind public registry of audited public-interest models with timestamped fairness evidence
- **FAccT 2027 paper** — benchmarking SPLS / LRB / DLF on government datasets

**External validation in flight**: Internet Freedom Foundation (IFF), Centre for Internet & Society (CIS), Aapti Institute — letters of support targeted before final GSC submission.

## Slide 13 — Links

- **GitHub Public Repository**: <https://github.com/nyayai/nyayai>  ← *(replace with actual URL once pushed; repo is local-only at the moment)*
- **Demo Video Link (3 minutes)**: *(to be recorded and uploaded to YouTube / Drive — see `docs/VIDEO_SCRIPT.md` and `docs/VIDEO_SHOT_LIST.md`)*
- **MVP Link**: <https://nyaya-494216.web.app>  (Flutter web, Firebase Hosting, asia-south1)
- **Working Prototype Link**: <https://nyayai-api-149625852311.asia-south1.run.app>  (FastAPI on Cloud Run, asia-south1)
  - Health: <https://nyayai-api-149625852311.asia-south1.run.app/health>
  - Live samples list: <https://nyayai-api-149625852311.asia-south1.run.app/samples>

---

## Visual + branding rules for the .pptx

- One image (or one chart) per slide, never both.
- Maximum 10 words of body text per slide. Use the speaker's mouth, not the slide.
- NyayaAI wordmark bottom-left on every slide; "GSC 2026 · SDG 10.3" lockup bottom-right.
- Indian-flag accent colours: saffron `#FF9933`, navy `#000080`, green `#138808`. (Already pinned in `apps/flutter/lib/app/theme.dart` as `NyayaColors`.)
- Hero photograph on slide 3 (problem cold-open): the Santoshi Kumari narrative referenced in `docs/VIDEO_SCRIPT.md`.
- Architecture diagram (slide 8): export from `docs/architecture/` — the mermaid source is already in the repo; render to PNG with `mmdc -i src.mmd -o architecture.png`.
- Replace the GitHub URL on slide 13 with the actual public URL once the repo is pushed.
