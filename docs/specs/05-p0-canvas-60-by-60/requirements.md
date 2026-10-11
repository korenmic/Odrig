# Requirements: Canvas 60 by 60 (seed 05)

Source seed: `project-seeds/05-p0-canvas-60-by-60/seed.md`. It depends on seeds 01 to 04,
which are implemented: the package `odrig`, the core in `core/`, the emulator with its page,
the command tool `odrigctl`, and the firmware with its tool `firmware/fw.py`. This seed
changes that code. These requirements rely on the code as it is; where the code differs
from what the four earlier specs say, the code is what counts.

`docs/format.md`, `docs/mapping.md`, `docs/show.md`, `docs/commands.md` and
`docs/reasons.md` define the behaviour. This seed changes `docs/mapping.md`: the mapping
file format gains legs that are columns. Where the seed and the documents leave a point
open, the answer used here is recorded in `docs/drifts.md` under "Seed 05".

Requirements of the earlier specs that name the ten-leg mapping, the 60 x 30 canvas or
`shows/demo-10` are replaced by the requirements below. The earlier spec files are not
edited.

Terms:

- **strip**: one straight run of LEDs of a leg: a row or a column of the canvas.
- **row leg**, **column leg**: a leg whose strips are rows, or columns.
- **row-leg file**, **column-leg file**: a mapping file whose legs are all row legs, or all
  column legs.
- **strip length**: the number of LEDs in every strip of a file: its `width` in a row-leg
  file, its `height` in a column-leg file.
- **the target file**: `mapping/legs-20.json`. **the bench file**: `mapping/legs-2.json`.
- **the converter**: the Python package `odrig`.
- **the core**: the C++ library in `core/`.
- **the page**: the web page the emulator serves; its **LEDs view** and its **mapping
  view**.
- **drawing area**: the part of the page's window that the drawing has. A window of
  1280 x 800 leaves it 1280 x 546.
- **cell**: the square of the drawing that one LED has, in pixels.
- **feed edge**: the edge of the canvas at which most legs of a file have their first LED.
- **the board**: the ESP32-S3-N16R8 of `docs/decisions.md`, connected over USB, with one
  60-LED strip wired to pin 1 and fed from the board's 3.3 V pin.
- **the firmware**, **the usermod**, **the tool**, **probe build**, **output**: as in the
  seed 04 requirements.
- **parallel driver**: the driver of WLED that sends several outputs in one transfer.
- **reference**: what a test computes by itself: the reference decoder of the converter
  followed by the rule of `docs/mapping.md`, written out in the test's own code.

## Requirement 1: A mapping file describes legs as rows or as columns

**User Story:** As the owner of an installation whose strips stand upright, I want the
mapping file to say so, so that the board and the emulator place every LED where it really
is.

### Acceptance Criteria

1. A mapping file SHALL be a row-leg file or a column-leg file. All legs of one file SHALL
   be of one kind.
2. A row-leg file SHALL be what a mapping file is today: the top-level members `version`,
   `width` and `legs` and no other, and in each leg the members `leg`, `pin`, `first_led`
   and `rows` and no other, with a `first_led` of `"left"` or `"right"`.
3. A column-leg file SHALL have the top-level members `version`, `height` and `legs` and no
   other. `height` SHALL be the number of LEDs in every column, an integer from 1 to
   65,535. Each leg SHALL have the members `leg`, `pin`, `first_led` and `columns` and no
   other. `columns` SHALL be an array of one or more integers: the canvas column (x) of
   each strip of the leg, in chain order. `first_led` SHALL be `"bottom"` or `"top"`: the
   end of the leg's first column where its first LED sits.
4. In a column-leg file the canvas height H SHALL be the file's `height`, the canvas width W
   SHALL be the total number of columns in the file, and the columns of all legs together
   SHALL hold every x from 1 to W exactly once.
