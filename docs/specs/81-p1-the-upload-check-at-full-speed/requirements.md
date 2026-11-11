# Requirements

Seed 81, `project-seeds/81-p1-the-upload-check-at-full-speed/seed.md`. The core's check of
an uploaded file takes its steps at every refresh, each charged by its work, within a
budget set by the refresh rate; the decoder keeps the mode of the record it decoded; the
test host and the reference model of the core's tests state the rule a second time; the
app says `Checking the animation on the installation: <m>:<ss>` until `upload end`
answers; the command tool waits up to 10,800 s; the pages give the new times. The
firmware's sources, the command list, every reply and every memory block are not changed.
The owner approved the fix on 2026-11-06 in the words the seed quotes.

## 1. The check takes its steps at every refresh

1.1 After the last byte of an upload, the check of the file takes its steps at every
refresh the host asks for, in step or late, once the LED data of that refresh is
complete: where it takes its one step today. A refresh that came after a grid time was
skipped is treated as one in step.
1.2 A step is what it is today: the header, one frame record, the end of the file, or one
slice of at most 32,768 bytes of body while a defect is settled. A text or a clock reads
its payload whole in one step.
1.3 A poll that produces no refresh takes no step, and nothing is added at a late refresh
for the grid times it skipped.
1.4 No step is taken outside a refresh: not inside a command, and not at a call of the
firmware between refreshes.

## 2. The charge of a step

2.1 The header step, the step that reads a text's or a clock's payload (a picture clock's
picture included) and the end step of a text or a clock are charged 0, so a text or a
clock is checked whole at the first refresh after its last byte.
2.2 A step that calls the decoder for a frame record, for a slice of settling or for the
end of a file of frames is charged the bytes of the body that call took: `body_read`
after it less `body_read` before it. For a compressed body these are inflated bytes. The
palette is counted with the first record. A whole end that finds nothing after the last
record takes no byte and is charged 0.
2.3 A call of `next` that decodes a whole coded record whose mode has the run bit and
predictor 1 or 2 is charged n / 32 more, by integer division, n being the decoder's
pixel buffer: 337 for a picture of 60 x 60 of three bytes a pixel, 112 with a palette.
Every other call is charged its body bytes alone.
2.4 The decoder keeps the mode byte of the record its last call of `next` decoded whole,
and 0 after any other call and after `open`; the charge of a call is computed from it and
from `body_read` alone, by one function of the core that the test host calls as well.

## 3. The debt

3.1 The check keeps a debt, in whole 256s of charge, from 0 to 15. A refresh's allowance
is its budget (4.1) less 256 times the debt.
3.2 A refresh whose allowance is 0 or less takes no step, and its debt falls by its
budget's number of 256s: 1, 2, 4 or 8.
3.3 Any other refresh takes steps while the check has not ended, its steps are fewer than
64 and their charge is below the allowance; its first step is always taken.
3.4 After such a refresh the debt is what the charge of its steps passed the allowance
by, in whole 256s rounded down, at most 15. A refresh whose last step gave `pending`, a
slice of settling, leaves a debt of 0.
3.5 So a charge within 255 of the allowance leaves no debt, and a file of small records,
such as the owner's clock, never rests.

## 4. The pace

