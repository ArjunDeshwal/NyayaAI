import 'package:flutter/material.dart';

import '../../app/theme.dart';

/// Marketing-grade hero. Shown above the audit form on the home page.
///
/// Three responsive zones:
///   1. Bilingual headline + sub-headline + primary CTA chip strip.
///   2. Three-stat row: 1.4B addressable / ~70s audit / 152 tests passing.
///   3. "How it works" — three illustrated steps that map 1:1 to the
///      Planner / Fairness Engine / Narrator triple in the agent timeline.
///
/// The hero accepts a `scrollToFormCallback` so the primary CTA can scroll
/// the form into view without leaving the route.
class HeroSection extends StatelessWidget {
  const HeroSection({
    super.key,
    required this.onPrimaryCtaTap,
    required this.onTryDemoTap,
  });

  /// Smoothly scrolls the form into view (parent owns the ScrollController).
  final VoidCallback onPrimaryCtaTap;

  /// Triggers a one-tap MUDRA-Lite sample audit.
  final VoidCallback onTryDemoTap;

  @override
  Widget build(BuildContext context) {
    final isWide = MediaQuery.sizeOf(context).width >= 720;

    return Semantics(
      container: true,
      header: true,
      child: Container(
        width: double.infinity,
        decoration: BoxDecoration(
          gradient: LinearGradient(
            begin: Alignment.topLeft,
            end: Alignment.bottomRight,
            colors: [
              NyayaColors.navy.withValues(alpha: 0.04),
              NyayaColors.saffron.withValues(alpha: 0.06),
              NyayaColors.green.withValues(alpha: 0.04),
            ],
          ),
          border: const Border(
            bottom: BorderSide(color: NyayaColors.border),
          ),
        ),
        padding: EdgeInsets.fromLTRB(
          isWide ? 56 : 24,
          isWide ? 56 : 36,
          isWide ? 56 : 24,
          isWide ? 48 : 32,
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Top brand row: tri-colour wordmark, GSC + SDG chips on the right.
            _BrandRow(isWide: isWide),
            SizedBox(height: isWide ? 32 : 24),

            // Bilingual headline + sub-line.
            ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 760),
              child: _Headline(isWide: isWide),
            ),
            const SizedBox(height: 20),

            // CTA row.
            _CtaRow(
              isWide: isWide,
              onPrimaryTap: onPrimaryCtaTap,
              onDemoTap: onTryDemoTap,
            ),
            SizedBox(height: isWide ? 40 : 28),

            // Stat strip.
            _StatStrip(isWide: isWide),
            SizedBox(height: isWide ? 36 : 28),

            // How-it-works row.
            _HowItWorks(isWide: isWide),
          ],
        ),
      ),
    );
  }
}

class _BrandRow extends StatelessWidget {
  const _BrandRow({required this.isWide});

  final bool isWide;

  @override
  Widget build(BuildContext context) {
    final wordmark = MergeSemantics(
      child: Semantics(
        label: 'NyayaAI, Nyaya A I, bias auditor',
        child: const _TriColourWordmark(size: 30),
      ),
    );

    const chipBar = Wrap(
      spacing: 8,
      runSpacing: 8,
      alignment: WrapAlignment.end,
      children: [
        _SmallChip(
          icon: Icons.flag_outlined,
          label: 'GSC 2026',
          fg: NyayaColors.navy,
          bg: Color(0xFFE0E7FF),
        ),
        _SmallChip(
          icon: Icons.public,
          label: 'SDG 10.3',
          fg: NyayaColors.green,
          bg: Color(0xFFD1FAE5),
        ),
        _SmallChip(
          icon: Icons.balance_outlined,
          label: 'Apache-2.0',
          fg: NyayaColors.muted,
          bg: Color(0xFFF3F4F6),
        ),
      ],
    );

    if (isWide) {
      return Row(
        children: [
          wordmark,
          const Spacer(),
          chipBar,
        ],
      );
    }
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        wordmark,
        const SizedBox(height: 12),
        chipBar,
      ],
    );
  }
}

class _TriColourWordmark extends StatelessWidget {
  const _TriColourWordmark({required this.size});

  final double size;

  @override
  Widget build(BuildContext context) {
    return RichText(
      text: TextSpan(
        style: TextStyle(
          fontSize: size,
          fontWeight: FontWeight.w800,
          letterSpacing: -0.5,
          height: 1.0,
        ),
        children: <InlineSpan>[
          const TextSpan(
            text: 'N',
            style: TextStyle(color: NyayaColors.saffron),
          ),
          const TextSpan(
            text: 'yaya',
            style: TextStyle(color: NyayaColors.navy),
          ),
          const TextSpan(
            text: 'A',
            style: TextStyle(color: NyayaColors.green),
          ),
          const TextSpan(
            text: 'I',
            style: TextStyle(color: NyayaColors.navy),
          ),
          TextSpan(
            text: '   न्याय AI',
            style: TextStyle(
              color: NyayaColors.ink,
              fontSize: size - 4,
              fontWeight: FontWeight.w600,
            ),
          ),
        ],
      ),
    );
  }
}

