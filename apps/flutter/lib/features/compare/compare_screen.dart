import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../app/theme.dart';
import '../../shared/api/audit_report.dart';
import '../../shared/widgets/disclaimer_footer.dart';
import '../../shared/widgets/metric_badge.dart';
import '../audit/audit_report_provider.dart';
import '../history/history_entry.dart';
import '../history/history_repository.dart';

/// `/compare` route — pairwise audit diff.
///
/// User flow:
///   1. The screen lists every audit in browser history with two radio
///      columns — A and B. The two selections must differ.
///   2. Once both are picked, the bottom panel fetches each report by
///      `/reports/{id}/json` and renders a side-by-side diff: overall DI,
///      drift, recommendation counts, narrative excerpt.
///
/// This is the first NyayaAI feature that compares more than one model
/// over time — exactly the longitudinal-evidence signal a regulator
/// (DPDP Board, RBI ombudsman) needs.
class CompareScreen extends ConsumerStatefulWidget {
  const CompareScreen({super.key});

  @override
  ConsumerState<CompareScreen> createState() => _CompareScreenState();
}

class _CompareScreenState extends ConsumerState<CompareScreen> {
  String? _idA;
  String? _idB;

  @override
  Widget build(BuildContext context) {
    final repo = ref.watch(historyRepositoryProvider);
    final entries = repo.list();

    return Scaffold(
      appBar: AppBar(
        backgroundColor: NyayaColors.card,
        surfaceTintColor: Colors.transparent,
        elevation: 0,
        title: Semantics(
          header: true,
          child: const Text(
            'Compare audits',
            style: TextStyle(
              color: NyayaColors.navy,
              fontWeight: FontWeight.w700,
            ),
          ),
        ),
        leading: Semantics(
          button: true,
          label: 'Back to the audit form.',
          child: IconButton(
            onPressed: () {
              if (context.canPop()) {
                context.pop();
              } else {
                context.go('/');
              }
            },
            icon: const Icon(Icons.arrow_back, color: NyayaColors.navy),
            tooltip: 'Back',
          ),
        ),
        bottom: const PreferredSize(
          preferredSize: Size.fromHeight(1),
          child: Divider(height: 1, color: NyayaColors.border),
        ),
      ),
      body: SafeArea(
        child: Center(
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 1080),
            child: Column(
              children: [
                Expanded(
                  child: entries.length < 2
                      ? const _NotEnoughHistory()
                      : SingleChildScrollView(
                          padding: const EdgeInsets.fromLTRB(40, 24, 40, 32),
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              const _Intro(),
                              const SizedBox(height: 16),
                              _Picker(
                                entries: entries,
                                idA: _idA,
                                idB: _idB,
                                onChanged: (a, b) {
                                  setState(() {
                                    _idA = a;
                                    _idB = b;
                                  });
                                },
                              ),
                              const SizedBox(height: 16),
                              if (_idA != null && _idB != null && _idA != _idB)
                                _DiffPanel(idA: _idA!, idB: _idB!),
                            ],
                          ),
                        ),
                ),
                const DisclaimerFooter(),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

class _Intro extends StatelessWidget {
  const _Intro();

  @override
  Widget build(BuildContext context) {
    return Container(
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
                Icons.compare_arrows,
                size: 20,
                color: NyayaColors.navy,
              ),
              const SizedBox(width: 8),
              Text(
                'Pairwise audit comparison',
                style: Theme.of(context).textTheme.titleLarge,
              ),
            ],
          ),
          const SizedBox(height: 4),
          const Text(
            'Pick two audits from your browser history. NyayaAI fetches both '
            'reports and surfaces the deltas — disparate impact, drift level, '
            'and recommendation severity — so you can prove longitudinal '
            'progress to a regulator or NGO reviewer.',
            style: TextStyle(color: NyayaColors.muted, fontSize: 13),
          ),
        ],
      ),
    );
  }
}

