# Tasks: Converter and reference codec (seed 01)

Rules for every task:

- One task is one commit on `master`. The same commit ticks the task's checkbox in this file.
- Stage named paths only (`git add <path> ...`), never `git add -A`, `git add .` or
  `git commit -a`. After committing, read `git show --stat` and confirm it lists exactly the
  files of the task.
- The tests of a task are in the task's commit. Before committing, run
  `python -m unittest discover -s tests/converter -t .` from the repository root; it passes.
- Where a task says "Prove it fails first", run the new test against the state described,
  watch it fail in the way described, and put the observed failure in the commit message.
- Code and tests state what they do now. They carry no comment about seeds, tasks, dates or
  earlier versions.
- No command, script or document lists test files; the suite is selected by discovery.
- `animations/`, `tools/`, `firmware/`, `esp32-backup/` and `scratch/` hold untracked files
  that are not part of this work. Do not move, edit, delete or stage them.
- Answers to questions that come up are recorded in `docs/drifts.md`, not asked.

- [x] 1. Package skeleton, command-line frame and test command
  - Create `.gitignore` (`/.venv/`, `/build/`, `__pycache__/`), `odrig/__init__.py`,
    `odrig/__main__.py`, `odrig/errors.py` (`Rejection`, `NOT_FOUND`) and `odrig/cli.py`:
    `main(argv)` with `argparse` subcommands, status 0 on success, status 2 on a usage
    error, and a `Rejection` turned into `error: <reason>: <detail>` with status 1.
  - Create `tests/__init__.py`, `tests/converter/__init__.py` and
    `tests/converter/test_cli.py`: no subcommand and an unknown subcommand give status 2; a
    `Rejection` gives the error line and status 1.
  - Start `docs/converter.md` (setup with a project-local `.venv`, the test command) and
    `docs/reasons.md` (`not-found`).
  - Set `"state": "in_progress"` in
    `project-seeds/01-p0-converter-and-reference-codec/state.json`.
  - Prove it fails first: add a temporary `tests/converter/test_probe.py` holding one failing
    test and run the test command. Failing looks like `FAILED (failures=1)` naming
    `test_probe`, which shows that discovery runs a file nobody listed. Delete the file
    before committing.
  - Requirements: 1.1, 1.2, 1.3, 1.4, 2.1, 2.2, 2.3, 20.1, 21.1, 21.2, 21.3

- [x] 2. Strict JSON, and reading and writing JSON frames
  - Create `odrig/strictjson.py` (`loads`, `members`, `integer`) and `odrig/jsonframes.py`
    (`Animation`, `loads`, `read`, `merged`, `dumps`, `write`, `colour_count`) as the design
    describes, with the check order and the canonical layout given there.
  - `tests/converter/test_jsonframes.py`: the example of `docs/format.md` is accepted; one
    rejected file for every reason of Requirement 3, including a repeated member name, a
    byte-order mark, `1.0` and `true` where an integer is expected, and a version 2 file
    with an extra member (reported as `bad-version`); the canonical bytes of a known
    animation; merging; read-after-write; two writes giving identical bytes.
  - Add the JSON frames table to `docs/reasons.md`.
  - Requirements: 2.4, 3.1, 3.2, 3.3, 3.4, 4.1, 4.2, 4.3, 4.4

