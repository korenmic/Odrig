# Design: Content commands (seed 07)

## Overview

Four additions to the command list: `space`, `list`, `remove` and `upload`. They are read
and answered in the core's command front-end, so every route and both hosts get them at
once. For them:

1. **The limits grow**: a line may have 2,048 characters and a reply 1,024 bytes.
2. **The host interface grows** by seven functions: three to write a file, `rename`,
   `remove`, `space`, and `read_at`, which reads a file beside the one that plays.
3. **The core changes its show while it runs.** Its tables are made at startup with room
   to spare. A removal and an upload rewrite `show.json` through a temporary file and a
   rename, in an order that leaves a valid show at every moment, and the start of the core
   removes what an interrupted command left.
4. **An upload** goes into the file `upload.part`. When its last byte has arrived, the
   core decodes the file back from storage, one frame record after each refresh, with a
   second decoder, so that playback goes on. `upload end` puts the file in place when that
   check has passed.
5. **The emulator** gives the core file operations on its folder. **The firmware** gives
   them on `/odrig` of WLED's file system, times every operation, and holds the next
   command line back for twice that time, so that the LEDs keep at least half of every
   second. **The command tool** gains `space`, `list`, `remove` and `upload`.

`docs/commands.md` and `docs/show.md` get the texts printed below.

Decisions taken where the seed left a point open are in `docs/drifts.md` under "Seed 07".
Six of them add to the form the owner approved; they are listed under "What goes beyond
the seed" at the end.

## What this design relies on

The code of seeds 02 to 04 was read for this design, and the design of seed 05 for what
seed 05 changes. A task that finds one of these different follows the code and records
the difference in `docs/drifts.md`.

| Where | What is there |
|---|---|
| `core/include/odrig_core.h` | `odrig_host` with `ctx`, `alloc`, `open`, `read`, `close`, `log`; seven functions; `ODRIG_LINE_MAX` 64 and `ODRIG_REPLY_MAX` 192. Seed 05 changes two comments in it and nothing else. |
| `core/src/core_state.h` | The core object, at most 4,096 bytes by a static assertion. `ItemInfo` (16 bytes), `FileInfo` (48 bytes: the name, `frames`, which nothing reads, and `total_ms`), the entry table of cycle entries, which hold positions of items. The line of the byte entry, 65 bytes, is in the object. |
| `core/src/show.cpp` | `show.json` is read twice: once to check and count, once to fill the tables, which are taken from the host between the two with exactly the counted sizes. A show without items is refused. |
| `core/src/commands.cpp` | `command_answer` splits a line at single spaces and knows a command with at most one argument. `odrig_core_feed` has its reply in a local array of 192 bytes. |
| `core/src/player.cpp` | One stream: the file of the animation on the LEDs stays open between refreshes. `player_poll` produces a refresh at a grid time. `player_play` sets an item playing from the next refresh. |
| `core/src/file_source.h`, `inflate.h`, `odrg_decoder.h` | One `FileSource`, one `Inflate`, one `OdrgDecoder`, in the core object; the decoder and the inflater take their bytes from a `FileSource *`. |
| `core/src/core.cpp` | `check_file` decodes a file whole at startup: the header, the size against the mapping, the body. |
| `core/Makefile` | The core's flags include `-Wframe-larger-than=512`. |
| The core **after seed 05** | The same host interface; `mapping.cpp` reads both kinds of mapping file; the memory for the target file with 100 items is 70,768 bytes in ten blocks. |
| `tests/core/host/host.cpp`, `tests/core/support.py` | The test host with its options and its checks; `ReferencePlayer`, the model the core is compared with. |
| `emulator/host.py`, `binding.py`, `engine.py`, `httpd.py`, `hub.py` | `FolderHost` with `open`, `read`, `close`, `log`; the host record declared for `ctypes`, compared with the header by a test; one lock round every call to the core; a body cut to 128 bytes; a log line cut to 64 characters. |
| `odrigctl/` | One exchange for one command: the port is opened, settled for 0.3 seconds, one line sent, one reply read. Statuses 0, 1, 2 and 3. |
| `firmware/usermod/` | `odrig_files.cpp` opens files of `/odrig` for reading; a test says the usermod never writes a file. `odrig_serial.cpp` takes at most 256 bytes of the port in one pass and feeds them one at a time. `odrig_http.cpp` keeps 128 bytes of a body and has its line and its reply on the stack. One mutex round every call to the core. |
| The firmware **after seed 05** | Twenty outputs; possibly a task of its own that asks the core for refreshes, if the loop did not hold 49 with 3,600 LEDs. |
| `firmware/fwtool/` | `install-show` and `read-show` edit and read the file system as an image over USB, with the board stopped. |

Read in the firmware tool's work folder, in WLED 16.0.1 and in the Arduino core it is
built with:

| # | Fact | Where |
|---|---|---|
| S1 | `WLED_FS` is `LittleFS`, the Arduino library over `esp_littlefs`. | `wled00/wled.h` |
| S2 | The file system is built with a cache of 512 bytes, a write size of 128, blocks worn evenly every 512 cycles, and disk version 2.0. Its blocks are 4,096 bytes. | `sdkconfig.h` of the core for this board; seed 04's storage images |
| S3 | `rename` of the Arduino library requires that the source exists and calls the C library's `rename`. It does not remove the destination first. | `libraries/FS/src/vfs_api.cpp` |
| S4 | `totalBytes()` and `usedBytes()` each ask the file system for its size, which walks its blocks. | `libraries/LittleFS/src/LittleFS.cpp` |
| S5 | The USB serial port puts received bytes into a queue of 256 bytes. When the queue is full, the rest of a packet is dropped. `setRxBufferSize` makes a new queue of another size and may be called after the port was begun. WLED begins the port in its setup. | `cores/esp32/HWCDC.cpp`; `wled00/wled.cpp` |

## The text of docs/commands.md

The whole page after this seed:

~~~~markdown
# Commands

The board and the emulator accept the same commands, handled by the same code. A command
exists only if something really uses it.

## Lines

A command is one line of text ending in a newline; a carriage return before the newline is
ignored. Words are separated by single spaces. A line is at most 2,048 characters.

Every command gets exactly one reply: a JSON object on one line of at most 1,024 bytes.

- Success: `{"ok":true}`, with more members for `status`, `space`, `list` and `upload`.
- Failure: `{"ok":false,"error":"<code>"}`, with one more member for `bad-file`.

