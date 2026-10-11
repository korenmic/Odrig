# Requirements: Firmware build with the player (seed 04)

Source seed: `project-seeds/04-p1-firmware-build-with-the-player/seed.md`. It depends on
seed 01 for packed shows and the readers of the package `odrig`, on seed 02 for the core in
`core/` and its host interface `core/include/odrig_core.h`, and on seed 03 for the command
tool `odrigctl`, the emulator the board is compared with, and the HTTP rules of its
Requirement 7. None of them is implemented when this is written: these requirements rely on
what their `design.md` files state.

`docs/format.md`, `docs/mapping.md`, `docs/show.md`, `docs/commands.md` and `docs/wifi.md`
define the behaviour. These requirements say what the firmware and its tools do with them.
Where those documents and the seed leave a point open, the answer used here is recorded in
`docs/drifts.md` under "Seed 04".

Terms:

- **the board**: the ESP32-S3-N16R8 of `docs/decisions.md`, connected over USB.
- **stock WLED**: the official build `WLED_16.0.1_ESP32-S3_16MB_opi.bin`.
- **the firmware**: the custom WLED 16.0.1 build of this seed.
- **the usermod**: the code this seed adds to WLED, in `firmware/usermod/`.
- **the core**: the C++ library of seed 02.
- **the tool**: the program started as `python3 firmware/fw.py`.
- **work folder**: `build/firmware/` under the repository root, which git ignores.
- **the port**: the board's USB serial port.
- **storage**: the board's LittleFS partition, named `spiffs` in the partition table.
- **show folder**: a folder holding an installed file set, as in `docs/show.md`.
- **output**: one LED output of WLED: a pin and a number of LEDs.
- **probe build**: a second build of the firmware, for tests only, that can also report
  measurements on the port.
- **owner's check**: a check that needs a person: eyes on the LEDs, or a device joined to
  the board's Wi-Fi network.

## Requirement 1: One command builds the firmware

**User Story:** As a maintainer, I want one command that turns this repository into a
firmware image, so that a build never depends on steps somebody remembers.

### Acceptance Criteria

1. WHEN `python3 firmware/fw.py build` is run from the repository root THEN the tool SHALL
   set up its tools, fetch WLED, build, write the image to
   `build/firmware/out/odrig-firmware.bin` with its SHA-256 beside it, and exit with
   status 0.
2. The tool SHALL fetch WLED's source at the tag `v16.0.1` and SHALL refuse to build unless
   the fetched source is at commit `29b389df1c1aaec6ff53aea742d17063b985906c`. WLED's source
   SHALL NOT be tracked in this repository.
3. Every change to a file of WLED SHALL exist only as a patch file in `firmware/patches/`,
   applied by the build in the order of the file names. The build SHALL work when the
   folder holds no patch.
4. The firmware SHALL be built from WLED's own environment `esp32s3dev_16MB_opi`: the same
   board, platform, flash settings and partition table. It SHALL differ only in what this
   seed needs: the usermod in place of WLED's audio usermod, the core, WLED's serial
   handling switched off, and a release name of its own.
5. IF the image is larger than the application partition, 3,145,728 bytes, THEN the build
   SHALL fail and SHALL say so.
6. WHEN the build is run again THEN it SHALL reuse what the work folder holds and SHALL NOT
   fetch WLED or the tools again.
7. `python3 firmware/fw.py build --stock` SHALL build WLED's own environment without the
   usermod and without any other change, and `--probe` SHALL build the probe build.

## Requirement 2: The tools live inside the repository tree

**User Story:** As the owner of this Mac, I want everything the build installs to stay in
one folder of the repository, so that removing that folder removes all of it.

### Acceptance Criteria

1. The tool SHALL install everything it needs into the work folder: a Python environment
   with PlatformIO, esptool and littlefs-python, Node.js, PlatformIO's packages and every
   cache.
2. The tool and the programs it starts SHALL NOT create or change a file outside the
   repository tree. In particular they SHALL leave the home folder as it was: no
   `~/.platformio`, no `~/.buildcache`, and nothing added to the caches of pip and npm
   there.
