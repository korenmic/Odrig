# Tasks: previews of the animations in the app (seed 44)

The code these tasks start from is `master` at `c52c935`, which holds seeds 20 to 43. The
owner asked for the spec and the work without a question pass: a question that comes up is
decided and recorded at the end of `docs/drifts.md` under "Seed 44", never asked. Tasks 1
to 9 need neither the board nor a phone. Task 10 builds the firmware and the APK and does
not flash. Task 11 is the owner's.

Rules for every task:

- One task is one commit, which ticks its checkbox here. Stage named paths only, never
  `git add -A`, `git add .` or `git commit -a`. After committing, read `git show --stat`.
- The tests of a task are in the task's commit. Before committing, run the suites the task
  names from the repository root: `npm test --prefix converter`,
  `python3 -m unittest discover -s tests/converter -t .`, `make -C core test` or
  `python3 -m unittest discover -s tests/core -t .`,
  `python3 -m unittest discover -s tests/emulator -t .`,
  `python3 -m unittest discover -s tests/app -t .`,
  `python3 -m unittest discover -s tests/onboarding -t .` and `python3 firmware/fw.py test`.
  Long suites run with the shell's own background run, never `nohup … &`, which makes the
  tests' Ctrl-C ignored. Task 10 runs every one of them.
- "Prove it fails first": run the new test against the state before the change, watch it
  fail, and put the observed failure in the commit message.
- Code and tests state what they do now: no comment about seeds, tasks, dates or earlier
  versions. No command, script or document lists test files.
- The one addition to the command list is `catalog page`, the owner's by the seed. No
  reply member, no error code and no host member is added. The core's memory and the core
  object keep their sizes.
- The board is not touched. The firmware is built with `python3 firmware/fw.py build`
  only, never flashed here.
- Every task that changes a page of `agent/` or `docs/` runs the onboarding suite; the
  decisions a task takes beyond the seed go into `docs/drifts.md` under "Seed 44" in the
  task's commit.

- [x] 1. The walk and the preview in the converter's library
  - Set the seed's `state.json` to `in_progress`.
  - `converter/lib/odrg.js`: `reader(data)` with `loopMs()` and `next()`; `decode` built
    on it, its results and refusals unchanged. `converter/lib/odrgx.js`:
    `framesReader(data, header)`; `decodeFrames` built on it.
  - `converter/lib/thumbnail.js`: `keyOf`, `maker` with its steps, `make`, the sampling,
    the palette, the nearest colour, the row flip, the GIF89a layout and the LZW of the
    design; `converter/lib/errors.js`: `preview-too-large`; `converter/lib/index.js`
    offers `thumbnail`.
  - Tests in `converter/tests/thumbnail.test.js`: the key against `node:zlib`'s CRC-32;
    frames, a text and a clock, each read back with a GIF reader written in the test: the
    loop extension, the delays at the bounds (a 100 ms file, a 2,880 ms one, a 15-minute
    one), the picture at each sample time compared with `odrg.decode`'s or `pictureAt`'s
    picture through the palette, the top row first; the palette of at most 256 colours
    and of more, its ties, its padding; the nearest colour's tie; the size steps to 12 and
    6 pictures and `preview-too-large` (with a noise animation); a refusal of every
    invalid vector with the reason `decode` gives; the walk handing out a new picture per
    record without keeping them (a file of 3,000 records made in the test); `maker`'s
    steps giving the same bytes as `make`. `converter/tests/browser.test.js`: the same
    previews in Chrome as in Node.js. `converter/tests/library.test.js`: the number of
    reasons. The existing decode, odrgx and stored-answer tests pass unchanged.
  - `docs/converter.md` names the module in "The library"; `docs/reasons.md` lists the
    reason. Drifts: the sample times, the delay's rounding, the GIF's fixed layout, the
    reader's two parts.
  - Suites: `npm test --prefix converter`, the converter's Python suite, onboarding.

