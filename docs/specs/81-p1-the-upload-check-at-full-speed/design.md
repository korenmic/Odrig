# Design

## Boundaries

The core changes when the check of an uploaded file takes its steps and how many, and
nothing of what a step does. The decoder keeps one byte more of what it read, in its
padding, and offers the charge of its last call. The test host prints the charges and,
on request, the pace and the debt; the reference model of the core's tests follows the
rule a second time. The app's upload job tells its screen when the last byte is
acknowledged, and the screens show the Checking line by the app's clock. The command tool
waits longer. The firmware, the emulator's own code, the converter, the Python library,
the command list and every reply are not changed. No decision of `docs/decisions.md`
changes; its change log gets an entry.

Requirements 1 to 14 refer to [requirements.md](requirements.md).

## The decoder: the mode of the record and the charge of a call

`core/src/odrg_decoder.h`:

- `const uint32_t kWalkDivisor = 32;` beside `kSettleSliceBytes`, with its comment: a
  coded record with the run bit and predictor 1 or 2 walks every position of the picture
  whatever its bytes, and is charged n / kWalkDivisor beside them.
- In `OdrgDecoder`, after `uint8_t settling;`, `uint8_t record_mode;`: the mode byte of the
  record the last call of `next` decoded whole; 0 after any other call and after `open`.
  It sits in the padding before `settle_found`: `settling` is at offset 789 and
  `settle_found` at 792 on this computer's GCC, so `sizeof(OdrgDecoder)` stays 832.
- `uint32_t charge_since(uint64_t before) const;` after `finish`, with its comment: the
  work of the call of `next` or `finish` that has just ended, in bytes of the body: the
  bytes it took since `before`, a value of `body_read` taken before the call, and
  n / kWalkDivisor more when it decoded a whole record that walks the picture.

`core/src/odrg_decoder.cpp`:

- `open` sets `record_mode = 0` beside the other fields it resets.
- `next` sets `record_mode = 0` first, before `if (settling)`, and
  `record_mode = static_cast<uint8_t>(mode);` just before its `return kNone` at the end of
  a whole record. `finish` sets `record_mode = 0` first.
- `charge_since`: `walked` is `(record_mode & kRunBit) != 0` and the predictor
  `(record_mode >> 4) & 3` is 1 or 2; it returns
  `static_cast<uint32_t>(body_read - before) + (walked ? n / kWalkDivisor : 0)`. `kRunBit`
  stays in the file's anonymous namespace.

Playback and the other checks never call `charge_since`; the one byte they write at each
record is all they pay.

## The upload's record

`core/src/core_state.h`, `struct Upload`, the bit field after `reason`:

```cpp
uint8_t header_read : 1; // the first step of the check has been taken
uint8_t absent : 1;      // the external destination must remain absent
uint8_t pace : 2;        // the check's budget is kUploadChargeUnit << pace
uint8_t debt : 4;        // the charge the check owes, in kUploadChargeUnit
uint16_t id;
char name[33];
uint8_t installed : 1;   // the file is installed: the id, the name, the size and the CRC-32 are its
uint8_t pace_fell : 1;   // the pace has fallen during this check
uint32_t size;
...
```

The fields keep their places: the first byte of bits is at offset 3, `installed` and
`pace_fell` share the byte at offset 39, and `sizeof(Upload)` stays 72. Every assignment
to a bit field is of a `uint8_t` already in its range, as GCC, Clang and MSVC take with
warnings as errors. `upload_begin`, `upload_begin_external` and `upload_begin_known` keep
setting and reading `installed` as today.

## The check at every refresh

`core/src/upload.h`:

- The constants of the rule, each with a comment that says what it is:
  `kUploadChargeUnit = 256` (a budget's and a debt's unit, in bytes of charge),
  `kUploadPaceStart = 1`, `kUploadPaceMost = 3`, `kUploadDebtMost = 15`,
  `kUploadStepsMost = 64` (the most steps of one refresh), `kUploadRateSlow = 21` (a second
  with fewer refreshes lowers the pace), `kUploadRateSteady = 40` (a second with this many
  or more raises it), `kUploadRateTrial = 27` (a second with this many or more raises it
  while it has not fallen), `kUploadMiddleMs = 500` and `kUploadTrialFewest = 11` (a
  second that has had this many refreshes or fewer at its middle lowers it).
