# Tasks

Requirements/design reviewed against the seed and inherited PR39 candidate. The
fairness repair is already implemented: these tasks verify/reuse it, never duplicate it.
One numbered task per proof commit. Final task waits for65–67 software completion.

- [x] 1. Audit and retain the existing watchdog-starvation repair
  - Confirm production-body fairness tests, candidate/source provenance and unchanged
    watchdog/priority/stack/output gates. Reuse inherited before/after evidence, label
    model limits and unknown installed physical version/reset cause explicitly.
  - Run discovered firmware suite; record verified reuse and set seed in_progress.
- [x] 2. Verify integrated sustained Only playback and command responsiveness
  - Exercise native clocks/messages, heavy/late rendering, delayed IO/replies and
    reconnects across existing command routes and shared app behavior. Reuse67 proofs
    where identical; add missing meaningful coverage. Only repair a residual fault
    after observing its own regression fail first.
  - Run discovered core/emulator/app/firmware suites; retain bounded-run evidence and
    distinguish native-core/model coverage from unperformed physical acceptance.
- [x] 3. Build and publish the integrated APK and firmware and hand off one PR
  - After65–67, run all supported discovered suites, build firmware through fw.py and
    build/sign the APK from clean runtime source. Verify offline image/provenance and
    Android VM installation/upgrade plus shared emulator functionality.
  - Replace existing Drive APK/FW in place, verify bytes/file identity and persistent
    signer backups, commit delivery evidence/task checkbox, push one new PR and gate
    exact final head CI. Attach PR, notify what finished/was uploaded and audit commits.

- [ ] 4. Reproduce and repair the firmware startup regression against stable master
  - Use the owner's confirmed old/new firmware comparison as evidence of a regression.
    Inspect the actual linked image and board-adapter startup paths; reproduce a concrete
    fault with executable firmware/host emulation or a production-code harness before repair.
  - Add a regression observed failing first. Repair the cause without changing hardware,
    power, command protocol, watchdog protection or unrelated feature behavior.
  - Run the affected discovered suites and compile/inspect the ESP32-S3 image through
    fw.py. Record the locally proven fault separately from the unresolved physical reset.
  - Reopened: the owner retested the callback-repair image and confirmed the same boot
    failure. That independent callback repair does not resolve the physical regression.
- [x] 5. Publish the startup repair firmware from the committed runtime source
  - Rebuild/verify through fw.py from clean committed runtime source, run the actual image
    in the available ESP32-S3 emulator and report its peripheral/physical limits.
  - Replace the existing Drive firmware in place with checksum/source verification;
    retain the current APK, push this PR and notify the operator of the firmware update.
- [x] 6. Prepare a matched master-source control after the rejected physical retest
  - Confirm the control's core/firmware inputs match freshly fetched origin/master and
    verify its existing clean Windows build through fw.py's offline inspector.
  - Upload a separately named master control with checksum, provenance and phone-flasher
    instructions. Preserve the usual artifacts; leave its physical outcome pending.
- [x] 7. Analyze the supplied reset capture and prepare an isolated firmware midpoint
  - Record the owner's positive master-control result and negative PR result. Preserve
    the raw log privately and publish only its hash and sanitized reset summary.
  - Distinguish confirmed reset evidence from its unknown cause. Prepare/inspect the
    timing-plus-fairness source midpoint without publishing it as a repair or flashing.
  - Record which further physical trace or bisection result is required; task4 stays open.

## Owner acceptance (not executable queue tasks)

- [ ] Identify the affected board's installed revision/reset cause and observe sustained
  Only playback, Wi-Fi and phone responsiveness after installing the delivery.
