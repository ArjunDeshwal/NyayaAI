import 'dart:async';

import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:nyayai_contracts/nyayai_contracts.dart';

import '../../shared/api/api_client.dart';
import '../../shared/api/audit_stream_event.dart';
import '../history/history_entry.dart';
import '../history/history_repository.dart';
import 'agent_timeline_state.dart';
import 'audit_form_state.dart';

/// Maps a server `phase` string to the canonical [AgentPhase] enum.
AgentPhase? _phaseFromWire(String wire) {
  for (final p in AgentPhase.values) {
    if (p.wire == wire) return p;
  }
  return null;
}

class AuditFormController extends StateNotifier<AuditFormState> {
  AuditFormController(this._api, this._history) : super(const AuditFormState());

  final NyayaApiClient _api;
  final AuditHistoryRepository _history;
  StreamSubscription<AuditStreamEvent>? _streamSub;

  /// Stream-aware upload flow. Drives the agent timeline.
  Future<void> submitUpload(AuditUploadRequest request) async {
    if (state.isSubmitting) return;
    _resetSubmitting();

    final stream = _api.streamUpload(request);
    await _consumeStream(
      stream,
      datasetName: request.datasetName,
      regimeWire: request.regime.wire,
    );
  }

  /// Stream-aware preset flow. Drives the agent timeline.
  Future<void> submitSample(
    AuditSampleRequest request, {
    required String datasetLabel,
  }) async {
    if (state.isSubmitting) return;
    _resetSubmitting();

    final stream = _api.streamSample(request);
    await _consumeStream(
      stream,
      datasetName: datasetLabel,
      regimeWire: (request.regime ?? Regime.dpdp).wire,
    );
  }

  /// Backwards-compat shim — keeps the old non-streaming entrypoint working
  /// for any caller that has not migrated.
  Future<void> submit(AuditUploadRequest request) => submitUpload(request);

  void reset() {
    _streamSub?.cancel();
    _streamSub = null;
    state = const AuditFormState();
  }

  // ---------------------------------------------------------------------------
  // Internals.
  // ---------------------------------------------------------------------------

  void _resetSubmitting() {
    _streamSub?.cancel();
    _streamSub = null;
    state = AuditFormState(
      status: AuditStatus.submitting,
      progressHint: 'Streaming agent timeline…',
      timeline: AgentTimelineState.initial(),
    );
  }

  Future<void> _consumeStream(
    Stream<AuditStreamEvent> stream, {
    required String datasetName,
    required String regimeWire,
  }) async {
    final completer = Completer<void>();

    _streamSub = stream.listen(
      (event) => _handleEvent(
        event,
        datasetName: datasetName,
        regimeWire: regimeWire,
      ),
      onError: (Object e, StackTrace st) {
        state = state.copyWith(
          status: AuditStatus.error,
          errorMessage:
              e is AuditApiException ? e.message : 'Unexpected error: $e',
        );
        if (!completer.isCompleted) completer.complete();
      },
      onDone: () {
        if (!completer.isCompleted) completer.complete();
      },
      cancelOnError: true,
    );

    await completer.future;
  }

