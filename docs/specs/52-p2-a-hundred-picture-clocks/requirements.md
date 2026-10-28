# Requirements: a hundred picture clocks

Seed: [`project-seeds/52-p2-a-hundred-picture-clocks/seed.md`](../../../project-seeds/52-p2-a-hundred-picture-clocks/seed.md).

The owner's picture `its not the time frames.png` holds 100 pixel-art timekeepers in a grid
of 10 by 10. This spec makes one animation of 60 x 60 and at most 8 colours of each tile,
and twelve more of the owner's ideas of time that is not the time. A tile with a dial
becomes a picture dial, and one with digits a picture display: two new widgets of the
widget payload of [format.md](../../format.md), which carry the tile's picture with its
hands or digits erased, and over which the player draws the hands or the digits of a
virtual time that runs at a random speed and in a random direction. A tile that shows no
time becomes frames that move as the tile suggests. The twelve become frames rendered from
their own scripts. The files, their previews and readmes are tracked in the collection,
`collection/card/clocks/`, as `collection/README.md` says, and their sources beside the
seed.

The seed has no open questions. The owner approved the two widgets on 2026-10-28 by asking
for the seed. The choices the seed leaves to the spec are made in
[design.md](design.md) and recorded at the end of [drifts.md](../../drifts.md) under
"Seed 52" by the task that applies each.

In this document "the core" is the C++ player of `core/`; "the converter" the JavaScript
tool and library of `converter/`; "a tile" one of the 100 pictures of the owner's grid,
numbered 1 to 100 by its place in reading order; "the twelve" the six demos of the
owner's conversation and the six of the standalone page; "a turn", "the seed" and "the
virtual time" are those of [format.md](../../format.md), "The widget payload"; "the
inventory" the JSON file that says, for each tile, what it becomes; "the collection" the
folder of seed 46, on this computer the share `E:\artifacts\odrig\collection`.

## Requirement 1: the picture dial and the picture display in the format

1. The widget payload SHALL know two more widgets beside 1 `analog`, 2 `digital` and 3
   `melting`: 4 `picture-dial` and 5 `picture-display`. The payload of widgets 1 to 3
   SHALL stay as it is, 20 bytes, and those files SHALL play as before.
2. The payload of a picture widget SHALL hold the loop in seconds, the least and the
   greatest speed as the existing clocks have them, a direction, a chance of turning, its
   parts, and its base picture.
3. The base picture SHALL be an ODRG file of [format.md](../../format.md) for the
   container's canvas, of one frame and a palette of 1 to 8 colours, at the end of the
   payload, compressed as the format compresses a picture.
4. A picture dial's parts SHALL be 1 to 8 hands and 0 to 4 caps. A hand SHALL have a
   unit (the hour, the minute or the second), a pivot in half pixels, a length and a tail
   behind the pivot, a half width, a colour of the palette and an offset of whole hours. A
   cap SHALL be a disc at a place, of a radius and a colour of the palette.
5. A picture display's parts SHALL be 1 to 4 fields. A field SHALL have a box of the
   canvas, a font, a pattern that says what it shows (the hour with or without its
   leading zero, the minutes, the seconds, colons and spaces), the colours of the digits
   and of the colons from the palette, whether the colons blink, and an offset of whole
   hours.
6. The direction SHALL be forward, backward, or chosen by the seed of the turn; a
   direction chosen by the seed SHALL also be able to turn at each of the swing's slowest
   points, at a chance the seed fixes between 0 and the payload's chance.
7. The largest payload of a widget SHALL be 32,768 bytes.
8. [format.md](../../format.md) SHALL give the bytes of both widgets, their JSON source,
   the virtual time with its direction, and the drawing, exactly enough that two readers
   written from it draw the same pixels.

## Requirement 2: reading and refusing a picture widget