class _NotEnoughHistory extends StatelessWidget {
  const _NotEnoughHistory();

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.all(40),
      child: Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const Icon(
              Icons.compare_arrows,
              size: 64,
              color: NyayaColors.muted,
            ),
            const SizedBox(height: 16),
            Text(
              'Run at least two audits to compare',
              style: Theme.of(context).textTheme.titleLarge,
            ),
            const SizedBox(height: 6),
            const Text(
              'NyayaAI compares any two audits stored in this browser. '
              'Run a sample audit, change a column or regime, run another, '
              'then come back here.',
              style: TextStyle(color: NyayaColors.muted, fontSize: 14),
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: 16),
            FilledButton.icon(
              onPressed: () => context.go('/'),
              icon: const Icon(Icons.play_arrow),
              label: const Text('Go run an audit'),
            ),
          ],
        ),
      ),
    );
  }
}

class _Picker extends StatelessWidget {
  const _Picker({
    required this.entries,
    required this.idA,
    required this.idB,
    required this.onChanged,
  });

  final List<HistoryEntry> entries;
  final String? idA;
  final String? idB;
  final void Function(String? idA, String? idB) onChanged;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
      decoration: BoxDecoration(
        color: NyayaColors.card,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: NyayaColors.border),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Padding(
            padding: EdgeInsets.symmetric(vertical: 8),
            child: Row(
              children: [
                Expanded(
                  flex: 6,
                  child: Text(
                    'Audit',
                    style: TextStyle(
                      fontSize: 12,
                      fontWeight: FontWeight.w800,
                      color: NyayaColors.muted,
                      letterSpacing: 0.4,
                    ),
                  ),
                ),
                Expanded(
                  flex: 1,
                  child: Center(
                    child: Text(
                      'A',
                      style: TextStyle(
                        fontSize: 12,
                        fontWeight: FontWeight.w800,
                        color: NyayaColors.muted,
                        letterSpacing: 0.4,
                      ),
                    ),
                  ),
                ),
                Expanded(
                  flex: 1,
                  child: Center(
                    child: Text(
                      'B',
                      style: TextStyle(
                        fontSize: 12,
                        fontWeight: FontWeight.w800,
                        color: NyayaColors.muted,
                        letterSpacing: 0.4,
                      ),
                    ),
                  ),
                ),
              ],
            ),
          ),
          const Divider(height: 1),
          for (final e in entries)
            Padding(
              padding: const EdgeInsets.symmetric(vertical: 6),
              child: Row(
                children: [
                  Expanded(
                    flex: 6,
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          e.datasetName,
                          style: const TextStyle(
                            fontSize: 14,
                            fontWeight: FontWeight.w700,
                            color: NyayaColors.ink,
                          ),
                        ),
                        const SizedBox(height: 2),
                        Text(
                          '${e.regime} · ${e.auditId}',
                          style: const TextStyle(
                            fontSize: 11,
                            color: NyayaColors.muted,
                          ),
                        ),
                      ],
                    ),
                  ),
                  Expanded(
                    flex: 1,
                    child: Center(
                      child: RadioGroup<String>(
                        groupValue: idA,
                        onChanged: (v) => onChanged(v, idB),
                        child: Radio<String>(value: e.auditId),
                      ),
                    ),
                  ),
                  Expanded(
                    flex: 1,
                    child: Center(
                      child: RadioGroup<String>(
                        groupValue: idB,
                        onChanged: (v) => onChanged(idA, v),
                        child: Radio<String>(value: e.auditId),
                      ),
                    ),
                  ),
                ],
              ),
            ),
          if (idA != null && idA == idB)
            const Padding(
              padding: EdgeInsets.symmetric(vertical: 8),
              child: Text(
                'A and B must be different audits.',
                style: TextStyle(color: NyayaColors.fail, fontSize: 12),
              ),
            ),
        ],
      ),
    );
  }
}

class _DiffPanel extends ConsumerWidget {
  const _DiffPanel({required this.idA, required this.idB});

