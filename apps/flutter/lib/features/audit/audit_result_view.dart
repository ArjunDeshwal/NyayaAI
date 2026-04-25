import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:nyayai_contracts/nyayai_contracts.dart';
import 'package:url_launcher/url_launcher.dart';

import '../../app/theme.dart';
import '../../shared/api/audit_report.dart';
import '../../shared/widgets/metric_badge.dart';
import 'audit_report_provider.dart';
import 'narrative_language.dart';
import 'widgets/remediation_chart.dart';

class AuditResultView extends ConsumerWidget {
  const AuditResultView({super.key, required this.response});

  final AuditResponse response;

  Future<void> _open(BuildContext context, String url) async {
    final uri = Uri.tryParse(url);
    if (uri == null) return;
    final ok = await launchUrl(uri, mode: LaunchMode.externalApplication);
    if (!ok && context.mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Could not open $url')),
      );
    }
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final di = response.overallDisparateImpact;
    final passes = response.passesFourFifths;

    final driftKind = switch (response.driftLevel) {
      'none' => BadgeKind.pass,
      'minor' => BadgeKind.warn,
      'major' => BadgeKind.fail,
      _ => BadgeKind.noData,
    };

    // Fetch the full report (narrative + remediation + per-attribute metrics).
    final asyncReport = response.auditId.isEmpty
        ? const AsyncValue<AuditReport?>.data(null)
        : ref.watch(auditReportProvider(response.auditId)).whenData<AuditReport?>((r) => r);

