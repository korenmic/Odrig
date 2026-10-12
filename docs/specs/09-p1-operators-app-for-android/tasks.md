# Tasks: the operators' app, command and control (seed 09)

Seeds 07, 08 and 16 are implemented before these tasks start: the tasks use the command
`list`, the board's network `odrig`, and the playlist with `play all`. Where the real
code differs from what this spec's design relies on, follow the code and record the
difference in `docs/drifts.md`.

Tasks 2 to 5 need the Chrome that is installed, and nothing that is not in the
repository. Task 6 needs the network, for npm, two archives, the SDK's packages and
Gradle: about 740 MB into the project folder, and the one licence of the SDK accepted.
Before its first download the owner is told the files, their sources and their sizes, and
says yes. Task 9 needs the owner and a phone. The design's tables "Assumed, to be
verified" name what tasks 2 and 6 settle: each writes what it found into
`docs/drifts.md`, and task 8 writes it into `docs/android-app.md`. No task needs the
board.

Rules for every task:

- One task is one commit. The same commit ticks the task's checkbox in this file.
- Stage named paths only, never `git add -A`, `git add .` or `git commit -a`. After
  committing, read `git show --stat`.
- The tests of a task are in the task's commit. Before committing, run the suites that
  need no board and no phone, from the repository root; all pass:
  `.venv/bin/python -m unittest discover -s tests/converter -t .`,
  `npm test --prefix converter`, `make -C core test`,
  `python3 -m unittest discover -s tests/emulator -t .`,
  `python3 -m unittest discover -s tests/onboarding -t .`, `python3 firmware/fw.py test`,
  and from task 2 on `python3 -m unittest discover -s tests/app -t .`.
  Run them so that a failing suite stops the commit: no pipe hides its status.
- Where a task says "Prove it fails first", run the test against the state described,
  watch it fail, and put the observed failure in the commit message.
- Code and tests state what they do now. No comment about seeds, tasks, dates or earlier
  versions. No command, script or document lists test files.
- The web code is plain: a browser runs the files of `app/www/` as they are. Nothing
  transpiles, bundles or generates a file of it, and it imports only its own files.
- The app sends the eight command lines of Requirement 1 and no other. No file of
  `core/`, `converter/`, `odrig/`, `odrigctl/` or `firmware/` changes.
- Everything a task installs goes into `app/node_modules/` or `build/app/`. Nothing is
  installed in the system, and no setting of the Mac is changed.
- No agent joins the Mac to the board's network, and no test needs a phone.
- A page changes in the commit that changes the code it describes.
- Before a push, fetch: another contributor pushes to this repository.
- Answers to questions that come up are recorded in `docs/drifts.md`, not asked. What
  needs the owner is asked in words: an addition to the command list, hardware, a
  download, and what only a phone shows.

- [x] 1. The emulator on the local network
  - Set `"state": "in_progress"` in
    `project-seeds/09-p1-operators-app-for-android/state.json`.
  - `emulator/httpd.py` and `emulator/app.py`: `--lan`, the `lan:` line, the warning, the
    usage error with `--record`, as the design's section has them. The line port and the
    serial port stay as they are.
  - `tests/emulator/`: the option among the options; the socket of the page with and
    without it; a reply on 127.0.0.1 and on the address of the `lan:` line; the line port
    still on 127.0.0.1; the addresses a source may name.
  - `docs/emulator.md`: the usage line, the table of options, the `lan:` line, the
    warning, and a section on reaching the emulator from a phone.
  - Prove it fails first: the test that starts the emulator with `--lan`, against the
    emulator as it is, fails: the option is a usage error.
  - Requirements: 12.1, 12.2, 12.3, 12.4

- [x] 2. The tool's `serve`, the suite's harness, the address, the client and the target screen
  - `app/app.py` and `app/apptool/`: the command `serve`, the exit statuses and the error
    line. The other commands come with task 6.
  - `tests/app/support.py` and `tests/app/page/`: the emulator, the stand-in target, the
    server, Chrome and the driver. Settle C1 to C3 and record each.
  - `app/www/`: `index.html`, `target.js`, `commands.js` for `status`, `client.js` with
    its queue and its state of the connection, `main.js`, `screens/target.js`, and the
    style as far as this screen needs it.
  - `tests/app/test_target.py`, `test_scope.py`, and `test_tool.py` for `serve`.
  - Prove it fails first: the scenario that reads `Answers` against an emulator, with a
    client that never sends `status`, fails: the words never appear.
  - Requirements: 1.2, 1.6, 2.1, 2.2, 2.3, 2.4, 2.5, 3.1, 3.2, 3.3, 3.4, 3.5, 8.1, 8.4,
    8.6, 13.6, 13.8, 14.1, 14.2

