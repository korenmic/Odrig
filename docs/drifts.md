# Drifts

This file lists the questions that came up while specs were written and while they were
implemented, and how each was settled without asking the owner. Every entry has three parts:
the question, with the place where things were unclear; the answer that was chosen and why;
and the resolution, which names the spec file and section that now carry the answer. Where a
question exposes a gap in one of the governing documents, the entry says so and its answer is
the working assumption until the owner rules otherwise.

## Seed 01: Names for the reasons

**Question.** The seed says `decode`, `check` and `pack` "name the reason", and that every
invalid test vector is rejected "with its own reason". No document gives the reasons names,
so two implementations could not be compared.

**Answer.** Each condition gets one fixed name made of lower-case words and hyphens, such as
`bad-magic`. The tool, the test vectors and later the core's `status` reply use the same
names, because seeds 02 and 03 compare reasons across implementations. The names are listed
in a new `docs/reasons.md`.

**Resolution.** `docs/specs/01-p0-converter-and-reference-codec/requirements.md`,
Requirements 2, 3, 6, 7, 10, 11, 13, 14 and 15; `design.md`, "errors"; `tasks.md`, tasks 1
to 4, 6, 11, 13 and 14.

## Seed 01: Rejections that docs/format.md implies but does not list

**Question.** "What a reader rejects" in `docs/format.md` does not mention a file that ends
early, an invalid DEFLATE stream, a width or height of zero (the header table says "at least
1"), a stored mode byte other than `0x40` (the text says the mode byte "is `0x40`"), or bytes
after the end of the DEFLATE stream. This is a gap in a governing document.

**Answer.** All five are rejected, as `truncated`, `bad-deflate`, `zero-size`,
`reserved-bits` and `trailing-bytes`. None of them can be read as a valid file, and two
readers must agree on them. `docs/format.md` was not changed while the spec was written.

**Resolution.** Seed 01 `requirements.md`, Requirement 6; `design.md`, "Reference decoder";
`tasks.md`, task 3, which adds the five cases to `docs/format.md` as the seed requires for
an ambiguous document.

## Seed 01: Padding bits that are not zero

**Question.** `docs/format.md` says the last byte of a coded frame is padded "with fewer than
8 zero bits", but its reject list only has "8 or more padding bits". It does not say whether
a reader refuses padding bits that are not zero. This is a gap in a governing document.

**Answer.** A reader does not look at the values of padding bits. That is the reject list as
written, and it is what the decoders the format was measured with do.

**Resolution.** Seed 01 `requirements.md`, Requirement 5 criterion 5; `tasks.md`, task 3,
which states it in `docs/format.md`.

## Seed 01: A file with several defects

**Question.** Nothing says which reason is reported when a file is wrong in more than one
way.

**Answer.** The reason of the defect met first when the file is read from front to back,
with a fixed order inside the header and inside a frame record. Within a record the checks
on the bits come before the check of palette indexes, so a reader that works through a
stream and one that holds the whole file can agree. Every invalid test vector has one
defect.

**Resolution.** Seed 01 `requirements.md`, Requirement 2 criterion 4 and Requirement 6
criteria 2 and 3; `design.md`, "Reference decoder".

## Seed 01: Strictness of the JSON readers

**Question.** `docs/format.md` and `docs/show.md` list members and types, but do not say
whether a repeated member name, a byte-order mark, or a number such as `1.0` where an integer
is expected is acceptable.

**Answer.** All three are refused. An integer is a JSON number without a fraction and
without an exponent. The strict reading is the one a small reader on the board can match
exactly, so the Python tool and the core accept the same files.

**Resolution.** Seed 01 `requirements.md`, Requirement 3; `design.md`, "strictjson".

## Seed 01: What makes a mapping file valid

**Question.** `docs/mapping.md` describes the fields of a mapping file but gives no rules for
an invalid one, and writes the LED formula with the numbers 60 and 180 although the file
carries `width` and a list of rows for each leg. This is a gap in a governing document.

**Answer.** A mapping file must have exactly the described members; version 1; a width from
1 to 65,535; one or more legs with different numbers from 1 to 255 and different pins from 0
to 255; `first_led` of `left` or `right`; one or more rows per leg; every row from 1 to the
height exactly once; and width times height at most 65,534, the largest canvas an ODRG file
can have. A leg may have any number of rows, and the formula uses the file's width. These
are the widest rules that still let a reader size its buffers.

**Resolution.** Seed 01 `requirements.md`, Requirement 10; `design.md`, "mapping";
`tasks.md`, task 6, which writes the rules and the general formula into `docs/mapping.md`.

## Seed 01: What "ordered by hue" means

**Question.** `docs/format.md` advises ordering the palette by hue. It does not say how
colours of equal hue, or colours with no hue, are ordered. The order changes the file size
and must be the same on every run.

**Answer.** Colours are sorted by hue, then saturation, then brightness, all computed as
exact fractions, which puts black and greys first. Run against the prototype that the
format's sizes were measured with, this order gives exactly the documented sizes: 17,731 and
1,134 bytes for Hello world, 3,799 and 1,594 for DVD bounce.

**Resolution.** Seed 01 `requirements.md`, Requirement 7 criterion 4; `design.md`,
"Encoder", step 2.

## Seed 01: Equal sizes and stored frames in the encoder

**Question.** The converter guidance says to "keep the smallest result" and to write a
stored frame "when nothing coded is smaller". It does not say in what unit sizes are
compared or what happens when two results are equally small.

**Answer.** Sizes are compared in whole bytes of data. Among equal sizes the encoder takes
the lowest predictor number, then plain mode before run mode, then the lowest k. It writes a
stored frame unless a coded one is strictly smaller than N bytes. A fixed rule is needed for
byte-identical output.

**Resolution.** Seed 01 `requirements.md`, Requirement 7 criteria 6 and 7; `design.md`,
"Encoder", step 3.

## Seed 01: Compression that does not help

**Question.** `encode` compresses "unless asked otherwise". Nothing says what it does when
the compressed file comes out larger than the uncompressed one.

**Answer.** It compresses anyway. Only `--uncompressed` turns compression off, so the kind
of file never depends on the content.

**Resolution.** Seed 01 `requirements.md`, Requirement 7 criterion 8.

## Seed 01: Limits that JSON frames lacks and ODRG has

**Question.** A JSON frames file has no upper limit on canvas size or on `ms`. An ODRG file
limits N to 65,534 and the frame count to 32 bits. The seed does not say what `encode` does
with a source that is over those limits.

**Answer.** `encode` refuses it, with `canvas-too-large` or `too-many-frames`.

**Resolution.** Seed 01 `requirements.md`, Requirement 7 criterion 9.

## Seed 01: What "identical frames" means after a round trip

**Question.** The definition of done asks that JSON to ODRG to JSON gives identical frames.
`encode` merges identical neighbours and splits long frames, so the frame list can change
while the picture at every millisecond does not.

**Answer.** `decode` writes the merged form. The frames come back identical for every source
that has no two consecutive identical frames, which is what the generators write. For other
sources the picture at every millisecond is identical.

**Resolution.** Seed 01 `requirements.md`, Requirement 8.

## Seed 01: How `check` knows the format, and what it prints

**Question.** The seed lists what `check` prints but not the layout, and does not say how
`check` tells a JSON frames file from an ODRG file. Looking at the content cannot work,
because an ODRG file with a wrong magic number must still be reported as a bad ODRG file.

**Answer.** The file name's ending decides, and `--format` overrides it. The output is a
fixed list of `name: value` lines.

**Resolution.** Seed 01 `requirements.md`, Requirement 9.

## Seed 01: Details of the 50 frames-per-second timeline

**Question.** The seed gives the rule: each 20 ms tick takes the source frame on screen at
that time. It does not say where time zero is in a video, how long the last frame stays on
screen, how the number of ticks is rounded, or what happens when the requested range runs
past the end of the media.

**Answer.** Time zero is the first video frame. The last frame stays for the mean interval
between frames. The number of ticks is the length divided by 20 ms, rounded to the nearest,
and at least one. A range that is not inside the media is refused with `bad-range` instead
of being shortened, so the output always has the length that was asked for.

**Resolution.** Seed 01 `requirements.md`, Requirements 11 and 13; `design.md`, "Import
timeline".

## Seed 01: GIF frames with a delay of zero

**Question.** Many GIF files record a delay of 0 or 10 ms, which no viewer honours. The seed
says to take the frame that is "on screen".

**Answer.** A delay of 10 ms or less counts as 100 ms, which is what web browsers show.

**Resolution.** Seed 01 `requirements.md`, Requirement 11 criterion 4.

## Seed 01: Details of fitting a picture

**Question.** The seed names three ways to fit and says shrinking uses area averaging. It
does not say what shape a canvas pixel has, what happens where an edge falls inside a canvas
pixel, or how a picture is enlarged.

**Answer.** Canvas pixels are square. Every canvas pixel is the mean of the source area it
covers, weighted by area and computed in whole numbers, so the edge of a black bar inside a
pixel is blended. The same rule is used when the picture grows. One rule covers all cases
and gives the same result on every machine.

**Resolution.** Seed 01 `requirements.md`, Requirement 12; `design.md`, "Fitting and the
area mean".

## Seed 01: What `import` does not correct

**Question.** A video from a phone can record a rotation for display, and some files have
pixels that are not square or carry a colour profile. The seed says nothing about them.

**Answer.** None of them is applied in this seed. The picture is used as the library decodes
it, so a video filmed upright on a phone has to be rotated before it is imported. This keeps
the seed to the behaviour it lists.

**Resolution.** Seed 01 `design.md`, "Import timeline", last paragraph.

## Seed 01: Libraries

**Question.** The seed asks for dependencies that install with pip alone on three systems
and names none. Seeds 02 and 03 need the reference decoder, and seed 03 allows only the
Python standard library.

**Answer.** `import` uses numpy, Pillow and PyAV, which all ship ready-built packages. The
decoder, the encoder, `check`, `pack` and the generators use the standard library only.
Exact versions are fixed when `import` is implemented.

**Resolution.** Seed 01 `requirements.md`, Requirement 20; `design.md`, "Third-party
libraries".

## Seed 01: Details of `pack`

**Question.** The seed does not say whether the output folder may already hold files,
whether `pack` can write uncompressed files, or how the invalid cases of `docs/show.md`,
written for `.odrg` files, apply to the JSON sources `pack` reads.

**Answer.** The output folder must be new or empty, so that it holds exactly the installed
file set. `pack` accepts `--uncompressed`, because `docs/format.md` keeps uncompressed files
as the fallback for a slow board. A missing, invalid or wrongly sized source is reported as
`file-missing`, `file-malformed` or `size-mismatch`.

**Resolution.** Seed 01 `requirements.md`, Requirement 14.

## Seed 01: Order of the checks on ids

**Question.** `docs/show.md` lists three ways the ids of a show can be wrong. Nothing says
which one is reported when a show has more than one of them, and the converter and the core
must report the same one.

**Answer.** The checks run in three passes: every repeated id first, then every id that a
cycle or `start` names and no item has, then every cycle that names a cycle. Within a pass
the items are taken in file order.

**Resolution.** Seed 01 `requirements.md`, Requirement 14 criterion 5; `design.md`, "show".
Seed 02 `design.md`, "show".

## Seed 01: Generators and the canvas size

**Question.** Seed 01 says the two generators write "for the 60 x 6 canvas". Seed 03 says
the generators take the canvas size from a mapping file.

**Answer.** They take a mapping file from the start, and the tracked sources are made with
the two-leg mapping. On a larger canvas Hello world is centred and DVD bounce uses the whole
canvas; on one that is too small they refuse with `canvas-too-small`. How the ten-leg demo
show looks is left to seed 03.

**Resolution.** Seed 01 `requirements.md`, Requirements 10 and 15; `design.md`,
"Generators".

## Seed 01: Where the dense test clip lives

**Question.** The seed needs a dense 60 x 30 clip for its tests, and seeds 02 to 04 need it
too. `docs/decisions.md` leaves open whether large JSON sources are tracked; this one is
about 7 MB.

**Answer.** A generator writes the clip when it is needed. The clip is not tracked.

**Resolution.** Seed 01 `requirements.md`, Requirement 16.

## Seed 01: Brightness and mapping of the example show

**Question.** The seed fixes the items, the cycle and the start of the example show but not
its brightness, and says it is "with the two-leg mapping" although `show.json` has no member
for a mapping.

**Answer.** Brightness is 128, as in the example of `docs/show.md`. The mapping is given
when the show is packed; the documented command and the tests use `mapping/legs-2.json`.

**Resolution.** Seed 01 `requirements.md`, Requirement 17; `design.md`, "Example show".

## Seed 01: Shape of the test vectors

**Question.** The seed says each valid vector has "its expected decoded frames" and that
there is one invalid file for each reason. It does not say how they are stored.

**Answer.** A valid vector is `NAME.odrg` with `NAME.json`, which has one frame per frame
record without merging, so a reader is checked record by record. An invalid vector carries
its reason in its file name. The valid set also covers palettes of 1 and 256 colours,
canvases one pixel wide and high, and the three kinds of DEFLATE block, because the core
brings its own decompressor. No vector is above 4,096 bytes.

**Resolution.** Seed 01 `requirements.md`, Requirements 18 and 19; `design.md`, "Test
vectors".

## Seed 01: Byte-identical output and the zlib library

**Question.** The seed asks that the same input and options give byte-identical output. The
bytes of a compressed file come from the zlib library of the Python installation, and two
builds of zlib can compress the same data differently.

**Answer.** The requirement is tested for repeated runs. Uncompressed files are the same on
every machine; compressed files are the same wherever zlib is the same. Writing a compressor
of our own to remove this was judged not worth its cost.

**Resolution.** Seed 01 `requirements.md`, Requirement 1 criterion 6; `design.md`, "cli".

## Seed 01: Media files for the tests

**Question.** The definition of done imports "a short mp4 and a GIF". The seed does not say
whether such files are tracked.

**Answer.** The suite builds them at run time with the declared libraries. No media file is
tracked.

**Resolution.** Seed 01 `design.md`, "Testing strategy"; `tasks.md`, task 13.

## Seed 01: Where the new files live

**Question.** The seed names no folders, and `animations/` and `tools/` already hold
untracked proof-of-concept files in the old coordinate convention.

**Answer.** The tool is a package `odrig/` at the repository root. The generated sources go
into `animations/` under names no existing file has, the example show into `shows/example/`,
tests into `tests/converter/` and vectors into `tests/vectors/`. No untracked file is moved,
edited or deleted.

**Resolution.** Seed 01 `design.md`, "Repository layout".

## Seed 01: Recording the seed's progress

**Question.** The adopted seed convention keeps a seed's state in its `state.json`, with the
values `remaining`, `in_progress`, `completed`, `suspended`, `cancelled` and `superseded`.
None of them means "spec written", and in the repository the convention comes from, seeds
keep `remaining` after their spec is committed.

**Answer.** The spec commit leaves `state.json` as it is. The first task sets `in_progress`
and the last task sets `completed`.

**Resolution.** Seed 01 `tasks.md`, tasks 1 and 14.

## Seed 02: The C++ language level

**Question.** The seed says the core "keeps to the language level that build's toolchain
supports" and does not name the level.

**Answer.** C++11, limited to what later standards also accept. WLED 16.0.1 builds for the
ESP32-S3 with GCC 8.4.0 on Arduino core 2.0.18, and the Arduino core 2.0.x build script
compiles C++ as `gnu++11`. The flag was read in the upstream core, not in the package WLED
really uses, so the first firmware build of seed 04 confirms it. The choice is safe either
way, because that compiler cannot be set lower than C++11 and C++11 code compiles under
every higher setting.

**Resolution.** `docs/specs/02-p0-shared-runtime-core/requirements.md`, Requirement 1
criterion 1; `design.md`, "Language level and toolchain".

## Seed 02: Rules beyond the ones the seed lists

**Question.** The seed forbids exceptions, run-time type information and threads. It does
not mention recursion, large local arrays, static state or floating point, which matter on
a board whose tasks have small stacks and which must give the same output as the Mac.

**Answer.** The core also has no recursion, no local array above 256 bytes, no state
outside the object the host holds, and no floating-point arithmetic. The build and the
suite enforce these where they can.

**Resolution.** Seed 02 `requirements.md`, Requirement 1 criteria 4 to 6; `design.md`,
"Language level and toolchain".

## Seed 02: No third-party code in the core

**Question.** The seed lets the core bring in third-party code for DEFLATE and JSON under a
permissive licence, and does not say whether it should.

**Answer.** The core brings in none and has its own small DEFLATE decoder and JSON reader.
The usual small decompressor has the same names as the copy in the ESP32's ROM, the core
needs to know the exact byte where a stream ends, and a decoder that returns one byte at a
time fits a decoder that never holds a frame record. The suite checks it against zlib.

**Resolution.** Seed 02 `requirements.md`, Requirement 15; `design.md`, "Third-party code"
and "inflate".

## Seed 02: Where startup memory comes from

**Question.** The seed says time, file access and logging go through the host interface and
that there is no heap allocation after startup. It does not say where the memory taken at
startup comes from.

**Answer.** The host supplies it, through a function the core calls during startup only.
The firmware can then choose which kind of memory the core gets, and "no allocation after
startup" becomes something the test host can check. Time is not a function of the host: it
is passed with every call, as the seed's "the host calls the core with the current time"
says.

**Resolution.** Seed 02 `requirements.md`, Requirements 2 and 13; `design.md`, "The host
interface".

## Seed 02: How thorough the check at startup is

**Question.** The seed says the core "checks every `.odrg` file the show names", and
`docs/show.md` says a file that "breaks its format" makes the show invalid. Finding every
such file means decoding each one completely at power-on. How long that takes on the board
has not been measured; a store full of dense animations may take many seconds.

**Answer.** The core decodes every file once at startup, as the documents say. The time
grows with the amount of animation installed and is measured in seed 04. A host that must
stay responsive meanwhile does its housekeeping in its `read` function.

**Resolution.** Seed 02 `requirements.md`, Requirement 3 criterion 1; `design.md`,
"Startup" and the rules of use of the host interface.

## Seed 02: When refreshes happen

**Question.** The seed says the host calls the core with the current time and "every 20 ms
the core produces the LED data for that moment". It does not say where the 20 ms steps
start, or what happens when the host calls late, early or with a time that goes backwards.

**Answer.** The steps start at the timestamp of the first call. A call produces at most one
refresh, and only when a step is due. A late call gets the picture of its own timestamp and
the missed steps are skipped, not replayed. A timestamp earlier than the latest one counts
as the latest.

**Resolution.** Seed 02 `requirements.md`, Requirement 5; `design.md`, "Clock, grid and
refreshes".

## Seed 02: When an item's time starts

**Question.** `docs/commands.md` says `play` starts an item "from its first frame". It does
not say at which instant the item's time is zero.

**Answer.** At the 20 ms step of the first refresh after the command, or after power-on for
the `start` item. Frames then change exactly on the steps, so a refresh that comes a few
milliseconds late still shows the right frame.

**Resolution.** Seed 02 `requirements.md`, Requirement 7 criterion 3.

## Seed 02: What is produced when there is nothing to show

**Question.** The documents say the LEDs "stay dark" when the show is invalid, when nothing
is playing and when switched off. They do not say whether the core still produces LED data
then.

**Answer.** With a valid mapping it produces a refresh of all zeros every 20 ms, which
clears LEDs that still hold old colours and keeps the refresh rate meaningful. With an
invalid mapping there are no legs and no refreshes.

**Resolution.** Seed 02 `requirements.md`, Requirement 5 criteria 6 and 7 and Requirement 6
criterion 4.

## Seed 02: The text of `error` in the status reply

**Question.** `docs/commands.md` says `error` is "the reason the show is invalid" and does
not give its form.

**Answer.** It is the reason name of seed 01, followed by the id or the file name it is
about, and for a file that breaks its format by the reason of the format, for example
`file-malformed hello.odrg bad-magic`. The text holds only lower-case letters, digits,
`.`, `-`, `_` and spaces, so it needs no escaping in JSON.

**Resolution.** Seed 02 `requirements.md`, Requirement 3 criterion 3.

## Seed 02: Two reasons that docs/show.md does not have

**Question.** `docs/show.md` lists the ways a show is invalid. A host can also fail to
supply memory or to read a file, which is none of them.

**Answer.** Both make the show invalid, with `out-of-memory` and `read-error <name>`.

**Resolution.** Seed 02 `requirements.md`, Requirement 3 criterion 3 and Requirement 13
criterion 4.

## Seed 02: Brightness when show.json cannot be used

**Question.** Brightness at power-on is "the value in `show.json`". Nothing says what it is
when `show.json` is missing or wrong.

**Answer.** It is 0. When `show.json` itself is sound and only an animation file fails, it
is the value in `show.json`.

**Resolution.** Seed 02 `requirements.md`, Requirement 4 criterion 3.

## Seed 02: Edge cases of command lines

**Question.** `docs/commands.md` does not say what an empty line, two spaces in a row,
capital letters or leading zeros give, or which error code is reported when several apply.

**Answer.** Every line gets one reply, an empty one included. Extra spaces make empty words,
which fail as an unknown command or a bad argument. Command names are matched exactly, in
lower case. An argument is decimal digits only, and leading zeros do not matter. The code
reported is the first that applies of `line-too-long`, `unknown-command`, `bad-argument`,
`show-invalid`, `unknown-id`.

**Resolution.** Seed 02 `requirements.md`, Requirements 10 and 11.

## Seed 02: Lines from bytes, lines from HTTP

**Question.** `docs/commands.md` says a transport only carries lines. A serial port delivers
bytes, and an HTTP request delivers one line with or without its newline. The documents do
not say who cuts bytes into lines and applies the limit of 64 characters.

**Answer.** The core has one entry that takes a line and returns its reply, and it ignores a
final newline and carriage return, so an HTTP body can be passed as it is. The core also has
an entry for bytes, which cuts them into lines, applies the limit without storing an endless
line, and hands back each line with its reply. Both hosts then use the same code for it, and
the emulator gets the lines it shows in its command log.

**Resolution.** Seed 02 `requirements.md`, Requirement 10; `design.md`, "The host
interface" and "Commands".

## Seed 02: Exact bytes of a reply

**Question.** `docs/commands.md` shows replies as examples. It does not say whether the
order of members and the absence of spaces are fixed.

**Answer.** They are fixed as in the examples, each reply ends with a newline, and no reply
is longer than 192 bytes. A client can then compare replies as text.

**Resolution.** Seed 02 `requirements.md`, Requirement 10 criterion 5 and Requirement 11
criterion 4.

## Seed 02: `animation` and `fps` in corner cases

**Question.** `animation` is "the animation item on the LEDs right now" and `fps` is the
"LED refreshes in the last full second". Neither is defined just after `play`, while the
LEDs are off, or before a full second has passed.

**Answer.** `animation` is the animation the latest refresh chose, or the item's first
animation when no refresh has happened since `play`; it is reported while the LEDs are off
too, because playback goes on. Seconds are counted from power-on, and `fps` is 0 until one
has ended and for a second without refreshes.

**Resolution.** Seed 02 `requirements.md`, Requirement 11 criterion 5 and Requirement 12.

## Seed 02: A file that fails while it is playing

**Question.** Files are checked at startup. Nothing says what happens when a file cannot be
read later, or has been replaced.

**Answer.** From that refresh on the show is invalid: the LEDs are dark, `status` gives the
reason, and `play` is refused until the next startup.

**Resolution.** Seed 02 `requirements.md`, Requirement 16.

## Seed 02: The memory limit and the size of the show

**Question.** The seed limits working memory "for a 60 x 30 canvas" to 128 KB. The tables
of the show grow with the number of items, and `docs/show.md` sets no limit on that number.

**Answer.** The tables are sized from the show at startup. The limit is proven for the
ten-leg mapping with a show of 100 items, which needs under 60 KB. A larger show asks for
more, and a host that cannot supply it gets `out-of-memory`.

**Resolution.** Seed 02 `requirements.md`, Requirement 13; `design.md`, "Data structures".

## Seed 02: What the tests need

**Question.** The seed says the core builds with nothing beyond Apple's command-line
developer tools, and that it is checked against seed 01's decoder, which is Python 3.10 or
later. Apple's tools carry Python 3.9.

**Answer.** The build needs only Apple's tools. The test command also needs Python 3.10 or
later, without any third-party package. The suite is Python driving a small native test
host.

**Resolution.** Seed 02 `requirements.md`, Requirement 17; `design.md`, "Build" and
"Testing strategy".

## Seed 02: Proving there is no allocation after startup

**Question.** The definition of done asks for "a test build that fails on any heap
allocation after startup" and does not say how such a build detects one.

**Answer.** The test host stops when the core asks it for memory, or calls `operator new`,
after startup. A test on the compiled library shows that the core refers to no allocation
routine at all, which covers every other way. The test host also runs with the address and
undefined-behaviour sanitizers.

**Resolution.** Seed 02 `requirements.md`, Requirement 17 criteria 6 and 7; `design.md`,
"Allocation after startup".

## Seed 02: Recording the seed's progress

**Question.** As for seed 01: the seed convention has no state that means "spec written".

**Answer.** The spec commit leaves `state.json` as it is. The first task sets `in_progress`
and the last task sets `completed`.

**Resolution.** Seed 02 `tasks.md`, tasks 1 and 11.

## Seeds 01 and 02: Tasks that edit the governing documents

**Question.** The spec writer was told not to edit `docs/format.md`, `docs/mapping.md`,
`docs/show.md`, `docs/commands.md` or `README.md`, yet seed 01 says an ambiguous document is
fixed in the same change, and its tasks 3 and 6 add clarifications to `docs/format.md` and
`docs/mapping.md`. May implementers edit those documents?

**Answer.** Yes. The restriction applied to spec writing only. An implementer edits a
governing document when its task says so, in the same commit as the code that depends on the
clarification.

**Resolution.** Seed 01 `tasks.md`, tasks 3, 6 and 14, and seed 02 `tasks.md`, task 11, stand
as written.

## Seed 02: Start-up time when every animation is checked

**Question.** `docs/show.md` makes a show invalid when a listed `.odrg` file breaks its
format, so the core decodes every listed file completely at start-up. With the board's
storage full of animations that could take many seconds. Should start-up check less?

**Answer.** No, not now. A full check at start-up keeps the board and the emulator identical
and reports a bad file before the show begins. Today's shows are tens of kilobytes. The time
is measured on the board in seed 04, and the rule is revisited only if start-up takes more
than two seconds with realistic content.

**Resolution.** Seed 02 `requirements.md` and `design.md` stand as written. Seed 04 measures
start-up time.

**Measured in seed 04, on the board, 2026-10-11.** The start of the core took 171 ms for the
example show, 3.1 seconds for one dense 60 x 30 clip of 10 seconds, compressed, and 2.2
seconds for the same clip uncompressed, and 38 seconds for a storage filled with 9 MB of
compressed dense clips. The limit of two seconds named above was not passed with today's
shows and was passed with dense content: by one second for a single dense clip, and by far
for a full storage. During the start the LEDs are dark and the board answers nothing. The
rule itself is not changed here; whether start-up should check less is the owner's to
decide before shows of that size are installed. See `docs/firmware.md`, "Measurements on
the board".

## Seed 01: Library versions for media import

**Question.** The exact versions of numpy, Pillow and PyAV, and whether PyAV installs with
pip alone on this Mac's Python, could not be confirmed while writing the spec.

**Answer.** Seed 01 task 13 pins the versions it actually installs and tests. If PyAV has no
ready-made package for the Python in use, the implementer chooses another reader that installs
with pip alone and records that choice here.

**Resolution.** Seed 01 `tasks.md`, task 13.

## Seed 01: Modules the design does not list

**Question.** The design gives `read` functions to `jsonframes`, `mapping` and `show`, a
`write` function to `jsonframes`, and describes under `cli` how an output goes through a
`.part` file. It names no place for the code that opens a file, which the format modules and
the command line both need, and no place for the code the tests share to run the tool.

**Answer.** `odrig/files.py` holds the one function that reads an input file, turning a
missing or unreadable file into a rejection, and the one that writes an output file through
`<name>.part`. The format modules and `cli` call it, and it calls only `errors`, so the
direction of dependency of the design is kept. `tests/converter/support.py` runs the command
line for the tests, in the test's own interpreter or in a fresh one.

**Resolution.** Seed 01 `design.md`, "Overview" and "Repository layout".

## Seed 01: Queue and session files

**Question.** The tasks are run from a local queue with session notes, kept in a folder
`.codex/` at the repository root. The design's `.gitignore` does not cover it, and it must
never be committed.

**Answer.** `.gitignore` also lists `/.codex/`.

**Resolution.** Seed 01 `design.md`, "Repository layout"; `.gitignore`.

## Seed 01: An output that cannot be written

**Question.** The requirements name a reason for every input that is refused. They say
nothing about an output file whose folder does not exist or may not be written, which would
end the tool with a Python traceback.

**Answer.** It is a rejection like the others, with the reason `cannot-write`: one error
line, status 1 and nothing left behind.

**Resolution.** Seed 01 `requirements.md`, Requirement 2 criterion 5; `docs/reasons.md`,
"Any output".

## Seed 01: Codes above 255

**Question.** `docs/format.md` says a coded frame holds N codes, "each 0 to 255", but its bit
codes can spell larger values: with k of 6 or 7 the short form of a Rice code reaches up to
1,023, and in run mode the Rice value 255 makes the code 256. The reject list does not
mention such a code and Requirement 6 has no reason for it. This is a gap in a governing
document.

**Answer.** A reader rejects it, with the new reason `bad-code`, judged when the Rice code
has been read completely. Taking the value modulo 256 instead would give one residual two
spellings and would make the result depend on how wide a reader's variables are. The core of
seed 02 has to refuse the same files: it takes its reasons from Requirement 6 of seed 01, and
the invalid test vectors carry both cases.

**Resolution.** `docs/format.md`, "What a reader rejects"; seed 01 `requirements.md`,
Requirement 6 and Requirement 19 criterion 2; `design.md`, "Reference decoder", step 6;
`docs/reasons.md`, "ODRG files".

## Seed 01: Letter case of the file name given to `check`

**Question.** `check` tells the format from a name ending in `.json` or `.odrg`. The
requirement does not say whether `CLIP.JSON` counts, while `import` accepts its endings "in
any letter case".

**Answer.** `check` accepts the two endings in any letter case too, so the two subcommands
read a file name the same way.

**Resolution.** Seed 01 `requirements.md`, Requirement 9 criterion 1.

## Seed 01: Compressed sizes of Hello world and DVD bounce

**Question.** The design says the tool encodes the two animations to exactly the sizes in
`docs/format.md`. The uncompressed files are exactly 17,731 and 3,799 bytes. The compressed
ones are 1,138 and 1,612 bytes, not 1,134 and 1,594.

**Answer.** The tool keeps the rule of Requirement 7 criterion 6. The figures in
`docs/format.md` were measured with the prototype, which among frame records of the same
size in bytes kept the one with the fewest bits; the tool takes the lowest predictor, then
plain mode, then the lowest k. The records have the same sizes and different bytes, so
DEFLATE gives a slightly different result. Both files are within the 2 percent that
Requirement 7 criterion 10 allows (0.4 and 1.1 percent). The table in `docs/format.md` is
kept, with a note.

**Resolution.** `docs/format.md`, "Measured sizes"; seed 01 `design.md`, "Encoder", step 2;
`docs/converter.md`, "Generators".

## Seed 01: What the vector builder needs from the tool

**Question.** The design has the vector builder force each choice with `coded_record`, and
write the expected frames "without merging". A frame record's L is at most N + 1, so a
coded record holds at most N bytes of data, and a forced combination cannot code every
picture: plain mode with k = 7, for one, fits only codes below 128. The design names no way
to find a picture that a combination can code, and `jsonframes.dumps` always merges.

**Answer.** `coded_record` raises `ValueError` for a combination that does not fit.
`odrg.codes` is one more public building block: the N codes of one predictor. The builder
grows each picture from codes its combination writes in at most N bytes and checks them
against `odrg.codes`. `jsonframes.dumps` takes `merge=False`, which only the builder passes.
Apart from the `escape` vector no vector uses the long form of a Rice code, so that vector
alone proves the feature.

**Resolution.** Seed 01 `design.md`, "jsonframes", "odrg" and "Test vectors";
`docs/converter.md`, "Test vectors".

## Seed 01: Line endings of tracked files

**Question.** The suite compares tracked files with the output of the generators and of the
vector builder byte for byte, and `pack` copies two JSON files as bytes. Git for Windows by
default rewrites the line ends of text files when it checks them out, which would make
those comparisons fail on a computer the tool is meant to run on.

**Answer.** A `.gitattributes` file tells git to leave every `.json` file as it is and to
treat `.odrg` files as binary.

**Resolution.** `.gitattributes`.

## Seed 01: The numpy version

**Question.** The design asks for one exact version of each library, the newest with
ready-made packages for Python 3.10 and later. No numpy release has packages for both
Python 3.10 and Python 3.14, which is the only Python on the Mac this seed is verified on:
numpy 2.2.6 is the last release for Python 3.10 and has none for 3.14, and from 2.3 on
numpy needs Python 3.11.

**Answer.** `requirements.txt` names two exact versions, each with the Python versions it
applies to: numpy 2.2.6 below Python 3.11 and numpy 2.4.6, the newest that still serves
Python 3.11, from there on. The tool uses only whole-number array arithmetic, which both
have. The suite was run with numpy 2.4.6 on Python 3.14. The line for Python 3.10 is not
verified, because no Python 3.10 is installed here.

**Resolution.** `requirements.txt`; seed 01 `design.md`, "Third-party libraries".

## Seed 01: The versions of Pillow and PyAV

**Question.** Which exact versions of Pillow and PyAV does `requirements.txt` name, and does
PyAV install with pip alone on this Mac's Python 3.14?

**Answer.** Pillow 12.3.0 and PyAV 17.1.0. Both install with pip alone on Python 3.14 on
this Mac, and both publish ready-made packages for Python 3.10 and later on macOS, Windows
and Linux. PyAV 17.1.0 is not the newest release: 18 needs Python 3.11 and 19 needs Python
3.12. It carries its own FFmpeg libraries, with the `mpeg4` encoder the tests use to make
their inputs. The names the design uses (`av.open`, `streams.video`, `decode`, `pts`,
`time_base`, `to_ndarray`) are as described in that version, and a file it cannot decode
raises `av.error.FFmpegError`.

**Resolution.** `requirements.txt`; seed 01 `design.md`, "Third-party libraries".

## Seed 01: Details of `import` settled while implementing

**Question.** The requirements give `import` its reasons but not the order of its checks,
and leave three cases open: a video with transparent pixels, although the design decodes
video without transparency; a file named `.gif` that is in fact another kind of picture;
and a video whose frames carry no time or come out of order.

**Answer.** `import` reads the mapping file first, as `pack` does, then judges the name of
the media file, then that it exists, then a negative start or a duration that is not above
0, then decodes, and judges the part against the length of the media last. A video is
decoded with its transparency and laid over black, like a GIF, so transparent pixels are
black in every kind of file. A `.gif` file is read by the GIF reader only, so another kind
of picture under that name is `unreadable-media`. A frame without a presentation time, or
frames whose times go backwards, are `unreadable-media` too.

**Resolution.** Seed 01 `design.md`, "Import timeline"; `docs/converter.md`, "import".

## Seed 01: The folders above the output folder of `pack`

**Question.** The documented command packs the example show into `build/example-show`. In a
fresh checkout there is no `build` folder, and nothing says who makes it.

**Answer.** `pack` makes its output folder and the folders above it. `import`, `encode` and
`decode` write one file and make no folder: a folder that does not exist is `cannot-write`.
`docs/converter.md` has the reader make `build` once before the examples that write a file
into it.

**Resolution.** `docs/converter.md`, "Setup" and "pack".

## Seed 01: What is verified

**Question.** The requirements ask for Python 3.10 and later on macOS, Windows and Linux,
and say that this seed verifies macOS only. The Mac has one Python, 3.14.

**Answer.** The suite passes on macOS 26.5 on Apple Silicon with Python 3.14.6, zlib 1.2.12,
numpy 2.4.6, Pillow 12.3.0 and PyAV 17.1.0, in a virtual environment built from
`requirements.txt`. For Python 3.10 the suite only checks that every source file keeps to
the grammar of that version. Nothing was run on Python 3.10 to 3.13, on Windows or on
Linux.

**Resolution.** `docs/converter.md`, "Setup"; `tests/converter/test_scope.py`.
## Seed 03: Where the emulator and the command tool live

**Question.** The seed names no folders. Seed 01's package `odrig` is the obvious home, but
its suite forbids every module of `odrig/` from importing network or serial modules and from
reading the operating system's name.

**Answer.** Two packages of their own at the repository root: `emulator`, run as
`python -m emulator`, and `odrigctl`, run as `python -m odrigctl`. The page's files are in
`emulator/web/`, the tests in `tests/emulator/`, the demo show in `shows/demo-10/`.

**Resolution.** `docs/specs/03-p0-emulator/design.md`, "Repository layout".

## Seed 03: How a Python program runs the core

**Question.** The seed says the emulator uses only the Python standard library apart from
the core, and that the core is compiled natively from the firmware's source files. It does
not say how Python reaches C++ code. Seed 02 left the build target for it to this seed.

**Answer.** The core is built as a shared library by a new target `shared` in
`core/Makefile`, from the same `src/*.cpp` with the same flags, and loaded with `ctypes`.
The host interface is plain C, so no wrapper code in C++ is needed and no source file of the
core changes. A second host program speaking over a pipe was not chosen: it would add a
protocol to write and to test for no gain. One lock makes every call to the core follow the
one before it, whichever thread asks.

**Resolution.** Seed 03 `requirements.md`, Requirement 2; `design.md`, "Running the core";
`tasks.md`, task 1.

## Seed 03: The command tool and the proof-of-concept tools

**Question.** The seed says "the repository's command tool is brought to the commands in
`docs/commands.md`" and "the generic line sender stays as it is". The tools it means,
`tools/wled.py` and `tools/wled_send.py`, are untracked proof-of-concept scripts that send
WLED's own JSON, and the adopted rule is that untracked files are not edited.

**Answer.** The command tool is new tracked code, the package `odrigctl`. The untracked
scripts are not moved, edited, deleted or staged. `wled_send.py` sends any line to any
serial port, so it works against the emulator's port unchanged; `wled.py` and
`wled_deploy.py` keep working only against stock WLED.

**Resolution.** Seed 03 `requirements.md`, Requirement 13; `design.md`, "The command tool".

## Seed 03: What a wrong folder is

**Question.** The seed asks for a clear message and a non-zero exit for "a wrong folder",
and also says that for an invalid show "the page shows the reason the core reports". A
folder without `mapping.json` is both.

**Answer.** A path that does not exist or is not a folder stops the emulator with
`not-a-folder`. Any folder starts the emulator: whether its content is a valid show is the
core's judgement, and the page shows the core's reason. The emulator has no check of its own
on the files.

**Resolution.** Seed 03 `requirements.md`, Requirements 1, 10 and 12.

## Seed 03: A stable name for the virtual serial port

**Question.** A pseudo-terminal gets a different device name on every run. The seed wants
serial tools to work "with only the port name changed", which needs a name that can be
written down.

**Answer.** The emulator makes a symbolic link to the device at
`build/emulator/serial` under the repository root, or at the path given with
`--serial-link`, replaces a link left by an earlier run, and removes it at exit. One
emulator uses one link path.

**Resolution.** Seed 03 `requirements.md`, Requirements 1 and 6; `design.md`, "The virtual
serial port".

## Seed 03: How refreshes and commands reach the page

**Question.** The page must show 50 refreshes a second and every command at once, and the
emulator may use only the standard library, which has no WebSocket.

**Answer.** One server-sent event stream, `GET /events`, carries four kinds of event:
`hello`, `frame`, `log` and `status`. A refresh of the ten-leg canvas is 5,400 bytes, 7,200
characters in base64, so 50 a second is about 360 kB a second on the loopback address. Each
page connection keeps only the newest refresh waiting, so a slow page skips refreshes
instead of falling behind; log and status events are never dropped. A WebSocket written by
hand was not chosen: the page sends nothing back, and the event stream reconnects by itself.

**Resolution.** Seed 03 `design.md`, "GET /events".

## Seed 03: HTTP details that docs/commands.md leaves open

**Question.** `docs/commands.md` defines `POST /odrig`, the 200 and the 405. It does not
say what content type a request has, what happens to a query string, a longer path, a
request without a length or a very long body, or whether the reply's newline is part of the
response body. The emulator and the board must agree on each. This is a gap in a governing
document.

**Answer.** Working assumptions until the owner rules otherwise: the request's content type
is not looked at; the path is exactly `/odrig` and what follows a `?` is ignored; another
method gets 405 with `Allow: POST`; a `POST` without a usable `Content-Length` gets 411; of a
body longer than 128 bytes the first 128 are passed on, which the front-end answers with
`line-too-long`; the response body is the reply exactly as the core returned it, newline
included, with `Access-Control-Allow-Origin: *`, which WLED's server adds to every response
on the board. The command tool sends `application/octet-stream`, because the board's web
server library takes form and some plain-text bodies apart before a handler sees them; see
"Seed 04: The content type of an HTTP command".

**Resolution.** Seed 03 `requirements.md`, Requirement 7; `design.md`, "POST /odrig" and
"The command tool". Seed 04 `design.md`, "HTTP transport".

## Seed 03: Where the page's status comes from

**Question.** The page shows the current status, and the definition of done wants it to
match what `status` returns. There are no emulator-only commands, and the log must show the
commands that arrived, not the emulator's own.

**Answer.** The emulator sends the core the ordinary `status` line after every command that
arrived and once a second, and passes the reply to the page unchanged. These requests are
not entered in the command log. Record mode makes none, so a recording holds exactly the
scripted session.

**Resolution.** Seed 03 `requirements.md`, Requirement 8 criteria 5 and 6 and Requirement 11
criterion 6.

## Seed 03: The record file and the script

**Question.** The seed asks for a record mode that takes "an optional script of timed
command lines" and "writes the per-leg LED data of every tick to a file". It gives neither
format, nor says when a scripted command acts relative to the tick of the same time.

**Answer.** The script is text: a time in milliseconds, a space, the command line. A
command is given to the core with its own time before the first tick that is not earlier, so
a command at the time of a tick is seen in that tick's refresh. The record file is binary
with a 16-byte header, the legs as the core lists them, and one fixed-size record for each
tick; replies of scripted commands are printed, not stored. Ticks are 0, 20, 40 ms and so on
below the length.

**Resolution.** Seed 03 `requirements.md`, Requirement 11; `design.md`, "Record mode".

## Seed 03: What the flipped-mapping check compares

**Question.** The definition of done says that with a mapping file in which one leg's
`first_led` is flipped, "the recorded picture differs from the reference in exactly that
leg's rows". A picture rebuilt with the same flipped file would not differ at all.

**Answer.** The comparison is of LED data, leg by leg, against the reference for the
unchanged mapping: the flipped file stands for a mapping file that does not match the
wiring. Every other leg is equal at every tick, and in the flipped leg every row holds the
reference row in reverse order.

**Resolution.** Seed 03 `requirements.md`, Requirement 11 criterion 8; `tasks.md`, task 2.

## Seed 03: Whether the ten-leg demo sources are tracked

**Question.** The seed asks for "a tracked demo show for the ten-leg mapping". Seed 01
tracks the two sources of the example show. For the 60 x 30 canvas the two JSON frames files
come to about 10 MB, and `docs/decisions.md` leaves open whether large JSON sources are
tracked.

**Answer.** `shows/demo-10/show.json` is tracked. The two sources are written by seed 01's
generators with `mapping/legs-10.json` into `build/demo-10/sources`, which is ignored, as
seed 01 does for the dense clip. The documentation gives the commands, and the suite
generates and packs the show in a temporary folder.

**Resolution.** Seed 03 `requirements.md`, Requirement 14; `design.md`, "The ten-leg demo
show".

## Seed 03: The board drawing

**Question.** The mapping view is "drawn from `mapping.json`", and needs the board's two
rows of pins "labelled as on the real board". The order of the pins is not in
`mapping.json`; it is only in the drawing of `docs/mapping.md`. Nothing says what is drawn
for a leg whose pin the board does not have.

**Answer.** The two rows of labels are a small table in the page, `board.js`, and a test
compares it with the drawing in `docs/mapping.md`. Everything about legs comes from
`mapping.json`. A pin that is not on the board gets a marked pad of its own under the
board, with its number. The board is drawn on the side of the canvas where most legs have
their first LED.

**Resolution.** Seed 03 `requirements.md`, Requirement 9; `design.md`, "board.js" and
"Mapping view".

## Seed 03: How LED values are shown on a screen

**Question.** The page draws the values the LEDs are given. A screen shows the value 128 at
about a fifth of full brightness, while an LED driven half of the time looks more than half
as bright, so dim shows would be nearly black on the page.

**Answer.** Every value passes through one fixed curve, `255 * (v / 255) ^ (1 / 2.2)`
rounded, before it is drawn, and a dark LED is drawn as a faint outline. The data, the
record file and the tests use the unchanged values.

**Resolution.** Seed 03 `requirements.md`, Requirement 4 criteria 6 and 7; `design.md`,
"layout.js" and "LEDs view".

## Seed 03: Testing the page without a browser

**Question.** The page must work out LED positions itself, and the suite may need neither
a browser nor anything installed. How is the page's code tested?

**Answer.** The page's geometry is in `layout.js`, which uses nothing a browser provides.
The suite runs it in the JavaScript shell that is part of macOS
(`/System/Library/Frameworks/JavaScriptCore.framework/Versions/Current/Helpers/jsc`, the
engine Safari uses) and compares every LED position with the rule of `docs/mapping.md`
computed in Python. How the page looks in Safari and in Chrome is a written check list for
a person or for an agent with a tool that drives a browser; it is the last task, and the
seed is completed only when it is done.

**Resolution.** Seed 03 `requirements.md`, Requirements 5 and 16; `design.md`, "Testing
strategy"; `tasks.md`, tasks 7, 8 and 11.

## Seed 03: Exit statuses and failure reasons

**Question.** The seed asks for "a clear message and a non-zero exit" from the emulator and
"a non-zero status when the reply is not ok or the target cannot be reached" from the
command tool. It names no statuses and no wording.

**Answer.** Both use the error line of seed 01, `error: <reason>: <detail>`. The emulator
exits with 1 for `not-a-folder`, `core-not-built`, `serial-unavailable`, `address-in-use`,
`bad-length` and `bad-script`, and with 2 for a usage error. The command tool exits with 0
for `"ok":true`, 1 for `"ok":false`, 2 for a usage error and 3 when the target cannot be
reached or does not answer in time, so a script can tell a refused command from a missing
target. These reasons are start-up failures of a program, not rejections of a file, so they
are listed in `docs/emulator.md` and not in `docs/reasons.md`.

**Resolution.** Seed 03 `requirements.md`, Requirements 12 and 13.

## Seed 03: One test command that needs a built library

**Question.** The suite needs the core's shared library, and the test command must be one
command that selects its suite by discovery.

**Answer.** The command is `python3 -m unittest discover -s tests/emulator -t .`. The test
package builds the library with `make -C core shared` when it is imported and fails with
make's output if that fails. The emulator itself never builds: without the library it stops
with `core-not-built`.

**Resolution.** Seed 03 `requirements.md`, Requirement 16; `design.md`, "Testing strategy".

## Seed 03: Recording the seed's progress

**Question.** As for seeds 01 and 02: the seed convention has no state that means "spec
written".

**Answer.** The spec commit leaves `state.json` as it is. The first task sets
`in_progress`. The last task, the check list by eye, sets `completed`.

**Resolution.** Seed 03 `tasks.md`, tasks 1 and 11.

## Seed 04: What the seed builds on

**Question.** The seed lists seeds 01 and 02 as what it depends on. Its definition of done
also uses "the repository's command tool" and compares the board with the emulator, which
are seed 03.

**Answer.** Seed 04 is implemented after seeds 01, 02 and 03. It uses `odrigctl` for every
exchange with the board's serial port and the emulator as what the board is compared with.

**Resolution.** `docs/specs/04-p1-firmware-build-with-the-player/requirements.md`, the
opening paragraph; `design.md`, "What this design relies on".

## Seed 04: Where the installed show lives on the board

**Question.** `docs/show.md` says a show is installed as one flat folder and that the same
folder is uploaded to the board. It does not say where on the board. The board's file
system already holds WLED's own files in its top folder. This is a gap in a governing
document.

**Answer.** The folder `/odrig` of WLED's LittleFS file system. Installing replaces that
folder and nothing else, so "exactly the installed file set" can be checked, files of an
earlier show cannot stay behind, and stock WLED, which ignores the folder, keeps its own
settings and show for a roll-back.

**Resolution.** Seed 04 `requirements.md`, Requirements 7 and 14; `design.md`, "Memory,
time and files" and "Installing a show".

## Seed 04: LED type and colour order

**Question.** WLED needs an LED type and a colour order for every output. `mapping.json`
has neither, and the seed says the outputs are set from `mapping.json` and that WLED's own
output settings are not a second source. This is a gap in `docs/mapping.md`.

**Answer.** Every output is made for WS2812B LEDs at 800 kHz with the order green, red,
blue, fixed in the firmware. These are the values the proof-of-concept deploy script wrote
for the strips that are confirmed working. A build with other LEDs needs a change to the
mapping format, which is the owner's to decide.

**Resolution.** Seed 04 `requirements.md`, Requirement 8 criterion 1; `design.md`, "The
outputs".

## Seed 04: How our code owns the LEDs

**Question.** The seed says the core's LED data is sent to the outputs and that WLED's
effects, presets and playlists take no part. WLED has no setting that switches its own
drawing off.

**Answer.** The usermod keeps WLED in the live mode that network pixel inputs use
(`realtimeLock` with the time-out that never ends), in which WLED's loop skips effects,
presets, playlists and nightlight, and checks at every pass that WLED is still in it. It
writes the core's bytes straight to the outputs through `BusManager`, not through WLED's
pixel buffer, so WLED's LED map, matrix layout, gamma correction and segments never touch
them, and it sets the outputs to full brightness before every refresh. A consequence: the
switch, the brightness slider and the live-override of WLED's interface no longer change
the LEDs; only the commands of `docs/commands.md` do.

**Resolution.** Seed 04 `requirements.md`, Requirements 9 and 10; `design.md`, "Holding the
LEDs" and "Sending a refresh".

## Seed 04: The values of the current limiter

**Question.** The seed says WLED's current limiter stays active. The limiter needs a
maximum current and a current for one LED, and the outputs are no longer made from WLED's
settings.

**Answer.** The limiter runs inside the call that sends a refresh, so it acts on every
refresh. Its maximum stays the one in WLED's LED settings, 850 mA when nothing was set, and
the outputs are made with WLED's default of 55 mA for one LED. The maximum is the one LED
setting of WLED that still counts; it is changed in WLED's interface.

**Resolution.** Seed 04 `requirements.md`, Requirement 10 criterion 2; `design.md`, "The
outputs" and "Sending a refresh".

## Seed 04: Ten legs on a chip with four RMT outputs

**Question.** `docs/mapping.md` records that WLED supports up to 12 outputs on the
ESP32-S3. Reading the source shows they are of two kinds: 4 RMT outputs and 8 through a
parallel driver. Which legs get which, and what if a mapping asks for more?

**Answer.** The usermod asks for RMT for every output; WLED gives it to the first four in
mapping order and the parallel driver to the rest. A refresh of ten legs of 180 LEDs is on
the wire for under 6 ms either way. The board can drive 12 legs. An output that cannot be
made, for a thirteenth leg or for a pin the chip keeps for itself, is named in WLED's
information; the other outputs and the core run unchanged, and `status` does not report it,
because `docs/commands.md` gives `status` no member for it.

**Resolution.** Seed 04 `requirements.md`, Requirement 8 criteria 4 and 5; `design.md`,
"The outputs".

## Seed 04: Calls to the core from two tasks

**Question.** Seed 02 says the core is used from one thread. On the board, WLED's web
server calls its handlers on the network task, while playback and the serial port run on
the task of the main loop.

**Answer.** One mutex is held for every call to the core, so the calls follow one another;
the core keeps nothing that belongs to a task. The timestamp of a call is read after the
mutex is taken. The emulator of seed 03 does the same with a lock.

**Resolution.** Seed 04 `requirements.md`, Requirement 3 criterion 4; `design.md`, "Threads
and the lock".

## Seed 04: The content type of an HTTP command

**Question.** `docs/commands.md` says the command line is the body of `POST /odrig` and
names no content type for the request. The web server library of WLED 16.0.1 takes a body
apart as form fields, before any handler sees it, when the type is
`application/x-www-form-urlencoded`, and when it is `text/plain` and the body looks like
`name=value`. This is a gap in a governing document.

**Answer.** The firmware reads the body as it is when the library passes it on, and from
the form field `body` when the library took it apart. With any other content type every
body reaches the core byte for byte. With those two types this holds for every body without
`&`, `=`, `+`, `%` and zero bytes, which every valid command is; a body with one of them can
reach the core changed and so get another reply than in the emulator. `odrigctl` sends
`application/octet-stream`. The owner may want `docs/commands.md` to name a content type.

**Resolution.** Seed 04 `requirements.md`, Requirement 12 criterion 3; `design.md`, "HTTP
transport". Seed 03 `design.md`, "The command tool".

## Seed 04: How the board reports that its Wi-Fi network is up

**Question.** The definition of done says "the board reports that its own Wi-Fi network is
up after power-on". `status` has no member for Wi-Fi, a command exists only if something
uses it, and WLED's own serial interface, through which this was asked on 2026-10-11, is
switched off in the firmware.

**Answer.** The report is WLED's own: `GET /json/info` on the board's address gives
`wifi.ap`. Reaching it needs a device on the network, which also proves the network is up.
It is one of the owner's checks, together with the HTTP commands, and `test-air` asks for
it. Nothing is added to `status`.

**Resolution.** Seed 04 `requirements.md`, Requirements 13 and 16; `design.md`, "Wi-Fi" and
"tests/air".

## Seed 04: What flashing writes

**Question.** The seed asks for one command that flashes and one that restores stock WLED.
It does not say which parts of the flash they write.

**Answer.** Both write only the first application partition and clear the boot selection
data, so that the board starts that partition. The bootloader and the partition table on
the board are the ones of WLED's 16 MB layout, which the firmware is built for, and the
tool reads the partition table to check that before it writes. `restore-stock --full` also
writes the stock bootloader and partition table. Storage is never written by either, so
WLED's settings, its old show and the files in `/odrig` survive going back and forth.

**Resolution.** Seed 04 `requirements.md`, Requirements 4, 5 and 6; `design.md`, "Flashing
and rolling back".

## Seed 04: The stock WLED files and their checksums

**Question.** Restoring needs the stock files and "files whose checksums are verified". The
three files are untracked, in `firmware/wled-16.0.1/` of the main checkout, with a checksum
list beside them.

**Answer.** The checksums are tracked in `firmware/stock.sha256`; the files stay
untracked, since WLED is not stored in this repository. `restore-stock` takes them from
`firmware/wled-16.0.1/` unless told otherwise and checks each before it writes anything.
The application image is the release asset of WLED 16.0.1, whose published SHA-256 equals
the tracked one, so it can be fetched again. The factory backup in `esp32-backup/` is the
last resort, used by hand; no tool reads or writes that folder.

**Resolution.** Seed 04 `requirements.md`, Requirements 5 and 6; `design.md`, "Flashing and
rolling back".

## Seed 04: What the build needs besides PlatformIO

**Question.** The seed says build tools install into a project-local environment. WLED's
build also runs Node.js, to pack its web interface, which the seed does not mention, and
WLED's configuration puts a build cache in the home folder.

**Answer.** Everything goes into `build/firmware/`: a Python environment with WLED's own
pinned PlatformIO, esptool and littlefs-python; Node.js 20.18 through the Python package
`nodeenv`; PlatformIO's packages and caches, moved there with `PLATFORMIO_CORE_DIR` and
`PLATFORMIO_BUILD_CACHE_DIR`; and the caches of npm and pip. The Mac must already have
Python 3.10 or later, git and Apple's developer tools. Whether PlatformIO 6.1.17 runs under
this Mac's Python 3.14, and whether `nodeenv` works here, is checked by the first task,
which records a fallback if not.

**Resolution.** Seed 04 `requirements.md`, Requirement 2; `design.md`, "The environment of
every child process" and "setup", assumptions A1 to A3.

## Seed 04: The C++ level of the WLED build

**Question.** Seed 02 chose C++11 for the core and left the real flag of the WLED build to
be confirmed here. Two sources read for this spec disagree: the build script of Tasmota's
Arduino core at its tag 2.0.18 has `-std=gnu++11`, and WLED's own notes say C++17 for this
platform.

**Answer.** The second task reads the flag from the verbose output of a real build and
records it. The core is valid C++11 and compiles under either; nothing in this design
depends on which it is.

**Resolution.** Seed 04 `design.md`, fact R28 and assumption A5; `tasks.md`, task 2.

## Seed 04: No change to WLED's own files

**Question.** The seed allows changes to WLED's files as small patch files. Does the
firmware need any?

**Answer.** No, as far as the source shows: the usermod is a library outside WLED's
folder, WLED's serial handling is switched off by its own build flag
`WLED_DISABLE_ADALIGHT`, the outputs and the live mode are reached through WLED's global
functions, and the HTTP handler is registered on WLED's server object. The build still
applies every patch file of `firmware/patches/`, so a patch that a task finds necessary has
its place.

**Resolution.** Seed 04 `requirements.md`, Requirement 1 criterion 3; `design.md`,
"Overview" and "build".

## Seed 04: Checking the board without eyes and without Wi-Fi

**Question.** Much of what the seed asks for shows only on the LEDs or in WLED's
information page, which needs the Wi-Fi network. An agent has neither eyes on the LEDs nor
a way to join the network, and the port carries only the commands of `docs/commands.md`.

**Answer.** A second build, the probe build, exists for the board tests only. It answers
the line `#probe` on the port with measurements: the outputs and whether they work, a
checksum of the colours each output holds, how often something else overwrote them, the
refreshes sent, and the longest times. With it a test compares what the outputs hold with
the emulator's recording. The firmware left on the board has none of this code. What still
needs a person is listed as the owner's checks.

**Resolution.** Seed 04 `requirements.md`, Requirements 15 and 16; `design.md`, "The probe
build" and "Who checks what".

## Seed 04: Shows installed by tests, and the wired strip

**Question.** The definition of done names the example show, whose brightness is 128. Today
one 60-LED strip is wired, on leg 1, fed from the board's 3.3 V pin, and power is out of
scope for this project.

**Answer.** Every show a test or an agent installs has a brightness of 40 or less; the
test helper packs a copy of the show with its brightness replaced by 32 and refuses a
brighter one. The items of the definition of done that need the LEDs to be seen, or two
legs wired, are the owner's, at the brightness the owner chooses for the power supply in
use.

**Resolution.** Seed 04 `requirements.md`, Requirement 15 criterion 5 and Requirement 16;
`tasks.md`, the rules and task 10.

## Seed 04: Playback inside WLED's main loop

**Question.** The usermod can ask the core for a refresh from WLED's main loop or from a
task of its own. WLED's notes say the loop runs up to 2,000 times a second when idle but
can slow to a few passes a second while its file system is written or many requests are
served.

**Answer.** Playback runs in the main loop: it is the simplest and shares no output with
another task. The core is asked only when the outputs can take data, so `fps` in `status`
is the real rate and shows a stall. If the measurements on the board show stalls in
ordinary use, playback moves to its own task, designed then from those measurements.

**Resolution.** Seed 04 `design.md`, "loop()" and "Risks"; `tasks.md`, tasks 6 and 8.

## Seed 04: Start-up time on the board

**Question.** Seed 02 left the time the core needs to check every file at start to be
measured here, and gave two seconds with realistic content as the point at which the rule
is looked at again. How is it measured?

**Answer.** The usermod times its call that starts the core. The probe build reports the
figure, and WLED's information shows it. It is measured for the example show, for one dense
60 x 30 clip of 10 seconds, and for storage filled with 9 MB of dense clips, and written
into `docs/firmware.md` and under the seed 02 entry of this file.

**Resolution.** Seed 04 `requirements.md`, Requirement 7 criterion 7; `tasks.md`, task 8.

## Seed 04: Recording the seed's progress

**Question.** As for the other seeds, and one more: the definition of done has items only
a person can check.

**Answer.** The spec commit leaves `state.json` as it is. The first task sets
`in_progress`. The last task is the owner's checks and sets `completed`; an agent leaves
it open.

**Resolution.** Seed 04 `tasks.md`, tasks 1 and 10.

## Seed 02: Queue records without task ids

**Question.** The workflow that queues the tasks adds a `TaskId` and a `TaskIdPacked` line
to each queue record, made by its task-id script. That script builds its paths for Windows
and stops on this Mac with a path that does not exist.

**Answer.** The queue records of seed 02 carry `Status`, `Source` and `Task` only, like
those of seed 01. The readers of the queue need no more: the status report counts all 25
records as by-reference, with no missing reference.

**Resolution.** `.codex/local-task-queue.md`, which is not tracked.

## Seed 02: The core's reasons and the converter's test of docs/reasons.md

**Question.** Task 1 adds `read-error` and `out-of-memory` to `docs/reasons.md`. The
converter's suite, as delivered, checks that document in both directions: every reason of
the tool is listed, and every listed reason is a reason of the tool. Seed 01's design asked
for the first direction only. With the two new names the second check fails, because the
tool does not have them.

**Answer.** The document gets a last section, "The core", for what only the core reports.
The converter's test reads the sections before it, so it still proves that the tool's part
of the document and `odrig/errors.py` agree in both directions. The core's suite proves the
other half: every name the core can report is in the document. The two names are not added
to `odrig/errors.py`, since the tool never gives them.

**Resolution.** `docs/reasons.md`, "The core"; `tests/converter/test_docs.py`;
`tests/core/test_build.py`.

## Seed 02: The header as the design prints it

**Question.** Task 2 creates `core/include/odrig_core.h` "exactly as in the design". The
printed text has no guard against being included twice, and a host that reaches it through
two of its own headers would not compile as C. The design of seed 03 also speaks of the
header's eight functions, and the printed header declares seven.

**Answer.** The file is the printed text between the lines of an include guard,
`ODRIG_CORE_H`. Nothing else differs, so the interface is the one the designs of seeds 03
and 04 were written against. The functions are seven: `odrig_core_begin`,
`odrig_core_poll`, `odrig_core_leg_count`, `odrig_core_leg`, `odrig_core_command`,
`odrig_core_feed` and `odrig_core_error`. The "eight" in seed 03's design, "binding", is a
miscount; its test compares the binding with the header itself, so it is not affected.

**Resolution.** `core/include/odrig_core.h`; `tests/core/test_build.py`.

## Seed 02: At which bit the DEFLATE decoder finds a defect

**Question.** The design lists what the decoder rejects as `bad-deflate`, "exactly what
zlib rejects". It does not say at which bit each defect is found. That matters for a
stream that is both wrong and cut short: the reference decoder reports what zlib finds
first, `bad-deflate` or `truncated`, and the core has to report the same.

**Answer.** The decoder judges each part of a stream at the point where zlib does: the two
counts of a dynamic block when its 14 bits are read; the code-length code when all of its
lengths are read; a repeat when its extra bits are read; the two codes of the block when
all their lengths are read, the missing end-of-block code first; a bit pattern that is no
code once as many bits are read as the longest code of the set has, and after one bit when
the set has no code; a length or distance symbol that does not exist when it is decoded; a
distance when its extra bits are read. zlib reads a code-length code that has no code at
all as lengths of zero that take one bit each, and the decoder does the same, so such a
block is refused for its missing end-of-block code. The suite compares the outcome of
every stream it has, whole, damaged or cut, with zlib's: the output and the number of
bytes left after the stream, or `bad-deflate`, or `truncated`.

**Resolution.** `core/src/inflate.cpp`; `tests/core/test_inflate.py`.

## Seed 02: Many inputs in one run of the test host

**Question.** The tasks ask for thousands of damaged streams and files. The test host is
built with the sanitizers and takes about 45 ms to start, so one run for each input would
take minutes. The design's `inflate` invocation also prints nothing that shows where the
decoder stopped reading, which is what the check for bytes after a stream relies on.

**Answer.** `inflate` takes the option `--batch`, and `decode` takes it when task 3 adds
that invocation: standard input then holds any number of inputs, each after its length as four bytes, and the host prints
the result of each in order. After `data <hex>`, `inflate` prints `left <n>`, the number of
bytes of input after the last byte of the stream. The host hands out every file in pieces
of changing sizes, none above 512 bytes, so every test runs the core against short reads.

**Resolution.** `tests/core/host/host.cpp`; `tests/core/support.py`.

## Seed 02: The reason for a file with several defects, read as a stream

**Question.** The core never holds a whole file, and `docs/reasons.md` fixes the order of
the checks for a reader that does: a compressed body is inflated whole before the first
record is looked at, and all data bytes of a record are present before one of its bits is
judged. A reader that works through a stream meets the defects of a file in another order.
For a file with two defects it would name another reason than `check`, and the design asks
only that the core accepts and rejects the same files.

**Answer.** The core reports the same reason as the reference decoder for every file. When
it finds a defect in the body it reads on before it answers: in a compressed file to the
end of the DEFLATE stream, where a defect of the stream or bytes after the stream win; and
in any file to the end of the record's data, where a record cut short wins as `truncated`.
This costs time only for a file that is refused, which ends the show in any case. The suite
compares the reason, not only acceptance, for 3,000 damaged copies and for every prefix of
a file.

**Resolution.** `core/src/odrg_decoder.cpp`, `settled` and `body_stopped`;
`tests/core/test_decoder.py`.

## Seed 02: Codes above 255 in the core

**Question.** The spec of seed 02 was written before `docs/format.md` and
`docs/reasons.md` gained the reason `bad-code`, and its design does not mention it.

**Answer.** The core rejects such a file as the documents now say: it reads the Rice code
whole, so a code cut off by the end of the data is `out-of-bits`, and then rejects a Rice
value above 255 in plain mode or above 254 in run mode as `bad-code`. The two invalid
vectors for it are rejected with that reason, and a test compares the reasons of the
vector folder with the "ODRG files" table of `docs/reasons.md`.

**Resolution.** `core/src/odrg_decoder.cpp`; `core/src/reasons.h`;
`tests/core/test_vectors.py`.

## Seed 02: Details of the ODRG decoder that differ from the design

**Question.** The design has `open` read the header and the palette. Requirement 3
criterion 4 has the size of a file compared with the mapping after its header and before
its body, and the palette is part of the body: a file of the wrong size whose body is cut
inside the palette must be `size-mismatch`. The design also compares every byte written
with C in a palette file.

**Answer.** `open` reads the 16 bytes of the header only, and the palette is read with the
first frame record. The palette indexes are checked by looking at the whole picture after
each record, which is what the reference decoder does and gives the same result as
checking each byte written. A record asked for after the last one of the file is
`truncated`. The functions keep the names and arguments the design gives them.

**Resolution.** `core/src/odrg_decoder.h`, `core/src/odrg_decoder.cpp`.

## Seed 02: Bytes outside ASCII in the JSON reader

**Question.** The converter refuses a mapping or show file that is not UTF-8, and the core
has to accept and refuse the same files. The design describes the core's JSON reader
without saying whether it checks UTF-8.

**Answer.** It does not need to. The reader refuses any byte of 128 or more at the place
where it stands. Outside a string such a byte is not JSON. Inside a string it would be
part of a member name, of `first_led` or of a file name, and none of those can hold it, so
the converter refuses the file too, as not UTF-8 or as an unknown name or a wrong value.
The verdict is the same in every case, and the suite compares it for hand-written texts
and for 250 seeded copies with one character changed.

**Resolution.** `core/src/json_reader.h`, `core/src/json_reader.cpp`;
`tests/core/test_json.py`.

## Seed 02: Lines of the test host that the design does not list

**Question.** The design gives the lines `odrig_host session` prints at startup and for
each input line. It has no line for the text the core passes to the host's `log` function,
and nothing marks where the startup lines end and the answers begin, although both can
start with `error`.

**Answer.** The host prints `log <text>` for every diagnostic text, at the moment the core
gives it, and `ready` after the last startup line. The guard's flag is declared in
`tests/core/host/guard.h`, shared by the two source files of the host. The suite runs
sessions side by side where a test needs hundreds of them.

**Resolution.** `tests/core/host/host.cpp`, `tests/core/host/guard.h`;
`tests/core/support.py`.

## Seed 02: Ids that no item can have

**Question.** The format of a show file lets an entry of a cycle, and `start`, be any
integer: `-5`, `0`, `70000` and a number of forty digits all pass it, and the converter
then refuses the show as `undefined-id`. The design's JSON reader fails on a minus sign
before anything but zero, which would make such a show `show-malformed` in the core, and
the entry table holds ids of 16 bits. Nothing says what `<id>` is in the reason text for a
number that is no id.

**Answer.** The core reports `undefined-id` as the converter does. Its JSON reader has a
second way to read an integer, as a sign and a size. The text names the number as the file
writes it: `undefined-id -5`, `undefined-id 0`, `undefined-id 70000`. A number beyond 32
bits is named as 4294967295, with its sign. The suite compares the reason and the id with
the converter's for 109 show texts and 250 seeded copies with one character changed.

**Resolution.** `core/src/json_reader.h`, `any_integer`; `core/src/show.cpp`;
`tests/core/test_json.py`, `tests/core/test_startup.py`.

## Seed 02: Seeing which files the core opens, and sessions in one run

**Question.** Task 5 asks for a test that a file named twice is opened for checking once.
Nothing the test host prints shows which files the core opens. The tests of the JSON
readers also start several hundred sessions, and a run of the test host under the
sanitizers takes about 60 ms to start.

**Answer.** `odrig_host session` takes the option `--trace-files`, which prints
`open <name> <result>` for every call of the host's `open` function. It also takes
`--batch` in place of the folder: standard input then holds any number of file sets with a
script each, the host keeps the files in memory, runs one session after the other and
prints `end` after each.

**Resolution.** `tests/core/host/host.cpp`; `tests/core/support.py`, `start_each`.

## Seed 02: A carriage return without a newline, and the line handed back

**Question.** Requirement 10 has the command entry ignore one newline at the end of a line
"and one carriage return before it". It does not say what a carriage return at the end of
a line without a newline is, which is what the byte entry passes on for a line that ended
in a carriage return and a newline. It also does not say in which form the byte entry
hands a line to the host.

**Answer.** The command entry drops one final newline when there is one, and then one
final carriage return when there is one, as the design's algorithm says: `on\r` is the
command `on`. The byte entry hands the host each line as the command entry reads it:
without the newline, without that one carriage return, and only its first 64 characters
when it is longer. A command log made from these lines shows no line ends. For seed 03
this means the line of a `log` event has no carriage return at its end; its design,
"binding", says a line is shorter than what arrived only when it is cut, which holds
apart from the line end.

**Resolution.** `core/src/commands.cpp`; `tests/core/test_commands.py`. Seed 03
`design.md`, "binding" and "Sending events", are met as described.

## Seed 02: What the test host checks in every reply

**Question.** Requirement 10 limits a reply to one line of 192 bytes, and the design has
the core return 0 when the room for a reply is too small. The design's test host prints a
reply and checks nothing about it.

**Answer.** The test host ends with status 72 and the line `bad reply` when a reply is
longer than 192 bytes, does not end in a newline, or holds a byte outside printable ASCII
before it. It gives the core a block of exactly 192 bytes for a reply and one of exactly
the line's length for the line, so the sanitizer reports a byte read or written outside
them. At the start of every session it asks for `status` with room for 191 bytes and
stops unless the core returns 0; that call carries no timestamp for the core.

**Resolution.** `tests/core/host/host.cpp`.

## Seed 02: A read failure that begins while a file plays

**Question.** Task 9 tests a read failure in the middle of a file while it plays. The
design's host option `--read-fails FILE OFFSET` makes every reading of the file fail,
and the core reads every file whole at startup, so with it the show is invalid before
anything plays. The task also asks for a test that no `read` asks for more than 512
bytes, and the design names no way to see that.

**Answer.** The test host has one more option, `--read-fails-after FILE OFFSET N`, which
spares the first N openings of the file, as `--remove-after` and `--swap-after` do. The
host stops with `file misuse` when the core asks for more than 512 bytes, or for none, in
one `read`; the invocation `odrig_host guard read` shows that it does, and every session
of the suite then proves that the core never asks for more.

**Resolution.** `tests/core/host/host.cpp`; `tests/core/test_failure.py`,
`tests/core/test_memory.py`.

## Seed 02: What is verified

**Question.** The requirements ask for source files that compile unchanged for macOS and
for the ESP32-S3 inside the WLED build, with a C++11 compiler or a later one. This seed
builds and tests on the Mac only.

**Answer.** The suite passes on macOS 26.5 on Apple Silicon with Apple clang 21, GNU Make
3.81 and Python 3.14.6 with zlib 1.2.12, from a copy that holds the tracked files only. A
test compiles the core's sources under C++11, 14, 17, 20 and 23 with every warning as an
error. By hand they were also checked, without building, under `gnu++11` with exceptions
switched on and `-Os`, as the Arduino core compiles, and for a 32-bit ARM target with
conversion warnings; both gave no message. Nothing was compiled with GCC, for the
ESP32-S3 or inside WLED, and no time was measured on the board: that is seed 04. The
benchmark figures are those of the Mac.

**Resolution.** `docs/core.md`; `tests/core/test_build.py`. Seed 04 `tasks.md`, tasks 5
and 8, build the core for the board and measure there.

## Seed 03: The ticks of a recording whose length is not a multiple of 20 ms

**Question.** Requirement 11 puts the ticks of a recording at "0 ms, 20 ms, 40 ms and so on
below S seconds". The design counts them as `floor(S * 1000 / 20)` and calls a length that
gives no tick `bad-length`. For a length of 30 ms the first gives the ticks 0 and 20 and the
second the tick 0 only; for 5 ms the first gives one tick and the second refuses the length.
The two agree for every length that is a multiple of 20 ms.

**Answer.** The requirement decides: every grid time below the length is a tick, so the
number of ticks is the length in milliseconds over 20, rounded up. `bad-length` is a length
that is not above 0 after rounding to the nearest millisecond, as Requirement 12 has it. A
scripted time is refused when it is at or after the length, as Requirement 11 criterion 4
says, not at `20 * T`.

**Resolution.** `emulator/record.py`, `tick_count` and `read_script`; `docs/emulator.md`,
"Record mode"; `tests/emulator/test_record.py`.

## Seed 03: A scripted command later than the last tick

**Question.** A scripted command is given to the core "before the first tick that is not
earlier than that time". A command whose time is after the last tick and below the length,
such as 59990 in a recording of 60 seconds, has no such tick. The loop of the design never
sends it, and Requirement 11 criterion 3 wants every command given and its reply printed.

**Answer.** Such a command is given to the core after the last tick, with its own time,
and its reply is printed like any other. It changes no tick of the file.

**Resolution.** `emulator/record.py`, `ticks`; `docs/emulator.md`, "The script".

## Seed 03: A record file that cannot be written, and details of the script

**Question.** Requirement 12 lists six reasons for a failed start. None fits a record file
whose folder does not exist or cannot be written. The design also leaves open what an empty
line of a script is when the file has carriage returns, and what is done with a script that
is not UTF-8.

**Answer.** A record file that cannot be written is `cannot-write`, the name the converter
gives the same condition, with status 1 and no `.part` file left. A script is read as
UTF-8, and one that is not is `bad-script`. Lines end at a newline. A line that is empty,
or holds only a carriage return, is skipped; the command of any other line is given to the
core as it is, a carriage return at its end included, which the core drops. A command may
be empty: the line `100 ` gives the core an empty line at 100 ms.

**Resolution.** `emulator/failure.py`; `emulator/record.py`; `docs/emulator.md`, "The
script" and "Exit statuses".

## Seed 03: The line of a log entry for a command that came over HTTP

**Question.** The log shows each command line as the core read it. The core's entry for
bytes hands that line back to its host; the entry for one line, which HTTP uses, hands back
only the reply. Requirement 2 keeps every interpretation of a command line out of the
emulator.

**Answer.** For a command that came over HTTP the emulator writes the log line as the core's
entry for bytes would hand it back: the body without one final newline and one final
carriage return, and its first 64 characters, marked as cut, when it is longer. This is how
a line is shown, not how it is obeyed: the reply and every effect come from the core, which
is given the body as it arrived. A test compares the lines with the ones the reference
player's entry for bytes hands back. A newline inside a body stays part of its one line and
is shown as `\x0A`.

**Resolution.** `emulator/engine.py`, `Engine.line`; `tests/emulator/test_engine.py`.

## Seed 03: Replies that no program reads

**Question.** The design has the port's reader block in a read and write every reply back
with a plain write. A pseudo-terminal holds about a thousand unread bytes. A program that
sends commands and never reads, such as a shell's `echo status > build/emulator/serial`
used a dozen times, fills it, the write then waits for ever, and the port takes no more
commands from anyone until the emulator is started again.

**Answer.** The near end of the pseudo-terminal does not block. The reader waits for bytes
with a time limit, so it can also be stopped, and a write that finds the port full waits up
to a second for a program to read. After that the unread replies are dropped and the newer
ones are written, as the output of a board is lost when nobody listens. A program that
reads in time loses nothing.

**Resolution.** `emulator/serialport.py`, `Port._read` and `Port._write`; `docs/emulator.md`,
"The serial port"; `tests/emulator/test_serial.py`.

## Seed 03: How much a page that does not read still receives

**Question.** The design gives each page connection one place for the newest refresh, and
its test has a connection that reads nothing for 2 seconds receive "the newest refresh, not
an old one". Between the emulator and a page are the buffers of the system. On this Mac
they take about half a megabyte for one connection whatever size a program asks for, which
is more than 4 seconds of refreshes of the two-leg canvas. The emulator cannot see what a
page has read, so for that long a silent page is not noticed, and when it reads again it
first gets what the system held.

**Answer.** The rule stands as the design has it, and holds from the moment the buffers of
the system are full: the emulator keeps no queue of refreshes of its own, and gives its
event connections a send buffer of 32,768 bytes. The suite proves the one place on the
connection object itself, and over a real connection with a canvas of 60 x 300, whose
refreshes fill the buffers within a few: after 2 silent seconds the timestamps jump by more
than a second and the refreshes that follow are the newest. In a browser the page reads at
once and draws only the newest refresh it has, so the picture does not lag either way.
`hello` carries the reason of an invalid show as the core gives it when the page connects,
not as it was at start.

**Resolution.** `emulator/hub.py`, `Connection`; `emulator/httpd.py`, `events`;
`tests/emulator/test_events.py`, `SlowPage`; `docs/emulator.md`, "The event stream".

## Seed 03: Details of the command tool that the design leaves open

**Question.** The design gives the command line of the tool and its two exchanges. It does
not say whether an option may follow the command, what an argument with a newline in it is,
what a path that opens but is no serial port is, or what a response with status 200 is whose
body is no reply.

**Answer.** The options may stand before or after the command, so the command and its
argument are two positions of one parser and not sub-commands. An argument with a newline
is a usage error, status 2: the tool sends one line, and this is the one thing about an
argument it looks at. A path that is no serial port, and a response with status 200 whose
body is not a JSON object with a member `ok`, count as a target that is not reached,
status 3. An address without a port means port 80. The sources of the tool hold no word for
the emulator or for the board, and a test says so.

**Resolution.** `odrigctl/cli.py`, `odrigctl/client.py`; `docs/emulator.md`, "The command
tool"; `tests/emulator/test_tool.py`, `tests/emulator/test_scope.py`.

## Seed 03: Waking the real-time loop in time

**Question.** The design has the loop sleep until 0.2 ms after the next grid time. On this
Mac one sleep of about 20 ms woke 6 ms late in the middle and up to 10 ms late: the system
lets a timer slip by a share of its length. The core still produced 50 refreshes a second,
so `status` showed nothing, but the refreshes left 12 to 30 ms apart, two of them often
fell into one frame of the browser, and the page's own count was 47.

**Answer.** The wait is cut up: half of what is left each time, and at the end steps of
half a millisecond. Measured the same way, the wake-up was then 0.05 ms late in the middle
and 0.3 ms at most, for about half a percent of one processor. The timestamps of the
refreshes are 20 ms apart and the page counts 49 to 51 in a second, for the example show
and for the dense 60 x 30 clip alike.

**Resolution.** `emulator/engine.py`, `wait_until`; `tests/emulator/test_realtime.py`.

## Seed 03: The page in a light appearance, and details of its files

**Question.** The design gives the page one set of colours, a dark one, and says nothing
of a system set to a light appearance. Its test forbids `//` in every page file, which is
also how a JavaScript comment and the SVG namespace are written. It gives the LEDs view a
cell of 17 pixels at 1280 x 800 and one label column, without widths.

**Answer.** In a light appearance the header, the reason band and the log are light. The
drawing always stands on the dark stage of the design, so the LEDs and the twelve leg
colours, which were chosen for a dark ground, look the same either way. The scripts use
block comments only, take the SVG namespace from an element the browser makes, and are
plain ASCII, so the test can forbid `//` outright. The parts around the canvas have two
sets of widths: a roomy one, which gives the 17 pixels at 1280 x 800, and a compact one
for areas where the roomy one would leave cells below 13 pixels. A faint band of the leg
colour lies behind the rows of each leg, the end numbers are in the leg colour, and the
columns of the canvas are numbered every ten.

**Resolution.** `emulator/web/style.css`, `emulator/web/layout.js`, `emulator/web/view.js`;
`tests/emulator/test_page_files.py`, `tests/emulator/test_layout.py`; `docs/emulator.md`,
"The page".

## Seed 03: Lines to the far row of pins, and the path of a chain

**Question.** The design draws the line of a pad in the row of pins away from the canvas
level through the board, behind its body. The two rows of the board have their pads at the
same heights, so that line lies exactly on the line of the pad opposite: in the ten-leg
mapping pin 1 is opposite pin 4 and pin 2 opposite pin 5, and all four are used. The design
also draws the path of each chain over the dots at 60 percent, which tints the live LEDs it
is meant to show.

**Answer.** A line to the far row goes round the board, over its top for a pad in the upper
half and under its bottom for one in the lower half, in nested loops, and the leg's label
stands outside the loops. No line passes through the board, and a test says so. The path of
a chain is drawn behind the dots: it shows through the rings of dark LEDs and between lit
ones, and a lit LED keeps its colour. Small arrows along every row, between two LEDs, give
the direction, with an arrow head where the chain turns into a row and a bar at its end.
The number of a leg's first LED is a tag on the line that feeds it.

**Resolution.** `emulator/web/layout.js`, `wires` and `chain`; `emulator/web/view.js`;
`tests/emulator/test_layout.py`, `Lines`; `docs/emulator.md`, "The mapping view".

## Seed 03: The mapping view in a narrow window, and its sizes

**Question.** The design has one arrangement, the board beside the canvas, sized for
1280 x 800. Beside a board, a window 900 pixels wide leaves cells of 5 pixels, in which no
row label can be read. The design also gives the board a fixed distance of 16 pixels
between its pads, and fixes the order of the tracks: the highest leg nearest the canvas.

**Answer.** Where the board beside the canvas would leave cells below 9 pixels, the board
stands below the canvas, which then takes the whole width: at 900 pixels the cells are 10.
The lines run down a channel beside the canvas; those for the row of pins on the other side
of the board go through a band between canvas and board and down a second channel. In this
arrangement the highest leg takes the track farthest from the canvas, which is what keeps
the lines from crossing on their way down; beside the board the order is the design's. The
drawing may then be higher than the window, and the stage scrolls. The distance between
pads is 16 pixels at 1280 x 800, as in the design, shrinks to 10 where the height is short,
and grows to 20 where the canvas leaves room. The labels take roomy widths where the cells
are 16 pixels or more. In every arrangement the lines of the ten-leg mapping cross six
times, which is the number of pairs of pins that are out of order on the board.

**Resolution.** `emulator/web/layout.js`, `fitBeside`, `fitBelow` and `wiresBelow`;
`tests/emulator/test_layout.py`, `Lines`; `docs/emulator.md`, "The mapping view".

## Seed 03: The check list by eye without a person and without Safari

**Question.** The last task goes through the check list "in current Safari and in current
Chrome" and needs "a person, or an agent with a tool that drives a real browser". The agent
that implemented the seed had Chrome and a way to drive it. It had no way to drive Safari:
Safari's remote automation has to be switched on in the system by its owner, and switching
it on was not the agent's to do.

**Answer.** The list was gone through in headless Chrome by a program, step by step, and
every step was as described; the next entry has the results. Safari is left to the owner.
The task is therefore not ticked, the queue record stays undone, and the seed's state stays
`in_progress`: `completed` is set by whoever goes through the twelve steps in Safari. One
check that a program can make for Safari was added to the suite: every script of the page
is valid for Safari's JavaScript engine, which is the engine of the JavaScript shell of
macOS.

**Resolution.** Seed 03 `tasks.md`, task 11, which stays open; `docs/emulator.md`, "What
has been checked"; `tests/emulator/test_page_files.py`.

## Seed 03: What is verified

**Question.** The requirements ask for a page that works in current Safari and Chrome, for
49 refreshes a second on this Mac, and for a command tool that works against the emulator
and the board alike. What of this has been seen to hold, and how?

**Answer.** The suite, 259 tests, passes on macOS 26.5 on Apple Silicon with Apple clang
21, GNU Make 3.81 and Python 3.14.6, after `make -C core clean`. It was not run with Python
3.10 to 3.13; a test parses every source in the grammar of 3.10.

The check list of `docs/emulator.md` was gone through in Chrome 154 without a window, in a
viewport of 1280 x 800, by a program that drove the browser through its remote-debugging
port. The emulator was started as the list says, on port 8600 and the link
`build/emulator/serial`, and commands were sent with `odrigctl`.

| Step | Criterion | What the program found |
|---:|---|---|
| 1 | 4.8 | The header read animation 1 at the start, 2 after 17 seconds and 1 after 32. The screenshots show HELLO WORLD upright, read from left to right, and then the square. |
| 2 | 4.6 | On the ring of a dark LED the canvas holds the colour `#2a2f36`; its centre is empty. |
| 3 | 4.9 | Example show: `page` read 50 in each of ten seconds, and `core` 50. |
| 4 | 8.1 | After `brightness 40` through the port and `play 2` over HTTP the log had one line and then two, with `serial` and `http`, the lines and `{"ok":true}`, without a reload. |
| 5 | 8.4 | The header read brightness 40, playing 2, animation 2; after `off` it read off and no LED was lit; after `on` the square was lit again. |
| 6 | 4.2 | Dense show: nothing to scroll; the canvas was 1020 x 510 pixels inside the window. At 1000 x 700 the cells became 14 pixels and at 1600 x 1000 22. |
| 7 | 4.9 | Dense show: `page` read 50 in each of ten seconds. |
| 8 | 9.1 | The antenna is above the first pad and the two sockets at the lower edge of the board; the labels of the two rows, read from top to bottom, are the two lists of `board.js`. |
| 9 | 14.5 | Ten pads are in a leg colour, leg N on pin N for 1 to 10, with ten lines, ten arrow heads and ten paths; the LEDs of this view were lit and `page` read 49 to 51. |
| 10 | 9.8 | 175 texts, 60 of them end numbers, and no two of them overlap. |
| 11 | 9.5 | Pointing at the label of leg 4, the pin of leg 3, the line of leg 9 and an LED of leg 10 highlighted that leg's label, pin, line, path, outline, numbers and band, faded 216 parts of the others and dimmed the rows of the nine other legs. The readouts were `leg 4, pin 4`, `leg 3, pin 3`, `leg 9, pin 9` and `leg 10, pin 10, LED 70 (10,2)`. |
| 12 | 10.1 | The band read `file-missing dvd.odrg` in the LEDs view and in the mapping view, and no LED was lit. |

Measured in the same way for ten seconds each: the example show and the ten-leg demo show
both gave `fps` 50 in every reply to `status`, and the page counted 49 to 51 in every
second, in the LEDs view and in the mapping view.

Not verified: Safari, in any step. A person looking at a screen, in either browser: whether
the rings of dark LEDs are easy enough to see and whether the drawing pleases are
judgements the program did not make, though the screenshots were looked at. The command
tool against the board: its serial path ran against pseudo-terminals only, and nothing was
sent to the board. A network other than the loopback address.

**Resolution.** `docs/emulator.md`, "The check list by eye". Seed 04 `tasks.md` uses the
tool against the board.

## Seed 04: Where Node.js comes from

**Question.** The design installs Node.js 20.18 with the Python package `nodeenv`, which
fetches it from nodejs.org, and names the Node.js already on the Mac as the fallback. The
run that implemented the seed was allowed to fetch from PyPI, PlatformIO's registry,
Espressif and WLED's repository only, and the Mac's own Node.js is version 26, which
nothing pins.

**Answer.** Node.js and npm come from PyPI: the package `nodejs-wheel` 20.18.0, which
carries Node.js 20.18.0 and npm 10.8.2, pinned in `firmware/requirements.txt` in the place
the design gives `nodeenv`. It installs into the tool's Python environment, so the work
folder has no `node/` of its own and `PATH` gets `build/firmware/venv/bin` only.
Assumption A2 was therefore not tried. The version is the one WLED's `.nvmrc` asks for.
The owner may prefer `nodeenv` and nodejs.org; it is a change of one line of the
requirements file and one step of `toolchain.py`.

WLED's own build fetches more than the tool does: the packages of WLED's
`package-lock.json` from the npm registry, and the platform, toolchains and libraries of
WLED's `platformio.ini` from PlatformIO's registry and from the GitHub repositories that
file names. Those cannot be chosen by this project; task 2 lists them in
`docs/firmware.md`.

**Resolution.** `firmware/requirements.txt`; `firmware/fwtool/toolchain.py`,
`firmware/fwtool/env.py`; `docs/firmware.md`, "What the tool needs" and "Verified on the
board".

## Seed 04: Details of the tool's setup that the design leaves open

**Question.** The design lists the steps of `setup` and says each is skipped when its
result is there. It does not say what the result of the package step is, what a command
does when the work folder is missing, when a usage error is found, or what becomes of a
file that a patch added when the build runs again.

**Answer.** After the packages are installed the tool keeps the SHA-256 of the two
requirement files in `build/firmware/venv/odrig-requirements.sha256`; the step runs again
when a requirement file changes. Every command, `test` included, first makes sure the work
folder has WLED's source and the Python environment, because WLED's `requirements.txt` is
one of the two files; so the first command on a new checkout needs the network whichever
it is. The command line is checked before that, so a usage error sets nothing up. The
commit check also refuses a folder that is not a git checkout of its own, so that no git
command meant for WLED can act on this repository. Before the patches are applied, files
that are neither tracked nor ignored by WLED are removed with `git clean`, so a patch that
adds a file applies again; what WLED ignores, its build folders and `node_modules`
included, stays.

**Resolution.** `firmware/fwtool/toolchain.py`, `firmware/fwtool/wled.py`,
`firmware/fwtool/cli.py`; `tests/firmware/test_wled.py`, `tests/firmware/test_cli.py`.

## Seed 04: Comparing the home folder before and after

**Question.** Tasks 1, 2 and 9 list the entries of the home folder with their modification
times before and after a step and expect the two lists to be the same. The agent that ran
the steps is itself a program on this Mac that writes into the home folder while it works,
and a cache of pip or npm would not show in the top level at all: it would land in
`~/Library/Caches` or in `~/.npm`, whose own times do not change.

**Answer.** The list also covers the folders where such things land: `~/.cache`, `~/.npm`,
`~/.config`, `~/.local`, `~/.local/share`, `~/Library/Caches`,
`~/Library/Application Support` and `~/Library/Preferences`, each with the time of every
entry. The lists are compared, and an entry that differs is named in `docs/firmware.md`
with the program it belongs to. A difference that belongs to the tool or to a program it
started would be a failure of the task.

**Resolution.** `docs/firmware.md`, "Verified on the board".

## Seed 04: The flash size in the stock bootloader

**Question.** The design writes every file with `--flash-size keep`, and for
`restore-stock --full` puts the stock bootloader and partition table into the same esptool
call. The stock file `bootloader_s3.bin` has the flash size 8 MB in its header. The
bootloader on the board is that file with 16 MB in the header and the checksum that follows
from it, which is what esptool makes of it when it writes a bootloader and is told to use
the size of the chip. Written as it is, the file would start a board that takes its 16 MB
flash for 8 MB, with the storage partition beyond the end.

**Answer.** A call that writes the bootloader passes `--flash-size detect`, with mode and
frequency kept; every other call keeps all three, as designed. `--full` checks the layout
in the stock partition table it is about to write, since the board's own table is what it
replaces. `--full` was not run on the board: a bootloader that fails to write leaves a
board that only the chip's own download mode recovers. Instead esptool compared the flash
with the three stock files as the tool would write them, and they are what the board
holds.

**Resolution.** `firmware/fwtool/flasher.py`, `Flasher.write` and `Flasher.verify`;
`firmware/fwtool/cli.py`, `_restore_stock`; `tests/firmware/test_flasher.py`;
`docs/firmware.md`, "restore-stock" and "Verified on the board".

## Seed 04: The C++ level the WLED build really uses

**Question.** Fact R28 of the design had two sources that disagree about the C++ level, and
read `-fexceptions` in the build script of the Arduino core.

**Answer.** The verbose build of WLED's own environment compiles every C++ file with
`-std=gnu++11 -fno-exceptions -fno-rtti -Os`. C++17 is not used, and exceptions are
switched off, not on. The core is written for exactly this: C++11 without exceptions and
without run-time type information.

**Resolution.** `docs/firmware.md`, "Verified on the board", A5. The entry "Seed 02: The
C++ language level" is confirmed.

## Seed 04: What the board suite compares in task 2, and the stock build's number

**Question.** Task 2 writes `tests/board/test_flash_restore.py` "for now with the
stock-built image in place of the firmware", and the design has that test compare the files
of storage before and after. The module that reads the files of storage is task 4's. How
does a test tell the stock-built image from the release image, when both are WLED 16.0.1?

**Answer.** In task 2 the test restores stock, flashes the stock-built image and restores
stock again, and checks WLED's handshake each time. The image built from source answers
with the number in WLED's source at the tag, 2605010; the release image answers 2606300,
so the test expects two different answers. Storage was compared once by hand in this
task, as whole images read before and after: the same bytes. The comparison by files joins
the test in task 5, as its task says.

**Resolution.** `tests/board/test_flash_restore.py`; `docs/firmware.md`, "Verified on the
board", A4 and A6.

## Seed 04: The current limiter with ten legs, and what an output gives back

**Question.** The design has the probe build report, for each output, the CRC-32 of the
colours read back from it, and the tests compare that with the bytes that were sent. It
also keeps WLED's current limiter active with the maximum of WLED's LED settings, which is
850 mA on the board. WLED counts 1 mA for every LED at rest, so ten legs of 180 LEDs are
estimated at 1,800 mA before any LED is lit, and the limiter then dims every refresh to
its lowest level whatever the picture. An output that was dimmed does not give back what
it was sent, and WLED's way of giving a colour back divides by the dimming.

**Answer.** The limiter is left as the seed asks. Two things follow.

For the owner: with ten legs wired, the LEDs stay at their lowest level until WLED's
maximum current is raised to what the power supply gives, in WLED's LED settings. The
firmware does not raise it. `docs/firmware.md` says so.

For the tests: the probe build's report has one more member, `limited`, the sends in which
the limiter dimmed. A test expects the exact bytes when `limited` is 0, and when it is not,
exactly what the dimming makes of the bytes: at the lowest level a channel stays lit when
it is above a quarter of the colour's largest channel, and WLED gives it back as 128. With
the pattern of task 3 this holds for all ten outputs, which shows that each output gets its
own leg's data in the right order. Exact bytes on ten outputs are checked in task 6 with a
ten-leg mapping of few LEDs, which the limiter does not dim.

The outputs are read back after the send and compared before the next one, so `overwritten`
is counted the same way with and without dimming.

**Resolution.** `firmware/usermod/odrig_probe.cpp`; `tests/board/test_probe.py`;
`docs/firmware.md`, "The probe build" and "Verified on the board".

## Seed 04: The access point, reported over USB

**Question.** The entry "Seed 04: How the board reports that its Wi-Fi network is up" left
that report to a person with a device on the network, because the firmware's port carries
only the commands of `docs/commands.md`. The probe build already answers one line of its
own on the port.

**Answer.** The probe build's report has the member `ap`: 1 while WLED's access point is up.
A program can so establish over USB that the board reports its network as up, which is the
first half of item 7 of the definition of done. Whether a device can join it and send
commands stays the owner's check. The firmware itself still has no such report on the
port, and `status` is unchanged.

**Resolution.** `firmware/usermod/odrig_probe.cpp`; `docs/firmware.md`, "The probe build".

## Seed 04: Outputs after one that cannot be made, and details of the outputs

**Question.** Requirement 8 wants the other outputs to work when one cannot be made. WLED
starts its outputs in order and stops at the first that does not work, so the outputs after
it would stay silent. WLED's settings can also hold a list of colour orders for ranges of
LEDs, which would change the order of an output made by the usermod.

**Answer.** After it has replaced the outputs, the usermod starts every working output
that comes after one that failed. It empties WLED's list of colour orders for ranges, so
every output has the one order, green, red, blue. An output's start and length are kept in
16 bits, as WLED keeps them, so that the comparison with the legs cannot disagree for
ever.

**Resolution.** `firmware/usermod/odrig_leds.cpp`, `apply` and `matches`. Task 6 tests a
mapping with a pin the chip keeps for itself.

## Seed 04: What the board suite leaves on the board

**Question.** Every task says what the board runs when it ends, and the tests of one run
flash several images in an order that discovery chooses. Which test puts the last image
on?

**Answer.** The package `tests/board` loads every test file of its folder by discovery and
adds one last step of its own, which makes the board run what the suite leaves there. In
task 3 that is the probe build; from task 5 on it is the firmware with the dim example
show. A test file added to the folder still runs without a change anywhere.

**Resolution.** `tests/board/__init__.py`, `load_tests`; `tests/board/support.py`,
`leave_the_board`.

## Seed 04: Reading the board's storage only when it changed

**Question.** The design reads the whole storage partition at the start of every
`install-show` and `read-show`. That takes 64 seconds, and the board suite installs dozens
of shows. The design also keeps every image it reads and writes, 10 MB each, in the work
folder, without end.

**Answer.** The tool keeps the newest eight storage images in `build/firmware/storage/`.
Before it reads the partition it has esptool compare the board's storage with the newest
image it kept, which the chip does by working out a checksum, in 17 seconds. When the
checksum agrees, that image is the copy of storage as it is now; when it does not, the
partition is read as designed. The copy from before a write is so still in the work folder
when the write begins. `install-show` takes 36 seconds this way, plus the wait for the
reply.

Installing the files that `/odrig` already holds changes no block and writes nothing.

**Resolution.** `firmware/fwtool/storage.py`, `from_board`, `keep` and `with_show`;
`tests/firmware/test_storage.py`; `docs/firmware.md`, "install-show".

## Seed 04: A folder that is no show folder, and the order of the checks

**Question.** The design refuses, unless `--no-check` is given, a folder that is not a
valid installed file set "and no other entry in the folder", with seed 01's reason. Seed 01
has no reason for a file the show does not name, for a folder inside the folder, or for a
path that is no folder. `read-show` needs a reason for an output folder that is not empty.

**Answer.** A path that is no folder, an entry that is no file, and, with the check, a
file the show does not name are `not-a-show-folder`, a reason of the tool. An output
folder that exists and is not empty is `output-not-empty`, the name the converter gives
the same condition. The valid file set is checked in the order of `docs/reasons.md`:
mapping, show, then each named file: present, decodable, of the mapping's size. A file
that is both damaged and of another size is `file-malformed` here, where the core, which
reads the header first, may say `size-mismatch`; the folder is refused either way.

**Resolution.** `firmware/fwtool/storage.py`, `folder_files` and `write_folder`;
`docs/firmware.md`, the table of reasons.

## Seed 04: What the install tests of task 4 can see

**Question.** Task 4 runs `install-show` against the probe build of task 3, which answers
no `status`, and asks for assumption A13 "as far as it can be seen here". What can be
seen?

**Answer.** The test expects `no-reply` after every check of the tool passed, as the task
says. It then reads the board's storage back, after the board has started on it: the
storage still has the checksum of the image the tool wrote. WLED formats a file system it
cannot mount, so this shows that WLED mounted the edited image and did not change it. The
show that the suite leaves on the board is the dim example show, which its last step
installs when `/odrig` holds something else.

**Resolution.** `tests/board/test_install.py`; `tests/board/support.py`,
`leave_the_board`.

## Seed 04: Replies that waited in the port's driver

**Question.** The design writes a reply with `Serial.write` and relies on fact R19 for the
rest. On the board, with the first build of task 5, about one reply in twenty did not
arrive: the command tool waited in vain, and the reply came out together with the reply to
the next command, however long that took. Measurements in the firmware showed that the
reply was written at once and then stayed in the driver's buffer. The driver of the
Arduino core hands a packet to the chip's USB unit when that unit reports that the
computer took the packet before; when it writes, it first offers the computer an empty
packet and then waits for that report, and the report can be cleared in the moment it
arrives. Nothing brings it back until the next byte comes in. How often this happens
depends on the timing of the build: one build lost 3 replies of 14, another none of 500.

**Answer.** The usermod watches the driver's buffer. For as long as something waits in it,
the usermod asks the USB unit every 2 ms to offer the computer a packet again, which brings
the report back; with nothing waiting it does nothing. For this one thing
`odrig_serial.cpp` includes a header of the chip's own software,
`hal/usb_serial_jtag_ll.h`, beside WLED's header. WLED's files and the Arduino core are
not changed. With the watch, 600 exchanges in a row and the board suite got every reply.
Stock WLED and the probe build of task 3 did not show the fault, because they write a
reply in several pieces or in one long piece, which the driver keeps pushing.

**Resolution.** `firmware/usermod/odrig_serial.cpp`, `keepSending`;
`tests/board/test_commands.py`, `test_every_reply_arrives_while_the_tool_waits_for_it`;
`tests/firmware/test_usermod_files.py`, the one allowed header.

## Seed 04: Asking the core for refreshes before the outputs are the mapping's

**Question.** Task 5 leaves the outputs WLED's and dark and gives task 6 "step 5 of the
design's loop: ask the core when the outputs can take data and send every refresh". Task 5
also compares the replies of the board with the emulator's. The `animation` of a reply to
`status` is the item the latest refresh chose, so a core that is never asked for a refresh
answers `null` where the emulator answers 1.

**Answer.** From task 5 on the usermod asks the core for a refresh in every pass of its
loop and, in task 5, throws the LED data away. Task 6 makes the request wait for the
outputs and sends the data. In task 5 `fps` is therefore the rate of the requests, 50, and
not yet the rate of what the LEDs get.

**Resolution.** `firmware/usermod/odrig_usermod.cpp`, `loop`.

## Seed 04: The session that the board and the emulator are compared with

**Question.** The design compares the replies to one session of commands on the board and
in an emulator that runs the same folder. The emulator of the test is started for the
session; the board has been running, with whatever brightness and item earlier tests left,
and both count the turns of a cycle from their own start.

**Answer.** The test restarts the board before the session, so both begin in the state
after power-on, and the session begins with `status`, which compares that state too. Every
`status` under the cycle comes within a few seconds of the start or of `play 3`, so both
are in the first turn. The replies are compared as JSON objects without the member `fps`,
together with the exit status of the command tool. The session holds every command and the
three error codes the tool can cause on a valid show; `show-invalid` is caused in the
install test, with an invalid show, and `unknown-command` cannot be caused with the tool.

**Resolution.** `tests/board/support.py`, `SESSION`, `session` and `emulator`;
`tests/board/test_commands.py`; `tests/board/test_install.py`.

## Seed 04: Details of the host functions on the board

**Question.** The design gives the host functions in a table. It leaves open how the
memory is aligned, what `open` does with a file that is still open, and what a name longer
than a show can have is.

**Answer.** Memory is taken aligned to 8 bytes, since the core's interface asks for memory
"aligned for any object" and the chip's allocator gives 4. `open` closes a file that is
still open first, although the core closes its file before it opens another. A name longer
than 32 characters, which no show can name, is answered with the failure value. The probe build's report takes its `error` from the core through
a function the usermod gives it, under the lock.

**Resolution.** `firmware/usermod/odrig_files.cpp`; `firmware/usermod/odrig_usermod.cpp`.

## Seed 04: Asking the core while the LEDs are still being written

**Question.** The design's loop asks the core for a refresh only when the outputs can take
new data, and sends at once. With ten legs and the dense 60 x 30 clip, measured on the
board, a refresh then costs the time the LEDs need on the wire, 5.4 ms, then the core's
work for a frame, 6.6 ms on average for the compressed clip, then the send, 7.7 ms with
the limiter's dimming: 19.7 ms of the 20 there are. The firmware still reported 49 or 50,
and the probe build, which also reads the outputs back, 46 to 49.

**Answer.** The usermod asks the core in every pass until the core has produced a refresh,
keeps that refresh until the outputs are free, sends it, and only then asks again. The
core's work for the next frame so happens while the last one is on the wire. What the
design wanted from its rule still holds: every refresh the core counts is sent, none is
overwritten before it is sent, and `fps` is the real rate. With this loop the probe build
sends 49 to 51 refreshes a second for both dense clips. Playback stays in WLED's main
loop; the measurements gave no reason for a task of its own.

**Resolution.** `firmware/usermod/odrig_usermod.cpp`, `loop`; `docs/firmware.md`, "What
the firmware does" and "Verified on the board".

## Seed 04: What the board tests of the outputs use, and the probe's sums

**Question.** The design's `test_probe.py` compares each output's CRC with the emulator's
recording for the example show's mappings and the ten-leg mapping. The limiter dims every
refresh of ten legs of 180 LEDs, and a bright picture on two legs, so those cannot be
compared byte for byte. The design also has no test for an output that cannot be made or
for an invalid mapping, which Requirement 8 names, and its probe reports only the longest
times.

**Answer.** The one-frame show gives every pixel a small colour of its own, which the
limiter does not dim on two legs. Ten outputs are compared byte for byte on a ten-leg
mapping of 18 LEDs for each leg, and on `mapping/legs-10.json` against what the limiter's
lowest level makes of the recording. Two tests are added: a mapping with a leg on pin 60,
which the board does not have, and a show folder with a broken `mapping.json`. The probe
build's report gets `poll_total_us` and `send_total_us`, the sums over the last full
second, so that means can be given, and it reads the outputs back around one send in five
only, so that its own work costs little of what it measures. The test of the rate while
`status` is asked five times a second keeps the port open, with the command tool's own
way of opening it.

**Resolution.** `tests/board/test_probe.py`, `tests/board/test_fps.py`,
`tests/board/support.py`; `firmware/usermod/odrig_probe.cpp`.

## Seed 04: What of the HTTP transport could be tried without the network

**Question.** Task 7 adds `POST /odrig`, the report in WLED's information and the suite
`tests/air/`, and says that `test-air` cannot be run by an agent. How sure is code that
never ran?

**Answer.** The firmware with the handler in it was built, flashed and run through the
whole board suite, so the handler does not disturb what the port and the LEDs do. The
handler itself did not serve a request. The tests of `tests/air/test_http.py` were run
against the emulator, which answers `POST /odrig` by the rules the board must follow; they
pass there, which shows that the tests themselves are sound, not that the board passes
them. `tests/air/test_wled.py` asks WLED's own interface and has not run anywhere. The
session over HTTP is compared with the same session through the port on the same board,
each begun with `on`, `brightness 32` and `play 3` through the port, because restarting
the board would take the network away from the Mac. A board whose core could not start
answers `POST /odrig` with 503, as the design says.

The text of the outputs for WLED's information is made on the loop's task and only read by
the web server's task, so that no output is looked at while WLED makes the outputs again.

**Resolution.** `firmware/usermod/odrig_http.cpp`; `firmware/usermod/odrig_leds.cpp`,
`summary`; `tests/air/`; `docs/firmware.md`, "What the firmware does" and "test-air". The
owner's checks of task 10 run `test-air`.

## Seed 04: Storage blocks that esptool takes for a program

**Question.** During task 7 every `install-show` began to fail with `esptool-failed`, after
some thirty installs had worked: esptool refused to write, with "is not an ESP32-S3 image".
esptool looks at every file it is given to write; one that begins with the byte `E9`, the
first byte of a program image, it takes for a program and refuses when the rest is not a
program for the chip. A block of storage can begin with any byte. The first block of the
file system begins with a counter that goes up with every change, and it had reached 233,
which is `E9`. A file of a show whose data block begins with that byte would do the same.

**Answer.** When the tool writes storage it tells esptool to leave that check out, with
esptool's `--force`. That option also leaves out esptool's warnings about a chip with
secure boot or flash encryption, which this board does not use and which do not concern a
write to storage; the tool's own check of every address against the storage partition
stays. A program, written by `flash` and `restore-stock`, is never written that way, so a
program for another chip is still refused. The tool also names a new storage image as one
of its kept images only when the board holds it; until then the image has a name the tool
does not take for the board's.

**Resolution.** `firmware/fwtool/flasher.py`, `Flasher.write`;
`firmware/fwtool/storage.py`, `pending` and `keep`; `firmware/fwtool/cli.py`,
`_install_show`; `tests/firmware/test_flasher.py`, `tests/firmware/test_storage.py`. The
board suite found it; the tests were run against the code without the change first.

## Seed 04: Waiting for a board that starts slowly

**Question.** The design gives `flash` and `install-show` 20 seconds to wait for the
board's answer after its restart. The core checks every file at start; with storage filled
with 9 MB of dense clips that took 38 seconds on the board, during which it answers
nothing, so `install-show` of such a show would end with `no-reply` although nothing is
wrong.

**Answer.** Both commands take `--wait SECONDS`; without it they wait 20 seconds as
designed. The measurement test gives the full storage 240 seconds. The 9 MB are twelve
copies of the dense clip of 10 seconds under names of their own and one of 4 seconds,
9,001,905 bytes with the two JSON files, which is what fits beside WLED's own files.

**Resolution.** `firmware/fwtool/cli.py`; `tests/board/test_measure.py`;
`docs/firmware.md`, "flash", "install-show" and "Measurements on the board".

## Seed 04: Criteria that had no test, and a test of the start without a command

**Question.** Task 9 reads the acceptance criteria of Requirements 1 to 15 again and adds a
test where a program can check a criterion and none does. Which were missing, and what of
the owner's first check can a program see?

**Answer.** Added in `tests/firmware/`: that the tool's own packages are pinned at exact
versions and WLED's pinned PlatformIO comes first, that nothing is fetched or installed
when the work folder has it all, that a Python below 3.10 is refused, and that every tool
is taken from the work folder (Requirements 1.6, 2.1, 2.3, 2.4); and, read in the
usermod's sources, where the core's memory comes from, which clock it is given, that files
are opened for reading only and in the show's folder, how a leg becomes an output, that a
refresh goes to the outputs directly at full brightness, and that WLED is held in its live
mode at every pass (Requirements 7.2, 7.3, 7.4, 7.6, 8.1, 9.2, 9.3, 10.1, 10.2). Added in
`tests/board/`: after a restart with no command sent to the core, `status` reports the
cycle playing, its two animations take turns after 15 seconds, and the rate is 49 or more
(Requirements 7.1 and 16.1, as far as a program sees them: what the LEDs show stays the
owner's). Added in `tests/air/`: WLED's own switch, brightness and live override do not
change what `status` reports (Requirement 9.4, for the owner to run).

Requirement 3.2, the core compiled with the flags of the environment, has no test of its
own: the flags were compared in the verbose build of task 5, and the tests hold what makes
it so, that `core/library.json` and the override give the core no flag.

**Resolution.** `tests/firmware/test_toolchain.py`, `tests/firmware/test_usermod_files.py`,
`tests/firmware/test_docs.py`, `tests/board/test_autostart.py`, `tests/air/test_wled.py`.

## Seed 04: The owner's checks without the owner

**Question.** The last task is the owner's: eyes on the LEDs after a power cycle, two legs
wired, and a device joined to the board's Wi-Fi network. The agent that implemented the
seed had the board on USB with one 60-LED strip on leg 1, could not see the LEDs, and was
not to join the board's network or to enter a Wi-Fi password anywhere.

**Answer.** Every part a program can establish over USB was done and written under the
task: the show plays from a restart with no command sent and its two animations take
turns every 15 seconds, by what `status` reports; the outputs hold the bytes the emulator
records; `status` reports 50 refreshes a second with the example show; and WLED reports
its access point as up. The four steps of `docs/firmware.md`, "The owner's checks", were
not done. The task is therefore not ticked, its queue record stays undone, and the seed's
state stays `in_progress`: `completed` is set by whoever does the four steps.

One thing the owner will meet at step 1 that no test shows: with one strip fed from the
board's 3.3 V pin the installed show has brightness 32, and WLED's limiter, at its maximum
of 850 mA and counting the 360 LEDs of two legs, dims the bright Hello world picture
further. For a brighter picture the show's brightness and WLED's maximum current are both
the owner's to set for the power supply in use.

**Resolution.** Seed 04 `tasks.md`, task 10, which stays open; `docs/firmware.md`, "The
owner's checks".

## Seed 05: Where leg 1 stands and where its snake begins

**Question.** The owner said the strips of the target stand upright and each snake begins at
the bottom, but not which leg is leftmost or which of a leg's three columns comes first.

**Answer.** Leg 1 is the leftmost leg and its snake begins at the bottom of its left column,
so its first LED is the bottom-left LED of the canvas, (1,1), which is where the coordinates
start. Legs are numbered left to right. The owner was shown this reading and has not yet
confirmed it by eye.

**Resolution.** Seed 05 `seed.md`, "Product Context" and Required Behavior 2. If the real
installation differs, only `mapping/legs-20.json` changes.

## Seed 05: Pins for legs 19 and 20

**Question.** Leg N uses the pin labelled N, but pins 19 and 20 carry the USB connection.

**Answer.** Leg 19 uses pin 21 and leg 20 uses pin 47. Both are free, are on the board's pin
rows, and are not boot-mode pins.

**Resolution.** Seed 05 `seed.md`, Required Behavior 2.

## Seed 07: The form of the new commands

**Question.** The owner approves every addition to the command list. The owner asked for
commands for free space, the installed animations, removing and uploading, and was shown
`space`, `list`, `remove <id>` and `upload begin` / `upload data` / `upload end` with their
replies. The owner then ordered the seeds to proceed without commenting on the form.

**Answer.** The commands take the form shown to the owner. Proceeding after seeing them is
taken as approval.

**Resolution.** Seed 07 `seed.md`, Required Behavior 1 to 5.

## Seed 05: Reasons for a column-leg file, and files that mix the two kinds

**Question.** The seed gives the members of a column-leg file and says that a file uses one
kind for all its legs. It names no reason for a file that breaks a new rule, and does not
say what a file with both `width` and `height`, a leg with `rows` in a column-leg file, or
a `first_led` of `"left"` beside `columns` is. `docs/mapping.md` and `docs/reasons.md` are
the authority and know only row legs.

**Answer.** No reason name is added. Every broken rule of either kind is
`mapping-malformed`, as every broken rule of a row-leg file is today, and a missing file is
`mapping-missing`; seeds 06 and 07 so meet the two names they know. The kind of a file is
told by its top level: `width` without `height`, or `height` without `width`. Both, neither,
a leg whose strips member is of the other kind, and a `first_led` of the other kind are all
invalid. The converter's reader checks in a fixed order, given in the design, so that a
second reader can give the same detail; the core gives the name alone and may check in any
order, because its reader takes the members as the file lists them.

**Resolution.** Seed 05 `requirements.md`, Requirement 1; `design.md`, "The mapping file
format", "The reader" and "The core"; `tasks.md`, tasks 3 and 4.

## Seed 05: The spike comes first, and uses row legs

**Question.** The seed wants twenty outputs established "first, by itself, on the board".
The target file is a column-leg file, which no reader can read before most of this seed is
done.

**Answer.** The spike is task 1 and needs none of the new format: twenty outputs of 180
LEDs are twenty row legs of three rows of 60 on the pins of the target file, which today's
format and today's core describe. The rate with a dense 60 x 60 clip is task 2, measured
on the same mapping. The board meets the target file itself in task 8, and the ten-leg
file goes only in task 9, when no test of any suite names it, so that every commit passes
its suites.

**Resolution.** Seed 05 `requirements.md`, Requirement 12 criterion 8; `design.md`, "The
spike" and "Order of work"; `tasks.md`, tasks 1, 2, 8 and 9.

## Seed 05: Where twenty outputs come from

**Question.** The seed says the chip's parallel driver can carry sixteen outputs, and
leaves open whether WLED is patched or the usermod drives the extra outputs itself.

**Answer.** Read in WLED 16.0.1 at the pinned commit and in the NeoPixelBus copy it pins:
the limit of twelve is two constants of `wled00/const.h`, four RMT channels and eight
parallel ones, and the eight-lane form of the library's parallel method that
`wled00/bus_wrapper.h` names. The library has the same method in a sixteen-lane form for
the ESP32-S3, and the chip's LCD unit has sixteen data lines. One patch file changes the
constant to sixteen, switches the parallel types to the sixteen-lane form and corrects
WLED's memory estimate; the usermod stays as it is. The usermod does not drive outputs of
its own: the chip has one LCD unit, and outputs outside WLED would be outside its current
limiter and its information, which seed 04 keeps. What reading cannot settle is whether the
sixteen-lane form sends correct data: the library's maintainer reported in 2024 that it
gave him a single pulse. The spike proves or disproves it. A fault inside the library's own
file is not patched in this seed; the fallback is the seed's: the largest number of outputs
that works, twelve with stock limits.

**Resolution.** Seed 05 `requirements.md`, Requirement 12; `design.md`, "Twenty outputs in
the firmware"; `tasks.md`, task 1.

## Seed 05: Proving an output that has no LED on it

**Question.** One strip is wired, on pin 1, and nobody looks at it. Seed 04 called an
output working when WLED made it and it held its leg's bytes. For a driver form that is
reported to hold data and send nothing, that proves too little.

**Answer.** The probe build measures the signal itself in two ways. It counts the pulses on
each output's pin during one refresh with the chip's pulse counter, which must give 24 for
every LED, and it times how long the parallel driver is busy after a send, which must be
the time the LEDs take on the wire, 5.7 ms for 180. Neither says that the pulses have the
right widths; that an LED strip on a lane of the parallel driver shows its picture stays an
owner's check, with a mapping that puts pin 1 on the sixteenth lane. If the pulse counter
cannot be attached to a driven pin, the wire time stands alone and the finding is recorded
here.

**Resolution.** Seed 05 `requirements.md`, Requirement 12 criteria 5 and 6 and
Requirement 18 criterion 3; `design.md`, "What a program can prove without LEDs";
`tasks.md`, tasks 1 and 10.

## Seed 05: The pins of the twenty legs

**Question.** The seed fixes pins 1 to 18, 21 and 47. Is one of them unusable on this
board: a pin of the flash, of the PSRAM, of USB, a boot-mode pin, or the on-board LED?

**Answer.** None was found unusable, and no pin was changed. All twenty pass WLED's own pin
check for this build. Espressif's pages give the pins to avoid as 19 and 20 (USB), 26 to 37
(flash and octal PSRAM), 0, 45 and 46 (boot-mode pins that boards pull), 43 and 44 (the
serial lines of the second USB socket) and 48 or 38 (the on-board LED). Pin 3 is a
boot-mode pin too, read at reset only, and seed 04 already made a working output on it.
Pin 47 runs at 1.8 V on modules with 1.8 V memory, which the N16R8 is not; the module's
datasheet was not read again for this. The spike proves every pin by its output and its
pulses; a pin that fails gets a replacement and an entry here.

**Resolution.** Seed 05 `requirements.md`, Requirement 12 criterion 10; `design.md`, "The
pins"; `tasks.md`, task 1.

## Seed 05: Fifty refreshes a second with 3,600 LEDs

**Question.** The seed asks for 49 refreshes a second on the board with a dense 60 x 60
clip. Seed 04 measured 6.6 ms for a request and 7.7 ms for a send with 1,800 LEDs while the
limiter dims every LED. Twice the LEDs are about 13 ms and 15 ms, more than the 20 ms there
are, and the limiter dims every refresh of 3,600 LEDs at WLED's maximum of 850 mA.

**Answer.** The spike measures. If the firmware holds 49 with the loop as it is, nothing
changes. Otherwise the request for a refresh moves to a task of its own on the chip's other
processor core, so that decoding runs beside the limiter and the transfer; the design gives
the hand-over, which keeps every call to the core one at a time and every counted refresh
sent. The core's decoder and WLED's limiter are not changed. If the rate still stays below
49, the measured rates are recorded as an open question and the seed stays `in_progress`.
The figures above are estimates until task 1 has measured.

**Resolution.** Seed 05 `requirements.md`, Requirement 13; `design.md`, "The time of one
refresh"; `tasks.md`, tasks 1 and 2.

## Seed 05: The tool that writes docs/mapping.md

**Question.** The seed asks for a tracked tool that produces the drawings and tables of
`docs/mapping.md`, and for a test. It does not say where the tool lives, how the page tells
its generated parts from the rest, or how sixty columns are drawn in a text file.
`docs/mapping.md` says today that its drawings are generated, and no tool is tracked.

**Answer.** The tool is the module `odrig/mapdoc.py`, started as `python -m odrig.mapdoc`,
beside the reader it uses. It is not a subcommand of `python -m odrig`, whose five
subcommands seed 06 mirrors. Generated parts stand between marker comments in the page; the
tool replaces them and leaves the rest. `--check` writes nothing and fails when the page
differs; the test runs it on the tracked files and on copies with a mapping file changed. A
column-leg file is drawn as a row-leg file is, one line for each strip with its two end
numbers and an arrow, so each column lies on its side with the bottom of the canvas at the
left; an upright drawing of sixty columns with numbers does not fit a text page. The order
of the board's pins is a table in the tool, and the test of seed 03 goes on comparing the
page's own table with the drawing. For the bench file the tool writes the bytes the page
has.

**Resolution.** Seed 05 `requirements.md`, Requirement 11; `design.md`, "The tool that
writes docs/mapping.md"; `tasks.md`, task 7.

## Seed 05: The page with twenty upright snakes

**Question.** The seed asks that both views show the 60 x 60 canvas with twenty upright
snakes "clearly, in a wide and in a narrow window", with the board, twenty lines, the paths
and the LED numbers. It gives no layout. Today's layout is written for rows, has twelve
colours, and draws at most ten lines in one channel.

**Answer.** The labels of the legs move to a band along the canvas, the LED numbers stand
upright at the ends of the columns, and twenty colours make every leg its own. The LEDs
view shows the whole canvas in a window of 1280 x 800 with cells of 7 or 8 pixels and
leaves the end numbers out where the cells are under 9 pixels. The mapping view keeps its
cells at 9 pixels or more and is then higher than a window of 1280 x 800: it scrolls up and
down and never sideways. Its lines run in two channels by fixed rules. The pins of the
board are not in the order of the legs, so lines cross: at least 76 times in any drawing
in which they reach the snakes from below, 88 times with the rules chosen, never twice for
one pair and never one on another.
Whether that is clear is judged by eye in the check list. Row-leg files keep the drawing
they have.

**Resolution.** Seed 05 `requirements.md`, Requirements 8, 9 and 10; `design.md`, "The
page"; `tasks.md`, tasks 5, 6 and 10.

## Seed 05: The demo show, its name and its sources

**Question.** The seed says the demo show for the target replaces the ten-leg demo show,
and not what it is called or whether its sources are tracked.

**Answer.** It is `shows/demo-20/show.json`, with the content the ten-leg one had, and
`shows/demo-10/` is removed. Only the show file is tracked: the two sources are 4.2 MB of
JSON, written by the generators into `build/`, as seed 03 settled for the ten-leg show. Its
brightness is 128, for the emulator; the board tests install it dimmed.

**Resolution.** Seed 05 `requirements.md`, Requirement 14; `design.md`, "The demo show";
`tasks.md`, task 9.

## Seed 05: DVD bounce on a square canvas

**Question.** The seed wants DVD bounce "made for 60 x 60". The generator of seed 01 moves
the square one pixel in each direction per frame from the top-left corner. On a canvas as
wide as it is high the square meets a side wall and the top or bottom wall in the same
frame, so it only runs to and fro along one diagonal, in a loop of 116 frames.

**Answer.** The generator is left as it is. Its rule is seed 01's, the sources of the bench
show must keep their bytes, and the seed asks for no change. The demo show is correct and
passes over every leg; it is duller than on the bench. A livelier path, for example a start
away from the corner on a square canvas, is the owner's to ask for.

**Resolution.** Seed 05 `requirements.md`, Requirement 14 criterion 4; `design.md`, "What
uses the reader" and "Risks".

## Seed 05: What fits into storage, and the noisy figure

**Question.** The seed asks that the statement of how much dense content fits into the
board's storage be recomputed. That statement is in `docs/decisions.md`, not in
`docs/format.md`, and beside the dense figure it has one for noisy content that came from a
prototype clip which is not in this repository.

**Answer.** The statement is written into `docs/format.md` and, in the same words, into
`docs/decisions.md`. It is computed from the measured size of the dense 60 x 60 clip of 10
seconds and from two sizes of storage: the partition, 10,354,688 bytes, and the 9,001,905
bytes of animations that seed 04 installed and played. The noisy figure is replaced by what
the format alone gives: content that nothing predicts is stored frame by frame, 10,805
bytes for each 20 ms. With the sizes measured when the spec was written that is 65 to 74
seconds of the dense clip compressed and 16 to 19 seconds stored.

**Resolution.** Seed 05 `requirements.md`, Requirement 16 criterion 3; `design.md`,
"Measured sizes and what fits"; `tasks.md`, task 10.

## Seed 05: Criteria of earlier specs that name the ten-leg build

**Question.** The specs of seeds 03 and 04 have criteria about the ten-leg mapping, a
60 x 30 canvas and `shows/demo-10`, and the check list by eye of `docs/emulator.md` and its
test cite them by number. This seed removes what they name, and the earlier specs are not
to be edited.

**Answer.** The earlier spec files keep their text as a record. The requirements of this
seed take the place of those criteria. The check list by eye keeps one step for each
criterion of seed 03 it had, done with the twenty-leg demo show and the dense 60 x 60 clip,
and gains steps for this seed's criteria, marked with the seed's number; its test reads
both.

**Resolution.** Seed 05 `requirements.md`, the introduction and Requirement 18; `design.md`,
"Documents"; `tasks.md`, tasks 9 and 10.

## Seed 05: What needs eyes, and when the seed is completed

**Question.** Whether the two views are clear, and whether LEDs light, cannot be settled by
a program, and the owner is not available. Seeds 03 and 04 stay `in_progress` for checks
only the owner can make.

**Answer.** The check list by eye is gone through in Chrome by a person or by a tool that
drives the browser and takes screenshots that are looked at, as seed 03 did; that is part
of this seed's work. What no program on this Mac can establish is listed as owner's checks
and does not hold the seed open: a strip on a lane of the parallel driver, twenty wired
legs, and the check list in Safari. The seed stays `in_progress` only if the board does not
reach 49 refreshes a second, or if no tool that drives a browser is at hand.

**Resolution.** Seed 05 `requirements.md`, Requirement 18 and Requirement 13 criterion 5;
`tasks.md`, tasks 10 and 11.
## Seed 08: Where the settings file is and what it looks like

**Question.** The seed asks for "one tracked settings file" with the name and the password.
It names neither the file's place nor its format nor its members.

**Answer.** `firmware/wifi.json`, beside the tool that reads it: a JSON object with exactly
the two strings `name` and `password`, read with the strict reader that reads `show.json`.
Every other tracked settings file of this project is JSON, and `.gitattributes` keeps git
from changing its bytes. It has no version member: it holds two values. A command can be
pointed at another file of the same format with `--settings FILE`, which is how the tests
give it other values; no option carries a name or a password itself, so neither lands in a
shell history.

**Resolution.** `docs/specs/08-p1-wifi-name-and-password/requirements.md`, Requirements 1
and 2; `design.md`, "The settings file" and "Reading and checking a settings file".

## Seed 08: "Nowhere else in the repository", and the name

**Question.** The seed says the name and the password live in the settings file "and
nowhere else in the repository". The name is `odrig`, the project's own name:
`docs/decisions.md` states it, the seed states it, and `docs/wifi.md` must describe the
network.

**Answer.** The rule is read as: there is no second source of the settings. No source of
the tool holds either value, and the tool takes them from a settings file only. The
password is in no other tracked file at all, which a test checks over every tracked file.
The name is also written in the documents that describe the network and in the one test
that checks that the file names `odrig`. Two things the rule cannot reach: every password
that was ever committed stays in the repository's history, and outside the repository the
password is on the board and in the storage images of the work folder, which are copies of
the board's storage that git ignores.

**Resolution.** Seed 08 `requirements.md`, Requirement 1 criteria 4 and 5 and Requirement 5
criterion 3; `design.md`, "The settings file".

## Seed 08: Which characters a name and a password may have

**Question.** The seed gives the limits in characters: 8 to 63 for the password, 1 to 32
for the name. The radio counts bytes, a WPA2 password is defined over printable ASCII, and
a name may be any 32 bytes. A name of 32 characters in another script is longer than 32
bytes, and WLED would cut it.

**Answer.** Both values are printable ASCII only, the characters from the space to the
tilde, so a character is a byte and the seed's counts are the radio's. A value is taken as
it is in the file; nothing is trimmed. A name in another script would need a limit in
bytes, which is the owner's to ask for.

**Resolution.** Seed 08 `requirements.md`, Requirement 2; `design.md`, "Reading and
checking a settings file".

## Seed 08: Where WLED keeps the name and the password, and what the tool writes

**Question.** The seed says the tool "writes the name and password into the board's
settings" and that WLED's other Wi-Fi settings are not changed. It does not say where those
settings are. WLED 16.0.1 keeps the name in `/cfg.json`, as `ap.ssid`, and the password in
`/wsec.json`, as `ap.psk`. It also reads a password from `/cfg.json` when one is there, in
place of the other, serves `/cfg.json` to every device on the network, and writes the
password's length there as `ap.pskl`. The board today holds the `/cfg.json` of the proof of
concept, with LED settings only, and no `/wsec.json`.

**Answer.** The tool sets `ap.ssid` and `ap.pskl` in `/cfg.json` and `ap.psk` in
`/wsec.json`, and removes an `ap.psk` from `/cfg.json`. A missing `ap` object or a missing
file is made with these members only; WLED uses its defaults for every member that is
absent. Everything else keeps its value and its place: the channel, the hidden name, when
the access point opens, the networks to join, and WLED's backup of its settings. `ap.pskl`
is not read by WLED; it is set so that the file is what WLED itself would write. A file
that already holds the values keeps its bytes.

**Resolution.** Seed 08 `requirements.md`, Requirement 4; `design.md`, "Editing WLED's
stored settings", facts W3 to W6 and observations B1 to B4.

## Seed 08: What "installs the firmware on a board from scratch" is

**Question.** The seed says the settings are applied "whenever the firmware tool installs
the firmware on a board from scratch". The tool has no such command. `flash` writes the
application only, and Requirement 4 of seed 04 says that it does not write storage and
leaves storage as it was, which the board suite checks. "From nothing to a playing board"
in `docs/firmware.md` is a list of commands.

**Answer.** A new command, `install-firmware`: it checks the settings file and the image,
writes the firmware as `flash` does, waits for the reply to `status`, and applies the
settings as `set-wifi` does. `flash` stays as seed 04 defines it, and the list in
`docs/firmware.md` names `install-firmware` in its place. A board from scratch is one with
WLED's 16 MB layout whose storage does not hold the settings yet; a chip with nothing on it
is first given the stock bootloader and partition table with `restore-stock --full`, as
before. A board that only ever got `flash` keeps WLED's default password. The owner may
prefer that `flash` itself applies the settings; that changes a requirement of seed 04 and
is the owner's to decide.

**Resolution.** Seed 08 `requirements.md`, Requirement 6 and Requirement 4 criterion 8;
`design.md`, "`install-firmware`".

## Seed 08: How the board reports its network's name over USB

**Question.** The definition of done says "the board reports over USB that its network is
up under the name `odrig`". The firmware's port carries only the commands of
`docs/commands.md`, `status` has no member for Wi-Fi, and a command is added only with the
owner's approval. WLED's own information reports whether the access point is active, not
its name, and is reached over the network. The probe build reports `ap`.

**Answer.** The probe build's report gets `ap_name` and `ap_auth`: the name and the
protection in the configuration the chip's radio holds for its access point, read with the
chip's own `esp_wifi_get_config`, and `null` while `ap` is 0. A board test takes "up under
the name" from `ap` and `ap_name`, and "a password is set" from `ap_auth`, which is 3 for
WPA2, and from storage read back, which must hold the password of the settings file; the
two passwords are compared without being printed. The firmware has none of this code and
no command is added. The usermod still names no Wi-Fi function of WLED: the call is the
chip's, only reads, and is in the probe file. That a device can join stays the owner's
check.

**Resolution.** Seed 08 `requirements.md`, Requirement 7; `design.md`, "The probe build's
report" and "How a program establishes the network over USB", facts W8 and W10 to W12,
assumption A1.

## Seed 08: Settings of WLED that decide whether the network opens, and what undoes ours

**Question.** The seed says that after the restart the board hosts the network, and also
that WLED's other Wi-Fi settings and its web interface are not changed. WLED's source shows
what the second sentence leaves open: the access point opens at start only while no network
to join is configured, else as WLED's setting for it says, and never with the setting
"button only"; whoever has joined the network can change the name and the password in
WLED's Wi-Fi settings page; and button 0, on pin 0, brings back WLED's default name and
password until the next restart when held for more than 5 seconds, and formats the file
system when held for more than 10.

**Answer.** The tool changes none of this. The board hosts the network as the seed says
when it is as it is today: no network to join, WLED's default setting. `docs/wifi.md` says
what changes that, and that `set-wifi`, and `install-show` after a format, put things back.
The button and the limit of four joined devices were read in the source and are not tried:
no task presses a button. The owner may later want WLED's settings locked or its interface
closed; the seed leaves the interface open "for now".

**Resolution.** Seed 08 `requirements.md`, Requirement 4 criterion 3, Requirement 7
criterion 1 and Requirement 9 criterion 3; `design.md`, "What is left as it is", facts W8,
W9, W14 and W15.

## Seed 08: What the command prints, and when it is done

**Question.** The seed says one command writes the name and the password "and restarts the
board". It does not say what the command prints, how it knows that the board is back, or
what it does when the board already holds the settings.

**Answer.** As `install-show` does, the command waits for the board's reply to `status`,
for 20 seconds or as long as `--wait` says, and ends with `no-reply` when none comes; the
settings are stored then. It prints `name: <name>`, `password: set` and the reply. Its exit
status does not depend on whether the show is valid, which is `install-show`'s matter. When
the board already holds the settings, nothing is written and the board is restarted all the
same. On a board that runs stock WLED the command stores the settings and ends with
`no-reply`, because stock WLED answers no `status`.

**Resolution.** Seed 08 `requirements.md`, Requirement 3; `design.md`, "`set-wifi`".

## Seed 08: Keeping the password out of tests, logs and hand-overs

**Question.** The seed says the password "is never printed by the tool or written to a
log". The tool keeps storage images in the work folder, and every one of them holds
`/wsec.json`. A failing test prints the two values it compared. The spec and its tasks are
tracked files, and whoever implements task 1 needs the password.

**Answer.** The tool writes no log. The storage images are copies of the board's storage in
a folder git ignores; they hold the password as the board does, and `docs/wifi.md` says so.
An error line quotes no text of a settings file, and the settings' text form inside the
tool hides the password. A test reduces a comparison of passwords to true or false before
it asserts. The board test that applies other values uses a name that begins with
`odrig-test` and a password made in that run, and puts the settings file's values back. The
spec holds no password: the implementer of task 1 gets it with the hand-over and writes it
into the settings file only, and without it the task is blocked, not done with a password
somebody made up.

**Resolution.** Seed 08 `requirements.md`, Requirement 5 and Requirement 8 criterion 5;
`design.md`, "Keeping the password out of sight"; `tasks.md`, the rules and task 1.

## Seed 08: What docs/wifi.md says beyond the name and the password

**Question.** The seed asks that `docs/wifi.md` describe the network and how to change its
name and password. That page lists three things as not decided or not verified: the name
and the password, how many phones can be joined at once, "not looked up or tested", and the
range on site. `docs/android-app.md` still asks whether the network should have a password.

**Answer.** The item on the name and the password goes. The number of phones was looked up
while WLED's source was read for this spec: four, the default of the Arduino core's
`softAP`, which WLED's call leaves. `docs/wifi.md` gives it as read and not tried, and it
stays in the list of what is not verified; nothing changes the limit. The range stays in
that list. `docs/android-app.md` is the page of seed 09 and is not edited here;
`docs/decisions.md` already holds the answer to its question.

**Resolution.** Seed 08 `requirements.md`, Requirement 9; `design.md`, "Documentation" and
fact W10.

## Seed 08: Seed 04 is not completed

**Question.** The seed depends on seed 04, whose state is `in_progress`: its last task, the
owner's checks, is open.

**Answer.** Seed 08 needs seed 04's tool, its probe build and its suites, which are done,
so its tasks do not wait. From task 4 of seed 08 on, the two owner's checks of seed 04 that
need the board's network are done on the network `odrig` with the password of the settings
file; task 6 writes that into the steps of `docs/firmware.md`.

**Resolution.** Seed 08 `tasks.md`, the opening paragraph and task 6.

## Seed 08: Recording the seed's progress

**Question.** As for the other seeds, and as for seed 04: the definition of done has an
item only a person can check.

**Answer.** The spec commit leaves `state.json` as it is. The first task sets
`in_progress`. The last task is the owner's check and sets `completed`; an agent leaves it
open.

**Resolution.** Seed 08 `tasks.md`, tasks 1 and 7.

## Seed 05: What the spike found, and a refresh that is copied while the last one is on the wire

**Question.** The design left five assumptions to the spike, A1 to A5, and gave the rate
to the second task. Requirement 12 asks that its criteria 1 to 7 be established in the
spike, and criterion 7 is the rate with a picture that does not change. What was found, and
what had to change at once?

**Answer.** A1 to A4 hold. With the patch the firmware makes twenty working outputs from
twenty row legs on pins 1 to 18, 21 and 47: four RMT and sixteen on the parallel driver in
its sixteen-lane form. The chip's pulse counter counts 24 pulses for every LED on each of
the twenty pins, 432 for 18 LEDs and 4,320 for 180; the parallel driver is busy for 0.8 ms
after a send of 18 LEDs and for 5.7 ms after one of 180, which is the 84 and the 570 bytes
they are on the wire; on legs of 18 LEDs every output holds exactly its leg's bytes; and
135,700 bytes of internal memory stay free with twenty outputs of 180 LEDs and the core.
No pin had to be changed. With the patch file moved out, outputs 13 to 20 do not work.

A5 does not hold with the loop of seed 04. With 3,600 LEDs and WLED's limiter dimming every
LED, a send takes 16.4 ms: 4.1 ms to copy the colours into the outputs and 12.3 ms for
WLED's show, in which the limiter reads and writes every LED again and the driver's buffer
is filled. The loop began a send only when the outputs could take data, 5.7 ms after the
last one: 22 ms for a refresh, and the probe build sent 41 or 42 of a still picture in a
second.

An output keeps what it is sending apart from what it is given: the RMT method has a
buffer for each, and the parallel method fills its own buffer at the show. So the copy does
not have to wait for the wire. Task 1 therefore splits the send in two: the refresh is
copied into the outputs as soon as the core has produced it, and shown as soon as the
outputs can take data. A refresh of a still picture then costs 16.4 ms, and 49 to 51 are
sent in every second, with 20 ms as the longest time between two. This is the first half of
step 2 of the design's "The time of one refresh", taken early because the spike is where
criterion 7 is to be established; the design has the copy wait for the outputs, which it
need not.

The dense 60 x 60 clip still falls short, as the design expected: 21 to 23 refreshes a
second for the compressed file and 31 or 32 for the uncompressed one, with the request in
the loop. A request then takes 28 ms and 14 ms on average because it decodes every frame
since the last one, 2.3 and 1.6 of them; one frame is 12.3 ms compressed and 8.6 ms
uncompressed. Moving the request to a task of its own is task 2.

**Resolution.** `firmware/patches/010-sixteen-parallel-outputs.patch`;
`firmware/usermod/odrig_leds.cpp`, `fill` and `show`; `firmware/usermod/odrig_usermod.cpp`,
`loop`; `tests/board/test_twenty.py`; `docs/firmware.md`, "What the firmware does" and
"Verified on the board".

## Seed 05: How the probe build measures with twenty outputs

**Question.** The design takes the wire time in the usermod's loop and relies on a pass of
the loop being under half a millisecond. It keeps seed 04's way of reading the outputs
back: all of them, around one send in five, and once more for every report. With twenty
outputs of 180 LEDs a pass that holds a send is 16 ms and one that opens a file 28 ms, so
the wire time read in the loop came out anywhere from 5.7 to 36 ms. Reading 3,600 LEDs back
takes 5.3 ms, and the report is a line of 2,300 characters that the port takes in pieces of
a few hundred. Each of the three cost refreshes: the probe build sent 47 or 48 of a still
picture a second where the loop has time for 50.

**Answer.** The probe build measures so that its own work stays small whatever the number
of outputs.

- The wire time is taken by a timer that looks every tenth of a millisecond at the busy
  flag of the chip's LCD unit, the one the library's own test of a finished write reads.
  It runs only while a transfer is on the wire.
- The outputs are read back in turn: after each send as many as have 200 LEDs together,
  and one at least, and the same ones again before the next copy. `overwritten` counts as
  before. The `crc` of an output in the report is that of its last reading, at most twenty
  sends old with twenty outputs of 180 LEDs; an output that was not read yet is read for
  the report.
- A report asked for between the copy and the show of a refresh is written after the
  show, so that it never describes colours that were not sent.
- The report is handed to the port as one long line, which the port writes in the pieces
  it takes without waiting, one in each pass, reading no command meanwhile.
- The pulse counter is set up with no pin of its own, because the chip's driver would
  make a pin it is given an input. The probe turns on the input of the pad and routes it
  to the counter, which leaves the output as it is: A3 holds, on RMT pins and on pins of
  the parallel driver.

The probe build includes three more headers of the chip's own software for this, which the
test of the usermod's files lists.

**Resolution.** `firmware/usermod/odrig_probe.cpp`; `firmware/usermod/odrig_serial.cpp`,
`writeLong`; `tests/firmware/test_usermod_files.py`; `docs/firmware.md`, "The probe build".

## Seed 05: A picture that does not change, in a test of the rate

**Question.** The one-frame animation of the board tests lasts one second, and the core
opens its file again each time the frame has ended. On the board an open takes 18 ms
before the first byte is decoded, 28 ms with a picture of 60 x 60. With a send of 16 ms
that is two refreshes of the second in which it happens: 48 are sent.

**Answer.** The test of the rate with a still picture uses one frame that lasts a minute,
so that the file is opened once in the time of the test; `one_frame` of the board tests
takes the length of its frame. That an open costs refreshes is not new, seed 04 measured
18.5 ms and one refresh; what it costs with 3,600 LEDs and the request in a task of its own
is measured in task 2.

**Resolution.** `tests/board/support.py`, `one_frame`; `tests/board/test_twenty.py`.

## Seed 05: The request in a task of its own, and the rate it reaches

**Question.** The design plans, for a loop that cannot hold 49 refreshes a second with the
dense 60 x 60 clip, a task on the chip's other processor core that asks the core for
refreshes, and estimates 17 ms for a refresh with it. It leaves three things to be found:
whether such a task can read the files, whether core 0 has the time, and whether the
watchdog stays quiet. It also has every call to the core take the lock, and the usermod
asks the core for its legs in every pass of the loop.

**Answer.** The task is in: `odrig`, on processor core 0, stack 8,192 bytes, priority 1.
It asks the core, again after a millisecond while no refresh is due, and waits while the
loop has not taken the last one. The loop copies a ready refresh into the outputs at once,
wakes the task, and shows the copy when the outputs can take data. Three things follow
from the lock being held for a whole request, 9 to 17 ms:

- The legs are read from the core once, in `setup()`, into a list of the usermod's own.
  The mapping does not change after the start, and a leg's LED data stays where it is, so
  the loop's check of the outputs in every pass and the copy need no lock. Only a request
  writes LED data, and the task makes none between a ready refresh and its copy.
- The port hands the core the bytes of a pass a line at a time, each line under one hold
  of the lock, as the design asks.
- The probe build times the request in the task and keeps its sums under a guard of their
  own.

Found on the board with the probe build: the task reads the files of `/odrig` while WLED's
loop runs, commands are answered, and no watchdog restarted the chip in the minutes it
ran. Core 0 does not have the time. The rate rose from 21 to 23 refreshes a second to 27
to 34 for the compressed clip and from 31 or 32 to 44 or 45 for the uncompressed one, and
not to 49: side by side a send takes 20 ms in place of 16.3 ms and the core's work for a
frame 16 to 17 ms and 12.7 ms in place of 12.3 ms and 8.6 ms. Reading the file in larger
pieces changes nothing; the time is the decoding, the placing and WLED's show. The design
forbids changing the core's decoder and WLED's limiter here, so step 3 of "The time of one
refresh" applies: the figures are in `docs/firmware.md` and in the open questions of
`docs/decisions.md`, Requirement 13 criterion 5 holds, and the seed stays `in_progress`.
The two tests of the rate in `tests/board/test_fps.py` state the requirement and fail on
the board until it is met.

The task could not be finished as its text asks. The firmware build's `status` with the
task, the 25-second measurements and the whole board suite were not run, and the board is
not left with the firmware of this task: see the next entry. Task 2 stays open.

**Resolution.** `firmware/usermod/odrig_usermod.cpp`, `requestRefreshes`, `readLegs` and
`loop`; `firmware/usermod/odrig_serial.cpp`, `handOn`; `tests/firmware/test_usermod_files.py`,
`TheTask`; `tests/board/test_fps.py`; `docs/firmware.md`, "What the firmware does" and
"Verified on the board"; `docs/decisions.md`, "Open questions".

## Seed 05: A trial build at another optimisation level, and a board that no longer answers

**Question.** With the task in place the board was 15 to 40 percent short of 49 refreshes
a second. The platform compiles every file at `-Os`. Would `-O2` buy the time?

**Answer.** It was tried for the whole firmware, with a change to the tool's build file
that was never committed, and it must not be tried that way again. WLED built at `-O2`
stops with a null pointer a moment after it starts and restarts several times a second.
For the first minute the restarts could be read on the port. Then the board stopped
answering on its USB port: no line arrives, no byte is taken, and esptool's reset into the
bootloader gets no reply, with its own sequence, with more attempts and without a reset.
The Mac still lists the USB device, it answers the requests every USB device answers, and
making the Mac list it afresh changed nothing. A look at the chip's debug unit showed the
first processor core being restarted about every 1.3 seconds and the second one never
released, so the chip is alive and restarting before the application is up. Further probing
through the debug unit was refused by the permission system of the session and was
stopped there.

What WLED itself does in such a loop was read in its source: after five quick restarts it
puts `/cfg.json` back from its copy, after ten it renames `/cfg.json` to `/rst.cfg.json`,
so WLED's settings, the Wi-Fi ones among them, are probably at their defaults until that
file is put back, and after fifteen it would switch to the second application partition
if that held a program, which the factory backup says it does not. No tool of this
repository wrote any of that; WLED did, on the board.

No program on this Mac can cut the board's power. It needs a person: unplug the USB cable,
plug it in, and run `python3 firmware/fw.py flash` at once. `docs/firmware.md`, "Verified
on the board", has the steps. Until then no task that needs the board can be done: the
rest of task 2, tasks 8 and 11, and the state the seed asks the board to be left in. The
tasks that need no board go on.

A build of the core alone at `-O2`, as its own library, is the form this trial should have
had; it is left to try once the board answers again.

**Resolution.** `docs/firmware.md`, "Verified on the board"; `docs/decisions.md`, "Open
questions"; `docs/specs/05-p0-canvas-60-by-60/tasks.md`, the notes under tasks 2, 8 and 11.

## Seed 05: A file with both `width` and `height`, or with neither, in the converter's tests

**Question.** The tasks say that a test that concerns a row-leg file passes unchanged. Two
lines of `tests/converter/test_mapping.py` expected the detail of a file made from a
row-leg file: with a `height` added, `unknown-member`, and with its `width` taken out,
`missing-member`. The design's order of the checks judges the kind of a file before the
members of its top level.

**Answer.** The order of the design holds, because a second reader must give the same
details. Such a file is of no kind, so it is not a row-leg file. Its reason is
`mapping-malformed` as before, and its detail is now `the file has both "width" and
"height"` or `the file has neither "width" nor "height"`. The two lines moved to the tests
of the kinds with these details. Every other test of a row-leg file is as it was, apart
from `Leg.rows`, which is `Leg.strips`, and from the one place that builds a `Mapping` by
hand, which now gives the kind first.

**Resolution.** `odrig/mapping.py`; `tests/converter/test_mapping.py`, `Kinds` and `Order`;
`tests/converter/test_import_timeline.py`.

## Seed 05: What the reader said of a column-leg file before it knew the kind

**Question.** Task 3 says its new tests, run against the reader as it was, fail with a
valid column-leg file refused for its member `height`.

**Answer.** They failed, and the file was refused, but the detail named the member that was
absent: `mapping-malformed: missing-member: the file has no member "width"`. The check of
the members reports a missing member before an unknown one. `height` was named, as
`unknown-member: the file has the unknown member "height"`, only for a file with both
`width` and `height`. The commit message of the task gives both texts as they were
observed.

**Resolution.** The commit of task 3.

## Seed 05: An LED number that a leg does not have, asked of `position`

**Question.** The design gives `odrig.mapping.position(canvas, leg, n)` and does not say
what it does with a number below 1 or above the leg's LED count.

**Answer.** It raises `ValueError`. It is a call from Python and reads no file, so no
reason name of `docs/reasons.md` applies. The page's `position` gives null there.

**Resolution.** `odrig/mapping.py`; `tests/converter/test_mapping.py`, `Positions`.

## Seed 05: The comments on rows in the two headers of the core

**Question.** Task 4 and the design's "The core" say to reword the comments of
`core/src/core_state.h` and `core/include/odrig_core.h` that say "rows" where both kinds of
leg are meant.

**Answer.** Neither file has such a comment. `core_state.h` says of a leg that its LEDs are
entries of the LED tables, and `odrig_core.h` that a leg is as the mapping file lists it,
with its LED data in chain order; both sentences hold for a column leg as they stand. The
two files are unchanged. What said "rows" was in `core/src/mapping.cpp`, which is rewritten
for strips, and in the row of `led_count` in `docs/core.md`.

**Resolution.** `core/src/mapping.cpp`; `docs/core.md`, "What the core offers";
`tests/core/test_docs.py`.

## Seed 05: The tests of the core that run on every mapping, before the page reads column legs

**Question.** The tasks say that a test that concerns a row-leg file passes unchanged, and
that the made-up column-leg mappings are given by a function of their own until the page
reads both kinds. Two tests of the core run on every mapping of `mapping_texts()` and read
`width` and `rows` from the file: the leg list in `tests/core/test_mapping.py` and the pixel
of every LED in `tests/core/test_playback.py`. And `led_pixels` of `tests/core/support.py`
took the width of the canvas alone, which does not give the place of an LED of a column leg.

**Answer.** The two tests run on the mappings of both functions, `mapping_texts()` and
`column_mapping_texts()`, and state the rule for both kinds. What they check for a row-leg
file is what they checked. The task of the page can so join the column-leg mappings to
`mapping_texts()` without a change to these tests. `led_pixels` takes the mapping in place
of its width, and its one caller outside the core's tests, `rule` in
`tests/emulator/test_layout.py`, passes the mapping; no other line of `tests/emulator/`
changes with the core's reader.

**Resolution.** `tests/core/support.py`, `column_mapping_texts` and `led_pixels`;
`tests/core/test_mapping.py`, `LegList`; `tests/core/test_playback.py`,
`EveryLedShowsItsPixel`; `tests/emulator/test_layout.py`, `rule`.

## Seed 05: A test of the emulator's suite that refuses an uncommitted change of the core

**Question.** The tasks say that the four suites pass before a task is committed.
`tests/emulator/test_scope.py` has a test of seed 03,
`test_no_commit_of_this_seed_changes_a_source_or_the_header_of_the_core`, that fails while
a file under `core/src` or `core/include` differs from what is committed. Task 4 changes
`core/src/mapping.cpp`, so the emulator's suite cannot pass before the commit of that task.

**Answer.** The test stays as it is; it belongs to seed 03. Before the commit of task 4 the
emulator's suite ran with that one failure, `' M core/src/mapping.cpp\n' != ''`, and its
other 258 tests passed. The test itself was run on a copy of the repository in which the
change was committed, and passed there. The whole suite is run once more after the commit.
The same holds for any later commit that changes a source of the core.

**Resolution.** The commit of task 4. `tests/emulator/test_scope.py` is unchanged.

## Seed 05: The cell of the LEDs view of upright legs, and the bands of its LED numbers

**Question.** The design says that the cell of the LEDs view of a column-leg file is the
largest from 4 to 28 pixels at which the canvas, the leg band, the header and the marks fit
the drawing area, and that the LED numbers at the ends of the columns are drawn where the
cells are 9 pixels or more. It does not say whether the two bands of numbers count when the
cell is chosen. If they do not, a drawing whose cells come out at 9 pixels is higher than
its area by the two bands, and the stage scrolls.

**Answer.** The bands count wherever they are drawn. The cell is the largest at which the
drawing with its two number bands fits the area. Where that is below 9 pixels the bands are
left out, and the cell is the largest that fits without them, and 8 pixels at most, so that
no drawing has cells of 9 pixels without its numbers. For the target file this gives cells
of 8 pixels without numbers in an area of 1280 x 546, as the design expects, the same in an
area of 1280 x 620, and cells of 9 pixels with the numbers from an area 648 pixels high on.

**Resolution.** `emulator/web/layout.js`, `fitUpright`; `tests/emulator/test_layout.py`,
`UprightLeds`.

## Seed 05: What the layout script gives for a column-leg file

**Question.** The design says what `emulator/web/layout.js` describes for the strips of a
leg and what the LEDs view of a column-leg file holds. It names neither the functions nor
the parts of the fit, and it leaves three points of the drawing open: the eight colours
that are added, the shape of the bracket, and a tenth row or column that lies next to the
last one.

**Answer.** `strips(m, i)` takes the place of `rows(m, i)`. A strip has `start`, `first`
and `last`, and its place across the strips as `y` for a row and as `x` for a column, so a
row-leg file gets what it got. `runs(m, i)` gives `top` and `bottom` for rows, as before,
and `left` and `right` for columns, from the left. `marks(count)` gives the rows or columns
that are marked, and `legSpans(m, f)` the pixels each run of columns of each leg takes
across the drawing. The fit of a column-leg file has `feed`, `header`, `legBand`,
`legWords` (where the words `leg` and `pin` stand), `yLabel`, `canvas`, and `numberTop` and
`numberBottom`, which are null where the numbers are left out. It has no `bracket`,
`numberLeft` or `numberRight`; those belong to a row-leg file.

The eight colours added are `#e599f7`, `#c98f5a`, `#a5d8ff`, `#7fa650`, `#96f2d7`,
`#868e96`, `#1098ad` and `#ffa8a8`: each differs from the leg before it and after it in the
list. The bracket of a run has its long side towards the leg's number and its two ends
towards the canvas, as the bracket of rows has; the design's drawing shows it open towards
the number. A tenth row or column nearer than three to the last one is not marked, as the
header of a row-leg file does it, so that no mark stands on another: a canvas 12 wide is
marked at 1 and 12.

**Resolution.** `emulator/web/layout.js`; `emulator/web/view.js`, `uprightLabels`;
`tests/emulator/test_layout.py`, `Positions`, `ColoursAndCurve` and `UprightLeds`.

## Seed 05: The tab Mapping on a column-leg file, before its mapping view is written

**Question.** Task 5 gives the page the LEDs view for column legs and task 6 the mapping
view. After the commit of task 5 the tab `Mapping` can be chosen while a column-leg file is
shown, and the suite fits every mapping of `mapping_texts()` with a board.

**Answer.** With a board, `fit` gives a column-leg file the arrangement of its LEDs view.
`wires` gives such a file no line and `chain` no point, and `view.js` draws no board, no
line and no chain for it: the tab shows the drawing of the LEDs view. One test says that
every mapping of both kinds is fitted with and without a board; it states nothing that the
mapping view of task 6 changes.

**Resolution.** `emulator/web/layout.js`, `fit`, `wires` and `chain`;
`tests/emulator/test_layout.py`, `EveryMapping`.

## Seed 05: The tests of the page for row-leg files, where a name changed

**Question.** The tasks say that a test that concerns a row-leg file passes unchanged. The
design gives `read` of the page the member `strips` in place of `rows`, writes the
functions that describe a leg for strips, and has twenty colours in place of twelve. Tests
of `tests/emulator/test_layout.py` read those names, some of them on every mapping of
`mapping_texts()`, which now has column-leg files.

**Answer.** The tests read `strips` where they read `rows`, from `read` and from
`strips(m, i)`, and three of them carry the new name of the function. Those that ran on
every mapping and read `y`, or walked along a row, now run on the six row-leg mappings and
check what they checked; beside each stands a test for the column-leg mappings. The test
that the colour of a leg is entry `i mod 12` is replaced by three: twenty colours used in
turn, the first twelve as they were, and twenty different ones for the target file. The two
tests of the core that joined `mapping_texts()` and `column_mapping_texts()` take
`mapping_texts()`, which holds both.

That the page draws a row-leg file as before was established twice. Everything the layout
script gives for the eight row-leg mappings of the suite, in fourteen drawing areas, with
and without a board, was written out before and after the change and compared: the
positions, the LED at every place, the strips, paths and runs, every part of the three
arrangements, every line and every chain are the same. And a new test, `BenchFile`, holds
the cell, the canvas and the board of the bench file in the nine areas the tests name, as
the layout script gave them before this task.

**Resolution.** `tests/emulator/test_layout.py`; `tests/emulator/js/dump_layout.js`;
`tests/core/test_mapping.py`, `LegList`; `tests/core/test_playback.py`,
`EveryLedShowsItsPixel`.

## Seed 05: What the test of the area of 1280 x 546 said of a fit made for rows

**Question.** Task 5 says that the test of the area of 1280 x 546 fails against a fit that
takes the canvas of the target file for 60 rows of a row-leg file.

**Answer.** It failed, but not for the size. The arrangement of a row-leg file puts its
labels beside the canvas, and an area of 1280 x 546 is wide: the target file got cells of 8
pixels and a canvas inside the area. What the test found missing were the parts of the LEDs
view of a column-leg file: `Lists differ: ['feed', 'legBand', 'legWords', 'numberBottom',
'numberTop'] != [] : the fit lacks parts of the LEDs view of a column-leg file`. The test
of the area of 500 x 546 failed for the size: `5 not greater than or equal to 7`. The other
failure the task asks for was as expected: with `layout.js` as it was, the position test
for the target file stopped in `read`, with `TypeError: undefined is not an object
(evaluating 'leg.rows.length')`. The commit message of the task gives the three texts.

**Resolution.** The commit of task 5.

## Seed 05: The mapping view of upright legs: its parts, its sizes and the size of the board

**Question.** The design draws the two arrangements of the mapping view of a column-leg
file and gives the sizes of the tracks. It does not name the parts of the fit, says "about
770 pixels high" for an area of 1280 x 546, and does not say how the room beside the canvas
is shared between the cells and the board, nor what `tracks` gives for a column-leg file.

**Answer.** With a board, `fit` gives a column-leg file `view` "mapping", `arrangement`
"wide" or "narrow", `feed`, the parts of its LEDs view with both number bands, and `level`,
`upright`, `nearLabel` (the names of the legs at the left of the board), `board`, `farZone`
and `reaches`. A reach says of a leg its `kind` ("near" for the left row of pads, "far" for
the right row, "off" for a pin the board lacks), its `level` track counted from the canvas,
its `upright` track counted from the board, and for the right row its `way`, "short" or
"long". `tracks` gives the legs of a column-leg file their places from the left; the level
track is that place in the narrow arrangement and the place from the other end in the wide
one. A row-leg file keeps "beside" and "below" and everything else it had.

The number bands are 30 pixels high, 40 where the cells are 13 pixels or more, so that the
numbers stand 11 pixels from the canvas, clear of the turns of the chains, which are 6
pixels outside it. For the target file this gives: in 1280 x 546 and in 1100 x 600 the wide
arrangement, cells of 9, a drawing of 1075 x 810; in 1920 x 1000 the wide one, cells of 12,
a drawing of 1255 x 990, whole in the area; in 756 x 546 the narrow one, cells of 9, a
drawing of 696 x 1263; in 600 x 546 the narrow one, cells of 7, a drawing of 576 x 1143.
The level channel is 150 deep and the upright channel 136 wide in all five. The wide
arrangement is used from a width of 960 on.

Beside the canvas the board keeps pads 16 pixels apart, or as many as the height allows,
before the cells grow beyond 9 pixels, and it gives way down to 10 only so that cells of 9
fit; what room is left then goes to the board, up to 20. Without this a file of 48 columns
took the whole width for its cells and left a board whose names stood on each other. The
canvas with its bands lies against the level channel and the board stands in the middle of
the height beside it. In the narrow arrangement the board has pads 10 to 16 apart, as the
board below the canvas of a row-leg file has.

**Resolution.** `emulator/web/layout.js`, `placeWired`, `fitWired` and `tracks`;
`tests/emulator/test_layout.py`, `UprightMapping`.

## Seed 05: The short way round the board, where the board does not stand beside the canvas

**Question.** The design says that a leg of the right row of pads takes the short way when
its level track is in the half of the level channel farthest from the canvas, and that the
rules keep two lines from crossing twice. In the narrow arrangement the far zone lies under
the canvas. A leg whose first LED is to the left of the loops would, on the short way, come
up to its level track and turn back along it, and two such lines cross twice: once where
the loop of one passes the level track of the other, and once more where the last piece of
the other passes the level track of the first. The design does not say which way the middle
track of an odd number of legs takes, nor where several pads that the board lacks stand.

**Answer.** In the narrow arrangement a leg takes the short way only when its level track
is in the far half and its first LED is to the right of every loop; otherwise it takes the
long way. In the wide arrangement the rule is the design's alone. For the target file
nothing changes: legs 1 and 2 take the short way in the wide arrangement and legs 19 and 20
in the narrow one. The middle track takes the short way, so one leg on a pad of the right
row is not led round the whole board. Of several pads beyond the board, the one whose level
track is farthest from the canvas stands nearest the level channel, so that their lines do
not cross each other.

Counted by the test from the lines themselves, the lines of the target file cross 88 times
in each of the five areas, in both arrangements, no pair twice and none on another: 83
pairs of the left row whose upper pad has the lower leg number, four pairs of a short-way
and a long-way line in the far zone, and legs 19 and 20. With every leg of the right row
on the short way the test failed with `116 != 88 : (1280, 546), wide: the lines of the
target file cross 116 times`; the narrow arrangement then has 118 crossings, and the lines
of legs 1 and 2 cross twice.

**Resolution.** `emulator/web/layout.js`, `placeWired`; `tests/emulator/test_layout.py`,
`UprightLines`.

## Seed 05: The made-up column-leg files, and the arrangement each gets

**Question.** Task 6 asks for the wide arrangement in areas of 1280 x 546, 1920 x 1000 and
1100 x 600 and the narrow one in 756 x 546 and 600 x 546, "for the target file and the
made-up column files". The made-up files of the suite have six columns at most. By the
design's rule the board stands beside the canvas wherever cells of 9 pixels fit the width
with it, and for those files that is every one of the five areas. None of them has a pin
the board lacks beside pads of both rows, and none is fed from the top with more than one
leg.

**Answer.** The rule is kept. The small files get the wide arrangement in all five areas,
and the tests say so. Five files are added in the test, each 48 columns wide or more, which
get the wide arrangement in the first three areas and the narrow one in the last two, as
the target file does: the target with leg 7 started at the top; the target with every leg
started at the top; a file of twelve legs with two pins the board lacks, pads in both rows,
columns that are not neighbours and two legs started at the top; the same with every start
turned over, which is fed from the top and has two legs started at the bottom; and sixteen
legs that are all on pads of the right row. They stay in the test: the made-up files of
`tests/core/support.py` are the ones every suite plays on, and those are not changed.

**Resolution.** `tests/emulator/test_layout.py`, `upright_mappings` and `UprightCase`.

## Seed 05: A first LED at the far edge, and chains of columns that are apart

**Question.** The design says that the number 1 of the first LED is a tag on the last piece
of the line, and that a first LED at the far edge is reached through the gap at the left of
the leg's first column, where the line turns into the LED from outside the canvas. That
turn is half a cell wide and 6 pixels outside the canvas: there is no room for a tag on it.
The design says that a chain turns outside the edge of the canvas into the next column, and
nothing about two turns at the same edge that span the same columns.

**Answer.** As in the drawing of rows: the tag of such a leg stands in the number band at
the far edge, over the column of the first LED, just beyond the turn, where the number 1
would stand; the line ends under it. Every other tag is on the last piece of its line. The
turns of all chains are 6 pixels outside the canvas. Where the columns of a leg are not
neighbours, a turn passes other columns, and two turns at one edge can lie on each other,
as the turns of rows that are apart do in the drawing of a row-leg file. The target file
has no such leg. Whether that needs more is for the check by eye.

**Resolution.** `emulator/web/layout.js`, `wiresWired` and `chain`; `emulator/web/view.js`,
`uprightLabels`; `tests/emulator/test_layout.py`, `UprightView`.

## Seed 05: The view script run without a browser, and row-leg files compared before and after

**Question.** Task 6 changes `emulator/web/view.js` and names tests of the layout script
only. What the view script draws was so far checked by eye and by reading its text. Task 6
also says that row-leg files are drawn exactly as before.

**Answer.** A second script for the JavaScript shell, `tests/emulator/js/dump_view.js`,
loads the page's scripts after a stand-in for the document that keeps every element they
make, and prints the elements of the mapping view. The tests read from it, for every
column-leg mapping in a wide and a narrow area: one pad, line, tag, chain and frame for
every leg in the leg's colour; the tag on the last piece of the line; the numbers upright
in the two bands, none over another and clear of the turns; `GPIO <pin>` beside a pad the
board lacks; and that pointing at a leg marks every part of it and fades the others.

That row-leg files are drawn as before was established by comparing, before and after the
change, for the eight row-leg mappings of the suite: everything the layout script gives in
fourteen areas with and without a board, and every element the view script makes for the
mapping view in nine areas, 20,295 elements with all their attributes. Both are the same,
byte for byte. The LEDs view of all eleven mappings of both kinds, 5,665 elements in nine
areas, is the same too. In the browser, headless Chrome 154, the target file was looked at
in windows of 1280 x 800 and 756 x 900, with the pointer on an LED, a label, a pad and a
line, and files with legs started at the top and with pins the board lacks beside it.

**Resolution.** `tests/emulator/js/dump_view.js`; `tests/emulator/test_layout.py`,
`UprightView`. The tab `Mapping` on a column-leg file now shows this view, which replaces
what the entry "The tab Mapping on a column-leg file, before its mapping view is written"
describes.

## Seed 05: What the tool that writes docs/mapping.md says of a page it refuses, and what it draws for other files

**Question.** The design names three failures of `python -m odrig.mapdoc` with status 1, a
marker that names a file that is not there, a marker without an end and a name it does not
know, and gives a word only for a page that differs, `page-differs`. It does not say what
a marker is inside a line of text, what an end without a marker is, where the fence of a
drawing stands, what the line under the board says, or how wide a drawing is for a file
other than the two of the page.

**Answer.** The tool writes the error line of the converter, `error: <word>: <detail>`.

- A mapping file that is not there is the reader's `mapping-missing`, and one that breaks a
  rule its `mapping-malformed`; a page that is not there is `not-found`. Those are the
  reasons of `docs/reasons.md` for those files.
- A marker without an end, before the next marker or before the end of the page, an end
  without a marker, and a marker that does not name a board, a drawing or a table of a
  file are `page-malformed`, with the page and the number of the line. Like `page-differs`
  it is a word of the module and not a reason of `docs/reasons.md`. An end without a marker
  is refused because a marker with a slip in its first words would otherwise leave its part
  unwritten and unchecked without a word.
- A marker and an end are whole lines: a line that starts with the marker's first words is
  a marker, a line that is the end comment and nothing else is an end, and the same words
  inside a line are text of the page. A file's name is made of letters, digits, `.`, `_`
  and `-` and starts with a letter or a digit, so a marker names no file outside the
  mapping folder.
- Every failure is found before anything is compared or written: `page-differs` is said
  only of a page whose markers are sound and whose files are read. Without `--check`, a
  page that already holds what would be written is not written again.
- The fence of a drawing is inside the generated part, and nothing but the marker and the
  end stands around it. Under the board, after an empty line, a leg whose pin the board
  lacks is named as `Not on the board: leg 2 on pin 60.`, with every such leg in the one
  line.
- For another file the numbers of a drawing are as wide as the largest LED number of the
  file, its labels are 6 wide or two more than the longest, the arrow is always 44, and
  the heading ends four places before the end of the lines, as in the drawing the page had.
  The board moves to the right when a leg number has three digits.

**Resolution.** `odrig/mapdoc.py`; `tests/converter/test_mapping_page.py`, `Refused`,
`OutsideTheGeneratedParts` and `MadeUpFiles`. `docs/converter.md` names the program in one
sentence and points to `docs/mapping.md`, which gives the command.

## Seed 05: The ten-leg section and "What is confirmed" of docs/mapping.md, with the tool

**Question.** Task 7 gives the page its section for twenty upright legs. The ten-leg file
is removed in task 9 and "What is confirmed" is task 10's. The page had a section for the
ten-leg file, and "What is confirmed" spoke of legs 3 to 10 and of ten outputs read from
WLED's source. The design's row for the page says that LEDs on pins 2 to 18, 21 and 47
have not been seen, and its list of risks says eighteen of the twenty pins.

**Answer.** The ten-leg section goes with task 7: the page has one target, and its test
reads the bench section and the twenty-leg section. `mapping/legs-10.json` stays tracked
until task 9, and nothing on the page names it. "What is confirmed" is reworded as little
as keeps the page true: legs 1 and 2 of today's build are confirmed on the hardware, as
before; the firmware makes twenty working outputs on pins 1 to 18, 21 and 47 and every pin
carries the signal of a whole refresh, measured with one strip wired, on pin 1; with that
firmware LEDs on pins 2 to 18, 21 and 47 have not been seen. Both figures of the design are
right: two legs were seen lit before this firmware, and one pin with it. Task 10 goes over
the section again.

`tests/emulator/test_board.py` reads the board from the generated part `board legs-20`
and no longer from behind a sentence of the page, which is reworded. In the test of the
tool, "the first row of `legs-2.json`" is the first row of its first leg, which changes
places with the second.

**Resolution.** `docs/mapping.md`; `tests/emulator/test_board.py`;
`tests/emulator/test_layout.py`, `sections_of_the_mapping_document`;
`tests/converter/test_mapping_page.py`, `ChangedMappingFile`.

## Seed 05: The board tests for the target file, written and not run

**Question.** Task 8 moves the board tests to the target file, runs the whole board suite
and writes the measurements. The board stopped answering on USB during task 2 and no
program on this Mac can bring it back. Task 9 then removes the ten-leg file, which the
board tests still named.

**Answer.** The tests are written now, so that nothing names the ten-leg file when it
goes, and task 8 stays open until they have run. `tests/board/test_probe.py` takes the two
tests of the spike in the form the task gives them: the target file, with the limiter's
lowest level, the pulses, the wire time and 49 sends a second of a picture that does not
change, and twenty column legs of three columns of 6 with exact bytes; they stand where
the two ten-leg tests stood. The spike's third test, which only measured the dense clips,
is not carried over: `tests/board/test_measure.py` has those rows. The demo show for the
board is made in the test's support from the two generators and the same items as
`shows/demo-20/show.json`, dimmed, because that file is added one task later. Storage is
filled with six dense 60 x 60 clips of 10 seconds and one of 5: 9,009,652 bytes, which the
tool's own check says fit.

What could be run without the board was run by hand: every helper up to the point where a
test talks to the board. The firmware's `status` on the board is expected to stay below 49
with the dense clip, so the two tests of `tests/board/test_fps.py` for it will fail there
until Requirement 13 is met; see "Seed 05: The request in a task of its own, and the rate
it reaches".

**Resolution.** `tests/board/support.py`, `tests/board/test_probe.py`,
`tests/board/test_fps.py`, `tests/board/test_measure.py`;
`docs/specs/05-p0-canvas-60-by-60/tasks.md`, the note under task 8.

## Seed 05: The tests of row legs that used the ten-leg file, once the file is gone

**Question.** Task 9 removes the ten-leg file and says that every test that used it uses
the target file. The tasks also say that a test that concerns a row-leg file passes
unchanged, and the design that the page's tests keep "everything of today for the row-leg
files". Many tests of the row views read the ten-leg file by its name: the cells and the
parts of the LEDs view, the board beside and below the canvas, the tracks, the six
crossings of the lines, the drawing of a row-leg file. They cannot run on a file of
columns. The core's and the page's tests that run on every mapping also played on it. The
task's list of files leaves out three that named the file: `tests/converter/test_mapping.py`,
`tests/core/test_mapping.py` and `tests/emulator/test_layout.py`.

**Answer.** The made-up mappings of `tests/core/support.py` gain `ten-row-legs`: ten legs
of three rows of 60 from the top row down, leg N on pin N, which is what the file held.
The tests of row legs read it under that name and are otherwise unchanged, and every suite
that plays on all mappings plays on the same eleven as before. The converter's test of the
ten-leg file is kept on a file made up in the test. Everything else moved to the target
file and 60 x 60: playback, memory, startup, the cycle, the decoder's list of canvases, the
generators, `import`, `pack`, the firmware's storage check, the demo show, the real-time
rate and the documented commands.

Three tests changed more than their size. The noise clip of `tests/core/test_decoder.py`
takes its pictures in turns of three, not four: on 60 x 60 a stored picture is 10,805
bytes, so four of them put a repeat 43,220 bytes back, outside the window of 32,768, and
the file would not compress; three put it 32,415 back, near the far end of the window. The
clips of `test_the_memory_does_not_depend_on_the_length_of_a_clip` are 180 KB and 10.8 MB.
The command tool's session runs against the example show, as before, and against the demo
show. A white picture in `tests/converter/test_import_fit.py` is resampled to 60 x 60.

The suites that play the demo show without the converter's command line take its files
from `demo_show()` of `tests/core/support.py`, which encodes what the two generators give
for the canvas of the target file; `tests/emulator/test_demo.py` runs the generators and
`pack` as the document gives them and compares the folder with those files.
`tests/board/support.py` still makes its own dimmed demo show and is not changed: the board
tests cannot be run.

**Resolution.** `tests/core/support.py`, `MADE_UP_MAPPINGS` and `demo_show`;
`tests/emulator/support.py`, `demo_show`; the tests named above.

## Seed 05: The check list by eye, between the task that removes the ten-leg file and the task that rewrites the list

**Question.** Task 9 changes "Two shows to run" of `docs/emulator.md` and the commands of
its check list, because no tracked file may name the ten-leg file or its demo show. The
steps of the list are rewritten in task 10, which also goes through them in a browser.
With the commands changed, steps 6, 9 and 10 still say what is seen with ten row legs on a
60 x 30 canvas, and "What has been checked" reports a pass through the list made with the
ten-leg shows. The sections on the two views speak of the ten-leg mapping too.

**Answer.** Only the commands and the sentence that introduces them change in the check
list: the demo show is `build/demo-20/show`, and the dense clip is made with the target
file. The steps keep their text until task 10 rewrites them for twenty upright legs and
goes through them; rewording them now would leave "What has been checked" reporting a pass
that nobody made. Until task 10 is done, the list is not a description of what the page
shows for the target. "Two shows to run" is rewritten for the target and gains the frames
and the sizes of the demo show's two packed files, which its test compares with what the
commands give.

**Resolution.** `docs/emulator.md`, "Two shows to run" and "The check list by eye";
`tests/emulator/test_docs.py`; `docs/specs/05-p0-canvas-60-by-60/tasks.md`, task 10.

## Seed 05: A record of what was measured on ten row legs, told apart from a statement about the target

**Question.** Task 10 asks for a test that no document, outside the change log of the
decisions, the drifts, the seeds and the specs, says that the target is 60 x 30 or has ten
legs. The documents hold figures that were measured before the target changed and that
nothing has replaced: the sizes of the prototype's dense clip at 60 x 30 in `docs/format.md`
and `docs/decisions.md`, and in `docs/firmware.md` everything seed 04 measured on the
board with ten row legs, 1,800 LEDs. A test that forbids the words would forbid the
records.

**Answer.** A record says itself that it is one. The test looks in every tracked `.md`
file outside those four places for a canvas of 60 x 30, ten legs, ten outputs, 1,800 LEDs
or 1,800 mA, legs 2 or 3 to 10, pins 1, 2 or 3 to 10, and 30 rows. Such a mention is allowed
only in a
section that holds the words "before the target became twenty upright legs" at or before
the paragraph of the mention; a section is the text from one heading to the next, and a
paragraph ends at an empty line. So the sentence that opens a record covers what follows
it in its section, and a mention above it, or in another section, fails the test. "Ten row
legs" is the name the records use for the layout they were measured on, as the made-up
mapping of the suites is called; the test does not take it for a mention, because the
target has column legs. The sections that carry the words are "Measured sizes" of
`docs/format.md`, "Measurements behind the choice", the bullet on FastLED's compiler and
"Open questions" of `docs/decisions.md`, and "Measurements on the board" and "Verified on
the board" of `docs/firmware.md`. A second test says what the documents that name the
target must name: 60 x 60, twenty legs, both kinds of leg and both mapping files.

**Resolution.** `tests/converter/test_docs.py`, `TheTarget`; the sections named above.

## Seed 05: The measurements of the board, kept as a record until the board tests have run

**Question.** Requirement 13 criterion 4 and Requirement 16 criterion 5 ask that
`docs/firmware.md` state the measurements made on the board with the target file. The
board tests that take them are written and have not run, because the board does not answer
on USB. "Measurements on the board" still held the figures of seed 04, written as if they
were the firmware's of today.

**Answer.** The figures stay and the section says what they are: taken with the firmware
of seed 04 on the bench file and on ten row legs of three rows of 60, 1,800 LEDs, and that
the measurements with the target file are not taken yet, with the test that will take
them. What was measured with twenty outputs and the dense 60 x 60 clip before the board
stopped answering is under "Verified on the board", where tasks 1 and 2 wrote it. The
limiter is written for 3,600 LEDs: 3,600 mA at rest against the 730 mA that WLED's maximum
of 850 mA leaves, so every LED is held at the lowest level; WLED's source, read in the
work folder, has that level as a brightness of 1 of 255, for every mapping of 730 LEDs or
more. The open question of the decisions on decode speed gives the figures of both sizes,
and the one on legs 3 to 10 became the one on twenty wired legs. The two criteria are not
met until task 8 is done.

**Resolution.** `docs/firmware.md`, "What the firmware does" and "Measurements on the
board"; `docs/decisions.md`, "Open questions"; `docs/mapping.md`, "What is confirmed";
`docs/specs/05-p0-canvas-60-by-60/tasks.md`, the note under task 8.

## Seed 05: The owner's check of a strip on the parallel driver, and what the limiter leaves of it

**Question.** The design gives the fifth owner's check a mapping of twenty legs of one row
of 60 that lists the leg on pin 1 last, so that the one wired strip is on the sixteenth
lane of the parallel driver, and says the strip must show the first row of that leg. It
names no animation, no row and no file, and such a mapping has 1,200 LEDs: WLED's limiter
counts 1,200 mA at rest against 730 mA and holds every LED at its lowest level.

**Answer.** The check prints the mapping file in full, to be saved as
`build/lane/mapping.json`: the legs 2 to 20 on the pins of the target, one row each from
the top of a 60 x 20 canvas down, and last the leg on pin 1 with the row y = 8. The show is
Hello world for that canvas at brightness 32, and y = 8 is the bottom row of its letters,
the row with the most LEDs lit: 29 of 60. What must be seen is given LED by LED, as a line
of `X` and `.`, and the check says that the LEDs glow faintly, because of the limiter.
Fewer LEDs would keep the limiter out, but Hello world needs 53 columns, and a strip of 60
that shows one row of it is the plainest thing to compare. A test reads the mapping from
the document, has the converter's reader accept it, finds pin 1 on the sixteenth lane, and
compares the printed line with the row the generator lights. The commands of the check
were run on this Mac up to `install-show`, and the emulator's record of the show has that
row on the leg of pin 1.

**Resolution.** `docs/firmware.md`, "The owner's checks", step 5;
`tests/firmware/test_docs.py`.

## Seed 05: The check list by eye for the target, and how it was gone through

**Question.** Task 10 rewrites the check list for the demo show of twenty legs and the
dense 60 x 60 clip, adds a step for each criterion of Requirement 18, and has it gone
through in windows of 1280 x 800 and 756 x 900. Two of the new steps are themselves about
the size of the window. Three numbers, 9.5, 9.8 and 10.1, are criteria of seed 03 and of
seed 05 alike. The step for Requirement 8 criterion 9 needs two shows. And a browser that
a program drives on this Mac has no window.

**Answer.** The list has 22 steps: twelve for the eleven criteria of seed 03, with the
target in them, and ten marked `(seed 05, N.M)`. Its test reads the two sets apart by the
mark, each against the requirements file that names it. The list is written for a window
of 1280 x 800; the step for the narrow arrangement makes the window 756 x 900 and back.
It was gone through twice in headless Chrome 154.0.8037.98, driven through its debugging
port by a program of Node.js in `build/t10/`: once as written, and once with a window of
756 x 900 from the first step on. All 86 screenshots in `build/t10/shots/` were looked
at; nothing on the page had to be changed, and no file of `emulator/web/` is touched.

Requirement 8 criterion 9 was read from the page's own figure: 49 to 51 in every one of
ten seconds with the demo show and with the dense 60 x 60 clip, in both views and both
windows, with Chrome's animation frames at 60 a second, and the same in a run of Chrome
with `--disable-gpu`. The remedy of the design's "Drawing 3,600 LEDs", squares in place
of circles, is not applied. A headless browser draws to no screen, so that the figure
holds on a real screen stays with the pass a person makes; it is listed under "What has
been checked" with Safari, the clarity of 88 crossings and the twenty colours.

The sizes the document gives for the target file, the two channels and the count of
crossings are compared with the layout script by the document's test. The sketch of the
mapping view of row legs showed a canvas of 30 rows; it now shows the bench file, whose
two lines cross once, as the suite has it.

**Resolution.** `docs/emulator.md`, "The LEDs view", "The mapping view", "The check list by
eye" and "What has been checked"; `tests/emulator/test_docs.py`.

## Seed 05: The board is back, and what WLED had done to its settings file

**Question.** The entry "A trial build at another optimisation level, and a board that no
longer answers" left the board unreachable and WLED's settings probably renamed.

**Answer.** The owner unplugged the board's USB cable and plugged it in again. The board
answered at once, and the session that coordinates this run flashed the firmware as
committed and installed the dim example show; nothing but a cut of the board's power had
been missing. Storage then held `/rst.cfg.json` and no `/cfg.json`: WLED had renamed its
settings file, as its source says it does after ten quick restarts. The file has 392
bytes, WLED's two LED outputs of the bench build and its start preset, and no Wi-Fi
setting, so no Wi-Fi setting was changed by the trial. It was given its name back in the
board's storage by a one-off script that used the firmware tool's own steps for storage:
the kept image confirmed by the chip, the rename in the image, the check that `/odrig` and
every other file are untouched, the one changed block written, the whole partition
compared. Afterwards the files outside `/odrig` were byte for byte those of the storage
image kept before the trial. The script is not tracked: the tool has no command for it and
this seed adds none.

The images in `build/firmware/out/` are rebuilt from the tracked sources before the board
tests run. The probe image of that folder had been built before the core read column
legs, and the board suite builds an image only when it is missing; with that old image a
show on the target file is `mapping-malformed`.

**Resolution.** `docs/firmware.md`, "Verified on the board".

## Seed 05: The rate the owner accepts on the board: from 20 to 50

**Question.** Requirement 13 asks for 49 refreshes a second on the board with a dense
60 x 60 clip, compressed and uncompressed, and holds the seed `in_progress` when the board
stays below. With the request in a task of its own the firmware reports 36 to 42 for the
compressed clip and 45 to 47 for the uncompressed one.

**Answer.** The owner ruled on it while this run was under way, and the rulings reached
this run through the session that coordinates it. The first accepted 30 frames per second
for dense video content; the second, which replaces it, is the one that stands: any
refresh rate from 20 to 50 a second is fine on the board, for any content, and the owner
only minds a rate above 50 or below 20. The measured rate is not a defect to fix, and no
other build of the whole firmware is to be tried for it.

So criteria 1 and 2 of Requirement 13 read, from here on: with the target file, `status`
reports 20 or more and 50 or fewer in every one of ten seconds, for the dense 60 x 60 clip
in both forms and for the demo show. A second can count one refresh more than was due in
it, as the tests of seed 04 already saw, so the tests allow 51 at the top. Criterion 5 no
longer holds the seed open. The board tests of the bench show, of seed 04, and the test of
a picture that does not change on twenty outputs, of Requirement 12, go on asserting 49 or
more: the board reaches it, and they guard what was measured. The documents give the
measured figures as they are, say which form of a dense file plays faster on the board,
the uncompressed one, and `docs/decisions.md` has the ruling as a decision in place of the
open question about the rate. The spec files are not edited; this entry is where the
requirement is changed.

**Resolution.** `tests/board/test_fps.py`; `docs/decisions.md`, "Firmware", "Canvas and
coordinates" and the change log; `docs/firmware.md`, "Verified on the board" and "The
owner's checks".

## Seed 05: The board tests for the target file, run

**Question.** The entry "The board tests for the target file, written and not run" left
task 8 open. The board is back.

**Answer.** The whole board suite ran with the firmware of task 2 and the target file: 30
tests, all passing, in 32 minutes. The measurements of `tests/board/test_measure.py` are in
`docs/firmware.md`, "Measurements on the board"; the figures of seed 04 for ten row legs
stay under them as a record, marked as such. The table has two columns more than the
task's list: the working outputs of each show and the free internal memory, both of
Requirement 13 criterion 4. The test of the exact bytes was shown to fail as the task
asks: with the `first_led` of leg 7 changed to `"top"` in the copy of the mapping the
emulator records, output 7 held `6240d9e2` where the recording gives `1368b71c`, and the
other nineteen outputs agreed.

The dense rows of the table are from the probe build, whose own work costs the compressed
clip some refreshes: 28 to 37 a second there, 36 to 42 in the firmware. Both are inside
what the owner accepts; see "The rate the owner accepts on the board: from 20 to 50".

**Resolution.** `docs/firmware.md`, "Measurements on the board" and "Verified on the
board"; `docs/mapping.md`, "What is confirmed"; `docs/specs/05-p0-canvas-60-by-60/tasks.md`,
the note under task 8.

## Seed 05: What is verified

**Question.** The last task reads every acceptance criterion of Requirements 1 to 18 once
more, names for each one a program can check the test that checks it, and adds a test where
one is missing. Which test checks which criterion, which tests were missing, and what has
no program checked?

**Answer.** The four suites that need no board pass on macOS 26.5 on Apple Silicon with
Apple clang 21, Python 3.14.6 and zlib 1.2.12: the converter's suite with 618 tests, the
core's with 246, the emulator's with 346 and the firmware tool's with 230. They were not
run with Python 3.10 to 3.13; tests parse the sources of the converter, the emulator and
the command tool in the grammar of 3.10. The board suite, `tests/board/`, has 30 tests. It
passed with the target file when task 8 ran it, and the last task runs it once more as its
own step.

A criterion is written as 8.2. A test is named by the folder of its suite under `tests/`,
its file and its class; where a file was named for a requirement, a class alone is of that
file.

- **Requirement 1, the format.** 1.1 to 1.6: `converter/test_mapping.py`, `Accepted`,
  `AcceptedColumns`, `Rejected`, `RejectedColumns`, which has a test for each of the eight
  rules, `Kinds` and `Order`. 1.7: `Files`, and every refusal those classes look at is
  `mapping-malformed`; `converter/test_docs.py`, `ReasonsDocument`. 1.8: the tests of
  row-leg files, which did not change, and `TrackedFiles`.
- **Requirement 2, where each LED is.** 2.1 to 2.3: `converter/test_mapping.py`,
  `Positions`, on five row-leg and six column-leg files. 2.4: `core/test_playback.py`,
  `EveryLedShowsItsPixel`, which finds the pixel of every LED in the LED data.
- **Requirement 3, the target file.** 3.1, 3.2: `converter/test_mapping.py`, `TargetFile`;
  `core/test_mapping.py`, `LegList`. 3.3: `converter/test_docs.py`, `TheTenLegFile`. 3.4:
  `TrackedFiles`.
- **Requirement 4, the converter.** 4.1, 4.2: `converter/test_mapping.py`,
  `AcceptedColumns` and `Files`. 4.3: `converter/test_generators.py`, `TrackedSources`,
  `ColumnLegMapping` and `Dense`; `converter/test_import_timeline.py`, `Video` and
  `ColumnLegMapping`; `converter/test_show_pack.py`, `Pack`. 4.4: `Pack`. 4.5:
  `converter/test_cli.py`, `Subcommands`, and the tests of every subcommand, which did not
  change; `converter/test_mapping_page.py`, `CommandLine`.
- **Requirement 5, the core.** 5.1: `core/test_json.py`, `MappingTexts`;
  `core/test_mapping.py`, `RefusedMappings` and `ChangedBetweenTheReadings`. 5.2:
  `LegList`. 5.3: `core/test_playback.py`, `EveryLedShowsItsPixel` and `ColumnLegs`. 5.4:
  `OneLoopAndIntoTheNext`. 5.5: `core/test_build.py`, `HostInterface`;
  `emulator/test_binding.py`, `Declarations`. 5.6: `core/test_memory.py`, `FixedMemory`
  and `Guard`; `core/test_docs.py`, `CoreDocument`, for the table of blocks. 5.7:
  `core/test_build.py`, `Sources` and `Library`; `core/test_memory.py`, `Guard`.
- **Requirement 6, the emulator and the command tool.** 6.1 to 6.3:
  `emulator/test_demo.py`, `DemoShow`; `emulator/test_record.py`, `Recording`, on the
  made-up column-leg files; `emulator/test_start.py`, that no option names a size. 6.4:
  `emulator/test_realtime.py`, `SpeedOfThisMac`, over five full seconds for each show.
  6.5: `emulator/test_tool.py`, `Session`.
- **Requirement 7, the page places the LEDs.** 7.1: `emulator/test_layout.py`, `Positions`
  and `WithoutABrowser`; `emulator/test_view.py`, `Painted`; `emulator/test_page_files.py`,
  `Files`. 7.2: `Positions`, the place of every LED and the LED at every place, on eleven
  mappings. 7.3: `WithoutABrowser`. 7.4: `emulator/test_record.py`, `Recording`, for what
  is recorded, and `Positions`, for where the page puts the LEDs.
- **Requirement 8, the LEDs view.** In `emulator/test_layout.py`, `UprightLeds` holds what
  the layout script gives, and in `emulator/test_view.py`, `UprightLedsView` and `Painted`
  hold what the view script draws from it. 8.1: `UprightLeds`, `Painted`. 8.2:
  `UprightLeds`, `UprightLedsView`. 8.3: `ColoursAndCurve`. 8.4, 8.5: `UprightLeds`,
  `UprightLedsView`. 8.6, 8.7: `UprightLeds`. 8.8: `Painted`, for the ring of a dark LED
  and the display curve; `ColoursAndCurve`; `emulator/test_page_files.py`, `Files`, for
  the curve and for the drawing made again when the size changes. 8.9: no test; see below.
- **Requirement 9, the mapping view.** In `emulator/test_layout.py`, `UprightMapping` and
  `UprightLines` hold what the layout script gives and `UprightView` what the view script
  draws, on the target file, the four made-up column-leg files and five more. 9.1:
  `emulator/test_board.py`, `BoardOfThePage`; `emulator/test_view.py`,
  `BoardInTheMappingView`. 9.2 to 9.6: `UprightLines`, `UprightView`. 9.7: `UprightView`,
  for the leg that is pointed at and the LED at a pixel; `emulator/test_page_files.py`,
  `Files`, for the words of the readout. 9.8, 9.9: `UprightMapping`. 9.10:
  `UprightMapping`, `UprightLines`, `UprightView`. 9.11: `UprightView`, `Painted`.
- **Requirement 10, row legs.** 10.1: `emulator/test_layout.py`, `Fit`, `Board`, `Lines`
  and the test of a row-leg file in `UprightView`; `emulator/test_view.py`,
  `BenchLedsView`. 10.2: `BenchFile`. 10.3: `ColoursAndCurve`.
- **Requirement 11, the tool that writes the page.** 11.1 to 11.8:
  `converter/test_mapping_page.py`, `TrackedFiles`, `MadeUpFiles`, `ChangedMappingFile`,
  `EveryRun`, `OutsideTheGeneratedParts`, `Refused` and `StandardLibraryOnly`. 11.9:
  `emulator/test_board.py`, `BoardOfThePage`.
- **Requirement 12, twenty outputs.** 12.1, 12.3 to 12.7: `board/test_probe.py`, `Outputs`,
  the test of the target file and the test of twenty column legs of 18 LEDs; without the
  board, `firmware/test_usermod_files.py`, `Host`, reads how a leg becomes an output. 12.2:
  `firmware/test_patches.py`; `firmware/test_wled.py`, `Patches`; `firmware/test_cli.py`,
  `Building`. 12.8 is the order of the commits. 12.9 and 12.10 did not arise: twenty
  outputs work, and no pin was replaced. 12.11: the board tests of seed 04, which run as
  before, `board/test_install.py`, `board/test_commands.py`, `board/test_autostart.py` and
  the other tests of `board/test_probe.py`; `firmware/test_usermod_files.py`.
- **Requirement 13, the rate on the board.** 13.1, as the entry "The rate the owner accepts
  on the board: from 20 to 50" reads it, and 13.2: `board/test_fps.py`, `Fps`. 13.3:
  `firmware/test_usermod_files.py`, `TheTask` and `Host`; on the board, `overwritten`
  stays 0 in `board/test_probe.py`. 13.4: `board/test_measure.py` takes the figures and
  `firmware/test_docs.py`, `Firmware`, reads the table. 13.5 does not hold; the measured
  rates are in both documents, which `Firmware` reads.
- **Requirement 14, the demo show.** 14.1, 14.2, 14.4: `emulator/test_demo.py`, `DemoShow`;
  `converter/test_generators.py`, `TrackedSources`, for the bytes of the bench sources.
  14.3: `converter/test_docs.py`, `TheTenLegFile`. 14.5: `emulator/test_docs.py`,
  `DocumentedShows`, which runs the commands as they are written.
- **Requirement 15, the tests.** 15.1: `TheTenLegFile`, and the tests named above for the
  target file. 15.2: `COLUMN_LEG_FILES` of `converter/test_mapping.py`,
  `MADE_UP_COLUMN_MAPPINGS` of `core/support.py`, which the core, the emulator and the
  page are run on, and `upright_mappings` of `emulator/test_layout.py`. 15.3: the tests
  on those files, with strips of 1, 4, 5 and 7 LEDs and legs of one to four strips; for
  the usermod, the board test of twenty column legs of 18 LEDs and the one of three legs;
  no test reads the sources for a size. 15.4: the four suites, run by discovery. 15.5:
  `firmware/test_cli.py`, `Commands`.
- **Requirement 16, the documents.** 16.1: `converter/test_docs.py`, `BothKindsOfLeg`;
  `converter/test_mapping_page.py`. 16.2: `TheTarget`, `BothKindsOfLeg`. 16.3:
  `MeasuredSizes`. 16.4: `emulator/test_docs.py`, `EmulatorDocument` and `DocumentedShows`.
  16.5: `firmware/test_docs.py`, `Firmware`. 16.6: `core/test_docs.py`, `CoreDocument`;
  `converter/test_docs.py`, `BothKindsOfLeg`, `ReasonsDocument` and `TheTarget`. 16.7:
  `TheTarget`.
- **Requirement 17, the board.** 17.1: `install` of `board/support.py` refuses a show
  above 40, which `board/test_install.py` tests. 17.2: `LeaveTheBoard` of
  `board/__init__.py`; `board/test_autostart.py`. 17.3: `firmware/test_flasher.py`,
  `Regions` and `NeverTheWholeFlashAndNoFuse`; `firmware/test_paths.py`, `BackupGuard`;
  `board/test_flash_restore.py`.
- **Requirement 18, what needs eyes.** 18.1, 18.2: `emulator/test_docs.py`,
  `EmulatorDocument`. 18.3: `firmware/test_docs.py`, `Firmware`. 18.4 is the last task
  itself.

Tests that were missing, and are added:

- The bytes of `mapping/legs-2.json`, written out, and that the row-leg file the mapping
  document shows is that file (1.8, 3.4). Its content was tested, its bytes were not.
- A mapping file has two reasons in the reasons document and in the converter, and no
  reason is named after a part or a kind of a mapping file (1.7).
- What the view script paints. A script for the JavaScript shell,
  `tests/emulator/js/dump_painted.js`, keeps every dot the page paints on its canvas. For
  every mapping of the suites, in the LEDs view and in the mapping view: each LED of a
  refresh is painted in the cell of its canvas position in the colour its own bytes give
  through the display curve, with every LED in a colour of its own, so that an exchange of
  two LEDs or of two bytes fails; a dark LED is a ring, lighter than the stage, and an LED
  with any light is a filled dot (7.1, 8.1, 8.8, 9.11). Until now the tests held where the
  layout script puts an LED and read the lines of `view.js` that paint it.
- What the view script draws in the LEDs view, which no test built: for a column-leg file
  the band and the bracket of every run of columns with the leg's number and pin in its
  colour, the marks of the rows and the columns, and the LED numbers at the ends of every
  column where the cells are 9 pixels or more and none where they are smaller (8.2, 8.4,
  8.5); for the bench file the brackets, the y of every row and the LED numbers at its
  ends (10.1).
- The board as the view script draws it: the antenna above the first pads, the two sockets
  at the lower edge, and the labels of the two rows in the order of `board.js` (9.1).
- With the `first_led` of leg 7 of the target file changed to `"top"`, the page puts every
  LED of that leg at the other end of its column and moves no other LED (7.4). The test of
  the recording held this for the core.
- The emulator records each of the four made-up column-leg mappings with the legs of that
  file, as the reference plays it (6.1, 15.2, 15.3). The core and the page ran on those
  files; of valid mappings the emulator itself ran on the two tracked files and on copies
  of them with one `first_led` changed.
- Read in `app.js`: the drawing is made again for the size of the stage when it changes
  (8.8), and the readout names the leg, the pin, the LED number and the coordinates (9.7).
- The mapping document has both kinds of file with their members, eight numbered rules,
  each with a test of the reader, the rule for both kinds of leg, both builds and what is
  confirmed; the decisions have what was measured for twenty outputs and the target in
  their change log; the converter's document has both kinds (16.1, 16.2, 16.6).
- The firmware document's table of measurements has every value that 13.4 names for the
  demo show and for the dense clip in both forms, with twenty of twenty outputs and rates
  from 20 to 50; the document says how many outputs the firmware drives and how, and names
  every patch file and every file of WLED a patch changes; it and the decisions give the
  rates of the dense clip beside what the owner accepts (13.4, 13.5, 16.5).

The tests of what the view script paints and draws, and the test of leg 7, were each seen
to fail against a copy of `view.js` or of `layout.js` with one fault put in: two bytes of
an LED exchanged, the canvas upside down, a dark LED filled, a dark LED not drawn, the
display curve left out, a ring in the colour of the stage, the two end numbers of a column
exchanged, the marks of the tenth rows left out, a bracket in another colour, the pin
replaced by the leg's number, the two end numbers of a row exchanged, the labels of the
pads counted from the sockets, the antenna at the lower end of the board, the sockets at
its top, and `"top"` read as `"bottom"`. The tests that read `app.js` and the documents
were not tried in that way.

No program checked:

- **The page in Safari, and at a real screen.** No step of the check list of
  `docs/emulator.md` has been gone through in Safari; the suite only has Safari's
  JavaScript engine accept the scripts. The list was gone through in Chrome without a
  window by the program of task 10, which is not tracked, and its screenshots were looked
  at once. So 8.9, 49 refreshes drawn in every second, rests on the page's own count in a
  browser that draws to no screen, and on no test. Whether the bands and the rings are
  faint enough and yet seen, whether 88 crossings can be followed and twenty colours told
  apart, the page in a light appearance, and a file with legs from the top or with pins
  the board lacks in a browser: these are the owner's, with the list in Safari.
- **Light on the target.** The owner's checks 5 and 6 of `docs/firmware.md`: a strip on a
  lane of the parallel driver, and twenty wired legs. A program counted 24 pulses for
  every LED on each pin and timed the wire, and read back what each output holds; it saw
  neither the widths of the pulses nor an LED. LEDs on pins 2 to 18, 21 and 47 have never
  been lit, nobody looked at the one wired strip, and the current of twenty legs was not
  measured. That leg 1 stands at the left with its first LED at the bottom is the reading
  of the first entry of this seed, and has not been compared with the installation.
- **49 refreshes a second with the dense clip on the board.** Criterion 13.1 as it is
  written is not met: the firmware reports 36 to 42 for the compressed clip and 45 to 47
  for the uncompressed one. The owner accepts 20 to 50, and the tests assert that.
- **Commands over the board's network.** `tests/air/` was not run with this firmware; the
  firmware tool's suite reads the handler in the usermod. The owner's checks 1 to 4, of
  seed 04, are open as before.
- **What only the probe build can see.** The pulses, the wire time and what the outputs
  hold are taken with the probe build; the firmware has no probe, and of it the tests know
  the replies to its commands and its rate.
- **The core for the chip.** Its suite compiles and runs it on the Mac, and the memory of
  5.6 is the Mac's figure. For the chip it is compiled by the firmware build, which the
  board suite uses; no test of the four suites compiles it there.
- **What did not change.** "No reason name is added" (1.7), "every function and every type
  as it is" and "no change to host a column-leg file" (5.5, 6.5) are held by tests of what
  is there now. That nothing changed was read once from the history: since the commit of
  the spec, of `core/include`, `core/src`, `emulator/*.py`, `odrigctl/` and
  `odrig/errors.py` only `core/src/mapping.cpp` differs, and `firmware/usermod/` has not
  changed since before the core read column legs.
- **Sizes written out in a source (15.3).** No test looks for them. Searched once in the
  tracked sources of the converter, the core, the emulator, the page, the command tool,
  the firmware tool and the usermod: none names a mapping file or a show of the repository,
  and of the numbers 60, 180, 540, 3,600 and 10,800 only the 180 ms of a frame of DVD
  bounce is there.
- **The real-time tests** of the emulator measure five full seconds, not the ten of the
  clip, on a Mac that does other work meanwhile. None of them failed in the runs of this
  task.

**Resolution.** `tests/converter/test_mapping.py`, `TrackedFiles`;
`tests/converter/test_docs.py`, `ReasonsDocument` and `BothKindsOfLeg`;
`tests/emulator/js/dump_painted.js`; `tests/emulator/test_view.py`;
`tests/emulator/test_layout.py`, `Positions`; `tests/emulator/test_record.py`, `Recording`;
`tests/emulator/test_page_files.py`, `Files`; `tests/firmware/test_docs.py`, `Firmware`.
`docs/emulator.md`, "What has been checked", and `docs/firmware.md`, "The owner's checks",
list what is left for the owner.
## Seed 06: Where the JavaScript converter lives and how it is started

**Question.** The seed asks for plain JavaScript modules in two parts and names no folder,
no file and no command.

**Answer.** The folder `converter/` at the repository root: the library in
`converter/lib/`, the command line part in `converter/odrig.js` and `converter/cli/`, the
tests in `converter/tests/`. The tool is started as
`node converter/odrig.js <subcommand> ...`. `converter/package.json` marks every file
under it as an ECMAScript module, which is also the form a web view loads, so nothing is
built. The tests live inside `converter/` and not under `tests/`, because the one test
command that Node.js 20 and later versions share starts in the folder it searches; see
"Seed 06: One test command for Node.js 20 and for later versions".

**Resolution.** `docs/specs/06-p1-javascript-converter/requirements.md`, Requirements 1
and 2; `design.md`, "Repository layout" and "How it is run".

## Seed 06: What "the same messages" covers

**Question.** The seed asks for "the same results and messages as the Python tool". Part
of what the Python tool writes is not its own wording: the position and message of
Python's JSON module in a `bad-json` detail, zlib's message in `bad-deflate`, the
operating system's message for a file that cannot be read or written, the message of
Pillow or PyAV in `unreadable-media`, and the usage text of `argparse`. The JSON module's
messages changed with Python 3.13.

**Answer.** The reason is the same for every input. The detail is the same, character for
character, wherever the Python tool words it itself, and what a successful run prints is
the same byte for byte. Where the detail holds the text of a library, the JavaScript tool
gives the same reason and its own words. For the common failures of the file system it
writes the system's words as Python gives them on macOS and Linux, from a small table.
The usage text is its own and names the tool as `node converter/odrig.js`. The tests
compare whole error lines except for the reasons listed.

**Resolution.** Seed 06 `requirements.md`, Requirement 3; `design.md`, "strictjson",
"Files" and "Testing strategy".

## Seed 06: Command lines the two tools read differently

**Question.** The Python tool's command line is `argparse`, which accepts more than the
documents show: an option shortened to an unambiguous beginning, and numbers of seconds in
every spelling Python's `decimal` reads, with underscores or digits of other scripts.

**Answer.** The JavaScript tool has a small parser of its own and accepts the documented
forms: `--name value`, `--name=value`, options in any place, a value such as `-1` after an
option, an option given twice with its last value, and seconds as a sign, digits, an
optional fraction and an optional exponent. A shortened option and an exotic spelling of a
number are usage errors in the JavaScript tool and work in the Python tool. Node's own
argument parser was not used, because it takes `--start -1` for a missing value, where the
Python tool reads the start and refuses it with `bad-range`.

**Resolution.** Seed 06 `requirements.md`, Requirement 2 criteria 3, 6, 8 and 9;
`design.md`, "Arguments".

## Seed 06: A reader of JSON of our own, and texts nested very deeply

**Question.** The files are read strictly: a member named twice, `1.0` where an integer is
expected and a byte-order mark are refused, and an integer of thirty digits must keep its
digits for a detail. JavaScript's `JSON.parse` reports none of the first three and loses
digits. The Python tool also refuses a text that is nested too deeply for Python, at a
depth that depends on the version of Python.

**Answer.** The library has its own reader of JSON, over the bytes of the text, which
keeps no state on the engine's stack. It refuses a text nested deeper than 512 levels as
`bad-json`. No file of this project nests deeper than four. A text between 513 levels and
Python's own limit is `bad-json` in the JavaScript tool and gets whatever reason its
content has in the Python tool; no such file is of use to anyone.

**Resolution.** Seed 06 `requirements.md`, Requirement 4; `design.md`, "strictjson".

## Seed 06: The DEFLATE compressor, and what "within 5 percent" is measured against

**Question.** The seed asks that compressed files decode to identical frames and are
"within 5 percent of the Python tool's" in size. It does not say what compresses, or
against which figure the 5 percent is taken. Node's `zlib` module does not exist in a web
view. The compression streams of Node.js and of browsers take no level and give the bytes
of the platform's own zlib, which differ between Node.js and Chrome.

**Answer.** The library has a compressor of its own, written in plain JavaScript by the
method of zlib at level 9, which is what the Python tool uses. A file encoded in the app
is then the file encoded on the command line, on every computer, and the test in Chrome
can ask for the same bytes. The measure is the size of the whole file the Python tool
writes for the same source, with the zlib of the Python that runs the test; the JavaScript
file may be at most 5 percent larger, and a smaller one is never a failure. A sketch of
the method was run for the spec on six bodies: the largest difference from zlib 1.2.12 was
0.1 percent, and one of the six streams had zlib's bytes. Identical bytes are not asked
for.

**Resolution.** Seed 06 `requirements.md`, Requirement 8; `design.md`, "The DEFLATE
compressor".

## Seed 06: The DEFLATE decoder

**Question.** The reference tells three failures of a compressed body apart, as zlib
reports them: `bad-deflate`, `truncated`, and `trailing-bytes` with the number of bytes
after the stream. A decompression stream of a browser gives one error for all three and
does not say where the stream ended.

**Answer.** The library decodes DEFLATE itself, by the method of the core's decoder, which
judges every part of a stream at the point where zlib does. The suite compares its verdict
with zlib's for whole, damaged and cut streams, as the core's suite does. The detail of
`bad-deflate` is the library's own; zlib's sentence is not copied.

**Resolution.** Seed 06 `requirements.md`, Requirement 6; `design.md`, "inflate".

## Seed 06: Numbers larger than JavaScript's

**Question.** Python's integers have no size and its fractions are exact. The Python tool
uses both: for a width of forty digits in a detail, for the sum of durations, for the
times of video frames, and for the area mean, which it computes in 64-bit integers. A
JavaScript number is exact only up to 2 to the power 53.

**Answer.** A whole number from a file is a `Number` while it is exact and a `BigInt`
otherwise, and sums and products of such values are computed so that no digit is lost.
Times and the rectangle of a fit are fractions of two `BigInt`s. The area mean runs in
`Number`s when its largest value, 511 times the area in the tool's units, is below 2 to
the power 53, which holds for every real video, and in `BigInt`s between there and the
Python tool's own limit of 2 to the power 63. Its division is written as
`(a - a % b) / b`, which is exact. Floor division rounds toward minus infinity, as in
Python. Seconds on the command line are read from their digits. The suite compares canvas
pictures and ticks with the Python tool's for data from seeds.

**Resolution.** Seed 06 `requirements.md`, Requirements 12 and 13; `design.md`, "Whole
numbers and fractions" and "fit".

## Seed 06: The package that decodes video, its licence and what its install leaves

**Question.** The seed asks for "a package that brings its own decoder; no system-wide
ffmpeg" and names none. Which package, under which licence, and does its install stay in
the project folder?

**Answer.** `ffmpeg-static` 5.3.0, licence GPL-3.0-or-later. Its install script fetches
one ffmpeg 6.1.1 program for the platform from the package's GitHub releases into
`converter/node_modules/`. The tool starts that program and reads its output; nothing of
it is loaded into Node.js, is part of the library or is tracked. Three things the owner
should know: the licence is the GPL; the script checks no checksum, so the repository
tracks the checksum of the program for each platform it was verified on and the suite
compares; and the script keeps a copy of the download in the user's cache folder,
`~/Library/Caches/ffmpeg-static-nodejs` on macOS, outside the project folder, as npm keeps
its own cache in `~/.npm`. Looked at and not chosen: `node-av`, whose API is closest to
PyAV, needs Node.js 22.18 or later, and the seed asks for 20; `@ffmpeg-installer/ffmpeg`
needs no download script but carries old builds nobody maintains, and is the fallback;
`@ffmpeg/ffmpeg` no longer runs in Node.js; `libav.js` publishes no build with the H.264
and HEVC decoders. Nothing was installed for this spec: the facts were read on npm's
registry and in the package's files, and the first task that needs the package verifies
them.

**Resolution.** Seed 06 `requirements.md`, Requirements 14 and 17; `design.md`, "Video",
facts V1 to V5 and assumptions A1 to A5; `tasks.md`, task 8.

## Seed 06: How frames and their times come out of the decoder program

**Question.** The Python tool gets each frame from PyAV with its presentation time as a
whole number in the stream's time base. A program gives pictures on a pipe; where do the
times come from, and what else must match?

**Answer.** One run of ffmpeg writes the frames as raw red, green, blue and alpha to
standard output, and its filter `showinfo` writes one log line for each frame with the
presentation time, and one line with the time base. The reader pairs them in order and
gives the library the time as an exact fraction. The form of those lines was read in the
source of the version the package carries. The run is told not to turn the picture by a
recorded rotation, which the Python tool does not apply, to keep every frame, and to use
the scaler setting PyAV uses. The format of a file is not forced: like PyAV, ffmpeg tells
it from the content. If the log does not serve, the times are taken from a second output
in ffmpeg's `framecrc` form.

**Resolution.** Seed 06 `design.md`, "Video", "The call" and assumption A2.

## Seed 06: GIF files: the reader, and whose rules build the pictures

**Question.** The Python tool reads a GIF with Pillow, which builds the picture of each
frame from the frames before it by rules of its own. Read for this spec in Pillow 12.3.0:
after a frame with disposal 2 that has no transparent index it paints the background
colour, where browsers make the area transparent; it keeps the disposal of the frame
before for a frame that names none; and it paints the background colour where the first
frame does not cover the screen. The seed asks that the test GIF gives identical JSON, and
seed 09 has the app's web view decode GIFs itself.

**Answer.** On the command line a GIF is read with the package `omggif` 1.0.10, licence
MIT, one file without a dependency, which gives each frame's rectangle, palette,
transparent index, delay and disposal. The pictures are built in the command line part by
the rules of the GIF format as browsers apply them, written out in the design, so that
the command line and the app give the same pictures. For the GIFs of the suite, and for
ordinary GIFs, these are Pillow's pictures. In the three corners named above the two
tools differ; the documentation says so. The delays are the file's own, which the package
gives unchanged. The decoder program can read GIFs too and is the fallback, with the GIF
reader forced so that another kind of picture under the name is still refused.

**Resolution.** Seed 06 `requirements.md`, Requirement 14 criteria 5, 6 and 10;
`design.md`, "GIF" and assumption A6.

## Seed 06: How a web view gives the library its frames

**Question.** The library reads no file, and seed 09 has the phone's web view decode video
and GIF. The seed says what the library holds and not how frames reach it.

**Answer.** One function, `importFrames`, takes a source: its kind, video or GIF, and an
iteration of frames, synchronous or asynchronous. A frame is its size, its pixels as red,
green, blue and alpha, rows from the top, and for a video its presentation time, as a
whole number of milliseconds or an exact fraction, for a GIF its delay. The rules that
turn times and delays into frames on screen are in the library, so a web view gets the
timeline of the command line. The command line uses the same function. Reading pixels
out of the web view's frames is seed 09's.

**Resolution.** Seed 06 `requirements.md`, Requirement 15; `design.md`, "How the library
is given frames".

## Seed 06: What of the Python tool is not ported

**Question.** The seed lists `import`, `encode`, `decode`, `check` and `pack`. The Python
package also has the generators of the tracked animations and of the dense clip, the
builder of the test vectors, and after seed 05 the tool that writes `docs/mapping.md`.
The firmware tool and the suites of the core and the emulator call the Python readers.

**Answer.** None of these is ported, and none of their users changes. The generators
compute with floating point and stay the one source of the tracked animations. The Python
package keeps every file. `canvas-too-small`, a reason only the generators give, is still
in the JavaScript list of reasons, so that the two lists are equal.

**Resolution.** Seed 06 `requirements.md`, Requirement 18 criterion 8; `design.md`, "What
this design relies on" and "Documents".

## Seed 06: One test command for Node.js 20 and for later versions

**Question.** The suite must run with one documented command, on Node's built-in test
runner, selected by directory or discovery. Tried for this spec: `node --test <folder>`
runs the folder's tests on Node.js 20.18 and fails on Node.js 26.5, which wants a pattern;
a pattern works on 26.5 and not on 20.18.

**Answer.** Without an argument both versions find the test files of the folder they are
started in. The command is `npm test --prefix converter`: npm starts the script
`node --test` in `converter/`, and the runner finds every file there whose name ends in
`.test.js`. That is why the tests are in `converter/tests/`.

**Resolution.** Seed 06 `requirements.md`, Requirement 18 criteria 1 and 2; `design.md`,
"Testing strategy".

## Seed 06: Chrome for the test

**Question.** The definition of done has a test that loads the library in headless
Chrome. No browser may be installed, and a package that drives a browser would be one more
dependency.

**Answer.** The test starts the Chrome that is installed, without a window and with a
profile folder of its own in a temporary folder, on a page served from the loopback
address; module scripts do not load from a file address. The page posts its results back
to the test's own server, so nothing drives the browser from outside. Chrome is looked for
at the path an environment variable names and then in the usual places. Where none is
found the test is reported as skipped; on the Mac of this project it must run.

**Resolution.** Seed 06 `requirements.md`, Requirement 16; `design.md`, "The page of the
Chrome test".

## Seed 06: The same installed file set, when compressed

**Question.** The seed says `pack` "produces the same installed file set as the Python
tool, byte-identical when uncompressed". Compressed files cannot have the Python tool's
bytes.

**Answer.** The same names in the folder; `mapping.json` and `show.json` with the same
bytes in both cases; with `--uncompressed` every file with the same bytes; without it,
every `.odrg` file decodes to the frame records of the Python tool's file and is at most
5 percent larger.

**Resolution.** Seed 06 `requirements.md`, Requirement 11 criteria 5 and 6.

## Seed 06: A tool started without its packages

**Question.** The Python tool needs its libraries only for `import`. What does the
JavaScript tool do when `npm ci` was not run?

**Answer.** `encode`, `decode`, `check` and `pack` run with Node.js alone; the two
packages are loaded only when a file of their kind is imported. Without the package,
`import` ends with status 1 and `error: decoder-missing: ...`, which names the command
that installs it. `decoder-missing` is a failure of the setup and not a rejection of an
input: it is listed in `docs/converter.md` and not in `docs/reasons.md`, as the emulator's
failures to start are listed in its own page.

**Resolution.** Seed 06 `requirements.md`, Requirement 14 criteria 8 and 9; `design.md`,
"Video".

## Seed 06: Which page presents which tool

**Question.** The seed says the tool documentation presents the JavaScript tool as the
converter and the Python tool as the reference used by tests. `docs/converter.md` is today
the Python tool's page, and tests of three suites read commands in it and in the pages of
the emulator and the firmware.

**Answer.** `docs/converter.md` becomes the JavaScript tool's page. A new page,
`docs/reference-converter.md`, takes what belongs to the Python tool: its setup, its
command line, the generators, the test vectors and its use from Python. The pages of the
emulator and the firmware pack their shows with the JavaScript tool; the generators stay
Python commands. The tests that read those pages are changed in the same task.

**Resolution.** Seed 06 `requirements.md`, Requirement 19; `design.md`, "Documents";
`tasks.md`, task 10.

## Seed 06: Show files while seed 07 changes them

**Question.** This seed ports the reader of show files. Seed 07 changes `docs/show.md`: a
show may then have no item. The two seeds can be implemented in either order.

**Answer.** The JavaScript reader is ported from `odrig/show.py` as it is on the day.
Whichever seed is implemented second brings both readers to the same rule; the comparison
tests of this seed fail if they differ.

**Resolution.** Seed 06 `design.md`, "show". Seed 07 `tasks.md`, task 3.

## Seed 06: Recording the seed's progress

**Question.** As for the other seeds: the seed convention has no state that means "spec
written".

**Answer.** The spec commit leaves `state.json` as it is. The first task sets
`in_progress` and the last task sets `completed`. Every item of the definition of done is
checked by a program, so no owner's check holds the seed open; it stays `in_progress` only
if Chrome cannot be started by a program.

**Resolution.** Seed 06 `tasks.md`, tasks 1, 9 and 10.

## Seed 07: Error codes the seed does not name

**Question.** The seed names eight codes for the new commands: `in-use`, `bad-argument`,
`no-space`, `busy`, `bad-offset`, `incomplete`, `bad-checksum` and `bad-file`. It has none
for `upload data`, `upload end` or `upload cancel` when no upload is open, which is what a
client meets after the 60 seconds or after a restart of the board; and none for a storage
that cannot be read or written. The owner approves every addition to the command list.
This is a gap in the seed.

**Answer.** Two codes are added, as working assumptions until the owner rules:
`no-upload`, for the three commands with no upload open, and `storage-error`, for a
failure of the host's storage, after which the show is as it was. The others are used as
far as they reach: `unknown-id` for `remove` of an id no item has, as for `play`, and
`show-invalid` for `list`, `remove` and every `upload` command while the show is invalid.
The order when several apply is one list for all commands: `line-too-long`,
`unknown-command`, `bad-argument`, `show-invalid`, `no-upload`, `incomplete`,
`bad-checksum`, `busy`, `unknown-id`, `in-use`, `no-space`, `bad-offset`, `bad-file`,
`storage-error`.

**Resolution.** `docs/specs/07-p1-content-commands/requirements.md`, Requirement 9;
`design.md`, "The text of docs/commands.md" and "What goes beyond the seed".

## Seed 07: `busy` for `upload end` and for `remove`

**Question.** The seed gives `busy` to `upload begin` when an upload is already open. It
does not say what `remove` does while an upload is open, or what `upload end` does when
the file cannot be judged at once.

**Answer.** `remove` is refused with `busy` while an upload is open: the upload may be
about to replace that item, and both need the one buffer the core writes `show.json`
from. `upload end` is answered with `busy` while the file is still being checked; the
upload stays open and the client sends `upload end` again. See "Seed 07: Checking an
uploaded file while the show plays". Both are uses of an approved code that the owner has
not seen.

**Resolution.** Seed 07 `requirements.md`, Requirement 4 criterion 3 and Requirement 7
criterion 6; `design.md`, "The upload".

## Seed 07: The form of the base64 and of the CRC-32

**Question.** The seed writes `<base64>` and `<crc32>` and gives neither a form. Seed 04
found that WLED's web server takes a request body apart as a form when a client sends it
as a form or as plain text, and that a body is safe then only without `&`, `=`, `+` and
`%`. The usual base64 has `+`, `/` and `=`.

**Answer.** The base64 is the alphabet of RFC 4648, section 5: `A`-`Z`, `a`-`z`, `0`-`9`,
`-` and `_`, without padding, with the unused bits of the last character zero, so that a
piece has one spelling. Every valid command line is then still free of the four
characters, whatever content type a client sends. The CRC-32 is the one of zlib and PNG,
written as exactly eight hexadecimal digits in lower case; the documents give the check
value for `123456789`.

**Resolution.** Seed 07 `requirements.md`, Requirement 6 criterion 2 and Requirement 7
criteria 1 and 2; `design.md`, "The upload".

## Seed 07: The chunk size

**Question.** The reply to `upload begin` names C, the most data bytes of one
`upload data` line. The seed fixes the line at 2,048 characters and not C.

**Answer.** C is 1,500. The longest line is then `upload data`, an offset of ten digits
and 2,000 characters of base64: 2,023 characters. 1,518 bytes would fit exactly; 1,500
leaves room and is a multiple of three, so every piece but the last is whole groups of
base64. C is a constant of the core, the same on every host.

**Resolution.** Seed 07 `requirements.md`, Requirement 5 criterion 1; `design.md`, "The
upload".

## Seed 07: Checking an uploaded file while the show plays

**Question.** `upload end` must refuse a file that is not valid ODRG for the canvas, with
the format's reason. Finding that out means decoding the whole file. At startup that
took 3.1 seconds on the board for a dense 60 x 30 clip of ten seconds, as seed 04
measured. The seed also says playback continues during an upload, and the core is one
thread that the host calls.

**Answer.** The file is checked in steps of one frame record, one step after each refresh
the core produces, by a second decoder with its own buffers that reads the file back from
storage. The check begins when the last byte has arrived. `upload end` is answered with
`busy` until it has ended. A step is skipped after a refresh that came late, so the check
never pushes the rate down further. Two things follow that the owner should know: a file
of F frames is checked in about F fiftieths of a second, however simple it is, so Hello
world takes five seconds; and the second decoder costs 43,568 bytes of the core's memory.
Checking the bytes as they arrive was not chosen: the decoder pulls its input and cannot
stop inside a frame record, and a file read back is a file that was really stored.
Checking inside `upload end` in one go was not chosen: the LEDs would stand still for
seconds.

**Resolution.** Seed 07 `requirements.md`, Requirement 7 criterion 6 and Requirement 10
criterion 6; `design.md`, "The check".

## Seed 07: One host function more than the seed lists

**Question.** The seed says the host interface grows only by writing a file, renaming,
deleting, and asking for free and total space. The check of an uploaded file needs to
read that file while the player has another file open, and `open`, `read` and `close`
hold one file, read front to back.

**Answer.** One more function, `read_at`: up to 512 bytes of a named file from an offset.
It carries no state in the core, and a host serves it with a second open file. It is a
working assumption until the owner rules. Without it the check would have to stop
playback, or the uploaded file would have to be trusted unchecked.

**Resolution.** Seed 07 `requirements.md`, Requirement 14 criterion 1; `design.md`, "The
host interface" and "The check".

## Seed 07: Writing a file is three host functions

**Question.** "Writing a file" could be one function that adds bytes to a named file. An
upload arrives over hundreds of commands.

**Answer.** Three functions: `write_open`, `write` and `write_close`. The host keeps the
file open between the commands, and the file system commits once, at the end. A host must
promise that a file is whole in storage after `write_close`, and that a file being
written when the power goes is one the core removes at its start.

**Resolution.** Seed 07 `design.md`, "The host interface".

## Seed 07: How many items a running show can hold, and what `no-space` covers

**Question.** The core takes its tables once, at startup, sized from `show.json`, and may
not allocate afterwards. An upload adds an item. `docs/show.md` sets no limit on the
number of items, and the seed names no code for a show that is full.

**Answer.** The tables are taken with room for 32 items more than the show has at
startup, and for at least 128. A new item beyond that is refused with `no-space`, which
the seed gives to "the file would not fit"; replacing and removing still work, and a
restart or a removal makes room. No limit is put on what a show file may hold. `no-space`
for the file itself is judged with a reserve: the size, a 256th of it and 16,384 bytes
must be free.

**Resolution.** Seed 07 `requirements.md`, Requirement 5 criteria 4 and 5 and
Requirement 13; `design.md`, "Tables with room".

## Seed 07: A show without items

**Question.** `remove` can remove the last item, and `space` can report 0 animations.
`docs/show.md` says `items` holds one or more items, so a show whose last item was removed
would be invalid at the next start, and an invalid show takes no upload.

**Answer.** `items` may be empty. A show without items is valid: nothing plays, `list`
gives no items, and an upload adds the first. This changes `docs/show.md`,
`docs/reasons.md`, the core and the Python reader of show files, and the JavaScript one
when it exists. It is a change to a governing document that the owner has not seen.

**Resolution.** Seed 07 `requirements.md`, Requirement 4 criterion 9 and Requirement 12
criterion 5; `design.md`, "The text of docs/show.md"; `tasks.md`, task 4.

## Seed 07: A power cut between two files

**Question.** A change touches up to three files: the animation, `show.json`, and the
animation that is no longer needed. A rename replaces one file at once, not three, and
the host interface cannot list the folder to find a file that no item names.

**Answer.** Every change has one rename of `show.json` at which the show changes; before
it the old show is whole and after it the new one. A new animation is renamed into place
before that point and an old one deleted after it. So that no file is left that the show
does not name, the core first writes the names concerned into a small file,
`pending.txt`; at its start it removes every file named there that no item names, and
then that file. The temporary files `upload.part` and `show.part` are removed at every
start. A folder with none of the three is started as before.

**Resolution.** Seed 07 `requirements.md`, Requirement 11; `design.md`, "The four kinds of
change" and "What the start does with leftovers".

## Seed 07: What show.json looks like after the core wrote it

**Question.** The core must write `show.json`. Nothing says in what layout, or which
brightness it writes after `brightness` commands.

**Answer.** One line without spaces and a line feed, with the members in the order of
`docs/show.md`. The brightness written is the one the file had when the core started:
what `brightness` changes is not kept across a restart, as before. A file written by hand
keeps its layout until the first change.

**Resolution.** Seed 07 `requirements.md`, Requirement 12; `design.md`, "The text of
docs/show.md".

## Seed 07: A file name that another item has

**Question.** `upload begin` names a file. `docs/show.md` lets two items name one file. An
upload under the name of another item's file would change that item's animation too.

**Answer.** It is refused with `in-use`. An upload for an item may use that item's own
file name or a name no item has. A show installed over USB with two items on one file
keeps working, and the file is deleted with the last item that names it.

**Resolution.** Seed 07 `requirements.md`, Requirement 5 criterion 4; `design.md`, "The
upload".

## Seed 07: `list` and `space` with an invalid show, and a cycle too long for a reply

**Question.** The seed does not say what `list` gives when the show is invalid, or what
is done with an item that does not fit into a reply of 1,024 bytes even alone, which a
cycle of more than about 150 ids of five digits does not.

**Answer.** With an invalid show `list` is refused with `show-invalid`, like `play`, and
so are `remove` and the `upload` commands: a show that is invalid cannot be repaired by a
command, only installed again. `space` still answers, with 0 animations. A cycle too long
for a reply is listed with an empty `cycle`, which no valid show has, so that `list`
always gets through the show.

**Resolution.** Seed 07 `requirements.md`, Requirement 2 criterion 2, Requirement 3
criteria 6 and 7 and Requirement 9 criterion 4.

## Seed 07: What plays after a change

**Question.** The seed says what happens when the playing item is removed. It does not
say what happens when the file of the animation on the LEDs is replaced.

**Answer.** When the item being played got a new file, or the cycle being played lists
it, what is playing starts again from its first frame at the next refresh. Every other
change leaves the LEDs exactly as they would have been. The player closes its file before
a rename or a removal touches it.

**Resolution.** Seed 07 `requirements.md`, Requirement 10 criteria 3 and 4; `design.md`,
"Playback and a change".

## Seed 07: What 60 seconds without data means

**Question.** "An upload with no data for 60 seconds is discarded." After the last byte no
data comes any more, the check can take longer than 60 seconds, and a client can go away
before it sends `upload end`.

**Answer.** The 60 seconds are counted from the last progress: `upload begin`, a piece
that was taken, or a step of the check. A check that runs is never cut off; an upload
whose check has ended and whose `upload end` does not come is discarded after 60 seconds.
The time is that of the timestamps the host passes with its calls.

**Resolution.** Seed 07 `requirements.md`, Requirement 8 criteria 2 and 3.

## Seed 07: Memory close to the limit

**Question.** The core's memory for the 60 x 60 canvas with 100 items must stay under
128 KB. Seed 05 leaves it at 70,768 bytes.

**Answer.** With this seed it is about 124,600 bytes, 95 percent of the limit: the second
decoder's window and pixel buffer, 43,568 bytes, the longer line and reply, the chunk
buffer, and tables with room. The limit holds and the suite measures it. A later feature
has little left.

**Resolution.** Seed 07 `requirements.md`, Requirement 13 criterion 4; `design.md`,
"Memory".

## Seed 07: The space the emulator reports

**Question.** The emulator applies the commands to its folder. The disk of a Mac has
hundreds of gigabytes free, so `no-space` could never be met and a client would show
figures unlike the board's.

**Answer.** The emulator reports the board's storage: 10,354,688 bytes in total, or the
number given with `--storage`, and as free the total less the files of the folder, each
rounded up to a block of 4,096 bytes. The files themselves are really written, renamed
and deleted in the folder.

**Resolution.** Seed 07 `requirements.md`, Requirement 16 criteria 2 and 3.

## Seed 07: Long lines in the emulator's log

**Question.** The page's log shows every command line. An upload is hundreds of lines of
2,000 characters.

**Answer.** A log entry carries the first 200 characters of a line and `length`, the
number of characters it has, and the page shows both. `cut` keeps its meaning: the line
was longer than the core's limit.

**Resolution.** Seed 07 `requirements.md`, Requirement 16 criterion 5.

## Seed 07: Writes on the board and the LEDs

**Question.** The board must report 25 or more refreshes a second during an upload. A
write to the flash stops the task that makes it, and the core's lock with it. Nothing
about the times of WLED's file system on this board was measured for the spec.

**Answer.** One `upload data` is one write of at most 1,500 bytes. The usermod times every
storage call and gives the core no further command line until twice that time has passed,
and at least 20 ms, without looking into a line: it holds the port's bytes and the web
server's request back. Storage calls so take at most a third of the time. An early task
measures this on the board with the probe build, before the core's upload is written. If
25 cannot be held, the writes move to a task of their own, designed from what was
measured.

**Resolution.** Seed 07 `requirements.md`, Requirement 17; `design.md`, "Pacing" and
assumptions B1 to B6; `tasks.md`, task 3.

## Seed 07: A long line on the board's port

**Question.** A line may have 2,048 characters. Read in the Arduino core: the USB serial
port keeps received bytes in a queue of 256 bytes and drops what does not fit.

**Answer.** The usermod makes the queue 4,096 bytes. Whether a line sent in one piece then
always arrives whole is tried on the board in task 3; if not, the command tool sends a
line in pieces.

**Resolution.** Seed 07 `design.md`, fact S5 and assumption B4.

## Seed 07: Which show the board is measured with

**Question.** The definition of done asks for 25 or more refreshes a second during an
upload and 49 or more afterwards. Whether the board holds 49 with twenty legs is an open
question of seed 05.

**Answer.** The measurement is made with the bench show on two legs, whose rate without
an upload is 49 or more whatever seed 05 found, and with an upload of a dense bench clip
of 60 seconds.

**Resolution.** Seed 07 `requirements.md`, Requirement 17 criterion 4; `tasks.md`, task 7.

## Seed 07: Details of the command tool

**Question.** The seed gives the tool four commands, a percentage, a speed and a status
that is not zero on a failure. It does not say where the progress goes, what name the
file gets, or what the tool does about a reply that does not come.

**Answer.** Progress goes to standard error, and standard output gets the reply that
ended the command. The name sent is the last part of the file's path, as it is; the core
judges it. A piece whose reply did not come is sent once more, and `bad-offset` for that
second line means the first was taken. On any reply that is not ok the tool sends
`upload cancel` and exits with 1. It waits on `busy` for up to 600 seconds. A file that
cannot be read is status 2, with nothing sent. Over the port the tool keeps the port open
for the whole upload.

**Resolution.** Seed 07 `requirements.md`, Requirement 18; `design.md`, "The command
tool".

## Seed 07: No command gives the canvas size

**Question.** The app of seed 09 converts a video on the phone for the installation's
canvas and speaks to the board only through the commands. No command reports the canvas
size.

**Answer.** Nothing is added here: a command or a member of a reply is the owner's to
approve. A file of the wrong size is refused by `upload end` with `bad-file` and the
reason `size-mismatch`, after it was sent. Seed 09 has to settle where the app gets the
size.

**Resolution.** Seed 07 `design.md`, "Risks", item 8.

## Seed 07: Recording the seed's progress

**Question.** As for the other seeds, and as for seeds 04 and 08: the definition of done
has an item only a person can check.

**Answer.** The spec commit leaves `state.json` as it is. The first task sets
`in_progress`. The last task is the owner's check over the board's network and sets
`completed`; an agent leaves it open.

**Resolution.** Seed 07 `tasks.md`, tasks 1 and 9.

## Seed 09: Seeds 06, 07 and 08 are not implemented

**Question.** The seed depends on the converter library, the content commands and the
board's network. None of the three exists while the spec is written: there is no
`converter/`, the core has five commands, and the board's network still has WLED's name.

**Answer.** The spec is written against the designs of the three seeds: what the library
offers and how it is given frames, the commands with their replies, codes and limits, and
the network `odrig` at `4.3.2.1`. Each task follows the code it finds and records a
difference. The first task stops when the core's limits are still those from before seed
07 or `converter/lib/` is not there.

**Resolution.** Seed 09 `requirements.md`, the opening; `design.md`, "What this design
relies on"; `tasks.md`, the opening and task 1.

## Seed 09: `status` with the canvas size, and replies that were to keep their bytes

**Question.** The owner settled that `status` gains `width` and `height`. Nothing says
where in the reply they stand, what "the mapping is unusable" is for the core, or how this
goes with seed 07's Requirement 1 criterion 6, by which `status` keeps its reply byte for
byte.

**Answer.** The two members come last, after `error`, so that everything before them
keeps its place. They are numbers whenever the core holds a mapping, also while the show
is invalid for another reason, and both `null` when it holds none: the file is missing,
breaks a rule, or got no memory. Seed 07's criterion gives way for `status` alone, by the
owner's decision; every other reply keeps its bytes. The board reports the size only after
the firmware was built and flashed again, so a task with the board does that, and the app
has a message for an installation that does not report it yet.

**Resolution.** Seed 09 `requirements.md`, Requirement 1; `design.md`, "`status` with the
canvas size" and "Messages"; `tasks.md`, tasks 1 and 2.

## Seed 09: Where the app lives, and what of it is tracked

**Question.** The seed names no folder and no file. It asks for plain web code, a
Capacitor project, and a copy of the library that the build makes and the repository does
not keep.

**Answer.** Everything is in `app/`: the web code in `app/www/`, the Capacitor project
for Android in `app/android/`, the tool in `app/app.py` with `app/apptool/`. The Android
project is tracked as Capacitor creates it, which is how Capacitor means it to be kept:
it holds our manifest, our plugin and the wrapper of the build. The web code imports the
library from `lib/` beside itself, and no such folder is tracked: the build puts the files
of `app/www/` and of `converter/lib/` together in `build/app/www/` and hands that folder
to Capacitor, and the suite's server serves `converter/lib/` under that path.

**Resolution.** Seed 09 `requirements.md`, Requirements 3 and 5; `design.md`, "Repository
layout" and "`build`"; `tasks.md`, task 4.

## Seed 09: The tool that builds the app, and what it takes from the Mac

**Question.** The seed says the tools needed to build the app install into the project
folder, and that one documented command builds the APK. It does not say what runs that
command, and Capacitor's command line itself needs Node.js.

**Answer.** A tool in Python's standard library, `python3 app/app.py`, as the firmware has
one: `setup`, `build`, `serve` for a browser on the Mac, and `install` for a phone on USB.
It installs the Capacitor packages, a JDK, the Android SDK's command-line tools and
packages into `app/node_modules/` and `build/app/`, and gives every program it starts a
home for its caches and settings there: npm, Gradle, the Android tools with their debug
key, and Capacitor's command line. Node.js is not installed into the project folder. It
is taken from the Mac, version 22 or later, as the converter of seed 06 takes it: the
working assumption is that "the tools needed to build the app" are the ones the app adds.

**Resolution.** Seed 09 `requirements.md`, Requirements 4 and 5; `design.md`, "The tool";
`tasks.md`, task 4.

## Seed 09: Which versions, and where each download comes from

**Question.** The spec has to name the packages, the JDK and the SDK with versions and
sources, from what is current, and nothing may be installed to find out.

**Answer.** Read on 2026-10-12: Capacitor 8.5.3, whose Android project is at API level
36 with the Android Gradle plugin 8.13.0, Gradle 8.14.3 and Java 21; Temurin JDK
21.0.12.1+1; the command-line tools 15859902 from the Android download page; and the SDK
packages `platform-tools`, `platforms;android-36` and `build-tools;35.0.0`. Each archive
is fixed by its size and SHA-256 in `app/toolchain.json`, and the Gradle distribution by
its checksum in the wrapper's properties. The documented downloads are 739,587,796 bytes;
what Gradle fetches beside them is not documented and is measured by the task. That the
versions install and build together on this Mac is assumed and is the first thing the
build task settles. The page of the SDK tool calls it deprecated in favour of a newer
program; it is used because it is in the pinned archive.

**Resolution.** Seed 09 `design.md`, "Read for this design", "Assumed, to be verified"
and "`app/toolchain.json`"; `tasks.md`, task 4.

## Seed 09: Which licence the build accepts

**Question.** The owner accepted the Android SDK's licence terms, so the build may accept
them. The SDK tool has a command that accepts every licence it knows, the licences of
preview packages among them.

**Answer.** The setup accepts one licence, `android-sdk-license`, which the three packages
of the build are under, by answering the one question their installation asks. It does
not run the command that accepts all. Afterwards the SDK's folder of licences must hold
that licence and no other; anything else ends the setup as `licence-refused`.

**Resolution.** Seed 09 `requirements.md`, Requirement 4 criterion 4; `design.md`,
"`setup`".

## Seed 09: How a request reaches a network without internet

**Question.** The seed says the app's requests must go to the board although its network
has no internet. Android sends an app's traffic through mobile data in that case. The
seed leaves open whether a Capacitor plugin or code of our own binds the traffic.

**Answer.** A plugin of our own inside the app's Android project, the sender: it asks
Android for the Wi-Fi network without asking for internet access, and opens every request
on that network with `Network.openConnection`, the interface that Android documents for
sending some of an app's traffic to such a network. It sends a line once, on a new
connection, and looks into nothing. No package from outside is used for it. Nothing of
this can be tried without a phone, so the connection screen shows what the phone reports:
whether there is a Wi-Fi network, whether Android found internet on it, and what carries
the phone's other traffic. If the owner's check finds that requests do not arrive, the
next step is named in the design: the sender also binds the process.

**Resolution.** Seed 09 `requirements.md`, Requirement 7; `design.md`, "Reaching the
target" and assumption P1; `tasks.md`, tasks 11 and 13.

## Seed 09: A `fetch` of the web view

**Question.** The app's code is web code, and web code sends with `fetch`. The spec has to
say how a `fetch` from the app's page is affected on the phone.

**Answer.** It leaves through the phone's default network, which is mobile data while the
board's network has no internet; it is a plain request from a page that Capacitor serves
as `https://localhost`, which the web view blocks unless mixed content is allowed; and it
needs plain HTTP allowed. Binding the whole process to the Wi-Fi network would carry it,
as far as the web view's network code follows the binding, which no interface promises.
So the web code does not use `fetch` for the target on the phone. It uses it in a browser
on a computer, where there is no sender, and that is the way the suite runs. The price:
the sender and the few lines that call it are proven on a phone alone.

**Resolution.** Seed 09 `requirements.md`, Requirement 7 criteria 4 and 8; `design.md`,
"How a `fetch` of the web view is affected, and why the app does not use one" and "Risks".

## Seed 09: Who joins the network, and what the phone makes of it

**Question.** `docs/android-app.md` left open whether the operator joins the board's
network by hand or the app asks Android to join it. Nothing says what a phone shows for
`odrig`.

**Answer.** The operator joins `odrig` in the phone's Wi-Fi settings. The app does not
join networks, does not hold the password and does not read the network's name, which
would need the location permission. Read in WLED's source: its access point answers every
name with its own address and redirects every page, so a phone is expected to offer a
sign-in for `odrig` or to say that it has no internet, and to keep its other traffic on
mobile data. What a real phone shows, and what to answer, is noted in the owner's check
and written into the app's page then.

**Resolution.** Seed 09 `requirements.md`, Requirement 6 criterion 8 and Requirement 23
criterion 2; `design.md`, "What the phone does with the board's network", assumption P2.

## Seed 09: The lowest Android and the lowest web view

**Question.** The spec has to name the minimum Android version and why.

**Answer.** API level 24, Android 7.0: the lowest the chosen Capacitor supports, and
nothing in the app needs more. What decides is the web view, which is updated apart from
Android: the app needs version 94, the first with the two decoding interfaces, and shows
a page that says so on an older one. The app targets API level 36. From Android 17 on, an
app that targets level 37 needs a permission of its own for addresses on the local
network; raising the target level is not part of this seed and will need that permission.

**Resolution.** Seed 09 `requirements.md`, Requirement 6; `design.md`, "The Capacitor
project".

## Seed 09: How a video is read without a decoder in the package

**Question.** The seed says video and GIF files are decoded with what the web view
provides and no decoder is bundled. The web view decodes video samples, but it has no
interface that takes a video file and gives its frames with their times.

**Answer.** The app reads the file's own table of samples, a reader of about 350 lines
that makes no picture, and gives the samples to the web view's `VideoDecoder`. Every frame
then has the time the file records, as a whole number of units of the track's time scale,
which goes to the library as an exact fraction: the ticks are the ones the converter on a
computer builds. Frames before the part are given to the library as stand-ins with their
true times and are not decoded, so the timeline stays exact and a part deep in a long file
costs only itself. A `<video>` element was the other way: it plays every file the phone
plays, but it gives its times through the player and has to seek for every tick. It is
named as the alternative if the owner's check finds videos that cannot be read.

**Resolution.** Seed 09 `requirements.md`, Requirement 14; `design.md`, "Reading media"
and "Risks".

## Seed 09: Which videos are read

**Question.** The seed says "a video". Phones hold MP4 and QuickTime files with H.264 or
HEVC, and now and then other containers and codecs.

**Answer.** An MP4 or QuickTime file that is not fragmented, whose first video track is
H.264 or HEVC, when the web view says it can decode it. A fragmented file, a file without
video and any other codec are refused with a message each; WebM and other containers are
refused as no video the app reads. Edit lists are not read: one that only shifts a track
changes nothing, because time is counted from the first frame.

**Resolution.** Seed 09 `requirements.md`, Requirement 14 criterion 6; `design.md`, "An
MP4 or QuickTime file" and "Messages".

## Seed 09: A video recorded upright, and a frame larger than the phone should read

**Question.** The converter on a computer applies no rotation that a file records, and
fits the full picture. A phone records upright videos as lying pictures with a rotation,
and its frames have two to eight million pixels.

**Answer.** The app differs from the converter on a computer in two places. It applies a
rotation of 90, 180 or 270 degrees, so that the preview and the LEDs show the picture as
the phone's gallery shows it; an operator has no other way to turn it. And a frame of more
than 1,048,576 pixels is drawn smaller by a whole divisor before the library fits it, so
that a frame read back is at most 4 MiB and the fitting takes milliseconds. The app's page
states both.

**Resolution.** Seed 09 `requirements.md`, Requirement 14 criteria 8 and 9, Requirement
23 criterion 3; `design.md`, "A frame read back".

## Seed 09: GIF delays and GIF pictures

**Question.** The library wants each GIF frame as it is on screen, with the delay the file
records. The web view's image decoder gives pictures and a duration, and a browser changes
a very short delay before it reports it.

**Answer.** The pictures come from the web view's `ImageDecoder`. The delays are read from
the file's own blocks by the app, so that the library gets what the file records and
applies its own rule to a short delay, as on the command line. A GIF of more than 64 MiB
is refused: the web view holds a GIF whole while it decodes it. That the decoder's
pictures follow the rules of seed 06's design is assumed and is compared with the
converter in the suite.

**Resolution.** Seed 09 `requirements.md`, Requirement 14 criteria 3, 4 and 10;
`design.md`, "A GIF" and assumption C4.

## Seed 09: How long a part may be

**Question.** The seed lets the operator choose which part to use and gives no limit. The
spec has to say what happens with long videos and with the phone's memory.

**Answer.** A part is at least 20 ms and at most 120 seconds, and its pictures may take at
most 134,217,728 bytes. On the 60 x 60 canvas 120 seconds are 64,800,000 bytes of
pictures, and storage holds about 70 seconds of a dense clip, so the limit is beyond what
can be installed. At first the part is the whole file, or its first 30 seconds. The
controls do not let a part outside the limits be chosen. Memory that runs out all the same
is caught and shown as a part too long for the phone.

**Resolution.** Seed 09 `requirements.md`, Requirement 15 criteria 4, 5 and 12;
`design.md`, "Long and large files".

## Seed 09: Compressed or uncompressed

**Question.** The converter writes a file compressed or, with an option, uncompressed.
The seed names the fit and the part as the operator's choices and not this one.

**Answer.** A switch, on at first: compressed. It is there because of what was measured
on the board for the target: a dense 60 x 60 clip is about 5 percent smaller compressed,
and the core needs 12.3 ms for one of its frames where it needs 8.6 ms for an
uncompressed one. So for a video an operator may want the uncompressed file. This goes
beyond the seed and is a working assumption until the owner rules.

**Resolution.** Seed 09 `requirements.md`, Requirement 15 criterion 6; `design.md`, "The
add screen".

## Seed 09: The id and the file name of an uploaded item

**Question.** `upload begin` takes an id and a file name, and the client chooses both.
The seed says the operator uploads an animation and nothing about either.

**Answer.** The operator chooses between a new item and the place of an animation item.
For a new item the app proposes the smallest id from 1 that the list does not have, and a
file name made from the picked file's name under the naming rule of `docs/show.md`, with
a number at its end while another item has it. In the place of an item the id and the
file name are that item's. The name can be changed and is checked before anything is
sent.

**Resolution.** Seed 09 `requirements.md`, Requirement 17 criteria 1 to 4; `design.md`,
"Uploading".

## Seed 09: A reply that is lost, and an upload that is already open

**Question.** Seed 07 gives the offset rule and one resend for its command tool. On Wi-Fi
at the event replies will be lost more often, a reply can be lost after its line was
taken, and one upload is open for all clients, with no way to tell whose it is.

**Answer.** A line without a reply is sent again, up to four more times, a second apart,
which stays inside the minute the target waits. A piece answered with `bad-offset` does
not end the upload: the next piece is sent, and the target takes it only if it holds
exactly the bytes before it, which tells a piece that had arrived from an upload out of
step. An `upload end` that was sent again and is answered with `no-upload` is settled by
reading the list. An `upload begin` answered with `busy` is never cleared by the app
itself, because `upload cancel` would end another operator's upload as well as a dead one
of this phone: the app says so and sends `upload cancel` only when the operator confirms.

**Resolution.** Seed 09 `requirements.md`, Requirement 18; `design.md`, "What a reply
means".

## Seed 09: How often the app asks, and how long it waits

**Question.** The seed says the status refreshes on its own and that a target not
answering is shown. It gives no times.

**Answer.** `status` once a second while the app is in front, on every screen, also
between the pieces of an upload; the list and the storage when a screen that shows them
is opened, after every change the app made, and every five seconds while such a screen is
shown. A request waits five seconds for its reply. One request is under way at a time,
and what the operator asked for goes first. While the app is not in front it asks for
nothing.

**Resolution.** Seed 09 `requirements.md`, Requirements 8, 10 and 12; `design.md`, "The
client".

## Seed 09: The emulator's option: its name, what it prints, and seed 03's rule

**Question.** The seed adds an option to listen on the local network and names neither
the option nor what the emulator prints. Seed 03 requires that the emulator listens on
127.0.0.1 only and prints exactly two lines, and its tests say that no option names an
address.

**Answer.** A flag, `--lan`, off unless given. With it the server is bound to every IPv4
address of the Mac, the two lines stay as they are, a third line `lan:` names the address
a phone uses, and a warning on standard error says that anyone on that network can send
commands and open the page. The flag names no address, so there is still no option that
does; record mode refuses it. Seed 03's rule holds without the flag, and its tests are
changed to say that.

**Resolution.** Seed 09 `requirements.md`, Requirement 2; `design.md`, "The emulator on
the local network"; `tasks.md`, task 3.

## Seed 09: The test mp4

**Question.** The definition of done has the app convert and upload "the test GIF and the
test mp4". The mp4 that the Python suite builds is MPEG-4 Part 2, which Chrome does not
decode, and a web view decodes what Chrome decodes.

**Answer.** The suite builds its videos with the same fixture and the codec H.264, which
the PyAV of this project can write. The result is compared with what
`node converter/odrig.js import` gives for the same file: the same number of frames and
durations, and each picture the list colour of the frame on screen; the largest
difference of a colour value is recorded, not required. For the GIFs the frames are
required to be identical.

**Resolution.** Seed 09 `requirements.md`, Requirement 15 criteria 7 and 8, Requirement
21 criterion 5; `design.md`, "The media"; `tasks.md`, task 5.

## Seed 09: How the suite drives the page, and which checks need what

**Question.** The definition of done wants the web code driven in headless Chrome against
the emulator, and tests that need a phone kept apart. No browser driver may be installed.

**Answer.** A driver page of the suite holds the app's page in a frame and works it as an
operator does: it presses buttons by their words, fills fields and gives the file input a
file. A server of the suite can stand between the app and the emulator to drop or delay a
reply. Three kinds of check are kept apart: the suite in `tests/app/`, which needs no
phone and no Android tool; `tests/apk/`, which looks into a built APK and needs the work
folder; and the owner's numbered list for a phone, which is no program. The sender is
compiled by the build and run by no test.

**Resolution.** Seed 09 `requirements.md`, Requirements 21 and 22; `design.md`, "Testing
strategy".

## Seed 09: The language, the look in numbers, and back

**Question.** The seed asks for a dark design with large controls for use outdoors at
night, and plain words for every failure. It gives no sizes and no language.

**Answer.** English, with every text in one file. Black behind everything; text with a
contrast of at least 7 to 1 and at least 18 CSS pixels high; everything that is pressed
at least 56 CSS pixels in both directions and 8 from its neighbour; nothing that needs a
long press or a swipe; four screens behind four buttons that are always there. A message
stays until it is dismissed. The system's back gesture goes to the screen before and does
not leave the app while a conversion or an upload runs. While the app is in front the
screen stays on.

**Resolution.** Seed 09 `requirements.md`, Requirements 6, 19 and 20; `design.md`, "The
look".

## Seed 09: The app's identifier, its name, its picture and the build's stamp

**Question.** An Android app needs an identifier and a name. Several operators will have
the app, and nothing says how to tell which build a phone has.

**Answer.** The identifier is `app.odrig.operators` and the name `odrig`. The launcher
picture and the start screen are the ones Capacitor's project comes with. The build writes
the commit it was made from into the package, and the connection screen shows it. The
debug key that signs the APK is kept in the work folder: a new work folder means a new
key, and an app signed with the old one has to be removed from a phone first.

**Resolution.** Seed 09 `requirements.md`, Requirement 5 criteria 3 and 6, Requirement 6
criterion 9; `design.md`, "The Capacitor project".

## Seed 09: docs/android-app.md

**Question.** `docs/android-app.md` holds first notes and questions for the owner, and
says that nothing in it is decided. The owner has answered its questions, and seeds 07
and 08 left the page to this seed.

**Answer.** The page becomes the app's page: building, installing, using, the messages,
the limits, the tests and the owner's check. The notes and the questions go, with their
answers in `docs/decisions.md` already. The spec does not edit the page; the
documentation task does.

**Resolution.** Seed 09 `requirements.md`, Requirement 23; `design.md`, "Documents";
`tasks.md`, task 12.

## Seed 09: Recording the seed's progress

**Question.** As for the other seeds: the definition of done has an item only a person
can check, with a phone.

**Answer.** The spec commit leaves `state.json` as it is. The first task sets
`in_progress`. The last task is the owner's check on a phone and sets `completed`; an
agent leaves it open.

**Resolution.** Seed 09 `tasks.md`, tasks 1 and 13.
## Seed 10: The names of the new files, their length, and where their tests live

**Question.** The seed names `AGENTS.md` and `CLAUDE.md` and describes four more pages
without naming them. It limits the entry file to 150 lines and says of the others only that
they are "short enough to be read in full at the start of a session". It asks for two tests
and does not say where they go.

**Answer.** The pages are `docs/vocabulary.md`, `docs/working-rules.md`,
`docs/getting-started.md` and `docs/animation-guide.md`, each of at most 200 lines. The
test that checks what the pages name is the suite `tests/onboarding/`, which needs Python
alone. The test that follows the pages is a suite of its own, `tests/walkthrough/`: it
installs libraries from the network and takes minutes, so no other test command starts it.

**Resolution.** Seed 10 `requirements.md`, the terms and Requirement 7 criterion 4;
`design.md`, "Repository layout".

## Seed 10: What a fresh clone is, for a test that has to pass before the commit

**Question.** The definition of done has a test follow the pages "from a fresh clone". A
clone holds what is committed, and a task has to see its tests pass before it commits the
page they follow.

**Answer.** The test clones the repository into a temporary folder and then brings over
every tracked file that differs in the working tree, is new or is gone, and commits that in
the copy. With a clean working tree the copy is a plain clone. Nothing untracked or ignored
reaches it, so a new file has to be staged before the test sees it.

**Resolution.** Seed 10 `requirements.md`, the term "a fresh copy"; `design.md`, "The
walk-through".

## Seed 10: What the test that follows the pages does not run

**Question.** The seed has that test run "the test suites", and has the getting-started
page give every suite that needs no board. The firmware tool's suite needs no board, but
its first run fetches WLED's source and installs PlatformIO, esptool and Node.js into the
work folder, some hundreds of megabytes. The page also starts the emulator in real time and
sends it commands from a second terminal, which wants somebody to look, and it gives the
command of the test itself.

**Answer.** The test runs the suites that need only what the page's own setup installs: the
converter's, the core's, the emulator's and the quick one. The firmware tool's suite stands
on the page under a heading of its own, with what its first run fetches, and the test does
not run it. The emulator is run in record mode, which the definition of done names; the
commands of the real-time run are given to the tools' parsers by the quick suite. Every
heading with commands is in the test either as followed or as not followed with its reason,
so a new heading cannot go unnoticed.

**Resolution.** Seed 10 `requirements.md`, Requirement 4 criterion 6 and Requirement 8
criterion 3; `design.md`, "The walk-through".

## Seed 10: Which Python the pages name

**Question.** `docs/converter.md` writes `python` for the Python of the virtual
environment, and `docs/emulator.md` says any Python from 3.10 will do, `python3` on a Mac.
A newcomer needs commands that can be copied, and an agent's shell does not keep an
activated environment from one command to the next.

**Answer.** The pages write `.venv/bin/python` wherever they call Python themselves, and
say once that the other documents write `python` for it. `make -C core test` and
`python3 firmware/fw.py` are given as their own documents give them.

**Resolution.** Seed 10 `design.md`, "The pages".

## Seed 10: What is added "at the end" of docs/decisions.md and of this file

**Question.** The seed says `docs/drifts.md` and `docs/decisions.md` "are only ever added
to at the end", and also that `docs/decisions.md` records the new rule "in place of" the
old one. `docs/decisions.md` states each decision as it stands, in sections, with a change
log at its end. In this file one entry of seed 02 was given a later paragraph in its
middle.

**Answer.** In this file a new entry goes at the end and an earlier entry is left as it
is; a later finding is a new entry that names the earlier one. In `docs/decisions.md` it is
the change log that is added to at the end. A statement in its sections changes only when
the decision changes, which needs the owner, as it does here: the seed is the owner's.
When two branches have both added at the end of either file, the merge keeps both
additions, those of `master` first.

**Resolution.** Seed 10 `requirements.md`, Requirement 3 criterion 7 and Requirement 6
criteria 3 and 4.

## Seed 10: Who merges, which suites, and where a clone comes from

**Question.** The seed's rule has a branch "brought up to date with `master` before
merging" and merged "only with every test suite passing". It does not say who merges. A
contributor without a board cannot run the suites that need one. `docs/decisions.md` says
there is no remote yet, and a second computer has to get the repository from somewhere.
This is a gap in a governing document.

**Answer.** The rule is written without naming who merges. "Every test suite" is every
suite that needs no board. The sentence about the remote stays as it is, and the pages
name no address: a newcomer clones from wherever the owner said. These are working
assumptions until the owner rules.

**Resolution.** Seed 10 `requirements.md`, Requirement 3 criterion 7.

## Seed 10: An imported source: whether it is committed, and how large it may be

**Question.** `docs/decisions.md` calls JSON frames "the tracked, lossless source of each
animation" and lists as open "whether large video-derived JSON sources are tracked as they
are". The animation guide has to say what is committed. This is a gap in a governing
document.

**Answer.** The working assumption, until the owner rules: a source made by an import is
committed in `animations/` when it is at most 50 MB, the size at which the large hosting
services warn; they refuse a file above 100 MB. A longer piece is cut into shorter
animations. The video or GIF it came from is not committed. A source that a tracked
generator writes for the target canvas is not committed either: it is written into
`build/` when a show is packed, as the demo show's sources are. The open question in
`docs/decisions.md` stays as it is.

**Resolution.** Seed 10 `requirements.md`, Requirement 5 criteria 3 and 4.

## Seed 10: The bench build, and the one strip that is wired

**Question.** `README.md` and `docs/decisions.md` call the bench build of two legs
"today's" and "confirmed working". `docs/firmware.md` and `docs/mapping.md` say that one
strip of 60 LEDs is wired at present, on pin 1.

**Answer.** Both are so, of different things, and the vocabulary says which: the bench
build is the build that `mapping/legs-2.json` describes, two row legs, which was confirmed
on the hardware; what is wired to the board at present is one strip. The brightness limit
follows what is wired.

**Resolution.** Seed 10 `requirements.md`, Requirement 2 criterion 4.

## Seed 10: Files that a clone does not have

**Question.** `docs/decisions.md` names proof-of-concept scripts in `animations/` and
`tools/`. They are untracked: they exist on the first computer only, as do `esp32-backup/`,
`firmware/wled-16.0.1/`, `scratch/` and a stock image at the root. A clone has none of
them.

**Answer.** The pages name only the two folders that nobody may change, say that they are
on the first computer only, and give the rule for every other such file: an untracked file
that you did not make is not yours. The sentence in `docs/decisions.md` is left as it is.

**Resolution.** Seed 10 `requirements.md`, Requirement 1 criterion 5, Requirement 3
criterion 5 and Requirement 7 criterion 1.

## Seed 10: The rules taken from another project

**Question.** `docs/decisions.md` records that the seed-based process and "agent policies,
limited to the policies that are relevant to this project" were adopted. Their text exists
only in the project they came from. Which of them bind here?

**Answer.** Five rules of conduct: a commitment for later reaches the owner and is not left
only in a file; the scope of a seed is fixed while it is being implemented; commits are
staged by named paths; a test for a fault is seen failing before the fault is mended; and
code carries no history. With them come the seed as a folder with its own state file, one
seed to a commit, and one task to a commit with its checkbox. The rule there that agents
never share a checkout is the root of this project's rule for several contributors. The
rules about that project's background workers and its build service are not taken.
`docs/working-rules.md` states all of this in this project's own words and does not name
the other project.

**Resolution.** Seed 10 `requirements.md`, Requirement 3.

## Seed 10: Recording the seed's progress, and the queue

**Question.** As for the other seeds.

**Answer.** The spec commit leaves `state.json` as it is. The first task sets
`in_progress` and the last task sets `completed`. The queue records carry `Status`,
`Source` and `Task` only, as "Seed 02: Queue records without task ids" has it.

**Resolution.** Seed 10 `tasks.md`, tasks 1 and 6; `.codex/local-task-queue.md`, which is
not tracked.

## Seed 10: The test of the change log

**Question.** The design has the quick suite check that the last entry of the change log of
`docs/decisions.md` is the new one. Every later change adds an entry after it, and the test
would then fail although nothing is wrong.

**Answer.** The test checks that the change log has the entry of the rule for several
contributors once, after the entry of the rule it takes the place of, and that the dates of
the entries never go backwards.

**Resolution.** `tests/onboarding/test_rules.py`.

## Seed 10: The core's test command with another Python

**Question.** `docs/core.md` gives `make -C core test PYTHON=.venv/bin/python` for running
the core's suite with another Python. Run from the repository root it stops with "the tests
need Python 3.10 or later, and '.venv/bin/python' is older or missing": the makefile checks
the Python from inside `core/`, where that path leads nowhere. The getting-started page has
to give a command for the core's suite.

**Answer.** The page gives `make -C core test`, which uses `python3`; the core's suite
needs no library, and `python3` of 3.10 or later is what the page asks for anyway.
`docs/core.md` and the makefile belong to seed 02 and are not changed here. The fault is
reported to the owner with this seed's hand-over.

**Resolution.** `docs/getting-started.md`, "Run the tests".

## Seed 10: Where the onboarding files live, and the Windows contributor

**Question.** While task 5 was being done the owner added four things, which reached this
run through the session that coordinates it. The onboarding files are a workstream of
their own and live in a folder `agent/` at the top of the repository, with
`agent/README.md` as the page a newcomer begins with; `AGENTS.md` and `CLAUDE.md` stay at
the top, short, and point into the folder. A second contributor works on a Windows
computer; making the emulator and the tools run there is seed 11 and that contributor's
first job. The repository has a remote, `https://github.com/korenmic/Odrig`, and the rule
for several contributors is to be made concrete for it. Hello world and DVD bounce are
proof-of-concept animations and are presented as test content only. The spec has the pages
under `docs/`, names no remote, and several points of the new work it does not settle.

**Answer.**

- The four pages moved with `git mv` to `agent/`, and `agent/README.md` is new: what the
  project is, the reading order, and what each file of the folder is for. `AGENTS.md`
  keeps the table from tasks to documents and the rules, because an agent that reads only
  that file has to know both; it gives up the commands of the setup, which the
  getting-started page has. Where this spec's requirements and design name a page under
  `docs/`, read `agent/`. Those two files are not edited; `tasks.md` has the work as
  task 6, and the final check is task 7.
- The address of the remote stands in the pages, in `docs/decisions.md` and in the tests,
  because the owner gave it to be written there. Requirement 7 criterion 5, which keeps
  persons and paths of somebody's computer out of the pages, is read as not concerning
  the address of the repository.
- Seeds 11 and 12 are on `master` and not on this branch, and the session's permissions
  did not allow this branch to be brought up to date with `master`. The pages name the
  folder of seed 11 as the owner said. The quick suite takes that one path as present when
  `master`, here or on the remote, holds it, and `AGENTS.md` names seeds 11 and 12 under
  "What is coming", so that its test holds once the branches meet. The suites have not run
  on the two branches together: whoever merges runs them on the result.
- `.gitattributes` on `master` has git keep the additions of both sides in this file. The
  same line is added on this branch, so that what the working rules say of it is so here
  and a test can check it. Two identical additions merge without a conflict.
- The setup on Windows is given as a block that the walk-through does not run, and the
  page says that none of it has been tried there. How Python is started on Windows is
  left to seed 11.
- `docs/decisions.md` said that there is no remote. It now names the remote, the folder
  and the contributor on Windows, and has one more entry at the end of its change log;
  the entry that task 2 of this seed added is left as it was.
- The commands that reach the remote, the clone, `git fetch` and `git push`, were not run
  from this worktree, whose session does not touch the remote. The quick suite checks only
  that they are commands of git that it knows.

**Resolution.** `agent/README.md` and the four pages beside it; `AGENTS.md`; `README.md`;
`docs/decisions.md`, "Scope and process" and the change log; `.gitattributes`;
`tests/onboarding/` and `tests/walkthrough/`; seed 10 `tasks.md`, task 6.
