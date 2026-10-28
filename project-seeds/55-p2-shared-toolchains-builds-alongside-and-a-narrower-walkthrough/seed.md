# Shared toolchains, builds alongside, and a narrower walkthrough

## Summary

The continuation of seed 53, which built the runner `tests/run.py`, its workers, the
fixes that made the suites fast and robust under load, and the end of processes left
behind. Its four last tasks move here, unchanged in substance: the walkthrough runs only
when asked and runs its suites through the runner; the APK tool and the firmware tool
take their toolchains from one folder shared by every checkout, `ODRIG_TOOLS`; the runner
builds the APK and the firmware while the suites run, with `--builds`; and the documents
describe the runner, its options and the times measured.

## Priority

- `P2`

## Depends On

- Seed 53, `project-seeds/53-p1-fast-and-parallel-tests-and-builds/`: the runner and its
  report, on which every task here builds. Its tasks 5 to 8 are this seed's tasks 1 to 4.

## Product Context

On 2026-10-28 the owner had seed 53 split: what was done and merge-ready, the runner that
took every suite from about 33 minutes one after another to about 7, goes to master, and
the rest becomes this seed. Seed 53's requirements 5 to 8 and its design's parts for the
walkthrough, the shared toolchains and the builds alongside hold here as written there.

## Technical Constraints

- **The walkthrough** (seed 53's requirement 5): run only by `tests/run.py --walkthrough`
  or its own command; its five suites in the fresh copy through the copy's runner; `npm ci`
  there from the computer's npm cache; its emulators given `--parent` and ended; port 8600
  checked free before the page's emulator, failing at once with the holder named.
- **Shared toolchains** (seed 53's requirement 6): `ODRIG_TOOLS` in `app/apptool/paths.py`
  and `firmware/fwtool/paths.py`, shared toolchains and caches there and every checkout's
  own outputs in its `build/`; a setup lock; a checkout's WLED copy cloned with its build
  folder from the shared one; Gradle without its daemon; nothing moved by the tools.
  `tests.firmware.test_paths` accepts the tool's Python under `ODRIG_TOOLS`.
- **Builds alongside** (seed 53's requirement 7): `--builds` builds the APK and the
  firmware while the suites run, two slots kept for them, `tests/apk` after the APK, sizes
  and SHA-256 printed and reported; nothing flashed, uploaded or installed.
- **Documents and measurement** (seed 53's requirement 8): `agent/getting-started.md` with
  the runner first and the times table measured, `ODRIG_TOOLS`, the Windows section;
  `agent/working-rules.md` with the runner before a merge and the rule of processes;
  `docs/android-app.md` and `docs/firmware.md` with the shared toolchains;
  `docs/decisions.md`'s line; the full pass with `--builds` within 12 minutes.

## Required Behavior

1. The walkthrough runs only when asked, through the runner, from the npm cache, and ends
   its emulators.
2. The APK and the firmware build from any checkout with `ODRIG_TOOLS` set, two at once
   without racing.
3. `tests/run.py --builds` builds both while the suites run, within 12 minutes in all.
4. The pages describe the runner, its options, the shared toolchains and the times.

## Definition Of Done

1. Every suite passes alone and through the runner, with `--builds` and `--walkthrough`.
2. The times on the first computer are in the getting-started page's table.

## Open Questions

None. Everything here was decided in seed 53's spec, `docs/specs/53-p1-fast-and-parallel-
tests-and-builds/`, and moved unchanged.

## The Owner's Answers

On 2026-10-28 the owner asked for seed 53 to be split: its finished work made merge-ready,
and its undone tasks moved to a continuation seed, specified to the bare minimum.
