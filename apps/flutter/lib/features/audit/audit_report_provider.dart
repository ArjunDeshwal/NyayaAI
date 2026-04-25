import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../shared/api/api_client.dart';
import '../../shared/api/audit_report.dart';

/// Lazily-fetches `GET /reports/{audit_id}/json` for the result card. Family
/// is keyed by `audit_id` so reloading the same audit hits the cache.
final auditReportProvider =
    FutureProvider.family<AuditReport, String>((ref, auditId) async {
  final api = ref.watch(apiClientProvider);
  return api.fetchReport(auditId);
});
