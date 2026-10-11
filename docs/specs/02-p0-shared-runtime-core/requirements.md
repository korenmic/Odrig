# Requirements: Shared runtime core (seed 02)

Source seed: `project-seeds/02-p0-shared-runtime-core/seed.md`. It depends on seed 01 for the
test vectors, the reference decoder and the names of the reasons.

`docs/format.md`, `docs/mapping.md`, `docs/show.md` and `docs/commands.md` define the
behaviour. These requirements say what the core does with them. Where those documents leave
a point open, the answer used here is recorded in `docs/drifts.md`.

Terms:

- **the core**: the C++ library of this seed.
- **host**: the program that runs the core: the emulator of seed 03, the firmware of seed 04,
  or the test host of this seed.
- **installed file set**: `mapping.json`, `show.json` and the `.odrg` files, as in
  `docs/show.md`.
- **timestamp**: a time in whole milliseconds that the host passes with a call.
- **power-on moment**: the timestamp of the first call the host makes after startup.
- **refresh**: one complete set of LED data, for every leg.
- **grid**: the times at which refreshes are due: the power-on moment and every 20 ms after
  it.
- **reason**: one of the fixed names of `docs/reasons.md`.
- **W**, **H**, **N**, **C**: as in `docs/format.md`.

## Requirement 1: One portable code base

**User Story:** As the owner of the installation, I want the code that decides behaviour to
exist once and to compile unchanged for the Mac and for the board, so that the emulator and
the board cannot behave differently.

### Acceptance Criteria

1. The core SHALL be written in C++11, using only constructs that are also valid in every
   later C++ standard, and the same source files SHALL be compiled for macOS and for the
   ESP32-S3 inside the WLED 16.0.1 build.
2. The core SHALL use no exceptions, no run-time type information and no threads, and SHALL
   compile with exceptions and run-time type information switched off.
3. The compiled core SHALL refer to nothing outside itself except the C library's routines
   for copying, filling and comparing memory and the compiler's own support routines.
4. The core SHALL keep all of its state in the object the host holds: it SHALL have no
   variable that outlives a call other than that object and constant tables.
5. The core SHALL use whole-number arithmetic only.
6. The core SHALL NOT call itself recursively, and no function of the core SHALL hold more
   than 256 bytes of local arrays.
7. WHEN `make -C core` is run on macOS with only Apple's command-line developer tools
   installed THEN it SHALL build the core as a library, with every compiler warning treated
   as an error.

## Requirement 2: A small host interface

**User Story:** As the author of a host, I want a small interface with everything the core
needs from me and everything it gives me, so that my host stays thin and the emulator and
the firmware use the core in the same way.

### Acceptance Criteria

1. The host interface SHALL be declared in one header that compiles both as C and as C++
   and that needs only `stdint.h` and `stddef.h`.
2. The core SHALL obtain from the host, through functions the host supplies: memory, during
   startup only; the content of a file of the installed file set, given its name; and a
   place to send diagnostic text.
3. The core SHALL have one file open at a time, SHALL read each file from its first byte to
   its last without going back, and SHALL close a file before it opens another.
4. The core SHALL receive the time only as a timestamp passed with a call. It SHALL NOT read
   a clock.
5. The core SHALL give the host, on request, the list of legs and the LED data of the last
   refresh, as Requirement 6 defines.
6. The core SHALL give the host, on request, the reason text of Requirement 3, or nothing
   when the show is valid.
7. The core SHALL accept command lines and return reply lines as Requirement 10 defines.
8. The core SHALL NOT write, create or delete a file.

## Requirement 3: Startup reads and checks the installed file set

**User Story:** As an operator, I want a show that is wrong in any way to be refused as a
whole at power-on, with the reason available, so that the LEDs never show a half-working
show.

### Acceptance Criteria

1. WHEN the host starts the core THEN the core SHALL read `mapping.json`, then `show.json`,
   and SHALL then decode every different `.odrg` file the show names from its first frame
   record to its last.
2. The core SHALL accept a mapping file under exactly the rules of Requirement 10 of the
   seed 01 requirements, the format of a show file under exactly the rules of Requirement 14
   criterion 4 of the seed 01 requirements, and an `.odrg` file under exactly the rules of
   Requirement 6 of the seed 01 requirements.
