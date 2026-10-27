# Requirements: a cross-wired snake 10

The seed is `project-seeds/43-p1-a-cross-wired-snake-10/`. The owner asked for it to be
specified without a question pass; where these requirements decide a point the seed
leaves open, the decision is recorded in `docs/drifts.md`.

## 1. The format

1.1 A leg of a mapping file may have a member `starts`: an array with one word for each
of its strips, in chain order, each `"bottom"` or `"top"` in a column-leg file and
`"left"` or `"right"` in a row-leg file. Its first word is the leg's `first_led`. With
it, strip `s` of the leg starts at the end `starts[s]` names; without it, the strips
alternate from the `first_led` end as today.

1.2 A `starts` whose length is not the number of strips, whose words are not those of
the file's kind, or whose first word is not `first_led` makes the file
`mapping-malformed`, as every broken rule does. Rule 6 of the format allows the member;
"Where each LED is" states the rule with it.

1.3 Every reader of the format follows 1.1: the core, the Python library's reader and
`position`, and the emulator's page, whose LEDs view and mapping view place and draw
the LEDs of such a leg by the stated ends. The target build's file `mapping/legs-20.json`
does not change.

## 2. The bit on the installation

2.1 Position 10 of the installation is cross-wired when leg 10 of the mapping has the
columns 28, 30, 29 with `starts` `bottom`, `bottom`, `top`; it is wired as the others
when leg 10 is the canonical columns 28, 29, 30 alternating from the bottom. The bit is
nothing but this: it is kept in the mapping file, so that a restart, the emulator and
every app agree.

2.2 `mapping get` reports the bit as a member `cross`, `true` or `false`, after
`revision`; `false` for a mapping that is not editable. A mapping is editable, as today,
when it is the canonical twenty three-column snakes of 60 x 60, and now also when leg 10
is cross-wired and the other nineteen are canonical.

2.3 A new command, `mapping cross on` and `mapping cross off`, sets the bit: it rewrites
the mapping file as `mapping set` does, atomically, with the pins as they are and leg 10
in the form the word names, and places leg 10's LEDs anew at once, so that the next
refresh shows the picture by the new placement. The same bit again is `{ok:true}` with
nothing written. The refusals are those of `mapping set` without the revision:
`bad-argument` for a word that is not `on` or `off` or for a mapping that is not
editable, `show-invalid`, `busy` while the start-up check runs or an upload is open, and
`storage-error` when the file cannot be written. The revision of the mapping stays the
CRC-32 of the twenty pins: the bit is not in it.

2.4 `mapping set` keeps the bit as it is: a permutation of the pins, or Restore defaults
in the app, rewrites leg 10 in the form it has. The interrupted and the recovered saves
of `mapping set` hold for `mapping cross` too: a power loss at any step leaves the file
whole, in the old form or the new.

2.5 The diagonal and the snake tests are drawn on the canvas as today. With the bit on
and the installation wired as the seed says, position 10's stub of the diagonal rises
like every other stub, and the block of the snake test of snake 10 climbs the three
physical columns 28, 30 and 29 together, as on every other snake, so that every LED
lights in turn and a strip that runs the wrong way is seen. With the bit off on that
installation, the block climbs column 28 and descends columns 29 and 30.

## 3. The app

3.1 Settings' Mapping section shows, under the editor's column and its buttons, a
checkbox `Snake 10 is cross-wired` with a line of small print that says what it is
for: the installation's snake 10 is chained 28 up, 30 up, 29 down around a dead output.
It shows the installation's bit, read with `mapping get` and followed by the same poll
that follows the pins, and is off until the installation says otherwise. It is disabled
while the mapping is not editable, while a move or a save is in flight, and while the
installation is not answering.

3.2 A tap saves at once with `mapping cross on` or `off`, as a drag saves a move: the
summary says `Saved: snake 10 is cross-wired.` or `Saved: snake 10 is wired as the
others.`; a refusal or a missing reply is said as a save's is, and the box shows the
installation's bit again.

3.3 The checkbox is the same in the APK, the browser and the emulator's Controller view.

3.4 The mapping from a photo is read as today, with any state of the bit. The page of
the app says what the bit changes: with it on, the photo of the diagonal shows a normal
stub at position 10; with it off on the installation as wired, position 10's stub is
broken, the reading gives that position no snake and the snake no other position shows,
and says so in its words, so that the operator applies the photo's mapping and then turns
the box on.

## 4. What does not change

4.1 No change in the firmware's own code: the leg stays one output of 180 LEDs on the
same pin, and only the core's placement of canvas pixels along it changes. The firmware
is rebuilt because it holds the core.

4.2 The commands of the list are as before but for `mapping cross`, and the replies but
for `cross` in `mapping get`. No library, no download.

## 5. Tests and documents

5.1 The core's suite reads a column-leg file with `starts` and places its LEDs by it,
reads a file without it as today, and refuses the three broken forms of 1.2 and a
`starts` in a row-leg file with column words. The library's suite reads and refuses the
same, and `position` follows `starts`. The emulator's suite shows the layout's
positions, strips and path of such a leg.

5.2 The mapping suite checks `mapping get` reporting `cross` false on the target's
file, `mapping cross on` rewriting the file with leg 10 crossed and reporting true, the
diagonal's pixels of leg 10 landing on the LEDs of the crossed chain, the snake test of
snake 10 lighting the chain's LEDs in rows together, `off` restoring the file, the same
bit again writing nothing, a `mapping set` keeping the bit, the refusals, the file whole
after a power loss at every step of the save, and the bit kept across a restart.

5.3 The app's suite, in Chrome against the emulator, checks the checkbox off by default,
on after a tap with the summary said and the emulator reporting true, the box following
the installation after a change elsewhere, a refusal said with the box back, and the
box disabled while the mapping is not editable; and the photo reading of a synthetic wall
whose position 10 is cross-wired and read with the bit off, the position given the
remaining snake.

5.4 docs/mapping.md, docs/commands.md, docs/core.md, docs/emulator.md,
docs/android-app.md and docs/python-library.md describe the member, the command, the
reply and the checkbox; docs/decisions.md gets a dated line; AGENTS.md lists the seed.

5.5 A new firmware and a new APK are built and put with the artifacts, the connected
board is flashed, and the owner's check on the installation is left open in words: with
the box on, an animation shows right on columns 28 to 30, the snake test of snake 10
climbs the three columns together, and the diagonal's stub at position 10 is normal.
