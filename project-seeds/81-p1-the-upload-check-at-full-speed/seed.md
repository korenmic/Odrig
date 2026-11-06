# The upload check at full speed

## Summary

After the last byte of an upload, the core checks the whole file before it installs it.
Today the check reads one frame record at a refresh, and only at a refresh that came one
grid time after the one before. A file of F frame records needs F + 2 such refreshes. At
R refreshes a second there are 2R - 50 of them a second, and none at 25 or fewer. The
owner's rotated clock has 14,399 frames. Its check took 288 s at a perfect 50 a second,
24 minutes at 30, and hours near 26. Meanwhile the app showed a frozen `Sending: 100%`.

This seed changes how much the check does at a refresh. At every refresh, in step or
late, it takes steps until those steps have read 256, 512, 1,024 or 2,048 bytes of the
file's body, at most 64 steps and always at least one. The budget changes once a second,
by the refreshes the second before had, so that the rate stays at 20 or more.

The check still reads the whole file, and its verdicts and reasons do not change. The app
shows `Checking the animation on the installation: 0:12` from the last byte until
`upload end` answers. The time comes from the app's own clock. It shows on Upload and in
the text and clock forms. The pages give the new times, and the command tool waits up to
1,800 s.

The core was measured in a host build on this computer, and the figures were scaled by the
board's documented timings. By that estimate, the owner's file is checked in about 7 to 9
s on a board that refreshes 50 times a second with room to spare, and in about 14 s at 25.
No command, reply, memory block or firmware source changes.

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
- Seed 63, completed: ready-made files uploaded to the board or the card, through the same
  job.
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
    settling of a defect. The step sets `upload.progress = now` (`:96`).
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
    a second.
  - The core suite pins the old pacing. `TheCheck` in `tests/core/test_upload.py:516-570`
    has, among others,
    `test_a_host_that_is_always_late_never_ends_the_check_and_the_upload_goes_after_60_seconds`.
    The reference player in `tests/core/support.py:1191-1197` takes one step after each
    refresh in step.
- **1. The check takes a budget at every refresh.**
  - At every refresh, in step or late, the check takes steps once the LED data is
    complete, where it takes its one step today. It goes on while all of these hold:
    - the check has not ended;
    - the steps of this refresh are fewer than 64;
    - the body bytes those steps took are fewer than the budget of point 2.

    The first step of a refresh is always taken. So a step may pass the budget by its own
    bytes, at most one step's worth.
  - A step stays what it is today: the header, one frame record, the end, or one slice of
    settling. The body bytes of a step are what the decoder's count `body_read` grew by in
    it. For a compressed body these are inflated bytes. The palette is counted with the
    first record, and a slice of settling counts the bytes it took, up to 32,768. The
    header and the end take none. A text or a clock reads its payload whole in one step,
    as today, and takes three steps in all.
  - A late refresh gets the same budget as one in step. Nothing is added for the grid
    times it skipped: a host that is late has no time to spare.
  - Only the refreshes the host asks for take steps. A poll that produces no refresh takes
    none, as today.
- **2. The pace.**
  - The budget is 256 bytes of body shifted left by the pace: 256, 512, 1,024 or 2,048
    bytes, for a pace of 0 to 3.
  - The pace is set to 1 (512 bytes) when the last byte has arrived and the check begins.
  - At the first refresh of a new whole second, while the check runs, the pace changes by
    the count of refreshes in the second just ended (`player_fps`, what `status` reports
    as `fps`). It goes up by one, to 3 at most, at 25 or more. It goes down by one, to 0
    at least, at fewer than 21. Otherwise it stays. In the first second after the core's
    start, which has no whole second before it, the pace does not change.
  - The basis: rule 12 accepts any rate from 20 to 50. A whole second below 21 is taken as
    the check's cost, so the pace falls back. A second at 25 or more leaves room, so it
    rises. The core cannot tell its own work from the host's, because it reads no clock
    inside a call. The refreshes of a whole second are the measure it has, and they are
    what the owner reads.
  - By the estimates of point 5, one rise adds at most about 8.1 ms to a refresh, from
    pace 2 to pace 3. From a rate of 25, 40 ms a refresh, that leaves about 20.8 a second.
    A board whose costs are higher than estimated, such as the spare with its quad PSRAM,
    falls back within a second.
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
  progress. A check now moves at every refresh, so the 60 s timer discards the upload only
  when the host asks for no refresh for 60 s, or when the check has ended and nobody asked
  `upload end` for 60 s. Both are as today. `upload end` stays `busy` while the check runs.
