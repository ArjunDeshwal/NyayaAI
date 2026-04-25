import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:url_launcher/url_launcher.dart';

import '../../app/theme.dart';
import '../../shared/widgets/disclaimer_footer.dart';
import '../../shared/widgets/metric_badge.dart';
import 'history_entry.dart';
import 'history_repository.dart';

/// Local-only audit history screen (Feature F).
///
/// Persisted in browser localStorage under `nyayai.audit_history`. The
/// screen renders a scrollable list of past audits, each with a DP-ratio
/// chip, drift badge, and an "Open report" button.
class AuditHistoryScreen extends ConsumerWidget {
  const AuditHistoryScreen({super.key});

  Future<void> _openUrl(BuildContext context, String url) async {
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
            'Audit history',
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
            constraints: const BoxConstraints(maxWidth: 960),
            child: Column(
              children: [
                Expanded(
                  child: entries.isEmpty
                      ? const _EmptyState()
                      : ListView.separated(
                          padding: const EdgeInsets.fromLTRB(40, 28, 40, 32),
                          itemCount: entries.length,
                          separatorBuilder: (_, __) =>
                              const SizedBox(height: 12),
                          itemBuilder: (context, i) {
                            final e = entries[i];
                            return _HistoryCard(
                              entry: e,
                              onOpen: e.reportHtmlUrl.isEmpty
                                  ? null
                                  : () => _openUrl(context, e.reportHtmlUrl),
                            );
                          },
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

class _EmptyState extends StatelessWidget {
  const _EmptyState();

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.all(40),
      child: Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const Icon(Icons.history, size: 64, color: NyayaColors.muted),
            const SizedBox(height: 16),
            Text(
              'No audits yet',
              style: Theme.of(context).textTheme.titleLarge,
            ),
            const SizedBox(height: 6),
            const Text(
              'Run an audit and it will be saved to this browser. Up to '
              '20 audits are stored locally.',
              style: TextStyle(color: NyayaColors.muted, fontSize: 14),
              textAlign: TextAlign.center,
            ),
          ],
        ),
      ),
    );
  }
}

class _HistoryCard extends StatelessWidget {
  const _HistoryCard({required this.entry, required this.onOpen});

  final HistoryEntry entry;
  final VoidCallback? onOpen;

  String _fmtDate(String iso) {
    final dt = DateTime.tryParse(iso);
    if (dt == null) return iso;
    final local = dt.toLocal();
    String pad2(int v) => v.toString().padLeft(2, '0');
    return '${local.year}-${pad2(local.month)}-${pad2(local.day)} '
        '${pad2(local.hour)}:${pad2(local.minute)}';
  }

  @override
  Widget build(BuildContext context) {
    final di = entry.overallDpRatio;
    final passes = entry.passesFourFifths;
    final driftKind = switch (entry.driftLevel) {
      'none' => BadgeKind.pass,
      'minor' => BadgeKind.warn,
      'major' => BadgeKind.fail,
      _ => BadgeKind.noData,
    };

    final dpLabel = di == null
        ? 'DP: n/a'
        : 'DP: ${di.toStringAsFixed(3)} ${passes ? "(pass)" : "(fail)"}';

    return Semantics(
      container: true,
      label:
          'Audit ${entry.datasetName}, completed ${_fmtDate(entry.completedAtIso)}. '
          '${dpLabel.replaceAll(":", "")}.',
      child: Card(
        child: Padding(
          padding: const EdgeInsets.all(20),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          entry.datasetName,
                          style: const TextStyle(
                            fontSize: 16,
                            fontWeight: FontWeight.w700,
                            color: NyayaColors.ink,
                          ),
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                        ),
                        const SizedBox(height: 4),
                        Text(
                          '${entry.regime} · ${_fmtDate(entry.completedAtIso)}',
                          style: const TextStyle(
                            fontSize: 12,
                            color: NyayaColors.muted,
                          ),
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(width: 12),
                  if (onOpen != null)
                    Semantics(
                      button: true,
                      label: 'Open the HTML audit report for ${entry.datasetName}.',
                      child: OutlinedButton.icon(
                        onPressed: onOpen,
                        icon: const Icon(Icons.open_in_new, size: 16),
                        label: const Text('Open report'),
                      ),
                    ),
                ],
              ),
              const SizedBox(height: 12),
              Wrap(
                spacing: 8,
                runSpacing: 8,
                children: [
                  MetricBadge(
                    kind: di == null
                        ? BadgeKind.noData
                        : (passes ? BadgeKind.pass : BadgeKind.fail),
                    label: dpLabel,
                  ),
                  MetricBadge(
                    kind: driftKind,
                    label: 'Drift: ${entry.driftLevel ?? "n/a"}',
                  ),
                  if (entry.remediationImproved == true &&
                      entry.remediationAfterDp != null)
                    MetricBadge(
                      kind: entry.remediationAfterDp! >= 0.8
                          ? BadgeKind.pass
                          : BadgeKind.warn,
                      label:
                          'After remediation: ${entry.remediationAfterDp!.toStringAsFixed(3)}',
                    ),
                ],
              ),
              const SizedBox(height: 8),
              SelectableText(
                'ID: ${entry.auditId}',
                style: const TextStyle(
                  color: NyayaColors.muted,
                  fontSize: 11,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
