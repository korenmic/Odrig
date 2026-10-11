# Requirements: Emulator (seed 03)

Source seed: `project-seeds/03-p0-emulator/seed.md`. It depends on seed 01 for the package
`odrig` (`pack`, the generators, the readers and the reference decoder) and on seed 02 for
the core in `core/`, its host interface `core/include/odrig_core.h`, `core/Makefile` and the
reference player in `tests/core/support.py`. Neither seed is implemented when this is
written: these requirements rely on what their `design.md` files state.

`docs/format.md`, `docs/mapping.md`, `docs/show.md` and `docs/commands.md` define the
behaviour. These requirements say what the emulator, its page and the command tool do with
them. Where those documents and the seed leave a point open, the answer used here is
recorded in `docs/drifts.md` under "Seed 03".

Terms:

- **the emulator**: the program started as `python -m emulator`.
- **the core**: the C++ library of seed 02.
- **show folder**: a folder holding an installed file set, as in `docs/show.md`.
- **the page**: the web page the emulator serves.
- **the port**: the emulator's virtual serial port.
- **the command tool**: the program started as `python -m odrigctl`.
- **refresh**, **grid**, **timestamp**: as in the seed 02 requirements.
- **tick**: one grid time of the record mode's virtual clock.
- **leg colour**: the one colour the page gives a leg.
- **reference**: the decoder of seed 01 followed by the mapping rule of `docs/mapping.md`,
  as the reference player of seed 02's suite states them in Python.

## Requirement 1: It starts from one argument

**User Story:** As someone who has packed a show, I want to start the emulator by naming the
folder and nothing else, so that trying a show takes one command.

### Acceptance Criteria

1. WHEN the emulator is started from the repository root as `python -m emulator SHOW_DIR`
   THEN it SHALL start the core on that folder, SHALL open the page and the port, and SHALL
   print exactly these two lines to standard output: `page: http://127.0.0.1:<port>/` and
   `serial: <path of the port>`.
2. The emulator SHALL run until it receives an interrupt or a termination signal, and SHALL
   then remove the port's link and exit with status 0.
3. The emulator SHALL accept `--port N` for the page's port number, where 0 means any free
   port, and `--serial-link PATH` for the path of the port. Without them it SHALL use port
   8600 and the path `build/emulator/serial` under the repository root.
4. The emulator SHALL take the canvas size only from `mapping.json` in the show folder. It
   SHALL have no option and no setting that names a size.
5. WHEN `SHOW_DIR` is a folder that does not hold a valid show THEN the emulator SHALL still
   start, as Requirement 10 defines.

## Requirement 2: It hosts the shared core and decides nothing itself

**User Story:** As the owner of the installation, I want the emulator to run the same code
the board runs, so that what I see on the Mac is what the board will do.

### Acceptance Criteria

1. The emulator SHALL run the core compiled natively for the Mac from the files
   `core/src/*.cpp`, used as they are: no copy, no changed file and no second build of the
   core for a browser.
2. The emulator SHALL leave every decision about decoding, the mapping, the show, time and
   commands to the core. It SHALL contain no ODRG decoder, no reader of `show.json`, and no
   interpreter of command lines.
3. Apart from the core, the emulator SHALL use only the Python standard library, and SHALL
   NOT use or need any third-party emulator or simulator.
4. The emulator SHALL make its calls to the core one at a time, never two at once.
5. The emulator SHALL run on macOS with Python 3.10 or later.

## Requirement 3: It runs in real time

**User Story:** As someone watching a show, I want the emulator to refresh as often as the
board does, so that timing looks the same.

### Acceptance Criteria

1. The emulator SHALL ask the core for a refresh at every grid time, 20 ms apart, passing a
   timestamp in whole milliseconds from a clock that does not go backwards.
2. WHEN a request is late THEN the emulator SHALL pass the current time and SHALL NOT ask
   again for the grid times it missed.
3. WHEN the example show of seed 01 runs on this Mac THEN `status` SHALL report 49 or more
   in `fps` for every full second after the first.
4. WHEN a show with the ten-leg mapping and a dense 60 x 30 animation runs on this Mac THEN
   `status` SHALL report 49 or more in `fps` for every full second after the first.

## Requirement 4: The page draws every LED

