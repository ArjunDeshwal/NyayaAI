import 'package:flutter/foundation.dart';
import 'package:go_router/go_router.dart';

import '../features/audit/audit_form_screen.dart';
import '../features/auth/auth_provider.dart';
import '../features/auth/sign_in_screen.dart';
import '../features/compare/compare_screen.dart';
import '../features/history/audit_history_screen.dart';

/// Prototype router.
///
///   * `/`          — public — main audit form + result card.
///   * `/signin`    — public — email/password + anonymous sign-in.
///   * `/history`   — protected — local audit history.
///   * `/compare`   — protected — pairwise audit diff.
///
/// Protected routes redirect to `/signin?next=<original-path>` when the
/// user is not signed in. Anonymous sessions count as signed in (the
/// guarded routes only need *some* user id, not necessarily an email).
///
/// `refreshListenable` is the FirebaseAuth state notifier — go_router
/// re-runs the redirect every time the user signs in or out.
GoRouter buildRouter({Listenable? refresh}) {
  return GoRouter(
    initialLocation: '/',
    refreshListenable: refresh,
    redirect: (context, state) {
      final path = state.uri.path;
      const protected = {'/history', '/compare'};
      final isProtected = protected.contains(path);
      final authed = isAuthenticatedNow();

      // Bounce signed-in users away from /signin to their next= or /.
      if (path == '/signin' && authed) {
        final next = state.uri.queryParameters['next'];
        return next != null && next.startsWith('/') ? next : '/';
      }

      if (!isProtected) return null;
      if (authed) return null;
      final next = Uri.encodeComponent(state.uri.toString());
      return '/signin?next=$next';
    },
    routes: <GoRoute>[
      GoRoute(
        path: '/',
        name: 'audit',
        builder: (context, state) => const AuditFormScreen(),
      ),
      GoRoute(
        path: '/signin',
        name: 'signin',
        builder: (context, state) {
          final next = state.uri.queryParameters['next'];
          return SignInScreen(next: next);
        },
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
