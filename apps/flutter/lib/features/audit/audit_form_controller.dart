import 'dart:async';

import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../shared/api/api_client.dart';
import 'audit_form_state.dart';

class AuditFormController extends StateNotifier<AuditFormState> {
  AuditFormController(this._api) : super(const AuditFormState());

  final NyayaApiClient _api;
  Timer? _hintTicker;

  Future<void> submit(AuditUploadRequest request) async {
    if (state.isSubmitting) return;

    state = state.copyWith(
      status: AuditStatus.submitting,
      clearError: true,
      clearResponse: true,
      progressHint: 'Uploading dataset…',
    );

    // Rotate a small set of human-readable phase labels so the spinner feels
    // alive. The backend pipeline is: upload -> fairness agent -> drift agent
    // -> narrative agent -> report writer.
    const hints = <String>[
      'Uploading dataset…',
      'Running 3 agents: fairness, drift, narrative…',
      'Scoring subgroups against the 4/5ths rule…',
      'Writing regulator-ready report…',
    ];
    var i = 0;
    _hintTicker?.cancel();
    _hintTicker = Timer.periodic(const Duration(seconds: 4), (_) {
      i = (i + 1) % hints.length;
      if (state.isSubmitting) {
        state = state.copyWith(progressHint: hints[i]);
      }
    });

    try {
      final response = await _api.submitAudit(request);
      _hintTicker?.cancel();
      state = AuditFormState(
        status: AuditStatus.success,
        response: response,
      );
    } on AuditApiException catch (e) {
      _hintTicker?.cancel();
      state = AuditFormState(
        status: AuditStatus.error,
        errorMessage: e.message,
      );
    } catch (e) {
      _hintTicker?.cancel();
      state = AuditFormState(
        status: AuditStatus.error,
        errorMessage: 'Unexpected error: $e',
      );
    }
  }

  void reset() {
    _hintTicker?.cancel();
    state = const AuditFormState();
  }

  @override
  void dispose() {
    _hintTicker?.cancel();
    super.dispose();
  }
}

final auditFormControllerProvider =
    StateNotifierProvider<AuditFormController, AuditFormState>((ref) {
  return AuditFormController(ref.watch(apiClientProvider));
});
