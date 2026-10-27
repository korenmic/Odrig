# A cross-wired snake 10

## Summary

Snake 10 of the installation is wired differently from the other nineteen since
2026-10-27, and the firmware must drive it right. The data output at the end of its
second strip, line 29, is dead, so the owner re-chained the three strips: the leg's
input still enters line 28 at the bottom and runs up; from the top of line 28 a long
wire crosses the board to the bottom of line 30, which runs up; from the top of line 30
the data enters line 29 at the top, which runs down and ends there, its dead output
unused. The chain is thus columns 28, 30, 29, running up, up, down, where the mapping's
rule has the three strips of a leg alternate, up, down, up. The core gets a way to say
the strips' directions of a leg, the operators' app gets a checkbox in Settings' Mapping
section, `Snake 10 is cross-wired`, off by default, kept on the installation and shown
alike in the APK, the browser and the emulator's Controller view; the snake test, the
diagonal and the playback follow it.

## Priority

- `P1`

## Depends On

- Seed 30, for the mapping file, `mapping get` and `mapping set`, the diagonal under
  `mapping test on`, and the mapping editor the checkbox stands beside.
- Seed 36, for the snake test of each snake, which must run along the chain as it is.
- Seed 40, for the mapping from a photo, whose reading of position 10 the checkbox
  changes.

## Product Context

On 2026-10-26 the owner found that line 29's data output does not drive line 30, while
line 29 itself lights. With every strip glued to the board and the connectors between
strips a few centimetres long, no re-chaining with twenty board outputs lights all sixty
lines unless line 29's output is restored: the forty lines that run up and the twenty
that run down give each chain the shape up, down, up, and every down-line's output is
needed. The owner chose the one chain that lets line 29 end a snake: one long wire from
the top of line 28 to the bottom of line 30, and line 30's top output into line 29's top
input, a short connector. Snake 10 now reads its 180 LEDs in the order 28 up, 30 up, 29
down.

The mapping describes a column leg as its columns in chain order with the end its first
LED starts at; the strips then alternate direction. That rule is true of nineteen snakes
and false of this one: with it the core puts the pixels of columns 29 and 30 on the wrong
rows of the wrong strips, the snake test runs the block the wrong way through two of the
three strips, and the diagonal's stub at position 10 is broken.

The owner asked for a checkbox rather than a fixed rule, off by default, because the
mapping from a photo cannot know ahead of time which physical position holds the
cross-wired snake: the operator reads the photo with the box off, then turns the box on
for the installation as it is wired. The cross-wiring belongs to the physical position,
columns 28 to 30, not to a pin: the mapping editor and the photo reading move pins
between positions, and whatever pin drives position 10, its strips run 28 up, 30 up, 29
down.

## Technical Constraints

- The mapping file gets a way to state the direction of each strip of a leg in chain
  order, for any leg, so that a leg no longer has to alternate: for snake 10, columns
  28, 30, 29 with the directions up, up, down. The core places every LED of such a leg
  by the stated directions; a leg without stated directions keeps the rule of today.
  The reader rejects directions that do not match the number of columns. The format's
  page says it, and the mapping file of the target build stays as it is, the box off.
- The checkbox is one bit on the installation, kept in the mapping file beside the
  legs, so that the firmware, the emulator and every app agree after a restart; the
  core applies it as it applies a changed pin, with the picture following at the next
  refresh. On, the leg of position 10 is columns 28, 30, 29 with directions up, up,
  down; off, columns 28, 29, 30 alternating. The command list gets what the app needs
  for it: the bit in the reply of `mapping get`, and a way to set it that the spec
  chooses between a member of `mapping set` and a command of its own; the owner decides
  this addition to the command list through this seed.
- Only position 10 is cross-wired in the installation, and the app shows one checkbox
  for it, `Snake 10 is cross-wired`, in Settings' Mapping section under the editor's
  column, off by default. The core and the format are general; the app is not.
- The snake test of snake 10 runs the block along the chain as wired: up line 28, up
  line 30, down line 29, and back, so that every LED of the snake lights in turn and
  the direction of each strip is seen. The diagonal lights the canvas as before; with
  the box on, position 10 shows a normal stub at the height of the snake that drives it.
- With the box off, position 10's stub is broken: the pixel of column 28 lands on its
  row, the pixels of columns 29 and 30 land on rows 62 - 3s and 61 - 3s for the snake s
  that drives it, in the rows of snake 21 - s. The photo reading must stay a best
  effort: that position's votes go to the wrong snake, which the position that really
  shows it holds with more votes, so position 10 gets no snake and the snake no other
  position shows, as today's fill rule gives it. The reading's words say the position
  shows no snake; the page of the app says why, and says to turn the box on after the
  photo's mapping is applied.
- WLED's outputs do not change: the leg is one bus of 180 LEDs on the same pin; only the
  core's placement of canvas pixels along the leg changes. No firmware setting, no
  download, no library.
- The emulator shows the installation as the box says: its LEDs view places the leg's
  pixels by the stated directions, so the Controller view and the APK show one thing.
- The checkbox is saved at once, as a drag in the editor is saved, with the revision
  last read; a conflict is said as there. The mapping editor's restore of the defaults
  leaves the box as it is.

## Required Behavior

1. The mapping format takes, for any column leg, the direction of each strip in chain
   order; without it the strips alternate as today. The core places the LEDs by it.
2. `mapping get` reports whether position 10 is cross-wired; the app's new way of
   setting it, chosen in the spec, keeps the bit in the mapping file on the
   installation.
3. Settings' Mapping section shows `Snake 10 is cross-wired`, off by default, saved on
   the tap, said as the editor's saves are said, and shown as the installation has it.
4. With the box on, an animation shows right on columns 28 to 30, the snake test of
   snake 10 runs up line 28, up line 30 and down line 29 and back, and the diagonal shows
   a normal stub at position 10.
5. With the box off, the photo reading gives position 10 the snake no other position
   shows, and says the position shows no snake.
6. The emulator's LEDs view and Controller view show the same as the APK, with the box
   in either state.
7. The pages of the format, the mapping, the commands, the core, the emulator and the
   app describe the directions, the bit and the checkbox.

## Definition Of Done

1. All test suites that need no board and no phone pass: the core's suite reads a leg
   with stated directions and places its LEDs, and rejects directions that do not fit;
   the mapping suite sets and gets the bit, through the emulator, and sees the snake
   test run along the chain as wired; the app's suite checks the checkbox in Chrome
   against the emulator, off by default, saved on the tap, a conflict said, and the
   photo reading with the box off giving position 10 the remaining snake; the emulator's
   suite shows the leg's pixels by the directions.
2. A new firmware and a new APK are built and put with the artifacts; the owner turns
   the box on and checks on the installation that columns 28 to 30 show an animation
   right, that the snake test of snake 10 runs the chain as wired, and that the
   diagonal's stub at position 10 is normal.

## Open Questions

None. The owner asked for this seed to be pushed at once; the decisions it needed are
taken in the constraints: the directions in the mapping file for any leg rather than a
special case in the core, one bit on the installation rather than a setting in the
phone, one checkbox for position 10 rather than a general editor of directions, off by
default, and the photo reading's best effort with the box off left as it is and said.

## The Owner's Answers

On 2026-10-27 the owner wrote that the dead output of line 29 was worked around by a
reverse chain for snake 10 alone: line 28's data output goes to line 30's input by a
long wire across the physical board, and line 30's data output goes into line 29's
input normally; and asked for a checkbox in Settings to toggle a special mapping for
snake 10, off by default, because while the diagonal's mapping from a photo is being
read it cannot be told ahead of time which snake is the cross-wired one.
