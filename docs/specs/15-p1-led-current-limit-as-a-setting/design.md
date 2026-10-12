# Design: the LED current limit as a setting

## Overview

The limit is one number in WLED's stored settings, `hw.led.maxpwr` of `/cfg.json`. Seed 08
built everything needed to change a member of that file on a board: the storage image is
mounted, the file is edited as JSON with every other member in its place, the new image
is checked, the changed blocks are written and compared. This design adds a second
setting to that way:

- `firmware/limit.json`, the tracked limit file;
- `firmware/fwtool/limit.py`, which reads a limit file and edits the limit in a storage
  image;
- the commands `set-limit` and `read-limit`, and the limit in `install-firmware`;
- one correction in the probe build, which counted every send as dimmed when the limiter
  is off.

The firmware is not changed.

## What was read

In WLED's source at the pinned commit, in the work folder's checkout, and in
`firmware/usermod/`.

| | Fact | Where |
|---|---|---|
| L1 | `deserializeConfig()` takes `hw.led.maxpwr` as the global maximum, a 16-bit number, and keeps the one it has when the member is absent. That one is 850 at first. | `wled00/cfg.cpp`, `wled00/const.h` |
| L2 | The usermod makes its outputs from the mapping and gives each a share of the global maximum in proportion to its LEDs, and 55 mA for one LED. It never sets the global maximum. | `firmware/usermod/odrig_leds.cpp`, `describeOutputs` |
| L3 | With a global maximum above 0 the limiter is in use when an output has an LED current above 0. With a global maximum of 0 it is in use only when an output has a maximum of its own above 0; the usermod's outputs then have 0, so the limiter is not in use, nothing is dimmed, and WLED's estimate stays 0. | `wled00/bus_manager.cpp`, `initializeABL` and `applyABL` |
| L4 | With a maximum from 1 to 120 the limiter allows 1 mA and holds every LED at its lowest level. | `wled00/bus_manager.cpp`, `applyABL` |
| L5 | The probe build reports `limit_ma` as the maximum less 120, or 0 when the maximum is 120 or less, and counts a send in `limited` when the estimate is at or above that. With the limiter off both are 0, so it counts every send. | `firmware/usermod/odrig_probe.cpp` |
| L6 | WLED writes `hw.led.maxpwr` when it saves its settings, and its LED settings page changes it. | `wled00/cfg.cpp`, `wled00/set.cpp` |

Assumed, and tried on the board in task 4: that WLED on the board takes the edited
`hw.led.maxpwr` at its start, as it took the edited `ap` in seed 08, and that with 0 the
probe report shows no dimming.

## The limit file

`firmware/limit.json`:

```json
{
  "milliamps": 850
}
```

Read with `odrig.strictjson.loads`, as the settings file of seed 08 is. `limit.read(path)`
returns the number:

1. The path is not a file: `limit-settings-missing`.
2. Not one JSON value, a member named twice, not an object, another member than
   `milliamps`, or `milliamps` not a number written as an integer:
   `limit-settings-malformed`. `1.5` and `"850"` are refused here.
3. Below 0 or above 65,535: `limit-invalid`, with the number in the detail.

## WLED's settings files, shared (`wledfiles.py`)

What `wifi.py` has for reading and writing one of WLED's settings files moves to
`firmware/fwtool/wledfiles.py` and is used by both modules: the names of the two files,
`object_of(files, path)`, which gives the object of a file, the empty object for an
absent one, and `wled-settings-malformed` for what is no object, and `text_of(value)`,
JSON without spaces. `wifi.py` behaves as before; its tests are not changed.

## Editing the limit (`limit.apply`, `limit.stored`)

`apply(image, milliamps)` returns the image with `hw.led.maxpwr` of `/cfg.json` set, or
the image itself when it holds that number already.

1. Mount, read every file, take the object of `/cfg.json`.
2. `hw` and `hw.led`: when there, each must be an object, else
   `wled-settings-malformed`; when absent, added as the last member of its parent.
3. `maxpwr` gets the number. A member that is there keeps its place.
4. A file that would not change keeps its bytes, and the image is returned as it is.
5. Written as `text_of`, unmounted; no room is `no-space`.
6. Checked before it is returned, each failure `verify-failed`: the geometry is the old
   one; every other file has its bytes; `stored(new)` is the number; and `/cfg.json`
   without `hw.led.maxpwr` is what it was without it, the order of the members included.
   A `hw.led` or `hw` left empty by this counts as absent.

`stored(image)` gives `hw.led.maxpwr` of `/cfg.json` when it is a whole number, and
`None` otherwise or when the file cannot be read.

The outputs of `hw.led.ins` are left alone: the usermod replaces them at every start
(L2), and their own `maxpwr` is not what the limiter then uses.