5. The rules that do not depend on the kind SHALL hold for both: the file is read as
   strictly as a JSON frames file; `version` is 1; `legs` is an array of one or more
   objects; every `leg` is an integer from 1 to 255 and no two legs have the same number;
   every `pin` is an integer from 0 to 255 and no two legs have the same pin; a leg may
   have any number of strips, and the legs need not have the same number; W * H is at most
   65,534.
6. A file SHALL be invalid when it has both `width` and `height` or neither; when a leg of
   a column-leg file has `rows`, or a leg of a row-leg file has `columns`, or a leg has
   both or neither; and when a `first_led` is not one of the two values of the file's kind.
7. A file that breaks any rule SHALL be refused with the reason `mapping-malformed`, and a
   file that does not exist with `mapping-missing`. No reason name SHALL be added.
8. Every row-leg file that was valid before this seed SHALL be valid and SHALL mean the
   same. `mapping/legs-2.json` SHALL keep its bytes.

## Requirement 2: Every LED of a column leg has one place

**User Story:** As someone who writes a reader of the mapping file, I want one rule that
says which canvas pixel each LED of a column leg shows, so that every reader gives the
same answer.

### Acceptance Criteria

1. A leg whose `columns` has C entries SHALL have H * C LEDs. For LED number n, counted
   from 1 at the end wired to the board: s = (n - 1) div H is the position of its column
   in `columns`, and i = (n - 1) mod H is how far along that column it is. Its x SHALL be
   `columns[s]`.
2. The column SHALL start at the `first_led` end when s is even and at the opposite end
   when s is odd. Its y SHALL be 1 + i when the column starts at the bottom and H - i when
   it starts at the top.
3. The rule for a row leg SHALL stay as `docs/mapping.md` has it.
4. Coordinates and pixel order SHALL stay as `docs/format.md` has them: (1,1) is the
   bottom-left pixel, and pixel (x, y) is at position (y - 1) * W + (x - 1).

## Requirement 3: The target mapping file

**User Story:** As the owner of the installation, I want one tracked file that describes
the target build, so that the board, the emulator and the documents all use it.

### Acceptance Criteria

1. `mapping/legs-20.json` SHALL be a column-leg file with `version` 1, `height` 60 and
   twenty legs, listed in the order of their numbers. Leg N SHALL have the columns 3N - 2,
   3N - 1 and 3N, in that order, and a `first_led` of `"bottom"`. Legs 1 to 18 SHALL be on
   pins 1 to 18, leg 19 on pin 21 and leg 20 on pin 47.
2. The file SHALL describe a canvas of 60 x 60 with 180 LEDs on every leg: LED 1 of leg 1
   at (1,1), LED 60 of leg 1 at (1,60), LED 61 at (2,60), LED 120 at (2,1), LED 121 at
   (3,1), and LED 180 of leg 20 at (60,60).
3. `mapping/legs-10.json` SHALL be removed. No tracked file SHALL name it, apart from the
   seeds, the specs, `docs/drifts.md` and the change log of `docs/decisions.md`.
4. `mapping/legs-2.json` SHALL stay as it is.

## Requirement 4: The converter reads both kinds

**User Story:** As someone who makes animations, I want the converter to take the canvas
from either kind of mapping file, so that I make content for the target the way I make it
for the bench build.

### Acceptance Criteria

1. The reader of the package `odrig` SHALL accept every valid file of both kinds and SHALL
   give: the kind, W, H, and for each leg in file order its number, its pin, its
   `first_led`, its strips in chain order and its number of LEDs.
2. The reader SHALL refuse every invalid file with `mapping-malformed`, with a detail that
   says which rule is broken, and a missing file with `mapping-missing`.
3. The generators, `import` and `pack` SHALL take the canvas size from the mapping file of
   either kind. WHEN they are given the target file THEN the canvas SHALL be 60 x 60.
4. `pack` SHALL copy the mapping file into the show folder byte for byte, and SHALL refuse
   a source of another canvas size with `size-mismatch`, for both kinds.
5. The subcommands of `python -m odrig`, their options, their output and their exit
   statuses SHALL stay as they are.

