import 'package:flutter/material.dart';

import '../../../app/theme.dart';
import '../../../shared/api/audit_report.dart';

/// Severity → palette helper used by both Counterfactual and Root-Cause cards.
Color _severityColor(String? severity) {
  return switch (severity) {
    'action_required' => NyayaColors.fail,
    'advisory' => NyayaColors.warn,
    'info' => NyayaColors.navy,
    _ => NyayaColors.muted,
  };
}

Color _severityBg(String? severity) {
  return switch (severity) {
    'action_required' => const Color(0xFFFEE2E2),
    'advisory' => const Color(0xFFFEF3C7),
    'info' => const Color(0xFFDBEAFE),
    _ => const Color(0xFFF3F4F6),
  };
}

String _pct(double v) => '${(v * 100).toStringAsFixed(1)}%';

/// Counterfactual card. Renders the LLM headline + interpretation, the
/// directional flip rate, the per-pair flip-rate table, and example
/// takeaways. Omits sections that are absent.
class CounterfactualCard extends StatelessWidget {
  const CounterfactualCard({super.key, required this.cf});

  final AuditCounterfactual cf;

  @override
  Widget build(BuildContext context) {
    final severity = cf.severity ?? 'info';
    final color = _severityColor(severity);
    final bg = _severityBg(severity);

    final pairs = cf.flipRateByPair.entries.toList()
      ..sort((a, b) => b.value.compareTo(a.value));

    return Semantics(
      container: true,
      header: false,
      label: 'Counterfactual fairness card. '
          'Directional flip rate ${_pct(cf.directionalFlipRate)}. '
          'Severity ${severity.replaceAll("_", " ")}.',
      child: Container(
        padding: const EdgeInsets.all(20),
        decoration: BoxDecoration(
          color: NyayaColors.card,
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: NyayaColors.border),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                const Icon(
                  Icons.swap_horiz,
                  size: 20,
                  color: NyayaColors.navy,
                ),
                const SizedBox(width: 6),
                Text(
                  'Counterfactual fairness',
                  style: Theme.of(context).textTheme.titleLarge?.copyWith(
                        fontSize: 15,
                      ),
                ),
                const Spacer(),
                Container(
                  padding:
                      const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                  decoration: BoxDecoration(
                    color: bg,
                    borderRadius: BorderRadius.circular(10),
                  ),
                  child: Text(
                    severity.replaceAll('_', ' ').toUpperCase(),
                    style: TextStyle(
                      fontSize: 11,
                      fontWeight: FontWeight.w700,
                      color: color,
                      letterSpacing: 0.4,
                    ),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 12),
            // Headline + interpretation.
            if (cf.headline != null && cf.headline!.isNotEmpty)
              Text(
                cf.headline!,
                style: const TextStyle(
                  fontSize: 14,
                  fontWeight: FontWeight.w700,
                  color: NyayaColors.ink,
                  height: 1.4,
                ),
              ),
            if (cf.interpretation != null &&
                cf.interpretation!.isNotEmpty) ...[
              const SizedBox(height: 6),
              Text(
                cf.interpretation!,
                style: const TextStyle(
                  fontSize: 13,
                  color: NyayaColors.ink,
                  height: 1.55,
                ),
              ),
            ],
            const SizedBox(height: 14),
            // Directional flip rate (large number).
            Row(
              crossAxisAlignment: CrossAxisAlignment.end,
              children: [
                Text(
                  _pct(cf.directionalFlipRate),
                  style: TextStyle(
                    fontSize: 40,
                    height: 1.0,
                    fontWeight: FontWeight.w800,
                    color: color,
                    letterSpacing: -1.0,
                  ),
                ),
                const SizedBox(width: 12),
                Padding(
                  padding: const EdgeInsets.only(bottom: 6),
                  child: Text(
                    'of ${cf.sampleSizeUsed} sampled rows\nflip on ${cf.protectedAttribute} swap',
                    style: const TextStyle(
                      fontSize: 12,
                      color: NyayaColors.muted,
                      height: 1.35,
                    ),
                  ),
                ),
              ],
            ),
            // Pair table (only if there's more than one pair).
            if (pairs.length > 1) ...[
              const SizedBox(height: 16),
              Text(
                'Flip rate by group pair',
                style: Theme.of(context).textTheme.labelLarge?.copyWith(
                      fontSize: 12,
                      color: NyayaColors.muted,
                      letterSpacing: 0.3,
                    ),
              ),
              const SizedBox(height: 6),
              for (final e in pairs.take(8))
                Padding(
                  padding: const EdgeInsets.symmetric(vertical: 3),
                  child: Row(
                    children: [
                      Expanded(
                        child: Text(
                          e.key,
                          style: const TextStyle(
                            fontSize: 12,
                            fontFamily: 'monospace',
                            color: NyayaColors.ink,
                          ),
                        ),
                      ),
                      Text(
                        _pct(e.value),
                        style: TextStyle(
                          fontSize: 12,
                          fontWeight: FontWeight.w700,
                          color: e.value >= 0.15
                              ? NyayaColors.fail
                              : (e.value >= 0.05
                                  ? NyayaColors.warn
                                  : NyayaColors.muted),
                          fontFamily: 'monospace',
                        ),
                      ),
                    ],
                  ),
                ),
            ],
            if (cf.exampleTakeaways.isNotEmpty) ...[
              const SizedBox(height: 14),
              Text(
                'Example flips',
                style: Theme.of(context).textTheme.labelLarge?.copyWith(
                      fontSize: 12,
                      color: NyayaColors.muted,
                      letterSpacing: 0.3,
                    ),
              ),
              const SizedBox(height: 4),
              for (final t in cf.exampleTakeaways)
                Padding(
                  padding: const EdgeInsets.symmetric(vertical: 2),
                  child: Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Padding(
                        padding: EdgeInsets.only(top: 4, right: 6),
                        child: Icon(
                          Icons.arrow_right,
                          size: 14,
                          color: NyayaColors.muted,
                        ),
                      ),
                      Expanded(
                        child: Text(
                          t,
                          style: const TextStyle(
                            fontSize: 12,
                            color: NyayaColors.ink,
                            height: 1.45,
                          ),
                        ),
                      ),
                    ],
                  ),
                ),
            ],
          ],
        ),
      ),
    );
  }
}