## The commands

```
python3 firmware/fw.py set-limit [--port P] [--settings FILE] [--wait SECONDS]
python3 firmware/fw.py read-limit [--port P]
python3 firmware/fw.py install-firmware [--port P] [--settings FILE] [--limit FILE] [--wait SECONDS]
```

`set-limit`: read the limit file; find the port; `storage_of`; `write_storage` with
`limit.apply`; wait for `status`; print the line of the limit and the reply. Status 0.

`read-limit`: find the port; `storage_of`; `limit.stored`; restart the board; print the
line. It writes nothing.

`install-firmware` reads the limit file after the settings file, both before the board
is touched, and makes its one new storage image with `wifi.apply` and then `limit.apply`.
It prints `name: <name>`, `password: set`, the line of the limit, and the reply.

The line of the limit is `limit: <N> mA`, `limit: off` for 0, and for `read-limit` on a
board without the member `limit: not stored; WLED uses 850 mA`.

New reasons: `limit-settings-missing`, `limit-settings-malformed`, `limit-invalid`.

## The probe build

`odrig_probe.cpp` counts a send in `limited` only while the global maximum is above 0.
`limit_ma` and `used_ma` are 0 while it is 0, as today. Nothing else changes, and the
firmware has none of this code: its image keeps its SHA-256.

## What a value means

| Limit | The bench: one strip fed from the board's 3.3 V pin | The installation: LEDs fed from the supply |
|---|---|---|
| 850 | The limiter is what keeps a `brightness 255` on a white picture from asking the pin for more than it gives. This is the tracked value. | Every LED is held at its lowest level: 3,600 LEDs count as 3,600 mA at rest. Useless. |
| What the supply gives | Not for the bench. | The limiter dims a picture that would ask the supply for more. |
| 0 | Not for the bench: nothing protects the pin then. | Nothing is dimmed. No LED current passes through the board, so the board is not at risk; what the supply and the wiring bear is the owner's matter. |

The value for the installation is the owner's. The tool refuses nothing inside 0 to
65,535.

## Tests

`tests/firmware/`, no board:

- `test_limit_settings.py`: the limits and every malformed form; each refusal through
  `set-limit --settings` and `install-firmware --limit` inside
  `support.untouched_board()`; the limit file is accepted and holds 850.
- `test_limit_storage.py`: on the bench board's files and on what WLED saved: only
  `hw.led.maxpwr` differs; a missing `hw`, a missing `hw.led` and a missing `/cfg.json`;
  the same value again gives the same image; 0, 850 and 65,535; the malformed forms;
  `stored` for each.
- `test_limit_commands.py`: with the stand-in for esptool: the calls of `set-limit` and
  its two lines; a second run writes nothing; `read-limit` reads, restarts and writes
  nothing, with its three forms of line; `install-firmware` makes one storage write that
  holds the name, the password and the limit, and prints four lines.
- `test_wifi_commands.py`, `test_wifi_settings.py`: `install-firmware` prints four lines.
- `test_usermod_files.py`: `limited` is counted only with a maximum above 0.
- `test_docs.py`, `test_cli.py`: the two commands, their options and reasons.

`tests/board/test_limit.py`, with the probe build and Hello world for the target mapping
at brightness 40:

1. `set-limit --settings` with a file of 0: two lines, `limit: off`. Over five seconds
   every report has `limited` 0, `limit_ma` 0 and sends. `read-limit` prints `limit: off`
   and storage read back holds 0.
2. `set-limit` with the limit file: `limit: 850 mA`. Over five seconds every report has
   `limited` above 0 and `limit_ma` 730. `read-limit` prints `limit: 850 mA` and storage
   read back holds 850.

`tests/board/support.py`: `leave_the_board()` also applies the limit file when storage
does not hold its value, and the suite's last step asks storage for it.

## Documents

`docs/firmware.md`: the two commands in the list, each with a section and an example;
`--limit` under `install-firmware`; the three reasons; the regions table; "The current
limiter stays active" says where the maximum comes from and has the table above; the
probe table says when `limited` counts; "Verified on the board" has what task 4 found.
`docs/decisions.md`: a line in the change log. `AGENTS.md`: seed 15 leaves "What is
coming".

## Risks

- **A limit of 0 on the bench.** The board test sets it for a minute, with a show of
  brightness 40 and no command that raises the brightness, and sets 850 again before it
  ends. A run stopped in between leaves 0: `python3 firmware/fw.py set-limit` puts 850
  back, and the suite's last step does it too.
- **WLED's LED settings page** changes the number (L6). `set-limit` puts the file's back.
- **Seed 08's promise of three lines** from `install-firmware` becomes four.