- [x] 2. The subcommand `thumbnail`
  - `converter/cli/arguments.js`: `thumbnail` in `NAMES` and the tool's usage, its
    `SPECS` with the variadic `FILE`, `--out`, `--catalog`, `--card` and the check of the
    two forms. `converter/cli/thumbnail.js`: the two forms, `parseCatalog`,
    `formatCatalog`, the names with `--card`, the passed-over lines; `main.js` maps it.
  - Tests in `converter/tests/thumbnailtool.test.js` (run as a process, as `cli.test.js`
    does): `--out` writes `make`'s bytes and writes nothing on a refused file (status 1,
    one `error:` line); `--catalog` makes the folder, adds GIFs and lines, adds a name to
    a key it holds without writing its GIF again, sorts keys and names by their bytes,
    escapes a name, writes the shape of the requirements byte for byte, names a file
    under `--card` by its path with `/` and one outside by its own name, passes over a
    refused file with its line and status 0, and refuses a malformed `catalog.js` as a
    fault of the tool; the usage errors (no form, both, `--out` with two files) give 2;
    nothing is written on standard output. `converter/tests/docs.test.js` and
    `cli.test.js`: six subcommands.
  - `docs/converter.md`: the subcommand's section with its usage line and an example, the
    table of subcommands, the status table. Drift: `--catalog` makes its folder.
  - Suites: `npm test --prefix converter`, onboarding.

- [x] 3. The command `catalog page` in the core
  - `core/src/commands.cpp`, `core/src/catalog.h`, `core/src/catalog.cpp`:
    `catalog_page` as the design has it.
  - Tests in `tests/core/test_catalog_page.py`, with the test host: both storages' pages
    read whole, page by page, against the files the PC library writes; offsets in a page,
    at its end and past it; a page without entries; `generation` as `catalog` gives it;
    `null` and the empty text for a storage `none`, `damaged`, `absent` and without a
    card; `busy` during a rebuild of that storage and not during one of the other nor
    during an open upload; `storage-error` with `--no-storage`; `bad-argument` for every
    other form (page 16, a word for a number, a missing or extra word, an offset above
    4,294,967,295); the escaping of a page holding a quote, a backslash and a byte above
    `~`, with `next` counting the bytes given; one `read_at` a call
    (`--trace-calls`); the memory figures of `tests/core/test_memory.py` and
    `test_drive.py` unchanged.
  - `docs/commands.md`: the command in the catalog section with an example;
    `docs/core.md`: the host rules and the catalogs; `docs/catalog.md`: the key. Drift:
    the reply holds fewer bytes when their escaped form would not fit.
  - Suites: the core's, onboarding.

- [x] 4. The command through the emulator and the command tool
  - `odrigctl/cli.py`: `catalog page internal|external PAGE OFFSET`.
  - Tests: `tests/emulator/` runs the emulator on a show folder with a catalog and a
    `--drive` with one and reads a page of each over the serial link and over HTTP with
    `odrigctl`; the command tool's synopsis test.
  - `docs/emulator.md`: the command tool's new form.
  - Suites: the emulator's, onboarding.

- [x] 5. The folder `thumbnails/` and the hosts of the app
  - `thumbnails/` made with the subcommand from `test-animations/` and the valid vectors
    (`tests/vectors/valid`, `texts/valid`, `widgets/valid`, `containers/valid`).
  - `converter/tests/thumbnails.test.js`: the folder's shape and its names; the GIFs of
    the tracked sources are `make`'s. `converter/tests/library.test.js`: the tracked GIF,
    MP4 and MOV files are exactly `thumbnails/*.gif`.
  - `emulator/httpd.py`, `app/apptool/paths.py`, `app/apptool/webserver.py`,
    `app/apptool/stage.py` as the design has them. Tests: `tests/emulator/test_page_files.py`
    (the served table, `image/gif`, 404 beside it), `tests/app/test_tool.py` (staging and
    the server), `tests/apk/test_apk.py` (the APK's files), `tests/app/test_scope.py` (the
    one import from `thumbnails/`). The firmware tool's image and `pack` take nothing of
    `thumbnails/`: a test of each.
  - `docs/emulator.md` and `docs/android-app.md`: what the hosts serve and pack. Drift:
    the folder's first content.
  - Suites: the converter's, the emulator's, the app's, the firmware tool's, onboarding.

