import 'package:firebase_core/firebase_core.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter/widgets.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'app/app.dart';
import 'firebase_options.dart';

Future<void> main() async {
  // Initialize Flutter bindings explicitly to avoid a startup race where
  // SemanticsBinding.instance is touched before WidgetsFlutterBinding ran.
  WidgetsFlutterBinding.ensureInitialized();

  // Flutter web ships a11y off by default for perf. NyayaAI serves judges,
  // regulators, and assistive-tech users. Force-enable the semantics tree so
  // screen readers and axe-core can traverse the UI from the first paint.
  if (kIsWeb) {
    WidgetsBinding.instance.ensureSemantics();
  }

  // Firebase. Auth state stream is the only thing we use for now; failure
  // here should not block the app — the user can still browse and run
  // sample audits without an account.
  try {
    await Firebase.initializeApp(
      options: DefaultFirebaseOptions.currentPlatform,
    );
  } catch (e) {
    debugPrint('Firebase init failed (continuing without auth): $e');
  }

  runApp(const ProviderScope(child: NyayaApp()));
}