3. The tool SHALL need only what is on the Mac before it runs: macOS with Apple's
   command-line developer tools, git, and Python 3.10 or later. It SHALL need a network
   connection only the first time, to fetch.
4. The versions of the tools SHALL be fixed: PlatformIO and its Python packages by WLED's
   own `requirements.txt` at the tag, the others by `firmware/requirements.txt`.
5. Nothing that is fetched or built SHALL be tracked.

## Requirement 3: The core is used as it is, and the added code is thin

**User Story:** As the owner of the installation, I want the board to run the very source
files the emulator runs, so that a show that works in the emulator behaves the same on the
board.

### Acceptance Criteria

1. The build SHALL compile the files `core/src/*.cpp` from where they are, as they are.
   There SHALL be no copy, no fork and no changed variant of them in `firmware/` or in the
   fetched WLED source.
2. The build SHALL compile the core with the compiler flags of the WLED environment and
   SHALL NOT change a flag for it.
3. The usermod SHALL only: give the core its memory, the time and the files of the show;
   carry bytes between the port and the core; carry request bodies and replies between
   WLED's web server and the core; set WLED's outputs from the core's list of legs; send the
   core's LED data to those outputs; keep WLED from the LEDs; and report its state in WLED's
   information page. It SHALL contain no decoder, no mapping rule, no show logic and no
   interpreter of commands.
4. The usermod SHALL make its calls to the core one at a time, never two at once.

## Requirement 4: One command flashes the firmware over USB

**User Story:** As a maintainer, I want one command that puts the built image on the
board, so that flashing cannot be done wrongly.

### Acceptance Criteria

1. WHEN `python3 firmware/fw.py flash` is run THEN the tool SHALL write the built image to
   the board, SHALL check what was written, SHALL restart the board, and SHALL confirm that
   the firmware answers `status` on the port.
2. The tool SHALL write only the first application partition, at `0x10000`, and SHALL
   clear the boot selection data at `0xE000` to `0xFFFF`, so that the board starts that
   partition. It SHALL NOT write the bootloader, the partition table or storage.
3. Before writing, the tool SHALL read the board's partition table and SHALL refuse with
   `layout-mismatch` unless it has an application partition at `0x10000` that the image
   fits in and a data partition named `spiffs`.
4. The tool SHALL refuse with `image-missing` when there is no built image and with
   `checksum-mismatch` when the image does not match the SHA-256 written beside it.
5. The tool SHALL use the port given with `--port`, else the one in `ODRIG_BOARD_PORT`,
   else the only `/dev/cu.usbmodem*` device. IF there is none, or more than one, THEN it
   SHALL refuse with `no-board`.
6. Flashing SHALL leave storage as it was: the installed show and WLED's settings stay.

## Requirement 5: One command restores stock WLED

**User Story:** As the owner of the board, I want one command that brings back the
official WLED build, so that trying the custom firmware can always be undone.

### Acceptance Criteria

1. WHEN `python3 firmware/fw.py restore-stock` is run THEN the tool SHALL write the stock
   application image to the first application partition, SHALL clear the boot selection
   data, SHALL restart the board, and SHALL confirm WLED's handshake: the board answers the
   byte `v` on the port with a line `WLED ` followed by a number.
2. Before it writes anything, the tool SHALL check the SHA-256 of every stock file it is
   about to write against the tracked list `firmware/stock.sha256`. IF a file is missing
   THEN it SHALL refuse with `stock-missing`, and IF a checksum differs THEN with
   `checksum-mismatch`.
3. WHEN `--full` is given THEN the tool SHALL also write the stock bootloader and the stock
   partition table, each checked in the same way.
4. Restoring SHALL leave storage as it was, so that WLED's settings and the show it played
   before are still there.

## Requirement 6: The backup and the board's fuses are never touched

**User Story:** As the owner of the board, I want the factory backup and the chip's
one-time settings to be out of reach of every tool, so that a mistake can never be final.

### Acceptance Criteria

1. No tool and no test SHALL create, change, move or delete anything in `esp32-backup/`.
   A tool that is given an output path inside that folder SHALL refuse with
   `backup-protected`.
