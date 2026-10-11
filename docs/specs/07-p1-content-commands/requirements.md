# Requirements: Content commands (seed 07)

Source seed: `project-seeds/07-p1-content-commands/seed.md`. It depends on seeds 02, 03 and
04, which hold the core with its command front-end, the emulator, the command tool
`odrigctl` and the firmware, and on seed 05, which changes the same code first. Seed 05 is
being implemented while this spec is written: these requirements rely on the repository as
seed 05 leaves it, and take the design of seed 05,
`docs/specs/05-p0-canvas-60-by-60/design.md`, as the description of that state. Where the
code then differs from that design, the code is what counts.

`docs/commands.md` and `docs/show.md` define the commands and the show. This seed changes
both, and `docs/core.md`, `docs/emulator.md`, `docs/firmware.md` and `docs/reasons.md` with
them. Where the seed leaves a point open, the answer used here is recorded in
`docs/drifts.md` under "Seed 07"; several of those answers add to what the owner approved
and are marked there as working assumptions.

Terms:

- **the core**, **host**, **the test host**: as in the seed 02 requirements.
- **the emulator**, **the command tool**: as in the seed 03 requirements.
- **the board**, **the firmware**, **the usermod**, **the probe build**, **the tool**,
  **storage**: as in the seed 04 requirements.
- **the folder**: the installed file set as a host holds it: the folder the emulator was
  started on, and `/odrig` in the board's storage.
- **item**, **animation item**, **cycle**, **id**: as in `docs/show.md`.
- **position**: the place of an item in `items` of `show.json`, counted from 0.
- **content command**: `space`, `list`, `remove` and the four `upload` commands.
- **an upload**: what `upload begin` opens and `upload end`, `upload cancel`, a failure or
  60 seconds without progress close. At most one is open.
- **the check**: the decoding of an uploaded file from its first frame record to its last,
  by the rules of `docs/format.md`, against the canvas of the mapping.
- **a change**: a `remove` or an `upload end` that succeeded.
- **power cut**: the host stops between two of its storage operations, or inside one, and
  the core starts again on what storage then holds.
- **C**: the most data bytes one `upload data` line may carry: 1,500.
- **refresh**: as in `docs/core.md`: the LED data the core produces at a grid time.

## Requirement 1: Longer lines and longer replies

**User Story:** As the developer of a client, I want a command line that can carry a piece
of a file and a reply that can carry a list, so that content can travel over the routes
that carry commands.

### Acceptance Criteria

1. A command line SHALL be at most 2,048 characters, not counting one newline at its end
   and one carriage return before it. A longer line SHALL be answered with `line-too-long`
   and SHALL change nothing.
2. A reply SHALL be one JSON object on one line of at most 1,024 bytes with its newline.
3. `ODRIG_LINE_MAX` SHALL be 2,048 and `ODRIG_REPLY_MAX` 1,024 in
   `core/include/odrig_core.h`.
4. `odrig_core_feed` SHALL keep an unfinished line of up to 2,048 characters and a
   carriage return from one call to the next, SHALL keep of a longer line no more than it
   needs to tell that it is too long, and SHALL hand the host each line as the command
   entry read it, cut to 2,048 characters when it is longer.
5. Over HTTP a body of up to 4,096 bytes SHALL reach the core as it is, on the emulator
   and on the board. Of a longer body the first 4,096 bytes SHALL be passed on, which the
   core answers with `line-too-long`.
6. `play`, `on`, `off`, `brightness` and `status` SHALL keep their replies, byte for byte.

## Requirement 2: `space`

**User Story:** As an operator, I want to see how much room is left before I add an
animation.

### Acceptance Criteria

1. `space` SHALL reply `{"ok":true,"free":F,"total":T,"animations":N}`: F and T the free
   and the total bytes of the storage the folder is in, as the host reports them, and N the
   number of animation items of the show.
2. WHILE the show is invalid N SHALL be 0, and F and T SHALL still be reported.
3. `space` with any argument SHALL be `bad-argument`.
4. IF the host cannot tell the space THEN the reply SHALL be `storage-error`.
5. `space` SHALL change nothing and SHALL not disturb playback or an open upload.

## Requirement 3: `list`

