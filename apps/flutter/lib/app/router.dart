import 'package:go_router/go_router.dart';

import '../features/audit/audit_form_screen.dart';
import '../features/compare/compare_screen.dart';
import '../features/history/audit_history_screen.dart';

/// Prototype router.
///   * `/`        — main audit form + result card.
///   * `/history` — local audit history (browser localStorage).
///   * `/compare` — pairwise diff between two audits in history.
GoRouter buildRouter() {
  return GoRouter(
    initialLocation: '/',
    routes: <GoRoute>[
      GoRoute(
        path: '/',
        name: 'audit',
        builder: (context, state) => const AuditFormScreen(),
      ),
      GoRoute(
        path: '/history',
        name: 'history',
        builder: (context, state) => const AuditHistoryScreen(),
      ),
      GoRoute(
        path: '/compare',
        name: 'compare',
        builder: (context, state) => const CompareScreen(),
      ),
    ],
  );
}
