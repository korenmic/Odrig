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
| `play <id>` | Plays the animation with that id, from its first frame, and then goes on with the playlist; plays the cycle with that id; makes the playlist of the card's folder with that id current and plays its first animation. An unavailable animation is refused. |
| `play all` | Plays the playlist, from its first animation, and makes the root playlist current. |
| `on` | Switches the LEDs on. |
| `off` | Switches the LEDs off: every LED is dark. Playback time keeps running. |
| `brightness <n>` | Sets brightness, 0 to 255. |
| `status` | Reports the current state. |
| `fault` | Reports the latest fault of a file since the start. |
| `space` | Reports the free and the total storage and the number of animations. |
| `list`, `list <from>` | Lists the items of the show, the playlists of the card's folders, and the animations of a USB drive or a card. |
| `read <id> <offset>` | Reads up to 600 bytes of the file of an animation back. |
| `catalog` | Reports the catalog of the board's own storage and of the drive. |
| `catalog page <storage> <page> <offset>` | Reads up to 512 bytes of a page of the catalog of the board's own storage, `internal`, or of the drive, `external`. |
| `catalog rebuild <storage>` | Reads every animation of the board's own storage, `internal`, or of the drive, `external`, and writes its catalog anew. |
| `catalog cancel` | Ends a rebuild; the catalog stays as it was. |
| `remove <id>` | Removes an item from the show. |
| `remove many <ids>` | Atomically removes 1–32 distinct installed animations. |
| `ignore <id> <value>` | Excludes or includes an installed animation in the automatic playlist. |
| `mapping get` | Reports saved pin assignments, their revision and diagnostic state. |
| `mapping set <revision> <pins>` | Atomically saves a complete comma-separated pin permutation. |
| `mapping cross on` | Saves snake 10 as cross-wired: its chain up column 28, up column 30, down column 29. |
| `mapping cross off` | Saves snake 10 as wired as the other snakes. |
| `mapping test on` | Shows the built-in diagonal until stopped. |
| `mapping test off` | Stops the diagonal and resumes the show. |
| `mapping test snake <n>` | Shows the test of snake n, 1 to 20, until stopped. |
| `order get`, `order get <from>` | Reports the ids of the listed animations in the saved playlist order. |
| `order move <revision> <id> <before>` | Moves one animation before another, or to the `end`, in the saved order. |
| `repeat <id> <n>` | Makes the playlist's turn in progress of that animation `n` loops long, for that turn alone. |
| `repeat <id> <n> save` | Keeps `n` loops as the animation's saved repeat, for every later turn, and gives them to its turn in progress. |
| `repeat <id> default` | Removes the animation's saved repeat: its turns play its own count again, the one in progress too. |
| `upload begin <id> <file> <bytes>` | Opens an upload of an animation; with the file's CRC-32 after `<bytes>`, answers `unchanged` when the last upload installed that file. |
| `upload begin external <file> <bytes>` | Opens an upload of an animation to the drive, when the core may write it. |
| `upload data <offset> <base64>` | Adds a piece of the file to the open upload. |
| `upload expect <crc32>` | Lets the open upload replace its item's file only while that file is the one the client read. |
| `upload end <crc32>` | Closes the upload and installs the animation. |
| `upload cancel` | Discards the open upload. |

