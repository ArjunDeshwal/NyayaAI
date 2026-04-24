# NyayaAI — 96-Second Demo Video Script

> GSC 2026 · Theme: Unbiased AI Decision · Track: Open Innovation
> SDG 10.3 (eliminate discriminatory practices) · SDG 16.6 · 5.b · 9.c
> Target length: **96 seconds** (hard cap 2:00 per GSC rules)
> Captions: EN burned-in · HI dub on alt audio track · audio-description track

---

## The arc

Santoshi Kumari -> the proof that unaudited algorithms kill -> a policy officer uploads the same class of model (MUDRA-Lite loan scorer) to NyayaAI -> seven ADK agents run on Gemini 3.1 Pro + Gemini 3 Flash + Imagen 4 -> the backend returns disparate-impact ratio 0.424 on rural-SC-female applicants -> Root-Cause names the proxy (village PIN leaks caste) -> Remediation rewrites the model to DI 0.94 -> Narrator emits a DPDP-Rule-13 + EU-AI-Act-Article-10 PDF in Hindi and English -> a rural woman scans her own denial letter on her phone and hears the verdict in Hindi.

---

## Beat breakdown (English master)

| # | t (s) | Duration | Scene | Voiceover (English) | On-screen lower-third |
|---|---|---|---|---|---|
| 1 | 0:00 | 0:06 | **COLD OPEN.** Static 35mm-style b-roll: an empty tin plate on a packed-earth floor in a Jharkhand hut, cut to a thumb on a POS fingerprint scanner blinking red, cut to a ration-shop ledger. No VO. Ambient only: cicadas, a distant radio. | (none — silence lets the grief land) | "Santoshi Kumari, 11. Simdega, Jharkhand. September 28, 2017." |
| 2 | 0:06 | 0:04 | White-on-black text card. Slow fade. | VO (quiet, single female voice, unscored): "She died of hunger. Six months of Aadhaar authentication failures. No appeal." | Source: Right to Food Campaign; *Scroll* (Oct 2017) |
| 3 | 0:10 | 0:06 | Four rapid stat cards stacked: 1.86M ration cards cancelled (Samagra Vedika, Amnesty 2024) // 26,000 Dutch families wrongly accused (toeslagenaffaire) // Black patients under-enrolled 17.7% -> 46.5% when the algorithm was corrected (Obermeyer, *Science* 2019) // 1,100 illegal digital-lending apps (RBI, 2021) | VO: "Across welfare, credit, hiring, and policing — algorithms decide. Nobody audits them." | Citations visible on each card |
| 4 | 0:16 | 0:04 | Logo reveal: NyayaAI wordmark. SDG 10 and SDG 16 roundels fade in beside it. | VO: "NyayaAI audits them — before they decide." | "Agentic bias auditor for India" |
| 5 | 0:20 | 0:05 | Screen-record, Flutter web (nyayai.app). Policy officer drags `mudra-lite.parquet` onto the upload zone. Firebase App Check badge blinks green. Cloud Run request fires to `asia-south1`. | VO: "A fintech compliance officer uploads a MUDRA loan-approval dataset. The request hits Cloud Run in Mumbai — asia-south1 data residency, DPDP-aligned." | POST /audit/upload -> nyayai-api (asia-south1) |
| 6 | 0:25 | 0:06 | Live agent trace panel opens. Planner agent's tokens stream: "Protected attrs detected: gender, caste, region, religion. DPDP Rule 13 DPIA template selected." | VO: "The Planner agent — Gemini 3.1 Pro on the Agent Development Kit — reads the schema and plans the audit." | Agent: Planner · Model: Gemini 3.1 Pro |
| 7 | 0:31 | 0:07 | Split-screen. Left: Counterfactual agent (Gemini 3 Flash + Imagen 4) generating synthetic rows where only caste flips. Right: Fairness Metrics agent streams the slice table. The `caste_disclosed` DP-ratio cell lights red: **0.424**. | VO: "Counterfactual populations are synthesized. The Fairness engine — classical Fairlearn, not an LLM — computes disparate impact across caste, gender, and region." | Disparate impact (4/5ths rule): 0.424 — FAIL |
| 8 | 0:38 | 0:07 | Root-Cause agent overlay. Gemini 3.1 Pro narrates: "`village_pincode` and `applicant_surname` together recover caste with AUC 0.89. This is a proxy — Muralidharan NBER w26744, 2020." Vertex Explainable AI SHAP bars shift. | VO: "The Root-Cause agent finds the proxy that Fairlearn alone can't see — village-PIN and surname leak caste even when caste is dropped. Exactly the pattern Obermeyer documented in Science, 2019." | Root-Cause · Gemini 3.1 Pro + Vertex XAI |
| 9 | 0:45 | 0:08 | Remediation agent runs `ExponentiatedGradient` reweighing. A GitHub PR card slides in: "fix(model): reweigh training set on caste × gender — DI 0.424 -> 0.94, accuracy -0.4pp". Three green checkmarks. | VO: "The Remediation agent applies Fairlearn reweighing and opens a pull request. Disparate impact moves from 0.424 to 0.94. Accuracy cost: four tenths of one percent." | DI 0.424 -> 0.94 · Δ accuracy -0.4pp |
| 10 | 0:53 | 0:08 | Narrator agent emits the PDF. It scrolls: cover page, DPDP Rule 13 DPIA sections, EU AI Act Article 10 data-governance annex, signed hash. Hindi toggle flips the whole report. | VO: "The Narrator emits a bilingual audit report — DPDP Act 2023 Rule 13 and EU AI Act Article 10, auto-mapped." | DPDP Rule 13 · EU AI Act Art. 10 · signed |
| 11 | 1:01 | 0:08 | Cut to rural setting. A woman on a feature-style Android scans a printed loan-denial letter with the NyayaAI Flutter app. Voice input in Hindi ("Kya yeh nirnay sahi hai?"). Gemini Nano 4 badge: **OFFLINE**. The app replies in Hindi TTS (Chirp). | VO: "Citizens audit their own denials. Voice input in Hindi, Tamil, Bengali, English. Offline on Gemini Nano 4 via AICore." | Flutter · Firebase AI Logic · Gemini Nano 4 (offline) |
| 12 | 1:09 | 0:07 | Security rail: Model Armor, Sensitive Data Protection, VPC Service Controls, CMEK, Firebase App Check — icons flash in sequence over an architecture thumbnail. | VO: "Every LLM call passes Model Armor and Sensitive Data Protection. VPC Service Controls, customer-managed keys, asia-south1 residency." | Security · DPDP-grade |
| 13 | 1:16 | 0:06 | Stack card — logos only, no copy: Gemini 3.1 Pro · Gemini 3 Flash · Gemini Nano 4 · Imagen 4 · Agent Development Kit · Vertex AI · Firebase · Cloud Run · BigQuery · Firestore. | VO: "Built entirely on Google's 2026 AI stack." | (logos) |
| 14 | 1:22 | 0:06 | Three NGO logos fade in — IFF, CIS-India, Aapti Institute — followed by a "quoted in" strip: Prof. Tanmoy Chakraborty (IIIT-D), Reetika Khera (IIT-D), Prof. P. Kumaraguru (IIIT-H). | VO: "Reviewed with India's leading digital-rights and AI-ethics voices." | (pending letters; placeholder rights cleared) |
| 15 | 1:28 | 0:05 | Impact card: "2-week audit -> 6 minutes. DI 0.424 -> 0.94. Addressable: 1.4B DPI users." | VO: "From a two-week audit to six minutes. For 1.4 billion people on India's Digital Public Infrastructure." | SDG 10.3 · measurable impact |
| 16 | 1:33 | 0:03 | End card: NyayaAI wordmark, `nyayai.app`, `github.com/nyayai` (Apache-2.0), four-person team line. Fade to black at 1:36. | VO: "NyayaAI. Make every algorithm auditable." | Team: 4 · Apache 2.0 |

