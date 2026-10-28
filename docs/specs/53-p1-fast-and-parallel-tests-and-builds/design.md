# Design: fast and parallel tests and builds

Requirements: [requirements.md](requirements.md).

## What is slow today, and why

Measured on the first computer, each suite alone, one after another: the converter's npm
suite 10 to 16 s; `tests/converter` 22 to 37 s; `tests/onboarding` 2 s; `tests/mapping`
38 to 42 s; `tests/firmware` 48 to 58 s; `tests/core` 473 to 547 s; `tests/emulator` 386
s; `tests/app` 555 to 622 s; `tests/walkthrough` 873 to 1,004 s, which reruns five of the
others in a fresh copy. About 45 minutes in all, on 10 processors of which one is busy.
Each suite is one `unittest` process, and the suites follow each other.

What stands in the way of running them at once, read from the code:

- `tests/emulator/__init__.py` runs `make -C core shared` (or `core/build.py shared`)
  whenever it is imported, so every process that imports the emulator's or the app's
  tests rebuilds the library into `core/build/`; two at once write the same files.
- `make -C core test` builds the sanitized test host and the library, then runs the suite;
  the build must happen once, before the core's workers.
- The emulator's and the app's tests already take port 0, temporary serial links,
  temporary show folders and temporary Chrome profiles (`tests/emulator/support.py`,
  `tests/app/support.py`); the firmware suite compiles its host program into a temporary
  folder per process (`tests/firmware/hostprogram.py`). A fixed path or port that the
  first loaded run shows is mended where it is found.
- The preview (`preview/__init__.py`) starts its emulator in a process group of its own
  and ends it on an interrupt or SIGTERM, but a preview killed without warning leaves its
  emulator running; tests that start emulators end them in their cleanups, which do not
  run when the test process itself is killed. Fourteen such emulators were found alive
  for one to three days on 2026-10-28.

## `tests/run.py`

A script of Python's own library, run from the repository's root. Its parts:

