import 'dart:typed_data';

import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';

import '../../../app/theme.dart';

class PickedFile {
  const PickedFile({required this.bytes, required this.name, required this.size});
  final Uint8List bytes;
  final String name;
  final int size;
}

/// Accessible file picker.
///
/// Design notes:
///   - The whole zone is a focusable button with a clear `Semantics` label.
///   - A secondary "Choose file" button is present for keyboard users so the
///     flow never relies on drag-and-drop alone (WCAG 2.5.7 doesn't mandate
///     drag-free equivalents until 2.2, but we ship it regardless).
///   - On pick, we store bytes in memory — no path-on-disk (web has none).
class FileDropZone extends StatelessWidget {
  const FileDropZone({
    super.key,
    required this.onPicked,
    required this.picked,
    this.enabled = true,
  });

  final void Function(PickedFile) onPicked;
  final PickedFile? picked;
  final bool enabled;

  Future<void> _pick() async {
    final result = await FilePicker.platform.pickFiles(
      type: FileType.custom,
      allowedExtensions: const ['csv', 'tsv', 'parquet'],
      withData: true,
      allowMultiple: false,
    );
    if (result == null || result.files.isEmpty) return;
    final f = result.files.single;
    final bytes = f.bytes;
    if (bytes == null) return;
    onPicked(PickedFile(bytes: bytes, name: f.name, size: f.size));
  }

  @override
  Widget build(BuildContext context) {
    final hasFile = picked != null;
    final label = hasFile
        ? 'Selected file: ${picked!.name}, ${_fmtSize(picked!.size)}. Activate to replace.'
        : 'Choose a dataset file. CSV, TSV, or Parquet. Required.';

    return Semantics(
      button: true,
      enabled: enabled,
      label: label,
      child: InkWell(
        onTap: enabled ? _pick : null,
        borderRadius: BorderRadius.circular(12),
        child: Container(
          width: double.infinity,
          padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 28),
          decoration: BoxDecoration(
            color: hasFile
                ? NyayaColors.green.withValues(alpha: 0.05)
                : NyayaColors.card,
            borderRadius: BorderRadius.circular(12),
            border: Border.all(
              color: hasFile ? NyayaColors.green : NyayaColors.border,
              width: hasFile ? 2 : 1.5,
              style: BorderStyle.solid,
            ),
          ),
          child: Row(
            children: [
              Icon(
                hasFile ? Icons.description_outlined : Icons.upload_file,
                size: 32,
                color: hasFile ? NyayaColors.green : NyayaColors.navy,
              ),
              const SizedBox(width: 16),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    ExcludeSemantics(
                      child: Text(
                        hasFile ? picked!.name : 'Drop a CSV / Parquet here',
                        style: const TextStyle(
                          fontSize: 16,
                          fontWeight: FontWeight.w600,
                          color: NyayaColors.ink,
                        ),
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                      ),
                    ),
                    const SizedBox(height: 4),
                    ExcludeSemantics(
                      child: Text(
                        hasFile
                            ? _fmtSize(picked!.size)
                            : 'or click anywhere in this box to browse. '
                                'Accepted: .csv, .tsv, .parquet (max 50MB).',
                        style: const TextStyle(color: NyayaColors.muted, fontSize: 13),
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(width: 12),
              OutlinedButton.icon(
                onPressed: enabled ? _pick : null,
                icon: const Icon(Icons.folder_open, size: 18),
                label: Text(hasFile ? 'Replace' : 'Choose file'),
              ),
            ],
          ),
        ),
      ),
    );
  }

  static String _fmtSize(int bytes) {
    if (bytes < 1024) return '$bytes B';
    if (bytes < 1024 * 1024) return '${(bytes / 1024).toStringAsFixed(1)} KB';
    return '${(bytes / (1024 * 1024)).toStringAsFixed(1)} MB';
  }
}