## Requirement 5: The core reads both kinds and places every LED

**User Story:** As someone who made a show for the target, I want the core to send every
leg the pixels of its own columns, so that the picture on the installation is the picture
I made.

### Acceptance Criteria

1. The core SHALL accept every valid mapping file of both kinds and SHALL refuse every
   invalid one with `mapping-malformed` and no legs. For every file of the suite its
   judgement SHALL be the converter's.
2. The core SHALL list the legs in file order, each with its number, its pin and its number
   of LEDs: the strip length times its number of strips.
3. After every refresh, LED n of a leg SHALL hold the colour of the pixel that
   Requirement 2, or the row rule of `docs/mapping.md`, gives it.
4. WHEN the target file is installed THEN, for Hello world, for DVD bounce and for a dense
   clip, each made for 60 x 60, the LED data of every leg at every refresh of one loop
   SHALL equal the reference.
5. The host interface `core/include/odrig_core.h` SHALL keep every function and every type
   as it is. The emulator's binding and the firmware's usermod SHALL need no change to
   host a column-leg file.
6. The core SHALL ask for memory only at startup, in the blocks it asks for today. WHEN the
   target file is installed with a show of 100 items, 80 animations with a file each and 20
   cycles of 10 entries, THEN the memory it asks for SHALL be below 131,072 bytes. The
   suite SHALL measure it, and `docs/core.md` SHALL state the figure for every block.
7. The core SHALL keep the rules of seed 02: C++11, no exception, no allocation after
   startup, nothing of a platform.

## Requirement 6: The emulator and the command tool run the target

**User Story:** As someone without twenty legs on the desk, I want the emulator to run the
target show, so that I see it before it is built.

### Acceptance Criteria

1. The emulator SHALL run a show folder whose `mapping.json` is a column-leg file with no
   option and no setting for it.
2. WHEN the emulator runs a show on the target file THEN the `hello` event SHALL list
   twenty legs, each with its number, its pin and 180 LEDs, a refresh SHALL have 10,800
   bytes, and `GET /show/mapping.json` SHALL give the target file byte for byte.
3. WHEN the demo show of Requirement 14 is recorded for 31 seconds THEN the LED data of
   every leg at every tick SHALL equal the reference.
4. WHEN the emulator runs the demo show, or a dense 60 x 60 clip of 10 seconds on the
   target file, compressed or uncompressed, on this Mac THEN `status` SHALL report 49 or
   more in `fps` for every full second.
5. The command tool SHALL need no change. WHEN its commands are sent to an emulator that
   runs the demo show THEN every reply SHALL be as `docs/commands.md` defines it.

## Requirement 7: The page places the LEDs of both kinds itself

**User Story:** As someone checking a mapping, I want the page to work out every LED's
place from the mapping file alone, so that a mistake in the core shows as a wrong picture.

### Acceptance Criteria

1. The page SHALL work out where LED n of a pin is from that pin, n and the show's
   `mapping.json`, by the rule of the file's kind, and SHALL never reorder or correct the
   bytes of a refresh.
2. For every mapping of the suite, the tracked files and made-up files of both kinds, the
   place the page gives every LED SHALL be the reference's, and the LED the page finds at
   every canvas position SHALL be the one that is there.
3. The rule SHALL be written in `emulator/web/layout.js` only, and that file SHALL run
   without a browser.
4. WHEN the `first_led` of one leg of the target file is changed from `"bottom"` to `"top"`
   in a recording's mapping THEN every column of that leg SHALL be reversed and no LED of
   another leg SHALL move.

## Requirement 8: The LEDs view shows upright legs

**User Story:** As someone judging an animation for the target, I want to see the whole
60 x 60 canvas with its twenty legs, so that I know what the installation will show.

### Acceptance Criteria

1. The LEDs view SHALL draw every LED of a column-leg file as a dot at its canvas position,
   with (1,1) at the bottom-left, x growing to the right and y growing upward.
