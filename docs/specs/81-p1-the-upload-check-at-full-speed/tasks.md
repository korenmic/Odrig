# Tasks

Each task is one commit on the branch `seed-81-upload-check-at-full-speed` from `master`,
named `Seed 81 task <n>: <title>`, with only its own checkbox ticked, staged by named paths
and read back with `git show --stat`. Every test of a fault is seen failing before the
change, and the failure seen goes into the commit message; a test of new behaviour that
cannot fail before its code exists says so in the commit message. Code carries no
history. In a fresh worktree `npm ci --prefix converter` comes first. The suites are run
through `python tests/run.py --suites <names>`; the firmware suite is run with
`ODRIG_TOOLS=C:\Users\koren\src\Odrig\scratch\seed76-tools`, where it fails only the three
known tests of this computer's shared-toolchain junction, and the app suite without
`ODRIG_TOOLS`.

- [x] 1. The charge of a call of the decoder
  - `core/src/odrg_decoder.h` and `.cpp`: `kWalkDivisor`, `record_mode` after `settling`,
    set by `next` for a record decoded whole and 0 at the start of `next`, of `finish` and
    in `open`; `charge_since(before)`, as the design gives them.
  - `tests/core/host/host.cpp`: `decode --taken FILE` and `decode --taken --batch`, the
    `taken <bytes> <charge>[ pending]` lines and no `frame` line, the usage line.
    `docs/core.md`, "The test host": the row of `decode --taken`, in this commit, as
    `tests/core/test_docs.py` requires of every option of the usage text.
  - `tests/core/support.py`: `_taken`, `taken_in` and `taken_each`; `found_in`,
    `decode_each` and `_decoded` unchanged.
  - `tests/core/test_decoder.py`, `TheChargeOfACall`: the fade of the design, made in the
    test, the tracked clock, a text's container, the reproducer `small()` of
    `test_bounded.py` and `--batch`, against the records Python reads of each body. Tests
    of a new option, which fail before it only as a usage error; the commit message says
    so.
  - Set the seed's state to `in_progress`, and in the same commit reword its line in
    `AGENTS.md`, "What is coming", from "planned; ..." to "in progress on branch
    `seed-81-upload-check-at-full-speed`; ..." with the rest of its words, the page within
    150 lines.
  - Run the core, mapping and onboarding suites. The memory the core asks for is
    unchanged, as `tests/core/test_memory.py` and the table test of
    `tests/core/test_docs.py` show.
  - Requirements: 2.3, 2.4, 8.2, 9.1, 9.5, 12.8, 13.7, 14.1, 14.2.

- [x] 2. The check at every refresh, charged and paced
  - First the model and the two tests of the fault. `tests/core/support.py`:
    `check_steps`, `CheckPace`, `check_end` and `refresh_times`, as the design gives them.
    `tests/core/test_upload_check.py`, new: `AtEveryRefresh` (13.1) and `TheOwnersClock`
    (13.2). A test of a fault: build the core as it is and run these two classes against
    it, and see them fail: the host at 45 ms gets `busy` until the upload is discarded and
    then `no-upload`, where the reference player has `{"ok":true}`; the clock at 20 ms has
    no `{"ok":true}` within 400 refreshes, and at 50 ms its upload is discarded. Put the
    failures seen into the commit message.
  - `core/src/core_state.h`: the bit fields `pace`, `debt`, `installed` and `pace_fell` of
    `Upload`. `core/src/upload.h`: the constants, `upload_refresh` in place of
    `upload_step`, the comment of `kUploadQuietMs`. `core/src/upload.cpp`: `upload_step`
    internal and returning its charge and whether it gave `pending`, `upload_refresh`,
    `pace_down` and `pace_up`, the pace, the debt and the mark set at the last byte, the
    progress set at every refresh of the check. `core/src/player.cpp`: `new_second` before
    the roll-over, `upload_refresh` at every refresh, its comment.
  - `tests/core/host/host.cpp`: `--trace-check` and its usage text; `docs/core.md`, "The
    test host": its row, in this commit.
  - `tests/core/support.py`, `ReferencePlayer`: `trace_check`, `second_running`, `_judge`
    with `check_steps`, `CheckPace` at the last byte, `poll` by the new rule with the
    progress set at every refresh of the check, `sound_records` removed.
    `tests/core/test_content.py`, `run_both`: `trace_check` for the reference player.
  - `tests/core/test_upload.py`: `Script` keeps its polls and `Script.check` counts by
    `check_end`; `TheCheck` rewritten as the design names its tests; `Quiet.states` with
    `support.dense_clip(60, 6, 1)` and the time of the check's last refresh. Every other
    test of the core, emulator and app suites that counted F + 2 refreshes or a step only
    after a refresh in step counts from the reference player or `check_end`; an emulator
    test that needs `busy` takes `support.dense_clip(60, 6, 2)` or the tracked clock, and
    `tests/emulator/test_record.py` a file whose check ends between 1200 and 1420. None
    pins the old pacing.
  - Then `AtEveryRefresh` and `TheOwnersClock` pass, with `{"ok":true}` at the refreshes
    the model gives; write the counts down for `verification.md`.
  - Run the core, mapping, emulator, app and onboarding suites.
  - Requirements: 1.1-1.4, 2.1, 2.2, 3.1-3.5, 4.1-4.6, 5.1-5.6, 6.1-6.3, 7.1, 7.3, 8.1,
    8.3, 9.2-9.4, 13.1, 13.2, 13.6.

