/// One NDJSON event from `POST /audit/sample-stream` or `/audit/upload-stream`.
///
/// Wire format (one JSON object per line):
///   {"phase":"planner","status":"started"}
///   {"phase":"planner","status":"done","elapsed_ms":4231}
///   {"phase":"remediation","status":"done","elapsed_ms":12340,
///    "improved":true,"target_attribute":"caste",
///    "before_dp_ratio":0.424,"after_dp_ratio":0.719}
///   {"phase":"complete","status":"done","audit_id":"audit_xxx",
///    "overall_disparate_impact":0.424,"drift_level":"major",
///    "report_html_url":"...","report_json_url":"...","report_pdf_url":"..."}
class AuditStreamEvent {
  const AuditStreamEvent({
    required this.phase,
    required this.status,
    this.elapsedMs,
    this.auditId,
    this.overallDisparateImpact,
    this.driftLevel,
    this.reportHtmlUrl,
    this.reportJsonUrl,
    this.reportPdfUrl,
    this.improved,
    this.targetAttribute,
    this.beforeDpRatio,
    this.afterDpRatio,
    this.errorMessage,
    this.raw = const <String, dynamic>{},
  });

  /// One of: `audit`, `planner`, `fairness`, `narrator`, `watcher`,
  /// `remediation`, `complete`. (Server may add more — we ignore unknown
  /// phases gracefully.)
  final String phase;

  /// One of: `started`, `done`, `skipped`, `error`.
  final String status;

  final int? elapsedMs;

  // Populated on `phase == "complete"` (and on the first `phase == "audit"`
  // event that announces the run id).
  final String? auditId;
  final double? overallDisparateImpact;
  final String? driftLevel;
  final String? reportHtmlUrl;
  final String? reportJsonUrl;
  final String? reportPdfUrl;

  // Populated on `phase == "remediation"`, `status == "done"`.
  final bool? improved;
  final String? targetAttribute;
  final double? beforeDpRatio;
  final double? afterDpRatio;

  /// Populated when `status == "error"`.
  final String? errorMessage;

  /// Original JSON object, in case downstream code needs a field we did not
  /// pre-extract.
  final Map<String, dynamic> raw;

  bool get isStarted => status == 'started';
  bool get isDone => status == 'done';
  bool get isSkipped => status == 'skipped';
  bool get isError => status == 'error';
  bool get isComplete => phase == 'complete' && status == 'done';

  factory AuditStreamEvent.fromJson(Map<String, dynamic> json) {
    double? toDouble(Object? v) => (v as num?)?.toDouble();
    return AuditStreamEvent(
      phase: (json['phase'] as String?) ?? 'unknown',
      status: (json['status'] as String?) ?? 'unknown',
      elapsedMs: (json['elapsed_ms'] as num?)?.toInt(),
      auditId: json['audit_id'] as String?,
      overallDisparateImpact: toDouble(json['overall_disparate_impact']),
      driftLevel: json['drift_level'] as String?,
      reportHtmlUrl: json['report_html_url'] as String?,
      reportJsonUrl: json['report_json_url'] as String?,
      reportPdfUrl: json['report_pdf_url'] as String?,
      improved: json['improved'] as bool?,
      targetAttribute: json['target_attribute'] as String?,
      beforeDpRatio: toDouble(json['before_dp_ratio']),
      afterDpRatio: toDouble(json['after_dp_ratio']),
      errorMessage: (json['error'] as String?) ??
          (json['error_message'] as String?) ??
          (json['detail'] as String?),
      raw: json,
    );
  }
}
