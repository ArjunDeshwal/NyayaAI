import 'package:flutter/foundation.dart';

/// Five canonical pipeline phases — order is fixed in the UI.
enum AgentPhase { planner, fairness, narrator, watcher, remediation }

extension AgentPhaseWire on AgentPhase {
  /// Server `phase` string for this enum value.
  String get wire => switch (this) {
        AgentPhase.planner => 'planner',
        AgentPhase.fairness => 'fairness',
        AgentPhase.narrator => 'narrator',
        AgentPhase.watcher => 'watcher',
        AgentPhase.remediation => 'remediation',
      };

  String get displayName => switch (this) {
        AgentPhase.planner => 'Planner',
        AgentPhase.fairness => 'Fairness Engine',
        AgentPhase.narrator => 'Narrator',
        AgentPhase.watcher => 'Watcher',
        AgentPhase.remediation => 'Remediation',
      };

  String get subtitle => switch (this) {
        AgentPhase.planner => 'Gemini 3.1 Pro chooses metrics',
        AgentPhase.fairness => 'Classical Fairlearn',
        AgentPhase.narrator => 'Gemini 3 Flash narrates',
        AgentPhase.watcher => 'Drift detector',
        AgentPhase.remediation => 'Fairlearn reductions + Gemini 3 Flash',
      };
}

enum AgentRunStatus { pending, running, done, skipped, error }

@immutable
class AgentPhaseState {
  const AgentPhaseState({
    required this.phase,
    this.status = AgentRunStatus.pending,
    this.elapsedMs,
    this.message,
  });

  final AgentPhase phase;
  final AgentRunStatus status;
  final int? elapsedMs;

  /// Optional one-line status message (e.g. error reason).
  final String? message;

  AgentPhaseState copyWith({
    AgentRunStatus? status,
    int? elapsedMs,
    String? message,
  }) {
    return AgentPhaseState(
      phase: phase,
      status: status ?? this.status,
      elapsedMs: elapsedMs ?? this.elapsedMs,
      message: message ?? this.message,
    );
  }
}

@immutable
class AgentTimelineState {
  const AgentTimelineState({this.phases = const []});

  /// Always five entries, in canonical order, even before the first event
  /// arrives. UIs render this list directly.
  final List<AgentPhaseState> phases;

  static AgentTimelineState initial() => AgentTimelineState(
        phases: AgentPhase.values
            .map((p) => AgentPhaseState(phase: p))
            .toList(growable: false),
      );

  /// True when at least one phase is running but no phase has errored and
  /// the run has not announced completion.
  bool get isRunning =>
      phases.any((p) => p.status == AgentRunStatus.running) ||
      phases.any((p) => p.status == AgentRunStatus.pending) &&
          phases.any(
            (p) =>
                p.status == AgentRunStatus.done ||
                p.status == AgentRunStatus.skipped ||
                p.status == AgentRunStatus.running,
          );

  AgentTimelineState updatePhase(AgentPhase phase, AgentPhaseState next) {
    final out = [
      for (final p in phases)
        if (p.phase == phase) next else p,
    ];
    return AgentTimelineState(phases: out);
  }
}
