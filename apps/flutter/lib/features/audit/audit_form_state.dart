import 'package:nyayai_contracts/nyayai_contracts.dart';

import 'agent_timeline_state.dart';

/// Machine states for the single audit form screen.
enum AuditStatus { idle, submitting, success, error }

/// Snapshot of the remediation phase as announced over the NDJSON stream.
/// Used for an early "Δ +0.295 (caste)" summary before the full report
/// arrives.
class RemediationSummary {
  const RemediationSummary({
    required this.improved,
    this.targetAttribute,
    this.beforeDpRatio,
    this.afterDpRatio,
  });

  final bool improved;
  final String? targetAttribute;
  final double? beforeDpRatio;
  final double? afterDpRatio;
}

class AuditFormState {
  const AuditFormState({
    this.status = AuditStatus.idle,
    this.response,
    this.errorMessage,
    this.progressHint,
    this.timeline,
    this.remediationSummary,
  });

  final AuditStatus status;
  final AuditResponse? response;
  final String? errorMessage;

  /// Human-readable phase label shown alongside the spinner. Retained for
  /// backwards-compat with the (small) sync code path.
  final String? progressHint;

  /// Live-agent timeline. Null when not yet running.
  final AgentTimelineState? timeline;

  /// Remediation block surfaced from the streaming pipeline — null until the
  /// remediation phase emits its `done` event.
  final RemediationSummary? remediationSummary;

  bool get isSubmitting => status == AuditStatus.submitting;
  bool get hasError => status == AuditStatus.error;
  bool get hasResult => status == AuditStatus.success && response != null;

  AuditFormState copyWith({
    AuditStatus? status,
    AuditResponse? response,
    String? errorMessage,
    String? progressHint,
    AgentTimelineState? timeline,
    RemediationSummary? remediationSummary,
    bool clearError = false,
    bool clearResponse = false,
    bool clearTimeline = false,
    bool clearRemediation = false,
  }) {
    return AuditFormState(
      status: status ?? this.status,
      response: clearResponse ? null : (response ?? this.response),
      errorMessage: clearError ? null : (errorMessage ?? this.errorMessage),
      progressHint: progressHint ?? this.progressHint,
      timeline: clearTimeline ? null : (timeline ?? this.timeline),
      remediationSummary: clearRemediation
          ? null
          : (remediationSummary ?? this.remediationSummary),
    );
  }
}