- `upload_step` leaves the header; in its place
  `void upload_refresh(Core &core, uint64_t now, bool new_second);`, whose comment says:
  called at every refresh once its LED data is complete, with whether it is the first
  refresh of a new whole second; while an uploaded file is checked, it sets the pace by
  the refresh rate and takes the steps the budget and the debt allow (requirements 3
  and 4).
- The comment of `kUploadQuietMs` names a refresh of the check as progress in place of a
  step of the check.

`core/src/upload.cpp`:

- `upload_step` moves into the anonymous namespace as
  `uint32_t upload_step(Core &core, bool *pending)`. It sets `*pending = false` first and
  returns the charge of the step it takes. It no longer sets `upload.progress`. Its
  branches stay as they are, and:
  - the header branch returns 0, whatever it found;
  - the record branch of a drawn payload returns 0;
  - the record branch of frames reads `const uint64_t before = checker.decoder.body_read;`
    before `next` and takes `checker.decoder.charge_since(before)` after it; when `next`
    gave `kPendingWork` it sets `*pending = true` and returns that charge; otherwise it
    goes on as today and returns the charge, also when the step ended the check;
  - the end branch does the same around `content_finish` for frames, `*pending` for
    `kPendingWork`; for a drawn file, whose `content_finish` calls no decoder, the charge
    is 0.
  The fault's context, `note_fault(core, kWorkUpload, upload.name, record, ...)`, and
  `check_ended` are as today.
- `upload_refresh(core, now, new_second)`:

  ```cpp
  Upload &upload = core.upload;
  if (upload.state != kUploadChecking) return;
  upload.progress = static_cast<uint32_t>(now);
  if (new_second) {
      const uint32_t rate = player_fps(core, now);
      if (rate < kUploadRateSlow) pace_down(upload);
      else if (rate >= kUploadRateSteady || (rate >= kUploadRateTrial && !upload.pace_fell)) pace_up(upload);
  }
  if (!upload.pace_fell && (now - core.t0) % 1000 >= kUploadMiddleMs && core.count_running <= kUploadTrialFewest) {
      pace_down(upload);
  }
  const uint32_t budget = kUploadChargeUnit << upload.pace;
  const uint32_t owed = kUploadChargeUnit * upload.debt;
  if (owed >= budget) {
      upload.debt = static_cast<uint8_t>(upload.debt - (budget / kUploadChargeUnit));
      return;
  }
  const uint32_t allowance = budget - owed;
  uint32_t charge = 0;
  bool pending = false;
  for (uint32_t steps = 0; upload.state == kUploadChecking && steps < kUploadStepsMost && charge < allowance; ++steps) {
      charge += upload_step(core, &pending);
  }
  const uint32_t over = pending || charge <= allowance ? 0 : (charge - allowance) / kUploadChargeUnit;
  upload.debt = static_cast<uint8_t>(over < kUploadDebtMost ? over : kUploadDebtMost);
  ```

  `pace_down` lowers the pace by one unless it is 0 and sets `pace_fell`; `pace_up` raises
  it by one unless it is `kUploadPaceMost`. Both are small functions of the anonymous
  namespace. `upload.cpp` includes `player.h` for `player_fps`.
- `upload_data`, at the last byte, where it sets `upload.state = kUploadChecking`, also
  sets `upload.pace = kUploadPaceStart`, `upload.debt = 0` and `upload.pace_fell = 0`.

`core/src/player.cpp`, `player_poll`:

- Before the second is rolled over: `const bool new_second = second != core.second_running;`.
  `second_running` starts at 0, so the refreshes of the first second are never new.
- In place of `if (in_step) { upload_step(core, now); }`: `upload_refresh(core, now, new_second);`
  at the same place, after the LED data is complete and before `check_after_start`. The
  comment above it says that the check of an uploaded file takes its steps at every
  refresh, and the check after the start its own. `in_step` stays for
  `check_after_start`.