## Commands

| Command | Effect |
|---|---|
| `play <id>` | Plays the item with that id from [show.json](show.md), from its first frame. |
| `on` | Switches the LEDs on. |
| `off` | Switches the LEDs off: every LED is dark. Playback time keeps running. |
| `brightness <n>` | Sets brightness, 0 to 255. |
| `status` | Reports the current state. |
| `space` | Reports the free and the total storage and the number of animations. |
| `list`, `list <from>` | Lists the items of the show. |
| `remove <id>` | Removes an item from the show. |
| `upload begin <id> <file> <bytes>` | Opens an upload of an animation. |
| `upload data <offset> <base64>` | Adds a piece of the file to the open upload. |
| `upload end <crc32>` | Closes the upload and installs the animation. |
| `upload cancel` | Discards the open upload. |

At power-on the LEDs are on, brightness is the value in `show.json`, and the `start` item
is playing if there is one. What `play`, `on`, `off` and `brightness` change is not kept
across a restart. What `remove` and `upload` change is: they change the installed show.

Brightness scales every colour value v to `(v * brightness + 127) / 255`, rounded down.

A number in a command is written in decimal digits.

## Status reply

```json
{"ok":true,"on":true,"brightness":128,"playing":3,"animation":1,"fps":50,"error":null}
```

| Member | Meaning |
|---|---|
| `on` | Whether the LEDs are switched on. |
| `brightness` | Current brightness, 0 to 255. |
| `playing` | The id of the item being played, or `null`. |
| `animation` | The id of the animation item on the LEDs right now, or `null`. It differs from `playing` when a cycle is playing. |
| `fps` | LED refreshes in the last full second. |
| `error` | `null`, or the reason the show is invalid. |

## Storage and the installed items

```
space
{"ok":true,"free":8372224,"total":10354688,"animations":2}
```

`free` and `total` are bytes of the storage the show is in. `animations` is the number of
animation items of the show, and 0 while the show is invalid.

```
list
{"ok":true,"items":[{"id":1,"file":"hello.odrg","bytes":1138},{"id":2,"file":"dvd.odrg","bytes":1612},{"id":3,"cycle":[1,2],"seconds":15}],"next":null}
```

The items come in the order of `show.json`, beginning at the position `<from>`, counted
from 0, which is 0 when it is left out. `<from>` is 0 to 65,535. An animation item has its
`id`, its `file` and the size of that file in `bytes`. A cycle has its `id`, the ids of its
animations in `cycle`, and its `seconds`. The reply holds as many items as fit into it.
`next` is the position of the first item that was left out, to be asked for with
`list <next>`, or `null` when the last item is in the reply. A position at or after the end
gives no items and `null`, and so does a show without items:
`{"ok":true,"items":[],"next":null}`. While the show is invalid, `list` is refused with
`show-invalid`. A cycle too long to fit into a reply by itself is listed with
`"cycle":[]`.

## Removing an item

```
remove 2
{"ok":true}
```

The item leaves the show, and the items after it move up.

- An animation that a cycle lists is refused with `in-use`: remove the cycle first.
- If the item is the `start` item, the show has no `start` afterwards.
- If the item is playing, playback stops and the LEDs go dark. Anything else that plays
  goes on undisturbed.
- The animation's file is deleted when no remaining item names it.
- While an upload is open, `remove` is refused with `busy`.

## Uploading an animation

An animation is sent as an ODRG file, in pieces, each acknowledged:

```
upload begin 4 clip.odrg 3200
{"ok":true,"chunk":1500}
upload data 0 T0RSRwEB...
{"ok":true,"received":1500}
upload data 1500 ...
{"ok":true,"received":3000}
upload data 3000 ...
{"ok":true,"received":3200}
upload end 1c291ca3
{"ok":true}
```

**`upload begin <id> <file> <bytes>`** opens an upload. One upload can be open at a time,
whichever route its commands arrive by.

- `<id>` is 1 to 65,535. An id that no item has makes a new item, which becomes the last
  of the show. The id of an animation item replaces that item's animation; the item keeps
  its id and its position. A client that wants a new item chooses any id that `list` does
  not show.
- `<file>` is the name the file gets, under the naming rule of [show.md](show.md).
- `<bytes>` is the size of the file, 1 to 4,294,967,295.
- The reply's `chunk` is the most bytes one `upload data` line may carry.
- It is refused with `busy` when an upload is open; with `in-use` when the id belongs to
  a cycle, or another item already names `<file>`; and with `no-space` when the file
  would not fit into the free storage, or the show has no room for another item.

**`upload data <offset> <base64>`** adds bytes. `<offset>` is the number of bytes sent
before these, and must equal the number received so far; otherwise the reply is
`bad-offset` and the bytes are not taken. `<base64>` is 1 to `chunk` bytes in base64 with
the alphabet `A`-`Z`, `a`-`z`, `0`-`9`, `-` and `_` (RFC 4648, section 5), without `=` at
the end. The reply's `received` is the number of bytes received so far. Bytes beyond the
size given to `upload begin` are refused with `bad-offset`.

**`upload end <crc32>`** closes the upload. `<crc32>` is the CRC-32 of the whole file as
eight hexadecimal digits, `0`-`9` and `a`-`f`: the CRC-32 of zlib and PNG, which for the
nine bytes `123456789` is `cbf43926`.

- `incomplete`: fewer bytes arrived than `upload begin` named. The upload stays open.
- `bad-checksum`: the bytes received have another CRC-32. The upload is discarded.
- `busy`: the file is still being checked. The upload stays open; send `upload end`
  again. The check decodes the whole file while the show goes on playing, one frame of
  the file for each LED refresh, so it takes about as long as a fiftieth of a second for
  each frame of the animation.
- `bad-file`: the file is not a valid ODRG file for the canvas. The reply has one more
  member, `{"ok":false,"error":"bad-file","reason":"<reason>"}`: a reason of "ODRG files"
  in [reasons.md](reasons.md), or `size-mismatch` when the file is for another canvas
  size. The upload is discarded.
- On success the file is in place and the item is in the show. It can be played at once.
  If the item that is playing got a new animation, or a cycle that is playing lists it,
  what is playing starts again from its first frame.

**`upload cancel`** discards the open upload. An upload on which nothing has moved for 60
seconds is discarded too: no data arrived, and no check is running.

