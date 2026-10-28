# Tasks: a bar for the animation playing now, and a frozen top

Requirements: [requirements.md](requirements.md). Design: [design.md](design.md).

- [x] 1. The ad hoc repeat and the counts in `status`
  - `core/src/core_state.h` (`turn_repeat`), `core/src/player.cpp` and `player.h` (the
    counts, `current_turn_ms`, the clearing, `player_reported`, `player_counts`,
    `player_set_repeat`), `core/src/commands.cpp` (`repeat <id> <n>` and its refusals; the
    two saving forms answered `bad-argument` until task 2; `repeat`, `loop` and `saved`,
    always `null` until task 2, in `status`).
  - `tests/core/support.py`: the reference player's ad hoc value, counts and members.
  - Tests in `tests/core/test_repeat.py`: the form and its refusals in order; a turn made
    `n` loops long from its first frame; `n` at or below the loop in progress ending the
    turn at that loop's end; `max_seconds` not cutting it; a text's passes; a clock's seed
    kept; a card's animation; a jump; every way the value is cleared and the ways it is
    kept; a folder's window waiting; `repeat` and `loop` against the reference player; a
    count above 65,535; the rounds after a long gap. `tests/core/test_status.py` and
    `tests/core/test_commands.py` with the three members.
  - `docs/commands.md`: the command, its refusals and the members; `agent/vocabulary.md`;
    `docs/drifts.md`: the decisions of the spec beyond the seed for the core.
  - `project-seeds/48-p2-a-bar-for-the-animation-playing-now/state.json`: `in_progress`.
  - Suites: the core's (after `make -C core build/odrig_host all shared`), the emulator's,
    onboarding.

- [x] 2. The saved repeats of the board's own files
  - `core/src/repeats.cpp` and `repeats.h`, `core/src/order.cpp` (the calls),
    `core/src/storage.cpp` (`repeats.part`, the reload after a renaming upload),
    `core/src/content.cpp` (the masked `repeat`), `core/src/commands.cpp` (the saving
    forms, `saved` in `status`), `core/Makefile` and `core/build.py` when they list sources,
    `tests/core/host/host.cpp` (the names).
  - `tests/core/support.py`: the reference player's file and saved repeats.
  - Tests in `tests/core/test_repeat.py`: the two forms and their refusals in order;
    `saved` in `status`; a saved repeat across a restart, by file name, after a removal and
    an upload; the order of the counts; `max_seconds` not cutting a saved repeat; the file's
    strict reading and its log line; a failure and a power cut at every call of a save and
    of a restore; `repeats.part` removed at the start; 512 lines and `no-space`, the lines
    of files `show.json` no longer names dropped; the rounds after a long gap with saved
    repeats; against the reference player.
  - `docs/commands.md`, `docs/show.md`, `docs/core.md`.
  - Suites: the core's, the emulator's, onboarding.

- [x] 3. The saved repeats of the drive's files
  - `core/src/repeats.cpp` (the table, the steps after the order's), `core/src/order.cpp`
    (the block, the phase, the yield), `core/src/core_state.h` (`repeats_drive`).
  - Tests in `tests/core/test_repeat.py` with a drive: a card's file saved and played by
    its count, across a restart, the card pulled out and put back, a rebuild of the
    drive's catalog; 32 places, `no-space` and `repeats over`; the memory limits with a
    drive in `tests/core/test_drive.py` and `docs/core.md`'s figures.
  - Suites: the core's, the emulator's, onboarding.

- [x] 4. The command tool, the firmware tool and the emulator's page
  - `odrigctl/cli.py`, `firmware/fwtool/storage.py`; tests in `tests/emulator/test_tool.py`
    and `tests/firmware/test_storage.py`.
  - `docs/emulator.md`, `docs/firmware.md`; `docs/decisions.md`: the commands' bullet and
    the change log with the owner's approval of the forms, the members and the file.
  - Suites: the emulator's, the firmware tool's, onboarding.

- [x] 5. The bar and its row actions
  - `app/www/commands.js` and `client.js` (the members, the three forms, `statusCount`),
    `app/www/index.html` (`#now-bar`), `app/www/screens/show.js` (`drawBar`, the actions
    without the moves, `Select` from the bar), `app/www/screens/filters.js` (`reveal`),
    `app/www/style.css`.
  - Tests in `tests/app/test_now_bar.py` with scenarios of their own: the bar's place and
    its states; its actions per kind of animation against the emulator and stand-ins;
    `Ignore` moving on; `Delete` asking first; `Select` from another folder and through a
    filter with the row below the panel; the buttons disabled while the installation does
    not answer and while the selection is locked. The scenarios that press `Select` by its
    words press the list head's; the lists of the panel's buttons follow the bar.
  - `docs/drifts.md`: the decisions of the spec beyond the seed for the app.
  - Suites: the app's.

- [x] 6. Repeat this, Save and Restore default
  - `app/www/screens/show.js` (the second and third lines, the focus rules, the sends and
    the sentences), `app/www/main.js` (`focusout`), `app/www/messages.js`,
    `app/www/style.css`.
  - Tests in `tests/app/test_now_bar.py`: `Repeat this` sent by its button with typed text
    and by Done, refused with `stale`; the field kept while it has the focus and its text
    not sent dropped a second after it is left; `Save` with typed text and with the
    untouched value; 0, 65,536 and an empty field sending nothing; Done never saving;
    `Restore default` disabled with nothing saved, enabled with a saved value, sent, and the
    field following `status`; the sentences and the refusals; the buttons disabled while a
    line is out; no question asked; a target without `repeat` or `saved`.
  - `docs/android-app.md`: the three lines in the table of lines with its count, the rows
    of the messages; `tests/app/test_docs.py` and `tests/app/test_scope.py` follow.
  - Suites: the app's.

- [x] 7. The frozen top and the bar's look
  - `app/www/style.css`, `app/www/screens/show.js` (`freeze`), `app/www/screens/reorder.js`
    (the top edge).
  - Tests in `tests/app/test_frozen.py`: the panel sticking at 412 x 915 with the list
    scrolling under it, and at 360 x 740 with no insets and with a 24 px top and 16 px
    bottom inset; sticking exactly when 80 px stay below it; no freeze at 740 x 360, at 320
    x 568 and with the keyboard open; a row moved under the frozen top. In
    `tests/app/test_look.py`: the bar's one height for every kind of animation at 320, 360
    and 740 px, and the look rules with the bar.
  - Suites: the app's.

- [ ] 8. The documents, every suite, the firmware and the APK
  - `docs/android-app.md`: the bar and the frozen top in "What it is" and "Using it", the
    check on a phone, what is verified and what is open; `AGENTS.md`: the line of seeds 47
    and 48, built with the owner's checks open.
  - Every suite that works on this computer; `python3 firmware/fw.py build` to prove that the
    firmware compiles, neither flashed nor uploaded; `python3 app/app.py build` and the
    APK's suite; the APK put with the artifacts on the share and on Drive. The seed stays
    `in_progress`: the owner's checks on a phone against the installation, which need a
    firmware with this seed on the board, are left open in words.
  - Suites: every suite.