3. IF the show is invalid THEN the core SHALL keep every LED dark and SHALL hold the reason
   as a text of one of these forms. The checks of the first ten rows are made in the order
   of the table and the first one that fails decides; the last two rows are reported at the
   point where they happen:

   | Text | Condition |
   |---|---|
   | `mapping-missing` | `mapping.json` does not exist. |
   | `mapping-malformed` | `mapping.json` breaks a rule. |
   | `show-missing` | `show.json` does not exist. |
   | `show-malformed` | `show.json` breaks its format. |
   | `duplicate-id <id>` | Two items have that id. |
   | `undefined-id <id>` | A cycle, or `start`, names that id and no item has it. |
   | `nested-cycle <id>` | The cycle item with that id names an item that is a cycle. |
   | `file-missing <name>` | The named `.odrg` file does not exist. |
   | `file-malformed <name> <reason>` | The named file is rejected with that reason of Requirement 6 of the seed 01 requirements. |
   | `size-mismatch <name>` | The named file's W or H differs from the mapping's. |
   | `read-error <name>` | The host reports a failure while the named file is read. |
   | `out-of-memory` | The host cannot supply the memory the core asks for. |

4. The core SHALL check the `.odrg` files in the order in which `show.json` first names
   them, and for each file SHALL check its header, then its size against the mapping, then
   its body.
5. WHEN the show is invalid THEN the core SHALL still answer every command.
6. WHEN the show is valid THEN the core SHALL hold no reason.

## Requirement 4: Power-on state

**User Story:** As an operator, I want the installation to come up in the state the show
file describes, so that it runs without anyone sending a command.

### Acceptance Criteria

1. WHEN the show is valid THEN after startup the LEDs SHALL be switched on, brightness SHALL
   be the value in `show.json`, and the `start` item SHALL be playing if there is one.
2. WHEN the show is valid and has no `start` THEN nothing SHALL be playing and every LED
   SHALL be dark until a `play` command arrives.
3. WHEN the show is invalid THEN after startup the LEDs SHALL be switched on, nothing SHALL
   be playing, and brightness SHALL be the value in `show.json` if the checks up to and
   including `nested-cycle` passed, and 0 otherwise.
4. The core SHALL keep nothing from one startup to the next.

## Requirement 5: Time and refreshes

**User Story:** As the author of a host, I want to hand the core the time and get LED data
back every 20 ms, so that my host needs no timing logic of its own.

### Acceptance Criteria

1. The grid SHALL start at the power-on moment and SHALL have one time every 20 ms.
2. WHEN the host asks for a refresh with a timestamp, and a grid time at or before that
   timestamp has neither been used nor skipped, THEN the core SHALL produce one refresh for
   that timestamp, SHALL count the latest grid time at or before the timestamp as used, and
   SHALL count every earlier unused grid time as skipped.
3. WHEN the host asks for a refresh and no such grid time exists THEN the core SHALL produce
   nothing and SHALL say so.
4. WHEN the host asks for a refresh at every grid time THEN the core SHALL produce one
   refresh per request.
5. IF a timestamp is earlier than one the core has already received THEN the core SHALL
   treat it as equal to the latest timestamp received.
6. WHEN the mapping is invalid THEN the core SHALL have no legs and SHALL produce no
   refresh.
7. WHEN the mapping is valid THEN the core SHALL produce refreshes whether or not the show
   is valid, an item is playing or the LEDs are switched on.

## Requirement 6: LED data reaches the LEDs as the mapping defines

**User Story:** As the author of a host, I want the colour of every physical LED of every
leg, in the order the LEDs are wired, so that I only have to send it to the right pin.

### Acceptance Criteria

1. WHEN the mapping is valid THEN after startup the core SHALL give, for each leg in the
   order of the mapping file, its leg number, its pin and its number of LEDs, which is W
   times the leg's number of rows.
2. After each refresh the core SHALL give, for each leg, three bytes for each of its LEDs,
   red, green and blue, in chain order starting with the LED wired to the board.
