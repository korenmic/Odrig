# Tasks

Each task is one commit on the branch `seed-87-live-mirror`, which is the branch of pull
request #63, `all-unmerged-seeds`, with master's seed 87 merged, with only its own checkbox
ticked. Every test of a fault is seen failing before the change, and the failure seen goes
into the commit message. Code carries no history.

- [x] 1. Planning and the plan in the core
  - `core/src/plan.cpp` and `plan.h`, new: `PlayState`, `take`, `put`, `plan_reply`,
    `item_end`, `sign`, `plan_bump`. `core/src/core_state.h`: the plan's fields.
    `core/src/player.cpp`: `player_project`, the projecting guards of `playlist_turn` and
    `clock_only_turn`, the sign after the refresh; `draw_noise` in `show_at`.
    `core/src/breaks.cpp`: `draw_noise` in `pick`. `core/src/catalog.cpp`: `catalog_key`.
    `core/src/commands.cpp`: `plan`, `plan since N`, `plan on`, `plan off`, and the bump
    after every line that is not a reading one. `core/src/core.cpp`: the bump in
    `quarantine_file`, `drive_faulted`.
  - `tests/core/test_plan.py`, new, seen failing first; the command lists of
    `tests/core/test_docs.py` and `tests/emulator/test_tool.py`; the figures of
    `tests/core/test_memory.py` and `tests/core/test_drive.py` as measured.
  - `docs/commands.md` (the table, "The plan", the error codes), `docs/core.md` (planning, the
    memory table), `docs/show.md` (a seed drawn while planning), `docs/decisions.md`
    ("Commands", "Animation formats", the change log with the owner's approval of
    2026-11-10), entries at the end of `docs/drifts.md`. The seed's state `in_progress`.
  - Suites: core, onboarding, emulator.
  - Requirements: 1.1–1.6, 2.1–2.8, 3.1–3.4, 5.1–5.3, 7.1–7.4, 18.1.

- [x] 2. The ways and the push in the core
  - `core/include/odrig_core.h`: `odrig_core_command_on`, `odrig_core_feed_on`,
    `odrig_core_plan_line`. `core/src/commands.cpp`: the way of a line, `plan push on|off`,
    `unsupported` on way 0. `core/src/core.cpp` or `plan.cpp`: the entries.
  - `tests/core/host/host.cpp`: `lineon WAY MS TEXT`, `byteson WAY MS HEX`, `planline WAY MS`.
    `tests/core/test_plan.py`: the push, seen failing first.
  - `docs/commands.md` ("The plan", "Transports"), `docs/core.md` (the entries).
  - Suites: core, onboarding.
  - Requirements: 4.1–4.6.

