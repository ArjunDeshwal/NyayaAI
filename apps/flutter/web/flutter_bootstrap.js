{{flutter_js}}
{{flutter_build_config}}

_flutter.loader.load({
  config: {
    // Serve canvaskit.wasm (~7MB) from our own origin instead of
    // https://www.gstatic.com/flutter-canvaskit/<rev>/, which is the default
    // and can stall on networks that rate-limit or block gstatic.com.
    canvasKitBaseUrl: "canvaskit/",
  },
  serviceWorkerSettings: {
    serviceWorkerVersion: {{flutter_service_worker_version}},
  },
});
