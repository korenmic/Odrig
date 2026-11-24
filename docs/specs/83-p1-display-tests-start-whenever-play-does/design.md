# Design

## The gates

- `mapping_test` (`core/src/mapping_control.cpp`) loses the line that refuses `busy` until
  the check after a start is complete and while an upload is open. Its other checks keep
  their order. The diagonal is decoded through playback's own file and decoder, and a
  snake is drawn into the pixels; the check after a start and an upload's check use the
  checker's file and decoders, so nothing is shared.
- `mapping_set` keeps `core.upload.state != kUploadNone` as `busy` and loses
  `!check_complete(core)`.
- `commands.cpp`, `upload`: a test refuses `upload begin` alone. The line is `busy` when
  its second word is `begin` and a test shows or a rebuild runs. `upload data`, `expect`,
  `end` and `cancel` go to `upload()` as without a test.
- `ignore`, `remove`, `remove many` and `catalog_rebuild` keep `core.mapping_test` as
  `busy`.

## Nothing plays under a test

- A test halts the player (`player_halt`), so `core.playing` is `kNothing` while it
  shows. `player_item_added` plays the playlist's first animation when nothing plays, and
  `player_file_replaced` calls it when nothing plays. An upload's end reaches both:
  `storage_install_upload` for the board's storage, `install_external_path` for the card.
- `player_item_added` therefore does nothing while `core.mapping_test` is set. Its Clocks
  only branch cannot meet a test, which Clocks only stops. The test's end,
  `mapping_test_stop`, already plays the saved place, else the playlist's first
  animation: a new one is played then.
- `player_drive_joined` already waits for the test's end.

## The saved place across an upload

- `mapping_saved_playing` is `core.playing` at the first test: `kPlaylist`, a cycle's item
  or `kNothing`. An upload to the board's storage appends a new item or keeps the replaced
  item's position, and `remove` is refused under a test, so the positions held do not move.
- `mapping_saved_shown` of the card is already moved by `player_drive_shifted` and
  `player_drive_moved` when the card's walk changes; a replaced file keeps its position.
- `mapping_test_stop` then plays the saved place as today, or falls back when it is gone.

## Tests

- `tests/core/test_snakes.py` and `tests/mapping/test_core.py`, against the test host:
  - a test, the diagonal and a snake, and `mapping set`, before the check after a start is
    done (`check_first=False`): taken; the check ends under the test, `status` reports it
    done, and the LEDs keep the test;
  - a test started while an upload is open: the rest of the upload's data and its
    `upload end` taken; the list has the new item; the LEDs keep the test; `mapping test
    off` resumes the animation that played before;
  - an upload under a test that replaces the file that played before it: the test's end
    plays it;
  - an upload cancelled under a test;
  - nothing played before the test and an upload adds the first animation: nothing plays
    under the test, and its end plays the new animation;
  - `upload begin`, `ignore`, `remove`, `remove many` and `catalog rebuild` still `busy`
    under a test;
  - `mapping set` still `busy` while an upload is open.
- The tests that expected `busy` for a test before the check's end or under an open
  upload change after the new ones were seen failing.
- `tests/emulator`: over the emulator's TCP line, a test taken before the check after its
  start ends, and an upload opened before a test ending under it.
