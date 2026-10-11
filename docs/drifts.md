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

## Seed 01: Library versions for media import

**Question.** The exact versions of numpy, Pillow and PyAV, and whether PyAV installs with
pip alone on this Mac's Python, could not be confirmed while writing the spec.

**Answer.** Seed 01 task 13 pins the versions it actually installs and tests. If PyAV has no
ready-made package for the Python in use, the implementer chooses another reader that installs
with pip alone and records that choice here.

**Resolution.** Seed 01 `tasks.md`, task 13.

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
