# The LED current limit as a setting

## Summary

Set the limit on LED current that the firmware applies from a tracked value, with the
firmware tool, and allow it to be switched off. Today it is WLED's default of 850 mA, and
with that the target installation shows nothing.

## Priority

- `P1`

## Depends On

- Seed 04, for the firmware and the firmware tool.
- Seed 08, for the way the firmware tool changes WLED's stored settings on the board.

## Product Context

WLED estimates the current that a picture draws and dims the picture until the estimate
is under a maximum. The maximum is one of WLED's LED settings and is 850 mA unless it was
changed. Our firmware leaves this limiter active and does not change the maximum.

For the target this is wrong. Its 3,600 LEDs are counted as 3,600 mA at rest alone, so
with a maximum of 850 mA the limiter holds every LED at its lowest level, whatever plays.
The same holds for every mapping of 730 LEDs or more. The maximum can be changed in
WLED's web interface, by hand, on each board, and nothing in the repository records it.

The owner ruled on 2026-10-12: switch the limiter off if that puts no hardware at risk.

- With the LEDs fed from the power supply, as the installation will be, no LED current
  passes through the board. Switching the limiter off puts nothing of the board at risk
  there.
- On the bench today, one strip of 60 LEDs is fed from the board's 3.3 V pin. A command
  can raise the brightness to 255, and the limiter is then what keeps the strip from
  asking the board for more than it can give. There the limiter stays on.

So the limit is a setting: 850 mA while a strip is fed from the board, and switched off,
or set to what the supply gives, when the LEDs have their own supply. Which of the two it
is on a given day is the owner's to say. It is about power.

## Technical Constraints

- The limit lives in one tracked settings file and nowhere else in the repository. It is
  one whole number of milliamps for all LEDs together; 0 means no limit.
- The tracked value is 850 until the owner changes it.
- The setting is applied over USB with the firmware tool, the way seed 08 applies the
  network's name and password. WLED's other settings and its web interface are not
  changed.
- The tool refuses a value that is not a whole number from 0 to 65,535 before it touches
  the board.
- The standalone firmware of seed 12 takes its limit from the same tracked value.
- Tests that need the board are kept apart from those that do not. On the board,
  brightness stays at 40 or less, whatever the limit is.

## Required Behavior

1. A tracked settings file holds the limit in milliamps.
2. One command of the firmware tool writes the limit into the board's settings and
   restarts the board. It says in one line what the limit now is, and for 0 that the
   limiter is off.
3. The same setting is applied whenever the firmware tool installs the firmware on a
   board from scratch.
4. After the restart the limiter works with that maximum, and with 0 it never dims.
5. The firmware tool reports the limit that is stored on the board.
6. `docs/firmware.md` describes the setting, what each value means for the bench and for
   the installation, and that the value for the installation is the owner's to set.

## Definition Of Done

1. The tool refuses -1, 65,536, 1.5 and a text, and accepts 0 and 850.
2. On the board, after the limit was set to 0 and the target mapping installed, the
   firmware's own report shows that no refresh was dimmed while Hello world for 60 x 60
   plays at brightness 40, where with 850 every refresh is dimmed.
3. On the board, reading the stored settings back shows the value that was set, for 0 and
   for 850.
4. Afterwards the board is left with the limit at 850, running the two-leg bench show,
   autostarting, at brightness 40 or less.

## Open Questions

None. Use the resolved behavior in this seed.
