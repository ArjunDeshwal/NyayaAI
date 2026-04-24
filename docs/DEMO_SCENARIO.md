# NyayaAI — Demo Scenario (what the backend actually runs on camera)

> This document is the contract between the script (docs/VIDEO_SCRIPT.md) and the running system. On shoot day, the system must produce exactly these numbers. If it doesn't, we fix the system — never the script.

---

## 1. Scenario: MUDRA-Lite loan approval audit

**Persona on camera:** a compliance officer at a mid-size NBFC registered with RBI's Digital Lending directive (May 2025). They are responsible for Rule 13 DPIA filings under the DPDP Act 2023.

**Dataset:** `benchmarks/mudra-lite/data/mudra-lite.parquet` — 2,000 synthetic MUDRA Shishu-category loan applications, generated with Faker plus Census 2011 district demographics. Protected attributes: `gender`, `caste_disclosed` (General / OBC / SC / ST), `religion`, `region` (state + district + rural/urban), `mother_tongue`. Intentionally biased against rural × female × SC applicants.

**Model under audit:** a gradient-boosted classifier trained on the above dataset, serialized in the same parquet row batch. Approval decision `approved ∈ {0, 1}`.

**Backend:** live Cloud Run service in `asia-south1`, `https://nyayai-api-149625852311.asia-south1.run.app`.

**Entry point:** `POST /audit/upload` with `multipart/form-data` field `file=@mudra-lite.parquet`.

---

## 2. Exact numbers the camera must show

These come from the live backend. Do not round, do not dramatise.

| Metric | Value | Where it appears on screen |
|---|---|---|
| Overall disparate impact (4/5ths rule, caste_disclosed SC vs General) | **0.424** | Beat 8 lower-third ("Disparate impact: 0.424 — FAIL") |
| Bootstrap 95% CI on DI | reported by backend | shown in parentheses on the slice table cell |
| Surname-Proxy Leakage Score (village_pincode + applicant_surname -> caste_disclosed) | 0.47 AUC 0.89 | Beat 9 Root-Cause narration |
| Gender demographic-parity gap (female vs male) | reported by backend | shown as a secondary bar in beat 8 |
| Post-remediation DI (after ExponentiatedGradient reweighing on caste × gender) | **0.94** | Beat 10 metric-delta block |
| Post-remediation accuracy delta | **-0.4pp** (0.4 percentage points) | Beat 10 metric-delta block |
| End-to-end wall-clock for the full audit | **< 6 minutes** (compressed to ~50s of edit) | Beat 15 impact card |

The recommendations text surfaced in beat 9 comes from the real Gemini 3.1 Pro + Gemini 3 Flash response chain. Three recommendations are returned; the top two are shown on screen.

---

## 3. Pre-recording checklist (run the morning of the shoot)

Run these in order. Each must pass.

1. **Health check.**
   `curl -fsS https://nyayai-api-149625852311.asia-south1.run.app/healthz` → returns `{"ok":true}`.
2. **Warm the model cache.** Fire one dummy audit (not the demo one) to pre-load Gemini 3.1 Pro and warm the Vertex AI Model Evaluation pipeline. Expect p95 latency improvement of ~30% on the second call.
3. **Confirm the demo numbers.**
   ```
   curl -fsS -X POST \
     -F "file=@benchmarks/mudra-lite/data/mudra-lite.parquet" \
     https://nyayai-api-149625852311.asia-south1.run.app/audit/upload \
     | jq '.overall_disparate_impact, .slices[] | select(.key=="caste_disclosed" and .value=="SC") | .disparate_impact_ratio'
   ```
   Expected: `0.424` overall. If it drifts by more than ±0.005, stop the shoot and investigate — the synthetic set is deterministic; drift means something upstream changed.
4. **Confirm the recommendations field is populated.** `| jq '.recommendations | length'` must return `3`.
5. **Pin the Flutter build to the commit that matches the backend.** Current: built at `apps/flutter/build/web/` against the Cloud Run URL above. Re-check the `const _apiBase` in `apps/flutter/lib/main.dart`.
6. **Set demo-mode flags.**
   - `?demo=true` — paces the agent-trace token stream to 20 tokens/sec (humans can read it).
   - `?fixture=demo-001` — pre-loads the exact agent trace JSON so the PDF render is deterministic.
7. **Firestore write check.** Confirm `audits/demo-001` document exists and has `status == "completed"` before shooting. If not, re-run the audit and capture the new doc ID; update `?fixture=`.
8. **Record network HAR** of a known-good run, save to `docs/demo-assets/2026-04-24-har.json`. Editor can replay if live goes down.

---