**User Story:** As an operator, I want to see what is installed, with the size of every
animation.

### Acceptance Criteria

1. `list` and `list <from>` SHALL reply `{"ok":true,"items":[...],"next":X}`, with the
   items in the order of `show.json`, beginning at the position `from`, which is 0 when it
   is left out.
2. An animation item SHALL be listed as `{"id":<id>,"file":"<name>","bytes":<size>}`,
   with the size of its file in bytes, and a cycle as
   `{"id":<id>,"cycle":[<id>,...],"seconds":<seconds>}`, with the ids of its animations in
   the order of the show.
3. The reply SHALL hold every item from `from` on that fits into 1,024 bytes, in order
   and without a gap. `next` SHALL be the position of the first item left out, or `null`
   when the last item is in the reply.
4. `from` SHALL be decimal digits with a value from 0 to 65,535, else `bad-argument`. A
   `from` at or beyond the number of items SHALL give `"items":[]` and `"next":null`.
5. A show without items SHALL give `{"ok":true,"items":[],"next":null}`.
6. WHILE the show is invalid `list` SHALL be answered with `show-invalid`.
7. A cycle whose entry does not fit into a reply by itself SHALL be listed with an empty
   list, `"cycle":[]`, which no valid show has.
8. Going through a show with `list`, `list <next>` and so on until `next` is `null` SHALL
   give every item exactly once, for a show of 132 items with file names of 32 characters.
9. `list` SHALL change nothing and SHALL not disturb playback or an open upload.

## Requirement 4: `remove`

**User Story:** As an operator, I want to delete an animation from the installation while
it runs.

### Acceptance Criteria

1. `remove <id>` SHALL remove the item with that id from the show and reply `{"ok":true}`.
   The items after it SHALL move up by one position.
2. `<id>` SHALL be decimal digits with a value from 1 to 65,535, else `bad-argument`.
3. WHILE the show is invalid the reply SHALL be `show-invalid`; WHILE an upload is open,
   `busy`; for an id no item has, `unknown-id`; for an animation item that a cycle lists,
   `in-use`. In each case nothing SHALL change.
4. WHEN the item is the `start` item THEN the show SHALL have no `start` afterwards.
5. WHEN the item is the one being played THEN playback SHALL stop: `status` reports
   `"playing":null` and `"animation":null`, and every LED is dark from the next refresh
   on.
6. WHEN another item is being played THEN playback SHALL go on undisturbed: the LED data
   of every refresh SHALL be what it would have been without the command.
7. WHEN the item is an animation item and no remaining item names its file THEN the file
   SHALL be deleted. WHEN another item names it THEN the file SHALL stay.
8. A cycle MAY be removed whether or not it plays; its animations stay.
9. The last item of a show MAY be removed. The show then has no items and is valid.
10. IF storage cannot be written THEN the reply SHALL be `storage-error` and the show
    SHALL be as it was, in memory and in storage.

## Requirement 5: `upload begin`

**User Story:** As an operator, I want to start sending an animation and be told at once
when it cannot be taken.

### Acceptance Criteria

1. `upload begin <id> <file> <bytes>` SHALL open an upload and reply
   `{"ok":true,"chunk":1500}`.
2. `<id>` SHALL be decimal digits with a value from 1 to 65,535; `<file>` a name under the
   naming rule of `docs/show.md`; `<bytes>` decimal digits with a value from 1 to
   4,294,967,295. Anything else, and another number of words, SHALL be `bad-argument`.
3. The id SHALL be one no item has, for a new item, or the id of an animation item, which
   the upload will replace.
4. The command SHALL be refused, with nothing changed: with `show-invalid` while the show
   is invalid; with `busy` while an upload is open; with `in-use` when the id belongs to a
   cycle, and when another item than the one with this id names `<file>`; with `no-space`
   when the file would not fit, and when the id is new and the show has no room for
   another item; with `storage-error` when the host cannot begin the file.
5. The file would not fit when `bytes + bytes div 256 + 16,384` is above the free bytes
   the host reports.
6. An upload SHALL belong to the core and not to a route: its commands MAY arrive over
   serial and over HTTP in any mixture.
7. Opening an upload SHALL NOT change the show, and SHALL NOT disturb playback.