2. Each leg SHALL have one colour. A faint band of the colour SHALL lie behind the leg's
   columns, and a bracket in the colour SHALL span them on the side of the canvas away from
   the feed edge, with the leg's number and its pin. A leg whose columns are not
   neighbours SHALL get a bracket for each run of neighbouring columns.
3. The twenty legs of the target file SHALL have twenty different colours.
4. The view SHALL mark the rows y = 1, every tenth row and the top row beside the canvas,
   and the columns x = 1, every tenth column and the last column above or below it.
5. WHERE the cells are 9 pixels or more, the view SHALL show at the two ends of every
   column the numbers of the LEDs that sit there.
6. WHEN the target file is shown in a drawing area of 1280 x 546 THEN the whole canvas with
   its labels SHALL be in the area, with nothing to scroll, and the cells SHALL be 7 pixels
   or more.
7. WHEN the target file is shown in a drawing area 500 wide and 546 high THEN the whole
   canvas with its labels SHALL be in the area and the cells SHALL be 7 pixels or more.
8. A dark LED SHALL stay visible as a faint ring, the drawing SHALL be drawn again when the
   window changes its size, and colour values SHALL be shown through the one display curve,
   as today.
9. WHEN the demo show or the dense 60 x 60 clip runs on this Mac THEN the page SHALL draw
   49 or more refreshes in every full second.

## Requirement 9: The mapping view shows the board, twenty lines and twenty snakes

**User Story:** As someone wiring the installation, I want to see which pin feeds which
leg and how each snake runs up and down its columns, so that I can wire it and trust the
mapping file.

### Acceptance Criteria

1. The mapping view SHALL draw the board as `docs/mapping.md` has it: the antenna at the
   top, the two USB sockets at the bottom, and its two rows of pins with their labels in
   that order.
2. For every leg the view SHALL draw a line from the pad of the leg's pin to the first LED
   of the leg's chain. The line SHALL end in an arrow head at that LED, and the number 1 of
   that LED SHALL sit on the line as a tag.
3. Every line SHALL be made of level and upright pieces. No two lines SHALL lie on each
   other, no line SHALL pass through the board or over an LED, and two lines SHALL cross at
   most once, at a right angle.
4. For every leg the view SHALL draw the path of the chain through the centres of the LEDs
   of every column in chain order, behind the dots, with arrows along every column that
   show the way the LED numbers grow, a turn outside the top or the bottom edge of the
   canvas into the next column, and a bar where the chain ends.
5. The view SHALL show the LED numbers at the two ends of every column, in the leg's
   colour, with no number drawn over another.
6. Each leg SHALL have one colour, used for its pad, its line, the path of its chain, the
   outline of its columns, its numbers and its labels.
7. WHEN the pointer is on a leg's label, its pad, its line or its columns THEN the view
   SHALL highlight that leg in all these places and SHALL fade the other legs. WHEN the
   pointer is on an LED THEN the readout SHALL name the leg, the pin, the LED number and
   the canvas coordinates.
8. WHEN the target file is shown in a drawing area of 1280 x 546 THEN the board SHALL stand
   beside the canvas, the cells SHALL be 9 pixels or more, and the drawing SHALL be no
   wider than the area. It may be higher than the area; the stage then scrolls up and
   down.
9. WHEN the target file is shown in a drawing area 756 wide THEN the board SHALL stand
   below the canvas, the cells SHALL be 9 pixels or more, and the drawing SHALL be no wider
   than the area.
10. Everything the view draws about legs SHALL come from `mapping.json`: other pins, a
    `first_led` of `"top"`, another order or number of columns, and legs with different
    numbers of columns SHALL be drawn without a change to the page. A pin the board does
    not have SHALL get a pad of its own, labelled `GPIO <pin>`.
11. The LEDs of the mapping view SHALL be live, as in the LEDs view.

## Requirement 10: Row legs are drawn as before

**User Story:** As someone at the bench with two legs of rows, I want the page to look as
it did, so that this seed takes nothing away.

### Acceptance Criteria

