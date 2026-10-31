# Verification: board time and daily hours

The runtime implemented through task5 (`ac4be3f`), including the task6 initial
authoring-inventory regression fix, passed the portable checks below on Windows
x64. Core and firmware sources remain unchanged from task3. The exact clean source
used for the packaged APK/firmware is recorded by the separate task7 delivery proof.

## Portable suites

The discovered complete run was `20261031-224540-24856` with six workers. Its unaffected
suites passed. Affected-suite run `20261031-225931-40148` passed firmware, mapping and
onboarding. It also exposed a delayed-inventory authoring race. Final run
`20261031-231535-120140`, with four workers, passed the complete app and onboarding suites
after that fix. These are the last passing
outcomes for all ten board-free Windows suites: **5239 cases, 21 platform
skips, no remaining failures**.

| Suite | Cases | Last result |
|---|---:|---|
| app | 493 | OK |
| firmware | 651 | OK (skipped=1) |
| core | 1085 | OK (skipped=1) |
| converter-npm | 1602 | OK |
| emulator | 671 | OK (skipped=19) |
| mapping | 43 | OK |
| runner | 26 | OK |
| converter | 552 | OK |
| onboarding | 88 | OK |
| firmware-host | 28 | OK |

Commands, with the existing configured shared tool cache available to the child:

```
python core/build.py host
python tests/run.py --workers 6 --slowest 8
python tests/run.py --suites app,firmware,mapping,onboarding --workers 4 --slowest 5
python tests/run.py --suites app,onboarding --workers 4 --slowest 5
```

The first run exposed three old expectations: caches were assumed to belong to
the current checkout despite an explicit shared-tool override, Gradle's home had
the same assumption, and a mapping test expected manual Off to create no persisted
metadata. The checks now require the configured tool roots and unchanged show
bytes plus the canonical manual-Off `schedule.txt`. Two browser cases hit Windows
socket pressure at peak concurrency; both passed isolated, then their affected
complete suites passed. Those corrections change test expectations only.

The subsequent app run observed a new text incorrectly choosing id1 instead of
free id3 before the initial names arrived. Deterministic native regressions then
failed for an enabled Upload with unknown inventory and an unguarded claimed id.
New authoring now waits for the name inventory and uses the existing internal
creation-only begin form; installed bytes/entries are preserved if an id was
claimed meanwhile. Existing-file editing retains its read CRC. This is the task6
runtime correction; no new command or format is introduced.

The portable walkthrough Plan additionally passes all four cases. The optional
full fresh-copy walkthrough uses POSIX shell commands, `.venv/bin` and a macOS
library path, so it was not run on Windows. Native Windows conversion, core,
emulator, command-tool, app and host suites provide the available alternatives.
The APK suite runs after task7 builds it. Board/air suites were not run.

## Feature evidence

- Civil-clock/schema/range/CRC tests, exact phone-zone DST transitions, reset
  invalidation and independent monotonic playback pass against the actual core.
- Overnight and same-day boundaries, DST skips/repeats, manual precedence and
  resume, persistence faults, read-only hosts and no frame-time writes pass.
- HTTP, TCP and byte-feed share board identity guards, including the largest
  unchanged2048-byte command. Timing files survive ordinary show install/readback.
- Native/browser tests prove default-on auto-sync, the per-board15-minute rule,
  invalid-clock bypass, manual sync, auto-off, live zone-only updates, worker
  responsiveness, no status-poll UTC writes/retries and stale-target protection.
- Fifteen Settings scenarios cover real native blackout/manual/Resume behavior,
  preference persistence, paired-hour confirmation, draft preservation, lost and
  refused replies, revision conflicts, reconnects, old firmware, corrupt metadata
  and labelled48-pixel controls. Physical phone/board acceptance is separate.
- The firmware power adapter's portable host tests distinguish external explicit
  power changes from initialization and its own visibility mirror.

## Memory and source bounds

The strict host was rebuilt with undefined-behavior traps, stack protection and
the existing512-byte frame guard. Actual host allocations are:

| Fixture | Bytes | Allocations |
|---|---:|---:|
|100-item target|125241|18|
|Example|88530|17|
|Read-only|77701|13|
|100-item target with drive|131029|21|

The Core object is3776 bytes, as measured for task3; core/firmware sources are
unchanged since that proof (`1a576c9`). The arena remains below131072 bytes and the
object below4096. Command/reply limits remain2048/1024. No ID/path/count domains or
existing limits were reduced to fit.

## Unperformed physical acceptance

These observations still need the owner after installing the delivered artifacts:

- On the actual phone, verify default-on sync, persisted auto-off, confirmed time
  and zone, edited/saved hours, refused/lost replies, reconnects and Resume.
- On the LEDs, with brightness40 or less, verify a scheduled blackout while playback
  progresses, On/Off boundaries and sticky manual priority through a restart.
- With auto-sync off, verify reset/power loss makes time invalid and ignores hours;
  then Sync now restores valid scheduling without changing the saved pair.
- Verify phone zone/DST changes, a due connection after15 minutes, no periodic UTC
  writes, and physical Wi-Fi/USB transport behavior with the installation.

Native and Android virtual-device evidence cannot replace real phone, LED,
electrical or power-loss observations. No board was flashed or erased by this run.

## Artifact handoff

Task7 owns clean-source firmware/APK builds, persistent signing, Android
installation/update/launch, mounted Drive replacement and byte/identity checks.
Its exact source hashes and artifact evidence belong in `delivery.json` after
those actions succeed. This task does not claim deployment happened yet.
