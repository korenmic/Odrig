# Tasks: clocks between the animations

Requirements: [requirements.md](requirements.md). Design: [design.md](design.md).

- [x] 1. The message
  - `project-seeds/54-p2-clocks-between-the-animations/source/render-message.mjs`, run from
    `scratch/`; `collection/card/clocks/message/its-not-the-time.odrg` with its GIF and
    readme; `thumbnails/catalog.js` and its GIF; the same three files in the share's
    collection, read back.
  - `docs/drifts.md`: the frames, the colours, the size.
  - `project-seeds/54-p2-clocks-between-the-animations/state.json`: `in_progress`.
  - Suites: the converter's, onboarding.
  - Requirements: 1.2, 1.3

- [x] 2. The settings in the core
  - `core/src/breaks.cpp` and `breaks.h` (the settings, the file, the commands),
    `core/src/commands.cpp` (the lines, `status`), `core/src/core.cpp` (`breaks_start`),
    `core/src/core_state.h`, `core/build.py` and `core/Makefile` when they list sources,
    `tests/core/host/host.cpp`'s names; `tests/core/support.py`: the reference player's
    lines, file and members.
  - Tests in `tests/core/test_clocks.py`: the four lines and their refusals in order; the
    file written, read strictly, its log line, `clocks.part` removed, a failure at each
    call of a save; the members; a restart.
  - `docs/commands.md`.
  - Suites: the core's, the emulator's, onboarding.
  - Requirements: 2.1 to 2.5

- [x] 3. The breaks in the core
  - `core/src/breaks.cpp` (the folders, the order, the message), `core/src/clock.cpp`
    (`clock_shuffle`), `core/src/player.cpp` and `player.h`, `core/src/mapping_control.cpp`,
    `core/src/order.cpp` and `drive.cpp` where the tree changes, `core/src/core_state.h`;
    `tests/core/host/host.cpp` (`shuffle`); `tests/core/support.py` (`clock_shuffle`).
  - Tests in `tests/core/test_clocks.py` as the design lists them; the memory test.
  - `docs/show.md`, `docs/core.md`, `docs/drifts.md`.
  - Suites: the core's, the emulator's, onboarding.
  - Requirements: 3.1 to 7.2

- [ ] 4. The emulator's `--drive-folder` and the demo show
  - `emulator/app.py`, `emulator/host.py`, their tests; `shows/clock-breaks/show.json`;
    `docs/emulator.md`.
  - Suites: the emulator's, onboarding.
  - Requirements: 8.1 to 8.3

- [x] 5. The command tool and the firmware tool
  - `odrigctl/cli.py`, `firmware/fwtool/storage.py` and their tests; `docs/firmware.md`;
    `docs/decisions.md`: the commands' bullet and the change log.
  - Suites: the emulator's, the firmware tool's, onboarding.
  - Requirements: 8.4, 10.1

- [x] 6. The app's panel
  - `app/www/index.html`, `screens/clocks.js`, `commands.js`, `client.js`, `main.js`,
    `style.css`; `tests/app/test_clocks.py`; `docs/android-app.md`.
  - Suites: the app's.
  - Requirements: 9.1 to 9.4

- [ ] 7. The clocks on the card, the pages and every suite
  - The 112 in `collection/card/clocks/` checked against the share; the emulator with the
    demo show and `--drive-folder collection/card`: a break after 5 turns, the message, a
    turn cut and resumed; `docs/microsd.md` (the 256), `agent/vocabulary.md` (`clock
    break`). Every suite that runs on Windows; the seed `completed` once 1 to 7 are done.
  - Requirements: 1.1, 10.1, 10.2

- [ ] 8. The owner's check on the installation
  - Not done by an agent.
  - Requirements: 10.3
