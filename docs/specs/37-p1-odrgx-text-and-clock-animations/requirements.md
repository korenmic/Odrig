# Requirements: ODRGX text and clock animations

Seed: [`project-seeds/37-p1-odrgx-text-and-clock-animations/seed.md`](../../../project-seeds/37-p1-odrgx-text-and-clock-animations/seed.md).

Today an animation is an ODRG file: a timeline of pictures that a computer or a phone
made. This spec adds a container, ODRGX, whose header says what its payload is: frames,
which are an ODRG file as it is; a text, which the player lays out and moves itself; or a
widget, a clock the player draws. A text or a clock file holds a description and its
settings, a few hundred bytes, not pictures. The core draws their pictures at every
refresh, on the board and in the emulator alike, and the app's preview draws the same
pixels with the same rules in JavaScript. Existing `.odrg` files play as before.

The owner answered the seed's questions on 2026-10-24: the fonts are in the firmware;
mixed Hebrew and English, with digits and punctuation, without niqqud; single and
multiline text; analog, digital and melting clocks with a fresh random variation each
time one plays; a text's pass is finished before the playlist moves on; clocks play 30
seconds by default. The choices the seed leaves to the specification were made under the
owner's mandate of 2026-10-24 and are recorded in [drifts.md](../../drifts.md), "Seed 37".

