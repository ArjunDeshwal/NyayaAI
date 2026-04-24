# NyayaAI — Video Shot List (96 seconds)

> One row per shot. Drives camera, screen-capture, and edit. Do not improvise; the 96 seconds is load-bearing.
>
> Columns: **#** shot number · **t** start time · **dur** duration (s) · **source** screen-cap / b-roll / static card / composite · **on-screen** visual description · **vo fragment** the exact narration words that land on this frame · **lower-third** burned caption below frame · **asset** where the raw asset lives.

---

## Act I — The cost (0:00 – 0:16)

| # | t | dur | source | on-screen | vo fragment | lower-third | asset |
|---|---|---|---|---|---|---|---|
| 1 | 0:00 | 3 | b-roll (licensed or staged) | Static wide: empty tin plate on packed-earth floor, late-afternoon key light. No camera move. | (silent — cicadas, distant radio) | Santoshi Kumari, 11 — Simdega, Jharkhand | `b-roll/01_plate.mov` |
| 2 | 0:03 | 3 | b-roll | Close-up: thumb on a ration-shop POS fingerprint scanner. Scanner blinks red three times. Match-cut from shot 1's darkness. | (silent) | September 28, 2017 | `b-roll/02_pos.mov` |
| 3 | 0:06 | 4 | static card | White Inter text on black: "She died of hunger. Six months of Aadhaar authentication failures. No appeal." | "She died of hunger. Six months of Aadhaar authentication failures. No appeal." | Right to Food Campaign; *Scroll*, Oct 16 2017 | `cards/03_died.png` |
| 4 | 0:10 | 6 | static cards (4 stacked, 1.5s each) | Four stat cards auto-advance: (a) 1.86M ration cards cancelled — Samagra Vedika, Amnesty 2024; (b) 26,000 Dutch families wrongly accused — toeslagenaffaire, Amnesty 2021; (c) Black enrolment 17.7% -> 46.5% when algorithm corrected — Obermeyer *Science* 2019; (d) 1,100 illegal digital-lending apps — RBI 2021. | "Across welfare, credit, hiring, and policing — algorithms decide. Nobody audits them." | (citation per card, bottom-left) | `cards/04a-d.png` |

## Act II — The demo (0:16 – 1:15)