  final String idA;
  final String idB;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final a = ref.watch(auditReportProvider(idA));
    final b = ref.watch(auditReportProvider(idB));

    if (a.isLoading || b.isLoading) {
      return const _LoadingPanel();
    }
    if (a.hasError || b.hasError) {
      return _ErrorPanel(
        message: 'Could not fetch one or both reports. '
            '${a.hasError ? "A: ${a.error}" : ""} '
            '${b.hasError ? "B: ${b.error}" : ""}',
      );
    }
    final reportA = a.value;
    final reportB = b.value;
    if (reportA == null || reportB == null) {
      return const _LoadingPanel();
    }
    return _DiffBody(reportA: reportA, reportB: reportB);
  }
}

class _LoadingPanel extends StatelessWidget {
  const _LoadingPanel();

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(24),
      decoration: BoxDecoration(
        color: NyayaColors.card,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: NyayaColors.border),
      ),
      child: const Row(
        children: [
          SizedBox(
            width: 18,
            height: 18,
            child: CircularProgressIndicator(strokeWidth: 2),
          ),
          SizedBox(width: 10),
          Text(
            'Fetching both reports…',
            style: TextStyle(color: NyayaColors.muted, fontSize: 13),
          ),
        ],
      ),
    );
  }
}

class _ErrorPanel extends StatelessWidget {
  const _ErrorPanel({required this.message});
  final String message;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: const Color(0xFFFEE2E2),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: NyayaColors.fail),
      ),
      child: Row(
        children: [
          const Icon(Icons.error_outline, color: NyayaColors.fail),
          const SizedBox(width: 10),
          Expanded(
            child: Text(
              message,
              style: const TextStyle(color: NyayaColors.fail, fontSize: 13),
            ),
          ),
        ],
      ),
    );
  }
}

class _DiffBody extends StatelessWidget {
  const _DiffBody({required this.reportA, required this.reportB});

  final AuditReport reportA;
  final AuditReport reportB;

  double? _overallDi(AuditReport r) {
    // Find the per-attribute mean DP ratio as a proxy for overall DI.
    final ratios = r.perAttributeDpRatio().values.toList();
    if (ratios.isEmpty) return null;
    final sum = ratios.fold<double>(0, (a, b) => a + b);
    return sum / ratios.length;
  }

  @override
  Widget build(BuildContext context) {
    final diA = _overallDi(reportA);
    final diB = _overallDi(reportB);
    final delta = (diA != null && diB != null) ? (diB - diA) : null;

    final recsA = reportA.narrative.recommendations.length;
    final recsB = reportB.narrative.recommendations.length;
    final actionA = reportA.narrative.recommendations
        .where((r) => r.severity == 'action_required')
        .length;
    final actionB = reportB.narrative.recommendations
        .where((r) => r.severity == 'action_required')
        .length;

    final isWide = MediaQuery.sizeOf(context).width >= 720;

    return Container(
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
              const Icon(Icons.equalizer, size: 20, color: NyayaColors.navy),
              const SizedBox(width: 8),
              Text(
                'Comparison',
                style: Theme.of(context).textTheme.titleLarge,
              ),
              const Spacer(),
              if (delta != null) _DeltaBadge(delta: delta),
            ],
          ),
          const SizedBox(height: 8),
          isWide
              ? Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Expanded(
                      child: _SideCard(
                        label: 'A',
                        report: reportA,
                        di: diA,
                        recCount: recsA,
                        actionCount: actionA,
                      ),
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: _SideCard(
                        label: 'B',
                        report: reportB,
                        di: diB,
                        recCount: recsB,
                        actionCount: actionB,
                      ),
                    ),
                  ],
                )
              : Column(
                  children: [
                    _SideCard(
                      label: 'A',
                      report: reportA,
                      di: diA,
                      recCount: recsA,
                      actionCount: actionA,
                    ),
                    const SizedBox(height: 12),
                    _SideCard(
                      label: 'B',
                      report: reportB,
                      di: diB,
                      recCount: recsB,
                      actionCount: actionB,
                    ),
                  ],
                ),
          const SizedBox(height: 16),
          _PerAttributeDiff(
            attrsA: reportA.perAttributeDpRatio(),
            attrsB: reportB.perAttributeDpRatio(),
          ),
        ],
      ),
    );
  }
}

