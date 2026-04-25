import 'dart:async';
import 'dart:convert';
import 'dart:typed_data';

import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:http/http.dart' as http;
import 'package:http_parser/http_parser.dart';
import 'package:nyayai_contracts/nyayai_contracts.dart';

import 'api_config.dart';
import 'audit_report.dart';
import 'audit_stream_event.dart';
import 'sample_dataset.dart';

/// Upload payload for `POST /audit/upload` — mirrors the FastAPI `Form` fields.
class AuditUploadRequest {
  const AuditUploadRequest({
    required this.datasetName,
    required this.goal,
    required this.protectedColumns,
    required this.outcomeColumn,
    required this.regime,
    this.modelId = 'unknown',
    this.modelScoreColumn,
    required this.fileBytes,
    required this.filename,
  });

  final String datasetName;
  final String goal;

  /// Comma-separated on the wire; we store a list and join at send time.
  final List<String> protectedColumns;
  final String outcomeColumn;
  final Regime regime;
  final String modelId;
  final String? modelScoreColumn;
  final Uint8List fileBytes;
  final String filename;
}

/// Body for `POST /audit/sample` and `POST /audit/sample-stream`.
class AuditSampleRequest {
  const AuditSampleRequest({
    required this.sampleId,
    this.goal,
    this.regime,
  });

  final String sampleId;

  /// Optional goal override. When null, the server's bundled default applies.
  final String? goal;

  /// Optional regime override.
  final Regime? regime;

  Map<String, dynamic> toJson() => <String, dynamic>{
        'sample_id': sampleId,
        if (goal != null && goal!.trim().isNotEmpty) 'goal': goal!.trim(),
        if (regime != null) 'regime': regime!.wire,
      };
}

class AuditApiException implements Exception {
  AuditApiException(this.message, {this.statusCode});

  final String message;
  final int? statusCode;

  @override
  String toString() => 'AuditApiException($statusCode): $message';
}

/// Thin HTTP wrapper — injectable for tests via `client:` constructor arg.
class NyayaApiClient {
  NyayaApiClient({
    required this.config,
    http.Client? client,
    this.timeout = const Duration(minutes: 3),
  }) : _client = client ?? http.Client();

  final ApiConfig config;
  final http.Client _client;
  final Duration timeout;

  // ---------------------------------------------------------------------------
  // Synchronous (non-streaming) endpoints — original code path.
  // ---------------------------------------------------------------------------

  Future<AuditResponse> submitAudit(AuditUploadRequest req) async {
    final uri = config.endpoint('/audit/upload');
    final request = _buildUploadRequest(uri, req);

    final http.StreamedResponse streamed;
    try {
      streamed = await _client.send(request).timeout(timeout);
    } on TimeoutException {
      throw AuditApiException('Audit timed out after ${timeout.inSeconds}s.');
    } catch (e) {
      throw AuditApiException('Network error: $e');
    }

    final body = await streamed.stream.bytesToString();

    if (streamed.statusCode < 200 || streamed.statusCode >= 300) {
      throw AuditApiException(
        _extractDetail(body),
        statusCode: streamed.statusCode,
      );
    }

    try {
      final json = jsonDecode(body) as Map<String, dynamic>;
      return AuditResponse.fromJson(json);
    } catch (e) {
      throw AuditApiException('Malformed response: $e');
    }
  }

  /// `POST /audit/sample` — synchronous fallback for the preset path.
  Future<AuditResponse> submitSample(AuditSampleRequest req) async {
    final uri = config.endpoint('/audit/sample');
    final http.Response response;
    try {
      response = await _client
          .post(
            uri,
            headers: const {'content-type': 'application/json'},
            body: jsonEncode(req.toJson()),
          )
          .timeout(timeout);
    } on TimeoutException {
      throw AuditApiException('Audit timed out after ${timeout.inSeconds}s.');
    } catch (e) {
      throw AuditApiException('Network error: $e');
    }

    if (response.statusCode < 200 || response.statusCode >= 300) {
      throw AuditApiException(
        _extractDetail(response.body),
        statusCode: response.statusCode,
      );
    }
    try {
      return AuditResponse.fromJson(
        jsonDecode(response.body) as Map<String, dynamic>,
      );
    } catch (e) {
      throw AuditApiException('Malformed response: $e');
    }
  }

  // ---------------------------------------------------------------------------
  // Sample catalog.
  // ---------------------------------------------------------------------------

  Future<List<SampleDataset>> fetchSamples() async {
    final uri = config.endpoint('/samples');
    final http.Response response;
    try {
      response = await _client.get(uri).timeout(const Duration(seconds: 30));
    } on TimeoutException {
      throw AuditApiException('Sample-catalog request timed out.');
    } catch (e) {
      throw AuditApiException('Network error: $e');
    }
    if (response.statusCode < 200 || response.statusCode >= 300) {
      throw AuditApiException(
        _extractDetail(response.body),
        statusCode: response.statusCode,
      );
    }
    try {
      final list = jsonDecode(response.body) as List;
      return list
          .whereType<Map<dynamic, dynamic>>()
          .map((m) => SampleDataset.fromJson(Map<String, dynamic>.from(m)))
          .toList(growable: false);
    } catch (e) {
      throw AuditApiException('Malformed /samples response: $e');
    }
  }