3. LED number n of a leg, counted from 1, SHALL show canvas pixel (x, y), where
   `r = (n - 1) div W`, `i = (n - 1) mod W`, y is entry r of the leg's `rows`, the row
   starts on the `first_led` side when r is even and on the other side when r is odd, and x
   is `W - i` when the row starts on the right and `1 + i` when it starts on the left.
4. WHEN the show is invalid, nothing is playing, or the LEDs are switched off THEN every
   byte of the LED data SHALL be 0.

## Requirement 7: The picture follows the format

**User Story:** As someone who makes animations, I want the board to show at every moment
exactly the frame the format defines, so that what I see in the source is what plays.

### Acceptance Criteria

1. WHEN an animation is on the LEDs THEN each refresh SHALL show the frame whose time span
   contains the animation's elapsed time at the refresh's timestamp, where frame 1 starts at
   0 and every other frame starts when the one before it ends.
2. WHEN the elapsed time reaches the sum of all frame durations THEN the animation SHALL
   start again from its first frame, and the pixel buffer SHALL be all zero before that
   first frame is decoded.
3. The elapsed time of an item SHALL be counted from the item's time zero: the grid time
   used by the first refresh produced after the item was played, by a command or at
   power-on.
4. WHEN refreshes were skipped THEN the next refresh SHALL show the same picture it would
   have shown had none been skipped.
5. The colour of a canvas pixel SHALL be its palette entry in a palette file and its three
   buffer bytes otherwise.

## Requirement 8: Cycles

**User Story:** As an operator, I want a cycle to rotate through its animations by itself,
so that the installation shows variety without commands.

### Acceptance Criteria

1. WHEN a cycle is playing THEN turn number t, counted from 0 at the cycle's time zero,
   SHALL last the cycle's `seconds` and SHALL show the animation at position `t mod n` of
   the cycle's list of n animations.
2. Each turn SHALL start its animation from the first frame, with the animation's elapsed
   time counted from the start of the turn, also when the same animation was on the LEDs in
   the turn before.
3. WHEN an animation is shorter than a turn THEN it SHALL loop within the turn as
   Requirement 7 defines.
4. The cycle SHALL repeat for as long as it is playing.

## Requirement 9: Brightness, on and off

**User Story:** As an operator, I want to dim the installation and to switch it dark and
back, so that I can adapt it to the surroundings without stopping the show.

### Acceptance Criteria

1. WHEN the LEDs are switched on THEN every colour value v of the picture SHALL be sent as
   `(v * brightness + 127) / 255`, rounded down.
2. WHEN the LEDs are switched off THEN every LED SHALL be dark and playback time SHALL keep
   running.
3. WHEN the LEDs are switched on again THEN the next refresh SHALL show the picture that
   belongs to its timestamp, as if they had never been off.
4. The core SHALL be the only place where brightness is applied to the LED data it gives.

## Requirement 10: Command lines in, reply lines out

**User Story:** As the author of a transport, serial or HTTP, I want to pass a line to the
core and get the reply back, so that every transport gives the same answers.

### Acceptance Criteria

1. The core SHALL offer one entry that takes a timestamp and one command line and returns
   exactly one reply. It SHALL be the only place where a command is interpreted.
2. The entry SHALL ignore one newline at the end of the line and one carriage return before
   it.
3. IF the line is then longer than 64 characters THEN the reply SHALL be the failure
   `line-too-long`.
4. The core SHALL split the line into words at every single space. Two spaces in a row, or
   a space at the start or the end of the line, SHALL give an empty word.
5. A reply SHALL be one JSON object on one line, ended by a newline, of at most 192 bytes.
6. The core SHALL also offer an entry for transports that deliver bytes: it SHALL take a
   timestamp and any number of bytes, SHALL treat every newline as the end of a line, SHALL
   pass each line to the entry of criterion 1, and SHALL hand each line and its reply to the
   host.
7. WHEN more than 64 characters arrive without a newline THEN the byte entry SHALL keep no
   more than the first 65 of them, and at the next newline SHALL reply once with
   `line-too-long`.
8. Every line SHALL get exactly one reply, an empty line included.

## Requirement 11: Commands and replies

**User Story:** As an operator or a program controlling the installation, I want the five
commands of `docs/commands.md` to behave exactly as documented, so that the same tool works
against the emulator and the board.