1. For a row-leg file both views SHALL be drawn by the rules they have today: the bracket
   and the `y` of every row, the LED numbers at the ends of every row, and in the mapping
   view the board beside or below the canvas with the lines in their channel.
2. For the bench file the place and the size of every part SHALL be what they are today,
   in every drawing area the suite names.
3. The colours of the first twelve legs of a file SHALL stay as they are.

## Requirement 11: docs/mapping.md is written by a tool and checked by a test

**User Story:** As a maintainer, I want the drawings and tables of the mapping page to come
from the mapping files, so that the page cannot say something the files do not.

### Acceptance Criteria

1. `python -m odrig.mapdoc` SHALL write the generated parts of `docs/mapping.md` from the
   tracked files: the drawing of the board with the pads of the target file's legs marked,
   and for each of the bench file and the target file a drawing and a table.
2. For a row-leg file the drawing SHALL have one line for each row, from the top row down,
   with the LED numbers at x = 1 and x = W, an arrow that points the way the numbers grow,
   and the leg and the pin beside the leg's first row. For a column-leg file it SHALL have
   one line for each column, from x = 1 on, with the LED numbers at y = 1 and y = H, the
   arrow, and the leg and the pin beside the leg's first column.
3. The table SHALL have one line for each leg: its number, its pin, its rows or columns in
   chain order, and the canvas position of the first and of the last LED of every strip.
4. For the bench file the tool SHALL write exactly the drawing and the table the page has
   today.
5. The drawing of the board SHALL name, beside each of the twenty pins of the target file,
   the leg that is wired to it, and SHALL keep the two rows of labels in the order of the
   real board.
6. The tool SHALL change nothing outside the generated parts, SHALL use only the Python
   standard library, and SHALL write the same bytes on every run.
7. `python -m odrig.mapdoc --check` SHALL write nothing. It SHALL exit with status 0 when
   the page holds what the tool would write, and with status 1 and a line that names the
   part that differs when it does not.
8. A test of the converter's suite SHALL fail when the page and the mapping files
   disagree: it SHALL run the check on the tracked files, and SHALL show that the check
   fails after a pin, a `first_led` or the order of two columns of a mapping file is
   changed without the page being written again.
9. The two rows of pin labels the page of the emulator uses SHALL be those of the generated
   drawing, and a test SHALL compare them.

## Requirement 12: The firmware drives one output for each of the twenty legs

**User Story:** As the owner of the installation, I want one board to drive all twenty
legs, so that the target needs one board, one show and one clock.

### Acceptance Criteria

1. WHEN the target file is installed THEN the usermod SHALL make one output for each of the
   twenty legs, in the order of the file, on the leg's pin, with 180 LEDs, for WS2812B LEDs
   with the colour order green, red, blue, and all twenty SHALL work.
2. Every change this needs to a file of WLED SHALL exist only as a patch file in
   `firmware/patches/`, applied by `python3 firmware/fw.py build`. `build --stock` SHALL
   apply no patch.
3. The first four legs of the file SHALL get WLED's RMT outputs and the next sixteen the
   parallel driver.
4. WHILE WLED's current limiter does not dim, every output SHALL hold exactly the bytes the
   core gives its leg. WHEN the limiter dims to its lowest level THEN every output SHALL
   hold exactly what that dimming makes of its own leg's bytes.
5. The pin of every output SHALL carry the signal of a whole refresh: the probe build SHALL
   count 24 pulses for every LED of the output in one refresh, on each of the twenty pins.
6. The parallel driver SHALL be busy after a send for the time its LEDs take on the wire:
   between 4.5 and 7.5 ms for legs of 180 LEDs.
7. WHEN twenty outputs of 180 LEDs show a picture that does not change THEN the firmware
   SHALL send 49 or more refreshes in every full second.
8. Criteria 1 to 7 SHALL be established on the board before any other work of this seed,
   with a mapping file of today's format: twenty row legs of three rows of 60 on the pins
   of the target file.
