/// Minimal Dart mirror of the server's full AuditReport JSON.
///
/// The Flutter app reads a few fields off the report — bilingual narrative
/// summary, remediation, counterfactual + root-cause + India RBI metric
/// blocks — so this model intentionally stays narrow. The bulk of the
/// report stays in the rendered HTML / PDF.
library;

class AuditRecommendation {
  const AuditRecommendation({
    required this.title,
    required this.detail,
    required this.severity,
  });

  final String title;
  final String detail;

  /// One of `info`, `advisory`, `action_required`.
  final String severity;

  /// Severity-sort key — higher values surface first.
  int get severityRank => switch (severity) {
        'action_required' => 3,
        'advisory' => 2,
        'info' => 1,
        _ => 0,
      };

  factory AuditRecommendation.fromJson(Map<String, dynamic> json) {
    return AuditRecommendation(
      title: (json['title'] as String?) ?? '',
      detail: (json['detail'] as String?) ?? '',
      severity: (json['severity'] as String?) ?? 'info',
    );
  }
}

class AuditNarrative {
  const AuditNarrative({
    this.summary,
    this.summaryHi,
    this.recommendations = const [],
  });

  /// English narrator output (Gemini 3 Flash).
  final String? summary;

  /// Hindi narrator output. May be null when translation was unavailable.
  final String? summaryHi;

  /// Plain-language recommendations, severity-tagged.
  final List<AuditRecommendation> recommendations;

  bool get hasHindi => summaryHi != null && summaryHi!.trim().isNotEmpty;

  factory AuditNarrative.fromJson(Map<String, dynamic> json) {
    final recsRaw = (json['recommendations'] as List?) ?? const [];
    return AuditNarrative(
      summary: json['summary'] as String?,
      summaryHi: json['summary_hi'] as String?,
      recommendations: recsRaw
          .whereType<Map<dynamic, dynamic>>()
          .map(
            (m) => AuditRecommendation.fromJson(Map<String, dynamic>.from(m)),
          )
          .toList(growable: false),
    );
  }
}

class AuditRemediation {
  const AuditRemediation({
    required this.improved,
    this.targetAttribute,
    this.targetGroupCount,
    this.mitigationName,
    this.beforeDpRatio,
    this.afterDpRatio,
    this.accuracyDeltaPp,
    this.summary,
    this.risks,
    this.codePatchSummary,
  });

  final bool improved;
  final String? targetAttribute;
  final int? targetGroupCount;
  final String? mitigationName;
  final double? beforeDpRatio;
  final double? afterDpRatio;
  final double? accuracyDeltaPp;
  final String? summary;
  final List<String>? risks;
  final String? codePatchSummary;

  double? get delta => (beforeDpRatio == null || afterDpRatio == null)
      ? null
      : afterDpRatio! - beforeDpRatio!;

  factory AuditRemediation.fromJson(Map<String, dynamic> json) {
    double? toDouble(Object? v) => (v as num?)?.toDouble();
    return AuditRemediation(
      improved: (json['improved'] as bool?) ?? false,
      targetAttribute: json['target_attribute'] as String?,
      targetGroupCount: (json['target_group_count'] as num?)?.toInt(),
      mitigationName: json['mitigation_name'] as String?,
      beforeDpRatio: toDouble(json['before_dp_ratio']),
      afterDpRatio: toDouble(json['after_dp_ratio']),
      accuracyDeltaPp: toDouble(json['accuracy_delta_pp']),
      summary: json['summary'] as String?,
      risks: (json['risks'] as List?)?.map((e) => e.toString()).toList(),
      codePatchSummary: json['code_patch_summary'] as String?,
    );
  }
}

/// One entry from `result.metrics`. Flutter reads only the per-attribute
/// demographic-parity-ratio rows (slice_key like `attribute=NAME` and
/// metric == `demographic_parity_ratio`).
class AuditMetric {
  const AuditMetric({
    required this.sliceKey,
    required this.metric,
    required this.value,
  });

  final String sliceKey;
  final String metric;
  final double? value;

  /// Returns the attribute name (e.g. "gender") if `slice_key` is of the form
  /// `attribute=<name>`. Returns null otherwise.
  String? get attributeName {
    const prefix = 'attribute=';
    if (!sliceKey.startsWith(prefix)) return null;
    final tail = sliceKey.substring(prefix.length).trim();
    return tail.isEmpty ? null : tail;
  }

  factory AuditMetric.fromJson(Map<String, dynamic> json) {
    return AuditMetric(
      sliceKey: (json['slice_key'] as String?) ?? '',
      metric: (json['metric'] as String?) ?? '',
      value: (json['value'] as num?)?.toDouble(),
    );
  }
}

