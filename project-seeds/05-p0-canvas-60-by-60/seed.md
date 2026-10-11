# Canvas 60 by 60

## Summary

Bring the whole project to the target installation: a square canvas of 60 columns by 60
rows, 3,600 LEDs, built from twenty legs whose strips run vertically. This covers the mapping
file format, the target mapping, the firmware's outputs, the emulator's views, the
documents, the demo show, the limits the code is tested against, and the measurements on the
board.

## Priority

- `P0`

## Depends On

- Seeds 01 to 04, which built everything this seed changes.

## Product Context

The owner corrected the target twice.

**Size.** The canvas is 60 x 60: every row has 60 LEDs and every column has 60 LEDs. The
earlier target was 60 x 30.

**Direction.** A leg is still one data pin with three 60-LED strips wired as one snake of
180 LEDs. In the target installation the strips stand upright: a leg is three columns, not
three rows. The snake begins at the bottom of the leg's first column and runs upward, comes
down the second column, and goes up the third.

Twenty legs stand side by side and make the 60 columns. Leg 1 is the leftmost: its snake
starts at the bottom-left LED of the canvas, (1,1), and it covers columns 1 to 3. Leg 2
covers columns 4 to 6, and so on to leg 20 on columns 58 to 60.

The board and the emulator read the same mapping file, so the mapping file format has to be
able to say this. Today it can only describe legs as rows.

Twenty legs need twenty LED outputs. Stock WLED drives at most twelve on this chip: four
through one driver and eight through a parallel driver. The chip's parallel driver can carry
sixteen, which with the other four makes twenty. Whether the firmware can really drive twenty
outputs has to be proven on the board.

Today's bench build, two legs of three rows (60 x 6), stays valid and stays as it is.

## Technical Constraints

- One mapping file format serves the board and the emulator. It describes legs as rows or as
  columns. A file uses one of the two for all its legs.
- Existing mapping files keep their meaning. `mapping/legs-2.json` is not changed.
- Nothing may assume legs are rows, three strips per leg, or a particular canvas size: the
  converter, the core, the emulator and its page, the tools, the firmware code, the tests and
  the documents.
- Pixel order and coordinates in the animation formats do not change: (1,1) is the
  bottom-left pixel.
- Pins 19 and 20 carry the USB connection and cannot drive LEDs, so legs 19 and 20 cannot
  follow the rule that leg N uses the pin labelled N.
- A change to WLED's own files is kept as a small patch file, as seed 04 requires.
- The core's working memory for the 60 x 60 canvas with 100 items stays under 128 KB.
- The drawings and tables in `docs/mapping.md` are produced from the mapping files by a
  tracked tool, and a test fails when the page and the files disagree.
- Tests that need the board are kept apart from those that do not.
- On the board, only one 60-LED strip is attached, on leg 1, powered from the 3.3 V pin.
  Anything shown on the board uses brightness 40 or less.

## Required Behavior

1. The mapping file format gains column legs:
   - A file with row legs is as today: a top-level `width`, and in each leg `rows` and a
     `first_led` of `left` or `right`.
   - A file with column legs has a top-level `height`, the number of LEDs in every column,
     in place of `width`. Each leg has `columns`, the canvas column (x) of each of its strips
     in chain order, in place of `rows`, and a `first_led` of `bottom` or `top`: the end of
     the leg's first column where its first LED sits.
   - The strips of a column leg alternate direction along the chain, as rows do.
   - With column legs the canvas width is the total number of columns in the file, and every
     x from 1 to the width appears exactly once.
2. `mapping/legs-20.json` describes the target: `height` 60 and twenty legs. Leg N has
   columns 3N-2, 3N-1 and 3N, and `first_led` is `bottom`. Legs 1 to 18 are on pins 1 to 18,
   leg 19 on pin 21 and leg 20 on pin 47.
3. `mapping/legs-10.json` is removed. It described the abandoned 60 x 30 target.
4. The converter, the core, the emulator, the command tool and the firmware accept both kinds
   of mapping file and place every LED as the file says.
5. The firmware drives one output per leg for all twenty legs of the target file.
   - This is established first, by itself, on the board: twenty outputs of 180 LEDs
     refreshing 50 times a second.
   - If twenty outputs cannot be driven from one board, the finding is written down with what
     was tried and measured, the firmware keeps the largest number of outputs that works, and
     the rest of this seed is still completed.
6. The emulator's LEDs view and mapping view show the 60 x 60 canvas with twenty upright
   snakes clearly, in a wide and in a narrow window: the board, a line from each of the
   twenty pins to the start of its snake, each snake's path up and down its three columns,
   and the LED numbers at the strip ends. The views still show row legs correctly.
7. The demo show is for the target: Hello world and DVD bounce made for 60 x 60, alternating
   every 15 seconds and starting at power-on. It replaces the ten-leg demo show.
8. `docs/mapping.md`, `docs/decisions.md`, `docs/format.md`, the emulator and firmware
   documents and the README describe the target and both kinds of leg. No document still
   presents 60 x 30, ten legs or horizontal strips as the target.
9. The table of measured sizes in `docs/format.md` gains the dense test clip at 60 x 60, and
   the statement of how much dense content fits in the board's storage is recomputed.
10. Tests of the converter, the core and the emulator that used a 60 x 30 clip or the
    ten-leg mapping cover 60 x 60 and the twenty-leg mapping.

## Definition Of Done

1. All test suites pass.
2. For the twenty-leg mapping, the LED data the core produces for each leg equals the
   reference computed independently in the test, for Hello world, DVD bounce and a dense
   clip.
3. The core's measured working memory for 60 x 60 with 100 items is under 128 KB and is
   reported.
4. The emulator holds 49 or more refreshes per second on the 60 x 60 demo show and on a
   dense 60 x 60 animation.
5. The test that compares `docs/mapping.md` with the mapping files passes, and fails when a
   mapping file is changed without regenerating the page.
6. On the board, with the target mapping installed and a dense 60 x 60 animation playing,
   `status` reports 49 or more refreshes per second, for the compressed file and for the
   uncompressed file, with the number of outputs the firmware drives stated. Start-up time is
   measured and reported.
7. Afterwards the board is left running the two-leg bench show, autostarting, at brightness
   40 or less.

## Open Questions

None. Use the resolved behavior in this seed.