4.1 The budget is 256 shifted left by the pace: 256, 512, 1,024 or 2,048 for a pace of 0
to 3.
4.2 When the last byte arrives and the check begins, the pace is 1, the debt 0, and the
mark that the pace has fallen is clear.
4.3 At the first refresh of each new whole second, counted from the power-on moment,
while the check runs and before that refresh's steps, the pace changes by R, the
refreshes of the second just ended as `status` reports them as `fps` (0 when that second
had none): below 21 it goes down by one, to 0 at least, and the mark is set; otherwise at
40 or more it goes up by one, to 3 at most; otherwise at 27 or more, while the mark is
clear, it goes up by one, to 3 at most.
4.4 At any refresh 500 ms or more into its second, while the check runs and the mark is
clear, before that refresh's steps: when that second has had 11 refreshes or fewer, this
one included, the pace goes down by one, to 0 at least, and the mark is set.
4.5 When one refresh meets both 4.3 and 4.4, 4.3 is applied first.
4.6 The mark stays set until the check ends.
4.7 In the model of the seed's point 5, a board at 22 refreshes a second or more before
the check stays at 20 or more during it, and one at 20 or 21 shows about 19. This is an
estimate until the owner's check of 14.6 measures it.
4.8 The target, for the owner's 14,399-frame clock while a show that is not dense plays:
on a board that refreshes 30 times a second or more before the check, `{"ok":true}`
within 30 s of its last byte; at 25 to 29 a second within a minute; below 25 within two
and a half minutes. While a dense animation plays it takes longer and has no limit. The
owner's check of 14.6 shows it; on a host that refreshes every 20 ms the rule's model
gives at most 7.5 s.

## 5. What stays whole

5.1 The check reads every record of the file and its end, as today, and compares the size
and the CRC-32 of what it read back with what was received.
5.2 Every verdict stays, with its reason: `bad-file` with the reason of `docs/reasons.md`,
`size-mismatch`, and `storage-error` for a read that fails or bytes that differ. A check
that does not end with `{"ok":true}` leaves the show as today.
5.3 The fault's context stays: the work `upload`, the file's name, the record and the
bytes of the body read.
5.4 Settling keeps its slices of 32,768 bytes, and `pending` stays internal.
5.5 The order of the steps stays: the header, the records in order, the end.
5.6 An upload to the card, `upload begin external`, is checked by the same rule, reading
`drive/upload.part` through `read_at`.

## 6. Progress, the quiet timer and the late host

6.1 Every refresh of the check sets the upload's progress: one that takes steps, and one
that rests to pay a debt.
6.2 So the 60 s quiet timer discards an upload whose check runs only when the host asks
for no refresh for 60 s, and one whose check has ended when nobody asked `upload end`
for 60 s, as today; `upload end` then answers `no-upload`.
6.3 `upload end` answers `busy` while the check runs, and its other answers stay as they
are.

## 7. Bounded calls and the firmware

7.1 A refresh adds to its work at most its allowance and the one step that passes it, and
at most 64 steps. That one step is what one step is today: one frame record or one slice
of settling.
7.2 No source of the firmware changes. The firmware's build takes the new core.
7.3 The check after the start, the check of a drive's file and the catalog's rebuild keep
their pacing; playback keeps its 131,072 bytes a refresh and the LED data of every
refresh is what it is today; the second decoders and their hand-over between the upload
and the other checks stay as they are; the upload's data phase and its speed stay.

## 8. Memory

8.1 The pace (2 bits) and the debt (4 bits) are bit fields of the upload's record beside
`header_read` and `absent`; `installed` is a 1-bit field in its own byte, at the place it
has now, and the mark that the pace has fallen is a second bit of that byte.
8.2 The decoder's mode byte is a `uint8_t` after `settling` in `OdrgDecoder`, in the
padding before `settle_found`.
8.3 `sizeof(Upload)` stays 72 bytes and `sizeof(OdrgDecoder)` 832 on this computer's GCC;
the core object stays 3,712 bytes; no block or table grows; the memory the core asks for,
as the core suite measures it, and the table of "Memory" in `docs/core.md` are
unchanged.

## 9. The test host and the reference model