// ---------------------------------------------------------------------------
// Counterfactual (individual fairness) — flip math + LLM narrative.
// ---------------------------------------------------------------------------

class CounterfactualExample {
  const CounterfactualExample({
    required this.rowIndex,
    required this.protectedValueBefore,
    required this.protectedValueAfter,
    required this.probabilityBefore,
    required this.probabilityAfter,
    required this.decisionBefore,
    required this.decisionAfter,
    required this.featureSnapshot,
  });

  final int rowIndex;
  final String protectedValueBefore;
  final String protectedValueAfter;
  final double probabilityBefore;
  final double probabilityAfter;
  final int decisionBefore;
  final int decisionAfter;
  final Map<String, String> featureSnapshot;

  factory CounterfactualExample.fromJson(Map<String, dynamic> json) {
    final raw = (json['feature_snapshot'] as Map?) ?? const {};
    return CounterfactualExample(
      rowIndex: (json['row_index'] as num?)?.toInt() ?? 0,
      protectedValueBefore: (json['protected_value_before'] as String?) ?? '',
      protectedValueAfter: (json['protected_value_after'] as String?) ?? '',
      probabilityBefore:
          (json['probability_before'] as num?)?.toDouble() ?? 0.0,
      probabilityAfter: (json['probability_after'] as num?)?.toDouble() ?? 0.0,
      decisionBefore: (json['decision_before'] as num?)?.toInt() ?? 0,
      decisionAfter: (json['decision_after'] as num?)?.toInt() ?? 0,
      featureSnapshot: {
        for (final e in raw.entries) e.key.toString(): e.value.toString(),
      },
    );
  }
}

class AuditCounterfactual {
  const AuditCounterfactual({
    required this.protectedAttribute,
    required this.directionalFlipRate,
    required this.flipRateByPair,
    required this.examples,
    required this.sampleSizeUsed,
    this.headline,
    this.interpretation,
    this.severity,
    this.exampleTakeaways = const [],
  });

  /// From `result.counterfactual`.
  final String protectedAttribute;
  final double directionalFlipRate;
  final Map<String, double> flipRateByPair;
  final List<CounterfactualExample> examples;
  final int sampleSizeUsed;

  /// From `counterfactual_narrative` (LLM output).
  final String? headline;
  final String? interpretation;
  final String? severity;
  final List<String> exampleTakeaways;

  static AuditCounterfactual? tryFromReport(Map<String, dynamic> json) {
    final result = (json['result'] as Map?) ?? const {};
    final summary = result['counterfactual'] as Map?;
    if (summary == null) return null;

    final pairsRaw = (summary['flip_rate_by_pair'] as Map?) ?? const {};
    final examplesRaw = (summary['examples'] as List?) ?? const [];
    final narrative = json['counterfactual_narrative'] as Map?;

    return AuditCounterfactual(
      protectedAttribute:
          (summary['protected_attribute'] as String?) ?? 'unknown',
      directionalFlipRate:
          (summary['directional_flip_rate'] as num?)?.toDouble() ?? 0.0,
      flipRateByPair: {
        for (final e in pairsRaw.entries)
          e.key.toString(): (e.value as num?)?.toDouble() ?? 0.0,
      },
      examples: examplesRaw
          .whereType<Map<dynamic, dynamic>>()
          .map(
            (m) => CounterfactualExample.fromJson(
              Map<String, dynamic>.from(m),
            ),
          )
          .toList(growable: false),
      sampleSizeUsed: (summary['sample_size_used'] as num?)?.toInt() ?? 0,
      headline: narrative?['headline'] as String?,
      interpretation: narrative?['interpretation'] as String?,
      severity: narrative?['severity'] as String?,
      exampleTakeaways: ((narrative?['example_takeaways'] as List?) ?? const [])
          .map((e) => e.toString())
          .toList(growable: false),
    );
  }
}

// ---------------------------------------------------------------------------
// Root-cause (proxy-feature attribution).
// ---------------------------------------------------------------------------

class FeatureContribution {
  const FeatureContribution({
    required this.featureName,
    required this.contributionToDisparity,
    this.plainExplanation,
  });

  final String featureName;
  final double contributionToDisparity;
  final String? plainExplanation;

  factory FeatureContribution.fromRanking(Map<String, dynamic> json) {
    return FeatureContribution(
      featureName: (json['feature_name'] as String?) ?? '',
      contributionToDisparity:
          (json['contribution_to_disparity'] as num?)?.toDouble() ?? 0.0,
    );
  }