    return Semantics(
      container: true,
      label: 'Audit result for ${response.auditId}.',
      child: Card(
        child: Padding(
          padding: const EdgeInsets.all(28),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  const Icon(
                    Icons.check_circle_outline,
                    color: NyayaColors.ok,
                    size: 24,
                  ),
                  const SizedBox(width: 10),
                  Expanded(
                    child: Semantics(
                      header: true,
                      child: Text(
                        'Audit complete',
                        style: Theme.of(context).textTheme.headlineMedium,
                      ),
                    ),
                  ),
                  // EN / HI toggle (top-right of the result card).
                  asyncReport.maybeWhen(
                    data: (report) => _LanguageToggle(
                      hasHindi: report?.narrative.hasHindi ?? false,
                    ),
                    orElse: () => const _LanguageToggle(hasHindi: false),
                  ),
                ],
              ),
              const SizedBox(height: 4),
              SelectableText(
                'ID: ${response.auditId}',
                style: const TextStyle(color: NyayaColors.muted, fontSize: 13),
              ),
              const SizedBox(height: 24),

              // Primary metric: disparate impact.
              Semantics(
                container: true,
                label: di == null
                    ? 'Overall disparate impact: not available.'
                    : 'Overall disparate impact: ${di.toStringAsFixed(3)}. '
                        'The four-fifths rule ${passes ? "passes" : "fails"}.',
                child: Row(
                  crossAxisAlignment: CrossAxisAlignment.end,
                  children: [
                    ExcludeSemantics(
                      child: Text(
                        di == null ? '—' : di.toStringAsFixed(3),
                        style: TextStyle(
                          fontSize: 56,
                          height: 1.0,
                          fontWeight: FontWeight.w800,
                          color: di == null
                              ? NyayaColors.muted
                              : (passes ? NyayaColors.ok : NyayaColors.fail),
                          letterSpacing: -1.5,
                        ),
                      ),
                    ),
                    const SizedBox(width: 16),
                    const Padding(
                      padding: EdgeInsets.only(bottom: 10),
                      child: Text(
                        'Overall\ndisparate impact',
                        style: TextStyle(
                          fontSize: 13,
                          color: NyayaColors.muted,
                          height: 1.3,
                        ),
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 20),

              // Badges row.
              Wrap(
                spacing: 12,
                runSpacing: 12,
                children: [
                  MetricBadge(
                    kind: di == null
                        ? BadgeKind.noData
                        : (passes ? BadgeKind.pass : BadgeKind.fail),
                    label: di == null
                        ? '4/5ths rule: n/a'
                        : (passes ? '4/5ths rule: pass' : '4/5ths rule: fail'),
                    semanticsLabel: di == null
                        ? 'Four-fifths rule: not applicable, no disparate impact computed.'
                        : 'Four-fifths rule: ${passes ? "pass" : "fail"}.',
                  ),
                  MetricBadge(
                    kind: driftKind,
                    label: 'Drift: ${response.driftLevel ?? "n/a"}',
                    semanticsLabel:
                        'Distribution drift level: ${response.driftLevel ?? "not available"}.',
                  ),
                  MetricBadge(
                    kind: BadgeKind.info,
                    label: 'Status: ${response.status}',
                  ),
                ],
              ),

              // Narrative summary (English / Hindi toggle).
              asyncReport.when(
                loading: () => const Padding(
                  padding: EdgeInsets.symmetric(vertical: 20),
                  child: _LoadingNarrative(),
                ),
                error: (e, _) => const SizedBox.shrink(),
                data: (report) {
                  if (report == null) return const SizedBox.shrink();
                  return _NarrativePanel(report: report);
                },
              ),

              // Before/after remediation chart.
              asyncReport.when(
                loading: () => const SizedBox.shrink(),
                error: (e, _) => const SizedBox.shrink(),
                data: (report) {
                  if (report == null) return const SizedBox.shrink();
                  return Padding(
                    padding: const EdgeInsets.only(top: 24),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Semantics(
                          header: true,
                          child: Text(
                            'Before vs. after remediation',
                            style: Theme.of(context).textTheme.titleLarge,
                          ),
                        ),
                        const SizedBox(height: 4),
                        const Text(
                          'Per-attribute demographic-parity ratios. The 0.8 '
                          'line marks the four-fifths rule.',
                          style: TextStyle(
                            color: NyayaColors.muted,
                            fontSize: 13,
                          ),
                        ),
                        const SizedBox(height: 16),
                        RemediationChart(report: report),
                      ],
                    ),
                  );
                },
              ),

              const SizedBox(height: 24),
              const Divider(),
              const SizedBox(height: 16),

              // Action buttons.
              Wrap(
                spacing: 12,
                runSpacing: 12,
                children: [
                  Semantics(
                    button: true,
                    label: 'Open full HTML audit report in a new browser tab.',
                    child: FilledButton.icon(
                      onPressed: () => _open(context, response.reportHtmlUrl),
                      icon: const Icon(Icons.open_in_new),
                      label: const Text('Open HTML report'),
                    ),
                  ),
                  if (response.reportPdfUrl != null)
                    Semantics(
                      button: true,
                      label: 'Download the audit report as a PDF.',
                      child: OutlinedButton.icon(
                        onPressed: () => _open(context, response.reportPdfUrl!),
                        icon: const Icon(Icons.picture_as_pdf_outlined),
                        label: const Text('Download PDF'),
                      ),
                    ),
                  Semantics(
                    button: true,
                    label: 'Open the raw JSON audit report.',
                    child: TextButton.icon(
                      onPressed: () => _open(context, response.reportJsonUrl),
                      icon: const Icon(Icons.data_object),
                      label: const Text('JSON'),
                    ),
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _LoadingNarrative extends StatelessWidget {
  const _LoadingNarrative();

  @override
  Widget build(BuildContext context) {
    return const Row(
      children: [
        SizedBox(
          width: 16,
          height: 16,
          child: CircularProgressIndicator(strokeWidth: 2),
        ),
        SizedBox(width: 10),
        Text(
          'Loading narrative summary…',
          style: TextStyle(color: NyayaColors.muted, fontSize: 13),
        ),
      ],
    );
  }
}

class _NarrativePanel extends ConsumerWidget {
  const _NarrativePanel({required this.report});

  final AuditReport report;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final lang = ref.watch(narrativeLanguageProvider);
    final hasHindi = report.narrative.hasHindi;
    final effectiveLang =
        (lang == NarrativeLanguage.hi && !hasHindi) ? NarrativeLanguage.en : lang;

    final body = effectiveLang == NarrativeLanguage.hi
        ? report.narrative.summaryHi
        : report.narrative.summary;

    if (body == null || body.trim().isEmpty) {
      return const SizedBox.shrink();
    }

    final isHindi = effectiveLang == NarrativeLanguage.hi;
    return Padding(
      padding: const EdgeInsets.only(top: 24),
      child: Container(
        padding: const EdgeInsets.all(18),
        decoration: BoxDecoration(
          color: NyayaColors.bg,
          borderRadius: BorderRadius.circular(8),
          border: Border.all(color: NyayaColors.border),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                const Icon(Icons.format_quote, size: 18, color: NyayaColors.navy),
                const SizedBox(width: 6),
                Text(
                  'Narrative summary',
                  style: Theme.of(context).textTheme.titleLarge?.copyWith(
                        fontSize: 15,
                      ),
                ),
              ],
            ),
            const SizedBox(height: 8),
            Semantics(
              label: isHindi
                  ? 'Narrative summary in Hindi.'
                  : 'Narrative summary in English.',
              child: SelectableText(
                body,
                textDirection: TextDirection.ltr,
                style: TextStyle(
                  fontSize: 14,
                  height: 1.55,
                  color: NyayaColors.ink,
                  // Hindi script needs a slightly larger line-height.
                  letterSpacing: isHindi ? 0.0 : 0.1,
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _LanguageToggle extends ConsumerWidget {
  const _LanguageToggle({required this.hasHindi});

  /// `true` when the current report has a `summary_hi` field. When `false`,
  /// the HI button is disabled with a tooltip.
  final bool hasHindi;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final lang = ref.watch(narrativeLanguageProvider);
    return Semantics(
      container: true,
      label: 'Narrative language toggle. Currently '
          '${lang == NarrativeLanguage.hi && hasHindi ? "Hindi" : "English"}.',
      child: SegmentedButton<NarrativeLanguage>(
        segments: <ButtonSegment<NarrativeLanguage>>[
          const ButtonSegment(
            value: NarrativeLanguage.en,
            label: Text('EN'),
            icon: Icon(Icons.translate, size: 16),
          ),
          ButtonSegment(
            value: NarrativeLanguage.hi,
            label: Tooltip(
              message: hasHindi
                  ? 'Hindi'
                  : 'Translation not available for this audit',
              child: const Text('हिन्दी'),
            ),
            enabled: hasHindi,
          ),
        ],
        selected: <NarrativeLanguage>{
          (lang == NarrativeLanguage.hi && !hasHindi)
              ? NarrativeLanguage.en
              : lang,
        },
        onSelectionChanged: (selection) {
          if (selection.isEmpty) return;
          final next = selection.first;
          if (next == NarrativeLanguage.hi && !hasHindi) return;
          ref.read(narrativeLanguageProvider.notifier).set(next);
        },
        showSelectedIcon: false,
        style: ButtonStyle(
          visualDensity: VisualDensity.compact,
          textStyle: WidgetStateProperty.all(
            const TextStyle(fontSize: 13, fontWeight: FontWeight.w600),
          ),
        ),
      ),
    );
  }
}
