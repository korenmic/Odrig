# Requirements

Seed 79, `project-seeds/79-p1-the-preview-of-an-upload-made-on-the-phone/seed.md`, built on
seed 73's branch so that the batch and the archive's uploads get their previews too. The
converter's library, the app's web code, their tests and documents. No command, reply,
core, firmware or emulator change.

## 1. The preview starts with the upload

1.1 Every upload of the app, of a converted video or GIF, a ready-made file, a text or a
clock, and each file of a batch or an archive, starts making the preview of its exact
bytes as it starts, a step at a time beside the upload; a ready-made file still starts it
when it is picked, now for every file.
1.2 One preview is made at a time, in the order the uploads started; a key the phone or the
default catalog already holds is not made again.
1.3 A preview made is the phone's for this run at once.
1.4 It is written to the phone's own catalog in IndexedDB only when an upload of those bytes
ended with success; a refused, failed or cancelled upload writes nothing, and its making
stops unless another upload of the same bytes waits for it.
1.5 The making of a picked ready-made file stops when the form lets the file go and no
upload of its bytes waits for it.
1.6 A file the maker refuses keeps no preview, and nothing is said.

## 2. The place of an upload

2.1 When an upload ends with success the app keeps, beside the key, its place: the target's
address, the storage, and the file's name as the list names it (on the card its path from
`odrig`).
2.2 That name's key is taken out of the keys of that storage's last read, and of a read
under way, for this run.
2.3 The places are kept in `odrig-previews`, version 3, store `uploads`, a record `<address>
<storage>` of the pairs of each name and its key; a later upload to a name replaces its key.
The upgrade creates only the stores that are missing.
2.4 Without IndexedDB, or when a write is refused, the places hold for the run.

## 3. The order in which a row's preview is found

3.1 The board's key, from the read under way first; its preview from the default catalog,
else the phone's own.
3.2 Else the key kept for the row's place, taken only when its size is the row's `bytes`.
3.3 Else the default catalog by the file's name and size.
3.4 Else none. A key found at 3.1 or 3.2 decides; a row without a known size takes no kept
place. The panel of what plays finds its preview in the same order.

## 4. A ready-made file of any size

4.1 The library gains `inflateStream()`, a raw DEFLATE reader fed in parts, told when the
input ended, giving its output a part at a time with a window of 32,768 bytes, with the
verdicts of `inflateRaw`, `truncated` only after the end, its output before a verdict a
prefix of zlib's, and `held`, the output it holds.
4.2 The preview maker reads the frame records of an ODRG file and of a container of frames
from that stream in two passes: the first judges the whole stream and sums the loop of a
file, the second reads the records; the verdicts and their order stay. `odrg.reader`,
`decode` and every other user keep inflating whole.
4.3 A step reads at most 256 records and 1,048,576 bytes of body; the first step reads the
header only; an uncompressed body is read in place in the same passes.
4.4 `previewSafe` no longer limits previews; the same animation compressed or not gives the
same preview.
4.5 The form of a ready-made file says `Preview from the animation catalog. The original
animation bytes are kept.` under a preview of the default catalog, and `Preview made on this
phone. The original animation bytes are kept.` under one this phone made.

## 5. What a kept place is not

5.1 A place is dropped when a complete list of its level, asked from its first part after
the upload ended, names no file of that storage at that name; when this app deletes the
file; and replaced by a later upload to the name.
5.2 Two boards at one address share their places.

## 6. The documents

6.1 `docs/android-app.md`, `docs/converter.md`, a step of "The check on a phone", a bullet of
"What is open", and `docs/drifts.md` with the measurement.
