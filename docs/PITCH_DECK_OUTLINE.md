# NyayaAI — GSC 2026 Pitch Deck Outline (10 slides)

> Design rule: one idea per slide, maximum 10 words of body text. Judges remember images and numbers, not paragraphs. All Google service names use 2026-correct nomenclature. Primary SDG target **10.3** appears on slides 1, 3, 9, 10.

---

## Slide 1 — Problem: algorithms decide who eats, borrows, and gets hired

- **15.1M people** suffered 10-percentage-point PDS exclusion in Jharkhand (Muralidharan et al., *NBER w26744*, 2020).
- **26,000 families** wrongly accused by the Dutch *toeslagenaffaire*; **200M patients** scored by a biased US care algorithm (Obermeyer, *Science*, 2019).
- No audit, no appeal, no recourse — the least literate pay the cost.

## Slide 2 — India context: the harm is already documented, and escalating

- **1.86M ration cards** cancelled by Telangana's Samagra Vedika algorithm with no appeal (Amnesty, 2024).
- **1,100 of 1,439** digital lenders flagged illegal by the RBI Rao WG (2021); audit was still *not* mandated in the 2025 Directions.
- Caste, religion, mother-tongue and region are **first-class protected attributes** — absent from every existing tool.

## Slide 3 — Solution: NyayaAI, an agentic India-aware bias auditor

- **7 specialist agents** — 6 Gemini-backed, 1 classical fairness engine — orchestrated on the **Agent Development Kit (ADK)**.
- **2-week manual audit to ~70 seconds** live on Cloud Run, asia-south1 (Mumbai).
- SDG **10.3** · **16.6** · **16.7**; DPDP Rule 13 and EU AI Act Art. 9/10/15 built in.

## Slide 4 — Architecture: Google-native, security-perimetered, India-resident

- Flutter (web/Android/iOS) → Cloud Run API → ADK on **Vertex AI Agent Engine** → BigQuery + Firestore + Cloud Storage (CMEK).
- **Model Armor** on every LLM call; **Sensitive Data Protection** redacts Aadhaar/PAN/phone pre-LLM.
- **VPC Service Controls** perimeter; Differential Privacy on intersectional slices; asia-south1 residency, asia-south2 DR.

## Slide 5 — Agents: 7 agents, 6 Gemini + 1 classical (by design)

- **Planner · Counterfactual · Root-Cause · Remediation · Narrator · Watcher** — Gemini 3.1 Pro / Gemini 3 Flash / Imagen 4 / Chirp.
- **Fairness Engine** stays classical Python (Fairlearn + SPLS / DLF / LRB novel metrics) — satisfies the rubric's *"could a simpler approach have worked?"* test.
- Every agent has typed Pydantic tool contracts and 30 Genkit eval goldens, regression-gated in CI.

## Slide 6 — Demo flow: upload → audit → mitigated PR in under 6 minutes on screen

- Policy officer pastes MUDRA-Lite model URL; Planner proposes a DPDP-Rule-13-mapped audit.
- Counterfactual generates 10,000 synthetic applicants; Fairness Engine shows live DP ratio **0.424** on `caste_disclosed` (2,000 rows, real math).
- Remediation opens a **GitHub PR** with the mitigated model; Narrator emits an EN + HI PDF while a rural user runs the same audit **offline on Gemini Nano 4**.

## Slide 7 — Impact: reproducible, measured, already-running numbers

- **Audit time ~2 weeks → ~70s** end-to-end live (Gemini 3.1 Pro + 3 Flash + Vertex AI wired on Cloud Run).
- **MUDRA-Lite DP ratio 0.424 → 0.94**, accuracy delta **−0.4pp**; UCI Adult DI **0.36 → 0.91**; COMPAS EO gap **21% → 5%**; Obermeyer-repro high-risk enrolment **17.7% → 46.5%**.
- Addressable: **1.4B DPI users · 900M PDS beneficiaries · 1.3M RBI-regulated lending touchpoints.**

## Slide 8 — Compliance: DPDP Rule 13 + EU AI Act, auto-mapped

- Every audit PDF auto-populates **DPDP Act 2023 Rule 13 DPIA** sections (purpose, data categories, risks, safeguards).
- EU AI Act **Art. 9** (risk) · **Art. 10** (data governance) · **Art. 13** (transparency) · **Art. 14** (human oversight) · **Art. 15** (accuracy/robustness) conformity annex generated per audit.
- Hook points: **SDP** pre-LLM redaction + **Model Armor** prompt-injection defense on every LLM call — no bypass path in production.

## Slide 9 — Team & roadmap: 4-person team, path to MeitY + RBI + EU AI Act

- Four engineering students: Fairness Engineer · Agent Architect · Flutter Engineer · Compliance & Infra; 98/98 tests passing; Apache-2.0, `CODEOWNERS` enforced.
- Roadmap: **MeitY IndiaAI Safe & Trusted AI pilot** → **RBI Digital Lending audit-as-a-service** → **EU AI Act compliance SaaS** → federated evaluation → public transparency registry.
- External validation in-flight from Internet Freedom Foundation, Centre for Internet & Society, and Aapti Institute.

## Slide 10 — Ask: advance NyayaAI, one audit mandate at a time

- Google credits, ADK + Vertex AI Agent Engine support, and a Cloud mentor to harden the production deployment at asia-south1 scale.
- Introductions to MeitY IndiaAI Mission and RBI for the Safe-&-Trusted-AI and Digital-Lending pilots.
- A GSC 2026 Top-10 slot so we can make SDG **10.3** — *"eliminate discriminatory laws, policies and practices"* — mean something for the 1.4B people behind the statistics.

---

**Visual discipline.** Every slide: one image or chart (not both), maximum 10 words of body text, the NyayaAI wordmark bottom-left, the GSC 2026 + SDG 10.3 lockup bottom-right. Slides 1, 3, 6 and 7 are the judge-sticky ones — lead with a photograph (Santoshi Kumari shot from the 96s video on slide 1), then numbers, then the product.