Playback goes on during an upload. Nothing of the show changes before `upload end`
succeeds.

## Error codes

| Code | When |
|---|---|
| `line-too-long` | The line is longer than 2,048 characters. |
| `unknown-command` | The first word is not a command. |
| `bad-argument` | An argument is missing, extra, not a number, out of range, or not in its form: a file name outside the naming rule, base64 that is not as described or stands for more bytes than `chunk`, a CRC-32 that is not eight hexadecimal digits, or a word after `upload` that is not `begin`, `data`, `end` or `cancel`. |
| `show-invalid` | `play`, `list`, `remove` or an `upload` command was sent while the show is invalid. |
| `no-upload` | `upload data`, `upload end` or `upload cancel` was sent while no upload is open. |
| `incomplete` | `upload end` came before all bytes. |
| `bad-checksum` | `upload end` names another CRC-32 than the bytes received have. |
| `busy` | `upload begin` or `remove` while an upload is open; `upload end` while the file is being checked. |
| `unknown-id` | `play` or `remove` names an id that is not in `show.json`. |
| `in-use` | `remove` names an animation that a cycle lists; `upload begin` names the id of a cycle, or a file name another item has. |
| `no-space` | `upload begin`: the file would not fit, or the show has no room for another item. |
| `bad-offset` | `upload data`: the offset is not the number of bytes received so far, or the bytes would pass the size of the file. |
| `bad-file` | `upload end`: the file is not a valid ODRG file for the canvas. |
| `storage-error` | The storage could not be read or written. The show is as it was. An upload that met it is discarded. |

When more than one code applies, the reply has the first in the order of this table.

## Transports

A transport only carries lines to the command front-end and replies back. The commands and
replies are the same on every transport.

| Where | Serial | Network |
|---|---|---|
| Board | The USB serial port. | HTTP over Wi-Fi, on the board's web server. |
| Emulator | A virtual serial port on the Mac. | HTTP on the emulator's page address. |

**HTTP.** A command is sent as `POST /odrig` with the command line as the request body, with
or without the final newline. The response body is the reply line, with content type
`application/json`. The response status is 200 whenever the line reached the command
front-end, including replies with `"ok":false`. Any other method on `/odrig` gets status 405.
~~~~

## The text of docs/show.md

Three places change, and two sections are added.

In the table of `show.json`, the row of `items` becomes:

~~~~markdown
| `items` | array | The items that can be played. It may be empty. |
~~~~

Under "Installed file set", after the table of files:

~~~~markdown
The player also keeps three files of its own in the folder while it changes the show:
`upload.part`, `show.part` and `pending.txt`. They are gone when a change is complete, and
the player removes what is left of them when it starts. No show names them: a name in
`show.json` ends in `.odrg`.
~~~~

The sentence "The player reads these files when it starts. Nothing else defines the layout
or the show." becomes:

~~~~markdown
The player reads these files when it starts. Nothing else defines the layout or the show.
While it runs, the commands `remove` and `upload` of [commands.md](commands.md) change the
show; see "Changing a show while it runs".
~~~~

New sections, before "When a show is invalid":

~~~~markdown
## Changing a show while it runs

`remove <id>` takes an item out of the show. `upload` adds an animation item, or gives an
animation item another animation. Both take effect at once and are kept: the player
writes `show.json` and the `.odrg` file, and a restart finds the show as it was left.

- A new item is added at the end of `items`. Its `id` is the one the upload named: any
  id from 1 to 65,535 that no item has. Ids need not follow each other, and the id of a
  removed item can be used again.
- An upload to the id of an animation item replaces its animation. The item keeps its id
  and its position, and gets the file name the upload named.
- A cycle cannot be made or changed by a command. A cycle can be removed, and an
  animation can be removed once no cycle lists it.
- Two items do not get the same file by an upload: a file name that another item has is
  refused. A show installed with two items that name one file keeps working, and the
  file is deleted when the last item that names it is removed.
- An `.odrg` file that no item names any more is deleted.
- The show may end up without items. It is valid: nothing plays until an animation is
  uploaded.
- `brightness` and `start` of `show.json` are not changed by an upload. Removing the
  `start` item removes `start`.
- `mapping.json` is never changed.

A change is made so that a power cut at any moment leaves a whole show in the folder: the
one from before the command, or the one after it. New content is written to a file of its
own and gets its name by renaming.

How many items a player has room for is fixed when it starts: 32 more than the show has
then, and at least 128. A new item beyond that is refused until the player has restarted
or an item was removed.

## show.json after a change

The player writes `show.json` as one line without spaces, followed by a line feed, with
the members in this order, and `start` only when the show has one:

```json
{"version":1,"brightness":128,"items":[{"id":1,"file":"hello.odrg"},{"id":3,"cycle":[1,2],"seconds":15}],"start":3}
```

`brightness` is the value the file had when the player started. A file written by hand in
another layout is read as before; it gets this layout the first time the show is changed.
~~~~

`docs/reasons.md` loses "there is no item" from the conditions of `show-malformed`.

## The host interface

The members after `log`, as `core/include/odrig_core.h` gets them:

```c
    /* Storage that can be changed. A host without it sets write_open to NULL.
       A name is 1 to 32 characters of a-z, 0-9, '-', '_' and '.'. */

    /* Begins a new, empty file of this name, in place of one that has it. A file that was
       being written is given up and removed. Returns 1, or -1 on failure. The core has at
       most one file being written. */
    int (*write_open)(void *ctx, const char *name);

    /* Adds bytes to the file being written. length is 1 to 1500. Returns 1, or -1. */
    int (*write)(void *ctx, const uint8_t *bytes, size_t length);

    /* Ends the writing. When it has returned 1, the file is whole in storage and stays so
       through a power cut. Returns 1, or -1 on failure. */
    int (*write_close)(void *ctx);

    /* Gives the file `from` the name `to`, in place of a file that has it. After a power
       cut during the call, `to` is its old file or the new one, whole. Neither file is
       open or being written when the core calls this. Returns 1, or -1. */
    int (*rename)(void *ctx, const char *from, const char *to);

    /* Removes the file of this name. A file being written under it is given up.
       Returns 1 when it removed one, 0 when there was none, -1 on failure. */
    int (*remove)(void *ctx, const char *name);

    /* The free and the total bytes of the storage the files are in. A value above
       4294967295 is given as that. Returns 1, or -1 when the host cannot tell. */
    int (*space)(void *ctx, uint32_t *free_bytes, uint32_t *total_bytes);

    /* Reads a file apart from the one that open, read and close hold: up to capacity
       bytes from this offset. Returns the number read, 0 at or after the end of the
       file, -1 on failure and when there is no such file. capacity is at most 512.
       The core reads a file with it from offset 0 on, each call where the last ended. */
    int32_t (*read_at)(void *ctx, const char *name, uint32_t offset,
                       uint8_t *buffer, size_t capacity);
```

