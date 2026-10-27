# Design: previews of the animations in the app

## What this design relies on

- Every catalog page line is `<crc32> <bytes> <width> <height> <total_ms> <type> <name>`,
  the CRC-32 that of zlib and PNG over the whole file as eight lowercase hexadecimal
  digits; a line is printable ASCII without `"` and `\` (the name rule of
  `catalog_name_allowed` in `core/src/catalog.cpp`), at most 161 bytes, and ends in `\n`.
  The sixteen pages are `catalog-00.txt` to `catalog-15.txt` on the board's storage and
  `drive/catalog-00.txt` to `drive/catalog-15.txt` on the card (`kPageNames`), and the
  core already reads both through the host's `read_at` (`FileSource`).
- `content_read` (`core/src/content.cpp`) is the precedent: it refuses `storage-error`
  without `storage_changes`, reads with `read_at` into `core.chunk`, which holds nothing
  between commands, and writes the reply into the 1,024 bytes of `Reply`. `read_at` reads
  at most 512 bytes a call (`kFileBufferSize`). A rebuild is `core.rebuild`, `1 + storage`
  while one runs; `catalog` writes a storage's `generation` only when it is `ok` or
  `loading` (`write_state`).
- The emulator runs the core as it is and its `FolderHost.read_at` maps `drive/<name>` to
  the card's folder; the board's host does the same. `odrigctl`'s `catalog` takes nothing,
  `cancel` or `rebuild internal|external` (`odrigctl/cli.py`).
- `odrg.decode` (`converter/lib/odrg.js`) reads the header, inflates the whole body, reads
  the palette, then every frame record in order, building a new pixel buffer for each,
  then refuses trailing bytes; `odrgx.decodeFrames` compares the canvases, decodes the
  payload with `odrg.decode`, then checks the payload's size and the loop. `pictureAt`
  draws a text at `t % loopMs` and a clock with a seed. Library pictures keep the bottom
  row first.
- The command line's subcommands are the map `SUBCOMMANDS` of `converter/cli/main.js`,
  their usage and options the `SPECS` of `converter/cli/arguments.js`, which takes fixed
  positional arguments only. A rejection gives status 1 and one `error:` line.
- The app sends one request at a time (`app/www/client.js`, `due()`), in the order: the
  operator's, `status`, an upload's line, `list`, the saved order, `space`. `catalog` is
  sent only by Settings (`app/www/screens/catalogs.js`) as an operator's request.
- The emulator serves the app under `/app/` and the converter's library under
  `/app/converter/` (`emulator/httpd.py`, `app_files`), `app.py serve` serves them under
  `/` and `/converter/` (`app/apptool/webserver.py`, `file_of_the_app`), and the APK's
  staging copies them into `build/app/www` and `build/app/www/converter`
  (`app/apptool/stage.py`); all three serve only `.html`, `.css`, `.js` and `.json`.
- `tests/app/test_scope.py` lets a script import only files of `app/www` and
  `converter/<file>`, lets only `convert.js` import the library and only `target.js`
  fetch; `tests/apk/test_apk.py` pins the APK's files; `converter/tests/library.test.js`
  forbids tracked GIF, MP4 and MOV files and pins the number of reasons.

## The key

`thumbnail.keyOf(bytes)` gives `<crc32>-<length>`: the library's own table-driven CRC-32 of
zlib and PNG, eight lowercase hexadecimal digits, a dash and the length in decimal. The
app computes the same key from the bytes it uploads with its own `crc32.js` and the
length; a catalog line gives it as its first two words joined by a dash.

## The walk of a file

`odrg.js` gains `reader(data)`. It reads the header and refuses as `header` does, inflates
the body and refuses as `decode` does, reads the palette, and returns an object with the
header's fields, `loopMs()` and `next()`:

- `loopMs()` sums the durations of the record starts it can find from the record after the
  palette, stepping by each record's length, and stops at the first start it cannot read
  or whose length does not fit. It never refuses: a file it cannot sum is refused by
  `next()` at the record where `decode` refuses it, so the sum then does not matter.
- `next()` reads the next frame record exactly as `decode` does, with the same refusals in
  the same order, and returns `{ms, picture, mode}`, the picture the pixel buffer holds
  after it, three bytes a pixel; after the last record it refuses trailing bytes as
  `decode` does and returns `null`.

`decode` becomes `reader` read to its end, collecting `records` and `modes`: its results
and refusals do not change, which the existing suites and the stored answers check.
`odrgx.js` gains `framesReader(data, header)`: the canvas comparison of `decodeFrames`,
then `odrg.reader` of the payload, and at the end the payload's size and the loop checked
as `decodeFrames` does; `decodeFrames` becomes `framesReader` read to its end.

## The preview

`converter/lib/thumbnail.js`, offered by `index.js` as `thumbnail`:

- `maker(data)` returns `{step(), done, preview}`. Each `step()` does a bounded part of the
  work and returns whether the preview is made; `preview` is then the GIF's bytes. A
  refusal is thrown by the step that meets it.
  - The first step tells the kind by the magic: an ODRG file takes `odrg.reader`; an ODRGX
    container is read with `odrgx.readHeader`, a frames container with
    `odrgx.framesReader`, a text with `decodeText` and a clock with `decodeWidget`.
  - `L` is `loopMs()` for frames, the header's loop for a text or a clock.
  - Times `t_k = floor(k * L / 24)` for `k` 0 to 23. Each later step of frames reads up to
    `STEP_RECORDS` records (256), keeping a running start time and, for each `t_k` it
    passes, a copy of the picture on screen then: the picture of the last record that
    began at or before `t_k`. A picture is copied only when a sample needs it; nothing else
    is kept. A text or a clock draws its 24 pictures with `pictureAt(decoded, t_k, 1)`,
    a few a step.
  - The last step encodes: 24 pictures; above `LARGEST` (65,536) bytes, the pictures of
    even `k`, which are those at twelfths; above again, those of `k` divisible by 4, at
    sixths; above again, `Rejection("preview-too-large", ...)`. The samples at twelfths
    and sixths are a subset of those at twenty-fourths, so the file is walked once.
- `make(data)` runs `maker` to its end; `keyOf(data)` gives the key.
- The encoding of `N` pictures of `w` by `h`:
  - Colours are numbers `r << 16 | g << 8 | b`. A `Map` counts each colour's pixels over the
    `N` pictures; at most 256 colours are all taken, else the 256 with the largest count,
    a tie to the smaller number; the palette is sorted ascending and padded with zeros to
    `max(2, 2^ceil(log2(size)))` entries.
  - Each distinct colour's index is found once, by the nearest of the sum of squares, the
    lower index on a tie, and kept in a `Map`.
  - The rows are flipped: GIF row `y` is library row `h - 1 - y`.
  - The bytes: `GIF89a`; the logical screen descriptor (`w`, `h`, the packed byte
    `0x80 | 0x70 | (bits - 1)`, background 0, aspect 0); the global colour table; the
    application extension `NETSCAPE2.0` with sub-block `01 00 00`; for each picture the
    graphic control extension `21 F9 04 04 dl dh 00 00` (disposal 1, no transparency, the
    delay of 2.4), the image descriptor at 0, 0, `w` by `h`, no local table, then the LZW
    data; the trailer `3B`.
  - LZW: minimum code size `m = max(2, bits)`, clear `2^m`, end `2^m + 1`, codes from
    `2^m + 2`, width `m + 1` growing when the next code reaches `2^width`, up to 12 bits; a
    clear code first and whenever the next code would be 4,096, after which the table and
    the width start again; codes packed least significant bit first; sub-blocks of 255
    bytes. The dictionary is a `Map` from `prefix * 256 + index` to code.
- The module uses only the language, typed arrays, `Map`, and the library's own modules,
  so Node.js and a web page give the same bytes; `browser.test.js` compares them.
- `errors.js` gains `PREVIEW_TOO_LARGE = "preview-too-large"` among the reasons.

## The subcommand `thumbnail`

- `arguments.js`: `NAMES` gains `thumbnail`; its `SPECS` entry has the usage of the two
  forms, a positional `FILE` that takes one or more values (`variadic`), the options
  `--out`, `--catalog` and `--card`, and a check after parsing that exactly one of
  `--out` and `--catalog` is given, and with `--out` exactly one `FILE`, else a
  `UsageError`. The parser keeps its rule that an option given twice takes its last value.
  The tool's usage text names six subcommands.
- `converter/cli/thumbnail.js` does the work, `main.js` maps `thumbnail` to it:
  - `--out`: reads the file, `thumbnail.make`, writes the GIF with `files.write`; a
    rejection propagates as for every subcommand (status 1, nothing written).
  - `--catalog DIR`: makes `DIR` when missing, reads `DIR/catalog.js` as text when it is
    there with `parseCatalog`, which takes exactly the shape of 4.2 and fails with the tool's
    own error (status 70) on anything else. For each file in order: its bytes, its key; a
    key in the mapping gains the name; otherwise `thumbnail.make`, `DIR/<key>.gif` written,
    and an entry made; a rejection of the file writes
    `passed over: <FILE>: <reason>: <detail>` to standard error and the run goes on. At
    the end `formatCatalog` writes the mapping anew, keys and names sorted by their bytes,
    names written with `JSON.stringify` and every character above `~` as `\uXXXX`. Status
    0.
  - The name: with `--card ODRIG`, a FILE whose resolved path lies inside the resolved
    `ODRIG` is named by its relative path with `/`; every other FILE by `path.basename`.
- `docs/converter.md`: the section of `thumbnail`, its line in the table of subcommands, the
  module in "The library", and the status table's line for `thumbnail --catalog`.

## The command `catalog page`

- `core/src/commands.cpp`: in the `catalog` branch, `words.count == 5`, `words.is(1,
  "page")`, the storage word, `number_word(words, 3, 0, 15, &page)` and
  `number_word(words, 4, 0, 0xFFFFFFFF, &offset)` call `catalog_page(core, storage, page,
  offset, reply)`; any other form stays `bad-argument`.
- `core/src/catalog.cpp`, `catalog_page`:
  1. `storage_changes(core)` false: `storage-error`.
  2. `core.rebuild == 1 + storage`: `busy`.
  3. The catalog's state not `ok`: `{"ok":true,"generation":null,"text":"","next":null}`.
  4. `read_at(ctx, kPageNames[storage][page], offset, core.chunk, kFileBufferSize)`; a
     count of 0 or below 0 gives the empty text and `next` `null` with the generation.
  5. Otherwise the reply `{"ok":true,"generation":<g>,"text":"`, then the bytes one by
     one while the escaped byte and the tail of 21 bytes still fit: `\n` as `\n`, `"` and
     `\` after a backslash, another byte below `0x20` or above `0x7E` as `\u00XX`, the rest
     as they are; then `","next":<offset + given>}`.
  No member of `Core` is added, no memory is asked, the stack holds a few words.
- `core/src/catalog.h` declares it with its comment; `docs/commands.md` describes it in
  the catalog section with an example; `docs/core.md` adds it to the host rules (`read`
  and `catalog page` read from a given offset) and to the catalogs.
- `odrigctl/cli.py`: `catalog` takes `page internal|external PAGE OFFSET`; the tool prints
  the reply as for every command. `docs/emulator.md`'s command tool section names it.

## The default preview catalog

- `thumbnails/` holds `catalog.js` and the GIFs; the first commit of the folder, in the
  task of the hosts, holds the previews of `test-animations/` and of the valid vectors,
  made by the subcommand; the task of the sources adds the rest with runs of the
  subcommand, one per source, the card copies with `--card`.
- A converter test reads the folder: `catalog.js` parses, every key's GIF is there, every
  GIF has its key, every GIF's name is `<key>.gif`, the file holds nothing else, every
  name is a name and no path of the computer (no leading `/`, no `:`, no `..`, no
  `/Users/`, `/Volumes/`, `CloudStorage`), and the GIFs of the tracked sources are what
  `make` gives for them. `library.test.js`'s media rule becomes: the tracked GIF, MP4 and
  MOV files are exactly `thumbnails/*.gif`.
- `firmware/fwtool`, `pack` and `odrig/catalog.py` read named folders only; a test of the
  firmware tool and one of `pack` confirm that nothing under `thumbnails/` reaches an
  image or a show.

## The hosts of the app

- `emulator/httpd.py`: `THUMBNAILS` is the repository's `thumbnails/`, served under
  `APP_PATH + "thumbnails/"`; `CONTENT_TYPES` gains `.gif: image/gif` for that folder
  only, so that the page's own files and the app's are as before. The table is made at
  start as today.
- `app/apptool/webserver.py`: `file_of_the_app` serves `/thumbnails/` from the folder with
  the types and `.gif`. `app/apptool/paths.py` names the folder.
- `app/apptool/stage.py`: `staged` copies `thumbnails/` beside the web code; the APK suite
  pins it byte for byte; `test_tool.py`'s staging test does too.
- `tests/app/test_scope.py` lets a script import `thumbnails/catalog.js` and no other file
  of that folder; `tests/emulator/test_page_files.py` pins the served table with the
  folder.

## The app reads the pages

`app/www/client.js` keeps what the previews need in `state.keys`, and does the reading
inside its queue:

- `state.catalog`: the newest reply of `catalog`, or null. `state.catalogNone`: whether
  the target answered `catalog` with `unknown-command` or `bad-argument`.
  `state.pagesRefused`: whether it answered a `catalog page` with `bad-argument`.
- `catalogDue` is set by `heard()` when the link becomes `answers` (the first answer and
  every answer after a silence, which also drops the keys), after a complete list, and
  never while `catalogNone`, or while `pagesRefused` (then Settings alone asks).
  `due()` gives `askCatalog` after `space`, then `askPage` while a read is under way.
- `noteCatalog(reply)`, called for every `catalog` reply, Settings' included: a storage
  not `ok` drops its keys and any read of it; a storage `ok` whose `{generation, entries}`
  differ from those of its keys, and that no read is under way for, starts a read
  `{storage, generation, entries, page: 0, offset: 0, tail: "", keys: new Map()}`.
  Internal is read before external.
- `askPage` sends `catalog page <storage> <page> <offset>`: text added to the tail, whole
  lines parsed (`/^([0-9a-f]{8}) ([0-9]+) [0-9]+ [0-9]+ [0-9]+ [a-z]+ (.+)$/`) into
  `keys.set(name, crc + "-" + bytes)`, the rest kept as the tail; `next` null moves to the
  next page with an empty tail; after page 15 the read's keys replace the storage's and
  `state.keysVersion` grows. A generation other than the read's starts it again; `null`
  ends it without keys; `busy` asks the same page again after 2,000 ms; `bad-argument`
  sets `pagesRefused` and drops every read; any other refusal ends the read without keys;
  a failure leaves it for the next answer.
- `begin()` clears all of it.
- `keyOf(animation)`: the key of the animation's storage and file when its size is the
  animation's `bytes`, else null.
- `catalogs.js` reads `state.catalogNone` instead of its own flag, sends nothing while it
  is set, and hands its replies to `client.noteCatalog`.
- `docs/android-app.md`'s table: the `catalog` row's occasions and the new row "Nothing:
  after the catalogs changed, page by page" `catalog page <storage> <page> <offset>`:
  thirty-five lines; `tests/app/test_docs.py` follows.

## The app shows them

- `app/www/previews.js`: imports `defaults` from `./thumbnails/catalog.js`, keeps the
  phone's own previews (below), and gives `sourceOf(key)`: `thumbnails/<gif>` for a key of
  the default catalog, the object URL of a phone preview, or null.
- `app/www/screens/show.js`: `row()` puts `span.thumb` (`aria-hidden`) first inside the
  Play button; `rowsState` sets each row's square from `previews.sourceOf(client.keyOf
  (animation))`, a faulty row none, creating, changing or removing the `img` only when its
  source differs, so that no row is redrawn. The image is `alt=""`, `draggable=false`,
  `decoding="async"`.
- The now-playing panel: `#now` holds `span.thumb#now-thumb` and `span#now-text`;
  `now()` gives the text, and the square shows the source of the animation on the LEDs
  when `status.animation` is not null, no test shows, and the list holds it; else it is
  hidden.
