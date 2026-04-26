import 'package:flutter/material.dart';

import '../../app/theme.dart';

/// "Why NyayaAI" — competitive comparison card.
///
/// 4-column comparison vs AIF360 / Fairlearn / Vertex Eval / Holistic AI.
/// Saffron-tinted NyayaAI column. Mirrors the talking points in the GSC
/// pitch deck (slide 4: USP + opportunities) so a judge sees the same
/// claim landed in code as on paper.
class WhyNyayaaiCard extends StatelessWidget {
  const WhyNyayaaiCard({super.key});

  static const _rows = <_FeatureRow>[
    _FeatureRow(
      label: 'India-aware taxonomy',
      detail: 'caste · religion · region · language',
      values: [_V.no, _V.no, _V.no, _V.no, _V.yes],
    ),
    _FeatureRow(
      label: 'Novel India metrics',
      detail: 'SPLS · LRB · DLF',
      values: [_V.no, _V.no, _V.no, _V.no, _V.yes],
    ),
    _FeatureRow(
      label: 'Counterfactual + Root-Cause',
      detail: 'individual fairness + proxy attribution',
      values: [_V.partial, _V.no, _V.no, _V.partial, _V.yes],
    ),
    _FeatureRow(
      label: 'Auto-mapped DPDP Rule 13',
      detail: 'EU AI Act Articles 9–15 · RBI Directions',
      values: [_V.no, _V.no, _V.no, _V.no, _V.yes],
    ),
    _FeatureRow(
      label: 'Bilingual Hindi narrative',
      detail: 'one Gemini call, no round-trip',
      values: [_V.no, _V.no, _V.no, _V.no, _V.yes],
    ),
    _FeatureRow(
      label: 'Real remediation, not just diagnosis',
      detail: 'ExponentiatedGradient retrain + gate',
      values: [_V.partial, _V.yes, _V.no, _V.partial, _V.yes],
    ),
    _FeatureRow(
      label: 'Hallucination-proof numbers',
      detail: 'classical math owns metrics, LLM only narrates',
      values: [_V.partial, _V.yes, _V.partial, _V.partial, _V.yes],
    ),
    _FeatureRow(
      label: 'Offline (Gemini Nano)',
      detail: 'on-device citizen audit',
      values: [_V.no, _V.no, _V.no, _V.no, _V.yes],
    ),
  ];

  static const _competitors = [
    'AIF360',
    'Fairlearn',
    'Vertex Eval',
    'Holistic',
  ];

  @override
  Widget build(BuildContext context) {
    final isWide = MediaQuery.sizeOf(context).width >= 720;
    return Semantics(
      container: true,
      label: 'Comparison card. NyayaAI versus AIF360, Fairlearn, Vertex Model '
          'Evaluation, and Holistic AI. NyayaAI checks every row.',
      child: Container(
        padding: EdgeInsets.all(isWide ? 24 : 18),
        decoration: BoxDecoration(
          color: NyayaColors.card,
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: NyayaColors.border),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                const Icon(
                  Icons.fact_check_outlined,
                  size: 20,
                  color: NyayaColors.navy,
                ),
                const SizedBox(width: 8),
                Text(
                  'Why NyayaAI',
                  style: Theme.of(context).textTheme.titleLarge,
                ),
              ],
            ),
            const SizedBox(height: 4),
            const Text(
              'A library is not a product. Below — what every audit toolkit '
              'we benchmarked ships, and what they don\'t.',
              style: TextStyle(color: NyayaColors.muted, fontSize: 13),
            ),
            const SizedBox(height: 16),
            isWide ? const _DesktopTable() : const _MobileList(),
          ],
        ),
      ),
    );
  }
}

class _DesktopTable extends StatelessWidget {
  const _DesktopTable();

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        const _HeaderRow(),
        const Divider(height: 16),
        for (final row in WhyNyayaaiCard._rows) _DataRow(row: row),
      ],
    );
  }
}

