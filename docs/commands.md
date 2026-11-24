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
| `play <id>` | Plays the animation with that id, from its first frame, and then goes on with the playlist; plays the cycle with that id; makes the playlist of the folder of the board's own storage or of the card with that id current and plays its first animation. An unavailable animation is refused. |
| `play all` | Plays the playlist, from its first animation, and makes the root playlist current. |
| `on` | Manually switches the LEDs on and saves an override of scheduling. |
| `off` | Manually blacks out the LEDs and saves an override; playback keeps running. |
| `brightness <n>` | Sets the runtime default brightness, 0 to 255. |
| `brightness <id> <n> save` | Saves brightness for the listed animation's file, including zero, without changing the default. |
| `brightness <id> default` | Removes that file's saved brightness, using the latest default immediately if it is playing. |
| `status` | Reports the current state. |
| `schedule` | Reads daily times, enablement and manual override. |
| `schedule set <revision> <on-HH:MM> <off-HH:MM> <on-or-off>` | Atomically saves the daily pair and enablement. |
| `schedule resume <revision>` | Releases manual control back to the saved schedule. |
| `time` | Reads the boot-local civil clock and accepted phone zone. |
| `time zone <base64>` | Atomically installs a complete phone-zone snapshot. |
| `time set <utc-seconds> <zone-crc32>` | Sets the clock against the accepted zone revision. |
| `guard <board-id> <timing-command>` | Executes a time or schedule command only on the named board. |
| `rotation` | Reports saved square output orientation and its revision. |
| `rotation set <revision> <degrees>` | Atomically saves 0, 90, 180 or 270 clockwise degrees. |
| `fault` | Reports the latest fault of a file since the start. |
| `space` | Reports the free and the total storage and the number of animations. |
| `list`, `list <from>` | Lists the items of the show at the root, the playlists of the folders of the board's own storage, and the root's level of a USB drive or a card: the playlists of its folders and its own animations. |
| `list in <folder-id>`, `list in <folder-id> <from>` | Lists one level of the board's own storage or of the card: the playlists of a folder's sub-folders and its own animations. |
| `read <id> <offset>`, `read <id> <offset> <count>` | Reads up to 600 bytes of the file of an animation back, or up to `<count>`, 1 to 720. |
| `catalog` | Reports the catalog of the board's own storage and of the drive. |
| `catalog page <storage> <page> <offset>` | Reads up to 512 bytes of a page of the catalog of the board's own storage, `internal`, or of the drive, `external`. |
| `catalog rebuild <storage>` | Reads every animation of the board's own storage, `internal`, or of the drive, `external`, and writes its catalog anew. |
| `catalog cancel` | Ends a rebuild; the catalog stays as it was. |
| `remove <id>` | Removes an item from the show. |
| `remove many <ids>` | Atomically removes 1–32 distinct installed animations. |
| `ignore <id> <value>` | Excludes or includes an animation, a folder of the board's own storage or an external folder in automatic playback. |
| `mapping get` | Reports saved pin assignments, their revision and diagnostic state. |
| `mapping set <revision> <pins>` | Atomically saves a complete comma-separated pin permutation. |
| `mapping test on` | Shows the built-in diagonal until stopped. |
| `mapping test off` | Stops the diagonal and resumes the show. |
| `mapping test snake <n>` | Shows the test of snake n, 1 to 20, until stopped. |
| `order get`, `order get <from>` | Reports the ids of the root level's animations in the saved playlist order. |
| `order get in <folder-id>`, `order get in <folder-id> <from>` | Reports the ids of a folder's animations in the saved playlist order. |
| `order move <revision> <id> <before>` | Moves one animation before another, or to the `end`, in the saved order. |
| `repeat <id> <n>` | Makes the playlist's turn in progress of that animation `n` loops long, for that turn alone. |
| `repeat <id> <n> save` | Keeps `n` loops as the animation's saved repeat, for every later turn, and gives them to its turn in progress. |
| `repeat <id> default` | Removes the animation's saved repeat: its turns play its own count again, the one in progress too. |
| `saved <id>` | Reports the saved brightness and the saved repeat of an animation, and whether it is the show's start. |
| `clocks on` | Switches the clocks between the animations on, and saves it. |
| `clocks off` | Switches them off, and saves it. |
| `clocks only` | Plays only the resolved Clocks subtrees of the card and of the board's own storage, and saves the mode. |
| `clocks message on` | Switches the message after each clock on, and saves it. |
| `clocks message off` | Switches it off, and saves it. |
| `clocks storage sd` | Plays the card's copy of a clock or a message that both storages hold, and saves the choice. |
| `clocks storage internal` | Plays the board's own copy of it, and saves the choice. |
| `upload begin <id> <file> <bytes>` | Opens an upload of an animation, `<file>` its name or the path of a folder of the board's own storage and its name; with the file's CRC-32 after `<bytes>`, answers `unchanged` when the last upload installed that file. |
| `upload begin external <file> <bytes>` | Opens an upload of an animation to the drive, when the core may write it. |
| `upload data <offset> <base64>` | Adds a piece of the file to the open upload. |
| `upload expect <crc32>` | Lets the open upload replace its item's file only while that file is the one the client read. |
| `upload end <crc32>` | Closes the upload and installs the animation. |
| `upload cancel` | Discards the open upload. |
| `folder make internal <path>` | Makes a folder of the board's own storage, listed while it is empty. |
| `folder make external <path>` | Makes a folder of the card, listed while it is empty. |
| `folder remove <id>` | Removes an empty folder of the board's own storage or of the card. |
| `move external <id> <path>` | Moves a file of the card into another of its folders, with its id and its saved settings. |
| `move internal <folder-id> <path>` | Moves or renames a folder of the board's own storage, its sub-folders with it, every id and setting kept. |
| `debug mini on` | Requests temporary miniature output; status reports host acknowledgement. |
| `debug mini off` | Requests restoration of normal output. |

