# Tasks: boot-local animation quarantine and recovery (seed 32)

Seeds 28, 29, 30, 31 and 38 are implemented before these tasks start. Where the real code
differs from what the design relies on, follow the code and record the difference in
`docs/drifts.md`. Tasks 1 to 5 need no board; task 6 needs the board.

Rules for every task:

- One task is one commit, which ticks its checkbox here. Stage named paths only.
- Before each commit the suites of the parts the task changed pass, with the core's, the
  onboarding's and the documents' tests always among them: a change of the core runs
  `make -C core test` and `python3 -m unittest discover -s tests/emulator -t .`; one of
  the app `python3 -m unittest discover -s tests/app -t .`. Every suite that needs no
  board passes at the end of the seed.
- "Prove it fails first": watch the test fail on the code before, and put what was seen
  into the commit message.
- Code states what it does now; no comment about seeds, tasks or dates.
- The reply member `fault`, a `bytes` of `null` and the error code `unavailable` are the
  additions to the command list, approved in advance by the owner; each goes into
  `docs/commands.md` and the change log of `docs/decisions.md`. Nothing else is added.
- Answers to questions that come up go into `docs/drifts.md`.

- [x] 1. The regression: one bad file ends the show
  - Set the seed's `state.json` to `in_progress`.
  - `tests/core/test_quarantine.py`: a show of three animations whose second has a bad
    body, a bad header, or is missing keeps playing the first and the third, and `list`
    and `remove` are answered; marked as expected failures, which task 2 turns into passes.
  - Prove it fails first: the show turns invalid and `list` is refused.
  - Requirements: 8.1

- [x] 2. Quarantine of installed files
  - `core/src/core_state.h`, `core.cpp`, `player.cpp`, `commands.cpp`, `content.cpp`:
    `FileInfo.fault` and `checked`, `quarantine_file`, `usable`, the player's routes,
    `player_file_failed`, `play` refused with `unavailable`, `list` with `fault` and
    `bytes` of `null`.
  - `tests/core/support.py`: the reference player's rules; the existing tests that
    expected the global invalidation of a file fault.
  - Tests: the expected failures of task 1 pass; bad headers, bodies, missing files,
    reads that fail, all files bad, show faults, cycles, the start's choice, `play`, a
    fault after good playback, the openings of a quarantined file, `ignored` beside it.
  - `docs/show.md`, `docs/core.md`, `docs/commands.md`, `docs/reasons.md`,
    `docs/firmware-additions.md`, `docs/decisions.md`.
  - Requirements: 1.1 to 1.4, 2.1 to 2.4, 3.1, 3.3, 4.1, 4.3, 4.4, 5.5, 8.2

- [x] 3. Repair while the check goes on
  - `core/src/commands.cpp`, `core.cpp`, `upload.cpp`, `content.cpp`: `list`, `remove`,
    `remove many`, `ignore` and `upload begin` during the check; `check_yields`; the
    check's place through removals; files an upload installed are not checked again; a
    replacement clears the quarantine.
  - Tests: each command during the check, with the reference player; an upload that
    replaces a quarantined animation makes it play; the check comes to its end after
    uploads and removals.
  - `docs/commands.md`, `docs/core.md`.
  - Requirements: 3.4, 5.1 to 5.3

- [x] 4. A drive's files: ids at once, listed with their fault, remembered
  - `core/src/core.cpp`, `core_state.h`, `content.cpp`: ids when a drive is taken up,
    `DriveEntry.fault`, left-out files listed, the boot's memory of 16 left-out files.
  - Tests: ids before the check; a left-out file listed with `fault`; the same content
    taken up again is left out after one read; another file of the same name and another
    drive are checked; a pulled drive; the other files keep playing.
  - `docs/show.md`, `docs/core.md`, `docs/commands.md`; the memory figures.
  - Requirements: 3.2, 4.2, 5.4, 6.1, 6.2

- [x] 5. The app and the emulator
  - `app/www/commands.js`, `app/www/screens/show.js`, `app/www/messages.js`,
    `app/www/style.css`: `fault` and `bytes` of `null` accepted; a grayed row with its
    reason and a disabled Play; the drive's note.
  - `tests/app`: a scenario with a quarantined animation of the show and one of the drive.
  - `tests/emulator/test_quarantine.py`: the emulator with a bad file plays the others and
    lists it with `fault` over HTTP and the line port.
  - `docs/android-app.md`; the state of the seed stays `in_progress` for task 6.
  - Requirements: 7.1 to 7.4, 8.3, 8.4, 8.5

- [ ] 6. The board
  - In the run's board session, at brightness 40 or less: a bad file in the board's
    storage and one on the card; the board starts, answers, plays the rest, and `list`
    marks both; the owner looks at the app and the LEDs; what is left on the board is
    said. The seed's state `completed` when all is seen, otherwise what is missing said
    in `docs/firmware.md`, "Verified on the board".
  - Requirements: 8.5