class _HeaderRow extends StatelessWidget {
  const _HeaderRow();

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 8),
      child: Row(
        children: [
          const Expanded(flex: 4, child: SizedBox.shrink()),
          for (final c in WhyNyayaaiCard._competitors)
            Expanded(
              flex: 2,
              child: Center(
                child: Text(
                  c,
                  style: const TextStyle(
                    fontSize: 12,
                    fontWeight: FontWeight.w700,
                    color: NyayaColors.muted,
                    letterSpacing: 0.4,
                  ),
                ),
              ),
            ),
          Expanded(
            flex: 2,
            child: Center(
              child: Container(
                padding:
                    const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                decoration: BoxDecoration(
                  color: NyayaColors.saffron.withValues(alpha: 0.18),
                  borderRadius: BorderRadius.circular(20),
                  border: Border.all(color: NyayaColors.saffron, width: 2),
                ),
                child: const Text(
                  'NyayaAI',
                  style: TextStyle(
                    fontSize: 12,
                    fontWeight: FontWeight.w800,
                    color: NyayaColors.navy,
                    letterSpacing: 0.4,
                  ),
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _DataRow extends StatelessWidget {
  const _DataRow({required this.row});
  final _FeatureRow row;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 6),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.center,
        children: [
          Expanded(
            flex: 4,
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  row.label,
                  style: const TextStyle(
                    fontSize: 13,
                    fontWeight: FontWeight.w700,
                    color: NyayaColors.ink,
                  ),
                ),
                const SizedBox(height: 2),
                Text(
                  row.detail,
                  style: const TextStyle(
                    fontSize: 11,
                    color: NyayaColors.muted,
                  ),
                ),
              ],
            ),
          ),
          // Indices 0–3 = competitors; index 4 = NyayaAI.
          for (var i = 0; i < 4; i++)
            Expanded(
              flex: 2,
              child: Center(child: _Cell(value: row.values[i])),
            ),
          Expanded(
            flex: 2,
            child: Center(
              child: Container(
                decoration: BoxDecoration(
                  color: NyayaColors.saffron.withValues(alpha: 0.10),
                  borderRadius: BorderRadius.circular(8),
                ),
                padding: const EdgeInsets.symmetric(vertical: 8),
                child: _Cell(value: row.values[4]),
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _MobileList extends StatelessWidget {
  const _MobileList();

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        for (final row in WhyNyayaaiCard._rows)
          Padding(
            padding: const EdgeInsets.only(bottom: 12),
            child: Container(
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: NyayaColors.bg,
                borderRadius: BorderRadius.circular(8),
                border: Border.all(color: NyayaColors.border),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      Expanded(
                        child: Text(
                          row.label,
                          style: const TextStyle(
                            fontSize: 13,
                            fontWeight: FontWeight.w700,
                            color: NyayaColors.ink,
                          ),
                        ),
                      ),
                      _Cell(value: row.values[4]),
                    ],
                  ),
                  const SizedBox(height: 4),
                  Text(
                    row.detail,
                    style: const TextStyle(
                      fontSize: 11,
                      color: NyayaColors.muted,
                    ),
                  ),
                  const SizedBox(height: 8),
                  Wrap(
                    spacing: 8,
                    runSpacing: 4,
                    children: [
                      for (var i = 0; i < 4; i++)
                        _MobileChip(
                          competitor: WhyNyayaaiCard._competitors[i],
                          v: row.values[i],
                        ),
                    ],
                  ),
                ],
              ),
            ),
          ),
      ],
    );
  }
}

class _MobileChip extends StatelessWidget {
  const _MobileChip({required this.competitor, required this.v});

  final String competitor;
  final _V v;

  @override
  Widget build(BuildContext context) {
    final color = switch (v) {
      _V.yes => NyayaColors.ok,
      _V.partial => NyayaColors.warn,
      _V.no => NyayaColors.muted,
    };
    final glyph = switch (v) {
      _V.yes => '✓',
      _V.partial => '~',
      _V.no => '×',
    };
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      decoration: BoxDecoration(
        color: NyayaColors.card,
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: NyayaColors.border),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Text(
            glyph,
            style: TextStyle(
              fontSize: 12,
              fontWeight: FontWeight.w800,
              color: color,
            ),
          ),
          const SizedBox(width: 6),
          Text(
            competitor,
            style: const TextStyle(
              fontSize: 11,
              color: NyayaColors.muted,
              fontWeight: FontWeight.w600,
            ),
          ),
        ],
      ),
    );
  }
}

class _Cell extends StatelessWidget {
  const _Cell({required this.value});

  final _V value;

  @override
  Widget build(BuildContext context) {
    switch (value) {
      case _V.yes:
        return Semantics(
          label: 'yes',
          child: const Icon(
            Icons.check_circle,
            color: NyayaColors.ok,
            size: 20,
          ),
        );
      case _V.no:
        return Semantics(
          label: 'no',
          child: const Icon(
            Icons.cancel_outlined,
            color: NyayaColors.muted,
            size: 20,
          ),
        );
      case _V.partial:
        return Semantics(
          label: 'partial',
          child: const Icon(
            Icons.adjust,
            color: NyayaColors.warn,
            size: 20,
          ),
        );
    }
  }
}

enum _V { yes, no, partial }

class _FeatureRow {
  const _FeatureRow({
    required this.label,
    required this.detail,
    required this.values,
  });

  final String label;
  final String detail;

  /// Order: AIF360, Fairlearn, Vertex Eval, Holistic AI, NyayaAI.
  final List<_V> values;
}