  factory FeatureContribution.fromDriver(Map<String, dynamic> json) {
    return FeatureContribution(
      featureName: (json['feature_name'] as String?) ?? '',
      contributionToDisparity:
          (json['contribution_to_disparity'] as num?)?.toDouble() ?? 0.0,
      plainExplanation: json['plain_explanation'] as String?,
    );
  }
}

class AuditRootCause {
  const AuditRootCause({
    required this.protectedAttribute,
    required this.proxyFeatures,
    required this.baselineDpGap,
    required this.topDrivers,
    this.headline,
    this.proxyWarnings = const [],
    this.suggestedActions = const [],
  });

  final String protectedAttribute;
  final List<String> proxyFeatures;
  final double baselineDpGap;
  final List<FeatureContribution> topDrivers;
  final String? headline;
  final List<String> proxyWarnings;
  final List<String> suggestedActions;

  static AuditRootCause? tryFromReport(Map<String, dynamic> json) {
    final result = (json['result'] as Map?) ?? const {};
    final summary = result['root_cause'] as Map?;
    if (summary == null) return null;

    final narrative = json['root_cause_narrative'] as Map?;
    final rankingsRaw = (summary['rankings'] as List?) ?? const [];
    final driversRaw = (narrative?['top_drivers'] as List?) ?? const [];

    // Prefer LLM drivers (they carry plain_explanation); fall back to
    // classical rankings.
    final List<FeatureContribution> drivers;
    if (driversRaw.isNotEmpty) {
      drivers = driversRaw
          .whereType<Map<dynamic, dynamic>>()
          .map(
            (m) => FeatureContribution.fromDriver(
              Map<String, dynamic>.from(m),
            ),
          )
          .toList(growable: false);
    } else {
      drivers = rankingsRaw
          .whereType<Map<dynamic, dynamic>>()
          .map(
            (m) => FeatureContribution.fromRanking(
              Map<String, dynamic>.from(m),
            ),
          )
          .toList(growable: false);
    }

    return AuditRootCause(
      protectedAttribute:
          (summary['protected_attribute'] as String?) ?? 'unknown',
      proxyFeatures: ((summary['proxy_features'] as List?) ?? const [])
          .map((e) => e.toString())
          .toList(growable: false),
      baselineDpGap: (summary['baseline_dp_gap'] as num?)?.toDouble() ?? 0.0,
      topDrivers: drivers,
      headline: narrative?['headline'] as String?,
      proxyWarnings: ((narrative?['proxy_warnings'] as List?) ?? const [])
          .map((e) => e.toString())
          .toList(growable: false),
      suggestedActions: ((narrative?['suggested_actions'] as List?) ?? const [])
          .map((e) => e.toString())
          .toList(growable: false),
    );
  }
}

// ---------------------------------------------------------------------------
// India-specific (RBI) metrics.
// ---------------------------------------------------------------------------

class AuditIndiaMetrics {
  const AuditIndiaMetrics({
    this.splsActualByGroup = const {},
    this.splsTargetByGroup = const {},
    this.splsShortfallByGroup = const {},
    this.splsWorstGroup,
    this.splsTotalShortfall,
    this.lrbRejectionByGroup = const {},
    this.lrbRatio,
    this.lrbBreach,
    this.lrbWorstGroup,
    this.dlfScore,
    this.dlfDisparateImpact,
    this.dlfEqualOpportunity,
    this.dlfCalibration,
  });

  final Map<String, double> splsActualByGroup;
  final Map<String, double> splsTargetByGroup;
  final Map<String, double> splsShortfallByGroup;
  final String? splsWorstGroup;
  final double? splsTotalShortfall;

  final Map<String, double> lrbRejectionByGroup;
  final double? lrbRatio;
  final bool? lrbBreach;
  final String? lrbWorstGroup;

  final double? dlfScore;
  final double? dlfDisparateImpact;
  final double? dlfEqualOpportunity;
  final double? dlfCalibration;

  bool get hasSpls => splsActualByGroup.isNotEmpty;
  bool get hasLrb => lrbRejectionByGroup.isNotEmpty;
  bool get hasDlf => dlfScore != null;
  bool get isPopulated => hasSpls || hasLrb || hasDlf;