2. No tool and no test SHALL write an eFuse or run a program that can.
3. No tool SHALL erase the whole flash.
4. The tools SHALL write to these regions of the flash only: the first application
   partition, the boot selection data and storage; and with `restore-stock --full` the
   bootloader and the partition table.

## Requirement 7: At start the core loads the installed file set from storage

**User Story:** As an operator, I want the board to play what is installed on it from
power-on, so that the installation runs without a computer.

### Acceptance Criteria

1. WHEN the firmware starts THEN the usermod SHALL start the core on the files in the
   folder `/odrig` of storage: `mapping.json`, `show.json` and the `.odrg` files.
2. The usermod SHALL give the core a file in the pieces the core asks for and SHALL never
   hold a whole file in memory.
3. The usermod SHALL take the core's memory from the chip's internal memory, and from the
   external memory only when the internal memory cannot supply it.
4. The usermod SHALL give the core the time in whole milliseconds since start from a
   64-bit clock that does not go backwards and does not wrap.
5. WHEN the installed show is invalid in any way `docs/show.md` lists THEN the LEDs SHALL
   stay dark and `status` on the board SHALL report the same reason text the emulator
   reports for the same folder.
6. The firmware SHALL NOT write, create or delete a file in `/odrig`.
7. The time the core takes to start SHALL be measured on the board and recorded: for the
   example show, for one dense 60 x 30 clip of 10 seconds, and for storage filled with 9 MB
   of dense clips.

## Requirement 8: The outputs are set from mapping.json

**User Story:** As the owner of the installation, I want the firmware's LED outputs to
follow the mapping file, so that the layout is defined in one place only.

### Acceptance Criteria

1. WHEN the core has started with a valid mapping THEN the usermod SHALL set WLED's outputs
   to one output for each leg, in the order of the mapping file, on the leg's pin, with the
   leg's number of LEDs, for WS2812B LEDs with the colour order green, red, blue.
2. Whatever outputs WLED's stored settings hold, the outputs after start SHALL be those of
   criterion 1. The usermod SHALL NOT write WLED's settings file to achieve this.
3. WHEN WLED's LED settings are saved while the firmware runs THEN the usermod SHALL put
   the outputs of criterion 1 back before it sends the next refresh.
4. WHEN the ten-leg mapping is installed THEN all ten outputs SHALL be created and usable.
5. IF an output cannot be created, because the board cannot use the pin or has no output
   left, THEN the other outputs SHALL work, the core SHALL run unchanged, and WLED's
   information page SHALL name the leg and the pin.
6. WHEN the mapping is invalid THEN the usermod SHALL leave WLED's outputs as they are and
   SHALL keep them dark.

## Requirement 9: The core's LED data is sent every 20 ms and WLED takes no part

**User Story:** As someone who made a show in the emulator, I want the board to show
exactly the core's LED data, so that nothing of WLED changes my picture.

### Acceptance Criteria

1. Whenever the outputs can take new data, the usermod SHALL ask the core for a refresh,
   and SHALL send every refresh the core produces to the outputs at once: each leg's data
   to that leg's output, LED number n of the leg to position n of the output.
2. WLED's effects, presets, playlists and transitions SHALL NOT run, and nothing of WLED
   SHALL change what the LEDs show. IF WLED is taken out of this state, by its interface or
   by a network pixel protocol, THEN the usermod SHALL take the LEDs back within one pass
   of WLED's main loop.
3. Every colour value SHALL reach its LED as the core produced it: WLED SHALL apply no
   brightness, no gamma correction, no white balance, no LED map and no matrix layout to
   it.
4. WLED's own switch and brightness control SHALL have no effect on the LEDs.
5. `status` SHALL report the real refresh rate of the board: every refresh the core counts
   SHALL have been sent to the outputs.
6. WHEN the example show plays THEN `status` SHALL report 49 or more in `fps` for every
   full second.
7. WHEN the ten-leg mapping is installed and a dense 60 x 30 animation plays THEN `status`
   SHALL report 49 or more in `fps` for every full second, for the compressed file and for
   the uncompressed file.
