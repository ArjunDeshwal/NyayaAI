import 'package:flutter/material.dart';

import '../../app/theme.dart';

/// Plain-language disclaimer so judges (and auditees) see the scope.
class DisclaimerFooter extends StatelessWidget {
  const DisclaimerFooter({super.key});

  @override
  Widget build(BuildContext context) {
    return Semantics(
      container: true,
      label: 'Disclaimer',
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 20),
        decoration: const BoxDecoration(
          border: Border(top: BorderSide(color: NyayaColors.border)),
        ),
        child: DefaultTextStyle.merge(
          style: const TextStyle(color: NyayaColors.muted, fontSize: 12, height: 1.5),
          child: const Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                'NyayaAI is a prototype built for Google Solution Challenge 2026. '
                'Reports are statistical audits, not legal advice. Human review by a '
                'qualified fairness / legal expert is required before any decision that '
                'affects individuals is made.',
              ),
              SizedBox(height: 6),
              Text(
                'Team attribution: NyayaAI — four-person team. Apache-2.0 licensed.',
              ),
            ],
          ),
        ),
      ),
    );
  }
}