  void _handleEvent(
    AuditStreamEvent event, {
    required String datasetName,
    required String regimeWire,
  }) {
    // Top-level pipeline events (phase=audit) — error fan-out.
    if (event.phase == 'audit') {
      if (event.isError) {
        state = state.copyWith(
          status: AuditStatus.error,
          errorMessage: event.errorMessage ?? 'Audit failed.',
        );
      }
      return;
    }

    // Per-phase updates.
    final phase = _phaseFromWire(event.phase);
    if (phase != null) {
      _updatePhase(phase, event);
    }

    // Remediation extras (target attribute, before/after).
    if (phase == AgentPhase.remediation && event.isDone) {
      state = state.copyWith(
        remediationSummary: RemediationSummary(
          improved: event.improved ?? false,
          targetAttribute: event.targetAttribute,
          beforeDpRatio: event.beforeDpRatio,
          afterDpRatio: event.afterDpRatio,
        ),
      );
    }

    // Terminal event — fold into the final AuditResponse.
    if (event.isComplete) {
      final response = AuditResponse(
        auditId: event.auditId ?? '',
        status: 'completed',
        overallDisparateImpact: event.overallDisparateImpact,
        driftLevel: event.driftLevel,
        reportJsonUrl: event.reportJsonUrl ?? '',
        reportHtmlUrl: event.reportHtmlUrl ?? '',
        reportPdfUrl: event.reportPdfUrl,
      );
      // Decorate the timeline rows with one-line "finding" pills so the
      // user sees a quick verdict on each phase without opening the report.
      var timeline = state.timeline ?? AgentTimelineState.initial();
      final di = event.overallDisparateImpact;
      if (di != null) {
        timeline = timeline.updatePhase(
          AgentPhase.fairness,
          timeline.phases
              .firstWhere((p) => p.phase == AgentPhase.fairness)
              .copyWith(finding: 'DI ${di.toStringAsFixed(3)}'),
        );
      }
      final drift = event.driftLevel;
      if (drift != null) {
        timeline = timeline.updatePhase(
          AgentPhase.watcher,
          timeline.phases
              .firstWhere((p) => p.phase == AgentPhase.watcher)
              .copyWith(finding: 'drift: $drift'),
        );
      }
      final rem = state.remediationSummary;
      if (rem != null &&
          rem.beforeDpRatio != null &&
          rem.afterDpRatio != null) {
        timeline = timeline.updatePhase(
          AgentPhase.remediation,
          timeline.phases
              .firstWhere((p) => p.phase == AgentPhase.remediation)
              .copyWith(
                finding:
                    '${rem.beforeDpRatio!.toStringAsFixed(3)} → ${rem.afterDpRatio!.toStringAsFixed(3)}',
              ),
        );
      }
      state = state.copyWith(
        status: AuditStatus.success,
        response: response,
        timeline: timeline,
      );
      // Persist this audit to localStorage history. Best-effort.
      _history.add(
        HistoryEntry(
          auditId: response.auditId,
          datasetName: datasetName,
          regime: regimeWire,
          overallDpRatio: response.overallDisparateImpact,
          driftLevel: response.driftLevel,
          remediationAfterDp: state.remediationSummary?.afterDpRatio,
          remediationImproved: state.remediationSummary?.improved,
          completedAtIso: DateTime.now().toUtc().toIso8601String(),
          reportHtmlUrl: response.reportHtmlUrl,
        ),
      );
    }
  }

  void _updatePhase(AgentPhase phase, AuditStreamEvent event) {
    final timeline = state.timeline ?? AgentTimelineState.initial();
    final existing = timeline.phases.firstWhere(
      (p) => p.phase == phase,
      orElse: () => AgentPhaseState(phase: phase),
    );

    AgentRunStatus next = existing.status;
    if (event.isStarted) {
      next = AgentRunStatus.running;
    } else if (event.isDone) {
      next = AgentRunStatus.done;
    } else if (event.isSkipped) {
      next = AgentRunStatus.skipped;
    } else if (event.isError) {
      next = AgentRunStatus.error;
    }

    final updated = existing.copyWith(
      status: next,
      elapsedMs: event.elapsedMs ?? existing.elapsedMs,
      message: event.errorMessage ?? existing.message,
    );

    state = state.copyWith(timeline: timeline.updatePhase(phase, updated));
  }

  @override
  void dispose() {
    _streamSub?.cancel();
    super.dispose();
  }
}

final auditFormControllerProvider =
    StateNotifierProvider<AuditFormController, AuditFormState>((ref) {
  return AuditFormController(
    ref.watch(apiClientProvider),
    ref.watch(historyRepositoryProvider),
  );
});