**User Story:** As someone without the hardware on the desk, I want to see every LED of the
installation light up, so that I can judge an animation as it will look.

### Acceptance Criteria

1. The page SHALL draw every LED of every leg as a dot at the canvas position Requirement 5
   gives it, with (1,1) at the bottom-left, x growing to the right and y growing upward.
2. The page SHALL scale the drawing to fit the window, SHALL draw it again when the window
   changes size, and SHALL show a 60 x 30 canvas completely, without scrolling, in a window
   of 1280 x 800.
3. The page SHALL mark, for every leg, which rows belong to it, with the leg's number and
   pin in the leg colour.
4. The page SHALL show the measured refresh rate: the `fps` the core reports, and the number
   of refreshes the page drew in the last full second.
5. The emulator SHALL offer every refresh to the page within the 20 ms in which the core
   produced it. WHEN a page cannot keep up THEN it SHALL receive the newest refresh and
   SHALL skip older ones.
6. A dark LED SHALL stay visible as a faint outline, so that the positions of all LEDs can
   be seen at any time.
7. The page SHALL show each colour value through one fixed display curve and SHALL NOT
   change the values in any other way.
8. WHEN the example show of seed 01 runs THEN the page SHALL show the words HELLO WORLD
   upright and readable from left to right, then the bouncing square, the two alternating
   every 15 seconds.
9. WHEN the example show, or a show with the ten-leg mapping and a dense 60 x 30 animation,
   runs on this Mac THEN the page SHALL draw 49 or more refreshes in every full second.

## Requirement 5: The page places the LEDs itself

**User Story:** As the author of the core, I want the page to place every LED from the pin
and the position along the chain, so that a mapping mistake in the core shows as a wrong
picture instead of being hidden.

### Acceptance Criteria

1. For every refresh the emulator SHALL send the page, for each leg in the order the core
   lists the legs, the LED bytes in chain order exactly as the core produced them. It SHALL
   NOT send canvas coordinates, a picture, or bytes in any other order.
2. The emulator SHALL tell the page each leg's number, pin and number of LEDs as the core
   reports them, and SHALL serve the show folder's `mapping.json` to the page byte for byte.
3. The page SHALL work out the canvas position of LED number n on a pin from that pin, n and
   `mapping.json`, by the rule of `docs/mapping.md`.
4. The page SHALL NOT reorder, mirror or correct the LED data it receives.
5. The page's position rule SHALL be in a script file that runs without a browser, so that
   the test suite can compare it with the reference for every LED.

## Requirement 6: A virtual serial port carries commands

**User Story:** As someone with serial tools that talk to the board, I want to point them at
the emulator by changing only the port name, so that I use one set of tools for both.

### Acceptance Criteria

1. The emulator SHALL create a pseudo-terminal and a symbolic link to it at the path of
   Requirement 1, so that the port has the same name on every run.
2. Every byte written to the port SHALL reach the core's entry for bytes, unchanged and in
   order, and every reply the core gives SHALL be written back to the port.
3. The port SHALL pass bytes unchanged in both directions: it SHALL NOT echo, and SHALL NOT
   add, remove or change a newline or a carriage return.
4. A program SHALL be able to open and close the port any number of times while the
   emulator runs.
5. WHEN a link from an earlier run is at the path THEN the emulator SHALL replace it. IF the
   path holds anything that is not a symbolic link, or the link cannot be created, THEN the
   emulator SHALL refuse to start, as Requirement 12 defines.
6. A program that sets a speed on the port, or changes its DTR and RTS lines, SHALL work
   against the port as it does against the board; these settings SHALL have no effect.

## Requirement 7: The page address accepts commands over HTTP

**User Story:** As the author of a phone app or a script, I want to send the emulator the
same HTTP request I will send the board, so that I can build against the emulator first.

### Acceptance Criteria

1. WHEN a `POST` request for `/odrig` arrives on the page address THEN the emulator SHALL
   pass its body, with or without a final newline, to the core's entry for one line, and
   SHALL answer with status 200, content type `application/json`, and the reply line exactly
   as the core returned it as the body.
2. The status SHALL be 200 for every line that reached the command front-end, also when the
   reply has `"ok":false`.
