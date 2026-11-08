# Design

## The pick (`convert.js`, `screens/storage.js`, `index.html`)

- `inspectReady(file, canvas)`: the part of `prepareReady` that reads the first 36 bytes:
  the ending, the size, the header, the canvas, a container's payload size and its frames'
  canvas. `prepareReady` calls it, then reads the whole file as today.
- `#ready-file` takes `multiple`, its label `Choose ready-made animations`. A change with one
  file goes to today's `chooseReady`; with two or more to the list. `#batch-more`, a second
  hidden input, takes `Add more`.
- `#batch`, a part of the Upload panel above `#chosen`: `#batch-sum`, `#batch-capacity`, the
  storage `#batch-storage`, `#batch-destination`, `#batch-rows` (a list of rows, each with
  the file's name, a name field, its size, its state and `Remove`), `#batch-upload`,
  `#batch-locked-reason`, `#batch-stop` and `#batch-retry`.
- A row: `{file, size, name, edited, state, reason, percent, tries, id, ending, inspected}`.
  Rows refused at the pick keep `refused` and their reason.
- The form of the list is a `destinations.capture()` of the first pick; `select` and
  `synchronize` move it as the single form's until the press.
- Names: `fileName(file.name, taken, ending)` in the list's order, `taken` holding the
  destination's names and the rows above; the destination's names are
  `client.state.rootNames.files` for Internal, and the file names of the external rows of
  `client.state.animations` at the browsed level for External, else none. A row's own text
  is checked with `destinations.pathOf`, and against the other rows.
- The sum: the sizes of the rows not refused; `fits(sum, free)` against
  `space.free` or `space.external.free`.

## The run (`app/www/batch.js`)

- `start(items, form, {guarded})`, `stop()`, `retry()`, `running()`, `rows()`, `line()`,
  `watch(fn)`, `seen()`. Items are `{name, storage, folder, size, read, replace}`; `read()`
  gives the bytes and the facts of a full check, or throws the reason.
- The run takes `client.setContentBusy("batch")` at its start and lets it go at its end.
- A file's turn:
  1. wait while the page is hidden (line: paused) or the link does not answer (line:
     waiting);
  2. `checking`; `read()`;
  3. a preflight, `client.uploadSnapshot(level)`: `busy` waits 2 s on the screen and tries
     again, up to 30 times; a request cancelled by leaving the screen waits and starts the
     turn again; a lost link waits for the link and starts again;
  4. the target, the card, its catalog and the folder: a change of target or a destination
     that no longer holds ends the run; then `destinations.validate` with the captured
     generation for the first file sent after the press alone; a collision, a moved
     catalog or no space fails the file;
  5. `uploading()` through `client.upload()`, its `report` into the row; `busy` of begin
     as in 3; `stale` of the board's storage starts the turn again once; `no-upload` after
     the page was hidden during the file, once; a lost link before the last byte had its
     reply: `upload cancel`, then once again; a lost link after: failed in today's words;
     `the address changed`: the run ends with `The target changed.`;
  6. success: `uploaded as animation <id>` or `uploaded to the card`, its preview made as a
     single ready-made file's, the run waiting for the preview of the file before.
- `Stop` sets a flag the run reads between files and in its waits; rows not sent become
  `not sent`.
- The failure words are `uploadRefusalWords(error, external, bytes, space, reason)` of
  `upload-destination.js`, shared with the single form, and the row drops a sentence that
  says to select the file again or press Upload again.
- `previews.makeOwn` gives a promise that settles when the preview is made or refused.

## The line and the locks

- `index.html`: `<p id="batch-line" class="pill" role="status" hidden>` between `#top` and
  `#mini-indicator`, sticky as the top is; `main.js` takes its tap to Upload and `seen()`.
- `storage.js`'s `lockReason` says `A batch upload is under way.` first while a run lasts;
  `author.js` disables `author-upload` and says it in `author-locked-reason`.
- Deleting and moving on Animations follow `client.contentBusy()`, which the run holds.

## Tests

`tests/app/test_batch.py`, scenario `batch.js`, in Chrome against the emulator, a card
given with `--drive`, and stand-ins of the target, with the cases of the seed's list.

## Documents

`docs/android-app.md`, `tests/app/test_docs.py`'s counts, `docs/drifts.md`.