9.1 `odrig_host decode --taken FILE` and `decode --taken --batch` print the lines of
`decode` without its `frame` lines: `container ...` for a container, `header ...` for
frames, then after each call of the decoder for a record or for the end (`next` or
`finish`) one line `taken <bytes> <charge>`, with ` pending` at its end for a call that
gave `pending`, then `end` or `rejected <reason>`. A container of a text or a clock gets no
`taken` line. `decode` without `--taken` prints what it prints today.
9.2 The session option `--trace-check` prints, after the `data` lines of each refresh at
which an upload was being checked when the refresh began, one line
`check <pace> <debt> <fell>`: the pace and the debt after that refresh, and 1 when the
mark is set, else 0.
9.3 The reference player of `tests/core/support.py` states the debt and the pace a second
time, takes the charge of each step that calls the decoder from `decode --taken`, as
`found_in` takes from the decoder where in a body a fault lies, and charges the header, a
drawn payload and a drawn end 0. It prints the `check` lines of 9.2 when the session has
`--trace-check`. Every test that compares the core's lines with it passes, so the rule is
pinned refresh for refresh.
9.4 The rule of 3 and 4 is also a model of its own in `tests/core/support.py`, which gives
for a list of step charges and the times of a session's refreshes the refresh at which
the check ends. The tests whose files the reference player cannot decode in a short time,
the owner's clock among them, count from it.
9.5 `found_in` and `decode_each` stay as they are.

## 10. The app's line while the board checks

10.1 The job of `app/www/upload.js` takes an optional `checking(since)` beside `report`,
`end` and `wake`. It is called once, when the reply to the last `upload data` has come,
with `performance.now()` of that moment, in the same task as the report of that reply. A
job that ends before the last byte never calls it.
10.2 From then until the job ends, the line of the screen that runs the job says
`Checking the animation on the installation: <m>:<ss>`: the whole seconds since `since`,
minutes without a leading zero and seconds in two digits (`0:00`, `0:12`, `1:05`,
`61:05`). The first text is written at once; the screen writes it again at each next
whole second of that time, by a timer set to `1000 - elapsed % 1000` ms, set again each
time.
10.3 The line holds no fraction and no speed. `Cancel` stays shown and sends
`upload cancel` as today, and `Cancelled.` follows. Every way the job ends stops the
timer, done, cancelled or failed, so the line does not change after it.
10.4 The time comes from the app's own clock and includes any time the app was hidden. The
job still sends `upload end` again every 250 ms while the app is shown and nothing while
it is hidden.
10.5 This holds on Upload, for `Upload to the installation` of a converted media file and
of a ready-made file, to the board or to the card, and in the text and clock forms, for
`Upload to the installation` and for `Save`. No command, reply member or message of
`messages.js` is added.

## 11. The command tool

11.1 `BUSY_SECONDS` of `odrigctl/content.py` is 10,800. `upload: checking` and the resend of
`upload end` every 0.2 s stay; after 10,800 s of `busy` the tool sends `upload cancel`,
prints the last reply and exits with status 1, as it does after 600 s today.

## 12. The pages, the log of decisions and the drifts

12.1 `docs/core.md`: "Uploads and the check", the bullet "The check", gives the charge,
the debt, the pace and the time, and no longer says F + 2 refreshes; the bullet "An
unchanged file" says a bit of the record marks the installed file; "Discarding" names a
refresh of the check as progress; "Bounded work", "The steps of the checks", says the
upload's check takes steps at every refresh within its budget, and "The budgets" has a row
for it, 256 to 2,048 a refresh by the pace, at most 64 steps; "The test host" has
`decode --taken` and `--trace-check`.
12.2 `docs/commands.md`, `busy` of `upload end`: the check's time by the budget, about 8 s
for 14,399 small frames at 50 refreshes a second, and about 2,048 bytes of body a refresh
at most on average; no fiftieth of a second for each frame.
12.3 `docs/android-app.md`: the Checking line after the Sending line, its time, and the
corrected time of the check; the same for the text and clock forms; no fiftieth of a
second for each frame.
12.4 `docs/emulator.md`: "After 10800 seconds of `busy`", as `tests/emulator/test_docs.py`
formats `BUSY_SECONDS`.
12.5 `docs/firmware.md`: after the upload measured on 2026-10-12, a paragraph that the
check is paced by the budget since seed 81, with the estimate of the seed's point 5, the
dated figures left as they are; step 7 of the owner's checks: `{"ok":true}` for the
hello-bench file a second or less after the last piece.
12.6 `docs/decisions.md`: no decision changes; the change log gets at its end an entry dated
2026-11-06 with the owner's approval in the words the seed quotes, the change of the
upload's check from one record at a refresh in step to steps at every refresh, charged
by their work and paced by the refresh rate, and that a board already at 20 or 21 a
second shows about 19 while it checks an upload, where before its check never ended. It
names seed 07's entry ("its check takes as long as the animation lasts") and does not edit
it.
12.7 `docs/drifts.md` gets at its end `## Seed 81: the upload check at full speed`, with
the measurements of the seed's point 5 and those of the emulator test of 13.8: the
time it took and the `fps` read during it; and an entry for each question this spec
answered that the seed left open.
12.8 `AGENTS.md`: the line of seed 81 in "What is coming" stays true as the work goes, and
the page stays within its 150 lines.

