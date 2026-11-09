# Tasks

Each task is one commit on the branch `seed-86-move-a-folder-inside-the-board`, which is
`master` with seed 74 part B (pull request #64) merged, with only its own checkbox ticked.
Every test of a fault is seen failing before the change, and the failure seen goes into the
commit message. Code carries no history.

- [x] 1. `move internal <folder id> <path>` in the core
  - `core/src/commands.cpp`: the line. `core/src/folders.cpp` and `.h`:
    `internal_folder_move`, `plan_move`, `write_moved`, `copy_lines`.
  - `tests/core/test_folder_move.py`, new, seen failing first; the command lists of
    `tests/core/test_docs.py` and `tests/emulator/test_tool.py`.
  - `docs/commands.md` (the table, "Folders of the board's own storage", the error codes),
    `docs/core.md` ("Internal folders"), the change log of `docs/decisions.md` with the
    owner's approval of 2026-11-09, and the drifts at the end of `docs/drifts.md`. Set the
    seed's state to `in_progress`.
  - Measure `sizeof(Core)`, `FileInfo` and `Upload` with g++ and the board's compiler: the
    memory table of `docs/core.md` unchanged; every new frame under 512 bytes.
  - Suites: core, onboarding, emulator (its tool's command list).
  - Requirements: 1.1–1.4, 2.1–2.2, 3.1–3.3, 4.1–4.2, 5.1–5.4, 6.1–6.11, 9.1.

- [x] 2. The emulator's line and the command tool
  - `odrigctl/cli.py`: `move internal ID PATH`. `tests/emulator/test_folder_move.py`, new:
    the line over HTTP and TCP; `tests/emulator/test_tool.py`: the tool's sending and its
    usage errors, seen failing first.
  - `docs/emulator.md`, `docs/drifts.md` at the end.
  - Suites: emulator, core, onboarding.
  - Requirements: 1.4, 8.1, 9.1.

- [x] 3. `Rename…` and `Move to…` of a folder of the board's storage in the app
  - `app/www/commands.js` (`moveInternal`), `app/www/messages.js` (its refusals),
    `app/www/moves.js` (the command move of selected folders), `app/www/client.js`
    (`followFolder`), `app/www/screens/explorer.js` (the two actions, their dialogs, the
    lost reply), `app/www/screens/show.js` (the folder hook of `extend`),
    `app/www/index.html` (the new path's line of the folder dialog).
  - Tests seen failing first: `tests/app/test_folder_move.py` with its page scenario, new;
    `tests/app/test_moves.py` for selected folders moved by the command;
    `tests/app/test_messages.py`; `tests/app/test_scope.py` takes `move internal <n> <n>`.
  - `docs/android-app.md`: the actions, and a step of "The check on a phone" with the counts
    of `tests/app/test_docs.py`; `docs/drifts.md` at the end.
  - Suites: app, emulator, onboarding.
  - Requirements: 7.1–7.8, 9.1.

- [x] 4. Deliver seed 86
  - Push the branch and open its pull request against `master`, saying it is built on pull
    request #64. From the pushed head with a clean tree: the installation's image
    (`odrig_microsd`) and the spare's (`odrig_microsd_n8r2`), each through
    `verify_build.py` for its module, and the APK signed with the persistent key, checked
    with `apksigner` and `zipalign -c 4`; their bytes and SHA-256; the files on the Drive
    in a new folder of `odrig archive/`.
  - Every suite that works on this computer passes.
  - `verification.md`: the commits, the suites, the builds with their links, and the
    owner's check on a phone, open. The seed's line in `AGENTS.md`.
  - Requirements: 9.2–9.4.

The test of requirement 5.5, a move into `clocks/message` and out of it, belongs where seed
61's internal clocks are built with this seed: it is added when this seed joins the branch
of every unmerged seed, pull request #63.
