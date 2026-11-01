# Tasks

Standalone extraction based directly on master. No dependency on the other feature
branches; no firmware, time/schedule, rotation or inventory-cache changes.

- [ ] 1. Enforce the Only boundary in shared navigation and browsing controls
  - Observe navigation escapes before implementing the boundary latch, enter/back
    guards and matching visible controls. Preserve Settings/Target and mode exit.
  - Run discovered app and emulator suites; record verification and update seed state.
- [ ] 2. Keep upload and authoring destinations inside the boundary
  - Observe internal-root and outside upload authorization before implementing capture,
    final policy preflight and shared-job guards. Preserve ordinary upload fallback.
  - Run discovered app, emulator and onboarding suites; document policy and evidence.
- [ ] 3. Build and publish the isolated APK and master-equivalent firmware
  - Parent delivery task: verify signed APK and application image, upload both under
    their own Drive subfolder, and hand off the standalone PR with physical limits.

## Owner acceptance (not executable queue tasks)

- [ ] Verify navigation and upload choices on the physical phone with real media.