"Writing a file" is three functions because an upload arrives over many commands: a host
that had to open, add and close for every piece would make its file system commit several
hundred times for one file. `read_at` is one function more than the seed lists; why it is
needed is under "The check".

`ODRIG_LINE_MAX` becomes 2048 and `ODRIG_REPLY_MAX` 1024. The seven functions the core
offers keep their signatures.

Rules of use, added to those of `docs/core.md`:

- The core calls the storage functions inside `odrig_core_begin`, `odrig_core_command`,
  `odrig_core_feed` and `odrig_core_poll`.
- With `write_open` `NULL` the host has no storage that can be changed: `remove` and
  `upload begin` are answered with `storage-error`, the start deletes nothing, and the
  blocks that only uploads need are not asked for. `space` may be `NULL` too; the command
  is then answered with `storage-error`.
- With `write_open` set, all seven are set.

## The core

### New and changed files

```
core/src/
  commands.cpp        changed: words of a line; the content commands dispatched
  content.cpp, .h     new: space, list, remove; the tables changed in place; show.json written
  upload.cpp, .h      new: the upload, base64, CRC-32, the check
  storage.cpp, .h     new: the core's file names, the sequences of a change, what the start removes
  show.cpp            changed: tables with room; a show without items; sizes of files
  core.cpp            changed: the start removes leftovers; the blocks for uploads
  player.cpp          changed: positions that move; a step of the check after a refresh
  file_source.cpp, .h changed: a source read with read_at, with the CRC-32 of what it read
  core_state.h        changed: the state below
```

### Lines and replies

A line is split into words at every single space, as today. `command_answer` gets the
words as positions in the line, up to five; a sixth word makes every command
`bad-argument`.

The line of the byte entry, 2,049 bytes, the reply of the byte entry, 1,024 bytes, and the
chunk buffer, 1,500 bytes, are three blocks taken at startup. They are not in the core
object, which stays under 4,096 bytes, and no function has a local array above 256 bytes.
`odrig_core_command` writes into the caller's reply, as today.

A reply is built by the `Reply` of `commands.cpp`, which gains `fits(bytes)`: `list` asks
before it adds an item.

### Tables with room

`read_show` counts the items as today and then takes the tables larger:

| Table | Entries | Each |
|---|---|---:|
| Items | `capacity = max(128, items + 32)`, at most 65,535 | 16 |
| Files | `capacity` | 48 |
| Cycle entries | the entries the show has; at least 1 | 2 |

A cycle is never made or lengthened by a command, so the entry table never grows.
`FileInfo` becomes the name, `bytes` and `total_ms`: `bytes` takes the place of `frames`,
which nothing reads, and the entry stays 48 bytes. At startup `bytes` is the number of
bytes the check of the file read, which is the whole file.

The core keeps `show_brightness`, the brightness of the file, apart from `brightness`,
which commands change.

**Removing the item at position p.** The item table closes the gap. Every position above p
that the core holds goes down by one: the entries of every cycle, `playing`, `shown`,
`stream_item`, `start_item`. If the item was a cycle, its entries leave the entry table
and the `first` of every later cycle goes down by their number. If it was an animation and
no other item names its file, the file leaves the file table and the `first` of every
animation item above it goes down by one. No entry of a cycle can be p: that is `in-use`.

**Adding an item.** An `ItemInfo` and a `FileInfo` are written at the end of their tables.

**Replacing.** The `FileInfo` of the item gets the new name, `bytes` and `total_ms`. When
another item named the old file too, the item gets a `FileInfo` of its own at the end of
the file table.

### The core's files in the folder

| Name | What it is |
|---|---|
| `upload.part` | The bytes of the open upload. |
| `show.part` | The next `show.json`, until it is renamed. |
| `pending.txt` | The names of `.odrg` files that a change makes or is about to delete, one on a line, each ended by a line feed. A file named here that no item of `show.json` names is not part of the show. |

### The four kinds of change

Each line is one call to the host. The show changes at the line marked with an arrow: a
power cut before it leaves the old show, one after it the new show.

**A removal.** F is the removed item's file; lines 1, 4 and 5 are left out when the item is
a cycle or another item names F.

```
1  write pending.txt: "F"
2  write show.part: the show without the item
3  rename show.part -> show.json                 <-
4  remove F
5  remove pending.txt
```

**An upload for a new item**, with the file name G:

```
1  write pending.txt: "G"
2  rename upload.part -> G
3  write show.part: the show with the item at its end
4  rename show.part -> show.json                 <-
5  remove pending.txt
```

**An upload that replaces an item's file by one of the same name G:**

```
1  rename upload.part -> G                       <-
```

`show.json` does not change.

**An upload that replaces an item's file F by one of another name G.** F is left out of
lines 1 and 5 when another item names it.

```
1  write pending.txt: "G", "F"
2  rename upload.part -> G
3  write show.part: the show with the item naming G
4  rename show.part -> show.json                 <-
5  remove F
6  remove pending.txt
```

"write X" is `write_open`, one or more `write` and `write_close`.

The tables in memory change after the arrow, never before. Before a `rename` onto a name,
and before a `remove` of a name, the player's stream is closed when it has that file
open; it opens again by itself at the next refresh if the item still plays.

**When a call fails** before the arrow, the reply is `storage-error`, and the core undoes
what it did as far as the host lets it: it removes `show.part`, a G it had just renamed
into place, and `pending.txt`, and the tables are as they were. An upload it happened to
is discarded with its bytes, and has to be sent again. When a call fails after the arrow,
the change stands and the reply is `{"ok":true}`: what could not be removed is named by
`pending.txt` and is removed at the next start.

### What the start does with leftovers

In `odrig_core_begin`, with a host that has storage:

1. Before anything is read: `remove upload.part` and `remove show.part`.
2. `mapping.json` and `show.json` are read and the ids checked, as today.
3. When that went well and `pending.txt` exists: it is read, at most 512 bytes; every
   line that ends in a line feed and is a file name under the naming rule is taken; each
   such file that no item names is removed; then `pending.txt` is removed. When the show
   file could not be used, `pending.txt` is left alone.
4. The files the show names are checked, as today.

A folder without these three names gets two `remove` calls that find nothing, one `open`
that finds nothing, and no other storage call.

**A power cut at each point**, for an upload that replaces F by G; the other kinds are
parts of this one:

| The cut falls | `show.json` | In the folder | The start |
|---|---|---|---|
| in an `upload data` | old | `upload.part`, in part | removes it |
| before line 1, or in it | old | `upload.part`; `pending.txt` missing, empty or cut | removes `upload.part`; a cut line of `pending.txt` names nothing; removes `pending.txt` |
| after line 1 | old | `upload.part`, `pending.txt` | removes `upload.part`; G is not there, F is named: nothing else |
| after line 2 | old | G, F, `pending.txt` | G is not named: removes it. The old show, whole |
| in line 3, or after it | old | G, F, `show.part` in part or whole, `pending.txt` | removes `show.part` and G |
| after line 4 | new | G, F, `pending.txt` | F is not named: removes it. The new show, whole |
| after line 5 | new | G, `pending.txt` | removes `pending.txt` |

The host's promises carry this: a file that was being written and not closed may hold any
beginning of its bytes or be missing, and is always one the start removes; a `rename` is
whole or did not happen.

### The upload

State in the core object: none, receiving, checking, checked. With it: the id, the file
name, the size, the bytes received, the running CRC-32, the time of the last progress, and
for `checked` the outcome: passed with the file's total duration, a reason, or a storage
failure.

**`upload begin`.** In the order of the codes: the words; the show valid; no upload open;
the id not a cycle's and the name not another item's; a new id and room in the tables;
`space` from the host and `bytes + bytes / 256 + 16384 <= free`; `write_open
upload.part`. Then the state is receiving. The reserve of 16,384 bytes is four blocks of
the board's file system, for `show.part`, `pending.txt` and the file system's own
records; `bytes / 256` covers the block pointers a large file needs.

**`upload data`.** The base64 is checked whole and decoded into the chunk buffer before
anything else happens. Then: an upload open; the offset equal to the bytes received and
the bytes inside the size; one `write`. The CRC-32 takes the bytes in. When the last byte
has arrived: `write_close`, and the state is checking.

**Base64.** The 64 characters `A`-`Z`, `a`-`z`, `0`-`9`, `-`, `_` stand for 0 to 63. Four
characters are three bytes. A last group of two characters is one byte and of three
characters two bytes; a last group of one character is not valid. The bits of the last
character that belong to no byte are zero. There is no padding character. This is the
alphabet of RFC 4648, section 5. It is chosen over the common one with `+`, `/` and `=`
because of what seed 04 found in WLED's web server: a body with `+` or `=` in it is taken
apart as a form when a client sends it as a form or as plain text. With this alphabet
every valid command line is free of those characters, whatever content type a client
sends.

**CRC-32.** The one of zlib: for each byte, `crc = table[(crc ^ byte) & 0xFF] ^ (crc >>
8)` over the reflected polynomial `0xEDB88320`, from a start of `0xFFFFFFFF`, with the
result inverted. The core computes it four bits at a time from a table of 16 entries.

**`upload end`.** In the order of the codes: the eight digits; an upload open; all bytes
there; the CRC-32 equal, else the upload is discarded; the check ended, else `busy`; the
check passed, else `bad-file` with its reason, or `storage-error`; then the change, by
the sequence of its kind.

**`upload cancel`**, **60 seconds** and **a show that becomes invalid** discard: `remove
upload.part`, which also gives up a file being written, and the state is none.

**The 60 seconds.** Every call that carries a timestamp, a command, bytes or a request for
a refresh, first looks at an open upload: when the time, as `clock_touch` gives it, is
60,000 ms or more after the last progress, the upload is discarded before the call does
anything else. Progress is `upload begin`, a taken `upload data`, and a step of the check.
So an upload whose data stops, and one whose check has ended and whose `upload end` does
not come, both go after 60 seconds, and a check that runs is never cut off.

### The check

An uploaded file must be decoded whole before it joins the show: a file that breaks the
format in its last record would otherwise make the show invalid when it is played, and
after a restart. Decoding takes as long as it does at startup: seed 05 expects about six
seconds for a dense 60 x 60 clip of ten seconds on the board. Done inside one command it
would stop the LEDs for that time.

So the check runs in steps, and beside playback:

- It has its own `FileSource`, `Inflate` and `OdrgDecoder`, one block of about 2,500
  bytes, its own pixel buffer and its own DEFLATE window. These are the same code as the
  player's, on second objects.
- Its `FileSource` reads `upload.part` with `read_at`, 512 bytes at a time, from the
  first byte on, and folds every byte it read into a CRC-32.
- The first step reads and judges the header and compares the canvas with the mapping.
  Every further step decodes one frame record and adds its duration. The step after the
  last record asks for the end of the file and compares the CRC-32 of the bytes read with
  the one of the bytes received.
- A step is taken inside `odrig_core_poll`, after the LED data of a refresh is complete,
  and only when the grid time of this refresh is 20 ms after that of the refresh before:
  when the host is late, the check waits. One step is one call of the decoder's `next`,
  which is what playback itself does for every refresh.
- The outcome is kept until `upload end` asks for it.

The check reads back from storage, not from the bytes as they arrive, for two reasons.
The decoder pulls its input and cannot stop in the middle of a frame record when a piece
has not arrived yet; and a file read back is a file that was really stored.

That needs a second file open while the player's file is open, which `open`, `read` and
`close` cannot give: they hold one file, and the format is read front to back. `read_at`
is the smallest addition that does it: one function, no state in the core.

A file of F frame records is checked in F + 2 refreshes: about a fiftieth of a second for
each frame of the animation. `upload end` before that is answered with `busy`.

### Playback and a change

| Change | What plays |
|---|---|
| The item being played is removed | `playing` and `shown` become nothing, the stream is closed, the next refresh is dark. |
| Another item is removed | Positions move; the LED data is as without the command. |
| A new item is uploaded | Nothing changes. |
| The file of the animation being played is replaced, or of an animation the playing cycle lists | `player_play` for the item being played: its time zero is the grid time of the next refresh. |
| Another item's file is replaced | Nothing changes. |

