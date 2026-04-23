/// Minimal Dart mirror of the server's AuditResponse.
///
/// Keep this tiny. The Flutter app does not consume the full AuditReport —
/// it reads the report HTML/PDF as a rendered document via URL.
library;

class AuditResponse {
  final String auditId;
  final String status;
  final double? overallDisparateImpact;
  final String? driftLevel;
  final String reportJsonUrl;
  final String reportHtmlUrl;
  final String? reportPdfUrl;

  const AuditResponse({
    required this.auditId,
    required this.status,
    required this.overallDisparateImpact,
    required this.driftLevel,
    required this.reportJsonUrl,
    required this.reportHtmlUrl,
    required this.reportPdfUrl,
  });

  factory AuditResponse.fromJson(Map<String, dynamic> json) {
    return AuditResponse(
      auditId: json['audit_id'] as String,
      status: json['status'] as String,
      overallDisparateImpact:
          (json['overall_disparate_impact'] as num?)?.toDouble(),
      driftLevel: json['drift_level'] as String?,
      reportJsonUrl: json['report_json_url'] as String,
      reportHtmlUrl: json['report_html_url'] as String,
      reportPdfUrl: json['report_pdf_url'] as String?,
    );
  }

  bool get passesFourFifths =>
      overallDisparateImpact != null && overallDisparateImpact! >= 0.8;
}

enum Regime { dpdp, euAiAct, rbi }

extension RegimeWire on Regime {
  String get wire => switch (this) {
        Regime.dpdp => 'DPDP',
        Regime.euAiAct => 'EU_AI_ACT',
        Regime.rbi => 'RBI',
      };
}
