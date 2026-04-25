import 'dart:convert';

import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'history_entry.dart';
import 'history_storage_io.dart'
    if (dart.library.html) 'history_storage_web.dart' as storage;

/// Browser-localStorage audit history (Feature F).
///
/// * Key: `nyayai.audit_history` (a JSON list).
/// * Cap: 20 entries, FIFO eviction (oldest dropped on overflow).
/// * Non-web platforms fall back to an in-memory list — the app is web-only
///   in production but this keeps unit tests portable.
class AuditHistoryRepository {
  AuditHistoryRepository();

  static const String storageKey = 'nyayai.audit_history';
  static const int maxEntries = 20;

  /// In-memory mirror used on non-web platforms (unit tests, mobile).
  final List<HistoryEntry> _memory = <HistoryEntry>[];

  /// Returns the current history, newest first.
  List<HistoryEntry> list() {
    final entries = _readAll();
    return List<HistoryEntry>.from(entries.reversed);
  }

  /// Inserts a new entry at the end (newest). Evicts oldest entries past
  /// [maxEntries].
  void add(HistoryEntry entry) {
    final entries = _readAll();
    // Drop any prior entry for the same audit_id (idempotent retries).
    entries.removeWhere((e) => e.auditId == entry.auditId);
    entries.add(entry);
    while (entries.length > maxEntries) {
      entries.removeAt(0);
    }
    _writeAll(entries);
  }

  void clear() {
    _memory.clear();
    if (kIsWeb) {
      storage.removeItem(storageKey);
    }
  }

  // ---------------------------------------------------------------------------
  // Internals.
  // ---------------------------------------------------------------------------

  List<HistoryEntry> _readAll() {
    if (!kIsWeb) {
      return List<HistoryEntry>.from(_memory);
    }
    try {
      final raw = storage.getItem(storageKey);
      if (raw == null || raw.isEmpty) return <HistoryEntry>[];
      final decoded = jsonDecode(raw);
      if (decoded is! List) return <HistoryEntry>[];
      return decoded
          .whereType<Map<dynamic, dynamic>>()
          .map((m) => HistoryEntry.fromJson(Map<String, dynamic>.from(m)))
          .toList();
    } catch (_) {
      return <HistoryEntry>[];
    }
  }

  void _writeAll(List<HistoryEntry> entries) {
    if (!kIsWeb) {
      _memory
        ..clear()
        ..addAll(entries);
      return;
    }
    try {
      final encoded = jsonEncode(entries.map((e) => e.toJson()).toList());
      storage.setItem(storageKey, encoded);
    } catch (_) {
      // Storage may be disabled (private mode, sandbox, quota). Silently
      // degrade — UI will simply show an empty history.
    }
  }
}

final historyRepositoryProvider = Provider<AuditHistoryRepository>((ref) {
  return AuditHistoryRepository();
});