class _SideCard extends StatelessWidget {
  const _SideCard({
    required this.label,
    required this.report,
    required this.di,
    required this.recCount,
    required this.actionCount,
  });

  final String label;
  final AuditReport report;
  final double? di;
  final int recCount;
  final int actionCount;

  @override
  Widget build(BuildContext context) {
    final passes = di != null && di! >= 0.8;
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: NyayaColors.bg,
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: NyayaColors.border),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Container(
                width: 24,
                height: 24,
                decoration: const BoxDecoration(
                  shape: BoxShape.circle,
                  color: NyayaColors.navy,
                ),
                child: Center(
                  child: Text(
                    label,
                    style: const TextStyle(
                      color: Colors.white,
                      fontSize: 13,
                      fontWeight: FontWeight.w800,
                    ),
                  ),
                ),
              ),
              const SizedBox(width: 8),
              Expanded(
                child: Text(
                  report.datasetName.isEmpty
                      ? report.auditId
                      : report.datasetName,
                  style: const TextStyle(
                    fontSize: 14,
                    fontWeight: FontWeight.w700,
                    color: NyayaColors.ink,
                  ),
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                ),
              ),
            ],
          ),
          const SizedBox(height: 4),
          Text(
            '${report.regime} · ${report.auditId}',
            style: const TextStyle(
              fontSize: 11,
              color: NyayaColors.muted,
            ),
          ),
          const SizedBox(height: 12),
          Row(
            crossAxisAlignment: CrossAxisAlignment.end,
            children: [
              Text(
                di == null ? '—' : di!.toStringAsFixed(3),
                style: TextStyle(
                  fontSize: 32,
                  height: 1.0,
                  fontWeight: FontWeight.w800,
                  color: di == null
                      ? NyayaColors.muted
                      : (passes ? NyayaColors.ok : NyayaColors.fail),
                  letterSpacing: -0.8,
                ),
              ),
              const SizedBox(width: 8),
              const Padding(
                padding: EdgeInsets.only(bottom: 6),
                child: Text(
                  'mean DP ratio',
                  style: TextStyle(
                    fontSize: 11,
                    color: NyayaColors.muted,
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 8),
          Wrap(
            spacing: 6,
            runSpacing: 6,
            children: [
              MetricBadge(
                kind: di == null
                    ? BadgeKind.noData
                    : (passes ? BadgeKind.pass : BadgeKind.fail),
                label: passes ? '4/5ths pass' : '4/5ths fail',
              ),
              MetricBadge(
                kind: actionCount > 0 ? BadgeKind.fail : BadgeKind.pass,
                label: '$actionCount action',
              ),
              MetricBadge(
                kind: BadgeKind.info,
                label: '$recCount total recs',
              ),
            ],
          ),
        ],
      ),
    );
  }
}

class _DeltaBadge extends StatelessWidget {
  const _DeltaBadge({required this.delta});
  final double delta;

  @override
  Widget build(BuildContext context) {
    final positive = delta >= 0;
    final improved = delta > 0;
    final color = improved
        ? NyayaColors.ok
        : (delta < 0 ? NyayaColors.fail : NyayaColors.muted);
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.10),
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: color.withValues(alpha: 0.40)),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(
            improved ? Icons.trending_up : Icons.trending_down,
            color: color,
            size: 16,
          ),
          const SizedBox(width: 4),
          Text(
            '${positive ? "+" : ""}${delta.toStringAsFixed(3)}',
            style: TextStyle(
              fontSize: 12,
              fontWeight: FontWeight.w800,
              color: color,
              fontFeatures: const [FontFeature.tabularFigures()],
            ),
          ),
          const SizedBox(width: 4),
          Text(
            'B − A',
            style: TextStyle(
              fontSize: 11,
              fontWeight: FontWeight.w600,
              color: color,
              letterSpacing: 0.3,
            ),
          ),
        ],
      ),
    );
  }
}

