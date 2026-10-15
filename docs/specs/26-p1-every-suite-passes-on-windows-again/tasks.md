# Tasks: every suite passes on Windows again (seed 26)

The work of seeds 09, 11, 14, 17, 18, 19, 20 and 23 is in `master` before these tasks
start. Where the real code differs from what the design relies on, follow the code and
record the difference in `docs/drifts.md`.

No task needs the board or a phone. Every task is done and checked on Windows.

Rules for every task:

- One task is one commit. The same commit ticks the task's checkbox in this file.
- Stage named paths only, never `git add -A`, `git add .` or `git commit -a`. After
  committing, read `git show --stat`.
- Prove it fails first: before the fix, run the tests the task names on Windows, see them
  fail, and put the failure seen in the commit message.
- Before committing, run on Windows, one at a time, the suites the task touches, and after
  the last task every suite: `npm test --prefix converter`,
  `.venv\Scripts\python -m unittest discover -s tests/converter -t .`,
  `.venv\Scripts\python core/build.py test`,
  `.venv\Scripts\python -m unittest discover -s tests/emulator -t .`,
  `.venv\Scripts\python -m unittest discover -s tests/app -t .` and
  `.venv\Scripts\python -m unittest discover -s tests/onboarding -t .`. No pipe hides a
  suite's status. Two suites never run at once.
- After a suite, no `python`, `node` or `chrome` process it started runs, and ports 8600
  and 8601 are free. A Chrome is only ever headless, with a profile folder of its own, and
  is never started with `--version`.
- Nothing changes on macOS or Linux: each change is a no-op there, as the design says.
- Code and tests state what they do now: no comment about seeds, tasks, dates or earlier
  versions. No command, script or document lists test files.
- Answers to questions that come up are recorded in `docs/drifts.md`, not asked.

- [x] 1. The emulator lets go of a folder it reads
  - Set `"state": "in_progress"` in
    `project-seeds/26-p1-every-suite-passes-on-windows-again/state.json`.
  - `emulator/host.py`: one function opens a file to read; on Windows with read, write and
    delete sharing; `open()` and `read_at()` use it, for the show and for the drive.
  - Prove it fails first: `test_binding`'s two tests and `test_drive`'s pull-out test fail
    with `PermissionError: [WinError 32]`.
  - Requirements: 1.1, 1.2, 1.5, 7.1, 7.2

- [x] 2. The preview ends on Ctrl+Break, and its tests stop it on Windows
  - `preview/__init__.py`: SIGBREAK, where the system has it, ends the preview as SIGTERM
    does.
  - `tests/emulator/test_preview.py`: the preview in its own group, stopped with
    Ctrl+Break on Windows; the held port; one helper for a test that names no port, which
    reads the `port 8600 is taken` line when 8600 is held by another program.
  - Prove it fails first: `test_a_file_plays_alone_until_the_preview_is_interrupted` fails
    with `module 'os' has no attribute 'killpg'`, and the next tests with port 8600 taken
    and `WinError 10022`.
  - Requirements: 1.3, 2.1, 2.3, 3.1, 3.2, 3.3, 5.1, 7.1

- [ ] 3. `odrigctl --log` ends on Ctrl+Break, and the tests of its stop run on Windows
  - `odrigctl/cli.py`: for `--log`, SIGBREAK where the system has it ends the tool as
    Ctrl+C does.
  - `tests/emulator/test_tool_log.py`: the program in its own group, stopped with
    Ctrl+Break on Windows and SIGINT elsewhere; `needs_interrupt` goes.
  - Prove it fails first: with the skip removed and the test sending Ctrl+Break, the stop
    tests fail on Windows before the change of `odrigctl/cli.py`.
  - Requirements: 2.2, 2.3, 2.4, 5.1, 7.1

- [ ] 4. The demo test where Python's zlib is zlib-ng
  - `tests/emulator/test_demo.py`: the JSON files byte for byte; the `.odrg` files byte
    for byte unless `zlib.ZLIB_RUNTIME_VERSION` names zlib-ng, and then by header and
    decoded records.
  - Prove it fails first: the test fails on Windows, `hello.odrg` 1210 bytes against 1213.
  - Requirements: 1.4, 7.1

- [ ] 5. The app's suite finds Chrome on Windows and lays out the page as on macOS
  - `tests/app/support.py`: `chrome()` with the places of Windows after `ODRIG_CHROME`;
    `--hide-scrollbars` for every headless Chrome of the suite.
  - Prove it fails first: without `ODRIG_CHROME`, `test_docs`'s two tests fail with `no
    Chrome was found`; with it, `test_look`'s buttons test measures 313 against 328.
  - Requirements: 4.1, 4.2, 4.5, 5.2, 7.1

- [ ] 6. The app's tool and its tests on Windows
  - `app/apptool/webserver.py`: `allow_reuse_address` only where the system is not
    Windows.
  - `tests/app/test_tool.py`: `serve` stopped with Ctrl+Break on Windows; fake programs as
    `.cmd` files on Windows, made by one helper; executable bits checked where the system
    keeps them; the expected `PATH` made with `os.path.join` and `os.pathsep`.
  - Prove it fails first: the eight tests of the design's table fail on Windows as it
    says.
  - Requirements: 4.3, 4.4, 2.3, 5.1, 7.1

- [ ] 7. The documents, and the seed done
  - Change first the onboarding tests that hold the sentences below, and see them fail.
  - `AGENTS.md`, "If you work on Windows"; `agent/getting-started.md`, "On Windows", with
    the app's suite in its list, within 200 lines; `docs/emulator.md` on ending the
    preview and `odrigctl --log` on Windows.
  - One entry at the end of `docs/drifts.md`.
  - Run every suite on Windows, one at a time; all pass; nothing is left running.
  - Set the seed's `state.json` to `completed`, with `completedAt`.
  - Requirements: 6.1, 6.2, 6.3, 5.1, and the definition of done
