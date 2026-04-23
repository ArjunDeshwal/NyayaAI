import 'package:flutter/material.dart';
import 'package:nyayai_contracts/nyayai_contracts.dart';
import 'package:url_launcher/url_launcher.dart';

import '../../app/theme.dart';
import '../../shared/widgets/metric_badge.dart';

class AuditResultView extends StatelessWidget {
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
  Widget build(BuildContext context) {
    final di = response.overallDisparateImpact;
    final passes = response.passesFourFifths;

    final driftKind = switch (response.driftLevel) {
      'none' => BadgeKind.pass,
      'minor' => BadgeKind.warn,
      'major' => BadgeKind.fail,
      _ => BadgeKind.noData,
    };

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
                  const Icon(Icons.check_circle_outline,
                      color: NyayaColors.ok, size: 24),
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