- [ ] 3. The mirror's entry in the core
  - `core/include/odrig_core.h`: `odrig_mirror`, `odrig_core_mirror`. `core/src/mirror.cpp`
    and `mirror.h`, new; `core/src/player.cpp` (`kMirrorPosition` in `length_of`, `type_of`,
    `id_of`, `open_stream`, `show_at`; the mirror's refresh in `player_poll`);
    `core/src/brightness.cpp`; `core/src/core_state.h` (the pointer).
  - `tests/core/host/host.cpp`: `mirror MS NAME ZERO LOOP SEED BRIGHTNESS ON ROTATION TEST
    SNAKE SERIAL` and `mirror none`. `tests/core/test_mirror.py`, new, seen failing first:
    frames, a text and a clock against `odrig_host render`, a late point, brightness, off,
    rotation, the diagonal, nothing written, the memory.
  - `docs/core.md` (the entry, the memory table).
  - Suites: core, onboarding.
  - Requirements: 6.1–6.3, 7.1–7.2.

- [ ] 4. `#plan` lines in the firmware
  - `firmware/usermod/odrig_uart.cpp`, `odrig_serial.cpp`, `odrig_usermod.cpp`: the ways 1 and
    2, the UART's whole line, the USB socket's pieces.
  - Tests of `tests/firmware` for both ways, seen failing first.
  - `docs/firmware.md` ("The log", "The two USB sockets").
  - Suites: firmware's host-only tests, core.
  - Requirements: 4.5, 8.1–8.2.

- [ ] 5. The emulator's ports as a board's
  - `emulator/binding.py` (the entries), `emulator/engine.py` (`way`, `plan_line`),
    `emulator/lineport.py` (a way for each connection, the push between replies, `plan push
    off` when it closes), `emulator/serialport.py` (way 1).
  - `tests/emulator/test_plan_push.py`, new, seen failing first.
  - `docs/emulator.md` ("The serial port", "The line port", "Commands over HTTP").
  - Suites: emulator, core, onboarding.
  - Requirements: 9.1–9.2.

- [ ] 6. `plan` in the command tool
  - `odrigctl/cli.py`: the six forms. `tests/emulator/test_tool.py`, seen failing first.
  - `docs/emulator.md` ("The command tool").
  - Suites: emulator, onboarding.
  - Requirements: 10.1.

- [ ] 7. The mirror's link and the man in the middle
  - `emulator/mirror/__init__.py`, `link.py`, `middle.py`, new. `emulator/app.py`
    (`--mirror-port`, `--mirror-tcp`, `--mirror-http`, their refusals, `mirror:`, the `--lan`
    warning), `emulator/engine.py` (lines to the middle, logged with the board's reply),
    `emulator/httpd.py` (a closed request on a lost link), `emulator/lineport.py` and
    `serialport.py` (the board's other `#` lines).
  - `tests/emulator/test_middle.py`, new, and the options in `tests/emulator/test_app.py`
    or a new file, seen failing first.
  - `docs/emulator.md` ("Starting", "A mirror of a board": the link and the man in the middle).
  - Suites: emulator, onboarding.
  - Requirements: 11.1–11.6, 12.1–12.6, 17.1.

- [ ] 8. The plan kept and shown, and the files
  - `emulator/mirror/keeper.py`, `files.py`, `driver.py`, new; `emulator/host.py` (the
    mirror's names), `emulator/engine.py` (the driver at each tick, the board's status).
  - `tests/emulator/test_mirror.py`, new, seen failing first: two emulators over the line
    port and over HTTP, the pictures within two refreshes, a late join, a missing file
    fetched and kept, a `play` through the mirror and through the board, a lost link and its
    return, a restart; `tests/emulator/test_files.py` for the collection's lookup.
  - `docs/emulator.md` ("A mirror of a board": the plan, the files, what it shows),
    `agent/vocabulary.md`.
  - Suites: emulator, core, onboarding.
  - Requirements: 13.1–13.4, 14.1–14.8, 15.1–15.4.

- [ ] 9. The page of a mirror
  - `emulator/httpd.py` (`hello`, `mirror` events, `/seek`), `emulator/hub.py`,
    `emulator/web/` (the header, the bands, the log's marks, no seek bar).
  - Tests of `tests/emulator` for the events, `/seek` and the page's script, seen failing
    first.
  - `docs/emulator.md` ("The page", "The event stream", the check list by eye).
  - Suites: emulator, onboarding.
  - Requirements: 16.1–16.5.

- [ ] 10. Deliver seed 87
  - Push the branch and open its pull request against `all-unmerged-seeds`, the branch of
    pull request #63. Run an emulator as the board and another as its mirror, through
    commands sent to both, and record what was seen. From the pushed head with a clean tree:
    the installation's image (`odrig_microsd`) and the spare's (`odrig_microsd_n8r2`), each
    through `verify_build.py` for its module, and the APK signed with the persistent key,
    checked with `apksigner` and `zipalign -c 4`; their bytes and SHA-256; the files on the
    Drive in a new folder of `odrig archive/`.
  - Every suite that works on this computer passes.
  - `verification.md`: the commits, the suites, the two emulators' run, the builds with their
    links, and the owner's checks, open. The seed's line in `AGENTS.md`.
  - Requirements: 18.2–18.4.
