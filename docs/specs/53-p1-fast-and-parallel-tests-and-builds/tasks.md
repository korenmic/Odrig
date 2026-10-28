# Tasks: fast and parallel tests and builds

Requirements: [requirements.md](requirements.md). Design: [design.md](design.md).

- [x] 1. The runner and its suite. `tests/run.py` and `tests/runner_worker.py`: the
      suites' table, discovery of modules, workers, the greedy fill from the report,
      `--suites`, `--serial`, `--workers`, `--slowest`, the lines, the failures, the
      report `build/tests/report.json`, the exit status; the core built once first with
      `ODRIG_CORE_BUILT` set, and `tests/emulator/__init__.py` building only without it,
      under `core/build/.lock`. `tests/runner` with stand-in suites. The page's command
      of the new suite and the onboarding suite's table of suites. Suites: runner,
      onboarding, emulator.
- [x] 2. Isolation under load. Run `tests/run.py` with the default workers and mend
      every failure that comes from two workers or two suites sharing a file, a port or
      a build: each test made to take its own, the failure seen first in the loaded run
      and quoted in the commit. Suites: runner, then every suite through the runner.
- [x] 3. Timing under load. Run `tests/run.py` three times in a row; every test that
      fails for time is made to assert what holds on a loaded computer, as requirement
      3.2 says, the failure seen first and quoted. Suites: every suite through the runner,
      three passes.
- [x] 4. No process left behind. `tests/children.py`; `ODRIG_RUN` passed on by every
      starter; process groups; the emulator's `--parent`; the preview, the tests'
      supports and the walkthrough passing it; the runner's end-of-run sweep and
      `--sweep`. Tests: a killed starter's emulator ends within two seconds; the runner
      ends its run's strays; `--sweep` on stand-in strays. Suites: runner, emulator, app,
      mapping, through the runner.
- [ ] 5. The walkthrough. It runs only by `--walkthrough` or its own command; its five
      suites in the copy through the copy's runner; `npm ci` from the computer's cache;
      its emulators ended; port 8600 checked before the page's emulator. Suites: runner,
      onboarding, then `tests/run.py --walkthrough`.
- [ ] 6. Shared toolchains. `ODRIG_TOOLS` in `app/apptool/paths.py` and
      `firmware/fwtool/paths.py`, the shared and the checkout's parts, the setup lock,
      the cloned WLED copy, Gradle without its daemon. Tests in `tests/app` and
      `tests/firmware` with stand-in folders. Then, on the first computer, a build of the
      APK and of the firmware from this checkout with `ODRIG_TOOLS` pointing at
      `scratch/combine-trial/build`. Suites: app, firmware, through the runner.
- [ ] 7. Builds alongside. `--builds`: the APK and the firmware built while the suites
      run, two slots kept for them, `tests/apk` after the APK, the builds' lines, sizes
      and SHA-256 in the output and the report; nothing flashed, uploaded or installed.
      Tests in `tests/runner` with stand-in builds. Suites: runner, then
      `tests/run.py --builds`.
- [ ] 8. The documents, every suite, and the measurement. `agent/getting-started.md`:
      the runner first, the times table measured, `ODRIG_TOOLS`, the Windows section;
      `agent/working-rules.md`: the runner before a merge, the rule of processes, the
      walkthrough's rule; `docs/emulator.md`, `docs/android-app.md`, `docs/firmware.md`;
      `docs/decisions.md`'s dated line; `docs/drifts.md`'s entries; the onboarding pins.
      Every suite passes alone and through the runner; the full pass with `--builds` is
      timed against the baseline of every suite one after another and the builds made
      today, and the times said in words.
