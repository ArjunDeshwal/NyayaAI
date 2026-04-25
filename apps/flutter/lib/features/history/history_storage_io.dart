/// IO (non-web) stub for the localStorage shim. The
/// [AuditHistoryRepository] only calls into these functions when `kIsWeb` is
/// true, so the bodies are unreachable on this platform — but Dart still
/// type-checks the signatures.
String? getItem(String key) => null;

void setItem(String key, String value) {}

void removeItem(String key) {}
