# Tasks: a hundred picture clocks (seed 52)

The code these tasks start from is `master` at `000303c`. The owner asked for the spec and
the work without a question pass: a question that comes up is decided and recorded at the
end of `docs/drifts.md` under "Seed 52", never asked. The work is done on a Windows
computer. Tasks 1 to 12 need neither the board nor the owner; task 13 is the owner's.

Rules for every task:

- One task is one commit, `Seed 52 task <n>: <title>`, which ticks its checkbox here.
  Stage named paths only, never `git add -A`, `git add .`, `git add -u` or
  `git commit -a`. After committing, read `git show --stat`.
- The tests of a task are in its commit. Before committing, run the suites the task names,
  one at a time, from the repository root: `npm test --prefix converter`,
  `python -m unittest discover -s tests/converter -t .`, `python core/build.py test`,
  `python -m unittest discover -s tests/emulator -t .`,
  `python -m unittest discover -s tests/app -t .` and
  `python -m unittest discover -s tests/onboarding -t .`. A test that fails on `master`
  on this computer too is noted, not mended.
- "Prove it fails first": run the new test against the state before the change, watch it
  fail, and put the observed failure in the commit message.
- Code and tests state what they do now: no comment about seeds, tasks, dates or earlier
  versions. No command, script or document lists test files.
- No command, reply member or error code of the command list is added; the core's memory
  and its object keep their sizes.
