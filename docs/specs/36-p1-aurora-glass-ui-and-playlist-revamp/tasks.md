# Tasks: Aurora Glass UI and playlist revamp (seed 36)

Seeds 09, 17, 28, 29, 30 and 38 are in the code these tasks start from (the branch of seed
31's first task). Where the real code differs from what the design relies on, follow the
code and record the difference in `docs/drifts.md`. Tasks 1 to 8 need no board; task 9
needs the board, task 10 the owner's phone.

Rules for every task:

- One task is one commit, which ticks its checkbox here. Stage named paths only.
- Before each commit run the suites of the parts the task changed, and always
  `python3 -m unittest discover -s tests/onboarding -t .`: the core's with
  `make -C core test`, the emulator's, the mapping suite, the app's, the firmware's with
  `python3 firmware/fw.py test`, the converter's two. Task 8 runs every suite.
- "Prove it fails first": watch the new test fail on the code before, and put what was
  seen into the commit message.
- Code states what it does now; no comment about seeds, tasks or dates.
- The commands, the reply members and the error code are those of the design, approved
  in advance by the owner on 2026-10-24; each goes into `docs/commands.md` with the task
  that adds it.

- [x] 1. The saved order in the core, read side
  - Set the seed's `state.json` to `in_progress`.
  - `core/src/order.h/.cpp`: the file's reader, the keys block, `order_start`,
    `order_drive_found`, `order_drive_step`, `order_reload`, `order_key`, `order get`.
    `core/src/core_state.h`, `core/src/core.cpp` (the block, the startup read, the
    drive's count and its part of the check, `drive_check_yields`), `core/src/player.cpp`
    (`next_animation` and the two first-animation functions by key),
    `core/src/content.cpp` (`external` in `list`; the keys follow `content_take_out`),
    `core/src/storage.cpp` (`order.part` at startup; the reload after an upload adds an
    item), `core/src/commands.cpp` (`order get`), the test host's names.
  - Tests, `tests/core/test_order.py`: a hand-written `order.txt` orders the playlist,
    `play all`, wrapping and the start; unnamed animations after named ones; a malformed
    header and malformed lines; absent and returning card entries; a stale internal id
    taken by a new upload before and after a restart; ignored items keep their place;
    `order get` parts and revision; `external` on every animation item; memory.
  - Earlier tests updated for `external` and the block; docs/commands.md, docs/core.md,
    docs/show.md.
  - Prove it fails first: the playlist of a show with an `order.txt` plays in the show's
    order.
  - Requirements: 1.1 to 1.5, 1.10, 1.11, 2.1

- [x] 2. The saved order in the core, write side
  - `order move` in `core/src/order.cpp` and `core/src/commands.cpp`; `order-conflict` in
    the error table.
  - Tests: moves before an id and to the end, internal and external, with absent card
    entries kept; no-op moves write nothing; every refusal in its order; a stale revision;
    a power cut at every storage call and a failed call at each, recovered by a start; the
    turn in progress, power and brightness kept; the order after a restart.
  - docs/commands.md, docs/core.md, docs/reasons.md if it lists codes.
  - Prove it fails first: `order move` is refused with `bad-argument`.
  - Requirements: 1.6 to 1.9

- [x] 3. The snake tests in the core
  - `core/assets/mapping-snakes.json`, `core/snakes.py`, `core/src/snakes_data.h`,
    `core/src/mapping_control.cpp`, `core/src/commands.cpp`, `core/src/core_state.h`.
  - Tests, `tests/core/test_snakes.py`: each snake's 60 pixels through the default and a
    swapped mapping; `snake` in `mapping get`; switching tests keeps the saved selection;
    stop, `play` and restart; busy rules; no file changes; the asset check.
  - The mapping suite's `mapping get` replies gain `snake`. docs/commands.md, docs/core.md.
  - Prove it fails first: `mapping test snake 1` is refused with `bad-argument`.
  - Requirements: 3.1 to 3.4

- [x] 4. The routes and the command tool
  - `odrigctl/cli.py`: `order get [FROM]`, `order move REV ID BEFORE`,
    `mapping test snake N`.
  - Tests, `tests/emulator/test_order.py`: the three forms over HTTP, TCP and the serial
    port, through `odrigctl`, and the same replies as the core's.
  - docs/emulator.md, docs/firmware-additions.md, agent/vocabulary.md and the documents'
    command lists.
  - Requirements: 4.1

- [ ] 5. The app: four tabs, the look, Animations' rows and menus, Upload, Settings
  - `app/www/index.html`, `style.css`, `main.js`, `client.js`, `commands.js`,
    `messages.js`, `screens/show.js`, `screens/selection.js`, `screens/storage.js`,
    `screens/mapping.js`.
  - Tests: every scenario and test of `tests/app/` and `tests/mapping/test_app.py` that
    named Show, Storage or Mapping, for the four tabs; the look at 360, 320 and
    landscape sizes; rows with badges; the menu's actions on internal and external rows;
    ignored rows; the selection mode and both deletions; Upload's conversion and
    uploading; Settings without playback controls.
  - Prove it fails first: the new tab test finds no tab Animations.
  - Requirements: 5.1 to 5.5, 6.1 to 6.6, 8.1 (the mapping editor)

- [ ] 6. The app: reordering
  - `app/www/screens/reorder.js`, `client.js`, `commands.js`, `messages.js`,
    `screens/show.js`.
  - Tests: rows in the saved order; a drag by touch-like pointer and by mouse, with the
    placeholder and scrolling in a long list; Move up and Move down; `Saving…` then the
    confirmed order; a conflict, a refusal and a lost reply each read again with no
    second move; an older target without `order`; dragging off while a deletion, an
    upload or the selection mode runs; a second controller's move appears.
  - Prove it fails first: the rows are drawn in the list's order.
  - Requirements: 7.1 to 7.4

- [ ] 7. The app: the Tests group and its checkbox
  - `app/www/screens/tests.js`, `screens/mapping.js`, `screens/show.js`, `client.js`,
    `commands.js`, `index.html`, `style.css`.
  - Tests: the checkbox off at first and remembered across a reload; 21 entries when on,
    none when off; a snake test and the diagonal started, named in the now-playing area
    on a second app, stopped, and ended by playing an animation; an unsupported mapping's
    explanation; the tests in no list, selection or order.
  - Prove it fails first: Settings has no checkbox Show test animations.
  - Requirements: 8.1 to 8.3

- [ ] 8. The documents, the APK and every suite
  - docs/android-app.md for the four tabs, the order and the tests; docs/decisions.md, a
    dated line; AGENTS.md's line of seed 36; the app's page's verified and open lists.
  - Every suite that runs without a board; `python3 app/app.py build`; `tests/apk`;
    `python3 firmware/fw.py build` and `python3 firmware/fw.py build --microsd`, nothing
    flashed.
  - The seed stays `in_progress` for tasks 9 and 10.
  - Requirements: 5.3, 9.1 to 9.4

- [ ] 9. The board
  - In the run's board session, with the firmware of the run: remove the 21 hand-uploaded
    line-test files from the board's storage; see a moved order, a card entry absent and
    back, Snake 1 to Snake 20 and the diagonal on the LEDs at brightness 40 or less; record
    what was seen and left on the board in docs/firmware.md, "Verified on the board".
  - Requirements: 9.4

- [ ] 10. The owner's check on a phone
  - The owner, with the APK of the run: the four tabs, the look, a drag by a finger, the
    menus, the Tests group, upright and sideways. Only then is the seed `completed`.
  - Requirements: 9.4
