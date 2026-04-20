---
name: nyayai-gsc-submission
description: NyayaAI project skill. Use when writing or reviewing any submission artifact — README, demo video script, pitch deck, architecture diagram captions, benchmark reports, impact metrics, NGO outreach letters, or GSC portal form fields. Ensures every artifact is LLM-judge-optimized: rubric-keyword-mirrored, explicitly names Google services, cites peer-reviewed sources, includes measurable impact numbers, and leads with SDG alignment. Invoke whenever polishing material that a GSC judge (human or LLM) will read.
---

# GSC 2026 Submission Optimization

GSC 2026 results arrive within 24 hours of submission — almost certainly AI-judged. This skill encodes the winning-pattern research into actionable rules for anything a judge reads.

## Rubric (weights)

| Criterion | Weight |
|---|---|
| Technical Merit | 40% |
| Alignment with Cause | 25% |
| Innovation & Creativity | 25% |
| User Experience | 10% |

LLM judges score by **keyword density of rubric terms**, **named Google services**, **measurable impact**, **SDG citations**, and **deployed artifacts**.

## Mandatory elements in any GSC-facing artifact

Every major artifact (README, deck, video script, portal description) MUST contain:

1. **SDG alignment within the first 150 words**, with sub-target numbers (e.g., "SDG 10.3", not "SDG 10").
2. **Peer-reviewed or official citation** for the problem (NBER, *Science*, Amnesty, RBI, MeitY).
3. **Measurable-impact numbers with a baseline** ("audit time 2 weeks → 6 minutes", "DI ratio 0.61 → 0.94"). No "helps millions" without a number.
4. **Named Google services in a table or bullet list** — spelled with correct 2026 names (see below).
5. **Architecture as an image** (PNG + mermaid source). LLM judges OCR.
6. **Accessibility line** — "WCAG 2.2 AA, screen-reader verified (TalkBack, VoiceOver), voice input in EN/HI/TA/BN, Gemini Nano 4 offline mode".
7. **Security line** — "VPC-SC, CMEK, SDP PII redaction, Model Armor, differential privacy, asia-south1 residency".
8. **Deployed live URL** — `https://nyayai.app` + Play Store link.
9. **Apache 2.0 license + GitHub link**.
10. **4-person team** attribution.

## Correct 2026 Google service names (do not use deprecated names)

| ✅ Use | ❌ Don't use |
|---|---|
| Gemini 3.1 Pro, Gemini 3 Flash, Gemini Nano 4 | PaLM, Bard, Gemini 1.x, "Gemini Pro 1.5" |
| Agent Development Kit (ADK), Vertex AI Agent Engine | "Vertex AI Agent Builder" alone, Agentspace |
| Firebase AI Logic (`firebase_ai`) | Vertex AI in Firebase, `firebase_vertexai`, `google_generative_ai` |
| Sensitive Data Protection (SDP) | Cloud DLP |
| Imagen 4 | Imagen 3, Imagen 2 |
| Veo 3 | Veo, Veo 1/2 |
| Conversational Agents | Dialogflow CX console |
| Vertex AI Model Evaluation (Fairness) | "Fairness Indicators" alone (aging) |

## Winning-pattern rules (from GSC 2024/2025 analysis)

1. **Team size = 4.** Always. Under-4 signals under-scope.
2. **Demo video ≤ 2 minutes.** Target 90–120s. Screen-recording beats slides. Hook in first 8 seconds.
3. **Problem scope must be narrow and legible.** "Bias auditor for Indian public-interest AI" beats "Bias auditor for everything."
4. **Deploy to Google-native infra.** Firebase Hosting, not Vercel. Play Store internal testing, not APK only.
5. **Public GitHub + Apache/MIT license** + CI badges + `CODEOWNERS`.
6. **Metrics table** with before/after, even from a 10-user pilot.
7. **NGO/expert letters** signal external validation. Target 3.
8. **Architecture diagram is an image**, labelled, not just mermaid (judges OCR).
9. **Dogfooding** — run NyayaAI on UCI Adult, COMPAS, Obermeyer 2019 and publish in `/benchmarks/`. Matches the 2026 theme exactly.
10. **Rubric-mirrored README H2s** — literal section titles "Problem", "Solution", "Technical Complexity", "AI Integration", "Security & Privacy", "Accessibility", "Measurable Impact", "Future Roadmap".

## Common failure modes to avoid

- Generic chatbot wrapper → fails "could a simpler approach have worked?"
- No deployed artifact (Figma-only) → fails UX
- Only one Google service → fails Creative Use
- Vague impact ("can help millions") → fails Expected Impact
- Solo/2-person team → signals under-scope
- Demo >3 min or all slides → fails UX
- README without architecture diagram → fails Technical Merit

## Content rules for the video (96s target)

- 0:00–0:08 cold open on Santoshi Kumari (§3 of plan).
- 0:08–0:18 four global+India stat cards.
- 0:18–0:25 title + SDG 10 + SDG 16 icons + tagline.
- 0:25–1:15 screen-recording of the actual audit.
- 1:15–1:35 Hindi toggle + voice-input demo + offline Nano.
- 1:35–1:42 Google-stack card.
- 1:42–1:50 NGO logos + GitHub stars.
- 1:50–1:56 tagline + URL + team photo.
- Captions burned in (Whisper → hand-correct).
- Audio-described alt track (AA rubric).

## Content rules for the README

Follow the template in `IMPLEMENTATION_PLAN.md` §18 verbatim. Every H2 is a rubric keyword. Every table is scannable. Every claim has a citation or a reproducible benchmark.

## NGO outreach email template (short form)

Subject: `NyayaAI — request for a letter of support for GSC 2026`

Body opens with:
1. One sentence: what NyayaAI is.
2. One sentence: why their org is the right supporter (cite a specific piece of their work).
3. One sentence ask: "Would you be open to reviewing our demo and, if useful, sharing a short letter or quote we can include in our submission?"
4. GitHub + live URL + 96s video.

Targets: IFF (Apar Gupta / Prateek Waghre), CIS (Amber Sinha / Divij Joshi), Aapti (Sarayu Natarajan / Astha Kapoor).

## Anti-patterns in artifact text

- ❌ "We leveraged cutting-edge AI" → ✅ "We used Gemini 3.1 Pro for multi-step reasoning and Gemini 3 Flash for throughput."
- ❌ "Helps millions of users" → ✅ "Addressable: 1.4B DPI users; 900M eligible PDS beneficiaries."
- ❌ "AI-powered dashboard" → ✅ "Seven-agent ADK orchestrator over Fairlearn + Vertex AI Model Evaluation."
- ❌ "Scalable and secure" → ✅ "Cloud Run autoscale; VPC-SC perimeter; asia-south1 data residency."
- ❌ Adjectives without evidence. Judges downrank.

## Use this skill

Whenever writing or reviewing: README, deck, video script, portal form text, GitHub release notes, LinkedIn announcement, NGO email, expert-quote request, benchmark summary.

## See also

- `IMPLEMENTATION_PLAN.md` §1, §17, §18, §19, §20, §21