- Animation files, the inventory, the base pictures and the tools that make them are
  never committed: they go into the collection, `E:\artifacts\odrig\collection\clocks\`,
  where only that folder is made and written. The previews are committed in
  `thumbnails/`.
- The owner's picture and the cut tiles are read and copied, never moved or changed.
  Python that reads them runs with `-I`. Chrome runs headless only, with a fresh profile
  that is removed afterwards.
- Every task that changes a page runs the onboarding suite; the decisions a task takes go
  into `docs/drifts.md` under "Seed 52" in its commit.

- [x] 1. The picture widgets in the converter
  - Set the seed's `state.json` to `in_progress`.
  - `fonts/tiny.txt`, `fonts/generate.mjs` with a repertoire for each font,
    `core/src/font_tables.cpp`, `converter/lib/fonttables.js`.
  - `converter/lib/draw.js`: `WIDGETS`, `clockOf` with `back` and `chance`,
    `pictureTime`, `overlayOf`, the drawing of both widgets. `converter/lib/odrgx.js`:
    the payload, its reasons in the core's order, the JSON source, `decode` of a picture
    widget back to its source; `LARGEST_PAYLOAD` of a widget 32,768.
    `converter/lib/errors.js`: `bad-picture`.
  - `tests/vectors/widgets/build.mjs`: `unknown-widget.four` becomes
    `unknown-widget.six`.
  - `docs/format.md`: the two widgets, their JSON source, the virtual time with a
    direction, the drawing. `docs/reasons.md`: "Widgets in ODRGX", "ODRGX files" and
    "JSON sources of clocks". `docs/converter.md`: `encode`, `decode`, `check` of a
    picture clock.
  - Prove it fails first: the JSON source of a picture dial is refused by `encode` with
    `out-of-range` for its widget.
  - Tests in `converter/tests/`: every refusal and its order; a source given back by
    `decode`; the virtual time forward equal to the analog clock's, backward its mirror,
    `random` turning only at slowest points, as the seed says; a hand, a cap and every
    pattern character drawn; `tiny` in the tables and refused for a text.
  - Suites: the converter's two, the core's, the onboarding suite.
  - Requirements: 1.1 to 1.8, 2.1 to 2.4, 3.1 to 3.5, 4.1, 4.2, 4.4

- [x] 2. The picture widgets in the core
  - `core/src/clock.h/.cpp`: `clock_read` with its `Picture`, `clock_overlay`,
    `clock_is_picture`, the virtual time with a direction. `core/src/container.h/.cpp`,
    `core/src/core.cpp`, `core/src/upload.cpp`, `core/src/player.cpp`: the picture decoded
    at the opening of a stream, the layer in the window, the LED data through it.
    `core/src/reasons.h/.cpp`: `bad-picture`. The test host's `decode` and `render`.
  - `odrig/odrgx.py`, `odrig/errors.py`; the reference player of `tests/core/support.py`.
  - `tests/vectors/widgets/`: valid picture dials and displays with their sources, an
    invalid vector for each new refusal. `tests/vectors/procedural/`: their reference
    pictures at several times and seeds.
  - `docs/core.md`: "Clocks" and "Memory"; `docs/reasons.md` where the core's list
    needs it.
  - Prove it fails first: the core refuses the valid picture dial vector with
    `payload-size`.
  - Tests in `tests/core/`: the vectors with their reasons; `render` equal to the
    converter's reference pictures; a picture widget in a show as the reference player
    plays it, from the start, an upload and a drive; a new seed at each turn; the memory a
    show asks for, the same with picture widgets and without them.
  - Suites: the converter's two, the core's, the emulator's, the onboarding suite.
  - Requirements: 2.1 to 2.3, 3.4, 3.5, 4.3, 5.1, 5.2, 11.1

- [x] 3. The app shows a picture clock and does not edit it
  - `app/www/screens/author.js`: "Edit" of a picture widget says "This clock is made
    from a picture: it cannot be edited here." and fills no form.
    `docs/android-app.md`.
  - Prove it fails first: "Edit" of a picture dial fills the clock form today.
  - Tests in `tests/app/`: the message, and no upload.
  - Suites: the app's, the onboarding suite.
  - Requirements: 11.2

- [x] 4. Motions and the subcommand `clocks`
  - `converter/lib/motion.js`: `level`, `flicker`, `pulse`, `turn` and `swing`, and the
    frames of a motion. `converter/lib/inventory.js`: the inventory read strictly, the
    files of its tiles. `converter/cli/`: `clocks INVENTORY.json --out DIR`.
    `converter/lib/index.js`. `docs/converter.md`: the subcommand, the inventory, the
    motions, the library's modules.
  - Prove it fails first: `node converter/odrig.js clocks` is a usage error today.
  - Tests in `converter/tests/`: each kind of motion at chosen times; a loop that comes
    back to its first picture; at most the palette's colours; the same bytes twice; a
    small inventory of a dial, a display and a motion made, checked and played back by
    the readers; the inventory's refusals naming the tile.
  - Suites: the converter's, the onboarding suite.
  - Requirements: 6.1 to 6.3, 7.1, 7.2

- [x] 5. The tiles prepared
  - The tools in the collection's `clocks/source/tools/`, run from `scratch/`: each tile
    scaled to 60 x 60 and reduced to 8 colours, black among them when it has black; the
    skeleton of `inventory.json` with each tile's palette, picture, kind and `about`; a
    contact sheet of the 100 reduced tiles to look at.
  - `docs/drifts.md`: the scaling, the colours, the kinds.
  - Requirements: 7.1, 7.3, 8.3

- [x] 6. The inventory: the dials
  - For each dial: its hands, caps, colours and settings; the hands erased from its base
    picture; a sheet of each at two times, with its hands drawn by the converter, looked
    at.
  - `docs/drifts.md`: the sundials, the numerals kept, the speeds.
  - Requirements: 7.1, 8.2, 8.3

- [ ] 7. The inventory: the displays
  - For each display: its fields, their boxes, fonts, patterns and colours; the time
    erased from its base picture; a sheet of each at two times, looked at.
  - `docs/drifts.md`: the tiles with several fields, the fonts chosen.
  - Requirements: 7.1, 8.2, 8.3

- [ ] 8. The inventory: the motions
  - For each tile that shows no time: its motion, its parts and their boxes; a sheet of
    each at four times, looked at.
  - `docs/drifts.md`: the motion of each tile.
  - Requirements: 6.1, 6.2, 7.1, 8.2

- [ ] 9. The hundred made and kept
  - `clocks` writes the 100 files into `build/clocks/`; `check` accepts each; each has
    at most 8 colours, counted from its pictures. The previews:
    `thumbnail --catalog thumbnails` of the 100, committed. The collection's `clocks/`:
    the files, their previews, their readmes, and `source/` with the owner's picture,
    `tiles/`, `inventory.json`, `base/` and `tools/`.
  - The emulator, with `--drive` on a folder that holds the 100 under `odrig/`, on free
    ports: each is listed and plays. Record mode: a picture dial and a picture display on
    two turns each, their hands or digits moving, at other speeds or ways.
  - `docs/drifts.md`: the sizes, the counts, what the recordings showed.
  - Suites: the converter's, the app's, the onboarding suite.
  - Requirements: 8.1, 10.1 to 10.3, 13.2, 13.3

- [ ] 10. The twelve: the original six
  - `render12.mjs` with the tools: the six scenes of `references/original/animation.js`
    rendered over their periods, 8 colours, 50 ms or 100 ms; compared with their
    reference GIFs. Their previews in `thumbnails/`; the files, previews and readmes in
    the collection.
  - `docs/drifts.md`: the colours, the rates, the sizes, the largest differences.
  - Suites: the converter's, the onboarding suite.
  - Requirements: 9.1 to 9.6, 10.1, 10.2

- [ ] 11. The twelve: the standalone six
  - As task 10, from `references/standalone/standalone-script.js`.
  - Suites: the converter's, the onboarding suite.
  - Requirements: 9.1 to 9.6, 10.1, 10.2

- [ ] 12. The pages, the decisions and every suite
  - `docs/decisions.md`: the format's extension and a line in the change log;
    `AGENTS.md`: the seed's line in "What is coming". The contact sheet of the 112 in
    `build/clocks/`. Every suite that runs on Windows, after bringing the branch up to
    date with `origin/master`. Set the seed's `state.json` to `completed` when tasks 1 to
    11 are done; task 13 stays the owner's.
  - Requirements: 12.1, 13.1, 13.2

- [ ] 13. The owner's look on the LEDs
  - The owner plays a selection of the clocks on the installation and says whether they
    read. Not done by an agent.
  - Requirements: 13.4
