# Tasks

Standalone extraction based directly on master. No dependency on the other feature
branches; no firmware, time/schedule, rotation or inventory-cache changes.

- [x] 1. Enforce the Only boundary in shared navigation and browsing controls
  - Observe navigation escapes before implementing the boundary latch, enter/back
    guards and matching visible controls. Preserve Settings/Target and mode exit.
  - Run fresh discovered boundary regressions; record the interim selected-suite run
    separately. Task2 runs the final frozen app/emulator suites after destination changes.
- [x] 2. Keep upload and authoring destinations inside the boundary
  - Observe internal-root and outside upload authorization before implementing capture,
    final policy preflight and shared-job guards. Preserve ordinary upload fallback.
  - Run final frozen discovered app and onboarding suites with one worker. Reuse the
    successful 657-case emulator suite because core/firmware remain unchanged; document
    the qualified interim run, policy and evidence.
- [x] 2.1. Align visible Clocks-only Settings help with the browsing boundary
  - Observe a browser regression for the visible Settings explanation, correct its
    contradictory unrestricted-browsing text, and run the affected discovered checks.
- [x] 3. Build the isolated APK and publish it with the verified master firmware control
  - Parent delivery task: build/verify the signed APK and prove core/firmware source
    equivalence before reusing the exact physically working master application image.
    Upload both under their own Drive subfolder with truthful source provenance, and
    hand off the standalone PR with physical limits.

## Owner acceptance (not executable queue tasks)

- [ ] Verify navigation and upload choices on the physical phone with real media.
