import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../app/theme.dart';
import '../../../shared/api/api_client.dart';
import '../../../shared/api/sample_dataset.dart';

/// Provider that fetches `GET /samples` once and caches the result.
final sampleCatalogProvider = FutureProvider<List<SampleDataset>>((ref) async {
  final api = ref.watch(apiClientProvider);
  return api.fetchSamples();
});

/// Region-coded preset chip.
///
/// India presets get a saffron tint; USA presets get a navy tint. The chip is
/// fully keyboard-accessible: tab focuses it, Enter / Space activates it. We
/// expose a single canonical `Semantics(button: true, ...)` per chip.
class SampleChip extends StatelessWidget {
  const SampleChip({
    super.key,
    required this.dataset,
    required this.selected,
    required this.onTap,
  });

  final SampleDataset dataset;
  final bool selected;
  final VoidCallback onTap;

  ({Color tint, Color border, Color fg}) _palette() {
    final isIndia = dataset.region.toLowerCase().contains('india');
    if (isIndia) {
      return (
        tint: NyayaColors.saffron.withValues(alpha: 0.18),
        border: NyayaColors.saffron,
        fg: NyayaColors.ink,
      );
    }
    // USA + default fallback.
    return (
      tint: NyayaColors.navy.withValues(alpha: 0.10),
      border: NyayaColors.navy,
      fg: NyayaColors.ink,
    );
  }

  @override
  Widget build(BuildContext context) {
    final palette = _palette();
    final ds = dataset;
    final selectedLabel = selected ? ' Selected.' : '';

    return Semantics(
      button: true,
      selected: selected,
      label: '${ds.name}. ${ds.region}. ${ds.rowCount} rows.$selectedLabel '
          'Activate to prefill the audit form with this preset.',
      child: Focus(
        canRequestFocus: true,
        child: Builder(
          builder: (context) {
            final hasFocus = Focus.of(context).hasFocus;
            return InkWell(
              onTap: onTap,
              borderRadius: BorderRadius.circular(20),
              child: Container(
                constraints: const BoxConstraints(minHeight: 48),
                padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
                decoration: BoxDecoration(
                  color: selected ? palette.tint : NyayaColors.card,
                  borderRadius: BorderRadius.circular(20),
                  border: Border.all(
                    color: hasFocus
                        ? NyayaColors.saffron
                        : (selected ? palette.border : NyayaColors.border),
                    width: hasFocus ? 3 : (selected ? 2 : 1.2),
                  ),
                ),
                child: Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Container(
                      width: 8,
                      height: 8,
                      decoration: BoxDecoration(
                        shape: BoxShape.circle,
                        color: palette.border,
                      ),
                    ),
                    const SizedBox(width: 8),
                    Flexible(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          Text(
                            ds.name,
                            style: TextStyle(
                              color: palette.fg,
                              fontSize: 13,
                              fontWeight: FontWeight.w600,
                              letterSpacing: 0.1,
                            ),
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                          ),
                          Text(
                            '${ds.region} · ${ds.rowCount} rows',
                            style: const TextStyle(
                              color: NyayaColors.muted,
                              fontSize: 11,
                              height: 1.2,
                            ),
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                          ),
                        ],
                      ),
                    ),
                    if (selected) ...[
                      const SizedBox(width: 8),
                      Icon(
                        Icons.check_circle,
                        size: 18,
                        color: palette.border,
                      ),
                    ],
                  ],
                ),
              ),
            );
          },
        ),
      ),
    );
  }
}

/// Horizontal row of preset chips, rendered above the upload form.
///
/// Tapping a chip calls [onSelected] with the chosen [SampleDataset]. The
/// parent screen is responsible for prefilling form controllers and toggling
/// the submission flow to `/audit/sample(-stream)`.
class SampleChipRow extends ConsumerWidget {
  const SampleChipRow({
    super.key,
    required this.selectedSampleId,
    required this.onSelected,
    required this.onCleared,
  });

  /// Currently-selected preset id, or null if no preset is active.
  final String? selectedSampleId;

  /// Called when the user taps a preset chip.
  final ValueChanged<SampleDataset> onSelected;

  /// Called when the user clears the active preset (e.g. by tapping the
  /// already-selected chip again).
  final VoidCallback onCleared;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final asyncSamples = ref.watch(sampleCatalogProvider);

    return Semantics(
      container: true,
      label: 'Bundled sample datasets — keyboard-accessible preset chips.',
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const Icon(
                Icons.dataset_outlined,
                size: 18,
                color: NyayaColors.navy,
              ),
              const SizedBox(width: 6),
              Text(
                'Try a bundled dataset',
                style: Theme.of(context)
                    .textTheme
                    .titleLarge
                    ?.copyWith(fontSize: 15),
              ),
            ],
          ),
          const SizedBox(height: 4),
          const Text(
            'Skip the upload — load a preset, then press Run audit.',
            style: TextStyle(color: NyayaColors.muted, fontSize: 13),
          ),
          const SizedBox(height: 12),
          asyncSamples.when(
            loading: () => const Padding(
              padding: EdgeInsets.symmetric(vertical: 8),
              child: Row(
                children: [
                  SizedBox(
                    width: 16,
                    height: 16,
                    child: CircularProgressIndicator(strokeWidth: 2),
                  ),
                  SizedBox(width: 10),
                  Text(
                    'Loading sample catalog…',
                    style: TextStyle(color: NyayaColors.muted, fontSize: 13),
                  ),
                ],
              ),
            ),
            error: (e, _) => Padding(
              padding: const EdgeInsets.symmetric(vertical: 8),
              child: Text(
                'Sample catalog unavailable: $e',
                style: const TextStyle(color: NyayaColors.muted, fontSize: 12),
              ),
            ),
            data: (samples) => FocusTraversalGroup(
              policy: ReadingOrderTraversalPolicy(),
              child: Wrap(
                spacing: 10,
                runSpacing: 10,
                children: [
                  for (final ds in samples)
                    Shortcuts(
                      shortcuts: const <ShortcutActivator, Intent>{
                        SingleActivator(LogicalKeyboardKey.enter):
                            ActivateIntent(),
                        SingleActivator(LogicalKeyboardKey.space):
                            ActivateIntent(),
                      },
                      child: Actions(
                        actions: <Type, Action<Intent>>{
                          ActivateIntent: CallbackAction<ActivateIntent>(
                            onInvoke: (_) {
                              _activate(ds);
                              return null;
                            },
                          ),
                        },
                        child: SampleChip(
                          dataset: ds,
                          selected: selectedSampleId == ds.id,
                          onTap: () => _activate(ds),
                        ),
                      ),
                    ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }

  void _activate(SampleDataset ds) {
    if (selectedSampleId == ds.id) {
      onCleared();
    } else {
      onSelected(ds);
    }
  }
}