### Writing show.json

`content.cpp` writes the text of "show.json after a change" into the chunk buffer and
gives it to `write` whenever 1,500 bytes are full, and at the end. The chunk buffer is
free then: a removal is refused while an upload is open, and an `upload end` that reaches
this point has no data left to take.

### Memory

For the target file, 60 x 60, with a show of 100 items, 80 animations with a file each and
20 cycles of 10 entries. Rows two to seven are as seed 05 leaves them; the core object
grows from 3,112 bytes by the state of an upload.

| Block | Size | Bytes |
|---|---|---:|
| The core object | fixed, at most 4,096 | about 3,300 |
| Legs | 12 for each leg | 240 |
| The pixel of each LED | 2 for each LED | 7,200 |
| LED data | 3 for each LED | 10,800 |
| Strip check | 1 bit for each strip | 8 |
| Pixel buffer | the smaller of 3 * W * H and 65,534 | 10,800 |
| Window of the DEFLATE decoder | 32,768 | 32,768 |
| Items | 16 for each of 132 | 2,112 |
| Cycle entries | 2 for each entry | 400 |
| Files | 48 for each of 132 | 6,336 |
| Line of the byte entry | 2,049 | 2,049 |
| Reply of the byte entry | 1,024 | 1,024 |
| Chunk buffer | 1,500 | 1,500 |
| The check: source, DEFLATE decoder, ODRG decoder | fixed | about 2,500 |
| The check: pixel buffer | as the player's | 10,800 |
| The check: window | 32,768 | 32,768 |
| **Total** | | **about 124,600** |

That is 95 percent of the 131,072 bytes the core may use for this canvas, where seed 05
leaves 54 percent. The two blocks of the check are 43,568 of the difference. The figures
marked "about" are settled by the compiler; `tests/core/test_memory.py` measures the total
and fails at 131,072. A host without storage is not asked for the last four blocks.

### Allocation

Nothing changes in how memory is taken: `arena_take` inside `odrig_core_begin` only. The
test host stops, as today, when the core asks for memory later, and the test of the
library's symbols still finds no allocation routine.

## The test host

`tests/core/host/host.cpp` gets the seven functions, on the folder of a session and on
the files of a batch session held in memory, and these options:

| Option | What it does |
|---|---|
| `--storage BYTES` | The total space. The free space is the total less the sizes of the files, each rounded up to 4,096. Without it the total is 10,354,688. |
| `--no-storage` | `write_open` and the other six are `NULL`. |
| `--store-fails-at N` | The N-th storage call fails: it does nothing and returns -1. |
| `--cut-at N` | The N-th storage call is not made; the program prints `power cut` and ends with status 75. |
| `--cut-at N --cut-keeps K` | The same, but when that call is a `write`, its first K bytes are written first. |
| `--trace-store` | Prints `store <call> <arguments> <result>` for every storage call. |

A storage call is one of `write_open`, `write`, `write_close`, `rename` and `remove`.
`space` and `read_at` are not counted. A file that was being written when the program ends
stays with the bytes written so far.

It stops with `file misuse`, status 71, also when the core: gives `write` no byte or more
than 1,500; calls `write` or `write_close` with no file being written; names a file
outside the names of Requirement 14; renames or removes the file its `open` holds; or
asks `read_at` for more than 512 bytes or for an offset that is not where its last call
for that file ended. Its check of a reply allows 1,024 bytes.

## The emulator

- `emulator/host.py`: `FolderHost` gains `write_open`, `write`, `write_close`, `rename`,
  `remove`, `space` and `read_at`. Files are opened in the folder only; a name with a
  path separator is refused, as in `open`. `write_close` flushes, has the system write the
  file out (`os.fsync`) and closes; `rename` is `os.replace`; `read_at` keeps one file
  open and seeks when the offset is not where it stands. The total space is 10,354,688
  bytes or the value of `--storage`.
- `emulator/binding.py`: the seven function types and members of the host record;
  `LINE_MAX` 2048 and `REPLY_MAX` 1024. The test that compares the record with the header
  covers the new members.
- `emulator/httpd.py`: a body is kept up to 4,096 bytes.
- `emulator/engine.py`, `hub.py`: a log entry keeps the first 200 characters of a line and
  gets `length`, the number of characters of the line as the core read it. `cut` stays
  what it is: the line was longer than the core's limit.
- `emulator/web/app.js`: a line longer than 200 characters is shown with its first 200
  and its length; the note on a cut line names 2,048.
- `emulator/app.py`: `--storage BYTES`, in real time and in record mode.

The emulator does not pace anything: its file operations take microseconds.

A folder the emulator was killed on during an upload holds `upload.part` until the next
start on it. `install-show` of the firmware tool refuses such a folder, as it refuses any
file the show does not name.

## The command tool

```
python -m odrigctl (--port NAME | --http ADDRESS) [--timeout SECONDS] space
python -m odrigctl (--port NAME | --http ADDRESS) [--timeout SECONDS] list
python -m odrigctl (--port NAME | --http ADDRESS) [--timeout SECONDS] remove ID
python -m odrigctl (--port NAME | --http ADDRESS) [--timeout SECONDS] upload ID FILE
```

- `odrigctl/client.py` gains a session: `Session(port=..., http=..., timeout=...)` with
  `exchange(line)` and `close()`. Over the port it opens the port once, as
  `serial_exchange` does, and keeps it open; over HTTP every exchange is one request.
  `serial_exchange` and `http_exchange` stay for one command.
- `odrigctl/content.py`, new: `list_all(session, show)`, and `upload(session, id, name,
  data, progress)`, which runs the steps of Requirement 18 and calls `progress(sent,
  total, seconds)` after every acknowledged piece. The board tests call `upload` with a
  `progress` that also asks for `status` through the same session.
- `odrigctl/cli.py`: the four commands; `upload` takes two arguments. The file is read
  whole before anything is sent. The name sent is the last part of the path, as it is.

Progress goes to standard error, one line for each report, or one line rewritten in place
when standard error is a terminal:

```
upload: 45% 613500/1362000 bytes 21400 B/s
```

The speed is the bytes acknowledged so far over the time since `upload begin` was
answered. After the last piece the tool writes `upload: checking` once and sends
`upload end` every 0.2 seconds while the reply is `busy`.

