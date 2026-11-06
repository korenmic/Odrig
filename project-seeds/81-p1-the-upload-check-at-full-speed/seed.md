# The upload check at full speed

## Summary

After the last byte of an upload, the core checks the whole file before it installs it.
Today the check reads one frame record at a refresh, and only at a refresh that came one
grid time after the one before. A file of F frame records needs F + 2 such refreshes. At
R refreshes a second there are 2R - 50 of them a second, and none at 25 or fewer. The
owner's rotated clock has 14,399 frames. Its check took 288 s at a perfect 50 a second,
24 minutes at 30, and hours near 26. Meanwhile the app showed a frozen `Sending: 100%`.

This seed changes how much the check does at a refresh. At every refresh, in step or
late, it takes steps within a budget of 256, 512, 1,024 or 2,048 bytes of the file's body.
Each step is charged by its work: its body bytes, and more for a record that walks the
whole picture. A record larger than the budget leaves a debt, and the refreshes after it
rest until the debt is paid. So the check's work at a refresh is about its budget, whatever
the file holds. The budget changes once a second by the refreshes the second before had.
It rises from 40 a second, and on trial from 27; a trial that costs the board its rate is
taken back in the middle of the next second. So a board at 22 a second or more stays at 20
or more.

The check still reads the whole file, and its verdicts and reasons do not change. The app
shows `Checking the animation on the installation: 0:12` from the last byte until
`upload end` answers. The time comes from the app's own clock. It shows on Upload and in
the text and clock forms. The pages give the new times, and the command tool waits up to
10,800 s.

The core was measured in a host build on this computer, and the figures were scaled by the
board's documented timings. By that estimate, the owner's file is checked in about 8 s on
a board that refreshes 50 times a second with room to spare, and within 30 s on a board at
30 or more while it plays a show that is not dense. No command, reply or memory block
grows, and no firmware source changes.

## Priority

- `P1`

## Depends On

- Seed 07, completed: the content commands, the upload and its check, which decodes the
  whole file beside playback with the second decoders, and `busy` to `upload end` while
  the check runs.
- Seed 14, completed: the check after the start, which has its own pacing (steps in a row,
  and one step after nine refreshes without one). That pacing is not changed here.
- Seed 31, completed: bounded work. A step is one frame record or one slice of at most
  32,768 bytes of body while a defect is settled. The decoder counts the bytes of the body
  it takes (`body_read`). The budgets are 50 ms for one call on the board, and 131,072
  bytes of body for playback at one refresh.
- Seed 37, completed: the text and clock forms of Upload, which send through the same job
  as Upload (`uploading` of `app/www/upload.js`).
- Seeds 38 and 63, completed: ready-made files uploaded to the board or the card, through
  the same job. An upload to the card (`upload begin external`) is checked the same way,
  from the card.
- Seed 76, completed: a board without `mapping.json` and `show.json` plays the
  installation's 60 x 60 canvas and takes its first upload. The tests here use such a
  board.
- Seeds 77 and 78, completed: the spare board's image `odrig-firmware-n8r2.bin`, which the
  owner's check uses.
- Related, not needed: seeds 73, 79 and 80, planned, send their uploads through the same
  job and change the same screens. Whichever lands later takes the other's lines in its
  merge. The job's new `checking` call (point 7) serves every user of the job.

## Product Context

On 2026-11-06 the owner uploaded the rotated clock
`time-original-5-every-row-another-time.odrg` (498,211 bytes, 14,399 frames) to the
spare board from the phone. The phone stayed at `Sending: 100%` and the upload never
seemed to finish. The diagnosis of that day found a slow check and no fault. The check
advances only at refreshes in step, one frame record each, and nothing tells the operator
that the board is checking.

The owner, in their words: "It is incredibly unreasonable that it takes more than half a
minute to validate 400K of animation."

Two remedies were put to the owner. One was to skip the check, which would let a broken
file onto the board. The other was "the board checks an upload at full speed, a few
seconds, instead of one frame per refresh, and the app shows Checking…". The owner chose
the second, in their words: "So you saw a problem with validation and you say you can
optimize it with a fixed seed. If you believe truly you can do this, then I approve.
Create that fixed seed right now, autonomously S2S it, and queue, implement, and push to a
branch from a temp work tree, then make a PR".

## Technical Constraints

