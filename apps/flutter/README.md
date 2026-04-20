# apps/flutter — NyayaAI Client (web + Android + iOS)

Single Flutter codebase: **auditor dashboard** (web-first) and **citizen portal** (mobile-first). Owner subagent: `flutter-engineer`.

## Stack

- Flutter stable (3.41.x line)
- Material 3 · dark mode · high-contrast variant
- Riverpod 3.x · go_router · intl (EN / HI / TA / BN)
- `firebase_ai` (Firebase AI Logic) — **not** the deprecated `firebase_vertexai` or `google_generative_ai`
- Firebase Auth / Firestore / Hosting / App Check / Crashlytics / Remote Config
- Google Speech-to-Text (voice input)
- Gemini Nano 4 via AICore Developer Preview (Android offline mode)
- Google Maps Platform (district-level choropleth)

## Layout

```
lib/
  app/          MaterialApp, router, theme, localization
  features/     auditor-dashboard · citizen-portal · audit-run · report
  shared/       design-system, widgets, utils
test/           widget + integration tests
```

## Accessibility target

WCAG 2.2 AA across every screen. Verified with TalkBack + VoiceOver before merge. See `.claude/skills/flutter-improving-accessibility/SKILL.md`.

## Running

```bash
flutter pub get
flutter run -d chrome            # web
flutter run -d <device>          # Android / iOS
flutter test
```