- [x] 3. The rule pinned
  - `tests/core/test_upload_check.py`: `TheFade` (13.3) with `--trace-check` and with
    `--trace-read-at`, the fade made in the test as the design defines it; `ThePace`
    (13.4), its two hosts on `support.dense_clip(60, 6, 10)` with `--trace-check`;
    `TheBounds` (13.5): the clip of 12-byte records and the cap of 64, the reproducer's
    slices leaving no debt, the host at 3,900 ms whose rests keep the upload, and the host
    that asks for no refresh for 60 s.
  - These are guards of the rule of task 2, which pass at once; the commit message says
    so. When one does not pass, the fault is mended in this commit, its failure written
    into the commit message.
  - Run the core suite.
  - Requirements: 6.1, 6.2, 7.1, 13.3-13.5.

- [x] 4. The core's pages
  - `docs/core.md`: "Uploads and the check", the bullets "The check", "An unchanged file"
    and "Discarding"; "Bounded work", "The steps of the checks" and the row of "The
    budgets"; as the design gives them, with no F + 2 refreshes left.
  - `docs/commands.md`, `busy` of `upload end`: the check's time by the budget, about 8 s
    for 14,399 small frames at 50 refreshes a second, about 2,048 bytes of body a refresh
    at most on average; no fiftieth of a second for each frame.
  - Run `python -B -m unittest tests.core.test_docs tests.app.test_docs
    tests.emulator.test_docs` and the onboarding suite.
  - Requirements: 12.1, 12.2.

- [x] 5. The command tool and the emulator's check of the owner's clock
  - `tests/emulator/test_tool.py`:
    `test_after_10800_seconds_of_busy_the_upload_is_cancelled_and_the_reply_is_busy`, with
    54,100 `busy` replies, in place of the test of 600 s. A test of a changed limit: seen
    failing first on `odrigctl/content.py` as it is, `600.0 != 10800`, which goes into the
    commit message.
  - `odrigctl/content.py`: `BUSY_SECONDS = 10800.0`. `docs/emulator.md`: "After 10800
    seconds of `busy`", which `tests/emulator/test_docs.py` finds.
  - `tests/emulator/test_upload_check.py`, new:
    `test_the_owners_clock_is_checked_within_two_minutes_of_its_last_byte` (13.8). Write
    down the time and the `fps` it prints for the drift entry.
  - Run the emulator and onboarding suites.
  - Requirements: 11.1, 12.4, 13.8, 13.9.

- [x] 6. The app says that the installation checks
  - First the tests. `tests/app/test_upload.py`: `checked_after(seconds)`,
    `test_while_the_installation_checks_the_line_counts_the_seconds` (13.10),
    `test_cancel_while_the_installation_checks` (13.13), and the sampled texts of
    `test_a_gif_is_uploaded_as_the_file_the_command_line_makes_and_plays` (13.11).
    `tests/app/test_authoring.py`: a text's upload and a clock's `Save` against stand-ins
    whose end is `busy` for 3.5 s (13.12). `tests/app/page/scenarios/uploads.js`,
    `author-text.js` and `author-edit.js`: the texts of the line, `Cancel` while it says
    `Checking`, the line after the message, the cancel while checking. A test of a fault:
    run against the app as it is and see the new tests fail with no Checking text after
    the Sending line; the failure goes into the commit message.
  - `app/www/upload.js`: the optional `checking(since)` of the job, `checkingText` and
    `showChecking`. `app/www/screens/storage.js` and `app/www/screens/author.js`: the
    Checking line from `checking` until the job ends, the timer stopped first in `end`,
    `Cancel` shown meanwhile.
  - `docs/android-app.md`: the Checking line after the Sending line, its time by the app's
    clock, the corrected time of the check, the same in the text and clock forms; no
    fiftieth of a second for each frame.
  - Run the app suite, without `ODRIG_TOOLS`, and the onboarding suite. A test of
    `test_tests` that times out under load is run again alone.
  - Requirements: 10.1-10.5, 12.3, 13.10-13.13.

