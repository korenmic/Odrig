# Design

## The emulator

- `emulator/binding.py`: `wiring_saves`, its comment, and the two places that count
  successful `mapping cross` replies go. `_refresh_legs()` after a successful `mapping set`
  stays.
- `emulator/engine.py`: `routing()` gives the core's legs alone; `line()` and `feed()` keep
  comparing it before and after a command and call `hub.mapping` when it changed.

## The command tool

- `odrigctl/cli.py`, `mapping`: a form is valid when it is `get`, `test on`, `test off`,
  `set REV PINS` or `test snake N`. The usage error says `mapping takes get, set REV PINS,
  test on|off, or test snake N`.

## Tests

- `tests/emulator`: the binding has no `wiring_saves`; the engine's routing is its legs;
  `mapping cross on` over TCP and HTTP answers `bad-argument`, leaves the folder's files and
  `mapping get` as they were, and sends the page no mapping; `mapping set` still does.
- `tests/mapping/test_hosts.py`: the forms of `MappingCli` without `cross`, and `mapping cross
  on|off` a usage error with status 2 and nothing sent.
- `tests/mapping/test_retired_cross.py` stays: the core's refusal.

## The audit

`rg -i "cross"` over `app/`, `emulator/web/`, `core/`, `firmware/` and `odrigctl/`, the
results that are not the photo reading, the emulator's drawing of lines that cross, the
cross-platform builds or packages named `cross-*`, written into the drift with what was
removed.
