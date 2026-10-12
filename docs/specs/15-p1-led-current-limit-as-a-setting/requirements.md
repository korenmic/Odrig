# Requirements: the LED current limit as a setting

Seed: [`project-seeds/15-p1-led-current-limit-as-a-setting/seed.md`](../../../project-seeds/15-p1-led-current-limit-as-a-setting/seed.md).

WLED estimates the current of every refresh and dims it until the estimate is under a
maximum, 850 mA unless it was changed. The firmware leaves that limiter on and never sets
the maximum. With the 3,600 LEDs of the target, 850 mA holds every LED at its lowest
level. This spec makes the maximum a tracked value that the firmware tool puts on a
board, as seed 08 did for the network's name and password.

In this document:

- "the limit" is the maximum in milliamps for all LEDs together; 0 means that the limiter
  is off;
- "the limit file" is `firmware/limit.json`;
- "WLED's stored settings" are the files of the board's storage that WLED reads; the
  limit is `hw.led.maxpwr` of `/cfg.json`.

## Requirement 1: one tracked file holds the limit

**User story.** As the owner, I want the limit in one file of the repository, so that
there is one place to read it and one place to change it.

1. The limit file SHALL be `firmware/limit.json`: a UTF-8 JSON object with exactly one
   member, `milliamps`, a whole number.
2. The tracked value SHALL be 850 until the owner changes it.
3. A limit SHALL be accepted only when it is a whole number from 0 to 65,535, written
   without a fraction and without an exponent.
4. IF the file is not there THEN the tool SHALL refuse with `limit-settings-missing`. IF
   it is not such an object THEN with `limit-settings-malformed`. IF the number is
   outside 0 to 65,535 THEN with `limit-invalid`.
5. In each of these cases the tool SHALL end with status 1 and one error line, and SHALL
   NOT have looked for the port or started esptool.
6. -1, 65,536, 1.5 and a text SHALL each be refused. 0 and 850 SHALL each be accepted.

## Requirement 2: one command puts the limit on a board

**User story.** As the person who prepares a board, I want one command that gives the
board the limit of the limit file.

1. WHEN `python3 firmware/fw.py set-limit` is run THEN the tool SHALL set `hw.led.maxpwr`
   of `/cfg.json` in the board's storage to the limit, check what was written, restart
   the board, and wait for the reply to `status`.
2. On success it SHALL print two lines, `limit: <N> mA`, or `limit: off` for 0, and the
   board's reply to `status`, and end with status 0.
3. The command SHALL accept `--port P`, `--settings FILE` for another limit file, and
   `--wait SECONDS`.
4. The tool SHALL change storage the way `set-wifi` does: only the blocks that differ are
   written, and the chip compares the whole partition with the new image.
5. Every other member of `/cfg.json` SHALL keep its value and its place, and every other
   file of storage its bytes. A `hw` or a `hw.led` object that is missing SHALL be added.
6. WHEN storage already holds the limit THEN nothing SHALL be written, the board SHALL be
   restarted, and the same lines printed.
7. IF `/cfg.json` is not a JSON object, or its `hw` or `hw.led` is there and is not an
   object, THEN the tool SHALL refuse with `wled-settings-malformed` and write nothing.

## Requirement 3: the tool reports the limit a board has

1. WHEN `python3 firmware/fw.py read-limit` is run THEN the tool SHALL read the board's
   storage, print one line, and restart the board.
2. The line SHALL be `limit: <N> mA`, `limit: off` for 0, or
   `limit: not stored; WLED uses 850 mA` when `/cfg.json` holds no `hw.led.maxpwr`.

## Requirement 4: a board from scratch gets the limit

1. WHEN `python3 firmware/fw.py install-firmware` is run THEN it SHALL also put the limit
   of the limit file into storage, in the same write as the name and the password, and
   SHALL print the line of the limit after `password: set`.
2. The limit file SHALL be read and checked before the board is touched. `--limit FILE`
   SHALL read another limit file.

## Requirement 5: the limiter follows the limit

1. WHEN the limit is above 0 THEN WLED's limiter SHALL work with it as its maximum.
2. WHEN the limit is 0 THEN no refresh SHALL be dimmed.
3. The probe build SHALL count a send as dimmed only while the limiter is on, and SHALL
   report `limit_ma` 0 and `used_ma` 0 while it is off.
4. The firmware SHALL NOT change: no code outside the probe build's is touched.

## Requirement 6: shown on the board

1. WHEN the limit is 0 and Hello world for the target mapping plays at brightness 40 THEN
   the probe report SHALL show no dimmed send over five seconds.
2. WHEN the limit is 850 with the same show THEN every report SHALL show dimmed sends.
3. WHEN storage is read back THEN it SHALL hold the value that was set, for 0 and for
   850.
4. The board suite SHALL leave the board with the limit of the limit file, and every
   show it installs SHALL have a brightness of 40 or less, whatever the limit is.

## Requirement 7: the documents

1. `docs/firmware.md` SHALL describe `set-limit` and `read-limit`, the limit file, the
   new reasons, and what a value means for the bench and for the installation.
2. It SHALL say that the value for the installation is the owner's to set, and that the
   limit stays 850 while a strip is fed from the board.
3. `AGENTS.md` SHALL no longer list seed 15 as coming.