- [ ] 7. The firmware's page and the change log
  - `docs/firmware.md`: after "While a dense clip plays" of the upload measured on
    2026-10-12, the paragraph of the check paced by the budget since seed 81, with the
    estimate of the seed's point 5, the dated figures left as they are; step 7 of the
    owner's checks, `{"ok":true}` a second or less after the last piece. Every string that
    `tests/firmware/test_docs.py` pins stays.
  - `docs/decisions.md`, at the end of the change log only:
    `- 2026-11-06: Seed 81, ...`, with the owner's approval of that day in the words the
    seed quotes, the check's steps at every refresh, charged by their work and paced by
    the refresh rate, in place of one record at a refresh in step, a board already at 20
    or 21 a second showing about 19 while it checks an upload where its check never ended
    before, and the name of seed 07's entry of 2026-10-12, which is not edited. No
    decision above the change log changes.
  - Run the firmware suite with `ODRIG_TOOLS`, the firmware-host and onboarding suites,
    and `python -B -m unittest tests.converter.test_docs`.
  - Requirements: 7.2, 12.5, 12.6.

- [ ] 8. The record, the deliveries and the pull request
  - `git fetch origin` and `git merge origin/master` on the branch, the change log of
    `docs/decisions.md` kept by hand with both sides, those of `master` first, and
    `docs/drifts.md` by union. Run `python tests/run.py`, every suite that works on this
    computer, and the firmware suite on its own with `ODRIG_TOOLS`.
  - Push the branch, and open the pull request from `master` with `gh pr create`: its title
    names seed 81, its body the seed, the verdict, what changed, the owner's open checks,
    and ends with the line of Claude Code. Reword the seed's line in `AGENTS.md` to
    "implemented in open PR #<n>; ..." with the rest of its words.
  - From the pushed head: the APK, built as this computer builds it, and the spare's image,
    `python firmware/fw.py build --module n8r2` and
    `python firmware/verify_build.py --module n8r2` with `ODRIG_TOOLS`. Both on the Drive
    under `odrig archive/seed-81/` with their `.sha256`; nothing above that folder touched.
  - `docs/specs/81-p1-the-upload-check-at-full-speed/verification.md`, in the form of seed
    78's: the commits by task; the suites by task with the failures seen first; the counts
    of `AtEveryRefresh` and `TheOwnersClock`; the emulator test's time and `fps`; the
    builds with their bytes and SHA-256; the Drive paths and the links of the files; the
    result of the pull request's checks on the head before this commit; and what stays
    open.
  - `docs/drifts.md`, at its end: `## Seed 81: the upload check at full speed` with the
    measurements of the seed's point 5 and those of the emulator test, then one entry for
    each question the design lists under "Questions this spec answered", each with its
    **Question.**, **Answer.** and **Resolution.**
  - The state stays `in_progress`; merging sets it `completed`. Commit, push, read the
    pull request's checks once, without polling, and notify the owner in words with
    `python C:/Users/koren/.claude/skills/notify/notify.py`: the pull request's link; the
    links of the APK and of the image; the owner's checks below; that a board already at 20
    or 21 a second shows about 19 while it checks an upload; that the dense clip of the
    seed is checked in about 14.9 s on a host at a perfect 50 a second, where it took 10 s;
    and the stale `body_read` of a text's fault context at `core/src/upload.cpp:150`,
    proposed as a seed of its own.
  - Requirements: 12.7, 12.8, 14.3-14.7; 4.7 and 4.8 are shown by the owner's checks
    below and stay open.

## Owner acceptance (not claimed by automated tasks)

On the spare board flashed with the image of task 8, `odrig-firmware-n8r2.bin`, and with
the APK of task 8: (1) note what the spare plays, and the Show screen's `N refreshes a
second` while it plays it; (2) upload the rotated clock
`clocks_rotated_right/time-original-5-every-row-another-time.odrg` (498,211 bytes) to
`Internal storage`; (3) after the Sending line the line says `Checking the animation on
the installation: 0:00` and counts up once a second; (4) the message `Uploaded as
animation <id> <file>. It plays in the playlist.` comes: while what plays is not dense, by
`0:30` when the rate of (1) was 30 or more, by `1:00` at 25 to 29 and by `2:30` below 25;
while a dense animation plays, the time is noted and has no limit; (5) the Show screen's
rate, read while the line says `Checking`, is 20 or more each time when the rate of (1)
was 22 or more; at 20 or 21 the lowest is noted; (6) the clock then plays on the LEDs;
(7) with a card in the spare, the same file uploaded to the card, the time the Checking
line reached and the lowest rate read during it noted, with no limit. These remain open
until the owner reports them.
