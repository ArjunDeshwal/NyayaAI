/// Minimal Dart mirror of the server's full AuditReport JSON.
///
/// The Flutter app only reads a few fields off the report — the bilingual
/// narrative summary and the remediation block — so this model intentionally
/// stays narrow. The bulk of the report stays in the rendered HTML / PDF.
library;

class AuditNarrative {
  const AuditNarrative({this.summary, this.summaryHi});

  /// English narrator output (Gemini 3 Flash).
  final String? summary;

  /// Hindi narrator output. May be null when translation was unavailable.
  final String? summaryHi;

  bool get hasHindi => summaryHi != null && summaryHi!.trim().isNotEmpty;

  factory AuditNarrative.fromJson(Map<String, dynamic> json) {
    return AuditNarrative(
      summary: json['summary'] as String?,
      summaryHi: json['summary_hi'] as String?,
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

class AuditReport {
  const AuditReport({
    required this.auditId,
    required this.metrics,
    required this.narrative,
    required this.remediation,
    required this.raw,
  });

  final String auditId;
  final List<AuditMetric> metrics;
  final AuditNarrative narrative;
  final AuditRemediation? remediation;

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

    return AuditReport(
      auditId: auditId,
      metrics: metrics,
      narrative: AuditNarrative.fromJson(
        Map<String, dynamic>.from(narrativeJson),
      ),
      remediation: remJson == null
          ? null
          : AuditRemediation.fromJson(Map<String, dynamic>.from(remJson)),
      raw: json,
    );
  }
}
