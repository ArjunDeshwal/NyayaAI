/// One row in the browser-localStorage audit history.
class HistoryEntry {
  const HistoryEntry({
    required this.auditId,
    required this.datasetName,
    required this.regime,
    required this.completedAtIso,
    required this.reportHtmlUrl,
    this.overallDpRatio,
    this.driftLevel,
    this.remediationAfterDp,
    this.remediationImproved,
  });

  final String auditId;
  final String datasetName;
  final String regime;
  final double? overallDpRatio;
  final String? driftLevel;
  final double? remediationAfterDp;
  final bool? remediationImproved;
  final String completedAtIso;
  final String reportHtmlUrl;

  /// `true` when the overall DP ratio meets the four-fifths rule. Mirrors
  /// the same logic as `AuditResponse.passesFourFifths`.
  bool get passesFourFifths =>
      overallDpRatio != null && overallDpRatio! >= 0.8;

  Map<String, dynamic> toJson() => <String, dynamic>{
        'audit_id': auditId,
        'dataset_name': datasetName,
        'regime': regime,
        'overall_dp_ratio': overallDpRatio,
        'drift_level': driftLevel,
        'remediation_after_dp': remediationAfterDp,
        'remediation_improved': remediationImproved,
        'completed_at_iso': completedAtIso,
        'report_html_url': reportHtmlUrl,
      };

  factory HistoryEntry.fromJson(Map<String, dynamic> json) {
    double? toDouble(Object? v) => (v as num?)?.toDouble();
    return HistoryEntry(
      auditId: (json['audit_id'] as String?) ?? '',
      datasetName: (json['dataset_name'] as String?) ?? '',
      regime: (json['regime'] as String?) ?? '',
      overallDpRatio: toDouble(json['overall_dp_ratio']),
      driftLevel: json['drift_level'] as String?,
      remediationAfterDp: toDouble(json['remediation_after_dp']),
      remediationImproved: json['remediation_improved'] as bool?,
      completedAtIso: (json['completed_at_iso'] as String?) ?? '',
      reportHtmlUrl: (json['report_html_url'] as String?) ?? '',
    );
  }
}
