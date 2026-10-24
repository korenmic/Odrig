# Tasks: readiness progress and retained fault diagnostics (seed 33)

Seeds 28 to 32 and 38 are implemented before these tasks start. Where the real code
differs from what the design relies on, follow the code and record the difference in
`docs/drifts.md`. Tasks 1 to 5 need no board; task 6 needs the board.

Rules for every task:

- One task is one commit, which ticks its checkbox here. Stage named paths only.
- Before each commit the suites of the parts the task changed pass, with the core's, the
  onboarding's and the documents' tests always among them; a change of the core runs the
  core's and the emulator's suites, one of the app the app's, one of the firmware or its
  tool `python3 firmware/fw.py test`. Every suite that needs no board passes at the end
  of the seed.
- "Prove it fails first": watch the test fail on the code before, and put what was seen
  into the commit message.
- Code states what it does now; no comment about seeds, tasks or dates.
- The members of `status` (`readiness`, `checked`, `to_check`, `unavailable`,
  `checking`, `host`) and the command `fault` are the additions to the command list,
  approved in advance by the owner; each goes into `docs/commands.md` and the change log
  of `docs/decisions.md`.
- Answers to questions that come up go into `docs/drifts.md`.

- [x] 1. The regression: a status that says nothing of the check
  - Set the seed's `state.json` to `in_progress`.
  - `tests/core/test_readiness.py`: a status during the check, after it with an
    unavailable animation, and of an invalid show is to report its readiness and counts;
    expected failures until task 2.
  - `tests/firmware`: `install-show` against a board that is still checking waits;
    expected failure until task 4.
  - Prove it fails first: the status has no `readiness`; the tool's wait ends at the first
    list.
  - Requirements: 8.1

- [x] 2. Readiness, counts and `fault` in the core
  - `core/src/commands.cpp`, `core.cpp`, `core_state.h`: the members of `status`, the
    command `fault`.
  - `tests/core/support.py`: the reference player's counts; the tests that compare
    `status` replies.
  - Tests: every state; `fault` before and after a fault of each work.
  - `docs/commands.md`, `docs/core.md`, `docs/decisions.md`.
  - Requirements: 1.1 to 1.4, 2.1, 2.2, 7.1, 8.2

- [x] 3. The host's name: `about`
  - `core/include/odrig_core.h`, `core/src/commands.cpp`: `about` and `host`.
  - `tests/core/host/host.cpp`: `--about TEXT`; `emulator/binding.py`, `emulator/host.py`:
    the emulator's `about`.
  - Tests: `host` with and without `about`; the emulator's over HTTP and the line port.
  - `docs/core.md`, `docs/emulator.md`.
  - Requirements: 3.1, 3.2, 3.3 (the emulator)

- [x] 4. The firmware: its name, the kept fault, and the tool's outcomes
  - `firmware/usermod/odrig_files.cpp` or `odrig_usermod.cpp`: `about`;
    `firmware/usermod/odrig_log.cpp`: the kept record; `firmware/fwtool/board.py`,
    `cli.py`: `ready`, `outcome`.
  - Tests: `tests/firmware`: the outcomes; the kept record in the firmware's test host.
  - `docs/firmware.md`: `about`, the kept record, the outcomes, "Capturing evidence".
  - Requirements: 3.3, 4.1 to 4.3, 5.1 to 5.3, 8.3

- [ ] 5. The app
  - `app/www/commands.js`, `screens/show.js`, `screens/target.js`, `messages.js`.
  - `tests/app`: a target that checks and then is degraded; the target screen's host and
    fault.
  - `docs/android-app.md`; the state stays `in_progress` for task 6.
  - Requirements: 6.1 to 6.3, 8.4, 8.5

- [ ] 6. The board
  - In the run's board session, with the firmware of the run at brightness 40 or less:
    the time to the first reply, the first list, the first picture and the end of the
    check, measured apart; `host` read; a quarantine, a reset by `restart`, and the
    retained text in the log; `install-show`'s outcome. Recorded in `docs/firmware.md`,
    "Verified on the board"; the seed `completed` when all is seen, otherwise what is
    missing said there.
  - Requirements: 4.1, 8.5