class _PerAttributeDiff extends StatelessWidget {
  const _PerAttributeDiff({required this.attrsA, required this.attrsB});

  final Map<String, double> attrsA;
  final Map<String, double> attrsB;

  @override
  Widget build(BuildContext context) {
    final allAttrs = {...attrsA.keys, ...attrsB.keys}.toList()..sort();
    if (allAttrs.isEmpty) return const SizedBox.shrink();
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Text(
          'Per-attribute demographic-parity ratio',
          style: TextStyle(
            fontSize: 12,
            fontWeight: FontWeight.w800,
            color: NyayaColors.muted,
            letterSpacing: 0.4,
          ),
        ),
        const SizedBox(height: 8),
        for (final attr in allAttrs)
          _AttrRow(name: attr, a: attrsA[attr], b: attrsB[attr]),
      ],
    );
  }
}

class _AttrRow extends StatelessWidget {
  const _AttrRow({required this.name, required this.a, required this.b});

  final String name;
  final double? a;
  final double? b;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Row(
        children: [
          SizedBox(
            width: 140,
            child: Text(
              name,
              style: const TextStyle(
                fontSize: 12,
                fontWeight: FontWeight.w700,
                color: NyayaColors.ink,
                fontFamily: 'monospace',
              ),
            ),
          ),
          Expanded(child: _Bar(value: a)),
          const SizedBox(width: 6),
          Expanded(child: _Bar(value: b)),
          const SizedBox(width: 8),
          SizedBox(
            width: 70,
            child: Text(
              (a != null && b != null)
                  ? '${b! - a! >= 0 ? "+" : ""}${(b! - a!).toStringAsFixed(3)}'
                  : '—',
              textAlign: TextAlign.right,
              style: TextStyle(
                fontSize: 12,
                fontWeight: FontWeight.w800,
                color: (a != null && b != null && b! > a!)
                    ? NyayaColors.ok
                    : (a != null && b != null && b! < a!)
                        ? NyayaColors.fail
                        : NyayaColors.muted,
                fontFeatures: const [FontFeature.tabularFigures()],
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _Bar extends StatelessWidget {
  const _Bar({required this.value});
  final double? value;

  @override
  Widget build(BuildContext context) {
    final v = value;
    if (v == null) {
      return Container(
        height: 18,
        decoration: BoxDecoration(
          color: const Color(0xFFF3F4F6),
          borderRadius: BorderRadius.circular(4),
        ),
        child: const Center(
          child: Text(
            'n/a',
            style: TextStyle(fontSize: 10, color: NyayaColors.muted),
          ),
        ),
      );
    }
    final clamped = v.clamp(0.0, 1.0);
    final color = clamped >= 0.8 ? NyayaColors.ok : NyayaColors.fail;
    return Container(
      height: 18,
      decoration: BoxDecoration(
        color: const Color(0xFFF3F4F6),
        borderRadius: BorderRadius.circular(4),
      ),
      child: Stack(
        children: [
          FractionallySizedBox(
            widthFactor: clamped,
            child: Container(
              decoration: BoxDecoration(
                color: color.withValues(alpha: 0.30),
                borderRadius: BorderRadius.circular(4),
              ),
            ),
          ),
          Center(
            child: Text(
              v.toStringAsFixed(3),
              style: TextStyle(
                fontSize: 10,
                fontWeight: FontWeight.w800,
                color: color,
                fontFeatures: const [FontFeature.tabularFigures()],
              ),
            ),
          ),
        ],
      ),
    );
  }
}