9. IF twenty outputs cannot be driven from the board THEN `docs/firmware.md` and
   `docs/decisions.md` SHALL say what was tried and what was measured, the firmware SHALL
   keep the largest number of outputs that works, the outputs beyond that number SHALL be
   named in WLED's information as not working, the core SHALL run unchanged, and every
   other requirement of this seed SHALL still be met, with that number stated wherever a
   document or a test names the number of outputs.
10. IF one of the pins 1 to 18, 21 and 47 cannot carry an output on this board THEN the
    finding and the pin that takes its place SHALL be recorded in `docs/drifts.md`, and the
    target file SHALL name that pin.
11. Everything else the firmware does SHALL stay as the seed 04 requirements have it: the
    core's sources are used as they are, the limiter stays active, WLED's settings file is
    not written for the outputs, an output that cannot be made does not stop the others,
    and the USB serial port and `POST /odrig` carry the commands.

## Requirement 13: The board plays the target at 50 refreshes a second

**User Story:** As someone who made a dense show for the target, I want the board to keep
the frame rate, so that motion looks on the installation as it does in the emulator.

### Acceptance Criteria

1. WHEN the target file and a dense 60 x 60 clip of 10 seconds are installed THEN `status`
   on the board SHALL report 49 or more in `fps` for every one of ten full seconds in a
   row, for the compressed file and for the uncompressed file.
2. WHEN the bench show is installed THEN `status` SHALL report 49 or more in `fps` as it
   does today.
3. Every refresh the core counts SHALL have been sent to the outputs, so that `fps` is the
   board's real rate.
4. The following SHALL be measured on the board and written into `docs/firmware.md`: the
   number of outputs the firmware drives; the time the core takes to start, for the demo
   show of Requirement 14 and for the dense clip, compressed and uncompressed; the
   refreshes sent in a second; the longest time between two sends; the mean and the longest
   time of a request for a refresh and of a send; the free internal memory; and the time
   `install-show` takes.
5. IF `fps` stays below 49 after the steps the design names THEN the measured rates SHALL
   be written into `docs/firmware.md` and into the open questions of `docs/decisions.md`,
   and the seed's state SHALL stay `in_progress`.

## Requirement 14: The demo show is for the target

**User Story:** As the owner of the installation, I want a ready show for the 60 x 60
canvas, so that I can see the target work in the emulator and on the board.

### Acceptance Criteria

1. `shows/demo-20/show.json` SHALL be tracked and SHALL hold: item 1, the animation
   `hello.odrg`; item 2, the animation `dvd.odrg`; item 3, a cycle of items 1 and 2 with
   `seconds` 15; `start` 3; and `brightness` 128.
2. The two sources SHALL be written by the Hello world and DVD bounce generators with the
   target file, which gives them the 60 x 60 canvas. No canvas size SHALL be written
   anywhere for this show. The sources and the packed show SHALL not be tracked.
3. `shows/demo-10/` SHALL be removed, and no tracked file SHALL name it, apart from the
   seeds, the specs, `docs/drifts.md` and the change log of `docs/decisions.md`.
4. WHEN the packed demo show plays THEN Hello world SHALL stand in the rows 28 to 33,
   upright and centred, and the square of DVD bounce SHALL pass over LEDs of all twenty
   legs. The generators SHALL stay as they are: the sources of the bench show keep their
   bytes.
5. The documentation SHALL give the commands that write the two sources and pack the show
   into `build/demo-20/show`.

## Requirement 15: The tests cover the target, and nothing assumes rows, three strips or a size

**User Story:** As a contributor, I want the suites to exercise the target and odd
layouts, so that a hidden assumption about the canvas is found by a test.

### Acceptance Criteria

1. Every test of the converter, the core and the emulator that used a 60 x 30 clip or the
   ten-leg mapping SHALL use a 60 x 60 clip and the target file.
2. The suites of the converter, the core and the emulator SHALL also run on made-up
   column-leg files: a leg that starts at the top; legs of two and of four columns in one
   file; columns that are not neighbours and not in order; a strip length that is not 60;
   and a canvas of one LED.