### Acceptance Criteria

1. WHEN the line is `play <id>`, with `<id>` written as decimal digits and from 1 to 65,535,
   and the show is valid and has an item with that id, THEN the core SHALL play that item
   from its first frame and SHALL reply `{"ok":true}`.
2. WHEN the line is `on` or `off` THEN the core SHALL switch the LEDs on or off and SHALL
   reply `{"ok":true}`.
3. WHEN the line is `brightness <n>`, with `<n>` written as decimal digits and from 0 to
   255, THEN the core SHALL set brightness to n and SHALL reply `{"ok":true}`.
4. WHEN the line is `status` THEN the core SHALL reply with exactly this form, with the
   members in this order and no spaces:
   `{"ok":true,"on":<true|false>,"brightness":<n>,"playing":<id|null>,"animation":<id|null>,"fps":<n>,"error":<"text"|null>}`.
5. In the status reply, `playing` SHALL be the id of the item being played or `null`;
   `animation` SHALL be the id of the animation item chosen by the latest refresh since the
   item was played, or the item's first animation if no refresh has been produced since, or
   `null` when nothing is playing; `error` SHALL be `null` or the text of Requirement 3.
6. IF a line is not a valid command THEN the core SHALL change nothing and SHALL reply
   `{"ok":false,"error":"<code>"}` with the first code of this table that applies:

   | Code | Condition |
   |---|---|
   | `line-too-long` | The line is longer than 64 characters. |
   | `unknown-command` | The first word is not exactly `play`, `on`, `off`, `brightness` or `status`. |
   | `bad-argument` | The number of words after the first is not what the command takes; or an argument is not made of decimal digits only; or its value is outside the command's range. |
   | `show-invalid` | The command is `play` and the show is invalid. |
   | `unknown-id` | The command is `play` and no item has that id. |

7. `on`, `off`, `brightness` and `status` SHALL work in the same way when the show is
   invalid.
8. A command SHALL change the state that `status` reports at once, and the LED data from
   the next refresh on.

## Requirement 12: The refresh rate is measured

**User Story:** As an operator, I want `status` to say how many refreshes really happened,
so that I can see whether the board keeps up.

### Acceptance Criteria

1. The core SHALL count the refreshes it produces in each whole second, where the first
   second starts at the power-on moment.
2. WHEN `status` is answered THEN `fps` SHALL be the number of refreshes produced in the
   second that ended most recently before the command's timestamp.
3. WHEN no whole second has ended, or no refresh was produced in the second that ended most
   recently, THEN `fps` SHALL be 0.

## Requirement 13: Fixed memory, files read as streams

**User Story:** As the author of the firmware, I want the core to take a known amount of
memory once and never more, so that it cannot fail from memory after hours of running.

### Acceptance Criteria

1. The core SHALL ask the host for memory only during startup, and SHALL size what it asks
   for from the mapping and the show.
2. WHEN the mapping is the ten-leg mapping and the show has 100 items THEN the memory the
   core asks for SHALL total less than 131,072 bytes.
3. The core SHALL read a file in pieces of at most 512 bytes and SHALL never hold a whole
   file or a whole frame record in memory. The memory it uses SHALL NOT depend on the size
   of an `.odrg` file or on its number of frames.
4. IF the host cannot supply the first block of memory THEN startup SHALL fail and the host
   SHALL be told so. IF the host cannot supply a later block THEN the show SHALL be invalid
   with `out-of-memory`.

## Requirement 14: Same inputs, same output

**User Story:** As a tester, I want the core's output to depend on nothing but its inputs,
so that a recorded session proves what the board will do.

### Acceptance Criteria

1. WHEN the core is run twice with the same installed file set and the same sequence of
   calls, with the same timestamps, command lines and bytes, THEN every reply and every
   byte of LED data SHALL be the same in both runs.
2. The core's output SHALL NOT depend on the address of any memory, on the content of
   memory it did not write, or on how long a call takes.

## Requirement 15: Its own DEFLATE decoder and JSON reader

**User Story:** As the owner of the installation, I want the core to carry its own
decompressor and JSON reader, so that every build runs the same code and reads a file in
the same way.

