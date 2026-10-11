# Tasks: JavaScript converter (seed 06)

Seeds 01 and 05 are implemented before these tasks start: they use the Python package
`odrig` as seed 05 left it, the test vectors and the mapping files. Where the real code
differs from what this spec's design relies on, follow the code and record the difference
in `docs/drifts.md`.

Task 8 needs the network, for `npm`. Task 9 needs the Chrome that is installed. No task
needs the board. The design's two tables "Assumed, to be verified" name what task 8
settles: it writes what it found into `docs/drifts.md`, and task 10 writes it into
`docs/converter.md`.

Rules for every task:

- One task is one commit. The same commit ticks the task's checkbox in this file.
- Stage named paths only (`git add <path> ...`), never `git add -A`, `git add .` or
  `git commit -a`. After committing, read `git show --stat` and confirm it lists exactly the
  files of the task.
- The tests of a task are in the task's commit. Before committing, run
  `npm test --prefix converter` and
  `.venv/bin/python -m unittest discover -s tests/converter -t .` from the repository
  root; both pass.
- Where a task says "Prove it fails first", run the test against the state described, watch
  it fail in the way described, and put the observed failure in the commit message.
- Code and tests state what they do now. They carry no comment about seeds, tasks, dates or
  earlier versions, and none that says a function was ported.
- No command, script or document lists test files; the suite is selected by discovery.
- No file of `odrig/`, `core/`, `emulator/`, `odrigctl/` or `firmware/` changes. The Python
  tool is the measure: where the JavaScript tool and the Python tool differ, the JavaScript
  tool is changed, unless the design names the difference.
- A detail is taken from the Python source, character for character. A test compares it
  with what the Python tool writes; it is not typed a second time into a test.
- No file of `converter/lib/` imports anything but `./<name>.js`, or names a module of
  Node.js or a package.
- `npm` is run with `--prefix converter` only. Nothing of `converter/node_modules/` is
  staged. No package is installed for the whole computer, and no browser is installed.
- `animations/`, `tools/`, `firmware/wled-16.0.1/`, `esp32-backup/`, `scratch/` and the
  stock image at the repository root hold untracked files that are not part of this work.
  Do not move, edit, delete or stage them.
- Answers to questions that come up are recorded in `docs/drifts.md`, not asked.

- [x] 1. The frame of the tool, and the test command
  - Set `"state": "in_progress"` in `project-seeds/06-p1-javascript-converter/state.json`.
  - Create `converter/package.json` as the design prints it, without `dependencies` for
    now, and add `/converter/node_modules/` to `.gitignore`.
  - Create `converter/odrig.js`, `converter/cli/main.js`, `cli/arguments.js` and
    `cli/files.js`: the version check, the parser for the five subcommands with their
    usage texts, the statuses, the error line, `read` and `write` with the table of the
    system's words. A subcommand whose code is not there yet is not in the table of
    subcommands and is answered as an unknown one.
  - Create `converter/lib/index.js` and `lib/errors.js`.
  - Create `converter/tests/support.js`: both tools run as child processes, the Python
    program found as the design says, temporary folders, and a generator of data from a
    seed.
  - `tests/cli.test.js`: the statuses; the error line of a rejection, in one line, with
    white space collapsed; `--help`; every usage error of Requirement 2 criterion 6 that
    needs no subcommand's code; `--name value`, `--name=value`, options in every place and
    `--start -1` taken as a value, on the parser; `read` of a missing file, of a folder and
    `write` into a folder that does not exist, with the words the Python tool writes;
    `write` leaves no part file; an old version of Node.js refused.
  - `tests/library.test.js` as the design lists it.
  - Prove it fails first: with the line `import fs from "node:fs";` added to
    `lib/errors.js`, `library.test.js` fails naming that file. Undo it.
  - Requirements: 1.1, 1.2, 1.3, 1.4, 1.8, 2.1, 2.3, 2.4, 2.5, 2.6, 2.7, 2.10, 3.1, 3.5,
    3.7, 17.4, 18.1, 18.2, 18.4

- [x] 2. Whole numbers, strict JSON and JSON frames
  - Create `lib/whole.js`, `lib/strictjson.js` and `lib/jsonframes.js` as the design's
    sections of those names describe them.
  - Create `converter/tests/reference.py` with its first requests, as the tests of this
    task need them.
  - `tests/strictjson.test.js` and `tests/jsonframes.test.js` as the design lists them.
    The Python side of each comparison is `python -m odrig check --format json` on the
    same bytes; the JavaScript side is the library's rejection with the file's name put
    in front of the detail.
  - Tests of `whole.js`: fractions against values worked out in the test; floor division
    of negative numbers; `fromDecimal` for `12.5`, `.5`, `1e3`, `-0.0005` and `0.0005`;
    `sixDigits` against Python's `format(x, ".6g")` for a list of values given by
    `reference.py`.
  - Prove it fails first: with the check for a member named twice left out of
    `strictjson.js`, the test of such a text fails: the file is accepted where `bad-json`
    is expected. Undo it.
  - Requirements: 1.5, 3.2, 3.3, 3.4, 4.1, 4.2, 4.3, 4.4, 4.5

