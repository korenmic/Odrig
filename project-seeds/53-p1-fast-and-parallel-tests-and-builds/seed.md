# Fast and parallel tests and builds

## Summary

One runner, `tests/run.py`, runs every suite that works on this computer at the same
time, splits the heavy suites across worker processes, starts the APK and the firmware
builds alongside them, reports the slowest tests, and leaves no process behind. The
full pass that a seed's last task makes today, about 45 minutes one suite after
another, is to take 12 minutes or less on the first computer, and every suite and both
builds are to work from any checkout, with the build toolchains shared across checkouts
instead of being set up in one. Nothing changes in what the suites check.

## Priority

- `P1`

## Depends On

- Seed 10, for the onboarding suite and the pages it pins; seed 11, 26 and 51, for the
  suites and the core's build on Windows, which the runner must keep.
- Seed 02 and 09, for the emulator and the app's suite in Chrome; seed 04 and 17, for
  the firmware and the APK tools and their work folders.

## Product Context

On 2026-10-28 the owner watched a seed's last task, "every suite, the firmware and the
APK", run for over 40 minutes and asked whether the testing could be made faster and
run in parallel, and whether it is already as fast as the computer allows. It is not:
on a Mac with 10 cores and 32 GB, each suite runs alone and single-threaded, one after
another, and the walkthrough suite reruns five of the others in a fresh copy. Measured
on 2026-10-27, one after another: converter's npm suite 10 to 16 s; converter's Python
569 tests 22 to 37 s; onboarding 81 tests 2 s; mapping 43 tests 40 s; firmware tool 626
tests 50 to 58 s; core 883 tests 8 to 9 min; emulator 642 tests 6.5 min; app 305 tests
9 to 10 min in headless Chrome; walkthrough 5 tests 15 to 17 min. The builds take
seconds when their toolchains are set up, but the toolchains, about 12 GB, exist in one
checkout only, so every agent builds there. The same day 14 emulator processes from
earlier test runs were found still running after one to three days, one of them holding
port 8600, left by the preview tool, the walkthrough and the emulator suite. The owner
asked for a seed that makes the testing and the APK and firmware builds as fast and as
parallel as possible, with every gap found on the way closed.

## Technical Constraints

- **One runner.** `tests/run.py`, Python of the venv, no new dependency, works on macOS,
  Linux and Windows (processes are started by `subprocess` and `multiprocessing` with
  the `spawn` method, no shell script, no `fork`). `python tests/run.py` runs every
  suite that works on the computer; `--suites core,app,...` picks some; `--serial`
  runs them one after another as today; `--workers N` sets the workers of the heavy
  suites, by default the computer's cores less two, at least 2, and at most 4 for the
  app suite; `--builds` also builds the APK and the firmware and runs the APK's suite;
  `--walkthrough` adds the walkthrough suite; `--slowest N` prints the N slowest tests
  (30 by default) with their seconds; `--sweep` lists and ends stray processes of
  earlier runs. It prints one line per suite as each ends, `core: 883 tests, 71 s, OK`,
  with failures and errors quoted in full after it, a final line with the wall time, and
  exits non-zero when any suite or build failed. A report, `build/tests/report.json`,
  holds every test's seconds, the suites' counts and the builds' times. The suites'
  own commands of `agent/getting-started.md` stay for running one suite by hand.
- **Discovery kept.** The runner never lists test files: each suite is discovered with
  `unittest`'s discovery, as today, and the heavy suites (core, emulator, app, the
  converter's Python, the firmware tool's) are split by test module across the workers,
  each worker a process that runs its modules by discovery with a module pattern; a
  worker's modules are chosen by a greedy fill from the previous report's seconds, so
  the slowest modules spread first, and evenly by count when no report exists. The
  converter's npm suite, mapping and onboarding run whole, each in its own process; the
  core is built once, with its sanitizers, before the suites that need it start.
- **Isolation.** Two workers of one suite, and two suites, never share a file or a
  port: every test takes its ports from the system (port 0), its folders from a
  temporary directory of its own, and its Chrome profile from one too; any test that
  uses a fixed path under `build/` or a fixed port is changed to take one of its own.
  The firmware tool's suite compiles its host programs into a folder named by the
  worker. Two copies of one suite may then run at once; the rule that forbade it goes.
- **Timing under load.** A test that measures time (the app's reads every two seconds,
  the slider's second, the 200 ms spacing, the emulator's grid and fps, the core's
  deadlines) asserts windows that hold with every core busy: a lower bound and a
  generous upper bound, or the order and count of events rather than their seconds;
  the runner runs the full pass three times in a row on the first computer with every
  worker busy, and a test that fails in any of them is made robust in this seed, not
  retried. The runner has no retry.
- **No process left behind.** Every process a test or a tool starts (an emulator, a
  stand-in server, Chrome, the test host, a preview) carries the marker environment
  variable `ODRIG_RUN=<run id>`, is started in its own process group (a new session on
  macOS and Linux, a new process group on Windows), and is ended by its starter in a
  cleanup that runs on failure too; when a starter dies, its group is ended by the
  runner's sweep, which at the end of a run ends every process whose marker is the
  run's id and says so. `python tests/run.py --sweep` lists every process carrying any
  marker, or started by the emulator, the preview or the walkthrough from a temporary
  folder, and ends it. The preview tool, `python -m preview`, ends the emulator it
  starts when it exits, is interrupted or is killed. The 14 processes found on
  2026-10-28 are ended by the owner with `--sweep` once it exists.
