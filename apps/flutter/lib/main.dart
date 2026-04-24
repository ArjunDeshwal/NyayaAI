import 'package:flutter/foundation.dart';
import 'package:flutter/widgets.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'app/app.dart';

void main() {
  // Initialize Flutter bindings explicitly to avoid a startup race where
  // SemanticsBinding.instance is touched before WidgetsFlutterBinding ran.
  WidgetsFlutterBinding.ensureInitialized();

  // Flutter web ships a11y off by default for perf. NyayaAI serves judges,
  // regulators, and assistive-tech users. Force-enable the semantics tree so
  // screen readers and axe-core can traverse the UI from the first paint.
  if (kIsWeb) {
    WidgetsBinding.instance.ensureSemantics();
  }
  runApp(const ProviderScope(child: NyayaApp()));
}
