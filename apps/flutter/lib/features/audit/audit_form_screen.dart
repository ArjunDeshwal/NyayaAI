import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:nyayai_contracts/nyayai_contracts.dart';

import '../../app/theme.dart';
import '../../shared/api/api_client.dart';
import '../../shared/api/sample_dataset.dart';
import '../../shared/widgets/disclaimer_footer.dart';
import '../landing/landing_banner.dart';
import 'audit_form_controller.dart';
import 'audit_form_state.dart';
import 'audit_result_view.dart';
import 'regime_hints.dart';
import 'widgets/agent_timeline.dart';
import 'widgets/file_drop_zone.dart';
import 'widgets/protected_columns_field.dart';
import 'widgets/regime_selector.dart';
import 'widgets/sample_chip_row.dart';

class AuditFormScreen extends ConsumerStatefulWidget {
  const AuditFormScreen({super.key});

  @override
  ConsumerState<AuditFormScreen> createState() => _AuditFormScreenState();
}

class _AuditFormScreenState extends ConsumerState<AuditFormScreen> {
  final _formKey = GlobalKey<FormState>();
  final _datasetNameCtrl = TextEditingController();
  final _goalCtrl = TextEditingController();
  final _protectedCtrl = TextEditingController();
  final _outcomeCtrl = TextEditingController();
  final _scoreCtrl = TextEditingController();

  Regime _regime = Regime.dpdp;
  PickedFile? _picked;
  String? _fileError;

  /// When non-null, submission flows through `/audit/sample(-stream)` and the
  /// file picker is disabled.
  SampleDataset? _selectedSample;

  @override
  void dispose() {
    _datasetNameCtrl.dispose();
    _goalCtrl.dispose();
    _protectedCtrl.dispose();
    _outcomeCtrl.dispose();
    _scoreCtrl.dispose();
    super.dispose();
  }

  void _onPicked(PickedFile f) {
    setState(() {
      _picked = f;
      _fileError = null;
    });
  }

  /// Map a server-side regime wire string ("DPDP", "EU_AI_ACT", "RBI") to the
  /// Dart `Regime` enum.
  Regime _regimeFromWire(String wire) {
    return switch (wire) {
      'EU_AI_ACT' => Regime.euAiAct,
      'RBI' => Regime.rbi,
      _ => Regime.dpdp,
    };
  }

  void _onSampleSelected(SampleDataset ds) {
    setState(() {
      _selectedSample = ds;
      _datasetNameCtrl.text = ds.name;
      _goalCtrl.text = ds.defaultGoal;
      _protectedCtrl.text = ds.protectedColumns.join(', ');
      _outcomeCtrl.text = ds.outcomeColumn;
      _scoreCtrl.text = ds.modelScoreColumn ?? '';
      _regime = _regimeFromWire(ds.defaultRegime);
      _fileError = null;
      // The bundled dataset replaces the upload — drop any picked file.
      _picked = null;
    });
  }

  void _onSampleCleared() {
    setState(() => _selectedSample = null);
  }

  Future<void> _submit() async {
    final formOk = _formKey.currentState?.validate() ?? false;

    // Sample path — no file required.
    if (_selectedSample != null) {
      if (!formOk) return;
      await ref.read(auditFormControllerProvider.notifier).submitSample(
            AuditSampleRequest(
              sampleId: _selectedSample!.id,
              goal: _goalCtrl.text.trim(),
              regime: _regime,
            ),
            datasetLabel: _selectedSample!.name,
          );
      return;
    }

    // Upload path — file is mandatory.
    final fileOk = _picked != null;
    if (!fileOk) {
      setState(() => _fileError = 'Please choose a dataset file.');
    }
    if (!fileOk || !formOk) return;

    final protected = _protectedCtrl.text
        .split(',')
        .map((s) => s.trim())
        .where((s) => s.isNotEmpty)
        .toList();

    final req = AuditUploadRequest(
      datasetName: _datasetNameCtrl.text.trim(),
      goal: _goalCtrl.text.trim(),
      protectedColumns: protected,
      outcomeColumn: _outcomeCtrl.text.trim(),
      regime: _regime,
      modelScoreColumn:
          _scoreCtrl.text.trim().isEmpty ? null : _scoreCtrl.text.trim(),
      fileBytes: _picked!.bytes,
      filename: _picked!.name,
    );

    await ref.read(auditFormControllerProvider.notifier).submitUpload(req);
  }