/// Root-Cause card. Renders the headline, top driver list (with feature
/// name + contribution number + plain explanation), proxy warnings, and
/// suggested actions.
class RootCauseCard extends StatelessWidget {
  const RootCauseCard({super.key, required this.rc});

  final AuditRootCause rc;

  @override
  Widget build(BuildContext context) {
    return Semantics(
      container: true,
      label: 'Root-cause card. '
          'Top driver: ${rc.topDrivers.isNotEmpty ? rc.topDrivers.first.featureName : "none"}. '
          'Baseline DP gap ${rc.baselineDpGap.toStringAsFixed(3)}.',
      child: Container(
        padding: const EdgeInsets.all(20),
        decoration: BoxDecoration(
          color: NyayaColors.card,
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: NyayaColors.border),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                const Icon(
                  Icons.account_tree_outlined,
                  size: 20,
                  color: NyayaColors.navy,
                ),
                const SizedBox(width: 6),
                Text(
                  'Root-cause analysis',
                  style: Theme.of(context).textTheme.titleLarge?.copyWith(
                        fontSize: 15,
                      ),
                ),
                const Spacer(),
                Text(
                  'baseline gap ${rc.baselineDpGap.toStringAsFixed(3)}',
                  style: const TextStyle(
                    fontSize: 11,
                    color: NyayaColors.muted,
                    fontFamily: 'monospace',
                  ),
                ),
              ],
            ),
            if (rc.headline != null && rc.headline!.isNotEmpty) ...[
              const SizedBox(height: 8),
              Text(
                rc.headline!,
                style: const TextStyle(
                  fontSize: 14,
                  fontWeight: FontWeight.w700,
                  color: NyayaColors.ink,
                  height: 1.4,
                ),
              ),
            ],
            const SizedBox(height: 14),
            // Top drivers.
            if (rc.topDrivers.isNotEmpty) ...[
              Text(
                'Top drivers (permutation importance against DP gap)',
                style: Theme.of(context).textTheme.labelLarge?.copyWith(
                      fontSize: 12,
                      color: NyayaColors.muted,
                      letterSpacing: 0.3,
                    ),
              ),
              const SizedBox(height: 6),
              for (final d in rc.topDrivers.take(5))
                _DriverRow(driver: d, isProxy: rc.proxyFeatures.contains(d.featureName)),
            ],
            if (rc.proxyWarnings.isNotEmpty) ...[
              const SizedBox(height: 14),
              Text(
                'Proxy-feature warnings',
                style: Theme.of(context).textTheme.labelLarge?.copyWith(
                      fontSize: 12,
                      color: NyayaColors.warn,
                      letterSpacing: 0.3,
                    ),
              ),
              const SizedBox(height: 4),
              for (final w in rc.proxyWarnings)
                Padding(
                  padding: const EdgeInsets.symmetric(vertical: 2),
                  child: Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Padding(
                        padding: EdgeInsets.only(top: 4, right: 6),
                        child: Icon(
                          Icons.warning_amber_outlined,
                          size: 13,
                          color: NyayaColors.warn,
                        ),
                      ),
                      Expanded(
                        child: Text(
                          w,
                          style: const TextStyle(
                            fontSize: 12,
                            color: NyayaColors.ink,
                            height: 1.45,
                          ),
                        ),
                      ),
                    ],
                  ),
                ),
            ],
            if (rc.suggestedActions.isNotEmpty) ...[
              const SizedBox(height: 14),
              Text(
                'Suggested actions',
                style: Theme.of(context).textTheme.labelLarge?.copyWith(
                      fontSize: 12,
                      color: NyayaColors.ok,
                      letterSpacing: 0.3,
                    ),
              ),
              const SizedBox(height: 4),
              for (final a in rc.suggestedActions)
                Padding(
                  padding: const EdgeInsets.symmetric(vertical: 2),
                  child: Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Padding(
                        padding: EdgeInsets.only(top: 4, right: 6),
                        child: Icon(
                          Icons.check_circle_outline,
                          size: 13,
                          color: NyayaColors.ok,
                        ),
                      ),
                      Expanded(
                        child: Text(
                          a,
                          style: const TextStyle(
                            fontSize: 12,
                            color: NyayaColors.ink,
                            height: 1.45,
                          ),
                        ),
                      ),
                    ],
                  ),
                ),
            ],
          ],
        ),
      ),
    );
  }
}