class _Headline extends StatelessWidget {
  const _Headline({required this.isWide});
  final bool isWide;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          'Audit AI bias for India\nin under 70 seconds.',
          style: TextStyle(
            fontSize: isWide ? 44 : 32,
            fontWeight: FontWeight.w800,
            color: NyayaColors.ink,
            letterSpacing: -1.0,
            height: 1.1,
          ),
        ),
        const SizedBox(height: 14),
        Text(
          'Seven Gemini-powered agents run a regulator-ready fairness audit '
          'against your dataset — caste, religion, gender, mother-tongue, '
          'rural/urban — and emit a DPDP Rule 13 + EU AI Act audit report in '
          'English and Hindi.',
          style: TextStyle(
            fontSize: isWide ? 17 : 15,
            color: NyayaColors.ink,
            height: 1.55,
            letterSpacing: 0.1,
          ),
        ),
        const SizedBox(height: 8),
        Semantics(
          label: 'Justice for every algorithm. Hindi.',
          child: Text(
            'हर एल्गोरिदम के लिए न्याय।',
            style: TextStyle(
              fontSize: isWide ? 17 : 15,
              color: NyayaColors.muted,
              height: 1.6,
            ),
          ),
        ),
      ],
    );
  }
}

class _CtaRow extends StatelessWidget {
  const _CtaRow({
    required this.isWide,
    required this.onPrimaryTap,
    required this.onDemoTap,
  });

  final bool isWide;
  final VoidCallback onPrimaryTap;
  final VoidCallback onDemoTap;

  @override
  Widget build(BuildContext context) {
    return Wrap(
      spacing: 12,
      runSpacing: 12,
      crossAxisAlignment: WrapCrossAlignment.center,
      children: [
        Semantics(
          button: true,
          label: 'Run an audit. Scrolls down to the audit form.',
          child: FilledButton.icon(
            onPressed: onPrimaryTap,
            icon: const Icon(Icons.play_arrow),
            label: const Padding(
              padding: EdgeInsets.symmetric(horizontal: 4, vertical: 2),
              child: Text(
                'Run an audit',
                style: TextStyle(fontSize: 15, fontWeight: FontWeight.w700),
              ),
            ),
          ),
        ),
        Semantics(
          button: true,
          label:
              'One-tap MUDRA-Lite demo. Submits a real audit against the bundled Indian micro-loan dataset.',
          child: OutlinedButton.icon(
            onPressed: onDemoTap,
            icon: const Icon(Icons.bolt_outlined),
            label: const Padding(
              padding: EdgeInsets.symmetric(horizontal: 4, vertical: 2),
              child: Text(
                'Try the MUDRA-Lite demo',
                style: TextStyle(fontSize: 15, fontWeight: FontWeight.w700),
              ),
            ),
          ),
        ),
        const _TrustBadge(),
      ],
    );
  }
}

class _TrustBadge extends StatelessWidget {
  const _TrustBadge();

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
      decoration: BoxDecoration(
        color: NyayaColors.card,
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: NyayaColors.border),
      ),
      child: const Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(
            Icons.lock_outline,
            size: 14,
            color: NyayaColors.muted,
          ),
          SizedBox(width: 6),
          Text(
            'Model Armor + Sensitive Data Protection',
            style: TextStyle(
              fontSize: 12,
              color: NyayaColors.muted,
              fontWeight: FontWeight.w600,
            ),
          ),
        ],
      ),
    );
  }
}

class _StatStrip extends StatelessWidget {
  const _StatStrip({required this.isWide});

  final bool isWide;

  @override
  Widget build(BuildContext context) {
    const stats = [
      _Stat(
        value: '1.4 B',
        unit: 'Indians',
        caption: 'on Digital Public Infrastructure',
        color: NyayaColors.saffron,
      ),
      _Stat(
        value: '~70 s',
        unit: 'end-to-end',
        caption: 'replaces a 2-week audit',
        color: NyayaColors.navy,
      ),
      _Stat(
        value: '0.424',
        unit: '→ 0.719',
        caption: 'live MUDRA-Lite remediation',
        color: NyayaColors.green,
      ),
      _Stat(
        value: '152',
        unit: 'tests passing',
        caption: 'Apache-2.0 · 7 ADK agents',
        color: NyayaColors.muted,
      ),
    ];
    if (isWide) {
      return Row(
        children: [
          for (var i = 0; i < stats.length; i++) ...[
            Expanded(child: stats[i]),
            if (i < stats.length - 1) const SizedBox(width: 12),
          ],
        ],
      );
    }
    return Wrap(
      spacing: 12,
      runSpacing: 12,
      children: [
        for (final s in stats)
          SizedBox(
            width: (MediaQuery.sizeOf(context).width - 60) / 2,
            child: s,
          ),
      ],
    );
  }
}

class _Stat extends StatelessWidget {
  const _Stat({
    required this.value,
    required this.unit,
    required this.caption,
    required this.color,
  });

