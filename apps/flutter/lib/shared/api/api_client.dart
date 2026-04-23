import 'dart:async';
import 'dart:convert';
import 'dart:typed_data';

import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:http/http.dart' as http;
import 'package:http_parser/http_parser.dart';
import 'package:nyayai_contracts/nyayai_contracts.dart';

import 'api_config.dart';

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

  Future<AuditResponse> submitAudit(AuditUploadRequest req) async {
    final uri = config.endpoint('/audit/upload');

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
      String detail = body;
      try {
        final decoded = jsonDecode(body);
        if (decoded is Map && decoded['detail'] != null) {
          detail = decoded['detail'].toString();
        }
      } catch (_) {
        // leave raw body as detail
      }
      throw AuditApiException(detail, statusCode: streamed.statusCode);
    }

    try {
      final json = jsonDecode(body) as Map<String, dynamic>;
      return AuditResponse.fromJson(json);
    } catch (e) {
      throw AuditApiException('Malformed response: $e');
    }
  }

  void close() => _client.close();
}

final apiConfigProvider = Provider<ApiConfig>((ref) => ApiConfig.fromEnv());

final apiClientProvider = Provider<NyayaApiClient>((ref) {
  final client = NyayaApiClient(config: ref.watch(apiConfigProvider));
  ref.onDispose(client.close);
  return client;
});