## Requirement 6: `upload data`

**User Story:** As the developer of a client, I want every piece acknowledged with the
number of bytes received, so that I can show progress and speed and notice a lost piece.

### Acceptance Criteria

1. `upload data <offset> <base64>` SHALL add the bytes to the open upload and reply
   `{"ok":true,"received":R}`, R being the number of bytes received so far.
2. `<base64>` SHALL be base64 with the alphabet `A`-`Z`, `a`-`z`, `0`-`9`, `-` and `_`,
   without padding and without any other character, with the unused bits of its last
   character zero, and SHALL stand for 1 to 1,500 bytes. `<offset>` SHALL be decimal
   digits with a value up to 4,294,967,295. Anything else SHALL be `bad-argument`.
3. WHILE no upload is open the reply SHALL be `no-upload`.
4. IF the offset is not the number of bytes received so far, or the bytes would pass the
   size given to `upload begin`, THEN the reply SHALL be `bad-offset`, the bytes SHALL NOT
   be taken, and the upload SHALL stay open as it was.
5. IF the host cannot write the bytes THEN the reply SHALL be `storage-error` and the
   upload SHALL be discarded.
6. Playback SHALL go on while data arrives: no `upload data` SHALL keep the core from
   producing the refresh of a grid time for longer than the host's write takes.
7. The bytes SHALL be written to a temporary file of the folder. No file the show names
   SHALL change before `upload end` succeeds.

## Requirement 7: `upload end`

**User Story:** As an operator, I want the installation to take a new animation only when
it arrived whole and can be played.

### Acceptance Criteria

1. `upload end <crc32>` SHALL close the upload. `<crc32>` SHALL be exactly eight
   hexadecimal digits, `0`-`9` and `a`-`f`: the CRC-32 of the whole file. Anything else
   SHALL be `bad-argument`.
2. The CRC-32 SHALL be the one of zlib, PNG and Ethernet: the polynomial `0xEDB88320` in
   its reflected form, a start value of all ones, and the final value inverted. The CRC-32
   of the nine bytes `123456789` is `cbf43926`.
3. WHILE no upload is open the reply SHALL be `no-upload`.
4. IF fewer bytes were received than `upload begin` named THEN the reply SHALL be
   `incomplete` and the upload SHALL stay open.
5. IF the CRC-32 of the bytes received differs THEN the reply SHALL be `bad-checksum` and
   the upload SHALL be discarded.
6. WHILE the check has not ended the reply SHALL be `busy` and the upload SHALL stay
   open: the client sends `upload end` again.
7. IF the check found the file invalid THEN the reply SHALL be
   `{"ok":false,"error":"bad-file","reason":"<reason>"}` and the upload SHALL be
   discarded. `<reason>` SHALL be the reason of `docs/reasons.md`, "ODRG files", that the
   reference decoder gives for the file, or `size-mismatch` when the file's canvas is not
   the mapping's. The header is judged first, then the size, then the body.
8. IF the bytes read back from storage do not have the CRC-32 of the bytes received, or
   storage cannot be read or written, THEN the reply SHALL be `storage-error`, the upload
   SHALL be discarded, and the show SHALL be as it was, in memory and in storage.
9. On success the reply SHALL be `{"ok":true}`, the file SHALL be in the folder under its
   name, and the show SHALL have the item: a new item at the end of `items`, or the item
   with that id naming this file, at the position it had.
10. WHEN an item was replaced and no remaining item names its old file THEN that file
    SHALL be deleted.

## Requirement 8: `upload cancel`, and an upload that goes quiet

**User Story:** As an operator, I want an upload that was given up to leave nothing behind
and block nobody.

### Acceptance Criteria

1. `upload cancel` SHALL discard the open upload, at any moment between `upload begin` and
   a successful `upload end`, the check included, and reply `{"ok":true}`. WHILE no upload
   is open it SHALL reply `no-upload`.
2. An upload SHALL be discarded when 60,000 milliseconds have passed without progress,
   counted with the timestamps the host supplies. Progress is: `upload begin`, an
   `upload data` that was taken, and a step of the check.
3. The core SHALL judge the 60,000 milliseconds at every call that carries a timestamp. It
   SHALL read no clock of its own.