3. WHEN a request for `/odrig` uses any other method THEN the emulator SHALL answer with
   status 405, an `Allow: POST` header and no body, and the front-end SHALL NOT be called.
4. The emulator SHALL NOT look at the content type of the request.
5. WHEN the body is longer than 128 bytes THEN the emulator SHALL pass on its first 128
   bytes only.
6. IF a `POST` request for `/odrig` has no usable `Content-Length` THEN the emulator SHALL
   answer with status 411 and the front-end SHALL NOT be called.
7. The path SHALL match `/odrig` exactly, whatever follows a question mark. A request for
   any path the emulator does not serve SHALL get status 404.
8. Commands from the port and commands over HTTP SHALL act on the same core: what one
   changes, `status` over the other reports.

## Requirement 8: The page shows commands and the status as they happen

**User Story:** As someone testing a tool or an app, I want to see each command arrive with
its reply and the state it leaves, so that I can tell what my tool really sent.

### Acceptance Criteria

1. WHEN a command line arrives by the port or over HTTP THEN the page SHALL show, without
   being reloaded, an entry with the time it arrived, whether it came by serial or HTTP, the
   line, and the reply.
2. WHEN the line was longer than 64 characters THEN the entry SHALL show its first 64
   characters and a mark that it was cut.
3. The emulator SHALL keep the last 500 entries, and a page opened later SHALL show the
   entries kept so far.
4. The page SHALL show the current status: on or off, brightness, the id of the item
   playing, the id of the animation on the LEDs, and the reason of an invalid show.
5. The status shown SHALL be what `status` returns: the emulator SHALL obtain it from the
   core's `status` command after every command that arrived and at least once a second.
6. The status requests the emulator makes for the page SHALL NOT appear in the command log.
7. The page SHALL NOT send commands, and the emulator SHALL have no command that the board
   does not have.

## Requirement 9: The mapping view shows the board, the legs and the snakes

**User Story:** As someone wiring or checking the installation, I want to see which pin
feeds which leg and how each leg's LEDs run through its rows, so that I can trust the
mapping file.

### Acceptance Criteria

1. The page SHALL have a mapping view with a drawing of the ESP32-S3 board: the antenna at
   the top, the USB sockets at the bottom, and its two rows of pins with the labels and the
   order of the drawing in `docs/mapping.md`.
2. For every leg in `mapping.json` the view SHALL draw a line from the leg's pin on the
   board to the first LED of the leg's chain.
3. For every leg the view SHALL draw the path of the chain through the leg's rows in chain
   order, with an arrow showing the direction in every row, and SHALL show the LED numbers
   at both ends of every row.
4. Each leg SHALL have one colour, used for its pin, its line, its path, the outline of its
   rows on the canvas and its label.
5. WHEN the pointer is on a leg's label, pin, line or rows THEN the view SHALL highlight
   that leg in all of these places and SHALL fade the other legs. WHEN the pointer is on an
   LED THEN the view SHALL also show its leg, pin, LED number and canvas coordinates.
6. The LEDs in the mapping view SHALL be live: they SHALL show every refresh as
   Requirement 4 defines.
7. Everything the view draws about legs SHALL come from `mapping.json`: a mapping with
   other pins, another first side, another order of rows or another number of rows per leg
   SHALL be drawn without a change to the page. WHEN a leg's pin is not on the board
   drawing THEN the view SHALL draw the pin beside the board with its number.
8. WHEN the ten-leg mapping is shown in a window of 1280 x 800 THEN all ten legs, their
   lines, their paths and the two end numbers of all 30 rows SHALL be readable, with no
   label drawn over another.

## Requirement 10: An invalid show is shown with its reason

**User Story:** As someone packing shows, I want the emulator to tell me why a show is
refused, in the words the board would use, so that I can fix it without the board.

### Acceptance Criteria

1. WHEN the core reports that the show is invalid THEN the page SHALL show the reason text
   exactly as the core reports it, in both views.
2. WHEN the mapping is valid and the show is not THEN the page SHALL draw every LED dark and
   the mapping view SHALL work.
3. WHEN the mapping is invalid THEN the page SHALL show the reason and no LEDs.
4. WHEN the show is invalid THEN the port and the HTTP address SHALL still pass every
   command to the core and return its reply.

## Requirement 11: A record mode runs on a virtual clock

