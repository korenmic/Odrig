# Tasks: ODRGX text and clock animations (seed 37)

Seeds 02 to 09, 14, 16, 17, 20, 28 to 30 and 38 are implemented before these tasks start;
seeds 31 to 36 and 39 are built at the same time on other branches. Where the real code
differs from what the design relies on, follow the code and record the difference in
`docs/drifts.md`. Tasks 1 to 12 need no board; task 13 needs the board and the owner;
task 14 is done after this branch is combined with those of seeds 31 to 36 and 39.

Rules for every task:

- One task is one commit, which ticks its checkbox here. Stage named paths only, never
  `git add -A`, `git add .` or `git commit -a`; read `git show --stat` after it.
- Before each commit run the suites of the parts the task changed, and always
  `python3 -m unittest discover -s tests/onboarding -t .`: the converter's
  (`npm test --prefix converter` and `python3 -m unittest discover -s tests/converter -t .`),
  the core's (`make -C core test`), the emulator's, the app's, the firmware's
  (`python3 firmware/fw.py test`). At the end of the seed every suite, `tests/mapping` too.
  Run them so that a failing suite stops the commit.
- "Prove it fails first": run the test on the code before, watch it fail, and put what
  was seen into the commit message.
- Code states what it does now; no comment about seeds, tasks or dates. No document lists
  test files.
- The commands and reply members added are those of Requirement 10, no other; each goes
  into `docs/commands.md` and as a dated line into the change log of `docs/decisions.md`
  in the task that adds it.
- No board, no serial port, no network of the board. Answers to questions go into
  `docs/drifts.md`.

- [x] 1. The fonts and their tables
  - Set the seed's `state.json` to `in_progress`.
  - `fonts/small.txt` and `fonts/medium.txt`, drawn by hand: 122 glyphs each, the printable
    ASCII characters and the Hebrew letters with their final forms. `fonts/generate.mjs`
    writes `core/src/font_tables.cpp` and `converter/lib/fonttables.js`, with the sine
    table of the clocks; `core/src/fonts.h`.
  - Tests: the generated files are what the sources give; every glyph's rows and width;
    every character of the repertoire in both fonts; the core builds the tables.
  - Requirements: 3.3, 3.4, 9.1

- [x] 2. The container in the converter
  - `converter/lib/odrgx.js`: the header, the frames payload, the reasons;
    `converter/lib/show.js`, `converter/lib/pack.js` and the CLI: `.odrgx` names,
    `encode`, `decode` and `check` of a frames container, `pack` with `X.json` for
    `X.odrgx`. `odrig/odrgx.py`, `odrig/show.py`. `tests/vectors/`: valid and invalid
    containers. `docs/format.md`: the container and the frames payload;
    `docs/reasons.md`: the new reasons.
  - Tests: a frames container decodes to the frames of its ODRG file; every invalid
    container with its reason; `.odrgx` names in a show and in `pack`.
  - Requirements: 1.1 to 1.6, 2.1, 11.2, 11.3

- [x] 3. The container in the core
  - `core/src/container.h/.cpp`, `FileSource::rewind`; the start, the check after it, a
    drive's check and the upload's check through `content_open`; `open_stream` of a frames
    container; `FileInfo.type`, `DriveEntry.type`; `.odrgx` names; `list` with `type`.
    `docs/commands.md` and the change log: `type`.
  - Prove it fails first: a show that names a frames container is refused today with
    `show-malformed` for its name, and the container itself as `bad-magic`.
  - Tests: a frames container plays the pictures of its ODRG file at the same times, from
    the show, an upload and a drive; every invalid container with the converter's reason;
    the legacy vectors and the demo show unchanged; `list` gives `type`.
  - Requirements: 1.4 to 1.6, 2.1 to 2.3, 10.1, 15.1

- [ ] 4. A text in the converter
  - `converter/lib/bidi.js`, `converter/lib/textlayout.js`, the text's JSON source and
    payload in `odrgx.js`, the pass in `converter/lib/draw.js`; `encode`, `decode` and
    `check` of a text.
  - Tests: the golden layouts of Requirement 16.2; the UAX #9 cases of the classes; the
    pass of every effect and motion; `does-not-fit`; `unsupported-character` with the
    code point; the source strict; a decoded text gives back its source.
  - Requirements: 3.1, 3.2, 4.1 to 4.5, 5.1 to 5.3, 11.1 to 11.3

