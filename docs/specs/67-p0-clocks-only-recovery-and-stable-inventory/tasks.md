# Tasks

Requirements/design reviewed against the seed and host contracts. Execution order:
67.1–67.3,66.1–66.2,65 after its owner answer, then68 integration/delivery. Each
numbered task is one proof commit; state becomes in_progress with the first task.

- [x] 1. Fail closed on uncertain saved clock settings
  - First observe actual-core regressions for initial/partial read failure and malformed
    settings. Separate genuinely missing settings from uncertain IO. Add bounded retry,
    dark effective Only, explicit uncertainty and atomic operator recovery. Check memory.
  - Run discovered core and emulator suites; update shared status parsing and run app
    suite if touched. Record the observed failures in the proof commit.
- [ ] 2. Preserve and validate last-good inventory without redundant reloads
  - First observe reconnect key loss, identical-list replacement and avoidable request
    counts. Keep bounded board/storage/path snapshots, gate unsafe stale-ID actions,
    validate authoritative revisions cheaply and retain arrays/keys/order on no change.
    Test real changes, targets, incomplete pagination and legacy bounded fallback.
  - Run discovered app/core/emulator suites for touched layers. Do not fake readiness.
- [ ] 3. Keep automatic Only recovery inside Clocks
  - First observe the recorded empty-root/catalog-absent escape followed by repeated
    Only status. Replace one-shot reconciliation, preserve valid descendants and handle
    changed IDs/media/stale responses with explicit unavailable Clocks state and retry.
    This task does not add66's deliberate-navigation restriction.
  - Run discovered app/emulator suites. Document recovery, cache freshness and physical
    evidence limits; append any implementation decisions to docs/drifts.md.

## Owner acceptance (not executable queue tasks)

- [ ] Confirm the physical intermittent return-to-root and phone readiness behavior
  after flashing the delivered firmware and installing the delivered APK.
