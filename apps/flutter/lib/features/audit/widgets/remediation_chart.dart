import 'package:fl_chart/fl_chart.dart';
import 'package:flutter/material.dart';

import '../../../app/theme.dart';
import '../../../shared/api/audit_report.dart';

/// Paired bar chart: per-attribute demographic-parity ratio Before vs After
/// remediation. Includes a 0.8 four-fifths-rule threshold line.
///
/// Behaviour:
///   * Bars at or above 0.8 render in [NyayaColors.ok] (green).
///   * Bars below 0.8 render in [NyayaColors.fail] (red).
///   * The "After" bar is only present on the remediation target attribute;
///     all other attributes show their Before bar greyed out (the audit only
///     remediates one slice).
///   * If [report.remediation] is null, the chart degrades to Before-only.
///   * Bars animate in over 800 ms.
class RemediationChart extends StatelessWidget {
  const RemediationChart({super.key, required this.report});

  final AuditReport report;

  @override
  Widget build(BuildContext context) {
    final beforeMap = report.perAttributeDpRatio();
    final attributes = beforeMap.keys.toList()..sort();

    if (attributes.isEmpty) {
      return _emptyState(
        'No per-attribute demographic-parity ratios available for this audit.',
      );
    }

    final remediation = report.remediation;
    final targetAttribute = remediation?.targetAttribute;
    final beforeOverall = remediation?.beforeDpRatio;
    final afterOverall = remediation?.afterDpRatio;
    final delta = remediation?.delta;

    final groups = <BarChartGroupData>[];
    for (var i = 0; i < attributes.length; i++) {
      final attr = attributes[i];
      final beforeVal = beforeMap[attr] ?? 0.0;
      final isTarget = remediation?.improved == true && attr == targetAttribute;
      final hasAfter = isTarget && afterOverall != null;
      final afterVal = hasAfter ? afterOverall : null;
      // Spec: when remediation succeeded, the non-target attributes show
      // their Before bar greyed out (we did not retrain for them). The
      // target attribute and the no-remediation case both keep the real
      // pass/fail palette.
      final muteBefore = remediation?.improved == true && !isTarget;

      groups.add(
        BarChartGroupData(
          x: i,
          barsSpace: 6,
          barRods: [
            BarChartRodData(
              toY: beforeVal.clamp(0.0, 1.0),
              width: 16,
              borderRadius: BorderRadius.circular(3),
              color: _barColor(beforeVal, muted: muteBefore),
              backDrawRodData: BackgroundBarChartRodData(
                show: true,
                toY: 1.0,
                color: NyayaColors.bg,
              ),
            ),
            if (afterVal != null)
              BarChartRodData(
                toY: afterVal.clamp(0.0, 1.0),
                width: 16,
                borderRadius: BorderRadius.circular(3),
                color: _barColor(afterVal),
                backDrawRodData: BackgroundBarChartRodData(
                  show: true,
                  toY: 1.0,
                  color: NyayaColors.bg,
                ),
              ),
          ],
          showingTooltipIndicators: const [],
        ),
      );
    }

    return Semantics(
      container: true,
      label: _semanticsSummary(beforeMap, remediation),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          _StatsRow(
            before: beforeOverall,
            after: afterOverall,
            delta: delta,
            targetAttribute: targetAttribute,
          ),
          const SizedBox(height: 18),
          SizedBox(
            height: 240,
            child: BarChart(
              BarChartData(
                alignment: BarChartAlignment.spaceAround,
                maxY: 1.0,
                minY: 0.0,
                barGroups: groups,
                gridData: const FlGridData(show: false),
                titlesData: FlTitlesData(
                  topTitles: const AxisTitles(
                    sideTitles: SideTitles(showTitles: false),
                  ),
                  rightTitles: const AxisTitles(
                    sideTitles: SideTitles(showTitles: false),
                  ),
                  leftTitles: AxisTitles(
                    sideTitles: SideTitles(
                      showTitles: true,
                      reservedSize: 36,
                      interval: 0.2,
                      getTitlesWidget: (value, meta) {
                        return Padding(
                          padding: const EdgeInsets.only(right: 4),
                          child: Text(
                            value.toStringAsFixed(1),
                            style: const TextStyle(
                              fontSize: 11,
                              color: NyayaColors.muted,
                            ),
                          ),
                        );
                      },
                    ),
                  ),
                  bottomTitles: AxisTitles(
                    sideTitles: SideTitles(
                      showTitles: true,
                      reservedSize: 36,
                      getTitlesWidget: (value, meta) {
                        final i = value.toInt();
                        if (i < 0 || i >= attributes.length) {
                          return const SizedBox.shrink();
                        }
                        final attr = attributes[i];
                        final isTarget =
                            remediation?.improved == true &&
                                attr == targetAttribute;
                        return Padding(
                          padding: const EdgeInsets.only(top: 6),
                          child: Text(
                            attr,
                            style: TextStyle(
                              fontSize: 11,
                              color: isTarget
                                  ? NyayaColors.navy
                                  : NyayaColors.ink,
                              fontWeight: isTarget
                                  ? FontWeight.w700
                                  : FontWeight.w500,
                            ),
                          ),
                        );
                      },
                    ),
                  ),
                ),
                borderData: FlBorderData(
                  show: true,
                  border: const Border(
                    left: BorderSide(color: NyayaColors.border),
                    bottom: BorderSide(color: NyayaColors.border),
                  ),
                ),
                extraLinesData: ExtraLinesData(
                  horizontalLines: [
                    HorizontalLine(
                      y: 0.8,
                      color: NyayaColors.warn,
                      strokeWidth: 2,
                      dashArray: [6, 4],
                      label: HorizontalLineLabel(
                        show: true,
                        alignment: Alignment.topRight,
                        padding: const EdgeInsets.only(right: 6, bottom: 2),
                        labelResolver: (_) => '4/5ths rule (0.8)',
                        style: const TextStyle(
                          color: NyayaColors.warn,
                          fontSize: 10,
                          fontWeight: FontWeight.w700,
                        ),
                      ),
                    ),
                  ],
                ),
              ),
              duration: const Duration(milliseconds: 800),
              curve: Curves.easeOutCubic,
            ),
          ),
          const SizedBox(height: 10),
          _Legend(hasAfter: remediation?.improved == true),
        ],
      ),
    );
  }

  static Color _barColor(double value, {bool muted = false}) {
    if (muted) return NyayaColors.muted.withValues(alpha: 0.45);
    return value >= 0.8 ? NyayaColors.ok : NyayaColors.fail;
  }

  Widget _emptyState(String message) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: NyayaColors.bg,
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: NyayaColors.border),
      ),
      child: Row(
        children: [
          const Icon(Icons.info_outline, size: 18, color: NyayaColors.muted),
          const SizedBox(width: 8),
          Expanded(
            child: Text(
              message,
              style: const TextStyle(
                color: NyayaColors.muted,
                fontSize: 13,
              ),
            ),
          ),
        ],
      ),
    );
  }

  String _semanticsSummary(
    Map<String, double> before,
    AuditRemediation? remediation,
  ) {
    final parts = <String>[
      'Before remediation, demographic-parity ratios were:',
      for (final entry in before.entries)
        '${entry.key} ${entry.value.toStringAsFixed(2)}',
    ];
    if (remediation?.improved == true && remediation?.targetAttribute != null) {
      parts.add(
        'After remediation on ${remediation!.targetAttribute}, the ratio '
        'rose from ${remediation.beforeDpRatio?.toStringAsFixed(2) ?? "n/a"} '
        'to ${remediation.afterDpRatio?.toStringAsFixed(2) ?? "n/a"}.',
      );
    }
    return parts.join(', ');
  }
}

