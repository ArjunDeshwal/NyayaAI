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
  testWidgets('renders the landing banner and form controls', (tester) async {
    await tester.pumpWidget(_harness());
    await tester.pump();

    // Bilingual wordmark is present.
    expect(find.textContaining('न्याय AI'), findsOneWidget);

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
    await tester.pumpWidget(_harness());
    await tester.pump();

    await tester.tap(find.widgetWithText(FilledButton, 'Run audit'));
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
