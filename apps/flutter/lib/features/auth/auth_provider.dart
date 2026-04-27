import 'package:firebase_auth/firebase_auth.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

/// Live `User?` stream from Firebase Auth.
///
/// `null` -> signed out; an anonymous user counts as signed-in. Routes that
/// require a real account (history, compare) check both `value != null`
/// and `!user.isAnonymous` if they want to gate features behind a
/// persistent account, but the prototype gates on signed-in only.
final authUserProvider = StreamProvider<User?>((ref) {
  return FirebaseAuth.instance.authStateChanges();
});

/// Synchronous "is the user authenticated right now" — useful for go_router
/// redirects which don't have async state.
bool isAuthenticatedNow() {
  return FirebaseAuth.instance.currentUser != null;
}

/// Wraps `FirebaseAuth` calls with consistent error mapping.
class AuthService {
  AuthService(this._auth);
  final FirebaseAuth _auth;

  Future<UserCredential> signInWithEmail({
    required String email,
    required String password,
  }) {
    return _auth.signInWithEmailAndPassword(
      email: email.trim(),
      password: password,
    );
  }

  Future<UserCredential> registerWithEmail({
    required String email,
    required String password,
    String? displayName,
  }) async {
    final cred = await _auth.createUserWithEmailAndPassword(
      email: email.trim(),
      password: password,
    );
    if (displayName != null && displayName.trim().isNotEmpty) {
      await cred.user?.updateDisplayName(displayName.trim());
    }
    return cred;
  }

  Future<UserCredential> signInAnonymously() => _auth.signInAnonymously();

  Future<void> signOut() => _auth.signOut();

  Future<void> sendPasswordReset({required String email}) {
    return _auth.sendPasswordResetEmail(email: email.trim());
  }
}

final authServiceProvider = Provider<AuthService>((ref) {
  return AuthService(FirebaseAuth.instance);
});

/// Friendly mapping of FirebaseAuthException codes onto messages we render.
String mapAuthError(Object e) {
  if (e is FirebaseAuthException) {
    return switch (e.code) {
      'invalid-email' => 'That email address looks malformed.',
      'user-disabled' => 'This account has been disabled.',
      'user-not-found' => 'No account found for that email.',
      'wrong-password' => 'Wrong password.',
      'email-already-in-use' =>
        'An account with that email already exists. Try signing in.',
      'weak-password' =>
        'Password is too weak — use at least 6 characters with mixed case.',
      'too-many-requests' =>
        'Too many attempts. Try again in a few minutes.',
      'operation-not-allowed' =>
        'Email / password sign-in is disabled. Tell the operator.',
      'network-request-failed' =>
        'Network error — check your connection and try again.',
      'invalid-credential' => 'Wrong email or password.',
      _ => e.message ?? 'Authentication failed (${e.code}).',
    };
  }
  return e.toString();
}
