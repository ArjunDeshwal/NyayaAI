import 'package:flutter/foundation.dart';

/// Seven canonical pipeline phases — order is fixed in the UI.
///
/// Counterfactual + Root-Cause fire only when the API was called with
/// `train_baseline=True` (the /audit/sample path). On the upload path they
/// arrive as `skipped` events with a reason — the row stays in the timeline
/// but renders strikethrough.
enum AgentPhase {
  planner,
  fairness,
  counterfactual,
  rootCause,
  narrator,
  watcher,
  remediation,
}

extension AgentPhaseWire on AgentPhase {
  /// Server `phase` string for this enum value.
  String get wire => switch (this) {
        AgentPhase.planner => 'planner',
        AgentPhase.fairness => 'fairness',
        AgentPhase.counterfactual => 'counterfactual',
        AgentPhase.rootCause => 'root_cause',
        AgentPhase.narrator => 'narrator',
        AgentPhase.watcher => 'watcher',
        AgentPhase.remediation => 'remediation',
      };

  String get displayName => switch (this) {
        AgentPhase.planner => 'Planner',
        AgentPhase.fairness => 'Fairness Engine',
        AgentPhase.counterfactual => 'Counterfactual',
        AgentPhase.rootCause => 'Root-Cause',
        AgentPhase.narrator => 'Narrator',
        AgentPhase.watcher => 'Watcher',
        AgentPhase.remediation => 'Remediation',
      };

  String get subtitle => switch (this) {
        AgentPhase.planner => 'Gemini 3.1 Pro chooses metrics',
        AgentPhase.fairness => 'Classical Fairlearn',
        AgentPhase.counterfactual =>
          'Individual-fairness flips · Gemini 3 Flash',
        AgentPhase.rootCause => 'Proxy-feature attribution · Gemini 3 Flash',
        AgentPhase.narrator => 'Gemini 3 Flash narrates',
        AgentPhase.watcher => 'Drift detector',
        AgentPhase.remediation => 'Fairlearn reductions + Gemini 3 Flash',
      };
}

/// Resolve a server phase string to its enum value, if recognised.
AgentPhase? agentPhaseFromWire(String wire) {
  for (final p in AgentPhase.values) {
    if (p.wire == wire) return p;
  }
  return null;
}

enum AgentRunStatus { pending, running, done, skipped, error }

@immutable
class AgentPhaseState {
  const AgentPhaseState({
    required this.phase,
    this.status = AgentRunStatus.pending,
    this.elapsedMs,
    this.message,
    this.finding,
  });

  final AgentPhase phase;
  final AgentRunStatus status;
  final int? elapsedMs;

  /// Optional one-line status message (e.g. error reason).
  final String? message;

  /// Short finding pill rendered after the phase completes — e.g.
  /// "DI 0.424", "flip 18%", "→ 0.719". Populated by the controller after
  /// the run completes (server emits the headline numbers on `complete`).
  final String? finding;

  AgentPhaseState copyWith({
    AgentRunStatus? status,
    int? elapsedMs,
    String? message,
    String? finding,
  }) {
    return AgentPhaseState(
      phase: phase,
      status: status ?? this.status,
      elapsedMs: elapsedMs ?? this.elapsedMs,
      message: message ?? this.message,
      finding: finding ?? this.finding,
    );
  }
}

@immutable
class AgentTimelineState {
  const AgentTimelineState({this.phases = const []});

  /// Always seven entries, in canonical order, even before the first event
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