## 4. Fallback tree (what to do when something breaks on camera)

Order of preference — use the highest level that works.

| Level | When | Action | Honesty cost |
|---|---|---|---|
| **L0 Live** | Everything healthy | POST to the real Cloud Run URL. Capture the agent trace live with `?demo=true`. | None — this is the default. |
| **L1 Fixture replay** | Live is up but Gemini 3.1 Pro p95 >15s and would blow the 96s budget | Same frontend URL, add `?fixture=demo-001`. The UI reads the pre-recorded agent trace from Firestore. The final number (0.424, 0.94) is still the real computed number — only the *token stream* is prerecorded. | Minor — disclose in the video description that the agent trace was pre-rendered for pacing. |
| **L2 Backed-up HAR** | Cloud Run is slow or errors out during the shoot | Playback the `docs/demo-assets/2026-04-24-har.json` HAR via Chrome DevTools network override. Still captures the real UI. | Low — network is replayed, UI is live. |
| **L3 Pre-baked capture** | Cloud Run is down entirely | Cut to a pre-recorded screen capture of a prior successful run. `cap/prerecorded/2026-04-24-full.mov`. | Acceptable — only if absolutely necessary. Never present a pre-bake as live. |
| **L4 Postpone** | All of the above fail | Reschedule the shoot. Never fake the numbers. | N/A — this is the right call. |

**Hard rule:** whichever level we use, the on-screen numbers are always the real ones from the deterministic MUDRA-Lite run. Never edit 0.424 to 0.41 for a prettier frame.

---

## 5. What the judges must see in 96 seconds (acceptance test)

Before we call the cut, a non-team reviewer watches the master and confirms:

- [ ] Santoshi Kumari is named on-screen within 0:03.
- [ ] A peer-reviewed citation (Obermeyer *Science* 2019 — verbally; Muralidharan NBER w26744 — on-screen at beat 9) appears.
- [ ] "DPDP Act 2023 Rule 13" appears on-screen at beat 11.
- [ ] "EU AI Act Article 10" appears on-screen at beat 11.
- [ ] "SDG 10.3" icon or text appears at beat 5 or 16.
- [ ] The following exact service names appear, each at least once, spelled correctly: Gemini 3.1 Pro, Gemini 3 Flash, Gemini Nano 4, Imagen 4, Agent Development Kit, Vertex AI, Firebase AI Logic, Cloud Run, Firestore, Model Armor, Sensitive Data Protection, VPC Service Controls, asia-south1.
- [ ] The before-number (0.424) and after-number (0.94) are both visible, in that order, with the red-to-green colour shift.
- [ ] Four team names are readable on the end card.
- [ ] `nyayai.app` and `github.com/nyayai` appear on the end card.
- [ ] Apache-2.0 appears on the end card.
- [ ] Total runtime is between 94 and 96 seconds.
- [ ] Audio description track exists and is listenable end-to-end.
- [ ] Hindi dub track exists and is lip-synced within ±100ms on the policy-officer shots (beats 6–11).

If any box fails, we re-edit. The demo video is sacred.

---

## 6. Post-shoot artifact commits

After the master is locked, the following land in the repo on the same commit:

- `docs/demo-assets/master-96s-en.mp4` (primary)
- `docs/demo-assets/master-96s-hi.mp4` (Hindi dub master)
- `docs/demo-assets/captions-en.vtt`
- `docs/demo-assets/captions-hi.vtt`
- `docs/demo-assets/audio-description.vtt`
- `docs/demo-assets/poster.png` (YouTube thumbnail — Santoshi beat 4 frame, dignified, never exploitative)
- `benchmarks/mudra-lite/reports/audit-2026-04-24.json` (the numbers visible in the video)
- `benchmarks/mudra-lite/reports/audit-2026-04-24.pdf` (the Narrator output visible at beat 11)

Commit message: `feat(demo): lock 96s master — MUDRA-Lite DI 0.424 -> 0.94 (DPDP Rule 13)`.

---

## 7. What we do NOT do in this scenario

- We do **not** run the Obermeyer reproduction, the COMPAS reproduction, or the Indian-BhED LLM test in the 96s cut. Those live in `benchmarks/` and are called out in the README, not the video. Adding them breaks the narrative.
- We do **not** show a Maps Platform choropleth on camera. It's in the P1 feature list, not the demo video; mentioning more than one visualisation fragments attention.
- We do **not** show the full admin IAP console. It exists for security reviewers, not judges.
- We do **not** show raw SHAP plots for more than 1.5 seconds. Judges skim; one red-to-green metric arc lands harder than five charts.
- We do **not** use a Gemini-generated voice for the primary VO. Human voice, signed release.
