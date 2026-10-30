# Shows

A show is everything installed on the board besides the firmware: which animations exist,
how they are numbered, and what plays at power-on.

## Installed file set

A show is installed as one flat folder of files:

| File | Content |
|---|---|
| `mapping.json` | The layout of the physical LEDs. See [mapping.md](mapping.md). |
| `show.json` | The list of things that can be played. See below. |
| `*.odrg`, `*.odrgx` | The animations named by `show.json`: ODRG files, and ODRGX containers. See [format.md](format.md). |

The player also keeps three files of its own in the folder while it changes the show:
`upload.part`, `show.part` and `pending.txt`. They are gone when a change is complete, and
the player removes what is left of them when it starts. It keeps the saved playlist order
in `order.txt`, see [the saved playlist order](#the-saved-playlist-order), and writes its
next version into `order.part`. No show names them: a name in `show.json` ends in
`.odrg` or `.odrgx`.

The same folder is what the emulator runs and what is uploaded to the board. The player reads
these files when it starts. Nothing else defines the layout or the show.
While it runs, the commands `remove` and `upload` of [commands.md](commands.md) change the
show; see "Changing a show while it runs".

## show.json

A UTF-8 JSON object with exactly these members:

| Member | Type | Meaning |
|---|---|---|
| `version` | integer | Format version. This document describes version 1. |
| `brightness` | integer | Brightness at power-on, 0 to 255. |
| `items` | array | The items that can be played. It may be empty. |
| `start` | integer | Optional. The `id` of an item. A cycle named here plays at power-on. An animation named here is where the playlist begins at power-on; without `start` it begins with the first animation. |
| `min_seconds` | integer | Optional, 1 to 65,535, and 30 without it: how long an animation plays at least when it has no `repeat`. |

The file is read as strictly as a JSON frames file (see [format.md](format.md)): UTF-8
without a byte-order mark, exactly one JSON value, no member named twice in one object, and
integers written without a fraction and without an exponent.

Each item has an `id`, an integer from 1 to 65,535 that is unique in the file, and is one of
two kinds, with the members of its kind and no other:

| Kind | Members | Meaning |
|---|---|---|
| Animation | `id`, `file`, and optionally `repeat`, `max_seconds` and `ignored` | `file` is the name of an `.odrg` or `.odrgx` file in the folder: 1 to 32 characters from `a`-`z`, `0`-`9`, `-`, `_` and `.`, ending in `.odrg` or `.odrgx`. The file's first bytes, not its name, say whether it is an ODRG file or an ODRGX container. `repeat` is how many times the animation is played through when its turn comes, and `max_seconds` the longest that turn lasts, each a whole number from 1 to 65,535. |
| Cycle | `id`, `cycle`, `seconds` | `cycle` is a list of one or more ids of animation items. `seconds` is how long each one is shown, 1 to 65,535. |

Example: two animations, and a cycle that alternates them every 15 seconds and starts at
power-on.

```json
{
  "version": 1,
  "brightness": 128,
  "items": [
    {"id": 1, "file": "hello.odrg"},
    {"id": 2, "file": "dvd.odrg"},
    {"id": 3, "cycle": [1, 2], "seconds": 15}
  ],
  "start": 3
}
```

## The playlist

The playlist is every included animation item of the show and the animations of a USB
drive or a microSD card when one is there, see [animations from a USB
drive](#animations-from-a-usb-drive), in the saved order, see [the saved playlist
order](#the-saved-playlist-order). Without a saved order it is the show's animations in the
order of `show.json` and after them the drive's. It is what a show plays by itself: each animation has its turn, then the next one, and after the
last the first again, without end. A show with one animation plays it turn after turn. A
show without an animation plays nothing.

With a card of sub-folders there is a playlist for each folder, and one of them is
current: the root's, the folder `odrig` with the show's animations and the loose files, or
a sub-folder's, see [animations from a USB drive](#animations-from-a-usb-drive). A
playlist plays its own animations in the saved order, each for its turn, then each of its
sub-folders' playlists once the same way, depth first, and then its own animations again:
the root exhausts the show's animations and the loose files, then each folder of the card
once, and starts over. A file that is left out, unavailable or still to be read is passed
over, and so is an ignored animation of the show, as always. While the current playlist
has nothing to play, the card out or not yet read or every file of its folders
unavailable, the root plays in its place, and the current playlist takes over at the end
of the turn in progress, from its first animation, as soon as it has something to play.

A current playlist plays for a window of 24 hours of the board's running time from the
moment it became current, the time the LEDs are off and the time a cycle or a jump plays
included; calendar time is never considered. When the window has passed, the turn in
progress ends as it would, and the next playlist in the tree's order becomes current with
a window of its own, the root after the last: a card of the folders `a`, `b` and `b/c`
plays the root for a day, then `a`, `b`, `b/c`, and the root again. A window that ends
while a cycle plays changes which playlist is current and not what plays; the cycle goes
on until a command ends it. A window that ends while a mapping test shows is taken when
the test ends. While the tree is not known, the card out or not yet read, the window's
end makes the root current with a fresh window. With no folder on the card the root is
the only playlist and its window changes nothing that plays. `status` says the seconds
left in the window as `left`.

At power-on a show plays the playlist, from its first animation, or from the animation
`start` names. Only a `start` that names a cycle plays something else: that cycle. The
playlist that was current is current again, with the time spent in its window, from the
board's own file `playlist.txt`: the root plays as said, and a folder of the card plays
from its first animation once the card is read, the root in its place until then. A
restart loses at most the last 15 minutes of the window.

A cycle has no turn in the playlist, wherever it stands among the items.

## The turn of an animation

How long an animation has before the next one starts follows from the length of its loop,
which is the sum of the durations of its frames, and from three numbers:

- With `repeat`, the turn is that many loops.
- Without `repeat`, the animation is played through again and again until at least
  `min_seconds` have passed, 30 when the show names none, and the loop it is in then is
  played to its end. So the turn is the fewest loops that last that long: 8 loops for an
  animation of 4 seconds, 3 loops for one of 10 seconds, one loop for one of 45 seconds.
- With `max_seconds`, the turn ends when that time is reached, in the middle of a loop if
  need be.

The loop of a text is its pass, and a text is never cut in the middle of one: its turn
ends at the end of the pass in which `max_seconds` falls, and in a cycle its turn is
`seconds` rounded up in the same way. A pass of 3 seconds with a `max_seconds` of 10 has a
turn of 12 seconds. The turns of an animation of frames are as above. `play`, `off` and
`on` act at once, in the middle of a pass too.

The loop of a clock is its `seconds`, and its turn is its loops as an animation's of
frames, cut by `max_seconds` in the middle of a loop if need be. Each turn of a clock gets
a seed when it begins, a `play` too, and keeps it to its end through all its loops; the
clock's time runs on from the turn's start, not from the start of a loop.

A turn begins with the first frame of its animation, and at the moment the turn before
it ended. The time of the playlist goes on while the LEDs are switched off.

The numbers above are an animation's own count. Two more come before it, see
[commands.md](commands.md#repeating-the-turn-in-progress): the count `repeat <id> <n>` gives
one turn, for the rest of that turn, and then the saved repeat of the animation in
`repeats.txt`, for every turn. Each is that many loops from the turn's first frame, and
`max_seconds` cuts neither. A cycle has no turn, and so neither.

## Playing an item by command

- `play <id>` of an animation item plays the playlist from that animation: its turn
  begins, with its first frame, and afterwards the playlist goes on with the animation
  after it. No command plays one animation without end. With a folder current, a jump to
  an animation of that folder or of one below it goes on from the jumped animation in the
  playlist's order; a jump to any other animation plays its turn, and then the animation
  whose turn the jump cut plays again, from its first frame, and the playlist goes on.
- `play <id>` of a cycle shows each listed animation in order for `seconds`, then starts
  over, and repeats forever. Each turn starts its animation from the first frame. While
  a cycle plays, the playlist does not.
- `play all` plays the playlist from its first animation, whatever `start` names, and
  makes the root playlist current.
- `play <id>` of a folder of the card makes that folder's playlist current and plays its
  first animation; when nothing at or below the folder can play, the root plays in its
  place.

## Animations from a USB drive

The player can take animations from a USB flash drive, when the program it runs in gives
it one; [core.md](core.md#a-drive) says how. The drive's animations are added to the
show's; they do not take the place of any. Nothing is written to a drive without a catalog,
and no command changes it; a drive with a catalog that its host can write takes uploads and
removals, see [commands.md](commands.md#catalogs).
On the board the drive is a USB stick or a microSD card, as
[firmware.md](firmware.md#the-external-storage) says.

- The drive's animations are the animation files of its folder `odrig` and of its
  sub-folders to three levels down: those whose names end in `.odrg` or `.odrgx`, in any
  case, and do not begin with a dot; other files are passed over. They are listed depth
  first, a folder's files in the order of their names and then its sub-folders in the
  order of their names, every file of the index of a drive with a catalog, and at most 256
  files and 32 sub-folders of one without, as [microsd.md](microsd.md#preparing-a-card)
  says; a file in a sub-folder is known by its
  path from `odrig`, `night/comet.odrg`, in `list`, in the saved order and in the catalog.
- The sub-folders make a tree, the folder `odrig` its root: a sub-folder with an animation
  file at any depth below it is a playlist of its own, with its path and an id from the
  same pool as the files', given after theirs. The drive is listed one level at a time:
  `list` gives the root's level after the show's items, the folders right in `odrig` and
  then its own files, and `list in <folder-id>` a folder's level, its sub-folders and then
  its own files; a folder is listed as
  `{"id":60007,"playlist":"night","external":true,"files":2}`, with the number of its own
  files.
- The player reads each of them whole, after the installed animations, while the show
  plays. A file that is sound and made for the canvas joins the playlist as soon as it
  has been read, at its place in the drive's walk, after the show's animations. One that is not is left out, named in the log
  with its reason, and listed with it; it does not make the show invalid, and the drive's
  other files play.
- Each has an id from the moment the drive is taken up: the lowest from 60001 up that the
  show does not use and no file of the drive before it has. The same files with the same
  show get the same ids every time.
- A file left out is remembered until the next start by its name and its first 512
  bytes: taken up again, it is left out again without being read further.
- Its turn is that of an animation without `repeat` and `max_seconds`. `play <id>` plays
  it, `status` names it, and `list` lists it after the show's items. `upload begin` of its
  id is refused with `in-use`, and so is `remove` of it, except on a drive with a catalog
  that the core may write.
- A show without an animation of its own plays the drive's animations.
- A drive plugged in while the show plays is taken up without a restart. A drive pulled
  out is dropped: its animations leave the playlist and `list`. When one of them was
  playing, the playlist goes on with the next animation that is left, from its first
  frame, or nothing plays. A file that cannot be read while it plays is dropped in the
  same way, and the show stays valid.
- The drive's animations are not part of `show.json`, and `space` does not count them.

A drive with a catalog, the files `catalog.txt` and `catalog-NN.txt` of its folder `odrig`
as [catalog.md](catalog.md) states them, is read otherwise: its folder is not listed, and
its animations are the files its catalog names, in the order of its pages, with the sizes,
lengths and types the catalog gives. The player reads the catalog in steps after the installed
animations, while the show plays, and every animation of it joins the playlist at the same
refresh, once every page agrees with the marker; none of the drive's files is read before
it plays. An entry made for another canvas is left out with `size-mismatch`. A file copied
onto such a drive without its entry is not an animation until `catalog rebuild external`
has read it. While the drive stays plugged in,
the marker is read again once in 10 seconds; another marker drops the drive's animations
and reads the catalog again. A damaged or incompatible catalog leaves the drive without
animations, named in the log as `catalog external damaged` or `catalog external
incompatible`, and the show plays on. A file the player left out is left out again when the
catalog is read again with the same entry, by its name and CRC-32; an entry with another
CRC-32 is a new file.

A drive with a catalog that its host can write, the card on the board, is changed by the
board's commands: `upload begin external` puts a file on it with its entry, `remove` of one
of its animations takes the file and its entry out, and `catalog rebuild external` reads
every file of it and writes its catalog anew, as `python3 -m odrig.catalog MOUNT import`
does on a computer, [microsd.md](microsd.md#the-catalog-made-on-a-computer).
[commands.md](commands.md#catalogs) has the commands.

## Changing a show while it runs

`remove <id>` takes an item out of the show. `upload` adds an animation item, or gives an
animation item another animation. Both take effect at once and are kept: the player
writes `show.json` and the `.odrg` file, and a restart finds the show as it was left.

- A new item is added at the end of `items`. Its `id` is the one the upload named: any
  id from 1 to 65,535 that no item has. Ids need not follow each other, and the id of a
  removed item can be used again. It has its turn in the playlist after the items
  before it, without a `repeat` or a `max_seconds` of its own.
- An upload to the id of an animation item replaces its animation. The item keeps its
  id, its position, its `repeat` and its `max_seconds`, and gets the file name the upload
  named. When it is the animation whose turn it is, the turn begins again with the new
  animation.
- When the animation whose turn it is is removed, the playlist goes on with the animation
  after it. When the cycle that plays is removed, the playlist plays, from its first
  animation.
- A cycle cannot be made or changed by a command. A cycle can be removed, and an
  animation can be removed once no cycle lists it.
- Two items do not get the same file by an upload: a file name that another item has is
  refused. A show installed with two items that name one file keeps working, and the
  file is deleted when the last item that names it is removed.
- An `.odrg` file that no item names any more is deleted.
- The show may end up without items. It is valid: nothing plays until an animation is
  uploaded, and then the playlist plays.
- `brightness`, `min_seconds` and `start` of `show.json` are not changed by an upload.
  Removing the `start` item removes `start`.
- `mapping.json` is never changed.

A change is made so that a power cut at any moment leaves a whole show in the folder: the
one from before the command, or the one after it. New content is written to a file of its
own and gets its name by renaming.

How many items a player has room for is fixed when it starts: 32 more than the show has
then, and at least 128. A new item beyond that is refused until the player has restarted
or an item was removed.

## show.json after a change

The player writes `show.json` as one line without spaces, followed by a line feed, with
the members in this order, and each of `min_seconds`, `repeat`, `max_seconds` and `start`
only when the show has it:

```json
{"version":1,"brightness":128,"min_seconds":45,"items":[{"id":1,"file":"hello.odrg","repeat":3,"max_seconds":120},{"id":2,"file":"dvd.odrg"},{"id":4,"cycle":[2,1],"seconds":15}],"start":4}
```

`brightness` is the value the file had when the player started. An animation that gets
another file by an upload keeps its `repeat` and its `max_seconds`; an item that an upload
adds has neither. A file written by hand in another layout is read as before; it gets this
layout the first time the show is changed.

## When a show is invalid

A show is invalid when `mapping.json` or `show.json` is missing or breaks its format, when an
id is used twice, when a cycle or `start` names an id that does not exist, or when a cycle
names a cycle.

With an invalid show the LEDs stay dark, and the status command reports what is wrong.

Each of these has a fixed name, listed under "Shows" in [reasons.md](reasons.md). When a show
is invalid in more than one way, the first in this order is reported: the mapping file, the
format of `show.json`, an id used twice, an id that does not exist, and a cycle that names a
cycle. The ids are checked over the items in file order.

## An animation that cannot be played

When it starts, the player reads the mapping, `show.json` and the header of every listed
file, and then plays at once. What a file holds after its header it reads while the show
plays. A listed `.odrg` file that is missing, cannot be read, breaks its format or has a
canvas size different from the mapping's is unavailable from the moment the player finds
it until the next start: the show stays valid and plays its other animations.

- The playlist, `start` and every cycle pass over it; a cycle that lists only
  unavailable animations gives way to the playlist. When every animation is unavailable,
  nothing plays and the LEDs are dark, and every command is answered.
- `play` of it is refused with `unavailable`, and `list` shows it with the reason.
- The file is not read again until the next start, and it is not changed or removed. An
  upload to its id that passes its check makes it available at once; `remove` takes it
  out of the show as any animation.
- A player whose storage cannot be changed reads every file to its end when it starts,
  and the same holds for what it finds there.

## Playlist inclusion

An animation item can contain `"ignored":true` to exclude it from automatic playback.
The optional member is a strict boolean; absent means false, and cycles reject it.
The converter preserves the original show bytes, including explicit false. Shows
using this member require the updated player and converter; older readers may reject it.
Manual play still plays one normal turn and cycles retain every explicitly named member.
All ignored with no external animations leaves a valid, idle black show. An ignored
startup item is skipped forward to the next included animation, wrapping if necessary.

## The saved playlist order

The order of the show's animations is kept in `order.txt` beside `show.json`. The player
writes it when a command moves an animation of the show, see
[commands.md](commands.md#the-saved-playlist-order), and nothing else changes it; it may be
missing.

```
odrig-order 1
i 12
i 3
```

The first line is `odrig-order 1`; a file with another first line names nothing. Every
further line ends in a line feed and is an entry: `i` and the id of an animation item of
the show, in decimal from 1 to 65,535 without a leading zero. A line `x` and a file name,
which named a file of the drive in a file written before, is passed over, and the next
write leaves it out. A line in another form is no entry and takes no place. The player
takes the first 512 entries, and of two entries for one animation the first.

- The playlist plays the show's animations the file names in the order of their entries,
  and after them the ones it does not name, in the order of `show.json`; a new item is
  therefore last until it is moved. Then it plays the drive's files in the drive's walk:
  the root's files, then each folder's, depth first, each folder's files in the order of
  the rows of the card's index, which `order move` changes on a card with a catalog, and of
  their names on a card without one.
- An entry of an id that no item has is passed over, and an upload that gives an item that
  id gives it that place.
- `start` still names where the playlist begins at power-on, and `play all` begins it with
  the first animation of the order. Cycles do not follow the order.
- A turn in progress, the brightness and whether the LEDs are on do not change when the
  order does; the next turn follows the new order.

## The saved repeats

The saved repeats are kept in `repeats.txt` beside `order.txt`. The player writes it when a
command saves a repeat or restores an animation's own count, see
[commands.md](commands.md#repeating-the-turn-in-progress), and nothing else changes it; it
may be missing. It is not JSON, because a drive's names may hold bytes JSON does not take.

```
odrig-repeats 1
5 f hello.odrg
3 x night/comet.odrg
```

The first line is `odrig-repeats 1`. Every further line ends in a line feed: the loops, in
decimal from 1 to 65,535 without a leading zero, a space, `f` and the name a file of the
board's own storage has in `show.json`, or `x` and the name of a file of a drive or a card as
the drive gives it, 1 to 127 bytes without NUL, as `order.txt` names it. The file holds at
most 512 lines. It is read strictly, as a whole: a first line that is not the header, a line
in another form, more than 512 lines or bytes after the last line feed make it unreadable,
which the log says once, `repeats unreadable`; no saved repeat is in force then, and the
next save writes the file anew. Of two lines for one file the first counts; the player
never writes two.

- A saved repeat belongs to the file name, not to the id. A removal keeps its line, and an
  item or a file that has that name again has it again; an upload under another name, or a
  new name, starts from the animation's own count. Two items that name one file share it.
- A drive's lines are matched to its files by name when it is read, before any of them
  plays: of its files, 32 at most have a saved repeat, the first 32 the file names; a drive
  that would have more gives the others none, and the log says `repeats over`.
- The player writes the file whole as `repeats.part` and renames it, as it writes
  `order.txt`: a power cut leaves the old file or the new one, and a `repeats.part` left by
  one is removed at the next start.
- `ignore`, a move of the order and the brightness leave the saved repeats alone, and
  `show.json` is never changed for a repeat.

## Clocks between the animations

While the clocks are on, `clocks on` of [commands.md](commands.md#clocks-between-the-animations),
the playlist has a break now and then: a turn of a clock, and, while the message is on and
there is one, one loop of the message after it. The clocks are the animation files directly
in the folder `clocks` of a card's folder `odrig`, at its first level, and each message is
the next eligible direct file in an independent shuffled bag of `clocks/message`; the show's own animations
are never clocks, nor is a file of another sub-folder of `clocks`. While both settings are
off, the player plays as the rest of this page says.

- **The folders are the breaks'.** While the clocks are on, every playlist passes over the
  folder `clocks` and every folder below it, as it passes over an ignored animation: the
  root's walk, a folder's, the first animation of a playlist, and a folder whose files are
  all in them, which has nothing to play, so that the root plays in its place. A `play
  <id>` of one of their files plays its turn as a jump; a `play <id>` of one of the folders
  makes it current, and the root plays in its place. While the clocks are off they are
  folders of the card like any other.
- **When a break comes.** The player counts the playlist's turns that end, at their end or
  cut by `play`, `play all`, `ignore`, `remove`, an upload, the quarantine of its file or
  the card pulled out, and the playlist's time: the running time while the playlist plays,
  the LEDs off included, but not while a cycle plays, a test of the mapping shows or
  nothing plays. A break begins at the end of a turn once 5 turns are counted, or once 5
  minutes, 300,000 ms, are counted at that end or before it. When the 5 minutes are counted
  within a turn, the turn is paused at that moment; after the break it goes on from the
  same point of its time, with its frame, its loop, a clock's seed and the count a `repeat`
  gave it, for the rest of its turn. Both counts start from zero at the start with the
  clocks on, at `clocks on`, at the end of every break, when a break is cut, and when a
  break is due and no clock can play; then nothing plays in its place.
- **A break.** The clock's turn is as long as its turn in the playlist would be: its saved
  repeat, else the fewest whole loops that last `min_seconds`; its seed is drawn when its
  turn begins. The message plays once: one loop, a text's pass, never cut. After the
  break the playlist goes on with the paused turn, or with the animation whose turn was to
  begin, or with the one after it when that can no longer play. `status` reports a break's
  turns as turns: `animation`, `repeat`, `loop` and `saved` are the clock's or the
  message's, and `playing` stays the playlist's.
- **The order of the clocks.** Each break takes the next clock of an order drawn at random
  among all the orders of the clocks there are, each once; a clock that cannot play when
  its place comes is passed over. When the order is used up a new one is drawn, and the
  last clock of one may be the first of the next. A new order is drawn at the start, when a
  card is taken up or dropped, and when its tree changes.
- **The order of messages.** Messages have their own shuffled bag in both enabled modes.
  Every eligible direct message is taken before that bag reshuffles; ignored files and
  descendants of ignored folders are passed over. A message turn is one complete loop,
  including procedural loops longer than 30 seconds. Choosing a message does not consume
  a place in the clock-face bag.
- **What cuts a break.** Whatever cuts a turn of the playlist cuts a break, its paused turn
  not resumed: a `play` of any kind, `play all`, `ignore`, `remove`, an upload, the
  quarantine of its file, the card pulled out; and a test of the mapping, after which the
  playlist plays, from its first frame, the animation the break was to give way to.
  `clocks off` and `clocks message off` let a break in progress play to its end, with the
  message as it was when the break began; `clocks message on` during a clock's turn gives
  that clock its message. `on`, `off`, `brightness`, `order move` and `list` change nothing
  of a break.
- **The window.** A playlist's window that passes during a break is taken at the break's
  end: the paused turn is not resumed, and the next playlist plays from its first
  animation. A restart forgets a break.

### Clocks only

`clocks only` uses the same two bags in a separate scheduler: a clock, optionally a
complete message, then the next clock. It does not run normal breaks or folder-window
rotation. The normal playlist path and its window stay saved, and leaving Only resumes
that valid playlist, else root, without restoring a paused break. A global restart
targets Clocks; an explicit inside file or subfolder is a manual turn before the
exclusive program continues. Outside play and output-taking diagnostics are refused.

Only remains selected when media is absent, Clocks is missing or no face is eligible.
Output stays dark and responsive with the reason in `clock_only`; a relevant media or
inclusion change retries selection. Browsing is unrestricted, and Ignore remains an
automatic exclusion rather than a manual-play ban inside the exclusive boundary.