  static AuditIndiaMetrics? tryFromReport(Map<String, dynamic> json) {
    final result = (json['result'] as Map?) ?? const {};
    final bundle = result['india_metrics'] as Map?;
    if (bundle == null) return null;

    final spls = bundle['spls'] as Map?;
    final lrb = bundle['lrb'] as Map?;
    final dlf = bundle['dlf'] as Map?;

    Map<String, double> doubleMap(Object? v) {
      if (v is! Map) return const {};
      return {
        for (final e in v.entries)
          e.key.toString(): (e.value as num?)?.toDouble() ?? 0.0,
      };
    }

    return AuditIndiaMetrics(
      splsActualByGroup: doubleMap(spls?['actual_pct_by_group']),
      splsTargetByGroup: doubleMap(spls?['target_pct_by_group']),
      splsShortfallByGroup: doubleMap(spls?['shortfall_pct_by_group']),
      splsWorstGroup: spls?['worst_group'] as String?,
      splsTotalShortfall: (spls?['total_shortfall_amount'] as num?)?.toDouble(),
      lrbRejectionByGroup: doubleMap(lrb?['rejection_rate_by_group']),
      lrbRatio: (lrb?['rejection_rate_ratio'] as num?)?.toDouble(),
      lrbBreach: lrb?['rbi_advisory_breach'] as bool?,
      lrbWorstGroup: lrb?['worst_group'] as String?,
      dlfScore: (dlf?['score'] as num?)?.toDouble(),
      dlfDisparateImpact: (dlf?['disparate_impact'] as num?)?.toDouble(),
      dlfEqualOpportunity: (dlf?['equal_opportunity'] as num?)?.toDouble(),
      dlfCalibration: (dlf?['calibration_within_groups'] as num?)?.toDouble(),
    );
  }
}

// ---------------------------------------------------------------------------
// Top-level report.
// ---------------------------------------------------------------------------

class AuditReport {
  const AuditReport({
    required this.auditId,
    required this.metrics,
    required this.narrative,
    required this.remediation,
    required this.counterfactual,
    required this.rootCause,
    required this.indiaMetrics,
    required this.regime,
    required this.datasetName,
    required this.protectedColumns,
    required this.raw,
  });

  final String auditId;
  final List<AuditMetric> metrics;
  final AuditNarrative narrative;
  final AuditRemediation? remediation;
  final AuditCounterfactual? counterfactual;
  final AuditRootCause? rootCause;
  final AuditIndiaMetrics? indiaMetrics;

  /// Wire regime: `DPDP`, `EU_AI_ACT`, or `RBI`.
  final String regime;

  /// Friendly dataset name (from `request.dataset.name`).
  final String datasetName;

  /// Caller-supplied protected columns (from `request.dataset.candidate_protected_columns`).
  final List<String> protectedColumns;

  /// Original JSON. Useful for debugging and for fields we have not modelled.
  final Map<String, dynamic> raw;

  /// Returns the per-attribute demographic-parity-ratio map, e.g.
  /// `{"gender": 0.91, "caste": 0.42, ...}`. Skips rows with null values.
  Map<String, double> perAttributeDpRatio() {
    final out = <String, double>{};
    for (final m in metrics) {
      if (m.metric != 'demographic_parity_ratio') continue;
      final attr = m.attributeName;
      if (attr == null) continue;
      final v = m.value;
      if (v == null) continue;
      out[attr] = v;
    }
    return out;
  }

  factory AuditReport.fromJson(Map<String, dynamic> json) {
    final auditId = (json['audit_id'] as String?) ??
        ((json['result'] as Map?)?['audit_id'] as String?) ??
        '';

    // `result.metrics` is the canonical location, but support a top-level
    // `metrics` field as a fallback.
    final result = (json['result'] as Map?) ?? const {};
    final metricsRaw =
        (result['metrics'] as List?) ?? (json['metrics'] as List?) ?? const [];
    final metrics = metricsRaw
        .whereType<Map<dynamic, dynamic>>()
        .map((m) => AuditMetric.fromJson(Map<String, dynamic>.from(m)))
        .toList(growable: false);

    final narrativeJson =
        (json['narrative'] as Map?) ?? const <String, dynamic>{};
    final remJson = json['remediation'] as Map?;

    final request = (json['request'] as Map?) ?? const {};
    final dataset = (request['dataset'] as Map?) ?? const {};
    final protectedRaw =
        (dataset['candidate_protected_columns'] as List?) ?? const [];

    return AuditReport(
      auditId: auditId,
      metrics: metrics,
      narrative: AuditNarrative.fromJson(
        Map<String, dynamic>.from(narrativeJson),
      ),
      remediation: remJson == null
          ? null
          : AuditRemediation.fromJson(Map<String, dynamic>.from(remJson)),
      counterfactual: AuditCounterfactual.tryFromReport(json),
      rootCause: AuditRootCause.tryFromReport(json),
      indiaMetrics: AuditIndiaMetrics.tryFromReport(json),
      regime: (request['regime'] as String?) ?? 'DPDP',
      datasetName: (dataset['name'] as String?) ?? '',
      protectedColumns:
          protectedRaw.map((e) => e.toString()).toList(growable: false),
      raw: json,
    );
  }
}