Seeds 35 (managed catalogs) and 36 (the app's new screens) are built at the same time on
other branches. This spec builds on today's upload path and today's app screens; what
needs those seeds is its last task, done after the branches are combined.

In this document "the core" is the C++ player of `core/`; "the converter" is the
JavaScript tool and library of `converter/`; "a pass" is one complete showing of a text,
from its first picture to its last; "a turn" is what the playlist or a cycle gives an
animation, as [show.md](../../show.md) says; "the virtual time" is the time a clock shows;
"a seed" is the 32-bit number that chooses a clock's variation.

## Requirement 1: the container

1. An ODRGX file SHALL begin with a header of 20 bytes: the magic `ODRX`, the container
   version 1, the content type (1 frames, 2 text, 3 widget), the type's own version, a
   reserved byte 0, the width and the height of the canvas, the length of one loop in
   milliseconds, and the length of the payload in bytes. The file SHALL be exactly the
   header and the payload.
2. The container's version, the content type and the type's version SHALL be three
   separate numbers: a new version of one type changes none of the others.
3. A frames payload SHALL be an ODRG file of [format.md](../../format.md) as it is, for the
   same canvas; its loop length SHALL be the sum of its frame durations.
4. Every reader SHALL dispatch by the header, not by the file's name: a file that begins
   with `ODRG` is an ODRG file, one that begins with `ODRX` is a container, whatever its
   name ends in.
5. An unknown container version, content type or type version, a reserved byte that is
   not 0, a payload length that is not the rest of the file, a payload that breaks its
   type's rules, a canvas other than the mapping's, and a loop length other than the one
   the payload gives SHALL each be refused with a reason of its own, named in
   [reasons.md](../../reasons.md), and SHALL never stop the show from being checked or the
   board from answering.
6. `.odrg` files SHALL be read, checked, played, listed, uploaded and removed exactly as
   today: the same bytes give the same pictures at the same times.

## Requirement 2: names and the file set

1. A file of a show SHALL be named with 1 to 32 characters of `a`-`z`, `0`-`9`, `-`, `_`
   and `.`, ending in `.odrg` or `.odrgx`, in `show.json`, in an upload and in the
   converter's `pack`.
2. A drive's file, on the microSD card or a USB stick or the emulator's folder, SHALL be
   taken when its name ends in `.odrg` or `.odrgx`, in any case.
3. An animation of any type SHALL be an ordinary item: listed, played, ordered, included
   or ignored, uploaded, replaced and removed by the commands of today, and part of the
   playlist after the items before it.

## Requirement 3: the text, its characters and its fonts

1. A text SHALL be UTF-8 of 1 to 512 bytes, and SHALL be kept in the file as it was
   written, with its settings, so that it can be read back and edited.
2. The characters a text may hold SHALL be the printable ASCII characters, the 27 Hebrew
   letters with the five final forms among them, and the line feed. Any other character,
   niqqud and emoji among them, SHALL be refused before a file is made, with a message
   that names the character and its code point; no character is ever dropped.
3. The player SHALL have three fonts, made for this project as pixel fonts by hand:
   `small`, 7 pixels from the baseline to the top of a capital; `medium`, 10 pixels; and
   `large`, `small` drawn twice as big. Each SHALL have a glyph for every character of
   3.2 but the line feed, and an identity and a version that a text file names.
4. The fonts' glyphs SHALL be kept in one place in the repository, as text that shows
   the pixels, from which the core's tables and the converter's are generated; a test
   SHALL fail when either generated file is not what the sources give.
5. A file that names a font or a font version the player does not have SHALL be refused
   with `unknown-font`.

## Requirement 4: the layout of a text

1. Mixed Hebrew and English SHALL be put in order by the Unicode Bidirectional Algorithm
   for the characters of 3.2: the paragraph's direction, the weak types of digits and
   their separators and terminators, the neutrals, the levels, the reordering of each
   line, and the mirroring of brackets in right-to-left runs. A paragraph's direction is
   that of its first strong letter, or the one the text's setting forces.
2. A line feed SHALL begin a new paragraph. With wrapping on, a paragraph SHALL be broken
   into lines no wider than the canvas, at spaces, and a word wider than the canvas at
   its characters; with wrapping off, each paragraph SHALL be one line.
3. Each line SHALL be aligned left, in the centre or right within the block of text, and
   the block SHALL be placed on the canvas by a horizontal and a vertical alignment.
4. Moving the text SHALL never mirror a glyph or change the order of a run: the reading
   order is that of the layout, and the motion moves the block as a whole.
5. The layout SHALL be made once, when the file is made, and stored in the file as the
   glyphs and their places; the player draws it.

## Requirement 5: the motion of a text and its pass

1. A text SHALL have one of four effects: `static`, shown in place for a time; `marquee`,
   which moves the block in from one side and out at the other; `slide`, which moves it in,
   holds it, and moves it out; and `pan`, which shows the block from one end to the other
   and back, holding at each end. The motion goes left, right, up or down, at a speed in
   pixels a second, with a pause in milliseconds.
2. The length of a pass SHALL follow from the canvas, the size of the block and the
   settings alone, by the formula of the design, in whole milliseconds; the converter
   writes it into the header and the core checks it.
3. No part of a text SHALL stay unseen: a block that does not fit the canvas in the
   direction it does not move is refused with `does-not-fit`, and so is a `static` or a
   `slide` block that does not fit at all. The app says so in its preview and names the
   effect that shows all of it.

## Requirement 6: the turn of a text

1. An automatic change of the animation SHALL wait until the text's pass ends: a turn of
   a text in the playlist or in a cycle SHALL end only at the end of a pass.
2. Without `repeat`, a text's turn SHALL be the fewest passes that last `min_seconds`;
   with `repeat`, that many passes; with `max_seconds`, it SHALL end at the end of the pass
   in which that time is reached; in a cycle, each turn of a text SHALL last the cycle's
   `seconds` rounded up to whole passes.
3. The timing of frames animations SHALL not change.
4. `play`, `play all`, `off`, `remove` and an upload that replaces the text SHALL act at
   once, as today: only the automatic change waits.

## Requirement 7: the clocks

1. A widget SHALL be one of three clocks: `analog`, a dial with twelve marks and an hour
   and a minute hand; `digital`, the hour and the minutes in the `large` font; and
   `melting`, a pocket watch whose face sags and folds, after the seed's reference picture.
2. The time a clock shows SHALL be imaginary: no clock of the board or of a network is
   read, and none is needed.
3. A clock SHALL play for `seconds` a loop, 30 by default, 1 to 3,600, and SHALL have four
   colours, the face, the hands, the rim and the background, and a range of speeds.
4. The melting clock SHALL draw its dial and its two hands, joined at one pivot, in the
   watch's own plane and then bend that plane, face and hands together, onto the folded
   surface; its hands move. The PNG of the seed is a target for the look, not a picture
   that is shown.

## Requirement 8: the seed and the virtual time

1. Every turn of a clock, also one that `play` began, SHALL get a seed of its own, chosen
   when the turn begins and kept until it ends; a `list`, a `status`, a late refresh or a
   loop that begins within the turn SHALL not change it.
2. `status` SHALL report the seed of the clock whose turn it is, as `seed`, and `null`
   while no clock is on the LEDs.
3. From the seed, the clock SHALL take a starting hour and a speed that changes smoothly
   within the clock's range, never below its least speed, so the hands never go back.
4. The virtual time SHALL be a function of the seed and of the time since the turn began,
   not of the number of refreshes: two runs with the same seed show the same picture at the
   same time, however many refreshes were left out.
5. The hands and the digits SHALL take their positions from the same virtual time.

## Requirement 9: one renderer, the same pixels

1. The core SHALL draw texts and clocks in integer arithmetic, with no floating point, in
   the same source files for the board and the emulator.
2. The converter's library SHALL draw them with the same rules, so that the app's preview
   shows what the LEDs show.
3. A set of reference pictures, each a canvas at a time of a text or a clock with a seed,
   SHALL be kept in `tests/vectors/`; the converter's suite, the core's suite and the
   emulator's suite SHALL each draw them and SHALL find every pixel equal.
4. The work of one refresh SHALL be bounded by the canvas and by the 512 glyphs a text may
   have at most, not by the length of a message or of a clock's loop, and no future
   picture SHALL be drawn ahead.

## Requirement 10: commands and replies

The owner approved these additions in advance on 2026-10-24.

1. Every animation item of `list`, of the show and of a drive, SHALL have `type`:
   `"frames"`, `"text"` or `"widget"`.
2. `read <id> <offset>` SHALL give up to 600 bytes of the file of an animation, from the
   offset, in base64 as `upload data` takes it, with the size of the file, so that a text
   or a clock can be read back and edited.
3. `upload expect <crc32>` SHALL make an open upload replace the item's file only when the
   file has that CRC-32 now; otherwise the reply is the new error `stale` and the upload is
   discarded, so that an edit never overwrites another controller's change.
4. `status` SHALL have `seed`, as Requirement 8 says.
5. Every route SHALL carry them unchanged, and `docs/commands.md` SHALL describe them.

## Requirement 11: the converter

1. A text and a clock SHALL each have a JSON source of their own, strict as the JSON
   frames are, with `version`, `type`, the canvas and every setting; the JSON frames format
   stays as it is.
2. `encode` SHALL make an `.odrgx` file of a text, a clock or JSON frames; `decode` SHALL
   give back the JSON source of a text or a clock, and the JSON frames of a frames file;
   `check` SHALL check an `.odrgx` file for a canvas; `pack` SHALL take a show that names
   `.odrgx` files, with `X.json` as the source of `X.odrgx`.
3. Every refusal SHALL have a reason of the converter's list, the same name as the core's
   where both refuse.

## Requirement 12: the app makes and previews

1. The app SHALL have a way to make a text: the text, the font, the colour of the text and
   of the background, the alignments, the direction, wrapping, the effect, the motion,
   the speed and the pause, with a preview of the actual canvas that moves as the LEDs
   will, and the length of a pass in words.
2. The app SHALL have a way to make a clock: its kind, its seconds, its four colours and
   its speeds, with a moving preview that takes a new seed when asked.
3. The preview SHALL say why a text cannot be made: a character that is not supported,
   with its code point, or a block that does not fit, with the effect that would show it.
4. A text or a clock SHALL be uploaded as a new item, as a video is, with progress,
   cancellation and every refusal in words.

## Requirement 13: the app edits

1. An installed text or clock SHALL be opened from the app's list, read back from the
   target, and shown in its form for editing.
2. Saving SHALL replace the item's file by an upload to its id with `upload expect`, so
   that the item keeps its id, its place in the show and its inclusion.
3. When another controller changed or removed the item meanwhile, saving SHALL be refused
   with a message that says so, and nothing is overwritten.
4. An animation of a drive SHALL not be edited: the drive is read only.

## Requirement 14: the hosts

1. The firmware and the emulator SHALL play every type through the core with no code of
   their own for it.
2. The emulator's preview of one animation, `python -m preview`, SHALL take an `.odrgx`
   file.
3. The firmware SHALL be built by the tool, and its font tables' size SHALL be measured
   and recorded.

## Requirement 15: memory and limits

1. The core SHALL ask for no new block of memory: a text's or a clock's description is
   held, while it plays, in the decoder's window, which no frames file uses then.
2. A text's payload SHALL be at most 3,612 bytes: 28 bytes of settings, 512 of text and
   512 glyphs of 6 bytes. A widget's SHALL be 20 bytes.
3. A text or a clock SHALL be refused on a canvas whose picture does not fit the core's
   pixel buffer, 65,534 bytes.

## Requirement 16: tests

1. The suites SHALL cover every type: legacy bytes and pictures unchanged, unknown types
   and versions, wrong lengths, bad UTF-8, an unknown font or widget, a payload too large,
   another canvas, a truncated file, a refused upload, and a file that fails while it is
   checked or plays.
2. Golden layouts SHALL cover English, Hebrew with its final forms, mixed directions with
   digits and punctuation, multiline wrapping, every effect and motion, a block too wide
   and too tall, and the refusal of a character that is not supported.
3. The core's suite SHALL show that a text is not cut off by the playlist, by a cycle or
   by `max_seconds`, that `play` and `off` act at once, and that a frames animation's
   timing is as before.
4. Clock tests SHALL replay a seed, show a new seed at each turn, the same virtual time for
   hands and digits, and a smooth bounded speed at irregular refreshes.
5. The app's suite SHALL cover making, previewing, uploading, editing, a stale edit, a
   refusal, a cancellation, and a drive's animation that cannot be edited.

## Requirement 17: documents and decisions

1. `docs/format.md` SHALL describe ODRGX and the three payloads; `docs/show.md` the names
   and the turn of a text; `docs/core.md` the drawing, the seed and the memory;
   `docs/commands.md` the commands and replies; `docs/converter.md` the sources and the
   subcommands; `docs/android-app.md` the app's new forms; `docs/emulator.md` and
   `docs/firmware.md` what they gained.
2. `docs/decisions.md` SHALL record that the runtime format and its sources were
   extended on purpose, and the change log SHALL have a dated line for each addition to
   the commands and replies.

## Requirement 18: the board and the owner

These need the board and the owner; they are done in a session with them.

1. The firmware of this seed SHALL be flashed, and its refresh rate measured with a text
   and each clock playing: 20 to 50 a second is accepted.
2. The owner SHALL look at a Hebrew text, a mixed text, every effect, and the three clocks
   with the melting clock's moving hands on the real 60 x 60 LEDs, and at the app on a
   phone.
3. What the board is left with SHALL be recorded.

## Requirement 19: after the branches are combined

These are done by the session that combines this branch with those of seeds 32 to 36
and 39.

1. Every type SHALL be registered by seed 35's catalogs, with its type and its loop
   length, on internal and external storage, without new scans.
2. A text or a clock that is refused SHALL be one of seed 32's faulted files: grayed in
   the list, never blocking the start or the healthy animations.
3. Making and editing a text or a clock SHALL be part of seed 36's upload and animation
   screens, with its look, and not a second set of controls.
4. Seed 39's filter by type SHALL use `type` of `list`.