class _DriverRow extends StatelessWidget {
  const _DriverRow({required this.driver, required this.isProxy});

  final FeatureContribution driver;
  final bool isProxy;

  @override
  Widget build(BuildContext context) {
    final value = driver.contributionToDisparity;
    final positive = value >= 0;
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 5),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Expanded(
                child: Row(
                  children: [
                    Text(
                      driver.featureName,
                      style: const TextStyle(
                        fontSize: 13,
                        fontWeight: FontWeight.w700,
                        fontFamily: 'monospace',
                        color: NyayaColors.ink,
                      ),
                    ),
                    if (isProxy) ...[
                      const SizedBox(width: 6),
                      Container(
                        padding: const EdgeInsets.symmetric(
                          horizontal: 6,
                          vertical: 2,
                        ),
                        decoration: BoxDecoration(
                          color: const Color(0xFFFEF3C7),
                          borderRadius: BorderRadius.circular(8),
                        ),
                        child: const Text(
                          'PROXY',
                          style: TextStyle(
                            fontSize: 9,
                            fontWeight: FontWeight.w700,
                            color: NyayaColors.warn,
                            letterSpacing: 0.4,
                          ),
                        ),
                      ),
                    ],
                  ],
                ),
              ),
              Text(
                '${positive ? "+" : ""}${value.toStringAsFixed(3)}',
                style: TextStyle(
                  fontSize: 12,
                  fontWeight: FontWeight.w700,
                  color: positive ? NyayaColors.fail : NyayaColors.muted,
                  fontFamily: 'monospace',
                ),
              ),
            ],
          ),
          if (driver.plainExplanation != null &&
              driver.plainExplanation!.isNotEmpty)
            Padding(
              padding: const EdgeInsets.only(top: 2),
              child: Text(
                driver.plainExplanation!,
                style: const TextStyle(
                  fontSize: 12,
                  color: NyayaColors.muted,
                  height: 1.45,
                ),
              ),
            ),
        ],
      ),
    );
  }
}

