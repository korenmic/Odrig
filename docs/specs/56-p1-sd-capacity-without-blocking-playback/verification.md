# Seed 56 software verification

The software changes are on `codex/seed-56-sd-capacity` in the managed worktree
`C:/Users/koren/.codex/worktrees/seeds-56-59/Odrig`. This is the first branch of
the owner's requested stack for seeds 56–59, intended for one final PR. Nothing
has been flashed, installed on a phone or changed on a real card in this run.

## Regression evidence and commits

- `901107c`, task 1: the compiled real-backend regression first reported
  `cold capacity delayed next refresh/status by 10000 ms` against the synchronous
  implementation and failed `nextRefreshAndStatus <= 50`. The deterministic
  stand-in accounts for delayed IO and the following refresh/status opportunity;
  its milliseconds are simulated, not a new board measurement.
- The fix uses one-sector FAT16/FAT32 discovery and a nonwaiting cache. Tests
  cover warm/busy queries, 64-bit capacity above 4 GiB, active FAT and partition
  selection, invalid/ambiguous geometry, interleaved reads, failure, mutation and
  remount. Failed writes cannot expose optimistic on-media free counts.
- `eac9a96`, task 2: the browser regression first failed for both initial absence
  and a mounted card. After 12 seconds without a valid reply the old client still
  showed `absent` or the stale 77.0 MB free of 99.0 MB report. It now discards that
  report and recovers presence/catalog counts from a fresh reply.

## Checks already completed

All suites use discovery. No firmware or APK build is included in these results.

| Check | Result |
|---|---|
| Compiled SPI-card backend | 27 tests pass, including raw-sector discovery and failed-write/remount safety |
| Drive source contracts | 11 tests pass |
| Core, through `tests/run.py --suites core,emulator --workers 4` | 951 tests pass, 1 platform skip |
| Emulator and command tool, same run | 630 tests pass, 19 platform skips |
| Shared app, through `tests/run.py --suites app --workers 2` | 367 tests pass, including emulator-backed controls and lost-storage-report recovery |

The first combined core run hit a Windows compiler-probe file collision with the
SD harness. The harness now probes in its own temporary folder. The first app run
with four workers had one cleanup error in the unchanged shared-toolchain lock
test (`WinError 32` deleting an open lock file). Its isolated test and seven-test
module passed; the complete two-worker app retry then passed. These attempts are
not presented as clean runs.

The full firmware suite was also attempted directly on Windows: 411 tests,
297 failures and 31 errors. Diagnostics include unavailable ASan/UBSan libraries,
macOS-oriented toolchain paths, absent firmware-environment packages and Windows
symlink privileges. It is not claimed passing. The changed SD backend itself is
compiled and executed by its 27 passing host tests. Future seed 60 records the
owner's separate Windows firmware-build work; it is not implemented here.

## Additional documentation and smoke checks

The remaining supported host suites ran through discovery: Python library/converter
552 tests, JavaScript converter 1,581, mapping 43 and runner 22 passed. The changed
core documentation passed 18 checks and app documentation passed 12. Onboarding's
first run found future seed 60 missing from the newcomer index (`60 not found`);
task 3 adds that planned-work entry, after which all 88 onboarding tests pass.

The deterministic record-mode CLI smoke issued `status`, `space`, `play 1`,
`status` and `space` over three seconds of virtual time. All five replies were
successful; status reported no error and 50 FPS, the animation remained selected,
and absent external storage retained the existing nullable schema. The record
contains 150 produced refreshes, each 20 ms apart, with nonblack animation pixels.
Mounted/unknown capacity and recovery are additionally covered by the emulator
management and browser tests. These results do not measure real-card latency.

Ignored smoke artifacts are under `build/seed56-smoke/run-7dj0ek65/`, with stdout,
stderr, command script and a machine-readable summary. The record SHA-256 is
`49035a576ee6dc582e39ce111bfdc7f62adb6dcebe4cd8499d8df7e8c71026a1`.

## Release and remaining acceptance

The owner explicitly deferred firmware compilation for this run and requested a
future cross-platform firmware pipeline seed instead. The final cumulative APK
is rebuilt only after seeds 56–59's software work, then delivered to the existing
Drive file with its original signer. This note does not claim those later steps.

Task 4 remains unchecked. An approved board session must repeat two cold starts,
first/warm `space` and concurrent `status` timings within 500 ms, 20–50 FPS without
long gaps, intact catalogs, removal/remount and controlled mutation/out-of-space
safety at brightness no greater than 40. The owner must inspect phone states.
Host/emulator success proves neither physical power readiness nor those timings.