  @override
  Widget build(BuildContext context) {
    final state = ref.watch(auditFormControllerProvider);
    final submitting = state.isSubmitting;

    return Scaffold(
      body: FocusTraversalGroup(
        policy: ReadingOrderTraversalPolicy(),
        child: SafeArea(
          child: Center(
            child: SingleChildScrollView(
              child: ConstrainedBox(
                constraints: const BoxConstraints(maxWidth: 960),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    const _TopBar(),
                    const LandingBanner(),
                    Padding(
                      padding: const EdgeInsets.fromLTRB(40, 32, 40, 24),
                      child: _buildFormCard(state, submitting),
                    ),
                    if (state.timeline != null && !state.hasResult)
                      Padding(
                        padding: const EdgeInsets.fromLTRB(40, 0, 40, 24),
                        child: AnimatedSwitcher(
                          duration: const Duration(milliseconds: 300),
                          child: AgentTimeline(
                            key: ValueKey<bool>(state.hasError),
                            timeline: state.timeline!,
                            errorMessage:
                                state.hasError ? state.errorMessage : null,
                          ),
                        ),
                      ),
                    if (state.hasResult)
                      Padding(
                        padding: const EdgeInsets.fromLTRB(40, 0, 40, 32),
                        child: AuditResultView(response: state.response!),
                      ),
                    const DisclaimerFooter(),
                  ],
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildFormCard(AuditFormState state, bool submitting) {
    final hint = RegimeHint.forRegime(_regime);
    final usingSample = _selectedSample != null;

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(28),
        child: Form(
          key: _formKey,
          autovalidateMode: AutovalidateMode.onUserInteraction,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Semantics(
                header: true,
                child: Text(
                  'Run an audit',
                  style: Theme.of(context).textTheme.headlineMedium,
                ),
              ),
              const SizedBox(height: 4),
              const Text(
                'Upload a dataset (CSV or Parquet), name the protected columns, '
                'and NyayaAI will run three agents — fairness, drift, and '
                'narrative — then render a regulator-ready audit report.',
                style: TextStyle(color: NyayaColors.muted, fontSize: 14),
              ),
              const SizedBox(height: 20),

              // Feature A — bundled-dataset preset chips.
              SampleChipRow(
                selectedSampleId: _selectedSample?.id,
                onSelected: submitting ? (_) {} : _onSampleSelected,
                onCleared: submitting ? () {} : _onSampleCleared,
              ),
              const SizedBox(height: 20),

              if (usingSample)
                _BundledPill(label: _selectedSample!.name)
              else
                FileDropZone(
                  picked: _picked,
                  enabled: !submitting,
                  onPicked: _onPicked,
                ),
              if (_fileError != null && !usingSample) ...[
                const SizedBox(height: 8),
                Semantics(
                  liveRegion: true,
                  child: Text(
                    _fileError!,
                    style: const TextStyle(color: NyayaColors.fail, fontSize: 13),
                  ),
                ),
              ],
              const SizedBox(height: 20),

              TextFormField(
                controller: _datasetNameCtrl,
                enabled: !submitting,
                textInputAction: TextInputAction.next,
                decoration: const InputDecoration(
                  labelText: 'Dataset name',
                  hintText: 'e.g. maharashtra-ration-card-2025-Q4',
                  prefixIcon: Icon(Icons.label_outline),
                ),
                validator: (v) {
                  final t = v?.trim() ?? '';
                  if (t.isEmpty) return 'Dataset name is required.';
                  if (t.length > 200) return 'Max 200 characters.';
                  return null;
                },
              ),
              const SizedBox(height: 16),

              // Feature E — placeholder + helper text follow the regime.
              TextFormField(
                controller: _goalCtrl,
                enabled: !submitting,
                minLines: 3,
                maxLines: 6,
                maxLength: 2000,
                decoration: InputDecoration(
                  labelText: 'Audit goal',
                  hintText: hint.placeholder,
                  helperText: hint.helper,
                  helperMaxLines: 3,
                  prefixIcon: const Icon(Icons.flag_outlined),
                ),
                validator: (v) {
                  final t = v?.trim() ?? '';
                  if (t.length < 5) return 'Please describe the audit goal (min 5 chars).';
                  return null;
                },
              ),
              const SizedBox(height: 16),

              ProtectedColumnsField(
                controller: _protectedCtrl,
                enabled: !submitting,
              ),
              const SizedBox(height: 16),

              TextFormField(
                controller: _outcomeCtrl,
                enabled: !submitting,
                textInputAction: TextInputAction.next,
                decoration: const InputDecoration(
                  labelText: 'Outcome column',
                  hintText: 'e.g. approved, loan_sanctioned',
                  prefixIcon: Icon(Icons.check_box_outlined),
                ),
                validator: (v) {
                  final t = v?.trim() ?? '';
                  if (t.isEmpty) return 'Outcome column is required.';
                  return null;
                },
              ),
              const SizedBox(height: 16),

              TextFormField(
                controller: _scoreCtrl,
                enabled: !submitting,
                textInputAction: TextInputAction.next,
                decoration: const InputDecoration(
                  labelText: 'Model score column (optional)',
                  hintText: 'e.g. pred_score',
                  prefixIcon: Icon(Icons.query_stats_outlined),
                  helperText: 'Leave blank if you only have ground-truth outcomes.',
                ),
              ),
              const SizedBox(height: 16),

              RegimeSelector(
                value: _regime,
                onChanged: (r) => setState(() => _regime = r),
                enabled: !submitting,
              ),

              const SizedBox(height: 24),

              if (state.hasError)
                Semantics(
                  liveRegion: true,
                  container: true,
                  child: Container(
                    padding: const EdgeInsets.all(14),
                    margin: const EdgeInsets.only(bottom: 16),
                    decoration: BoxDecoration(
                      color: const Color(0xFFFEE2E2),
                      borderRadius: BorderRadius.circular(8),
                      border: Border.all(color: NyayaColors.fail),
                    ),
                    child: Row(
                      children: [
                        const Icon(Icons.error_outline, color: NyayaColors.fail),
                        const SizedBox(width: 10),
                        Expanded(
                          child: Text(
                            state.errorMessage ?? 'Submission failed.',
                            style: const TextStyle(color: NyayaColors.fail),
                          ),
                        ),
                      ],
                    ),
                  ),
                ),

              Row(
                children: [
                  Expanded(
                    child: Semantics(
                      button: true,
                      enabled: !submitting,
                      label: submitting
                          ? 'Running audit. Please wait.'
                          : 'Run audit.',
                      child: FilledButton.icon(
                        onPressed: submitting ? null : _submit,
                        icon: submitting
                            ? const SizedBox(
                                width: 18,
                                height: 18,
                                child: CircularProgressIndicator(
                                  strokeWidth: 2.5,
                                  valueColor:
                                      AlwaysStoppedAnimation<Color>(Colors.white),
                                ),
                              )
                            : const Icon(Icons.play_arrow),
                        label: Text(submitting ? 'Auditing…' : 'Run audit'),
                      ),
                    ),
                  ),
                  const SizedBox(width: 12),
                  Semantics(
                    button: true,
                    enabled: !submitting,
                    label: 'Reset the form.',
                    child: OutlinedButton(
                      onPressed: submitting
                          ? null
                          : () {
                              _formKey.currentState?.reset();
                              _datasetNameCtrl.clear();
                              _goalCtrl.clear();
                              _protectedCtrl.clear();
                              _outcomeCtrl.clear();
                              _scoreCtrl.clear();
                              setState(() {
                                _picked = null;
                                _fileError = null;
                                _regime = Regime.dpdp;
                                _selectedSample = null;
                              });
                              ref
                                  .read(auditFormControllerProvider.notifier)
                                  .reset();
                            },
                      child: const Text('Reset'),
                    ),
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }
}

/// Top bar with the History link (Feature F entry point).
class _TopBar extends StatelessWidget {
  const _TopBar();

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.fromLTRB(40, 12, 24, 12),
      decoration: const BoxDecoration(
        color: NyayaColors.card,
        border: Border(bottom: BorderSide(color: NyayaColors.border)),
      ),
      child: Row(
        children: [
          ExcludeSemantics(
            child: Text(
              'NyayaAI',
              style: Theme.of(context).textTheme.titleLarge?.copyWith(
                    color: NyayaColors.navy,
                    fontWeight: FontWeight.w800,
                    letterSpacing: -0.3,
                  ),
            ),
          ),
          const Spacer(),
          Semantics(
            button: true,
            label: 'View past audits stored in this browser.',
            child: TextButton.icon(
              onPressed: () => context.go('/history'),
              icon: const Icon(Icons.history, size: 18),
              label: const Text('History'),
            ),
          ),
        ],
      ),
    );
  }
}

/// Pill shown in place of the file-drop zone when a bundled preset is active.
class _BundledPill extends StatelessWidget {
  const _BundledPill({required this.label});

  final String label;

  @override
  Widget build(BuildContext context) {
    return Semantics(
      container: true,
      label: 'Using bundled dataset: $label. No upload required.',
      child: Container(
        width: double.infinity,
        padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 18),
        decoration: BoxDecoration(
          color: NyayaColors.saffron.withValues(alpha: 0.10),
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: NyayaColors.saffron, width: 2),
        ),
        child: Row(
          children: [
            const Icon(Icons.dataset, size: 24, color: NyayaColors.navy),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  ExcludeSemantics(
                    child: Text(
                      'Using bundled $label (no upload needed)',
                      style: const TextStyle(
                        fontSize: 15,
                        fontWeight: FontWeight.w700,
                        color: NyayaColors.ink,
                      ),
                    ),
                  ),
                  const SizedBox(height: 2),
                  const ExcludeSemantics(
                    child: Text(
                      'Submission will run on the server-side preset.',
                      style: TextStyle(
                        fontSize: 12,
                        color: NyayaColors.muted,
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}
