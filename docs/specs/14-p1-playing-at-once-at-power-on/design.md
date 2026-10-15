# Design: playing at once at power-on

## Overview

The start of the core stops decoding the animations. It opens each one, which reads its
header and its palette, and then the show plays. The bodies are decoded afterwards by the
second set of decoders that the check of an upload has, some records at each refresh,
while the first set plays.

Two things follow. The length of an animation, the sum of the durations of its frames,
is not known at the start any more, and the playlist needs it for a turn: the player
learns it by playing the first loop to its end. And the size of a file is not known
until the check has read it, so `list` has nothing to say until then, and the check
holds the decoders an upload needs: `list`, `remove` and `upload begin` answer `busy`
while it runs.

Everything is in the core. The firmware tool and the operators' app learn to wait for
`busy` to end.

## What this design relies on

Read in `core/src/` and in the tests, as they are after seed 16:

| | Fact | Where |
|---|---|---|
| S1 | The start reads the mapping, the show and then every file with `check_file`: it opens the file, opens the decoder on it, compares the canvas, decodes every record, reads the end, and notes the file's bytes and its length. The first failure ends the start. | `core.cpp`, `start` |
| S2 | Opening the decoder reads the header and the palette and gives the number of frames. | `odrg_decoder.h` |
| S3 | A second file source, inflater and decoder, with a pixel buffer and a window of their own, exist when the host's storage can be changed. The check of an upload uses them: one step at each refresh that follows the one before without a grid time left out. | `core.cpp`, `upload.cpp`, `player.cpp` |
| S4 | The player works out the loop and the place in it from the file's length by division, and opens the file anew for every loop. The playlist's turn is worked out from the length. | `player.cpp`, `advance`, `turn_ms` |
| S5 | A file that cannot be played makes the show invalid from that refresh on, with the reason the start would give. | `player.cpp`, `advance` |
| S6 | `list` writes the bytes of every file. `remove` and `upload begin` answer `busy` while an upload is open. `busy` stands after `show-invalid` and before `unknown-id` in the order of the error codes. | `content.cpp`, `commands.cpp`, `docs/commands.md` |
| S7 | A frame lasts at least one millisecond: a duration of 0 is a fault of the file. So a length of 0 can stand for "not known". | `docs/format.md`, the vector `zero-duration` |
| S8 | The reference player decodes every file whole at its start, and counts the steps of an upload's check at the refreshes of S3. | `tests/core/support.py` |
| S9 | `install-show` restarts the board and waits for the reply to `status`. | `firmware/fwtool/cli.py` |
| S10 | The app takes a refusal of `list` for an invalid show. | `app/www/client.js` |

## The start

`start` reads the mapping and the show as today. Then, for every file in the order in
which the show first names it, it opens the file and the decoder on it and compares the
canvas, and closes it: what `check_file` does before its loop over the records. A file
that is missing, a header or a palette that is not sound, and another canvas make the
show invalid there, with today's reasons in today's order.

Opening reads the palette as well as the header. That is at most 768 bytes of the body,
whatever the size of the file, and it is what the decoder's opening has always done: the
start does not grow with the bodies. The requirements say "the header only"; the
difference is recorded in `docs/drifts.md`.

Of a file the core then knows that it can be opened. `FileInfo` gets one more member,
`checked`, in bytes that were padding: it is 0 until the check after the start has read
the file to its end. `bytes` and `total_ms` are 0 until they are known.

With a host whose storage cannot be changed there is no second set of decoders (S3). The
start then decodes every file as today, every file is `checked`, and nothing of the rest
of this design happens.

## The check after the start

The core keeps where the check stands: the position of the file it is at, whether that
file's header was read, how many of its records are still to decode, the sum of their
durations so far, and how many refreshes in a row came without a grid time left out.

At each refresh, after the picture was made:

- when the refresh did not follow the one before it without a gap, the count of the row
  goes back to 0 and the check takes no step;
- otherwise the count goes up by one, to at most 16, and the check takes that many steps.

A step is one of three, as a step of an upload's check is:

1. the file is opened with the second file source and the second decoder is opened on
   it: the header and the palette again;
2. one frame record is decoded into the second pixel buffer, and its duration is added;
3. after the last record the end of the file is read: nothing may follow. The file's
   bytes and its length are noted, the file is `checked`, and the check goes to the next
   file.

A fault at any step makes the show invalid as `check_file` does: `file-missing`,
`read-error` or `file-malformed` with the file's name and, for the last, the reason.
After the last file the check is complete, for good.

So a show of light animations is checked fast, sixteen records at a refresh, and a show
whose own pictures are heavy gives way: a step that makes the next refresh late costs
the check its row. The reference player counts the same row from the same timestamps,
so the two agree on the refresh at which the check is complete.

The check and the player may have the same file open at the same time, each through its
own file source.

An upload cannot be open while the check runs, so the two users of the second decoders
never meet.

## Playing without the length

The player keeps one more number of its open file: how many records of it were decoded.
With that and the number of frames of the header it sees the end of a loop without
knowing the length.

To bring the pixel buffer to the picture of an animation at a time since the start of
its turn:

1. When the length is known, the loop and the place in it are found by division, as
   today. When it is not, the loop is the first one and the place is the time itself.
2. The file is opened for that loop unless it is open for it already.
3. Records are decoded while the place is at or after the end of the last one decoded,
   and records are left.