3. The converter, the core, the emulator, the page, the command tool, the tool of the
   firmware and the usermod SHALL take the canvas size, the strip length, the number of
   legs and the number of strips of a leg from the mapping file only.
4. Each of the four suites that need no board SHALL be selected by discovery in its folder
   and SHALL pass: `tests/converter/`, `tests/core/`, `tests/emulator/` and
   `tests/firmware/`.
5. The tests that need the board SHALL stay in `tests/board/`, run only by
   `python3 firmware/fw.py test-board`, and SHALL pass on the board.

## Requirement 16: The documents describe the target and both kinds of leg

**User Story:** As a newcomer, I want every document to describe the installation as it is
planned now, so that I do not build for a canvas that was given up.

### Acceptance Criteria

1. `docs/mapping.md` SHALL describe both kinds of mapping file, every rule, where each LED
   is for both kinds, the bench build and the target build, and what is confirmed on the
   hardware.
2. `docs/decisions.md` SHALL state the target and both kinds of leg in its section on the
   canvas, SHALL state what was measured for its open question about twenty outputs, and
   SHALL have an entry in its change log.
3. The table of measured sizes in `docs/format.md` SHALL have a row for the dense clip at
   60 x 60, and the document SHALL say how many seconds of dense 60 x 60 content fit into
   the board's storage. `docs/decisions.md` SHALL state the same figure.
4. `docs/emulator.md` SHALL describe the two views for both kinds of leg, the two shows to
   run, and a check list by eye with steps for the twenty-leg views.
5. `docs/firmware.md` SHALL state how many outputs the firmware drives and how, what the
   patch changes in WLED, the measurements of Requirement 13, and what a person has still
   to check.
6. `docs/core.md`, `docs/converter.md`, `docs/reasons.md` and `README.md` SHALL describe
   both kinds of leg wherever they describe a leg, and SHALL name the target wherever they
   name one.
7. No document SHALL present 60 x 30, ten legs or horizontal strips as the target. The
   change log of `docs/decisions.md`, `docs/drifts.md`, the seeds and the earlier specs
   keep what they recorded.

## Requirement 17: The board is handled safely and left as it was found

**User Story:** As the owner of the board, I want this seed to leave it running the bench
show, so that the bench works when I come back to it.

### Acceptance Criteria

1. Every show a task or a test installs on the board SHALL have a brightness of 40 or
   less. No task SHALL rely on anybody seeing the LEDs.
2. WHEN the last task that touches the board ends THEN the board SHALL run the firmware
   with the bench show at a brightness of 40 or less, playing from its start with no
   command sent, and `status` SHALL report `"playing":3` and no reason.
3. The rules of seed 04 for the board SHALL hold: nothing is written to the factory backup,
   no fuse is written, the whole flash is never erased, and stock WLED can be restored.

## Requirement 18: What needs eyes is listed, and a program does the rest

**User Story:** As the owner, who is not at the desk, I want the seed to finish with
everything a program can establish, and to find a short list of what is left for my eyes.

### Acceptance Criteria

1. The check list by eye of `docs/emulator.md` SHALL have a numbered step, with what to do
   and what must be seen, for each of: Requirement 8 criteria 2, 6 and 9, Requirement 9
   criteria 2 to 5, 8 and 9, and Requirement 10 criterion 1.
2. The steps SHALL be gone through in current Chrome by a person or by a tool that drives
   the browser and takes screenshots that are looked at, and the document SHALL say what
   was checked and how.
3. `docs/firmware.md` SHALL list as owner's checks what no program on this Mac can
   establish: that a strip on a pin of the parallel driver shows its picture, and that
   twenty wired legs show the demo show.
4. The seed SHALL be completed when every other requirement is met and criterion 2 is
   done. The owner's checks of criterion 3 and a pass through the check list in Safari
   SHALL stay listed as open and SHALL not hold the seed open.
