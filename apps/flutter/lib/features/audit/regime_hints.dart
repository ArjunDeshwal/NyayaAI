import 'package:nyayai_contracts/nyayai_contracts.dart';

/// Per-regime placeholder + helper text for the goal field (Feature E).
///
/// When the user switches the regulatory regime, the goal field's hint and
/// helper text update — but the goal text itself is preserved so we never
/// overwrite a partially-typed audit goal.
class RegimeHint {
  const RegimeHint({required this.placeholder, required this.helper});

  final String placeholder;
  final String helper;

  static const RegimeHint dpdp = RegimeHint(
    placeholder:
        'Audit for caste, religion, region and language bias under DPDP '
        'Act 2023 Rule 13 and the RBI Digital Lending Directions.',
    helper:
        'DPDP Rule 13 mandates a Data Protection Impact Assessment for '
        'high-risk processing.',
  );

  static const RegimeHint euAiAct = RegimeHint(
    placeholder:
        'Audit for sex, race, age and country-of-origin bias under EU AI '
        'Act Article 10 (data governance) and Article 13 (transparency).',
    helper:
        'Article 10 governs training-data bias; Article 13 covers '
        'transparency to deployers.',
  );

  static const RegimeHint rbi = RegimeHint(
    placeholder:
        'Audit a digital lending model for caste, region and gender '
        'disparate impact per the RBI Digital Lending Directions 2025.',
    helper:
        'RBI guidelines require fair and non-discriminatory credit '
        'decisioning.',
  );

  static RegimeHint forRegime(Regime regime) => switch (regime) {
        Regime.dpdp => dpdp,
        Regime.euAiAct => euAiAct,
        Regime.rbi => rbi,
      };
}
