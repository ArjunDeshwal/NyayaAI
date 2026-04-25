/// Bundled-dataset metadata returned by `GET /samples`.
///
/// These mirror the FastAPI server's response for the three demo presets
/// (MUDRA-Lite, UCI Adult, COMPAS). The Flutter app uses them to prefill the
/// audit form when a user taps a preset chip.
class SampleDataset {
  const SampleDataset({
    required this.id,
    required this.name,
    required this.description,
    required this.region,
    required this.rowCount,
    required this.protectedColumns,
    required this.outcomeColumn,
    required this.modelScoreColumn,
    required this.defaultGoal,
    required this.defaultRegime,
    required this.defaultModelId,
    required this.available,
  });

  final String id;
  final String name;
  final String description;
  final String region;
  final int rowCount;
  final List<String> protectedColumns;
  final String outcomeColumn;
  final String? modelScoreColumn;
  final String defaultGoal;
  final String defaultRegime;
  final String defaultModelId;
  final bool available;

  factory SampleDataset.fromJson(Map<String, dynamic> json) {
    return SampleDataset(
      id: json['id'] as String,
      name: json['name'] as String,
      description: (json['description'] as String?) ?? '',
      region: (json['region'] as String?) ?? 'Unknown',
      rowCount: (json['row_count'] as num?)?.toInt() ?? 0,
      protectedColumns:
          ((json['protected_columns'] as List?) ?? const <dynamic>[])
              .map((e) => e.toString())
              .toList(growable: false),
      outcomeColumn: (json['outcome_column'] as String?) ?? '',
      modelScoreColumn: json['model_score_column'] as String?,
      defaultGoal: (json['default_goal'] as String?) ?? '',
      defaultRegime: (json['default_regime'] as String?) ?? 'DPDP',
      defaultModelId: (json['default_model_id'] as String?) ?? 'unknown',
      available: (json['available'] as bool?) ?? true,
    );
  }
}