- **The walkthrough.** It keeps its purpose, a fresh copy following the pages, and runs
  only through `--walkthrough`, which a seed's last task passes when
  `agent/getting-started.md` or `agent/animation-guide.md` changed, as the rule already
  says; it runs the suites it checks through the runner, in parallel; it reuses the
  computer's pip and npm caches and links the converter's installed node modules
  instead of installing them again; it ends every emulator it starts; it fails at once
  with a clear line when port 8600 is held, since the page's command uses it. Its time
  falls to the fresh copy and setup, about 3 minutes.
- **The builds, shared toolchains.** The APK tool and the firmware tool take the
  folder of their toolchains from the environment variable `ODRIG_TOOLS`, by default
  `build/` of the checkout as today, so that one folder on a computer serves every
  checkout: the JDK, the Android SDK, Gradle and its caches, the PlatformIO core and
  its cache, the newer environment, the pip and npm caches and the WLED archive are
  shared; the patched WLED copy, PlatformIO's build folder, the staged web folder and
  the outputs stay in the checkout's `build/`. A setup that finds the toolchains present
  does nothing; two setups at once wait on a lock file in that folder. Gradle runs with
  its daemon and parallel option off, so that two checkouts' builds do not fight; the
  firmware build keeps `pio run`'s own parallel compile. The owner sets `ODRIG_TOOLS`
  to the first computer's folder once; the docs say how.
- **Builds alongside the suites.** With `--builds` the runner starts the APK build and
  the firmware build as soon as it starts, in the checkout it runs from (which needs the
  toolchains, by `ODRIG_TOOLS` or its own `build/`), with their own CPU share: the
  suites take the cores less two, and the builds the rest, since both builds are short
  when incremental; the APK's suite runs when the APK is built; the firmware is built
  and never flashed by the runner; the outputs and their SHA-256 are printed. The
  artifacts step, putting the APK and the firmware with the artifacts, stays with the
  task, not the runner.
- **Targets and measurement.** On the first computer the full pass, every suite but the
  walkthrough with both builds, takes 12 minutes or less, and the core, emulator and
  app suites each take a third or less of their time today; `agent/getting-started.md`'s
  times table shows the runner's times and each suite's, measured, and the onboarding
  suite pins the table's form, not its numbers. As with the board's refresh rate, a
  full pass within the target is not made faster for its own sake.
- **The rules and the docs.** `agent/working-rules.md`: the rule to run every suite
  before a merge names the runner; a rule that every test and tool ends the processes
  it starts, with the marker; the rule that forbade two copies of a suite at once goes.
  `agent/getting-started.md`: the runner's command first, then the suites' own, the
  times table, `ODRIG_TOOLS` in the setup, the Windows section. `docs/emulator.md`: the
  preview ends its emulator. `docs/android-app.md` and `docs/firmware.md`: the shared
  toolchains and the lock. `AGENTS.md`'s rules keep their numbers. Rulings beyond this
  seed go to the end of `docs/drifts.md`.
- **Out of scope.** Choosing suites by the files a change touched, a continuous
  integration service, a test framework other than `unittest` and `node --test`, and
  the board's and the air's suites, which need the board and stay serial.

## Required Behavior

1. `python tests/run.py` runs every suite that works on the computer at the same time,
   the heavy suites split across worker processes found by discovery, and prints one
   line per suite, the slowest tests and the wall time, exiting non-zero on any failure.
2. The full pass with both builds takes 12 minutes or less on the first computer, and
   three passes in a row with every worker busy pass.
3. No process outlives its run: tests and tools end what they start, the runner sweeps
   its run's stragglers, `--sweep` lists and ends strays, and the preview ends its
   emulator.
4. The walkthrough runs only when asked, reuses the computer's caches, runs its suites
   in parallel, ends its emulators, and refuses plainly when port 8600 is held.
5. The APK and the firmware build from any checkout with `ODRIG_TOOLS` set, at the same
   time as the suites, without racing each other or another checkout's build.
6. Every suite still passes on Windows through the runner, and the suites' own commands
   still work alone.

## Definition Of Done

1. All test suites that need no board and no phone pass, through the runner and alone.
   The onboarding suite checks the runner's command, the times table's form, the new
   rule and the Windows section; a test of the runner itself checks the split of
   modules, the report, the exit status, `--serial` and `--sweep` on stand-in suites;
   a test starts a child under the marker, kills its parent, and asserts the sweep
   ends the child; the emulator and app suites' tests of timing are shown passing
   three times under full load; the preview's test shows its emulator ended after a
   kill.
2. The runner's times on the first computer are recorded in the times table, and the
   full pass is at or under 12 minutes.
3. `ODRIG_TOOLS` is set on the first computer, the toolchains moved there once, and the
   APK and the firmware built from a second checkout while the first runs its suites.
4. On Windows, `python tests/run.py` runs every suite the computer can run and passes.

## Open Questions

None. Everything here is decided above: the runner's name, options and report; the
split by module through discovery; the isolation and the timing windows; the marker,
the process groups and the sweep; the walkthrough's narrower run; `ODRIG_TOOLS` with
its lock and Gradle's daemon off; the 12-minute target; and what is out of scope.
Nothing needs the owner by the working rules: no command of the installation, no
decision of `docs/decisions.md`, no hardware.

## The Owner's Answers

On 2026-10-28 the owner asked whether the test suites could be made faster and run in
parallel, or whether they already run as fast as the computer allows, and then asked for
this seed with the research needed to detail every optimization step and every other
gap in how the tests, the firmware and the APK are made, without running the suites for
the research.