  final String value;
  final String unit;
  final String caption;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return Semantics(
      container: true,
      label: '$value $unit. $caption.',
      child: Container(
        padding: const EdgeInsets.fromLTRB(16, 14, 16, 14),
        decoration: BoxDecoration(
          color: NyayaColors.card,
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: NyayaColors.border),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Container(
              width: 24,
              height: 3,
              decoration: BoxDecoration(
                color: color,
                borderRadius: BorderRadius.circular(2),
              ),
            ),
            const SizedBox(height: 10),
            ExcludeSemantics(
              child: RichText(
                text: TextSpan(
                  style: const TextStyle(
                    fontSize: 26,
                    fontWeight: FontWeight.w800,
                    color: NyayaColors.ink,
                    letterSpacing: -0.6,
                    height: 1.0,
                  ),
                  children: [
                    TextSpan(text: value),
                    TextSpan(
                      text: '  $unit',
                      style: TextStyle(
                        fontSize: 13,
                        fontWeight: FontWeight.w700,
                        color: color,
                        letterSpacing: 0.2,
                      ),
                    ),
                  ],
                ),
              ),
            ),
            const SizedBox(height: 6),
            ExcludeSemantics(
              child: Text(
                caption,
                style: const TextStyle(
                  fontSize: 12,
                  color: NyayaColors.muted,
                  height: 1.35,
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _HowItWorks extends StatelessWidget {
  const _HowItWorks({required this.isWide});

  final bool isWide;

  @override
  Widget build(BuildContext context) {
    const steps = [
      _Step(
        number: 1,
        icon: Icons.auto_awesome_outlined,
        title: 'Plan',
        copy: 'Gemini 3.1 Pro reads your schema, picks fairness slices, and '
            'maps the right regulatory regime — DPDP, EU AI Act, or RBI.',
      ),
      _Step(
        number: 2,
        icon: Icons.balance_outlined,
        title: 'Audit',
        copy: 'Classical Fairlearn computes demographic parity, equal '
            'opportunity, and India-specific metrics (SPLS · LRB · DLF). '
            'Counterfactual flips and root-cause attribution name the proxies.',
      ),
      _Step(
        number: 3,
        icon: Icons.menu_book_outlined,
        title: 'Narrate · Remediate',
        copy: 'Gemini 3 Flash narrates findings in English + Hindi. When the '
            '4/5ths rule fails, Fairlearn ExponentiatedGradient retrains and '
            'opens a remediation report.',
      ),
    ];

    if (isWide) {
      return Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          for (var i = 0; i < steps.length; i++) ...[
            Expanded(child: steps[i]),
            if (i < steps.length - 1)
              const Padding(
                padding: EdgeInsets.symmetric(horizontal: 8, vertical: 24),
                child: Icon(
                  Icons.arrow_forward,
                  size: 22,
                  color: NyayaColors.muted,
                ),
              ),
          ],
        ],
      );
    }
    return Column(
      children: [
        for (var i = 0; i < steps.length; i++) ...[
          steps[i],
          if (i < steps.length - 1)
            const Padding(
              padding: EdgeInsets.symmetric(vertical: 4),
              child: Icon(
                Icons.arrow_downward,
                size: 22,
                color: NyayaColors.muted,
              ),
            ),
        ],
      ],
    );
  }
}

class _Step extends StatelessWidget {
  const _Step({
    required this.number,
    required this.icon,
    required this.title,
    required this.copy,
  });

  final int number;
  final IconData icon;
  final String title;
  final String copy;

  @override
  Widget build(BuildContext context) {
    return Semantics(
      container: true,
      label: 'Step $number. $title. $copy',
      child: Container(
        padding: const EdgeInsets.all(16),
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
                Container(
                  width: 28,
                  height: 28,
                  decoration: const BoxDecoration(
                    shape: BoxShape.circle,
                    color: NyayaColors.navy,
                  ),
                  child: Center(
                    child: ExcludeSemantics(
                      child: Text(
                        '$number',
                        style: const TextStyle(
                          color: Colors.white,
                          fontSize: 14,
                          fontWeight: FontWeight.w800,
                        ),
                      ),
                    ),
                  ),
                ),
                const SizedBox(width: 10),
                Icon(icon, size: 22, color: NyayaColors.navy),
                const SizedBox(width: 8),
                Text(
                  title,
                  style: const TextStyle(
                    fontSize: 16,
                    fontWeight: FontWeight.w700,
                    color: NyayaColors.ink,
                    letterSpacing: -0.2,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 10),
            Text(
              copy,
              style: const TextStyle(
                fontSize: 13,
                color: NyayaColors.muted,
                height: 1.5,
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _SmallChip extends StatelessWidget {
  const _SmallChip({
    required this.icon,
    required this.label,
    required this.fg,
    required this.bg,
  });

  final IconData icon;
  final String label;
  final Color fg;
  final Color bg;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
      decoration: BoxDecoration(
        color: bg,
        borderRadius: BorderRadius.circular(20),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(icon, size: 14, color: fg),
          const SizedBox(width: 6),
          Text(
            label,
            style: TextStyle(
              fontSize: 12,
              color: fg,
              fontWeight: FontWeight.w700,
              letterSpacing: 0.3,
            ),
          ),
        ],
      ),
    );
  }
}
