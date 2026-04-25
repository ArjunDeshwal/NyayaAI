import 'package:go_router/go_router.dart';

import '../features/audit/audit_form_screen.dart';
import '../features/history/audit_history_screen.dart';

/// Prototype router. Two routes today:
///   * `/`        — main audit form + result card.
///   * `/history` — local audit history (browser localStorage).
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
    ],
  );
}