A refresh that is late gets the same budget as one in step (1.1, 1.3). A poll that
produces no refresh returns before this point (1.3), and no command calls
`upload_refresh` (1.4). The check after the start, the drive's check and the catalog's
rebuild still wait while an upload is open, as `check_after_start` has it (7.3).

Requirement 6.1 is a decision of this spec: the seed has each step set the progress and a
refresh that pays a debt rest, at most 15 in a row, so a host that refreshed less often
than once in 3.75 s could lose an upload whose check runs. Every refresh of the check now
sets the progress, and the seed's statement of its point 4 holds exactly.

## The test host

`tests/core/host/host.cpp`:

- `decode_one(host, name, slice, taken)`: with `taken`, it prints no `frame` line; it reads
  `body_read` before each call of `decoder.next` and of `content_finish`, and prints after
  the call `taken <body_read - before> <decoder.charge_since(before)>`, with ` pending`
  when the call gave `kPendingWork`. For a drawn container it prints the `container` line
  and no `taken` line. Everything else is as today: `container`, `header`, `end` or
  `rejected <reason>`. `decode(argument, slice, taken)` passes it on.
- The arguments: `decode --taken FILE` and `decode --taken --batch`. The usage line reads
  `odrig_host decode [--slice BYTES | --taken] FILE | --batch`.
- The session option `--trace-check`, `bool trace_check` among the options with its
  comment: in `poll`, the host reads `core_->state.upload.state == odrig::kUploadChecking`
  before `odrig_core_poll`, and when the poll produced a refresh and the check was running
  it prints, after the `data` lines, `check <pace> <debt> <fell>` from
  `core_->state.upload`. The option is in the usage text.
- `docs/core.md`, "The test host", gets the row of `decode --taken` and the row of
  `--trace-check`, in the commit that adds them, as `tests/core/test_docs.py` requires of
  every option of the usage text.

## The reference model

`tests/core/support.py`:

- `_taken(lines)` parses the lines of one file of `decode --taken`: `(bytes, charge,
  pending)` for each `taken` line, ending at `end` or `rejected`. `taken_in(data)` gives
  them for one file through `decode --taken --batch`, kept by content as `found_in` keeps
  its results.
  `taken_each(files)` gives them for several in one run. `found_in`, `decode_each` and
  `_decoded` are not changed.
- `check_steps(data, canvas=None)`: the charges of the steps of the check of a file on a
  canvas, each `(charge, pending)`: `[(0, False)]` for a file whose header or size is
  refused (`header_fault`; with `canvas` None the header is taken to be sound); for a
  text or a clock `[(0, False)] * 2` when `found_in` gives a reason
  and `* 3` otherwise; for frames `[(0, False)]` and then `(charge, pending)` of each line
  of `taken_in(data)`.
- `class CheckPace`, the rule of requirements 3 and 4 a second time, written from the
  requirements, with the constants of the core under the same meanings. It holds the
  steps, the next step, the pace (1), the debt (0) and `fell` (False).
  `refresh(into_second_ms, new_second, last_second, this_second)` applies 4.3 when
  `new_second`, with `last_second` the refreshes of the second just ended, then 4.4 with
  `this_second` the refreshes of the running second, this one included; then 3.2 to 3.4;
  and returns the steps it took. `ended` says whether the last step was taken; `line()`
  gives `check <pace> <debt> <fell>`.
- `check_end(steps, refreshes, t0, first)`: the rule's model over a session. `refreshes`
  are the times of every refresh of the session in order, the ones before the check
  included for the counts of the seconds; the check begins at the refresh with index
  `first`. It returns the index of the refresh at which the check ends, or None. The
  counts follow the core: a second is counted from `t0`, the first refresh of a second is
  new unless its second is 0, and `last_second` is the count of the second before it, 0
  when it had none.
- `refresh_times(polls, t0)`: the times of the polls that produce a refresh by the grid
  rule of "Time, the grid and refreshes" of `docs/core.md`.
