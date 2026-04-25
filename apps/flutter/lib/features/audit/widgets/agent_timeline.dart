import 'package:flutter/material.dart';

import '../../../app/theme.dart';
import '../agent_timeline_state.dart';

/// Live agent-pipeline timeline.
///
/// Renders five fixed rows in canonical order: Planner -> Fairness Engine ->
/// Narrator -> Watcher -> Remediation. Each row updates as NDJSON events
/// arrive on the audit stream. Phase changes are announced to assistive
/// technology via a top-level `Semantics(liveRegion: true)` wrapper.
class AgentTimeline extends StatelessWidget {
  const AgentTimeline({
    super.key,
    required this.timeline,
    this.errorMessage,
  });

  final AgentTimelineState timeline;

  /// Optional pipeline-level error reason. When set, the timeline stays
  /// visible and the message renders at the bottom.
  final String? errorMessage;

  String _liveRegionAnnouncement() {
    final running = timeline.phases.firstWhere(
      (p) => p.status == AgentRunStatus.running,
      orElse: () => const AgentPhaseState(phase: AgentPhase.planner),
    );
    if (running.status == AgentRunStatus.running) {
      return 'Running ${running.phase.displayName}.';
    }
    final lastDone = timeline.phases
        .where(
          (p) =>
              p.status == AgentRunStatus.done ||
              p.status == AgentRunStatus.skipped ||
              p.status == AgentRunStatus.error,
        )
        .lastOrNull;
    if (lastDone == null) return 'Audit pipeline starting.';
    return '${lastDone.phase.displayName} ${lastDone.status.name}.';
  }

  @override
  Widget build(BuildContext context) {
    return Semantics(
      container: true,
      liveRegion: true,
      label: _liveRegionAnnouncement(),
      child: Container(
        decoration: BoxDecoration(
          color: NyayaColors.card,
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: NyayaColors.border),
        ),
        padding: const EdgeInsets.fromLTRB(20, 18, 20, 18),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                const Icon(
                  Icons.bolt_outlined,
                  size: 20,
                  color: NyayaColors.navy,
                ),
                const SizedBox(width: 6),
                Text(
                  'Agent timeline',
                  style: Theme.of(context).textTheme.titleLarge,
                ),
              ],
            ),
            const SizedBox(height: 4),
            const Text(
              'Five agents collaborate on every audit. Watch their progress live.',
              style: TextStyle(color: NyayaColors.muted, fontSize: 13),
            ),
            const SizedBox(height: 12),
            for (var i = 0; i < timeline.phases.length; i++) ...[
              _AgentRow(state: timeline.phases[i]),
              if (i < timeline.phases.length - 1)
                const Divider(height: 16, thickness: 1),
            ],
            if (errorMessage != null) ...[
              const SizedBox(height: 12),
              Container(
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: const Color(0xFFFEE2E2),
                  borderRadius: BorderRadius.circular(8),
                  border: Border.all(color: NyayaColors.fail),
                ),
                child: Row(
                  children: [
                    const Icon(
                      Icons.error_outline,
                      color: NyayaColors.fail,
                      size: 18,
                    ),
                    const SizedBox(width: 8),
                    Expanded(
                      child: Text(
                        errorMessage!,
                        style: const TextStyle(
                          color: NyayaColors.fail,
                          fontSize: 13,
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

class _AgentRow extends StatelessWidget {
  const _AgentRow({required this.state});

  final AgentPhaseState state;

  @override
  Widget build(BuildContext context) {
    final crossed = state.status == AgentRunStatus.skipped;
    final faded = state.status == AgentRunStatus.pending;

    final titleStyle = TextStyle(
      fontSize: 14,
      fontWeight: FontWeight.w600,
      color: faded ? NyayaColors.muted : NyayaColors.ink,
      decoration: crossed ? TextDecoration.lineThrough : null,
      decorationColor: NyayaColors.muted,
    );
    final subtitleStyle = TextStyle(
      fontSize: 12,
      color: NyayaColors.muted,
      decoration: crossed ? TextDecoration.lineThrough : null,
      decorationColor: NyayaColors.muted,
    );

    return Semantics(
      container: true,
      label: '${state.phase.displayName}. '
          '${state.phase.subtitle}. '
          'Status: ${_statusLabel(state.status)}'
          '${state.elapsedMs != null ? ", ${_formatElapsed(state.elapsedMs!)}." : "."}',
      child: Padding(
        padding: const EdgeInsets.symmetric(vertical: 4),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.center,
          children: [
            ExcludeSemantics(child: _StatusGlyph(status: state.status)),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(state.phase.displayName, style: titleStyle),
                  const SizedBox(height: 2),
                  Text(state.phase.subtitle, style: subtitleStyle),
                  if (state.message != null) ...[
                    const SizedBox(height: 4),
                    Text(
                      state.message!,
                      style: const TextStyle(
                        fontSize: 12,
                        color: NyayaColors.fail,
                      ),
                    ),
                  ],
                ],
              ),
            ),
            if (state.elapsedMs != null && state.status != AgentRunStatus.error)
              ExcludeSemantics(
                child: Container(
                  padding:
                      const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                  decoration: BoxDecoration(
                    color: const Color(0xFFE0E7FF),
                    borderRadius: BorderRadius.circular(10),
                    border:
                        Border.all(color: NyayaColors.navy.withValues(alpha: 0.25)),
                  ),
                  child: Text(
                    _formatElapsed(state.elapsedMs!),
                    style: const TextStyle(
                      fontSize: 11,
                      fontWeight: FontWeight.w700,
                      color: NyayaColors.navy,
                      fontFeatures: [FontFeature.tabularFigures()],
                    ),
                  ),
                ),
              ),
          ],
        ),
      ),
    );
  }

  String _statusLabel(AgentRunStatus s) => switch (s) {
        AgentRunStatus.pending => 'pending',
        AgentRunStatus.running => 'running',
        AgentRunStatus.done => 'done',
        AgentRunStatus.skipped => 'skipped',
        AgentRunStatus.error => 'errored',
      };

  static String _formatElapsed(int ms) {
    if (ms < 1000) return '${ms}ms';
    final seconds = ms / 1000.0;
    return '${seconds.toStringAsFixed(1)}s';
  }
}

class _StatusGlyph extends StatelessWidget {
  const _StatusGlyph({required this.status});

  final AgentRunStatus status;

  @override
  Widget build(BuildContext context) {
    switch (status) {
      case AgentRunStatus.pending:
        return const Icon(Icons.schedule, size: 22, color: NyayaColors.muted);
      case AgentRunStatus.running:
        return const SizedBox(
          width: 22,
          height: 22,
          child: CircularProgressIndicator(
            strokeWidth: 2.5,
            valueColor: AlwaysStoppedAnimation<Color>(NyayaColors.navy),
          ),
        );
      case AgentRunStatus.done:
        return const Icon(
          Icons.check_circle,
          size: 22,
          color: NyayaColors.ok,
        );
      case AgentRunStatus.skipped:
        return const Icon(
          Icons.remove_circle_outline,
          size: 22,
          color: NyayaColors.muted,
        );
      case AgentRunStatus.error:
        return const Icon(Icons.error, size: 22, color: NyayaColors.fail);
    }
  }
}