- **5. The target, and its basis.**
  - Measured on 2026-11-06 on this computer: an Intel Core i7-14700 running Windows 11,
    GCC 16.1.0 of WinLibs with `-O2`. The core sources of `73da1103` were linked into a
    scratch host. The host held the files in memory, uploaded the file and polled every 20
    ms of a virtual clock, timing each poll. Three runs agreed.

    | File | Steps | Body bytes | Processor time of the whole check |
    |---|---:|---:|---:|
    | The owner's rotated clock, 498,211 bytes, CRC-32 `4894fa74` | 14,401 | 627,470, at most 130 in a step | 22.6 ms, 1.57 µs a step |
    | The tracked clock `collection/card/clocks/time-original-5-every-row-another-time.odrg`, 471,095 bytes | 14,401 | 624,310, at most 139 | 23.0 ms |
    | The dense 60 x 60 clip of 10 s of `tests/board/support.py`, compressed, 1,372,244 bytes | 502 | 1,462,220 | 44.3 ms |
    | The same clip uncompressed, 1,462,236 bytes | 502 | 1,462,220 | 25.1 ms |

  - The board's speed at the check. The board checked that dense clip at power-on in 6.0 s
    compressed and 4.2 s uncompressed, with the reading included
    ([decisions.md](../../docs/decisions.md), "Emulator"). That makes the board 135 to
    167 times slower than this computer at the check. Beside a send to twenty outputs on
    the other processor core, the core's work takes about 1.4 times as long: 12.3 ms
    becomes 16 to 17, and 8.6 ms becomes 12 to 13
    ([firmware.md](../../docs/firmware.md)).
  - So the whole check of the owner's file is about 3.0 to 3.8 s of the core's work on the
    board, and 4.3 to 5.3 s beside the sends.
  - The cost of one refresh at each pace, from the median processor time of the owner's
    file, is:

    | Pace | Budget | Here | On the board, beside the send |
    |---|---:|---:|---:|
    | 0 | 256 bytes | 10 µs | at most 2.3 ms |
    | 1 | 512 bytes | 19 µs | at most 4.7 ms |
    | 2 | 1,024 bytes | 37 µs | at most 8.7 ms |
    | 3 | 2,048 bytes | 72 µs | at most 16.8 ms |

    A dense frame record takes more than any budget alone. Its check takes one record a
    refresh, 12 to 17 ms, as one step costs today. At 50 a second the board's send takes
    15.6 to 16.4 ms of each 20 ms on one processor core. The core's work and the copy of
    4.1 ms share the other core, so pace 3 still leaves a light show at about 45 to 50 a
    second.
  - The time the rule gives for the owner's file was worked out from the bytes of each of
    its 14,401 steps. "Today" is the measured time.

    | Host refreshes | Refreshes | Time | Today |
    |---|---:|---:|---:|
    | every 20 ms, 50 a second | 366 | 7.3 s | 288 s |
    | every 25 ms, 40 a second | 353 | 8.8 s | 480 s |
    | every 30 ms, 33 a second | 346 | 10.4 s | 864 s |
    | every 40 ms, 25 a second | 353 | 14.1 s | never |
    | every 45 ms, 22 a second | 1,171 | 52.7 s | never |
    | every 50 ms, 20 a second | 2,231 | 111.5 s | never |

  - The target, therefore, for the owner's file:
    - On a board that refreshes 30 times a second or more before the check, within 30 s.
      That is about 7 to 11 s when the show leaves the board's processor room, and up to
      about 30 s when the show's own playback fills the processor, since the pace then
      stops at 1 or 2.
    - At 25 to 29 a second, within a minute.
    - Only a board whose own playback holds it below 25 takes longer, about two minutes
      at 20 a second.

    Throughout, the rate stays at 20 or more. These figures are an estimate until the
    owner's check of the Definition Of Done measures them.
- **6. The firmware.**
  - No source of the firmware changes. It hosts the core as it is, and its build takes
    the new core. The usermod's requester polls once the loop has copied the last
    picture. On a board whose loop is the slower side, no poll comes between refreshes, so
    giving the check that idle time would need a second entry into the core. That would
    change the host contract, the emulator and every host. The per-refresh budget reaches
    the target without it.
  - Every call stays bounded. The check adds to a refresh at most its budget and one step,
    in the 50 ms of one call on the board.
