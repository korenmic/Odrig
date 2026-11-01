# Tasks

Standalone recovery extraction on master. One task and checkbox per proof commit.
Stable inventory caching and the other feature PRs are excluded.

- [ ] 1. Fail closed on uncertain saved clock settings
  - Observe the actual-core read-error/corrupt-policy regression fail before repair.
  - Port bounded policy recovery and its shared Settings diagnostic without time/schedule.
  - Run discovered core, emulator and app suites; retain failures and passing evidence.
- [ ] 2. Keep automatic Only recovery inside Clocks without inventory caching
  - Observe unknown-ID/absent-media automatic Root fallback before repair.
  - Reconcile Only context, preserve valid descendants and retry unresolved paths while
    guarding Restart clocks. Keep confirmed Off/Between and target reset usable.
  - Run discovered app/emulator suites and record independent feature scope.
- [ ] 3. Build and publish the standalone recovery APK and firmware
  - Build from clean committed source, verify source/signer/image bytes and exercise
    the shared native core/Android app. Publish to its own Drive subfolder and one PR.
  - Preserve other feature artifacts and record emulator and physical acceptance limits.

## Owner acceptance

- [ ] Observe physical boot, sustained Only playback, Wi-Fi and the real phone UI.