- [x] 3. The DEFLATE decoder, the ODRG decoder, `decode` and `check`
  - Create `lib/inflate.js` and the decoder of `lib/odrg.js`. Add `decode` and `check` to
    the table of subcommands.
  - `tests/inflate.test.js` and `tests/decode.test.js` as the design lists them, with the
    request `inflate` of `reference.py` for zlib's verdicts.
  - Extend `tests/cli.test.js`: `check` of a name without a known ending is a usage error;
    `--format` overrides the name; the endings in capital letters.
  - Prove it fails first: with the check for bytes after the DEFLATE stream left out, the
    test of the invalid vectors fails for `trailing-bytes.after-deflate.odrg`, which is
    accepted. Undo it.
  - Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 6.1, 6.2, 6.3, 6.4, 9.1, 9.2, 9.3, 9.4

- [ ] 4. The DEFLATE compressor
  - Create `lib/deflate.js` as the design's "The DEFLATE compressor" describes it.
  - `tests/deflate.test.js`, the parts that need no encoder: for the six bodies of the
    design's table, given by the request `encode` of `reference.py`, and for the inputs of
    Requirement 8 criterion 6: zlib inflates every stream to its input with nothing left
    over, and so does `lib/inflate.js`; two runs give the same bytes; the stream of each of
    the six bodies is at most 5 percent larger than zlib's at level 9; the time limit of
    Requirement 8 criterion 7. Print the sizes of both in the test's output.
  - Prove it fails first: with matches switched off, so that every byte is written as a
    literal, the size test fails for Hello world with the size it measured. Undo it.
  - Put the measured sizes of the six bodies into the commit message.
  - Requirements: 8.1, 8.4, 8.5, 8.6, 8.7

- [ ] 5. The encoder and `encode`
  - Add the encoder to `lib/odrg.js`: `paletteFor`, `hueOrder`, `codes`, `dataSizes`,
    `bestRecord`, `codedRecord`, `storedRecord`, `container` and `encode`. Add `encode` to
    the table of subcommands.
  - `tests/encode.test.js` as the design lists it, and the rest of `tests/deflate.test.js`:
    Requirement 8 criteria 2 and 3 on whole files, through the command line of both tools.
  - Extend `tests/decode.test.js`: `encode` followed by `decode` gives back a merged
    source byte for byte.
  - Prove it fails first: with run mode taken before plain mode among forms of the same
    size, the test of identical uncompressed files fails. Put the source it failed for and
    the first byte that differs into the commit message. Undo it.
  - Requirements: 1.9, 2.11, 7.1, 7.2, 7.3, 7.4, 7.5, 7.6, 7.7, 8.2, 8.3, 9.5

- [ ] 6. Mapping files, show files and `pack`
  - Create `lib/mapping.js`, `lib/show.js`, `lib/pack.js` and `cli/folder.js`, from the
    Python files as they are in the repository. Add `pack` to the table of subcommands.
  - `tests/mapping.test.js` and `tests/pack.test.js` as the design lists them. The demo
    show's sources are written by the generators of the Python tool into a temporary
    folder.
  - If `odrig/mapping.py` does not read column legs yet, seed 05 is not finished: stop,
    and record that the task is blocked.
  - Prove it fails first: with the check of the output folder moved behind the sources, a
    `pack` into a folder that is not empty, with a source missing, fails the test:
    `file-missing` where `output-not-empty` is expected. Undo it.
  - Requirements: 10.1, 10.2, 10.3, 10.4, 10.5, 11.1, 11.2, 11.3, 11.4, 11.5, 11.6, 11.7

