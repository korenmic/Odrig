# Standalone firmware as a fallback

## Summary

A second firmware for the board that does not use WLED: a small program that hosts the same
shared core, drives the same twenty outputs and accepts the same commands. It exists so that
on the day of the event there is a tested alternative if the WLED-based firmware misbehaves.

## Priority

- `P2`

## Depends On

- Seeds 02, 04 and 05, for the shared core, the firmware tool and the twenty outputs.
- Seed 07, so that both firmwares are built against the same command list.

## Product Context

The firmware in use is WLED 16.0.1 with a patch that raises its outputs from twelve to
twenty, plus our player. It works and is measured. It also carries a large program we do not
control, and one patch that has to keep applying.

The owner wants more than one way to run the installation, prepared and tested ahead of
time, so that a problem found late does not mean developing a replacement from nothing.

The player is not tied to WLED. The shared core does the decoding, the mapping, the show,
the timing and the commands, and a host only supplies time, files, a way to carry command
lines, and LED outputs. WLED is one such host. A second host can be much smaller.

The LED library that WLED uses can be used without WLED. Its sixteen-line parallel output
and its four single outputs are the ones already proven on this board.

## Technical Constraints

- The shared core's source files are used unchanged, the same files the emulator and the
  WLED-based firmware use.
- The same installed file set and the same commands and replies, over USB serial and over
  HTTP on the board's own Wi-Fi network, as `docs/commands.md` and `docs/show.md` define.
- The same storage layout as the WLED-based firmware, so a board can be switched from one
  firmware to the other without reinstalling its show.
- Twenty outputs as `mapping/legs-20.json` names them.
- Built, flashed and rolled back with the existing firmware tool, with the same safety rules.
- It has no web page and no settings interface. What WLED's interface offers is given up.
- The network's name and password come from the same tracked settings file the WLED-based
  firmware uses.
- A limit on total LED current is kept, set from a tracked value, because nothing else
  protects the wiring from a full-white picture.
- Tests that need the board are kept apart from those that do not. On the board, brightness
  stays at 40 or less.

## Required Behavior

1. One command of the firmware tool builds the standalone firmware and one flashes it. The
   existing commands for the WLED-based firmware keep working.
2. At start it loads the installed show, sets one output per leg from `mapping.json`, plays
   the start item, and hosts the Wi-Fi network.
3. It accepts every command in `docs/commands.md` over USB serial and over HTTP, with the
   same replies as the WLED-based firmware.
4. The board tests that the WLED-based firmware passes are run against it, and it passes the
   ones that do not depend on WLED itself.
5. `docs/firmware.md` describes both firmwares, how to switch between them, and what each
   one offers that the other does not.

## Definition Of Done

1. On the board: the bench show autostarts, `status` reports a rate between 20 and 50, and
   the command tool gives the same replies as with the WLED-based firmware.
2. On the board: twenty outputs each carry a full 180-LED signal with the target mapping,
   and the refresh rate with the demo show and with a dense 60 x 60 animation is measured and
   reported beside the WLED-based firmware's figures.
3. Switching the board from one firmware to the other and back keeps the installed show.
4. Afterwards the board is left on the WLED-based firmware with the bench show.

## Open Questions

None. Use the resolved behavior in this seed.
