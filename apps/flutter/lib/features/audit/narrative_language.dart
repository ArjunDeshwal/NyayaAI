import 'package:flutter_riverpod/flutter_riverpod.dart';

/// Narrative language preference. Persists across audits in-memory (Feature
/// D). The toggle hides itself when Hindi is unavailable for the current
/// audit; this preference still survives so the next audit with Hindi
/// available will default back to whatever the user last chose.
enum NarrativeLanguage { en, hi }

class NarrativeLanguageNotifier extends StateNotifier<NarrativeLanguage> {
  NarrativeLanguageNotifier() : super(NarrativeLanguage.en);

  void set(NarrativeLanguage lang) => state = lang;
}

final narrativeLanguageProvider =
    StateNotifierProvider<NarrativeLanguageNotifier, NarrativeLanguage>(
  (ref) => NarrativeLanguageNotifier(),
);