  // ---------------------------------------------------------------------------
  // Full report — used to fetch narrative.summary_hi, remediation, metrics.
  // ---------------------------------------------------------------------------

  Future<AuditReport> fetchReport(String auditId) async {
    final uri = config.endpoint('/reports/$auditId/json');
    final http.Response response;
    try {
      response = await _client.get(uri).timeout(const Duration(seconds: 30));
    } on TimeoutException {
      throw AuditApiException('Report fetch timed out.');
    } catch (e) {
      throw AuditApiException('Network error: $e');
    }
    if (response.statusCode < 200 || response.statusCode >= 300) {
      throw AuditApiException(
        _extractDetail(response.body),
        statusCode: response.statusCode,
      );
    }
    try {
      return AuditReport.fromJson(
        jsonDecode(response.body) as Map<String, dynamic>,
      );
    } catch (e) {
      throw AuditApiException('Malformed report JSON: $e');
    }
  }

  // ---------------------------------------------------------------------------
  // Streaming endpoints — NDJSON, one event per line.
  // ---------------------------------------------------------------------------

  /// Stream of NDJSON events from `POST /audit/sample-stream`.
  Stream<AuditStreamEvent> streamSample(AuditSampleRequest req) {
    final uri = config.endpoint('/audit/sample-stream');
    final request = http.Request('POST', uri)
      ..headers['content-type'] = 'application/json'
      ..headers['accept'] = 'application/x-ndjson'
      ..body = jsonEncode(req.toJson());
    return _streamNdjson(request);
  }

  /// Stream of NDJSON events from `POST /audit/upload-stream`.
  Stream<AuditStreamEvent> streamUpload(AuditUploadRequest req) {
    final uri = config.endpoint('/audit/upload-stream');
    final request = _buildUploadRequest(uri, req)
      ..headers['accept'] = 'application/x-ndjson';
    return _streamNdjson(request);
  }

  // ---------------------------------------------------------------------------
  // Internals.
  // ---------------------------------------------------------------------------

  http.MultipartRequest _buildUploadRequest(Uri uri, AuditUploadRequest req) {
    final request = http.MultipartRequest('POST', uri)
      ..fields['dataset_name'] = req.datasetName
      ..fields['goal'] = req.goal
      ..fields['protected_columns'] = req.protectedColumns.join(',')
      ..fields['outcome_column'] = req.outcomeColumn
      ..fields['regime'] = req.regime.wire
      ..fields['model_id'] = req.modelId;

    if (req.modelScoreColumn != null && req.modelScoreColumn!.isNotEmpty) {
      request.fields['model_score_column'] = req.modelScoreColumn!;
    }

    final mime = req.filename.toLowerCase().endsWith('.parquet')
        ? MediaType('application', 'octet-stream')
        : MediaType('text', 'csv');

    request.files.add(
      http.MultipartFile.fromBytes(
        'file',
        req.fileBytes,
        filename: req.filename,
        contentType: mime,
      ),
    );
    return request;
  }

  /// Sends `request` and parses the response stream as NDJSON. Each
  /// non-blank line is decoded into an [AuditStreamEvent]. Lines that fail to
  /// decode are skipped (we still want the rest of the timeline to render).
  Stream<AuditStreamEvent> _streamNdjson(http.BaseRequest request) async* {
    final http.StreamedResponse streamed;
    try {
      streamed = await _client.send(request).timeout(timeout);
    } on TimeoutException {
      throw AuditApiException('Audit stream timed out after '
          '${timeout.inSeconds}s.');
    } catch (e) {
      throw AuditApiException('Network error: $e');
    }

    if (streamed.statusCode < 200 || streamed.statusCode >= 300) {
      final body = await streamed.stream.bytesToString();
      throw AuditApiException(
        _extractDetail(body),
        statusCode: streamed.statusCode,
      );
    }

    final lines = streamed.stream
        .transform(utf8.decoder)
        .transform(const LineSplitter());
    await for (final raw in lines) {
      final line = raw.trim();
      if (line.isEmpty) continue;
      try {
        final json = jsonDecode(line);
        if (json is Map<String, dynamic>) {
          yield AuditStreamEvent.fromJson(json);
        }
      } catch (_) {
        // Skip malformed lines — the stream is best-effort.
      }
    }
  }

  String _extractDetail(String body) {
    try {
      final decoded = jsonDecode(body);
      if (decoded is Map && decoded['detail'] != null) {
        return decoded['detail'].toString();
      }
    } catch (_) {/* fall through */}
    return body;
  }

  void close() => _client.close();
}

final apiConfigProvider = Provider<ApiConfig>((ref) => ApiConfig.fromEnv());

final apiClientProvider = Provider<NyayaApiClient>((ref) {
  final client = NyayaApiClient(config: ref.watch(apiConfigProvider));
  ref.onDispose(client.close);
  return client;
});
