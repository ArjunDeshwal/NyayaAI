// Firebase web SDK config for project nyaya-494216.
//
// Generated from `firebase apps:sdkconfig WEB`. Web-only; native platforms
// are not in scope for the GSC 2026 prototype.

import 'package:firebase_core/firebase_core.dart' show FirebaseOptions;
import 'package:flutter/foundation.dart' show TargetPlatform, defaultTargetPlatform, kIsWeb;

class DefaultFirebaseOptions {
  DefaultFirebaseOptions._();

  static FirebaseOptions get currentPlatform {
    if (kIsWeb) return _web;
    // The prototype is web-only; if anyone ever runs the app on a mobile
    // target, fall through to the web config and let the platform plugin
    // surface a clearer error.
    switch (defaultTargetPlatform) {
      case TargetPlatform.android:
      case TargetPlatform.iOS:
      case TargetPlatform.macOS:
      case TargetPlatform.linux:
      case TargetPlatform.windows:
      case TargetPlatform.fuchsia:
        return _web;
    }
  }

  static const FirebaseOptions _web = FirebaseOptions(
    apiKey: 'AIzaSyAZ8Twj2BI1k4kJ38YMQhdlGtpv9-CQ2ag',
    appId: '1:149625852311:web:da48149a4a48ace9d074d2',
    messagingSenderId: '149625852311',
    projectId: 'nyaya-494216',
    authDomain: 'nyaya-494216.firebaseapp.com',
    storageBucket: 'nyaya-494216.firebasestorage.app',
    measurementId: 'G-VSECR1LK1Z',
  );
}
