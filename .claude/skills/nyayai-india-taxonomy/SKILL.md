---
name: nyayai-india-taxonomy
description: NyayaAI project skill. Use when working with India-specific protected attributes — caste, religion, region, mother-tongue, age-cohort, disability, digital-literacy. Invoke when adding a new attribute, mapping user data to the canonical schema, writing proxy warnings, or localizing labels into Hindi/Tamil/Bengali. This is the single source of truth for what counts as a protected attribute in NyayaAI.
---

# India-Context Fairness Taxonomy

NyayaAI's originality claim rests on being the only bias auditor with India protected attributes as first-class citizens. Fairlearn, AIF360, Aequitas, and every commercial competitor are US-/EU-centric. This skill is the canonical source.

## Canonical protected-attribute schema

Stored in `packages/india-taxonomy/src/schema.py` as Pydantic enums. Every protected-attribute column in any dataset must be mapped to these before metric computation.

### Caste

```
GENERAL | OBC | SC | ST | NT_DNT | UNKNOWN
```

- Source: Constitution of India Schedules + Mandal Commission groupings.
- NT-DNT (Nomadic Tribes / Denotified Tribes) is frequently omitted — include.
- **Common proxies that leak caste:** surname, village PIN (Census block), school name, mother-tongue, diet flags, father's occupation.

### Religion

```
HINDU | MUSLIM | CHRISTIAN | SIKH | BUDDHIST | JAIN | PARSI | OTHER | NONE | UNKNOWN
```

- Source: Census of India.
- **Proxies:** first name, festival references in free-text, dietary restrictions, hijri-date usage, surname (less strong than caste).

### Region

```
state_code: ISO 3166-2:IN (e.g., "IN-JH")
district_code: LGD (Local Government Directory, MoPR)
habitation: RURAL | URBAN | PERI_URBAN
```

- Source: Census LGD codes (canonical).
- **Proxies for caste/religion:** PIN code at sub-district level, Aadhaar address hash, even anonymized zip.

### Mother-tongue

```
ASM | BEN | BOD | DOG | ENG | GUJ | HIN | KAN | KAS | KOK | MAI | MAL | MAR | MEI
| NEP | ORI | PAN | SAN | SAT | SND | TAM | TEL | URD | OTHER | UNKNOWN
```

- 22 Scheduled Languages + English + Other.
- **Proxies:** script (Devanagari vs Roman vs Tamil), grammar cues in free-text (detectable by Gemini 3 Flash).

### Gender

```
FEMALE | MALE | THIRD | UNKNOWN
```

- Source: Transgender Persons (Protection of Rights) Act 2019 — THIRD is a legal category.
- **Proxies:** first-name priors (Indian names dictionary), pronouns in free-text.

### Age cohort

```
AGE_LT_18 | AGE_18_25 | AGE_26_45 | AGE_46_60 | AGE_GT_60
```

Used for intersectional slicing; do **not** bin raw age on ingest if consent is fresh.

### Disability

Per RPwD Act 2016 Schedule — 21 specified disabilities. Store as a string enum list. Common flags: visual, hearing, locomotor, intellectual, psychosocial, multiple.

### Digital-literacy proxy

```
DLQ1 | DLQ2 | DLQ3 | DLQ4 | UNKNOWN
```

Derived from: device class, OS locale, typing cadence, prior app sessions. Self-report preferred but rarely available. Used for the DLF custom metric.

## Default intersectional slices

Compute by default on every audit:

1. `rural × FEMALE × (SC|ST|NT_DNT)`
2. `URBAN × MUSLIM × AGE_18_25`
3. `disability_any=true × rural`
4. `mother_tongue=HIN × dlq=DLQ1`
5. `THIRD × any`
6. `AGE_GT_60 × DLQ1`

Rationale: these are the subgroups documented as highest-risk in Muralidharan 2020, IFF-Vidhi 2021, Amnesty 2024.

## Localization strings

All attribute labels must be localized to EN, HI, TA, BN. File: `packages/india-taxonomy/locales/{lang}.arb`. Labels are used by:
- Flutter citizen portal.
- Narrator agent's bilingual audit PDF.

## Proxy-warning engine

When a user claims a feature is "not a protected attribute", run the **surname-proxy leakage score** (see `nyayai-bias-metrics`). If SPLS ≥ 0.65 on that feature, add a `WARNING: feature '{x}' proxies '{protected_attr}'` to the audit report and refuse to drop it from the metric computation.

## Do not

- Do not hard-code caste values as strings elsewhere — import from schema.
- Do not assume gender is binary in ANY function signature or UI — `THIRD` is a first-class value.
- Do not use a US name-frequency dictionary for gender inference in India — use the IndicNLP / CDAC name dataset.
- Do not deploy without the translations for all four languages.

## References

- Census of India Language Atlas — mother-tongue codes.
- MoPR LGD (Local Government Directory) — canonical district codes.
- RPwD Act 2016 Schedule — disability categories.
- Transgender Persons (Protection of Rights) Act 2019 — gender legal recognition.
- Muralidharan, Niehaus & Sukhtankar (NBER w26744, 2020) — PDS exclusion patterns.
- Khandelwal et al., *Indian-BhED* (FAccT 2024) — caste/religion stereotypes in LLMs.

## See also

- `.claude/skills/nyayai-bias-metrics/SKILL.md`
- `IMPLEMENTATION_PLAN.md` §7
