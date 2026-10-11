# Requirements: The board's Wi-Fi name and password (seed 08)

Source seed: `project-seeds/08-p1-wifi-name-and-password/seed.md`. It depends on seed 04 for
the firmware tool `firmware/fw.py`, the way that tool reads and writes the board's storage,
the probe build and the three test suites. Seed 04 is implemented up to its owner's checks:
these requirements rely on its code as it is and name it where they extend it.

`docs/wifi.md`, `docs/firmware.md`, `docs/commands.md` and `docs/decisions.md` define the
behaviour around this seed. Where they and the seed leave a point open, the answer used
here is recorded in `docs/drifts.md` under "Seed 08".

This spec holds no password. Where an example needs one it shows
`<the operators' password>`.

Terms:

- **the board**, **the tool**, **the firmware**, **the probe build**, **the port**,
  **storage**, **work folder**, **stock WLED**: as in the seed 04 requirements.
- **the access point**: the Wi-Fi network the board hosts. It is WLED's.
- **the name**: the network name of the access point.
- **the password**: the WPA2 password of the access point.
- **the settings file**: `firmware/wifi.json`, the tracked file that holds the name and the
  password.
- **a settings file**: the settings file, or a file of the same format named with
  `--settings`.
- **WLED's stored settings**: the files `/cfg.json` and `/wsec.json` in storage.
- **printable ASCII**: the 95 characters from the space, U+0020, to the tilde, U+007E.
- **a board from scratch**: a board with WLED's 16 MB layout whose storage does not hold
  the name and the password yet: one that runs stock WLED or an earlier build of the
  firmware, or one whose file system WLED has just made.
- **owner's check**: a check that needs a person: a phone or computer joined to the
  board's network.

## Requirement 1: One tracked file holds the name and the password

**User Story:** As the owner of the installation, I want the network's name and password in
one file of this repository, so that there is one place to read them and one place to
change them.

### Acceptance Criteria

1. The settings file SHALL be `firmware/wifi.json`, tracked by git: a UTF-8 JSON object
   with exactly the two members `name` and `password`, each a string.
2. The name in the settings file SHALL be `odrig`.
3. The password in the settings file SHALL be the one the owner supplied. It SHALL NOT be
   WLED's default password, `wled1234`.
4. The password SHALL be in no other tracked file: no source, no test, no document, no
   spec, no seed and no state file.
5. The tool SHALL take a name and a password from a settings file and from nowhere else.
   No command SHALL have an option, an argument or an environment variable that carries a
   name or a password.
6. Without `--settings` a command SHALL read the settings file. With `--settings FILE` it
   SHALL read `FILE`, which has the same format.

## Requirement 2: Values outside the limits are refused before the board is touched

**User Story:** As a maintainer, I want a name or a password that no phone could use to be
refused at once, so that a board is never left with a network nobody can join.

### Acceptance Criteria

1. A name SHALL be accepted only when it has 1 to 32 characters, and a password only when
   it has 8 to 63 characters, every one of them printable ASCII.
2. IF the name is empty, has more than 32 characters, or has a character outside printable
   ASCII THEN the tool SHALL refuse with `wifi-name-invalid`.
3. IF the password has fewer than 8 characters, more than 63, or a character outside
   printable ASCII THEN the tool SHALL refuse with `wifi-password-invalid`.
4. IF the file is not there THEN the tool SHALL refuse with `wifi-settings-missing`. IF it
   is not UTF-8, begins with a byte-order mark, is not exactly one JSON value, names a
   member twice in one object, is not an object, lacks `name` or `password`, has another
   member, or has a member that is not a string THEN the tool SHALL refuse with
   `wifi-settings-malformed`.
5. In each of these cases the tool SHALL exit with status 1 and one line
   `error: <reason>: <detail>` on standard error, and SHALL NOT have looked for the port,
   started esptool, or read or written a storage image.