4. WHEN the show becomes invalid THEN an open upload SHALL be discarded.
5. Discarding SHALL delete the temporary file, SHALL leave the show as it was, and SHALL
   let the next `upload begin` succeed.
6. Any other word after `upload` than `begin`, `data`, `end` and `cancel`, and `upload`
   alone, SHALL be `bad-argument`.

## Requirement 9: Error codes and their order

**User Story:** As the developer of a client, I want one fixed code for every refusal, and
to know which one I get when several apply.

### Acceptance Criteria

1. The error codes SHALL be the five of today, `unknown-command`, `bad-argument`,
   `unknown-id`, `show-invalid` and `line-too-long`, and `no-upload`, `incomplete`,
   `bad-checksum`, `busy`, `in-use`, `no-space`, `bad-offset`, `bad-file` and
   `storage-error`.
2. A line that is refused SHALL be answered with the first code that applies in this
   order: `line-too-long`, `unknown-command`, `bad-argument`, `show-invalid`, `no-upload`,
   `incomplete`, `bad-checksum`, `busy`, `unknown-id`, `in-use`, `no-space`, `bad-offset`,
   `bad-file`, `storage-error`.
3. A reply with `"ok":false` SHALL be `{"ok":false,"error":"<code>"}`, and for `bad-file`
   it SHALL have the one further member `reason`.
4. `show-invalid` SHALL answer `play`, `list`, `remove` and every `upload` command while
   the show is invalid. `space`, `on`, `off`, `brightness` and `status` SHALL work as
   ever.
5. `unknown-id` SHALL answer `play` and `remove`. `upload begin` with an id no item has
   opens an upload for a new item.
6. Every reply SHALL be made of printable ASCII, with its members in the order shown and
   no space.

## Requirement 10: A change takes effect at once, and playback goes on

**User Story:** As an operator, I want to play a new animation the moment it is installed,
and I want the installation to keep running while I work on it.

### Acceptance Criteria

1. After a change, `list`, `space`, `play` and `status` SHALL see the show as it is now,
   with no restart.
2. A new item SHALL be playable with `play <id>` as soon as `upload end` has replied
   `{"ok":true}`.
3. WHEN the file of the animation item that is being played is replaced, or of an
   animation that the cycle being played lists, THEN the item being played SHALL start
   again from its first frame at the next refresh, with the new file.
4. In every other case a change SHALL leave playback undisturbed: the LED data of every
   refresh SHALL be what it would have been without it.
5. Brightness, on and off, and what plays SHALL NOT be changed by a content command, apart
   from criterion 3 and Requirement 4 criterion 5.
6. The check SHALL run in steps of one frame record: one step after a refresh was
   produced, and none after a refresh before which a grid time was skipped. No call to
   the core SHALL decode more than one frame record of the uploaded file.
7. While an upload is open the core SHALL go on producing a refresh at every grid time at
   which it is asked.

## Requirement 11: A change survives a restart and a power cut

**User Story:** As the owner, I want the installation to come back after a power cut with
a show that is whole: the one from before the command or the one after it.

### Acceptance Criteria

1. A change SHALL be kept across a restart: the core, started again on the folder, SHALL
   have the show as the change left it.
2. After a power cut at any moment the folder SHALL hold a valid show: either the show
   from before the command with every file it names as it was, or the show after it with
   every file it names whole. It SHALL never hold a mixture.
3. New content SHALL be written to a temporary file and put in place by renaming.
   `show.json` SHALL never be written in place.
4. At its start the core SHALL remove what an interrupted command left: the temporary
   files, and a file that no item names and that the interrupted command made or was
   about to delete.
5. A folder that holds no trace of an interrupted command SHALL be started as today: the
   core then deletes and writes nothing.
6. Brightness, on and off, and what plays SHALL NOT be kept across a restart, as before:
   a restart begins with the brightness and the `start` item of `show.json`.
7. The names `upload.part`, `show.part` and `pending.txt` in the folder SHALL be the
   core's. No other file SHALL be created.

## Requirement 12: The show file the core writes

**User Story:** As a maintainer, I want to know exactly what `show.json` looks like after
the installation changed it, so that every tool reads it and a test can compare bytes.

