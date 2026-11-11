# Design

## The library

- `inflate.js`: `inflateStream()` decodes the same blocks as `inflateRaw` one unit at a time:
  a block's header and codes, a literal, a length with its distance, an end of block, or a
  part of a stored block. A unit that runs out of input is undone and read again when more
  comes; once the end is told it is `truncated`, at the same bit as `inflateRaw`. The output
  goes into a ring of 131,072 bytes, of which the 32,768 behind are the window, and `pull`
  gives at most 65,536 bytes at a time.
- `odrg.js`: `records(head, source)` is the palette and `next()` of `reader`, reading from a
  source `{take(count, what), rest()}`; `reader` gives it the inflated body as before and
  keeps `loopMs`.
- `thumbnail.js`: `maker(data)` reads the header in its first step; a container of a text or
  a clock is decoded as before; frames are read in a first pass of at most 1 MiB a step,
  which takes the stream's verdicts, the bytes after it and a palette cut short, and sums
  the durations of the records whose bytes all came; then in a second pass of at most 256
  records and 1 MiB a step through `odrg.records` over a fresh stream, taking from it only
  what a record needs. After the last record a container's payload size and loop are
  checked. `held()` gives the stream's held bytes.

## The app

- `previews.js`:
  - `making(bytes)`: a queue of one preview at a time; `makeOwn` gives a handle `{key,
    done, wait()}`, and a preview made goes into `own` for the run at once; `keep(key)`
    writes it to the store when an upload of its key succeeds, at once if it is made, else
    when it is; `drop(handle)` stops a making nobody waits for.
  - Database version 3; the upgrade creates `previews`, `keys` and `uploads` when missing.
  - `uploaded(address, storage, name, key)` keeps a place, in `uploads` and for the run;
    `placed(address, storage, name)` gives its key; `forget(address, storage, names,
    level)` drops the places of a level a complete list did not name; `removed(...)` drops
    one.
- `client.js`: `keyOf(animation)` first; then the kept place for the target's address, the
  row's storage and its `file`, taken when the key's size is `bytes`; the read keys of a name
  just uploaded are left out until a page read after the upload names it. A complete list
  asked from its first part after an upload drops the places it does not name.
- The uploads (single form, text and clock form, the batch's run): the making starts as the
  upload starts; success keeps the key and the place; anything else drops the making.
- `convert.js`: `previewSafe` is true for every file the checks take.
- `storage.js`: the note under a ready-made file's preview names its source.

## Tests

- Converter: `tests/inflatestream.test.js`, the stream against `inflateRaw` in parts of 1, 7
  and 4,096 bytes on built and damaged streams and the vectors' bodies; `truncated` after the
  end; a body of more than 16 MB with at most the window held, its preview that of its
  uncompressed twin; a compressed vector and its twin. The thumbnail test's count of steps
  takes the first pass.
- App: `tests/app/test_phone_previews.py`, against the emulator and a show packed without a
  catalog: a preview in the row with no `catalog page` asked; a target refusing `catalog
  page`; a card's upload before its pages are read; a refused upload writes nothing; a kept
  place after a reload; a complete list without the file drops it; a board key that differs
  decides; a row of another size takes none; a compressed ready-made file gets its preview;
  version 2 to 3.