6. A name of 33 characters, a password of 7 characters and a password of 64 characters
   SHALL each be refused. A name of 1 character, a name of 32, a password of 8 and a
   password of 63 SHALL each be accepted.

## Requirement 3: One command applies the settings over USB

**User Story:** As a maintainer with the board on the desk, I want one command that gives
the board the name and the password of the settings file, so that changing them is as plain
as installing a show.

### Acceptance Criteria

1. WHEN `python3 firmware/fw.py set-wifi` is run THEN the tool SHALL make WLED's stored
   settings on the board hold the name and the password of the settings file, SHALL check
   what was written, SHALL restart the board, and SHALL wait for the board's reply to
   `status`.
2. On success the tool SHALL print exactly three lines to standard output, `name: <name>`,
   `password: set` and the board's reply to `status`, and SHALL exit with status 0. The
   exit status SHALL NOT depend on whether that reply reports an invalid show.
3. The command SHALL accept `--port P`, with the choice of the port that Requirement 4
   criterion 5 of the seed 04 requirements defines; `--settings FILE`; and
   `--wait SECONDS`, the time it waits for the reply, which is 20 seconds without the
   option.
4. The tool SHALL change storage the way `install-show` does: it reads the board's
   partition table and takes the place and the size of storage from it; it has a copy of
   storage as it is in the work folder before it writes; it edits that copy, with the file
   system keeping the disk version it has; it writes only the blocks that differ; and it
   has the chip compare the whole partition with the new image.
5. The tool SHALL check the result in two ways: the board's storage has the checksum of
   the image the tool made; and in that image WLED's stored settings, read back, hold the
   name and the password.
6. WHEN WLED's stored settings already hold what Requirement 4 criteria 1 and 2 ask for
   THEN the tool SHALL write nothing to the board, SHALL restart it, and SHALL print the
   same three lines.
7. IF the board gives no reply to `status` in the time given THEN the tool SHALL fail with
   `no-reply`. The settings are stored on the board then.
8. IF the changed files do not fit into storage THEN the tool SHALL fail with `no-space`
   and SHALL write nothing to the board.
9. IF `/cfg.json` or `/wsec.json` in storage is not a JSON object, or its member `ap` is
   not an object, THEN the tool SHALL fail with `wled-settings-malformed` and SHALL write
   nothing to the board.
10. IF a step fails after the tool has put the chip into its bootloader THEN the tool SHALL
    restart the board before it reports the failure.

## Requirement 4: Only the name and the password change

**User Story:** As the owner, who wants to explore WLED's own interface, I want everything
else of WLED left as it is, so that setting the name and the password costs me nothing I
had.

### Acceptance Criteria

1. The tool SHALL set these members and no other: `ap.ssid` of `/cfg.json` to the name,
   `ap.pskl` of `/cfg.json` to the number of characters of the password, and `ap.psk` of
   `/wsec.json` to the password.
2. `/cfg.json` SHALL NOT hold the password afterwards: IF it has a member `ap.psk` THEN
   the tool SHALL remove that member.
3. Every other member of the two files SHALL keep its value and its place, among them the
   access point's channel (`ap.chan`), whether its name is hidden (`ap.hide`), when it
   opens (`ap.behav`), and the networks the board is to join (`nw`).
4. WHEN a file has no `ap` object THEN the tool SHALL add one that holds only the members
   of criterion 1. WHEN a file is not in storage THEN the tool SHALL create it with only
   that object.
5. A file that already holds what criteria 1 and 2 ask for SHALL keep its bytes.
6. Every other file of storage SHALL keep its content: the installed show in `/odrig`,
   WLED's presets and every other file of WLED. The file system SHALL keep its disk
   version.
7. This seed SHALL NOT change the firmware. No file of the usermod changes outside the code
   of the probe build, no patch to WLED is added, and WLED's web interface, its settings
   pages and its JSON interface stay reachable as they are.