- **What happens today.** Read at `master` `73da1103` on 2026-11-06.
  - `player_poll` (`core/src/player.cpp:1336-1341`) computes the grid time and
    `in_step = core.had_refresh && grid == core.last_grid + kGridStep`. After the LED
    data is complete it calls `upload_step` only `if (in_step)` (`:1374-1379`), once.
  - `upload_step` (`core/src/upload.cpp:90-152`, declared at `core/src/upload.h:44-47`)
    takes one step. A step is the header, one frame record, the end, or one slice of the
    settling of a defect. A text or a clock reads its payload whole in one step
    (`drawn_read`). The step sets `upload.progress = now` (`:96`).
  - The check after the start has a fallback for a host that is always late:
    `kCheckLongestWait` gives one step after nine refreshes without one
    (`core/src/core.cpp:703-731`, `core/src/core_state.h:835-838`). The upload's check has
    no such fallback.
  - So the upload's check takes F + 2 steps, and at R refreshes a second it takes
    max(0, 2R - 50) steps a second. At an even 25 a second or fewer it takes none. After
    60 s without progress, `upload_touch` (`core/src/upload.cpp:75-79`, `kUploadQuietMs`
    of `upload.h:11-13`) discards the upload, and `upload end` answers `no-upload`.
  - The diagnosis measured this in the core's library, the emulator and a host build, on
    the owner's two copies of the file (14,401 steps). The check took 288.1 s at 50
    refreshes a second, 864 s at 33.3 and 3,008 s at 27.4. The board's own record agrees:
    a check of 100 frames took 17 s at 25 to 29 refreshes a second
    (`docs/firmware.md:1511-1512`).
  - The decoder's count `body_read` is set to 0 by `OdrgDecoder::open`
    (`core/src/odrg_decoder.cpp:207`), which the header step calls through `content_open`.
    A text or a clock never opens the decoder for its payload
    (`core/src/container.cpp:81-83`), and a picture clock opens it again for its picture
    (`core/src/clock.cpp:690`).
  - Decoding a coded record with the run bit and predictor 1 or 2 walks every position of
    the picture, a zero at a time (`Picture::zeros`, `core/src/odrg_decoder.cpp:164-176`),
    whatever the record's bytes. The converter's encoder picks such records for a picture
    that changes evenly, as in a fade, a strobe or a colour cycle.
  - `upload end` answers `busy` while the check runs (`core/src/upload.cpp:395-397`). No
    reply reports how far the check is.
  - The app resends `upload end` every 250 ms (`CHECKED_AGAIN_MS`, `app/www/upload.js:11`
    and `:164-178`). Its line stays as the last data reply left it:
    `Sending: 100%, N KB a second` on Upload (`app/www/screens/storage.js:208` and
    `:214-216`), and `Sending: 100%` in the text and clock forms
    (`app/www/screens/author.js:316` and `:322-324`). `Cancel` stays.
  - `docs/commands.md:358-361` and `docs/android-app.md:586-587` promise "a fiftieth of a
    second for each frame". `docs/core.md:931-941` describes the in-step pacing of the
    upload's check.
  - `odrigctl/content.py:15` gives up after `BUSY_SECONDS = 600.0` of `busy`, as
    `docs/emulator.md:1054-1057` says. For this file that fails at any rate below about 37
    a second. `tests/emulator/test_docs.py:150` looks for `f"{content.BUSY_SECONDS:g}
    seconds"` in that page, and `tests/emulator/test_tool.py:1075-1083` feeds 4,000
    `busy` replies and asserts 600.
  - The core suite pins the old pacing. `TheCheck` in `tests/core/test_upload.py:516-635`
    has, among others,
    `test_a_host_that_is_always_late_never_ends_the_check_and_the_upload_goes_after_60_seconds`.
    The reference player in `tests/core/support.py:1191-1197` takes one step after each
    refresh in step.