### Acceptance Criteria

1. WHEN the core writes `show.json` THEN it SHALL write one line:
   `{"version":1,"brightness":<b>,"items":[<item>,...],"start":<id>}` and a line feed,
   with no space, an animation item as `{"id":<id>,"file":"<name>"}` and a cycle as
   `{"id":<id>,"cycle":[<id>,...],"seconds":<seconds>}`, and without the member `start`
   when the show has none.
2. `<b>` SHALL be the brightness the show file had when the core started, whatever
   `brightness` commands arrived since.
3. The items SHALL keep their order; a new item SHALL be the last.
4. The file SHALL be valid under `docs/show.md`, and the converter and the core SHALL read
   it back as the show the core holds.
5. A show MAY have no item: `"items":[]` SHALL be valid for the core and for every reader
   of show files in the repository. Such a show has no `start`.
6. A removal or an upload SHALL NOT change `mapping.json`.

## Requirement 13: No allocation after startup, and the limits that follow

**User Story:** As the owner, I want the installation to run for days with the memory it
took at power-on, so that changing the show cannot exhaust the board.

### Acceptance Criteria

1. The core SHALL ask the host for memory only inside `odrig_core_begin`, as before. No
   content command, no upload and no check SHALL allocate.
2. The tables of items and of files SHALL be made at startup with room for 32 items more
   than `show.json` lists then, and for at least 128 items.
3. WHEN the tables are full THEN `upload begin` with a new id SHALL be refused with
   `no-space`. Replacing and removing SHALL still work, and a removal makes room.
4. For the canvas of `mapping/legs-20.json` with a show of 100 items, 80 animations with a
   file each and 20 cycles of 10 entries, the memory the core asks for SHALL be under
   131,072 bytes. The suite SHALL measure it and `docs/core.md` SHALL state it.
5. The core object SHALL stay at most 4,096 bytes, and no function of the core SHALL have
   a local array above 256 bytes.
6. A host without storage functions SHALL get none of the blocks that only uploads need.
7. IF the host cannot supply a block THEN the show SHALL be invalid with `out-of-memory`,
   as before.

## Requirement 14: The host interface

**User Story:** As the writer of a host, I want the smallest set of functions that lets
the core change the folder, with rules I can meet on a flash file system.

### Acceptance Criteria

1. `odrig_host` SHALL gain exactly these members, after `log`, with the signatures of the
   design: `write_open`, `write`, `write_close`, `rename`, `remove`, `space` and
   `read_at`.
2. The core SHALL have at most one file being written at a time, SHALL give `write` at
   most 1,500 bytes in one call, and SHALL give `read_at` a capacity of at most 512.
3. The core SHALL use only names made of `a`-`z`, `0`-`9`, `-`, `_` and `.` of 1 to 32
   characters: `mapping.json`, `show.json`, the `.odrg` names of the show and of
   uploads, `upload.part`, `show.part` and `pending.txt`.
4. A host SHALL keep these promises: after `write_close` returned 1 the file is whole in
   storage; after `rename` returned 1 the new name holds the file, and after a power cut
   during it the new name holds its old file or the new one, whole; `remove` of a name
   that is being written gives the writing up.
5. A host MAY set `write_open` to `NULL`: it then has no storage that can be changed. The
   core SHALL then answer `remove` and `upload begin` with `storage-error`, SHALL delete
   nothing at its start, and SHALL call none of the seven functions but `space`.
6. The core SHALL call the seven functions only inside `odrig_core_begin`,
   `odrig_core_command`, `odrig_core_feed` and `odrig_core_poll`, never from inside
   another host function.
7. `open`, `read`, `close`, `alloc` and `log` SHALL keep their signatures and their
   rules. The functions the core offers SHALL keep their signatures.

## Requirement 15: Every route, on both hosts

**User Story:** As the owner, I want these commands to be the same over USB and over
Wi-Fi, on the board and in the emulator.

### Acceptance Criteria

1. The content commands SHALL be read and answered in the core's command front-end and
   nowhere else. No transport and no host SHALL look into a line.
2. The same lines given to the core over serial and over HTTP, on the emulator and on the
   board, with the same folder and the same space, SHALL get the same replies.
