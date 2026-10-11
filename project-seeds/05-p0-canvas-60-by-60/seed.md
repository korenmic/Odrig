# Canvas 60 by 60

## Summary

Bring the whole project to the new target canvas of 60 columns by 60 rows, 3,600 LEDs: the
target mapping, the documents, the demo show, the emulator's views, the limits the code is
tested against, and the measurements on the board.

## Priority

- `P0`

## Depends On

- Seeds 01 to 04, which built everything this seed resizes.

## Product Context

The target was 60 x 30. The owner changed it to 60 x 60, a square canvas.

The firmware drives at most 12 LED outputs, so 20 legs of three rows cannot each have a pin.
In the target build the ten legs stay on pins 1 to 10 and each leg carries six rows: one
chain of 360 LEDs snaking through six rows of 60.

A leg is therefore one data pin together with the rows wired to it as one snake. Today's
bench build has two legs of three rows (60 x 6) and stays as it is.

Much of what exists was written, tested or drawn for three rows per leg and for 60 x 30: the
target mapping file, the drawings in `docs/mapping.md`, the demo show, the wording and layout
of the emulator's mapping view, test clips, the memory limit, and the board measurements.

## Technical Constraints

- The mapping file format does not change. It already allows any number of rows per leg.
- Nothing may assume three rows per leg or a particular canvas height: the core, the
  emulator and its page, the tools, the firmware code, the tests and the documents.
- The core's working memory for the 60 x 60 canvas with 100 items stays under 128 KB.
- A chain of 360 LEDs takes about 11 ms to send. Sending must fit inside the 20 ms refresh.
- The drawings and tables in `docs/mapping.md` are produced from the mapping files by a
  tracked tool, and a test fails when the page and the files disagree.
- Tests that need the board are kept apart from those that do not.
- On the board, only one 60-LED strip is attached, on leg 1, powered from the 3.3 V pin.
  Anything shown on the board uses brightness 40 or less.

## Required Behavior

1. `mapping/legs-10.json` describes the target build: ten legs on pins 1 to 10, each with six
   rows, leg 1 holding rows 60 to 55 at the top and leg 10 holding rows 6 to 1, every chain
   starting at the right end of its top row.
2. `mapping/legs-2.json` is unchanged.
3. `docs/mapping.md`, `docs/decisions.md`, `docs/format.md`, the emulator and firmware
   documents and the README describe the 60 x 60 target and the meaning of a leg given above.
   No document still presents 60 x 30 or three rows per leg as the target.
4. The table of measured sizes in `docs/format.md` gains the dense test clip at 60 x 60, and
   the statement of how much dense content fits in the board's storage is recomputed.
5. The demo show holds Hello world and DVD bounce made for 60 x 60, alternating every 15
   seconds and starting at power-on.
6. The emulator's LEDs view and mapping view show the 60 x 60 canvas with six-row snakes
   clearly, in a wide and in a narrow window. The mapping view shows each snake's whole path
   and its LED numbers at the row ends for any number of rows.
7. Tests of the core, the converter and the emulator that used a 60 x 30 clip or mapping
   cover 60 x 60.
8. The firmware accepts ten outputs of 360 LEDs set from the target mapping file.

## Definition Of Done

1. All test suites pass.
2. The core's measured working memory for 60 x 60 with 100 items is under 128 KB and is
   reported.
3. The emulator holds 49 or more refreshes per second on the 60 x 60 demo show, and on a
   dense 60 x 60 animation.
4. The test that compares `docs/mapping.md` with the mapping files passes, and fails when a
   mapping file is changed without regenerating the page.
5. On the board, with the target mapping installed and a dense 60 x 60 animation playing,
   `status` reports 49 or more refreshes per second, for the compressed file and for the
   uncompressed file. Start-up time is measured and reported.
6. Afterwards the board is left running the two-leg bench show, autostarting, at brightness
   40 or less.

## Open Questions

None. Use the resolved behavior in this seed.
