# The board's Wi-Fi name and password

## Summary

Give the board's own Wi-Fi network the project's name and a password that only the operators
know, set from a tracked settings file by the firmware tool.

## Priority

- `P1`

## Depends On

- Seed 04, for the firmware tool and the way it writes to the board's storage.

## Product Context

The board hosts the Wi-Fi network that operators' phones join. Today that network has WLED's
default name and WLED's default password, which is public knowledge. Anyone at the event
could join it and send commands.

The owner wants a password that only operators know, and allows it to be kept in this
repository.

The owner wants WLED's own web interface left reachable and unchanged for now.

## Technical Constraints

- The name and the password live in one tracked settings file and nowhere else in the
  repository.
- A Wi-Fi password is 8 to 63 characters. A name is 1 to 32 characters. The tool refuses
  values outside these limits before touching the board.
- The settings are applied over USB with the firmware tool, the way a show is installed.
- WLED's other Wi-Fi settings and its web interface are not changed.
- The password is never printed by the tool or written to a log.
- Tests that need the board are kept apart from those that do not.

## Required Behavior

1. A tracked settings file holds the network name and password. The name is `odrig`.
2. One command of the firmware tool writes the name and password into the board's settings
   and restarts the board.
3. The same settings are applied whenever the firmware tool installs the firmware on a board
   from scratch.
4. After the restart, the board hosts a network with that name, protected by that password.
5. `docs/wifi.md` describes the network and how to change its name and password.

## Definition Of Done

1. The tool refuses a password of 7 characters and one of 64, and a name of 33 characters.
2. On the board, after applying the settings, the board reports over USB that its network is
   up under the name `odrig`, and reading its stored settings back shows that name and that
   a password is set.
3. The owner joins the network with the password from a phone or computer and sends one
   command over HTTP.

## Open Questions

None. Use the resolved behavior in this seed.