## 13. The tests

13.1 Core, seen failing first: a host that refreshes every 45 ms uploads
`support.clip(54, 60, 6, (20,) * 300)` onto the two-leg show; `upload end` answers
`{"ok":true}` at the refresh the reference player gives, 76 after the last byte by the
rule, and within 100. On the core of today it answers `busy` until the upload is
discarded, then `no-upload`.
13.2 Core, seen failing first: the tracked clock
`collection/card/clocks/time-original-5-every-row-another-time.odrg`, uploaded to a board
without show files, answers `{"ok":true}` at the refresh the rule's model gives and
within at most 400 refreshes after the last byte with a refresh every 20 ms, 400 every
30 ms, 1,300 every 45 ms and 2,400 every 50 ms, with no `no-upload` on the way; then `list`
lists it with its 471,095 bytes. On the core of today it needs 14,401 refreshes at 20 ms.
13.3 Core: the fade of 60 x 60, three bytes a pixel, 1,024 frames, uncompressed, of the
seed's point 5, made in the test with `odrig.odrg.encode`, uploaded to a board without
show files under a host that refreshes every 20 ms: the core's lines are the reference
player's, `check` lines included; and with `--trace-read-at` the bytes `read_at` gives of
`upload.part` within one poll are never more than 2,048, plus the largest charge of a
step of the file, plus 256.
13.4 Core, the pace pinned against the reference player with `--trace-check`: a host at
20 ms, then 50 ms for three seconds, then 20 ms again, during one check: the pace rises,
falls with the mark set, and rises again from 50 a second; a host at 30 ms, then 60 ms
from the start of the second after the pace rose, for half a second, then 30 ms again:
the pace falls at that second's middle and does not rise again at 33 a second.
13.5 Core: a file of records of about 12 bytes is taken 64 steps at a refresh once the
pace is 2 or more; a slice of settling ends its refresh's steps and leaves no debt; every
invalid vector still gets its `bad-file` reason, now at the refresh the reference player
gives; `--read-back-fails` and `--read-back-differs` still give `storage-error`; a host
that asks for no refresh for 60 s still loses the upload, and a host whose refreshes rest
to pay a debt does not.
13.6 Core: the tests that pinned F + 2 refreshes or the in-step rule (`TheCheck` of
`tests/core/test_upload.py` and its neighbours, and every other test of the core, the
emulator and the app suites that counted them) count from the reference player or the
rule's model; none pins the old pacing.
13.7 Decoder: `decode --taken` of the fade gives for each record its bytes and a charge 337
higher exactly for the records whose mode, read from the file by Python, has the run bit
and predictor 1 or 2; of the clock, 112 higher for those; the end's line is `taken 0 0`;
a text's container has no `taken` line; a defect settled in slices gives `pending` lines.
13.8 Emulator: the tracked clock is uploaded over HTTP to an emulator started on an empty
folder; `upload end` answers `{"ok":true}` within 120 s after the last byte; the test
writes the time it took and the `fps` that `status` reported during the check to its
standard error. A test that needs `busy` uploads a file whose check takes many refreshes.
13.9 Command tool: `BUSY_SECONDS` is 10,800, the resend every 0.2 s is unchanged, the
test of the limit feeds more than 54,000 `busy` replies, and `docs/emulator.md` names the
new figure.
13.10 App, with the stand-in targets of `tests/app/test_upload.py`: on Upload a target
answers `busy` to `upload end` for 3.5 s by its own clock from its first `upload end`, then
`{"ok":true}`; after the Sending line the sampled texts read
`Checking the animation on the installation: 0:00` first, each later one a second more
than the one before, `0:01` and `0:02` among them; no text with `%` or `KB a second`
follows the last byte; `Cancel` is shown meanwhile; the success message comes and the
line is hidden.
13.11 App: `test_a_gif_is_uploaded_as_the_file_the_command_line_makes_and_plays` expects
Sending texts, then Checking texts, in that order.
13.12 App: the same as 13.10 for a text's upload and for a clock's `Save` in the forms.
13.13 App: `Cancel` while the line says `Checking`: `upload cancel` is sent, `Cancelled.`
is shown, and the text does not change after it.

