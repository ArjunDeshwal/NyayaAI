import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';

import 'package:nyayai_app/app/theme.dart';
import 'package:nyayai_app/features/audit/audit_form_screen.dart';
import 'package:nyayai_app/shared/api/api_client.dart';
import 'package:nyayai_app/shared/api/api_config.dart';

/// A mock `http.Client` that never actually gets called during these tests —
/// we only exercise form rendering + client-side validation.
http.Client _mockClient() {
  return MockClient((request) async {
    return http.Response('{}', 500);
  });
}

Widget _harness() {
  return ProviderScope(
    overrides: [
      apiConfigProvider.overrideWithValue(
        const ApiConfig(baseUrl: 'http://test.local'),
      ),
      apiClientProvider.overrideWithValue(
        NyayaApiClient(
          config: const ApiConfig(baseUrl: 'http://test.local'),
          client: _mockClient(),
        ),
      ),
    ],
    child: MaterialApp(
      theme: buildNyayaTheme(),
      home: const AuditFormScreen(),
    ),
  );
}

void main() {
  // The audit form is intentionally tall (banner + form + footer). Pin the
  // surface size to a desktop viewport so off-screen widgets are still
  // available to find.bySemanticsLabel and tap().
  setUp(() {
    TestWidgetsFlutterBinding.ensureInitialized();
  });

  testWidgets('renders the landing banner and form controls', (tester) async {
    tester.view.physicalSize = const Size(1280, 4000);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);

    await tester.pumpWidget(_harness());
    await tester.pump();

    // The bilingual wordmark lives inside a `RichText` that exposes its
    // composite text via a `Semantics(label: "NyayaAI, Nyaya A I, ...")`
    // wrapper. `find.textContaining` does not see RichText fragments, so we
    // assert via the semantics tree.
    final SemanticsHandle handle = tester.ensureSemantics();
    expect(
      find.bySemanticsLabel(RegExp('Nyaya')),
      findsWidgets,
    );
    handle.dispose();

    // Primary form section header.
    expect(find.text('Run an audit'), findsOneWidget);

    // All required text fields (labels).
    expect(find.text('Dataset name'), findsOneWidget);
    expect(find.text('Audit goal'), findsOneWidget);
    expect(find.text('Protected columns'), findsOneWidget);
    expect(find.text('Outcome column'), findsOneWidget);
    expect(find.text('Regulatory regime'), findsOneWidget);

    // File drop zone affordance.
    expect(find.text('Choose file'), findsOneWidget);

    // Submit button.
    expect(find.widgetWithText(FilledButton, 'Run audit'), findsOneWidget);
  });

  testWidgets('submitting without a file surfaces an accessible error',
      (tester) async {
    tester.view.physicalSize = const Size(1280, 4000);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);

    await tester.pumpWidget(_harness());
    await tester.pump();

    final submitFinder = find.widgetWithText(FilledButton, 'Run audit');
    await tester.tap(submitFinder, warnIfMissed: false);
    await tester.pump();

    expect(find.text('Please choose a dataset file.'), findsOneWidget);
    // Required-field errors should also render.
    expect(find.text('Dataset name is required.'), findsOneWidget);
  });

  testWidgets('has a semantics header for the primary section', (tester) async {
    await tester.pumpWidget(_harness());
    await tester.pump();

    final SemanticsHandle handle = tester.ensureSemantics();
    expect(
      find.bySemanticsLabel('Run an audit'),
      findsOneWidget,
    );
    handle.dispose();
  });
}