- `ReferencePlayer`:
  - `__init__` takes `trace_check=False`, and keeps `self.second_running = 0`.
  - `_judge(data)` returns `(steps, reason, clip)`, `steps` from `check_steps(data,
    self.canvas)`; the reason and the clip as today. `sound_records` is removed: the steps
    come from the core's decoder now.
  - At the last byte of `upload data` the upload gets `"pace": CheckPace(steps)` in place
    of the count of steps.
  - `poll`, after it counted the refresh in `refreshes_in`: `new_second` as the core
    computes it, then `self.second_running = second`. In place of the in-step step: while
    the upload's state is `checking`, `progress = now`, `pace.refresh(...)` with
    `(now - t0) % 1000`, `new_second`, `refreshes_in[second - 1]` (0 for second 0) and
    `refreshes_in[second]`; the state becomes `checked` when `pace.ended`; and with
    `trace_check` the refresh's lines get `pace.line()` after the `data` lines, which
    `answer` prints.
- `tests/core/test_content.py`, `Content.run_both`, gives the reference player
  `trace_check="--trace-check" in options`.

`tests/core/test_upload.py`:

- `Script` keeps the times of its polls. `Script.check(data, short=0)` polls, every 20 ms
  from its clock, as many refreshes as `support.check_end` gives for
  `support.check_steps(data)` (the file is taken to fit the canvas) over the
  script's refreshes so far and the new ones, less `short`; it no longer adds a refresh
  for a check in step. `frames_of` stays for the tests that count records.
- `TheCheck` is rewritten to the new rule:
  - `test_end_is_busy_until_the_check_has_taken_its_steps`: the four clips of today; the
    `busy` replies are the refreshes `check_end` gives.
  - `test_asking_more_often_than_the_grid_does_not_hurry_the_check`: as today, the count of
    refreshes from the reference player.
  - `test_a_late_refresh_takes_its_steps_as_one_in_step`, in place of the test of a
    skipped grid time: the same script, `upload end` answers as the reference player
    gives.
  - `test_a_host_that_is_always_late_never_ends_the_check_and_the_upload_goes_after_60_seconds`
    is removed: `AtEveryRefresh` of `test_upload_check.py` takes its place (13.1).
  - `test_every_invalid_vector_is_a_bad_file_with_the_reason_of_the_reference_decoder`:
    the refreshes of each vector from `check_end` of the reference player's steps, not from
    `sound_records`.
  - `test_a_file_of_another_canvas_is_a_bad_file_with_size_mismatch` and
    `test_bytes_that_storage_gives_back_changed_are_a_storage_error`: as today, their
    counts from the reference player.
- `Quiet.states` brings the upload to "the check half done" with a file whose check takes
  several refreshes, `support.dense_clip(60, 6, 1)`, and `moved` of "the check done" is the
  time of the refresh at which the check ended, from the reference player.
- The other tests of the core suite that counted F + 2 refreshes, or a step only after a
  refresh in step, count from the reference player or from `check_end`.

## The tests of the rule

`tests/core/test_upload_check.py`, new, on the classes and helpers of `test_upload.py`
and `test_content.py`:

- `AtEveryRefresh.test_a_host_that_refreshes_every_45_ms_ends_the_check` (13.1): the
  two-leg show of `TheCheck`, polls every 45 ms from `T0`, `support.clip(54, 60, 6,
  (20,) * 300)` sent at once, `upload end` after each poll; the core's lines are the
  reference player's; the first `{"ok":true}` comes at the refresh the reference player
  gives, which the seed puts at the 76th after the last byte, and within 100, and
  `verification.md` records the count. Seen failing first: on the core of today `busy`
  until the upload is discarded, then `no-upload`. It lives in a file of its own so that a
  run of the old core shows the failure without the rewritten `TheCheck`.
- `TheOwnersClock`, on a board without show files (an empty file set, seed 76), the
  tracked clock `collection/card/clocks/time-original-5-every-row-another-time.odrg`
  (13.2): one test for each host period, 20, 30, 45 and 50 ms, each polling every period
  from `T0` and sending `upload end` after each poll; `{"ok":true}` comes at the refresh
  `support.check_end` gives for the clock's steps and the session's refresh times, within
  400, 400, 1,300 and 2,400 refreshes after the last byte; no reply is `no-upload`; `list`
  then lists `{"id":1,...,"bytes":471095,...}`. The reference player is not run on the
  clock, whose 14,399 pictures it would decode in Python. Seen failing first at 20 ms:
  14,401 refreshes on the core of today.