| # | t | dur | source | on-screen | vo fragment | lower-third | asset |
|---|---|---|---|---|---|---|---|
| 5 | 0:16 | 4 | static composite | NyayaAI wordmark animates in on black. SDG 10 and SDG 16 UN roundels fade in to the right. Sanskrit tagline line: "Nyaya = Justice". | "NyayaAI audits them — before they decide." | Agentic bias auditor for India | `cards/05_logo.mp4` |
| 6 | 0:20 | 5 | screen-cap (Flutter web, nyayai.app) | Cursor drags `mudra-lite.parquet` onto the upload dropzone. File chip appears: "mudra-lite.parquet — 2,000 rows". Firebase App Check green. A POST fires; request URL visible: `https://nyayai-api-149625852311.asia-south1.run.app/audit/upload`. | "A fintech compliance officer uploads a MUDRA loan-approval dataset. The request hits Cloud Run in Mumbai — asia-south1 data residency." | POST /audit/upload · Cloud Run · asia-south1 | `cap/06_upload.mov` |
| 7 | 0:25 | 6 | screen-cap (agent trace panel) | Right-side drawer opens: "Planner agent". Tokens stream in mono: `Detected protected attrs: gender, caste_disclosed, religion, region. Slices: rural x female x SC; urban x Muslim x youth. Template: DPDP Rule 13 DPIA. Est. 6 min.` | "The Planner agent — Gemini 3.1 Pro on the Agent Development Kit — reads the schema and plans the audit." | Agent: Planner · Gemini 3.1 Pro · ADK | `cap/07_planner.mov` |
| 8 | 0:31 | 7 | composite split-screen | **Left (55%):** Counterfactual agent panel — synthetic row table auto-generating; an Imagen-4 thumbnail renders beside a résumé for the vision-counterfactual cameo. **Right (45%):** Fairness Metrics table. The row `rural x female x caste_disclosed=SC` turns from neutral to Material Red 600: `DI = 0.424`. Bootstrap CI shown in parentheses. | "Counterfactual populations are synthesized. The Fairness engine — classical Fairlearn, not an LLM — computes disparate impact across caste, gender, and region." | Disparate impact (4/5ths rule): 0.424 — FAIL | `cap/08_cf_metrics.mov` |
| 9 | 0:38 | 7 | screen-cap (Root-Cause panel) | Gemini 3.1 Pro narration streams: "village_pincode + applicant_surname jointly recover caste_disclosed with AUC 0.89 — Surname-Proxy Leakage Score 0.47. Pattern consistent with Obermeyer, Science 2019 and Muralidharan NBER w26744, 2020." Below it, a Vertex Explainable AI SHAP chart animates to show PIN's outsized contribution. | "The Root-Cause agent finds the proxy that Fairlearn alone can't see — village-PIN and surname leak caste even when caste is dropped. Exactly the pattern Obermeyer documented in Science, 2019." | Root-Cause · Gemini 3.1 Pro + Vertex XAI | `cap/09_rootcause.mov` |
| 10 | 0:45 | 8 | screen-cap (Remediation -> GitHub PR) | Remediation agent card: "Applying ExponentiatedGradient reweighing on (caste_disclosed, gender)...". Progress bar fills. Transition: GitHub PR page opens — title `fix(model): reweigh training set on caste x gender`. Three green CI checks. Metric delta block: `DI 0.424 -> 0.94 · Accuracy -0.4pp`. | "The Remediation agent applies Fairlearn reweighing and opens a pull request. Disparate impact moves from 0.424 to 0.94. Accuracy cost: four tenths of one percent." | DI 0.424 -> 0.94 · Δ accuracy -0.4pp | `cap/10_remediation.mov` |
| 11 | 0:53 | 8 | screen-cap (PDF viewer) | Audit PDF opens at page 1 — cover with signed-hash footer. Auto-scroll through: "Section 3 — DPDP Rule 13 DPIA", "Section 7 — EU AI Act Article 10 (Data governance)", "Appendix B — slice metrics". At 0:59 a language-toggle button is clicked; the entire PDF re-renders in Devanagari. | "The Narrator emits a bilingual audit report — DPDP Act 2023 Rule 13 and EU AI Act Article 10, auto-mapped." | DPDP Rule 13 · EU AI Act Art. 10 · signed hash | `cap/11_pdf.mov` |

## Act III — The citizen (1:01 – 1:22)

| # | t | dur | source | on-screen | vo fragment | lower-third | asset |
|---|---|---|---|---|---|---|---|
| 12 | 1:01 | 8 | b-roll + phone-cap composite | Medium shot: Indian woman, mid-40s, seated on a charpai, holding a printed loan-denial letter and a mid-range Android. Cut to phone screen-capture: NyayaAI Flutter app, "Audit my decision" tab. Voice button pressed; Hindi waveform animates as she says "Kya yeh nirnay sahi hai?". Response renders in Hindi with a red banner: "Sambhavit algorithmic paksh". Gemini Nano 4 badge on the status bar reads OFFLINE (airplane-mode icon visible). | "Citizens audit their own denials. Voice input in Hindi, Tamil, Bengali, English. Offline on Gemini Nano 4 via AICore." | Flutter · Firebase AI Logic · Gemini Nano 4 (offline) | `b-roll/12_citizen.mov` + `cap/12_phone.mov` |
| 13 | 1:09 | 7 | static composite | Architecture thumbnail centre; five security glyphs flash in sequence around it: Model Armor, Sensitive Data Protection, VPC Service Controls, Cloud KMS (CMEK), Firebase App Check. `asia-south1` pin drops on a faint India outline. | "Every LLM call passes Model Armor and Sensitive Data Protection. VPC Service Controls, customer-managed keys, asia-south1 residency." | Security · DPDP-grade | `cards/13_security.mp4` |

## Act IV — The proof (1:16 – 1:36)

