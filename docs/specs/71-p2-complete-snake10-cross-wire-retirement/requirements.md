# Requirements

Seed 71, `project-seeds/71-p2-complete-snake10-cross-wire-retirement/seed.md`. The
emulator, the command tool, their tests and the documents. No command, reply, core,
firmware, app, wiring, power or storage change.

## 1. No counter or observer of the retired command

1.1 The emulator's core binding keeps no count of `mapping cross` replies, and its engine
reads the mapping again for the page only when the legs or their pins change.
1.2 A successful `mapping set` still makes the page read the mapping again; the miniature
output and every other routing update stay.

## 2. No form of it in the command tool

2.1 `odrigctl mapping cross on` and `off` are usage errors, status 2, like any other form
the tool does not know, and nothing is sent.
2.2 The tool's words for `mapping` name `get`, `set REV PINS`, `test on|off` and `test snake
N`.

## 3. The retired command stays refused

3.1 `mapping cross on` and `off`, sent as lines over the emulator's TCP and HTTP lines,
still answer `bad-argument`, write no file, keep the mapping and its revision, and make the
page read nothing again.

## 4. What stays

4.1 Snake 10 as an ordinary snake: its test, its pin, its geometry.
4.2 The generic mapping format and installed per-strip geometry, the photo reading of a
strip wired another way, and the records of seed 43 and seed 69.

## 5. The audit

5.1 The shared app, the emulator's page, the core and the firmware have no path of the
feature; the record says what was searched and found, in `docs/drifts.md`.
5.2 The documents that face the user name no form of it but the retirement sentence of
`docs/commands.md`.