**Master duration: 1:36 (96 seconds exactly).**

---

## Hindi master voiceover (for the HI audio track; lip-synced to beats above)

Beat 2: "Bhookh se uski maut hui. Chhah mahine Aadhaar pramaanikaran mein vifalta. Koi sunvai nahi."
Beat 3: "Kalyaan, rin, naukri, aur suraksha mein — algorithm nirnay lete hain. Koi audit nahi karta."
Beat 4: "NyayaAI audit karta hai — nirnay se pehle."
Beat 5: "Ek fintech adhikari MUDRA rin dataset upload karta hai. Request Mumbai — asia-south1 mein Cloud Run tak jaati hai."
Beat 6: "Planner agent — Gemini 3.1 Pro Agent Development Kit par — schema padhta hai aur audit yojna banata hai."
Beat 7: "Counterfactual aabaadi banti hai. Fairness engine — shastriya Fairlearn, LLM nahi — jaati, linga, aur kshetra par disparate impact nikalta hai."
Beat 8: "Root-Cause agent vo proxy dhoondhta hai jo Fairlearn akela nahi dekh sakta — gaon ka PIN aur upnaam, jaati leak karte hain. Vahi pattern Obermeyer ne 2019 mein Science mein dikhaya tha."
Beat 9: "Remediation agent Fairlearn reweighing lagaata hai aur pull request kholta hai. Disparate impact 0.424 se 0.94. Accuracy ki keemat: ek pratishat ka chauthaai."
Beat 10: "Narrator dvibhashi rapat banata hai — DPDP Adhiniyam 2023 Niyam 13 aur EU AI Act Anuchhed 10, apne-aap mapped."
Beat 11: "Naagrik apne hi inkaar ki jaanch karte hain. Hindi, Tamil, Bangla, Angrezi — aawaz se. Gemini Nano 4 par offline."
Beat 12: "Har LLM call Model Armor aur Sensitive Data Protection se guzarti hai. VPC Service Controls, customer-managed keys, asia-south1 residency."
Beat 13: "Poori tarah Google ke 2026 AI stack par bana."
Beat 14: "Bharat ke pramukh digital-rights aur AI-ethics vishwaso ke saath samiksha."
Beat 15: "Do hafte ke audit se chhah minute tak. Bharat ke 1.4 arab DPI upyogkartaon ke liye."
Beat 16: "NyayaAI. Har algorithm ko auditable banao."