- [x] 6. The app reads the pages
  - `app/www/commands.js`: `catalogPage(storage, page, offset)` with its reply checked.
    `app/www/client.js`: the catalog's occasions, `noteCatalog`, the read, the keys,
    `keyOf`. `app/www/screens/catalogs.js`: the shared answer and its replies noted.
  - Tests (a target of the test's own, as `tests/app/test_catalog.py` has): `catalog` at
    the first answer, after an answer after a silence and after a complete list; the
    sixteen pages of each `ok` storage read in order, a line cut between two replies;
    nothing read again for the same generation and entries, read again after a change of
    either; the keys kept while a read runs and dropped at a state other than `ok`, at a
    silence and at another target; a page of another generation, `busy`, `null`, another
    refusal; a target that refuses `catalog page` and one that refuses `catalog`, each
    asked as the requirements say; Settings' text from the shared answer; the operator's
    requests going first.
  - `docs/android-app.md`: the table of thirty-five lines and the reading.
    `tests/app/test_docs.py`: the table.
  - Suites: the app's, onboarding.

- [x] 7. The app shows the previews
  - `app/www/previews.js` (the default catalog and `sourceOf`), `app/www/screens/show.js`
    (the square in the rows, the now-playing panel), `app/www/index.html`,
    `app/www/style.css`, `app/www/main.js`.
  - Tests in Chrome against the emulator, on a show and a drive with catalogs whose files
    are in the default catalog, and on a show without a catalog: the rows with their
    previews at the root and inside a folder, a row whose key is unknown and a faulty row
    with an empty square, folder rows and the Tests group without one, the image's
    attributes, a tap on the square playing; the now-playing panel with and without a
    preview and hidden as the requirements say; the previews after `catalog rebuild
    internal` on the show without a catalog. `tests/app/test_look.py`: a row in selection
    mode with its note at 320, 360 and 740 px.
  - `docs/android-app.md`: the previews in the rows and the panel.
  - Suites: the app's, onboarding.

- [ ] 8. The phone's own previews
  - `app/www/convert.js` (`previewMaker`), `app/www/previews.js` (IndexedDB, `makeOwn`),
    `app/www/screens/storage.js` and `app/www/screens/author.js`.
  - Tests in Chrome against the emulator: an animation uploaded from the Upload screen and
    a text saved from its form get their previews, kept across a reload; the default
    catalog's key wins and its phone copy is dropped at the start; a refused preview keeps
    nothing and says nothing; a web view without IndexedDB keeps the preview for the run.
  - `docs/android-app.md`: the phone's catalog of previews.
  - Suites: the app's, onboarding.

- [ ] 9. The default preview catalog from every source
  - Runs of `thumbnail --catalog thumbnails` over every source the seed lists, the two
    card copies with `--card`; the passed-over files and the sources not at hand noted.
  - `thumbnails/` committed; its test of task 5 passes.
  - `agent/animation-guide.md`: the row of the preview; `agent/vocabulary.md`: the
    preview; `docs/decisions.md`: the GIF's second role and the change-log entry;
    `docs/drifts.md`: the tracked previews as the media the repository holds.
  - Suites: the converter's, onboarding.

- [ ] 10. Every suite, the firmware and the APK
  - Every suite this computer runs; `python3 firmware/fw.py build`; the APK built and its
    suite run; the APK's size, the number of previews and their size in the commit
    message and in the change-log entry.
  - `AGENTS.md`: seed 44's line, built with the owner's session open.

- [ ] 11. The owner's session
  - The firmware flashed; `odrigctl catalog page external 0 0` compared with the card's
    `catalog-00.txt`; the previews on a phone with the APK against the board, and the
    preview of an animation uploaded from the phone.
