# Tasks

Requirements/design reviewed against the seed and inherited PR39 candidate. The
fairness repair is already implemented: these tasks verify/reuse it, never duplicate it.
One numbered task per proof commit. Final task waits for65–67 software completion.

- [x] 1. Audit and retain the existing watchdog-starvation repair
  - Confirm production-body fairness tests, candidate/source provenance and unchanged
    watchdog/priority/stack/output gates. Reuse inherited before/after evidence, label
    model limits and unknown installed physical version/reset cause explicitly.
  - Run discovered firmware suite; record verified reuse and set seed in_progress.
- [ ] 2. Verify integrated sustained Only playback and command responsiveness
  - Exercise native clocks/messages, heavy/late rendering, delayed IO/replies and
    reconnects across existing command routes and shared app behavior. Reuse67 proofs
    where identical; add missing meaningful coverage. Only repair a residual fault
    after observing its own regression fail first.
  - Run discovered core/emulator/app/firmware suites; retain bounded-run evidence and
    distinguish native-core/model coverage from unperformed physical acceptance.
- [ ] 3. Build and publish the integrated APK and firmware and hand off one PR
  - After65–67, run all supported discovered suites, build firmware through fw.py and
    build/sign the APK from clean runtime source. Verify offline image/provenance and
    Android VM installation/upgrade plus shared emulator functionality.
  - Replace existing Drive APK/FW in place, verify bytes/file identity and persistent
    signer backups, commit delivery evidence/task checkbox, push one new PR and gate
    exact final head CI. Attach PR, notify what finished/was uploaded and audit commits.

## Owner acceptance (not executable queue tasks)

- [ ] Identify the affected board's installed revision/reset cause and observe sustained
  Only playback, Wi-Fi and phone responsiveness after installing the delivery.
