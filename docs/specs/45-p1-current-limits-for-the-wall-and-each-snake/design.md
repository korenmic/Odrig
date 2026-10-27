# Design: current limits for the wall and each snake

Requirements: [requirements.md](requirements.md). Seed:
`project-seeds/45-p1-current-limits-for-the-wall-and-each-snake/seed.md`.

## The Python reference, `odrig/limits.py`

One module states the rule once for the tests and the tools:

- `estimate(data)`: floor(sum × 55 / 765) + len(data) // 3.
- `fade(data, level)`: the video fade of requirement 1.4 over a leg's bytes.
- `level(data, budget)`: requirement 1.3, the halving over 1 to 254 with all eight fades
  (start 1..254, keep the best level whose faded estimate is within the budget).
- `limit(legs, budgets, wall)`: requirement 1.5 over a list of leg byte strings, giving
  the bytes sent, each leg's estimate and `limited`, the wall's estimate and `limited`.
- `loads(data)` / `read(path)`: the strict reader of `limits.json` of requirement 2.2,
  raising `errors.Rejection` with `limits-malformed`; `dumps(wall, legs)`: the writer's
  bytes, for the tests and the tool.

`errors.py` gains `LIMITS_MALFORMED = "limits-malformed"`; `docs/python-library.md` names
the module. The module is the reference the core's suite and the reference player use.

## The core

**Data.** `LegInfo` gains `uint16_t budget` and `uint8_t limited` (16 bytes, +4 a leg).
`Core` gains `uint32_t wall_budget; uint32_t wall_default; uint8_t wall_limited; uint8_t
limits_saved; uint8_t limits_present;`, `present` when a `limits.json` exists, readable or
not. The estimates are not kept: `limits` makes them from `led_data`.

