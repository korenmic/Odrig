# Tasks: the app's count of installed and external animations (seed 28)

Seeds 09, 20, 29 and 38 are implemented before these tasks start: the app, a drive's
animations, `external` in `space`, and the microSD card. Where the real code differs from
what the design relies on, follow the code and record the difference in `docs/drifts.md`.

Tasks 1 and 2 need Chrome and nothing that is not in the repository. Task 2 builds the APK
with the toolchain of `build/app/`. Task 3 needs the owner, a phone and the board.

Rules for every task:

- One task is one commit. The same commit ticks the task's checkbox in this file.
- Stage named paths only, never `git add -A`, `git add .` or `git commit -a`.
- The tests of a task are in the task's commit. Before committing, the suites that need
  no board and no phone pass: `npm test --prefix converter`,
  `python3 -m unittest discover -s tests/converter -t .`, `make -C core test`,
  `python3 -m unittest discover -s tests/emulator -t .`,
  `python3 -m unittest discover -s tests/onboarding -t .`, `python3 firmware/fw.py test`
  and `python3 -m unittest discover -s tests/app -t .`.
- Where a task says "Prove it fails first", watch the test fail against the state named,
  and put the failure seen into the commit message.
- Code and tests state what they do now; no comment about seeds, tasks or dates.
- No package is added; no command is added, no reply changes; the app sends the lines it
  sends today.
- Answers to questions that come up are recorded in `docs/drifts.md`, not asked.

- [x] 1. The two numbers on the dashboard
  - Set `"state": "in_progress"` in the seed's `state.json`.
  - `app/www/client.js`: `state.listBusy`. `app/www/capacity.js`: `counts` and the words.
    `app/www/screens/show.js`, `app/www/screens/storage.js`: the numbers into the lines.
  - `tests/app/page/reading.js` and `tests/app/test_counts.py`: the checks of the design.
  - `docs/android-app.md`: the two numbers in "What it is" and the step of the check on a
    phone.
  - Prove it fails first: the test of a drive with two animations, against the web code
    as it is, fails: the external line has no number.
  - Requirements: 1.1 to 1.3, 2.1 to 2.3, 3.1 to 3.3, 4.1, 4.2, 5.1 to 5.3, 6.1, 6.2

- [x] 2. The APK and the documents
  - `python3 app/app.py build`; `python3 -m unittest discover -s tests/apk -t .` passes
    against the new APK; its size and SHA-256 go into the commit message.
  - `docs/android-app.md`: "What is verified" and "What is open". `docs/decisions.md`: a
    line in the change log.
  - Requirements: 6.3

- [ ] 3. The owner's check on a phone
  - With the new APK and the board, the card in and then out: the two numbers match the
    board's own animations and the card's, and the external line says `absent` without a
    number when the card is out.
  - What was seen goes into `docs/android-app.md`; the seed's `state.json` becomes
    `completed`, with `completedAt`, and the seed leaves "What is coming" in `AGENTS.md`.
  - Requirements: 6.4