- [ ] 7. Fitting and the timeline, in the library
  - Create `lib/fit.js` and `lib/timeline.js` as the design's sections "fit", "timeline"
    and "How the library is given frames" describe them.
  - `tests/fit.test.js` and `tests/timeline.test.js` as the design lists them, with the
    requests `resample` and `ticks` of `reference.py`. The frames are made by the tests;
    no media file is read in this task.
  - A test of `importFrames`: a synchronous and an asynchronous source give the same
    animation; a source is asked for no frame after the part is covered, and its `return`
    is called; times given as whole numbers, as `[n, d]` of `Number`s and of `BigInt`s
    give the same ticks.
  - Prove it fails first: with the floor of `whole.js` replaced by the division of
    `BigInt`, which rounds toward zero, the test of `fit` with a source narrower than the
    canvas shape fails: the bar on the left has other values than the Python tool's. Undo
    it.
  - Requirements: 12.1, 12.2, 12.3, 12.4, 12.5, 12.6, 12.7, 12.8, 13.1, 13.2, 13.3, 13.4,
    13.5, 13.6, 15.1, 15.2, 15.3, 15.4, 15.5

- [ ] 8. Media on the command line: the two packages and `import`
  - Add `ffmpeg-static` 5.3.0 and `omggif` 1.0.10 to `converter/package.json` at these
    exact versions, run `npm install --prefix converter`, and track
    `converter/package-lock.json`. Before the install, list the entries of the home folder
    and of `~/Library/Caches`, `~/.npm` and `~/.cache` with their times; list them again
    afterwards, and name in `docs/drifts.md` what the install added.
  - Create `converter/ffmpeg.sha256` with the SHA-256 of the installed program for this
    Mac's platform, and record the first line of `ffmpeg -version`.
  - Create `cli/video.js` and `cli/gif.js` as the design describes them, and add `import`
    to the table of subcommands.
  - `tests/import.test.js` as the design lists it. The media are made by the requests
    `gif` and `video` of `reference.py`: the GIFs and videos of the Python suite's import
    tests, the GIFs of the design's assumption A6, a mov with transparency, and a video
    whose first frame is not at time zero.
  - Verify assumptions A1 to A6 of the design. For each, record what was found in
    `docs/drifts.md`; where one does not hold, take the way the table names.
  - Prove it fails first: with the canvas of `cli/gif.js` cleared before every frame, the
    test of the GIF whose later frames are smaller than the screen fails against the
    Python tool's JSON. Undo it.
  - Requirements: 1.6, 1.7, 2.2, 2.8, 2.9, 2.11, 3.6, 14.1, 14.2, 14.3, 14.4, 14.5, 14.6,
    14.7, 14.8, 14.9, 14.10, 14.11, 15.6, 17.1, 17.2, 17.3, 17.5, 18.3, 18.5, 18.6

- [ ] 9. The library in Chrome
  - Create `converter/tests/page/index.html` and `page/page.js`, and
    `tests/browser.test.js`, as the design's "The page of the Chrome test" describes them.
  - Run it with the Chrome that is installed. Record Chrome's version in the commit
    message.
  - Prove it fails first: with the line `import fs from "node:fs";` added to
    `lib/errors.js`, the test fails with the error the page posts, and not with a time-out.
    Undo it.
  - If Chrome cannot be started without a window by a program on this Mac, record what
    was tried, leave this task open and say so in the hand-over.
  - Requirements: 16.1, 16.2, 16.3, 16.4, 16.5, 1.9

- [ ] 10. The documents and the last check
  - Rewrite `docs/converter.md` and create `docs/reference-converter.md` as the design's
    table "Documents" lists them. Change `README.md`, `docs/emulator.md`,
    `docs/firmware.md`, `docs/reasons.md` and `docs/decisions.md` as it lists them.
  - `tests/docs.test.js` as the design lists it. Change `tests/converter/test_docs.py`,
    `tests/emulator/test_docs.py` and `tests/firmware/test_docs.py` where they read a
    command or a page that changed.
  - Read every acceptance criterion of Requirements 1 to 19 once more and name, for each
    one a program can check, the test that checks it; add a test where one is missing.
  - Run `npm test --prefix converter` and the four suites of Requirement 18 criterion 7.
    All pass. When `build/firmware/venv/bin/node` is there, run the suite of the
    JavaScript tool with that Node.js 20 as well, and record the result.
  - Write under "What is verified" of `docs/converter.md`: the versions of macOS, Node.js,
    npm, Chrome, Python, zlib and the decoder program that were used, and what was not
    run: Windows, Linux, and a Node.js other than those named.
  - Prove it fails first: `tests/docs.test.js` against `docs/converter.md` as it is before
    this task fails naming the first subcommand section without a `node converter/odrig.js`
    example.
  - Set `"state": "completed"` and `completedAt` in
    `project-seeds/06-p1-javascript-converter/state.json`. If task 9 is open, leave the
    state `in_progress`, leave this task open, and say in the hand-over what is left.
  - Requirements: 17.6, 18.1, 18.7, 18.8, 19.1, 19.2, 19.3, 19.4, 19.5, 19.6, 19.7