- [x] 3. ODRG reference decoder and the `decode` subcommand
  - Add `Decoded` and `decode` to `odrig/odrg.py`, following the nine steps of the design.
    Standard library only.
  - Add the `decode` subcommand, with output through a `.part` file moved into place.
  - `tests/converter/test_odrg_decode.py`: files assembled by hand in the test from the
    examples of `docs/format.md` (Rice code of 5 with k = 1 is `1101`; Gamma codes of 1, 2
    and 5; codes 0 to 4 and 255 as residuals; each predictor on a 3 x 2 canvas with results
    worked out in the test; the neighbour of a row's first pixel; a palette file; a
    compressed body) and one hand-made file for every reason of Requirement 6, including a
    Gamma code cut off by the end of the data and padding bits that are not zero (accepted).
  - Extend `test_cli.py`: `decode` replaces an existing output; a rejected input leaves no
    output and no `.part` file.
  - `docs/format.md`, "What a reader rejects": add a file that ends early, an invalid
    DEFLATE stream, a width or height of zero, a stored mode byte other than `0x40` and
    bytes after the DEFLATE stream; state that a reader does not examine padding bits.
  - Add the ODRG table to `docs/reasons.md` and a `decode` section to `docs/converter.md`.
  - Requirements: 1.3, 1.5, 5.1, 5.2, 5.3, 5.4, 5.5, 6.1, 6.2, 6.3, 8.1, 8.3, 22.4

- [x] 4. ODRG encoder and the `encode` subcommand
  - Add `palette_for`, `to_buffer`, `coded_record`, `stored_record`, `best_record`,
    `container` and `encode` to `odrig/odrg.py`, and the `encode` subcommand with
    `--uncompressed`.
  - `tests/converter/test_odrg_encode.py`: seeded random animations, with and without a
    palette, on canvases from 1 x 1 to 60 x 6, decode to their source; for seeded random
    frame pairs `best_record` is no longer than any of the 64 `coded_record` results and
    picks the first of equal ones in the stated order; noise frames give stored records;
    identical neighbours are merged; a frame of 200,000 ms becomes records of 65,535,
    65,535, 65,535 and 3,395 ms; the palette of a known colour set is in the stated order;
    `canvas-too-large` and `too-many-frames`; flag bit 0 with and without `--uncompressed`;
    an invalid source is rejected with its JSON frames reason.
  - Extend `test_cli.py`: `encode` then `decode` of a merged source gives a byte-identical
    file; two `encode` runs give identical bytes.
  - Add an `encode` section to `docs/converter.md` and the two encode reasons to
    `docs/reasons.md`.
  - Requirements: 1.6, 7.1, 7.2, 7.3, 7.4, 7.5, 7.6, 7.7, 7.8, 7.9, 8.2

- [x] 5. The `check` subcommand
  - Add `check` with `--format`, printing the lines of Requirement 9.
  - `tests/converter/test_check.py`: the exact output for a JSON frames file, for a
    compressed palette ODRG file and for an uncompressed ODRG file without a palette;
    `--format` overriding the file name; status 2 when the format is not known; a rejected
    file prints nothing to standard output.
  - Add a `check` section to `docs/converter.md`.
  - Requirements: 9.1, 9.2, 9.3

- [x] 6. Mapping file reader
  - Create `odrig/mapping.py` (`Leg`, `Mapping`, `read`).
  - `tests/converter/test_mapping.py`: `mapping/legs-2.json` gives 60 x 6 with two legs and
    `mapping/legs-10.json` gives 60 x 30 with ten; one rejected file for every rule of
    Requirement 10 (unknown member, version 2, width 0, no legs, repeated leg number,
    repeated pin, a `first_led` of another word, an empty `rows`, a row listed twice, a row
    missing, a row above H, W * H above 65,534); a missing file is `mapping-missing`.
  - `docs/mapping.md`: add the rules a mapping file must meet, and write the LED formula
    with the file's `width` and the leg's number of rows in place of 60 and 180.
  - Add the mapping table to `docs/reasons.md`.
  - Requirements: 10.1, 10.2, 10.3, 22.4

