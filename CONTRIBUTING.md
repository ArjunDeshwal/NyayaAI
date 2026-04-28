# Contributing to NyayaAI

NyayaAI is built for the Google Solution Challenge 2026. Contributions from outside are welcome after the submission window.

## Branching

- Trunk-based. Short-lived feature branches off `main`.
- Conventional Commits (`feat:`, `fix:`, `chore:`, `docs:`, `test:`, `refactor:`).
- PRs require green CI + one approving reviewer from `CODEOWNERS`.
- No direct pushes to `main`.

## Local setup

```bash
./scripts/bootstrap.sh
```

Runs: `uv sync` (Python), `pnpm install` (TS), `fvm install` + `flutter pub get`, `terraform init` (staging).

## Running tests

```bash
make test          # full suite
make test.fast     # unit only
make benchmark     # reproduce UCI Adult + COMPAS + MUDRA-Lite
make eval          # Genkit agent evals (TS)
```

## PR checklist

- [ ] CI is green
- [ ] Tests added or updated
- [ ] If touching `services/fairness/`, property tests updated
- [ ] If touching `services/orchestrator/`, Genkit evals ≥95% pass
- [ ] If touching PII code path, `compliance-auditor` reviewed
- [ ] If touching infra, `terraform plan` attached
- [ ] If user-visible, a11y reviewed, strings localized to EN/HI/TA/BN
- [ ] If submission-facing, `gsc-submission-reviewer` scored ≥8/10

## Security

See `SECURITY.md`. Report vulnerabilities to the tech lead via encrypted channel — never file a public issue.
