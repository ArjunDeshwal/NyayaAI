import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import 'router.dart';
import 'theme.dart';

final _routerProvider = Provider<GoRouter>((ref) => buildRouter());

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
            textScaler: media.textScaler.clamp(minScaleFactor: 1.0, maxScaleFactor: 2.0),
          ),
          child: child ?? const SizedBox.shrink(),
        );
      },
    );
  }
}