At power-on the LEDs are on, brightness is the value in `show.json`, and the show plays
what [show.md](show.md) says it plays by itself: the playlist of its included animations, or
the cycle its `start` names. What `on`, `off` and `brightness` change is not kept across a
restart, nor is a `play` of an animation or a cycle; the playlist that `play` makes
current, a folder of the card or the root, is kept with the time spent in its window, see
[show.md](show.md#the-playlist). What `remove` and `upload` change is: they change the
installed show.

Brightness scales every colour value v to `(v * brightness + 127) / 255`, rounded down.

A number in a command is written in decimal digits.

## Status reply

```json
{"ok":true,"on":true,"brightness":128,"playing":3,"animation":1,"fps":50,"error":null,"width":60,"height":6,"readiness":"ready","checked":2,"to_check":0,"unavailable":0,"checking":null,"host":null,"seed":null,"repeat":null,"loop":null,"saved":null,"left":86399}
```

| Member | Meaning |
|---|---|
| `on` | Whether the LEDs are switched on. |
| `brightness` | Current brightness, 0 to 255. |
| `playing` | What is being played: `"all"` for the root playlist, the id of the card's folder whose playlist is current while the card is in and holds it, the id of a cycle, or `null`. |
| `animation` | The id of the animation item, or of the drive's animation, on the LEDs right now, or `null`. |
| `fps` | LED refreshes in the last full second. |
| `error` | `null`, or the reason the show is invalid. |
| `width`, `height` | The canvas of the installed mapping, in pixels: what an animation for this target is made for. Both `null` while there is no mapping the player can use; reported also while the show is invalid for another reason. |
| `readiness` | `checking` while the player still reads files after a start, while a rebuild reads them and while a drive's catalog is read, `degraded` when it has read them all and one or more animations are unavailable, `ready` when it has read them all and none is, and `recovery` while the show is invalid. What plays is said by `playing` and `animation`, whatever the readiness. |
| `checked` | The files the player has read to their end, or found a fault in, since its start: those of the show, each once however many items name it, and those of a drive. While a rebuild runs, the files it has read. |
| `to_check` | The files it has still to read, or that a rebuild has still to read. No time is given for them. |
| `unavailable` | The animations unavailable now: the show's whose file had a fault, and the drive's files left out. |
| `checking` | The name of the file the player reads now, or that a rebuild reads; `catalog` while a drive's catalog is read; or `null`. |
| `host` | The name the board or the emulator gives itself: on the board its build, its storage and the reason of its last start, at most 95 characters; `null` when it gives none. |
| `seed` | The seed of the clock on the LEDs, 1 to 4,294,967,295: the number its turn chose when it began, from which [format.md](format.md), "The widget payload", draws every picture of the turn. `null` while the animation whose turn it is is no clock, while nothing plays, and from a `play` until the next refresh. A reply without `seed` comes from a player before it. |
| `repeat` | The loops of the playlist's turn in progress, while it is reported: the `n` of `repeat <id> <n>`, else the count the show gives the animation, a loop cut by its `max_seconds` counting as one; at most 65,535,000. `null` while no turn is reported, and while the length of its loop is not known yet and no `repeat` gave it a count. A turn is reported while the show is valid, no test of the mapping shows, the playlist plays, `animation` names the animation whose turn it is, and the turn's first refresh was made. |
| `loop` | The loop in progress of that turn, from 1, at most `repeat`; 1 while the length of its loop is not known yet; `null` while no turn is reported. A loop is a file's frames once, a text's pass, or a clock's `seconds`. |
| `saved` | The saved repeat of the animation whose turn is reported, 1 to 65,535, or `null` when it has none or no turn is reported. A reply without `repeat`, `loop` and `saved` comes from a player before them. |
| `left` | The whole seconds left in the window of the current playlist, 86,400 down to 0: the 24 hours of running time it plays for before the next playlist of the card's folders is current, see [show.md](show.md#the-playlist). 0 from the window's end until the turn in progress ends. Reported whatever the card holds, a fresh 86,400 each time a playlist becomes current. A reply without `left` comes from a player before it. |

`checked`, `to_check` and `unavailable` are 0, and `checking` is `null`, while the show
is invalid.

## The last fault

```
fault
{"ok":true,"fault":{"work":"play","file":"dvd.odrg","record":3,"bytes":1234,"reason":"truncated"}}
```

`fault` reports the latest fault the player met in a file since its start: `work` is
`start` for the check at and after the start, `play` for playback, `upload` for the check
of an upload and `drive` for the check of a drive's file; `file` is the file's name, cut to
32 characters; `record` the frame record it was at, counted from 0, the number of records
after the last one; `bytes` the bytes of its body read so far, inflated ones of a
compressed body; `reason` the reason, as [reasons.md](reasons.md) names it. A later fault
replaces an earlier one. Before any fault the reply is `{"ok":true,"fault":null}`. The
reason is what the decoder found in the bytes it was given; it does not tell whether the
storage is damaged or a read went wrong on the way. `fault` is answered while the show
is invalid too.

## Storage and the installed items

```
space
{"ok":true,"free":11517952,"total":13500416,"animations":2,"external":{"present":false,"free":null,"total":null,"read_only":true}}
```

`free` and `total` are bytes of the storage the show is in. `animations` is the number of
animation items of the show, unavailable ones among them, and 0 while the show is invalid.

```
list
{"ok":true,"items":[{"id":1,"file":"hello.odrg","bytes":1138,"ignored":false,"external":false,"type":"frames"},{"id":2,"file":"dvd.odrg","bytes":1612,"ignored":false,"external":false,"type":"frames"},{"id":3,"cycle":[1,2],"seconds":15}],"next":null}
```

The items come in the order of `show.json`, beginning at the position `<from>`, counted
from 0, which is 0 when it is left out. `<from>` is 0 to 65,535. An animation item has its
`id`, its `file` and the size of that file in `bytes`, and `external`: `false` for an
animation of the board's own storage, `true` for one of the external storage; then its
`type`, what the file holds as its header says ([format.md](format.md)): `"frames"` for an
ODRG file and for an ODRGX container of frames, `"text"` for a text and `"widget"` for a
clock. A reply without `type` comes from a player before it, and its animations are
frames. A cycle has its `id`, the ids of its
animations in `cycle`, and its `seconds`. The reply holds as many items as fit into it.
`next` is the position of the first item that was left out, to be asked for with
`list <next>`, or `null` when the last item is in the reply. An unavailable animation, one
whose file had a fault in this boot, is listed in its place with `bytes` `null` and one
more member, `fault`, the name of the reason:
`{"id":2,"file":"dvd.odrg","bytes":null,"ignored":false,"fault":"bad-palette-index"}`.
A usable animation has no `fault`. A position at or after the end
gives no items and `null`, and so does a show without items:
`{"ok":true,"items":[],"next":null}`. While the show is invalid, `list` is refused with
`show-invalid`. A cycle too long to fit into a reply by itself is listed with
`"cycle":[]`.

The files of a USB drive or of the card come after the items of the show, in the order of
the drive's listing, each as an animation item: `{"id":60001,"file":"sunrise.odrg","bytes":52340,"external":true,"type":"frames"}`.
A file in a sub-folder of the card's folder `odrig` has its path from `odrig` as its
`file`: `{"id":60004,"file":"night/comet.odrg","bytes":52340,"external":true,"type":"frames"}`.
The sub-folders themselves come between the items of the show and the files, in the
order of the listing, depth first, each as a playlist item with its path:
`{"id":60007,"playlist":"night","external":true}`, then
`{"id":60008,"playlist":"night/deep","external":true}`. Their ids come after the files',
from the same pool, in the order of the items. [show.md](show.md#animations-from-a-usb-drive)
says what a folder of the card is to the player.
A file left out for a fault is listed in its place as
`{"id":60002,"file":"broken.odrg","bytes":null,"external":true,"type":"frames","fault":"truncated"}`, and `play` of it is
refused with `unavailable`. Their ids are from 60001 up, the lowest that the show does not
use, given when the drive is taken up and before the files are read, and `file` is the
name on the drive, cut to 127 bytes, with `"` and `\` after a backslash and every
character outside printable ASCII as `\u` and four hexadecimal digits, and so is
`playlist`. The positions of `<from>` and `next` count the three kinds. An animation of the drive is listed once the player
has read it whole; while the drive is read, `list` answers without the ones still to be
read, and is not refused with `busy` for them. [show.md](show.md#animations-from-a-usb-drive)
says what the board does with a drive.

After a start the show plays at once, and the player reads every installed animation to
its end while it plays. Until it has read a file whole it does not know its size: `list`
gives its `bytes` as `null` until then. `list`, `remove`, `remove many`, `ignore` and
`upload` are answered from the start, as `status` and `space` are.

## Reading a file back

```
read 2 0
{"ok":true,"bytes":40,"data":"T0RSWAEDAQA8ADwAMHUAABQAAAADAB4A9OzQICAg1KAXAAAAPABYAg"}
read 2 40
{"ok":true,"bytes":40,"data":""}
```

`read <id> <offset>` gives up to 600 bytes of the file of an animation, of the show or of
a USB drive, from `<offset>`, so that a text or a clock can be read back and edited.
`bytes` is the size of the file, and `data` its bytes from the offset in base64 as
`upload data` takes it; at the end of the file it is empty. `<id>` is 1 to 65,535 and
`<offset>` 0 to 4,294,967,295, both in decimal digits.

- An offset above the size of the file is refused with `bad-argument`.
- An id that is no animation of the show or of the drive, a cycle's too, is refused with
  `unknown-id`.
- A file the player has not read whole since the start is refused with `busy`: ask again
  a moment later. An animation that is unavailable, as its file had a fault, is refused
  with `unavailable`; while the show is invalid, `read` is refused with `show-invalid`; and
  when the file cannot be read, or the player has no storage that can be changed, with
  `storage-error`.

## Removing an item

```
remove 2
{"ok":true}
```

The item leaves the show, and the items after it move up.

- An animation that a cycle lists is refused with `in-use`: remove the cycle first.
- An animation of a USB drive is refused with `in-use`: the drive holds it.
- A folder of the card is refused with `in-use`: it is a playlist, not a file.
- If the item is the `start` item, the show has no `start` afterwards.
- If the item is the animation whose turn it is in the playlist, the playlist goes on
  with the animation after it, from its first frame. If it was the only animation of the
  show, nothing plays and the LEDs are dark.
- If the item is the cycle that is playing, the playlist plays, from its first animation.
- Anything else that plays goes on undisturbed.
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
- It is refused with `busy` when an upload is open; with `in-use` when the id belongs to a
  cycle, to an animation of a USB drive or to a folder of the card, or another item already names `<file>`; and with `no-space` when the file would
  not fit into the free storage, or the show has no room for another item.

**`upload begin <id> <file> <bytes> <crc32>`** is the same with the CRC-32 of the file, as
`upload end` takes it: eight hexadecimal digits, `0`-`9` and `a`-`f`. When the last upload
of this boot installed `<file>` as the file of the animation item `<id>`, with `<bytes>`
bytes and this CRC-32, no upload has begun since, and the item names that file still,
usable, the reply is

```
upload begin 4 clip.odrg 3200 1c291ca3
{"ok":true,"unchanged":true}
```

and no upload opens: nothing is sent and nothing is written. Otherwise the line is taken
as `upload begin <id> <file> <bytes>`: a file that was installed in another way, or before
another upload, is uploaded again. A client that sends the same file again after a reply
that did not arrive is told so instead of writing the file a second time. A target older
than this form answers `bad-argument`.

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
- On success the file is in place and the item is in the show. A new item has its turn in
  the playlist after the items before it, and `play` can play it at once. If nothing was
  playing, the playlist starts. If the animation whose turn it is got a new animation,
  its turn begins again; if a cycle that is playing lists it, the cycle starts again from
  its first frame.

**`upload expect <crc32>`**, after `upload begin` and before `upload end`, makes the
upload replace the item's file only when that file has this CRC-32 now: the one the client
read with `read`. `<crc32>` is written as for `upload end`. The reply is `{"ok":true}` when
it has.

- `stale`: the id of the upload has no animation item, or its file has another CRC-32:
  another controller changed or removed it. The upload is discarded.
- `bad-argument`: the item's file is longer than 16,384 bytes. The upload stays open.
- `storage-error`: the file could not be read. The upload is discarded.

While an upload is open no other controller can change the show's files, so what
`upload expect` found holds until `upload end`.

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
| `show-invalid` | `play`, `list`, `read`, `remove`, `repeat` or an `upload` command was sent while the show is invalid: its mapping file or show file cannot be used, or its ids are wrong. A fault of one animation file does not make it invalid. |
| `no-upload` | `upload data`, `upload expect`, `upload end` or `upload cancel` was sent while no upload is open. |
| `incomplete` | `upload end` came before all bytes. |
| `bad-checksum` | `upload end` names another CRC-32 than the bytes received have. |
| `busy` | `repeat <id> <n> save` and `repeat <id> default` until the player has read every installed animation after a start, while an upload is open and while a rebuild runs; `read` of a file the player has not read whole since the start; `upload begin` or `remove` while an upload is open; `upload end` while the file is being checked; `upload begin`, `remove`, `remove many`, `ignore`, `order move`, `mapping set` and `catalog rebuild` while a rebuild runs; `catalog rebuild` while an upload is open, a test shows or the drive's catalog is read. |
| `unknown-id` | `play` or `remove` names an id that is neither in `show.json` nor of an animation or a folder of a USB drive or the card; `repeat <id> <n> save` or `repeat <id> default` names one of nothing `list` lists; `read` names one that is no animation of either; `play all` was sent while the playlist has no animation. A folder's id is unknown while the card is out. |
| `unavailable` | `play` names an animation that is unavailable in this boot, as its file had a fault, a file of a drive left out for a fault, or a cycle that lists only such; `read` names such an animation. |
| `in-use` | `repeat <id> <n> save` or `repeat <id> default` names a cycle or a folder of the card; `remove` names an animation that a cycle lists, or one of a drive the core may not write; `upload begin` names the id of a cycle or of an animation of a USB drive, or a file name another item has; `remove`, `remove many`, `ignore`, `read`, `order move` or `upload begin` names the id of a folder of the card, which is a playlist and no file. |
| `read-only` | `upload begin external` or `catalog rebuild` while the core may not write the storage: no drive, a drive its host cannot write, one without a catalog that is `ok`, or a host whose own storage cannot be changed. |
| `mapping-conflict` | The mapping changed since the client read its revision; reload before saving. |
| `stale` | `upload expect`: the item of the upload is gone, or its file is not the one the client read. The upload is discarded. `repeat <id> <n>`: no turn of that animation is reported. |
| `order-conflict` | `order move`: the saved order or the listed animations changed since the client read the order's revision; read it again before moving. |
| `no-space` | `repeat <id> <n> save`: no room is left for another saved repeat; `upload begin`: the file would not fit, or the show has no room for another item; `upload begin external`: the file would not fit on the drive, or the drive has 256 animations. |
| `bad-offset` | `upload data`: the offset is not the number of bytes received so far, or the bytes would pass the size of the file. |
| `bad-file` | `upload end`: the file is not a valid ODRG file for the canvas. |
| `storage-error` | The storage could not be read or written. The show is as it was. An upload that met it is discarded. A file an earlier change could not remove is removed before a change; while that fails, the change is refused with this code, and the next start removes it. |

When more than one code applies, the reply has the first in the order of this table.

## Transports

A transport only carries lines to the command front-end and replies back. The commands and
replies are the same on every transport.

| Where | Serial | Network |
|---|---|---|
| Board | The USB serial port. | HTTP over Wi-Fi, on the board's web server. |
| Emulator | A virtual serial port on a Mac. On Windows, and on a Mac when asked, the same lines on a TCP port of 127.0.0.1. | HTTP on the emulator's page address. |

**Lines that are no reply.** On the board's serial ports, a line that begins with `#` is
no reply: the firmware writes its log there between replies, as
[firmware.md](firmware.md#the-log) describes, and the chip's loader prints lines at a
start. A reply is a line that is a JSON object with `ok`; a client passes over every
other line.

**HTTP.** A command is sent as `POST /odrig` with the command line as the request body, with
or without the final newline. The response body is the reply line, with content type
`application/json`. The response status is 200 whenever the line reached the command
front-end, including replies with `"ok":false`. Any other method on `/odrig` gets status 405.

## Mapping controls

`mapping get` reports `{ok:true,editable:true,pins:[...],revision:N,cross:false,test:false,snake:null}`.
Pins are in snake order, 1 through 20. Unsupported or invalid mappings report
`editable:false`, an empty `pins` array, revision 0 and `cross:false`. The test flag is
target-wide. Only the target's existing twenty-pin permutation is editable, its twenty
snakes of three columns each, snake 10 wired as the others or cross-wired. `cross` is
`true` when snake 10 is cross-wired.

`mapping set <revision> <pins>` accepts exactly twenty comma-separated GPIO numbers.
The revision is the decimal CRC-32 of the current twenty pin bytes in snake order.
Every current output pin must occur exactly once. A successful reply means the new
mapping is durably committed and ready for output routing. An identical assignment
performs no storage writes. Re-read after any uncertain reply.

A stale revision gives `mapping-conflict`; malformed or unsupported assignments give
`bad-argument`. Invalid shows give `show-invalid`; startup checking or an open upload
makes writes `busy`; failed or unavailable writable storage gives `storage-error`.

`mapping cross on` saves snake 10 as cross-wired, its chain running up column 28, up
column 30 and down column 29, as the installation's snake 10 is wired around a dead data
output; `mapping cross off` saves it as wired as the others, up, down, up. The pins stay
as they are, and the mapping file is rewritten as `mapping set` writes it, atomically,
with snake 10's leg as `"columns":[28,30,29],"starts":["bottom","bottom","top"]` when it
is cross-wired ([mapping.md](mapping.md)). From the next refresh the snake's LEDs show the
canvas by the new wiring; nothing else changes. The same word again is `{ok:true}` and
writes nothing. The revision is the pins' and is not changed by the wiring, which a
`mapping set` keeps. A word other than `on` or `off`, or a mapping that is not editable,
gives `bad-argument`; `show-invalid`, `busy` and `storage-error` are as for `mapping set`.

`mapping test on` displays the built-in diagonal until `mapping test off` or a valid
ordinary play command. Both test commands are idempotent. Entry requires the valid
60 x 60 target mapping and a completed startup check with no open upload. During the
test status reports no ordinary playing item or animation; `mapping get` identifies
the active test. Upload and remove return `busy`, but mapping saves, list, space,
status, power and brightness remain available. The test changes no show entry.

`mapping test snake <n>` shows the test of snake n, n from 1 to 20, until
`mapping test off` or a valid ordinary play command: one white block of 3 x 3 pixels that
runs the length of the snake's three columns, from their bottom to their top and back, one
row every 40 milliseconds, through the saved mapping, with every other LED dark; one way
up lights every LED of the snake once. While it shows,
`mapping get` reports `"test":true` and `"snake":<n>`; for the diagonal and while no test
shows, `"snake":null`. Entry, busy refusals, power, brightness and restart are as for the
diagonal. A test that starts while another one shows takes its place, and stopping it
resumes what played before the first. No test enters the playlist, `start`, a cycle or
the saved order, and none changes a file.

The protocol is identical over HTTP, board serial and emulator serial or TCP.

## Playlist inclusion and batch deletion

`ignore <id> <0|1>` persists an installed animation's automatic-playlist exclusion:
1 excludes, 0 includes. It is idempotent and returns `{"ok":true}` after durability.
`list` includes boolean `ignored` on installed animations only. Explicit play and
cycle membership still work. Unknown ids return unknown-id; cycles/drive ids in-use.

`remove many <id,id,...>` deletes 1–32 distinct installed animation items atomically
per command. Every id is validated first; unknown ids return unknown-id; cycles,
external entries and animations referenced by cycles return in-use. Duplicates and
malformed lists return bad-argument. Single `remove <id>` retains cycle deletion.
Both mutation forms return busy during an upload or the mapping test;
show-invalid and storage-error retain their meanings. Every transport forwards these
commands into the same core parser; no route has separate deletion/playback rules.

### External storage capacity

`space` retains its internal `free`, `total` and installed `animations` count, including
ignored items. Its `external` object contains boolean `present`, `read_only:true`, and
nullable `free` and `total` byte counts. Absent media reports false/null/null. Mounted
media with unknown capacity reports true/null/null. Known counters support volumes
over 4 GiB, up to 9,007,199,254,740,991 bytes. Capacity never grants write access to a drive.

## Catalogs

```
catalog
{"ok":true,"internal":{"state":"ok","generation":42,"entries":84,"uncataloged":0},"external":{"state":"absent"},"rebuild":null}
```

**`catalog`** reports the catalog of each storage, as [catalog.md](catalog.md) states it:
`internal` of the board's own storage, `external` of the drive.

- `state`: `none` (the storage has no catalog and is read as before catalogs), `ok`,
  `loading` (a drive's catalog being read), `damaged`, `incompatible` (another version of
  the format or the check), or `absent` (no drive is plugged in). A damaged one has
  `detail`: `marker`, `page`, `line` or `interrupted`.
- `generation` and `entries`: those of a catalog that is `ok` or `loading`.
- `uncataloged`: the files of the show whose size and length did not come from the
  catalog; the start opens them and the check after the start reads them, as without a
  catalog.
- `writable`: whether the core may write the drive, when one is plugged in.
- `rebuild`: `null` while no rebuild runs; during one, `{"storage":"internal","read":12,"to_read":72}`:
  the storage, the files it has read and those it has still to read.

At the start the core reads the internal catalog. Every file of the show that it has an
entry for has its size and its type in `list` at once and is neither opened nor read by the
check after the start; an entry for another canvas than the mapping's makes its file unavailable with
`size-mismatch`. A damaged or incompatible catalog is logged (`catalog internal damaged`,
`catalog internal incompatible`) and its storage is read as without one. A change of the
catalog that a cut interrupted after its commit is finished first.

**`catalog rebuild internal`** reads every file of the show whose name a catalog may hold,
page by page, with the steps of the check after the start, and writes the board's catalog
anew at the end in one commit, generation one more than the old one's, or 1: the same
files the PC tool's rebuild writes of the same files. A file that passes gets its size and
length at once; one that fails is quarantined, as by the check. The check after the start
gives way while it runs and takes up after it the files it did not read. **`catalog
rebuild external`** does the same for the drive: its places go, the folder is listed once,
and each file joins the playlist as it is read, or is left out; at the end the drive's
catalog is `ok`. Both answer `{"ok":true}` when the rebuild begins, and `catalog` shows its
progress. Refused with `bad-argument` for another word, `show-invalid`, `busy` while an
upload is open, a test shows, a rebuild runs or the drive's catalog is read, `read-only` on
a host that cannot change its storage, and for `external` without a drive the core may
write, and `storage-error` when a change that a failed call left cannot be finished first.
While a rebuild runs, every command that writes storage is `busy`. A storage call that
fails ends it, logged as `catalog rebuild failed: storage-error`, with the catalog as it
was; a drive pulled out ends it too. **`catalog cancel`** ends a rebuild: the pages it
wrote are removed, the catalog is as it was, and what the files read taught the core stays.
It is `{"ok":true}` also without a rebuild.

```
catalog page external 0 0
{"ok":true,"generation":3,"text":"1a2b3c4d 52340 60 60 12000 frames sunrise.odrg\n5e6f7a8b 1882 60 60 20000 text night/comet.odrgx\n","next":96}
```

**`catalog page <storage> <page> <offset>`** reads up to 512 bytes of a page of a storage's
catalog, `internal` for the board's own and `external` for the drive's, page `<page>`, 0
to 15, of [catalog.md](catalog.md), from `<offset>`, 0 to 4,294,967,295: a client learns
from its lines the CRC-32 and the size of each file without reading the files. `generation`
is the storage's, as `catalog` gives it. `text` holds the bytes as the inside of a JSON
string, a line's end as `\n`, a quote and a backslash after a backslash and any other byte
outside printable ASCII as `\u00XX`, as many as fit into the reply; `next` is the offset
after them. At or after the page's end, and for a page that cannot be read, as a page
without entries has no file, `text` is empty and `next` is `null`; a storage whose catalog
is not `ok`, and a drive that is not plugged in, give `"generation":null` as well. The page
is read with one `read_at` of the host into the chunk buffer, and no memory is asked for.
Refused with `bad-argument` for another form, `busy` while a rebuild of that storage runs,
and nothing else, an open upload included, and `storage-error` on a host that cannot
change its storage. A client reads a page whole from offset 0 and then from each `next`
until it is `null`; a page whose generation differs from that of the first page of the
same read was changed in between.

A drive with a catalog is `loading` from its plug-in until every page is read; its
animations then join `list` together. One without a catalog is `none` and is listed and
read as before; [show.md](show.md#animations-from-a-usb-drive) has both.

**`upload begin external <file> <bytes>`** and **`upload begin external <file> <bytes>
<crc32>`** open an upload to the drive when the core may write it: its host says the drive
can be written and the drive's catalog is `ok`. `<file>` follows the naming rule of the
show's files. The rest of the upload is as for the board's own storage: `upload data`, the
check, `upload end`. On success one commit of the drive's catalog moves the file onto its
name with its entry, and the reply gives the animation's id: `{"ok":true,"id":60003}`. A file
of that name on the drive is replaced and keeps its id, and where it plays it plays anew
from its start, as an item's file replaced under its name does; a new one gets the lowest free id
from 60,001, and its place in the saved order by its name. `busy` while an upload is open or
the drive's catalog is read, `read-only` when the core may not write the drive, `no-space`
when `drive_space` says the file does not fit or 256 animations are on the drive.

`remove <id>` of an animation of a drive the core may write removes its file and its entry
in one commit; its id is free again. Of any other drive it is `in-use`, as before. `space`
reports `"read_only":false` for a drive the core may write.

An upload, `remove` and `remove many` keep a catalog that is `ok`: an upload commits the
entry of its file, with the size, the CRC-32, the length and the type its check found (of a
text or a clock the loop its header gives), in the same
commit that puts the file in place; a removal takes the entries of the files that go out
before the show file is written. Each writes the pages of its entries, the marker and the
commit record, and no other file of the catalog. A storage without a catalog, or with one
that is not `ok`, gets none from a change.

A storage call that fails stops a change where it is. Before its commit record is whole the
change is refused with `storage-error` and the catalog is as it was; a file it was writing
is removed. After it the reply is as for success, and what is left is finished before the
next change of that storage writes anything: while that fails, the change is refused with
`storage-error`, and the upload's part that the record may move is kept. A start that cannot
finish it reads its storage as without a catalog, `damaged` with `interrupted`, and takes the
catalog up again once a later change has finished it; a drive that cannot be finished at its
plug-in is `damaged`, `interrupted`, until it is plugged in again.

## The saved playlist order

The playlist plays its included animations in the saved order, which the board keeps in
its own storage, internal and external animations in one order. An animation the saved
order does not name comes after every one it names: the internal ones in the order of
`show.json`, then the external ones in the order of their file names. An external
animation is named by its file name, so it keeps its place while its medium is absent
and takes it again when the medium is back. [show.md](show.md#the-saved-playlist-order)
has the file.

```
order get
{"ok":true,"ids":[3,60002,1],"next":null,"revision":2805384113}
```

`ids` are the ids of the animations `list` lists, the ignored ones, the unavailable ones
and the external storage's among them, in the saved order, beginning at the position `<from>`, counted
from 0, which is 0 when it is left out; `<from>` is 0 to 65,535. The reply holds as many
as fit into it, and `next` is the position of the first one left out, or `null`, as for
`list`. `revision` is a number that changes whenever the order or the listed animations
change, and is the same after a restart for the same files. `order get` is refused as
`list` is, with `show-invalid` while the show is invalid; while the player reads every
installed animation after a start it answers, as `list` does, and `order move` is refused
with `busy`.

```
order move 2805384113 1 3
{"ok":true}
```

`order move <revision> <id> <before>` moves the listed animation with the id `<id>`, of the
board's own storage or of the external storage, to stand right before the listed animation
with the id `<before>`, or last when `<before>` is the word `end`. `<revision>` is the
`revision` of `order get` the client read, 0 to 4,294,967,295; `<id>` and `<before>` are 1
to 65,535. The reply `{"ok":true}` comes once the whole order is saved; a power cut leaves
the order before the move or the one after it. A move that changes nothing, of an
animation that already stands right before `<before>`, or last for `end`, or before
itself, writes nothing.

- `bad-argument`: the words are not in their form.
- `show-invalid`: the show is invalid.
- `busy`: until the player has read every installed animation after a start, and while
  an upload is open.
- `unknown-id`: `<id>` or `<before>` is the id of no listed animation, of no cycle and of
  no folder of the card.
- `in-use`: `<id>` or `<before>` is the id of a cycle or of a folder of the card, which
  have no place in the order.
- `order-conflict`: `<revision>` is not the order's revision now. Nothing changes; read
  `order get` again.
- `storage-error`: the order could not be saved. It is as it was.

A move does not change the animation whose turn it is, its time, the brightness or
whether the LEDs are on; the next turn follows the new order. It works while a test of
the mapping shows. Every route carries it to the one command parser of the core.

## Repeating the turn in progress

```
repeat 1 8
{"ok":true}
```

`repeat <id> <n>` makes the playlist's turn in progress of the animation `<id>` `<n>` loops
long, counted from the turn's first frame, as `repeat` of [show.md](show.md) counts them.
`<id>` is the id `status` names as `animation`, 1 to 65,535; `<n>` is 1 to 65,535. Nothing
restarts: the frame on the LEDs, the turn's time and a clock's seed go on. When `<n>` is at
or below the loop in progress, the turn ends at the end of that loop, never in the middle
of one: the core keeps the larger of the two, which `status` then reports as `repeat` and
which may be above 65,535. The animation's `max_seconds` does not cut a turn so set. A text
counts its passes and a clock the loops of its `seconds`; an animation of a drive or a card
is taken as an item is; after `play <id>` it acts on the turn that `play` began. While the
length of the loop is not known yet, the turn is in its first loop.

The count holds for that turn alone and is kept in memory only: it is dropped at the
turn's end and by every new turn, whether by `play`, `play all`, a folder's `play`, an
upload that changes or adds the animation of the turn, the quarantine of its file, its
removal, `ignore`, a drive or a card pulled out, a test of the mapping or a restart. `order
move`, `on`, `off` and `brightness` keep it; while the LEDs are off or dark the loops run on.
A folder's window that ends during such a turn waits for the turn's end, with `left` at 0.

- `bad-argument`: the words are not in their form.
- `show-invalid`: the show is invalid.
- `stale`: no turn of `<id>` is reported, as `status` says it: a cycle plays, nothing
  plays, a test of the mapping shows, the turn has not had its first refresh, or it has
  moved on to another animation.

```
repeat 1 5 save
{"ok":true}
repeat 1 default
{"ok":true}
```

`repeat <id> <n> save` keeps `<n>` loops as the saved repeat of the animation `<id>`, for
every later turn of it, across a restart, and gives them to its turn in progress, when one
is reported, as `repeat <id> <n>` does. `repeat <id> default` removes the saved repeat: the
animation's turns play its own count again, and its turn in progress, when one is reported,
drops its own value and plays its own count, or ends with the loop in progress when that
count has already passed; while the length of its loop is not known the turn's own value is
merely dropped. Both are about the animation and not the turn: they work for every
animation `list` lists, an unavailable one and one of a drive or a card included, while a
test of the mapping shows too, and are never `stale`. A saved repeat is kept by the file's
name in `repeats.txt` of the board's own storage, see
[show.md](show.md#the-saved-repeats); the reply comes once the whole file is saved, and a
power cut leaves the file before the change or the one after it. Saving the value already
saved, and restoring an animation that has none, write nothing and still act on its turn.

- `bad-argument`: the words are not one of the three forms, or a number is out of range.
- `show-invalid`: the show is invalid.
- `busy`: while a rebuild of a catalog runs, until the player has read every installed
  animation after a start, and while an upload is open.
- `unknown-id`: `<id>` is the id of no animation `list` lists, of no cycle and of no folder
  of the card.
- `in-use`: `<id>` is the id of a cycle or of a folder of the card, which keep no repeat.
- `no-space`, for a save only: the drive's files would have more than 32 saved repeats, or
  the file holds 512 lines of other animations once the lines of files `show.json` no
  longer names are dropped, which a save does whenever it finds the file full.
- `storage-error`: the file could not be read or written, or the board's storage cannot be
  changed. Nothing changes. A file out of form is no failure: a save writes it anew.