- **Suites.** A table in the runner of the suite names and how each is run: the folder
  under `tests/` with `unittest` discovery, or `npm test --prefix converter`; whether it is
  split; what it needs (the core built, Chrome, the firmware tool's Python, the APK). The
  folders themselves are not listed: a test folder the table does not know is run whole,
  by discovery, and named in the output, so that a new suite is never skipped.
- **Discovery of modules.** For a split suite the runner runs
  `unittest.defaultTestLoader.discover(folder, top_level_dir=".")` in a short child
  process and takes the module names of the tests found, in their order.
- **Workers.** A worker is a child process, `python -m tests.runner_worker` (a module of
  the runner's own, beside it), given its suite, its modules and a report path. It loads
  each module by name, runs it with a `unittest.TextTestRunner` whose result records each
  test's seconds, and writes its results as JSON lines. A worker's standard output and
  error go to a log in `build/tests/<run id>/`; the runner prints a failing worker's
  failures from its results.
- **Scheduling.** A pool bounded by `--workers`: the split suites' workers and the whole
  suites are queued, the slowest first by the last report, and started as slots free.
  With `--builds`, two slots are kept for the builds while they run.
- **The core's build** runs first and alone: `make -C core all shared build/odrig_host`
  (the targets `make -C core test` builds before its suite) on macOS and Linux,
  `python core/build.py test` and `shared` on Windows. The runner then sets
  `ODRIG_CORE_BUILT=1` for every child, and `tests/emulator/__init__.py` builds only when
  that is not set, under a lock file `core/build/.lock` when it does.
- **The run's id** is the time and the runner's process id; it is set as `ODRIG_RUN` for
  every child, which passes it on.
- **Output and report** as requirement 1.5 and 1.6; `build/tests/report.json` is replaced
  at each run, and the run's logs are kept until the next run.
- **`--serial`** runs each suite in one process by its own command, one after another, for
  comparison and for a computer with one processor.

## Process groups and the sweep

- A helper, `tests/children.py`, starts a child with `ODRIG_RUN` passed on, in a new
  session on macOS and Linux (`start_new_session=True`) and with
  `CREATE_NEW_PROCESS_GROUP` on Windows, and ends it and its group: an interrupt, a wait
  of two seconds, then a kill of the group (`os.killpg`, or `taskkill /T /F` on Windows).
  The tests' supports (emulator, app, mapping, walkthrough) and the preview use it.
- **The starter watch.** The emulator takes `--parent PID`: it checks every second that
  that process lives (`os.kill(pid, 0)`, or `OpenProcess` on Windows) and ends itself,
  as on an interrupt, when it does not. The preview and the tests' supports pass their own
  process id. This catches a starter killed without warning, which no cleanup can.
- **The sweep.** On macOS and Linux the runner lists processes with `ps -axww -o
  pid,etime,command` and reads each candidate's environment where the system allows
  (`ps -E` on macOS, `/proc/<pid>/environ` on Linux); on Windows with `wmic` or
  PowerShell's `Get-CimInstance Win32_Process`. A process carrying `ODRIG_RUN`, or a
  `python -m emulator` whose show folder is under a temporary folder or a `build/preview/`
  folder, is a stray. At the end of a run the runner ends its own run's strays;
  `--sweep` lists all strays with their age and ends them.

## The walkthrough

`tests/walkthrough` keeps its fresh copy and its page commands. Its run of the five
suites in the copy goes through the copy's `tests/run.py --suites` with workers. It sets,
for the commands it runs in the copy, `npm_config_cache` to the computer's npm cache and
`npm_config_prefer_offline=true`, so that `npm ci` installs from the cache. It passes
`--parent` to every emulator it starts and ends them in its cleanups; before it starts the
page's emulator on 8600 it checks that the port is free and fails at once otherwise,
naming the process that holds it.

## Shared toolchains

- `app/apptool/paths.py` and `firmware/fwtool/paths.py` take `TOOLS` from `ODRIG_TOOLS`,
  else `ROOT / "build"`; the shared parts named by requirement 6.1 are under `TOOLS / "app"`
  and `TOOLS / "firmware"`, the checkout's own under `ROOT / "build"`. When `ODRIG_TOOLS`
  is not set, every path is what it is today.
- **The lock.** `TOOLS / "setup.lock"`, taken by `setup` with an exclusive create and
  released at its end; a setup that finds it waits, up to a limit, then reads the setup
  records and does only what is still missing. A lock older than an hour whose owner is
  gone is taken over.
- **The WLED copy.** The firmware tool keeps a prepared copy, patched and once built, in
  `TOOLS / "firmware" / "WLED"`; a checkout without its own copy gets one by
  `cp -c -R` on macOS (copy-on-write on APFS), `cp --reflink=auto -R` on Linux, a plain
  copy elsewhere, with its `.pio` build folder, and patches it as today. The build of a
  checkout then compiles only what its own sources change.
- **Gradle** runs with `--no-daemon`, so that no daemon outlives a build, with its user
  home shared; Gradle locks its caches itself, so two builds at once are safe.
- **What moves.** Nothing is moved by the tools. The owner points `ODRIG_TOOLS` at the
  first computer's existing work folders once; the docs say how, and that the folder
  `scratch/combine-trial/build` holds them today.

## Builds alongside

With `--builds` the runner starts `python3 app/app.py build` and `python3 firmware/fw.py
build` as children, in its checkout, with `ODRIG_TOOLS` passed on, as soon as the core is
built; then `tests/apk` once the APK is built. Each build's output is read for its size
and SHA-256. A build that cannot find its toolchain fails with the tool's own reason.

## What is out of scope

Choosing suites by the files a change touched; a continuous integration service; another
test framework; parallel runs of `tests/board` and `tests/air`, which need the board.

## Tests

- `tests/runner`: stand-in suites in a temporary folder (passing, failing, slow, one that
  prints) run through the runner: the split by module and the greedy fill from a report,
  the lines and the report, the exit status, `--serial`, `--suites`, a stray started under
  the run's id ended at the end, `--sweep` on a stand-in stray, and a child started with
  `--parent` of a process that is then killed, ended within two seconds.
- The emulator's suite: `--parent` ends the emulator; the preview's emulator ends after
  the preview is killed.
- The app's and the firmware tool's suites: `ODRIG_TOOLS` paths, the lock, the WLED clone
  (with stand-in folders).
- The onboarding suite: the runner's command on the page, the times table's form, the new
  rule.
