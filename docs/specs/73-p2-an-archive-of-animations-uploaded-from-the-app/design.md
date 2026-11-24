# Design

## `app/www/zip.js`

- `readZip(bytes)`: finds the end of the central directory in the last 65,557 bytes, refuses
  a zip64 end locator and counts of `0xFFFF`, and reads at most 512 central entries: `{path,
  method, encrypted, crc, packed, size, offset, unreadable}`. An entry is unreadable when it
  is encrypted (flag bit 0), of a method other than 0 or 8, or zip64 (a size or offset of
  `0xFFFFFFFF`). Folders (names ending in `/`) are left out. It gives `{entries, left,
  tooLarge}`: the entries beyond 512, and whether the unpacked sizes pass 64 MB, after which
  no entry is read.
- `extract(bytes, entry)`: the local header's name and extra lengths, the data, `inflateRaw`
  for method 8, the size and the CRC-32 checked; a reason as an `Error` otherwise.

## `app/www/screens/archive.js`

- The panel `#archive` on Upload: `#archive-file` (`.zip`), `#archive-rows`, `#archive-all`,
  `#archive-none`, `#archive-storage`, `#archive-sum`, `#archive-upload` with
  `#archive-locked-reason`, `#archive-stop`.
- At the pick each animation entry is extracted, checked with `prepareReady` on a `File` of
  its bytes, and its kind (`frames`, `text`, `widget`) and length taken from the container's
  header or the frames' `loopMs`; the bytes are then let go. The rows: `{entry, name, edited,
  ticked, replace, kind, ms, size, reason}`.
- Names: the last part of the path for the board's storage, the path for the card;
  `destinations.pathOf`'s rule for the last part, at most 100 bytes for the path; a row says
  why and has its name field; a name the destination's list has says `A file of this name is
  there.` with a `Replace` checkbox.
- `Upload ticked` is disabled while nothing is ticked, a ticked name cannot be taken, a
  ticked existing name is not allowed to be replaced, the sum does not fit, or the screen's
  lock holds; the line under it says why. The press starts `batch.start` with the ticked
  rows, `read()` extracting and checking a row at its turn.

## `batch.js`

- An item with `replace` skips the collision check of `destinations.validate`, and on the
  board's storage takes the id of the root's item of that name and sends `upload begin <id>
  <file> <bytes>` without a creation guard; on the card it sends no `upload expect`.

## Tests

`tests/app/test_archive.py`, scenario `archive.js`, zips made by the test with `zipfile`:
stored and deflated entries read; an encrypted, a zip64 and a broken entry unreadable; a
text passed over; a file of another canvas refused; a name too long renamed; the sum against
`space`; ten files uploaded to the emulator's storage and to a card, one refused in the
middle; `Replace`; `Stop`; the look rules at 320, 360 and 740 pixels.