/// India-specific RBI metrics card. Shows SPLS shortfall, LRB rejection
/// disparity, and DLF composite when present in `result.india_metrics`.
class IndiaMetricsCard extends StatelessWidget {
  const IndiaMetricsCard({super.key, required this.metrics});

  final AuditIndiaMetrics metrics;

  @override
  Widget build(BuildContext context) {
    if (!metrics.isPopulated) return const SizedBox.shrink();
    return Semantics(
      container: true,
      label: 'India-specific RBI metrics card.',
      child: Container(
        padding: const EdgeInsets.all(20),
        decoration: BoxDecoration(
          color: NyayaColors.card,
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: NyayaColors.border),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                const Icon(
                  Icons.account_balance_outlined,
                  size: 20,
                  color: NyayaColors.navy,
                ),
                const SizedBox(width: 6),
                Text(
                  'India-specific (RBI) metrics',
                  style: Theme.of(context).textTheme.titleLarge?.copyWith(
                        fontSize: 15,
                      ),
                ),
              ],
            ),
            const SizedBox(height: 4),
            const Text(
              'Sourced from RBI Master Directions on Priority Sector Lending '
              'and the RBI Digital Lending Directions (2022).',
              style: TextStyle(color: NyayaColors.muted, fontSize: 12),
            ),
            if (metrics.hasSpls) _SplsBlock(m: metrics),
            if (metrics.hasLrb) _LrbBlock(m: metrics),
            if (metrics.hasDlf) _DlfBlock(m: metrics),
          ],
        ),
      ),
    );
  }
}

class _SplsBlock extends StatelessWidget {
  const _SplsBlock({required this.m});
  final AuditIndiaMetrics m;

  @override
  Widget build(BuildContext context) {
    final groups = m.splsActualByGroup.keys.toList()..sort();
    return Padding(
      padding: const EdgeInsets.only(top: 14),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            'Sub-Plan Lending Shortfall (SPLS)',
            style: Theme.of(context).textTheme.labelLarge?.copyWith(
                  fontSize: 12,
                  fontWeight: FontWeight.w700,
                  letterSpacing: 0.3,
                ),
          ),
          const SizedBox(height: 4),
          for (final g in groups)
            Padding(
              padding: const EdgeInsets.symmetric(vertical: 2),
              child: Row(
                children: [
                  Expanded(
                    child: Text(
                      g,
                      style: const TextStyle(
                        fontSize: 12,
                        fontFamily: 'monospace',
                        color: NyayaColors.ink,
                      ),
                    ),
                  ),
                  Text(
                    'actual ${m.splsActualByGroup[g]!.toStringAsFixed(2)}%   '
                    'target ${(m.splsTargetByGroup[g] ?? 0).toStringAsFixed(2)}%   '
                    'gap ${(m.splsShortfallByGroup[g] ?? 0).toStringAsFixed(2)}%',
                    style: TextStyle(
                      fontSize: 11,
                      fontFamily: 'monospace',
                      color: (m.splsShortfallByGroup[g] ?? 0) > 0
                          ? NyayaColors.fail
                          : NyayaColors.muted,
                    ),
                  ),
                ],
              ),
            ),
          if (m.splsWorstGroup != null)
            Padding(
              padding: const EdgeInsets.only(top: 4),
              child: Text(
                'Worst-shortfall group: ${m.splsWorstGroup}',
                style: const TextStyle(
                  fontSize: 11,
                  color: NyayaColors.fail,
                  fontStyle: FontStyle.italic,
                ),
              ),
            ),
        ],
      ),
    );
  }
}

class _LrbBlock extends StatelessWidget {
  const _LrbBlock({required this.m});
  final AuditIndiaMetrics m;