3. Given the same files, the same host answers and the same calls with the same
   timestamps, the core SHALL give the same replies, the same LED data and the same
   storage operations in the same order.

## Requirement 16: The emulator

**User Story:** As a developer, I want to try uploads and removals against the emulator
before the board is touched.

### Acceptance Criteria

1. The emulator SHALL apply the content commands to the folder it was started on: files
   are written, renamed and deleted there, and nowhere else.
2. The emulator SHALL report as total space 10,354,688 bytes, the size of the board's
   storage, or the number given with `--storage BYTES`, and as free space the total less
   the sizes of the files of the folder, each rounded up to 4,096 bytes, and not below 0.
3. `--storage` SHALL take a whole number from 0 to 4,294,967,295; anything else is a usage
   error. Record mode SHALL take it too.
4. A file name SHALL be used only when it is one the core may use; the emulator SHALL
   refuse a name with a path separator.
5. The page's command log SHALL show a long line by its first 200 characters and the
   number of characters it has. A `log` event SHALL carry `length` for it.
6. In record mode the content commands of a script SHALL act on the folder as in real
   time, and the recording SHALL be the same on every run from the same folder.
7. A change made through the emulator SHALL be there when the emulator is started again
   on the same folder.

## Requirement 17: The firmware

**User Story:** As an operator at the event, I want to add an animation over the board's
network while the LEDs keep showing the show.

### Acceptance Criteria

1. The usermod SHALL supply the seven storage functions on the folder `/odrig` of WLED's
   file system. It SHALL write, rename and delete no file outside that folder.
2. The usermod SHALL give the core's writes to the file system as they come, one write of
   at most 1,500 bytes for each `upload data`, and SHALL time every storage operation.
3. After a storage operation that took d the usermod SHALL hand the core no further
   command line, from the port or from the web server, before `2 * d` have passed, and at
   least 20 ms. It SHALL do this without looking into a line.
4. While an upload runs, `status` SHALL report 25 or more refreshes in every full second,
   on the board with the bench show playing. After the upload it SHALL report 49 or more.
5. The probe build SHALL report, for the storage operations since the last report, their
   number, the longest and the sum of their times, and the same for the steps of the
   check.
6. `POST /odrig` SHALL take a body of up to 4,096 bytes and give back a reply of up to
   1,024 bytes. The port SHALL take a line of 2,048 characters sent in one piece.
7. IF 25 refreshes a second cannot be held with criteria 2 and 3 THEN the writes SHALL
   move to a task of their own, designed from what was measured, and the finding SHALL be
   recorded in `docs/drifts.md`.
8. `install-show` and `read-show` of the tool SHALL keep working: a folder read back after
   an upload holds the uploaded file with its bytes.
9. Every show a test puts on the board SHALL have a brightness of 40 or less.

## Requirement 18: The command tool

**User Story:** As a maintainer at a laptop, I want to see, remove and upload content with
the tool I already use for commands.

### Acceptance Criteria

1. `odrigctl` SHALL gain the commands `space`, `list`, `remove ID` and `upload ID FILE`,
   over `--port` and over `--http`.
2. `space` and `remove ID` SHALL send one line and print the reply, as the commands of
   today.
3. `list` SHALL send `list`, print the reply, and for as long as `next` is not `null`
   send `list <next>` and print that reply. It SHALL stop at a reply that is not ok.
4. `upload ID FILE` SHALL read the file, send `upload begin ID <name> <bytes>` with the
   last part of the file's path as the name, send the file in pieces of the size the reply
   names, each as one `upload data` line, and send `upload end` with the file's CRC-32.
   WHILE the reply to `upload end` is `busy` it SHALL wait and send it again, for at most
   600 seconds.
5. During an upload the tool SHALL write to standard error the percentage sent, the bytes
   sent and the total, and the speed in bytes a second: at least once a second, and a last
   time when the data is sent.
6. The tool SHALL print the last reply it received to standard output and SHALL exit with
   status 0 only when that is the `{"ok":true}` of `upload end`.
7. WHEN a reply is not ok THEN the tool SHALL print it, SHALL send `upload cancel` when an
   upload it opened may still be open, and SHALL exit with status 1.