**User Story:** As a tester, I want to run a show for a stated time without waiting and get
every LED value in a file, so that I can compare the emulator with the reference exactly.

### Acceptance Criteria

1. WHEN the emulator is started as
   `python -m emulator SHOW_DIR --record OUT --seconds S [--script FILE]` THEN it SHALL open
   no page and no port, SHALL NOT wait for real time, SHALL ask the core for a refresh at
   every tick, the ticks being 0 ms, 20 ms, 40 ms and so on below S seconds, and SHALL then
   exit with status 0.
2. The record file SHALL hold the legs as the core lists them and, for every tick, the
   tick's time, whether the core produced a refresh, and each leg's LED data in chain order.
3. A script SHALL be a text file with one command per line, written as a time in whole
   milliseconds, a space and the command line. The emulator SHALL give each command to the
   core's entry for one line with the command's own time as the timestamp, before the first
   tick that is not earlier than that time, and SHALL print `reply <time> <reply>` for it.
4. IF the script has a line without a time, a time earlier than the one before it, or a
   time at or after the length of the recording THEN the emulator SHALL refuse it before
   recording, as Requirement 12 defines, and SHALL write no file.
5. WHEN the emulator records twice with the same show folder, length and script THEN the
   two record files SHALL be byte-identical.
6. The emulator SHALL make no status request of its own in record mode.
7. WHEN 60 seconds of the example show are recorded THEN the LED data of every leg at every
   tick SHALL equal the reference, the two changes of the cycle at 15 and 30 seconds
   included.
8. WHEN a show is recorded whose `mapping.json` has the `first_led` of one leg flipped THEN
   the LED data SHALL equal the reference for the unchanged mapping in every other leg, and
   in the flipped leg every row SHALL hold the reference row in reverse order.

## Requirement 12: Failures at start are clear

**User Story:** As a user, I want a wrong start to end at once with one line that says
what is wrong, so that I do not stare at a page that never loads.

### Acceptance Criteria

1. IF the emulator cannot start THEN it SHALL write exactly one line
   `error: <reason>: <detail>` to standard error, SHALL exit with status 1, and SHALL leave
   no link, no listening address and no partly written file behind.
2. The reason SHALL be the one of this table:

   | Reason | Condition |
   |---|---|
   | `not-a-folder` | `SHOW_DIR` does not exist or is not a folder. |
   | `core-not-built` | The core's shared library is not found or cannot be loaded. The detail names the command that builds it. |
   | `serial-unavailable` | The pseudo-terminal or its link cannot be created, or the link's path holds something that is not a symbolic link. |
   | `address-in-use` | The page address is already in use or cannot be opened. |
   | `bad-length` | In record mode, the length is not above 0. |
   | `bad-script` | In record mode, the script cannot be read or breaks a rule of Requirement 11. |

3. IF the command line is not understood THEN the emulator SHALL print a usage message and
   exit with status 2.

## Requirement 13: One command tool for the emulator and the board

**User Story:** As an operator or a tester, I want one tool that sends the documented
commands to the emulator or to the board, over serial or over HTTP, so that I learn it
once.

### Acceptance Criteria

1. The command tool SHALL be started as
   `python -m odrigctl (--port NAME | --http ADDRESS) COMMAND`, where COMMAND is one of
   `play ID`, `on`, `off`, `brightness N` and `status`.
2. The tool SHALL send the command as one line, `play <ID>`, `on`, `off`,
   `brightness <N>` or `status`, followed by a newline. It SHALL send ID and N as they were
   typed and SHALL NOT check them, so that every judgement is the command front-end's.
3. WHEN `--port` is given THEN the tool SHALL open that serial port without resetting the
   board: it SHALL lower RTS before it lowers DTR, SHALL discard what was waiting in the
   port, SHALL send the line, and SHALL take as the reply the first received line that is a
   JSON object with an `ok` member. It SHALL ignore every other line it receives.
4. WHEN `--http` is given THEN the tool SHALL send the line as the body of
   `POST http://ADDRESS/odrig` with the content type `application/octet-stream`, and SHALL
   take the body of a response with status 200 as the reply.
5. The tool SHALL print the reply line to standard output and SHALL exit with status 0 when
   the reply has `"ok":true` and with status 1 when it has `"ok":false`.
