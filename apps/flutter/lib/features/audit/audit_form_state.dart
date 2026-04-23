import 'package:nyayai_contracts/nyayai_contracts.dart';

/// Machine states for the single audit form screen.
enum AuditStatus { idle, submitting, success, error }

class AuditFormState {
  const AuditFormState({
    this.status = AuditStatus.idle,
    this.response,
    this.errorMessage,
    this.progressHint,
  });

  final AuditStatus status;
  final AuditResponse? response;
  final String? errorMessage;

  /// Human-readable phase label shown alongside the spinner.
  final String? progressHint;

  bool get isSubmitting => status == AuditStatus.submitting;
  bool get hasError => status == AuditStatus.error;
  bool get hasResult => status == AuditStatus.success && response != null;

  AuditFormState copyWith({
    AuditStatus? status,
    AuditResponse? response,
    String? errorMessage,
    String? progressHint,
    bool clearError = false,
    bool clearResponse = false,
  }) {
    return AuditFormState(
      status: status ?? this.status,
      response: clearResponse ? null : (response ?? this.response),
      errorMessage: clearError ? null : (errorMessage ?? this.errorMessage),
      progressHint: progressHint ?? this.progressHint,
    );
  }
}
