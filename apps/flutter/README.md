# apps/flutter — NyayaAI client (web prototype)

Single-page Flutter **web** app for the GSC 2026 prototype: upload a dataset,
run the three NyayaAI agents server-side, and open the rendered audit report.

The Android / iOS / voice / offline Gemini Nano 4 / TA-BN localisation paths
are deferred to the finals build.

## Stack

- Flutter 3.24+, Dart 3.5+
- Material 3, India-flag accent palette (saffron / navy / green) mirrored from
  the report template at `services/reporter/.../templates/report.html.j2`
- Riverpod 2.x for state, `go_router` for routing
- `http` + `http_parser` for multipart upload, `file_picker` for dataset
  selection, `url_launcher` to open the rendered report
- Shared Dart contracts via the path package
  `packages/contracts/dart/nyayai_contracts/`
- `firebase_ai` is NOT used from the client — all Gemini calls are server-side

## Layout

```
lib/
  main.dart                       enables web a11y then runs NyayaApp
  app/                            MaterialApp + theme + go_router
  features/
    audit/                        single prototype screen + controller
    landing/                      bilingual (EN + HI) banner
  shared/
    api/                          http client, ApiConfig from --dart-define
    widgets/                      metric badges, footer
test/
  audit_form_screen_test.dart     widget + validation tests
  api_client_test.dart            unit tests with a mocked http.Client
```

## Running

Point at the FastAPI gateway (default `http://localhost:8080`):

```bash
cd apps/flutter
flutter pub get
flutter run -d chrome --dart-define=API_BASE=http://localhost:8080
```

## Building for web

```bash
flutter build web --release --dart-define=API_BASE=https://api.nyayai.app
```

Deploy the `build/web/` output to Firebase Hosting. Ensure the API's
`CORSMiddleware` `allowed_origins` includes the hosting domain.

## Tests

```bash
flutter test
```

The widget tests exercise rendering + client-side validation; the API client
tests use `http/testing.dart`'s `MockClient`. No Flutter driver / integration
tests yet (deferred).

## Accessibility

- Semantics enabled at startup via `SemanticsBinding.instance.ensureSemantics()`
  so screen readers and axe-core see the DOM from the first paint.
- Minimum tap target 48x48; focus ring is 3px navy.
- `Semantics(liveRegion: true)` wraps the progress hint and form-level errors.
- Color is never the only status signal — every badge pairs color with icon
  and text.
- Text scaler clamped to 2.0 in `app.dart` to honour WCAG 2.2 SC 1.4.4
  without breaking the layout at extreme OS settings.

## Environment

| Variable     | Default                 | Purpose                           |
| ------------ | ----------------------- | --------------------------------- |
| `API_BASE`   | `http://localhost:8080` | FastAPI gateway base URL          |

Set via `--dart-define=API_BASE=...` at build/run time.