- **7. The app's line while the board checks.**
  - The job of `app/www/upload.js` gains an optional `checking(since)`. It is called once,
    when the reply to the last `upload data` has come, with `performance.now()` of that
    moment. A job that ends before the last byte never calls it.
  - From then until the job ends, the line of the screen that runs it says
    `Checking the animation on the installation: <m>:<ss>`. That is the time since
    `since`, in whole seconds, minutes without a leading zero and seconds in two digits
    (`0:00`, `0:12`, `1:05`, `61:05` past an hour). A timer of the screen writes it again
    every second, and its first text is written at once.
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
- **8. The command tool.** `BUSY_SECONDS` of `odrigctl/content.py` becomes 1,800. The core
  already discards an upload whose check does not move for 60 s, so the limit only guards
  against a target that answers `busy` for ever. A file whose records each hold more
  body than the budget is checked one record a refresh. One such file is
  `collection/card/space/space-scan-10x.odrg`: 34,410,601 bytes, 18,004 frames, 2,061
  bytes of body a record on average. With the rule of point 2 it takes about 15 minutes
  at 20 refreshes a second, past 600 s, worked out from the bytes of each of its steps
  measured as in point 5. `upload: checking` and the resend every 0.2 s stay.
- **9. Memory.**
  - The pace is two bits in the bit field of the upload's record (`struct Upload`,
    `core/src/core_state.h:126-142`), beside `header_read` and `absent`.
  - No field, block or table grows. The core object stays at 3,712 bytes, and the table of
    "Memory" in [core.md](../../docs/core.md) is unchanged.
- **10. The decisions.**
  - No decision of [decisions.md](../../docs/decisions.md) changes. "The board takes the
    file only after it has decoded all of it, while the show goes on playing" stays. So
    do the accepted rates of 20 to 50 and the budgets of seed 31.
  - The change log gets an entry at its end, dated 2026-11-06. It records the owner's
    approval of that day in the words quoted above, and that the upload's check now takes
    a budget of body bytes at every refresh instead of one record at a refresh in step.
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
    - "Uploads and the check", the bullet "The check": the budget, the pace and the time;
    - "Bounded work": "The steps of the checks", and a row of "The budgets" for the
      upload's check;
    - the test host's `decode --taken`.
  - [commands.md](../../docs/commands.md), `busy` of `upload end`: the check's time by the
    budget, about 7 to 9 s for 14,399 small frames at 50 refreshes a second, and one
    dense frame a refresh.
  - [android-app.md](../../docs/android-app.md): the Checking line after `Sending`, the
    time, and the corrected time of the check; the same for the text and clock forms.
  - [emulator.md](../../docs/emulator.md): 1,800 seconds of `busy`.
  - [firmware.md](../../docs/firmware.md):
    - after the measured upload checks of 2026-10-12, a paragraph saying that the check is
      paced by the budget since this seed, with the estimate of point 5. The dated figures
      stay as they are;
    - step 7 of the owner's checks: the time to `{"ok":true}` for the hello-bench file,
      now a second or less after the last piece.
  - [decisions.md](../../docs/decisions.md): the entry of point 10, at the end of the
    change log.
  - [drifts.md](../../docs/drifts.md): an entry at its end, "Seed 81: the upload check at
    full speed", with the measurements of point 5 and those of the emulator test.
  - `AGENTS.md`: the line of this seed in "What is coming", kept true as the work goes.
- **Tests.**
  - In the core suite, `python core/build.py test`:
    - **Seen failing first:** the test that replaces
      `test_a_host_that_is_always_late_never_ends_the_check_and_the_upload_goes_after_60_seconds`.
      A host refreshes every 45 ms, so no refresh is in step, and uploads a clip of 300
      records of 60 x 6. Its `upload end` answers `{"ok":true}` within 310 refreshes after
      the last byte. Today it answers `busy` until the upload is discarded, then
      `no-upload`.
    - **Seen failing first:** the tracked clock
      `collection/card/clocks/time-original-5-every-row-another-time.odrg`, uploaded to a
      board without show files (seed 76). `upload end` answers `{"ok":true}` within these
      refreshes after the last byte:
      - at most 400 with a refresh every 20 ms, where today it needs 14,401;
      - at most 400 every 30 ms;
      - at most 1,300 every 45 ms;
      - at most 2,400 every 50 ms, with no `no-upload` on the way.

      The file is then listed with its 471,095 bytes.
    - The reference player of `tests/core/support.py` states the budget and the pace a
      second time. Every test that compares the core's lines with it passes, so the rule
      is pinned refresh for refresh. It takes the body bytes of each step from the core's
      decoder through the test host, as `found_in` takes the sound records today. For that,
      the test host's `decode` gains `--taken`: after each call of the decoder (`next` or
      `finish`, a call that gives `pending` included) it prints `taken <bytes>`, the
      body bytes that call took, before the line the call gives, if any.
    - A host that refreshes every 20 ms, then every 50 ms for three seconds, then every 20
      ms again during the check gives the reference player's lines. That pins the pace's
      fall and rise.
    - With `--trace-calls`, no poll during the check of an uncompressed file reads more
      than 2,048 bytes plus one record plus 256 bytes.
    - Every invalid vector still gets its `bad-file` reason, now at the refresh the
      reference player gives. `--read-back-fails` and `--read-back-differs` still give
      `storage-error`. A host that asks for no refresh for 60 s still loses the upload.
    - The tests that pinned F + 2 refreshes or the in-step rule (`TheCheck` and its
      neighbours) are rewritten to the new rule. They count refreshes from the reference
      player, and none of them pins the old pacing.
  - In the emulator suite: the tracked clock is uploaded over HTTP to an emulator started
    on an empty folder (seed 76). `upload end` answers `{"ok":true}` within 15 s after the
    last byte, and the test reports the time it took. The drift gives it. Tests that need
    a `busy` reply upload a file whose check takes several refreshes at pace 3, such as
    that clock. A small clip may now be checked in the refresh after its last byte.
  - In the command tool's tests: `BUSY_SECONDS` is 1,800, the resend every 0.2 s is
    unchanged, and the page names the new figure.
  - In the app's suite, with the stand-in targets of `tests/app/test_upload.py`:
    - On Upload, a target answers `busy` to `upload end` for 2.5 s by the app's clock,
      then `{"ok":true}`. After `Sending: 100%` the line reads
      `Checking the animation on the installation: 0:00`, then `0:01` and `0:02`. No line
      with `%` or `KB a second` appears after the last byte, and `Cancel` is shown. Then
      the success message comes and the line is hidden.
    - The same with a text's upload and a clock's Save in the forms.
    - `Cancel` while the line says `Checking`: `upload cancel` is sent, `Cancelled.` is
      shown, and the text does not change after it.
