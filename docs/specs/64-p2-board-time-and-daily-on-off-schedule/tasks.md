# Tasks: board time and a daily on/off schedule

Requirements: [requirements.md](requirements.md). Design: [design.md](design.md).
Execute one task, verify it, tick its checkbox and proof-commit before the next.
Only seed64 is in scope; do not implement seeds45 or61 or resume cancelled seed12.

- [x] 1. Implement the boot-local civil clock and bounded phone-zone snapshot
  - Add civil_time state/parser, read/set/zone command dispatch and additive capability.
    Load verified persisted zone rules without restoring epoch validity. Keep memory,
    allocation, reply and compiler stack bounds; compact existing state only if needed.
  - Add deterministic tests for unset/set/read, range/schema/base64/revision failures,
    forward/backward corrections, timer behavior, DST transitions, corrupt/partial
    zone files, unchanged writes and atomic failures. Observe missing time command
    behavior before adding it; capture the red assertion in the proof commit.
  - Document the time contract and memory figures; append resolved design choices to
    drifts/decisions. Set the seed in_progress. Discover core and onboarding suites.
  - Verified:1067 discovered core tests pass(1 skip), including17 new civil-time
    scenarios;88 onboarding tests pass. Initial missing-command test failed at
    `assertTrue(state['ok'])` before implementation. Target memory131013 bytes,
    Core3760 bytes; existing limits and status prefix/suffix contracts retained.

- [x] 2. Implement persistent daily scheduling and sticky manual overrides
  - Add schedule settings validation/readback/atomic publication and wire operations.
    Integrate visibility evaluation with refresh/commands and preserve playback.
    Manual on/off always wins until explicit resume, including reset persistence.
  - Test overnight/same-day/equal/boundary behavior, DST skips/repeated hours, invalid
    clock bypass, clock jumps, resume, disabled mode, resets, read-only hosts, storage
    faults, unchanged saves and no per-tick writes. Observe the missing schedule
    command/automatic boundary behavior before implementation. Any regression fix
    must first fail on unfixed code with its observed failure recorded.
  - Document schedule persistence and manual error semantics. Run discovered core,
    emulator and onboarding suites before the proof commit.
  - The full emulator gate exposed Windows socket-buffer exhaustion before connect.
    A controlled regression reproduced the error before its fix. The harness now
    bounds recovery to two seconds before transmission, with explicit tests that
    other errors remain immediate and this recovery never replays a sent command.
  - Verified:1085 discovered core tests pass(1 skip),663 emulator tests pass(20
    platform skips),88 onboarding tests pass. Missing schedule read first failed
    `assertTrue(state['ok'])`. Native RGB blackout preserves advancing loop counts;
    frame ticks do not write timing files. Core3768 bytes, drive arena131021 bytes.

- [ ] 3. Integrate shared timing commands with hosts and command tools
  - Ensure byte-feed/serial, TCP, HTTP and command tool reach the same timing state.
    Preserve schedule/zone files through ordinary show installs/readback as appropriate.
    Integrate external manual WLED control without turning scheduler output into an
    override; keep all hardware/power configuration unchanged.
  - Add transport, firmware-host and tool tests; prove any reproduced host feedback or
    persistence regression failing before its fix and record the observed failure.
    Update commands/firmware/emulator docs and firmware-additions.
  - Run discovered emulator, firmware-tool, firmware-host and onboarding suites.

- [ ] 4. Add phone-zone generation and guarded connection-triggered synchronization
  - Implement worker-based zone snapshots from phone Intl data, validated timing
    commands and serialized client operations with target/connection generations.
    Add persistent default-on auto-sync and per-board 15-minute confirmations;
    invalid clocks bypass cooldown, zone updates do not reset it, status polls never
    trigger periodic UTC writes. Manual sync shares the same confirmation path.
  - Test byte format/CRC and actual named-zone DST against the phone, unsupported
    zones, connection timing, clock loss, auto-sync off, failed/unconfirmed writes,
    manual sync, target switches across awaits/queued sends and old firmware.
    Observe absent sync behavior before adding it; bug regressions are red first.
  - Run discovered app and onboarding suites; retain meaningful progress notifications.

- [ ] 5. Add confirmed Time and schedule controls to Settings
  - Add time/zone readout, refresh, sync now, auto-sync preference, enabled flag,
    On/Off fields, Save, override status and explicit Resume schedule.
    Confirm replies, protect typed values/target changes and show plain-language
    unsupported/invalid/busy/error states with accessible phone-sized controls.
  - Test UI defaults/edit validation/confirmation, sticky manual mode and resume,
    stale replies, reconnects and unsupported firmware through shared browser UI.
    Observe missing controls first; any UI regression test must be red before fixing.
  - Run discovered app/onboarding suites and native emulator timing UI scenarios.

- [ ] 6. Verify the integrated feature and document release acceptance
  - Run every board-free suite that works on this Windows host, using discovery.
    Verify native HTTP/TCP and app behavior against deterministic clocks, power loss
    and persisted manual mode; retain memory/source/stack evidence.
  - Update operating docs, agent index and verification.md with actual results and
    an explicit unperformed physical phone/board checklist. Fix in-scope failures
    with fail-first regression evidence, never fake physical acceptance.
  - Audit task/proof boundaries and prepare a clean runtime build source.

- [ ] 7. Build, deploy and verify the APK and firmware artifacts
  - Build firmware only through fw.py on Windows and inspect its ESP32-S3 image and
    build inputs. Build the APK with the existing persistent dedicated signer;
    verify clean install, same-key update and launch on an owned Android emulator.
  - Overwrite the existing Drive Artifacts/odrig APK and firmware in place, preserve
    signing backups/file identity and verify bytes. Record hashes, sizes and exact
    source commit in delivery.json without exposing signing secrets.
  - Commit this task's proof; audit one task per commit, push one PR to master and
    run the exact-head PR CI gate. Resolve in-scope regressions before ready handoff.
    Notify task completion, all-tasks finish and successful push/CI delivery separately.
