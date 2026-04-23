/// API_BASE is supplied at build time via `--dart-define=API_BASE=...`.
/// Default points at the locally-running FastAPI gateway.
class ApiConfig {
  const ApiConfig({required this.baseUrl});

  final String baseUrl;

  static const String _defaultBase = String.fromEnvironment(
    'API_BASE',
    defaultValue: 'http://localhost:8080',
  );

  /// Resolves the base URL from the dart-define, trimming any trailing slash.
  static ApiConfig fromEnv() {
    final base = _defaultBase.endsWith('/')
        ? _defaultBase.substring(0, _defaultBase.length - 1)
        : _defaultBase;
    return ApiConfig(baseUrl: base);
  }

  Uri endpoint(String path) {
    final normalized = path.startsWith('/') ? path : '/$path';
    return Uri.parse('$baseUrl$normalized');
  }
}