## 14. The branch, the pull request, the deliveries and the owner's checks

14.1 The work lands on the branch `seed-81-upload-check-at-full-speed` from `master`, one
commit per task, `Seed 81 task <n>: <title>`, each ticking its own checkbox in this
spec's `tasks.md`, and as a pull request of its own.
14.2 The first task sets the seed's state to `in_progress`; implementation merged into
`master` sets `completed` with the owner's checks left open, as the working rules say.
14.3 On the branch brought up to date with `origin/master`, `python tests/run.py` passes
every suite that works on this computer; the firmware suite, run on its own with
`ODRIG_TOOLS` set, fails only the three known tests of this computer's shared-toolchain
junction. The pull request's checks on GitHub pass, the firmware workflow among them.
14.4 The APK built from the branch, and the spare's image `odrig-firmware-n8r2.bin` built
on Windows by `python firmware/fw.py build --module n8r2` and verified by
`python firmware/verify_build.py --module n8r2`, go on the Drive under
`odrig archive/seed-81/` with their `.sha256`, and their file links are sent to the owner
in words.
14.5 `verification.md` of this spec records the commits, the suites with the failures
seen first, the measurements of the emulator test, the builds with their hashes, the
Drive paths and links, the result of the pull request's checks, and what stays open.
14.6 The owner's checks on the spare board with that image and that APK, which only a
person can make, stay open until the owner reports them: (1) note what plays and the Show
screen's `N refreshes a second`; (2) upload the rotated clock
`clocks_rotated_right/time-original-5-every-row-another-time.odrg` (498,211 bytes) to
`Internal storage`; (3) after the Sending line the line says
`Checking the animation on the installation: 0:00` and counts up once a second; (4) the
success message comes, while what plays is not dense by `0:30` when the rate of (1) was
30 or more, by `1:00` at 25 to 29 and by `2:30` below 25, and with no limit while a dense
animation plays; (5) the rate read while the line says `Checking` is 20 or more each time
when the rate of (1) was 22 or more, and at 20 or 21 the lowest is noted; (6) the clock
then plays on the LEDs; (7) with a card in the spare, the same file uploaded to the card,
the time the Checking line reached and the lowest rate noted, with no limit.
14.7 The hand-over tells the owner in words the pull request's link, the links of the
APK and the image, the owner's checks of 14.6, that a board already at 20 or 21 a second
shows about 19 while it checks an upload, that the dense clip of the seed is checked in
about 14.9 s on a host at a perfect 50 a second where it took 10 s, and the stale
`body_read` of a text's fault context at `core/src/upload.cpp:150`, proposed as a seed of
its own.
