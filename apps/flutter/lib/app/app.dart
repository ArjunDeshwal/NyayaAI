import 'dart:async';

import 'package:firebase_auth/firebase_auth.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import 'router.dart';
import 'theme.dart';

/// `Listenable` adapter for the FirebaseAuth state stream.
///
/// `GoRouter` re-evaluates its `redirect` whenever this notifies. We piggy-
/// back on `authStateChanges()` so signing in / signing out causes
/// protected-route guards to re-check immediately.
///
/// Tolerates Firebase being uninitialized: if the FirebaseAuth.instance
/// access throws (e.g. firebase_core_web plugin glue missing on this build),
/// the notifier silently no-ops instead of crashing the app at startup.
class _AuthChangeNotifier extends ChangeNotifier {
  _AuthChangeNotifier() {
    try {
      _sub = FirebaseAuth.instance.authStateChanges().listen((_) {
        notifyListeners();
      });
    } catch (_) {
      _sub = null;
    }
  }
  StreamSubscription<User?>? _sub;

  @override
  void dispose() {
    _sub?.cancel();
    super.dispose();
  }
}

final _authNotifierProvider = Provider<_AuthChangeNotifier>((ref) {
  final n = _AuthChangeNotifier();
  ref.onDispose(n.dispose);
  return n;
});

final _routerProvider = Provider<GoRouter>((ref) {
  final notifier = ref.watch(_authNotifierProvider);
  return buildRouter(refresh: notifier);
});

class NyayaApp extends ConsumerWidget {
  const NyayaApp({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final router = ref.watch(_routerProvider);
    return MaterialApp.router(
      title: 'NyayaAI — Bias auditor',
      debugShowCheckedModeBanner: false,
      theme: buildNyayaTheme(),
      routerConfig: router,
      builder: (context, child) {
        // Clamp text scaling so runaway OS font sizes never break the layout,
        // but still honour up to 200% per WCAG 2.2 SC 1.4.4.
        final media = MediaQuery.of(context);
        return MediaQuery(
          data: media.copyWith(
            textScaler:
                media.textScaler.clamp(minScaleFactor: 1.0, maxScaleFactor: 2.0),
          ),
          child: child ?? const SizedBox.shrink(),
        );
      },
    );
  }
}