Standard output gets the reply that ended the command: the `{"ok":true}` of `upload end`,
or the first reply that was not ok.

| Status | Meaning |
|---:|---|
| 0 | The reply, for `upload` the reply to `upload end`, and for `list` every reply, has `"ok":true`. |
| 1 | A reply has `"ok":false`. It is printed. An upload the tool had opened is cancelled first. |
| 2 | The command line was not understood, or the file to upload cannot be read. |
| 3 | The target could not be reached, or no reply arrived in time. |

After 600 seconds of `busy` the tool sends `upload cancel`, prints the last reply and
exits with status 1.

## The firmware

### The host functions (`odrig_files.cpp`)

The seven functions on WLED's file system, every path `/odrig/<name>`, every name checked
for its length and its characters before it is used:

| Function | On the board |
|---|---|
| `write_open` | Closes and removes a file that was being written; `WLED_FS.open(path, "w")`. |
| `write` | `File::write`; -1 when fewer bytes were taken than given. |
| `write_close` | `File::close`; then the size of the file is compared with the bytes written. |
| `rename` | Closes the second reader and the writer when they hold either name; `WLED_FS.rename`. |
| `remove` | Closes the second reader and the writer when they hold the name; `WLED_FS.remove`; 0 when the file was not there. |
| `space` | `WLED_FS.totalBytes()` and `usedBytes()`; free is their difference. |
| `read_at` | A second `File`, kept open with its name and position; opened or moved with `seek` when a call asks for another file or place. |

`usedBytes` walks the file system (S4). The usermod keeps the figure it got and asks the
file system again only after one of its own storage calls, so that `space` asked once a
second by an app costs nothing.

### Pacing

A storage call stops the task that makes it for as long as the flash takes: programming
a page, and now and then erasing a block, which the flash's data sheets give as tens of
milliseconds and at worst some hundreds. The call is made with the core's lock held, so
the request for a refresh waits behind it.

- **Sized.** One `upload data` is one `write` of at most 1,500 bytes: with the file
  system's cache of 512 bytes (S2) that is three pieces to the flash, and a new block,
  with its erase, about every third command.
- **Timed.** The usermod measures every storage call with the chip's microsecond clock.
- **Paced.** After a storage call that took d, no further command line is given to the
  core until `max(20 ms, 2 * d)` have passed. The port leaves the bytes that arrive in
  its queue; the web server's handler waits before it takes the lock. Neither looks at a
  line: they know a storage call happened because the usermod's own host functions were
  called. So storage calls take at most a third of the time, whatever a client does, and
  the client sees the pacing as the time a reply takes, which is what its speed display
  shows.
- **The queue of the port** is made 4,096 bytes in the usermod's `setup` (S5), so that a
  line of 2,048 characters sent in one piece is not dropped while the loop is busy.
- The reply of the port and the body and reply of the web server are not on a stack: the
  port's reply is a static array of 1,024 bytes, and the handler keeps body and reply in
  memory that belongs to the request.

The check adds one frame record of decoding to a refresh, and waits when the host is
late. On the bench show that is a fraction of a millisecond.

### The probe build

The report gains `store`, an object: `calls`, `longest_us` and `total_us` of the storage
calls since the last report, and `check_steps`, `check_longest_us` and `check_total_us`
of the requests for a refresh in which a step of the check ran. And one line of its own,
answered by the usermod and not by the core, for the spike:

```
#store <bytes>
```

writes a file `probe.part` of that size into `/odrig` in pieces of 1,500 bytes through
the usermod's own host functions, one piece in each pass of the loop that the pacing
allows, renames it onto `probe.odrg`, reads it back with `read_at`, removes it, and then
answers with the times and the bytes a second. Like every probe code it is inside
`#ifdef ODRIG_PROBE`.

### Assumed, to be verified on the board

| # | Assumption | If it does not hold |
|---|---|---|
| B1 | `WLED_FS.rename` onto a name that has a file replaces it, when neither file is open. | The host removes the destination first, and the core's sequences are looked at again for the moment between the two calls; the drift is recorded. |
| B2 | A file can be written, renamed and read with a second handle while the player has another file open and reads it. | The finding is recorded; the check is then done with playback stopped, which the owner has to accept. |
| B3 | A `write` of 1,500 bytes takes a few milliseconds, and one in three some tens. With the pacing, `status` reports 25 or more with the bench show playing. | The writes move to a task of their own, with a queue in the external memory, designed from the measurements. |
| B4 | A line of 2,048 characters written to the port in one piece arrives whole with a queue of 4,096 bytes. | The command tool writes a line in pieces of 256 bytes with a short wait, and the drift is recorded. |
| B5 | `usedBytes` takes under 100 ms with storage nearly full. | The figure is taken once at start and kept up by the sizes of what the usermod writes and removes. |
| B6 | An upload over USB carries 10,000 bytes a second or more. | The figure is reported as it is; the pacing's lower limit of 20 ms is the first thing to look at. |

That a power cut during `rename` leaves the old or the new file is LittleFS's own promise
and is not tried: no task cuts the board's power.

## Testing strategy

Four suites need no board:

```
.venv/bin/python -m unittest discover -s tests/converter -t .
make -C core test
python3 -m unittest discover -s tests/emulator -t .
python3 firmware/fw.py test
```

`python3 firmware/fw.py test-board` needs the board, and `test-air` a joined network.