4. When the place is before that end, the picture is there. Otherwise every record was
   decoded and the time lies beyond the loop: the sum of the durations is the length.
   It is noted, and the work begins again at 1, now with a division.

With the length known, step 4 never comes to its second half, and the player does what
it does today.

**The playlist's turn.** To know whether the turn of an animation has ended, the length
is needed. While it is not known:

- when the time since the turn began is below the animation's `max_seconds`, or it has
  none: the records are decoded up to that time, as above. If the loop ends on the way,
  the length is known and the turn is worked out as ever. If not, the animation is in
  its first loop and its turn has not ended;
- when that time has reached `max_seconds`: the records are decoded up to that longest
  time and not further. If the loop ends on the way, the turn is worked out as ever. If
  not, the loop is longer than the longest time, and the turn ended there.

Whole rounds of the playlist are taken off by division only when the length of every
animation is known. Otherwise the turns are walked one by one, and an animation whose
turn was passed over without a refresh is read through once to learn its length. That is
the work the start did for every file, and it is done at most once for each.

A cycle counts the time of each of its turns from that turn's start and needs the length
only when an animation is shorter than its turn. The same four steps serve it.

Whatever is learned by playing is the length the check finds later: both add up the same
durations.

## The commands

`list`, `remove` and `upload begin` answer `busy` while the show is valid and the check
after the start is not complete. Where another code stands earlier in the order of the
error codes, that one is given: a `bad-argument` is still a `bad-argument`, and an
invalid show is `show-invalid`.

`docs/commands.md`, the row of `busy`: "`list`, `remove` or `upload begin` while the
installed animations are still being checked after a start; `upload begin` or `remove`
while an upload is open; `upload end` while the file is being checked."

`upload data`, `upload end` and `upload cancel` find no upload open and answer
`no-upload`, as today. Every other command works as ever. `space` counts the animations
of the show, which it knows.

## The reference player

It is rewritten from this design and not from the core's source.

- **The start.** It judges of every file what opening it shows: the header, by the
  first 16 bytes; the canvas; and the palette, which a file without compression either
  holds whole or not. A fault there makes the show invalid at the start. What the body
  holds beyond that is not looked at then.
- **The check.** It counts steps as the core does: for each file one, one for each of
  its frames, and one. It takes them at the refreshes of S3, as many as the row is long,
  at most 16. At the step that ends a file it knows the file's bytes; when the last file
  ends, `list`, `remove` and `upload begin` work.
- **A fault in a body.** The reference decodes a file at once and cannot tell at which
  record a fault lies, least of all inside a compressed body. So for a show with a
  damaged body it is told by the test at which refresh the show turns invalid, and says
  with which reason, which is today's. The tests of such shows run the core first, take
  the refresh from it, check that it lies where the check or the player could have come
  to that file, and then compare every line.
- **Lengths.** It knows every length and plays as it does today. For a show of sound
  files nothing it prints changes but the replies of the three commands while the check
  runs.

## The firmware tool, the app and the command tool

- `install-show` and `install-firmware`, after the board answers `status`, send `list`
  every half second until the reply is no `busy`, within the time `--wait` gives, and
  then read `status` once more. A reason in it is a failure, as it is today, and so is a
  check that did not end in time, with the reason `check-not-done`.
- The app's client: a `busy` to `list` leaves what it knows as it is and asks again a
  second later. It is no failure and shows no message.
- The command tool prints the reply. Nothing changes in it.

## Tests

- `tests/core/`: the start opens every file once and decodes no record, read from the
  host's trace; the check's order, its pace with refreshes in a row and with gaps, and
  the refresh at which it is complete, for one file and for several, with a file named
  twice; `busy` for the three commands before and their replies after; an animation
  played before its file was checked, in the playlist and in a cycle, with `repeat`, with
  `max_seconds` below and above the loop, and after a jump; refreshes that come late and
  a long gap, with lengths not known; a damaged body found by the check and one found by
  the player, for every invalid vector whose fault is in a body; a host whose storage
  cannot be changed; the memory, with its number.
- The tests that send `list`, `remove` or an upload at the start let the check end first.
- `tests/emulator/`: `busy` and then the list over each transport; record mode; a show of
  dense animations of 60 seconds in all that plays in the first second.
- `tests/firmware/`: the tool waits, against the stand-in for a board; a show that turns
  invalid during the wait; a check that does not end.
- `tests/app/`: a target that answers `busy` twice and then lists.
- `tests/board/`: as "Shown on the board" of the requirements.

## Documents

`docs/core.md`: the start, the check after the start, playing without the length, the
memory. `docs/show.md`: when a show is found invalid. `docs/commands.md`: `busy`, and
`list`. `docs/emulator.md`, `docs/firmware.md`, `docs/android-app.md`: what a client
sees after a start. `docs/decisions.md`: a line in the change log. `AGENTS.md`.

## Risks

- **Many tests send `list` or an upload at the start.** They are found by running the
  suites; each gets the refreshes the check needs first.
- **The moment a damaged body is found is not fixed by the documents**, only bounded:
  after the start, and no later than the check comes to it.
- **A show of heavy pictures checks slowly**, because the check gives way. On the board
  the time is measured for a dense clip; if `status` falls below 20 refreshes a second
  there, the pace is lowered and the drift recorded.
- **A read through of an animation at a late refresh** takes as long as the start took
  for that file. It happens when a host asked for no refresh for longer than a turn.
