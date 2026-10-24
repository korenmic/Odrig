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
| `play <id>` | Plays the animation with that id, from its first frame, and then goes on with the playlist; plays the cycle with that id. An unavailable animation is refused. |
| `play all` | Plays the playlist, from its first animation. |
| `on` | Switches the LEDs on. |
| `off` | Switches the LEDs off: every LED is dark. Playback time keeps running. |
| `brightness <n>` | Sets brightness, 0 to 255. |
| `status` | Reports the current state. |
| `space` | Reports the free and the total storage and the number of animations. |
| `list`, `list <from>` | Lists the items of the show, and the animations of a USB drive. |
| `remove <id>` | Removes an item from the show. |
| `remove many <ids>` | Atomically removes 1–32 distinct installed animations. |
| `ignore <id> <value>` | Excludes or includes an installed animation in the automatic playlist. |
| `mapping get` | Reports saved pin assignments, their revision and diagnostic state. |
| `mapping set <revision> <pins>` | Atomically saves a complete comma-separated pin permutation. |
| `mapping test on` | Shows the built-in diagonal until stopped. |
| `mapping test off` | Stops the diagonal and resumes the show. |
| `upload begin <id> <file> <bytes>` | Opens an upload of an animation. |
| `upload data <offset> <base64>` | Adds a piece of the file to the open upload. |
| `upload end <crc32>` | Closes the upload and installs the animation. |
| `upload cancel` | Discards the open upload. |

At power-on the LEDs are on, brightness is the value in `show.json`, and the show plays
what [show.md](show.md) says it plays by itself: the playlist of its included animations, or
the cycle its `start` names. What `play`, `on`, `off` and `brightness` change is not kept
across a restart. What `remove` and `upload` change is: they change the installed show.

Brightness scales every colour value v to `(v * brightness + 127) / 255`, rounded down.

A number in a command is written in decimal digits.

## Status reply

```json
{"ok":true,"on":true,"brightness":128,"playing":3,"animation":1,"fps":50,"error":null,"width":60,"height":6}
```

| Member | Meaning |
|---|---|
| `on` | Whether the LEDs are switched on. |
| `brightness` | Current brightness, 0 to 255. |
| `playing` | What is being played: `"all"` for the playlist, the id of a cycle, or `null`. |
| `animation` | The id of the animation item, or of the drive's animation, on the LEDs right now, or `null`. |
| `fps` | LED refreshes in the last full second. |
| `error` | `null`, or the reason the show is invalid. |
| `width`, `height` | The canvas of the installed mapping, in pixels: what an animation for this target is made for. Both `null` while there is no mapping the player can use; reported also while the show is invalid for another reason. |

## Storage and the installed items

```
space
{"ok":true,"free":11517952,"total":13500416,"animations":2,"external":{"present":false,"free":null,"total":null,"read_only":true}}
```

`free` and `total` are bytes of the storage the show is in. `animations` is the number of
animation items of the show, unavailable ones among them, and 0 while the show is invalid.

```
list
{"ok":true,"items":[{"id":1,"file":"hello.odrg","bytes":1138,"ignored":false},{"id":2,"file":"dvd.odrg","bytes":1612,"ignored":false},{"id":3,"cycle":[1,2],"seconds":15}],"next":null}
```

The items come in the order of `show.json`, beginning at the position `<from>`, counted
from 0, which is 0 when it is left out. `<from>` is 0 to 65,535. An animation item has its
`id`, its `file` and the size of that file in `bytes`. A cycle has its `id`, the ids of its
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

The animations of a USB drive come after the items of the show, in the order of their
file names, each as an animation item: `{"id":60001,"file":"sunrise.odrg","bytes":52340,"ignored":false}`.
Their ids are from 60001 up, the lowest that the show does not use, and `file` is the
name on the drive, cut to 127 bytes, with `"` and `\` after a backslash and every
character outside printable ASCII as `\u` and four hexadecimal digits. The positions of
`<from>` and `next` count both kinds. An animation of the drive is listed once the player
has read it whole; while the drive is read, `list` answers without the ones still to be
read, and is not refused with `busy` for them. [show.md](show.md#animations-from-a-usb-drive)
says what the board does with a drive.

After a start the show plays at once, and the player reads every installed animation to
its end while it plays. Until it has read a file whole it does not know its size: `list`
gives its `bytes` as `null` until then. `list`, `remove`, `remove many`, `ignore` and
`upload` are answered from the start, as `status` and `space` are.

## Removing an item

```
remove 2
{"ok":true}
```

The item leaves the show, and the items after it move up.

- An animation that a cycle lists is refused with `in-use`: remove the cycle first.
- An animation of a USB drive is refused with `in-use`: the drive holds it.
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
  cycle or to an animation of a USB drive, or another item already names `<file>`; and with `no-space` when the file would
  not fit into the free storage, or the show has no room for another item.

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
| `show-invalid` | `play`, `list`, `remove` or an `upload` command was sent while the show is invalid: its mapping file or show file cannot be used, or its ids are wrong. A fault of one animation file does not make it invalid. |
| `no-upload` | `upload data`, `upload end` or `upload cancel` was sent while no upload is open. |
| `incomplete` | `upload end` came before all bytes. |
| `bad-checksum` | `upload end` names another CRC-32 than the bytes received have. |
| `busy` | `upload begin` or `remove` while an upload is open; `upload end` while the file is being checked. |
| `unknown-id` | `play` or `remove` names an id that is neither in `show.json` nor of an animation of a USB drive; `play all` was sent while the playlist has no animation. |
| `unavailable` | `play` names an animation that is unavailable in this boot, as its file had a fault, or a cycle that lists only such. |
| `in-use` | `remove` names an animation that a cycle lists, or one of a USB drive; `upload begin` names the id of a cycle or of an animation of a USB drive, or a file name another item has. |
| `mapping-conflict` | The mapping changed since the client read its revision; reload before saving. |
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

`mapping get` reports `{ok:true,editable:true,pins:[...],revision:N,test:false}`.
Pins are in snake order, 1 through 20. Unsupported or invalid mappings report
`editable:false`, an empty `pins` array and revision 0. The test flag is target-wide.
Only the target's existing twenty-pin permutation is editable.

`mapping set <revision> <pins>` accepts exactly twenty comma-separated GPIO numbers.
The revision is the decimal CRC-32 of the current twenty pin bytes in snake order.
Every current output pin must occur exactly once. A successful reply means the new
mapping is durably committed and ready for output routing. An identical assignment
performs no storage writes. Re-read after any uncertain reply.

A stale revision gives `mapping-conflict`; malformed or unsupported assignments give
`bad-argument`. Invalid shows give `show-invalid`; startup checking or an open upload
makes writes `busy`; failed or unavailable writable storage gives `storage-error`.

`mapping test on` displays the built-in diagonal until `mapping test off` or a valid
ordinary play command. Both test commands are idempotent. Entry requires the valid
60 x 60 target mapping and a completed startup check with no open upload. During the
test status reports no ordinary playing item or animation; `mapping get` identifies
the active test. Upload and remove return `busy`, but mapping saves, list, space,
status, power and brightness remain available. The test changes no show entry.

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
