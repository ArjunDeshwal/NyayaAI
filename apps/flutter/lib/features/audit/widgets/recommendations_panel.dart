import 'package:flutter/material.dart';

import '../../../app/theme.dart';
import '../../../shared/api/audit_report.dart';

/// Severity-grouped recommendations panel.
///
/// Renders the Narrator's `recommendations` list, grouped into three
/// sections (action_required → advisory → info) with colour-coded headers.
/// Empty groups collapse silently.
class RecommendationsPanel extends StatelessWidget {
  const RecommendationsPanel({super.key, required this.recommendations});

  final List<AuditRecommendation> recommendations;

  @override
  Widget build(BuildContext context) {
    if (recommendations.isEmpty) return const SizedBox.shrink();

    final byBucket = <String, List<AuditRecommendation>>{
      'action_required': [],
      'advisory': [],
      'info': [],
    };
    for (final r in recommendations) {
      byBucket.putIfAbsent(r.severity, () => []).add(r);
    }

    final hasAction = (byBucket['action_required'] ?? const []).isNotEmpty;
    final actionCount = byBucket['action_required']?.length ?? 0;
    final advisoryCount = byBucket['advisory']?.length ?? 0;
    final infoCount = byBucket['info']?.length ?? 0;

    return Semantics(
      container: true,
      label: 'Recommendations panel. '
          '$actionCount action-required, '
          '$advisoryCount advisory, '
          '$infoCount informational.',
      child: Container(
        padding: const EdgeInsets.all(20),
        decoration: BoxDecoration(
          color: NyayaColors.card,
          borderRadius: BorderRadius.circular(12),
          border: Border.all(
            color: hasAction
                ? NyayaColors.fail.withValues(alpha: 0.5)
                : NyayaColors.border,
            width: hasAction ? 2 : 1,
          ),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(
                  hasAction ? Icons.priority_high : Icons.task_alt_outlined,
                  size: 20,
                  color: hasAction ? NyayaColors.fail : NyayaColors.navy,
                ),
                const SizedBox(width: 8),
                Text(
                  'Recommendations',
                  style: Theme.of(context).textTheme.titleLarge,
                ),
                const Spacer(),
                _CountChip(
                  label: 'action',
                  count: actionCount,
                  color: NyayaColors.fail,
                ),
                const SizedBox(width: 6),
                _CountChip(
                  label: 'advisory',
                  count: advisoryCount,
                  color: NyayaColors.warn,
                ),
                const SizedBox(width: 6),
                _CountChip(
                  label: 'info',
                  count: infoCount,
                  color: NyayaColors.navy,
                ),
              ],
            ),
            const SizedBox(height: 4),
            const Text(
              'Sorted by severity. Action-required items must be resolved '
              'before deploying the model under the chosen regime.',
              style: TextStyle(color: NyayaColors.muted, fontSize: 13),
            ),
            const SizedBox(height: 16),
            if (actionCount > 0)
              _Group(
                title: 'Action required',
                color: NyayaColors.fail,
                bg: const Color(0xFFFEE2E2),
                items: byBucket['action_required']!,
              ),
            if (actionCount > 0 && advisoryCount > 0)
              const SizedBox(height: 12),
            if (advisoryCount > 0)
              _Group(
                title: 'Advisory',
                color: NyayaColors.warn,
                bg: const Color(0xFFFEF3C7),
                items: byBucket['advisory']!,
              ),
            if ((actionCount + advisoryCount) > 0 && infoCount > 0)
              const SizedBox(height: 12),
            if (infoCount > 0)
              _Group(
                title: 'Informational',
                color: NyayaColors.navy,
                bg: const Color(0xFFE0E7FF),
                items: byBucket['info']!,
              ),
          ],
        ),
      ),
    );
  }
}

class _CountChip extends StatelessWidget {
  const _CountChip({
    required this.label,
    required this.count,
    required this.color,
  });

  final String label;
  final int count;
  final Color color;

  @override
  Widget build(BuildContext context) {
    final dim = count == 0;
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
      decoration: BoxDecoration(
        color: dim ? Colors.transparent : color.withValues(alpha: 0.10),
        borderRadius: BorderRadius.circular(10),
        border: Border.all(
          color: dim ? NyayaColors.border : color.withValues(alpha: 0.40),
        ),
      ),
      child: Text(
        '$count $label',
        style: TextStyle(
          fontSize: 11,
          fontWeight: FontWeight.w700,
          color: dim ? NyayaColors.muted : color,
          letterSpacing: 0.3,
          fontFeatures: const [FontFeature.tabularFigures()],
        ),
      ),
    );
  }
}

class _Group extends StatelessWidget {
  const _Group({
    required this.title,
    required this.color,
    required this.bg,
    required this.items,
  });

  final String title;
  final Color color;
  final Color bg;
  final List<AuditRecommendation> items;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Container(
          padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
          decoration: BoxDecoration(
            color: bg,
            borderRadius: BorderRadius.circular(6),
          ),
          child: Text(
            title.toUpperCase(),
            style: TextStyle(
              fontSize: 11,
              fontWeight: FontWeight.w800,
              color: color,
              letterSpacing: 0.6,
            ),
          ),
        ),
        const SizedBox(height: 8),
        for (final r in items)
          Padding(
            padding: const EdgeInsets.symmetric(vertical: 4),
            child: _RecommendationRow(rec: r, accent: color),
          ),
      ],
    );
  }
}

class _RecommendationRow extends StatelessWidget {
  const _RecommendationRow({required this.rec, required this.accent});

  final AuditRecommendation rec;
  final Color accent;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.fromLTRB(14, 12, 14, 12),
      decoration: BoxDecoration(
        color: NyayaColors.bg,
        borderRadius: BorderRadius.circular(8),
        border: Border(
          left: BorderSide(color: accent, width: 4),
          top: const BorderSide(color: NyayaColors.border),
          right: const BorderSide(color: NyayaColors.border),
          bottom: const BorderSide(color: NyayaColors.border),
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            rec.title,
            style: const TextStyle(
              fontSize: 14,
              fontWeight: FontWeight.w700,
              color: NyayaColors.ink,
              height: 1.35,
            ),
          ),
          const SizedBox(height: 4),
          Text(
            rec.detail,
            style: const TextStyle(
              fontSize: 12,
              color: NyayaColors.ink,
              height: 1.5,
            ),
          ),
        ],
      ),
    );
  }
}