8. WHILE WLED updates the firmware through its own interface, the usermod SHALL NOT read
   files or send LED data.

## Requirement 10: Only the core dims, and the current limiter stays active

**User Story:** As the owner of the installation, I want brightness to have one meaning on
the board and in the emulator, and WLED's protection against drawing too much current to
stay in place.

### Acceptance Criteria

1. For every refresh the outputs SHALL be at WLED's full brightness, so that the only
   scaling of a colour value is the core's.
2. WLED's current limiter SHALL act on every refresh, with the maximum current of WLED's
   LED settings and WLED's default current for one LED.
3. WHEN the limiter dims a refresh THEN `status` SHALL still report the core's brightness.

## Requirement 11: The port carries the core's commands

**User Story:** As an operator with a USB cable, I want the board to answer the documented
commands on its serial port, so that the command tool works on the board as on the
emulator.

### Acceptance Criteria

1. Every byte the board receives on the port SHALL reach the core's entry for bytes,
   unchanged and in order, and every reply the core gives SHALL be written to the port.
2. WLED's own serial handling SHALL be switched off in the firmware: no Adalight, no TPM2,
   no Improv, no JSON over serial, no answer to WLED's single-letter commands, and no `Ada`
   line at start.
3. The firmware SHALL write nothing to the port except replies.
4. WHEN the same show is installed on the board and run in the emulator, and the same
   commands are sent to both with `odrigctl`, THEN the replies SHALL be the same, the
   value of `fps` aside.
5. WHEN the show is invalid THEN the port SHALL still carry every command and its reply.

## Requirement 12: The web server accepts commands over HTTP

**User Story:** As an operator with a phone, I want the board to accept the documented
commands over HTTP, so that the installation can be run without a cable.

### Acceptance Criteria

1. WLED's web server SHALL answer `POST /odrig` as `docs/commands.md` and Requirement 7 of
   the seed 03 requirements define: the body goes to the core's entry for one line; the
   answer has status 200, content type `application/json` and the reply as the core
   returned it; another method gets 405 with `Allow: POST`; the path matches exactly; of a
   longer body the first 128 bytes are passed on.
2. Commands over HTTP and commands from the port SHALL act on the same core.
3. WHEN the request's content type is neither `application/x-www-form-urlencoded` nor
   `text/plain` THEN the line the core receives SHALL be the body, byte for byte. With one
   of those two content types this SHALL hold for every body that has none of the
   characters `&`, `=`, `+` and `%` and no zero byte, which every valid command satisfies.
4. WLED's own pages and its JSON interface SHALL keep working.

## Requirement 13: The board hosts its Wi-Fi network as WLED does

**User Story:** As an operator at the event, I want the board to open its own network
when there is no other, so that a phone can reach it anywhere.

### Acceptance Criteria

1. The firmware SHALL leave WLED's Wi-Fi behaviour and settings as they are. WHEN no
   network to join is configured THEN the board SHALL open WLED's access point at start,
   and WHEN a configured network cannot be joined THEN it SHALL open it as WLED's
   access-point setting says.
2. WHEN a device has joined the access point THEN `POST http://4.3.2.1/odrig` SHALL be
   answered as Requirement 12 defines, with the same replies as on the port.
3. The usermod SHALL keep WLED's captive portal answering while it holds the LEDs.
4. WLED's information SHALL report the access point as active, and SHALL show the
   usermod's state: the show's reason or that it is valid, and how many outputs work.

## Requirement 14: One command installs a show over USB

**User Story:** As someone who packed a show, I want one command that puts the folder on
the board, checks it and restarts the board, so that the board runs exactly what the
emulator ran.

### Acceptance Criteria

1. WHEN `python3 firmware/fw.py install-show DIR` is run THEN the tool SHALL make the
   folder `/odrig` of storage hold exactly the files of `DIR`, SHALL check what was
   written, SHALL restart the board, and SHALL print the board's reply to `status`.
2. The tool SHALL refuse a folder that the readers of seed 01 do not accept as an
   installed file set, with their reason, before it touches the board. `--no-check` SHALL
   install any flat folder of files, for tests of invalid shows.