| Suite | Tests |
|---|---|
| `tests/core/test_commands.py` | Lines of 2,048 and 2,049 characters through both entries; a reply of `list` at 1,024 bytes; the old commands byte for byte. |
| `tests/core/test_content.py`, new | `space` with the host's figures, without storage, with a host that cannot tell; `list` on every show of the suite, with `from` at every position, with names of 32 characters, with 132 items, with a cycle too long for a reply, on an empty and on an invalid show; `remove` of each kind of item, of the playing item, of the `start` item, of an item a cycle lists, of the last item, with a file two items name; the LED data against the reference before and after. |
| `tests/core/test_upload.py`, new | A new item and a replacement, with the same and with another name, compressed and uncompressed, on every mapping of the suite; pieces of 1, 1,499 and 1,500 bytes; every broken form of base64 and of the CRC; each error code through each command that gives it; pairs of codes for the order; `bad-file` for every invalid test vector and for a file of another canvas, with the reason the reference gives; `busy` until the check has ended, counted in refreshes; a late host; `upload cancel` and 60 seconds at each state; commands over the two entries mixed; playback against the reference during all of it; the replaced file playing from its first frame. |
| `tests/core/test_powercut.py`, new | For each kind of change, and for an upload in each state: a run with `--cut-at N` for every N the change has, and with `--cut-keeps` inside a write; then a start on the folder as it is: the show is valid and is the old one or the new one, every file it names decodes, and the folder holds no other file. The same with `--store-fails-at N`: `storage-error`, the old show, nothing left. |
| `tests/core/test_memory.py` | The total for the target file with 100 items, below 131,072; no allocation during a session of content commands; a host without storage is asked for four blocks fewer. |
| `tests/core/test_startup.py`, `test_json.py` | A show without items is valid; the tables have room; a folder without leftovers gets the two `remove` calls of the design and no other storage call; each leftover, alone and together, is removed; `pending.txt` with a cut line, with a name outside the naming rule and beside a show file that cannot be used. |
| `tests/core/support.py` | `ReferencePlayer` with storage as a dictionary, the content commands, and the check counted in refreshes. |
| `tests/converter/` | `odrig/show.py` reads a show without items; `pack` of one writes the two JSON files; the show file as the core writes it is read back. |
| `tests/emulator/` | `test_binding.py`: the new members. `test_http.py`: a body of 4,096 bytes and of 4,097. `test_events.py`: `length`. `test_content.py`, new: the commands over serial and over HTTP against the reference, `--storage`, `no-space`. `test_tool.py`: the four commands of the tool; an upload over serial and over HTTP with its progress lines, then `list`, `play`, a restart of the emulator, `list` and `remove`; each exit status; a lost reply, with a server that drops one; `busy` waited out. `test_record.py`: a script with an upload gives the same recording twice. |
| `tests/firmware/test_usermod_files.py` | Files are written, renamed and removed only in `odrig_files.cpp` and only under `/odrig/`; the pacing is in the usermod and names no command word; `BODY_BYTES` is 4,096; no array of 1,024 bytes on a stack; the new probe code is inside the probe flag. |
| `tests/board/test_upload.py`, new | The spike's `#store`; then the session of Requirement 21 with the command tool over USB; `status` once a second during an upload of a dense bench clip of 60 seconds; the speed; `read-show` afterwards gives the uploaded bytes; the folder is left as it was found. |
| `tests/air/test_upload.py`, new | The same session over HTTP, for a person whose computer has joined the board's network. |

**Who checks what** of the seed's definition of done:

| Item | Checked by |
|---|---|
| 1. Every command, every code, an upload interrupted at each step, a power cut at each write | `tests/core/test_content.py`, `test_upload.py`, `test_powercut.py` |
| 2. The tool uploads in the emulator over serial and HTTP; list, play, restart, remove | `tests/emulator/test_tool.py` |
| 3. The same on the board over USB; the speed | `tests/board/test_upload.py`, `docs/firmware.md` |
| 4. 25 during an upload, 49 afterwards | `tests/board/test_upload.py` |
| 5. The two documents | `tests/core/test_docs.py`, which compares the error codes and the limits of `docs/commands.md` with the core |
| 6. Upload over Wi-Fi | The owner, with `tests/air/test_upload.py` |

## Documents

| Document | What changes |
|---|---|
| `docs/commands.md` | The text above. |
| `docs/show.md` | The texts above. |
| `docs/reasons.md` | `show-malformed` without "there is no item". |
| `docs/core.md` | The host interface with the seven functions and their rules; the limits; "It never writes" gives way to what it writes and when; the start with leftovers; the check; the memory table with measured figures; the test host's options and its new checks. |
| `docs/emulator.md` | `--storage`; the body limit; `length` in the log event; the command tool's four commands, the progress line and the statuses. |
| `docs/firmware.md` | "The firmware never writes" gives way to what it writes; the pacing; the port's queue; the body limit; `store` in the probe's report; "Measurements on the board" with the upload; the owner's check. |
| `docs/decisions.md` | "Commands": the list as it is. The change log. |
| `docs/android-app.md` | Not edited: it is the page of seed 09. |

## Order of work

1. The limits, in the core and the emulator.
2. The host interface, the test host, the emulator's host, and `space`.
3. A spike on the board: the firmware's storage functions and their timing, with the
   probe build, before the core's upload is written.
4. The show that changes: `list`, `remove`, the tables, `show.json` written, leftovers,
   power cuts in a removal.
5. The upload, whole: `begin`, `data`, the check, `end`, `cancel`, the 60 seconds, and
   power cuts in each kind of upload.
6. The command tool.
7. The firmware with the whole core: the session on the board and the measurements.
8. The documents and the last run.
9. The owner's check.

Until its task, a command that is not there yet is answered with `unknown-command`, and
`docs/commands.md` lists only what exists.

## Risks

1. **Writes and the LEDs on the board** (B3). Nothing was measured for this design. The
   spike comes third for that reason, and the fallback is a task for the writes.
2. **Memory.** 95 percent of the limit. A later feature that needs a block has to find it
   elsewhere, or the limit has to be looked at again.
3. **`read_at`** is a function the seed does not list, and the check by steps makes
   `upload end` answer `busy`. Both follow from "playback continues"; the owner may
   prefer a dark second to either.
4. **The check is slow for long, simple animations**: a fiftieth of a second for each
   frame, whatever the frame costs.
5. **Six additions to the approved form**, below.
6. **Seed 05's loop.** If seed 05 moved the request for a refresh to a task of its own,
   the check runs on that task and the storage calls on the loop or the network task.
   The lock keeps them apart; the pacing then has to be measured again in the spike.
7. **A long line over USB** (B4).
8. **No command gives a client the canvas size.** The app of seed 09 converts on the
   phone and must know it; a wrong size is found only by `upload end`. This seed adds
   nothing for it: a command is the owner's to approve.

## What goes beyond the seed

Each is a working assumption until the owner rules, with its entry in `docs/drifts.md`:

1. Two error codes the seed does not name: `no-upload` and `storage-error`.
2. `busy` as a reply to `upload end`, while the file is checked, and to `remove`, while an
   upload is open.
3. `in-use` also for a file name that another item has.
4. `no-space` also when the show has no room for another item.
5. A show may have no items, which changes `docs/show.md` and the Python reader.
6. `read_at`, a host function beyond the four kinds the seed lists.