  @override
  Widget build(BuildContext context) {
    final groups = m.lrbRejectionByGroup.keys.toList()..sort();
    final breach = m.lrbBreach == true;
    return Padding(
      padding: const EdgeInsets.only(top: 14),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Text(
                'Loan Rejection Bias (LRB)',
                style: Theme.of(context).textTheme.labelLarge?.copyWith(
                      fontSize: 12,
                      fontWeight: FontWeight.w700,
                      letterSpacing: 0.3,
                    ),
              ),
              const SizedBox(width: 8),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                decoration: BoxDecoration(
                  color: breach
                      ? const Color(0xFFFEE2E2)
                      : const Color(0xFFDCFCE7),
                  borderRadius: BorderRadius.circular(8),
                ),
                child: Text(
                  breach ? 'RBI ADVISORY BREACH' : 'WITHIN ADVISORY',
                  style: TextStyle(
                    fontSize: 9,
                    fontWeight: FontWeight.w700,
                    color: breach ? NyayaColors.fail : NyayaColors.ok,
                    letterSpacing: 0.4,
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 4),
          for (final g in groups)
            Padding(
              padding: const EdgeInsets.symmetric(vertical: 2),
              child: Row(
                children: [
                  Expanded(
                    child: Text(
                      g,
                      style: const TextStyle(
                        fontSize: 12,
                        fontFamily: 'monospace',
                        color: NyayaColors.ink,
                      ),
                    ),
                  ),
                  Text(
                    '${(m.lrbRejectionByGroup[g]! * 100).toStringAsFixed(1)}% rejected',
                    style: const TextStyle(
                      fontSize: 12,
                      fontFamily: 'monospace',
                      color: NyayaColors.ink,
                    ),
                  ),
                ],
              ),
            ),
          if (m.lrbRatio != null)
            Padding(
              padding: const EdgeInsets.only(top: 4),
              child: Text(
                'Worst-best ratio: ${m.lrbRatio!.toStringAsFixed(3)}'
                '${m.lrbWorstGroup != null ? "  ·  worst: ${m.lrbWorstGroup}" : ""}',
                style: TextStyle(
                  fontSize: 11,
                  color: breach ? NyayaColors.fail : NyayaColors.muted,
                  fontStyle: FontStyle.italic,
                ),
              ),
            ),
        ],
      ),
    );
  }
}

class _DlfBlock extends StatelessWidget {
  const _DlfBlock({required this.m});
  final AuditIndiaMetrics m;

  @override
  Widget build(BuildContext context) {
    final score = m.dlfScore!;
    return Padding(
      padding: const EdgeInsets.only(top: 14),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            'Digital Lending Fairness (DLF) composite',
            style: Theme.of(context).textTheme.labelLarge?.copyWith(
                  fontSize: 12,
                  fontWeight: FontWeight.w700,
                  letterSpacing: 0.3,
                ),
          ),
          const SizedBox(height: 4),
          Row(
            crossAxisAlignment: CrossAxisAlignment.end,
            children: [
              Text(
                score.toStringAsFixed(3),
                style: TextStyle(
                  fontSize: 26,
                  height: 1.0,
                  fontWeight: FontWeight.w800,
                  color: score >= 0.8
                      ? NyayaColors.ok
                      : (score >= 0.6 ? NyayaColors.warn : NyayaColors.fail),
                ),
              ),
              const SizedBox(width: 8),
              const Padding(
                padding: EdgeInsets.only(bottom: 4),
                child: Text(
                  '/ 1.000',
                  style: TextStyle(
                    fontSize: 12,
                    color: NyayaColors.muted,
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 4),
          if (m.dlfDisparateImpact != null)
            Text(
              'DI ${m.dlfDisparateImpact!.toStringAsFixed(3)}   '
              'EO ${m.dlfEqualOpportunity!.toStringAsFixed(3)}   '
              'CAL ${m.dlfCalibration!.toStringAsFixed(3)}',
              style: const TextStyle(
                fontSize: 11,
                color: NyayaColors.muted,
                fontFamily: 'monospace',
              ),
            ),
        ],
      ),
    );
  }
}