- `TheFade` (13.3): the fade made in the test: 60 x 60, three bytes a pixel, 1,024
  frames of 20 ms; the picture of frame k is, for y from 0 to 59 and within it x from 0 to
  59, the three bytes `(4x mod 200) + d`, `(4y mod 200) + d` and `((x + y) mod 200) + d`,
  with d = k mod 56, as `jsonframes.Animation` takes a picture; encoded by
  `odrig.odrg.encode(..., compressed=False)`, 15,313 bytes. Uploaded to a board without
  show files, polls every 20 ms with `--trace-check`: the core's lines are the reference
  player's. The same session on the core alone with `--trace-read-at`: the counts of the
  `read_at upload.part ...` lines one poll prints, before its `refresh` line, add up to
  at most 2,048 + the largest charge of `taken_in(fade)` + 256.
- `ThePace` (13.4), on the two-leg show with `support.dense_clip(60, 6, 10)` and
  `--trace-check`: (a) polls every 20 ms, from the second after the pace rose to 3 every
  50 ms for three seconds, then every 20 ms: the core's lines are the reference player's,
  and the `check` lines show the pace at 3, then lower with `fell` 1, then rising again;
  (b) polls every 30 ms, from the start of the second after the pace rose every 60 ms for
  half a second, then every 30 ms: the pace falls at that second's middle and does not
  rise again while the host is at 33 a second.
- `TheBounds` (13.5):
  - a clip of 60 x 6 with a palette in which one pixel changes at each of 2,000 frames,
    made with `odrig.odrg.encode`, about 12 bytes a record, on the two-leg show at 20 ms:
    the core's lines are the reference player's, and in the rule's model its refreshes at
    pace 2 and 3 take 64 steps each, the cap;
  - the reproducer `small()` of `test_bounded.py` on its canvas of 4 x 4, with
    `--trace-check`, the core alone: every `check` line after a refresh at which a slice
    of settling was taken has a debt of 0, and `upload end` gives its reason;
  - `support.dense_clip(60, 60, 1)`, whose records of about 10,800 bytes leave a debt of
    15 at pace 0, on a board without show files under a host that refreshes every
    3,900 ms: the sixteen refreshes from one step to the next span more than 60 s, the
    upload is not
    discarded, and `upload end` answers `{"ok":true}` at the refresh the reference player
    gives (6.1);
  - a host that asks for no refresh for 60 s during the check still loses the upload:
    `upload end` then answers `no-upload`, as `Quiet` of `test_upload.py` has it for the
    other states.

`tests/core/test_decoder.py` (13.7), `TheChargeOfACall`: `decode --taken` of the fade, of
the tracked clock and of a text's container, and `decode --taken --batch`. For each file of
frames Python reads the records of the body (inflated for a compressed one): the n-th
`taken` line has the bytes of the n-th record, the first with its palette, and a charge
higher by n / 32 exactly when the record's mode has the run bit and predictor 1 or 2; the
last line before `end` is `taken 0 0`. A text's container gives `container` and `end` and
no `taken` line. `small()` of `test_bounded.py` gives `pending` lines of at most 32,768
bytes and then its reason.

## The emulator and the command tool

- `odrigctl/content.py`: `BUSY_SECONDS = 10800.0`.
- `tests/emulator/test_tool.py`:
  `test_after_10800_seconds_of_busy_the_upload_is_cancelled_and_the_reply_is_busy`, in
  place of the test of 600 s: 54,100 `busy` replies, the ends about 10,800 s of 0.2 s
  apart, `content.BUSY_SECONDS == 10800`.
- `docs/emulator.md`: "After 10800 seconds of `busy`".
- `tests/emulator/test_upload_check.py`, new (13.8):
  `test_the_owners_clock_is_checked_within_two_minutes_of_its_last_byte`. An emulator on an
  empty folder; the tracked clock sent over HTTP as `tests/emulator/test_content.py`
  sends an upload; from the reply to the last `upload data`, `upload end` every 0.25 s and
  `status` between them, until the reply is not `busy`. The reply is `{"ok":true}` within
  120 s, `list` lists the file with its 471,095 bytes, and the test writes one line to its
  standard error, `the owner's clock was checked in <s> s at <least> to <most> refreshes
  a second`, which the drift entry quotes.