- [x] 7. Hello world and DVD bounce generators and their tracked sources
  - Create `odrig/generators/__init__.py`, `rainbow.py`, `hello_world.py` and
    `dvd_bounce.py` with the expressions, the font and the layout of the design.
  - Write `animations/hello.json` and `animations/dvd.json` with the generators and
    `mapping/legs-2.json`, and track these two files. Stage them by name; the folder holds
    untracked files that stay as they are.
  - `tests/converter/test_generators.py`: Hello world has 255 frames of 20 ms, the same 122
    lit pixels in every frame, tops of letters on row 6, text from column 4 to column 56,
    and every lit pixel showing each of the 255 rainbow colours exactly once over the 255
    frames; DVD bounce has 232 frames of 180 ms, a
    2 x 2 square starting at columns 1 to 2 and rows 5 to 6, moving one pixel in each
    direction per frame; the tracked files equal the generator output byte for byte; a
    canvas of 52 x 6 and one of 2 x 2 are `canvas-too-small`; each animation encodes and
    decodes back to identical frames, compressed and uncompressed; the four encoded sizes
    are within 2 percent of 17,731, 1,134, 3,799 and 1,594.
  - Add a generators section to `docs/converter.md`.
  - Requirements: 7.10, 7.11, 10.1, 15.1, 15.2, 15.3, 15.4, 15.5

- [x] 8. Dense test clip generator
  - Create `odrig/generators/dense.py` with the expressions of the design and the arguments
    `OUT --mapping MAPPING [--seconds N]`.
  - Extend `test_generators.py`: for `mapping/legs-10.json` and 10 seconds the clip is
    60 x 30 with 500 frames of 20 ms, more than 256 colours and no dark pixel; it encodes
    and decodes back to identical frames, compressed and uncompressed; a 1-second clip for
    `mapping/legs-2.json` is 60 x 6 with 50 frames.
  - Requirements: 7.11, 16.1, 16.2, 16.3

- [x] 9. Valid test vectors
  - Create `tests/converter/build_vectors.py` with the valid set of the design, run it, and
    track `tests/vectors/valid/`.
  - `tests/converter/test_vectors.py`: every `NAME.odrg` in the folder has a `NAME.json`
    and decodes to it record by record; no `.odrg` is above 4,096 bytes; the coverage of
    Requirement 18 criterion 3, computed from the headers, the mode bytes and the codes of
    the tracked files, with one assertion per feature; the folder holds exactly the names
    the builder produces, and every file the builder makes without zlib is byte-identical
    to the builder's output. The test lists the folder; it names no file.
  - Prove it fails first: with the `escape` vectors moved out of the folder, the coverage
    test fails with the message that no vector uses the escape code. Move them back.
  - Describe the vector layout and the build command in `docs/converter.md`.
  - Requirements: 18.1, 18.2, 18.3, 18.4, 18.5

- [x] 10. Invalid test vectors
  - Add the invalid set to `build_vectors.py`, run it, and track `tests/vectors/invalid/`.
  - Extend `test_vectors.py`: every file in the folder is rejected with the reason before
    the first dot of its name; every reason of Requirement 6 has at least one file; the
    cases of Requirement 19 criterion 2 are present; for every case of the builder, the
    file before its one change decodes and the file after it is rejected; the folder holds
    exactly the names the builder produces, and every file the builder makes without zlib
    is byte-identical to the builder's output.
  - Prove it fails first: with one file copied under the name of another reason, the test
    fails stating the expected and the reported reason. Remove the copy.
  - Requirements: 6.1, 19.1, 19.2, 19.3, 19.4

- [x] 11. Show reader, the `pack` subcommand and the example show
  - Create `odrig/show.py` (`Item`, `Show`, `read`, `files`) and `odrig/pack.py`, and add the
    `pack` subcommand with `--uncompressed`.
  - Create and track `shows/example/show.json` as in the design.
  - `tests/converter/test_show_pack.py`: the example of `docs/show.md` is accepted; one
    case for every reason of Requirement 14, in the order of its table when two apply; the
    output folder of the example show holds exactly `mapping.json`, `show.json`,
    `hello.odrg` and `dvd.odrg`, the two JSON files byte-identical to their inputs, each
    `.odrg` passing `check` and decoding to the frames of its source; `--uncompressed`
    clears flag bit 0 in every file; a show naming one file twice writes it once; a
    non-empty output folder is `output-not-empty`; a refusal leaves the output folder and
    its parent as they were.
  - Add a `pack` section to `docs/converter.md` and the show table to `docs/reasons.md`.
  - Requirements: 1.3, 14.1, 14.2, 14.3, 14.4, 14.5, 14.6, 14.7, 14.8, 14.9, 17.1, 17.2