| # | t | dur | source | on-screen | vo fragment | lower-third | asset |
|---|---|---|---|---|---|---|---|
| 14 | 1:16 | 6 | static logo grid | 2x5 logo grid, no copy: Gemini 3.1 Pro · Gemini 3 Flash · Gemini Nano 4 · Imagen 4 · Agent Development Kit · Vertex AI · Firebase · Cloud Run · BigQuery · Firestore. | "Built entirely on Google's 2026 AI stack." | (no lower-third — let the logos speak) | `cards/14_stack.png` |
| 15 | 1:22 | 6 | static card | Three NGO logos fade in on top row: IFF, CIS-India, Aapti Institute. Below, three name tags fade in: Prof. Tanmoy Chakraborty (IIIT-D, CRAI), Reetika Khera (IIT Delhi), Prof. P. Kumaraguru (IIIT-H). | "Reviewed with India's leading digital-rights and AI-ethics voices." | External validation (letters pending Day 30) | `cards/15_ngo.png` |
| 16 | 1:28 | 5 | static card | Three stacked impact lines: "2-week audit -> 6 minutes" · "DI 0.424 -> 0.94" · "Addressable: 1.4 billion DPI users". SDG 10.3 icon bottom-right. | "From a two-week audit to six minutes. For 1.4 billion people on India's Digital Public Infrastructure." | SDG 10.3 · measurable impact | `cards/16_impact.png` |
| 17 | 1:33 | 3 | static end card | NyayaAI wordmark centre; `nyayai.app` and `github.com/nyayai (Apache-2.0)` below; four-name team credit in a single row at the bottom. Fade to black at 1:36. | "NyayaAI. Make every algorithm auditable." | Team: 4 · Apache 2.0 · GSC 2026 | `cards/17_end.png` |

**Total: 96 seconds.**

---

## Global capture rules

1. **Browser:** Chrome 134 stable, 1440x900 viewport, 2x DPR. Hide bookmarks bar, extensions, profile chip.
2. **URL bar visible at least once per screen-cap segment.** Must show `nyayai.app` (beats 6–11) or the Cloud Run URL (beat 6 only). No `localhost`, no `ngrok`.
3. **Cursor:** macOS default, 1.5x size, no click-ripple animation. Record at 60fps; export at 60fps.
4. **Agent trace panel:** set `?demo=true` query param to pace token streaming to 20 tokens/sec (real trace is bursty and reads badly).
5. **Colour:** passing metrics `#137333`, failing `#D93025`. The 0.424 -> 0.94 arc must be visually unambiguous.
6. **No personal data on any screen.** The MUDRA-Lite set is synthetic; confirm before every shoot with `git log benchmarks/mudra-lite/data/`.
7. **Captions:** Whisper `large-v3` first pass, hand-corrected against this script. EN burned-in, HI `.vtt` sidecar, audio description `.vtt` sidecar.
8. **Audio:** single female VO, neutral Indian English; Hindi dub by a separate native speaker (not TTS). -16 LUFS integrated, -1 dBTP ceiling.

## Fallback if live Gemini is slow on shoot day

- Pre-record agent traces from a successful run and play them as a looped `.mov` in the trace panel — the frontend reads from a fixture JSON when `?fixture=demo-001` is set.
- The MUDRA-Lite 0.424 DI number is already committed in `benchmarks/mudra-lite/reports/audit-2026-04-24.json`. Editor can pull from that file if the live run stalls.
- Never edit the number to smooth the narrative. The honesty is the story.

## Asset ownership

| Asset class | Owner |
|---|---|
| Screen captures (cap/*) | Flutter engineer (P3) + AI/ML engineer (P2) |
| B-roll (b-roll/*) | Product & Research (P4) — licence via Pond5 or shoot in Ranchi with a consenting subject |
| Cards (cards/*) | Product & Research (P4) — Figma -> MP4 |
| Voiceover (EN + HI) | Product & Research (P4) — contracted |
| Final edit | Product & Research (P4), reviewed by full team |

## Sign-off gate (before shoot)

- [ ] Every on-screen metric matches a committed artifact in `benchmarks/mudra-lite/`.
- [ ] Every cited source appears on-screen as a footnote card.
- [ ] Santoshi Kumari is named on screen in beat 1 lower-third.
- [ ] Four-person team credit present in beat 17.
- [ ] All service names match `.claude/skills/nyayai-gsc-submission/SKILL.md` deprecation table.
- [ ] Total runtime between 94 and 96 seconds; hard cap 120.