**The host's default.** `odrig_host` gains, at its end, `uint32_t (*limit_default)(void
*ctx)`: "Optional: the wall's budget in mA while no budgets are saved; NULL, or 0, is no
limit." `odrig_core_begin` reads it once, before `start()`, into `wall_default`.

**`core/src/limits.cpp`, `limits.h`.**
- `limits_apply(Core&)`: called in `player_poll` after the bytes are written, fill or
  dark, and after the clear of a show that turned invalid; not on a refresh that keeps the
  picture before. It runs requirement 1.5 over `led_data` leg by leg (`legs[i].first`,
  `count`): `leg_estimate`, `leg_level` (halving: lo 1, hi 254, a probe sums the faded
  bytes without writing them), `leg_fade`; then the wall's level by the same halving over
  all legs; then the third pass. It sets `legs[i].limited` and `wall_limited`.
- `limits_read(Core&)`: at the start, right after the mapping is read, whatever its
  result, before `start()`'s early return for a mapping that cannot be used:
  `core.file.open("limits.json")`, so that a start opens `mapping.json` twice and then
  `limits.json`; missing: defaults, `present` 0; read with `JsonReader`
  by the members' bits as the mapping is; a broken file: defaults, `present` 1, the log
  line `limits unreadable`. A leg number the mapping lacks is skipped; a leg the file does
  not name stays 0.
- `limits_reply(Core&, from, Reply&)`: the reply of requirement 3.1, the tail's size worked
  out first and each leg written only while it fits, as `order_get` does.
- `limits_set_wall`, `limits_set_leg`, `limits_default`: the refusals after the parser's
  (show-invalid, the leg lacking, busy), then the save. `limits_save` writes `limits.part`
  with a writer over `core.chunk` like `MappingWriter`: the head, the mapping legs above 0,
  then, when an old readable file is present, its legs the mapping lacks, read through
  `checker->file.open_at` after `drive_check_yields`, as `order move` copies the old order;
  then `write_close` and the rename, removing the part on any failure. `limits_default`
  removes `limits.json` when `present`, and sets the defaults.
- `storage_clear_parts` removes `limits.part` by the probe-then-remove of `mapping.part`,
  so that the `--cut-at` numbering of the existing tests does not move.

**Commands.** `commands.cpp`: `words.is(0, "limits")` with the forms of requirement 3;
the catalog rebuild's `busy` in the parser, as for `mapping set`. `docs/commands.md`:
rows `` `limits`, `limits <from>` ``, `` `limits wall <mA>` ``, `` `limits snake <n> <mA>` ``,
`` `limits default` ``, and a section "Current limits". The first word `limits` joins the
pinned lists of the docs tests and `agent/vocabulary.md`; the second words `wall`,
`snake`, `default` join `tests/core/test_docs.py`'s set.

**Memory.** `LegInfo` +4 a leg and `Core` about +12: the target with a drive goes from
130,509 to about 130,600 bytes of 131,072. `tests/core/test_memory.py` (`20 * 16`),
`docs/core.md`'s memory table and totals, and the drive figure follow.

**The test host.** `--limit-default MA` sets the member; without it NULL. `check_name`
accepts `limits.json` and `limits.part`. `docs/core.md` documents the option and the
member. The member joins the pinned list of `tests/core/test_docs.py` and the layout
program and member order of `tests/emulator/test_binding.py`; `odrig_files.cpp` must set
`made.limit_default = nullptr`, since its record is not zeroed.

**The reference player.** `tests/core/support.py` applies `odrig.limits.limit` after the
brightness, with the budgets of the show folder's `limits.json` and the host's default it
is given; without either nothing changes, so every existing comparison stands.

## The firmware

- `firmware/usermod/odrig_limit_default.h`: `inline uint32_t odrigWallDefault(uint32_t
  maximum)`, 0 → 0, 1 to 120 → 1, else maximum − 120; includes only `stdint.h`; tested by
  `tests/firmware/test_usermod_limit_default.py` with a small program as `kept` is.
- `odrig_usermod.cpp` setup: before `odrig_core_begin`, `wallDefault =
  odrigWallDefault(BusManager::ablMilliampsMax())` and `host.limit_default =
  wallDefaultOf`. `odrig_files.cpp` sets `limit_default = nullptr` in the shared record.
- `odrig_leds.cpp`: `switchWledLimiterOff()`: when `BusManager::_useABL` is true, set it
  false and call `applyBriLimit(255)` on every digital output, so that no output keeps a
  level of WLED's limiter; called at the top of `fill()` and `show()`, after
  `finalizeInit()` in `apply()`, and in `dark()`. `describeOutputs()` keeps its share and
  55 mA. `test_usermod_files.py`'s pins of fill and show still hold; the comment of
  `odrig_leds.h` on `show()` follows.
- The probe's code stays. `tests/board/test_limit.py` and `test_probe.py`'s target test
  follow requirement 4.3; `docs/firmware.md`: the limiter section, the WLED-changes table,
  the probe table, the example line and the read-back paragraph, owner's checks 5 and 6.
- The standalone limiter goes (requirement 4.4); `tests/firmware/host/host.cpp` keeps the
  `settings` mode.

## The firmware tool

`storage.py`: `LIMITS_NAME = "limits.json"`, accepted by the folder check. `cli.py`
`install-show` gains `--limits`: before the board is touched, `limits-missing` when the
folder lacks the file and `limits-malformed` when `odrig.limits.loads` refuses it; beside
the carrying of `order.txt`, without `--limits` the folder's `limits.json` is dropped from
the files and the board's, when present, carried in. `read-show` needs nothing. The usage
line, the error table and the install-show section of `docs/firmware.md` follow.

## The emulator and the command tool

The binding's `HostRecord` gains `limit_default`, NULL: no limit. The show folder keeps
`limits.json` through `FolderHost` as it does every file. `odrigctl`: `COMMANDS["limits"]
= ("[OPERATION]",)`, the forms checked in `checked()`, and `limits` alone followed through
`content.list_all(session, _print, b"limits")`. `docs/emulator.md`: the command tool's
synopses and examples, the Controller view's lines, the show folder's file.

## The app

`app/www/screens/limits.js`, started and shown from `main.js` beside the mapping's:
`latest` the merged reply of all parts, `saving`, `none` for an installation without
`limits`, `fieldState` per field (focus, dirty). `commands.js`: `limits(from)` validates
the reply; `limitsWall(mA)`, `limitsSnake(n, mA)`. `client.js`: `limitsRead()` loops the
parts inside one `requestOperation("limits", ...)`, as `readFile` does, and the two sets.
`index.html`: `<div id="limits" class="panel">` after `#mapping`, with `#limits-summary`
(status), `#limits-error` (alert), the explanation, `#limits-wall` and `#limits-rows`.
Fields are `type="text" inputmode="numeric"`, saved on `change`. `style.css` for the rows.
The app sends `limits`, `limits <next>`, `limits wall <mA>`, `limits snake <n> <mA>`:
thirty-eight lines. `docs/android-app.md`: the table, the Settings bullet, a paragraph
"Current limits", the verified bullet.

## Tests

- `tests/converter/test_limits.py`: the reference's arithmetic on worked cases (full white
  at 500 mA → level 7, 451 mA; WLED's level would leave 684), the file's reading and
  refusals.
- `tests/core/test_limits.py`: random pictures against `odrig.limits.limit`; defaults with
  `--limit-default 730` and without; the file's strict reading and the log line; the save
  and its atomicity, `--store-fails-at`, `--cut-at` at every step; the commands, paging,
  refusals in order; a budget kept with its snake after `mapping set` and `mapping cross`.
- The emulator's suite: LEDs limited with a saved `limits.json`; the command tool's forms;
  the binding's member.
- The firmware suite: the default header; `install-show --limits` and its refusals;
  `read-show` keeping the file.
- The app's suite: `tests/app/test_limits.py` with a scenario: the panel, saving, a
  refusal, focus kept, an older installation.
