# Requirements: fast and parallel tests and builds

The seed is `project-seeds/53-p1-fast-and-parallel-tests-and-builds/`. It has no open
questions; the owner ordered on 2026-10-28 that it be specified and built at once, and a
point these requirements decide that the seed leaves open is recorded at the end of
`docs/drifts.md`. By the owner's order of 2026-10-28 the seed was split: requirements 5, 6,
7 and 8 and tasks 5 to 8 moved to seed 55; this seed delivers requirements 1 to 4.

## 1. The runner

1.1 `tests/run.py`, run by the Python of the environment (`.venv/bin/python tests/run.py`,
`python tests/run.py` on Windows), needs nothing but Python's own library and works on
macOS, Linux and Windows: it starts processes with `subprocess` only, never through a
shell, and gives each worker the environment it needs explicitly.

1.2 Without options it runs every suite that works on the computer: the converter's npm
suite, and the suites of `tests/converter`, `tests/onboarding`, `tests/mapping`,
`tests/firmware` (where the firmware tool's work folder or `ODRIG_TOOLS` holds its
Python), `tests/core`, `tests/emulator` and `tests/app` (where Chrome is found). A suite
that cannot run on the computer is named with its reason and is not a failure.
`tests/walkthrough`, `tests/apk`, `tests/board` and `tests/air` are not run without
their options: `--walkthrough` adds the walkthrough, `--builds` the builds and
`tests/apk`; the board's and the air's suites stay with the firmware tool.

1.3 Options: `--suites a,b` runs only those suites, by their folder names and `converter-npm`;
`--serial` runs the suites one after another, each in one process, as the commands of
`agent/getting-started.md` do; `--workers N` sets the number of worker processes of a
split suite, by default the computer's processors less two, at least 2; the app's suite
uses at most 4; `--slowest N` prints the N slowest tests, 30 by default, 0 for none;
`--sweep` lists the stray processes of earlier runs (requirement 4.4) and ends them, and
runs nothing else.

1.4 The core is built once, before any suite that needs it starts, by the command each
system uses today (`make -C core all shared` and the test host on macOS and Linux,
`python core/build.py test` and `shared` on Windows), and no worker builds it again.

1.5 It prints one line for each suite as it ends, `core: 883 tests, 71 s, OK` or
`core: 883 tests, 71 s, FAILED (failures=2)`, the output of every failing test in full
after the line, then the slowest tests, then a last line with the wall time, and ends
with status 0 only when every suite it ran passed and every build it made succeeded.

1.6 It writes `build/tests/report.json`: for every test its suite, its id and its
seconds; for every suite its counts, its seconds and its outcome; for every build its
seconds, its outcome, and its output's size and SHA-256; and the wall time.

## 2. Splitting a suite

2.1 The suites of `tests/core`, `tests/emulator`, `tests/app`, `tests/converter` and
`tests/firmware` are split across worker processes by test module. The modules are found
at run time by the same discovery that `-m unittest discover -s FOLDER -t .` makes; no
file lists them.

2.2 A suite's modules are given to its workers by a greedy fill: in the order of their
seconds in the previous report, the slowest first, each to the worker with the least
seconds so far; a module the report lacks counts as the mean of its suite. Without a
report they are given round the order of discovery.

2.3 The converter's npm suite, `tests/onboarding` and `tests/mapping` run whole, each in
one process. Different suites run at the same time. The total of worker processes never
exceeds the number given by `--workers`, apart from one process for each unsplit suite.

2.4 A test of a split suite passes or fails as it does when its suite runs alone: a
worker runs its modules in their order of discovery, and every class's set-up runs in the
worker that runs the class.

## 3. Isolation and timing

3.1 No two workers, and no two suites, share a written file, a port or a Chrome profile:
every test takes its ports from the system (port 0), its folders and files from a
temporary directory of its own, and its Chrome profile from one too. A test that writes a
fixed path, holds a fixed port, or builds into the checkout at run time is changed so
that it does not; `tests/emulator/__init__.py` does not build the core library when the
runner has built it, and builds it under a lock otherwise.

3.2 A test that measures time asserts what holds with every processor busy: a lower
bound and an upper bound wide enough for a loaded computer, or the order and the number
of events rather than their seconds. The runner has no retry: a test that fails in a
loaded run is made robust.

3.3 Three full passes in a row of `tests/run.py`, on the first computer with its default
workers, pass.

## 4. No process left behind