- [ ] 5. A text in the core, and the shared drawing
  - `core/src/text.h/.cpp`: the payload's check, its pass, its drawing; `open_stream` and
    `show_at` of a drawn stream; `turn_ms` and the cycle's turns at whole passes.
    `converter/lib/draw.js`: the drawing of a text. The test host's `render`.
    `tests/vectors/procedural/`: the texts' reference pictures.
  - Prove it fails first: a text file is refused by the core with `unknown-type`.
  - Tests: the reference pictures, equal in the converter and the core; every refusal of a
    text; a text's turn in the playlist, in a cycle and with `max_seconds` ends at a pass's
    end; `play` and `off` at once; frames timing unchanged.
  - Requirements: 5.2, 6.1 to 6.4, 9.1 to 9.4, 15.1 to 15.3, 16.1 to 16.3

- [ ] 6. The clocks
  - `core/src/clock.h/.cpp` and `converter/lib/draw.js`: the widget's check, the seed, the
    virtual time, the analog, digital and melting clocks; the widget's JSON source and
    payload in `odrgx.js`; `status` with `seed`. The clocks' reference pictures.
    `docs/commands.md` and the change log: `seed`.
  - Prove it fails first: a widget file is refused by the core with `unknown-type`.
  - Tests: the reference pictures, equal in both; a new seed at every turn and at `play`,
    the same through a turn's loops and its refreshes; a seed replayed; hands and digits
    from one virtual time; the speed within its range at irregular refreshes.
  - Requirements: 7.1 to 7.4, 8.1 to 8.5, 9.1 to 9.4, 10.4, 16.4

- [ ] 7. Reading back and replacing safely
  - `read <id> <offset>`, `upload expect <crc32>` and the error `stale` in the core;
    `docs/commands.md`; the change log.
  - Tests: `read` of a text, a clock, a frames file and a drive's file, at offsets and at
    the end; its refusals; `upload expect` with the right CRC-32 replaces and keeps the id,
    the place and `ignored`; a changed or removed item gives `stale` and the upload is
    gone; a long file gives `bad-argument`; every route.
  - Requirements: 10.2, 10.3, 10.5, 13.2, 13.3

- [ ] 8. The emulator, the firmware and the sample pictures
  - `emulator/host.py`, `preview/`, `firmware/usermod/odrig_drive.cpp`: `.odrgx`.
  - `tests/emulator/`: the emulator plays the reference texts and clocks, and its LEDs show
    the reference pictures; a drive's `.odrgx`.
  - `python3 firmware/fw.py build`: the image's size before and after, the tables' bytes;
    `docs/firmware.md`, `docs/emulator.md`.
  - Requirements: 2.2, 9.3, 14.1 to 14.3

- [ ] 9. The app: making a text
  - `app/www/`: "Make a text", its form, the moving preview, the pass's length, the
    refusals in words, the upload as a new item.
  - Tests in `tests/app/`: the preview's pixels are those of the converter's drawing; an
    unsupported character and a block that does not fit are named; an upload lists the
    new item with `type` `text`; a cancelled upload.
  - Requirements: 12.1, 12.3, 12.4, 16.5

- [ ] 10. The app: making a clock
  - `app/www/`: "Make a clock", its form, the preview with a new seed, the upload.
  - Tests in `tests/app/`: the preview, a new seed, an upload listed with `type` `widget`.
  - Requirements: 12.2, 12.4, 16.5

- [ ] 11. The app: editing
  - `app/www/`: "Edit" on a text or a clock, `read` back, the form filled, "Save" with
    `upload expect`, `stale` in words; no "Edit" for a drive's animation.
  - Tests in `tests/app/`: an edit keeps the id, the place and the inclusion; another
    controller's change gives the message and overwrites nothing; a drive's animation has
    no "Edit".
  - Requirements: 13.1 to 13.4, 16.5

- [ ] 12. The documents and the decisions
  - `docs/format.md`, `docs/show.md`, `docs/core.md`, `docs/converter.md`,
    `docs/android-app.md`, `docs/emulator.md`, as Requirement 17 says; `docs/decisions.md`:
    the runtime format, the sources and the drawing, and a line in the change log;
    `AGENTS.md`: the seed's line in "What is coming"; the APK built with the app's tool
    when its toolkit is there.
  - Requirements: 17.1, 17.2

- [ ] 13. The board and the owner's checks
  - In the board session of the run, with the owner: the firmware of the combined branch
    flashed; a show with a Hebrew text, a mixed text, every effect and the three clocks;
    `status` while each plays, 20 to 50 refreshes a second; the owner looks at the LEDs
    and at the app on a phone. `docs/firmware.md`, "Verified on the board"; what the board
    is left with.
  - Requirements: 18.1 to 18.3

- [ ] 14. After combining with seeds 32, 35, 36 and 39
  - Done by the session that combines the branches: seed 35's catalogs register the type
    and the loop of every file; seed 32's quarantine takes a refused text or clock; the
    forms of tasks 9 to 11 move into seed 36's upload and animation screens; seed 39's
    filter takes `type`. Every suite on the combined branch. Then set the seed's
    `state.json` to `completed` when task 13 is done too.
  - Requirements: 19.1 to 19.4