At power-on brightness comes from `show.json` and the show plays what
[show.md](show.md) specifies. The LEDs start on unless a saved manual override says
otherwise. Scheduling waits for valid civil time after every reset. Manual `on` and
`off` persist until explicit `schedule resume`; they never expire at a boundary.
Ordinary `brightness <n>` and a `play` of an animation or cycle are not kept across a
restart. The current playlist, a folder of the board's own storage or of the card, or
the root, and its spent window are kept as [show.md](show.md#the-playlist) describes.
`remove` and `upload` change the installed show.

Brightness scales every colour value v to `(v * selected + 127) / 255`, rounded down,
where selected is the file's saved override or the runtime default. Overrides replace
the default; they do not multiply it. A nonzero override still shows when the default
is zero. Power off always makes every LED black. Miniature output then caps the
selected value at 40; WLED's existing current limiter remains in force.

A number in a command is written in decimal digits.

## Daily schedule and manual control

`schedule` reports `ok`, boolean `enabled`, On/Off as HH:MM strings `on`/`off`,
nullable `override` (on/off), CRC-32 `revision`, effective boolean `power`, boolean
`active`, nullable `reason`, boolean `saved` and nullable `error`. Defaults are
enabled, On 18:00, Off 06:00 and no override. An overnight On window includes18:00
and excludes06:00; same-day windows use the same half-open rule. Clock/zone
corrections evaluate the resulting current window without replaying missed edges.

`schedule set REV ON OFF on|off` validates and atomically saves the complete pair
and enablement against the read revision. Equal times, malformed HH:MM and values
outside00:00..23:59 are bad-argument. `schedule resume REV` clears only the manual
override and immediately evaluates an enabled schedule with valid time. Wrong
revisions are stale. Disabled scheduling keeps its pair and manual mode.

The canonical ASCII/LF `schedule.txt` is a header `odrig-schedule 1`, then one line
`ENABLED ON_MINUTE OFF_MINUTE MODE`, then EOF. Enabled is0/1, minutes0..1439 and mode
0 auto/1 on/2 off. Decimal tokens have no leading zeros. Missing means the defaults;
its reported revision is the canonical defaults CRC without creating the file.
Changed settings write `schedule.part`, close durably, verify every byte, and rename
atomically. Unchanged settings write nothing. No tick/boundary/time sync writes it.
Corrupt settings disable scheduling and report settings-unreadable; ordinary edits
do not silently repair them. Restore a known-good file deliberately before editing.

Manual `on`/`off` always immediately controls LED visibility and overrides scheduling,
across boundaries, clock changes, reconnections, and reset after a successful save.
Time-pair edits and auto-sync do not release it. If persistence fails, the immediate
manual effect remains and the reply reports storage-error (or busy for a conflicting
upload/rebuild). Read `schedule`: saved:false and manual-not-saved identify a volatile
override; a corrupt file instead reports settings-unreadable. Hosts without write
callbacks still accept ordinary volatile manual control. An off installation remains
reachable and its playback keeps progressing; scheduled On never restarts it or
resets brightness. Unset/invalid time bypasses automatic scheduling.

## Board time

`guard BOARD COMMAND` accepts only the complete `time` and `schedule` forms below.
It checks the physical identity under the same core call before executing the inner
command: a different board returns `stale` without applying it; no usable identity
returns `unsupported`. IDs are complete 1..31 ASCII letters/digits/hyphen/underscore,
never addresses or truncated names. Malformed wrappers yield `bad-argument`. This
protects queued writes when different boards use the same Wi-Fi address. It is a
target check, not authentication. A largest zone plus a 31-byte ID fits2048 bytes.
The board reports its factory MAC as an opaque ID; the emulator hashes the resolved
storage root, retaining the same ID across restarts and ports.

`time` reports `ok`, `valid`, nullable UTC seconds `utc`, nullable IANA `zone`,
nullable offset seconds `offset`, nullable eight-digit lowercase CRC-32 `revision`,
zone coverage `from`/`until`, nullable stable `board` identity, and nullable `error`. Time is invalid after every core
restart until a successful set, even when rules survive. Missing rules have null
metadata; damaged rules report `zone-unreadable`. Reads work during show recovery.

`time zone DATA` takes URL-safe unpadded base64 of the complete bounded snapshot
format in [the design](specs/64-p2-board-time-and-daily-on-off-schedule/design.md#a-compact-complete-zone-snapshot).
It is at most1500 decoded bytes: a120-byte header and up to276 five-byte UTC/offset
index transitions. Rules cover a range inside[946684800,4102444800), carry up to8
distinct signed offsets in seconds and a63-character IANA name, and must be exact,
strictly ordered and canonical. They live in `timezone.bin`. Publication writes
`timezone.part`, closes it durably, verifies its exact bytes and atomically renames
it. An unchanged revision writes nothing. A failed update keeps prior accepted
rules. Abandoned parts never supply rules on startup.

`time set UTC REVISION` takes decimal UTC seconds from946684800 through4102444799
and the zone's confirmed lowercase CRC. It writes no flash and affects neither
playback time nor animation clocks. The rules must cover the given UTC. Time then
advances offline from monotonic elapsed milliseconds, including zone transitions;
no Internet, phone or NTP is needed. Range expiry is invalid time, never a wrap.

Success replies are `{"ok":true}`; read `time` afterwards to confirm. Invalid forms,
ranges, schema or encoding are `bad-argument`; a wrong revision is `stale`; no usable
zone is `zone-unset`; unavailable write callbacks are `unsupported`; an active
upload/rebuild is `busy`; failed storage or verification is `storage-error`. These
operations share the same dispatch for existing serial, HTTP and native hosts.

## Saved animation brightness

`brightness ID VALUE save` durably saves 0..255 for the listed animation's file;
`brightness ID default` removes it. Both work for a noncurrent animation too.
Cycles and folders are `in-use`, an unlisted ID is `unknown-id`, checking/upload
conflicts are `busy`, a failed settings operation is `storage-error`, and a full
settings file is `no-space`. Malformed forms/ranges are `bad-argument`.
An unchanged save writes nothing. A successful reply means the complete setting
was verified and published; clients then read fresh `status` to confirm it.

Identity is the internal filename or the full external path, in separate namespaces,
as for saved repeats. Internal items naming the same file share its value. The same
external path on a replacement card inherits its value. Replacement/restoration at
the same path retains it; a rename is a different identity. Deleted, absent and
unlisted paths are retained indefinitely, with no eviction. Settings stay on the
board's internal storage even when the animation is on read-only media.

`brightness.txt` uses LF line endings, this header and records:

```
odrig-brightness 1
0 f hello.odrg
27 x night/comet.odrg
```

There may be 512 records total and at most 32 external records, including retained
absent paths. First matching record wins. Changing/removing an existing entry works
at capacity; adding another is refused. The tool's ordinary install preserves this
file, an explicit copy replaces it, and read-show includes it. Neither animation
bytes nor show/catalog bytes or generations change for a brightness edit.

Publication writes `brightness.part`, closes it durably, verifies its complete
grammar/bytes/CRC and atomically renames it. Failed operations retain the last
usable published setting. Startup ignores an abandoned part. A missing file means
defaults; corrupt/truncated/over-limit settings log `brightness unreadable`, use
defaults and report `dimming.error:"settings-unreadable"`. Saves are then refused
with `storage-error` until a deliberate repair/replacement. Restore a known-good
file, or deliberately reset all overrides to the header alone; ordinary brightness
commands do not repair or erase settings. Preserve a copy before such maintenance.

`status.brightness` always reports the runtime default. `dimming.value` reports
the selected value before blackout/mini cap and `dimming.saved` is null or the
override, including zero. They refer to the same animation/file as status. Off is
still unconditionally black; returning from a clock/message selects the resumed
file's override or latest default without restarting its timing. Missing/null
`dimming` means no override support, and ordinary default commands remain usable.

## Status reply

```json
{"ok":true,"on":true,"brightness":128,"dimming":{"value":128,"saved":null,"error":null},"mini":{"supported":false,"on":false,"pending":false,"requested":false,"error":null,"brightness":40},"playing":3,"animation":1,"fps":50,"error":null,"width":60,"height":6,"timing":true,"readiness":"ready","checked":2,"to_check":0,"unavailable":0,"checking":null,"host":null,"seed":null,"repeat":null,"loop":null,"saved":null,"file":"hello.odrg","playlist":null,"clocks":false,"clock_message":false,"clock_mode":"off","clock_storage":"sd","clock_only":null,"left":86399}
```

| Member | Meaning |
|---|---|
| `timing` | True when board-time commands are supported; absent on older firmware. |
| `on` | Whether the LEDs are switched on. |
| `brightness` | Runtime default brightness, 0 to 255, initialized from the show. An animation override does not change this value. |
| `dimming` | Selected animation brightness before blackout/mini cap as `value`, nullable saved override as `saved` (zero is valid), and nullable settings `error`. `null` when persistence is unsupported; absent in older firmware. A damaged settings file reports `settings-unreadable`. |
| `playing` | What is being played: `"all"` for the root playlist, the id of the folder of the board's own storage whose playlist is current, the id of the card's folder whose playlist is current while the card is in and holds it, the id of a cycle, or `null`. |
| `animation` | The id of the animation item, or of the drive's animation, on the LEDs right now, or `null`. |
| `fps` | LED refreshes in the last full second. |
| `error` | `null`, or the reason the show is invalid. |
| `width`, `height` | The canvas of the installed mapping, in pixels: what an animation for this target is made for. Both `null` while the mapping file cannot be used; reported also while the show is invalid for another reason. A target without a mapping file plays on the installation's mapping and reports 60 and 60. |
| `readiness` | `checking` while the player still reads files after a start, while a rebuild reads them and while a drive's catalog is read, `degraded` when it has read them all and one or more animations are unavailable, `ready` when it has read them all and none is, and `recovery` while the show is invalid. What plays is said by `playing` and `animation`, whatever the readiness. |
| `checked` | The files the player has read to their end, or found a fault in, since its start: those of the show, each once however many items name it, and those of a drive. While a rebuild runs, the files it has read. |
| `to_check` | The files it has still to read, or that a rebuild has still to read. No time is given for them. |
| `unavailable` | The animations unavailable now: the show's whose file had a fault, and the drive's files left out. |
| `checking` | The name of the file the player reads now, or that a rebuild reads, a file of a folder of the board's own storage by its path, `shows/night/stars.odrg`, each cut to its first 32 characters as a drive's names are; `catalog` while a drive's catalog is read; or `null`. |
| `host` | The name the board or the emulator gives itself: on the board its build, its storage, the external memory it found and the internal memory free when the core started, and the reason of its last start, at most 127 characters; `null` when it gives none. |
| `seed` | The seed of the clock on the LEDs, 1 to 4,294,967,295: the number its turn chose when it began, from which [format.md](format.md), "The widget payload", draws every picture of the turn. `null` while the animation whose turn it is is no clock, while nothing plays, and from a `play` until the next refresh. A reply without `seed` comes from a player before it. |
| `repeat` | The loops of the playlist's turn in progress, while it is reported: the `n` of `repeat <id> <n>`, else the count the show gives the animation, a loop cut by its `max_seconds` counting as one; at most 65,535,000. `null` while no turn is reported, and while the length of its loop is not known yet and no `repeat` gave it a count. A turn is reported while the show is valid, no test of the mapping shows, the playlist plays, `animation` names the animation whose turn it is, and the turn's first refresh was made. |
| `loop` | The loop in progress of that turn, from 1, at most `repeat`; 1 while the length of its loop is not known yet; `null` while no turn is reported. A loop is a file's frames once, a text's pass, or a clock's `seconds`. |
| `saved` | The saved repeat of the animation whose turn is reported, 1 to 65,535, or `null` when it has none or no turn is reported. A reply without `repeat`, `loop` and `saved` comes from a player before them. |
| `file` | The name of the file of the animation `animation` names: an item's file, a file of a folder of the board's own storage by its path, `shows/night/stars.odrg`, or a drive's file by its path from the card's folder `odrig`, `night/comet.odrg`; `null` while `animation` is. So a client names what plays without the list that holds it. A reply without `file` comes from a player before it. |
| `playlist` | The path of the folder of the board's own storage or of the card's folder whose playlist is current while `playing` is its id, `night/deep`; `null` otherwise. |
| `clocks`, `clock_message` | Compatibility booleans: `clocks` is true in either enabled mode, and `clock_message` enables the message after a clock. A reply without them comes from a player before them. |
| `clock_mode` | `off`, `between`, or `only`. Older targets without this member support the existing boolean Off/Between interface. |
| `clock_storage` | The storage whose copy plays when a clock or a message is on both storages, as `clocks storage` chose it: `sd`, the card's, or `internal`, the board's own; `sd` while the saved settings are unreadable. It is reported in every mode. A reply without it comes from a player before it, which plays only the card's clocks and messages. |
| `clock_only` | `null` outside Only; otherwise `{"folder":ID_OR_NULL,"state":STATE}`, with state `playing`, `no-card`, `missing-folder`, or `no-clocks`. The folder is the card's folder `clocks` when the card has one, else the board's own, resolved from the active tree/catalog or `folders.txt`, never remembered by transient ID. Without a folder `clocks` of the board's own storage the state is `no-card` without a card, else `missing-folder` without the card's, else `no-clocks` while nothing plays, else `playing`; with one, `playing` while a turn plays, else `no-clocks`. In Only, `playing` names that folder and `playlist` is `clocks` while a turn plays; `file` gives a file of the board's own storage by its path, `clocks/message/v7-the-time.odrgx`, and `animation` its id. The path is the same on both storages. A folder's id tells its storage, 60,000 or less for the board's own and 60,001 or more for the card's, and so does an animation's id of 60,000 or less, the board's own; but an animation of the show may have any id from 1 to 65,535, so a client tells the storage of an animation by its row, `external`, in `list in` of the folders `clocks` and `clocks/message` of each storage. |
| `clock_error` | Optional `unreadable` when saved policy cannot be established. The effective mode is fail-closed Only, output is dark and the saved mode is unconfirmed. Omitted when confirmed. The board retries at most once a second; an explicit clock-mode save can replace corrupt settings. A message-only or storage-only change cannot guess the lost policy and is refused with `storage-error`. |
| `left` | The whole seconds left in the window of the current playlist, 86,400 down to 0: the 24 hours of running time it plays for before the next playlist is current, a folder's of the board's own storage or of the card, or the root's, see [show.md](show.md#the-playlist). 0 from the window's end until the turn in progress ends. Reported whatever the card holds, a fresh 86,400 each time a playlist becomes current. A reply without `left` comes from a player before it. |

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
from 0, which is 0 when it is left out. `<from>` is 0 to 4,294,967,295. An animation item has its
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

The drive is listed one level at a time. `list` gives the root's level after the items of
the show and the folders of the board's own storage, below: the playlists of the folders
right in the card's folder `odrig`, then the files of `odrig` itself, each as an animation
item: `{"id":60001,"file":"sunrise.odrg","bytes":52340,"external":true,"type":"frames"}`.
`list in <folder-id>` and `list in <folder-id> <from>` give the level of the card's folder
with that id: the playlists of its sub-folders, then its own files, from the position
`<from>` of that level, with `next` as `list` has it. A file in a sub-folder has its path
from `odrig` as its `file`, and a folder's playlist item its path and `files`, the number
of its own files that `list in` of it gives:

```
list in 60007
{"ok":true,"items":[{"id":60008,"playlist":"night/deep","external":true,"files":1},{"id":60004,"file":"night/comet.odrg","bytes":52340,"external":true,"type":"frames"}],"next":null}
```

A folder's id comes after the files', from the same pool, in the tree's order, depth
first. `list in` is refused with `bad-argument` for another form, `show-invalid` while the
show is invalid, and `unknown-id` for an id that is no folder of the card or of the board's
own storage, a folder of the card while the card is out too; [folders of the board's own
storage](#folders-of-the-boards-own-storage) says how theirs are listed.
[show.md](show.md#animations-from-a-usb-drive) says what a folder of the card is to the
player.
A file left out for a fault is listed in its place as
`{"id":60002,"file":"broken.odrg","bytes":null,"external":true,"type":"frames","fault":"truncated"}`, and `play` of it is
refused with `unavailable`. Their ids are from 60001 up, the lowest that the show does not
use, given when the drive is taken up and before the files are read, and `file` is the
name on the drive, cut to 127 bytes, with `"` and `\` after a backslash and every
character outside printable ASCII as `\u` and four hexadecimal digits, and so is
`playlist`. The positions of `<from>` and `next` count the kinds of the level. An animation of the drive is listed once the player
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
read 2 0 4
{"ok":true,"bytes":40,"data":"T0RSWA"}
```

`read <id> <offset>` gives up to 600 bytes of the file of an animation, of the show or of
a USB drive, from `<offset>`, so that a text or a clock can be read back and edited.
`read <id> <offset> <count>` gives up to `<count>` bytes, so that a whole file is read
back, for a download or a backup, in fewer replies. `bytes` is the size of the file, and
`data` its bytes from the offset in base64 as `upload data` takes it; at the end of the
file it is empty. `<id>` is 1 to 65,535 and `<offset>` 0 to 4,294,967,295, both in decimal
digits; `<count>` is 1 to 720, in decimal digits too. 720 bytes are 960 characters of
base64, and with a size of ten digits they make a reply of 1,001 bytes: the 1,024 bytes of
a reply would hold 737 at most. The form with a count was added under the owner's approval
of 2026-11-06. An installation from before it refuses the four words with `bad-argument`;
a client sends `read <id> 0 1` once to find out, and reads such an installation with the
form without a count.

- An offset above the size of the file, and a count of 0 or above 720, are refused with
  `bad-argument`.
- An id that is no animation of the show or of the drive, a cycle's too, is refused with
  `unknown-id`; a folder of the board's own storage or of the card, which is a playlist,
  with `in-use`.
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
- A folder of the board's own storage or of the card is refused with `in-use`: it is a
  playlist, not a file.
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
  cycle, to an animation of a USB drive or to a folder of the board's own storage or of the card, or another item already names `<file>`; and with `no-space` when the file would
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
  again. The check decodes the whole file while the show goes on playing, at each LED
  refresh as much as a budget of the work of decoding allows, at most 2,048 bytes of the
  file's body and one frame more, less on a board whose refresh rate falls; a file of
  large frames, such as dense 60 x 60 ones, averages up to about 2.6 times the budget. So
  the 14,399 small frames of a clock are checked in about 8 s on a board that refreshes
  50 times a second, and a file takes longer on a slower board and the larger its body.
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

### External folder destinations and guarded creation

A CRC-bearing internal begin that opens a transaction includes `replacing:false`
for an unused id, `replacing:true` for an existing item, beside `chunk`. A new-file
client requires false and otherwise cancels before any data; this closes the race
between listing free ids and begin. A new CRC-bearing internal upload also refuses
`in-use` when its physical filename exists outside the show. The five-argument
internal form and the
idempotent `unchanged` reply retain their behavior. No command spelling is added.

The existing `upload begin external <file> <bytes> [<crc32>]` also accepts the
full canonical path of a file in an existing indexed folder. Its basename keeps
the internal32-byte naming rule; its folders and full path obey the catalog's
100-byte/three-level limits. URI-encode spaces and percent signs in that argument
(for example `space%20room/new.odrg`); the core decodes once, then validates the
entire path. Absolute paths, traversal, bad escapes and unsafe components are
`bad-argument`; a missing indexed folder is `unknown-id`. No folder is created.

For a new external file, follow begin with `upload expect 00000000` before data.
This requires an absent catalog and physical destination, checks it again just
before publication, and discards the upload with `stale` on collision. External
nonzero expectations and an expectation after data are `bad-argument`. Existing
explicit external uploads without the absence guard retain replacement behavior;
existing internal edit expectations keep their CRC semantics. Card removal ends
the external transaction; later data/end answer `no-upload`, including after
reinsertion. A new manual attempt is needed and never continues in other storage.

### Making a folder of the card

```
folder make external clocks
{"ok":true,"id":60009,"made":true}
folder make external clocks/message
{"ok":true,"id":60010,"made":true}
```

`folder make external <path>` makes the folder `<path>` in the card's folder `odrig` and
adds it to the card's index in one commit of its catalog, so that `list` and `list in`
show it at once with `files` 0 while it is empty, and after a restart or a replug. The
path is written as `upload begin external` writes one: decoded once from URI escapes, one
to three folder names joined by `/`, each under the card's naming rule, and short enough
that `<path>/a.odrg` is a name the catalog takes; a last name ending in `.odrg` or
`.odrgx`, in any case, is `bad-argument`. Folders are made one level at a time: the parent
is the root or a folder of the index, and a missing one is `unknown-id`. The new folder
takes its place among its parent's sub-folders by the bytes of their names, as a rebuild
orders them, and the lowest id the index does not hold.

- A folder the index already has at that path answers `{"ok":true,"id":<id>,"made":false}`
  and writes nothing, so that a client may send the line again after a lost reply.
- A file or a folder of the parent whose name is the same in any case is `in-use`.
- `busy` while an upload is open, a rebuild runs, a test of the mapping shows or the card's
  catalog is read; `read-only` while the core may not write the card; `no-space` when the
  index has no free id; `storage-error` when the folder or the catalog cannot be written,
  the index then as it was.
- A host that cannot make folders answers `unsupported`, after the form is checked, and so
  does one whose `make_folder` answers that its card cannot make them. A board with a USB
  stick makes folders of its own storage only and never writes the stick, so it answers
  `read-only` there, or `busy` as above.

An empty folder is a playlist with nothing to play, as a folder whose files are all
ignored is. An upload into it works as into any folder. Before an upload into a folder the
board makes each folder of its path that is missing from the card, so that an empty folder
an operator removed on a computer is there again. The removal of a folder's last file takes
the folder out of the index only when it has no sub-folder, as before. A `catalog rebuild
external` lists the card's files, and so keeps no empty folder. `folder remove` takes one
empty folder out, [below](#removing-an-empty-folder).

### Moving a file of the card

```
move external 60003 clocks
{"ok":true,"id":60003,"moved":true}
move external 60003 clocks
{"ok":true,"id":60003,"moved":false}
move external 60003 /
{"ok":true,"id":60003,"moved":true}
```

`move external <id> <path>` moves the card's file with the id into the card's folder with
the path, `/` for the card's root, under the owner's approval of 2026-11-06. The path is
written as `folder make external` writes one, decoded once from URI escapes. The file keeps
its name, its id and its entry, and takes its place last among the folder's own files; it
is renamed on the card in one commit of the card's catalog, which moves its line in the
index and on the pages, so that `list`, `list in` and a restart find it there at once. Its
old folder is left as a removal leaves it: a folder left without a file and without a
sub-folder goes from the index, with each folder above it left so, while its directory
stays on the card. The saved brightness, the saved repeat and the Ignore of the file, which
the board keeps by the card's path, are given to its new path: a journal on the card,
`moving.txt`, is written before the commit and removed once they are, and a mount of the
card after a cut finishes them when the card's catalog shows the move, or drops the journal
when it does not. A file that plays goes on playing under its new path. A folder is moved
by the app, folder by folder and file by file ([android-app.md](android-app.md#folders-of-the-card-and-moves)).

- A file in that folder already answers `{"ok":true,"id":<id>,"moved":false}` and writes
  nothing, so that a client may send the line again after a lost reply.
- Refusals, in this order: `bad-argument` for another form; `show-invalid`; `busy` while an
  upload is open, a rebuild runs, a test of the mapping shows or the card's catalog is
  read; `unknown-id` for an id that is no file of the card, an item's of the show among
  them, and for a folder the card has not; `in-use` for the id of a folder of either
  storage; `bad-argument` for a new path over 100 bytes; `in-use` for a file or a folder
  of the destination whose name is the file's in any case; `read-only` while the core may
  not write the card; `storage-error` when the file or the catalog could not be changed,
  the card then as it was.

### Folders of the board's own storage

```
folder make internal shows
{"ok":true,"id":5,"made":true}
folder make internal shows/night
{"ok":true,"id":6,"made":true}
upload begin 12 shows/night/stars.odrg 52340
{"ok":true,"chunk":1500}
list in 5
{"ok":true,"items":[{"id":6,"playlist":"shows/night","external":false,"files":1,"ignored":false,"inherited_ignored":false}],"next":null}
list in 6
{"ok":true,"items":[{"id":12,"file":"shows/night/stars.odrg","bytes":52340,"ignored":false,"external":false,"type":"frames","stored":"2/stars.odrg","inherited_ignored":false}],"next":null}
```

The board's own storage has folders too, under the owner's approval of 2026-11-06. Each is a
playlist, as a folder of the card is, with an id from the show's pool: the lowest id no
item and no folder has, at most 60,000. A file in a folder keeps one name that stays while
it stays there, its stored name, `<n>/<name>`, where `n`, 1 to 255, is the number of the
folder; `show.json`, the internal catalog, `repeats.txt`, `brightness.txt` and the board's
own folders hold that name. What an operator sees is the path: the folder's path, `/` and
the file's name. [core.md](core.md#internal-folders) says how they are kept.

`folder make internal <path>` makes the folder `<path>`: one to three names under the card's
naming rule, 93 bytes at most, decoded once from URI escapes, the last not ending in `.odrg`
or `.odrgx`. Folders are made one level at a time, a new one among its parent's sub-folders
by the bytes of their names. The reply is that of `folder make external`, and a folder that
is there at that path answers `"made":false` and writes nothing. Refusals, in this order:
`bad-argument` for another form; `show-invalid`; `unsupported` on a host whose storage
cannot be changed or that makes no folders; `busy` while an upload is open or a rebuild
runs; `storage-error` while the board could not read its folders in this boot; `in-use`
for a name a sibling has but for the case of its letters; `unknown-id` for a parent that is
not there; `no-space` at 32 folders, without a free number or id, or with less than 8,298
bytes free; `storage-error` when the folder or its line cannot be written, the folders then
as they were.

`upload begin <id> <path> <bytes>` puts a file into a folder: `<path>` is the folder's path,
`/` and the file's name, 100 bytes at most, decoded once from URI escapes; a name alone is
the root, as before. A folder that is not there is `unknown-id`, and the id of a folder is
`in-use`. An upload under the id of an animation of another folder moves the item's file
there.

`list` gives the folders of the root after the show's items at the root and before the
card's, each as `{"id":5,"playlist":"shows","external":false,"files":1,"ignored":false,"inherited_ignored":false}`:
its path, the number of its own animations, its own Ignore and whether a folder above it is
ignored. `list in <id>` of a folder gives its sub-folders, then its own animations in the
order of the show, each with its path as `file`, its stored name as `stored`, and
`inherited_ignored`. `order get in <id>` gives a folder's animations in the saved order,
and `order move` moves one inside its folder; `order get` gives the root's alone.

`ignore <id> <0|1>` of a folder excludes it and every folder below it from automatic
playback, and includes it again: its files then play only by `play` of them. `play <id>`
of a folder makes its playlist current, its own files first and then its sub-folders',
depth first, and plays the first; a host that keeps no current playlist, one without a
drive, answers `unsupported`. The root's playlist plays the show's animations at the root,
then each folder's, then the card's. `read`, `remove`, `remove many`, `saved`, `repeat`
and `brightness` of a folder's id are `in-use`, as for a folder of the card.

A folder emptied of its last file, with no sub-folder, goes, and so does each folder above
it that is left empty the same way; a folder made by `folder make internal` stays while it
was never filled. A folder emptied while a rebuild runs or an upload is received, or by a
removal that a power cut ended before the folder went, stays as one never filled does, and
takes files again, until `folder remove` removes it, [below](#removing-an-empty-folder). A
show without folders is listed, played and saved as before.

A file is a file of its folder while its path is 100 bytes at most, as an upload makes it.
One that a computer's tool put in a folder of a longer path is listed at the root under its
stored name, plays with the root's animations and is named so in `status`, as a file is
whose folder `folders.txt` does not name.

### Removing an empty folder

```
folder remove 5
{"ok":true}
folder remove 60009
{"ok":true}
folder remove 7
{"ok":false,"error":"in-use"}
```

`folder remove <id>`, under the owner's approval of 2026-11-09, removes one empty folder of
the board's own storage or of the card, by the id `list` gives its row, read as `remove
<id>` reads an id. A folder of the board's own storage is empty when no file of the show is
stored in its numbered folder, a file listed at the root for a path over 100 bytes among
them, and no folder is below it; a folder of the card, when the card's index gives it no
own file and no sub-folder. Any other folder is `in-use`, and nothing changes.

- The folder's entry goes first, durably, and its folder of the storage after it: on the
  board's own storage its line of `folders.txt`, written through `folders.part`, then its
  numbered folder; on the card its line of the index's table and map and its row in its
  parent's file, in one commit of the card's catalog that writes no page, then its folder
  on the card. Every other folder and file keeps its id, and no file moves.
- The reply is `{"ok":true}` once the entry is gone. A folder of the storage the host cannot
  remove then, because the power was cut first or it holds a file neither the show nor the
  index knows, stays, listed nowhere: on the board's own storage a later folder given its
  number takes it, and on the card a folder made again at its path. A line sent again after
  a lost reply is `unknown-id`.
- Only the folder named goes: a parent it leaves empty stays until its own `folder remove`.
- A removed folder that is the current playlist gives the root's, with a fresh window,
  saved; another current playlist stays current. The animation that plays goes on.
- A folder of the board's own storage takes its Ignore with its line; a folder of the card
  leaves its `d <path>` line of `ignored.txt`, as every absent path does, so a folder made
  again at that path is excluded again. An empty `clocks` or `clocks/message` of the card
  may be removed, and `status` then reports the clocks as for a card without it.

Refusals, in this order: `bad-argument` for another form; `show-invalid`; `in-use` for the
id of an item of the show or of an animation of a drive. For a folder of the card: `busy`
while an upload is open, a rebuild runs, a test of the mapping shows or the card's catalog
is read; `read-only` while the core may not write the card, a USB stick among them;
`in-use` for a folder that is not empty; `storage-error` when the commit fails, the index
then as it was. An id above 60,000 is `busy` while the card's catalog is read, and the id of
a folder of the card is unknown while the card is out. For any other id of 60,000 or less:
`unsupported` on a host whose storage cannot be changed; `busy` while an upload is open or a
rebuild runs; `storage-error` while the board could not read its folders in this boot;
`unknown-id` when no folder of the board's own storage has the id; `in-use` for a folder
that is not empty; `storage-error` when `folders.txt` cannot be written, the folders then as
they were. Any other id is `unknown-id`.
### Moving or renaming a folder of the board's own storage

```
move internal 6 night
{"ok":true,"id":6,"moved":true}
move internal 6 shows/night
{"ok":true,"id":6,"moved":true}
move internal 6 shows/night
{"ok":true,"id":6,"moved":false}
```

`move internal <folder-id> <path>`, under the owner's approval of 2026-11-09, gives a folder
of the board's own storage a new path: another parent, another name, or both, its
sub-folders with it. `<path>` is the folder's new full path from the storage's root, written
as `folder make internal` writes one; the new parent, the path without its last name, is the
root or a folder of the board's own storage, and the folder takes the last name as its own.
The id is read as `remove <id>` reads one.

- The folder's line and the line of each folder below it get the new path in place of the
  old one at their start, and go together to the folder's new place in the tree's order:
  among the new parent's sub-folders by the bytes of their names, where a folder made there
  would go. `folders.txt` is written once, through `folders.part`; nothing else of the
  storage is written, renamed or removed.
- Every number, id and Ignore, the header's next number, every item, stored name and file,
  the saved order, brightness and repeat, the internal catalog and `show.json` stay as they
  are, so the previews on the phone stay too.
- The reply gives the id and `"moved":true`; a folder that has that path already answers
  `"moved":false` and writes nothing, so a line sent again after a lost reply changes nothing.
- The root's playlist and the rotation take the new order at their next pick, and the turn
  in progress goes on. A moved folder is held under an ignored new ancestor and no longer
  under an ignored old one, and the turn in progress is checked again. A current playlist
  that is the folder or below it stays current with its window: its path in `status` follows
  at once, and in `playlist.txt` at the next refresh.

Refusals, in this order: `bad-argument` for another form or a path outside the rule;
`show-invalid`; `unsupported` on a host whose storage cannot be changed; `busy` while an
upload is open or a rebuild runs; `storage-error` while the board could not read its folders
in this boot; `in-use` for the id of an item of the show, or of an animation or a folder of a
drive, and `unknown-id` for an id nothing has; `bad-argument` for a move into the folder
itself or below it, for a folder of its subtree that would get a path over 93 bytes or more
than three levels, and for a file listed in a folder of its subtree whose path would pass 100
bytes (a file listed at the root for a longer path does not count); `"moved":false` for its
own path; `in-use` when another folder of the new parent has the last name, in bytes or but
for the case of its letters (a rename of the folder's own name that changes only its case is
taken); `unknown-id` when the new parent is not there; `storage-error` when `folders.part`
cannot be written or renamed, the folders then as they were.

## Miniature display debug mode

`status.mini` reports `supported`, acknowledged `on` (null after failed setup),
`pending`, `requested`, `error` (null or `output-setup-failed`) and effective capped
`brightness`. A supporting host needs a60x60 canvas. `debug mini on|off` changes
only RAM and returns acceptance; read status for completion. Opposite requests
during setup are `busy`; the same request is idempotent. Boot is off. Unsupported
hosts refuse the request; failed setup holds output dark until a successful retry.
For example, `debug mini on` may answer `{"ok":true}` while a following status
still reports `"pending":true,"on":false`. Completion is a later status with
`"pending":false,"on":true,"error":null`. Repeating the pending request is
idempotent; `debug mini off` during that pending enable is refused as `busy`.
An explicit on or off retry after failure is allowed. Unsupported capability is
the `unsupported` refusal, not a successful off setting. Status brightness is
the effective miniature cap, zero while power is off; ordinary `brightness` still
reports the requested normal value. No setting file is changed. Reboot is off.
Every existing serial, TCP and HTTP route carries these same command lines;
`odrigctl debug mini on` and `odrigctl debug mini off` validate the two forms.
Read [the wiring and reboot boundaries](../README.md#miniature-display-debug-mode)
before a physical check. Firmware compilation and physical acceptance are open.
The host description is at most 127 input bytes and 256 escaped bytes, ending at a
character boundary, so expanded status remains within the fixed reply limit.

## Error codes

| Code | When |
|---|---|
| `line-too-long` | The line is longer than 2,048 characters. |
| `unknown-command` | The first word is not a command. |
| `bad-argument` | An argument is missing, extra, not a number, out of range, or not in its form: a file name outside the naming rule, base64 that is not as described or stands for more bytes than `chunk`, a CRC-32 that is not eight hexadecimal digits, or a word after `upload` that is not `begin`, `data`, `end` or `cancel`; `move external` of a file whose new path would pass 100 bytes; `move internal` of a folder into itself or below it, or one whose subtree would pass the limits of a folder's or a file's path. |
| `show-invalid` | `play`, `list`, `read`, `remove`, `repeat`, `clocks` or an `upload` command was sent while the show is invalid: its mapping file or show file cannot be used, or its ids are wrong. A fault of one animation file does not make it invalid. |
| `unsupported` | `debug mini` needs a supporting host and an installed60x60 canvas; `folder make` on a host that makes no folders, `folder make internal`, `move internal`, and `folder remove` of a folder of the board's own storage, on one whose storage cannot be changed, and `play` of a folder of the board's own storage on a host that keeps no current playlist. Judged after syntax. |
| `no-upload` | `upload data`, `upload expect`, `upload end` or `upload cancel` was sent while no upload is open. |
| `incomplete` | `upload end` came before all bytes. |
| `bad-checksum` | `upload end` names another CRC-32 than the bytes received have. |
| `busy` | `repeat <id> <n> save`, `repeat <id> default`, `saved` and the lines of `clocks` until the player has read every installed animation after a start, while an upload is open and while a rebuild runs; `read` of a file the player has not read whole since the start; `upload begin` or `remove` while an upload is open; `mapping set` while an upload is open; `upload begin`, `ignore`, `remove` and `remove many` while a test of the mapping shows; `upload end` while the file is being checked; `upload begin`, `remove`, `remove many`, `ignore`, `order move`, `mapping set` and `catalog rebuild` while a rebuild runs; `catalog rebuild` while an upload is open, a test shows or the drive's catalog is read; `folder make external` while an upload is open, a rebuild runs, a test shows or the card's catalog is read; `folder make internal` and `move internal` while an upload is open or a rebuild runs; `folder remove` of a folder of the card while an upload is open, a rebuild runs, a test shows or the card's catalog is read, of an id above 60,000 while the card's catalog is read, and of a folder of the board's own storage while an upload is open or a rebuild runs; `move external` while an upload is open, a rebuild runs, a test shows or the card's catalog is read. |
| `unknown-id` | `play` or `remove` names an id that is neither in `show.json` nor of a folder of the board's own storage nor of an animation or a folder of a USB drive or the card; `repeat <id> <n> save` or `repeat <id> default` names one of nothing `list` lists; `read` names one that is no animation of either; `play all` was sent while the playlist has no animation; `folder make` names a parent folder the card's index or the board's own storage has not; `upload begin` names a folder of the board's own storage that is not there; `move external` names an id that is no file of the card, or a folder the card has not; `folder remove` names an id that is no folder of either storage, and the line sent again after a removal; `move internal` names an id nothing has, or a new parent the board's own storage has not. The id of a folder of the card is unknown while the card is out. |
| `unavailable` | `play` names an animation that is unavailable in this boot, as its file had a fault, a file of a drive left out for a fault, or a cycle that lists only such; `read` names such an animation. |
| `in-use` | `repeat <id> <n> save` or `repeat <id> default` names a cycle or a folder of the card; `remove` names an animation that a cycle lists, or one of a drive the core may not write; `upload begin` names the id of a cycle or of an animation of a USB drive, or a file name another item has; `remove`, `remove many`, `ignore`, `read`, `order move` or `upload begin` names the id of a folder of the card, which is a playlist and no file, and `remove`, `remove many`, `read`, `saved`, `repeat`, `brightness`, `order move` or `upload begin` names that of a folder of the board's own storage; `folder make` names a path whose last name a file or a folder of its parent has, in any case; `move external` names the id of a folder of either storage, or a destination a file or a folder of whose has the file's name in any case; `folder remove` names a folder that holds a file or a folder, or the id of an item of the show or of an animation of a drive; `move internal` names the id of an item of the show or of an animation or a folder of a drive, or a path another folder of the new parent has, in any case. |
| `read-only` | `upload begin external`, `folder make external`, `folder remove` of a folder of the card, `move external`, `catalog rebuild`, or `order move` of a file of the drive, while the core may not write the storage: no drive, a drive its host cannot write, one without a catalog that is `ok`, or a host whose own storage cannot be changed. |
| `mapping-conflict` | The mapping changed since the client read its revision; reload before saving. |
| `rotation-conflict` | Output orientation changed since the client read it; reload before saving. |
| `zone-unset` | No usable phone-zone rules have been installed for a time set. |
| `stale` | `upload expect`: the item of the upload is gone, or its file is not the one the client read. The upload is discarded. `repeat <id> <n>`: no turn of that animation is reported. |
| `order-conflict` | `order move`: the saved order or the listed animations changed since the client read the order's revision; read it again before moving. |
| `no-space` | `repeat <id> <n> save`: no room is left for another saved repeat; `upload begin`: the file would not fit, or the show has no room for another item; `upload begin external`: the file would not fit on the drive; `folder make external`: the card's index has no free id; `folder make internal`: the board's own storage has 32 folders, no free number or id, or too little room. |
| `bad-offset` | `upload data`: the offset is not the number of bytes received so far, or the bytes would pass the size of the file. |
| `bad-file` | `upload end`: the file is not a valid ODRG file for the canvas. |
| `storage-error` | The storage could not be read or written. The show is as it was. An upload that met it is discarded. A file an earlier change could not remove is removed before a change; while that fails, the change is refused with this code, and the next start removes it. `folder make internal`, `folder remove` of a folder of the board's own storage, `move internal` and an upload into a folder while the board could not read its folders in this boot, when its folders' ids are not known either; `move internal` when `folders.part` cannot be written or renamed. |

When more than one code applies, the reply has the first in the order of this table.

## Transports

A transport only carries lines to the command front-end and replies back. The commands and
replies are the same on every transport.

| Where | Serial | Network |
|---|---|---|
| Board | The USB serial port, from a computer or from the operators' app on a phone with a cable. | HTTP over Wi-Fi, on the board's web server. |
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

`mapping get` reports `{ok:true,editable:true,pins:[...],revision:N,test:false,snake:null}`.
Pins are in snake order, 1 through20. Unsupported or invalid mappings report
`editable:false`, an empty `pins` array and revision0. The test flag is target-wide.
The target's existing twenty-pin permutation is editable when each180-LED snake
occupies its own three columns on the60x60 canvas. Pin saves preserve the installed
strip order and starting ends. A target without a mapping file reports the
installation's default pins, editable, with their revision; its first save writes the
file.

`mapping set <revision> <pins>` accepts exactly twenty comma-separated GPIO numbers.
The revision is the decimal CRC-32 of the current twenty pin bytes in snake order.
Every current output pin must occur exactly once. A successful reply means the new
mapping is durably committed and ready for output routing. An identical assignment
performs no storage writes. Re-read after any uncertain reply.

A stale revision gives `mapping-conflict`; malformed or unsupported assignments give
`bad-argument`. Invalid shows give `show-invalid`; an open upload makes writes `busy`,
while the check after a start does not; failed or unavailable writable storage gives
`storage-error`.

The retired cross-wiring operation is not supported; its forms return `bad-argument` without changing the mapping.

`mapping test on` displays the built-in diagonal until `mapping test off` or a valid
ordinary play command. Both test commands are idempotent. Entry requires the valid
60 x 60 target mapping, and is taken whenever play is: while the check after a start
goes on, and while an upload is open. During the test status reports no ordinary
playing item or animation, and the check after a start, the card's check and the
loading of its catalog go on; `mapping get` identifies the active test. `upload begin`,
`ignore`, `remove`, `remove many` and `catalog rebuild` return `busy`, but mapping saves,
list, space, status, power and brightness remain available. An upload that was open
when the test started goes on: its `upload data`, `upload expect`, `upload end` and
`upload cancel` are taken, and an `upload end` that succeeds changes the show, while
nothing plays until the test ends. The test changes no show entry.

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

`ignore <id> <0|1>` persists an animation's, an internal folder's or an external folder's automatic-playlist exclusion, an internal folder's in its line of `folders.txt`:
1 excludes, 0 includes. It is idempotent and returns `{"ok":true}` after durability.
`list` includes boolean `ignored` on installed animations. External file and folder
rows also carry their own `ignored` choice and boolean `inherited_ignored`, derived
from excluded ancestors. Including a parent leaves every child's own choice intact.
Explicit play remains available for excluded files; internal cycle membership still
works. Unknown ids return unknown-id; cycles return in-use.

External choices are saved in internal `ignored.txt`, never on the external medium:
`odrig-ignored 1\n`, followed by `f FULL_PATH\n` or `d FULL_PATH\n` for exclusions.
An absent record means included. Paths survive remounts and reassigned numeric IDs;
file and folder identities are distinct, and absent paths are retained. At most 128
records are kept, without eviction: a new exclusion at capacity returns no-space,
while an existing exclusion can still be removed. Malformed settings discard partial
exclusions, log `ignored unreadable`, and refuse mutations with storage-error.

Saving closes and verifies `ignored.part` before atomic replacement. Failed saves
preserve published bytes and active choices. Abandoned parts are ignored and cleaned
at startup. Every automatic traversal, clock/message candidate and resumed automatic
turn applies own and ancestor exclusion; a changed choice revalidates the current
automatic turn at the next refresh. An explicit manual turn remains available.

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
name with its entry and its row in the root's file of the index, and the reply gives the
animation's id: `{"ok":true,"id":60003}`. A file of that name in the drive's folder is
replaced and keeps its id and its row, and where it plays it plays anew from its start, as
an item's file replaced under its name does; a new one goes last among the root's files,
with the lowest id from 60,001 that the index's map does not hold. `busy` while an upload is
open or the drive's catalog is read, `read-only` when the core may not write the drive,
`no-space` when `drive_space` says the file does not fit.

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

The playlist plays its included animations in the saved order: the board's own in the
order the board keeps in its own storage, then the external storage's in the walk of its
folders, the root's files and then each folder's, each folder's files in the order the
card's index keeps for them. An animation of the board that the saved order does not name
comes after every one it names, in the order of `show.json`; a file uploaded to the card
goes last among the root's files. [show.md](show.md#the-saved-playlist-order) has the
file.

```
order get
{"ok":true,"ids":[3,60002,1],"next":null,"revision":2805384113}
```

`ids` are the ids of the animations `list` lists, the ignored ones, the unavailable ones
and the external storage's among them, of one level, in the saved order, beginning at the position `<from>`, counted
from 0, which is 0 when it is left out; `<from>` is 0 to 4,294,967,295. `order get` gives the
root level, the show's animations at the root and the root's files of the card, and
`order get in <folder-id>` the files of that folder of the board's own storage or of the
card, refused as `list in` is. The reply holds as many
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
`revision` of `order get` of the level of `<id>` the client read, 0 to 4,294,967,295;
`<id>` and `<before>` are 1 to 4,294,967,295. The reply `{"ok":true}` comes once the whole order is saved; a power cut leaves
the order before the move or the one after it. A move that changes nothing, of an
animation that already stands right before `<before>`, or last for `end`, or before
itself, writes nothing.

A file of the card moves among its folder's files, and is saved in the card's index in one
commit of the card's catalog, as `catalog.md` says: `<before>` is a file of the same folder,
or, for a file of the root, an animation of the show, which puts it first among the root's
files. An animation of the show put before a file of the root goes last among the show's.
A card without a catalog that is `ok`, or one the core may not write, keeps the order of
its files: `read-only`.

- `bad-argument`: the words are not in their form.
- `show-invalid`: the show is invalid.
- `busy`: until the player has read every installed animation after a start, and while
  an upload is open.
- `unknown-id`: `<id>` or `<before>` is the id of no listed animation, of no cycle and of
  no folder of the board's own storage or of the card.
- `in-use`: `<id>` or `<before>` is the id of a cycle or of a folder of the board's own
  storage or of the card, which have no place in the order, or `<before>` is an animation
  of another level than `<id>`.
- `read-only`: `<id>` is a file of the card, and the core may not write its index.
- `order-conflict`: `<revision>` is not the order's revision now. Nothing changes; read
  `order get` again.
- `storage-error`: the order could not be saved. It is as it was.

A move does not change the animation whose turn it is, its time, the brightness or
whether the LEDs are on; the next turn follows the new order. It works while a test of
the mapping shows. Every route carries it to the one command parser of the core.

## What is saved for an animation

```
saved 2
{"ok":true,"brightness":27,"repeat":3,"start":false}
```

`saved <id>` reports what the board keeps for an animation of the show or of the card:
`brightness`, its saved brightness of `brightness <id> <n> save`, 0 to 255, or null for
none; `repeat`, its saved repeat of `repeat <id> <n> save`, or null for none; and `start`,
true when it is the item the show's `start` names. A client reads it before it moves an
animation, to give the new file the same settings. `in-use` for a cycle or a folder of the
board's own storage or of the card, `unknown-id` for an id that `list` does not list,
`busy` as for `repeat <id> default`, and `show-invalid` while the show is invalid. It
writes nothing.

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
  of the board's own storage or of the card.
- `in-use`: `<id>` is the id of a cycle or of a folder of the board's own storage or of the
  card, which keep no repeat.
- `no-space`, for a save only: the drive's files would have more than 32 saved repeats, or
  the file holds 512 lines of other animations once the lines of files `show.json` no
  longer names are dropped, which a save does whenever it finds the file full.
- `storage-error`: the file could not be read or written, or the board's storage cannot be
  changed. Nothing changes. A file out of form is no failure: a save writes it anew.

## Clocks between the animations

```
clocks on
{"ok":true}
clocks message on
{"ok":true}
clocks storage internal
{"ok":true}
```

`clocks on` selects Between animations, `clocks off` selects Off, and `clocks only`
selects Clocks only. The independent `clocks message on|off` setting controls a message
after each clock in both enabled modes, and `clocks storage sd|internal` chooses the
storage whose copy of a clock or a message plays, below. Mode, message setting and storage
survive restart. Each line replies `{"ok":true}` once its setting is saved; a setting
already in force writes nothing and replies the same. While both are off the player plays
as [show.md](show.md) says without them. `status` reports them as `clocks`,
`clock_message`, `clock_mode` and `clock_storage`.

The settings are kept in `clocks.txt` of the board's own storage, beside `order.txt` and
`repeats.txt`, in lines each ended by LF and nothing more. While the card's copies are
preferred, three:

```
odrig-clocks 2
mode between
message off
```

While the board's own copies are preferred, four, of version 3, at most 57 bytes:

```
odrig-clocks 3
mode between
message off
storage internal
```

The second line is `mode off`, `mode between` or `mode only`; the third is `message on`
or `message off`; the fourth of version 3 is `storage internal`, or `storage sd`, which is
read but never written. Valid version-1 files (`odrig-clocks 1`, `clocks on|off`, then the
message line) still load, mapping on to Between and off to Off. Versions 1 and 2 prefer the
card's copies. The next changed setting writes version 2, or version 3 while the board's
copies are preferred; a no-op does not rewrite an old file. So a saved choice of the card
is the same version 2, byte for byte, that a player before the choice reads; version 3 is
out of form to such a player, which then fails closed as below until a mode line is sent,
and `clocks storage sd` before going back to it writes version 2 again. A missing file
means Off/message off and the card's copies when the host authoritatively reports no such
file. Unreadable or malformed saved settings, a version 3 without its fourth line among
them, fail closed: effective Only, dark output, the card's copies, `clock_error:"unreadable"`
and `clocks unreadable` in the log. Independent bounded reads retry at most once a second.
A valid read restores the saved mode and storage; an explicit mode command atomically
replaces the policy and clears the error, even if it chooses Only, and keeps the card's
copies. A message-only or storage-only change is refused with `storage-error` until the
saved mode is established.

Saving closes and reads back all of `clocks.part` before one atomic rename. A failure
preserves published bytes and active settings; an abandoned part is removed at startup.
No animation, catalog or show file is rewritten for a mode change.

The faces are the direct files of the folders `clocks` of the card and of the board's own
storage, and the messages those of their folders `clocks/message`: [show.md](show.md#clocks-between-the-animations).
Both modes draw from one bag of the faces of both storages and one of their messages. A
card's file and a file of the board's own storage of the same class, the same name but for
the case of ASCII letters and the same known type are copies: one place of the bag. With
`clocks storage sd`, the default, the card's copy takes it when it plays automatically, and
the board's only when the card's cannot; with `clocks storage internal`, the board's copy
takes it when it plays, and the card's only when the board's cannot. Each copy is judged by
its own storage's rules: listed and readable, not ignored by its own or an inherited Ignore,
not quarantined or unavailable. Each copy keeps its own id for `play`, `read`, edits,
brightness, repeats, Ignore, quarantine and removal: the choice never sends a command to
the other storage's file, and changes nothing of ordinary playlists or of an explicit
`play`. A new choice takes effect at the next draw of either bag, both bags drawn anew; the
turn in progress plays to its end, a message its whole loop. No catalog and no file of
either storage is rewritten for it.

Only stops outside playback and runs the faces of both storages in a shuffled bag, with
one complete direct message from its independent bag after each clock when enabled.
It has no five-turn/five-minute break recursion. Messages finish a complete declared
loop, including loops longer than 30 seconds. Own and ancestor Ignore choices apply
to automatic candidates and are rechecked after changes. Without eligible faces, Only
stays dark and reports why; it does not fall back to ordinary animations or messages, and
with a face of the board's own storage it plays without a card.

Raw command browsing remains unrestricted; the operators' app confines visible browsing
and upload and move destinations to Clocks in Only mode. The boundary holds the folder
`clocks` and every folder below it of the card and of the board's own storage. Outside file/folder/cycle
play and output-taking mapping diagnostics return `in-use` without changing playback, and
an inside file of the board's own storage that is unavailable returns `unavailable`. Raw
`play all` is also refused; the app restarts Clocks with `play <resolved-clocks-folder-id>`,
and `play` of either storage's folder `clocks` does the same.
An explicit inside file remains playable even when ignored or when automatic messages
are off; an inside subfolder starts its first available file, by the walk's order on the
board's own storage, then the exclusive program continues; a subfolder without one restarts
Clocks. These actions do not overwrite the saved normal playlist. Leaving Only
restores its valid path, else root, with its window held and no paused break restored.

- `bad-argument`: the words are not one of the seven forms.
- `show-invalid`: the show is invalid.
- `busy`: while a rebuild of a catalog runs, until the player has read every installed
  animation after a start, and while an upload is open.
- `storage-error`: the file could not be written or verified, or the board's storage cannot be
  changed; for `clocks message on|off` and `clocks storage sd|internal`, also while the saved
  settings are unreadable, until a mode line establishes them. Nothing changes.

They come in this order: `bad-argument`, `show-invalid`, `busy`, `storage-error`.

## Square output rotation

`rotation` returns `ok`, `supported`, `degrees` (0,90,180,270 clockwise), decimal
`revision` (CRC32 of the quarter-turn byte) and `error` (null or `unreadable`).
`rotation set REVISION DEGREES` replies with the complete confirmed object after
atomic publication. Missing settings mean0. Invalid/unreadable `rotation.txt` means0
with an error and a deliberate save can repair it. The bounded ASCII file is
`1 DEGREES\n`; writes go through `rotation.part` and atomic rename. A valid no-op
writes nothing. Refused/failed saves retain the last confirmed live and saved value.
Uploads, catalog rebuilding or pending miniature setup can return busy. Content
validation does not block this independent installation setting. Rotation remains
readable, writable and persistent when mapping/show files are missing or invalid,
or no animation is usable; those content faults still prevent playback. Unavailable
storage reports storage-error. Physical mapping diagnostics return in-use. Valid
rectangular legacy fixtures report unsupported; the installation is permanently
60x60, with no rectangular fit selector.

Rotation samples the complete RGB/palette/text/clock/message/picture composition
before physical mapping and miniature averaging, exactly once. Source previews,
animation bytes, timing, power/current limits and pins stay unchanged. Main and
miniature diagnostic output retain physical coordinates. Ordinary show installation
preserves the saved orientation. Existing HTTP and line transports and odrigctl carry
these same operations; a lost reply must be resolved with a read, not blind replay.
