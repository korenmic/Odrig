# Tasks: current limits for the wall and each snake

Requirements: [requirements.md](requirements.md). Design: [design.md](design.md).

- [x] 1. The Python reference and the standalone limiter's end. `odrig/limits.py`: the
      estimate, the fade, the level by halving, the order of requirement 1.5, and the
      strict reader and writer of `limits.json`; `errors.LIMITS_MALFORMED` with its row in
      `docs/reasons.md`; `limits.py` in `tests/converter/test_scope.py`'s list of the
      library; `tests/converter/test_limits.py` with the worked cases and the file's
      refusals; `docs/python-library.md`. The standalone firmware's `limit.h` and
      `limit.cpp`, the `limit` mode of `tests/firmware/host/host.cpp`, `limit.cpp` in
      `tests/firmware/hostprogram.py` and `tests/firmware/test_standalone_limit.py` go;
      `docs/drifts.md` records seed 12's requirement 6, its probe members and its tasks 6
      and 10 giving way. Suites: converter's Python, firmware, onboarding.
- [x] 2. The core's limiting, the budgets' file read at the start, and the host's default.
      `LegInfo`'s budget and `limited`, `Core`'s wall fields, `odrig_host`'s
      `limit_default` in the header and in every record that builds one (the test host
      with `--limit-default MA`, the firmware's shared record at `nullptr`, the emulator's
      binding at NULL), `core/src/limits.cpp` with `limits_apply` called from
      `player_poll` and `limits_read` at the start with its log line, the test host's
      names `limits.json` and `limits.part`, and the reference player of
      `tests/core/support.py` using `odrig.limits` with a show folder's `limits.json`.
      Tests: random pictures and worked cases against the reference, both kinds of budget
      at once, the third pass, a dark picture, a kept picture not limited again, the tests
      limited, the defaults with and without `--limit-default`, the file's strict reading
      and its log line; the start's opens in `tests/core/test_startup.py` (`limits.json`
      after the mapping's); the memory figures; the member lists of
      `tests/core/test_docs.py` and `tests/emulator/test_binding.py`. `docs/core.md`: the
      host's member, the LED data, the start, the memory table, the test host's option.
      Suites: core, emulator, onboarding.
- [x] 3. The commands and the save. `limits_reply` with paging, `limits wall`, `limits
      snake`, `limits default` with their refusals in order, the atomic save copying the
      legs the mapping lacks, `limits.part` cleared at the start, the command tool's forms
      and paging. Tests: the defaults' first save, the same value again, a power loss at
      every step, `--store-fails-at`, the reply's size and paging, a leg's budget kept
      after `mapping set` and `mapping cross on`; the emulator showing limited LEDs once
      budgets are saved; the command tool, with `tests/emulator/test_tool.py`'s session,
      reference replies and pinned lists. `docs/commands.md`, `docs/core.md`,
      `docs/emulator.md`, `agent/vocabulary.md` and the docs tests' pinned lists.
      Suites: core, mapping, emulator, onboarding.
- [x] 4. The firmware. `firmware/usermod/odrig_limit_default.h` and its test, the default
      given at setup, WLED's limiter switched off in memory before every fill and send with
      the outputs' dimming reset, the board suite's limiter tests and the probe suite's
      target test as requirement 4.3 says, with the run of a stored maximum of 0 saving
      `limits wall 730` first and ending with `limits default`; `docs/firmware.md`'s
      limiter section, keeping or updating the phrases `tests/firmware/test_docs.py`
      pins, the WLED-changes table, the probe table, its example line and read-back
      paragraph, the owner's checks 5 and 6; `docs/firmware-additions.md` row 14; and the
      bench rule as rule 10 of "If you have a board" in `agent/working-rules.md`, with
      `tests/onboarding/test_rules.py`'s count of the board rules. Suites: firmware,
      onboarding; the board suite needs the flashed firmware and is left open.
- [ ] 5. The firmware tool. The folder check's name, `install-show --limits` with
      `limits-missing` and `limits-malformed` before the board is touched, the board's file
      kept without it, `read-show` keeping the file; `odrig.limits` in
      `tests/converter/test_scope.py`'s list of what a tool may read; tests;
      `docs/firmware.md`'s usage line, error table and install-show section. Suites:
      firmware, converter's Python, onboarding.
- [ ] 6. The app's panel. `screens/limits.js`, `commands.js`, `client.js`, `index.html`,
      `style.css`, `main.js`: the panel of requirement 6, its reads, saves, refusals,
      warnings and marks, focus and unsaved text kept, an older installation. Tests in
      `tests/app/test_limits.py` with a scenario against the emulator and stand-ins; the
      app's docs and scope tests' lines; `docs/android-app.md`. Suites: app, mapping,
      onboarding.
- [ ] 7. Every suite, the firmware and the APK. `docs/decisions.md`'s dated line, the seed
      in AGENTS.md's list, `docs/drifts.md`'s entry of what this spec decided beyond the
      seed, every suite that runs on this computer, `fw.py build` kept without flashing,
      `app/app.py build` put with the artifacts on the share and on Drive, and the open
      checks said in words: the firmware's flashing and its place with the artifacts, the
      board suite on the probe build with the refresh rate of requirement 7.4, and the
      owner's checks on the installation, after seed 43 is merged and this branch brought
      onto master.
