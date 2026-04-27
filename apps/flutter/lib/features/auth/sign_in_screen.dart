import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../app/theme.dart';
import '../../shared/widgets/disclaimer_footer.dart';
import 'auth_provider.dart';

/// `/signin` route — Email/Password (with create-account toggle) plus a
/// "Continue as guest" anonymous-sign-in button.
///
/// Anonymous identities give every visitor a stable user id without an email
/// — enough to gate History + Compare per-device. An anonymous account can
/// later be upgraded to a real one with `linkWithCredential`, but the
/// prototype doesn't expose that yet.
class SignInScreen extends ConsumerStatefulWidget {
  const SignInScreen({super.key, this.next});

  /// Optional `?next=/path` redirect target — where to send the user after
  /// successful sign-in. Defaults to `/`.
  final String? next;

  @override
  ConsumerState<SignInScreen> createState() => _SignInScreenState();
}

class _SignInScreenState extends ConsumerState<SignInScreen> {
  final _formKey = GlobalKey<FormState>();
  final _emailCtrl = TextEditingController();
  final _passwordCtrl = TextEditingController();
  final _nameCtrl = TextEditingController();

  bool _busy = false;
  bool _registerMode = false;
  String? _error;

  @override
  void dispose() {
    _emailCtrl.dispose();
    _passwordCtrl.dispose();
    _nameCtrl.dispose();
    super.dispose();
  }

  void _goNext() {
    final target = widget.next ?? '/';
    if (mounted) context.go(target);
  }

