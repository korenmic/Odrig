# The display tests start whenever play does

## Summary

Let the display tests, the diagonal and the twenty snake tests, start whenever an ordinary
play command is taken. Today the board answers `busy` to them while it reads its
animations after a start, and while an upload is open, though it plays any animation it is
asked to in both cases. Starting a test waits for nothing that play does not wait for. An
upload that is open when a test starts goes on to its end. A mapping save no longer waits
for the reading after a start.

## Priority

`P1`.

## Product Context

On 2026-11-07 the owner connected the phone to the board over USB serial right after the
board started. The app changed animations at once, but every press of `Diagonal` or
`Snake n` was answered `The installation is busy. Try again in a moment. (busy)`. The
owner's ruling: "If there is no slowdown in deciding to play non-test animations, there is
no reason why there should be a slowdown in selecting test animations. It's not a
legitimate bug and it should be fixed." The link is not the cause: the refusal comes from
the core, the same over Wi-Fi, serial and the emulator.

How it is today:

- `mapping_test` (`core/src/mapping_control.cpp`) refuses `mapping test on` and
  `mapping test snake <n>` with `busy` while `!check_complete(core)`, the reading of every
  installed animation after a start, or while `core.upload.state != kUploadNone`, an open
  upload. `docs/commands.md`, "Mapping controls", writes this rule ("Entry requires ... a
  completed startup check with no open upload"), and seed 30's design wrote it without a
  reason.
- `mapping_set` refuses `mapping set` with `busy` under the same two conditions.
- The tests need nothing the reading or the upload uses. The diagonal is decoded once by
  playback's own file and decoder (`decode_diagonal`), and a snake test is drawn into the
  pixels at every refresh (`snake_test_draw`). The reading after a start, the upload's
  check, the card's check and a catalog's rebuild use the second decoders.
- Play is taken in both conditions. `docs/commands.md` says "Playback goes on during an
  upload".
- While a test shows, `upload` in every form, `ignore`, `remove`, `remove many` and a
  catalog's rebuild are refused with `busy` (`core/src/commands.cpp`, `catalog_rebuild`).
  So a test started under an open upload would starve it: its next `upload data` would be
  `busy`, and after 60 s without progress the upload is discarded.
- With hundreds of animations, or a few long ones such as the owner's rotated clocks, the
  reading after a start lasts minutes. The board also loads the card's catalog only after
  it, so the tests were refused for that whole time.

## Required Behavior

1. **Tests start when play does.** `mapping test on` and `mapping test snake <n>` are no
   longer refused because the reading after a start is under way or an upload is open.
   They keep every other answer of today, in the same order: `in-use` in Clocks only,
   success when the same test already shows, `show-invalid`, `bad-argument` for a mapping
   the tests cannot use, and `storage-error` when the diagonal cannot be decoded.
   `mapping test off` is taken as today.
2. **The reading goes on during a test.** The reading after a start, the card's check and
   the loading of the card's catalog that follows it go on while a test shows, as they do
   while an animation plays. `status` reports their progress as today, and they end as they
   would without the test.
3. **An open upload goes on during a test.** When a test starts while an upload is open,
   that upload's `upload data`, `upload expect`, `upload end` and `upload cancel` are taken
   as without a test, and its check runs to its verdict. An `upload end` that succeeds
   during the test changes the show as it does during play. The test keeps showing until
   `mapping test off` or a valid ordinary play command. Its end resumes what played before
   the first test, and when that animation is no longer there, it falls back as a test
   falls back today when the card went.
4. **What stays refused during a test.** `upload begin`, `ignore`, `remove`, `remove many`
   and a catalog's rebuild stay `busy` while a test shows, as today. Only an upload that
   was already open is let through.
5. **A mapping save does not wait for the reading.** `mapping set` is no longer refused
   because the reading after a start is under way. It stays `busy` while an upload is open,
   as other writes of the show are, and keeps its other answers.
6. **Same everywhere.** The board, the spare's firmware and the emulator answer alike,
   since they share the core. Wi-Fi, USB serial and the emulator's TCP lines carry the same
   replies. No command, reply member or error code is added or removed.

## Technical Constraints

- The change is in the core (`core/src/mapping_control.cpp`, the `upload` and test gates
  of `core/src/commands.cpp`, and wherever an upload's end changes the show's items).
  No firmware source, host, wiring or power change, but the firmware images are rebuilt
  because they compile the core.
- An `upload end` that inserts or replaces an item during a test must keep the test's
  saved resume point, `mapping_saved_playing` and `mapping_saved_shown`, pointing at the
  same animation, as the player's current item is kept during play.
- The core's fixed memory and 512-byte stack-frame limit hold. No new memory is added for
  this.
- Tests seen failing first: the core suite with a host whose reading after a start is still
  under way, for the diagonal, a snake test and `mapping set`; a test started under an
  open upload that then completes and one that is cancelled; the reading and the card's
  loading completing under a test; the refusals of item 4 unchanged. The emulator's suite
  over its TCP lines. The existing tests that expect `busy` for these cases are changed
  after the new ones were seen failing.
- Documents: `docs/commands.md`, "Mapping controls" and the upload section;
  `docs/core.md` where it names the test's gates; the change log of `docs/decisions.md`
  with the owner's ruling of 2026-11-07; an entry at the end of `docs/drifts.md`.

## Open Questions

None. The owner ruled that a test is selected as freely as an animation. The seed decides
the rest from that ruling: the open upload is let through instead of starved, the
mutations that a test refuses today stay refused, and `mapping set` loses the same needless
wait for the reading after a start but keeps waiting for an open upload, as every other
write of the show does.

## Definition Of Done

1. A requirements/design/tasks specification of the gates, the open upload under a test and
   the mapping save.
2. The core, emulator and app suites pass with the new tests, seen failing first.
3. Firmware images for the installation's board and the spare's module, built as
   `firmware/fw.py` builds them.
4. The owner's check on the board: right after a start, while the app says
   `Reading the animations`, `Diagonal` and a snake test show at once, `Stop test` resumes
   the animation, and the reading and the card's loading finish.
