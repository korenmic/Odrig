# Tasks: SD capacity without blocking playback

Execute one task per commit and tick its checkbox in that proof commit. First
implementation task sets the seed to `in_progress`. Preserve the owner's final
APK build ordering; firmware compilation is deferred to future seed 60. Task 4
requires a later approved physical session and is not software-complete by proxy.

- [ ] 1. Replace synchronous SD capacity scans with generation-safe bounded discovery.
  - Observe a compiled real-backend cold-query regression fail first and record
    the observed failure in the commit. Keep mounted presence independent.
  - Implement the fixed-memory FAT16/FAT32 sector state machine, checked geometry,
    partition/active-FAT handling, 64-bit counts, one-sector worker slices and
    nonwaiting cached callbacks. Cover invalid/unsupported and failed reads.
  - Invalidate before every possible external mutation, including partial/error
    paths; pause while writing and restart after close, removal or remount.
  - Verify compiled stand-ins by discovered firmware tests where supported, plus
    core/emulator capacity and upload rollback tests by discovery. Report unrelated
    host limitations without claiming a firmware build.

- [ ] 2. Discard stale storage reports and distinguish unknown capacity in the shared app.
  - Observe regressions for stale absence and mounted reports fail before the fix.
  - Invalidate old `space` state on connection loss; render a current unknown
    report, a present/unknown card and a confirmed absence distinctly. Preserve
    catalog counts, supported writes and target/reply isolation.
  - Run discovered app tests against the emulator/stand-in targets, including
    disconnect/reconnect and target changes, without rebuilding the APK yet.

- [ ] 3. Document capacity freshness and record software verification.
  - Update core/firmware/microSD/app contracts and append design resolutions to
    `docs/drifts.md`; keep command/schema compatibility and safe unknown uploads.
  - Record failing-before evidence, passing discovered suites, emulator smoke and
    actual host limitations in a verification note. Explicitly defer firmware
    compilation to seed 60 and cumulative APK release to the end of this stack.
  - Run relevant discovered documentation/onboarding suites and all supported
    software suites after the code changes; leave physical acceptance open.

- [ ] 4. Verify cold capacity and phone states on the real installation with the owner.
  - In a later approved session, repeat two cold starts, first/warm `space` and
    concurrent status timings <=500 ms, 20–50 FPS without long gaps, intact catalogs,
    removal/remount and controlled mutation/out-of-space safety at brightness <=40.
  - Record firmware identity, rates, exact timing and the owner's phone observations.
    Do not check this task or mark the seed completed without those observations.
