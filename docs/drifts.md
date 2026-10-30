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

## Seed 02: The core's test command with another Python, settled

**Question.** `docs/core.md` gave `make -C core test PYTHON=.venv/bin/python`, which fails
because `make` runs inside `core/` and looks for the interpreter there. Should the makefile
or the document change?

**Answer.** The document. The interpreter is named by its full path. Run from the top of the
repository, `make -C core test PYTHON="$PWD/.venv/bin/python"` passes all 246 tests.

**Resolution.** `docs/core.md`, the test command.

## Seed 11: What the seed leaves to its spec

**Question.** The seed asks for a tracked script that builds the core on Windows, for the
line protocol on a local TCP port, and for the command tool to reach it. It names no file,
no option, no port number and no printed line. What are they?

**Answer.**

- The build script is `core/build.py`, written in Python with the standard library alone:
  Python is the one program every contributor already has. It finds the compiler itself and
  looks in the folder `tools/` of the repository before the path, so that a compiler can be
  unpacked there without being installed. `tools/` is ignored by git. `core/Makefile` stays
  as it is and stays the way macOS builds.
- The shared library is `core/build/odrig_core.dll` on Windows, whichever compiler built it.
- The emulator's option is `--tcp-port N`, the port without the option is 8601, one above
  the page's, and the printed line is `tcp: 127.0.0.1:<port>`. On macOS the option opens the
  line port beside the serial port and does not take its place, so that nothing a Mac prints
  or opens changes unless the option is given.
- On Windows `--serial-link` is refused with the reason `serial-unavailable`, which the
  emulator already has, and not with a new reason.
- The command tool's option is `--tcp ADDRESS`, where the address must have its port: the
  board has no such port, so no port number is the usual one.
- A command that arrived by the line port has the transport `tcp` in the log. This adds no
  command: the line protocol and the list of commands are those of `docs/commands.md`.
- A real serial port on Windows is opened through `kernel32` with `ctypes`, which is part
  of Python. The rule of seed 03 that only the emulator's binding uses `ctypes` gives way
  for this one module of the command tool.
- The JavaScript shell of the emulator suite on Windows is Node.js, which a developer there
  usually has. macOS keeps `jsc`.
- The core suite needs the object listing and the syntax checks of a GNU-style toolchain.
  With Microsoft's toolchain the build script builds the libraries and the test host, and
  the tests that question a GNU-style compiler are skipped with that reason.

**Resolution.** `docs/specs/11-p0-emulator-and-tools-on-windows/`: `requirements.md`,
`design.md` and `tasks.md`.

## Seed 11: A library that a running emulator has loaded

**Question.** The build script compiled and linked everything at every run. On Windows a
DLL that a running program has loaded cannot be written, so the emulator suite, which
builds the library when it starts, could not run while an emulator was open. What does the
build script do?

**Answer.** What `make` does: a file is made again only when it is missing or older than
what it is made from. An object is made from its source, every header of the core, the
build script and the toolchain written down in `core/build/toolchain.json`, which is
rewritten only when another toolchain is used. So a build with nothing to do touches
nothing, and the suite runs beside an open emulator. When a source did change and the
library is loaded, the script ends with `build-failed` and says to stop the emulator.

**Resolution.** `core/build.py`: `stale`, `needed_by`, `record` and `writable`.
`tests/emulator/test_build_script.py`, the class `OnlyWhatChanged`.

## Seed 11: The emulator suite where there is no pseudo-terminal

**Question.** Many tests of the emulator suite send their lines through the serial port,
end the emulator with SIGTERM, ask `lsof` and `nm`, compile with `cc`, link folders and run
the page's scripts in `jsc`. None of that exists on Windows. Which tests are skipped there,
and which run another way?

**Answer.** A test is skipped only when what it checks is the pseudo-terminal itself or
something Windows cannot do. Everything else runs through what the system has.

- A test that used the serial port as "the other transport beside HTTP" now takes the
  transport that carries bytes on its system: the serial port where there is one, the line
  port elsewhere. The helpers are `support.lines`, `support.line_target` and
  `support.LINES`, which is `serial` or `tcp`. On macOS these tests do what they did.
- Skipped where there is no pseudo-terminal, with that reason: the module of the serial
  port, the tests of the link, and the tests of the POSIX serial exchange. The Windows
  exchange has its own tests, with a stand-in for `kernel32`, which run everywhere.
- The emulator is ended with the break of the console on Windows, the one signal a parent
  can send a child there, and with SIGTERM and SIGINT elsewhere. Ctrl-C itself cannot be
  sent to a child on Windows by a test; the emulator handles it with the same handler.
- The test that stops the emulator's process for 300 ms is skipped where there is no
  SIGSTOP.
- The JavaScript shell is `jsc` where macOS has it and Node.js elsewhere, with
  `tests/emulator/js/shell.js`, which takes the command line of `jsc` and has its `print`,
  `read`, `load` and `checkSyntax`. The syntax check of the page's scripts is then made by
  the engine of Chrome and Edge, not by that of Safari: the test is named for the shell.
- What a library exports is read from the DLL's own table; the C compiler is the one beside
  the compiler that built the library, and with Microsoft's compiler the one test that
  compiles a C program is skipped; the listening addresses come from the system's list
  where there is no `lsof`; folders are copied where a program may not make links; and
  `mkdir` is done by the test where the system has no such program.

On the Windows computer the suite runs 443 tests, of which 15 are skipped.

**Resolution.** `tests/emulator/support.py`; `tests/emulator/js/shell.js`; the test modules
of `tests/emulator/` that the commit of seed 11 task 4 changes.

## Seed 11: The core suite with the compilers of Windows

**Question.** `make -C core test` builds the test host with the address and
undefined-behaviour sanitizers and the suite reads the library with `nm -m` of macOS. What
does `python core/build.py test` build on Windows, and what does the suite read?

**Answer.**

- GCC for Windows has no run-time library for either sanitizer. The build script takes the
  first set of checks with which a small program can be built and run: the two sanitizers
  where they are; then the undefined-behaviour checks as traps, which need no library,
  with the stack protector and the assertions of the standard library; then none. It
  prints the line `checks: <what it took>`. On the Windows computer, with GCC 16.1 of
  WinLibs, that is the second set. A fault of memory that only the address check finds is
  therefore found on macOS, not on Windows.
- With Microsoft's compiler the test host is built with `/RTC1 /GS /sdl`. Its address
  check is not used: the program then needs a DLL of the compiler, which is found only
  inside the compiler's own environment.
- The test host needs three calls of Windows: memory with a wider alignment from
  `_aligned_malloc`, standard input and output as bytes, and a backslash taken as a
  separator of a path.
- The compiled core refers to `strlen` when GCC builds it, though no source calls it: GCC
  puts it in the place of a loop that looks for the end of a text. `strlen` joins the list
  of names the core may refer to. It takes no memory, does no input or output and reads no
  clock. `docs/core.md` said the core refers only to routines that copy, fill and compare
  memory: that sentence now names this one too. This is a change to a document that
  defines the project, and it holds until the owner rules otherwise.
- Where `nm` gives a letter for the kind of a name, the suite reads that form and puts an
  underscore in front of every name, so that the list of allowed names is one list. With
  Microsoft's compiler the ten tests that need a GNU-style `nm`, `ar`, `cc` or `c++` are
  skipped.

On the Windows computer `python core/build.py test` runs 246 tests, all of which pass with
GCC; with `--cxx cl`, 246 with 10 skipped.

**Resolution.** `core/build.py`: `checks`, `build_host` and `test`. `tests/core/host/`.
`tests/core/support.py`, `tests/core/test_build.py`, `tests/core/allowed_symbols.txt`.
`docs/core.md`, the second paragraph.

## Seed 11: The converter suite on Windows

**Question.** On Windows 33 of the 618 tests of the converter suite failed. Is anything
wrong in the converter?

**Answer.** No: the converter writes every file as bytes and makes the same files on
Windows. The three causes were in the tests.

- Five places wrote a page as text, and Python then writes the line ending of the system:
  `\r\n` on Windows. The tool reads bytes and found no marker that ended in `\n`. The tests
  now write `\n`.
- One test compared a path inside the package with `generators/dense.py`; on Windows the
  path came with a backslash. It is compared in the form the documents write.
- The builder of the test vectors has zlib make the body of `deflate-fixed.odrg` with the
  strategy `Z_FIXED`. The Python 3.14 of Windows has zlib-ng, 1.3.1.zlib-ng here, which
  answers that request with a stored block, so the builder gave up. The builder now keeps
  what zlib made when that is one last block of the fixed codes, as with the zlib of macOS
  and of Python 3.12, and otherwise writes such a block itself, every byte as a literal.
  The tracked vector does not change. The file was never compared byte for byte with what
  the builder makes, because the output of zlib depends on its version.

The sizes the documents give for compressed files were measured with zlib 1.2.12 and are
compared within 2 percent; with zlib-ng they still are within that.

**Resolution.** `tests/converter/test_mapping_page.py`, `tests/converter/test_scope.py`,
`tests/converter/build_vectors.py`: `fixed_block` and `fixed_codes`, and
`tests/converter/test_vectors.py`, the class `TheBuilder`.

## Seed 11: The pages after the work on Windows

**Question.** The getting-started page and the animation guide are each 200 lines long,
the most the quick suite lets a page be, and the walk-through runs their commands on the
first computer. How do they give the commands of Windows? And the decisions said the
emulator runs on macOS for now: who changes that?

**Answer.**

- The pages keep their commands, which are those of macOS and which the walk-through runs.
  The section "On Windows" of the getting-started page has what a Windows computer needs,
  one block with the setup and the four suites, and one table that says how everything
  else on the two pages is written on Windows: the Python of the environment, the build
  script in place of `make`, `mkdir`, the file a script is written to, and the line port in
  place of the serial port. The block is not marked as a shell block, so the walk-through
  does not run it; the quick suite asks each tool whether it understands its commands, and
  compares the four suites with the four the page runs after the setup.
- The quick suite knows `.venv\Scripts\python` as a Python and `core/build.py` as a
  program, and takes `tools/` and `scratch/` as folders no clone has to hold.
- The owner said during this work where a Windows contributor puts what is fetched: nothing
  is installed in the system; a program that is needed is unpacked into `tools/`, and a
  trial goes into `scratch/`. Both are ignored by git. `AGENTS.md` has it as a rule under
  "If you work on Windows", and the build script looks into `tools/` for a compiler.
- `docs/decisions.md` now says that the emulator runs on macOS and on Windows, that it is
  our own program, no longer "Mac program", and that on Windows the lines of the serial
  port travel over a TCP port. The seed, which the owner wrote, asked for exactly this, so
  the sentences follow the seed and no decision is made here. The change log has an entry.
- `AGENTS.md` no longer lists seed 11 under "What is coming".
- The walk-through suite and the firmware tool were not ported: the seed leaves the
  firmware and the board with the first computer, and the walk-through follows the
  commands of macOS.

**Resolution.** `agent/getting-started.md`, "On Windows"; `agent/animation-guide.md`, its
first paragraph; `AGENTS.md`, "If you work on Windows"; `docs/emulator.md`, "Commands" and
"On Windows"; `docs/core.md`, "Commands"; `docs/commands.md`, "Transports";
`docs/decisions.md`; `tests/onboarding/`.

## Seed 11: The final check on Windows

**Question.** What was seen working on the Windows computer, with what, and what did the
check itself turn up?

**Answer.** What was seen is in `docs/emulator.md` under "What has been checked on
Windows". Three things came up on the way and were settled.

- The fresh clone was set up with Python 3.12 where the rest of the work used 3.14, to
  have a second Python and a zlib that is not zlib-ng. There one test of the command tool
  failed: it sets a time limit of 0.4 seconds and measured 0.391. The clock a program reads
  with Python 3.12 and earlier on Windows counts in steps of 1/64 of a second, so a wait of
  0.4 seconds can measure one step short. The limit was kept; the two tests that measure
  it allow one step of the clock, which on macOS is next to nothing.
- The fresh clone was made with git set to convert line endings, `core.autocrlf` true,
  which is what the installer of git for Windows proposes. No file was converted: the
  first line of `.gitattributes` holds.
- A video for the import was made with PyAV, which the converter's environment has: the
  folder of leads the owner gave holds GIFs only.

The check list by eye was not gone through step by step on Windows. A program read the
header and took screenshots in Chrome and in Edge without a window, and the screenshots of
the LEDs view and of the mapping view were looked at. A person at a screen, Python 3.10
and 3.11, a Mac and a board on a `COM` port are what is left, and each is listed in
`docs/emulator.md`.

**Resolution.** `docs/emulator.md`, "What has been checked on Windows" and "On Windows".
`tests/emulator/support.py`, `CLOCK_STEP`, and `tests/emulator/test_tool.py`.
## Seed 03: The check list by eye, closed without a person

**Question.** The last task of seed 03 is a check list to be gone through by a person in
Safari and in Chrome. It was gone through by program in Chrome and left open for the owner.
The owner has said they will not check pages by eye; the only checks they do are of real
LEDs on the board.

**Answer.** The task is closed on the evidence there is: every step of the list passes in
Chrome driven by program, with screenshots. Safari was never checked, and that is recorded
here, not hidden. From now on a check that needs a person is asked of the owner only when it
is about real LEDs on the board.

**Resolution.** Seed 03 `tasks.md`, task 11, ticked; the seed's `state.json` set to
`completed`.

## Seed 11: What the review of the pull request found

**Question.** The work of seed 11 went into a pull request and was read by a reviewer who had
not written it. What did the review find, and what was done about it?

**Answer.** The product code of macOS was found unchanged in what it does. Three tests of the
suite would have failed on the first computer, and six smaller points were named.

- Three tests held only on Windows. One compared every name a shared library offers with the
  seven functions, where only a DLL offers no other name: it now takes the names that begin
  with `odrig_core_`, as the test did before. One expected the settings structure of a serial
  port of Windows to be 28 bytes, which it was only on Windows, because the number type it
  was built from is wider elsewhere: the structures are now built from types of a fixed size.
  One expected a compiler named `C:\x\bin\cl.exe` to be known as Microsoft's on every system:
  the name of a program now ends its folder at a slash or a backslash wherever the script
  runs.
- The command tool on Windows lowered RTS and then DTR by asking for each directly, and went
  on when a request was refused. Windows refuses the request for RTS when the port was left
  to drive RTS by itself, and DTR would then have gone low with RTS still high, which is the
  combination that resets the chip. The tool now lowers the lines through the port's
  settings, written twice: first RTS, with DTR as it was, then DTR. Seen on the `COM1` of
  the Windows computer, with nothing connected, also with RTS set to handshake beforehand:
  both were reported off afterwards. A board has still not been tried.
- The build script read what the command prompt writes in the wrong code page, so a user
  name that is not ASCII would have broken the search for Microsoft's compiler; it used a
  compiler named by a relative path from the wrong folder; both are mended.
- The line port could take a connection, or hand on a line, in the moment it was closing;
  it now takes none and hands on nothing from then on. A library named without a folder is
  loaded from the working folder on Windows too. The helper that ends an emulator in the
  tests ends it also when the signal cannot be sent.
- Not changed: a source that is removed stays in a library that is already built, until the
  build folder is cleaned. The makefile behaves the same way.
- Two tests of the core suite and one of the converter suite called zlib in a way Python
  3.10 does not know. They now use a call every Python has. The two of the core suite were
  there before this seed; this was seen failing with Python 3.10 and has not been run with
  it again.

Before the owner ruled that Linux is no requirement and that the Linux subsystem of the
Windows computer is not to be used for tests, the suites were run there once, with Python
3.10, as the nearest thing to a Mac at hand. The three tests above failed there, which is how
they were seen failing. Everything of the serial port, the serial exchange of the command
tool and the two signals passed. What else failed there concerns Linux only, the names of its
terminal devices and the size of a buffer, and is left as it is. This is not a run on macOS:
the list in `docs/emulator.md` stands.

On the Windows computer, after the mends: converter 622 tests, core 246, emulator 460 with 15
skipped, onboarding 75.

**Resolution.** `odrigctl/winserial.py`; `core/build.py`: `stem`, `absolute` and
`microsoft_environment`; `emulator/lineport.py`; `emulator/binding.py`: `load`;
`tests/emulator/`, `tests/core/support.py`: `raw_deflate`.
## Seed 06: Where the check of the Node.js version lives

**Question.** The design has `converter/odrig.js` check the version of Node.js and then
import `cli/main.js`, and has a test give the check a version. A test that imports
`odrig.js` starts the tool, and an old Node.js that reads `cli/main.js` before the check
runs stops at the first word it does not know, with its own message.

**Answer.** The check is a function of a file of its own, `converter/cli/version.js`,
which the design's layout does not list. It is written in the oldest form of the language
that knows modules, and `odrig.js` imports nothing else before the check has run:
`cli/main.js` is imported afterwards, with `import()`. The test calls the function with
versions, and starts the tool once with a Node.js that is made to report version 18.

**Resolution.** `converter/cli/version.js`, `converter/odrig.js`;
`converter/tests/cli.test.js`, "an old version of Node.js is refused".

## Seed 06: The status of an error that is not a rejection

**Question.** Requirement 2 criterion 10 asks that an error that is no rejection ends the
program with Node's own message and a status that is neither 0, 1 nor 2. Node.js ends a
program with status 1 when an error is not caught, which is the status of a rejected
input.

**Answer.** `main` of `cli/main.js` throws such an error on, as the design says.
`converter/odrig.js` writes the error as Node.js prints it, with the places it passed
through, to standard error and ends with status 70.

**Resolution.** `converter/odrig.js`; `converter/tests/cli.test.js`, "an error that is no
rejection is thrown on".

## Seed 06: Arguments that begin with a minus sign, and seconds the parser refuses

**Question.** The design takes the argument after an option for its value "unless it
begins with `-` and is not a minus sign followed by digits with an optional fraction".
The `argparse` of Python 3.14, which runs the reference here, reads more arguments as
values: every argument in which a minus sign is followed by a digit, or by a point and a
digit, so `-1e3` and `-1.` as well; a minus sign alone; and an argument that holds a
space. Requirement 2 criterion 9 asks for the status of the Python tool.

**Answer.** The parser follows the `argparse` that is installed: an argument is a value,
after an option and among the positional arguments, when it does not begin with a minus
sign, when a digit or a point and a digit follow the minus sign, when it is the minus sign
alone, or when it holds a space. Anything else that begins with a minus sign and is no
option of the subcommand is an unknown option. An older Python reads `-1e3` after
`--start` as an unknown option and ends with status 2, where the JavaScript tool reads the
start and ends with status 1.

The parser checks the form of `--start` and `--duration` and keeps their text; the
subcommand turns the text into milliseconds with the library. Seconds may be written
`1.` and `.5`, as Python reads them. An exponent beyond 9999, plus or minus, is not a
number of seconds. The Python tool ends a command line with such an exponent above zero
with a traceback of its `decimal` module, and reads one with such an exponent below zero
as 0 seconds; nobody writes either.

`-h` is read as `--help`, as the Python tool reads it. A `--` in front of the subcommand,
which the Python tool passes over, is not: the first argument is the subcommand or
`--help`.

**Resolution.** `converter/cli/arguments.js`; `converter/tests/cli.test.js`, "the parser".

## Seed 06: The Python program the suite compares with, in a checkout without `.venv`

**Question.** Requirement 18 criterion 4 takes the Python tool from `.venv/bin/python` of
the repository, or from the program the environment variable `ODRIG_PYTHON` names. The
tasks of this seed were run in a second checkout of the repository, a git worktree, which
has no `.venv` folder of its own. Which of the two is asked first?

**Answer.** `.venv` of the repository when it is there, else the program `ODRIG_PYTHON`
names. With neither, every test that needs the Python tool fails with one message that
names both ways and the two commands that make `.venv`. The suite was run in the worktree
with `ODRIG_PYTHON` set to `.venv/bin/python` of the main checkout, and the three Python
suites with that same program started in the worktree's root, so that it loads the
worktree's `odrig`. In the main checkout nothing needs to be set. The suite gives
`PYTHONPATH` the repository root when it starts Python, so that both tools can be started
in a temporary folder and name a file by the same relative path.

**Resolution.** `converter/tests/support.js`, `pythonFrom`, `python` and `runPython`;
`converter/tests/cli.test.js`, "the Python tool the suite compares with".

## Seed 06: The queue records of a run in a worktree

**Question.** The tasks were queued and run in a git worktree while another run used the
queue of the main checkout. The queue file is not tracked.

**Answer.** The worktree has its own `.codex/local-task-queue.md` and
`.codex/tactic/session.json`. Its records are numbered from Q-201, so that they can be
appended to the main checkout's queue, whose numbers are lower. The records have no
`TaskId` and no `TaskIdPacked`, as the records of the seeds before, because the task-id
script does not run on this Mac.

**Resolution.** `.codex/local-task-queue.md` of the worktree, records Q-201 to Q-210.

## Seed 06: When the reader of JSON finds a member named twice, and how deep Python reads

**Question.** The design refuses a member name "that is already there". The Python tool
finds a name given twice when the object ends, and a `NaN` when it reads it, so a text
with two defects gets the detail of the one Python meets first. The design's test of
depth compares both tools at 512 and 513 levels.

**Answer.** The reader keeps the names and values of an object as they come and checks
the names when the object ends, in the order of the text, so `{"a": 1, "a": NaN}` gets
`NaN is not a JSON value` and `{"a": {"b": 1, "b": 2}, "a": 3}` names `b`, as in the
Python tool. `NaN`, `Infinity` and `-Infinity` are refused where they stand.

Python 3.14 on this Mac reads arrays nested 100,000 deep and refuses a million. A text of
513 or 600 levels is `bad-json` in both tools here, because its top level is an array,
with another detail in each; the test compares the reason for these and the whole line
for texts of 512 levels and of a million.

**Resolution.** `converter/lib/strictjson.js`; `converter/tests/strictjson.test.js`.

## Seed 06: Six significant digits, where the rounding of JavaScript is not Python's

**Question.** The design writes the end of the media in a `bad-range` detail with
`toPrecision(6)` of the fraction as a `Number`. `toPrecision` takes a half at the last
digit upward, and Python's `format(x, ".6g")` takes it to the even digit: 123456.5 is
`123457` in JavaScript and `123456` in Python. A fraction of two numbers beyond 2 to the
power 53 is also not turned into the nearest `Number` by dividing two `Number`s.

**Answer.** `sixDigits` of `whole.js` does both by itself. It finds the floating-point
number nearest to the fraction, halves to the even one, from the two `BigInt`s; it takes
that number as the exact fraction it is and rounds it to six significant digits, halves to
the even digit; and it writes the digits in the form of Python's `g`. The suite compares
it with Python for 600 fractions from seeds, for halves at the sixth digit, and for
fractions beside a half of the floating-point grid.

**Resolution.** `converter/lib/whole.js`, `sixDigits`; `converter/tests/whole.test.js`.

## Seed 06: What the tests ask of reference.py, and test files the design does not list

**Question.** The design lists seven requests of `converter/tests/reference.py` and
fifteen test files. The tests need more of the Python side than the list has.

**Answer.** `reference.py` gets a request wherever a test needs a value only Python has;
the requests are named in its `REQUESTS`. With the second task these are: `check`, which
runs `check --format` of the Python tool on many files in one interpreter, each under the
name `case.json` or `case.odrg` in an empty folder, because a new Python for each of some
hundred texts would take most of the suite's time; `dumps`, the bytes of
`odrig.jsonframes.dumps`; `sixdigits`, Python's `format(x, ".6g")`; and `milliseconds`,
the seconds of the command line as the Python tool reads them. The tests of `whole.js`
are in a file of their own, `converter/tests/whole.test.js`.

**Resolution.** `converter/tests/reference.py`; `converter/tests/support.js`,
`pythonChecks`.

## Seed 06: A Gamma code too long for Python to print

**Question.** The value of a Gamma code has as many bits as the code has zero bits in
front, plus one, and the data of a record can hold a code of more than 200,000 bits. The
reference names the length of the run, g - 1, in the detail of `run-past-end`. Python
refuses to write a whole number of more than 4,300 digits as text: for a Gamma code of
more than about 14,000 bits the Python tool ends with a traceback, `ValueError: Exceeds
the limit (4300 digits) for integer string conversion`, and status 1.

**Answer.** The JavaScript decoder reads a Gamma code of up to 30 bits as a `Number` and a
longer one as a `BigInt`, and writes every digit. For a code of 14,000 bits and more it
gives `error: run-past-end: ...` with the whole number, where the Python tool gives its
traceback; the status is 1 in both. No encoder writes such a code: a run cannot be longer
than N, which is at most 65,534.

**Resolution.** `converter/lib/odrg.js`, `gamma` in `coded`;
`converter/tests/decode.test.js`, "codes are read whole before they are judged, and
padding is not looked at", which has codes of 40 and of 60 bits.

## Seed 06: What the DEFLATE decoder says, and what the tests of the decoders compare

**Question.** The design gives `inflateRaw` two reasons and leaves its details open, and
lists what the tests of the two decoders hold without saying how many files.

**Answer.** A stream that ends early is `truncated` with the sentence of the Python tool,
`the file ends inside the DEFLATE stream`, so the ODRG decoder passes it on as it is. A
stream that is not valid is `bad-deflate` with words of the decoder's own for each defect.

`inflate.test.js` compares the verdict with zlib's for 126 streams zlib makes of nine
inputs, at every level and with each of its strategies, each cut at every length and
damaged in every byte where it has 400 bytes or fewer, for 6,000 streams both damaged and
cut, for 3,000 inputs of noise, and for 27 streams with one defect each that the test
writes out bit by bit. `decode.test.js` compares the whole error line with the Python
tool's for 13,556 copies of the valid vectors: cut at every length, with a byte added,
and with every byte changed twice, where a vector has 420 bytes or fewer, and at 420
places from a seed where it has more. `reference.py` has the requests `inflate` and
`deflate` for this. `summary` of `cli/main.js` gives the lines of `check` for bytes, so
that these comparisons need no new program for each file.

**Resolution.** `converter/lib/inflate.js`; `converter/tests/inflate.test.js`,
`converter/tests/decode.test.js`; `converter/cli/main.js`, `summary`.

## Seed 06: The compressor gives the bytes of zlib 1.2.12, and what is still asked of it

**Question.** The design asks for zlib's method at level 9 and not for its bytes: the
sketch made for it gave zlib's bytes for one body of six. How closely does the
compressor of the library follow zlib, and what do the tests ask?

**Answer.** `converter/lib/deflate.js` follows zlib step for step, also where a choice
does not change what a decoder reads: position 0 of the input is never taken for the start
of a match, as in zlib, where 0 stands for "none"; among two symbols that appear equally
often the one whose tree is less deep is joined first; the code lengths are listed with
zlib's rules for the repeat symbols 16, 17 and 18; and a comparison that runs past the
end of the input meets zeros. The streams it writes for the six bodies of the design's
table, for the dense 60 x 60 clip of ten seconds, and for 403 inputs made from seeds
for this task, of up to 200,000 bytes, are the bytes zlib 1.2.12 writes at level 9 with
its default memory level, which is how the Python tool calls it:

| Body | Bytes | zlib 1.2.12, level 9 | `deflateRaw` |
|---|---:|---:|---:|
| Hello world, 60 x 6 | 17,715 | 1,122 | 1,122 |
| DVD bounce, 60 x 6 | 3,783 | 1,596 | 1,596 |
| Dense, 60 x 6, 2 s | 34,462 | 32,826 | 32,826 |
| Hello world, 60 x 60 | 19,356 | 1,194 | 1,194 |
| DVD bounce, 60 x 60 | 2,324 | 1,036 | 1,036 |
| Dense, 60 x 60, 1 s | 146,717 | 140,856 | 140,856 |
| Dense, 60 x 60, 10 s | 1,462,220 | 1,383,750 | 1,383,750, in 0.05 s |

The tests ask what Requirement 8 asks and no more: every stream is inflated by zlib and
by the library to its input with nothing left over, two runs give the same bytes, and a
stream is at most 5 percent larger than zlib's. They do not ask for zlib's bytes, because
another build of zlib, such as the one some Pythons carry in place of zlib 1.2, writes
other bytes; the test prints for each body whether the bytes are the same. One place
where the bytes can differ from zlib 1.2.12 is known: within the last 258 bytes of an
input longer than 65,274 bytes, zlib compares past the end of the input with bytes left
over from 32,768 bytes earlier, where this compressor meets zeros, so among two matches
that both reach the end of the input it can take another one.

`reference.py` has the request `encode`, which gives the uncompressed and the compressed
file of `odrig.odrg.encode` for an animation or for a generator of the Python tool and a
mapping file; the body is the file without its 16-byte header. Its request `deflate`
calls zlib with the default memory level, as the Python tool does.

**Resolution.** `converter/lib/deflate.js`; `converter/tests/deflate.test.js`;
`converter/tests/reference.py`, `encode` and `deflate`.

## Seed 06: The files of the JavaScript encoder beside the Python tool's

**Question.** Requirement 7 asks for identical uncompressed files and Requirement 8 for
compressed files within 5 percent. What do the two tools write for the tracked animations
and the dense clip?

**Answer.** The same bytes in every case that was run, compressed as well, with zlib
1.2.12 on the Python side:

| Source | Uncompressed, both tools | Compressed, JavaScript | Compressed, Python |
|---|---:|---:|---:|
| Hello world, 60 x 6 (`animations/hello.json`) | 17,731 | 1,138 | 1,138 |
| DVD bounce, 60 x 6 (`animations/dvd.json`) | 3,799 | 1,612 | 1,612 |
| Hello world, 60 x 60 | 19,372 | 1,210 | 1,210 |
| DVD bounce, 60 x 60 | 2,340 | 1,052 | 1,052 |
| Dense, 60 x 60, 2 s | 299,683 | 285,360 | 285,360 |
| Source of the vector `encoded.pal` | 202 | 184 | 184 |
| Source of the vector `encoded.rgb` | 169 | 78 | 78 |

The tests ask for identical uncompressed files and, for compressed ones, the same frame
records from the reference decoder and from the library's own, and a size within 5
percent; they print whether the compressed bytes are the same.

**Resolution.** `converter/tests/encode.test.js`; `converter/tests/deflate.test.js`,
"whole files, through the command line of both tools".

## Seed 06: Details of the encoder that the design leaves open

**Question.** The design names the functions of the encoder and not their shapes, and its
count of frame records is "the sum over the frames of `ceil(ms / 65535)`", where `ms` can
be a number of thirty digits.

**Answer.** A palette is one `Uint8Array` of three bytes for each colour, or null.
`hueOrder(r, g, b)` gives five whole numbers: the hue and the saturation each as a
numerator and a denominator, and the largest channel; two colours are compared by
cross-multiplying. The number of records of a frame is worked out without a division of
floating-point numbers: with the remainder for a `Number`, and in `BigInt`s for a longer
time, so `too-many-frames` names the count the Python tool names for a frame of 10 to the
power 30 ms. `bestRecord` keeps the codes of the form it chose and writes the record from
them; `codedRecord` writes one given form and refuses, as a mistake of the program and not
as a rejection, a form whose data is longer than the pixel buffer, as the Python function
does. `toBuffer` is offered beside the functions the task lists.

`reference.py` has two more requests: `forms`, the 64 coded records of
`odrig.odrg.coded_record` for a pair of pixel buffers with the record `best_record`
chooses, and `decode`, the frame records of `odrig.odrg.decode` with the SHA-256 of each
picture. The first lets a test compare every form of the search and not only the one that
wins; the second gives the frame records of the reference decoder, which `decode` on the
command line merges. `support.js` makes the 200 animations from seeds and has the
generators of the Python tool write their sources into a temporary folder.

**Resolution.** `converter/lib/odrg.js`; `converter/tests/reference.py`, `forms` and
`decode`; `converter/tests/support.js`, `animationFrom` and `generated`.

## Seed 06: The order of the first checks of pack, and what the library says of a source it was not given

**Question.** The design has `pack` on the command line read the mapping file, read the
show file, and then call `pack.begin`, which checks the mapping and then the show. The
Python tool reads and checks the mapping file before it reads the show file: a mapping
file that breaks a rule and a show file that is not there is `mapping-malformed` in the
Python tool and would be `show-missing` in that order. The library also packs from bytes
held in memory, where a source that is missing has no words of the operating system.

**Answer.** `cli/folder.js` reads the mapping file, checks it with the library's reader,
and only then reads the show file and calls `pack.begin`. The mapping is read twice; it is
a few hundred bytes. `pack.pack` of the library gives `file-missing` for a source that is
not among the bytes it was given, with the detail `X.json: the show names X.odrg and its
source is not there`; on the command line the detail is the operating system's, as in the
Python tool. An item of a show is `{id, file, cycle, seconds}` with null for what its kind
does not have, as the Python reader has it. A folder and a name are joined as Python's
`os.path.join` joins them, so an empty sources folder gives the name alone. The folders
above the output folder are made one by one, the topmost first, as Python's `os.makedirs`
makes them, so that a failure names the same path in both tools.

**Resolution.** `converter/cli/folder.js`; `converter/lib/pack.js`, `converter/lib/show.js`;
`converter/tests/pack.test.js`, "a mapping file that breaks a rule and a show file that is
not there" and "the output folder".

## Seed 06: How mapping files and shows are compared before import is there, and tables of command lines

**Question.** The design reads every mapping file "by both tools through `import`", and
`import` is added two tasks after the reader of mapping files. Its tables of shows and of
mapping files have some hundred entries, each a command line for both tools.

**Answer.** `mapping.test.js` compares the two readers themselves: `reference.py` gives
what `odrig.mapping.loads` returns or rejects, for the tracked files, for the made-up
files of `tests/core/support.py` and for 73 files of each kind that break a rule, and the
library must give the same kind, canvas, legs and counts of LEDs, or the same reason and
detail. It compares the two command lines through `pack`, the one subcommand that reads a
mapping file at this point: a file that breaks a rule gives the same error line, and a
file that is as the format says gives `size-mismatch` for a source of another canvas, whose
detail names the canvas of the mapping. The task that adds `import` reads mapping files
through `import` as well. `pack.test.js` compares the readers of show files in the same
way.

Where a table has many command lines, the Python side runs them in one Python, through
the request `run` of `reference.py`, which calls the command line of the Python tool once
for each, and the JavaScript side calls `main` of `cli/main.js` in the test's own program.
A few entries of every table are run once more as programs of their own, and the three
shows of Requirement 11, the output folder with paths from the folder the tool is started
in, and the usage errors always are. A new Python for each of 300 command lines would take
most of a minute.

`reference.py` has the requests `mappings`, `read_mappings`, `read_shows` and `run` for
this.

**Resolution.** `converter/tests/mapping.test.js`, `converter/tests/pack.test.js`;
`converter/tests/support.js`, `runPythonMany` and `runJsHere`.

## Seed 06: A request to reference.py that never came back, and how the tests now ask

**Question.** The design gives the Python side its input on standard input. In one run of
the whole suite, the twelfth or so, a request of `inflate.test.js` with 6,000 streams did
not come back: the Python program waited to read its standard input, and the test's
Node.js 26.5 waited, inside the call that starts a program and waits for it, for the
program to end. Neither moved for ten minutes; the suite has no time limit of its own. The
Python program was ended by its process number, and the test then failed.

**Answer.** The cause was not found: both sides were waiting on a pipe whose other end was
open, which points at Node.js or the system and not at the tests. The requests no longer
use a pipe for their data. `reference` of `support.js` writes the input into a file of a
temporary folder and names it, and a second file for the answer, on the command line of
`reference.py`, which reads the one and writes the other; the folder is removed after the
call. Every program the tests start, both tools and `reference.py`, is started without a
standard input and with a limit of ten minutes, after which it is ended and the test fails
with a message, so a program that stalls can no longer hold the suite. The whole suite ran
three times in a row after the change, 1,016 tests each time, in 22 seconds.

This was seen once and is recorded so that a second sighting is recognised: if a test
fails after ten minutes with "did not come to an end", it is this.

**Resolution.** `converter/tests/support.js`, `reference`, `runJs` and `runPython`;
`converter/tests/reference.py`, `main`.

## Seed 06: What importFrames takes and when it asks, for whoever hands it frames

**Question.** The design gives the shape of a source and of a frame. It leaves open what
happens with a time that is a `Number` with a fraction, with a GIF frame without a delay,
with a picture without pixels, and how many frames of a video are asked for when only a
part is wanted. The app of seed 09 hands the library its frames and has to know.

**Answer.** As the Python tool has it wherever the Python tool has the case:

- A time, and a delay, is a `Number` that is a safe integer, a `BigInt`, or `[n, d]` of two
  of these. A `Number` that is not whole, such as 33.3667, is refused as a mistake of the
  caller, with a `RangeError` and not with a rejection: the caller gives the fraction it
  has, for a timestamp in microseconds `[timestamp, 1000]`.
- A frame of a video without a `time`, or with null, is `unreadable-media`, "a frame has
  no presentation time". A frame of a GIF without a `delayMs`, or with null, counts as a
  delay of 0, which is 100 ms, as in the Python tool when the file records none.
- A frame of width or height 0 is `unreadable-media`, "a picture has no pixels", when it
  is handed over, whether it is on screen at a tick or not. Its pixels are looked at only
  when it is on screen at a tick.
- A frame of a video is complete when the next one has come, because it is on screen until
  then. So `importFrames` asks for one frame more than the part shows, and a fault of that
  frame, a missing time or a time that goes backwards, is reported, as in the Python tool,
  whose decoder runs one frame ahead in the same way. A frame of a GIF is complete by
  itself.
- When the part is covered, the iteration is left with `break`, so an iterator with a
  `return` method has it called, once, and is awaited when it is asynchronous. A source
  that is read to its end is not told to stop.
- A start or a duration that is negative or 0 is refused before the first frame is asked
  for.
- `fit.place(source, w, h, fit)` is the whole fitting of one source picture, for a caller
  that wants a still picture and no timeline.

**Resolution.** `converter/lib/timeline.js`, `converter/lib/fit.js`;
`converter/tests/timeline.test.js`, "importFrames takes frames from whoever has them".

## Seed 06: How fitting and the timeline are compared with the Python tool without a media file

**Question.** The task makes its frames in the tests and reads no media file, and the
Python tool's timing rules for video and GIF are inside the functions that open a file
with PyAV and Pillow. The design asks for a case on each side of 2 to the power 53.

**Answer.** `reference.py` has four requests. `rects` is `odrig.media.source_rect`.
`resample` lays a source picture over black and fits it, or fits a picture to a rectangle
it is given. `ticks` is `odrig.media.tick_pictures` on frames that have times only, and
reports which frame is at each tick, which frames were fitted and how many were asked
for. `timeline` runs `odrig.media.import_media` itself, with stand-ins in place of
`av.open` and `PIL.Image.open` that hand out made-up frames with a presentation time and
a time base, or a delay: everything after the decoder is the Python tool's own code, and
the test compares the JSON frames file byte for byte, the rejection with its detail, and
the number of frames asked for, for 700 videos and GIFs from seeds.

The border of the `Number` arithmetic is reached with a picture of 64 x 32,768 pixels
stretched to a canvas of 64 columns: 511 times the area passes 2 to the power 53 between
canvases of 32,832 and 32,833 rows. Both pictures are the Python tool's, the second
computed in `BigInt`s. A smaller picture cannot reach the border with values other than
black, because the area in the tool's units is 4 times the pixels of the canvas times the
pixels of the rectangle. The limit of 2 to the power 63 is met with a rectangle far larger
than its picture.

The floor of `whole.js` decides more than the bar on the left that the task names: the
last source pixel a slice covers is found with a ceiling, which is a floor of the negated
value, so a floor that rounds toward zero drops the pixel in which a slice ends. With such
a floor 38 tests fail, among them the one the task names.

**Resolution.** `converter/tests/reference.py`, `rects`, `resample`, `ticks` and
`timeline`; `converter/tests/fit.test.js`, `converter/tests/timeline.test.js`.

## Seed 06: Python crashing while it decodes a video for a comparison

**Question.** While the task that adds `import` was being done, macOS showed "Python quit
unexpectedly" 22 times in two minutes. Every report is a fault of memory (SIGSEGV) in a
Python whose parent is `node`, inside PyAV: `VideoStream.decode`, called from
`Packet.decode` in the generator of `InputContainer`. What asked Python to do that, and is
it the tests or the Python tool?

**Answer.** It is the Python tool's own `import`, on a video it cannot decode, and a probe
of this task gave it such videos. The probe was not part of the suite: to see whether the
two tools judge a broken file alike (the design's assumption A5), it wrote 480 cut and
damaged copies of four test videos and ran `python -m odrig import` on each, one program
after the other. Nothing ran at the same moment, no container was closed early and no
program was ended from outside.

The cause: for a file that is cut inside its header, PyAV 17.1.0 lists a video stream for
which it has no decoder: `container.streams.video[0].codec_context` is None.
`odrig/media.py` takes the first video stream and calls `container.decode(stream)`
(lines 207 and 211), and PyAV then follows the missing decoder without looking and ends
the whole program. 21 of the 480 copies are of this kind, and 21 of the reports have this
place; the other report is of the first run of the probe, in which one Python read all
copies. It was seen again once, on purpose, in a program that ends quietly: the file is
opened, has one stream of type video, its `codec_context` is None, and the first frame
asked of `container.decode` ends Python with signal 11.

To see it without a report on the screen, in the repository root:

```
.venv/bin/python -c "
from tests.converter import media_fixtures as f
f.write_video('build/whole.mp4', f.COLOURS)
open('build/cut.mp4', 'wb').write(open('build/whole.mp4', 'rb').read()[:993])
import av
print(av.open('build/cut.mp4').streams.video[0].codec_context)"
```

prints `None` (the folder `build/` must be there; the whole file has 1,529 bytes with
PyAV 17.1.0, and cuts at 993 to 1,070 bytes are of this kind). Then
`.venv/bin/python -m odrig import build/cut.mp4 build/out.json --mapping mapping/legs-2.json`
ends Python with the fault, and macOS shows its dialog. Whether a whole video in a codec
that PyAV's FFmpeg does not have is of this kind too was not tried; it would have the same
missing decoder.

The same probe found two more ways in which the Python tool ends without its error line,
with a traceback and status 1: a video whose metadata is not UTF-8 (3 of the 480 copies;
`UnicodeDecodeError` from `av.open`, which is not one of PyAV's own errors), and a GIF that
is cut short (298 of 970 cut and damaged copies of three GIFs; `IndexError` and
`struct.error` from Pillow, which `odrig/media.py` does not catch).

No file of `odrig/` changes in this seed (Requirement 18 criterion 8), so the Python tool
is as it was: this needs the owner, as a seed of its own. The mending is small:
`_video_frames` refuses a stream without a `codec_context` as `unreadable-media` and
catches `UnicodeDecodeError`, and `_gif_frames` catches `IndexError` and `struct.error`.
The JavaScript tool gives `unreadable-media` for all of these files.

What changed on the side of the tests, so that no test can do this to whoever sits at the
computer:

- The suite never gives the Python tool a cut or damaged video as a program of its own.
  Such files are imported by the JavaScript tool alone, which must end with a file or
  with `unreadable-media`.
- Where a test compares the two tools on a file that is no whole video, the Python side
  goes through `reference.py`, which looks at the streams of a video before it runs
  `import`, without decoding, and does not run it when the first video stream has no
  decoder; the test then gets no status and the reason.
- `reference.py` makes a fault of memory end it quietly, with the number of the signal as
  its status, by naming the C function `_exit` as the handler of the signal. The test that
  asked fails and says which signal it was.

**Resolution.** `converter/tests/reference.py`, `_quiet_faults`, `_undecodable_video` and
`_run`; `converter/tests/support.js`, `runPython` and `runPythonMany`;
`converter/tests/import.test.js`, "a damaged or cut media file ends the import with a
result or with unreadable-media, and never keeps it busy". Open for the owner: the three
faults of `odrig/media.py` named above.

## Seed 06: What the install of the two packages needs and leaves, with npm 12

**Question.** The design's assumption A1: the decoder program of `ffmpeg-static` 5.3.0
installs under npm 12 on this Mac and runs. Its facts V1 to V4 were read on the registry
and not tried.

**Answer.** A1 holds with one addition, and one fact is other than read.

- npm 12 runs no install script of a dependency unless `package.json` allows it. After
  `npm install --prefix converter` the package was there without its program, and npm
  said that the install script of `ffmpeg-static@5.3.0` was blocked.
  `converter/package.json` therefore has, beside the design's members,
  `"allowScripts": {"ffmpeg-static@5.3.0": true}`, written by
  `npm install-scripts approve ffmpeg-static` and pinned to the version. With it,
  `npm ci --prefix converter` fetches the program. The script was read first: it fetches
  `ffmpeg-darwin-arm64.gz`, a README and a licence from the release `b6.1.1` of the
  package's GitHub repository into the package's folder and makes the program executable,
  as fact V2 says. An npm older than 12 does not know the member and runs the script
  anyway.
- The program of that release for macOS on Apple Silicon is ffmpeg 6.0, not 6.1.1: its
  first line is `ffmpeg version 6.0 Copyright (c) 2000-2023 the FFmpeg developers`. It has
  45,568,216 bytes and the SHA-256
  `a90e3db6a3fd35f6074b013f948b1aa45b31c6375489d39e572bea3f18336584`, which
  `converter/ffmpeg.sha256` holds for `darwin-arm64`.
- 21 packages are installed for the two that are named: `ffmpeg-static` needs four for its
  install script, and those need others. `converter/node_modules/` has 45 MB.
- Outside the project folder the install wrote two things, found by listing the home
  folder, `~/Library/Caches`, `~/.npm` and `~/.cache` before and after:
  `~/Library/Caches/ffmpeg-static-nodejs`, new, 6 files of 19,255,699 bytes, the package's
  copy of what it fetched; and npm's own cache and log, `~/.npm/_cacache` and
  `~/.npm/_logs`, which were there. Nothing new is in the home folder itself or in
  `~/.cache`.
- The tool does not ask the package for the path of its program: the package gives the
  value of the environment variable `FFMPEG_BIN` in place of its own path when that is
  set (fact V4), which could be an ffmpeg of the system. `cli/video.js` takes the program
  at `converter/node_modules/ffmpeg-static/ffmpeg`, `ffmpeg.exe` on Windows, and nothing
  else. When the package's folder or the program is not there, `import` of a video ends
  with `decoder-missing`. `omggif` is loaded with `import()`.
- `decoder-missing` is checked after the mapping file, the name of the media file and
  that it is there, and before the start and the duration. Its detail names the package
  and the command with the folder the tool is in, `npm ci --prefix <folder>`.

**Resolution.** `converter/package.json`, `converter/package-lock.json`,
`converter/ffmpeg.sha256`; `converter/cli/video.js`, `program`;
`converter/tests/import.test.js`, "the packages" and "a tool without its packages".

## Seed 06: The decoder program as found: assumptions A2 to A5

**Question.** The design's assumptions about what ffmpeg writes and how it ends, to be
verified by the task that adds `import`.

**Answer.**

- **A2 holds.** The filter `showinfo` of ffmpeg 6.0 writes
  `config in time_base: 1/12800, frame_rate: 25/1` and for each frame a line with `n:`,
  `pts:` and `s:<w>x<h>`, the `pts` in that time base, which is the stream's. Two
  additions to the design's call: `-copyts`, without which ffmpeg counts the times from
  the start of the file and not as the file records them, and `file:` in front of the
  path, so that a name is never read as an address of another kind. After each frame line
  comes a line on colour, and the scaler writes lines of its own; the reader passes over
  both.
- **A3 holds.** A mov with `qtrle` and transparency comes out with its alpha: the pixels
  of the transparent half are `0 200 0 0`.
- **A4 holds, with no difference at all.** 55 imports of 15 videos, with each fit and with
  a part, give the bytes of the Python tool's file: mpeg4 in mp4 and mov, `qtrle`, H.264
  with frames that are stored out of order, 25, 29.97 and 60 frames a second, frames with
  gaps, a ramp of colours, a picture higher than wide, and sound beside the video. PyAV 17
  carries FFmpeg 8 and the package ffmpeg 6.0.
- **A5 holds; `-xerror` is not added.** A text file, an empty file and a file cut short
  end ffmpeg with status 1, or with all the frames the file still has. A file without a
  video stream makes it say `Stream map '0:v:0' matches no streams`, which the reader
  reports with the Python tool's words, `the file has no video stream`. With `-xerror`
  ffmpeg refused 43 of 480 cut and damaged copies of four videos that the Python tool
  reads, against 16 that it reads and the Python tool refuses without it; so it is left
  out.

The two tools do not always judge a file that is damaged alike, and nothing in this seed
makes them. Of the 480 copies of videos, 230 are refused by both and 203 give the same
file; 21 cannot be given to the Python tool at all (see "Python crashing while it decodes
a video for a comparison"); 16 are read by the JavaScript tool and refused by the Python
tool; on 3 the Python tool ends with a traceback; and 7 are read by both with other
pixels. Of 970 such copies of three GIFs, 501 are refused by both and 96 give the same
file; 70 are refused by the JavaScript tool and read by Pillow: files cut inside a later
frame, of which Pillow shows the frames before the cut, frames that reach beyond the
screen, and blocks the package does not know; on 298 the Python tool ends with a
traceback; 4 are read by both with other pixels, and 1 by the JavaScript tool alone. Both
tools read a GIF under the name `.mp4`, as a video, and both refuse a video under the name
`.gif`.

The reader holds at most 64 MB of frames that the library has not asked for yet and makes
the program wait meanwhile; the log is read all the time.

**Resolution.** `converter/cli/video.js`; `converter/tests/import.test.js`.

## Seed 06: GIF pictures as found (A6), and a damaged GIF that kept the package busy without end

**Question.** The design's assumption A6: for the GIFs of the Python suite and for GIFs
that stay out of Pillow's three corners, the pictures built from what `omggif` gives equal
Pillow's. And what does the package do with a file that is damaged?

**Answer.** A6 holds: 368 imports of 92 GIFs give the bytes of the Python tool's file. The
GIFs are those of the Python suite, one with a transparent index on every frame, one whose
later frames are smaller than the screen, one for each disposal from 0 to 3 with a
transparent index and the disposal named on every frame, 40 GIFs from seeds as Pillow
writes pictures of a few colours by itself, and 40 palette GIFs from seeds with a
transparent index and one disposal for all frames.

The package does not judge the codes of a frame's data. Three of 970 damaged copies kept
it busy without end: a code that the table does not have yet makes its table point
at itself. `cli/gif.js` therefore goes through the codes of a frame before the package
draws it, as the package reads them, and refuses data with a code the table does not
have, with a first code after a cleared table that is no colour, or that spells more or
fewer pixels than the frame has. Data that passes cannot keep the package busy, because
every entry of the table then points at an earlier one. The package still draws every
pixel; the reader of the design, which watches for the package's warning, stays as a
second look. The suite reads every cut and every changed byte of four GIFs, more than
3,000 files, in a program of its own with a limit of two minutes,
`converter/tests/gifs.js`.

A frame without a palette, which the package would draw from the wrong bytes, is
`unreadable-media` as well. A file that ends after its header and has no frame gives
`the file holds no picture`. The delay of a frame is the file's hundredths of a second
times 10.

**Resolution.** `converter/cli/gif.js`, `codeFault` and `frames`;
`converter/tests/import.test.js`, "the pictures of a GIF are built by the rules of the
format as browsers apply them" and "a damaged or cut media file ends the import with a
result or with unreadable-media, and never keeps it busy"; `converter/tests/gifs.js`.

## Seed 06: The media of the import tests, and what is not verified of import

**Question.** The task names the media of the import tests and leaves their making to the
requests `gif` and `video` of `reference.py`.

**Answer.** One request, `media`, writes them all into a temporary folder: the GIFs above
and fifteen videos, with `tests/converter/media_fixtures.py` where the Python suite has
the file and with PyAV directly for the others. A file that this build of PyAV cannot
write is left out and named; on this Mac none was. The JavaScript side imports in the
test's own program and the Python side in one Python, and five files are imported once
more by both tools as programs of their own.

Not verified: a rotation that a file records for display. The call has `-noautorotate`,
and no test file with a rotation was made, because PyAV writes none in a simple way. Not
verified either: a video of a real camera or phone, and anything on Windows or Linux.

**Resolution.** `converter/tests/reference.py`, `media`; `converter/tests/import.test.js`.

## Seed 06: The page of the Chrome test, as built

**Question.** The design has `page.js` import `/lib/index.js`, and has the test compare
the page's results with "what the same calls give in Node.js". A module that imports the
library at its top cannot post an error when the import fails: the script then does not
run at all, and the test would wait for its minute. And how are "the same calls" kept the
same?

**Answer.** `converter/tests/page/page.js` has one function, `work`, which is given the
library and the bytes of the source and does everything that is compared: it reads Hello
world, encodes it compressed and uncompressed, decodes both, imports three source pictures
it fills by a fixed rule as a GIF with each fit and as a video, and fits each picture to
three canvases with each fit. It uses nothing but the library and the language. In a page
the file loads the library with `import()` inside a `try`, fetches the source, calls
`work`, and posts the results, or the name and the message of the error; the test in
Node.js imports the same file and calls the same `work` with the library it imported
itself. The file imports nothing when it is loaded, and the page has the one script.
Bytes travel as base64, which the file writes itself.

The test asserts that the page was served every file of `converter/lib/`, so a module the
page did not load cannot go unnoticed. Chrome gets three arguments beside the design's:
`--use-mock-keychain` and `--password-store=basic`, so that a new profile does not ask
macOS for the keychain, and `--disable-breakpad`. Chrome is ended by the process number
the test started, and the profile folder is removed and checked to be gone.

It ran with Google Chrome 154.0.8037.98 on this Mac, without a window; the page reports
`HeadlessChrome/154.0.0.0`. Every result of the page equals Node's, and the two files
equal what `node converter/odrig.js encode` writes.

**Resolution.** `converter/tests/page/index.html`, `converter/tests/page/page.js`,
`converter/tests/browser.test.js`.

## Seed 06: The documents as written, and pages and tests the task does not list

**Question.** The design's table "Documents" lists seven documents and two test files, and
the task a third test file. Other pages pointed at sections of `docs/converter.md` that
moved, another test of the Python suite read that page, and the emulator's suite ran the
pack commands of its page with Python. What else changed, and what does a suite need now?

**Answer.**

- `docs/core.md`, `docs/format.md` and `docs/mapping.md` named `converter.md` for the
  generators, for the Python that runs `odrig.mapdoc`, and for the readers the core's suite
  compares with. They name `reference-converter.md` now, and the bench target of the core,
  which starts the Python tool, is said to use the reference converter. Nothing else of
  these pages changed.
- `tests/converter/test_generators.py` read the sizes of the dense clip in
  `docs/converter.md`. It reads them in `docs/reference-converter.md`, as Requirement 19
  criterion 7 asks of every test of the Python suite that read the page.
- The emulator's suite runs the commands of its page as they are written. Three of them
  are now `node converter/odrig.js pack`, so that suite needs Node.js 20 or later as
  `node`, and the page says so in its table of commands. Without it the test fails and
  says what is missing. It is not skipped: a skipped test would leave the commands of the
  page and its table of sizes unchecked. The sizes of that table are compared exactly now,
  not within 2 percent, because the converter gives them on every computer.
- `docs/firmware.md` says beside its pack command that it needs Node.js as `node`. The
  firmware tool installs a Node.js 20 of its own into its work folder, for WLED's build;
  that one is not on the path, and the tool is as it was.
- Hello world and DVD bounce are called test content on both pages, as the owner sees
  them: made to try the tools and the board, and not finished animations of the
  installation.
- `docs/converter.md` has what the design lists, and for the library also the calls with
  what goes in and what comes out, because the app of seed 09 is written against them.
  `docs/reference-converter.md` has, beside what the design lists, where the two tools are
  known to differ, and the three known faults of the Python tool on damaged media, with a
  pointer to the entry "Python crashing while it decodes a video for a comparison".
- "Conversion" in `docs/decisions.md` says that the library has been run in Chrome and not
  inside an app yet.

**Resolution.** `docs/converter.md`, `docs/reference-converter.md`, `README.md`,
`docs/emulator.md`, `docs/firmware.md`, `docs/reasons.md`, `docs/decisions.md`,
`docs/core.md`, `docs/format.md`, `docs/mapping.md`; `converter/tests/docs.test.js`;
`tests/converter/test_docs.py`, `tests/converter/test_generators.py`,
`tests/emulator/test_docs.py`, `tests/firmware/test_docs.py`.

## Seed 06: Which test checks which criterion, and the test that was missing

**Question.** The last task asks to read every acceptance criterion of Requirements 1 to
19 once more and to name, for each one a program can check, the test that checks it.

**Answer.** The tests are those of `converter/tests/`, named here by their file without
its ending and, where it helps, by the title of the test.

| Requirement | Checked by |
|---|---|
| 1, the two parts | `library`: criteria 3, 4 and 5 by "the library is made of its own files only" and "index.js offers every module of the library"; criteria 1, 2, 6 and 7 by "the tool is the library and a command line part that is built on it", which was missing and is added; criterion 8 by `cli`, "an old version of Node.js is refused"; criterion 9 by `browser`. |
| 2, the command line | `cli`: "the statuses", "the error line", "--help", "the parser", "the command line as a program", "reading and writing files"; criterion 8 also by `whole`, "fromDecimal reads a number from its digits", and `import`, "seconds on the command line are rounded ..."; criterion 11 by `encode` and `import`, "the same ... give the same ... on every run". |
| 3, reasons and messages | `library`, "the reasons are those of the Python tool"; the comparisons of whole error lines in `strictjson`, `jsonframes`, `decode`, `mapping`, `pack`, `timeline` and `import`; criterion 5 by `cli`, "reading and writing files"; criterion 7 by `cli`, "--help" and "the parser". |
| 4, strict JSON and JSON frames | `strictjson`, `jsonframes`; criterion 5 by "a file of 20 MB is read in under 10 seconds". |
| 5, the ODRG decoder | `decode`. |
| 6, a compressed body | `inflate`; criterion 4 by `decode`, with the vector `trailing-bytes.after-deflate`. |
| 7, the encoder | `encode`. |
| 8, compression | `deflate`; criterion 5 also by `browser`. |
| 9, decode and check | `decode`, and `cli`, "check tells the format from the name, and --format overrides it". |
| 10, mapping files | `mapping`, and `import`, "both command lines read a mapping file the same way, through import". |
| 11, shows and pack | `pack`. |
| 12, the timeline | `timeline`. |
| 13, fitting | `fit`. |
| 14, media on the command line | `import`; criterion 4 but for the rotation, see below. |
| 15, frames from whoever has them | `timeline`, "importFrames takes frames from whoever has them"; criterion 6 by the added test of `library`. |
| 16, the library in a page | `browser`. |
| 17, dependencies | `import`, "the packages" and "a tool without its packages"; criterion 4 by `library`; criterion 6 by `docs`. |
| 18, tests | criteria 2 and 5 by the added test of `library` and by `docs`; criterion 3 by the files named above; criterion 4 by `cli`, "the Python tool the suite compares with". |
| 19, documentation | `docs`, and `tests/converter/test_docs.py`, `tests/emulator/test_docs.py` and `tests/firmware/test_docs.py`. |

No program of the suite checks these:

- Requirement 1 criterion 9 asks for the same result in a web view "for every function".
  The page calls `jsonframes.loads` and `dumps`, `odrg.encode` and `decode`,
  `timeline.importFrames` and `fit.place`, which pass through every file of the library
  but not through every function by itself.
- Requirement 14 criterion 4, that a rotation recorded for display is not applied: the
  call has `-noautorotate`, and no test file with a rotation was made.
- Requirement 16 criterion 5, the test reported as skipped where there is no Chrome: on
  this Mac there is one, so the skipping was read and not seen.
- Requirement 18 criterion 6, no network connection: nothing of the suite opens one but
  the Chrome test, to `127.0.0.1`; no program proves it.
- Requirement 18 criteria 7 and 8 are checked by running the other suites and by
  `git diff` against the commit this seed started from, which shows no file of `odrig/`,
  `core/`, `emulator/`, `odrigctl/` or `firmware/`.
- Requirement 19 criterion 6: `docs` checks that the versions are named, not that they
  are the ones that were used.

**Resolution.** `converter/tests/library.test.js`, "the tool is the library and a command
line part that is built on it".

## Seed 06: The last check: what was run, and the suite of the firmware tool that was not

**Question.** Requirement 18 criterion 7 names four suites that need no board, among them
`python3 firmware/fw.py test`, and the last task runs them. The run that did the tasks of
this seed was told not to start the firmware tool, because another run was working with
the board through it.

**Answer.** Run after the last change, all passing:

| Command | Tests |
|---|---:|
| `npm test --prefix converter`, Node.js 26.5.0 | 1,286 |
| The same suite with Node.js 20.18.0, started as `node --test` in `converter/` | 1,286 |
| `.venv/bin/python -m unittest discover -s tests/converter -t .` | 616 |
| `make -C core test` | 246 |
| `python3 -m unittest discover -s tests/emulator -t .` | 328 |
| `python3 -m unittest tests.firmware.test_docs` | 12 |

The Node.js 20 is the one the firmware tool keeps in its work folder,
`build/firmware/venv/bin/node` of the main checkout, started by itself. Of the firmware
tool's suite only the last line was run: the one file of tests that reads
`docs/firmware.md`, by itself and without the tool. The rest of that suite was not run. No
file of `firmware/` changed in this seed, and no other test of that suite reads a file
this seed changed, so nothing of it should differ. The state of the seed is set to
completed with that one run open: whoever merges this seed runs
`python3 firmware/fw.py test` when the board is free.

The versions: macOS 26.5 (25F71) on Apple Silicon, npm 12.0.2, Chrome 154.0.8037.98,
Python 3.14.6 with zlib 1.2.12, PyAV 17.1.0 and Pillow 12.3.0, and ffmpeg 6.0 as the
decoder program. The suites ran in a second checkout of the repository, a git worktree,
with the environment variable `ODRIG_PYTHON` naming the Python of the main checkout's
`.venv`.

**Resolution.** `docs/converter.md`, "What is verified";
`project-seeds/06-p1-javascript-converter/state.json`.

## Seed 06: The pages for newcomers and their tests, once both seeds were on `master`

**Question.** Seed 06 and seed 10 were built side by side, each correct on its own branch.
Merged, the pages for newcomers, `AGENTS.md` and the folder `agent/`, still gave the Python
tool as the converter, and four tests failed: two of `tests/onboarding/test_entry.py`, one
of `tests/onboarding/test_start.py` and one of `tests/converter/test_docs.py`. Which
failure is the fault of a page and which of a test, and what do the tests of the pages
need to check a command that starts `node` or `npm`?

**Answer.**

- **The pages were out of date and are brought to the repository as it is.** `import`,
  `check` and `pack` are commands of `node converter/odrig.js`; the setup has Node.js 20 or
  later and `npm ci --prefix converter`; the suites to run gain
  `npm test --prefix converter`; the generators stay Python commands. Seed 06 is no longer
  under "What is coming", and the entry file links `docs/reference-converter.md`. The
  Python package has a name of its own in the vocabulary and among the parts of the
  project, the reference converter.
- **Two tests looked for a sentence in a document that no longer holds it, and now look
  where it is.** No document changed for them. "is verified on macOS" was a sentence of the
  Python tool's setup: `test_start.py` now reads what each tool's own page says, "Windows
  and Linux are supported by construction and not verified: nothing has been run there."
  in `docs/converter.md` and "It is verified on macOS with Python 3.14." in
  `docs/reference-converter.md`. "from a mapping file of either kind, a row-leg file or a
  column-leg file" and a command with `--mapping mapping/legs-20.json` belong to the
  generators and moved with them: `tests/converter/test_docs.py` reads both under
  "Generators" of `docs/reference-converter.md`, in a test of its own.
  `docs/converter.md` lost nothing true: its section "import" still gives the canvas for
  both kinds of mapping file and names the demo show of the target, and the test that
  asserted that still does.
- **The other tests of the pages follow the pages**: the parts of the project, the
  commands of the setup, of the suites and of the demo show, the setup shown for Windows,
  and the words of the vocabulary. The test that keeps what is planned in one place no
  longer counts "JavaScript" and seed 06 as planned. A new test asserts that no command of
  a page converts, checks or packs with the reference converter.
- **A command that starts the converter is put before the converter's own parser.**
  Node.js loads `converter/cli/version.js` and `converter/cli/arguments.js` and gives the
  arguments to `parse`; nothing of the command is run. So `tests/onboarding` now needs
  Node.js as `node`. Without it the test fails and says what is missing, as the suite of
  the emulator does; it is not skipped. Of `npm` the test takes the two commands of the
  pages and no other. The suite takes two seconds, not one.
- **Both pages were at their limit of 200 lines.** The getting-started page gives the two
  suites that need more in one block and shows the reply to `status` once, under "Check it
  without a screen", not twice. The animation guide lost words and no statement.
- **The walk-through follows the pages as rewritten.** The setup of the page now runs
  `npm ci --prefix converter` in the copy, so the packages land in the copy's
  `converter/node_modules`, inside the temporary folder. Five suites run, and that of the
  converter is judged by its counts, `fail 0` and a `pass` above 0, since it has no last
  line `OK`. npm and the package `ffmpeg-static` keep their caches in the user's account,
  as pip does; the walk-through leaves that as it is for anyone who follows the page. The
  caller's `ODRIG_PYTHON` is not passed on, so the suite of the converter compares with
  the Python of the copy.
- **The known fault.** The animation guide says that the `import` of the reference
  converter can end Python itself on a damaged or cut video, which is the first of the
  three faults of the entry "Seed 06: Python crashing while it decodes a video for a
  comparison", and that a fix is planned. That it is planned was said with the task of
  this change; no seed for it exists yet.
- **Windows.** The pages say what can be tried there today, the converter, the reference
  converter, the generators and their two suites, all written to run there and none run
  there, and that everything else waits for seed 11, whose Required Behavior 8 also has
  the suite of the converter run on Windows.

Run in a worktree after the change, all passing: `tests/onboarding`, `tests/walkthrough`,
`tests/converter`, `npm test --prefix converter`, `tests/emulator` and `make -C core test`.
Not run: `python3 firmware/fw.py test`, which needs the work folder `build/firmware/` that
a worktree does not have, and anything on Windows or Linux.

**Resolution.** `AGENTS.md`, `agent/README.md`, `agent/vocabulary.md`,
`agent/working-rules.md`, `agent/getting-started.md`, `agent/animation-guide.md`;
`tests/onboarding/support.py`, `_converter`, `_node` and `_npm`, and the tests of that
folder; `tests/walkthrough/test_fresh_copy.py`, `tests/walkthrough/support.py`;
`tests/converter/test_docs.py`, "the document of the reference has the generators for both
kinds and for the target".

## Seed 13: The bytes of whole files, compared once and not pinned

**Question.** The design asks for a test that a whole video and a whole GIF give the same
JSON frames bytes as "a copy of the expected output kept from before the change". The exact
pixel values of a decoded video depend on the build of the decoder, so bytes kept in the
repository would fail on another computer for a reason that has nothing to do with this
seed.

**Answer.** The comparison was made once, by running the tool of the commit before the seed
and the tool after task 3 on the same whole video and the same whole GIF: the two JSON
frames files are byte-identical for each. No bytes are pinned in a test. The existing import
tests, which recognise each frame by the nearest of the fixed colours, keep covering whole
files.

**Resolution.** Seed 13 `tasks.md`, task 3; the commit message of task 3 records the
comparison.

## Seed 13: Where the two tools differ on a damaged video

**Question.** The JavaScript converter's suite again gives the Python tool every cut and
damaged video it gives the JavaScript tool, 160 files. Do the two tools agree on them?

**Answer.** On 159 of 160. Where both refuse a file they give the same reason,
`unreadable-media`. One file is read by the JavaScript tool and refused by the Python tool:
`alpha.mov` with the byte at 1137 changed by 245. The two tools decode with different builds
of FFmpeg, and one recovers a picture where the other gives up. The file is named in the
table `KNOWN_DIFFERENCES` of the test, and a difference that is not in the table fails the
test. The Python tool ended every one of the 160 with status 0 or 1 and without a traceback,
and no crash report was written.

The made-up video of `converter/tests/reference.py` gained a `codec_context`, because the
Python tool now reads it before decoding.

**Resolution.** `converter/tests/import.test.js`, `KNOWN_DIFFERENCES` and the test of 80
cuts and 80 changed bytes; `converter/tests/reference.py`, without `_undecodable_video`.

## Seed 07: What seed 05 left, where this spec expected something else

**Question.** The spec of seed 07 was written while seed 05 was being implemented, from
the design of seed 05. Its tasks say: where the code differs, follow the code and record
the difference. What differs?

**Answer.** The code was read before the first task. The core, the emulator and the
command tool are as the design's table "What this design relies on" has them. Four things
differ, all on the board:

- The request for a refresh has a task of its own, `odrig`, on the chip's other processor
  core, and the core's lock is held for a whole request, 9 to 17 ms with a dense clip. The
  design names this as its risk 6. So a step of the check will run on that task, and the
  storage calls of a command on WLED's loop, for the port, and on the network task, for
  HTTP. The spike of task 3 measures the pacing in that arrangement.
- The port no longer feeds the core one byte at a time. It collects the bytes of a pass,
  at most 272, and hands them on at the end of a line or when the buffer is full, each
  hand-over under one hold of the lock. A line of 2,048 characters so reaches the core in
  eight or more pieces, which the core's byte entry joins.
- The owner has ruled, in seed 05, that any rate from 20 to 50 refreshes a second is fine
  on the board for any content. The session that coordinates this run passed the ruling on
  for this seed: where the seed and this spec ask for 25 or more during an upload and 49
  or more afterwards, the board tests assert 20 or more in both places, and the measured
  figures are written down as they are. Requirement 17 criteria 4 and 7 and Requirement 21
  criterion 3 are read that way from here on.
- This run works in a checkout of its own, beside the first one. The stock WLED files and
  the factory backup exist in the first checkout only. The tool of this checkout builds in
  its own `build/firmware/`; where a board test restores stock WLED, the stock files are
  read from the first checkout through a link that is removed afterwards, and nothing of
  that folder is copied or changed.

The session of the board suite, `tests/board/support.py`, has one line that must be too
long. It had 75 characters and gets 2,055 in the first task, with the limit, although the
board suite runs again only in task 3, when the firmware with the longer line is on the
board.

**Resolution.** `docs/specs/07-p1-content-commands/tasks.md`, tasks 3 and 7;
`tests/board/support.py`, `SESSION`.

## Seed 07: The byte entry without its two blocks, and where the blocks are taken

**Question.** The line and the reply of the byte entry leave the core object and become
two blocks taken at startup. The design does not say when, or what `odrig_core_feed` does
when the host could not supply them. A reply of 1,024 bytes cannot stand on the stack of
a function of the core, so without the blocks the entry has nowhere to put a line or a
reply.

**Answer.** The two blocks are the first the core asks for after its own object, before
the mapping is read: commands arrive whatever the show is, also when there is none. When
either is missing the show is invalid with `out-of-memory`, as for every later block,
`odrig_core_feed` takes no bytes and calls nothing, and `odrig_core_command`, which writes
into the caller's room, works as ever. So a host that could not give 3 KB answers over
HTTP and not over its serial port, and `status` says why. The numbers of the blocks in
the tests of a failing `alloc` move up by two.

A line is split into up to five words; a line with more is `bad-argument` for every
command, and `unknown-command` when its first word is no command, which comes first in
the order of the codes.

**Resolution.** `core/src/core.cpp`, `start`; `core/src/commands.cpp`, `Words` and
`odrig_core_feed`; `docs/core.md`, "Command lines" and "Memory";
`tests/core/test_memory.py`.

## Seed 07: The length in a log entry of a line that was cut

**Question.** A log entry of the emulator gets `length`, "the number of characters of the
line as the core read it". Of a line of more than 2,048 characters the core hands back
its first 2,048, and of a body of more than 4,096 bytes the emulator keeps 4,096.

**Answer.** `length` is the length of the line the core read: 2,048 for every line that
was cut, with `cut` true. The page shows such a line with its first 200 characters and
`more than 2048 characters`, and a shorter long line with its first 200 and its real
length.

**Resolution.** `emulator/hub.py`, `Hub.log`; `emulator/web/app.js`; `docs/emulator.md`,
"The page" and "The event stream".

## Seed 07: Queue and session files in a checkout of its own

**Question.** The run works in a checkout of its own. Where do the queue and the session
state go, and how are the records numbered?

**Answer.** Into `.codex/` of that checkout, which git ignores: the queue records Q-401
to Q-409, one for each task of this spec, without task ids, because the script that makes
them does not run on this Mac, and the session state in `.codex/tactic/session.json`. No
branch is pushed: there is no remote.

**Resolution.** `.codex/local-task-queue.md` and `.codex/tactic/session.json` of the
checkout, untracked.

## Seed 07: What the test host has beyond the design's list, and what it takes for misuse

**Question.** The design lists six options for the test host and the misuses it stops. It
asks for `space` to be tested "with a host that cannot tell", and for a host whose
`write_open` is `NULL` while `space` answers, and has no option for either. It says each
new check is "shown to stop the test host", and the core never does what the checks
stop, so no session can show it. The header lets a host give up a file that is being
written when `write_open` is called again, while Requirement 19 has the test host stop
when the core "has two files being written".

**Answer.** Two options more: `--space-unknown`, with which `space` returns -1, and
`--only-space`, with which only `space` of the seven is there. `--no-storage` makes all
seven `NULL`, as the design says. Nine invocations more, `odrig_host guard write`,
`write-none`, `close-none`, `two-files`, `name`, `rename-open`, `remove-open`, `read-at`
and `read-at-offset`, each of which uses the storage functions as the core never may and
is stopped with `file misuse`. A second `write_open` while a file is being written is
misuse for the test host: the core removes or closes a file before it begins another, and
a host only has to cope with the other case. `read_at` may always start again at
offset 0, which is how the core begins the check of every upload. The name check covers
`open` too, in sessions.

**Resolution.** `tests/core/host/host.cpp`; `docs/core.md`, "The test host";
`tests/core/test_content.py`, `StorageGuards`.

## Seed 07: Where `space` and the reply live in the core, and what `storage-error` says for now

**Question.** The design puts `space` into `content.cpp`, which its task list creates
only in task 4, and leaves the `Reply` in `commands.cpp`, where `content.cpp` cannot
reach it. `docs/commands.md` is to list only what exists, and the design's sentence for
`storage-error` speaks of a show and of an upload.

**Answer.** `content.cpp` begins in task 2 with `space`. The `Reply`, with `succeed` and
`refuse`, moves to `commands.h`, so that `content.cpp` and later `upload.cpp` write
replies with the same code. `storage.h` holds the three names the core keeps for itself
and the question whether the host's storage can be changed. Until the commands that
write exist, `docs/commands.md` gives `storage-error` as what `space` is answered with on
a board that cannot tell its space, and the test of the command tool that compares the
tool's commands with the document says that `space` is in the document and not yet in
the tool.

**Resolution.** `core/src/content.cpp`, `commands.h`, `storage.h`; `docs/commands.md`,
"Error codes"; `tests/emulator/test_tool.py`,
`test_the_commands_are_those_of_the_commands_document`.

## Seed 07: The emulator's host: which names it takes, and a host object without storage

**Question.** The emulator "refuses a name with a path separator" and uses a name "only
when it is one the core may use". A test of seed 03 forbids the emulator to write out the
name `show.json`, so it cannot list the core's names. The binding is also used with host
objects that only read.

**Answer.** `FolderHost` takes a name of 1 to 32 characters of `a`-`z`, `0`-`9`, `-`, `_`
and `.` that is not made of dots alone, and refuses every other: such a name has no
separator and cannot leave the folder. The binding gives the core the seven storage
functions when the host object has `write_open`, and seven null pointers otherwise.
`FolderHost.close` stays what the core calls to close the open file; `release` closes
every file the host holds, at the end of the program.

**Resolution.** `emulator/host.py`; `emulator/binding.py`, `Core.__init__`;
`docs/emulator.md`, "Starting".

## Seed 07: The board cannot tell its space quickly, so the usermod keeps the number

**Question.** The design assumed, as B5, that the file system tells its used bytes in
under 100 ms with storage nearly full, and named what to do otherwise. The spike measured
30 ms with the example show, 79 ms with one dense clip of 1.4 MB and 377 ms with 9 MB.
The player waits for the same lock for that long.

**Answer.** The design's other way is taken. The usermod asks the file system once,
before the core starts, and keeps the number of used blocks up by what its storage
functions write, replace and remove: no block for a file of 512 bytes or less, which the
file system keeps beside the name, and for a longer file the blocks of 4,096 bytes that
the file system needs for it, the pointers at the start of each block counted. `space`
is answered from that number with no call to the file system, in every state of the
board. The number is an account, not a measurement: it leaves out the blocks the file
system takes for its own lists as a folder grows. The board test allows 16,384 bytes
between the number kept and the number after a restart, and the spec has the core keep a
reserve of that size when it judges whether an upload fits. Every start takes the number
afresh.

A client sees nothing else than the design describes: `free` in whole blocks. On the
board `free` after an upload or a removal can differ by a few blocks from what the same
command reports after the next start.

**Resolution.** `firmware/usermod/odrig_files.cpp`, `askSpace`, `blocksOf` and
`tellSpace`; `docs/firmware.md`, "What the firmware does", "Storage", and B5 in "Verified
on the board"; `tests/firmware/test_usermod_files.py`; `tests/board/test_upload.py`,
`test_the_space_is_told_without_a_storage_call_and_follows_what_is_written_and_removed`;
`tests/board/test_measure.py`, `space_us`.

## Seed 07: How the pacing counts, and the rates it was measured with

**Question.** The design holds command lines after a storage call for the longer of 20 ms
and twice the call's time. A command makes several storage calls in a row, and the spike
found a write of 1,500 bytes slower than the design assumed: 31 ms in the mean and 152 ms
at the longest, where the design expected a few milliseconds and some tens for one in
three. The design asked for 25 refreshes a second or more during the writes, and for the
writes to move to a task of their own if that failed.

**Answer.** The times of the storage calls are added up until a hold has run out, and the
hold is the longer of 20 ms and twice that sum, counted from the end of the last call. So
a command that makes five calls is followed by one hold for all five. A read through
`read_at` is not counted: the check of an upload reads inside the player's own request
for a refresh. A command over HTTP waits in the network task before it takes the lock.

With that pacing the board sent 34 to 46 refreshes in every second while a megabyte was
written, and 50 in each of the ten seconds after. With the pacing taken out it sent 10 or
11. The owner accepts every rate from 20 to 50 on the board, so the writes stay where
they are, and the board tests assert 20 or more during an upload and after it, where the
spec has 25 and 49. The figures measured are in `docs/firmware.md`.

Not tried: writes while a dense 60 x 60 clip plays. A storage call stops the player for
as long as it takes, and the player then decodes every frame that came due meanwhile in
one request, so a rate below 20 in the second of a long call is possible there.

**Resolution.** `firmware/usermod/odrig_files.cpp`, `Timed` and `holding`;
`odrig_serial.cpp`, `poll`; `odrig_usermod.cpp`, `commandLine`; `docs/firmware.md`,
"Storage calls are paced" and B3; `tests/board/test_upload.py`, `LOWEST`;
`tests/firmware/test_usermod_files.py`, `Pacing`.

## Seed 07: What the probe build gained for the spike

**Question.** The design gives the probe build a `store` object in its report and says
that the spike writes a megabyte through the usermod's storage functions "from a probe
command". It does not say what that command is, or what `check_steps` counts before the
core has a check.

**Answer.** The probe build answers a second line, `#store <bytes>`, as it answers
`#probe`: on the port only, at the start of a line, and without the core seeing it. It
writes, renames, reads back and removes a file of its own in `/odrig`, `probe.part` and
`probe.odrg`, a step in each pass of the loop that the pacing allows, and answers with
one line of times. The firmware itself has no such line. A file named `probe.odrg` or
`probe.part` in a show would be overwritten by the trial; no show of the repository has
one. The report gains `space_us`, the time the file system took to tell its space at the
start, beside `store`. `check_steps` counts the requests for a refresh during which a
second file was read by anyone, so the trial's own read-back shows up in it; with the
core's check it is the number of steps of the check.

**Resolution.** `firmware/usermod/odrig_probe.cpp`, `storeStep`, `fitOf` and `report`;
`docs/firmware.md`, "The probe build"; `tests/board/test_upload.py`, `Spike`.

## Seed 07: The board tests keep the port open and send one line at a time

**Question.** The board tests sent each command through the command tool, which opens
the port, waits and closes it for every line. The spike has to ask for a report once a
second while a trial runs. The first run of the whole suite also failed in two tests
after a test had written two lines of 2,048 characters in one piece: 4,098 bytes do not
fit the port's queue of 4,096, and the rest of the second line stayed in the core's line
until the next test's first command, which was then answered with `line-too-long`.

**Answer.** `tests/board/support.py` gains `Port`, the port kept open for several
exchanges, opened as the command tool opens it. It sends one newline when it opens and
discards what arrives, so that a line a test before it left unfinished ends there. The
tests send one line and wait for its reply before the next, as the command tool does;
the design's B4 is one line in one piece, and that is what is tried.

The board suite also needs the stock files of `firmware/wled-16.0.1/`, which exist in
the main checkout only. In another checkout the suite's test of `restore-stock` has no
files to compare with; for this seed's runs a link to the main checkout's folder stood
in the worktree, untracked, and was removed afterwards.

**Resolution.** `tests/board/support.py`, `Port`; `tests/board/test_upload.py`,
`test_a_line_of_2048_characters_in_one_piece_is_read_and_one_of_2049_is_too_long`;
`docs/firmware.md`, B4.

## Seed 07: What the documents say of the show before the upload exists

**Question.** Task 4 puts "the texts of the design" into `docs/show.md` and `busy` and
`in-use` into `docs/commands.md`. Those texts speak of the upload: a new item, a file
replaced, `busy` while an upload is open. The upload is task 5, and a document lists only
what exists. The design's example of a written `show.json` also has a cycle that lists
id 2 while no item has that id, which is not a valid show.

**Answer.** With task 4 `docs/show.md` has the design's texts as far as they hold with
`remove` alone: "Changing a show while it runs" speaks of `remove`, and the sentences on
uploads, on a new item and on the room for one are added with task 5. `docs/commands.md`
gets `list`, `remove` and `in-use`; `busy` comes with task 5, when something can be busy.
The example of a written `show.json` is a valid show: items 1 and 2 and a cycle 4 that
lists them, with `start`. Task 8 compares both pages with the design word for word.

**Resolution.** `docs/show.md`, "Changing a show while it runs" and "show.json after a
change"; `docs/commands.md`, "Storage and the installed items" and "Removing an item";
`tests/core/test_docs.py`.

## Seed 07: What a removal leaves when storage fails half-way

**Question.** The design gives the sequence of a removal: `pending.txt` with the file's
name, `show.part`, the rename onto `show.json`, the file removed, `pending.txt` removed.
It says what a power cut leaves. It does not say what the core does when a call fails
after the rename, or what the start does with a `pending.txt` whose file cannot be
removed or that cannot be read.

**Answer.** Up to the rename a failure undoes the command: `show.part` and `pending.txt`
are removed, the show in memory is unchanged, and the reply is `storage-error`. From the
rename on the command has succeeded, whatever follows: the show in storage is the new
one, so the reply is `{"ok":true}`. If the file then cannot be removed, `pending.txt`
stays, and the next start removes the file. At the start, `pending.txt` is removed only
when every file it names is gone or is named by an item; if a removal fails or the file
cannot be read, it stays for the start after. A line of `pending.txt` that is not a file
name is skipped, and so is a last line without a line feed, which is what a power cut
during the write leaves.

**Resolution.** `core/src/storage.cpp`, `storage_remove_item` and
`storage_settle_pending`; `docs/core.md`, "The files the core writes";
`tests/core/test_powercut.py`, `Removal`; `tests/core/test_startup.py`, `Leftovers`.

## Seed 07: The empty show in the converter, and the test of the tool's commands

**Question.** Task 4 changes `odrig/show.py` for a show without items, "and
`converter/lib/show.js` if it is there". It also adds commands to `docs/commands.md`
that the command tool gets only in task 6, while a test of the tool holds the tool's
commands and the document's to be the same.

**Answer.** This branch has no `converter/` folder, so only the Python reader changes;
the JavaScript converter of the main line needs the same change when the two are merged:
a show with `"items":[]` is valid. The tool's test says, until task 6, which commands
the document has that the tool does not send yet.

**Resolution.** `odrig/show.py`; `tests/converter/test_show_pack.py`;
`tests/emulator/test_tool.py`, `test_the_commands_are_those_of_the_commands_document`.

## Seed 07: The check stands still while the player is late

**Question.** The design gives the check of an uploaded file one step after a refresh
that came in step: on the grid slot right after the one before. That keeps the check
from taking time the player needs. It does not say what follows when no refresh is in
step for a long time, which is the case when content plays at 25 refreshes a second or
fewer: every refresh is then a slot late.

**Answer.** It is built as designed, and what follows is this. A step of the check is
what counts as progress of an upload in the checking state. With no step for 60 seconds
the upload is discarded like any other on which nothing moved, and the next `upload end`
is answered with `no-upload`. A client sees `busy` for up to a minute and then
`no-upload`. At rates between 25 and 50 the check runs, slower the more refreshes are
late: a step for every refresh that follows another without a gap.

On the board this matters for a show whose content is dense enough to play below 50: the
dense 60 x 60 clip plays at 28 to 37 compressed. An upload while such content plays is
checked slowly, and at 25 or fewer not at all. `off`, or playing an item that keeps the
rate at 50, lets the check run at full speed: one frame of the file for each refresh.
The owner should see this before the event; a change, such as a step for every refresh
when the last step is more than a second old, would change the design and is not made
here.

**Resolution.** `core/src/player.cpp`, `in_step`; `core/src/upload.cpp`, `upload_step`
and `upload_touch`; `docs/core.md`, "Uploads and the check"; `tests/core/test_upload.py`,
`TheCheck`.

## Seed 07: The codes of a file that storage gave back wrong

**Question.** The check reads the uploaded file back from storage. The design answers a
file that is not valid with `bad-file` and storage that failed with `storage-error`. It
does not say which of the two a file gets whose bytes, read back, are not the bytes that
were received.

**Answer.** The check decodes what it reads back and, at the end, compares the number of
bytes and their CRC-32 with what was received. A read that fails is `storage-error`.
Bytes that differ and still decode are `storage-error`, found at the end. Bytes that
differ and do not decode are `bad-file` with the decoder's reason, because the decoder
meets them first; `bad-file` is also the earlier of the two in the order of the codes.
The upload is discarded in all three cases. The test host gets two options for these
cases beyond the design's list: `--read-back-fails OFFSET`, from which on `read_at`
answers -1, and `--read-back-differs OFFSET`, the place of one byte that `read_at` gives
back with one bit changed.

**Resolution.** `core/src/upload.cpp`, `upload_step` and `upload_end`;
`tests/core/host/host.cpp`; `docs/core.md`, "The test host"; `tests/core/test_upload.py`.

## Seed 07: What the reference player and the emulator needed for the upload

**Question.** The reference player counts the check in refreshes, so it has to know
after how many steps the core's decoder refuses a damaged file; the converter's decoder,
which the reference player uses, refuses a file as a whole. The emulator tells the core
the space of its folder from the sizes of the files, while Python keeps written bytes in
a buffer of its own.

**Answer.** For a file whose body is refused, a test tells the reference player how many
frame records decode before the refused one, by the CRC-32 of the file; without that it
takes the number the header names. The check then ends two steps later, as for a sound
file: one step for the header and one for the end. The emulator's host opens the file it
writes without a buffer, so that every piece is in the folder when the core has given
it, and `space` during an upload counts it.

**Resolution.** `tests/core/support.py`, `ReferencePlayer.sound_records`;
`emulator/host.py`, `write_open`; `tests/emulator/test_content.py`, `Uploads`.

## Seed 07: When the command tool writes a progress line

**Question.** The design has the tool write progress "one line for each report", and
calls `progress` after every acknowledged piece; Requirement 18.5 asks for a line "at
least once a second, and a last time when the data is sent". Over USB a piece is
acknowledged nine times a second, so a line for every piece is 900 lines for a file of
1.4 MB when standard error is a file or a pipe.

**Answer.** `odrigctl.content.upload` calls `progress` after every acknowledged piece, as
designed, and the board tests use that. The command line writes a report when half a
second has passed since the one before, and always for the last piece, so a small file
gives one line with 100%. The speed in a line is whole bytes a second, rounded, and 0
when no time has passed. On a terminal the one line is written over again and ended
before the reply is printed.

**Resolution.** `odrigctl/cli.py`, `Progress`; `docs/emulator.md`, "The command tool";
`tests/emulator/test_tool.py`, `ProgressLines`.

## Seed 07: What the tool's session does with a reply that comes late

**Question.** Through the port the replies carry no mark of the line they answer; the
session takes the next reply for the answer. The design has the tool send an
`upload data` line once more when no reply came in time. If the first reply was only
late, two replies are then on their way for one piece, and the second would be taken for
the answer of the next piece.

**Answer.** Two rules in the session, for the port only. A line that arrived whole before
a line is sent is no answer to it and is dropped; the beginning of a line that has not
ended is kept and judged with its end. And after a second `upload data` line that was
answered with anything but `bad-offset`, the tool drops what arrives in the next half
second. A reply later than that still ends the upload with `bad-offset`, a cancel and
status 1; the upload can be sent again. Over HTTP a late reply belongs to a request that
was closed and is never seen.

Only an `upload data` line is sent twice. Without a reply to `upload begin`, to
`upload end` or to a line of another command the tool exits with status 3 and sends no
cancel: it cannot reach the target. An upload left open so is discarded by the target
after 60 seconds, and after a lost reply to `upload end` the file may be installed all
the same; `list` tells.

**Resolution.** `odrigctl/client.py`, `Session.exchange` and `Session.discard`;
`odrigctl/content.py`, `upload`; `docs/emulator.md`, "The command tool";
`tests/emulator/test_tool.py`, `LostReply` and `SessionOfExchanges`.

## Seed 07: When the tool cancels an upload

**Question.** Requirement 18.7 has the tool send `upload cancel` after a reply that is
not ok "when an upload it opened may still be open". It does not say after which replies
that is.

**Answer.** After a refused `upload begin` the tool sends no cancel: it opened nothing,
and with `busy` the open upload is another sender's. After a reply to a piece or to
`upload end` that is not ok it sends `upload cancel`, unless the code is one after which
the target holds no upload: `no-upload`, `bad-checksum`, `bad-file`, `storage-error` or
`show-invalid`. So a cancel follows `bad-offset`, `bad-argument`, `incomplete`, and
`busy` after 600 seconds. The reply to the cancel is not printed and does not change the
status.

Beside what the design names, `cli.checked` gives the command and its arguments after
their number is checked, and every command, also the five of before, goes through a
`Session`.

**Resolution.** `odrigctl/content.py`, `GONE` and `_given_up`; `odrigctl/cli.py`;
`tests/emulator/test_tool.py`, `UploadSteps` and
`test_an_upload_that_is_refused_at_its_begin_cancels_nothing`.

## Seed 07: An upload while dense content plays

**Question.** The spec measures the rate during an upload with the bench show playing,
which plays at 50 refreshes a second with room to spare. At the event the board plays
60 x 60 content, and a dense clip already plays below 50. Nothing in the spec says what
an upload does there.

**Answer.** It was tried once, outside the suite, with the firmware and the dense
60 x 60 clip playing compressed on the target file, 40 to 42 refreshes a second before
the upload. Every upload succeeded. While the data of a file of 285,360 bytes arrived,
`status` reported 16 to 27, below 20 in 13 of the 60 seconds, and the file arrived at
4,714 bytes a second, where the bench show gives 12,583. Its check of 100 frames took 17
seconds at 25 to 29 refreshes a second. In the second in which a file was put in place,
`status` reported 6 or 7. So an upload while dense content plays can take the board
below the 20 the owner accepts, for as long as the data arrives.

Nothing is changed for it: the pacing is the design's, and a longer hold would make the
upload slower still. What an operator can do today is to send `off`, or to play an item
that is not dense, for the time of an upload; the app of seed 09 could do that by
itself. Whether the board should do more, such as a longer hold while the rate is low,
is the owner's to decide and would be a seed of its own.

**Resolution.** `docs/firmware.md`, "Measurements on the board", "An upload over USB";
no code.

## Seed 07: What the board tests of the upload run on, and what they compare

**Question.** Task 7 asks for one session on the board with the command tool, for the
rate during an upload of a dense bench clip of 60 seconds with the probe's figures, for
`read-show` to give "the folder as it was at the start", and for the replies to equal an
emulator's "apart from `fps` and `free`".

**Answer.** The session runs on the firmware, the image the board is left with, and
the large upload on the probe build, whose report has the storage calls. Both assert 20
refreshes a second or more where the spec has 25 and 49, by the owner's ruling. The
session ends with three refusals, so that `in-use` and `unknown-id` are met on the board
too. After it, the folder read back from the board has the files that were installed,
with `show.json` as the core writes it: one line, the same show. It is byte for byte the
folder the emulator has after the same session, and that is what the test compares, so a
board that wrote a show file of its own kind would be seen. The suite's cache of what it
installed is cleared whenever commands changed the show, so that the next test asks the
board. The last step of the suite now also asks `list`, `status` and `space`, for the
three items of the example show and nothing else.

**Resolution.** `tests/board/test_upload.py`, `ContentCommands` and `DenseUpload`;
`tests/board/support.py`, `content_session`, `measured_upload`, `changed_by_commands`
and `read_back`; `tests/board/__init__.py`, `LeaveTheBoard`.

## Seed 07: The test over the air, and how it was run without the air

**Question.** Task 7 asks for "the same session over HTTP" in `tests/air/`, which no
agent can run, and to run its session against the emulator. The session of the board
test restarts the board, and a restart takes the board's network away from the computer
that joined it.

**Answer.** The test over the air sends the same session without the restart, once over
HTTP and once through the port, and holds the replies to be the same, as the suite's
other tests do. A second test uploads the dense bench clip of ten seconds over HTTP,
asks `status` once a second, asserts 20 or more, and writes the speed to
`build/firmware/out/upload-air.json`: the first figure for an upload over Wi-Fi will
come from the owner's run. Both were run with an emulator in the place of the board's
network: the suite was given the address of an emulator started on the dim example show,
with the board on USB, so the HTTP half of each test spoke to the emulator and the port
half to the board. Both passed so. That says the session and the comparison are sound;
it says nothing of the board's web server with lines of 2,048 characters, which only the
owner's check can show.

**Resolution.** `tests/air/test_upload.py`; `docs/firmware.md`, "test-air" and step 7 of
"The owner's checks".

## Seed 07: The last check: what the documents were compared with, and the tests added

**Question.** Task 8 compares `docs/commands.md` and `docs/show.md` with the design word
for word, reads every acceptance criterion once more, and adds a test where a program can
check a criterion and none did.

**Answer.** `docs/commands.md` is the design's text, byte for byte. `docs/show.md` has
the design's four texts word for word, apart from the example of a written `show.json`,
which the design gives with a cycle that lists an id no item has; the page has a valid
show there, as recorded with task 4. No other difference was found, so nothing else was
settled.

Six criteria had no test and got one:

- 13.5, no array above 256 bytes in a function of the core: a scan of the sources,
  beside the compiler's limit of 512 bytes for a frame and the assertion that holds the
  core object to 4,096 bytes.
- 15.1, no host looks into a line: the emulator's sources also hold none of the words
  `list` and `upload` and none of the core's three file names; `space` and `remove` are
  allowed in the binding alone, where they are members of the host record.
- 16.4, the emulator's host refuses a name that is no file name of the folder: now also
  for the five storage methods that take a name.
- 20.5 and 21.2, `docs/firmware.md` has the storage functions, the pacing, the probe's
  members and the measured upload.
- 20.6, `docs/reasons.md` no longer lists a show without items as malformed.
- 20.7, `docs/decisions.md` lists the commands and the two limits.

What no program checks: 14.4 as far as it is the file system's own promise for a power
cut during a rename, which no task tries on the board; 14.6, which holds because no host
function calls the core, and is seen in the traces of the storage calls; and 21.5 and
21.6, the owner's check.

The first table of "Measurements on the board" was taken again with the firmware as it
is now: the core asks for more memory at its start, so less of the chip's internal
memory is free, and every start takes a little longer.

**Resolution.** `tests/core/test_build.py`,
`test_no_function_has_an_array_above_256_bytes`; `tests/emulator/test_scope.py`;
`tests/emulator/test_binding.py`,
`test_the_storage_methods_refuse_every_name_that_is_not_a_file_name_of_the_folder`;
`tests/firmware/test_docs.py`,
`test_it_says_what_the_firmware_writes_how_it_paces_and_what_an_upload_measured`;
`tests/core/test_docs.py`, `Decisions` and
`test_a_show_without_items_is_not_listed_as_malformed`; `docs/decisions.md`, "Commands"
and the change log; `docs/firmware.md`, "Measurements on the board".

## Seed 07: The owner's check is open

**Question.** Task 9 is the upload over the board's Wi-Fi: a phone or a computer joined
to the board's network. No agent joins that network, and this run was told not to join
it and not to change a Wi-Fi setting.

**Answer.** The task stays open, its checkbox unticked, and the seed stays `in_progress`.
Under the task, `tasks.md` has what a program established over USB: the command tool
uploads Hello world to the board, lists it, plays it and removes it, by hand and in the
board suite with a restart in it, with the replies the emulator gives; and the test over
the air passes with an emulator in the place of the board's network. What remains is
step 7 of "The owner's checks" in `docs/firmware.md`, and
`python3 firmware/fw.py test-air --http 4.3.2.1` with this Mac joined to the board's
network. Two things only that run can show: that the board's web server carries a line
of 2,048 characters, which is what an `upload data` line is, and the speed of an upload
over Wi-Fi. When both pass, the owner sets the seed to `completed`.

**Resolution.** `docs/specs/07-p1-content-commands/tasks.md`, task 9; `docs/firmware.md`,
"The owner's checks", step 7; `project-seeds/07-p1-content-commands/state.json` is not
changed.

## Merging seed 07: a show without items, and the JavaScript converter

**Question.** Seed 06 and seed 07 were done at the same time, each from a `master` that
did not have the other. Seed 07 made a show without items valid and took the rule out of
the Python reader. The JavaScript converter of seed 06 still refused such a show as
`show-malformed`. After the merge the two tools disagreed, and eight tests of
`npm test --prefix converter` failed. Is that a new seed, or part of the merge?

**Answer.** Part of the merge. `master` is not pushed with a failing suite, and the rule
is one line. The JavaScript reader accepts a show without items, the case moved from the
broken shows of its suite to the whole ones, and `pack` is compared with the Python tool
on such a show: the two JSON files and nothing else. Two pages that seed 07 wrote made
the file of their upload example with the Python tool; they now use the converter, which
writes the same 1,138 bytes. The pages for newcomers name nine commands, and the notes on
the Android app no longer say that the list of items cannot be read.

**Resolution.** `converter/lib/show.js`; `converter/tests/pack.test.js`, "a show without
items on the bench canvas" and `WHOLE_SHOWS`; `docs/emulator.md` and `docs/firmware.md`,
the upload examples; `tests/firmware/test_docs.py`; `agent/vocabulary.md`, "command";
`tests/onboarding/test_vocabulary.py`,
`test_the_entry_for_command_names_every_command_of_the_command_list`;
`docs/android-app.md`.

## The owner's ruling on the current limiter

**Question.** The owner ruled on 2026-10-12: switch the limiter off if that does not
burn the board and puts no hardware at risk. Does it?

**Answer.** Not in the installation, and yes on the bench. With the LEDs fed from the
power supply no LED current passes through the board, and the limiter protects nothing
of it. On the bench one strip of 60 LEDs is fed from the board's 3.3 V pin; the rule of
a brightness of 40 or less binds agents and not a command, and `brightness 255` on a
white picture would ask that pin for about 3 A. There the limiter at 850 mA is the
protection. So nothing was switched off on the board. The limit becomes a tracked
setting, seed 15: 850 mA while a strip is fed from the board, and 0, which is off, or
what the supply gives, once the LEDs have their own supply. The value for the
installation is about power and is the owner's.

**Resolution.** `project-seeds/15-p1-led-current-limit-as-a-setting/`; `AGENTS.md`,
"What is coming".

## Seed 12 spec: Where the standalone firmware gets the network and the limit

**Question.** The seed says the network's name and password come from the same tracked
settings file the WLED-based firmware uses, and the limit on LED current from a tracked
value. The tracked files are on the computer. How do the values reach a firmware that has
no settings interface: compiled in at build time, or read on the board?

**Answer.** Read on the board, from the two files WLED reads: `ap.ssid`, `ap.chan` and
`hw.led.maxpwr` of `/cfg.json`, and `ap.psk` of `/wsec.json`. The firmware tool writes
them from the tracked files (seed 08, and seed 15 for the limit). So a board has one set
of stored settings, both firmwares use it, a switch needs no rebuild, and no image holds
the password. Compiled in, the two firmwares could disagree after a change, and the
password would be in a file under `build/`.

**Resolution.** `docs/specs/12-p2-standalone-firmware-as-a-fallback/design.md`, "The
stored settings"; `requirements.md`, 4.1, 4.4 and 6.1.

## Seed 12 spec: No network without stored settings

**Question.** WLED hosts a network with its public default name and password when none
are stored. What does the standalone firmware do then?

**Answer.** It hosts none. A default would have to be compiled in, and the seed for the
password exists because a known password lets anyone at the event send commands. The
board still plays and answers over USB, and the probe report says that no access point
is up. Seed 08's `set-wifi` is what puts the settings there.

**Resolution.** `requirements.md`, 4.3 and 4.4; `design.md`, "The network and HTTP".

## Seed 12 spec: What the two firmwares share

**Question.** The seed asks only that the core's files are used unchanged. The usermod
has 1,100 lines around the core. Written again, or shared?

**Answer.** Three files are shared: the files, the port and the HTTP transport. They
take one object each from WLED, and they are where the pacing of storage calls and the
handling of a request body live, which seed 07 measured and tuned. They now reach their
platform through `odrig_platform.h`, of which each build has its own. The outputs are
written anew, because the usermod's are WLED's bus layer. The lock, the task and the
loop, 120 lines, are written again in `main.cpp`: sharing them would put the usermod's
start behind an interface for no other gain. The price is a change to three files of the
firmware in use, and task 2 runs the whole board suite on it.

**Resolution.** `design.md`, "The platform header" and "The program"; `tasks.md`, task 2.

## Seed 12 spec: A probe build of its own, and which board tests run

**Question.** The seed asks that the board tests the WLED-based firmware passes are run
against the standalone one, except those that depend on WLED. Most of them read the
probe report. And "twenty outputs each carry a full 180-LED signal" has to be shown
without eyes.

**Answer.** The standalone firmware gets a probe build with the members of the report
that mean something without WLED, among them `pulses`, the rising edges the chip counts
on a pin: 4,320 for 180 LEDs. The pulse counter moves out of the usermod's probe file
and is shared. The board suite is run a second time with `test-board --standalone`; a
test that needs WLED is marked and skipped there. Both runs leave the WLED-based
firmware on the board.

**Resolution.** `requirements.md`, 9 and 10; `design.md`, "The probe build" and "The
board suite".

## Seed 12 spec: The order with seeds 08 and 15

**Question.** Is seed 12 blocked?

**Answer.** Its spec is not. Its implementation waits for seed 08: the network's name
and password are in the board's stored settings only after it, and without them the
standalone firmware hosts no network, so its HTTP transport could not be tried. Seed 15
is not needed: without it the limit is 850 with both firmwares. So the order is seed 08,
then seed 12, and seed 15 at any point after seed 08.

**Resolution.** `tasks.md`, the opening; `design.md`, "What this design relies on".

## Seed 08: What a file system keeps of a file that was rewritten

**Question.** A test of the edit looked for a password that had stood in `/cfg.json` in
the bytes of the whole storage image afterwards, and found it. Is the edit wrong?

**Answer.** No. The file no longer holds it: the file system writes a changed file into
other blocks and does not erase the blocks it frees. So after a change of the password,
the bytes of the old one can stay in storage, outside every file, until those blocks are
used again, and in the storage images the work folder keeps. WLED serves files and not
blocks, so nothing on the network gives them out; reading the flash over USB does. The
test now reads the file. `docs/wifi.md` says this where it says what else holds the
password.

**Resolution.** `tests/firmware/test_wifi_storage.py`,
`test_a_password_in_the_configuration_is_gone_afterwards`; `docs/wifi.md`, in task 6.

## Seed 08: `write_storage` is given the making of the new image

**Question.** The design gives `write_storage(on_port, region, before, after)` the new
image. `install-show` has made its new image inside the block that restarts the board
when something fails, so that a show that does not fit, `no-space`, leaves a board that
runs again and not one that waits in its bootloader. With the new image made by the
caller, each caller would have to repeat that.

**Answer.** `write_storage(on_port, region, before, make)` gets a function that makes
the new image from the one the board holds, and calls it inside the block. `install-show`
passes `storage.with_show`, `set-wifi` passes `wifi.apply`. So a refusal of either, also
`wled-settings-malformed`, restarts the board and writes nothing, and `install-show`
behaves as it did: its tests pass unchanged.

**Resolution.** `firmware/fwtool/cli.py`, `write_storage`, `_install_show` and
`store_settings`; `tests/firmware/test_wifi_commands.py`,
`test_settings_of_wled_that_are_no_object_are_refused_and_nothing_is_written`.

## Seed 08: The stand-in for esptool confirms a kept image

**Question.** In the command tests a second run on "another board" took the image the
work folder kept from the run before, and a storage that should have been refused was
never looked at. Why?

**Answer.** The tool takes its newest kept image when the chip confirms that image's
checksum, and the stand-in for esptool confirms every comparison unless it is told to
fail one. That is right for a second run on the same board. Where a test means a board
that holds something else, it tells the stand-in to fail the first comparison, and the
tool reads storage again, as it does on a real board.

**Resolution.** `tests/firmware/test_wifi_commands.py`, `OnASmallLayout.esptool` and the
tests that pass `failing_verifies`.

## Seed 08: Which test checks which criterion

**Question.** Task 6 asks to read the acceptance criteria of Requirements 1 to 9 once more
and to name, for each one a program can check, the test that checks it. Where is that
written, and what was missing?

**Answer.** Here. The files are in `tests/firmware/` unless a folder is named.

| Criteria | Checked by |
|---|---|
| 1.1 to 1.4 | `test_wifi_settings.py`, `TheSettingsFile` |
| 1.5, 1.6 | `test_wifi_commands.py`: `test_it_has_no_option_that_carries_a_name_or_a_password` of both commands, `test_without_the_option_the_settings_file_is_read` of both, `WhereThePasswordGoes` |
| 2.1 to 2.4, 2.6 | `test_wifi_settings.py`, `Reading` |
| 2.5 | `test_wifi_settings.py`, `ThroughTheCommands` |
| 3.1 to 3.7, 3.10 | `test_wifi_commands.py`, `SetWifi` |
| 3.8 | `test_wifi_commands.py`, `test_settings_that_do_not_fit_into_storage_are_no_space_and_nothing_is_written`; `test_wifi_storage.py`, `test_a_file_system_with_no_room_is_no_space` |
| 3.9 | `test_wifi_commands.py`, `test_settings_of_wled_that_are_no_object_are_refused_and_nothing_is_written`; `test_wifi_storage.py` |
| 4.1 to 4.6 | `test_wifi_storage.py` |
| 4.7 | `test_usermod_files.py`, `test_the_radio_is_only_read_and_only_by_the_probe_build_for_its_report`; `test_patches.py`; the firmware's SHA-256, recorded in `docs/firmware.md` |
| 4.8 | `test_wifi_commands.py`, `test_flash_makes_no_call_that_reads_or_writes_storage`; `test_flasher.py`, `RestoreStock` |
| 5.1 to 5.4 | `test_wifi_commands.py`, `test_nothing_of_these_runs_shows_the_password` of both commands, `WhereThePasswordGoes` |
| 5.2, 5.5 | `test_wifi_settings.py`, `test_no_detail_quotes_text_of_the_file`, `test_the_text_form_of_the_settings_does_not_hold_the_password` |
| 5.6 | by reading: every comparison of a password is `assertTrue` or `assertFalse` on a result |
| 6.1 to 6.4 | `test_wifi_commands.py`, `InstallFirmware`; `tests/board/test_wifi.py`, `FromScratch` |
| 6.5, 9.6 | `test_docs.py`, `test_it_says_what_set_wifi_does_and_names_its_reasons`, `test_it_says_what_install_firmware_does_and_where_it_takes_the_place_of_flash`, `test_the_probe_report_has_the_access_points_name_and_protection` |
| 7.1, 7.2, 7.4 | `tests/board/test_wifi.py`, `TheReport` and `TheSettings` |
| 7.3 | `test_usermod_files.py`, the test of the radio and `test_the_usermod_names_no_wifi_function_of_wled` |
| 7.5 | `test_wifi_commands.py`, `test_no_tool_and_no_test_changes_the_network_settings_of_this_computer` |
| 8.1 to 8.4 | the three suites, each found by discovery |
| 8.5, 8.6 | `tests/board/test_wifi.py`; `tests/board/__init__.py`, `LeaveTheBoard` |
| 8.3 | `tests/air/test_wifi.py`, written and run by no agent |
| 9.1 to 9.5 | `test_wifi_docs.py` |

Six tests were missing and were added: the `no-space` of 3.8 through the command, the
settings file read by `install-firmware` without the option, the three of
`WhereThePasswordGoes`, and the suite's last step now asks storage for the settings.

Not in the spec, because the pages for newcomers did not exist when it was written:
`AGENTS.md` no longer lists the name and the password under what is coming.

**Resolution.** `tests/firmware/test_wifi_commands.py`; `tests/firmware/test_wifi_docs.py`;
`tests/air/test_wifi.py`; `AGENTS.md`, "What is coming"; `tests/onboarding/test_entry.py`.

## Seed 08: The owner's check is open

**Question.** Task 7 needs a phone or a computer joined to the board's network. No agent
joins that network.

**Answer.** The task stays open, its checkbox unticked, and the seed stays `in_progress`.
Under the task, `tasks.md` has what a program established over USB: the board hosts
`odrig` with WPA2, and its storage holds the name and the password of the settings file.
What remains is "The owner's check" of `docs/wifi.md`, four steps. When they pass, the
owner sets the seed to `completed`.

**Resolution.** `docs/specs/08-p1-wifi-name-and-password/tasks.md`, task 7;
`docs/wifi.md`, "The owner's check";
`project-seeds/08-p1-wifi-name-and-password/state.json` is not changed.

## Seed 15: Where the limit lives, and how a board is asked for it

**Question.** The seed says that the limit lives in one tracked settings file and that the
firmware tool reports the limit stored on the board. Which file, and which command?

**Answer.** A file of its own, `firmware/limit.json`, with the one member `milliamps`. The
settings file of seed 08 holds exactly a name and a password, and its reader refuses a
third member; a limit is no Wi-Fi setting either. Reporting is a command of its own,
`read-limit`, which reads storage and writes nothing, as `read-show` does. On a board
whose `/cfg.json` holds no `hw.led.maxpwr` it says so and names WLED's own 850 mA.

**Resolution.** `firmware/limit.json`; `firmware/fwtool/limit.py`;
`docs/specs/15-p1-led-current-limit-as-a-setting/design.md`, "The commands".

## Seed 15: `install-firmware` prints four lines

**Question.** Seed 08 required `install-firmware` to print the three lines `set-wifi`
prints. Seed 15 has it apply the limit too.

**Answer.** It prints four: the name, `password: set`, the line of the limit, and the
reply to `status`. It makes one storage image with both settings and writes once. Both
files are read and checked before the board is touched, the settings file first.
`--limit FILE` reads another limit file, as `--settings FILE` reads another settings
file. The tests of seed 08 that held three lines hold four.

**Resolution.** `firmware/fwtool/cli.py`, `store_settings` and `_install_firmware`;
`tests/firmware/test_wifi_commands.py`; `tests/board/test_wifi.py`, `FromScratch`.

## Seed 15: The probe build counted every send as dimmed with the limiter off

**Question.** The seed's check on the board is that the probe report shows no dimmed
send with a limit of 0. The report showed 49 to 67 in every second.

**Answer.** The count was wrong, not the limiter. With a maximum of 0, WLED's limiter is
not in use: it estimates nothing and dims nothing, as its source says and as `used_ma` 0
showed. The probe build counted a send as dimmed when the estimate was at or above the
limit, and 0 is at or above 0. It now counts only while WLED's maximum is above 0. The
firmware has none of that code and its image is unchanged.

**Resolution.** `firmware/usermod/odrig_probe.cpp`, `limiterOn`;
`tests/firmware/test_usermod_files.py`,
`test_the_probe_build_counts_a_dimmed_send_only_while_the_limiter_is_on`;
`tests/board/test_limit.py`.

## Seed 15: A limit of 0 on the bench, for a minute

**Question.** The bench strip is fed from the board's 3.3 V pin, and the limiter is what
protects that pin from a high brightness. The board test switches the limiter off.

**Answer.** For about a minute, with a show of brightness 40 installed and no command
sent that changes the brightness, and it sets 850 again before it ends. At brightness 40
the 60 LEDs of the strip cannot ask for more than they do in every other board test. A
run that is stopped in between leaves 0 on the board: the suite's last step puts the
limit of the limit file back, and so does `python3 firmware/fw.py set-limit`.

**Resolution.** `tests/board/test_limit.py`; `tests/board/support.py`, `ensure_settings`;
`tests/board/__init__.py`, the last step.

## Seed 12: The RMT method is the library's own

**Question.** The design gives four legs to "the RMT methods" of the LED library. WLED
does not use those on this chip: it adds a driver of its own to the library, in its
folder `lib/`, and uses that for its RMT outputs.

**Answer.** The standalone firmware uses the library's own RMT method,
`NeoEsp32RmtNWs2812xMethod`, with one channel for each of the four legs. WLED's driver is
a file of WLED, and the standalone firmware compiles none. The trial program showed the
library's method beside the sixteen-lane parallel one on the board: 4,320 pulses on each
of the four pins in every send, 50 sends a second.

**Resolution.** `firmware/standalone/src/main.cpp`; `docs/firmware.md`, "Verified on the
board", S2.

## Seed 12: The spike's findings

**Question.** Task 1 was to settle six assumptions before anything else was written.
Does a finding change the design?

**Answer.** None does. Five hold as assumed, with numbers in `docs/firmware.md`; the
sixth, that a source file of the usermod can be compiled into the standalone program, is
task 2's. Two things were learned beside them: `--standalone` on `build` cannot be one of
the exclusive options beside `--stock` and `--probe`, because it goes with `--probe`, so
the tool refuses `--standalone --stock` itself, as a usage error before anything is set
up; and the libraries of the standalone project are kept in that project's own folder
under `build/firmware/standalone/`.

**Resolution.** `firmware/fwtool/cli.py`, `parsed`; `tests/firmware/test_standalone.py`.

## Seed 12: The WLED-based firmware after the platform header

**Question.** Three sources of the usermod now include `odrig_platform.h` in place of
`wled.h`. The design said the compiled code of the WLED-based firmware does not change.
Its image has another SHA-256.

**Answer.** The code did not change. The image before and the image after, built in the
same work folder, differ in 65 bytes of 1,221,568: 32 bytes at `0xB0`, where the build
keeps a hash of its own program file, and the checksum and the hash at the end of the
image. The program file holds the names of the source files for a debugger, and one more
header is named now. Every other byte is the same. The whole board suite was run on the
new image all the same.

**Resolution.** `docs/firmware.md`, "Verified on the board", S4;
`firmware/usermod/wled/odrig_platform.h`; `tests/firmware/test_usermod_files.py`,
`test_the_shared_sources_reach_their_platform_through_the_platform_header`.

## Seed 12: The channel, a hidden name, and which member counts

**Question.** The design gave the network channel 1 where the stored settings name none,
and did not say what a hidden name or a member named twice does.

**Answer.** The reader follows WLED, so that one set of stored settings gives one
network whichever firmware runs. The channel is `ap.chan` when it is a whole number from
1 to 13 and 6 otherwise: 6 is what WLED takes, not 1. The network hides its name when
`ap.hide` is a whole number above 0, as WLED's does. Of a member that is named twice the
first counts. A file that is not one JSON object counts as absent as a whole: the reader
walks all of it before it takes anything.

**Resolution.** `firmware/standalone/src/settings.h` and `settings.cpp`;
`tests/firmware/test_standalone_settings.py`.

## Seed 09 after the owner split the app

**Question.** Seed 09 was the whole operators' app, and its spec, thirteen tasks, was
written for all of it. On 2026-10-12 the owner split the app: command and control first,
converting and uploading second. No task of seed 09 had been done. What becomes of the
seed and of its spec?

**Answer.** Seed 09 keeps its number and becomes the first part, with a new text; its
scope may change because none of its tasks was done. The second part is a new seed, 17.
The reply to `status` with the canvas size goes with the second part: only converting
needs it. The spec of seed 09 stays in its folder until the seed is taken through its
spec again, and its three pages say at their top that they describe the whole app and
are not to be implemented from. A beginning of the old first task, the canvas size in
`status`, was set aside and is not in the repository.

**Resolution.** `project-seeds/09-p1-operators-app-for-android/seed.md`;
`project-seeds/17-p2-operators-app-converting-and-uploading/`;
`docs/specs/09-p1-operators-app-for-android/`, the note at the top of each page;
`AGENTS.md`, "What is coming".
## Seed 11: Master moved under the pull request

**Question.** While the pull request of seed 11 waited, `master` got the content commands
(seed 07), the converter in JavaScript (seed 06) and three more seeds. What had to be done
to the work on Windows, what does the converter's suite do on Windows, which the seed asks
to be run there once the converter is in the repository, and what in the pull request was
not about Windows?

**Answer.**

- The command tool had become a `Session`: several exchanges through one opening of a
  port. The serial port of Windows and the connection over TCP are put into it. An open
  port is the descriptor of `_open` where the system has `termios`, and an object elsewhere;
  four small functions do with either what the tool did with a descriptor. A session takes
  `tcp=` beside `port=` and `http=`, so `list` and `upload` work over TCP.
- The new tests of the emulator suite and of the core suite took the same turn as the
  earlier ones: the transport of the system in place of the serial port, and in the core's
  test host the calls of Windows for renaming over a file, removing and listing a folder.
- **The converter's own suite on Windows**, `npm test --prefix converter`, with Node.js
  24.13 and Python 3.14: 499 tests, 288 pass, 208 fail, 3 are skipped. 73 of the failures
  show the same error: the suite starts a helper in Python,
  `converter/tests/reference.py`, which loads the C library of the system with
  `ctypes.CDLL(None)`, and Windows has no such thing to load. The other failures were not
  looked into. The commands of the converter that `docs/emulator.md` gives run on Windows:
  the emulator suite runs them. Mending the converter's suite is not part of this seed and
  was not begun: `docs/converter.md` still says that nothing has been run on Windows.
- The system's error 10055, seen once before and left unexplained, came again while two
  suites ran at the same time, as the reason an emulator could not take a port. It is the
  system running short of ports or buffers under that load, not a fault of the emulator.
- The owner ruled that the pull request holds the support of Windows only and that Linux
  is not worked on. What the branch did for a system that is neither macOS nor Windows,
  and a mend of two older tests for Python 3.10, were taken out and are kept on the branch
  `beyond-windows`. The spec of this seed still names `libodrig_core.so` for other
  systems: the code no longer does.

On the Windows computer, on the merged branch: the reference converter's suite 638 tests,
the core suite 364, with Microsoft's compiler 364 of which 10 are skipped, the emulator
suite 523 of which 17 are skipped, the onboarding suite 81.

**Resolution.** `odrigctl/client.py`: `Session`, `_ready`, `_take`, `_give`, `_had` and
`_shut`; `tests/core/host/host.cpp`; `tests/emulator/support.py`: `BytePort`,
`session_target`; `agent/getting-started.md` and `AGENTS.md`, the sections about Windows.

## Seed 16: The page names the animation by its id

**Question.** The design of the playlist says that the emulator's page shows `playlist`
where `playing` is `"all"`, "and the file name of the animation on the LEDs beside it".
The task says only the first. The page reads the `status` events and the mapping file; it
does not read the items of the show, so it has no file name to show.

**Answer.** The page shows `playlist` in its `playing` field and, as before, the id of the
animation in its `animation` field. A file name would need the page to read the items and
to read them again after every upload and removal, which is a part of the app of seed 09
and not of this seed. The requirement, that the page shows that the playlist plays and
which animation, is met by the id.

**Resolution.** `emulator/web/app.js`, `onStatus`; `tests/emulator/test_page_files.py`;
`docs/emulator.md`, the header.

## Seed 16: What follows from an animation never playing alone

**Question.** With `play <id>` of an animation a jump in the playlist, nothing plays an
animation by itself any more. Does the core keep the code for it, and what do the pages
count as a command?

**Answer.** The core does not keep it: the player's function plays a cycle and is named
so, and `playing` holds the playlist, a cycle or nothing. The tests that expected an
animation to loop for ever after `play`, and the LEDs to go dark when what plays is
removed, were rewritten to what the owner ruled; none was dropped. The vocabulary counts
ten commands: `play all` has its own row in the table of `docs/commands.md`, and
`upload` is counted once, as before. The demo show's test records 73 seconds where it
recorded 31, a round of the playlist and the start of the next: the turn of Hello world
is 30.6 seconds and that of the bouncing square 41.8.

**Resolution.** `core/src/player.cpp`, `player_play_cycle`; `tests/core/test_content.py`,
`test_removing_what_plays_leaves_the_playlist_playing`; `agent/vocabulary.md`;
`tests/emulator/test_demo.py`.

## Seed 16: On the board, and the figures of the firmware page

**Question.** The firmware page has a table of measurements "with the firmware as it
is", taken by the board suite. After the firmware was built with the core that plays the
playlist, are the figures of the earlier run kept?

**Answer.** They are replaced by those of the run that verified this firmware, so that
the page describes the firmware a reader builds. Two things of that run are recorded
beside them. The dense 60 x 60 clip compressed had 24 to 33 sends a second in the probe
build where the run before recorded 29 to 36; it is inside the 20 to 50 the owner
accepts, and no work is done on a rate inside that range, so what made it slower was not
looked for. And the firmware from before the seed refuses a show with one of the new
members as `show-malformed`: the page says that such a show and this firmware go on a
board together. The one line of the air suite that changed was not run, because that
suite needs the Mac on the board's network. The text of seed 14 speaks of the start item
playing at once; with the playlist it is whatever the show plays by itself, which its
spec will say when it is written.

**Resolution.** `docs/firmware.md`, "Measurements on the board" and "Verified on the
board", the paragraph on the playlist; `tests/board/test_playlist.py`;
`tests/air/test_upload.py`.

## Seed 09: What Chrome showed for the app's suite

**Question.** The design of the app assumed three things about Chrome without a window,
C1 to C3, for the suite that drives the web code. Do they hold, and what else did the
first run of the suite show?

**Answer.**

- C1 holds. A page from `127.0.0.1:A` posts a text to `127.0.0.1:B/odrig` with `fetch`
  and reads the emulator's reply, with no request before it: the emulator's log has the
  one line `status` for each request, as `http`.
- C2 does not hold. With `--window-size=360,740` the driver's page was laid out 500 by
  653 pixels: Chrome has a smallest window. The fallback of the design applies: the
  driver gives the frame that holds the app its size, and the app in it is 360 by 740.
- C3 holds. The app's page in a frame of the driver's page, both from the suite's
  server, is worked by the driver, and an address the driver keeps before the frame
  loads is the one the app starts with.
- The board's address, `4.3.2.1`, is somebody else's computer on every network but the
  board's own, and the app asks it when no address was set. So the suite's server is
  also Chrome's proxy: what is not for this computer arrives there, is answered with
  502 and goes no further. The suite reads from it what the pages asked other computers
  for, which is how the test of the first address sees the line `status` on its way to
  `4.3.2.1`. Chrome asks for things of its own, such as the time; they end there too
  and are not counted, because they name no page.
- `messages.js` is there from this task, with the texts of the four failures of the way
  to the target, because the target screen shows them; the order of work had it later.
- An address is kept in small letters and a port without zeros in front. While a request
  to the address before is under way, a new address waits for its end, at most the five
  seconds of the time limit: one request is under way at a time.

**Resolution.** `tests/app/support.py`, `run` and `_Pages`; `tests/app/page/driver.js`;
`app/www/target.js`, `parse`; `app/www/client.js`, `begin`.

## Seed 09: The list on the show screen

**Question.** What did building the show screen settle that the design left open?

**Answer.**

- The app asks for the list with `list 0` and then `list <next>`, and never with the bare
  `list`: the two mean the same to the target, and one form is one line to check.
- The design takes a `status` that is due before a list that is due. With a target whose
  replies take longer than a second, a status is always due, and the list would never be
  asked for. A list that waited while a status was sent goes before the next status. The
  design says so now.
- While the show is invalid, `list` is refused. The screen then has no rows and does not
  say that no animation is installed: it does not know. The reason of the invalid show
  stands where the screen says what plays.
- While the target does not answer, the line reads `The installation has not answered
  for 12 seconds.`, counted from the last reply, or from the start when there was none.
- The stand-in target of the suite answers by the first word of a line, so that it can
  stand for a target that knows `status` and `list`.

**Resolution.** `app/www/commands.js`, `list`; `app/www/client.js`, `due`;
`app/www/screens/show.js`; `docs/specs/09-p1-operators-app-for-android/design.md`, "The
client"; `tests/app/support.py`, `StandIn`.

## Seed 09: The controls of the show screen

**Question.** What did building the controls settle that the design left open?

**Answer.**

- The status that follows a command of the operator goes before a list that waits, so
  that the screen shows at once what the command did.
- "The value at which the slider is let go is always sent" would send a tap on the
  slider twice, as the move and as the letting go. The value is sent again at the
  letting go only when its command went out a second ago or more: somebody else may
  have set another brightness since. A brightness command still keeps 200 ms from the
  one before it.
- The slider counts as held from its first move until it is let go.
- What the operator asked for and was not sent yet is dropped when the app leaves the
  screen of the phone: it is not sent later, when the app comes back.
- The animations are buttons, and the buttons are made again only when the list is
  another one. A status arrives every second; making them again each time could lose a
  press.
- A refusal is shown as one general sentence with its code. The table of messages comes
  with the task of the messages.

**Resolution.** `app/www/client.js`, `give`, `want` and the handler of
`visibilitychange`; `app/www/screens/show.js`, `sendLevel`, `drawRows` and `start`.

## Seed 09: Messages, the look and back

**Question.** What did the tasks of the messages, the look and the back gesture settle?

**Answer.**

- A refusal's message is made from the line that was refused: `unknown-id` names the
  animation of `play <id>`, and says that no animation is installed for `play all`. The
  message of `show-invalid` has the reason when a status has said one, and does without
  it otherwise. A code the app does not know, whatever its spelling, gets the general
  sentence with the code in brackets.
- While the target does not answer, the show screen has two lines: for how long, and the
  message of the failure with its code, as the target screen has it.
- Back. The app's entries of the page's history are its first screen, or that and the
  other screen on top of it. When the target answers for the first time, the entry of
  the target screen is replaced by one of the show screen, which is the app's first
  screen from then on: back from the target screen shows it, and back from it leaves
  the app. The button of the screen below goes back as the gesture does, so that no
  entries pile up. Before the first answer the target screen is the first entry.
- The style needed no change for the measures of the design: the suite measures them at
  360 and at 320 pixels, with a file name of 32 characters, and with a control made too
  low and a text made too dim two of its tests fail.

**Resolution.** `app/www/messages.js`, `ofRefusal`; `app/www/screens/show.js`, `draw`;
`app/www/main.js`, `go` and the watcher of the client; `tests/app/test_look.py`.

## Seed 09: The toolchain and the first APK

**Question.** The design of the app assumed seven things about the build, T1 to T7, and
named six facts to be read again before anything is pinned. What was found?

**Answer.** The owner said yes to the downloads and to the SDK's licence on 2026-10-13,
after the files, their sources and their sizes were named.

- The facts, read again at their sources on that day, are as the design has them:
  Capacitor 8.5.3, the Temurin JDK 21.0.12.1+1, the command-line tools 15859902, the
  three SDK packages under `android-sdk-license`, and Gradle 8.14.3. Nothing else is
  pinned.
- T1 holds. `npm ci` with Node.js 26.5 installed the three packages at 8.5.3, and
  `cap add android` made the project the design describes: API levels 24, 36 and 36, the
  Android Gradle plugin 8.13.0, Gradle 8.14.3, the one permission `INTERNET`. The
  template also puts Google's services plugin on the build's classpath; it is applied
  only when a `google-services.json` is there, and none is.
- T2 holds: Capacitor takes `../build/app/www` as its folder of web files.
- T3 holds: `sdkmanager` ran on the JDK, asked once, and installed the three packages;
  the SDK's folder of accepted licences holds `android-sdk-license` and nothing else.
- T4 holds: after three builds the SDK holds the three packages and no other.
- T5 did not hold at first. The Android build wrote `analytics.settings`, a record that
  nothing is reported, into `.android` of the user's folder: Java takes that folder from
  the system, whatever `HOME` and `ANDROID_USER_HOME` say. Gradle is now given
  `-Duser.home` with a folder of the work folder, the file was removed, and after a
  further build nothing new was in `.gradle`, `.android`, `.npm` or `.m2` of the user's
  folder. One more thing was written there, by hand and not by the tool: the lock file
  was made once with `npm install --package-lock-only` without the tool's environment,
  and npm's own cache in the user's folder got the packages' descriptions and a log.
  Every run of npm by the tool keeps its cache in the work folder.
- T6 holds: Gradle took `distributionSha256Sum`, and Capacitor's `sync` left the file.
- T7 was not tried as written, because no setting of the Mac is changed. With Gradle's
  own `--offline`, a build from an emptied build folder of the Android project succeeded
  in 5 seconds.
- A setup took 16 seconds on this network. The first build took 56 seconds, with Gradle
  fetching itself and what the Android build needs; a second build took 4.5 seconds. The
  work folder `build/app/` has 2.2 GB after a build: 354 MB of kept archives, 336 MB of
  JDK, 530 MB of SDK and 1.0 GB of Gradle with what it fetched. `app/node_modules/` has
  31 MB.
- The APK has 4,132,388 bytes, and every build of the same files gave the same bytes.
- `npm audit` names three advisories of moderate severity, all through one package that
  Capacitor's command line uses, `uuid`. It runs at build time only; nothing of it is in
  the APK.
- The JDK's archive holds links, so it is unpacked as a tar archive is and not as plain
  data. A variable `ANDROID_SDK_ROOT` of the caller is not passed on.

**Resolution.** `app/toolchain.json`, `app/package.json`, `app/apptool/toolchain.py`,
`env.py` and `build.py`; `app/android/gradle/wrapper/gradle-wrapper.properties`;
`docs/specs/09-p1-operators-app-for-android/design.md`, "The environment of every child
process".

## Seed 09: The sender and the checks of the APK

**Question.** What did the task of the sender settle?

**Answer.**

- The sender is one class of 166 lines with two methods, `send` and `route`. It was
  compiled into the APK by the tool's build. No test runs it: it needs a phone on a Wi-Fi
  network, and the check on a phone is the owner's. What the suites do check is what its
  source says and that it is in the package.
- The APK with the sender has 4,137,137 bytes. Its three permissions are `INTERNET`,
  `ACCESS_NETWORK_STATE` and `CHANGE_NETWORK_STATE`, none of which asks the operator a
  question. A fourth one in the package is the app's own, declared by an AndroidX
  library, as the design expected.
- The suite of the APK reads the package with `aapt2` of the SDK in the work folder. It
  compares the web code in the package byte for byte with `app/www/`, so an APK built
  before a change of the web code fails it and says to build again. The note of the
  build names the commit the build stood on; the suite asks that the commit exists and
  not that it is the newest, because a build made before its own commit names the one
  before.
- The suites of the app are two, and the getting-started page names both. That page
  holds 200 lines at most, so the sentences about the suites that need more were made
  shorter.

**Resolution.** `app/android/app/src/main/java/app/odrig/operators/TargetPlugin.java`;
`tests/apk/test_apk.py`; `tests/app/test_android.py`; `agent/getting-started.md`,
"Suites that need more".

## Seed 09: What the first part of the app has beyond its seed

**Question.** The seed of the app's first part asks for the screens, the emulator's
option, a build with one command, tests in Chrome and documents. What was built that it
does not name?

**Answer.** Each of these was in the design from the start, and none adds a command to
the command list or changes what the installation does.

- Two more commands of the tool: `serve`, which serves the web code to a browser on this
  computer and is what the suite uses, and `install`, which puts the APK on a phone that
  is connected by USB.
- A second suite, `tests/apk/`, which reads a built APK.
- The line of the target screen that says how the phone's requests travel, with the
  sender's method `route` behind it, so that a failure on a phone can be read off the
  screen. And `build.json`, the note of the commit an APK was built from.
- `old.html`, the page for a web view that is too old.

The pages for newcomers named the app as planned, and a test kept its words out of them.
The first part exists now, so the pages name it, and the test keeps out the words of
what is still planned: the PC version and the app's second part. The seed stays in
progress: its last item, the check on a phone, is the owner's.

**Resolution.** `app/apptool/cli.py`; `tests/apk/`; `app/www/screens/target.js`,
`routeLine`; `app/apptool/stage.py`; `tests/onboarding/test_pages.py`, `PLANNED`;
`docs/android-app.md`.

## Seed 14: What the start reads of a file

**Question.** The requirements say the start reads "the header only". The design says
opening a file reads the palette as well, and calls that a difference. Which is it?

**Answer.** The header only: the first 16 bytes. The core's decoder reads the palette
with the first frame record, not when it is opened. So the code does what the
requirements say, and the design's sentence about the palette is wrong. A fault in a
palette is a fault in the body: the check after the start or the player finds it, not
the start. Of the 34 invalid vectors, 10 are found by the start and 24 after it.

**Resolution.** `core/src/core.cpp`, `open_file`; `tests/core/test_power_on.py`,
`TheStart`; `docs/core.md`, "Startup".

## Seed 14: How the old tests of the core meet the check after the start

**Question.** About 150 tests of the core send `list`, `remove` or an upload right after
the start, where the answer is `busy` now. The design gives each of them the refreshes
the check needs first. Is that how it is done?

**Answer.** No. The test host has a new option, `--check-first`: the check takes all its
steps before the session begins, with no refresh between them. The helpers of the suite
give that option unless a test asks for the core as it is after power-on, and the
reference player has the same switch. Adding refreshes to 150 scripts would have changed
the timestamps and the output of each, and with them what the tests say. The new tests,
in `tests/core/test_power_on.py`, run without the option.

Three more changes of the test host came with it. `--trace-reads` prints how many bytes
of a file the core read before it closed it, which is how a test sees that the start
decodes nothing. `--read-fails FILE OFFSET` now fails for `read_at` too, so a file that
cannot be read is found by the check as it was found by the start.
`--read-back-fails` and `--read-back-differs` now touch `upload.part` only: they are
about what storage gives back of an upload, and the check after the start reads the
installed files through the same function.

**Resolution.** `tests/core/host/host.cpp`; `tests/core/support.py`, `CHECK_FIRST`;
`docs/core.md`, "The test host".

## Seed 14: How the reference player knows where a fault in a body lies

**Question.** The reference player decodes a file at once and cannot say at which frame
record a fault lies. The design has each test tell it the refresh at which the show
turns invalid. Is that how it is done?

**Answer.** No. For a file its own decoder refuses, the reference asks the core's
decoder, outside any session, how many frame records come before the fault. From that
number it counts the check's steps and knows the frames the player can still show, so
every line of a session is compared, and no test has to give a refresh. The reference
leans on the core for that one number; the tests of the invalid vectors pin it apart
from any session.

**Resolution.** `tests/core/support.py`, `found_in` and `_check`.

## Seed 14: The design's `checked` mark of a file

**Question.** The design gives every file a mark `checked`. Is it in the code?

**Answer.** No. The core has one mark for the whole check, `check_done`. Nothing would
read a mark of one file: `list`, `remove` and `upload begin` wait for the whole check,
and the files of the show change only after it. Once it is complete it stays complete: a
file an upload adds was read by the upload's own check.

The player counts the records of a loop only while the length is not known. With the
length known it decodes by time, as before, so a file that was swapped for a shorter one
behind the core's back is still refused as `truncated`.

**Resolution.** `core/src/core_state.h`, `check_done`; `core/src/player.cpp`,
`first_loop_to` and `show_at`.

## Seed 14: The emulator's tests, before the emulator's own task

**Question.** The emulator plays with the same core, so from the first task on its tests
get `busy` where they list, remove or upload right after a start. The tasks give those
tests to the third task. What happens to them in the first?

**Answer.** They are mended in the first, because every suite has to pass with every
commit. The suite's `Emulator` asks for the list over HTTP until it is no longer
refused, and only then hands the emulator to the test; a test that wants the emulator as
it is after power-on says so. The emulator logs what it is asked, so the helper that
reads the event stream leaves those first entries out. Two tests of record mode, where
time is the script's, send their upload a second later, and the reference they are
compared with reads its files at its refreshes, as the core does. The third task adds
the emulator's new tests and its page.

**Resolution.** `tests/emulator/support.py`, `Emulator.wait_for_the_check`,
`EventStream` and `reference`; `tests/emulator/test_record.py`.

## Seed 14: A file that is gone when the check comes to it

**Question.** The design lists `file-missing` among the faults the check after the
start can find. Can it?

**Answer.** No. The check reads with `read_at`, which answers -1 for a file it cannot
read and has no other answer for one that is not there. So a file that vanished between
the start and the check is `read-error` with its name. The start still says
`file-missing`: it opens every file with `open`, which tells the two apart.

**Resolution.** `core/src/core.cpp`, `check_step`; `docs/core.md`, "The check after
the start"; `tests/core/test_body_faults.py`.

## Seed 14: A host that is late for every refresh

**Question.** The requirements give the check after the start its steps at refreshes
that follow one another without a gap, "and none at any other refresh". What becomes of
the check on a board whose every refresh is late?

**Answer.** It would never end. The board sends a dense 60 x 60 animation 24 to 33 times
a second; below 25 every refresh leaves a grid time out, so the check would take no step
for as long as such an animation plays, and `list`, `remove` and `upload begin` would
stay `busy` with it. So the rule has a floor: a refresh after a gap takes no step,
unless the three refreshes before it took none either; then it takes one. A host that is
always late gets one step in four refreshes. The price is the time of one frame record
at that refresh: for the dense animation about a twentieth of a second in four
refreshes, which leaves the rate above 20 a second by the figures of the firmware page.
The board test of the seed measures it.

The check of an upload has the same rule without the floor, from seed 07, and is left as
it is: an upload whose check does not move for a minute is discarded, as the commands
page says. On a board that plays such an animation an upload can fail that way. That is
for the seed of uploading from the app to settle, and the owner is told.

**Resolution.** `core/src/core.cpp`, `check_after_start`; `core/src/core_state.h`,
`kCheckLongestWait`; `tests/core/support.py`, `CHECK_LONGEST_WAIT`;
`tests/core/test_power_on.py`, `TheCheck`; `tests/core/test_body_faults.py`,
`FoundByTheCheckOfALateHost`; `docs/core.md`, "The check after the start".

## Seed 09: Two tasks added after its tasks had begun

**Question.** The scope of a seed is fixed once its tasks are being done, and a gap
becomes a new seed. On 2026-10-14 the owner asked for two things that no seed has: the
operators' app shown in the emulator's page, running the code the phone runs, and the
board taking commands "via serial/usbc/wifi". Are they new seeds?

**Answer.** No, by the owner's word: "nothing new and no new seeds or tasks, just a
refinement on what we already agreed on", to be done within the seeds that are under
way, with the missing guidance filled in. Both are about how the app and its commands
reach a target, so they were added to the spec of seed 09 as Requirements 17 and 18, two
sections of its design, and tasks 10 and 11, which stand before the owner's check on a
phone. The board had been connected through its socket marked COM that day, where the
firmware did not listen; that is what Requirement 18 mends.

What was not added: the phone talking to the board over a USB cable, which the app has
no code for, and the board reading animations from a USB drive, which is seed 20 and
waits for the owner's answers on its hardware.

**Resolution.** `docs/specs/09-p1-operators-app-for-android/requirements.md`,
Requirements 17 and 18; `design.md`, "The app in the emulator's page" and "Commands on
the board's second USB socket"; `tasks.md`, tasks 10 and 11.

## Seed 19: What the preview names, and who refuses a file

**Question.** The design of the preview names the steps of the getting-started page as
"Build the core" and "What the computer needs", and lets the core refuse a file that is
no ODRG file. Is that what the code does?

**Answer.** Not quite. The page has no such headings: the core's library is built in "Set
up", by `make -C core shared`, and Node.js is under "What you need". The preview names
those, and the command that builds the library. And the converter's `check`, which the
preview runs first to learn the canvas of the file, refuses a file that is no ODRG file,
or a damaged one, before any emulator is started, with the reason the core would give:
the two readers are kept to the same reasons by the stored vectors. The core judges what
the converter takes, the canvas among it. So a refused file leaves nothing to stop.

The spec puts the command into the emulator's package, as `python -m emulator.preview`.
It is a package of its own, `preview/`, run as `python -m preview FILE`: the emulator's
package may import nothing but the standard library and itself, and holds no command
name, which its scope tests keep it to; the preview uploads with the command tool. So
the preview stands between the two, as a client of both, and the emulator stays as it
was.

**Resolution.** `preview/__init__.py`, `run` and `checked`;
`tests/emulator/test_preview.py`.

## Seed 14: A refresh that is in step but late

**Question.** The board test of the seed played a dense 60 x 60 animation while the
board read two more of them. Its rate fell to between 14 and 24 refreshes a second, and
the reading took 205 seconds. Why, and what changes?

**Answer.** On the board a dense frame takes most of a grid time to make, and a step of
the check, decoding one dense frame record, about as long again. A refresh that came
late within its grid time still counted as in step, so the count of the row went on
growing: two steps, then three, made the refreshes after them later still, and the rate
fell below what the owner accepts. A first change, one step at each refresh that is in
step but late, was not enough: on the board a step of a dense record, which reads the
file again besides decoding it, costs more than a grid time, and the rate stayed between
13 and 23. So now a refresh takes steps only when it is in step and no more than 2 ms
after its grid time; any other refresh takes none, apart from the one in four of the
floor. Beside a light show the polls come on time and the check runs at up to sixteen
steps a refresh, as before; beside a heavy one it takes a step now and then. The test
host polls on its grid times, so the core's tests keep their figures; two new tests poll
late within the grid.

The figures of the board after the change are in the firmware page.

**Resolution.** `core/src/core.cpp`, `check_after_start`; `core/src/player.cpp`,
`player_poll`; `core/src/core_state.h`, `kCheckOnTimeMs`; `tests/core/support.py`,
`CHECK_ON_TIME_MS`; `tests/core/test_power_on.py`, `TheCheck`; `docs/core.md`, "The
check after the start".

## Seed 14: How long the firmware tool waits for an install

**Question.** `install-show` and `install-firmware` wait for the board to read its
animations, within 20 seconds by default. Is that enough?

**Answer.** No. On the board a storage full of dense animations is read for some minutes
while one of them plays, and the default made such an install end with `check-not-done`.
The default of these two commands is 300 seconds now. They go on as soon as the board has
read its animations, so a small show costs no more than before. The other commands keep
20 seconds.

**Resolution.** `firmware/fwtool/board.py`, `SETTLE_SECONDS`; `firmware/fwtool/cli.py`;
`docs/firmware.md`, `install-show` and `install-firmware`.

## Seed 14: The floor of the check's pace on the board

**Question.** The floor of the check's pace gives a host that is late for every refresh
one step in four refreshes. Is that within what the owner accepts on the board?

**Answer.** No. With a dense 60 x 60 animation playing, the board's refreshes are late
nearly always, and a step of the check on another dense file costs it about 120 ms: the
two files are read and decoded side by side. One step in four refreshes held the rate
between 12 and 22 a second, below the 20 the owner accepts. The floor is one step in ten
refreshes now, which costs about an eighth of a second in four. Beside a light animation
the check keeps its pace, sixteen steps a refresh at the most, since the refreshes come on
time. The price is the time the check takes while a dense animation plays: minutes for a
storage of dense files, during which `list`, `remove` and `upload begin` answer `busy`.
The firmware page has the figures.

**Resolution.** `core/src/core_state.h`, `kCheckLongestWait`; `tests/core/support.py`,
`CHECK_LONGEST_WAIT`; `tests/core/test_power_on.py`; `tests/core/test_body_faults.py`;
`docs/core.md`.

## Seed 14: The check gives way to a low rate

**Question.** With the floor at one step in ten refreshes, the board's rate still fell
below 20 a second while a dense animation played and the check read another. Why?

**Answer.** On the board a refresh of a dense animation comes on time more often than the
rate shows: the task that asks for refreshes waits for the outputs and then asks at once,
often within 2 ms of the next grid time. So the check took its row of steps at those
refreshes, each about 120 ms, and the rate fell. The check now also looks at the rate:
it takes its steps only while the last whole second had 30 refreshes or more, or in the
first second, which has no last one. Below that it takes the floor's one step in ten
refreshes and no more, and the rate comes back. Beside a light animation the rate is 50
and nothing changes.

**Resolution.** `core/src/player.cpp`, `player_poll`; `core/src/core_state.h`,
`kCheckLeastRate`; `tests/core/support.py`, `CHECK_LEAST_RATE`;
`tests/core/test_power_on.py`, `TheCheck`; `docs/core.md`.

## Seed 20: A drive's entry is 16 bytes

**Question.** The design gives the drive's table twelve bytes an entry, 3,072 in all.
Which size is it?

**Answer.** Sixteen bytes an entry, 4,096 in all. The length of a drive's animation is
kept as wide as that of an installed file, 64 bits, since a file's frame count is a
32-bit number, and an entry with it is sixteen bytes. The target file then asks for
128,701 bytes with a drive, 98 percent of the 131,072 it may use. The core object grew
by 56 bytes for the drive's fields, the name the check reads by among them.

**Resolution.** `core/src/core_state.h`, `DriveEntry`; `tests/core/test_drive.py`;
`docs/core.md`, "Memory".

## Seed 20: Names of a drive's files in a reply

**Question.** The design writes a name as a JSON string with `"` and `\` escaped, a
byte below 32 as `\u00XX` and every other byte as it is. A reply is one line of
printable ASCII, and a name on a drive may be Hebrew, or longer than a reply holds.
How is it written?

**Answer.** In printable ASCII: a character of UTF-8 outside it as `\u` and its code,
one above U+FFFF as two such units, DEL and a control byte by their value, and a byte that
is not UTF-8 as U+FFFD. The JSON a client reads gives the name as the drive has it. The
core asks the host for at most 127 bytes of a name, so that an item of the list always
fits into a reply, even alone: a longer name is listed cut.

**Resolution.** `core/src/commands.h`, `json_escaped`; `core/src/core_state.h`,
`kDriveListedName`; `tests/core/test_drive.py`; `docs/commands.md`.

## Seed 20: An upload and the drive's check

**Question.** Requirement 4.2 has `upload end` answer `busy` while the drive's check
holds the second decoders. Does it?

**Answer.** It never has to. The drive's check gives the decoders up when `upload begin`
is answered, and reads the file it was in again from its start once the upload is
closed. An upload is then never kept waiting for a drive, and `upload end` answers `busy`
only while its own file is checked, as without a drive. While an upload is open the
drive's check waits, as the requirement says.

**Resolution.** `core/src/core.cpp`, `drive_check_yields`; `tests/core/test_drive.py`,
`TheCheckOfTheDrive`.

## Seed 20: The test host's drive lines and faults

**Question.** The design gives the script lines `drive plug <ms>` and `drive pull <ms>`,
and `--drive-read-fails NAME OFFSET` makes a file of the drive fail. When does a line
take effect, and which reading fails?

**Answer.** The lines are `drive plug` and `drive pull`, without a time: the test host
has no clock, and the core sees the change at its next refresh, which the next `poll`
line asks for. `--drive-read-fails` makes `read` fail, the player's reading, and leaves
`read_at` whole: a file whose reading fails in the check is left out as a damaged one
is, which a damaged file tests already, and only so can a test reach a fault while the
file plays. With `--check-first` the drive's files are read before the session too.

**Resolution.** `tests/core/host/host.cpp`; `docs/core.md`, "The test host".

## Seed 20: The reference player has no drive

**Question.** Task 1 gives the reference player of `tests/core/support.py` the drive.
Is it given one?

**Answer.** No. The tests of the drive assert what the core does directly: the order of
the list, the ids, the turns, what a pull and a fault do, and the pictures, against
those of the same file installed. A second model of the drive's check, with its pace
among the steps of the installed check, would repeat the core's code rather than state
what it must do, and every test of the reference player runs without a drive, where the
core is unchanged.

**Resolution.** `tests/core/test_drive.py`.

## Seed 20: A drive needs storage that can be changed

**Question.** A host whose storage cannot be changed has no second decoders. Can it have
a drive?

**Answer.** No. The drive's files are checked by the second decoders, which only a host
with storage that can be changed is given. Such a host's `drive` and `drive_name` are not
called, and the core plays as without them.

**Resolution.** `core/src/core.cpp`, `start`; `tests/core/test_drive.py`; `docs/core.md`,
"The host interface".

## Seed 20: The emulator's drive and record mode

**Question.** The design gives the emulator `--drive DIR`. Does record mode take it, and
what does the page get?

**Answer.** Record mode does not: `--drive` with `--record` is a usage error. The drive's
folder is looked for once a second of the computer's clock, which record mode does not
run on, so a recording with a drive would not come out the same twice. The page's
`hello` has the member `drive` always, the folder of `--drive` or `null`, as it has
`serial` and `tcp`, and the header shows it only when it is there.

**Resolution.** `emulator/app.py`, `parse` and `serve`; `emulator/web/app.js`;
`tests/emulator/test_drive.py`; `docs/emulator.md`, "A drive".

## Seed 20: The firmware before the trial with the adapter

**Question.** Task 4, the trial of the USB host with the owner's adapter, comes before
task 5, the firmware with the drive. May the firmware be written first?

**Answer.** Yes. On 2026-10-14 the owner asked for the firmware with the drive to be built
at once and said yes to the download of the driver's sources. The firmware is built by
the tool and was flashed the same day through the chip's own socket. The tool's wait for
the answer to `status` failed there, as it must: the socket went from the computer when
the firmware switched it to host mode. Whether the firmware answers on the socket marked
COM, whether a drive answers through the adapter, what the board's rate is while a file
of the drive is read, and the board's tests with a drive wait for the board, the drive
and the adapter; until then task 5's box stays empty.

**Resolution.** `firmware/usermod/odrig_drive.cpp`; `firmware/usb_host_msc/`;
`docs/firmware.md`, "A USB drive".

## Seed 20: The probe build keeps its serial port

**Question.** The firmware switches the chip's own socket to host mode for a drive, and
the socket is no serial port from then on. The board's suite talks to the probe build on
that socket. Does the probe build host a drive?

**Answer.** No. It keeps the socket a serial port, so the suite works as before. The
firmware that plays a drive takes its commands, and its flashing, on the socket marked
COM; the chip's own socket reaches its loader with the button BOOT held.

**Resolution.** `firmware/usermod/odrig_usermod.cpp`, `setup`; `docs/firmware.md`.

## Seed 20: Names on the board's drive

**Question.** The core writes a name as the drive gives it. What does the board's file
system give?

**Answer.** The framework's FAT has long names and the code page 850 for them, and it is
built so; it cannot be set without building the framework. A name of the letters `a`-`z`
and `A`-`Z`, digits, `-`, `_` and `.` comes out as it is. A character the code page does
not have, a Hebrew letter for one, comes out as `?`, and the file cannot be opened by
that name: it is left out and logged. The firmware page tells how to name the files.

**Resolution.** `docs/firmware.md`, "A USB drive".

## Seed 20: How the board reads a drive's file

**Question.** The core reads at most 512 bytes in one call. Does each call go to the
drive?

**Answer.** No. Each of the two files that are read has a buffer of 4,096 bytes in memory
the USB unit reaches, so one request to the drive brings eight sectors, and the driver
copies nothing on the way. The list's names, 256 of up to 255 bytes, are in the external
memory.

**Resolution.** `firmware/usermod/odrig_drive.cpp`, `READ_BUFFER`.

## Seed 17: The buttons of the question before a removal

**Question.** The design gives the question before a removal the buttons `Remove` and
`Keep`. Each row of the storage screen has a button `Remove` too. Which words do the
question's buttons have?

**Answer.** `Remove it` and `Keep it`. While the question is open the rows stay on the
screen, and two buttons with the same words, one that asks and one that removes, would
be easy to mix up, for an operator's thumb and for the suite's driver, which presses a
button by its words.

**Resolution.** `app/www/index.html`; `docs/android-app.md`; the design of seed 17.

## Seed 17: A video's pictures are taken at the ticks

**Question.** The design takes each frame of a video after a seek with
`requestVideoFrameCallback`, whose `mediaTime` is the frame's own time. Does that work?

**Answer.** Not reliably: a seek that lands on the frame already on the screen presents
no new frame, and the callback does not come. A trial in Chrome showed that the picture
drawn after `seeked` is the frame on the screen at the time sought. So the app seeks
every 20 ms tick plus half a millisecond from the start of the part, and gives
`importFrames` the picture with the time of its tick. Its timeline takes, at each tick,
the picture on the screen then, which is what the command line takes from the frames'
own times, and ticks with the same picture are joined into one frame as the command line
joins them. A video of the suite gives the command line's frames and lengths, with and
without a part.

**Resolution.** `app/www/convert.js`; `tests/app/test_convert.py`; the design of seed 17.

## Seed 21: How the board sees a computer, and its setting

**Question.** The design looks for a computer with the raw start-of-frame bit of the
chip's unit for serial and JTAG, and has `readFromConfig` answer whether the setting was
there. Is that how it is done?

**Answer.** The frame index of the unit is read instead of the raw bit: the serial driver
of the framework handles the unit's interrupts and may clear the bit before the task
reads it, while the index of the last start-of-frame packet changes each millisecond a
computer is there and only then. `readFromConfig` answers that the settings are complete
whether the member is there or not: an answer of incomplete would make WLED write its
settings file at the start, and the firmware writes nothing on its own. WLED's page shows
the wait from `addToConfig`, and keeps it in `/cfg.json` when the owner saves the page.

**Resolution.** `firmware/usermod/odrig_drive.cpp`, `computerThere`;
`firmware/usermod/odrig_usermod.cpp`; `docs/firmware.md`, "A USB drive".

## Seed 23: How the log is taken, and how the watcher sees a device go

**Question.** The design gives `take` only the room of the line, has the UART write a
line when `availableForWrite` takes it, and has the second client of the USB host close
a device once it has read what it is. Is that how it is done?

**Answer.** `take` gets a third number, the most the UART takes now, so that it hands
over a line only when the whole line fits, and a line that does not fit stays first. The
UART gets a queue of 2,048 bytes for what it writes: without one, `availableForWrite` is
the 128 bytes of the UART's own queue, less than a line may be, and a reply blocked until
its last byte was in that queue. A line is written when the queue has room for it and 32
bytes more, since the driver keeps a short header beside each write. The USB host library
tells only the clients that opened a device that it went, so the watcher keeps the
device it described open until then, and closes it at `a device went`; it is served in
the host's task, between the library's events, every 20 ms at most. A folder `odrig`
that cannot be opened for another reason than its absence gives
`stick not opened: a fault in reading the folder odrig`.

**Resolution.** `firmware/usermod/odrig_log.h`, `odrig_log.cpp`, `odrig_uart.cpp`,
`odrig_drive.cpp`; `docs/firmware.md`, "The log".

## Seed 23: `--log` on Windows, and a closed connection

**Question.** The design has the emulator's suite run `--log` against a target of its own
and stop it, and says that the target's errors are those of a command. How is it stopped
in a test on Windows, and what does a TCP target that closes the connection give?

**Answer.** A test stops the tool as Ctrl-C does, with SIGINT, which Windows cannot send
to another program: the two tests that stop it are skipped there, and the others run. A
TCP target that closes the connection is status 3, `error: unreachable: <address>: the
target closed the connection`, since nothing more can arrive; a serial port that goes
away is status 3 as for a command. Without `--log` and without a command the usage error
says `a command is needed, or --log`.

**Resolution.** `odrigctl/cli.py`, `odrigctl/client.py`, `follow_log`;
`tests/emulator/test_tool_log.py`; `docs/emulator.md`, "The command tool".

## Seed 18: How the answers of Python are stored

**Question.** The design has `tests/converter/make_expected.py` compute, with the Python
package, what the JavaScript suite compares with, in a compact form for each kind of
request, and has the import tests read media files of `converter/tests/media/`. The inputs
of most comparisons are made by the JavaScript tests themselves, from seeds. How is it done?

**Answer.** The suite records them itself. Every request a test makes of Python, a
request of `reference.py` or a command line of the Python tool or of a generator, goes
through `converter/tests/stored.js`, which keeps it under a key made of what it asks: the
request and its input, with the temporary folders and the repository written as names,
the files of those folders as they were before it, and every other file its command line
names. With it are kept its answer and the files it made, wrote and removed.
`make_expected.py` runs the suite in the mode that records, and writes one file of answers
for each kind of request, compressed when it is larger than 64 KB, and each written file
larger than 16 KB apart in `files/`, compressed and named by its SHA-256. A run of more than
64 hexadecimal digits in an answer is kept as a digest, the first 16 digits of its SHA-256
and its number of bytes, except in the answers of `deflate`, the streams the inflater's
tests go on to read. The media of the import tests are the files the `media` request
wrote, kept as its answer, and the generators' animations are the files they wrote. All of
it takes 4.2 MB. Without `ODRIG_EXPECTED` a request asks Python and checks that its answer
and its files are the stored ones, so the suite as it runs checks every stored answer
against what Python answers today; the kinds whose tests compare digests where the
answers hold them take the stored answers without Python, kind by kind.

**Resolution.** `converter/tests/stored.js`, `support.js`, `expected.test.js`;
`tests/converter/make_expected.py`; `converter/tests/expected/`.

## Seed 18: The compressor's bodies without Python

**Question.** The compressor's tests measured it on bodies the Python tool encoded from
its generators, among them a dense 60 x 60 clip of 1 second and one of 10 seconds, whose
time they also took. Without Python the bodies have to come from stored files, and the
generator's file of the clip of 10 seconds alone would take some 7 MB. What do they use?

**Answer.** The six bodies are those of the generators' files that the other tests store
already: Hello world, DVD bounce and the dense clip of 2 seconds, on 60 x 6 and on 60 x 60.
The encoder writes each, and its uncompressed file is checked against the Python tool's;
zlib's length is that of the Python tool's compressed file. The time is taken on the body of
the dense 60 x 60 clip of 2 seconds five times over, 5.4 MB: its repeats lie farther apart
than the compressor looks back for a match, so it has the work of a clip of 10 seconds, and
its stream is at most 5 percent larger than five of zlib's. The tests of the encoder, the
decoder, the compressor and the inflater, and the checks of the vectors, take the stored
answers without Python: the kinds `check`, `cli`, `decode`, `deflate`, `encode`, `forms`,
`generators` and `inflate`.

**Resolution.** `converter/tests/deflate.test.js`, `encode.test.js`, `inflate.test.js`,
`stored.js`.

## Seed 18: The import's tests without Python

**Question.** The tests of the fit, the timeline, the import and the arithmetic of whole
numbers compare pictures and animations with what Python answers. Where the stored answer
keeps a picture as a digest, how is a difference shown?

**Answer.** A test puts what it made into the form of the stored answer, each run of
hexadecimal digits where the answer has a digest as the digest of its own bytes, and
compares the two; a difference names the case, no longer the pixel. The kinds `mappings`,
`media`, `milliseconds`, `rects`, `resample`, `run`, `sixdigits`, `ticks` and `timeline`
take their stored answers without Python. The test of the check against Python sets that
mode for its own requests, since no kind of its own is left in it.

**Resolution.** `converter/tests/stored.js`, `inStoredForm`; `fit.test.js`,
`timeline.test.js`, `expected.test.js`.

## Seed 18: The helpers without Python, and the maker of the stored answers

**Question.** Task 4 removes `reference.py` and every helper of the tests' support that
starts Python, and task 5 removes `tests/converter/make_expected.py`. The maker records by
running the converter's suite in a mode in which those helpers ask Python. What becomes of
the maker, and of the tests' names for what they compare with?

**Answer.** The maker goes in task 4, with the helpers it needs: from then on the stored
answers are the record, as the design says they are once the converting parts go, and
nothing can make them again. The helpers that gave Python's answers give the stored ones
under names that say so: `storedAnswer` for a request, `storedRun` for a command line of
the Python tool, `runJsAndStored` for both tools, `storedChecks`, `storedRuns` and
`storedGenerated`. The modes that asked Python go with them. The section "Tests" of
`docs/converter.md` says where the answers are in the same task, since `ODRIG_PYTHON`,
which it named, is gone; the rest of the pages follow in task 6. A test runs the helpers
with only Node.js on the path, with every way of starting a program refused for a name
that holds `python`.

**Resolution.** `converter/tests/support.js`, `stored.js`, `expected.test.js`, the test
files of the converter; `docs/converter.md`, "Tests".

## Seed 18: What replaces the parts of the Python package that go

**Question.** With `cli`, `__main__`, `media` and `pack` gone, the suites that packed
shows with `pack.pack`, the media that the walk-through and the app's suite drew with
Pillow and PyAV, and the pages and checks that named `python -m odrig` or installed
`requirements.txt` need another way. Which?

**Answer.** One helper packs for the suites of the core, the emulator, the firmware tool and
the board: `pack_with_the_converter` of `tests/core/support.py`, which runs
`node converter/odrig.js pack` and which the other supports import; the emulator's test of
the demo show runs the converter's `pack` itself, as its page does. The core's benchmark
encodes its clip with the converter, and the uncompressed clip is the same file as
before. The GIF of the walk-through and the media of the app's suite are stored in the
programs that wrote them, as their bytes, since no media file is tracked in the
repository; the files they write are those Pillow and PyAV made before. The helper that
gives a command line its exit status moves to `errors` as `status_of`. The Python tests
of the removed modules go, and those of the show reader stay in `test_show.py`. The setup
of the getting-started page makes `.venv` and installs nothing into it, and the check of
the pages' commands refuses `python -m odrig` and `pip`. The vocabulary's entry of the
Python package no longer starts it as a program; the rest of the pages follow in task 6.

**Resolution.** `odrig/`; `tests/core/support.py`; `core/Makefile`;
`tests/walkthrough/make_gif.py`; `tests/app/media.py`; `agent/getting-started.md`,
`agent/vocabulary.md`; `tests/onboarding/support.py`.

## Seed 24: How a table is named

**Question.** The design has `layout_of` name a table WLED's layout or the bigger one by its
entries, and refuse any other. The tool has always taken any table with a firmware slot at
`0x10000` and a storage named `spiffs`, and its suite runs on tables whose storage is a few
blocks. What does it name?

**Answer.** A table is named by its firmware slots: with a second one it is WLED's layout,
with one alone the bigger one; the size the line gives is that of the table's storage. A
table without a slot at `0x10000` that the image fits in, or without `spiffs`, is refused as
before, with `layout-mismatch`. The move to the bigger layout, which writes where WLED's
layout has its second slot, takes WLED's table only as it is, entry for entry.
`install-firmware` prints the line once, before it writes the firmware.

**Resolution.** `firmware/fwtool/partitions.py`, `layout_of`, `layout_line`;
`firmware/fwtool/cli.py`.

## Seed 24: Reading the size of a grown file system, and the way back's read

**Question.** The tool reads the disk version, the block size and the number of blocks of
the storage from the figures that follow the superblock's mark. The storage that
`big-storage` makes is grown from 3 MB to 13.5 MB, and littlefs keeps the grown figures in
a later commit of its first block, where they no longer follow the mark; after a show is
installed into it, no copy of the figures follows the mark at all. And `restore-stock
--full` never read the board before. How are they done?

**Answer.** The tool asks littlefs: it mounts the image with the block size of a copy of
the figures that follows the mark, or else with each of the usual block sizes, 4,096 first,
and takes the figures littlefs reads from the newest commit of the superblock. A test
installs a show into the storage the move leaves and reads it back. `restore-stock --full`
now reads the board's partition table first, to know whether WLED's storage has to be
written; a table it cannot read is a board that gets the stock files as before.

**Resolution.** `firmware/fwtool/storage.py`, `geometry`, `with_settings`;
`firmware/fwtool/cli.py`, `_big_storage`, `wleds_storage`.

## Seed 24: What WLED's information says of an update over Wi-Fi

**Question.** The design has the firmware refuse an update over Wi-Fi on a board without a
second slot. How does the owner see on the board which way it goes, before trying one?

**Answer.** WLED's information has an entry `odrig update`: `refused: no second slot` where
the refusal is registered, `WLED's` where WLED's own update works. The page's table of the
information names `odrig drive` too, which it had left out.

**Resolution.** `firmware/usermod/odrig_usermod.cpp`, `addToJsonInfo`; `docs/firmware.md`.

## Seed 25: The check that nothing depends on a long press

**Question.** The app's suite checks that the web code listens to five events, `click`,
`input`, `change`, `visibilitychange` and `popstate`, so that nothing of the app depends
on hovering, a long press or a swipe. The listener that stops the menu of a long press is
a listener of a sixth, `contextmenu`. Does the check still hold?

**Answer.** It does, and it now says so: it takes `contextmenu` among the events, and
checks that its one listener, at the start of the app, only stops the menu outside the
fields and does nothing else. No action of the app is done by a long press.

**Resolution.** `tests/app/test_look.py`, `Touch`; `app/www/main.js`.

## Seed 25: Where a long press is tried on a phone

**Question.** The step of the check on a phone holds a finger on buttons. Whether a long
press on a button of Android's web view also presses it, once its menu is stopped, no
program here can tell. Which buttons does the step use?

**Answer.** `On`, which does no harm while the installation is on, and an animation,
which plays it. The step asks only that no text be marked and no menu open there, and
that the buttons still work by a tap, and to note whether a long press on a button
pressed it too.

**Resolution.** `docs/android-app.md`, "The check on a phone", step 13.

## The converter on Windows: its suite passes there

**Question.** The converter's suite, `npm test --prefix converter`, did not pass on Windows.
Seed 18 took the Python converter out, and the suite now compares with the answers of the
Python package stored in `converter/tests/expected/`, which were recorded on macOS. What
failed on Windows, and how do the same stored answers serve both systems?

**Answer.** The suite passes on Windows 11: 1317 tests, none failed and none skipped. What
failed there, and what was done:

- Two faults of the JavaScript tool. Windows refuses a folder that is written over as if
  for want of permission, a path below a file as if nothing were there, and a file whose
  right is denied with EPERM. The tool said `EPERM`, `No such file or directory` and
  `Operation not permitted` there, where macOS says `Is a directory`, `Not a directory`
  and `Permission denied`. On Windows it now looks at the path and says what macOS says.
  The files it writes do not change. One test gave Node.js a path for `--import`, where
  Windows needs a file URL.
- 115 tests found no stored answer: a request's key came out other than on macOS. Paths
  below a temporary folder or the repository kept the separator `\`, a file in a temporary
  folder was taken for one outside it, and the files of a folder came in the order Windows
  lists them. The key now joins such paths by `/` and puts the files in the order of their
  names, as Node.js gives them on macOS. A stored answer is read with the separators of the
  system, and a path the command line gave keeps the spelling it was given.
- The key of six requests of `pack` held a file the recording computer had in `animations/`
  beside the two tracked ones, most likely a `.DS_Store`. A folder of the repository now
  counts only what git tracks, and the six answers have new keys.
- In the import tests the JavaScript tool wrote its files into the folder of the media,
  whose files are part of the key of every request of the Python tool. The pictures decoded
  from a video differ by a colour value or two from one build of FFmpeg to another: on the
  recording computer the JavaScript tool's imports of the videos had the Python tool's
  bytes, on Windows 51 of 55 do not. The JavaScript side now writes into a folder of its
  own, and the 32 requests from the videos on have new keys; each answer was found by the
  files it wrote or by the JavaScript tool's answer to the same command line. Three tests
  that compared an imported video byte for byte compare it by its frames, no colour value
  more than 3 apart, as the test of the videos does.
- Windows lets no ordinary user make a symbolic link; the test that puts Node.js alone on
  a path copies it there.
- The three tests of a file that may not be read or a folder that may not be written into
  were skipped on Windows. They now take the right away by an entry of the access list,
  with `icacls`, where macOS and Linux use the mode.
- The test in Chrome asked Chrome its version with `--version`, which opens a window on
  Windows. It now reads the version from the DevTools of the headless Chrome it starts.

Every stored file holds as many answers as before; 38 of them have new keys, each as it
was. One point stays open: the import tests write `CLIP.MP4` and `Clip.MoV` beside
`clip.mp4` and `clip.mov`, which macOS and Windows take for the same files. On a system
that tells them apart, as Linux does, the keys of the later import requests differ, as
they did before.

**Resolution.** `converter/tests/stored.js`; `converter/tests/support.js`, `forbid` and
`allowAgain`; `converter/tests/import.test.js`, `expected.test.js`, `browser.test.js`,
`cli.test.js`, `pack.test.js`; `converter/tests/expected/cli.json.gz` and `run.json.gz`;
`converter/cli/files.js`, `why`; `AGENTS.md` and `agent/getting-started.md`, On Windows.

## Seed 22: Which newer software, and where its hubs come from

**Question.** The seed names a version of Espressif's software that knows hubs, ESP-IDF
5.5 or later, and leaves open which one and how. Arduino-ESP32's libraries come compiled,
and the configuration they are compiled with leaves the hub support of ESP-IDF's USB host
off, as ESP-IDF does unless it is switched on. Which software, and how does the firmware
get hubs?

**Answer.** Arduino-ESP32 3.3.12 on ESP-IDF 5.5.5, with pioarduino's platform
55.03.312-1, its newest release that is not a test release, of 2026-09-22; it needs
PlatformIO 6.2.0. The hubs come from ESP-IDF 5.5.5's own USB host library, taken into
`firmware/usb_host/` and compiled with its hub support on, as the driver of flash drives
was taken into `firmware/usb_host_msc/`. The support is ESP-IDF's driver of the hub class
of the USB standard, and nothing of it names a hub. The other way, having the platform
compile all of Arduino-ESP32's libraries again with ESP-IDF and the option on, fetches
ESP-IDF itself, its Python packages and some thirty components besides what this way
fetches, and its exact list is known only when it runs. The driver of flash drives stays
1.1.1, which Espressif gives for ESP-IDF 4.4.1 and later; 1.1.4 is on the list of
downloads only for the case that 1.1.1 does not build. Should the owner prefer the other
way, the list changes before anything is fetched.

**Resolution.** `docs/specs/22-p2-a-usb-stick-through-a-hub/design.md`, "The newer
software", "The USB host library with hubs" and "What the trial fetches".

## Seed 22: The newer software beside the build known good

**Question.** The trial build needs PlatformIO 6.2.0 and a platform of its own, where the
firmware's build has the PlatformIO 6.1.17 that WLED pins; and stock WLED is still built
on the older software after the move. How do the two live in one work folder?

**Answer.** The newer software has a folder of its own, `build/firmware/newer/`, with its
Python environment, its PlatformIO folder and its build cache; pip's and npm's caches are
shared, since they only keep what was fetched. `build --trial` and `build --trial --probe`
build on it, into images with names of their own, so the image known good is never
replaced. After the move the firmware and its probe build take the newer folder, and
`build --stock` keeps the older one. The PlatformIO of the newer folder is PlatformIO's own
6.2.0, which the platform asks for; the platform installs pioarduino's PlatformIO into a
Python environment of its own for itself.

**Resolution.** `docs/specs/22-p2-a-usb-stick-through-a-hub/design.md`, "The tool" and
"The move".

## Seed 22: What counts as WLED building on the newer software

**Question.** The seed ends the trial when WLED does not build on the newer software. How
much change of WLED's source does the trial allow before it says so?

**Answer.** A change that WLED's source needs goes into a patch file of
`firmware/patches/`, each change held to the newer software by `ESP_IDF_VERSION_MAJOR`, so
that the build known good stays as it is. A change of WLED's drivers of the LEDs, the
Wi-Fi or the storage, or a library that has no version for the newer software, ends the
trial: that is no longer WLED 16.0.1 as it is, and the owner decides.

**Resolution.** `docs/specs/22-p2-a-usb-stick-through-a-hub/requirements.md`, 1.5;
`design.md`, "The USB host library with hubs".

## Seed 22: The board's suite on the trial build

**Question.** The trial asks that the board's suite pass on the trial build. The suite
flashes the firmware and the probe build under the names the tool keeps them by, which the
trial does not replace. How does it run on the trial build?

**Answer.** The trial has a probe build too, `build --trial --probe`, and the suite takes
the trial's two images where it takes the firmware and the probe build when the variable
`ODRIG_BOARD_IMAGES` is `trial`. No command of the tool is added for it, and both go at the
move.

**Resolution.** `docs/specs/22-p2-a-usb-stick-through-a-hub/design.md`, "The tool" and
"The trial on the board"; `tests/board/support.py`.

## Seed 22: The log of a device that goes, and of a device on a hub

**Question.** The seed asks for a line when a hub comes and when it goes. The log says
`a device went` for any device, and its watcher keeps only the first device open, so it
is told only of the first that goes.

**Answer.** The watcher keeps up to eight devices open, each with its numbers and its
kind, and the line of a device that goes names it as its line of coming did:
`a device went: maker 1a40, product 0101, a hub`. On the newer software the line of a
device that comes behind a hub ends with `, on port <n> of a hub`. Eight is more than a hub
with a stick brings.

**Resolution.** `docs/specs/22-p2-a-usb-stick-through-a-hub/requirements.md`, Requirement
3; `design.md`, "The log of what comes and goes".

## Seed 22: Two sticks through one hub

**Question.** Through a hub two sticks can be plugged in at once. The seed says nothing of
it.

**Answer.** One stick is read at a time, as the firmware does today: a second one that
comes is passed over until the first goes. Reading two would change seed 20's list and
its names, which is not this seed's work.

**Resolution.** `docs/specs/22-p2-a-usb-stick-through-a-hub/requirements.md`, 2.5.

## Seed 22: The hub support is already in Arduino-ESP32 3.3.12

**Question.** The design builds ESP-IDF 5.5.5's USB host library with its hub support on,
as a library of the repository, because Arduino-ESP32 comes with that library compiled.
Is the compiled one without hubs?

**Answer.** No. Every memory variant of the ESP32-S3 in Arduino-ESP32 3.3.12's compiled
libraries, `qio_opi` of this board among them, has `CONFIG_USB_HOST_HUBS_SUPPORTED 1`
and `CONFIG_USB_HOST_HUB_MULTI_LEVEL 1` in its `sdkconfig.h`, and its `libusb.a` is built
so. The trial takes the compiled library as it is: no `firmware/usb_host/`, no source of
ESP-IDF in the repository or fetched for it, and no flags for its options. The support is
still the USB standard's own, with nothing for one maker or model.

**Resolution.** `docs/specs/22-p2-a-usb-stick-through-a-hub/design.md`, "The USB host
library with hubs"; `docs/firmware.md`, "The newer USB software".
## Seed 27: Where the room of the bars comes from, and the colour behind them

**Question.** The seed asks for the room of the bars from what the phone reports, and for
black behind the bars with readable icons, and allows the Android project to change only
where the web code cannot. What does the page read, and what changes in the Android
project?

**Answer.** Capacitor 8.5.3, already installed, has a core plugin `SystemBars` that sets
the room at each side as four CSS variables on the page's root, and in a web view of
version 140 or later also as `env(safe-area-inset-*)`. The page takes the variable, else
the web view's value, else nothing, so a browser sees no room. The plugin's setting
`style` `DARK` makes the bars' icons light. The plugin paints the window behind the page
with the theme's window background, which is light in the app's theme, so that theme gets
a black one. Both are settings of the Android project; no Java changes and no package is
added.

**Resolution.** `docs/specs/27-p1-the-app-clear-of-the-phones-bars/design.md`, "The style
sheet" and "The Android project".

## Seed 27: How the page knows that the keyboard is open

**Question.** The seed asks that the tabs not ride up over a field when the keyboard
opens. The page has no word from the phone that the keyboard is open, and Capacitor's
plugin of the keyboard is a package the app does not have.

**Answer.** When the keyboard opens, the plugin of the bars pads the window at the bottom
by the keyboard's height, so the page's view gets lower. The page keeps the tallest
height its view has had at each width, and takes the keyboard for open while a field one
types into has the focus and the view is lower than three quarters of that height. Then
the tabs are hidden and the field is scrolled into view. In a browser the view does not
get lower when a field has the focus, so nothing changes there.

**Resolution.** `docs/specs/27-p1-the-app-clear-of-the-phones-bars/design.md`, "The
keyboard".

## Seed 27: What scrolls under the bar at the top

**Question.** The page scrolls as a whole. With room kept at the top, what scrolls up
would still pass under the clock. How do the screens scroll within the app's area?

**Answer.** A band of the app's black, fixed at the top and as high as the room there,
lies over the page; what scrolls up goes under it. The page still scrolls as a whole, as
the tests of the screens expect, and in a browser the band has no height.

**Resolution.** `docs/specs/27-p1-the-app-clear-of-the-phones-bars/design.md`, "The style
sheet".

## Seed 38: Which file systems of a card the firmware reads

**Question.** The seed says the card's file system is "FAT32 as a card comes". Arduino's
`SD` library mounts a card with the chip's FatFs, which reads FAT16 and FAT32, and reads
exFAT only when it was compiled with it, which the compiled libraries of Arduino-ESP32
3.3.12 may or may not be. What does the firmware promise?

**Answer.** FAT32 and FAT16: a card of 32 GB or less as it comes from the shop, or any
card formatted FAT32 on a computer. A card above 32 GB comes as exFAT, which is not
promised; the owner formats such a card FAT32 on a computer before use. Names are kept to
the letters `a`-`z` and `A`-`Z`, digits, `-`, `_` and `.`, as for the stick: another
letter may come out as `?` and such a file cannot be opened by its name and is left out.
The owner's card of 122 animations has such names.

**Resolution.** `docs/specs/38-p1-a-microsd-card-as-the-external-storage/requirements.md`,
2.1 and 2.2; `design.md`, "The card".

## Seed 38: The emulator and the card

**Question.** Seed 20 gave the emulator an option `--drive DIR`, a folder that stands in
for the stick. Does the emulator change for the card?

**Answer.** No. The core knows "a drive": a number that changes when one comes and is 0
while none is there, and a list of names. Whether the firmware fills that from a USB stick
or from a card is the host's matter, and the emulator's folder stands in for either. The
app shows the external animations the same way. Nothing of the core, the emulator or the
app is touched by this seed; the words "drive" and "USB drive" in their documents mean the
external storage, and `docs/show.md` gets one sentence that says so.

**Resolution.** `docs/specs/38-p1-a-microsd-card-as-the-external-storage/design.md`,
"What does not change".

## Seed 38: Codex's pages, `docs/microsd.md` and `docs/microsd-preflight/`

**Question.** Codex wrote `docs/microsd.md` and six files under `docs/microsd-preflight/`:
two records of the board sessions of 2026-10-22 and 2026-10-23, and four checklists of its
own. `docs/` holds the documents that define the project, and a checklist of a session
is not one. What becomes of them?

**Answer.** `docs/microsd.md` stays and becomes the card's page, in the house style: how
to prepare a card, the reader's wiring as the owner reported it, the build, flashing, the
log's lines, WLED's information, what the two board sessions gave, and what is open. The
two records are folded into it, the four checklists are superseded by this spec's
`tasks.md`, and the folder `docs/microsd-preflight/` goes, with every link to it. Until
the documents task is done, the pages stay as Codex wrote them, so that nothing is lost
in the meantime.

**Resolution.** `docs/specs/38-p1-a-microsd-card-as-the-external-storage/design.md`,
"The documents"; `tasks.md`, the documents task.

## Seed 38: The dropouts of 2026-10-22 are found out, not solved

**Question.** In the first board session the card's entries disappeared and were found
again, at 4 MHz, 1 MHz and 400 kHz alike; in the second, with both USB sockets of the
board on the Mac, nothing was lost in fifteen minutes. Does this seed undertake to solve
the dropouts?

**Answer.** It undertakes to find out whether they are still there, with the cable
arrangement the owner names for the event, and to record what was seen, with the evidence
kept before anything is changed: the log's lines, `status` and `list` over time, and the
image's hash. A cause inside the card's code or its clock that the session shows is this
seed's to mend, since the card's firmware is its subject. A cause in the wiring, the
power or the reader is the owner's, and what follows from it becomes a new seed. Slower
clocks are not tried again: they did not help on 2026-10-22.

**Resolution.** `docs/specs/38-p1-a-microsd-card-as-the-external-storage/requirements.md`,
Requirement 9; `design.md`, "The board session".

## Seed 38: The seed is added in progress

**Question.** The working rules have a seed added as `remaining`, and the first task of
its spec set it to `in_progress`. This seed's first five tasks are Codex's commits of
2026-10-22 and 2026-10-23, made before the seed existed. Which state is the seed added in?

**Answer.** `in_progress`, in the commit that adds it. The spec's `tasks.md` ticks those
five tasks and names their commits, so the rule is met in substance: the state was set by
the commit that accounts for the work already done. `remaining` would say that nothing
has begun, which is false.

**Resolution.** `project-seeds/38-p1-a-microsd-card-as-the-external-storage/state.json`;
`docs/specs/38-p1-a-microsd-card-as-the-external-storage/tasks.md`, tasks 1 to 5.

## Seed 38: The stick's code and the hub's trial stay

**Question.** The card takes the stick's place. Do the stick's code, `build --trial` and
the trial's environments go now?

**Answer.** No. The owner's decision of 2026-10-21 keeps the USB build available, and the
one of 2026-10-24 keeps the move to the newer software, which the card's build is built
on: `build` goes on building the firmware with the stick's code on the software known
good, `build --trial` the hub's trial, and `build --microsd` the card's firmware, in the
same folder `build/firmware/newer/`. Where the documents call the newer software "the
trial", one sentence says that the microSD build uses the same software. Whether the
card's build becomes the firmware that `build` makes, and the trial's environments and
`ODRIG_BOARD_IMAGES=trial` go with that move, is the owner's question 8 of the seed; the
last tasks wait for it.

**Resolution.** `docs/specs/38-p1-a-microsd-card-as-the-external-storage/requirements.md`,
Requirement 10; `design.md`, "What does not change" and "What needs the owner".

## Seed 38: The log's kind `sd`, and `odrig drive` in WLED's information

**Question.** The seed asks for "the same log" as the stick. Codex's code writes the
card's lines with the kind `sd`, where the stick's have `usb`, and keeps WLED's
information entry under the name `odrig drive`. Which names does the spec take?

**Answer.** Those built: the lines of the card are of the kind `sd`, since they say what
the card does and not what a USB port sees, and `odrig drive` keeps its name in WLED's
information, with the card's states in it, so that the documents and the owner's habits
keep one name for the external storage. The player's lines, `drive file <name> left out:
<reason>`, stay as they are for the card.

**Resolution.** `docs/specs/38-p1-a-microsd-card-as-the-external-storage/requirements.md`,
Requirements 3 and 5; `design.md`, "The log and WLED's information".

## Seed 38: The card's free and total space

**Question.** Seed 29, on `master` since 2026-10-24, gave the core an optional host
function `drive_space`, and the stick's code answers it from the FAT volume of the USB
driver. Codex's card code was written before and has no such function; merged as they
are, the card's build would not compile, since the stick's function names what the card's
build leaves out. What does the card's build answer?

**Answer.** The card's numbers, from Arduino's `SD` library: `totalBytes()` and
`usedBytes()`, which read the volume's free clusters and write nothing; free is total
minus used. The function answers only while the card is mounted and the number asked for
is the card's current number, with the same guard as every other call, and -1 otherwise,
so `space` reports the card present with null capacities when the numbers cannot be read.
This is done in the commit that merges `master` into the seed's branch, with the test
that compiles the card's code against the stand-in card, since that commit is the first
in which both sides exist.

**Resolution.** `docs/specs/38-p1-a-microsd-card-as-the-external-storage/requirements.md`,
2.6; `design.md`, "Free and total space"; `tasks.md`, task 6.
## Seed 26: what failed on Windows, and three points the spec had otherwise

**Question.** Seed 26 makes every suite that runs on Windows pass there again. Where did
the work come out otherwise than the spec said?

**Answer.** The causes were those of the design, and so were the fixes, with three
differences.

- The design gave the app's suite a line in the Windows list of commands of
  `agent/getting-started.md`. That list has to match the list "Run the tests", which the
  onboarding suite checks, and that list has no app's suite: its command is in
  `docs/android-app.md`. So the page names the app's tool among what works on Windows, and
  the list stays as it is.
- The definition of done said that no suite skips on Windows a test it runs on macOS. The
  emulator's suite skips the 19 tests that need a virtual serial port, which Windows does
  not have, and the core's suite skips one test of file names that Windows does not allow,
  both as before this seed. The definition now says so.
- The design made the stand-ins for `sdkmanager`, `adb` and `node` `.cmd` files on
  Windows. Each is now a few lines of Python on every system, started by a `#!` wrapper
  where the system has one and by a `.cmd` file on Windows, so a stand-in has one text.
  And the preview tests stop every preview they start at the end of the test, also when
  the test fails: a failed test had left a preview holding port 8600 for the tests after
  it.

On Windows 11 with Python 3.14 every suite passes, run one at a time, with nothing left
running after it: the converter's 1317 tests, none skipped; the Python library's 465; the
core's 504, 1 skipped; the emulator's and the command tool's 565, 19 skipped; the app's
144, none skipped; the onboarding suite's 81.

**Resolution.** `emulator/host.py`, `reading`; `preview/__init__.py`, `waited` and
SIGBREAK; `odrigctl/cli.py`, SIGBREAK for `--log`; `app/apptool/webserver.py`,
`allow_reuse_address`; `tests/emulator/test_binding.py`, `test_preview.py`,
`test_tool_log.py`, `test_demo.py`; `tests/app/support.py`, `test_emulator_view.py`,
`test_tool.py`; `AGENTS.md`, `agent/getting-started.md`, `docs/emulator.md`;
`docs/specs/26-p1-every-suite-passes-on-windows-again/requirements.md`.

## Seed 29: The scope and meaning of ignoring an animation

**Question.** The owner requested a playlist toggle in the Android app, emulator and
serial tool. Does ignoring delete or hide an animation, affect explicit play or cycles,
or apply to a removable drive? What happens when all installed animations are ignored?

**Answer.** The setting belongs to each animation in the writable installed show and
survives restarts. It only excludes automatic playlist turns. Explicit play still gives
an ignored animation one normal turn, and explicit cycles keep their contents. Drive
animations remain outside this seed. Ignoring the current playlist animation advances
immediately; an empty eligible playlist becomes idle and black without changing the
on/off setting. Including an animation while idle resumes the playlist. The shared
web app supplies one labelled toggle everywhere it runs. The command is an idempotent
`ignore <id> <0|1>`, with an optional boolean `ignored` in show items and a boolean in
installed animation list replies. New uploads are included; replacements preserve the
setting. This plans the owner's requested extension of the default playlist decision;
implementation must update the defining documents and their change log together.

**Resolution.** `project-seeds/29-p1-toggle-animations-in-the-playlist/seed.md` states
these choices, including startup, errors, persistence, synchronization and checks.
The entry file lists the planned seed. No runtime behavior changes with this record.

## Seed 30: Reassign whole snakes and check them with one diagonal

**Question.** The owner requested app-controlled pin-to-snake mapping and a diagonal
animation in one seed. Does this include arbitrary GPIOs, changes within a snake or
automatic detection of wiring? Is the test an ordinary uploaded playlist item?

**Answer.** The feature permutes the twenty output pins of the target's valid mapping
among the twenty fixed three-column snakes. It does not choose new pins or alter the
geometry, snake directions, wiring or power. The app edits a draft and saves the whole
assignment in one durable operation to the existing mapping file. A built-in diagnostic
animation shows only white pixels at x = y on black, through the normal decoder and
mapping pipeline, until stopped. It does not need an upload or join the playlist. The
shared app controls both features on Android and in the emulator; all target operations
also use the common command routes. An operator verifies the physical line by eye.
The seed specifies startup, conflicts, failures, test-mode exit and compatibility.

**Resolution.** `project-seeds/30-p1-app-mapping-and-diagonal-check/seed.md` records
the combined scope and resolved behavior. Implementation must update the default-pin
and command decisions and the defining documents together. No installed mapping,
firmware, animation or hardware is changed while creating the seed.

## Seed 30: Mapping protocol, asset and output handoff

**Question.** How can twenty pins be saved within the existing line limit, conflicts
be detected across restarts, and a diagnostic be shipped without consuming user
animation storage? The firmware also caches startup leg descriptors.

**Answer.** Use `mapping get`, `mapping set REV PINS` with a comma-separated complete
permutation and the CRC-32 of current pin bytes, and `mapping test on/off`. Serialize
to mapping.part and commit by atomic rename. Probe and discard a leftover part at
startup without changing ordinary startup storage-call numbering. Embed the same
converter-produced ODRG bytes in the core and decode once into existing playback
memory. Freeze physical output resources and refresh their cached RGB pointers by
matching the new logical leg assignment to each physical pin under the core lock.
The fallback currently remains a seed-12 trial; its output adapter can share this
routing contract without claiming a completed standalone player.

**Resolution.** The seed-30 design, core mapping_control implementation and command,
mapping and core documentation specify these choices. Hardware acceptance remains
explicitly deferred because the owner requested no flashing in this run.

## Seed 30: Keeping transport inventories consistent during implementation

**Question.** The core and documentation now expose a mapping command family, while
the command tool's inventory was assigned to the later app task. Host integration
verification checks that those inventories agree.

**Answer.** Add the command tool's basic mapping argument forms in the transport task,
with the corresponding inventory fixtures. Keep app controls and end-to-end client
scenarios in the following task. This changes task ownership, not seed scope. Keep
physical driver resources stable and change cached pointers under one lock instead
of rebuilding outputs while another processor copies a refresh.

**Resolution.** Seed-30 tasks 2 and 3, the command tool, firmware routing helper and
emulator mapping events carry the integration boundary. Per-pin byte regressions
were observed failing with the old cached assignment before the host changes.


## Seed 30: Recovering an uncertain save in the shared app

**Question.** A mapping save may commit even when its reply is lost. Background reads
and target changes must not silently replace the operator's unsaved assignments.

**Answer.** Serialize mapping requests with the app's existing command stream. Keep a
local draft and its base revision, poll only while Mapping is visible, and block a stale
save until Reload or Cancel. After a failed mutation read once, keep the draft, and
require an explicit reload before another attempt. Never repeat the write automatically.
Changing the target clears the draft and rejects replies from the previous target.
The diagnostic is target-owned and stays active through app navigation or restart.

**Resolution.** The shared Mapping screen and browser regressions cover swaps, save,
cancel, default drafts, concurrent edits, lost replies, target changes, app restarts,
unsupported targets and both portrait and landscape. Four bottom tabs use equal widths
and 16px labels to fit at 320px while keeping 56px touch targets.


## Seed 30: Keeping the packaged diagnostic outside example fixtures

**Question.** The fresh-checkout walkthrough failed after the new tracked diagnostic
source changed the directory digest of `animations/`, used by the converter's stored
reference requests. Before the source was tracked, that suite had passed locally.

**Answer.** Keep the diagnostic JSON in `core/assets/`, beside the player that packages
it. Update the converter-only asset generator and mapping documentation to that path.
Leave the example sources, frozen reference answers and converter output unchanged.

**Resolution.** The fresh-checkout failure was observed before moving the file. The
converter's 1,317 tests then passed with the source tracked at its final location, the
asset regeneration check still produced the same 45 bytes, and all 29 mapping tests
passed. Both firmware builds and the rebuilt APK are retained without flashing; real
installation and phone acceptance remain the owner's later task.


## Seed 30: Preserving APK update identity across worktrees

**Question.** A build in the temporary worktree generated a new debug signing key. The
resulting APK's certificate differed from the previously published APK's certificate.

**Answer.** Build the delivery APK with the existing local debug keystore, copied only
into the worktree's ignored build folder. Verify both APK certificate hashes and rerun
the APK suite against that final signed file. Never track or publish the keystore.

**Resolution.** The rebuilt APK has the same signer as the existing public APK and all
eight APK checks pass. Its final hash is in the verification record. The branch carries
only source and documentation; APK binaries and local key material remain ignored.

## 2026-10-24 — playlist storage transactions

The owner's expanded playlist-management request authorizes ignore and remove many
on every existing command route. Batch commands accept at most 32 distinct installed
animations; the app chunks larger selections and reports partial failure. Shared
files survive any remaining reference. The existing chunk of 1,500 bytes also bounds the
recovery journal, extended from 512 bytes. Failed cleanup blocks subsequent show
mutations until restart retries it, preventing journal overwrite. Explicit false is
preserved; omitted ignored remains omitted until changed. External capacity is an
optional fact supplied by the host, never a new permission to write removable media.

## Seed 29: mutation controls on an older target

**Question.** An older list reply omits `ignored` on every animation, while the shared
protocol now omits it only on external entries. Can the app infer editability from ids?

**Answer.** No. An installed animation can have an id above60000. Keep playback controls
but omit inclusion and deletion controls wherever the flag is absent. A missing external
capacity object means unavailable, rather than inventing absent media. The core remains
the authority for every mutation and capacity fact.

**Resolution.** `app/www/commands.js`, the Show and Storage screens, and
`docs/android-app.md` describe and implement this compatibility behavior.

## Seed 28: where the two numbers stand

**Question.** The seed asks for a line of its own for the external number, hidden when no
medium is plugged in, but seed 29 has since put a line of the external storage's capacity
on the same dashboard, which says `absent` when there is none. Two lines about one medium?

**Answer.** One line each, the lines seed 29 made: the number goes before the capacity,
`Internal storage: 84 animations, free …` and `External storage: 12 animations, free …`.
While the medium is absent, the external line says `absent` with no number and no label
of a number, which is what the owner asked for on 2026-10-16: the label or the value is
missing. A present medium without animations says `0 animations`, as the owner answered.
The storage screen's lines are made by the same code and say the same words.

**Resolution.** `docs/specs/28-p2-the-apps-count-of-installed-and-stick-animations/`,
Requirements 1 and 2; `app/www/capacity.js`.

## Seed 28: numbers that cannot be known

**Question.** While the board reads its animations after a start, `list` answers `busy`;
while the show is invalid, `space` reports 0 animations and `list` is refused. What do the
lines say then?

**Answer.** The internal number comes from `space`, which answers from the start; while
the newest status reports an invalid show it says `animations not known`, as 0 would be
wrong. The external number needs a complete list: while the newest list request was
answered `busy`, before the first list, and when the difference of the list and `space`
falls below 0 for a moment between their two replies, it says `animations not known yet`.
When a later seed marks each item's storage in `list`, the app counts by that mark in
place of the difference; the ids are never used.

**Resolution.** Requirements 3 and 4 of the spec; `app/www/client.js`, `state.listBusy`.

## Seed 31: no new limit on a body's size

**Question.** The seed asks for explicit expansion limits, and a limit would end the
reproducer quickly; but the format says a compressed body is inflated whole before its
records count, and a limit would change which reason an overlong bad file gets, in the
converter and the Python library too. Limit, or slices?

**Answer.** Slices, and no new limit. Settling inflates on in slices of 32 KiB, one per
call, and ends with the very reason a whole-file reader gives, so the format and its
other readers do not change. A huge tail only takes longer to settle, in the background,
while every command is answered; seed 32 makes the file's animation unplayable as soon as
its first defect is found, before settling ends.

**Resolution.** `docs/specs/31-p0-bounded-decoding-and-responsive-fault-handling/`,
Requirement 1.

## Seed 31: the budgets, and the reproducer on the board

**Question.** Must the budgets wait for a board session, and how does the reproducer reach
the board, which the seed forbids to install as an ordinary animation?

**Answer.** The budgets are set from what is on record (seed 05's 9 to 17 ms for a dense
frame, seed 14's timings, Codex's captures): 32 KiB a settling slice, 128 KiB of catch-up a
refresh, 50 ms a call, 250 ms a host's read. The board session measures them. The
reproducer goes on the microSD card for that session, never into the board's own storage,
and is taken off again. The check at the start of a host that cannot change its storage,
the emulator's record mode, still reads whole files in one call: nothing waits on it.

**Resolution.** The spec's design, "Budgets and their reasons"; task 5.

## The serial run of 2026-10-24: which suites before a commit

**Question.** Every task's rules say to run every suite before its commit, about seventeen
minutes; the owner's run of 2026-10-24 has about forty tasks in eight hours. Every suite
before every commit, or not?

**Answer.** Every suite at the end of each seed, before its branch is pushed, and before
each task's commit the suites of the parts the task changed, always the core's, the
onboarding's and the documents' tests among them. A task that changes the core runs the
core's and the emulator's suites; one that changes the app runs the app's; one that
changes the firmware runs the firmware's. A failure found at a seed's end is mended in a
commit of its own before the push.

**Resolution.** The commits of the run say which suites ran.

## Seed 31: the name of the internal result `pending`

**Question.** The design names the internal result `kPending`, but `core/src/storage.h`
already has a constant `kPending`, the name of the file `pending.txt`. Rename that one, or
name the result otherwise?

**Answer.** The result is `kPendingWork`, a value of `Reason` after `kReasonCount`, with
no name; the file's constant keeps its name, as the rules of the run ask to add and not
rename. The documents call the result `pending`, as the spec does.

**Resolution.** `core/src/reasons.h`.

## Seed 31: slices of 7 bytes without a second build of the host

**Question.** The design has the core's tests build a second test host with
`-DODRIG_SETTLE_SLICE=7`. That is a second compilation of every source with the
sanitizers, in the makefile and in `core/build.py` for Windows. Is there a lighter way that
tests the same code?

**Answer.** The size of a slice is a field of the decoder, `settle_slice`, which `open`
sets to `kSettleSliceBytes`. The test host's `decode --slice BYTES` sets it after `open`
and decodes as the core's whole-file check does, calling again while the decoder gives
`pending`, and prints how many calls gave it. Every vector, 1,500 damaged copies and the
reproducer give the same records and reasons in slices of 7 bytes, and of 1, as in one
call. The core and its build are the same everywhere.

**Resolution.** `core/src/odrg_decoder.h`, `tests/core/host/host.cpp`,
`tests/core/test_bounded.py`.

## Seed 31: empty DEFLATE blocks inside one byte of output

**Question.** Settling is bounded now. Is any other call of the decoder unbounded?

**Answer.** One is, and it is a gap of the spec, not of this seed's tasks: the DEFLATE
decoder's `get` goes on through blocks that give no byte until one does, and a block with
the fixed codes builds its tables anew. A crafted stream of many empty blocks, a few
hundred kilobytes of them, could hold one call of `get` for seconds. Valid files from the
converter have no empty blocks. Mending it means a limit on blocks without output, which
changes what the format accepts (an owner's decision, docs/format.md), or a decoder that
can stop between blocks inside a frame record, which is larger than this seed. It is
proposed to the owner as new work and left as it is.

**Resolution.** None yet; said to the owner in the run's report.

## Seed 31: what a refresh shows while the player catches up

**Question.** The design says a refresh that brought no picture keeps the picture before.
What does `status` report as the animation then, and is there content that never catches
up?

**Answer.** The LEDs keep the LED data of the refresh before, and `status` keeps naming
the animation that picture came from until a picture of the new one is shown. A refresh
decodes at most 131,072 bytes of a body, a record's boundary after it, and always one
record; a settling slice counts against it, so a settling takes one slice a refresh. A
clip whose frames last less than its records take to decode at that rate, such as frames
of 1 ms on a dense 60 x 60 canvas, would fall further behind at every refresh and keep its
picture: no file of the converter has such frames, and the board could not show them in
time before either. A file that settles longer than a cycle's turn lasts begins its
settling again at each of its turns, as it opens anew; the check after the start, which
reads files beside playback and is not bound to turns, comes to its reason.

**Resolution.** `core/src/player.cpp`, `next_record` and `advance`.

## Seed 31: what the fault's context names, and how the emulator measures a call

**Question.** The design keeps the file's name in the fault's context, but a drive's file
is known to the core as `drive/<place>`; and the emulator cannot time a call of the core
from outside. What is kept, and what is measured?

**Answer.** A drive's file is kept by the name the host gives it, cut to 32 characters,
as an installed file is; a file that did not open was at record 0 with no body read. An
upload whose bytes read back differ from those received has no reason and leaves the
context as it was. The emulator's suite measures what a command waits: the time from a
`status` line on the line port to its reply, which holds the wait for the core's lock and
the call. With a show that plays the reproducer in a cycle and checks it after a sound
file of 3,000 frames, every wait stays within 50 ms on the Mac; the core before seed 31
made one wait 122.8 ms.

**Resolution.** `core/src/core_state.h`, `FaultContext`; `tests/emulator/test_bounded.py`.

## Seed 32: which faults still make the show invalid

**Question.** The seed keeps mapping and show-file faults apart from animation faults and
asks for a safe recovery state for the first. Which reasons quarantine one file, and what
is the recovery state?

**Answer.** `file-missing`, `size-mismatch`, `read-error` while a file is read, and every
reason of "ODRG files" belong to one file and quarantine it. The reasons of the mapping
file and of the show file, `duplicate-id`, `undefined-id`, `nested-cycle` and
`out-of-memory` still make the show invalid, as they did: without a show there are no
safe ids to act on. The invalid show is the recovery state: `status` reports the fault,
the LEDs are dark, and the commands that need a show are refused with `show-invalid`;
the board is put right by installing a show, as before.

**Resolution.** The spec's requirements 1.1 to 1.3; `docs/show.md`.

## Seed 32: the names of the additions

**Question.** How does a reply mark an unavailable animation, and how is `play` of one
refused?

**Answer.** A `list` item gets the member `fault`, the name of the reason, only when the
animation is unavailable: a reply stays as it was for a usable one, and the member adds
the reason the app shows. `bytes` is `null` for a file not read whole. `play` of an
unavailable animation, or of a cycle without a usable member, is refused with the new
error code `unavailable`. A quarantine writes `file <name> unavailable: <reason>` to the
log, beside the drive's `drive file <name> left out: <reason>`.

**Resolution.** `docs/commands.md`; the spec's design, "Commands and replies".

## Seed 32: what "the same content" of a drive's file is

**Question.** A quarantined file must not be tried again when its medium is taken up
again in the same boot, but a card swapped in may hold another file of the same name. The
host gives the core no size and no identity of a card. What is the content's identity?

**Answer.** The file's name on the drive, the bytes of its first read, at most 512, and
their CRC-32: the one read the check's header step makes anyway. A remembered file is
left out again after that read, without its body being decoded. The core remembers the
last 16 files left out in the boot, 704 bytes; one pushed out is checked again, under the
bounds of seed 31. Two files that agree in name and in their first 512 bytes and differ
after them are taken for the same.

**Resolution.** The spec's design, "A drive".

## Seed 32: entries of a medium that is gone

**Question.** The seed asks to keep known entries as unavailable when their medium
disappears. The core knows a drive's file names only through the host, while the drive is
in, and has no room for 256 names of 127 bytes. Keep them, or drop them?

**Answer.** A pulled drive's files leave the playlist and `list` as today; the files of
the next drive are checked and listed anew, and a remembered one is left out again. Keeping
the entries of an absent medium needs its metadata in the core, which the managed catalog
of seed 35 brings; it is left to that seed.

**Resolution.** The spec's requirement 6.2; seed 35.

## Seed 32: when the player meets a defect that settles long

**Question.** Seed 31's drift log said that seed 32 makes an animation unplayable as soon
as its first defect is found, before settling ends. Must the player stop at once?

**Answer.** No. The reason a file is reported with is the one settling ends with, and the
player keeps the picture before while it settles, a slice a refresh. The check after the
start settles the same file sixteen slices a refresh beside it, and whichever ends first
quarantines the file; then the player goes on with the next animation. For the
reproducer of seed 31 that is under three seconds. A report before settling ends could
name a reason the file does not have.

**Resolution.** The spec's requirement 2.2.

## Seed 32: the commands of repair during the check

**Question.** `list`, `remove` and `upload begin` wait for the check after the start
today, because it reads the files they change and owns the decoders an upload's check
needs. How do they stay open during the check?

**Answer.** `list` answers at once, with `bytes` of `null` for a file not read whole. A
removal keeps the check at its file. An upload takes the second decoders; the check takes
no step while an upload is open and afterwards begins its file again. A file an upload
installed was read whole by the upload's check and is not checked again.

**Resolution.** The spec's requirement 5; `docs/commands.md`.

## Seed 32: the tests and checks that made a show invalid with a missing file

**Question.** Many tests, and step 22 of the emulator's check list by eye, made an invalid
show by leaving out an animation file. With the quarantine such a show is valid. What do
they use now, and what does the status of a quarantine say?

**Answer.** A test that needs an invalid show adds to the show file a cycle that names an
id no item has (`with_show_fault` of the core's and the emulator's test support), and
expects `undefined-id 99`; a test of a missing, cut or unreadable file expects the
quarantine. Step 22 removes `show.json` and expects `show-missing`. `status` keeps
`"error":null` for a quarantine; a cycle that is played names its first usable animation
as the one on the LEDs from its start; an upload that replaces an animation while nothing
plays, because none was usable, starts the playlist. The room for an invalid show's text
stays 96 bytes, though its longest text is 24 characters now.

**Resolution.** `tests/core/support.py`, `tests/emulator/support.py`, `docs/emulator.md`,
`core/src/player.cpp`.

## Seed 32: how a client knows the check has ended

**Question.** Tests and tools waited for the end of the check after the start by asking
`list` until it was no longer `busy`. `list` is answered at once now. What tells the end?

**Answer.** `list` gives `"bytes":null` for a file not read whole yet; once every listed
animation has its size or a `fault`, the check has passed every file. The emulator's test
support waits for that, and the app's storage screen shows `size not read yet` in place
of a size. `remove`, `remove many`, `ignore` and `upload` are answered during the check;
an upload holds the check until it ends. Seed 33 reports the check's progress itself.

**Resolution.** `tests/emulator/support.py`, `app/www/screens/storage.js`,
`docs/commands.md`.

## Seed 32: another drive, and the first read of a drive's file

**Question.** Requirement 3.2 asks to check every file of another drive anew, but the
host gives the core a new number at every plug, for the same card as for another one; and
the hosts give a file's bytes in pieces of any size, so the bytes of the first call of
`read_at` are no identity. What does the core compare?

**Answer.** The first step of a drive's file reads its first 512 bytes, whatever pieces
they come in, and the core compares their number and CRC-32 with the name. Another card
with a file of the same name and the same first 512 bytes is taken for the same content,
as the design says; a file that differs in those bytes, on any card, is checked anew. The
first step reads those bytes once more than before, at most 512 of them.

**Resolution.** `core/src/core.cpp`, `drive_step`; `docs/core.md`, "A drive".

## Seed 32: what the test host needs for another drive

**Question.** A test of another card with a file of the same name needs a second drive
in one session, and the test host knows one drive's folder.

**Answer.** The input line `drive plug <folder>` plugs in a drive that stands for that
folder from then on; `drive plug` alone plugs the same folder again, as before.

**Resolution.** `tests/core/host/host.cpp`; `docs/core.md`, "The test host".
## Seed 38: The owner's question 7, the cables at the event

**Question.** The seed's question 7 was the owner's: which socket powers the board at the
event, the chip's own or the one marked COM, and is a computer on it? The first board
session, with the Mac on the chip's own socket only, lost the card; the second, with both
sockets on the Mac, did not. Task 9 waits for the answer.

**Answer.** Decided under the owner's mandate for the run of 2026-10-24, which has every
open question answered and recorded rather than asked: the firmware must work with one
cable or with two, powered through either socket, with or without a computer on the
other; and the board session checks the two-cable arrangement of today, both sockets on
the Mac, for fifteen minutes, as step 4 of the design's "The board session" has it. A
dropout seen with one cable is a fault of the card's code or its clock when the session
shows a cause there, and the owner's otherwise, as "The dropouts of 2026-10-22 are found
out, not solved" above says. Task 9 needs no further answer.

**Resolution.** `project-seeds/38-p1-a-microsd-card-as-the-external-storage/seed.md`,
"The Owner's Answers"; `docs/microsd.md`, "What is open".

## Seed 38: The card's page and the two session records

**Question.** The design folds the two records of `docs/microsd-preflight/` into
`docs/microsd.md` "in full". The records hold the Mac's mount of the card's source folder,
the local file names of the session logs under `build/`, and the steps of Codex's own
checklists. What of them goes into the page?

**Answer.** What the board showed and how it was asked: the cables and the sockets, the
firmware's hash, every count, time and rate, the four files played with their ids, and
what stayed unknown. The path of the Mac's mount, the names of the local logs, which are
in an ignored folder of another worktree, and the checklists' steps stay out: the first
two name nothing another computer has, and the third is this spec's `tasks.md`. The page
says the board's serial devices by the names the Mac gave them, as `docs/firmware.md`
does.

**Resolution.** `docs/microsd.md`, "The board sessions".

## Seed 38: The owner's question 8, the firmware that `build` makes

**Question.** The seed's question 8 was the owner's: once the board checks pass, does the
microSD build become the firmware that `build` makes, with the stick's build kept behind
an option? Task 10 waits for the answer, and when it is yes leaves open what the option
is called, what the images are named, and what becomes of `build --microsd`.

**Answer.** Yes, decided under the owner's mandate for the run of 2026-10-24, before the
board checks of tasks 8 and 9, which the run leaves to the session with the board:

- `build` makes the card's firmware on the newer software, environment `odrig_microsd`,
  as `odrig-firmware.bin`, and `build --probe` its probe build, the new environment
  `odrig_microsd_probe`, as `odrig-probe.bin`. So `flash` without `--image`,
  `install-firmware` and the board's suite take the card's firmware without a word more.
- The stick's build is `build --stick`, environment `odrig` on the software known good,
  as `odrig-stick.bin`, and `build --stick --probe`, environment `odrig_probe`, as
  `odrig-stick-probe.bin`. The environments keep their names, so WLED's folder keeps the
  libraries it fetched for them; `--stick` goes with neither `--stock` nor
  `--standalone`, as `--trial` did not.
- `build --microsd` stays and builds the same firmware into `odrig-microsd.bin`, the name
  the board sessions of 2026-10-22 and 2026-10-23 used and the spec's board session
  names; the other lines of the run may name it too. Two names for one firmware is the
  price of not breaking a command that is written down.
- `build --trial`, the environments `odrig_trial` and `odrig_trial_probe`, and
  `ODRIG_BOARD_IMAGES=trial` go. `tests/firmware/test_trial.py` becomes
  `test_newer_software.py`, since what it tests, the newer software's folder, packages and
  environment, stays.
- The board's suite on the card's firmware is run in the board session of task 8, which
  flashes that firmware anyway; task 10 has no board of its own in this run.
- Seed 12's spec takes the card's line, line 26 of `firmware-additions.md`, as its
  Requirement 13, and the stick's lines 17 and 18 hold for the stick's build only: the
  seed's question 8 says the fallback follows the firmware the installation runs.

**Resolution.** `firmware/fwtool/build.py`, `firmware/fwtool/cli.py`,
`firmware/platformio_override.ini.in`, `tests/board/support.py`; `docs/firmware.md`,
"The newer software" and "build"; `docs/decisions.md`, "Firmware";
`docs/specs/12-p2-standalone-firmware-as-a-fallback/requirements.md`, Requirement 13.

## Seed 38: The last task before the board session

**Question.** Task 11 sets the seed's state to `completed` and takes the seed out of
"What is coming" in `AGENTS.md`. The run of 2026-10-24 does task 11 before tasks 8 and 9,
which need the board and the owner and are left to the session with the board at the end
of the run. Is the seed completed by task 11 then?

**Answer.** No. With Requirement 9 and the definition of done's points 3, 4 and 6 open,
`completed` would say what is not so; seeds 20, 24, 27, 29 and 30 stay `in_progress` with
their owner's checks open. Task 11 does what is true now: the change log says what the
board runs and what the two sessions showed, and that the session is open; line 9 of
`firmware-prerequisites.md` says the same; `AGENTS.md` keeps the seed in "What is coming"
with what is left. Setting `state.json` to `completed` with `completedAt`, and taking the
seed out of "What is coming", move to the commit of the last of tasks 8 and 9 that is
done, which task 9 now names.

**Resolution.** `docs/specs/38-p1-a-microsd-card-as-the-external-storage/tasks.md`,
tasks 9 and 11; `docs/decisions.md`, the change log; `AGENTS.md`, "What is coming".
## Seed 36: the order file and what it names

**Question.** The owner answered that the playlist order is a file of the internal storage
that names internal items by id and card items by file name, one mixed order, an absent
card entry keeping its place. What is its form, where do animations it does not name go,
and what of an entry whose internal item was removed?

**Answer.** `order.txt` beside `show.json`, a header line `odrig-order 1` and one entry a
line, `i <id>` or `x <name>`, at most 512 entries. Animations it does not name come after
the named ones, the internal ones in the order of `show.json`, then the card's in the
order of their names, so that a new upload is last until it is moved and a show without
the file plays as before. An entry of a removed internal id stays until the file is next
written, and an upload that reuses the id takes its place; the core reads the file again
after such an upload, so that a restart gives the same order. The core keeps a key of two
bytes per item and per drive place, and a byte of each card name's hash, not the names.

**Resolution.** `docs/specs/36-p1-aurora-glass-ui-and-playlist-revamp/design.md`, "The
order file"; `docs/show.md` and `docs/core.md` with task 1.

## Seed 36: the order's commands

**Question.** The seed leaves the protocol of the saved order to the spec. Should `list`
report each item's place and the order's revision, or should the order have commands of
its own?

**Answer.** Commands of its own: `order get [<from>]` gives the listed animations' ids in
the saved order with a revision, in parts as `list` does, and
`order move <revision> <id> <before>` moves one animation before another or to the `end`,
refused with the new error `order-conflict` when the revision is stale. `list` gains only
`external`, which the three lines of the run agreed on, so that the other lines' tests of
`list` keep their replies. The revision is the CRC-32 of each listed animation's id and
key, so it is the same after a restart for the same files and changes with any change of
the order or of the listed animations. A move is refused `busy` during the startup check
and an open upload, whose check shares the second file source, and allowed while a test
animation shows, since it changes no playback.

**Resolution.** The spec's design, "`order get`" and "`order move`"; docs/commands.md with
tasks 1 and 2.

## Seed 36: what a snake test shows

**Question.** The seed asks that Snake N identify one three-strip snake through the saved
mapping, and to reuse the diagonal's one-white-pixel-wide line from bottom left to top
right. Three pixels of the canvas's diagonal fall into one snake; is that the picture?

**Answer.** No: each snake shows its own diagonal across its three columns, from the
bottom of its first column to the top of its third, 20 white pixels in each column and
every other LED dark. That lights 60 LEDs, places the snake at once, and shows whether each
of its strips runs the right way, which three pixels would not. The diagonal of the whole
canvas stays the 21st test. The pictures are one 20-frame JSON source that the converter
encodes, embedded in the core as the diagonal is.

**Resolution.** The spec's requirement 3.1 and design, "The test animations".

## Seed 36: the look's measures

**Question.** The app's look tests demanded a black background, three colours of text and
controls of 56 pixels; the owner chose Aurora Glass, a midnight background with teal and
violet accents and translucent panels, with a small `...` button on each row. Which
measures stay?

**Answer.** Every text keeps a contrast of 7:1 or more against what lies behind it, the
translucent panels composited onto the midnight background; the page's background stays
dark; the tabs stay along the bottom at equal width. The main controls keep 48 pixels or
more, and the row's `...` button, the badge-sized controls and the test buttons 44, the
size of a fingertip that Android's own guidelines name. Power is one toggle, as the mockup
draws it, which sends `on` or `off` by the state the target last reported.

**Resolution.** The spec's design, "The look"; `tests/app/test_look.py` with task 5.

## Seed 36: the diagonal's buttons and the test state

**Question.** Settings keeps the mapping editor and loses the duplicated playback
controls; where do the diagonal's Show and Stop go, and how does an app learn that a test
shows when it did not start it?

**Answer.** The diagonal is one of the 21 entries of the Tests group, and Settings says to
turn on Show test animations to check the wiring. Every test, from any controller, makes
`status` say that nothing plays on a valid show; only then, and after a test command, does
the app ask `mapping get` every two seconds while Animations shows, and it names the
active test with Stop test in the now-playing area, whether the Tests group is shown or
not. No member is added to `status`.

**Resolution.** The spec's design, "Tests and Settings".

## Seed 36: the power control, again

**Question.** The entry "Seed 36: the look's measures" made power one toggle that sends
`on` or `off` by the state the target last reported. Building it showed that a toggle
sends the wrong line when another controller changed the power within the last second,
and sends nothing before the first status. Is a toggle what the operator should have?

**Answer.** No: power is two buttons, On and Off, together in one rounded pill with the
power sign, as the mockup draws one pill. Each sends what it says whatever the last
status was, the one that is in effect is marked, and a status keeps them true. The other
measures of that entry stand.

**Resolution.** `app/www/index.html`, `#power-switch`; `app/www/screens/show.js`.

## Seed 39: Move up and Move down while a filter hides rows

**Question.** The seed turns dragging off while a filter is not All, because the places of
hidden rows would be unclear, and keeps the row menu, inclusion, play and deletion as they
are. Move up and Move down are in the row menu and move a row as a drag does. Do they stay?

**Answer.** No: they are reordering, and with rows hidden "up" would pass over rows the
operator cannot see. Both are off in the menu while a filter is not All, and the list says
`Set both filters to All to move animations: hidden rows would make the places unclear.`
The menu's other actions work as before.

**Resolution.** `docs/specs/39-p2-playlist-filters-by-storage-and-type/requirements.md`,
1.6; `app/www/screens/reorder.js`, `blocked()`.

## Seed 39: what counts as which type, and when the filters show

**Question.** `type` comes from seed 37, which another line builds at the same time. What
of a `type` the app does not know, of a target change, and of an installation without
animations?

**Answer.** A missing `type`, and any value other than `text` and `widget`, counts as
Normal, so a newer type never vanishes from All and Normal. The choices are the phone's
and stay across a target change, as they stay across a reload. The two rows of choices
show while the list has animations, and the list says that no animation is installed, as
before, when it has none.

**Resolution.** `app/www/screens/filters.js`; the spec's design, "The filters".

## Seeds 32 and 36: an unavailable animation in the rows of Animations

**Question.** Seed 32 grays an animation whose file had a fault on the show screen, says
its reason under it and turns its Play off; seed 36 replaces that screen with rows that
play on a tap and have a menu, and the storage screen, which said `size not read yet`,
with Upload, which has no list. Where do these go, and does an unavailable row keep its
menu and its place in the order?

**Answer.** In the row: its Play, the name and the line of id and size, is dimmed and
cannot be pressed; the reason in words, and on the external storage `Fix it on a computer:
the card is read-only here.`, stand under it across the row; the line of id and size says
`size not read yet` while `bytes` is null. The menu stays as for any row, so an internal
unavailable animation can be ignored, selected and deleted, and any can be moved with
Move up and Move down, since replacing or removing it is the way out and its place in the
playlist is the operator's. The filters count it by its storage and type as any other.

**Resolution.** `app/www/screens/show.js`, `row()` and `metaOf()`; `app/www/style.css`,
`.row.unavailable` and `.row .fault`; `tests/app/test_quarantine.py`.

## Seeds 32 and 36: the saved order of unavailable animations, and during the check

**Question.** Seed 36's `order get` holds "the animations `list` lists" and is "refused
as `list` is". Seed 32 lists a file of the card left out for a fault, with an id, and
answers `list` while the player reads the installed animations after a start, where it
was refused with `busy` before. Does the order hold such a file, and does `order get`
answer during the check?

**Answer.** Yes to both, as the two sentences say. A file of the card left out for a
fault stands in the order where its name does and can be moved; without it the app,
which keeps an order only when it holds exactly the listed animations, asked for the list
and the order again and again while a card had such a file. `order get` answers during
the check, as `list` does, so the rows stand in the saved order from the start; `order
move` stays refused with `busy` until the check ends, since the move reads the order file
with the reader that the check uses.

**Resolution.** `core/src/order.cpp`, `listed()` and `listed_with()`;
`core/src/commands.cpp`, the route of `order get`; docs/commands.md, `order get`;
tests/core/test_order.py, `UnavailableAnimations` and `test_it_is_refused_as_list_is`.

## Seed 33: where readiness and the last fault are reported

**Question.** The seed asks to extend existing reporting where it can and approves no
command, while the owner approved in advance every command the specs of the run need.
Does the fault's context go into `status`, or a command of its own?

**Answer.** Readiness and the counts go into `status`, which every client asks already.
The fault's context, a file name, a record, a byte count and a reason, is asked for
seldom and would make every `status` longer; it gets the command `fault`, approved in
advance. Its reply names a decoder's reason and the work it came in, and claims no damage
on the storage.

**Resolution.** The spec's requirements 1 and 2; `docs/commands.md`.

## Seed 33: what names the host, and what survives a reset

**Question.** The seed asks for the firmware's identity, its storage, its media and the
reason of its last reset in the reports, and for the last fault to survive a reset. The
core knows none of the first, and the board has no storage meant for logs.

**Answer.** An optional host function, `about`, gives a text of at most 95 bytes that
`status` reports as `host`. The firmware gives WLED's release name, the build's date and
time, its storage and the reset reason ESP-IDF names; the emulator gives its own name.
The firmware keeps the latest reason text its player logged in memory that survives a
software or watchdog reset, never in flash or on the card, with a CRC-32, and writes it
to its log at its next start. A power cut loses it, as the seed allows when it is said.

**Resolution.** The spec's requirements 3 and 4; `docs/firmware.md`.

## Seed 33: the tool's wait after seed 32

**Question.** `install-show` waited for a `list` that is not `busy`. Since seed 32 `list`
is answered at once during the check, so the tool stops waiting at once. How does it know
the check has ended, and what does it say?

**Answer.** It asks `status` until `readiness` leaves `checking`, and falls back to the
`busy` list of a firmware without `readiness`. It prints `outcome: healthy`,
`outcome: degraded: <n> unavailable` or `outcome: recovery: <reason>`; healthy and
degraded end with 0, as the board plays, and recovery with 1. A wait that runs out stays
the failure `check-not-done`.

**Resolution.** The spec's requirement 5; `firmware/fwtool/board.py`.

## Seed 33: the emulator's name

**Question.** The design has the emulator name itself `odrig emulator, core <date of the
library's build>`. The core's library tells no date of its build: no function of its
interface gives one. Does the core get one for the emulator?

**Answer.** No. The interface stays as the other hosts use it. The emulator names itself
and the computer it runs on, `odrig emulator on <system> <processor>`, as Python tells
them, which is what tells one emulator from another in a report.

**Resolution.** `emulator/host.py`; `docs/emulator.md`.

## Seed 33: the app's lines on the screens of seed 36

**Question.** The spec was written for the app before seed 36. Its task 5 is built on seed
36's four tabs. Where do the line of the reading, the installation's name and the last
fault go, and when is `fault` asked for?

**Answer.** The line of the reading stands in the panel of Animations, under the
refreshes a second: `Reading the animations: <n> read, <m> to read.`, with
`, <k> unavailable` when there are, and `<k> animations unavailable; the others play.`
when the reading has ended with some unavailable, `1 animation` for one; no line for a
ready installation or one that does not say. The name and the last fault stand on the
target screen, the name as `Installation: <host>`. `fault` is asked for each time the
operator opens the target screen after the installation has answered, once for each
opening, and never at the start: the app leaves the target screen at the first answer. A
software that does not know `fault` shows no line of it, and no message.

**Resolution.** `app/www/screens/show.js`, `app/www/screens/target.js`,
`app/www/messages.js`; `docs/android-app.md`.
## Seed 34: where the broad write is

**Question.** The seed asks that one-file maintenance not rebuild the animation folder.
Which operation rebuilds it?

**Answer.** The firmware tool's `install-show`: it reads the board's storage into an image,
removes `/odrig` with everything in it, writes every file again and writes the blocks that
differ, which for one removal from a storage 80 % full are 8.4 MB of WLED's layout and
10.9 MB of the bigger one. The commands `upload`, `remove`, `remove many` and `ignore`
already change one file and the show file through a temporary file and a rename, and
survive a power cut at every storage call (seed 07). The seed's work is therefore on the
image route, plus three things of the live route: an upload of unchanged bytes, the
cleanup a change leaves unfinished, and fault tests for `remove many`, `ignore` and the
start's cleanup.

**Resolution.** The spec's requirement 1; `firmware/fwtool/storage.py`.

## Seed 34: the order of the image's write, and the step that cannot be cancelled

**Question.** Writing changed raw blocks is not atomic: esptool erases a sector and then
programs it, and sorts the stretches of a call by address. Where can a write of the image
be cancelled safely?

**Answer.** A new or changed file is written into the image while every old file is still
there, so the file system puts its bytes into blocks the old file system does not use;
only the records of the file system, one or two blocks for one file, change blocks in use.
The tool writes the free blocks in one esptool call and the blocks in use in a second.
Up to the second call a cut leaves the board's file system exactly as it was: a test
writes the free part alone and reads the old show. The second call and the comparison are
the commit: they are not cancelled, an interrupt from the keyboard waits for their end,
and a cut there needs the recovery. On a full storage the commit is 2 blocks, 8 KiB.
LittleFS has no means in the tool's library to make the commit one atomic write of one
block, and a simulation of a cut inside it found the old show, the new one, a mixture and
an unreadable storage; so the tool does not promise more than a deterministic recovery.

**Resolution.** The spec's requirement 2; the design, "The write".

## Seed 34: no restart after a cut commit

**Question.** Today the tool restarts the board after every failure. Should it after a cut
commit?

**Answer.** No. WLED mounts its file system with `WLED_FS.begin(true)`, which formats a
file system it cannot mount: a board started on a half-written storage can lose its
settings and its show. After a failure in the commit or the comparison the chip stays in
its bootloader, and the message names `recover-storage`. esptool 5.4 resets the chip as
`--after` says also after a failed command, so every call of the write is made with
`--after no-reset`, and the board is restarted by a call of its own once the comparison
passed. A power cut of the board itself cannot be prevented; then
`recover-storage` finds the storage changed outside the change, and `--whole` writes the
new image whole.

**Resolution.** The spec's requirement 3.3; `firmware/fwtool/cli.py`.

## Seed 34: what recover-storage brings back

**Question.** The tool keeps the image from before and the new one. Does that make a cut
change reversible?

**Answer.** It makes it finishable. The journal names the new image and the runs of the
change; the board's storage outside them is the image from before, which the chip
confirms before anything is written. `recover-storage` writes the change again and
compares it: the board then holds the new image. A change cut before its commit is given
up, as the board holds the image from before. Going back to the image from before is not
offered: the change was asked for, and writing the old runs back is the same kind of
write with the same commit. When the storage outside the change differs, something else
wrote it since (the board started and formatted it, or saved settings), and the tool
refuses with `storage-changed`; `recover-storage --whole` writes the whole new image, the
last resort, which brings back the settings it holds and loses what the board wrote since.

**Resolution.** The spec's requirement 3.5; the design, "recover-storage".

## Seed 34: comparing the written blocks only

**Question.** The tool compares the whole partition after each write, 17 seconds on the
board. Must it?

**Answer.** No. Before the write the chip confirmed that the board holds the kept image,
or the tool read the partition whole; the write changes only the runs. The chip compares
every written run with the new image in one call, and the board is restarted when all are
equal. An unchanged folder writes and compares nothing.

**Resolution.** The spec's requirement 2.4.

## Seed 34: an unchanged upload, and its CRC-32

**Question.** An upload of the bytes an item already has writes the file again. How does
the core know that it is unchanged before the bytes are sent?

**Answer.** `upload begin` takes an optional fourth argument, the CRC-32 of the file, as
`upload end` does. When the last upload of this boot installed that file as the item's,
with that size and that CRC-32, no upload has begun since, and the item holds it still,
the reply is `{"ok":true,"unchanged":true}` and no upload opens. The upload's record keeps
the id, the name, the size and the CRC-32 after `upload end`, and one byte of its padding
says that it was installed. A file the check after the start read, or an older upload
installed, is uploaded again as today. Two files of the same size and CRC-32 are taken for
the same, as `upload end` takes them. Old firmware answers `bad-argument` to the fourth
argument, and `odrigctl` then sends the form without it.

**Resolution.** `docs/commands.md`; the spec's requirement 5.1.

## Seed 34: the cleanup at the next change

**Question.** When a change committed but could not remove the file it replaced, or
`pending.txt`, every later change is refused with `storage-error` until a restart. Is a
restart needed?

**Answer.** No. The next change first does the cleanup again: it reads `pending.txt` with
`read_at`, removes each file it names that no item names, and then `pending.txt`. When
that still fails, the change is refused as today and the next start tries again. The
cleanup reads at most 1,500 bytes, within the budget of a call.

**Resolution.** The spec's requirement 5.4; `core/src/storage.cpp`.

## Seed 34: no CRC-32 for every file

**Question.** A CRC-32 of each file would let the core answer `unchanged` for every file
it read whole: 8 bytes an entry of the file table (4 and the alignment of the next entry),
1,056 bytes for the target file. With seeds 31, 32 and 36 joined, the target file with a
drive takes about 130,701 of the 131,072 bytes the core may use. Is there room?

**Answer.** No. The core remembers the file the last upload installed only, in the record
the upload has anyway: the case the seed names, a request repeated after a reply that did
not arrive, writes nothing, and the core grows by no byte. The padding of a file's entry
and of an item is taken by seeds 29 and 32, and making `total_ms` 32 bits would change
what an animation of four billion frames does.

**Resolution.** `core/src/core_state.h`, `Upload.installed`; `docs/core.md`, "Uploads and
the check".

## Seed 34: `remove many` without a file that goes

**Question.** The fault tests found that `remove many` of an animation whose file another
item names gives the host a `write` of 0 bytes for `pending.txt`, which the host interface
forbids. Is mending it in the seed's scope?

**Answer.** Yes: it is a durable step of a live change, and the seed asks for every one to
be tested. Without a file that goes, `remove many` writes no `pending.txt`, as `remove`
does not.

**Resolution.** `core/src/storage.cpp`; `tests/core/test_incremental.py`.

## Seed 34: the app's uploads

**Question.** Must the operators' app send the CRC-32 with `upload begin`?

**Answer.** No. The app uploads a new animation under a free id and a name no item has;
an upload repeated after a lost reply is refused with `in-use` without a write. Seed 36
redraws the app; it can take the fourth argument up when it replaces animations.

**Resolution.** The app is unchanged.

## Seed 34: what install-show prints, and the copies

**Question.** How precise is the tool's account, and how is an affected file kept before
it is removed?

**Answer.** Before writing, `install-show` prints the number of files kept and each file
added, replaced or removed with its bytes, then the blocks and bytes to write, the free
ones first; afterwards one line `storage: committed: ... written and compared; the board
restarts`, or `unchanged`, or the error. `--dry-run` prints the plan and writes nothing.
`--keep-copies DIR` copies each file it removes or replaces, as the board holds it, into a
new or empty folder before anything is written. `read-show` copies everything, as before.

**Resolution.** The spec's requirement 4.

## Seed 34: the saved order on the image route

**Question.** Seed 36 keeps the playlist order the operator chose in `order.txt` of
`/odrig`. A show folder from the converter has none, and the check of a show folder
refuses one. What does `install-show` do with it?

**Answer.** It keeps it. The seed asks to preserve the stored playlist choices unless the
operation changes them, and installing animations does not change the order: an entry of
an id or a file that is gone is passed over, and a new animation comes last until it is
moved. A folder may hold its own `order.txt`, as `read-show` copies it, and that one takes
its place. `order.part` is the core's own and goes like any file the folder does not hold.

**Resolution.** `firmware/fwtool/storage.py`, `folder_files`; `firmware/fwtool/cli.py`,
`install-show`; the spec's requirement 1.6.
## Seed 37: The header, the three versions and the names

**Question.** The seed asks for a header-selected container with magic, lengths, canvas,
type and version, keeps the owner's names odrg1, odrg2 and odrg3 for frames, text and
widgets, and leaves the layout of the header to the specification.

**Answer.** A header of 20 bytes, `ODRX`, the container's version, the type (1 frames,
2 text, 3 widget, the owner's odrg1 to odrg3), the type's own version, a reserved byte,
the canvas, the loop in milliseconds and the payload's length. The loop is in the header so
that the start, which reads headers only, knows every file's length and type at once, and
the check after the start holds it to the payload. A frames payload is an ODRG file as it
is, so no second codec exists. The extension is `.odrgx`, and readers dispatch by the
magic: a container named `.odrg` is read as a container, and an ODRG file named `.odrgx`
as an ODRG file.

**Resolution.** `docs/specs/37-p1-odrgx-text-and-clock-animations/design.md`, "The
container".

## Seed 37: Where the layout of a text is made

**Question.** The seed wants the C++ core to own rendering and the app's preview to show
the same pixels, allows "compact precomputed layout ... with font/version references",
and asks for the Unicode Bidirectional Algorithm for mixed Hebrew and English. Is the
bidirectional ordering and the wrapping done by the core at every start, or once?

**Answer.** Once, by the converter's library, when the file is made, in the app or on a
computer; the file stores the text as written, its settings, and the glyphs with their
places. The core checks that every glyph is in its font and in its block, computes the
pass from the settings and the block, and draws. So the algorithm exists once, in
JavaScript, beside the preview that uses it, and the core stays small; a text whose stored
glyphs do not spell its text can only show its glyphs. Both the core and the converter
draw, with the same integer rules, and reference pictures that both must reproduce hold
them together; compiling the core to WebAssembly for the app would need a toolchain the
project does not have.

**Resolution.** `docs/specs/37-p1-odrgx-text-and-clock-animations/design.md`, "The layout,
in the converter" and "Decisions".

## Seed 37: The fonts

**Question.** The owner wants the fonts in the firmware, preferably pixel fonts drawn by
hand for Hebrew and Latin in two or three sizes, made in the repository. Which sizes and
which characters?

**Answer.** Two drawn fonts and a third made from the first: `small`, 7 pixels from the
baseline to a capital's top with 2 below, ten pixels a line, five lines and more on 60
rows; `medium`, 10 and 3, fourteen a line, four lines; and `large`, `small` at twice the
size, for big messages and the digital clock's digits. Each has the 95 printable ASCII
characters and the 27 Hebrew letters, the five final forms among them, which descend below
the baseline as `ק` does. Niqqud, other scripts and emoji are refused by name. The glyphs
are text files that show the pixels, and one generator writes the core's tables and the
converter's.

**Resolution.** `fonts/`; `docs/specs/37-p1-odrgx-text-and-clock-animations/design.md`,
"The fonts".

## Seed 37: Where a clock's randomness comes from

**Question.** A clock needs a fresh random seed at each turn. The core has no source of
randomness, and promises the same output for the same timestamps. Does the host give one?

**Answer.** No member is added to the host. The core mixes the timestamp of every refresh
into a 32-bit noise, and a clock's seed is that noise mixed with the item and the start
time of the turn. On the board and in the emulator the refreshes come at times that jitter,
so every turn and every start differs; in the tests the timestamps are given, so the seeds
are repeatable. `status` reports the seed, and the converter's drawing replays it.

**Resolution.** `docs/specs/37-p1-odrgx-text-and-clock-animations/design.md`, "The seed".

## Seed 37: The commands for editing

**Question.** The app must read an installed text or clock back to edit it, and must not
overwrite another controller's change. Which commands, given that a command line has at
most five words and the owner approved new commands in advance?

**Answer.** `read <id> <offset>`, which gives up to 600 bytes of an animation's file in
base64, and `upload expect <crc32>`, sent between `upload begin` and `upload end`, which
makes the upload replace the item's file only when that file has the CRC-32 the app read;
otherwise the new error `stale`, and the upload is discarded. While an upload is open no
other controller can change the show's files, so the comparison holds until the end. The
core keeps no CRC-32 of a file: it reads the item's file when asked, which is why `upload
expect` takes files of at most 16,384 bytes. `list` gains `type` and `status` gains
`seed`.

**Resolution.** `docs/specs/37-p1-odrgx-text-and-clock-animations/requirements.md`,
Requirement 10; `design.md`, "Commands".

## Seed 37: What waits for seeds 32, 35, 36 and 39

**Question.** The seed registers every type through seed 35's catalogs, keeps seed 32's
quarantine, puts authoring into seed 36's upload screen, and seed 39 filters by type.
Those seeds are built at the same time on other branches.

**Answer.** This branch builds on today's upload path and today's storage screen, and its
last task is done by the session that combines the branches: the catalogs take the type
and the loop of the header, the quarantine takes a refused file, the forms move into seed
36's screens, and the filter reads `type`. Until then a refused file installed by hand
makes the show invalid, as any refused file does today, while an upload of one is refused
with `bad-file` and changes nothing.

**Resolution.** `docs/specs/37-p1-odrgx-text-and-clock-animations/tasks.md`, task 14.

## Seed 37: The stored answers of the Python tool and the show's file names

**Question.** A show may now name `.odrgx` files, and the converter and the Python library
both say "ending in .odrg or .odrgx" of a name that breaks the rule. The converter's suite
compares that detail with what the Python tool answered when it still converted, stored in
`converter/tests/expected/`, where 24 answers say "ending in .odrg". The Python tool can no
longer be run to answer again. What becomes of those answers?

**Answer.** They are changed in that phrase only, in `read_shows.json` and in
`run.json.gz`, since the Python library, which is the reference they record, now gives the
new phrase in the same place: every other byte of each answer, and every key, stays. The
reason, `show-malformed`, does not change.

**Resolution.** `odrig/show.py`, `converter/lib/show.js`, `converter/tests/expected/`.

## Seed 37: The swing of a clock's speed

**Question.** The design gives a clock's speed a swing of up to all the room between its
base speed and the nearer of its two limits, so that the speed is never below the least.
The cosine is read from the sine table between its entries, and those straight pieces are
steeper than the true curve by up to 0.47 percent. With the whole room, the speed dips
below the least by that much, and below nothing for a least speed of 1: the hands would go
back for a moment. Is the room or the guarantee kept?

**Answer.** The guarantee. The swing is at most 100/102 of the room, `(r % 101) / 102`
where the design had `/ 100`, so the steepest piece of the table stays inside the limits.
The converter's suite checks the speed over irregular steps for hundreds of seeds and
limits.

**Resolution.** `docs/specs/37-p1-odrgx-text-and-clock-animations/design.md`, "The virtual
time"; `docs/format.md`, "The widget payload".

## Seed 37: When `status` has a seed

**Question.** Requirement 8 asks for the seed of the clock whose turn it is, and `null`
while no clock is on the LEDs. A `play` closes what plays until the next refresh, and
`off` darkens the LEDs while the turn goes on. What does `status` give then?

**Answer.** The seed belongs to the turn. `status` gives it from the turn's first refresh
to its end, also while the LEDs are off, since the turn and its clock go on and `on`
shows them again at once. From a `play` until the next refresh, while the new turn has
no seed yet, and while frames or a text or nothing plays, it gives `null`.

**Resolution.** `docs/commands.md`, "Status reply"; `docs/core.md`, "Clocks".

## Seed 37: A status reply longer than 192 bytes

**Question.** `seed` makes the longest `status` reply 210 bytes. Seed 02 held every reply
to 192 bytes, and the core's suite still holds `status` to that. Is a member dropped?

**Answer.** No. Seed 07 raised every reply to 1,024 bytes, and nothing reads `status` into
a smaller buffer: the emulator's and the firmware's replies take 1,024. The test now holds
the longest `status` under 256 bytes.

**Resolution.** `tests/core/test_commands.py`; the change log of `docs/decisions.md`.

## Seed 37: The look of the melting watch

**Question.** The melting clock is to resemble the seed's picture, a tilted pocket watch
whose lower half sags, with hands that stay joined at their pivot. Which shape, made of
integer steps the core can take at every refresh?

**Answer.** The dial of the analog clock, two thirds as large, up and to the left of the
centre, tilted counter-clockwise by 25 to 40 degrees. Above a fold line it lies flat;
below it the face hangs straight down, stretched by 130 to 170 percent, drifting right and
narrowing as it hangs, and darker the deeper it hangs, with a dark crease at the fold. The
fold waves slowly with the real time. A crown and a ring of the rim's colour sit at 12
o'clock. Each pixel is taken back to the dial, so the hands bend with the face and stay on
it. The owner's look on the LEDs is task 13.

**Resolution.** `docs/format.md`, "The widget payload"; `core/src/clock.cpp`;
`converter/lib/draw.js`.

## Seed 37: Carried onto the joined seeds, and what task 14 has left

**Question.** Seeds 31, 32, 36 and 39 were joined while this seed was being built, on
`seeds-28-to-39-unified`, and the run's main session asked for seed 37 to be built on
top of them before its app tasks. Task 14 was to fit seed 37 to them after combining.
What of task 14 is left?

**Answer.** Seed 37 was carried onto the joined branch as
`seed-37-odrgx-text-and-clock-animations-unified`, each task with its own commit again,
and fitted there: a text or a clock with a fault is quarantined as seed 32 quarantines
any file, and `read` answers `unavailable` for one; `list` gives `type` after seed 36's
`external` and before seed 32's `fault`; a cycle's turns take the animation seed 32
chooses for each; `stale` stands after `mapping-conflict` and before `order-conflict`;
the forms of tasks 9 to 11 were built in seed 36's Upload tab and rows' menus, from the
start; seed 39's filter reads `type` as it is. The core asks for 16 bytes more than the
joined seeds: the noise and the seed lie in holes of its object, a drive entry keeps its
type in a half byte beside its state, and the upload's check reads its header into the
check's. What is left of task 14 is seed 35's catalogs, which register the type and the
loop of every file; it waits for seed 35 to be joined. The seed's state then follows task
13 too.

**Resolution.** `docs/specs/37-p1-odrgx-text-and-clock-animations/tasks.md`, task 14;
the branch `seed-37-odrgx-text-and-clock-animations-unified`.


## Seed 35: what a storage without a catalog does

**Question.** The seed wants no routine reading of the library and no discovery of
copied files, and also no automatic rebuild when a catalog is missing. The board and the
owner's card have no catalog today. What does a start or a plug-in do with them?

**Answer.** They are legacy and are read as before this spec: the start opens each file
and the check after the start reads it, a drive is listed and its files checked before
they play, and a file copied onto a legacy drive joins as before. Nothing writes a
catalog by itself; `catalog rebuild` on the board, or the PC tool's `import`, makes one
once, and from then on the storage is read from its catalog. A damaged or incompatible
catalog is reported and its files read as legacy (internal) or not taken (a drive), so
that nothing that plays now stops playing and no start loops.

**Resolution.** The spec's requirements 2.3, 4.3 and 4.5; design, "The start" and "The
drive".

## Seed 35: the format, its pages and its commit

**Question.** The seed asks for metadata work per change that does not grow with the
library and for a fixed-size marker, and the owner for byte-identical files from the board
and from a computer. One catalog file rewritten at each change grows with the library;
fixed slots need a byte of memory for every installed file, which the target file does not
have.

**Answer.** Text, 16 pages, an entry's page the low four bits of its name's FNV-1a hash
(the hash of the saved order), lines in the order they came in; a marker of 409 bytes with
the generation and each page's count and CRC-32. A change writes its pages and marker as
`.new` files and then the commit record `catalog.do`; finishing renames them into place
and is repeated after a cut. A change rewrites the page of its entry, N/16 entries on
average and at most N, which the documents say as such; no change lists the storage or
reads another animation. On FAT, where a file cannot be renamed onto another, the host
removes the target first, and the commit record covers the moment between.

**Resolution.** The design, "The catalog format"; `docs/catalog.md`.

## Seed 35: the show file and the catalog

**Question.** An upload of a new item and a removal change both `show.json` and the
catalog. Each file is replaced in one rename. Which goes first, and what does a cut between
leave?

**Answer.** An upload commits the catalog first, with the file's rename in its commit
record, and then writes the show as before; a removal writes the show and removes the file
as seed 34 does, and then commits the catalog. A cut between leaves an entry for a file
the show does not name, or a file the show names without its entry: the first is not an
animation, the second is read as legacy, and the next rebuild leaves both out. A
replacement under its name is one commit.

**Resolution.** The design, "Changes of the internal storage".

## Seed 35: room in the core

**Question.** With a drive the target file takes 130,701 of 131,072 bytes. The catalogs
need about 220 bytes of state. Where is the room?

**Answer.** The drive's table keeps a file's length in 32 bits: 49 days and more count as
4,294,967,295 ms. Its 256 entries take 12 bytes each instead of 16, which frees 1,024
bytes; the catalogs take part of them, and the measurement says what is left.

**Resolution.** The design, "Memory"; `docs/core.md`'s table.

## Seed 35: the board writes the card

**Question.** The owner's answer 7 lets the board write the card. Which commands, which
ids, and what of a USB drive?

**Answer.** The host says whether its drive can be written: the SD card when it is
mounted, a USB drive never. `upload begin external <file> <bytes> [<crc32>]` uploads to the
card, and `upload end` answers the new animation's id; a file of the same name is replaced
and keeps its id. `remove <id>` removes a card's animation; `remove many` and `ignore` stay
for the board's own storage. A legacy card is not written until it has a catalog, and the
new error `read-only` says so, as it does for a card that cannot be written.

**Resolution.** The design, "The board writes the drive".

## Seed 35: rebuild, its writes and its budget

**Question.** A rebuild writes a page while it reads its files over many refreshes, and the
host has one file being written. What of other changes meanwhile, and what are the budgets?

**Answer.** While a rebuild has a page open, the commands that write storage answer `busy`;
playing, power, brightness, `list` and the rest work. A rebuild takes the steps of the
check after the start: up to 16 a refresh, each one read of at most 512 bytes or one frame
record, and one at least in 10 refreshes. A drive's catalog is read in the same steps; an
unchanged drive's marker is read once in 10 seconds; the internal catalog is read whole at
the start (at most 132 entries, metadata only). An external rebuild drops the card's
animations, lists the folder once and lets each file join again as it passes.

**Resolution.** The design, "Rebuild" and "The drive".

## Seed 35: unmanaged changes and the check

**Question.** How is a file that was changed behind the catalog's back found?

**Answer.** By the PC tool's `check`, which compares each file's size and CRC-32 with its
entry, and by a rebuild, which reads every file; playback keeps seed 31's decoding and seed
32's quarantine, which catch a file that no longer decodes. No start or refresh hashes the
library.

**Resolution.** The spec's requirement 2.5; the design, "The PC tool".

## Seed 35: the PC tool's reader and seed 37's types

**Question.** The PC tool must admit what the core admits. Which reader does it use, and
what type does an entry have before seed 37?

**Answer.** The project's Python reader, `odrig.odrg.decode`, whose reasons the shared
vectors keep equal to the core's; the tests run the core and the tool on the same files.
Every entry of an ODRG file has the type `frames`; seed 37 adds `text` and `widget` with its
container.

**Resolution.** The design, "The PC tool"; `tests/vectors/catalog/`.

## Seed 35: where the app puts a new animation

**Question.** The owner wants one or two small animations on the board and the rest on the
card. What does Upload offer?

**Answer.** When the card can be written, Upload offers `The card` first and `This board`
second; otherwise it stores on the board as before. Settings shows both catalogs and their
rebuilds; a card's row has `Delete` when the card can be written.

**Resolution.** The design, "The app".

## Seed 35: the PC tool's lines and exit statuses

**Question.** The design gives `python3 -m odrig.catalog <mount> status|import|add|remove|
check|recover`, exit 0, 1 and 2 and a line of outcome per change. What are the lines, and
what does it do on a card without a catalog or a folder that is not there?

**Answer.** One line per file or outcome, `added: NAME, BYTES bytes`, `replaced: ...`,
`removed: NAME`, `refused: NAME: REASON` with the check's reason, `imported: N animations,
generation G`, `differs: NAME: missing|size|crc` and `checked: N entries, M differ`;
`status` gives the catalog's state with its generation and entries, the animation files of
the folder and those without an entry. A refused file does not stop the others. `add`,
`remove` and `check` need a catalog that is `ok` and say so on standard error with what to
run (`import`, or `recover` for an interrupted change); `status`, `import` and `recover` work
on any. A file to add that cannot be read is refused as `file-missing`. A MOUNT without a
folder `odrig`, or with `--folder` a path that is no folder, is a usage error, status 2,
as `odrigctl` treats what it cannot start with. The canvas is the installation's, 60 x 60.
`main` is added to `odrig/catalog.py` and nothing of the module changes.

**Resolution.** `odrig/catalog.py`, `main`; `tests/converter/test_catalog_cli.py`;
`docs/microsd.md`, "The catalog, made on a computer".

## Seed 35: the catalog that install-show writes

**Question.** The firmware tool's `install-show` is to write the internal catalog of the
folder it installs, as a rebuild would, with the generation after the board's. Its check
of the folder already decodes every animation, and a rebuild decodes them again; the
board's generation is known only once the board's storage is read; and installing the
same folder again changed nothing before. How do these go together?

**Answer.** `storage.folder_files` checks the folder by the rebuild itself, on an
in-memory storage, in the show's order and for the mapping's canvas: each animation is
decoded once. The first file the rebuild refuses, in the show's order, is judged again by
the check before it, so that its reason and its words stay those of the converter's
readers; a name the show allows and the catalog does not is checked alone and left out of
the catalog. A catalog the folder holds is made anew. Once the board's storage is read,
the marker gets the generation after the board's, or 1; when the board's catalog has the
same pages the board's own marker is kept, so that the same folder installed again still
writes nothing. `--no-check` writes no catalog. The rebuild of the PC library stands for
the core's in the tests until the core rebuilds.

**Resolution.** `firmware/fwtool/storage.py`, `folder_files`, `catalog_files`,
`with_board_generation`; `tests/firmware/test_catalog.py`; `docs/firmware.md`,
"install-show".

## Seed 35: the board writes the card, and a storage call that fails

**Question.** A card that its host can write takes `upload begin external` and `remove`,
and the design asks for a cut and a failure at every storage call of every change on both
storages. What does a call that fails leave behind, and what does the next change do with
it? Which names may an upload to the card have while the entries of the catalog have no
type yet? The app sends neither new command before its own task: what does it make of the
new code `read-only`?

**Answer.** Before the commit record is whole, a failed call ends the change with
`storage-error`, and a file that was being written is removed, which also ends its writing,
as seed 34's changes do. After it the change is made and the reply is as for success. The
finishing stops at the call that failed and leaves the record; every later change of that
storage finishes it before it writes anything, and is refused with `storage-error` while
it cannot; the start and the plug-in keep `upload.part` while a record is left, since the
record may move it. A start that cannot finish the record reads the board's storage as
without its catalog, `damaged` with `interrupted`, and the first change that finishes it
takes the catalog up again from its marker; a card whose record cannot be finished at its
plug-in is `damaged`, `interrupted`, and nothing of it plays until it is plugged in again.
The core's own commit on the card sets the CRC-32 of the marker that the look every 10
seconds compares, so that the card is not read again after each change. An upload to the
card takes a name of the show's files that ends in `.odrg` until the entries record their
type (seed 37's task 14), and the upload's check gives the new place its type. A file
replaced while it plays is released before the commit and played anew from its start
after it, as an item's file replaced under its name is. The app's
tests count `read-only` among the codes the app cannot get (`NOT_FOR_THE_APP`) until its
task gives it a text. Task 4's tests had the cut at every call and not the failure; the
failure at every call of the internal changes comes with this task's.

**Resolution.** `core/src/catalog.cpp` (`finish`, `catalog_settle`, `catalog_left`,
`write_whole`, `write_page`, `catalog_install_external`, `catalog_remove_external`),
`core/src/upload.cpp`, `core/src/content.cpp`, `core/src/commands.cpp`,
`core/src/storage.cpp`; `tests/core/test_catalog_writes.py`,
`tests/core/test_catalog_changes.py`; `docs/commands.md`, "Catalogs"; `docs/catalog.md`,
"A change".

## Seed 35: a rebuild on the board

**Question.** `catalog rebuild internal|external` reads every animation with the check's
steps and commits the catalog at the end, and `catalog cancel` ends it. Where do the
pages' counts and CRC-32s wait while the rebuild goes page by page, what is left on the
storage by a cancel, a failed call or a drive pulled out, which files does a rebuild of
the board's storage take while the catalog cannot hold every name the show may have, and
what does the check after the start do after it?

**Answer.** The count and the CRC-32 of each page wait at the end of the chunk buffer, six
bytes a page from byte 1,400, which nothing else uses while a rebuild runs, as every
command that writes storage is `busy` meanwhile; the core object grows by 16 bytes for the
rebuild's own fields, measured: the target file 125,341 bytes, 129,821 with a drive. A
cancel, a storage call that fails and a drive pulled out end the rebuild without its
commit: the page being written and the pages written before it are removed, and on a drive
that is gone they stay, never read without a record. A rebuild first finishes a change
that a failed call left, as every change does, and is `storage-error` when it cannot. A
rebuild of the board's storage takes the show's files whose names a catalog may hold; the
check after the start gives way while it runs and takes up after it, or after a cancel,
every file that is neither read nor quarantined. A rebuild of the drive drops its places,
lists the folder once and gives each file its id and its place in the saved order as a
plug-in without a catalog does; a file joins as it is read. Readiness is `checking` with
the rebuild's files read and to read while it runs, and the file it reads.

**Resolution.** `core/src/catalog.cpp` (`catalog_rebuild`, `catalog_cancel`,
`catalog_rebuild_step`, `catalog_drive_went`), `core/src/core.cpp` (`check_file_step`
shared with the rebuild), `core/src/commands.cpp` (the routes, `busy`, readiness);
`tests/core/test_catalog_rebuild.py`; `docs/commands.md`, "Catalogs"; `docs/core.md`,
"Readiness" and "Memory".
## Seed 35: the firmware writes the card

**Question.** Task 11 has the firmware list the drive's folder only when the core asks,
give places the names the core binds, say whether the card can be written, and make the
core's changes by `drive/<name>`, with `odrig_files.cpp` routing the `drive/` names. Where
does the routing go, which drives get the three functions, what does a card without its
folder do, how is the one file being written kept across two storages, and what of the
file the player reads when a change replaces it?

**Answer.** The routing of `drive/` names was in `odrig_drive.cpp` already, whose
`withDrive` wraps the installed files' functions for the reads; it wraps the five that
change files too, when the installed files have them, and `odrig_files.cpp` only lends its
timing: `OdrigFiles::StorageCall` times a change of the card as its own calls are timed,
so that the command lines are paced after it. Both backends have `drive_list`,
`drive_bind` and `drive_writable`, so that a stick with a catalog is read from it too; the
stick's `drive_writable` says 0 and its changes fail. The card is written while it is
mounted, has its folder `odrig` and no read of it has failed: the board makes no folder,
so a card without one stays as it is. Beginning a file in one storage gives up and removes
the one being written in the other, as the core's header has it for one storage. A rename
onto a file that is there removes that file first, as FAT renames onto none, once the file
to be renamed is there; when the target is the same file in another case, nothing is
removed. A change of the file the player holds closes it first, as FAT frees the clusters
of a removed file under a reader: its reads fail, as the installed files' do with no file
open, and the card stays mounted; the file `read_at` holds is closed at every change and at
every list. A write is whole only when the card holds every byte given, so a failed write
makes the end fail as well. Mounting a drive logs `card mounted` or `stick mounted`, or
that it has no folder `odrig`; the lines with the number of files come when the folder is
listed.

**Resolution.** `firmware/usermod/odrig_drive.cpp`, `odrig_drive.h`, `odrig_files.h`,
`odrig_files.cpp`; `tests/firmware/test_usermod_sd.py`, `test_usermod_drive.py`,
`test_usermod_files.py`, `test_usermod_log.py`; `docs/microsd.md`, `docs/firmware.md`,
`docs/firmware-additions.md`, line 26.

## Seed 35: the command tool's catalog and the card's upload

**Question.** The design names `odrigctl catalog [rebuild internal|rebuild external|cancel]`
and `odrigctl upload --external FILE`. How does the tool's table of commands hold a command
whose operation may be left out, how is `--external` told from an id, and does the tool
wait for a rebuild to end?

**Answer.** `catalog` takes `[OPERATION]` in the table and the synopsis: none, `rebuild
internal`, `rebuild external` or `cancel`, each sent as it is, anything else a usage error
of status 2 that says what it takes. `--external` is an option of the tool that goes with
`upload` only and takes the file alone; the upload is the one of `upload ID FILE` with the
word `external` in the place of the id, so that `upload begin external <name> <bytes>
<crc32>` goes out, and the reply of `upload end` with the card's id is printed as it comes.
The tool does not wait for a rebuild: its reply comes at once, and `catalog` shows the
progress. The tests run the commands through the emulator by each transport, and a card
the emulator wrote is read by the PC tool and the other way round.

**Resolution.** `odrigctl/cli.py`; `tests/emulator/test_catalog.py`,
`tests/emulator/test_tool.py`; `docs/emulator.md`, "The command tool".
## Seed 35: the app's task built beside the core's

**Question.** Task 13, the app, is built at the same time as tasks 7 and 8, which give the
core the upload to the card, the removal from it, `space`'s `read_only` and the rebuild.
What does the app follow, and what does it run against?

**Answer.** The forms the design and the core's line fixed for those tasks: `catalog` with
`internal`, `external` and `rebuild`, `catalog rebuild internal|external` and `catalog
cancel`, `upload begin external <file> <bytes>` with its `upload end` giving `id`,
`remove <id>` of a card's animation, `"read_only":false`, and the code `read-only`. The
app's tests run them against stand-in targets that answer so, and `catalog`'s states
against the emulator as well. The app gives `read-only` its sentences already; the table
of codes in `docs/commands.md`, and with it the count of `tests/app/test_messages.py`,
gain the code with task 7.

**Resolution.** `app/www/commands.js`, `app/www/screens/catalogs.js`,
`tests/app/test_catalog.py`; `docs/android-app.md`.

## Seed 35: where the app's choices stand, and their words

**Question.** The design names `Store on: The card / This board` on Upload, `Rebuild` and
`Cancel` in Settings, and the progress `Reading the animations: 12 of 84`. Upload makes
texts and clocks as well as animations of videos, Settings has the mapping's `Cancel`
already, and Animations says `Reading the animations: ...` during a rebuild. Where do the
choices stand, and what do they say?

**Answer.** `Store on` stands with the animation that was made, above `Upload to the
installation`, as it is the choice of that upload; texts and clocks are stored on the
board, as the card's catalog holds `.odrg` files only. Settings' buttons name what they
do, `Rebuild the board's catalog`, `Rebuild the card's catalog` and `Cancel the
rebuild`, and the question's `Rebuild` and `Not now`; the progress is `Rebuilding the
catalog of the board: 12 of 84 animations read.`, so that it is not Animations' line. The
app does not judge a card's free storage before an upload: the card's file system rounds
as the board knows, and the board refuses with `no-space` before a byte is sent. A card's
storage line and its badge say `read-only` only while the installation cannot write it,
and a file with a fault on a card it can write is deleted from its menu, not mended on a
computer.

**Resolution.** `app/www/index.html`, `app/www/screens/storage.js`, `screens/show.js`,
`screens/catalogs.js`, `capacity.js`; `docs/android-app.md`.
## Seed 35: a checked install of a show with ODRGX containers

**Question.** On the board, `install-show` of a show that names a text and a clock refused
the folder: `file-malformed: .../hebrew.marquee.odrgx: bad-magic: the file starts with 4f 44
52 58, not 4f 44 52 47`. Its check read every file as ODRG; seed 37 lets a show name ODRGX
containers. How does the check read them?

**Answer.** As the library reads them, told apart by their first four bytes as format.md
says: an ODRG file whole, as before and in the same words; a container of frames by
`odrgx.decode_frames`, its canvas, its frames and their loop; a container of text or of a
widget by `odrgx.read_header` and the length its header gives the payload; each with the
mapping's canvas, else `size-mismatch`. A refused file is reported with the library's
reason. The library has no reader of the payloads of text and widgets, which the board
reads by its own: a payload whose settings or glyphs are wrong passes the tool's check and
is made unavailable by the board's (seed 32), and a payload with bytes after it or cut short
is refused here as `payload-size` where the board's reader names `trailing-bytes` or
`truncated`. Until the catalog reads containers, they are left out of it and the board
checks them at its start.

**Resolution.** `firmware/fwtool/storage.py`, `_check_animation`;
`tests/firmware/test_containers.py`.

## Seed 37: the type and the loop in a catalog, the PC part

**Question.** Seed 35's catalogs were made before seed 37 and read every file as ODRG. Seed
37's task 14 asks the catalogs to register the type and the loop of every file. Does the
format have room, and what does the PC library record?

**Answer.** The format has room: each line of a page holds a length in milliseconds and a
type, `frames`, `text` or `widget`, so no line changes its form. `odrig.catalog.entry_of` reads
a container as the core's check does, told apart by its first four bytes: one of frames by
`odrgx.decode_frames`, one of text or a widget by `odrgx.read_header` and the length its
header gives the payload; the entry has the header's canvas, its loop as the length and its
type; an ODRG file stays of `frames` with the sum of its durations. Names may end in
`.odrgx`, and a storage lists them as the drive does. `canvas=None` leaves the canvas
uncompared, which the firmware tool's check uses before it compares the mapping's in its own
words. This is the PC library's half; the core's reader of a catalog still takes names
ending in `.odrg` only and writes `frames` for every entry, and is the other half of the
task.

**Resolution.** `odrig/catalog.py`, `entry_of`, `name_allowed`, `names`;
`firmware/fwtool/storage.py`, `_check_animation`; `tests/converter/test_catalog_types.py`;
`docs/catalog.md`.

## Seeds 35 and 37: the core records the type and the loop

**Question.** With the PC library's half in (it reads a container as the core's check does
and writes each entry's type and loop), the core still took only `.odrg` names on a page
and wrote `frames` for every entry, so that a catalog that `install-show` writes for a show
with texts or clocks would be read by the board as damaged. What does the core write, read
and give for each kind of file, and may the card hold texts and clocks?

**Answer.** The core writes the type its check found and, for a text or a clock, the loop
its header gives as the length; it reads the type back with the entry and gives it to the
show's file and to the drive's place, so that `list` has it at once, without a scan. A
name on a page may end in `.odrg` or `.odrgx`, in any case, as the PC library's rule says,
and `upload begin external` takes either: the card may hold texts and clocks, and the app
keeps sending them to the board, as its task chose. A rebuild takes `.odrgx` files from
here on. The rest of seed 37's task 14 stands on what the branch holds: a refused text or
clock is quarantined at the start (seed 37's tests of texts and clocks), the forms of making
and editing are in seed 36's Upload and Animations (seed 37's tasks 9 to 11), and seed
39's filter goes by `type` of `list` (seed 39's task 1).

**Resolution.** `core/src/catalog.cpp` and `.h` (`catalog_name_allowed`, `EntryLine.type`,
`CatalogChange.added_type`, `put_entry`), `core/src/storage.cpp`, `core/src/commands.cpp`;
`tests/core/test_catalog_odrgx.py`; `docs/commands.md`, "Catalogs".

## Seed 35: the measured costs, and two that the design put otherwise

**Question.** Task 14 asks for `docs/catalog.md` with the measured costs. The design's
table said that a start reads the marker and the pages once, and that a drive's catalog is
read in steps of at most 512 bytes. What do the measurements say, and how are they taken
without a board?

**Answer.** They are taken through the core's test host, with refreshes 20 ms apart, on the
target file of 80 animations and on drives of 16, 64 and 256 animations, and given in
`docs/catalog.md` beside the table. A start reads the marker once and the pages twice: the
core checks every page against the marker before it takes an entry, so that a damaged page
leaves every file as without a catalog; 7,289 bytes for a catalog of 3,849. A step of a
drive's catalog is one read of at most 512 bytes, and the marker is read again before each
page, so that a marker changed while the pages are read starts the reading again; a refresh
takes as many steps as the check's pace gives it, at most 2,266 bytes for 256 animations,
in 10 refreshes. The table now says both. The board's own times are its session's, task 15.
The app's page gave as the reason that texts and clocks stay on the board that the card's
catalog held `.odrg` files only; with seed 37's types in the catalogs that is no longer so,
and the page gives the app's choice alone.

**Resolution.** `docs/catalog.md`, "What each operation costs"; `docs/core.md`, "Startup" and
"The catalogs"; `docs/android-app.md`, "Using it".

## Seed 36: the snake test seen on the installation

**Question.** With the twenty snakes wired, the owner found the test of a snake, one white
line of 20 pixels in each of its three columns, too sparse to judge the snake by: most of
its LEDs stayed dark. What should it show?

**Answer.** The owner's choice: a white block of 3 x 3 pixels that runs the length of the
snake, from the bottom of its three columns to their top and back, one row every 40 ms,
so that every LED of the snake lights in turn and the direction of each strip is seen as
the block passes. Within one snake a block three wide can move along the snake's length
only, so "back and forth" is up and down the columns. It is drawn at each refresh from
the time since the player started, as a clock is, and keeps no state and no embedded
picture; the file of twenty frames and its generator are gone.

**Resolution.** `core/src/mapping_control.cpp`, `snake_test_draw`; docs/commands.md,
docs/core.md, docs/android-app.md; the change log of docs/decisions.md.

## Seed 40: the owner's photo in a lit room, and the edge the wires are at

**Question.** The owner's first photo of the diagonal, taken in a lit room with the wall on
its table and seen from the side, was refused: 401 bright spots, the lens of every unlit
LED catching the room's light, which a threshold of the picture's median plus a margin
could not part from the lit LEDs; darkening the photo by hand did not help, as the median
darkened with it. And the stubs fell to the right, where the design expects them to rise:
seen from the side, the positions run down the picture and the heights across it. How are
the lit LEDs told from the lenses, and how is the picture's orientation read?

**Answer.** The owner's rule: the picture is scanned from the brightest level down, as if
brightened little by little, and the count of peaks at or above each level is watched; the
lit LEDs, all about as bright, come in together and then nothing new comes until the lenses
and the reflections flood in, so the level is the middle of the longest stretch of levels
over which the count holds steady, at one to a hundred peaks. A picture with no stretch of
twelve levels has no steady set of lit LEDs and is refused, `no steady set of lit LEDs
among them`. Pictures with reflections are the normal case, not a fault. The slope of the
stubs tells upright from turned: they rise to the right when the wall is seen upright and
fall when it is seen from the side, a quarter turn either way. Which edge the wires are at,
the picture cannot tell, so the advice asks for the wires' edge at the bottom of the
picture or at its left, and both edges are offered as choices, the advised one first, in
the words of the wires rather than of a dark strip at the left or the right, which a
turned picture would confuse. The picture is analysed at 900 pixels on its long side, not
600, so that the LEDs of a wall that fills the frame are some 15 pixels apart. The owner's
screenshots of the app with the photo, one as taken and one darkened, are test vectors
beside the seed, read to the mapping the stubs show by eye.

**Resolution.** `app/www/photo.js`, `app/www/screens/photomap.js`; the seed's
`photos/05-the-diagonal-from-the-side-screenshot.jpg` and `06-…-darkened-screenshot.jpg`;
docs/android-app.md; the spec's requirements and design; the change log of
docs/decisions.md.

## Seed 43: how a leg says that its strips do not alternate

**Question.** Snake 10 of the installation runs up column 28, up column 30 and down column
29, where the mapping's rule has the strips of a leg alternate from the `first_led` end.
How does the mapping file say so, and in which words?

**Answer.** A leg may have `starts`, one word for each strip in chain order, the end the
strip starts at, in the words of `first_led`: `bottom` or `top` for a column, `left` or
`right` for a row, not `up` and `down`, which the format does not use. Its first word
repeats `first_led`, so a reader that knows only `first_led` still places the first strip
right, and a difference is malformed. Without `starts` the strips alternate as before, so
every file written before is the same file. The member is general, for any leg of either
kind; only the app's checkbox is particular to snake 10. The core takes the bits of the
ends only when the file has a `starts`, so the memory of a file without one is unchanged:
one block more, of one bit a strip, with it.

**Resolution.** docs/mapping.md, rule 6 and "Where each LED is"; `core/src/mapping.cpp`,
`odrig/mapping.py`, `emulator/web/layout.js`; the tests of the core, the library and the
emulator.

## Seed 43: the bit of the cross-wired snake, its command and its revision

**Question.** How does the app set the bit that snake 10 is cross-wired: a member of
`mapping set`, or a command of its own? Is the bit part of the revision that guards a
save? And what does the snake test of snake 10 show with the bit on?

**Answer.** A command of its own, `mapping cross on|off`: `mapping set` keeps its form,
which every client and the command tool send, and the bit is not a pin. The revision
stays the CRC-32 of the twenty pins: the app computes it from the pins it shows, and the
bit is idempotent, so a stale app can only set the bit it means to set; `mapping set`
keeps the bit as it is. The bit is nothing but the form of leg 10 in the mapping file,
`"columns":[28,30,29]` with `"starts":["bottom","bottom","top"]`, so a restart, the
emulator and every app agree, and a hand-written file with that leg reads as the bit on.
The snake test and the diagonal are drawn on the canvas as before: with the bit on, on
the installation as wired, the block of snake 10 climbs its three lines together and the
stub of position 10 rises like the others; with it off the block climbs line 28 and
descends lines 29 and 30. The emulator publishes the mapping again after every successful
`mapping cross`, so that its page reads the file again, although the legs and their pins
are the same.

**Resolution.** docs/commands.md, "Mapping controls"; docs/core.md; docs/mapping.md;
`core/src/mapping_control.cpp`, `core/src/commands.cpp`; `emulator/binding.py`,
`emulator/engine.py`; `odrigctl/cli.py`; the mapping suite.

## Seed 43: the photo of a cross-wired snake read with the box off

**Question.** The design said that nothing of the photo reading changes: with snake 10
cross-wired and the box off, position 10's second and third LEDs land in the rows of the
snake 21 - s, the position that shows that snake keeps it with more votes, and position
10 gets the snake that remains. The test of such a wall failed instead: every position
was read one snake off, and positions 10 and 11 had none. Why, and what changes?

**Answer.** The two misplaced LEDs share their rows with the stub of snake 21 - s, so two
rows hold two LEDs each. The grid of the rows takes its pitch at each step from the four
nearest gaps between sorted values, and the two gaps of nearly nothing between the LEDs
of one row halved it there: the next step counted two places, and every row above was
one place higher. The pitch now leaves out a gap of less than 0.6 of the typical gap, two
LEDs at one place, and takes the four nearest gaps between places. A wall with no two
LEDs in a row reads as before; the owner's photos read as before.

**Resolution.** `app/www/photo.js`, `places`; the wall of the tests with a cross-wired
position, `tests/app/page/scenarios/photo-analysis.js`; `tests/app/test_photo.py`;
docs/android-app.md, "The mapping from a photo".
## Seed 42: what the emulator takes for the position, the length and a seek

**Question.** The seed asks for a seek bar in the emulator alone: the core exposes
neither the position of the animation on the LEDs nor its length, and no command may be
added for the emulator. Where does the emulator take the position and the length from,
what does a seek do at the grid, and what of the rules that the page sends no command and
the emulator holds no reader of the show?

**Answer.** The core opens the file it plays through the host anew at every loop and
every turn, and a refresh begins at a grid time, so the start of a loop is the grid time
of the refresh in which the played file was opened, and the first open after a change of
file, a command answered, or a restart of the emulator's own is the start of a turn; the
emulator asks `status` once more after such a refresh, so that the animation's id is
known at once. A numeric `playing` is a cycle, as the page reads it today; the bar shows
nothing then, and a seek is refused with `cycle`. The length comes from the storage's
catalog, which the emulator's `lengths` module reads itself, line by line, since the
emulator imports nothing of the `odrig` package; else from the converter's `check` of
the file, run in a thread when Node.js is on the path, which the emulator's suite needs
anyway, so that the emulator's `lengths` module is the second tool, after the preview,
that starts the converter, and only to check; else from two consecutive opens of the same file with no command answered and no
seek between them, kept per file across a restart. A text or a clock without a catalog
entry has no length. The numbers are `m:ss`, and `h:mm:ss` from one hour. A seek names a
point from 0 to the length less two grid steps; the move of the clock is rounded down to
whole grid steps, so the position lands within a grid step below the point; a move back
is a restart with the emulator's own `play <id>`, logged with the transport `seek`, then
one grid step so that the core takes the refresh that begins the turn, whose grid time
is the start, then the move. The page keeps the rule that it sends no command: its one
request, `POST /seek`, is a route of the emulator and no command of the core; the page
files test allows that one fetch and keeps `/odrig` forbidden. The engine reads
`animation` and `playing` off the status reply with two patterns rather than a JSON
reader, since only the hub reads JSON in the emulator. No keyboard seeking. The word
`length unknown` stands while the length is not known, and `clock +N s` for three seconds
after a seek that moved the clock. The Chrome check runs a harness page served beside the
emulator's page, since Chrome's dump of a page waits for its load, which an open event
stream never ends: the harness frames the page, reads its numbers, drags its bar with
pointer events, and holds its own load back with a late image.

**Resolution.** `emulator/engine.py`, `emulator/lengths.py`, `emulator/host.py`,
`emulator/hub.py`, `emulator/httpd.py`, `emulator/web/`; docs/emulator.md; the spec's
requirements and design; tests/emulator/test_playback.py, test_seek.py,
test_page_files.py, tests/app/test_emulator_seek.py; the change log of docs/decisions.md.

## Seed 42: a seek far into a long file

**Question.** The owner's look: a seek into the middle of a long animation left the LEDs
still for seconds before the frame of the point came. The core decodes at most 128 KB of
a file at one refresh and keeps the picture before until it has come to the picture of
its time, so one move of the clock by minutes left it decoding the way at 128 KB a
refresh, 8 seconds for a seek of five minutes into an 87 MB file. How is the move made so
that the frame of the point shows at once?

**Answer.** In strides: the engine moves its clock 400 ms at a time and asks the core for
the refresh of each, under its lock, and hands the hub the last frame. A stride of 400 ms
holds fewer bytes than the core's bound for any file the converter writes, the heaviest
on the share being under 200 KB a second, so every refresh of the walk comes to its
picture, and the walk of a seek by minutes takes a fraction of a second. The emulator's
suite checks it with a file of random pixels whose seconds hold more than the bound.

**Resolution.** `emulator/engine.py`; docs/emulator.md; tests/emulator/test_seek.py.
## Seed 41: what the spec and its tasks decided beyond the seed

**Question.** The seed came with no question open, and its spec and the tasks that built it
still had to settle what the seed did not say. Which decisions were taken, and where are
they?

**Answer.** The firmware's log says one line for a listing, with the counts of what was
passed over, `card opened: <n> animation files in <m> folders of odrig; <k> files and <f>
folders passed over`, not a line per file. The path rule is one rule for both catalogs,
since `catalog_name_allowed` serves both, and a path deeper than three folders in a catalog
is a damaged line, as any name the rule refuses. A place whose folder would be the 33rd
sub-folder, which only a catalog can name since every lister cuts at 32, is left out with
the reason `too-many-folders`. `remove`, `remove many`, `ignore`, `read`, `order move` and
`upload begin` of a folder's id answer `in-use`, the code a cycle's id gets. `play` of a
folder while nothing at or below it and nothing in the root can play makes the folder
current and answers ok; `play all` with an empty playlist stays `unknown-id`. `status`
names the current folder in `playing` while the root plays in its place too. The current
playlist takes over from its first animation at the end of the turn in progress, as soon
as it has something to play again; at power-on with a saved folder the root plays in its
place until the card is read and the turn ends. A jump's turn begins at the refresh after
`play`, as every turn, and `left` is floored to whole seconds, so two statuses 5 ms apart
may differ by one. The round shortcut of the playlist is bounded by the window's end with
the root alone too, so that the core and the reference player agree on `left` after a gap
of days, and a rotation that lands on the playlist that was current changes nothing that
plays. The saved file is not written while the tree has no folder and no file exists,
since an absent file means the root with a fresh window; a write waits while an upload
receives its bytes or a rebuild holds a page open; the file is read and its part probed
only on a host that has a drive; the root made current by a read card without the saved
folder, or by the removal of the current folder's last file, is saved at the next refresh
with the time spent since. In the app the count in a group's heading is the number of its
rows, filters or not; a folder head's button is named `Play folder <path>` for a screen
reader and the root's keeps the id `play-all` and the words `Play this folder`; a folder
the list does not hold yet is named by its id with the time left and the list is asked at
once, and a number without `left` reads `Cycle <id>` as before; a row moved down from the
last-but-one place of its group goes to the end of the whole saved order, `order move <id>
end`, which leaves every group's relative order as if it went after its group's last row;
an upload's landing in the root is checked by the core's test of `upload begin external`,
since an upload from the page needs a cataloged card the emulator may write.

**Resolution.** `docs/specs/41-p1-sub-folder-playlists-from-the-card/design.md`; the
commits of tasks 1 to 10 on the branch `seed-41-sub-folder-playlists`; docs/show.md,
docs/commands.md, docs/core.md, docs/microsd.md, docs/android-app.md, docs/reasons.md.

## Seed 42: a folder's playlist is not a cycle

**Question.** With seed 41, `status` names a folder of the card in `playing` while its
playlist is current, a number as a cycle's id is, and the engine took any number there
for a cycle: the bar showed nothing during a folder's playlist and a seek was refused
with `cycle`. How does the emulator tell the two apart, without a reader of JSON and
without asking more than it needs?

**Answer.** By the cycles `list` names: the engine lists the show's items with requests of
its own, reading each cycle's id off the reply with a pattern, when `playing` holds a
number it has not told apart since the last command answered; any other number is a
folder's playlist, shown as the playlist is. A show without cycles and a playlist of the
root ask nothing more than before.

**Resolution.** `emulator/engine.py`; docs/emulator.md; tests/emulator/test_playback.py.

## Seed 44: the preview's times, its GIF and the walk of a file

**Question.** The seed gives a preview 24 pictures over the first loop, each shown for a
twenty-fourth of it rounded to 10 ms within 20 and 120 ms, and asks that a long file be
walked without keeping every picture and that the same file give the same bytes
everywhere. Which time is "k twenty-fourths", how is a delay rounded, what does the GIF
hold besides its pictures, and how is the loop known before the walk reaches its end?

**Answer.** Picture `k` is the one on screen at `floor(k * loop / 24)` ms, so those at
twelfths and sixths are the even ones and those of `k` divisible by 4, and one walk serves
all three sizes. A delay is `floor((loop + 5N) / (10N))` hundredths, half rounded up,
between 2 and `288 / N`. The GIF holds a global table and no local one, the loop extension
`NETSCAPE2.0` with the count 0, and for each picture a control extension with the disposal
"do not dispose" and no transparency, and a whole image of the canvas; its LZW starts with
a clear code and clears again when the table is full. `odrg.reader` reads the header, the
body and the palette at once and then one record at a time, as `decode` does, with the same
refusals; its `loopMs` sums the durations from the records' starts alone and refuses
nothing, since a file it cannot sum is refused by the walk at the record where `decode`
refuses it. A container of frames gives the loop its header names, which the end of the
walk checks. `decode` and `decodeFrames` are the readers read to their end.

**Resolution.** `converter/lib/thumbnail.js`, `converter/lib/odrg.js`,
`converter/lib/odrgx.js`; docs/converter.md, docs/reasons.md;
converter/tests/thumbnail.test.js, converter/tests/browser.test.js.

## Seed 44: what `thumbnail --catalog` does beside adding previews

**Question.** The seed gives `thumbnail FILE... --catalog DIR [--card ODRIG]` and passes
over a file the readers refuse. What does it do with a folder `DIR` that is missing, with a
key whose line is there and whose GIF is not, with `--card` given with `--out`, and with a
GIF or the mapping that cannot be written?

**Answer.** It makes the folder and the folders above it. A key whose GIF is missing gets
its GIF again; one whose GIF is there keeps it and only gains the name. `--card` goes with
`--catalog` only: with `--out` it is a mistake of the command line, status 2. A file that
cannot be read is passed over as a refused one is, with `not-found`; a GIF or a mapping
that cannot be written ends the run with status 1 and `cannot-write`, since the catalog is
then not what the run would leave. The tests of the subcommand are in
`converter/tests/thumbnailtool.test.js`, as a test file's name is letters alone.

**Resolution.** `converter/cli/thumbnail.js`, `converter/cli/arguments.js`;
docs/converter.md; converter/tests/thumbnailtool.test.js.

## Seed 44: what `catalog page` gives when a page's bytes do not fit, or the card is out

**Question.** The seed gives `catalog page` up to 512 bytes of a page as the text of a reply
of at most 1,024 bytes, and `"generation":null` for a storage whose catalog is not `ok`.
What does it give when the escaped bytes would not fit, and for the card when none is
plugged in, whose catalog the core may still hold as it was?

**Answer.** The text holds the bytes one by one while each one's escaped form and the end
of the reply still fit, and `next` counts the bytes given, so that a client reading on from
each `next` gets every byte. A page of a sound catalog is printable ASCII with line ends,
512 bytes and their line ends always fit; only a page changed behind the core's back can be
given in shorter parts. A drive that is not plugged in answers as a storage without an `ok`
catalog, as `catalog` reports it `absent`. The example of `docs/commands.md` is the one
reply example with a space, inside its text; its test checks that the example is the
compact JSON of its value.

**Resolution.** `core/src/catalog.cpp`, `core/src/commands.cpp`; docs/commands.md,
docs/core.md, docs/catalog.md; tests/core/test_catalog_page.py, tests/core/test_docs.py.

## Seed 44: the first content of `thumbnails/`, and how the hosts take it

**Question.** The seed makes `thumbnails/` the default preview catalog, served and packed as
the converter's library is, and fills it from every source of the first computer. What
does the folder hold before those sources are read, which of its files do the hosts take,
and how is it kept out of a board's storage?

**Answer.** Its first commit holds the previews of the tracked animations alone,
`test-animations/` and the valid vectors, made by `thumbnail --catalog thumbnails`, so that
a clone can make them again and a test compares them with what the library makes; the
sources of the first computer come in a commit of their own. The emulator, `app.py serve`
and the APK's staging take `catalog.js` and the `.gif` files of the folder and nothing below
it: the emulator under `/app/thumbnails/`, the server under `/thumbnails/`, both with
`image/gif`, the staging into `thumbnails/` beside the web code. The web code may import
`thumbnails/catalog.js` and no other file of the folder. A board's storage is made from a
show folder, which the firmware tool refuses when it holds a folder or a file the show does
not name, a GIF of the folder among them, and `pack` writes exactly the show's files.

**Resolution.** `thumbnails/`, `emulator/httpd.py`, `app/apptool/webserver.py`,
`app/apptool/stage.py`, `app/apptool/paths.py`; docs/emulator.md, docs/android-app.md;
converter/tests/thumbnails.test.js, converter/tests/library.test.js,
tests/emulator/test_page_files.py, tests/app/test_tool.py, tests/app/test_scope.py,
tests/apk/test_apk.py, tests/firmware/test_storage.py.

## Seed 44: how the app's reading of the pages fits its queue

**Question.** The seed has the app ask `catalog` at the target's first answer and after every
complete list and read the pages one request at a time after the operator's own. Where do
`catalog` and the pages stand among the app's other requests, which generation do the keys
carry, which replies of `catalog` count, and what of the keys is left when a reply ends a
silence?

**Answer.** `catalog` and the pages come after everything else the app sends: the
operator's requests, `status`, an upload's lines, `list`, the saved order and `space`; one
page part is sent at a time, so that the operator's next request goes out after the part
under way. `catalog` is also asked when the target answers again after a silence, and every
reply of `catalog` counts, Settings' included, so that Settings' two-second asking starts a
read at once. The keys carry the generation of the pages they were read from and the number
of entries of the reply that started the read; a later reply of another generation or number
starts a read again. A reply that ends a silence drops the keys and every read, and the
reading starts anew from `catalog`. The board's storage is read before the card's. A target
whose catalog refuses `catalog page` is asked `catalog` only by Settings, and a target that
refuses `catalog` by no one, until the target changes; Settings tells the second from the
client's answer. A reply to `catalog page` that is no page's answer counts as such a refusal,
so that the reading never marks the target as silent. The app's tests that pin the lines the
app sends take `catalog` and its pages among the lines it sends by itself.

**Resolution.** `app/www/client.js`, `app/www/commands.js`, `app/www/screens/catalogs.js`;
docs/android-app.md; tests/app/test_keys.py, tests/app/page/scenarios/keys.js.

## Seed 44: the square in a row, and the note under the name

**Question.** The seed puts a square of 44 by 44 pixels at the start of each row's Play
button and the row's `Saving…` or `⊘ Ignored` note under the name inside Play at 320 px in
selection mode. Is the note moved only then, how does a row get its preview without being
drawn again, and how is the row's checkbox measured?

**Answer.** The note stands under the name inside Play at every width and in every mode,
one layout for all. The square is set each time the rows' state is drawn, its image made,
changed or taken out only when its source differs, so that a row is never drawn again for
its preview and a press is never lost to it; the square takes no pointer itself and the
tap goes to Play. The now-playing panel's square shows when `status` names an animation the
list holds and something plays, which is never so during a test. The look test measures a
row in selection mode with its note; the row's checkbox counts among the row's own controls,
44 pixels high as its Play and its menu are.

**Resolution.** `app/www/previews.js`, `app/www/screens/show.js`, `app/www/index.html`,
`app/www/style.css`; docs/android-app.md; tests/app/test_previews.py,
tests/app/page/scenarios/previews.js, tests/app/test_look.py.

## Seed 44: the phone's own catalog in IndexedDB

**Question.** The seed keeps the previews this phone makes in the web view's IndexedDB, in
steps that leave the screen answering, the default catalog looked up first. How is the
store laid out, what is a step, and when does a row show a preview of its own?

**Answer.** One database, `odrig-previews`, with one store, `previews`, whose keys are the
animations' keys and whose values are the GIFs as `image/gif` blobs; at the start every key
the default catalog has is deleted and the rest are taken into the run as object addresses.
A step is one step of the library's maker, a bounded number of records or drawings, run
from a timer of 0 ms. The preview is made from the bytes the upload sent, keyed by their
CRC-32 and size, the same key the installation's catalog writes for them, so the row shows
it once the read of the changed catalog gives the row its key. The Animations screen draws
again when the phone's catalog gains a preview.

**Resolution.** `app/www/previews.js`, `app/www/convert.js`, `app/www/screens/storage.js`,
`app/www/screens/author.js`, `app/www/main.js`; docs/android-app.md;
tests/app/test_own_previews.py, tests/app/page/scenarios/ownpreviews.js.

## Seed 44: the tracked previews are the media the repository holds

**Question.** An answer of this page, that of the converter's own tests, says that no media
file is tracked in the repository. Seed 44 tracks a GIF for every animation known on the
first computer. What does the repository hold now, and how is the default catalog made
again?

**Answer.** Besides the images it held, the icons and splash screens of the app and the
pictures of the seeds, the repository tracks the previews of `thumbnails/` and no other GIF,
MP4 or MOV file; the converter's test says exactly that. The first default catalog was made
on 2026-10-27 by `thumbnail --catalog thumbnails`, one run for each source the seed lists,
the two card copies with `--card`: 424 previews of 609 to 65,484 bytes, 12,510,264 bytes in
all, 409 of them of 24 pictures and 15 of 12. Every source was at hand, the share and the
mirror of Google Drive among them. Three files were passed over, the broken test files of the
board's session of 2026-10-25: `huge-tail-test.odrg` twice with `bad-palette-index` and
`broken-test.odrg` with `bad-palette-size`. A later conversion adds its preview the same way
in the commit that records it; a file whose key the folder holds only adds its name.

**Resolution.** `thumbnails/`; agent/animation-guide.md, agent/vocabulary.md,
docs/decisions.md; converter/tests/thumbnails.test.js.

## Seed 52: the bytes of a picture clock

**Question.** Seed 52 asks for two widgets that carry their base picture, "compressed as the
format compresses a picture", with their geometry, and leaves the bytes to the spec. How
are they laid out, how large may a widget's payload be, and how is a widget of 20 bytes
told from one with a picture?

**Answer.** The widget's first byte tells it: 1 to 3 keep their 20 bytes, 4
`picture-dial` and 5 `picture-display` have a head of 12 bytes, their parts (hands of 10
bytes and caps of 6, or fields of 22) and then the picture, an ODRG file of one frame and
a palette of 1 to 8 colours, to the end of the payload. The ODRG file is how the format
compresses a picture, and the core already decodes it. A widget's payload may have 32,768
bytes, more than the largest picture needs. So the widget's byte is read before the
payload's length is compared: a file of widget 1 with a length of 21 is still refused with
`payload-size`, and the vector `unknown-widget.four` is now `unknown-widget.six`. A
picture whose frames or palette are not those of a picture clock is refused with a new
reason, `bad-picture`. A hand has a tail behind its pivot and an offset of whole hours, and
a cap is a disc of a colour over the hands, so that a tile's pivot cap or a second clock
of another time zone can be drawn; a field shows a pattern of the hour, the minutes and
the seconds, and a display has up to 4 fields, for tiles whose time is in several boxes.
`check` prints a picture clock's `direction` and the size of its `palette`.

**Resolution.** `docs/format.md`, "Picture clocks"; `docs/reasons.md`;
`converter/lib/odrgx.js`; `docs/converter.md`.

## Seed 52: the direction and the slowest points

**Question.** A picture clock runs forward, backward, or in a way chosen by the seed of its
turn, which "may also turn at the swing's slowest point, at a chance the seed fixes". What
does the seed draw, where are the slowest points, and how is the time found so that a time
of the turn has one picture however the refreshes come?

**Answer.** The seed draws the eleven values of the other clocks, in their order, and then
`back`, r % 2, and `chance`, r % (turns + 1). The swing's speed is least where the angle of
its cosine is three quarters of a turn, once in each period P, the first at
`t0 = floor(P * ((3 * 2^24 - Φ) mod 2^26) / 2^26)`. Whether the way turns at the k-th
slowest point is `mix(seed ^ k) % 100 < chance`, a fact of the seed and k alone, and the
time is the sum of the ways over the whole periods before it, each b * P long, so it needs
no state. At a slowest point itself the time is the turn's point: the step that ends there
still goes the earlier way.

**Resolution.** `docs/format.md`, "Picture clocks"; `converter/lib/draw.js`,
`pictureTime`.

## Seed 52: the font of small displays

**Question.** Many tiles show their time in a display a few pixels high once the tile is
60 x 60: the small font, 7 rows, does not fit them. Which font do they use?

**Answer.** A fourth font, `tiny`: the ten digits, the colon and the space, 3 by 5, in
`fonts/tiny.txt`, generated with the others into the tables of the core and the
converter. A font file may now name its repertoire, `digits`; the fonts of texts keep the
whole one. A text cannot name it: the texts' fonts stay 1 to 3, and a text of font 4 is
refused with `unknown-font` as before.

**Resolution.** `fonts/tiny.txt`, `fonts/generate.mjs`, `core/src/font_tables.cpp`,
`converter/lib/fonttables.js`; `docs/format.md`.

## Seed 52: the vectors of picture clocks, and which task holds them

**Question.** The tasks of seed 52 put the vectors of picture clocks with the core, task 2.
But the converter's suite checks that the invalid vectors of widgets have every reason of
"Widgets in ODRGX", the Python library's that every listed reason is one of its own, and
the core's that it has every reason of a widget: once task 1 lists `bad-picture`, those
suites need its vector and its name. Where do the vectors go, and how is each commit whole?

**Answer.** The vectors of picture clocks are a folder of their own,
`tests/vectors/pictures/`, with its builder, valid clocks with their sources and an
invalid vector for each refusal; they come with task 1, which the converter's suite reads.
The name `bad-picture` comes with task 1 in the converter, the Python library and the
core's list of reasons; the core produces it, and its suite reads the folder, with task 2.
The folder of the clocks of 20 bytes keeps its vectors.

**Resolution.** `tests/vectors/pictures/build.mjs`; `converter/tests/picture.test.js`,
`converter/tests/clock.test.js`; `odrig/errors.py`; `core/src/reasons.h`,
`core/src/reasons.cpp`.

## Seed 52: where the core keeps a picture clock

**Question.** Seed 52 asks that a picture clock cost the core no memory: its picture
decoded once a turn into the pixel buffer, its hands or digits drawn over it as the LED
data is made, the pixel buffer never written meanwhile. Where are the head, the parts and
the hands of a refresh kept, and what decodes the picture at each check?

**Answer.** The picture is decoded into the pixel buffer as palette indices by the
player's decoder, which keeps its palette; the window of the DEFLATE decoder, which a
drawn type leaves free, keeps the head and the parts from its first byte and, from byte
128, a layer of a byte for each pixel, written at each refresh with the hands and caps or
the digits; `fill_leds` takes the layer's colour where it has one. The window serves the
picture's inflate first: the head is read onto the stack and copied there afterwards.
Each check decodes the picture with the decoder, the window and the pixel buffer it has
for frames, so it needs nothing more. The Python library's header reader allows a widget
32,768 bytes, as the converter and the core do.

**Resolution.** `core/src/clock.h`, `core/src/clock.cpp`, `core/src/container.h`,
`core/src/player.cpp`; `docs/core.md`, "Clocks" and "Memory"; `odrig/odrgx.py`.

## Seed 52: the reference pictures are written the same on every computer

**Question.** The builder of `tests/vectors/procedural/` wrote its PNG files with the zlib
of Node.js, and Node.js on Windows gives other bytes than on the Mac that made them: 18 of
the 35 pictures came out different with the same pixels, and the converter's suite failed
on Windows on one of them. Seed 52 adds pictures of picture clocks; made on Windows, they
would fail on the Mac. How are they written?

**Answer.** The builder compresses with the library's own DEFLATE, which writes the same
bytes everywhere, in a zlib stream of its own making. All the pictures were written again:
every one keeps its pixels, which the core's and the emulator's suites read, and the
converter's suite finds them what their builder makes on Windows too.

**Resolution.** `tests/vectors/procedural/build.mjs` and its pictures.

## Seed 52: what the app does with a picture clock

**Question.** The app lists a picture clock as a `widget`, as `list` says, and so offers
its `Edit`; the form of a clock has no fields for a picture, hands or fields. What does
`Edit` do with it?

**Answer.** `list` says only the type, so the menu keeps `Edit`; the app reads the file as
for any clock, and when it holds a picture, says "This clock is made from a picture: it
cannot be edited here." in place of the form, and sends nothing. The app does not make
one either: the converter's `clocks` does, from an inventory.

**Resolution.** `app/www/screens/author.js`, `app/www/messages.js`;
`docs/android-app.md`; `tests/app/test_authoring.py`.
## Seed 50: which catalogs are of version 2

**Question.** The seed takes the marker's format to version 2 and says a reader of version
1 finds it incompatible. The board's own storage has a catalog too, with no folder and no
index. Does its marker go to version 2 as well, which would make every board's catalog
incompatible after the update?

**Answer.** No. Version 2 is the marker of a catalog with an index, a drive's: the marker
of version 1 with the lines `folders` and `ids` before its `crc` line, 461 bytes. The board's
own catalog stays of version 1, 409 bytes, as it has no index. Each reader takes only its
storage's version: a drive's catalog of version 1, the cards made before the index, is
`incompatible` until `import` or `catalog rebuild external` writes it anew, and a catalog of
version 2 in the board's own storage is `incompatible` too.

**Resolution.** `odrig/catalog.py` (`parse_marker(data, drive)`, `Storage(folder, drive)`);
docs/catalog.md, "The marker"; docs/specs/50-p2-more-than-256-files-on-a-drive/design.md.

## Seed 50: the index's files and lines

**Question.** The seed asks for fixed-width lines and three kinds of file, but names
neither the files, the widths nor the fields beyond a list, and does not say where a
folder's file's CRC-32 stands, since the marker cannot name a number of files that grows
with the folders.

**Answer.** `index-<id>.txt` for each folder, the root's `index-0.txt`, `index-folders.txt`
for the table and `index-ids.txt` for the map. Lines of 180 bytes in a folder's file and
in the table, 36 in the map, padded with spaces before the line feed; a line's last field
is what follows its fixed fields with the padding cut off, which a name never ends in. A
file's line has the fields of its catalog line after its id and `f`, its canvas among
them, so that the core leaves out a file of another canvas without a page; a folder's line
has its id, `d`, its number of own files, which the app shows on a folder's row, and its
path. The table's line has, besides the seed's fields, the ordinal after the folder's last
descendant, the number of files of the folders before it, and the CRC-32 of its file; the
marker names the table and the map with their lines and CRC-32s, so any change of a
folder's file changes the table's CRC-32 and the marker.

**Resolution.** `odrig/catalog.py` (`Index`, `parse_index`); docs/catalog.md, "The index of
a drive".

## Seed 50: the ids the writers give, and the show's

**Question.** The seed keeps the ids stable "as today": the lowest free id when a file is
added, the same files with the same show the same ids. Today the core skips the ids of the
show's items. The PC tool, which writes the index on a computer, does not know the show,
and the two writers must leave the same bytes. And what does a rebuild give, which sorts
nothing in memory?

**Answer.** Neither writer looks at the show. A rebuild and an import give the files the
ids from 60001 in the walk's order and the folders the ids after them in the table's order,
as a listed drive's files and folders get theirs today with an empty show; an upload of a
new file takes the lowest id the map does not hold, a replacement keeps its file's, a
removal frees its own and those of the folders it empties. Where an item of the show has a
drive's id, every command means the item, as `play` finds the show's items first today;
an upload to the show of an id the drive's index holds stays `in-use`. A rebuild that
gives the ids anew in the walk's order keeps the same files in the same order on the same
ids, and writes the map in one pass, without a sort.

**Resolution.** `odrig/catalog.py` (`build_index`, `lowest_free_id`); docs/catalog.md, "The
index of a drive".

## Seed 50: the order a rebuild keeps, and the old index it trusts

**Question.** A rebuild and an import keep the order of the rows they find for the files
still there and put new files after them. Which old index is trusted, and how is a "new"
file told apart in the core, which cannot hold the old rows of a big folder?

**Answer.** The old index is taken when its marker is of version 2 and every page, the
table, the map and each folder's file agree with their CRC-32s and each line is in its
form, the check the core can make by reading each once; otherwise every folder's files are
by the bytes of their names. A folder's old rows are those of the first line of the old
table with its path. A new file is one the old pages have no line for, which the core
finds by reading one page; both writers ask the pages, not the old rows, so that they
agree on every card.

**Resolution.** `odrig/catalog.py` (`_sound_old`, `build_index`); docs/catalog.md, "A
drive's index in a change".

## Seed 50: the record's actions of an index

**Question.** The commit record of version 1 knows `move upload.part <name>` and `remove
<name>`. How does it put a change's index files in place, and in what order?

**Answer.** `move <from> <to>` takes any file of the catalog as `<from>`, and `remove` an
index file too; the record's first line stays `odrig-catalog-do 1`. A change writes each
index file it changes as `.new` before the marker, and the record names them in a fixed
order, so that both writers write the same record: the removals of the files of the folders
that left, the animation's own action, each folder's file in the table's order, the table,
then the map. A file of the index left without a line, the root's or the map, is removed.

**Resolution.** `odrig/catalog.py` (`_index_actions`, `commit`); docs/catalog.md, "A
drive's index in a change".

## Seed 50: where the PC tool adds a file to a drive

**Question.** `add` puts a file into the folder under the last part of its path, so always
into the root. The library's `add` takes any name a catalog may hold. Where does a file
with a folder in its name go in a drive's index, whose folder may not be in the table?

**Answer.** Into the root only, as the board's uploads: the library refuses a name with a
`/` for a drive with `file-malformed`. A file put into a folder on a computer joins the
index with `import`.

**Resolution.** `odrig/catalog.py` (`add`).

## Seed 50: what `status` names, and a folder's count in `list`

**Question.** The seed approves that `status` names the playing animation's path, so that
the app need not hold the whole list. The app also marks the levels that lead to the
current playlist and shows on a folder's row the count of its own files, both of which it
took from the whole list. Which members carry them, and where do they stand?

**Answer.** `status` gains two members before `left`, which stays its last: `file`, the
file of the animation `animation` names, an item's file or a drive's by its path, and
`playlist`, the path of the card's folder whose playlist is current while `playing` is its
id; each `null` otherwise. A folder's item of `list` and `list in` gains `files`, the number
of its own files that `list in` of it gives. All three are parts of the forms the owner
approved, the playing animation named and one level given with its folder rows, and add
no command.

**Resolution.** `core/src/commands.cpp` (`status`), `core/src/content.cpp`
(`content_list`); docs/commands.md, "Status reply" and "Storage and the installed items".

## Seed 50: the revision of a level's order

**Question.** `order get` now gives one level, and `order get in <folder-id>` another. The
revision was the CRC-32 of every listed animation's id and key. Of what is a level's
revision made, and which revision does `order move` compare?

**Answer.** A level's revision is the CRC-32 of the ids of its animations in the saved
order, each as four bytes, low byte first: it changes whenever the level's order or its
animations change, and is the same after a restart for the same files. `order move`
compares the revision of the level of `<id>`, the root's for a show's item.

**Resolution.** `core/src/order.cpp` (`revision_of`, `order_get`, `order_move`);
docs/commands.md, "The saved playlist order".

## Seed 50: what the core checks of a drive's index

**Question.** The PC tool reads a drive's index whole and checks every file's CRC-32 and
every line against the pages. The core may not read the whole index: it publishes the drive
from its marker and reads lines as it needs them. What does it check, and what does it say
of a damage it meets?

**Answer.** The core checks the marker, of version 2, at the plug-in and at each look. It
reads neither the pages nor the CRC-32s of the index's files. A line it reads that is not
in its form, or a file shorter than the lines the marker or the table gives it, makes the
catalog `damaged` with `line` at the next refresh, and the drive's animations go; the PC
tool says `page` for a file of the wrong length. A damage the core does not read is found
by the PC tool's `check`.

**Resolution.** `core/src/drive.cpp` (`index_line`, `drive_row`), `core/src/catalog.cpp`
(`catalog_drive_look`); docs/catalog.md, "The index of a drive"; docs/core.md, "A drive".

## Seed 50: the files a rebuild of a drive's catalog writes for itself

**Question.** The design names `rebuild.tmp` and `rebuild-folders.tmp` and the phases that
write them, but not every field of their lines, nor what the draft of the table holds when
a folder's end and counts are known only after its subtree.

**Answer.** Both have lines of 180 bytes, padded as the index's. A line of `rebuild.tmp` is
`1 <crc> <bytes> <width> <height> <length> <type> <path>` for a file that passed, so that
what follows `1 ` is its page line, and `0 00000000 0 0 0 0 frames <path>` for one that did
not. A line of `rebuild-folders.tmp` is `<ordinal> <depth> <first> <path>`, the root's
`0 0 0`: a folder's own files are the next line's first position less its own, and its end
and its sub-folders are found by reading on until a line of its depth or less, so that no
line is written before it is known. Each phase takes at most eight lines at a step. A
plug-in of a drive that can be written removes both files, as it removes `upload.part`.

**Resolution.** `core/src/catalog.cpp` (`scan_step`, `draft_step`, `folders_step`,
`map_step`, `table_step`, `commit_drive`, `catalog_drive_step`).

## Seed 50: a drive after its rebuild

**Question.** A rebuild used to leave the drive listed, its refused files in `list` with
their faults until the next plug-in. The design reads the drive again from its new index at
the end. What of the files the rebuild refused, and of a drive that is pulled out while it
runs?

**Answer.** At the commit the drive's animations are dropped and its catalog read again at
once, as after another marker: the playlist plays from its first animation, and only the
files of the index are listed. A refused file is logged when the scan meets it, `drive file
<name> left out: <reason>`, for a drive without a catalog as before. While the rebuild
runs, an indexed drive plays from its old index and its catalog stays `ok`; a listed drive
is listed again and its catalog is `none`, as before. A drive pulled out ends the rebuild
without removing anything, since another drive may be in by then; its files are never read
without a record, and the next plug-in of it removes the two files of the rebuild.

**Resolution.** `core/src/catalog.cpp` (`drive_rebuild_step`, `catalog_drive_went`).

## Seed 50: the hosts list every file

**Question.** The core takes a listed drive's first 256 files and 32 sub-folders. Should the
hosts still cut their listings?

**Answer.** The test host and the emulator list every animation file of the drive's folder
to three levels, so that a rebuild reads every file and the core's own cut is tested; the
firmware still stops at 256 files and 32 sub-folders, which the host interface allows. The
emulator's `drive_cut` goes, and the interface's comment says a host may stop there.

**Resolution.** `tests/core/host/host.cpp` (`list_drive`), `emulator/host.py`
(`drive_list`), `core/include/odrig_core.h` (`drive_name`).

## Seed 50: reads of a drive's index at any offset

**Question.** The host interface says the core reads a file with `read_at` from offset 0
on, each call where the last ended, but for the commands `read` and `catalog page`. The
design reads the index's lines by their numbers and finds ids and folders by binary search.
May the core begin a read anywhere in those files?

**Answer.** Yes, in the files of a drive's index, `drive/index-...`, and in the two files a
rebuild writes for itself, `drive/rebuild...`: every host with a drive seeks there already,
the firmware's `readPart` with `fseek` and the emulator's with `seek`. Every other file is
read as before, and the test host still stops on a read of another file that does not go on
where the last ended. The emulator opens and closes a file of the drive's catalog or
index at each read, so that the PC tool may replace it on Windows while the emulator has
the card: the core no longer reads `order.txt` after the marker, which used to let go of
the last file of the catalog it read.

**Resolution.** `core/include/odrig_core.h` (`read_at`), `tests/core/host/host.cpp`
(`read_at`), `emulator/host.py` (`read_at`); docs/core.md, "Rules of use".

## Seed 50: where the cursor's code lives

**Question.** The tasks name `core/src/index.h` and `index.cpp` for the index's rows. The
same calls answer for a drive without a catalog, from its table and its tree. Where do they
go?

**Answer.** Into `core/src/drive.h` and `drive.cpp`, the drive as the rest of the core reads
it, whatever keeps it; the reading and writing of the fields of a catalog's and an index's
lines into `core/src/fields.h`, which the catalog shares. The writers of the index's files
stay in `core/src/catalog.cpp` beside the commit they belong to.

**Resolution.** `core/src/drive.h`, `core/src/drive.cpp`, `core/src/fields.h`.
## Seed 51: the core builds on Windows again

**Question.** Microsoft's compiler does not know `__attribute__((noinline))` and doubts the
`Marker` of `catalog_read_internal`; GCC 16 refuses a comparison of `page_step`. Where does
the mark of a function kept out of line live, and how is a warning that is wrong answered,
when every warning is an error and no flag may change?

**Answer.** One macro, `ODRIG_NOINLINE`, in `core/src/core_state.h`, the header every source
of the core reaches: `__declspec(noinline)` where `_MSC_VER` is defined, which `clang-cl`
defines too, and `__attribute__((noinline))` everywhere else, so that GCC and Clang, and the
firmware and macOS with them, compile the same text as before. A header of its own for one
macro was not needed. The wrong warning, C4701, is answered in the code, not by turning it
off: the `Marker` starts as zeros and is set by `read_marker` before it is read, as before.
The comparison takes the length as an unsigned number; the sum is the same number. The
emulator's check that the library it loads is as new as the core's sources is not part of
this seed; that it ran an old library without a word on 2026-10-27 is told to the owner.
On Windows, outside this seed, the core's suite has one error, a test that writes a file
named `z"z.odrg`; the emulator's suite fails the walk of a folder named `bad.`, which
Windows names `bad`, the position of `test_events`, whose start is not a multiple of 20
frames there, and most times the internal catalog's rebuild through the emulator, answered
`busy`, the same without this seed's change of `catalog_read_internal`; the converter's
suites fail the same folder `bad.`, a file named `a"b.odrg` and a reference picture.

**Resolution.** `core/src/core_state.h`, `core/src/catalog.cpp`, `core/src/player.cpp`;
docs/core.md; tests/emulator/test_build_script.py.
## Seed 47: the slider taken while the field holds text not sent

**Question.** The seed has the slider's move win over text typed and not sent, "whatever
the browser does with the focus", by the slider's own `input` handler. A browser that moves
the focus to the slider when a finger lands on it fires the field's `change` before the
slider's first `input`. What is sent then?

**Answer.** The field's `change` is a commit, and it sends the typed value by the slider's
path; the slider's first `input` then writes its own value into the field and sends it
through the same `sendLevel`, which spaces the two by 200 ms and replaces a brightness that
still waits. The slider's value is the one that stands, on the installation and in the
field. Where the browser keeps the focus in the field, as Chrome does for a programmatic
move, the handler drops the text first, so that nothing typed is sent; the field gives up
the focus only after it holds the slider's value, so that leaving it finds nothing to send.

**Resolution.** `app/www/screens/show.js`;
`docs/specs/47-p2-a-brightness-field-beside-the-slider/design.md`.

## Seed 47: the field and the slider with no value in force

**Question.** The field and the slider "show the value in force" after a commit that sends
nothing. Before the first `status` there is none. What do they show then, and where does
the range line stand?

**Answer.** The field is emptied, with its placeholder `-`, and the slider stands at 0, as
before the first `status` today. The line `The brightness is 0 to 255.` is the paragraph
`#level-range`, in the small lettering of the app's notes, hidden while it says nothing;
it is said for a value above 255 whether the field was entered or left, and goes at the next
keystroke in the field, at a move of the slider and at the next value sent.

**Resolution.** `app/www/index.html`, `app/www/screens/show.js`;
`docs/specs/47-p2-a-brightness-field-beside-the-slider/requirements.md`.

## Seed 47: the APK and the seed's state

**Question.** Seed 47 asks for a new APK with the artifacts, and the working rules have the
last task of a spec make the seed `completed`. Seed 48 is built on the same branch right
after it, and the owner's check on a phone is open. When is the APK built, and what is the
seed's state?

**Answer.** One APK is built from the branch's tip once seed 48 is built too, and put with
the artifacts on the share and on Drive; it holds both seeds. The seed stays `in_progress`
while the owner's check on a phone is open, as seed 43 does; the owner's check closes it.

**Resolution.** `docs/specs/47-p2-a-brightness-field-beside-the-slider/tasks.md`,
`project-seeds/47-p2-a-brightness-field-beside-the-slider/state.json`.

## Seed 48: when the turn in progress is reported

**Question.** The seed has `status` give `repeat`, `loop` and `saved` only while a playlist
turn plays and `animation` names that turn's animation, null at a turn's change until the
new animation's first picture, and has `repeat <id> <n>` refused with `stale` "while they
are null"; but `repeat` alone is also null while the loop's length is not known. When is a
turn reported, which nulls make `stale`, and what does `repeat <id> <n>` do while the length
is not known?

**Answer.** A turn is reported while the show is valid, no test of the mapping shows, the
playlist plays, the animation the latest refresh chose is the one whose turn it is, and the
turn's first refresh has been made. `stale` comes exactly when `loop` would be null: no turn
of that id is reported. While the length of the loop is not known the turn is in its first
loop, `loop` is 1, and `repeat <id> <n>` gives the turn `n` loops, which `repeat` then
reports. Between the end of a turn's time and the refresh that moves on, `loop` is at most
`repeat`, and a `repeat` then keeps that count, so that the turn ends at that refresh.

**Resolution.** `core/src/player.cpp` (`player_reported`, `player_counts`),
`docs/commands.md`; `docs/specs/48-p2-a-bar-for-the-animation-playing-now/requirements.md`.

## Seed 48: Restore default after the turn's own count has passed

**Question.** `repeat <id> default` drops the turn's own value and gives it "the larger of
the default count and the loop now playing". When the default's end lies at or before the
moment, as when 10 loops were saved and the turn is in its ninth of a default of eight, the
turn would end at once in the middle of a loop. And a save or a restore reads the count
after it has changed it. What counts?

**Answer.** Both saving forms act on the turn with the loop that was in progress before the
count changed. A restore whose default turn ends at or before the moment ends the turn at
the end of the loop in progress, never in the middle of one and never in the past; one whose
default ends later plays the default, `max_seconds` cutting as for any default. A save gives
the turn the larger of its `n` and that loop.

**Resolution.** `core/src/player.cpp` (`player_hold_turn`, `player_default_again`),
`core/src/repeats.cpp`, `tests/core/support.py`; `docs/commands.md`.

## Seed 48: the old file of saved repeats cannot be read

**Question.** The host's `read_at` answers -1 both for a missing file and for a failure. A
save reads `repeats.txt` before it writes the next one; a failure taken for a missing file
would write a file with one line and lose every other saved repeat. And how does a host
whose storage cannot be changed answer?

**Answer.** A read that fails after the first byte is `storage-error`, as for `order.txt`;
one that fails at the first byte is `storage-error` too while a saved repeat is in force,
and a missing file otherwise. A host whose storage cannot be changed keeps no saved repeat
and answers the saving forms `storage-error`, after `unknown-id` and `in-use`, as `order
move` does.

**Resolution.** `core/src/repeats.cpp`, `docs/core.md`, `docs/commands.md`.

## Seed 48: the 512 lines of the file

**Question.** A save is `no-space` when the file "already holds 512 lines once a save has
dropped the lines of the board's own files that `show.json` no longer names, which it does
whenever it finds the file full". Which lines count, and which are dropped?

**Answer.** The lines of other animations count; the animation's own line, or lines, are
replaced, so a save of an animation the file names is never `no-space` for the file. When
the other lines number 512, the save drops those `f` lines whose names no item of the show
names, and is `no-space` when 512 remain. `x` lines are never dropped: a card that is out
keeps its lines. A file out of form is written anew with the new line alone.

**Resolution.** `core/src/repeats.cpp`, `docs/commands.md`, `docs/show.md`.

## Seed 48: `repeats over` at a take-up only

**Question.** A drive's lines are matched to its files at its take-up, and the file is read
whole again after every save, upload and rebuild of the drive's catalog. The log is to say
`repeats over` when more than 32 lines match. Does every reading say it?

**Answer.** Only the take-up of a drive, the drive's check reading its part of the file in
steps, says it, once; the whole readings after a save, an upload or a rebuild match the same
first 32 lines and say nothing. `repeats unreadable` is said by every reading that finds the
file out of form.

**Resolution.** `core/src/repeats.cpp`, `docs/core.md`.

## Seed 48: the firmware is built and not put with the artifacts

**Question.** The seed's definition of done has a new firmware put with the artifacts on the
share and on Drive. The owner ordered this run on 2026-10-27 not to upload a firmware: the
board runs seed 45's firmware with the owner's saved budgets, and a firmware without seed 45
would drop them.

**Answer.** The firmware is built, `python3 firmware/fw.py build`, only to prove that it
compiles, and is neither flashed nor uploaded; the APK is put with the artifacts. The commands
`repeat` and the members of `status` need a firmware with this seed on the board, which waits
for seed 45 and this seed to be merged; the app hides `Repeat this`, `Save` and `Restore
default` on a board whose `status` has no `repeat` or `saved`. The seed stays `in_progress`
until the owner's checks on a phone are made.

**Resolution.** `docs/specs/48-p2-a-bar-for-the-animation-playing-now/requirements.md`,
`project-seeds/48-p2-a-bar-for-the-animation-playing-now/state.json`.

## Seed 48: the words of the bar that the seed leaves open

**Question.** The seed names the accessible names of the row actions on the bar, of `Save`
and of `Restore default`, and the sentence said without a reply to `Save` or `Restore
default`. What are the names of `Repeat this` and of its field, and what is said when
`Repeat this` gets no reply?

**Answer.** `Repeat this` is named `Repeat 1 hello.odrg this turn` and its field `Loops of 1
hello.odrg this turn`; the bar is a group named `The animation playing now`. A `Repeat this`
without a reply says `No confirmed reply. The turn's count is read again before another
change.`, as `Save` and `Restore default` say theirs of the saved repeat. The row actions
take the first word of the menu's label, and their names the label in full with the
animation after its first word.

**Resolution.** `app/www/screens/show.js`, `app/www/messages.js`, `docs/android-app.md`.

## Seed 48: when the bar keeps what it shows

**Question.** The bar stays on its animation while its field has the focus, while a line of
it is out, and until its field has been without the focus for a second. Does the field
follow `status` after a reply while it still has the focus, as after Done?

**Answer.** The text sent is no text not sent: after a reply the bar no longer waits out the
second after the field lost the focus, and the field follows `status` once it has not the
focus; while it keeps the focus, after Done, it keeps the text it was sent with. The second
is counted from the document's `focusout`, which `main.js` passes to the screen, and the bar
is drawn again with each `status`, about once a second.

**Resolution.** `app/www/screens/show.js`, `app/www/main.js`.

## Seed 48: how the frozen top is measured

**Question.** The panel sticks while at least 80 px stay between it and the tabs, opaque,
and a field brought into view stops under it. What is measured, when, and with which colour?

**Answer.** The room is the height of the view less the band of the phone's bar, the panel
and the tabs, measured at every draw of Animations, about once a second, and at every
`resize`, which also follows the keyboard; the panel sticks while Animations is shown, the
keyboard is closed and the room is 80 px or more. While it sticks its colour is `#0f1630`,
the panel's own over the midnight, made opaque, and the page's `scroll-padding-top` is the
band and the panel, so that a field scrolled into view stops under it. `Select` on the bar
scrolls the row to 8 px under the panel, or under the band while the panel does not stick.

**Resolution.** `app/www/screens/show.js`, `app/www/style.css`, `app/www/screens/reorder.js`.

## Seed 49: the lines of each reply, not each page

**Question.** The seed says that the keys of a page are used as soon as that page is read.
A page of the card's catalog takes several replies of 512 bytes. Is a key used when its
page has ended, or sooner?

**Answer.** Sooner: the whole lines of each reply give their rows their keys as soon as
the reply has come, which is what the owner asked for, each preview as soon as it can be.
A line is whole when it is taken, so no half key is used. A page of another generation
starts the read again and drops what it had taken, and a read that ends without keys
leaves `reads`, so that no line of either gives a key. The keys of the storage,
`state.keys`, are still set only when the read has ended whole, and only those are kept on
the phone.

**Resolution.** `app/www/client.js`; docs/android-app.md; tests/app/test_keys.py,
tests/app/page/scenarios/keys.js.

## Seed 49: the keys kept on the phone

**Question.** How are the keys kept between two starts of the app, and what if they come
later than the first reply of `catalog`?

**Answer.** In the database of the phone's own previews, `odrig-previews`, at version 2,
whose upgrade creates each of its stores, `previews` and `keys`, that it lacks, so that a
phone of version 1 keeps its previews. A record of `keys` is named `<address> <storage>`,
the address as the app keeps it, and holds `{generation, entries, names}`, `names` the
pairs of name and key; a record of another shape is skipped. One connection serves both
stores. An open that an older connection blocks is given up for this run, and is closed if
it succeeds later; the connection closes on `versionchange`. Keys kept in this run before
the database is open are not replaced by older ones, and are written when it opens. No
page of a catalog is asked before the kept keys have been taken or found missing, so that
a reply of `catalog` that comes first does not start a read the kept keys would have
spared; a read it started ends when they come. Should IndexedDB never answer, the pages
are asked three seconds after the start, as before this seed.

**Resolution.** `app/www/previews.js`, `app/www/client.js`, `app/www/main.js`;
docs/android-app.md; tests/app/test_keys.py, tests/app/page/scenarios/keys.js,
tests/app/page/scenarios/ownpreviews.js.

## Seed 49: a preview by name and size, and the test's own catalog

**Question.** Which key does a file's name find, and how is a name of two keys tested when
the default catalog has none?

**Answer.** The keys the default catalog gives the file's name, of the row's size; when
the catalog does not name the file at all and the file holds a `/`, those of its own name,
the part after the last `/`, since a run of `thumbnail` without `--card` names a card file
by its own name only. Exactly one key is used; none or more than one give no preview until
the board's key is read. The suite's server serves a folder of the test's own in place of
`thumbnails/` when `support.run` is given `thumbnails=`, with a `catalog.js` and GIFs the
test writes; the stand-in `Paged` can refuse every page with `busy` and list the card's
folders. The plan of `keys.js` waits for a number of rows, `untilRows`, rather than the
spec's `{"until": "rows"}`, and opens a folder with `enter`.

**Resolution.** `app/www/previews.js`, `app/www/screens/show.js`; tests/app/support.py,
tests/app/test_previews.py, tests/app/test_keys.py, tests/app/page/scenarios/keys.js.

## Seed 49: the APK waits

**Question.** The seed's Definition Of Done builds the APK from the branch. Is it built?

**Answer.** No, not by this seed's tasks. On 2026-10-28 the owner asked: "do not rebuild
apk, another agent is working on apk changes so only after they finish we can rebuild apk,
but you may test this on an emulator". The APK of the branch is built when that work has
ended, for the owner's check on a phone.

**Resolution.** docs/specs/49-p1-previews-at-once/tasks.md, task 6.

## Seed 49: the measurement

**Question.** How many requests does the app send before its first preview, before the
seed and after it, and what does that mean on the board?

**Answer.** Measured on 2026-10-28 with two emulators side by side, one of `master` at
`3709ce0` and one of this branch, each with the show `scratch/seed-44-show`, 116
animations, and the card copy `scratch/all-card-local`, 235 animations of catalog
generation 2, `--drive-read-only`; the app at `/app/` in a browser, and each emulator's
log of commands read from `/events`.

- `master`, at the first start and at the second alike: 86 requests before the first
  preview, among them the 44 parts of `list`, `catalog` and 44 `catalog page`; 98 `catalog
  page` in the first 15 seconds of each start; every preview of a storage asked for within
  a few milliseconds of the first.
- The branch, first start: 45 requests before the first preview, `status` and the 44 parts
  of `list`, and no `catalog page` before it. The previews are asked for as soon as the
  rows are drawn, and the pages are read after them, 98 in 15 seconds.
- The branch, second start: 45 requests before the first preview, and no `catalog page` in
  the first 15 seconds; `catalog` was asked twice, and the kept keys answered both times.

The list itself, 44 parts for 351 animations, is what the rows wait for now; this seed
does not change it. The round trip to the board was not measured: the board answers on its
own Wi-Fi network, at 4.3.2.1, which this computer is not on, and joining it would change
the computer's network. Each request costs one round trip on the board, so the first start
waits 41 round trips less for its first preview, and a second start sends 44 or more
requests fewer; the seconds wait for the owner's session.

**Resolution.** docs/specs/49-p1-previews-at-once/tasks.md, task 5.

## The owner's ruling of 2026-10-28: GIFs beside a seed, and line ends

**Question.** Seed 52 tracks twelve GIFs of reference in its folder, and two text files of
its references end their lines with a carriage return and a line feed. The converter's
test let no GIF be tracked but the previews of `thumbnails/`, and the emulator's test lets
no tracked text file hold a carriage return, so both failed on `master`.

**Answer.** The owner's words of 2026-10-28: "gifs are acceptable alongside seeds", and the
conversion of the text files from Windows line ends to Unix ones is accepted. A GIF may be
tracked anywhere inside a seed's folder, `project-seeds/NN-.../`, besides the previews of
`thumbnails/`; MP4 and MOV files are still tracked nowhere. The two text files,
`references/conversation.txt` and `references/standalone/standalone-script.js`, end their
lines with a line feed alone now, and hold no other change.

**Resolution.** converter/tests/library.test.js; the two files of
project-seeds/52-p2-a-hundred-picture-clocks/references/; docs/decisions.md.

## The owner's order of 2026-10-28: one Select, the power icon and a collapsing panel

**Question.** On 2026-10-28 the owner ordered five changes of the operators' app and had
them committed on `master` before their tests and documents, by the owner's exception to
the rule of one's own branch (269e50a and 4dc1c22): the list's own `Select` and `Add
animation` go, the line of what plays and the words `On` and `Off` are hidden, the power
icon alone switches the LEDs, and a chevron collapses the panel of what plays to its top
row. Which points did the order leave open, for the tests and the documents that followed
the same day?

**Answer.**

- Where the selection starts. With the list's `Select` gone, the selection mode starts
  only from `Select` in an internal row's menu or on the bar, each with its row ticked.
  While nothing plays, or a cycle, a test or an animation the list lacks plays, the bar is
  hidden and a row's menu is the one way. A level where no row's menu offers `Select`, a
  folder of the card or an installation that does not report inclusion, offers no
  selection, as the list's `Select` was off there before. The suite starts a selection from
  the first row of the level whose menu offers it, `startSelection` of
  `tests/app/page/reading.js`.
- The line of what plays is hidden by the style sheet alone and keeps its words, which
  the app writes as before. The suite reads its words, `playing` of `reading.js`, waits on
  them with a pattern, `line`, where it waited on the screen's text, and pins that the line
  is not shown. So Animations no longer shows the time left in a playlist's window, a
  cycle's id, or why the installed show is invalid; the target screen still says why a show
  is invalid, and so does the message of a refused play. The hand-over of this work says
  so to the owner.
- The buttons `On` and `Off` stay in the page, hidden, with their `aria-pressed`. The
  suite presses the power icon by its id, `tap` of `tests/app/page/driver.js`, and the
  lists of controls that must stay pressable name `power-toggle`.
- The power icon follows the status alone: a press sends `off` while the icon is pressed
  and `on` otherwise, and the icon changes when a status says the LEDs changed, not at the
  press. A second press before that status sends the same line again.
- The collapse button is 48 pixels, as the message of 4dc1c22 says, where its style had
  44: the look wants the main controls 48 high. The icons of both buttons are held to the
  contrast of the texts, 7:1, lit and dark, the panel whole and collapsed.
- The panel's `position: relative`, left from 269e50a's collapse button placed against
  it, went: nothing is placed against the panel any more, and the frozen top's test wants
  the panel static while it is not frozen.
- The choice to collapse is kept per phone, under `odrig.panel` in the web view's local
  storage, as the filters' choices are.

**Resolution.** `app/www/style.css`; `tests/app/page/reading.js`,
`tests/app/page/driver.js`, `tests/app/test_panel_top.py`,
`tests/app/page/scenarios/paneltop.js`; docs/android-app.md.

## Seed 53: isolation under load, and the slowest tests

**Question.** Task 2 of seed 53 mends every failure that comes from two workers or two
suites sharing a file, a port or a build. What did the first loaded run show, and where
does the work go that brings the slowest tests within requirement 8.1?

**Answer.** The first run of `tests/run.py` with its default eight workers, on db81baa with
the runner of task 1, failed in nothing shared: every failure of the emulator's, the
app's, the core's and the converter's suites was absent, and the one failure, of
`tests.firmware.test_paths`, came from the firmware tool's Python environment linked into
the checkout from another one, which task 6's `ODRIG_TOOLS` settles. The suites already
take their ports from the system, their folders from temporary directories and their
Chrome profiles from temporary folders, and the firmware suite compiles its host program
into a temporary folder; the emulator's package no longer builds the core under the
runner (task 1). Its wall time was 631 s, against 1,954 s for the same suites one after
another; the core's suite, 598 s, was bound by one test of 492 s,
`test_the_memory_does_not_depend_on_the_length_of_a_clip`, whose time is the test host's
`read_at` reading the whole of a 10.8 MB file again for every call of at most 512 bytes.
That and the other tests that keep a suite above a third of its time alone are task 3's,
with the timing: requirement 8.1 is met there.

**Resolution.** No code changes for task 2; task 3 takes the slowest tests with the timing.

## Seed 53: the slowest tests, a module split by its classes, and timing under load

**Question.** Task 3 makes the tests that fail under load robust and brings the core's,
the emulator's and the app's suites within a third of their time alone (requirement 8.1).
What did that take?

**Answer.** Three things. The core's test host read a whole file from storage again for
every `read_at` of at most 512 bytes; a 10.8 MB clip took 193 s to play. It now keeps the
content it read while the next call goes on where the last ended, with no storage call
and no change of the drive in between, and reads anew otherwise; the clip plays in 0.6 s
and the core's suite alone takes 368 s instead of 564. The runner gives a module that took
more than a worker's share in the previous report by its test classes, and the report
keeps the times of the suites a run did not run. And under load the app asked an
installation that keeps no catalogs twice: the client asks once the target answers, and
Settings' question, queued behind that answer, was sent after it; a queued question is now
not sent once the installation is known to keep none (`client.catalog`), with a test whose
stand-in answers in three seconds. Three passes in a row with eight workers then took 435,
377 and 399 s, against 1,954 s one after another, with no failure but the linked Python
environment of task 2's entry. Alone through the runner: core 95 s (564), emulator 58 s
(387), app 271 s (854, its four workers kept).

**Resolution.** `tests/core/host/host.cpp`'s `read_at`; `tests/run.py`'s `split` and report;
`app/www/client.js`'s `catalog`; `tests/runner/test_runner.py`; `tests/app/test_catalog.py`.

## Seed 53: no process left behind, without a helper of its own

**Question.** Task 4 names `tests/children.py`, a marker set to `manual` outside the runner,
and process groups for every starter. What was needed?

**Answer.** The emulators found running for days were left by starters killed without a
chance to clean up, which no cleanup can mend; the emulator now takes `--parent PID` and
ends within two seconds after that process ends, and the preview and the emulator suite's
starter give their own id. The starters already put their children in a group of their
own. The runner sets `ODRIG_RUN` for its children, which every child inherits, ends at a
run's end what still carries its id, and `--sweep` ends every process that carries any id
and every emulator of a temporary or a preview's folder; outside the runner no id is set,
and the sweep's second rule finds those emulators. So no helper module and no `manual` id.
A preview also removes, at its start, the work folders of previews no longer running, and
the preview's tests look at their own folder only. Under load, a test of the app's kept
keys found the board's pages read again after the card was back rather than before; it now
looks for them from the moment the board's catalog is whole.

**Resolution.** `emulator/parent.py`, `emulator/app.py`'s `--parent`, `preview/__init__.py`,
`tests/run.py`'s `strays`, `end` and `--sweep`, `tests/emulator/test_parent.py`,
`tests/app/test_keys.py`.
## Seed 52: the inventory, its motions and the subcommand `clocks`

**Question.** The seed asks for one inventory that the converter reads, and for the motions
of the tiles that show no time, of the kinds it names, and leaves their form, the reading
and the place of the code to the spec. What are they?

**Answer.** A subcommand of the converter, `clocks INVENTORY.json --out DIR`, so that the
files can be made again from a clone, with `converter/lib/inventory.js` and
`converter/lib/motion.js` beside the other modules. The inventory holds each tile's
palette and picture as a picture clock's source does, rows of palette digits, so it needs
no reader of images; a tile's base picture is that picture. A motion is up to 8 parts,
each working on what the ones before it made: a level that falls and rises again in a
triangle over the loop, so that it loops without a jump; a flicker of 2 or 3 recolourings;
a pulse through up to 8 recolourings and back; a turn and a swing of the pixels of some
colours about a point. Turns and swings are made in whole numbers with the sine table of
the clocks, so the same inventory gives the same bytes on every computer, and they keep
the palette's colours, as a recolouring does: no motion makes a colour. Every file is made
before one is written. The design's `from` and `to` of a level are named `start` and
`half`, its share at the start of the loop and at its half: the library's test of its own
imports reads a quoted `from` as one.

**Resolution.** `converter/lib/motion.js`, `converter/lib/inventory.js`,
`converter/cli/clocks.js`; `docs/converter.md`, "clocks".

## Seed 52: the tiles reduced to 8 colours

**Question.** Each tile is to be "scaled to 60 x 60 and reduced to" at most 8 colours,
"black among them when the clock has black". The cut tiles are not square: those of the
lower rows of the owner's picture are 103 to 114 pixels high and about 122 wide, because
the picture's rows are. How is a tile scaled, how are its colours chosen, and where is the
tool?

**Answer.** Each cut tile is scaled to 60 x 60 as it is, with Pillow's box filter: the
lower rows' tiles are stretched up to 17 percent in height, which pixel art bears, rather
than given bands that are not in the picture. Its colours are a median cut of the scaled
tile, refined by k-means, 8 or fewer; when the tile has a pixel darker than 24 in each
channel, the colour nearest black becomes black. Each pixel takes the nearest colour,
without dithering, and the colours are ordered from dark to light. The tool, `prep.py`,
and every other tool of the inventory are kept with the collection in
`clocks/source/tools/`, as the inventory is, and were run from `scratch/clocks52/` of the
first checkout on the Windows computer; the kinds came from a look at the picture: 38
dials, 28 displays and 34 motions, the list of
`docs/specs/52-p2-a-hundred-picture-clocks/design.md`.

**Resolution.** The collection's `clocks/source/tools/prep.py` and
`clocks/source/inventory.json`.

## Seed 52: the dials of the inventory

**Question.** For each of the 38 dials: which hands it has, where its pivot is, how its
painted hands are erased, and how fast it runs. The seed calls a sundial's shadow "a dial
with one hand" and lists sundials among the tiles that show no time.

**Answer.** The sundials and the obelisk, tiles 1 to 3, are dials of one hour hand in the
shadow's colour about the foot of the gnomon: the hand the seed names; it hides behind the
gnomon for part of its turn, as a shadow would. A dial's numerals and marks stay: they are
its face; only its hands are erased, painted with the colours of the face around them, a
column's own grain on the wooden tile 38. Hands are drawn in the colours the tile's hands
had, an hour hand of half width 2 and a minute hand of 1 where the dial is big enough; a
second hand only where the tile had one (33, 39, 45, 58 and 76), and those dials run 2 to
30 times real time so that the second hand can be followed, the others 60 to 600. Several
pivots where the tile has several dials: the world map, tile 59, with three clocks 5 hours
behind, at and 3 hours ahead; the chess clock, tile 70, two hours apart; the chronograph's
four small dials, tile 33. Where the palette lost a hand's colour (the red hands of 39 and
58) the nearest colour of the palette draws it, and on the busy faces of 34 and 50 a light
hand is drawn over a wider dark one so that it reads. The kitchen timer, tile 68, has one
hand, a minute hand of its pointer's two colours; the stopwatch, 76, a second hand only.
Every dial runs 30 seconds a loop in a random direction, turns 30.

**Resolution.** The collection's `clocks/source/inventory.json`; the scripts of each tile
in `clocks/source/tools/helpers-dials/`.

## Seed 52: the displays of the inventory

**Question.** For each of the 28 displays: the box of its time, the font that fits it,
what it shows, and its colours; and the tiles whose time is not one line.

**Answer.** The time is erased by painting its box with the display's background, labels
that are not the time kept (GPS, NTP, the date of tile 64, the cities of tile 60, the
battery's charge bar of 89). The font is the largest whose widest time fits the box whole,
checked over every time of a day: `medium` for most clocks of 10 rows, `small` for
watches, the holograms and the lines of seconds, `large` only for the LED matrix 26,
`tiny` for the parking meter 86. The flip clock 24 and the band 29 have a field for the
hours and one for the minutes; the nixie tubes 25 a field for each tube; the three cities
of 60 three fields at offsets 0, -7 and -2 hours. The time sources 51 to 53 show
`hh:mm:ss`, the timers 66, 67, 75 and 83 minutes and seconds (`m:ss` on 83, as its picture
shows `5:00`), the traffic light 84 its seconds; those run 2 to 30 times real time, the
others 60 to 600. The colons of the digital clocks blink; those of the flaps, tubes and
lights do not.

**Resolution.** The collection's `clocks/source/inventory.json`; the script of the
displays in `clocks/source/tools/helpers-displays/`.

## Seed 52: the motions of the inventory

**Question.** For each of the 34 tiles that show no time: its motion, of the kinds the seed
names, and how far its picture may be changed to make the motion read.

**Answer.** Hourglasses (4, 5, 6, 74, 79, 87, 88) and water clocks (7, 8, 9) are levels:
the upper sand or water falls while the lower rises, and in the second half of the loop
the sand goes back up, which is the installation's "this is not the time" and loops
without a jump; a falling stream is a flicker of three variants that moves down a pixel a
step. Flames, smoke, the lava lamp, the bulb, the waves of the mast, the satellite and the
tuning fork, the calendars, the moon displays, the drum machine, the music box, the atom's
electrons and the zen garden's rings are flickers or slow pulses of palette colours. The
metronome 71 swings and the egg timer 69 rocks; the gears 92, the water wheel 93 and the
spinner 80 turn. Where the reduced picture of a moving part was too ragged to turn
cleanly, the part was drawn again in its own colours about one centre (the metronome's
arm, the spinner's dots, the gears, the water wheel, the zen garden's rings, the window's
hourglass 88); every other tile keeps its picture but for a few stray pixels. Every motion
runs 12 to 16 seconds, its frames 50 ms apart, the spinner's 150 ms, one dot a frame.

**Resolution.** The collection's `clocks/source/inventory.json`; the script of each tile in
`clocks/source/tools/helpers-motions/`.

## Seed 52: the hundred made and kept

**Question.** Where do the 100 files go, with what, and how are they known to work?

**Answer.** `clocks` made them from the inventory in one run: 38 picture dials and 28
picture displays of 393 to 1,218 bytes each, and 34 frames files of up to 45,633, 153,655
bytes in all.
`check` accepts each, and each has at most 8 colours, counted over the pictures of a
frames file and over a clock's pictures every 250 ms of its loop with three seeds: 97 of
them 8, the others 5 to 7. Their previews, made by `thumbnail --catalog thumbnails`, are
100 GIFs in `thumbnails/`, 1,775,742 bytes, committed; the collection's folder `clocks/` on the share holds
each file with its preview `X.gif`, the copy of its GIF in `thumbnails/`, and its readme
`X.md` in the shape of seed 46, which names the owner's picture, the tile and its place;
and `source/` with the owner's picture, the 100 cut tiles, the inventory, each base picture
as a PNG and the tools. Nothing of it is committed. The emulator, given a drive whose
folder `odrig` held the 100, listed all of them and played each with `play <id>`, `status`
naming it with a seed. A recording of 16 seconds played the wall clock, tile 15, and the
red alarm clock, tile 21, twice each, each turn begun by `play`: the wall clock went
backward at about 7.5 minutes a second, then forward at 2.5; the alarm clock backward at
1.4, then backward at 3; 7 to 59 LEDs changed in each second.

**Resolution.** `thumbnails/`; the collection's `clocks/`.

## Seed 52: the original six of the twelve

**Question.** The original six are to be rendered from `references/original/animation.js`
"by calling the script's drawing at each frame's time", 8 colours each: "black, then the
colours its script draws with, most used first". The script draws only on its own timer
and keeps its drawings inside its closure; and on its 60 x 60 canvas almost no pixel has a
named colour exactly, every dot and line being soft at its edges. How are the frames taken,
which colours count as used, and how near are the files to the reference GIFs?

**Answer.** The page that renders adds one name after the script's own list of its six
drawing functions, which are pure functions of the time, and calls them at 0, 50, 100 ms
and so on, on the script's own canvas after its own background: so each frame is the
script's picture at that time exactly. The colours the script names are `#d6e3e8`,
`#51e6df`, `#ef80bd`, `#ffc577` and `#354953` and its background `#040609`, which is black;
each pixel counts for the named colour whose blend with the background comes nearest it,
and the colours that a scene uses come after black, the most used first: 4 to 6 colours.
Every other pixel takes the nearest of them. At 50 ms a frame every file is far below
2 MB, so none is taken at 100 ms: the largest, every row 720 s, has 471,095 bytes, the
others 1,443 to 23,875. Compared with the reference GIFs at their 100 ms frames, mapped to
the same colours, two times and every row differ in no pixel, the clock that melts in at
most 4 of 3,600, sand in at most 93 and we were here in 58, both at single frames; never
zero differs at each whole second, up to 792 pixels, a digit: the GIFs were rendered by
adding steps of 0.1 s, which lands just before the second, where the file shows the
script's time exactly. Every row is compared over the GIF's 144 seconds of its 720.

**Resolution.** The collection's `clocks/time-original-*.odrg` with their readmes;
`clocks/source/tools/render12.mjs`, `make12.mjs` and `compare12.mjs`.

## Seed 52: the standalone six of the twelve

**Question.** The same for the standalone six, whose script names many colours.

**Answer.** `TimeAnimations.draw(ctx, scene, seconds)` of
`references/standalone/standalone-script.js` draws a scene at a time on a canvas of the
page's own; its frames are taken at 0, 50, 100 ms and so on for 18 seconds. Of the colours
the script names, the seven a scene uses most, by the same count, follow black: 8 colours
each. Every file is below 26 KB at 50 ms. Compared with the GIFs the page held, at their
times, mapped to the same colours, they differ in 24 to 73 pixels of 3,600 on average, at
most 45 to 109: the page made its GIFs another way, and the colours of a soft edge fall to
one side or the other of a nearest colour.

**Resolution.** The collection's `clocks/time-standalone-*.odrg` with their readmes; the
same tools.
## Seed 50 and seed 48: the saved repeats of a drive's files

**Question.** Seed 48 keeps the saved repeats of 32 of the drive's files by their places,
found by the hash of `order.txt`'s entries, and reads the drive's lines of `repeats.txt` in
steps after the drive's part of `order.txt`. Seed 50 takes the places, the hashes and the
drive's part of `order.txt` away: an indexed drive has positions in its walk and no listing.
How do the two meet?

**Answer.** An entry holds the position of the drive's file in its walk and its loops, 8
bytes. A line `x <name>` finds its file by its path: a listed drive's by the host's names of
its places, an indexed drive's in the rows of the folder of its path. The file is read whole
at once when the drive is taken up: a listed drive's at its first step, before its files are
checked; an indexed drive's when it is published, before any of its files plays. An upload
to the drive and a removal from it read the file again, since the positions after them
move; a rebuild reads it with the drive read anew. The limits stay: 32 entries, `repeats
over` once, `no-space` for a 33rd.

**Resolution.** `core/src/repeats.cpp` (`apply_drive`, `repeats_drive_taken`),
`core/src/drive.cpp` (`drive_position_named`), `core/src/core.cpp` (`drive_step`),
`core/src/catalog.cpp` (`publish`); docs/core.md, "The saved repeats".
## Seed 46: the installation's animations in git, the heavy ones on the share

**Question.** The decision committed the JSON source of every animation; seed 10's answer
committed an imported source in `animations/` up to 50 MB; the pages called the remote
private; and "Seed 44: the tracked previews are the media the repository holds" let no GIF
be tracked but the previews, and since 2026-10-28 GIFs beside a seed. Where is an
animation the installation is given kept now, and what does git track of it?

**Answer.** By the owner's answers of 2026-10-27 and 2026-10-28: git tracks `collection/`,
each small animation file of `card/`, `earlier/` and `others/` with its `X.gif`, a copy of
its preview, and its readme `X.md`; of a heavy file, a group of a long video or a file
over 50,000,000 bytes, only its GIF and readme in `long/`, its key and its path on the
card being in `thumbnails/catalog.js`. The share's collection, at `ODRIG_ANIMATIONS` of
`env`, holds every file. No JSON of these animations is committed. The remote is public,
and the tracked collection is published with it. The decisions this work took beyond the
seed:

- The collection built by hand in the owner's checkout was moved whole to
  `scratch/collection-built-2026-10-27/`, and its line of `.git/info/exclude` removed, in
  the first task: that line held for every worktree and hid every path of `collection/`
  from `.gitignore`, so the files could only have been staged with `-f`. The archive is
  only read since; the share holds every file.
- The moves on the share were made and checked by a script of the agent's in
  `scratch/collection-46/`, reading every file back against the archive; the share's path
  came from `env`.
- `collection/README.md` is a tracked file now; the share's copy has its bytes.
- The test of the collection is in the onboarding suite, which checks what a clone holds;
  it asks a git of its own about the lines of `.gitignore`, so that no exclude of one
  computer counts.
- The converter's test of tracked media lets the collection's GIFs be tracked, besides
  those of `thumbnails/` and of a seed's folder.
- `env` and `../../env` are names a page may give although no clone holds them, matched as
  whole words, so that `env.template` is still looked for.

**Resolution.** `.gitignore`, `collection/`, `converter/cli/`, docs/converter.md,
docs/decisions.md, agent/animation-guide.md, agent/vocabulary.md,
agent/getting-started.md, agent/working-rules.md, agent/README.md, docs/format.md;
tests/onboarding/, converter/tests/library.test.js, converter/tests/thumbnailtool.test.js.

## Seed 46: the measurement

**Question.** How large is the repository with the collection, and is every animation
available?

**Answer.** Measured on 2026-10-28 on the branch of the seed. Before the commit of the
collection, `git count-objects -vH` gave 33.24 MiB of packs; after it, 607.54 MiB. What
`master` reaches is 28,910,112 bytes; what the branch reaches, 631,177,331, about 602 MB
more. A clone of the branch, `git clone --no-local --single-branch`, holds 629,060 KiB of
git and 672,136 KiB of files, 2,963 tracked files, 1,002 of them in `collection/`, and no
animation file of `collection/long/`.

A check of every animation, `scratch/collection-46/available.py` of the first computer,
ended with `AVAILABLE 359`: each of the 359 animation files of the collection built on
2026-10-27, by its key, is on the share's collection with its bytes; the 283 small ones
are tracked with their bytes; the 76 heavy ones have their GIFs, their readmes and their
keys tracked, each key with the file's path on the card among its names.

Every suite that works on the first computer passed: the converter's 1,435, the Python
library's 534, the core's 886, the emulator's 639 (10 skipped), the app's 344, the
onboarding suite's 86, the mapping's 43, the walk-through's 5 and the firmware tool's 623.
The walk-through, which clones the repository, took 1,418 seconds.

**Resolution.**
docs/specs/46-p2-every-animation-file-tracked-with-its-preview-and-source/tasks.md, task
6.

## Seed 50: the memory with a drive, after seed 48

**Question.** Requirement 8 asks the core's memory with a drive to stay below 130,509 bytes,
the figure before seed 48. Seed 48's saved repeats came in on the way, with 4 bytes for each
of 32 entries, and an indexed drive's positions do not fit in their 16 bits. Is the
requirement kept?

**Answer.** Against the same core without the index, it is: the cursor of 972 bytes and 40
bytes more of the core object take the place of the saved order's 4 bytes for each of 256
places, 1,024. The saved repeats' entries grow to 8 bytes, a position of 32 bits and the loops,
128 bytes more, so the target file with a drive takes 130,761 bytes, 116 more than master's
130,645 and within the 131,072 the core may use. Nothing else is cut to win the 116 back.

**Resolution.** docs/core.md, "Memory"; docs/decisions.md, the change log of 2026-10-28.

## Seed 50 and seed 48: the bar of the animation playing now, one level at a time

**Question.** Seed 48's bar names the animation playing now from the whole list, and its
`Select` went back to the root to select it there. Seed 50's app holds only the level
shown. Where does the bar show, and what does its `Select` do?

**Answer.** The bar shows while the level shown holds the animation that plays, the root
playlist or a folder's playing, as `status` names it; on another level it is hidden. Its
`Select` selects the animation in the level shown, the filters showing it, as a row's menu
does. The stand-in of the app's tests answers `list` and `list in` one level at a time.

**Resolution.** `app/www/screens/show.js` (`barAnimation`, `selectFromBar`);
`tests/app/test_now_bar.py`.
## Seed 52: the clocks placed as the collection says

**Question.** The tasks of seed 52 kept the 112 files outside git, in the share's
collection `clocks/`, with their sources there too. Then the collection's standard was
merged with seed 46, `collection/README.md`: an animation the installation is given is
tracked in `collection/`, at its path on the card, with its GIF and readme beside it. The
owner asked on 2026-10-28 that seed 52 follow it. Where do the files and their sources go?

**Answer.** The 112 files are in `collection/card/clocks/`, their path on the card
`clocks/`, none of them heavy: the largest has 471,095 bytes. Each has `X.gif`, written
by `thumbnail --catalog thumbnails --card collection/card --beside`, so the line of its
key in `thumbnails/catalog.js` holds `clocks/X` too; and `X.md` of the 16 lines, its
Platform `unknown`, as none of the platforms the standard lists made it. Their sources,
the owner's picture, the 100 cut tiles, the inventory, the base pictures and the tools,
are tracked beside the seed in `project-seeds/52-p2-a-hundred-picture-clocks/source/`,
with `twelve.json` and `comparison.json`, what the twelve's colours were and how near
they came to their GIFs: they make the files, and the collection holds animations only.
On the share, the same files are in the collection's `card/clocks/`, and its earlier
`clocks/` was moved, not deleted, to artifacts/odrig/archived/collection/clocks/; every
file was read back. The earlier entries of this seed name `clocks/source/` of the
collection: that is now the seed's `source/`. With the clocks the card's folder `odrig`
of the collection holds more than 256 files, the most a card takes today; seed 50 is the
work that lifts that limit.

**Resolution.** `collection/card/clocks/`; `project-seeds/52-p2-a-hundred-picture-clocks/source/`;
`thumbnails/catalog.js`; `docs/specs/52-p2-a-hundred-picture-clocks/requirements.md` and
`design.md`.

## Seed 54: the message's frames, colours and size

**Question.** The requirements ask for 120 frames of 50 ms from the owner's page
`horror-text-60x60.html`, its colours as the page draws them. The page anti-aliases its
Hebrew text, blends a dark red edge and scanlines over it, and lays a noise that changes 12
times a second; what does the file hold, and is it light enough for the card?

**Answer.** `render-message.mjs` steps the page's clock to 0, 50, ... 5,950 ms and takes
120 frames of 50 ms; two runs gave the same bytes. Six of them, at 50, 150, 300, 1,550, 4,650
and 4,800 ms, are the same as the frame before: the page's noise holds for 83 ms, and the
text then stands still while its scanline is off the canvas. The converter merges them as
the format says, so the file has 114 frames, 6,000 ms in all.
The page draws 855 colours, kept as they are, not reduced to 8: the file has no palette,
3 bytes a pixel, and its body is compressed. `its-not-the-time.odrg` has 120,969 bytes,
key `5218d8e1-120969`, far from heavy; `check` accepts it.

**Resolution.** `project-seeds/54-p2-clocks-between-the-animations/source/render-message.mjs`;
`collection/card/clocks/message/`; `thumbnails/catalog.js`.
## Seed 54: the two members of `status` and the longest reply

**Question.** `clocks` and `clock_message` add 37 bytes to every reply of `status`. The
suite's bound of the longest reply added the longest reason text of an invalid show to a
file being checked and a seed, and came to 1,059 bytes with them, above the 1,024 of a
reply. Does the reply still fit?

**Answer.** Yes. The core writes a reason text only while the show is invalid, and then
`checking` and `seed` are `null`; the bound took both at once. Taken apart, a valid show
with a file of 32 characters being checked and a seed of ten digits comes to 996 bytes,
an invalid one with a reason text of 65 characters to 999, each with the longest name of
a host, every byte of it escaped. The suite's bound now takes the two cases apart.

**Resolution.** `tests/core/test_commands.py`, `LineEndings`.

## Seed 54: the settings and the breaks in the core

**Question.** The design of seed 54 names the core's code for the two settings of the
clocks and for the breaks. What does the code do where the design leaves a point open or
the code differs from it?

**Answer.**

- `clocks.txt` is read at the start only by a core whose storage can be changed, as
  `order.txt` and `repeats.txt` are; on a host whose storage cannot be changed both
  settings are off, and the four lines answer `storage-error`, as `repeat`'s saving forms
  do, before a setting already in force is looked at.
- A failed read of `clocks.txt` at offset 0 is taken as a missing file, both off without a
  log line; one that fails later, or a file of 64 bytes or more, is out of form.
- A `play` that cuts a turn of the playlist counts it only when the turn had its first
  refresh; two `play`s before a refresh count one. A cut never begins a break: once 5
  turns are counted by cuts, the break comes at the end of the next turn. A `play` of a
  cycle cuts the turn and counts it as a `play` of an animation does.
- "The message as it was set then": the message follows a clock when it was on as the
  break began, or when `clocks message on` comes during the clock's turn; `clocks message
  off` during the break takes it from no break that has begun.
- The design calls `breaks_tree` in `player_drive_changed` too. Every path of the code that
  changes the tree calls `tree_clear`, `tree_build` or `tree_find_current` before it, and
  the moves of the walk call `player_drive_moved` and `player_drive_shifted`; those five
  find the clocks' folders again, and a fault of one file draws no new order.
- An upload that replaces the file of the paused turn's animation during a break makes it
  play from its first frame after the break, as a turn of a replaced file begins again.
  When the paused animation is removed, ignored, quarantined or leaves with the card, the
  playlist goes on after the break with the animation after it.
- The test host's `shuffle KEY COUNT` takes a count of 1 to 65,536 and prints the
  permutation on one line.

**Resolution.** `core/src/breaks.cpp`, `core/src/player.cpp`, `core/src/order.cpp`,
`core/src/mapping_control.cpp`, `tests/core/host/host.cpp`; `docs/show.md`,
`docs/core.md`, `docs/commands.md`.

## Seed 54: the clocks on the card, and the proof on the emulator

**Question.** Are the clocks of `collection/card/clocks/` those of the share, and do the
breaks play on the collection's card as the seed says?

**Answer.** The 339 files of `collection/card/clocks/`, the 112 clocks and the message with
their GIFs and readmes, have the bytes of the share's `card/clocks/`. The demo show with
`--drive-folder collection/card`, the clocks and the message switched on by their lines:
the folder `clocks` was passed over by the playlist; when 5 minutes were counted, the
frames clock `clock-013` cut the turn of `archive/vjmorph-nurave-kali_fit.odrg` after 10 s
of it, the message played once for 6 s, and that turn went on for the 17.5 s it had left;
five turns later the picture dial `clock-064` played between two turns. The card's folder
has more than 256 files without a catalog, so its last files are passed over; the clocks
come early in the walk and all 113 play.

**Resolution.** `docs/microsd.md`, `agent/vocabulary.md` (`clock break`).

## The tests that failed on Windows only

**Question.** A test needs a file or a folder whose name Windows forbids or changes; the
sweep of a run cannot see a process's environment on Windows. What do they do there?

**Answer.** A test keeps its case on every system that allows the name. On Windows it uses
a name Windows allows when the behaviour does not hang on the forbidden character, as the
readiness test's drive file, and leaves the one case out with its reason when it does: the
folder `bad.` on disk, and the quoted name in the thumbnail catalog. On Windows the runner
puts its workers in a job object and ends what is still in it after them; `--sweep`
there finds only the emulators of temporary and preview folders, as without a runner.

**Resolution.** `tests/run.py`, `tests/runner/test_runner.py`,
`tests/core/test_readiness.py`, `tests/emulator/test_drive.py`,
`tests/emulator/test_events.py`, `tests/converter/test_catalog_types.py`,
`converter/tests/thumbnailtool.test.js`; `agent/working-rules.md`.

## The generators that docs/emulator.md shows

**Question.** The converter's test of the documents counted three generator lines in
`docs/emulator.md`, those of the demo show and of the dense show; the demo show of the clock
breaks shows the demo's generators again, on macOS and Linux and in PowerShell. Is the count
or the page wrong?

**Answer.** The count. What the test means is that the page generates with the Python
programs, and each of them is still the one the commands start: the generators the page
names are exactly `hello_world`, `dvd_bounce` and `dense`, however many lines run them.

**Resolution.** `converter/tests/docs.test.js`.

## The internal catalog's rebuild through the emulator, answered busy

**Question.** On Windows the emulator's test of `catalog rebuild internal` was answered
`busy` most times, alone too. Is the core's refusal wrong there?

**Answer.** No. The test starts the emulator with a card and sends the rebuild at once;
the core reads the drive's catalog for the first frames after the start, and
`docs/commands.md` has `catalog rebuild` answer `busy` while it does. Where the suite passed,
the tool's line came after that reading; on Windows it often came during it, with the drive's state
`loading`. The test now waits until `status` names nothing it checks, the drive's catalog
included, as an operator's tool would, and the core is as it was.

**Resolution.** `tests/emulator/test_catalog.py`.

## The tests that fail only when every suite runs at once on Windows

**Question.** With `tests/run.py` on Windows, the emulator's LAN test and the lost-reply
tests of the command tool failed now and then with WinError 10055 at a connect, and
scenarios of the app and the mapping, a different few in each run, with the app still on
`Checking` when their wait ran out; each passes alone. What gives way?

**Answer.** Two things, both of Windows. The emulator's tests sent every command on a
connection of its own, and each closed connection holds a port of the computer's 16,384 for
two minutes; a run of the emulator's, the app's and the mapping's suites held 8,790 at its
peak, and the full run and other work on the computer more, until a connect had no port
left. The tests' helper now keeps its connection to the emulator from one command to the
next, as a browser does, and the same run held 3,422; the command tool still opens one for
each exchange, as `docs/emulator.md` says. And a server of Python's library lets five
connections wait to be taken; when the queue is full, macOS and Linux leave the next one
to try again, and Windows refuses it. A loaded computer is slow to take them, Chrome asks
for the app's modules all at once, and one refused module leaves the app as its page
stands, on `Checking`, even after 30 seconds. The emulator's server, the app tool's server
and the app tests' stand-in target now let 64 wait. The waits of the scenarios were not
lengthened: with the app stopped no length would do.

**Resolution.** `tests/emulator/support.py`, `emulator/httpd.py`,
`app/apptool/webserver.py`, `tests/app/support.py`, `tests/emulator/test_http.py`,
`tests/app/test_tool.py`.
## Seed 55: the lock of a setup, held by the system

**Question.** Seed 53's design takes `setup.lock` by an exclusive create, and a lock older
than an hour whose owner is gone is taken over. A setup that dies leaves the file; how long
does the next one wait, and how is "gone" known on Windows, where `os.kill(pid, 0)` ends
the process?

**Answer.** The lock is one the system holds for the open file, `flock` on macOS and Linux
and `msvcrt.locking` on Windows: it is free as soon as its process is gone, however it
ended, so nothing is taken over and no process is looked up. A setup that finds it held
says that it waits, and waits at most an hour.

**Resolution.** `app/apptool/setuplock.py`, `firmware/fwtool/setuplock.py`, their tests in
`tests/app/test_shared_tools.py` and `tests/firmware/test_shared_tools.py`.

## Seed 55: the shared WLED copy is the source as fetched

**Question.** The design keeps a prepared WLED copy in the shared folder, "patched and once
built". Who builds it, and when, while each checkout patches its copy with its own
patches and builds with its own path in the override file?

**Answer.** The shared copy is WLED's source as fetched, never patched or built there. A
checkout's copy is cloned from it, copy-on-write where the system can, with whatever
build folder it holds, and is patched and built in the checkout. PlatformIO's build cache
is shared, so a checkout's first build reuses what any checkout compiled: a second
checkout's first firmware build took 52 s, beside an APK build.

**Resolution.** `firmware/fwtool/paths.py`, `firmware/fwtool/wled.py`,
`firmware/fwtool/toolchain.py`; `docs/firmware.md`.

## Seed 55: no port to check before the walkthrough's emulator

**Question.** Seed 53's requirement 5.3 says the walkthrough fails at once when port 8600
is held before it starts the page's emulator. Which emulator is that?

**Answer.** None: the walkthrough leaves out "Run it in the emulator", which needs a
person at the page, and its record runs open no port. It ends the process group of every
command it runs once the command ends, so nothing it starts is left; the suites in the
copy run through the copy's runner, which ends what is left of its run.

**Resolution.** `tests/walkthrough/support.py`, `tests/walkthrough/test_fresh_copy.py`.

## Seed 55: two tests of master that failed in every run

**Question.** Requirement 8.5 asks every suite to pass, alone and through the runner. On
master the converter's `docs.test.js` counted exactly three generator commands in
`docs/emulator.md`, which has seven since the demo of the clock breaks, and
`tests.emulator.test_preview` failed when a preview of another worker ran beside it.

**Answer.** The documents test asks for three or more, which is what it says it checks:
that the page generates with the Python programs. The preview test checks that the work
folders of its own previews are gone, by their process ids, and no longer that no other
folder appeared meanwhile.

**Resolution.** `converter/tests/docs.test.js`, `tests/emulator/test_preview.py`.

## Seed 56: capacity work that does not hold playback's filesystem lock

**Question.** Moving `SD.totalBytes()` and `SD.usedBytes()` to another task still
lets `f_getfree` hold resources needed by reads. How is capacity discovered without
making unknown capacity mean an absent or read-only card?

**Answer.** Keep mounted generation and write capability independent. The query
tries the guard without waiting and copies only a complete cache. The card worker
reads at most one raw 512-byte sector per slice, validates a FAT16/FAT32 volume
and counts its free allocation units with 64-bit totals. It releases the guard
and yields between slices. Unsupported/ambiguous partition layouts remain unknown
rather than counting a different volume; no catalog or animation scan is needed.
This is bounded discovery, not proof of physical transfer latency or board FPS.

**Resolution.** `firmware/usermod/odrig_sd_capacity.h`,
`firmware/usermod/odrig_drive.cpp`, `docs/microsd.md` and the seed 56 spec.

## Seed 56: failed writes and stale storage observations

**Question.** Can a raw FAT rescan immediately after a failed write publish exact
free bytes, and can the app retain its last absent report after losing the target?

**Answer.** Neither is trusted as current information. A failed mutation may leave
dirty FatFs state newer than media, so capacity remains unavailable until remount;
ordinary safe writes and catalog access are not disabled merely for unknown space.
The shared client discards its cached space report on a connection failure, as on
a refused query or target change. A missing current report says information is
unavailable; a fresh present card can separately report unknown byte counts.
The owner deferred this run's firmware compilation to future seed 60; final APK
build/delivery follows all four software seeds. Physical cold-card/phone acceptance
remains open and cannot be inferred from the host and browser suites.

**Resolution.** `firmware/usermod/odrig_drive.cpp`, `app/www/client.js`,
`app/www/capacity.js`, `docs/android-app.md` and seed 56's verification note.

## Seed 57: host acknowledgement and bounded miniature storage

**Question.** Which host boundary avoids claiming successful physical setup from a
command reply, and how does projection fit within the core's existing memory budget?

**Answer.** A host explicitly opts into miniature support and acknowledges a matching
request revision after clearing/checking output setup. Submission is pending; failure
reports unknown and requires dark output until retry. Other hosts/canvases are
unsupported. One192-byte optional startup block holds state and a180-byte physical
image; averaging uses three local sums per10x10cell. Preview consumers reorder that
same image, without a second projection or buffer in the core. The measured host
allocation with a drive is131041bytes, below131072. Normal leg data is unchanged.
The physical index x*6+y follows the manufacturer's schematic/PCB for the approved
landscape orientation; it remains subject to a later powered corner/axis check.

**Resolution.** `core/src/mini.cpp`, `core/include/odrig_core.h`, `docs/core.md`
and the seed57 design. This records software design, not electrical acceptance.

## Seed 57: status reply space

**Question.** How does the additional mode state fit within the fixed1024-byte
reply when the host description contains control characters?

**Answer.** Keep the95-byte input bound and cap the encoded description at256bytes,
truncating on a character boundary. Normal printable host descriptions are unchanged.
The longest-status conservative check first measured1099bytes; the regression for
95control bytes first retained all95 instead of the bounded42. The escaped limit
leaves room for mode state without changing the public line/reply limits.

**Resolution.** `core/src/commands.cpp`, `docs/commands.md` and the miniature tests.

## Seed 57: unknown state during a failed-setup retry

**Question.** Does submitting a retry establish a known output mode?

**Answer.** No. Keep the previous failure and `on:null` while retry is pending;
only successful host acknowledgement establishes a known mode. The regression first
observed `on:false` before acknowledgement. Repeated setup failure remains unknown.

**Resolution.** `core/src/commands.cpp` and the miniature control tests/design.

## Seed 57: output setup and paired preview delivery

**Question.** How are physical setup and preview delivery kept consistent without
holding command replies or implementing the planned current-budget controls?

**Answer.** The main loop clears and drains the old output, checks readiness again
before setup, checks every new output, then clears and drains it before acknowledging.
Failure keeps decoded frames from the outputs and allows an explicit retry. The
refresh producer publishes under the common lock, after probe measurements; hardware
operations and transfer waits remain outside it. Host regressions first found setup
attempted during a resumed transfer and a stale20-output summary after selecting one.
The existing WLED limiter stays enabled and counts the selected60LED bus. Seed45
remains planned; its separate core/app budget controls are not supplied by this work.

The emulator acknowledges virtual setup and publishes the core's physical RGB beside
the corresponding normal frame in one coalesced slot. The browser only reorders those
60pixels. Slow clients cannot accumulate a separate preview queue; normal canvas and
ODRR geometry are unchanged. WLED's pinned transfer/limiter interface was checked at
[29b389df1c1aaec6ff53aea742d17063b985906c](https://github.com/wled/WLED/blob/29b389df1c1aaec6ff53aea742d17063b985906c/wled00/bus_manager.cpp).
Host tests are not a firmware build or physical transfer/power proof.

**Resolution.** `firmware/usermod/odrig_mini_output.h`, `odrig_usermod.cpp`,
`odrig_leds.cpp`, `emulator/binding.py`, `emulator/hub.py` and `docs/emulator.md`.

## Seed 57: the app's confirmed miniature state

**Question.** What does the checkbox show while a request is accepted but output
setup has not completed, or a reply is lost?

**Answer.** It keeps the last status value while the serialized request and its
first subsequent status are outstanding, then follows the host's pending state.
Only a fresh status establishes the mode; a successful command reply does not
check the box. A connection failure invalidates the snapshot until a newer status
arrives, including when another kind of reply reestablishes contact first.
Missing or unsupported capability is explicitly unavailable, never treated as off.
An output failure shows unknown, permits an explicit retry and offers Restore
normal outputs. Target changes clear all local request state. Reopening the app
reads status and never enables or retries the mode automatically. An indication
outside Settings names active miniature output and its brightness cap.

The first browser pass exposed a null-member crash with legacy firmware, then
passed after the missing capability was handled throughout the drawing path.
The app message-table check first counted20 command error codes against19;
the approved `unsupported` refusal now has its own explanation and coverage.
The tests also distinguish command acceptance from physical acknowledgement and
exercise the same controls against the running emulator.

**Resolution.** `app/www/commands.js`, `app/www/client.js`,
`app/www/screens/mini.js` and `tests/app/test_mini.py`.

## Seed 57: operator orientation and power boundaries

**Question.** What does source evidence establish before a powered matrix check?

**Answer.** The manufacturer's schematic and PCB establish a derived chain:
DIN to LED116,60 parts through LED39, rotated into landscape front view with IN
at left. Indices rise up each column, `x*6+y`; the rear view reverses left/right.
The manufacturer's linked LED datasheet gives2.8V input-high minimum at5V, which
supports the already approved direct3.3V data plan for the documented part.
Neither fact proves that the received assembly matches or that the actual board's
5V path, protection, concurrent USB paths or current budget are ready. Those
checks include boot and failed/restored normal output, where the miniature-only
brightness cap cannot protect the assembly. Keep the full wall disconnected and
power off before changing wires. No new circuit or supply is introduced.

**Resolution.** The root README pin table, operator sequence and source links;
`docs/mapping.md`, `docs/firmware.md` and the retained human acceptance task.

The integrated documentation audit first found the vocabulary's approved-command
list missing `debug`; both its entry and coverage now include the miniature form.
The mapping browser's unsupported wait also first read a null mapping error:
its whole-page text search matched the new miniature explanation before mapping
had answered. Waiting on the mapping error itself preserves the independent
mapping assertion rather than depending on another panel's timing.

The catalog-serving test met WinError10055 twice while opening a connection for
each of538 files. Its verification loop now reuses existing HTTP/1.1 support,
with every file, byte, content type, cache header and rejected path still checked.
The serving class then passed all7 cases. This changes a test fixture only;
production server behavior and Windows settings are unchanged.

## Seed 58: preference storage and compatibility

**Question.** How are durable brightness overrides bounded without changing the
existing default-brightness contract or evicting missing files?

**Answer.** Use internal `brightness.txt`/`brightness.part`, path namespaces like
saved repeats, at most512 retained records and32 external records. New entries
beyond either limit are `no-space`; existing entries can be updated/removed and
missing media never makes room automatically. Zero is a present value. Cache
listed internal/external values with fixed startup memory, compacting private
metadata without narrowing existing position/count domains or raising memory
bounds. Publish only verified durable settings; report damaged settings and use
defaults safely, retaining usable state on failed updates.

`status.brightness` remains the runtime default. Add `dimming` selected/saved/error
readback, before blackout/mini cap; the renderer and miniature share selection.
The app captures target/animation identity at input start and reads back before
claiming a saved state. The existing WLED limiter remains; seed45's planned new
budgets are not implemented here. Owner-approved save/default command forms need
no additional command decision. Firmware compilation stays deferred to seed60.

**Resolution.** Seed58 requirements/design/tasks; all product questions were
already answered in its seed. Physical acceptance remains a separate task.

## Seed 58: refreshing preferences after file identity changes

**Question.** Does an item's cached preference survive a change to a different
file name merely because its numeric id stays the same?

**Answer.** No. Preferences belong to paths. The upload/restore regression first
observed `[19,19]` instead of `[19,null]`: restoring the original path correctly
used19, but assigning a different path kept that cached value. Refresh preferences
after durable renamed-file publication, and alongside repeat-cache refreshes after
indexed-file publication, movement and removal. The retained settings file itself
is unchanged by an animation rename/removal; restoring its old path still uses it.

**Resolution.** `core/src/storage.cpp`, `core/src/catalog.cpp` and the brightness
identity regression. Fixed startup allocations remain below the existing bounds:
Core3944 bytes and the100-item drive case131069 bytes, with full position/count
domains preserved. Independent128-byte settings reads keep compiler stack frames
within the existing512-byte limit.

## 2026-10-30 — bounded saved brightness and app confirmation

Saved brightness uses internal namespace/path records retained even for absent files,
with 512 total and 32 external records and no eviction. A 128-byte independent reader
preserves decoder ownership and the 512-byte stack-frame bound. Existing item padding,
full-domain 6-byte repeat records,5-byte brightness records and private-field alignment
keep the 100-item drive allocation 131069 bytes and Core 3944 without raising limits.
One selector supplies player and miniature output; `status.brightness` stays the
runtime default and additive `dimming` aligns with the status file identity.

The app captures target epoch, animation ID/file and mode. Dirty or already-entered
numeric edits require later status before capture; every override release commits
its final value, with unchanged writes elided in the core. Only valid status restores
status freshness after communication failure. Other command replies cannot make old
override data editable. Firmware tools preserve/replace/read back brightness.txt.
These technical resolutions do not close electrical, board or phone acceptance;
firmware compilation remains deferred to the separately planned seed 60.

Integrated verification also showed that a held brightness draft must be discarded
when status freshness is lost, even if the same file returns after recovery. The
controller's edit binding includes freshness, so releasing an interrupted drag
cannot resend the discarded value. The failing70-versus20 regression then passed.