- **Where it lands.** A branch `seed-81-the-upload-check-at-full-speed` from `master`, as a
  pull request of its own.

## Required Behavior

1. After the last byte of an upload, the core checks the whole file at every refresh, in
   step or late. At each refresh it takes steps within a budget of 256 to 2,048 bytes of
   body, at most 64 steps, and at least one step.
2. The budget starts at 512 bytes. Once a second it rises at 25 refreshes a second or
   more and falls below 21, so that the rate stays at 20 or more during the check.
3. Every verdict, reason and fault context of the check stays as it is. A check that does
   not end with `{"ok":true}` leaves the show as today.
4. On a board that refreshes 30 times a second or more before the check, the owner's
   14,399-frame clock is checked within 30 s of its last byte.
5. From the last byte until `upload end` answers, the app's line says
   `Checking the animation on the installation: <m>:<ss>`, counting from the last byte by
   the app's own clock. This holds for every upload through the job. `Cancel` still stops
   the upload.
6. The pages give the new times. The command tool waits up to 1,800 s of `busy`.
7. No command, reply, reply member, memory block or firmware source changes.

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
   1. Note the Show screen's `N refreshes a second` while the spare plays its show.
   2. Upload the rotated clock
      `clocks_rotated_right/time-original-5-every-row-another-time.odrg` (498,211 bytes)
      to `Internal storage`.
   3. After `Sending: 100%, ...`, the line says
      `Checking the animation on the installation: 0:00` and counts up once a second.
   4. The success message `Uploaded as animation <id> <file>. It plays in the playlist.`
      comes. It comes by `0:30` when the rate noted in step 1 was 30 or more, by `1:00`
      at 25 to 29, and by `2:30` below 25.
   5. The Show screen's rate, read while the line says `Checking`, is 20 or more each time.
   6. The clock then plays on the LEDs.

   Until the owner reports these, the check is open, and the hand-over says so.

## Open Questions

None. The owner approved the fix on 2026-11-06. Decided here:

- the check stays whole, with every verdict, reason and fault context unchanged;
- it takes steps at every refresh, in step or late, within a budget of body bytes (256,
  512, 1,024 or 2,048), at most 64 steps and at least one;
- the budget starts at 512 and changes once a second by `fps`: up at 25 or more, down
  below 21, so that the rate stays within rule 12;
- a late refresh gets no extra steps for the grid times it skipped;
- the pace is two bits of the upload's record, and no memory grows;
- the firmware's sources stay, with no time between refreshes, because the per-refresh
  budget reaches the target with every host alike;
- the target is the owner's file within 30 s on a board at 30 refreshes a second or more,
  estimated at 7 to 11 s when the show leaves the processor room, from this computer's
  measurement and the board's documented timings, and longer only on a board held below
  25 by its own playback;
- the app shows `Checking the animation on the installation: <m>:<ss>` by its own clock,
  for every upload through the job, with no fraction, `Cancel` kept;
- the command tool waits 1,800 s;
- no decision of `docs/decisions.md` changes, and the change log records the owner's
  approval in their words;
- the test host's `decode` gains `--taken` for the reference player;
- no command, reply member or message is added, and the seed is a pull request of its own
  from `master`.
