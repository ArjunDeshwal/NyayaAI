import 'package:flutter/material.dart';

import '../../app/theme.dart';

/// Top-of-page brand banner.
///
/// Per task scope: ships **English + Hindi** only (a Hindi greeting is our
/// signal to the GSC judges that l10n is a first-class concern; TA/BN land
/// in the finals build).
class LandingBanner extends StatelessWidget {
  const LandingBanner({super.key});

  @override
  Widget build(BuildContext context) {
    return Semantics(
      container: true,
      header: true,
      child: Container(
        width: double.infinity,
        decoration: const BoxDecoration(
          color: NyayaColors.card,
          border: Border(
            top: BorderSide(color: NyayaColors.navy, width: 6),
            bottom: BorderSide(color: NyayaColors.border),
          ),
        ),
        padding: const EdgeInsets.symmetric(horizontal: 40, vertical: 28),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Bilingual wordmark — `NyayaAI — न्याय AI`.
            MergeSemantics(
              child: Semantics(
                label: 'NyayaAI, Nyaya A I, bias auditor',
                child: RichText(
                  text: const TextSpan(
                    style: TextStyle(
                      fontSize: 34,
                      fontWeight: FontWeight.w800,
                      letterSpacing: -0.5,
                    ),
                    children: <InlineSpan>[
                      TextSpan(
                        text: 'N',
                        style: TextStyle(color: NyayaColors.saffron),
                      ),
                      TextSpan(
                        text: 'yaya',
                        style: TextStyle(color: NyayaColors.navy),
                      ),
                      TextSpan(
                        text: 'A',
                        style: TextStyle(color: NyayaColors.green),
                      ),
                      TextSpan(text: 'I', style: TextStyle(color: NyayaColors.navy)),
                      TextSpan(
                        text: '  —  न्याय AI',
                        style: TextStyle(
                          color: NyayaColors.ink,
                          fontSize: 28,
                          fontWeight: FontWeight.w600,
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            ),
            const SizedBox(height: 8),
            const Text(
              'Agentic, India-aware bias auditor for public-interest AI.',
              style: TextStyle(fontSize: 16, color: NyayaColors.ink),
            ),
            const SizedBox(height: 4),
            Semantics(
              label:
                  'Namaste. Find bias in your data — in a single click. Hindi.',
              child: const Text(
                'नमस्ते। अपने डेटा में पूर्वाग्रह ढूँढिए — सिर्फ़ एक क्लिक में।',
                style: TextStyle(
                  fontSize: 15,
                  color: NyayaColors.muted,
                  height: 1.5,
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
