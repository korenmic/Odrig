# Requirements

Seed 83, `project-seeds/83-p1-display-tests-start-whenever-play-does/seed.md`. The core,
its tests, the emulator's suite and the documents. No command, reply member, error code,
firmware source, host, wiring or power change; the firmware images are rebuilt because
they compile the core.

## 1. A test starts when play does

1.1 `mapping test on` and `mapping test snake <n>` are not refused `busy` while the check
after a start is under way.
1.2 Neither is refused `busy` while an upload is open.
1.3 Every other answer stays, in today's order: `in-use` in Clocks only, success when the
same test already shows, `show-invalid`, `bad-argument` for a mapping the tests cannot use,
`storage-error` when the diagonal cannot be decoded.
1.4 `mapping test off` is taken as today.

## 2. The reading goes on under a test

2.1 The check after a start, the card's check and the loading of the card's catalog go on
while a test shows, and end as they would without it; `status` reports their progress.
2.2 A test that shows when they end keeps showing; nothing starts to play under it.

## 3. An open upload goes on under a test

3.1 When a test shows, `upload data`, `upload expect`, `upload end` and `upload cancel` of
an upload already open are taken as without a test, and its check runs to its verdict.
3.2 An `upload end` that succeeds under a test changes the show as during play: a new
item, a replaced file, a new file of the card.
3.3 Nothing starts to play under the test because of it: the test keeps showing until
`mapping test off` or a valid ordinary play command.
3.4 The test's end resumes what played before the first test, its saved place kept across
the upload's change; an animation that is no longer there falls back as today. When
nothing played before the test, its end plays the playlist from its first animation, the
new one included.

## 4. What stays refused under a test

4.1 `upload begin` in every form, `ignore`, `remove`, `remove many` and `catalog rebuild`
stay `busy` while a test shows.

## 5. `mapping set`

5.1 `mapping set` is not refused because the check after a start is under way.
5.2 It stays `busy` while an upload is open, and keeps its other answers.

## 6. The same everywhere

6.1 The emulator answers alike over its TCP and HTTP lines; the board and the spare's
firmware compile the same core.
6.2 The core's fixed memory and the 512-byte frame limit hold; no memory is added.

## 7. The documents

7.1 `docs/commands.md`: the test's and `mapping set`'s refusals, and the `busy` row.
7.2 `docs/core.md`: the diagnostic's entry and what an upload does under it.
7.3 The change log of `docs/decisions.md` with the owner's ruling of 2026-11-07, and an
entry at the end of `docs/drifts.md`.