  Future<void> _submitEmailFlow() async {
    if (!(_formKey.currentState?.validate() ?? false)) return;
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      final svc = ref.read(authServiceProvider);
      if (_registerMode) {
        await svc.registerWithEmail(
          email: _emailCtrl.text,
          password: _passwordCtrl.text,
          displayName: _nameCtrl.text,
        );
      } else {
        await svc.signInWithEmail(
          email: _emailCtrl.text,
          password: _passwordCtrl.text,
        );
      }
      _goNext();
    } catch (e) {
      setState(() => _error = mapAuthError(e));
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _continueAsGuest() async {
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      await ref.read(authServiceProvider).signInAnonymously();
      _goNext();
    } catch (e) {
      setState(() => _error = mapAuthError(e));
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _resetPassword() async {
    final email = _emailCtrl.text.trim();
    if (email.isEmpty || !email.contains('@')) {
      setState(() => _error = 'Type your email above first.');
      return;
    }
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      await ref.read(authServiceProvider).sendPasswordReset(email: email);
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('Password-reset link sent to $email'),
          behavior: SnackBarBehavior.floating,
          duration: const Duration(seconds: 4),
        ),
      );
    } catch (e) {
      setState(() => _error = mapAuthError(e));
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final isWide = MediaQuery.sizeOf(context).width >= 600;
    return Scaffold(
      body: SafeArea(
        child: Center(
          child: SingleChildScrollView(
            padding: EdgeInsets.symmetric(
              horizontal: isWide ? 40 : 18,
              vertical: 24,
            ),
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 460),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  Padding(
                    padding: const EdgeInsets.only(bottom: 24),
                    child: Row(
                      children: [
                        TextButton.icon(
                          onPressed: () => context.go('/'),
                          icon: const Icon(Icons.arrow_back, size: 16),
                          label: const Text('NyayaAI'),
                        ),
                      ],
                    ),
                  ),
                  Card(
                    child: Padding(
                      padding: EdgeInsets.all(isWide ? 28 : 20),
                      child: Form(
                        key: _formKey,
                        autovalidateMode: AutovalidateMode.onUserInteraction,
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.stretch,
                          children: [
                            Semantics(
                              header: true,
                              child: Text(
                                _registerMode
                                    ? 'Create your account'
                                    : 'Sign in to NyayaAI',
                                style: Theme.of(context)
                                    .textTheme
                                    .headlineMedium,
                              ),
                            ),
                            const SizedBox(height: 4),
                            Text(
                              _registerMode
                                  ? 'Save audits to your account, share '
                                      'reports with regulators or NGOs.'
                                  : 'Welcome back. Pick up your audit history '
                                      'and saved reports.',
                              style: const TextStyle(
                                color: NyayaColors.muted,
                                fontSize: 14,
                              ),
                            ),
                            const SizedBox(height: 20),
                            if (_registerMode) ...[
                              TextFormField(
                                controller: _nameCtrl,
                                enabled: !_busy,
                                textInputAction: TextInputAction.next,
                                decoration: const InputDecoration(
                                  labelText: 'Display name',
                                  hintText: 'How regulators see you on reports',
                                  prefixIcon: Icon(Icons.person_outline),
                                ),
                                validator: (v) {
                                  final t = v?.trim() ?? '';
                                  if (t.isEmpty) {
                                    return 'Name is required.';
                                  }
                                  if (t.length > 80) {
                                    return 'Max 80 characters.';
                                  }
                                  return null;
                                },
                              ),
                              const SizedBox(height: 14),
                            ],
                            TextFormField(
                              controller: _emailCtrl,
                              enabled: !_busy,
                              autofillHints: const [AutofillHints.email],
                              keyboardType: TextInputType.emailAddress,
                              textInputAction: TextInputAction.next,
                              decoration: const InputDecoration(
                                labelText: 'Email',
                                hintText: 'you@example.com',
                                prefixIcon: Icon(Icons.email_outlined),
                              ),
                              validator: (v) {
                                final t = v?.trim() ?? '';
                                if (t.isEmpty) return 'Email is required.';
                                if (!t.contains('@') || !t.contains('.')) {
                                  return 'That email looks malformed.';
                                }
                                return null;
                              },
                            ),
                            const SizedBox(height: 14),
                            TextFormField(
                              controller: _passwordCtrl,
                              enabled: !_busy,
                              obscureText: true,
                              autofillHints: _registerMode
                                  ? const [AutofillHints.newPassword]
                                  : const [AutofillHints.password],
                              textInputAction: TextInputAction.done,
                              onFieldSubmitted: (_) => _submitEmailFlow(),
                              decoration: const InputDecoration(
                                labelText: 'Password',
                                prefixIcon: Icon(Icons.lock_outline),
                              ),
                              validator: (v) {
                                final t = v ?? '';
                                if (t.isEmpty) {
                                  return 'Password is required.';
                                }
                                if (_registerMode && t.length < 6) {
                                  return 'Use at least 6 characters.';
                                }
                                return null;
                              },
                            ),
                            if (_error != null) ...[
                              const SizedBox(height: 14),
                              Container(
                                padding: const EdgeInsets.all(12),
                                decoration: BoxDecoration(
                                  color: const Color(0xFFFEE2E2),
                                  borderRadius: BorderRadius.circular(8),
                                  border:
                                      Border.all(color: NyayaColors.fail),
                                ),
                                child: Row(
                                  children: [
                                    const Icon(
                                      Icons.error_outline,
                                      color: NyayaColors.fail,
                                      size: 18,
                                    ),
                                    const SizedBox(width: 8),
                                    Expanded(
                                      child: Text(
                                        _error!,
                                        style: const TextStyle(
                                          color: NyayaColors.fail,
                                          fontSize: 13,
                                        ),
                                      ),
                                    ),
                                  ],
                                ),
                              ),
                            ],
                            const SizedBox(height: 18),
                            FilledButton.icon(
                              onPressed: _busy ? null : _submitEmailFlow,
                              icon: _busy
                                  ? const SizedBox(
                                      width: 18,
                                      height: 18,
                                      child: CircularProgressIndicator(
                                        strokeWidth: 2.5,
                                        valueColor:
                                            AlwaysStoppedAnimation<Color>(
                                          Colors.white,
                                        ),
                                      ),
                                    )
                                  : Icon(
                                      _registerMode
                                          ? Icons.person_add_alt_1
                                          : Icons.login,
                                    ),
                              label: Text(
                                _busy
                                    ? 'Working…'
                                    : (_registerMode
                                        ? 'Create account'
                                        : 'Sign in'),
                              ),
                            ),
                            const SizedBox(height: 10),
                            Row(
                              mainAxisAlignment: MainAxisAlignment.spaceBetween,
                              children: [
                                TextButton(
                                  onPressed: _busy
                                      ? null
                                      : () => setState(() {
                                            _registerMode = !_registerMode;
                                            _error = null;
                                          }),
                                  child: Text(
                                    _registerMode
                                        ? 'Already have an account? Sign in'
                                        : 'New here? Create account',
                                  ),
                                ),
                                if (!_registerMode)
                                  TextButton(
                                    onPressed: _busy ? null : _resetPassword,
                                    child: const Text('Forgot password?'),
                                  ),
                              ],
                            ),
                            const Padding(
                              padding: EdgeInsets.symmetric(vertical: 12),
                              child: Row(
                                children: [
                                  Expanded(child: Divider()),
                                  Padding(
                                    padding: EdgeInsets.symmetric(
                                      horizontal: 8,
                                    ),
                                    child: Text(
                                      'or',
                                      style: TextStyle(
                                        color: NyayaColors.muted,
                                        fontSize: 12,
                                      ),
                                    ),
                                  ),
                                  Expanded(child: Divider()),
                                ],
                              ),
                            ),
                            OutlinedButton.icon(
                              onPressed: _busy ? null : _continueAsGuest,
                              icon: const Icon(Icons.person_outline),
                              label: const Text('Continue as guest'),
                            ),
                            const SizedBox(height: 8),
                            const Text(
                              'Guest sessions are tied to this browser. '
                              'Sign up later to keep your audits across devices.',
                              style: TextStyle(
                                color: NyayaColors.muted,
                                fontSize: 11,
                                height: 1.45,
                              ),
                            ),
                          ],
                        ),
                      ),
                    ),
                  ),
                  const DisclaimerFooter(),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}