- [x] 12. Fitting a picture to the canvas
  - Create `requirements.txt` with numpy at an exact version, and `odrig/media.py` with
    `source_rect` and `resample`.
  - `tests/converter/test_import_fit.py`: for each fit, a source wider than the canvas
    shape and one taller, with the rectangle and the canvas picture worked out in the test;
    a 4 x 4 block source shrunk to 2 x 2 is the plain mean of each block; a shrink by 1.5
    weights the shared source pixels by half; `fit` gives black bars and a blended edge
    column; growing repeats source pixels; a result exactly between two whole numbers
    rounds up; the top source row lands on canvas row H.
  - `tests/converter/test_stdlib_only.py`: a fresh interpreter that runs `encode`,
    `decode`, `check`, `pack` and the three generators has none of `numpy`, `PIL` and `av`
    in `sys.modules`.
  - Requirements: 12.1, 12.2, 12.3, 12.4, 12.5, 12.6, 20.2, 20.3

- [x] 13. The `import` subcommand: readers, timeline and ranges
  - Add Pillow and av to `requirements.txt` at exact versions, and confirm the PyAV names
    the design uses against that version.
  - Add `source_frames`, `tick_pictures` and `import_media` to `odrig/media.py`, and the
    `import` subcommand with `--mapping`, `--fit`, `--start` and `--duration`.
  - Create `tests/converter/media_fixtures.py`, which builds a GIF, an mp4 and a mov in a
    temporary folder as the design describes.
  - `tests/converter/test_import_timeline.py`: a GIF with delays of 30, 50, 70 and 0 ms
    gives the tick pictures worked out in the test, with the last delay counted as 100 ms;
    transparent pixels are black; the mp4 and the mov give the mapping's canvas size, every
    `ms` a multiple of 20 and a total within 20 ms of the requested length; a 25 frames per
    second source puts each source frame on two ticks; `.MP4` in capitals is accepted; a
    `.png` name is `unsupported-media`; a text file named `.mp4` is `unreadable-media`.
  - `tests/converter/test_import_range.py`: `--start` and `--duration` select the stated
    ticks; durations of 30 and 50 ms give 2 and 3 ticks and 9 ms gives 1; each condition of
    `bad-range`; two runs give identical bytes.
  - Add an `import` section to `docs/converter.md`, with the three fits, and the import
    reasons to `docs/reasons.md`.
  - Requirements: 1.6, 11.1, 11.2, 11.3, 11.4, 11.5, 11.6, 11.7, 11.8, 11.9, 13.1, 13.2,
    13.3, 20.2

- [ ] 14. Documentation and final check
  - Complete `docs/converter.md` (every subcommand with one example, packing the example
    show into `build/example-show`, the vector layout) and `docs/reasons.md`, and add one
    sentence to `README.md` pointing to `docs/converter.md`.
  - `tests/converter/test_docs.py`: every reason constant of `odrig/errors.py` appears in
    `docs/reasons.md`; `docs/converter.md` names every subcommand and the test command.
  - `tests/converter/test_scope.py`: no module of `odrig/` imports `socket`, `ssl`, `http`,
    `urllib.request` or `serial`, and none reads `sys.platform`, `os.name` or `platform`.
  - Run the whole suite on macOS in a fresh `.venv` built from `requirements.txt`.
  - Set `"state": "completed"` and `completedAt` in
    `project-seeds/01-p0-converter-and-reference-codec/state.json`.
  - Requirements: 1.1, 1.7, 20.4, 21.4, 21.5, 22.1, 22.2, 22.3
