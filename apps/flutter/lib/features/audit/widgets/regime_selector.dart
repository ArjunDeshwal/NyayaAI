import 'package:flutter/material.dart';
import 'package:nyayai_contracts/nyayai_contracts.dart';

/// Regulatory-regime dropdown. Values map 1:1 to the server's `Regime` enum
/// via the `RegimeWire` extension in the contracts package.
class RegimeSelector extends StatelessWidget {
  const RegimeSelector({
    super.key,
    required this.value,
    required this.onChanged,
    this.enabled = true,
  });

  final Regime value;
  final ValueChanged<Regime> onChanged;
  final bool enabled;

  static const Map<Regime, ({String label, String hint})> _entries = {
    Regime.dpdp: (
      label: 'DPDP 2023 (India)',
      hint: 'Digital Personal Data Protection Act, India.',
    ),
    Regime.euAiAct: (
      label: 'EU AI Act',
      hint: 'European Union Artificial Intelligence Act.',
    ),
    Regime.rbi: (
      label: 'RBI guidance',
      hint: 'Reserve Bank of India — responsible AI in finance.',
    ),
  };

  @override
  Widget build(BuildContext context) {
    return Semantics(
      label:
          'Regulatory regime. Choose DPDP 2023, EU AI Act, or RBI guidance. Current value: ${_entries[value]!.label}.',
      child: DropdownButtonFormField<Regime>(
        value: value,
        onChanged: enabled
            ? (v) {
                if (v != null) onChanged(v);
              }
            : null,
        decoration: const InputDecoration(
          labelText: 'Regulatory regime',
          helperText: 'Frames the report against the chosen compliance lens.',
          prefixIcon: Icon(Icons.gavel_outlined),
        ),
        items: [
          for (final r in Regime.values)
            DropdownMenuItem<Regime>(
              value: r,
              child: Text(_entries[r]!.label),
            ),
        ],
      ),
    );
  }
}