4.1 Every process that a test or a tool of this repository starts, an emulator, a stand-in
server, Chrome, the test host, a preview, a build, carries the environment variable
`ODRIG_RUN`, set by the runner to its run's id and passed on by every starter; a process
started outside the runner carries the id `manual`.

4.2 Every starter ends what it started in a cleanup that also runs when a test fails or is
interrupted, and starts a long-lived child in a process group of its own (a new session
on macOS and Linux, a new process group on Windows) so that the group can be ended whole.

4.3 An emulator started by the preview, or by a test, ends when its starter is gone: it
watches the process that started it and exits within two seconds after that process
ends, even when the starter was killed without a chance to clean up.

4.4 At the end of a run the runner ends every process that still carries its run's id and
says how many. `tests/run.py --sweep` lists every process that carries any `ODRIG_RUN`,
and every `python -m emulator` started from a temporary folder or from a
`build/preview/` folder, with its age and command, and ends them.

## 5. The walkthrough

5.1 The walkthrough runs only through `--walkthrough` or its own command. A seed's last
task passes `--walkthrough` when `agent/getting-started.md` or `agent/animation-guide.md`
changed, as the page already says.

5.2 In its fresh copy it runs the page's commands as today, but the five suites it checks
run through the copy's own `tests/run.py` with workers; `npm ci` there uses the computer's
npm cache, preferring it to the network.

5.3 It ends every emulator it starts, and when port 8600 is held before it starts the
page's emulator it fails at once with a line that names the port and the process.

## 6. Shared toolchains

6.1 The APK tool and the firmware tool take the folder of their toolchains from the
environment variable `ODRIG_TOOLS`; without it, the checkout's `build/` as today.
Shared there: the JDK, the Android SDK, Gradle and its user home with its caches, the
Android user folder, the npm caches, the firmware tool's Python environment, PlatformIO's
core and cache, the newer environment, the pip cache, and the WLED archive. Per checkout,
in its `build/`: the patched WLED copy with PlatformIO's build folder, the staged web
folder, `app/node_modules`, the Android project's build folder, and every output.

6.2 A setup that finds the toolchains present in `ODRIG_TOOLS` does nothing but the
checkout's own part. Two setups at once, from two checkouts, wait for each other on a lock
file in that folder; the second does nothing that the first has done.

6.3 The firmware tool makes a checkout's WLED copy by cloning the shared folder's
prepared copy with its build folder, copy-on-write where the file system can, so that a
checkout's first firmware build is incremental.

6.4 Two builds at once from two checkouts, an APK and a firmware or two of a kind, both
succeed.

## 7. Builds alongside the suites

7.1 With `--builds` the runner builds the APK and the firmware in its own checkout, by the
tools' own `build` commands, while the suites run, and runs `tests/apk` once the APK is
built. It never flashes, uploads or installs anything.

7.2 While builds run the suites use the processors less two, and the builds the rest.

7.3 It prints each build's line, `apk: 16,893,191 bytes, 9 s, SHA-256 37e3c75c...`, and
records it in the report; a build that cannot run, for want of its toolchain, is named
with its reason and is a failure only when `--builds` was asked for.

## 8. The target, the rules and the docs

8.1 On the first computer, `tests/run.py --builds` takes 12 minutes or less, and each of
the core's, the emulator's and the app's suites a third or less of its time run alone
today. A run within the target is not made faster for its own sake.

8.2 `agent/getting-started.md` gives the runner's command first among the tests, then each
suite's own command, which keeps working alone; its times table gives each suite's time
alone and the runner's, measured; it says how to set `ODRIG_TOOLS`, and the Windows
section gives the runner's command there.

8.3 `agent/working-rules.md`: the rule to run every suite before a merge names the
runner; a new rule says that every test and tool ends what it starts and carries
`ODRIG_RUN`; the walkthrough's rule says when to pass `--walkthrough`.

8.4 `docs/emulator.md` says that the emulator ends when the preview, or the test, that
started it is gone; `docs/android-app.md` and `docs/firmware.md` describe `ODRIG_TOOLS`,
its lock and the cloned WLED copy; `docs/decisions.md` records the runner and the shared
toolchains; `docs/drifts.md` records what this spec decided beyond the seed.

8.5 Every suite passes alone, by its own command, and through the runner. The onboarding
suite pins the runner's command, the form of the times table and the new rule; the
runner's own suite, `tests/runner`, checks the split, the report, the exit status,
`--serial`, `--sweep` and a child that outlives a killed parent being ended.

8.6 Windows: the runner is written for it as for macOS; its run there is left open, said
in words, since the first computer is a Mac.