6. IF the target cannot be reached, or no reply arrives within the time limit, 2 seconds
   unless `--timeout` says otherwise, THEN the tool SHALL print one line to standard error
   and exit with status 3. IF the command line is not understood THEN it SHALL exit with
   status 2.
7. The tool SHALL treat the emulator and the board alike: it SHALL have no option and no
   code that tells them apart.
8. The tool SHALL use only the Python standard library.
9. WHEN a session with every command of `docs/commands.md` is sent to the emulator with the
   tool, once through the port and once over HTTP, THEN the replies of the two sessions
   SHALL be the same and SHALL be the replies the reference player of seed 02 gives, the
   value of `fps` aside, and each command SHALL appear in the page's log with its transport
   and its reply.
10. The tool SHALL be new tracked files. The untracked proof-of-concept tools in `tools/`
    SHALL stay as they are.

## Requirement 14: A demo show for the ten-leg build

**User Story:** As the owner of the installation, I want a ready show for the target
canvas, so that I can see the ten-leg build work before it is wired.

### Acceptance Criteria

1. `shows/demo-10/show.json` SHALL be tracked and SHALL hold: item 1, the animation
   `hello.odrg`; item 2, the animation `dvd.odrg`; item 3, a cycle of items 1 and 2 with
   `seconds` 15; `start` 3; and `brightness` 128.
2. The two sources SHALL be written by the Hello world and DVD bounce generators of seed 01
   with `mapping/legs-10.json`, which gives them the 60 x 30 canvas. No canvas size SHALL be
   written anywhere for this show.
3. The documentation SHALL give the commands that generate the two sources and pack the
   show, with `mapping/legs-10.json`, into `build/demo-10/show`.
4. WHEN the packed demo show is recorded for 31 seconds THEN the LED data SHALL equal the
   reference.
5. WHEN the emulator runs the packed demo show THEN the mapping view SHALL show the board,
   ten legs on pins 1 to 10 and each leg's path across its three rows, with the animation
   playing on the LEDs.

## Requirement 15: Local and self-contained

**User Story:** As a user on a laptop without a network, I want the emulator to need
nothing from outside, so that it works anywhere.

### Acceptance Criteria

1. The emulator SHALL listen on 127.0.0.1 only.
2. The page SHALL load every file it uses from the emulator, and SHALL work in current
   Safari and Chrome with no plug-in.
3. The emulator, the page and the command tool SHALL work without a network connection.

## Requirement 16: One test command, checked against the reference

**User Story:** As a contributor, I want one command that proves the emulator and the
command tool, so that a change that breaks them cannot pass unnoticed.

### Acceptance Criteria

1. The command `python3 -m unittest discover -s tests/emulator -t .`, run from the
   repository root on macOS, SHALL build the core's shared library and SHALL run the whole
   suite of this seed.
2. The command SHALL select tests by discovery in that folder: a test file added there
   SHALL be run without a change to any command, script or list.
3. The suite SHALL need no hardware, no network connection and no browser. It SHALL need
   only Apple's command-line developer tools, the JavaScript shell that is part of macOS,
   and Python 3.10 or later.
4. The suite SHALL contain a test for every acceptance criterion of Requirements 1 to 15
   that a program can check, and the checks of Requirement 11 criteria 7 and 8 SHALL compare
   with the reference at every tick.
5. The criteria that need a person, or a tool that drives a browser, to look at the page
   SHALL be listed in the documentation as a check list, each to be checked in Safari and in
   Chrome: Requirement 4 criteria 2, 6, 8 and 9, Requirement 8 criteria 1 and 4,
   Requirement 9 criteria 1, 5 and 8, Requirement 10 criterion 1 and Requirement 14
   criterion 5.

## Requirement 17: The emulator and the tool are documented

**User Story:** As a newcomer, I want to read how to start the emulator and use the command
tool, so that I can try a show without reading the code.

### Acceptance Criteria

1. `docs/emulator.md` SHALL describe how to build the core's shared library, how to pack
   and start the example show and the demo show, the two views of the page, the port, the
   HTTP address, the record mode with its script and file formats, the command tool with
   one example for each command and for each transport, the test command, and the check
   list of Requirement 16 criterion 5.
2. `README.md` SHALL point to `docs/emulator.md`.