1. Every reader (the converter, the core at each of its checks and at play, and the
   Python library's header reader) SHALL accept a picture widget that follows the format
   and SHALL refuse one that does not, with the reasons of [reasons.md](../../reasons.md),
   "Widgets in ODRGX", in the order there.
2. A base picture that is not of one frame, or whose palette has no colour or more than 8,
   SHALL be refused with the new reason `bad-picture`; one of another canvas with
   `canvas-mismatch`; one the ODRG reader refuses with that reader's reason.
3. A colour of a hand, a cap or a field that is not a colour of the palette, a value
   outside its range, a box outside the canvas and an unknown pattern character SHALL be
   refused with `bad-settings`; a font the reader does not have with `unknown-font`.
4. The existing vector `unknown-widget.four` SHALL become `unknown-widget.six`: 4 is now a
   widget.

## Requirement 3: the time a picture widget shows

1. A picture widget SHALL take from the seed of its turn the values the existing clocks
   take, in their order, and after them whether a turn chosen by the seed starts backward
   and its chance of turning.
2. Forward, its virtual time SHALL be that of an existing clock with the same seed and
   speeds; backward, it SHALL run the same way back from the same start.
3. With the direction chosen by the seed, the time SHALL reverse only at a slowest point
   of the swing, where the speed is least, and whether it reverses at the k-th such point
   SHALL follow from the seed and k alone.
4. A time of the turn SHALL have one picture, however the refreshes come.
5. Two turns of the same clock SHALL differ by their seeds as the existing clocks' turns
   do.

## Requirement 4: drawing a picture widget

1. A picture dial SHALL show its base picture with each hand drawn over it at the angle of
   its unit's time, in the order of the hands, and each cap over them.
2. A picture display SHALL show its base picture with each field's pattern drawn in its
   font, centred in its box and clipped to it, its colons shown in the first half of each
   real second when they blink.
3. The converter and the core SHALL draw the same pixels: reference pictures of picture
   widgets in `tests/vectors/procedural/` SHALL be drawn equal by the converter's library,
   by the core's test host and on the emulator's LEDs.
4. A font `tiny` of the ten digits, the colon and the space, 3 by 5 pixels, SHALL exist
   for the displays, generated from `fonts/` into the tables of the core and the converter
   as the other fonts are. A text SHALL NOT be able to use it.

## Requirement 5: no more memory

1. The core SHALL decode the base picture once a turn into the pixel buffer it has, and
   SHALL draw the hands or the digits over it as the LED data is made at each refresh,
   without writing into the pixel buffer.
2. The core SHALL ask for no new block, and its object SHALL keep its size: the memory
   table of [core.md](../../core.md) SHALL stay as it is, and a show with picture widgets
   SHALL ask for the same memory as the same show without them.

## Requirement 6: frames that move as a tile suggests

1. The converter SHALL make, from a base picture of at most 8 colours and a motion, a
   frames animation of the canvas that keeps those colours, at least 10 seconds long, that
   loops without a jump.
2. A motion SHALL be made of parts of these kinds: a level that falls and rises in a box;
   a flicker of two or three variants of a box; a turn of the pixels of a box about a
   point; a swing of them about a point; a slow pulse of a box through colours of the
   palette.
3. The same inventory SHALL give the same bytes on every computer.

## Requirement 7: the inventory and its subcommand

1. One inventory, a JSON file, SHALL say for each of the 100 tiles its name `clock-NNN`,
   its tile, its kind (dial, display or motion), its 8 colours or fewer, its base picture
   with its hands or digits erased, and its clock or its motion.
2. A subcommand of the converter, `clocks`, SHALL read the inventory strictly and write
   one file for each tile: `clock-NNN.odrgx` for a dial or a display and `clock-NNN.odrg`
   for a motion. Nothing else SHALL convert the tiles.
3. The inventory and the base pictures SHALL be kept beside the seed, in its `source/`.

## Requirement 8: the hundred

1. Each of the 100 tiles SHALL become one file, 60 x 60, of at most 8 colours, which
   `node converter/odrig.js check` accepts and the emulator plays.
2. The tiles with a dial (watches, wall, pocket, alarm, mantel, tower and station clocks,
   a stopwatch, a kitchen timer, a chess clock, the sundials' shadows) SHALL be picture
   dials; the tiles with digits SHALL be picture displays; the others SHALL be motions.
3. Each base picture SHALL be its tile scaled to 60 x 60 and reduced to its 8 colours,
   black among them when the tile has black, with the hands of a dial or the time of a
   display erased.

## Requirement 9: the twelve

1. Each of the twelve SHALL be a frames animation of 60 x 60 rendered from its own script
   in a headless Chrome with a profile of its own: the original six from
   `references/original/animation.js`, the standalone six from
   `references/standalone/standalone-script.js`.
2. Each SHALL hold whole periods: the original two times 18 s, never zero 16 s, sand 16 s,
   we were here 10 s, every row 720 s, the clock that melts 90 s; each standalone one
   18 s.
3. Its frames SHALL be 50 ms apart, or 100 ms apart when the file would be larger than
   2 MB at 50 ms.
4. Each SHALL have at most 8 colours: black, then the colours its script draws with, most
   used first; every other pixel SHALL take the nearest of them.
5. Each SHALL match its reference GIF at the same times, but for the 8 colours, and the
   largest difference SHALL be measured and recorded.
6. They SHALL be named `time-original-1-two-times.odrg` to
   `time-original-6-the-clock-melts.odrg` and `time-standalone-1-two-times.odrg` to
   `time-standalone-6-melting-clock.odrg`.

## Requirement 10: where the files go

1. The 112 files SHALL be in the collection's `collection/card/clocks/`, their path on the
   card `clocks/`, each with its preview `X.gif` and its readme `X.md` in the shape of
   `collection/README.md`, which names its source: the owner's picture and its tile, or
   its script and its reference GIF; and on the share at the same paths.
2. The previews SHALL be added to `thumbnails/` by `thumbnail --catalog thumbnails --card
   collection/card --beside`, as the collection keeps them, and committed with the files.
3. The owner's picture, the 100 cut tiles, the inventory, the base pictures and the
   scripts that made the files SHALL be kept beside the seed, in
   `project-seeds/52-p2-a-hundred-picture-clocks/source/`, tracked.

## Requirement 11: the app and the emulator

1. The emulator SHALL play the two new widgets through the core, with no code of its own
   for them.
2. The operators' app SHALL show a picture widget as it shows a clock, with its preview,
   and SHALL NOT offer to make or edit one: "Edit" on a picture widget SHALL say that it is
   made from a picture and change nothing.

## Requirement 12: the pages

1. `docs/format.md`, `docs/core.md`, `docs/reasons.md`, `docs/converter.md`,
   `docs/decisions.md` and `docs/android-app.md` SHALL say what exists; the change log of
   `docs/decisions.md` SHALL have the line of the approval; the line of `AGENTS.md` in
   "What is coming" SHALL say what is built and what is open while the owner's check is
   open.

## Requirement 13: the checks

1. Every suite that runs on Windows SHALL pass, as on `master` before the seed: the
   converter's two, the core's, the emulator's, the app's and the onboarding suite.
2. The 112 files SHALL play in the emulator, one after the other, from a drive, and each
   SHALL be listed and play.
3. A recording of a picture dial and of a picture display, each on two turns, SHALL show
   the hands or the digits moving, at different speeds or in different directions between
   the turns.
4. The owner's look at a selection of the clocks on the LEDs is the owner's check and
   stays open until the owner has made it.