3. Every file of storage outside `/odrig` SHALL keep its content, and the file system
   SHALL keep the format version it had.
4. The tool SHALL check the result in two ways: storage on the board has the checksum of
   the image the tool built, over the whole partition; and in that image `/odrig` holds
   exactly the files of `DIR`, byte for byte.
5. IF the files do not fit THEN the tool SHALL refuse with `no-space` and SHALL write
   nothing to the board.
6. The tool SHALL keep a copy of storage as it read it, in the work folder, before it
   writes.
7. WHEN the installed show is valid THEN the tool SHALL exit with status 0, and WHEN the
   board's `status` reports a reason THEN with status 1.
8. `python3 firmware/fw.py read-show OUT` SHALL copy the files of `/odrig` on the board
   into the new or empty folder `OUT`, so that they can be compared with a show folder.

## Requirement 15: Tests that need the board are kept apart

**User Story:** As a contributor without the board on the desk, I want to run every test
that does not need it with one command, and to know which tests need it.

### Acceptance Criteria

1. `python3 firmware/fw.py test` SHALL run the suite in `tests/firmware/`, which needs no
   board, no network connection and nothing outside the work folder.
2. `python3 firmware/fw.py test-board` SHALL run the suite in `tests/board/`, which needs
   the board on USB. IF no board is found THEN it SHALL refuse with `no-board` and run
   nothing.
3. `python3 firmware/fw.py test-air --http ADDRESS` SHALL run the suite in `tests/air/`,
   which needs the board on USB and this Mac joined to the board's Wi-Fi network.
4. Each of the three commands SHALL select its tests by discovery in its folder: a test
   file added there SHALL be run without a change to any command, script or list.
5. Every show a test installs on the board SHALL have a brightness of 40 or less.
6. A test that changes what the board runs SHALL leave the board with the firmware of
   this seed and a valid show.

## Requirement 16: The firmware is accepted on the real board

**User Story:** As the owner of the installation, I want every item of the seed's
definition of done checked on the board, and to know which of them a person checked.

### Acceptance Criteria

1. Owner's check: WHEN the example show is installed and the board is powered on with no
   command sent THEN Hello world and the bouncing square SHALL alternate every 15 seconds
   on the LEDs.
2. WHEN the example show is installed THEN `status` SHALL report 49 or more in `fps`.
   Owner's check: the same with two legs wired.
3. A session with every command of `docs/commands.md`, sent with `odrigctl` to the board
   and to the emulator running the same show folder, SHALL give the same replies on both,
   the value of `fps` aside.
4. The files `read-show` copies from the board SHALL be byte-identical to the show folder
   the emulator ran.
5. WHEN the ten-leg mapping and a dense 60 x 30 animation are installed THEN `status` SHALL
   report 49 or more in `fps`, for the compressed and for the uncompressed file.
6. WHEN `restore-stock` has run THEN the board SHALL answer WLED's handshake, and WHEN
   `flash` has run after it THEN the firmware SHALL play the installed show again.
7. Owner's check: after power-on the board's own Wi-Fi network SHALL be up, and with a
   computer or phone joined to it `odrigctl --http 4.3.2.1` SHALL get the same replies as
   over USB.
8. The documentation SHALL list the owner's checks with what to do and what must be seen,
   and the seed SHALL be completed only when they are done.

## Requirement 17: Building, flashing, installing and rolling back are documented

**User Story:** As a newcomer with the board on the desk, I want to read how to build,
flash, install a show and go back to stock WLED, so that I can do it without reading the
code.

### Acceptance Criteria

1. `docs/firmware.md` SHALL describe what the tool needs, the work folder, every command
   of the tool with an example, the regions of the flash the tools write, how to roll back,
   what the firmware changes in WLED's behaviour and what it leaves as it is, the three
   test commands, the owner's checks, and the measurements made on the board.
2. `README.md` SHALL point to `docs/firmware.md`.
3. `docs/decisions.md` SHALL state what was measured for its two open questions about the
   board: the decode speed at 50 frames per second for 1,800 LEDs, and ten outputs in the
   firmware.