8. `flash` and `restore-stock` SHALL stay as the seed 04 requirements define them. They do
   not write storage, so the name and the password stay through both.

## Requirement 5: The password is never shown

**User Story:** As the owner, I want the password to appear in the settings file and
nowhere I did not put it, so that a terminal, a log or a failing test never gives it away.

### Acceptance Criteria

1. The tool SHALL NOT write the password to standard output or to standard error: not on
   success, not in an error line, and not in the output of a program it started.
2. An error line about a settings file SHALL quote no text from that file. It MAY give the
   number of characters of a value it refuses.
3. The tool SHALL write no log. It SHALL write the password only to the board's storage
   and into the storage images of the work folder, which are copies of the board's storage
   that git ignores.
4. The tool SHALL NOT pass the password to another program in an argument or in an
   environment variable.
5. The text form of the settings inside the tool, what Python's `repr` and `str` give,
   SHALL NOT contain the password.
6. No test SHALL print a password. A test that compares passwords SHALL reduce the
   comparison to true or false before it asserts, so that a failure names no value.

## Requirement 6: A board from scratch gets the settings with the firmware

**User Story:** As someone who prepares a new board, I want the command that installs the
firmware to give the board the name and the password as well, so that no board reaches the
event with WLED's public password.

### Acceptance Criteria

1. WHEN `python3 firmware/fw.py install-firmware` is run THEN the tool SHALL write the
   built firmware to the board as `flash` does, SHALL wait for the firmware's reply to
   `status`, SHALL then apply the settings as `set-wifi` does, and SHALL print the three
   lines `set-wifi` prints.
2. Before it touches the board the tool SHALL check the settings file as Requirement 2
   defines and the image as `flash` does (`image-missing`, `checksum-mismatch`,
   `image-too-large`). IF one of these checks fails THEN nothing SHALL be written to the
   board.
3. The command SHALL accept `--port P`, `--settings FILE` and `--wait SECONDS`. It SHALL
   install `build/firmware/out/odrig-firmware.bin` and no other image.
4. WHEN the board's storage held no settings file of WLED, or a `/cfg.json` without an
   `ap` object, before the command THEN the settings SHALL be applied all the same, as
   Requirement 4 criterion 4 defines.
5. `docs/firmware.md` SHALL give `install-firmware` as the command that puts the firmware
   on a board from scratch, in its section "From nothing to a playing board".

## Requirement 7: A program establishes over USB that the network is up

**User Story:** As a maintainer who cannot join the board's network from this Mac, I want a
program to find out over the USB cable that the board hosts the network under the new name
and with a password, so that the owner is asked only for what needs a person.

### Acceptance Criteria

1. WHEN the settings have been applied and the board has restarted THEN the board SHALL
   host a network with the name, protected by the password, opened as WLED opens it: with
   no network to join configured, about two seconds after the firmware has started, at the
   address `4.3.2.1`.
2. The probe build's report SHALL have, beside `ap`, the members `ap_name`, the name in the
   configuration the chip's radio holds for its access point, and `ap_auth`, the number of
   that configuration's protection: 0 for a network without a password and 3 for WPA2 with
   a password. WHILE `ap` is 0 both SHALL be `null`.
3. The probe build SHALL only read that configuration. No code of the usermod, in either
   build, SHALL set a Wi-Fi setting or name a Wi-Fi function or a Wi-Fi variable of WLED
   other than `apActive`. The firmware SHALL have no code for these members, and `status`
   and the commands of `docs/commands.md` SHALL stay as they are.
4. A board test SHALL establish, with the probe build and without joining the network:
   after the settings of a settings file made for the test were applied, and again after
   those of the settings file were applied, the report has `ap` 1, `ap_name` equal to the
   name and `ap_auth` 3 within 30 seconds of the board's reply to `status`, and storage
   read back from the board holds that name and that password.
5. No tool and no test SHALL join this Mac to the board's network or change the Mac's
   network settings.

