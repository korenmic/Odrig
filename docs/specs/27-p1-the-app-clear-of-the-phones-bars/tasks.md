# Tasks: the app clear of the phone's bars (seed 27)

Seeds 09, 17 and 25 are implemented before these tasks start: the app's three screens, its
three fields, and the rules of a long press. Where the real code differs from what this
spec's design relies on, follow the code and record the difference in `docs/drifts.md`.

Task 1 needs Chrome and nothing that is not in the repository. Task 2 builds the APK with
the toolchain of `build/app/`, which seed 09 set up. Task 3 needs the owner and a phone.
No task needs the board.

Rules for every task:

- One task is one commit. The same commit ticks the task's checkbox in this file.
- Stage named paths only, never `git add -A`, `git add .` or `git commit -a`. After
  committing, read `git show --stat`.
- The tests of a task are in the task's commit. Before committing, run the suites that
  need no board and no phone, from the repository root; all pass:
  `.venv/bin/python -m unittest discover -s tests/converter -t .`,
  `npm test --prefix converter`, `make -C core test`,
  `python3 -m unittest discover -s tests/emulator -t .`,
  `python3 -m unittest discover -s tests/onboarding -t .`, `python3 firmware/fw.py test`
  and `python3 -m unittest discover -s tests/app -t .`.
  Run them so that a failing suite stops the commit: no pipe hides its status.
- Where a task says "Prove it fails first", run the test against the state described,
  watch it fail, and put the observed failure in the commit message.
- Code and tests state what they do now. No comment about seeds, tasks, dates or earlier
  versions. No command, script or document lists test files.
- The web code is plain: a browser runs the files of `app/www/` as they are. No package
  is added, to the app or anywhere.
- No command is added, no reply changes, and the app sends the lines it sends today.
- Nothing of the commands, the firmware, the converter or the emulator changes.
- A page changes in the commit that changes the code it describes.
- Answers to questions that come up are recorded in `docs/drifts.md`, not asked.

- [x] 1. The page keeps the room of the bars
  - Set `"state": "in_progress"` in
    `project-seeds/27-p1-the-app-clear-of-the-phones-bars/state.json`.
  - `app/www/style.css`, `app/www/main.js`: the room, the band at the top, and the tabs
    while the keyboard is open. `app/capacitor.config.json` and
    `app/android/app/src/main/res/values/styles.xml`: the bars' style and black behind
    them.
  - `tests/app/`: the scenario and the checks of the design.
  - `docs/android-app.md`: how the app keeps clear of the bars, the step of the check on
    a phone, what is verified and what is open.
  - Prove it fails first: the test that the tabs lie above the room at the bottom,
    against the web code as it is, fails: the tabs reach the bottom edge.
  - Requirements: 1.1 to 1.5, 2.1, 2.2, 3.1, 3.2, 4.1, 4.2, 5.1, 5.3

- [x] 2. The APK and the documents
  - `python3 app/app.py build`; `python3 -m unittest discover -s tests/apk -t .` passes
    against the new APK, with the check of the setting of the bars. Its size and SHA-256
    go into the commit message.
  - `docs/decisions.md`: a line in the change log. `AGENTS.md`: the seed leaves "What is
    coming". `docs/firmware-prerequisites.md`: the seed among the seeds not finished,
    with the owner's check.
  - Requirements: 5.2, 5.4

- [ ] 3. The owner's check on a phone
  - The owner installs the new APK and makes the step of the check on a phone: the tabs
    above the bottom bar and the heading below the top bar, held upright and sideways,
    the last line of each list above the tabs, and a field in view with the keyboard
    open.
  - What was seen goes into `docs/android-app.md`.
  - Set the seed's `state.json` to `completed`, with `completedAt`.
  - Requirements: 5.5