- [x] 3. The show screen: the state and the list
  - `commands.js` for `list`; `client.js`: when `status` and `list` are due, a list in
    parts, nothing sent while hidden; `screens/show.js` without its controls.
  - `tests/app/test_show.py`.
  - Prove it fails first: the test of a show of 40 animations, against a client that
    asks for `list` once, fails: the rows end where the first reply ends.
  - Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 5.1, 5.2, 5.3, 5.4, 5.5, 5.6

- [ ] 4. The controls
  - `commands.js` for `play <id>`, `play all`, `on`, `off` and `brightness <n>`; the
    order of the queue and a waiting brightness replaced; the buttons and the slider of
    `screens/show.js`.
  - `tests/app/test_controls.py`.
  - Prove it fails first: the test that counts `brightness` lines while the slider is
    moved for a second, against a slider that sends on every move, fails: the log has
    more than five.
  - Requirements: 1.3, 6.1, 6.2, 6.4, 7.1, 7.2, 7.3, 7.4, 8.2, 8.3, 8.5

- [ ] 5. Every message, the look and back
  - `messages.js` with the whole table and the codes the app cannot get; a message that
    stays; the list asked for again after `unknown-id`. `style.css` to the design's
    measures; the history entries.
  - `tests/app/test_messages.py` and `test_look.py`.
  - Prove it fails first: the test that reads the error codes of `docs/commands.md`,
    against a table without `show-invalid`, fails and names the code.
  - Requirements: 6.3, 9.1, 9.2, 9.3, 9.4, 11.1, 11.2, 11.3, 11.4, 11.5, 11.6, 11.8

- [ ] 6. The toolchain and a first APK
  - Tell the owner the files to be downloaded, their sources and their sizes, and wait
    for a yes.
  - Read F1, F3, F7, F8, F10 and F11 of the design again at their sources, and pin what
    is current; a difference is a drift.
  - `app/apptool/`: `setup`, `build` and `install`. `app/toolchain.json`,
    `app/package.json` with its lock file, `app/capacitor.config.json`, `.gitignore`,
    `app/www/old.html`.
  - `python3 app/app.py setup`, then `cap add android` once: `app/android/` is tracked as
    it was made, with the checksum of Gradle in the wrapper's properties.
  - `python3 app/app.py build` makes `build/app/odrig-debug.apk` with the web code in it.
  - `tests/app/test_tool.py` for these commands; it downloads nothing.
  - Settle T1 to T7 and record each in `docs/drifts.md`, with the size of the work folder
    and the time of a first and of a second build.
  - Prove it fails first: the test of an archive with another SHA-256, against a tool
    that unpacks without comparing, fails: the archive is unpacked.
  - Requirements: 1.1, 1.5, 13.1, 13.2, 13.3, 13.4, 13.5, 13.7

- [ ] 7. The sender, the app's own Android files and the APK
  - `TargetPlugin.java`, `MainActivity.java`, `AndroidManifest.xml` and
    `network_security_config.xml`, as the design has them.
  - `python3 app/app.py build`; `tests/apk/test_apk.py` passes on the APK it made.
  - Prove it fails first: `tests/apk`, against the APK of task 6, fails: the permission
    `CHANGE_NETWORK_STATE` is not in it.
  - The commit message says that no test runs the sender, and what the build printed:
    the size and the SHA-256 of the APK.
  - Requirements: 10.1, 10.2, 10.3, 10.4, 11.7, 14.3

- [ ] 8. The documents and the last run
  - `docs/android-app.md` as the design's "Documents" has it, with what tasks 2 and 6
    found and the check on a phone as numbered steps. `docs/wifi.md`, `docs/decisions.md`
    with a line in its change log, `AGENTS.md`, `README.md` and the pages of `agent/`.
    `tests/app/test_docs.py`.
  - Record in `docs/drifts.md` what goes beyond the seed, as the design lists it.
  - Run every suite that needs no board and no phone, and `tests/apk`.
  - The seed's state stays `in_progress`: its last item is the owner's.
  - Requirements: 14.4, 15.1, 15.2, 15.3

- [ ] 9. The check on a phone
  - The owner installs `build/app/odrig-debug.apk` and goes through "The check on a
    phone" of `docs/android-app.md`, against an emulator started with `--lan` and against
    the board on its own network.
  - What the owner found is written into `docs/android-app.md`, with P1 to P5 of the
    design each answered, and a fault found becomes a seed.
  - Set the seed's `state.json` to `completed`, with `completedAt`.
  - Requirements: 10.5, 16.1, 16.2