## Requirement 8: Tests that need the board are kept apart

**User Story:** As a contributor without the board on the desk, I want everything about the
name and the password that a program can check without the board to run with the tests that
need none.

### Acceptance Criteria

1. `python3 firmware/fw.py test` SHALL run, in `tests/firmware/` and without a board: the
   checks of Requirement 2 on settings files the tests make; the settings file against
   Requirement 1; the editing of Requirement 4 on storage images the tests make with
   littlefs-python, among them one with the files the board holds today, a `/cfg.json`
   with LED settings only and no `/wsec.json`, and one with the files WLED writes when it
   saves its settings; the esptool calls of `set-wifi` and `install-firmware`, with the
   stand-in for esptool; and Requirement 5, with a password that is a text found nowhere
   else.
2. `python3 firmware/fw.py test-board` SHALL run, in `tests/board/`, the tests of this seed
   that need the board: Requirement 7 criterion 4, and `install-firmware`. There SHALL be
   no more of them than these two need.
3. `python3 firmware/fw.py test-air --http ADDRESS` SHALL run, in `tests/air/`, one test
   file of this seed for a person who has joined the network: WLED's own output of its
   settings names the network as the settings file does, `/cfg.json` as WLED serves it
   holds no password, and `/wsec.json` is not served.
4. Each of the three commands SHALL find these tests by discovery in its folder, as the
   seed 04 requirements define.
5. A board test that applies other values than those of the settings file SHALL use a name
   that begins with `odrig-test` and a password made in that run and kept nowhere, and
   SHALL apply the settings file again before it ends.
6. The board suite SHALL leave the board with the firmware, a valid show of brightness 40
   or less, and the name and the password of the settings file.

## Requirement 9: The network and how to change it are documented

**User Story:** As an operator or a newcomer, I want to read what the board's network is
called, where its password is and how both are changed, so that I need not read the code.

### Acceptance Criteria

1. `docs/wifi.md` SHALL describe the network as it is: its name; that it is protected with
   WPA2 and the password of the settings file; where that file is; that the file is the
   only place in the repository that holds the password, and that whoever can read the
   repository can read it; the board's address; when WLED opens the network; and how many
   devices can be joined at once, as read in the source, with what was not tested.
2. `docs/wifi.md` SHALL say how the name and the password are changed: edit the settings
   file, run `set-wifi` for every board over USB, commit the file; the limits of
   Requirement 2; and that every phone must be given the new password.
3. `docs/wifi.md` SHALL say what else changes them or undoes them: WLED's own Wi-Fi
   settings page, WLED's button held for more than five seconds, and that `flash` and
   `restore-stock` keep them.
4. `docs/wifi.md` SHALL no longer list the access point's name and password as undecided
   and SHALL no longer say that the access point has WLED's defaults.
5. `docs/wifi.md` SHALL give the owner's check of this seed as steps that name what to do
   and what must be seen.
6. `docs/firmware.md` SHALL describe `set-wifi` and `install-firmware`, each with an
   example and every option, the new reasons, the two new members of the probe build's
   report, and `set-wifi` among the commands that write storage.

## Requirement 10: The settings are accepted on the real board

**User Story:** As the owner of the installation, I want every item of the seed's
definition of done checked on the board, and to know which of them a person checked.

### Acceptance Criteria

1. The tool SHALL refuse a password of 7 characters, a password of 64 characters and a name
   of 33 characters, each before it touches the board.
2. On the board, after the settings were applied, the board SHALL report over USB that its
   network is up under the name `odrig`, and its stored settings, read back, SHALL show
   that name and the password of the settings file.
3. Owner's check: with a phone or a computer the owner SHALL join the network `odrig` with
   the password of the settings file and SHALL send one command of `docs/commands.md` over
   HTTP, which the board answers.
4. The seed SHALL be completed only when the owner's check is done.
