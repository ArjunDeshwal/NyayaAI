# services/reporter — Bilingual Audit Report Generator

Narrator agent's downstream renderer. Takes a completed audit bundle and emits:

- Primary audit PDF (EN + one of HI/TA/BN)
- EU AI Act conformity annex (if applicable)
- Machine-readable JSON report
- Model card (Markdown + protobuf — Google Model Card Toolkit schema)
- Reproducibility bundle (dataset fingerprint, model fingerprint, audit config, seeds)
- Hash-signed PDF (SHA-256) committed to the retention-locked log

Owner: `compliance-auditor` (templates), `agent-architect` (Narrator prompts).

## Templates

DPDP Rule 13 DPIA sections + EU AI Act Art. 9/10/13/14/15 mapping. See `.claude/skills/nyayai-dpdp-compliance/SKILL.md`.

## Stack

- Python 3.12
- Jinja2 templates → WeasyPrint PDF
- Chirp TTS (audio summary for ombudsmen)
- Imagen 4 (generated chart images embedded)
- Google Model Card Toolkit schema

## Run

```bash
uv sync
uv run python -m reporter.cli --audit-id <id>
```
