# packages/india-taxonomy — India-Context Protected Attributes

First-class protected-attribute schema for Indian datasets. Absent from every competitor tool. See [`.claude/skills/nyayai-india-taxonomy/SKILL.md`](../../.claude/skills/nyayai-india-taxonomy/SKILL.md) for the canonical spec.

## What's in here

- `src/schema.py` — Pydantic enums: caste, religion, region, mother-tongue, gender, age, disability, digital-literacy
- `src/proxies.py` — Surname-proxy detector, PIN-code-to-district mapping, language-script detector
- `src/mapper.py` — Maps user-supplied column names to canonical enums
- `locales/en.arb` · `hi.arb` · `ta.arb` · `bn.arb` — localized labels

## Data sources

- Constitution of India Schedules (caste categories)
- Census of India Language Atlas (mother-tongue codes)
- MoPR Local Government Directory (district codes)
- RPwD Act 2016 Schedule (disability categories)
- Transgender Persons (Protection of Rights) Act 2019 (gender recognition)
- IndicNLP / CDAC name dataset (gender inference priors)