- `app/www/style.css`: `.thumb` 44 by 44 px, a dark fill, the image `width:100%;
  height:100%; object-fit:contain; image-rendering:pixelated`; the Play button a flex
  row of the square and a column of the name, the meta and, in selection mode, the note,
  which moves from beside the button to under the name inside it.

## The phone's own previews

- `app/www/convert.js` gains `previewMaker(bytes)`, the library's `thumbnail.maker`, so
  that it stays the one script that imports the library.
- `app/www/previews.js`:
  - `start()`: opens IndexedDB `odrig-previews`, store `previews`, keys of the form of the
    key, values `Blob`s of `image/gif`; deletes each key the default catalog has; makes an
    object URL for each other one. Any failure leaves an in-memory map and says nothing.
  - `makeOwn(bytes)`: the key from `crc32.js` and the length; when the key is in neither
    catalog, runs `previewMaker` one step per `setTimeout(0)`, then keeps the GIF in the
    map and writes it to the store, and tells its watchers, which redraw. A refusal keeps
    nothing.
- `app/www/screens/storage.js` and `app/www/screens/author.js` call `previews.makeOwn`
  with the bytes they sent after the upload ended with success and its message is shown.
- `main.js` starts `previews` before the screens.

## Pages and records

- `docs/decisions.md`: the GIF's second role in the table of formats and a change-log
  entry for `catalog page`, `thumbnails/` and the phone's previews.
- `docs/drifts.md`, at its end, under "Seed 44": the tracked previews as the media the
  repository holds besides its images; the sample times and the delay's rounding; the
  GIF's fixed layout; the reader's two parts; the order of the pages read; `--catalog`
  making its folder; the square's update without a redraw.
- `agent/vocabulary.md`: "preview" in the converter's entry and a term of its own;
  `agent/animation-guide.md`: the row of the preview in the table of where things go.
- `AGENTS.md`: seed 44's line in "What is coming".