8. WHEN no reply to an `upload data` arrives in time THEN the tool SHALL send the same
   line once more. A `bad-offset` for that second line means the first one was taken, and
   the tool goes on.
9. IF the file cannot be read THEN the tool SHALL write `error: not-found: <detail>` to
   standard error and exit with status 2, having sent nothing. Status 3 SHALL remain the
   target that cannot be reached or does not answer.
10. Through the port the tool SHALL keep the port open for the whole upload.
11. The tool SHALL judge nothing itself: the id, the name and the file go out as given.

## Requirement 19: Tests

**User Story:** As a maintainer, I want every command, every code and every moment a
power cut can fall on covered without the board, and the board tested for what only it
can show.

### Acceptance Criteria

1. The suite of the core SHALL cover: every content command; every error code, each
   through every command that can give it; the order of Requirement 9 for lines to which
   two codes apply; an upload broken off after each of its steps, by `upload cancel`, by
   60 seconds and by a restart; and a power cut at each storage operation of each kind of
   change, and inside a write.
2. For each power cut the suite SHALL start the core again on the folder as the cut left
   it and SHALL find Requirement 11 criterion 2 met and nothing left of the names of
   criterion 7.
3. The reference player of `tests/core/support.py` SHALL be given the content commands,
   and the replies and the LED data of the core SHALL be compared with it for sessions
   that mix playback with removals and uploads.
4. The test host SHALL stop when the core allocates after startup, asks `write` for more
   than 1,500 bytes, has two files being written, or gives a host function a name outside
   Requirement 14 criterion 3.
5. The suite of the emulator SHALL have the command tool upload an animation over serial
   and over HTTP, find it in `list`, play it, find it after the emulator was started
   again, and remove it.
6. Tests that need the board SHALL be in `tests/board/` and those for a joined network in
   `tests/air/`, apart from the four suites that need neither.
7. The board suite SHALL run the session of criterion 5 over USB, restart the board in
   it, and measure Requirement 17 criterion 4 and the speed of the upload.
8. Each suite SHALL be selected by discovery.

## Requirement 20: Documents

**User Story:** As the developer of the operators' app, I want the commands written down
exactly, so that I can write a client from the documents alone.

### Acceptance Criteria

1. `docs/commands.md` SHALL have the text the design gives under "The text of
   docs/commands.md": the limits, the four commands with every reply member, the base64
   form, the CRC-32, every error code with its condition, and their order.
2. `docs/show.md` SHALL have the texts the design gives under "The text of docs/show.md":
   that a show may have no items, how a running show is changed, what the core writes,
   the ids of uploaded items, and the files of the folder that are the core's.
3. `docs/core.md` SHALL describe the seven new host functions, the limits, the blocks of
   memory with the measured figures, the check and its steps, and the options of the test
   host.
4. `docs/emulator.md` SHALL describe `--storage`, the `length` of a `log` event, and the
   four new commands of the command tool with an example each and the exit statuses.
5. `docs/firmware.md` SHALL describe what the firmware writes and where, the pacing, the
   new members of the probe build's report, the measurements, and the owner's check.
6. `docs/reasons.md` SHALL no longer list a show without items as malformed.
7. `docs/decisions.md` SHALL list the commands as they are, with a line in its change
   log.
8. The documents and the code SHALL change in the same commits.

## Requirement 21: Accepted on the board

**User Story:** As the owner, I want every item of the seed's definition of done checked
on the board, and to know which a person checked.

### Acceptance Criteria

1. On the board over USB the command tool SHALL upload an animation, `list` SHALL show
   it, `play` SHALL play it, it SHALL be there after a restart of the board, and `remove`
   SHALL remove it.
2. The speed of that upload SHALL be measured and written into `docs/firmware.md`.
3. `status` during the upload SHALL report 25 or more refreshes a second, and 49 or more
   afterwards.
4. The board suite SHALL leave the board with the firmware and the bench show at a
   brightness of 40 or less, with no file of a test in `/odrig`.
5. Owner's check: with a phone or a computer joined to the board's network, an animation
   SHALL be uploaded over HTTP, listed, played and removed.
6. The seed SHALL be completed only when the owner's check is done.