- The emulator's tests that needed `busy` and now see a check end at once take a file
  whose check takes many refreshes: `support.dense_clip(60, 6, 2)` on the example show's
  canvas of 60 x 6, the tracked clock on 60 x 60. `tests/emulator/test_record.py` keeps
  its `busy` at 1200 and its `{"ok":true}` at 1420 with a file whose check, by the
  reference player, ends between them.

## The app

`app/www/upload.js`:

- `uploading({id, file, bytes, ...}, {report, end, wake, checking = null})`. In the data
  stage, after
  `samples.push({at, received})` and `report(...)`, when `received >= bytes.length` it sets
  `stage = "end"` and calls `checking(at)` when there is one, `at` being the
  `performance.now()` the sample took.
- `export function checkingText(elapsed)`: `Checking the animation on the installation: `
  and the whole seconds of `elapsed` ms, at least 0, as `<m>:<ss>`.
- `export function showChecking(line, since)`: writes `checkingText(performance.now() -
  since)` into `line` at once, sets a timer for `1000 - elapsed % 1000` ms that writes it
  again and sets itself again, and returns a function that stops it, after which nothing
  is written.

`app/www/screens/storage.js` and `app/www/screens/author.js`: each upload keeps
`let stopChecking = () => {};`; the job gets
`checking(since) { stopChecking = showChecking(shown, since); }`; `end(how)` calls
`stopChecking()` first, then does what it does today: the line hidden on success and on a
failure, `Cancelled.` on a cancel. `Cancel` is not hidden while the line says `Checking`.

`docs/android-app.md`: on Upload, after `Sending: 45%, 12 KB a second`, the line
`Checking the animation on the installation: 0:12` from the last byte until the
installation answers, with `Cancel`, counted by the app's clock; the check's time by the
budget, about 8 s for the owner's clock of 14,399 frames on a board at 50 refreshes a
second, in place of a fiftieth of a second for each frame; the same line in the text and
clock forms, for `Upload to the installation` and `Save`.

The app's tests, `tests/app/test_upload.py`, `tests/app/test_authoring.py` and the
scenarios of `tests/app/page/scenarios/`:

- `checked_after(seconds)` in `test_upload.py`: a reply function for `upload end` that
  answers `busy` until `seconds` have passed on the test's clock since the first `upload
  end` it got, then `{"ok":true}`.
- `uploads.js` collects the texts of `uploading` as today, and for each text that begins
  with `Checking` whether `cancel-upload` is shown; after the message whether
  `uploading` is hidden; with `cancel: "checking"` it presses `Cancel` once the line says
  `Checking`, waits for `Cancelled.`, and reads the line again 1.5 s later.
- `test_while_the_installation_checks_the_line_counts_the_seconds` (13.10), with
  `checked_after(3.5)`; `test_cancel_while_the_installation_checks` (13.13), with an end
  that stays `busy`; `test_a_gif_is_uploaded_as_the_file_the_command_line_makes_and_plays`
  (13.11): every sampled text is a Sending text or a Checking text, and no Sending text
  follows a Checking text.
- `author-text.js` and `author-edit.js` collect the texts of `author-uploading` until the
  message. `test_authoring.py`: a text's upload with `checked_after(3.5)` on
  `stand_in_of(60, 6, ...)`; a clock's `Save` on a stand-in that lists the clock of the
  form with id 7, answers `read 7 <offset>` with the bytes of `encoded({**CLOCK,
  "width": 60, "height": 6})`, `upload expect` with `{"ok":true}` and `upload end` with
  `checked_after(3.5)` (13.12). The texts after the last Sending text are as in 13.10.

## The pages

- `docs/core.md`, "Uploads and the check": the bullet "The check" says the check takes its
  steps at every refresh, in step or late, after the LED data; a step's charge (its body
  bytes, n / 32 more for a record that walks the picture, the header, a drawn payload and
  the end 0); the budget 256 << pace, the debt of up to 15 times 256 and its rest; the
  pace from 1, its changes once a second by `fps` and at the middle of the second after a
  trial; the time: 14,401 small steps in about 7.5 s on a host at 50 a second, where it
  was 288 s, and a text or a clock at the first refresh after its last byte, where it took
  three. "An unchanged file": a bit of the record says the file is installed.
  "Discarding": a refresh of the check is progress. "Bounded work": "The steps of the
  checks" says the upload's check takes several steps at a refresh within its budget, at
  most 64, and the one that passes it; "The budgets" gains the row "The check of an
  upload at one refresh | 256 to 2,048 bytes of charge, by the pace; at most 64 steps |
  the work of a refresh follows the budget whatever the file holds, and the pace follows
  the refresh rate".
- `docs/commands.md`, `busy` of `upload end`: the check decodes the whole file while the
  show plays, at most about 2,048 bytes of body a refresh on average, so about 8 s for
  14,399 small frames on a board at 50 refreshes a second, longer on a slower board.
- `docs/firmware.md`: after the paragraph "While a dense clip plays" of the upload
  measured on 2026-10-12, a paragraph: since seed 81 the check takes steps at every
  refresh within a budget paced by the refresh rate; the estimate of the seed's point 5,
  about 8 s for the owner's clock on a board at 50 with room to spare, within 30 s at 30
  or more with a show that is not dense, and a rate of 20 or more kept from 22 before; the
  figures above are those of 2026-10-12. Step 7 of the owner's checks: `{"ok":true}` a
  second or less after the last piece.
- `docs/decisions.md`, at the end of the change log: `- 2026-11-06: Seed 81, ...`, with the
  owner's words of the seed, the change of the check, the board at 20 or 21 showing about
  19, and the name of seed 07's entry of 2026-10-12, which is not edited.
- `docs/drifts.md`, at its end: `## Seed 81: the upload check at full speed`, its
  **Question.** (how fast the board checks an upload, and what the app says meanwhile),
  **Answer.** (the rule, the seed's measurements of point 5, and the emulator test's time
  and `fps`) and **Resolution.** (`core/src/upload.cpp`, `app/www/upload.js`,
  `docs/core.md`); then one entry for each question of the list below.
- `AGENTS.md`: the seed's line says "in progress on branch
  `seed-81-upload-check-at-full-speed`" from task 1 and "implemented in open PR #<n>" from
  the last task, with the rest of its words, the page within 150 lines.

## Questions this spec answered

The seed has no open question; these points it left to the spec, and the drift entries
of the last task record them:

1. The branch is `seed-81-upload-check-at-full-speed`, the name the owner's workflow gave
   it, not the seed's `seed-81-the-upload-check-at-full-speed`.
2. Every refresh of the check sets the upload's progress, a rest included (6.1).
3. When the first refresh of a second is also 500 ms or more into it, the rule of the
   whole second is applied first (4.5).
4. The first refresh after the last byte that is the first of a new second changes the
   pace by the second before, as any refresh of the check does; the seed's model began a
   check inside a second.
5. The decoder's mode byte is set only for a record decoded whole and cleared at every
   other call, so one function charges the calls of `next` and of `finish` alike.
6. The test host gains `--trace-check` beside `decode --taken`, so the pace and the debt are
   compared with the reference player refresh for refresh; the rule also has a model of
   its own in `support.py` for the files the reference player cannot decode quickly.
7. The tests of the rule are a new file, `tests/core/test_upload_check.py`; the fade and
   the files of 13.5 are made in the tests.

## Delivery

The last task merges `origin/master` into the branch, runs `python tests/run.py` and the
firmware suite with `ODRIG_TOOLS`, pushes, and opens the pull request with `gh pr create`
from `master`, its body naming the seed, the verdict, the owner's open checks and ending
with the line of Claude Code. It then builds the APK from the pushed head by hand, as this
computer builds it, and the spare's image by `python firmware/fw.py build --module n8r2`
and `python firmware/verify_build.py --module n8r2` with `ODRIG_TOOLS`, places both with
their `.sha256` on the Drive under `odrig archive/seed-81/`, writes `verification.md`,
appends the drift entries, points the `AGENTS.md` line at the pull request, commits,
pushes, reads the pull request's checks once, and notifies the owner with the links of the
pull request and of each file.
