import 'package:flutter/material.dart';

import '../../app/theme.dart';

enum BadgeKind { pass, fail, warn, info, noData }

/// Pill-shaped status badge. Color is never the only signal — we pair it with
/// an icon and a text label so users with color-vision differences still
/// perceive pass/fail.
class MetricBadge extends StatelessWidget {
  const MetricBadge({
    super.key,
    required this.kind,
    required this.label,
    this.semanticsLabel,
  });

  final BadgeKind kind;
  final String label;
  final String? semanticsLabel;

  ({Color bg, Color fg, IconData icon}) _style() {
    switch (kind) {
      case BadgeKind.pass:
        return (
          bg: const Color(0xFFDCFCE7),
          fg: NyayaColors.ok,
          icon: Icons.check_circle,
        );
      case BadgeKind.fail:
        return (
          bg: const Color(0xFFFEE2E2),
          fg: NyayaColors.fail,
          icon: Icons.cancel,
        );
      case BadgeKind.warn:
        return (
          bg: const Color(0xFFFEF3C7),
          fg: NyayaColors.warn,
          icon: Icons.warning_amber_rounded,
        );
      case BadgeKind.info:
        return (
          bg: const Color(0xFFE0E7FF),
          fg: NyayaColors.navy,
          icon: Icons.info_outline,
        );
      case BadgeKind.noData:
        return (
          bg: const Color(0xFFF3F4F6),
          fg: NyayaColors.muted,
          icon: Icons.help_outline,
        );
    }
  }

  @override
  Widget build(BuildContext context) {
    final style = _style();
    return Semantics(
      label: semanticsLabel ?? label,
      container: true,
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
        decoration: BoxDecoration(
          color: style.bg,
          borderRadius: BorderRadius.circular(16),
          border: Border.all(color: style.fg.withValues(alpha: 0.25)),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(style.icon, size: 16, color: style.fg),
            const SizedBox(width: 6),
            Text(
              label,
              style: TextStyle(
                color: style.fg,
                fontWeight: FontWeight.w700,
                fontSize: 12,
                letterSpacing: 0.4,
              ),
            ),
          ],
        ),
      ),
    );
  }
}
