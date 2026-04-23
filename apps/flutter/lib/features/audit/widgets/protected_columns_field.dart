import 'package:flutter/material.dart';

/// Comma-separated protected-column entry.
///
/// The wire format (per `services/api/.../app.py`) is a comma-separated
/// string. We keep the UI as a single text field to match that contract
/// and help the user paste column names directly.
class ProtectedColumnsField extends StatelessWidget {
  const ProtectedColumnsField({
    super.key,
    required this.controller,
    this.enabled = true,
  });

  final TextEditingController controller;
  final bool enabled;

  String? _validate(String? raw) {
    final trimmed = raw?.trim() ?? '';
    if (trimmed.isEmpty) {
      return 'Enter at least one protected column (e.g. gender, caste, religion).';
    }
    final parts = trimmed
        .split(',')
        .map((s) => s.trim())
        .where((s) => s.isNotEmpty)
        .toList();
    if (parts.isEmpty) {
      return 'Protected columns must be comma-separated, non-empty values.';
    }
    for (final p in parts) {
      if (p.length > 64) {
        return 'Column name "$p" is too long (max 64 chars).';
      }
    }
    return null;
  }

  @override
  Widget build(BuildContext context) {
    return Semantics(
      textField: true,
      label:
          'Protected columns. Comma-separated column names whose fairness will be audited.',
      child: TextFormField(
        controller: controller,
        enabled: enabled,
        autocorrect: false,
        textInputAction: TextInputAction.next,
        decoration: const InputDecoration(
          labelText: 'Protected columns',
          hintText: 'e.g. gender, caste, religion, state',
          helperText: 'Comma-separated. These columns will be audited for bias.',
          prefixIcon: Icon(Icons.shield_outlined),
        ),
        validator: _validate,
      ),
    );
  }
}