### Acceptance Criteria

1. The core SHALL decompress DEFLATE and read JSON with code that is part of its own source
   files, and SHALL NOT use a decompressor or a JSON reader of a platform.
2. IF source code from outside this repository is brought into the core THEN it SHALL have a
   permissive licence and SHALL be stored together with its licence text.
3. The core's DEFLATE decoder SHALL decode every valid raw DEFLATE stream with a window of
   up to 32,768 bytes, made of stored, fixed-code and dynamic-code blocks, and SHALL reject
   an invalid stream as `bad-deflate` and a stream that ends early as `truncated`.
4. The core's JSON reader SHALL accept and refuse the same mapping files and show files as
   the tool of seed 01.

## Requirement 16: A failure while playing

**User Story:** As an operator, I want a file that goes bad while the installation runs to
turn the LEDs dark and be reported, so that a damaged file never shows garbage.

### Acceptance Criteria

1. IF, while an item is playing, a file cannot be opened, the host reports a failure while
   it is read, or the file fails a check of the format, THEN from that refresh on the show
   SHALL be invalid: every LED dark, nothing playing, and the reason held as
   `file-missing <name>`, `read-error <name>`, `size-mismatch <name>` or
   `file-malformed <name> <reason>`.
2. WHEN the show has become invalid in this way THEN `play` SHALL be answered with
   `show-invalid` until the next startup.

## Requirement 17: One test command, checked against the reference

**User Story:** As a contributor, I want one command that proves the core against the
reference of seed 01, so that a change that alters behaviour cannot pass unnoticed.

### Acceptance Criteria

1. `make -C core test`, run on macOS, SHALL build the core and its test host and SHALL run
   the whole suite of this seed. The suite SHALL be selected by discovery in `tests/core/`:
   a test file added there SHALL be run without a change to any command, script or list.
2. The suite SHALL prove that every valid test vector of seed 01 decodes to its expected
   frames, record by record, and that every invalid one is rejected with the reason in its
   name. It SHALL find the vectors by listing their folders.
3. The suite SHALL prove, for Hello world and DVD bounce on the two-leg mapping and for the
   dense clip on the ten-leg mapping, that the LED data of every leg at every refresh of one
   full loop and the start of the next equals the reference: the decoder of seed 01 followed
   by the mapping rule of Requirement 6, computed in the test without the core.
4. The suite SHALL run a scripted session of timestamps and command lines and SHALL compare
   every reply and every refresh with the expected ones. The session SHALL cover every
   command, every error code, a cycle changing from one animation to the next, a turn that
   starts again from the first frame, switching off and on, and changes of brightness.
5. The suite SHALL have, for each text of Requirement 3, a test in which the LEDs stay dark
   and `status` reports that text.
6. The test host SHALL stop with a failure when memory is allocated after startup, by the
   host interface or in any other way, and the whole suite SHALL pass on that test host.
7. The suite SHALL prove criterion 3 of Requirement 1 by listing the names the compiled core
   refers to and comparing them with an allowed list.
8. The suite SHALL need no hardware and no network connection.

## Requirement 18: A benchmark on the Mac

**User Story:** As the owner of the installation, I want to know how long a frame takes to
decode, so that there is a first figure to compare the board with.

### Acceptance Criteria

1. WHEN `make -C core bench` is run THEN it SHALL print, for the dense 60 x 30 clip of 10
   seconds, compressed and uncompressed, the size of the file, the number of frames, and the
   mean and the longest time to decode one frame.
2. The benchmark SHALL NOT be part of the test command and SHALL NOT pass or fail on a time.

## Requirement 19: The core is documented

**User Story:** As the author of a host, I want the build command and the host interface
written down, so that I can host the core without reading its source.

### Acceptance Criteria

1. `docs/core.md` SHALL give the build command, the test command and the benchmark command,
   and what each needs installed.
2. `docs/core.md` SHALL describe the host interface: every function the host supplies, every
   function the core offers, the order of calls, the rules of time and refreshes, the form
   of the LED data, and how much memory the core asks for.
3. `docs/reasons.md` SHALL list the texts of Requirement 3.
4. `README.md` SHALL point to `docs/core.md`.