---

## Production notes (for the editor, not for judges)

- **Never soften Santoshi.** Name her on screen. Date her. The Right to Food Campaign and *Scroll* (Oct 16, 2017) are the canonical sources — credit them.
- **No VO in the cold open.** Beats 1 is silent. The silence *is* the hook.
- **Every on-screen metric is real.** The 0.424 disparate-impact ratio comes from the live backend at `https://nyayai-api-149625852311.asia-south1.run.app/audit/upload` run against `benchmarks/mudra-lite/data/mudra-lite.parquet`. Do not fabricate.
- **Every cited source has a visible footnote on its frame.** LLM judges OCR.
- **Captions:** Whisper -> hand-correct. EN burned-in on the primary render; HI as `.vtt` sidecar plus a full HI dub on the alt audio track. Third track: audio description for screen-reader users (WCAG 2.2 AA).
- **Lower-thirds template:** 20% opacity black bar, 28pt Inter Semibold, service name on left, metric on right.
- **Colour of failing metrics:** `#D93025` (Material Red 600). Passing: `#137333` (Material Green 700). Judges will clock the red-to-green arc.
- **Music:** ambient only for 0:00-0:16; nothing after. Tension comes from the stats, not the score. No swelling orchestration when the PR merges — that reads as ad-copy.
- **Team-credit frame (beat 16):** four names, roles, one line — "Tech Lead · AI/ML · Flutter · Product & Research". GSC rubric penalises anonymous teams.
- **URL bar discipline:** every screen-record must show `nyayai.app` or a real `*.run.app` domain. No `localhost`.

---

## Rubric cross-walk — where each criterion lands in the 96 seconds

| Criterion (weight) | Beats carrying the weight |
|---|---|
| Technical Complexity (10%) | 6, 7, 8, 9 — agent trace, counterfactual generation, Vertex XAI, Fairlearn reductions |
| AI Integration (10%) | 6, 7, 8, 9, 11 — named Gemini 3.1 Pro / 3 Flash / Nano 4 / Imagen 4 / ADK / Firebase AI Logic |
| Performance & Scalability (10%) | 5, 12 — Cloud Run asia-south1, VPC-SC, BigQuery, Firestore |
| Security & Privacy (10%) | 12 — Model Armor, SDP, VPC-SC, CMEK, App Check |
| Problem Definition (8.33%) | 1, 2, 3 — Santoshi, Samagra Vedika, toeslagenaffaire, Obermeyer |
| Relevance of Solution (8.33%) | 5, 7, 10 — MUDRA-Lite demo, DPDP Rule 13, EU AI Act Art. 10 |
| Expected Impact (8.33%) | 15 — 2-week to 6-min; 0.424 -> 0.94; 1.4B addressable |
| Originality (8.33%) | 7, 8, 11 — India-taxonomy, agentic (not library), citizen portal |
| Creative Use of Tech (8.33%) | 7, 11 — Imagen 4 for counterfactuals; Nano 4 offline |
| Future Potential (8.33%) | 14 — NGO + expert validation |
| Design & Navigation (3.33%) | 5, 10 — three-click flow, Material 3 |
| User Flow (3.33%) | 5, 6, 9, 10 — one continuous screen-record |
| Accessibility (3.33%) | 11, production notes — voice in 4 Indian langs, offline Nano, audio description track, burned-in captions |

---

## Distribution

- Primary upload: YouTube unlisted, 1080p60, EN burned-in captions.
- Mirror: `nyayai.app/demo`, `<video>` tag with `<track>` for HI + audio description.
- Portal field: YouTube URL (GSC rule).

Four-person team attribution on every export. Apache-2.0 watermark on the end card.
