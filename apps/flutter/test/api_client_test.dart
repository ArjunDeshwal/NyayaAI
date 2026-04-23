import 'dart:convert';
import 'dart:typed_data';

import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:nyayai_contracts/nyayai_contracts.dart';

import 'package:nyayai_app/shared/api/api_client.dart';
import 'package:nyayai_app/shared/api/api_config.dart';

AuditUploadRequest _fixture() {
  return AuditUploadRequest(
    datasetName: 'test-dataset',
    goal: 'Audit a toy lending model for caste and gender disparity.',
    protectedColumns: const ['gender', 'caste'],
    outcomeColumn: 'approved',
    regime: Regime.dpdp,
    fileBytes: Uint8List.fromList(utf8.encode('a,b,c\n1,2,3\n')),
    filename: 'toy.csv',
  );
}

void main() {
  const config = ApiConfig(baseUrl: 'http://test.local');

  test('submitAudit posts multipart to /audit/upload and parses AuditResponse',
      () async {
    late http.BaseRequest captured;

    final mock = MockClient.streaming((request, body) async {
      captured = request;
      return http.StreamedResponse(
        Stream.value(utf8.encode(jsonEncode({
          'audit_id': 'audit_abc123',
          'status': 'completed',
          'overall_disparate_impact': 0.82,
          'drift_level': 'minor',
          'report_json_url': 'http://test.local/reports/audit_abc123/json',
          'report_html_url': 'http://test.local/reports/audit_abc123/html',
          'report_pdf_url': 'http://test.local/reports/audit_abc123/pdf',
        }))),
        200,
        headers: {'content-type': 'application/json'},
      );
    });

    final api = NyayaApiClient(config: config, client: mock);
    final resp = await api.submitAudit(_fixture());

    expect(resp.auditId, 'audit_abc123');
    expect(resp.status, 'completed');
    expect(resp.overallDisparateImpact, closeTo(0.82, 1e-9));
    expect(resp.passesFourFifths, isTrue);
    expect(resp.driftLevel, 'minor');

    expect(captured.method, 'POST');
    expect(captured.url.toString(), 'http://test.local/audit/upload');
    final ct = captured.headers['content-type'] ?? '';
    expect(ct.toLowerCase(), contains('multipart/form-data'));
  });

  test('submitAudit raises AuditApiException on non-2xx response', () async {
    final mock = MockClient((_) async {
      return http.Response(jsonEncode({'detail': 'bad column'}), 400);
    });
    final api = NyayaApiClient(config: config, client: mock);

    expect(
      () => api.submitAudit(_fixture()),
      throwsA(
        isA<AuditApiException>()
            .having((e) => e.statusCode, 'statusCode', 400)
            .having((e) => e.message, 'message', contains('bad column')),
      ),
    );
  });

  test('four-fifths rule boundary — 0.80 passes, 0.79 fails', () {
    const a = AuditResponse(
      auditId: 'a',
      status: 'completed',
      overallDisparateImpact: 0.80,
      driftLevel: 'none',
      reportJsonUrl: '',
      reportHtmlUrl: '',
      reportPdfUrl: null,
    );
    const b = AuditResponse(
      auditId: 'b',
      status: 'completed',
      overallDisparateImpact: 0.79,
      driftLevel: 'none',
      reportJsonUrl: '',
      reportHtmlUrl: '',
      reportPdfUrl: null,
    );
    expect(a.passesFourFifths, isTrue);
    expect(b.passesFourFifths, isFalse);
  });
}
