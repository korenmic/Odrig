# Shows

A show is everything installed on the board besides the firmware: which animations exist,
how they are numbered, and what plays at power-on.

## Installed file set

A show is installed as one flat folder of files:

| File | Content |
|---|---|
| `mapping.json` | The layout of the physical LEDs. See [mapping.md](mapping.md). |
| `show.json` | The list of things that can be played. See below. |
| `*.odrg` | The animations named by `show.json`. See [format.md](format.md). |

The player also keeps three files of its own in the folder while it changes the show:
`upload.part`, `show.part` and `pending.txt`. They are gone when a change is complete, and
the player removes what is left of them when it starts. No show names them: a name in
`show.json` ends in `.odrg`.

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
| Animation | `id`, `file`, and optionally `repeat` and `max_seconds` | `file` is the name of an `.odrg` file in the folder: 1 to 32 characters from `a`-`z`, `0`-`9`, `-`, `_` and `.`, ending in `.odrg`. `repeat` is how many times the animation is played through when its turn comes, and `max_seconds` the longest that turn lasts, each a whole number from 1 to 65,535. |
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

The playlist is every animation item of the show, in the order of `show.json`. It is what
a show plays by itself: each animation has its turn, then the next one, and after the
last the first again, without end. A show with one animation plays it turn after turn. A
show without an animation plays nothing.

At power-on a show plays the playlist, from its first animation, or from the animation
`start` names. Only a `start` that names a cycle plays something else: that cycle.

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

A turn begins with the first frame of its animation, and at the moment the turn before
it ended. The time of the playlist goes on while the LEDs are switched off.

## Playing an item by command

- `play <id>` of an animation item plays the playlist from that animation: its turn
  begins, with its first frame, and afterwards the playlist goes on with the animation
  after it. No command plays one animation without end.
- `play <id>` of a cycle shows each listed animation in order for `seconds`, then starts
  over, and repeats forever. Each turn starts its animation from the first frame. While
  a cycle plays, the playlist does not.
- `play all` plays the playlist from its first animation, whatever `start` names.

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
id is used twice, when a cycle or `start` names an id that does not exist, when a cycle names
a cycle, or when a listed `.odrg` file is missing, breaks its format, or has a canvas size
different from the mapping's.

With an invalid show the LEDs stay dark, and the status command reports what is wrong.

Each of these has a fixed name, listed under "Shows" in [reasons.md](reasons.md). When a show
is invalid in more than one way, the first in this order is reported: the mapping file, the
format of `show.json`, an id used twice, an id that does not exist, a cycle that names a
cycle, and then the listed files in the order `show.json` names them. The ids are checked
over the items in file order.
