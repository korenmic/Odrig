# Tasks: shared toolchains, builds alongside, and a narrower walkthrough

Requirements: [requirements.md](requirements.md). Design: [design.md](design.md).
Each task is seed 53's task of the same subject, moved here unchanged.

- [x] 1. The walkthrough (seed 53's task 5). It runs only by `--walkthrough` or its own
      command; its five suites in the copy through the copy's runner; `npm ci` from the
      computer's cache; its emulators given `--parent` and ended; port 8600 checked before
      the page's emulator. Suites: runner, onboarding, then `tests/run.py --walkthrough`.
- [x] 2. Shared toolchains (seed 53's task 6). `ODRIG_TOOLS` in `app/apptool/paths.py` and
      `firmware/fwtool/paths.py`, the shared and the checkout's parts, the setup lock, the
      cloned WLED copy, Gradle without its daemon, `tests.firmware.test_paths` accepting
      the shared Python. Tests in `tests/app` and `tests/firmware` with stand-in folders;
      then a build of the APK and of the firmware from a second checkout. Suites: app,
      firmware, through the runner.
- [ ] 3. Builds alongside (seed 53's task 7). `--builds`: both built while the suites run,
      two slots kept, `tests/apk` after the APK, sizes and SHA-256 printed and reported.
      Tests in `tests/runner` with stand-in builds. Suites: runner, then `--builds`.
- [ ] 4. The documents, every suite, and the measurement (seed 53's task 8).
      `agent/getting-started.md`, `agent/working-rules.md`, `docs/android-app.md`,
      `docs/firmware.md`, `docs/decisions.md`'s line, `docs/drifts.md`'s entries, the
      onboarding pins; every suite alone and through the runner; the full pass with
      `--builds` timed.