- **1. The check takes steps at every refresh, by their work.**
  - At every refresh, in step or late, the check takes its steps once the LED data is
    complete, where it takes its one step today. A step stays what it is today: the
    header, one frame record, the end, or one slice of settling.
  - **The charge of a step.**
    - The header step, the step that reads a text's or a clock's payload (a picture
      clock's picture included), and the end step are charged 0. A text or a clock is so
      checked whole at the first refresh after its last byte.
    - A step that calls the decoder for a frame record, or for a slice of settling, is
      charged its body bytes: `body_read` after the step less `body_read` before it, both
      read after the header step has opened the decoder. For a compressed body these are
      inflated bytes. The palette is counted with the first record.
    - A step that decodes a whole coded frame record with the run bit and predictor 1 or
      2 is charged n / 32 more (integer division), where n is the decoder's pixel buffer
      (`checker.decoder.n`): 337 for a 60 x 60 picture of three bytes a pixel, 112 with a
      palette. The decoder keeps the mode byte of the record it has just read, in a byte of
      its existing padding (point 9).
    - The basis, measured on this computer (point 5): the processor time of a step is 25
      to 35 ns for each byte it is charged, for every kind of record measured: the clock's,
      a dense clip's, `space-scan-10x`'s, a fade of three bytes a pixel and one with a
      palette. A file of records of 12 bytes took 51 ns a byte; the cap of 64 steps
      bounds such a refresh below the clock's at the same pace. By body bytes alone a
      record of a fade of three bytes a pixel took 890 ns a byte at the median, 25 times
      the clock's 35. A charge of at least n / 64 for every record would charge the
      clock's records 40 % more than their work.
  - **The debt.** The check keeps a debt, in whole 256s of charge, from 0 to 15. A
    refresh's allowance is its budget (point 2) less 256 times its debt.
    - A refresh whose allowance is 0 or less takes no step, and its debt falls by its
      budget's 256s: 1, 2, 4 or 8.
    - Any other refresh takes steps while all of these hold: the check has not ended; the
      steps of this refresh are fewer than 64; the charge of those steps is below the
      allowance. Its first step is always taken.
    - After it, the debt is what the charge of its steps passed the allowance by, in whole
      256s rounded down, at most 15. A refresh whose last step gave `pending`, a slice of
      settling, leaves no debt: the decoder inflates a slice of 32,768 bytes in about a
      millisecond on the board ([core.md](../../docs/core.md), "Bounded work"), far less
      than its charge, and its charge already ends the refresh's steps.
    - So a record larger than the allowance is taken about once in every (its charge /
      the budget) refreshes, and the check's work at a refresh is, on average, its
      budget. A charge within 255 of the allowance leaves no debt, so a file of small
      records, such as the clock, never rests.
  - A late refresh gets the same budget as one in step. Nothing is added for the grid
    times it skipped: a host that is late has no time to spare.
  - Only the refreshes the host asks for take steps. A poll that produces no refresh takes
    none, as today.
- **2. The pace.**
  - The budget is 256 bytes of charge shifted left by the pace: 256, 512, 1,024 or 2,048,
    for a pace of 0 to 3.
  - When the last byte has arrived and the check begins, the pace is 1, the debt 0, and
    the mark that the pace has fallen is clear.
  - At the first refresh of each new whole second while the check runs, before that
    refresh's steps, after `player_poll` has rolled the second over, the pace changes by
    R, the count `player_fps(now)` then gives: the refreshes of the second just ended, or
    0 when the host gave none in it. It is what `status` reports as `fps`.
    - At R below 21 the pace goes down by one, to 0 at least, and the mark is set.
    - Otherwise, at R of 40 or more, it goes up by one, to 3 at most.
    - Otherwise, at R of 27 or more while the mark is clear, it goes up by one, to 3 at
      most.
  - At any refresh 500 ms or more into its second (`(now - t0) % 1000`), while the mark is
    clear, before that refresh's steps: when that second has had 11 refreshes or fewer,
    this one included (`count_running`), the pace goes down by one, to 0 at least, and the
    mark is set. At an even 20 a second a refresh 500 ms in is the eleventh of its second,
    at 22 the twelfth.
  - The mark stays set until the check ends.
  - The basis.
    - Rule 12 accepts any rate from 20 to 50. The core reads no clock inside a call, so
      it cannot time its own work; the refreshes of a whole second are the measure it has,
      and they are what the owner reads.
    - The charge makes the check's work at a refresh follow its budget: the mean work at
      a refresh of each pace was 9.8, 18.8, 36.8 and 72.3 µs for the owner's clock, 9.0,
      17.9, 26.9 and 53.9 µs for a fade of three bytes a pixel, 8.1, 16.2, 32.4 and 64.7
      µs for the dense clip and 6.9, 13.8, 27.6 and 54.6 µs for `space-scan-10x`. So a
      rise at most doubles the check's work at a refresh, and at most halves the rate.
    - A rise from 40 or more so keeps the rate at 20 or more.
    - A rise from 27 to 39 is a trial. When the second after it falls below about 20 a
      second, its first half has had 10 refreshes or fewer, and the pace falls back at
      its middle. That second then has at least a quarter of the rate before the rise in
      its first half and half of it in its second, three quarters of 27, about 20. After a
      fall the pace rises only from 40, so a board whose own playback fills its processor
      does not go through a trial a second time.
    - This matters most while a dense animation plays. Playback then decodes every frame
      that is due whatever the rate ([firmware.md](../../docs/firmware.md), "Once a
      refresh is late the core decodes every frame up to the one that is due"), so only
      the copy of 4.1 ms and the check grow with the refresh count, and each millisecond
      of the check costs the board several milliseconds of a refresh. A rise from 25 with
      no trial held such a board below 20 in about half of its seconds in the model of
      point 5.
    - A board already at 20 or 21 a second before the check has no time to spare. The
      check at pace 0 adds about 2 ms to its refreshes, and the board shows about 19 while
      the check runs. Today such a board never checks an upload: its upload is discarded
      after 60 s.
- **3. What stays whole.**
  - The check reads every record of the file and its end, as today. The size and the
    CRC-32 of what it read back are compared with what was received.
  - Every verdict stays the same, with its reason: `bad-file` with the reason of
    [reasons.md](../../docs/reasons.md), `size-mismatch`, and `storage-error` for a read
    that fails or bytes that differ.
  - The fault's context stays the same: the work `upload`, the record and the bytes of the
    body.
  - Settling keeps its slices of 32,768 bytes, and `pending` stays internal.
- **4. The quiet timer, and a host that is late.** Each step still sets the upload's
  progress. A refresh that pays a debt takes no step, and at most 15 do so in a row. So the
  60 s timer discards the upload only when the host asks for no refresh for 60 s, or when
  the check has ended and nobody asked `upload end` for 60 s. Both are as today.
  `upload end` stays `busy` while the check runs.
- **5. The target, and its basis.**
  - Measured on 2026-11-06 on this computer: an Intel Core i7-14700 running Windows 11,
    GCC 16.1.0 of WinLibs with `-O2`. The core sources of `73da1103` were linked into a
    scratch host. The host held the files in memory, uploaded the file and polled every 20
    ms of a virtual clock, one step at a poll, timing each poll. Three runs agreed.

    | File | Steps | Body bytes | Charge | Processor time of the whole check |
    |---|---:|---:|---:|---:|
    | The owner's rotated clock, 498,211 bytes, CRC-32 `4894fa74` | 14,401 | 627,470, at most 130 in a step | 644,718 | 22.6 ms, 1.4 µs for a median step of 40 bytes |
    | The tracked clock `collection/card/clocks/time-original-5-every-row-another-time.odrg`, 471,095 bytes | 14,401 | 624,310, at most 139 | 657,686 | 22.6 to 23.0 ms |
    | The dense 60 x 60 clip of 10 s of `tests/board/support.py`, compressed, 1,372,244 bytes | 502 | 1,462,220 | 1,464,242 | 44.3 ms |
    | The same clip uncompressed, 1,462,236 bytes | 502 | 1,462,220 | 1,464,242 | 25.1 ms |
    | `collection/card/space/space-scan-10x.odrg`, 34,410,601 bytes | 18,006 | 37,105,667, at most 5,758 | 37,390,769 | 940 ms |
    | A fade of 60 x 60, three bytes a pixel, 1,024 frames, uncompressed, 15,313 bytes, made with `odrig.odrg.encode` | 1,026 | 15,297, 10 a record | 360,048 | 9.3 ms, 8.9 µs a record |
    | A fade of 60 x 60 with a palette, 1,024 frames, compressed, 911 bytes | 1,026 | 9,981 | 124,669 | 3.5 ms, 3.3 µs a record |
    | A picture of 60 x 60 with a palette in which one pixel changes at each of 1,000 frames, compressed, 6,702 bytes | 1,002 | 12,258, 12 a record | 12,370 | 0.6 ms |

  - The board's speed at the check. The board checked that dense clip at power-on in 6.0 s
    compressed and 4.2 s uncompressed, with the reading included
    ([decisions.md](../../docs/decisions.md), "Open questions"). That makes the board 135
    to 167 times slower than this computer at the check. Beside a send to twenty outputs
    on the other processor core, the core's work takes about 1.4 times as long: 12.3 ms
    becomes 16 to 17, and 8.6 ms becomes 12 to 13 ([firmware.md](../../docs/firmware.md)).
    So the factors used below are 189 and 234.
  - So the whole check of the owner's file is about 3.0 to 3.8 s of the core's work on the
    board, and 4.3 to 5.3 s beside the sends.
  - The cost of one refresh at each pace, for the owner's file, with the rule of point 1
    at that pace alone:

    | Pace | Budget | Here, median | Here, worst | On the board beside the send, median | worst |
    |---|---:|---:|---:|---:|---:|
    | 0 | 256 | 9.7 µs | 26.0 µs | 1.8 to 2.3 ms | 4.9 to 6.1 ms |
    | 1 | 512 | 18.6 µs | 36.9 µs | 3.5 to 4.4 ms | 7.0 to 8.6 ms |
    | 2 | 1,024 | 36.4 µs | 59.2 µs | 6.9 to 8.5 ms | 11.2 to 13.9 ms |
    | 3 | 2,048 | 71.7 µs | 106.9 µs | 13.6 to 16.8 ms | 20.2 to 25.0 ms |

    A record larger than the allowance is one step of its own, as one step is today: a
    dense record took 87.7 µs here at the median and 165.5 µs at most, about 17 to 21 ms
    and 31 to 39 ms on the board beside the send; the largest record of `space-scan-10x`
    took 262 µs, 50 to 61 ms, as its step takes today. The debt then rests the refreshes
    after it. The demo show's own work is 1.2 to 2.1 ms a refresh, and the copy 4.1 ms
    (firmware.md, the table of the probe build), so pace 3 leaves a light show at about
    43 to 50 a second.
  - The times the rule gives were worked out from the charge and the processor time of
    each step, with the rule of points 1 and 2, at six offsets of the check's start in its
    second. First on a host whose refreshes come at a fixed period, as the core's tests
    and the emulator do: the rates in this table are the rates during the check.

    | Host refreshes | The owner's clock: refreshes | time | Today | The tracked clock: refreshes |
    |---|---:|---:|---:|---:|
    | every 20 ms, 50 a second | 345 to 374 | 7.5 s at most | 288 s | 351 to 380 |
    | every 25 ms, 40 a second | 338 to 361 | 9.0 s | 480 s | 344 to 367 |
    | every 30 ms, 33 a second | 334 to 353 | 10.6 s | 864 s | 340 to 359 |
    | every 40 ms, 25 a second | 1,201 | 48.0 s | never | 1,221 |
    | every 45 ms, 22 a second | 1,201 | 54.0 s | never | 1,221 |
    | every 50 ms, 20 a second | 2,289 to 2,299 | 115.0 s | never | 2,322 to 2,331 |

    The other files, at 50 and at 20 a second: the fade of three bytes a pixel 4.6 s and
    52 s (today 20.5 s at 50); the dense clip 14.9 s and 273 s (today 10.0 s at a perfect
    50, with one dense record at each refresh); `space-scan-10x` 346 s and 6,793 s (today
    360 s at 50).
  - Then on the board, by the rate before the check. A model of the board, while a show
    that is not dense plays: a refresh lasts its time before the check plus the check's
    work at it on the board, its processor time here times 189 or 234, and at least 20
    ms. While a dense animation plays, playback decodes every frame that is due, so only
    the copy of 4.1 ms and the check grow with the refresh count: a refresh lasts (4.1 ms
    + the check's work on the board) / the share of the processor that playback leaves,
    0.175 for the compressed dense clip at 42 a second and 0.375 for the uncompressed one
    at 46, and at least 20 or 21.5 ms. The lowest rate is that of a whole second during
    the check.

    | Rate before the check, and what plays | The owner's clock: time | lowest rate during it |
    |---|---:|---:|
    | 50, with room to spare (the demo show) | 7.5 to 8.3 s | 43 to 49 |
    | 40 | 13.1 to 14.1 s | 23 to 25 |
    | 33 | 14.7 to 23.8 s | 22 to 23 |
    | 30 | 25.1 to 26.1 s | 23 to 24 |
    | 27 | 48.7 to 49.7 s | 24 |
    | 25 | 52.3 to 53.3 s | 22 |
    | 22 | 106.4 to 108.3 s | 21 |
    | 20 | 118.7 to 119.8 s | 19 |
    | 42, the dense clip compressed | 52.5 to 83.8 s | 22 to 26 |
    | 46, the dense clip uncompressed | 18.0 to 20.9 s | 22 to 24 |

    In the same model the other files keep the rate at 20 or more from 22 before: the
    dense clip takes 16 to 18 s at 50 with room, and `space-scan-10x` 6 to 7 minutes.
  - The target, therefore, for the owner's file, while a show that is not dense plays:
    - on a board that refreshes 30 times a second or more before the check, within 30 s;
    - at 25 to 29 a second, within a minute;
    - below 25, within two and a half minutes.

    While a dense animation plays it takes longer, up to about 85 s in the model. The rate
    stays at 20 or more on a board at 22 or more before the check, and a board at 20 or 21
    shows about 19 while it runs (point 2). These figures are an estimate until the owner's
    check of the Definition Of Done measures them.
  - An upload to the card is checked by the same rule, reading `drive/upload.part` from
    the card through `read_at`. Its time is not estimated here: these measurements read
    the file from memory and the board's from its internal flash.
- **6. The firmware.**
  - No source of the firmware changes. It hosts the core as it is, and its build takes
    the new core.
  - On a board with room, the usermod's task asks the core for a refresh again after a
    millisecond while none is due ([firmware.md](../../docs/firmware.md), "Playback"), so
    the core is called between refreshes. The check takes no step at those calls. The core
    reads no clock inside a call, so a step taken at such a call could run past the next
    grid time, and a board whose loop is the slower side has no such calls. So the check
    works only at refreshes, where `fps` measures its cost.
  - Every call stays bounded. The check adds to a refresh its allowance and at most the one
    step that passes it, at most 64 steps. That one step is what one step is today: one
    frame record, or one slice of settling.
- **7. The app's line while the board checks.**
  - The job of `app/www/upload.js` gains an optional `checking(since)`. It is called once,
    when the reply to the last `upload data` has come, with `performance.now()` of that
    moment. A job that ends before the last byte never calls it.
  - From then until the job ends, the line of the screen that runs it says
    `Checking the animation on the installation: <m>:<ss>`. That is the time since
    `since`, in whole seconds, minutes without a leading zero and seconds in two digits
    (`0:00`, `0:12`, `1:05`, `61:05` past an hour). Its first text is written at once.
    The screen then writes it again at each next whole second of that time: a timer set to
    `1000 - elapsed % 1000` ms, set again each time.
  - The `checking` call comes in the same task as the report of the last data reply, so
    `Sending: 100%` may never be painted; the Checking line follows the Sending line.
  - The line holds no fraction and no speed, because no reply gives a fraction. `Cancel`
    stays and sends `upload cancel` as today, and `Cancelled.` follows. Every way the job
    ends stops the timer: done, cancelled, or failed.
  - This holds for every upload through the job today: `Upload to the installation` on
    Upload (converted media and ready-made files, to the board or the card), and the
    upload and the Save of the text and clock forms. A later user of the job gets the call
    as well.
  - The time comes from the app's own clock and includes any time the app was hidden. The
    job still resends `upload end` every 250 ms while it is shown, and nothing while it is
    hidden, as today. No command, no reply member and no new message are added.
- **8. The command tool.** `BUSY_SECONDS` of `odrigctl/content.py` becomes 10,800. The
  core already discards an upload whose check does not move for 60 s, so the limit only
  guards against a target that answers `busy` for ever. The largest file of the
  collection, `collection/card/space/space-scan-10x.odrg` (34,410,601 bytes, 18,004
  frames, 2,061 bytes of body a record on average), takes up to 6,793 s at 20 refreshes a
  second by the rule of point 2 on a fixed host, and about 7,000 s on a board at 20 in the
  model of point 5. 10,800 s, three hours, covers it. `upload: checking` and the resend
  every 0.2 s stay.
- **9. Memory.**
  - The pace (2 bits) and the debt (4 bits) fill the free bits of the bit field of the
    upload's record (`struct Upload`, `core/src/core_state.h:126-142`), beside
    `header_read` and `absent`. `installed` becomes a 1-bit field in its own byte, at the
    place it has now, and the mark that the pace has fallen is a second bit of that byte.
  - The decoder's mode byte of the record it has just read is a `uint8_t` after `settling`
    in `OdrgDecoder` (`core/src/odrg_decoder.h`), in the padding before `settle_found`,
    which is of the size of an `int` (`settling` is at offset 789, `settle_found` at 792).
  - Checked with GCC 16.1.0 on this computer: `Upload` is 72 bytes with these fields, as
    it is now, and `OdrgDecoder` 832.
  - No field, block or table grows. `sizeof(Upload)` and `sizeof(OdrgDecoder)` stay, the
    core object stays at 3,712 bytes, and the table of "Memory" in
    [core.md](../../docs/core.md) is unchanged.
- **10. The decisions.**
  - No decision of [decisions.md](../../docs/decisions.md) changes. "The board takes the
    file only after it has decoded all of it, while the show goes on playing" stays. So
    do the accepted rates of 20 to 50 and the budgets of seed 31.
  - The change log gets an entry at its end, dated 2026-11-06. It records the owner's
    approval of that day in the words quoted above; that the upload's check now takes its
    steps at every refresh, charged by their work and paced by the refresh rate, instead
    of one record at a refresh in step; and that a board already at 20 or 21 a second
    shows about 19 while it checks an upload, where before its check never ended.
  - The entry of seed 07 in the log ("its check takes as long as the animation lasts") is
    not edited. The new entry names it.
- **What stays.**
  - Every command, reply and refusal, and the commands' list.
  - The order of the steps, the verdicts, the reasons and the fault's context.
  - The check after the start, the check of a drive's file and a catalog's rebuild, with
    their in-step pacing.
  - Playback, its 131,072 bytes a refresh, and the LED data of every refresh.
  - The 60 s quiet timer, the second decoders and their hand-over to the other checks.
  - The upload's data phase and its speed. Sending 498 KB at the 19 KB a second the phone
    saw takes about 26 s, and that is not this seed's.
  - The firmware's sources, its pacing of storage calls, and the APK's other screens.
- **The pages.**
  - [core.md](../../docs/core.md):
    - "Uploads and the check", the bullet "The check": the charge, the debt, the pace
      and the time;
    - "Bounded work": "The steps of the checks", and a row of "The budgets" for the
      upload's check, 256 to 2,048 a refresh;
    - the test host's `decode --taken`.
  - [commands.md](../../docs/commands.md), `busy` of `upload end`: the check's time by the
    budget, about 8 s for 14,399 small frames at 50 refreshes a second, and about 2,048
    bytes of body a refresh at most on average.
  - [android-app.md](../../docs/android-app.md): the Checking line after the Sending line,
    the time, and the corrected time of the check; the same for the text and clock forms.
  - [emulator.md](../../docs/emulator.md): "After 10800 seconds of `busy`", written as
    `tests/emulator/test_docs.py` formats `BUSY_SECONDS`, with no thousands separator.
  - [firmware.md](../../docs/firmware.md):
    - after the measured upload checks of 2026-10-12, a paragraph saying that the check is
      paced by the budget since this seed, with the estimate of point 5. The dated figures
      stay as they are;
    - step 7 of the owner's checks: the time to `{"ok":true}` for the hello-bench file,
      now a second or less after the last piece.
  - [decisions.md](../../docs/decisions.md): the entry of point 10, at the end of the
    change log.
  - [drifts.md](../../docs/drifts.md): an entry at its end, "Seed 81: the upload check at
    full speed", with the measurements of point 5 and those of the emulator test, the time
    it took and the `fps` read during it.
  - `AGENTS.md`: the line of this seed in "What is coming", kept true as the work goes.
- **Tests.**
  - In the core suite, `python core/build.py test`:
    - **Seen failing first:** the test that replaces
      `test_a_host_that_is_always_late_never_ends_the_check_and_the_upload_goes_after_60_seconds`.
      A host refreshes every 45 ms, so no refresh is in step, and uploads
      `support.clip(54, 60, 6, (20,) * 300)`: 300 records of 60 x 6 with a palette of 5,
      about 148 bytes each. Its `upload end` answers `{"ok":true}` at the refresh the
      reference player gives, 76 after the last byte by the rule, and within 100. Today it
      answers `busy` until the upload is discarded, then `no-upload`.
    - **Seen failing first:** the tracked clock
      `collection/card/clocks/time-original-5-every-row-another-time.odrg`, uploaded to a
      board without show files (seed 76). `upload end` answers `{"ok":true}` within these
      refreshes after the last byte (the rule's counts of point 5 in brackets):
      - at most 400 with a refresh every 20 ms (351 to 380), where today it needs 14,401;
      - at most 400 every 30 ms (340 to 359);
      - at most 1,300 every 45 ms (1,221);
      - at most 2,400 every 50 ms (2,322 to 2,331), with no `no-upload` on the way.

      The file is then listed with its 471,095 bytes.
    - The reference player of `tests/core/support.py` states the charge, the debt and the
      pace a second time. Every test that compares the core's lines with it passes, so
      the rule is pinned refresh for refresh. It takes the charge of each step that calls
      the decoder from the core's decoder through the test host, as `found_in` takes from
      it today where in a body a fault lies. For that, the test host's `decode` gains
      `--taken`. With it, `decode` prints `header ...` as today, then one line
      `taken <bytes> <charge>` after each call of the decoder (`next` or `finish`), with
      ` pending` at its end for a call that gave `pending`, then `end` or
      `rejected <reason>`. It prints no `frame` lines, so the clock's 14,399 pictures are
      not printed. For a container of a text or a clock it prints the `container` line
      and no `taken` line, and the reference player charges its three steps 0, so they
      fall in one refresh. `--taken` gets its own parser in `tests/core/support.py`;
      `found_in` and `decode_each` stay as they are.
    - The fade of 60 x 60, three bytes a pixel, uncompressed, of point 5, made in the
      test with `odrig.odrg.encode`, uploaded under a host that refreshes every 20 ms:
      the core's lines are the reference player's, refresh for refresh. With
      `--trace-read-at`, on a board without show files (seed 76), which plays nothing
      from storage, the bytes `read_at` gives from `upload.part` within one poll are
      never more than 2,048, plus the file's largest step, plus 256.
    - The pace, pinned against the reference player:
      - a host that refreshes every 20 ms, then every 50 ms for three seconds, then every
        20 ms again during the check: the pace falls, sets the mark, and rises again from
        50 a second;
      - a host that refreshes every 30 ms, then every 60 ms from the start of the second
        after the pace rose, for half a second, then every 30 ms again: the pace falls at
        that second's middle and does not rise again at 33 a second.
    - Every invalid vector still gets its `bad-file` reason, now at the refresh the
      reference player gives; a slice of settling ends its refresh's steps and leaves no
      debt. `--read-back-fails` and `--read-back-differs` still give `storage-error`. A
      host that asks for no refresh for 60 s still loses the upload.
    - The tests that pinned F + 2 refreshes or the in-step rule (`TheCheck`,
      `tests/core/test_upload.py:516-635`, and its neighbours) are rewritten to the new
      rule. They count refreshes from the reference player, and none of them pins the old
      pacing.
  - In the emulator suite: the tracked clock is uploaded over HTTP to an emulator started
    on an empty folder (seed 76). `upload end` answers `{"ok":true}` within 120 s after the
    last byte; the rule gives 7.6 s at 50 a second, 49 s at 25 and 55 s at 22. The test
    prints the time it took and the `fps` that `status` reported during the check, and the
    drift gives both. Tests that need a `busy` reply upload a file whose check takes
    several refreshes at pace 3, such as that clock, about 350. A small clip may now be
    checked in the refresh after its last byte.
  - In the command tool's tests: `BUSY_SECONDS` is 10,800, the resend every 0.2 s is
    unchanged, and the page names the new figure. The test of the limit
    (`tests/emulator/test_tool.py:1075-1083`) feeds more than 54,000 `busy` replies.
  - In the app's suite, with the stand-in targets of `tests/app/test_upload.py`:
    - On Upload, a target answers `busy` to `upload end` for 3.5 s by its own clock,
      counted from its first `upload end`, then `{"ok":true}`. After the Sending line the
      sampled texts of the line read `Checking the animation on the installation: 0:00`
      first, each later one one second more than the one before, `0:01` and `0:02` among
      them. No text with `%` or `KB a second` appears after the last byte, and `Cancel` is
      shown. Then the success message comes and the line is hidden.
    - `test_a_gif_is_uploaded_as_the_file_the_command_line_makes_and_plays`
      (`tests/app/test_upload.py:79`) now expects Sending texts, then Checking texts, in
      that order.
    - The same with a text's upload and a clock's Save in the forms.
    - `Cancel` while the line says `Checking`: `upload cancel` is sent, `Cancelled.` is
      shown, and the text does not change after it.
- **Where it lands.** A branch `seed-81-the-upload-check-at-full-speed` from `master`, as a
  pull request of its own.

## Required Behavior

1. After the last byte of an upload, the core checks the whole file at every refresh, in
   step or late. Each step is charged by its work: its body bytes, and n / 32 more for a
   coded record with the run bit and predictor 1 or 2; the header, a text's or a clock's
   payload and the end are charged 0. A refresh takes steps while their charge is below
   its allowance, its budget of 256 to 2,048 less its debt, at most 64 and the first
   always. What a refresh's steps pass the allowance by is a debt of up to 15 times 256,
   and a refresh whose debt is a whole budget or more takes no step and pays it.
2. The budget starts at 512. Once a second, by the refreshes of the second before, it
   falls below 21, rises at 40 or more, and rises at 27 or more until it has first fallen.
   In the second after a rise it falls back at the middle when that second has had 11
   refreshes or fewer. A board at 22 a second or more before the check stays at 20 or
   more during it; one at 20 or 21 shows about 19.
3. Every verdict, reason and fault context of the check stays as it is. A check that does
   not end with `{"ok":true}` leaves the show as today.
4. On a board that refreshes 30 times a second or more before the check, while a show
   that is not dense plays, the owner's 14,399-frame clock is checked within 30 s of its
   last byte.
5. From the last byte until `upload end` answers, the app's line says
   `Checking the animation on the installation: <m>:<ss>`, counting from the last byte by
   the app's own clock. This holds for every upload through the job. `Cancel` still stops
   the upload.
6. The pages give the new times. The command tool waits up to 10,800 s of `busy`.
7. No command, reply, reply member or memory block changes or grows, and no firmware
   source changes.

## Definition Of Done

1. On the up-to-date branch, `python tests/run.py` passes every suite that works on this
   computer, with the tests above. The firmware suite, run on its own with `ODRIG_TOOLS`
   set, fails only the 3 known tests of this computer's shared-toolchain junction.
2. The pull request's checks on GitHub pass, the firmware workflow among them, which builds
   the installation's image and the spare's from the branch.
3. The APK built from the branch, and the spare's image `odrig-firmware-n8r2.bin` built on
   Windows from the branch by `python firmware/fw.py build --module n8r2` and verified by
   `python firmware/verify_build.py --module n8r2`. Both go on the Drive under
   `odrig archive/seed-81/` with their `.sha256`, and their file links are sent to the
   owner in words.
4. The owner's check on the spare board, with that image flashed and that APK. These
   checks only a person can make:
   1. Note what the spare plays, and the Show screen's `N refreshes a second` while it
      plays it.
   2. Upload the rotated clock
      `clocks_rotated_right/time-original-5-every-row-another-time.odrg` (498,211 bytes)
      to `Internal storage`.
   3. After the Sending line, the line says
      `Checking the animation on the installation: 0:00` and counts up once a second.
   4. The success message `Uploaded as animation <id> <file>. It plays in the playlist.`
      comes. While what plays is not dense, it comes by `0:30` when the rate noted in
      step 1 was 30 or more, by `1:00` at 25 to 29, and by `2:30` below 25. While a dense
      animation plays, note the time; it has no limit.
   5. The Show screen's rate, read while the line says `Checking`, is 20 or more each time
      when the rate of step 1 was 22 or more. At 20 or 21 before, note the lowest rate.
   6. The clock then plays on the LEDs.
   7. With a card in the spare, upload the same file to the card, and note the time the
      Checking line reached and the lowest rate read during it. This step has no limit.

   Until the owner reports these, the check is open, and the hand-over says so.

## Open Questions

None. The owner approved the fix on 2026-11-06. Decided here:

- the check stays whole, with every verdict, reason and fault context unchanged;
- it takes steps at every refresh, in step or late, each charged its body bytes and n / 32
  more for a record that walks the whole picture, the header, a drawn payload and the end
  0, because the processor time of a step follows that charge for every kind of record
  measured;
- a refresh takes steps within its allowance, its budget (256, 512, 1,024 or 2,048) less a
  debt of up to 15 times 256, at most 64 steps and the first always; a refresh whose debt
  is a whole budget or more rests; a slice of settling leaves no debt;
- the budget starts at 512 and changes once a second by `fps`: down below 21, up from 40,
  and up from 27 on trial until it has first fallen; a trial falls back at the middle of
  the next second when that second has had 11 refreshes or fewer;
- a board at 22 or more stays at 20 or more during the check, and one at 20 or 21 shows
  about 19, where before its check never ended; the change log records it;
- a late refresh gets no extra steps for the grid times it skipped;
- the pace, the debt and the mark of a fall are 7 bits of the upload's record, with
  `installed` made a bit, and the decoder's mode byte sits in its padding; no memory grows;
- the firmware's sources stay, and the check takes no step at the calls between
  refreshes, because the core reads no clock inside a call;
- the target is the owner's file within 30 s on a board at 30 refreshes a second or more
  while a show that is not dense plays, from this computer's measurement and the board's
  documented timings; an upload to the card is checked alike and not estimated;
- the app shows `Checking the animation on the installation: <m>:<ss>` by its own clock,
  for every upload through the job, with no fraction, `Cancel` kept;
- the command tool waits 10,800 s;
- no decision of `docs/decisions.md` changes, and the change log records the owner's
  approval in their words;
- the test host's `decode` gains `--taken` for the reference player;
- no command, reply member or message is added, and the seed is a pull request of its own
  from `master`.
