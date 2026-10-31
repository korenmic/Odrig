# Tasks

Each task runs through TACTIC as one proof commit with only its own checkbox
ticked. Regression tests must be observed failing before the fix. Preserve
previously delivered seeds56–60; seed61 is not a dependency or part of this run.

- [x] 1. Support guarded external uploads into existing indexed folders
  - Extend existing begin path parsing, compact Upload destination lifetime and
    external absence expectation without adding command spellings.
  - Update atomic catalog/index publication for nested insertion and preserve
    playback/id-map/folder counts, recovery, cancellation and media-removal safety.
  - Add fail-first host regressions for ODRG/ODRGX byte identity, limits, folder
    resolution, collision guards and interrupted operations; append command/drift
    documentation. Set seed state in_progress. Run discovered core and odrigctl
    suites, firmware_host tests and the core memory/stack checks.
  - Requirements:2.3–2.4,3.1–3.4.

- [x] 2. Add ready-made upload preparation and visible storage/folder choices
  - Implement bounded read-only ODRG/ODRGX preparation, exact encoded-byte sending,
    content-key preview reuse and honest fallback without full compressed expansion.
  - Add the dropdown, per-form External default/absence/redetection behavior,
    captured browsing context, basename/collision checks and fresh preflight.
    Apply destination behavior to converted media too; preserve anchored edits.
  - Add fail-first app/browser regressions and update app documentation. Run
    discovered app and converter-npm suites and relevant emulator checks.
  - Requirements:1.1–1.3,2.1–2.4,3.1–3.4.

- [x] 3. Prove ready-made uploads against the emulator and document acceptance
  - Exercise shared app/core root/nested uploads, default/fallback/reconnect,
    explicit Internal, staleness, collisions, malformed/mismatched files,
    read-only/full storage, cancellation, removal and old-target refusal.
  - Upload the actual space-scan ready file, verify stored byte hash, complete
    acknowledged catalog/index entry, read/play/ignore/brightness/remove and
    restart behavior. Record bounded preparation and preview evidence.
  - Run all portable discovered suites, retain proof logs, and document which
    physical board/phone checks remain open. No hardware changes or flashing.
  - Requirements:4.1,3.2–3.4.

- [x] 4. Build and deliver signed APK and updated firmware
  - Build firmware through the existing Windows pipeline and APK from the same
    clean software source using the persistent dedicated key. Verify signer,
    packaging and native Android clean install/same-key update/launch.
  - Overwrite the existing Drive APK and firmware in place and verify hashes,
    lengths and file identity. Preserve existing signing backups and record
    source/build/upload provenance with no secrets. Mark seed completed.
  - Run relevant artifact/onboarding checks. Commit the proof and task tick;
    the implement wrapper then pushes, checks PR CI and sends final/push notices
    naming completed work and uploaded files. Keep physical acceptance open.
  - Requirements:4.2–4.3.

- [x] 5. Keep browsed folders through transient lookup failures
  - Diagnose the owner's Clocks-to-Root report and observe the navigation
    regression failing before fixing it. Revalidate a refused folder by its
    captured path before treating it as removed; preserve target/navigation
    guards and bound retries without mixing pages from different listings.
  - Cover transient first/later-page failures, changed folder IDs, real removal,
    failed verification and navigation during recovery in discovered app tests.
    Exercise the shared app against the native emulator with Clocks content.
    Record the actual reproduction and remaining physical acceptance limits.

- [ ] 6. Deliver the folder-navigation correction
  - Build the APK from the clean task-5 source with the same persistent key,
    verify packaging and Android AVD installation/update/launch, and overwrite
    the existing Drive APK in place with hash/length/identity readback.
  - Rebuild firmware only if the correction changes firmware/core sources;
    otherwise retain the delivered firmware and state that explicitly. Record
    delivery provenance, push to the existing PR, check CI and notify the owner.

## Owner acceptance (not claimed by automated tasks)

Try the delivered APK on the operator's phone and upload on the physical board
with its SD card, including removal/reinsertion and observed playback. These
checks remain open until the owner reports them; emulator/AVD proof is separate.