class _StatsRow extends StatelessWidget {
  const _StatsRow({
    required this.before,
    required this.after,
    required this.delta,
    required this.targetAttribute,
  });

  final double? before;
  final double? after;
  final double? delta;
  final String? targetAttribute;

  String _fmt(double? v) => v == null ? '—' : v.toStringAsFixed(3);

  String _fmtDelta(double? d) {
    if (d == null) return '—';
    final sign = d >= 0 ? '+' : '';
    return '$sign${d.toStringAsFixed(3)}';
  }

  @override
  Widget build(BuildContext context) {
    final showDelta = delta != null && targetAttribute != null;
    return ExcludeSemantics(
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceEvenly,
        children: [
          _Stat(label: 'Before', value: _fmt(before), color: NyayaColors.ink),
          _Stat(
            label: 'After',
            value: _fmt(after),
            color: after == null ? NyayaColors.muted : NyayaColors.ink,
          ),
          _Stat(
            label: showDelta ? 'Δ ($targetAttribute)' : 'Δ',
            value: _fmtDelta(delta),
            color: (delta == null)
                ? NyayaColors.muted
                : (delta! >= 0 ? NyayaColors.ok : NyayaColors.fail),
          ),
        ],
      ),
    );
  }
}

class _Stat extends StatelessWidget {
  const _Stat({
    required this.label,
    required this.value,
    required this.color,
  });

  final String label;
  final String value;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        Text(
          label,
          style: const TextStyle(
            fontSize: 11,
            color: NyayaColors.muted,
            fontWeight: FontWeight.w600,
            letterSpacing: 0.4,
          ),
        ),
        const SizedBox(height: 2),
        Text(
          value,
          style: TextStyle(
            fontSize: 26,
            fontWeight: FontWeight.w800,
            color: color,
            fontFamily: 'monospace',
            fontFeatures: const [FontFeature.tabularFigures()],
            letterSpacing: -0.5,
          ),
        ),
      ],
    );
  }
}

class _Legend extends StatelessWidget {
  const _Legend({required this.hasAfter});

  final bool hasAfter;

  @override
  Widget build(BuildContext context) {
    return Wrap(
      spacing: 12,
      runSpacing: 6,
      children: [
        const _LegendDot(
          color: NyayaColors.fail,
          label: 'Below 0.8 (fails 4/5ths)',
        ),
        const _LegendDot(
          color: NyayaColors.ok,
          label: 'At or above 0.8 (passes)',
        ),
        if (hasAfter)
          _LegendDot(
            color: NyayaColors.muted.withValues(alpha: 0.45),
            label: 'Untargeted attribute (Before only)',
          ),
      ],
    );
  }
}

class _LegendDot extends StatelessWidget {
  const _LegendDot({required this.color, required this.label});

  final Color color;
  final String label;

  @override
  Widget build(BuildContext context) {
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Container(
          width: 10,
          height: 10,
          decoration: BoxDecoration(
            color: color,
            borderRadius: BorderRadius.circular(2),
          ),
        ),
        const SizedBox(width: 6),
        Text(
          label,
          style: const TextStyle(
            fontSize: 12,
            color: NyayaColors.muted,
          ),
        ),
      ],
    );
  }
}
