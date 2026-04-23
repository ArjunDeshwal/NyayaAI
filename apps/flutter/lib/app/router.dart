import 'package:go_router/go_router.dart';

import '../features/audit/audit_form_screen.dart';

/// Prototype router — single `/` route. More routes (run history, citizen
/// portal, etc.) arrive in the finals build.
GoRouter buildRouter() {
  return GoRouter(
    initialLocation: '/',
    routes: <GoRoute>[
      GoRoute(
        path: '/',
        name: 'audit',
        builder: (context, state) => const AuditFormScreen(),
      ),
    ],
  );
}
