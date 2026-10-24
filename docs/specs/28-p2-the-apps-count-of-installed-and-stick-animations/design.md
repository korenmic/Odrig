# Design: the app's count of installed and external animations

## Overview

The two numbers are made in the app's web code alone, by the module that already makes the
two lines' words, `app/www/capacity.js`. The client, `app/www/client.js`, keeps one more
fact of what the replies said: whether the newest `list` request was answered `busy`. The
show screen and the storage screen hand the module the state they already watch.

## What this design relies on

- `client.state.space` is the newest reply to `space`, or null; its `animations` counts
  the show's animation items, ignored ones among them, and is 0 while the show is
  invalid; its `external.present` tells a plugged-in medium from none
  (`core/src/content.cpp`).
- `client.state.animations` is the animation items of the newest complete list, in the
  order of the reply, or null while there is none; a `busy` refusal leaves it as it was
  and asks again after a second.
- The items of the external storage come after the show's in the reply to `list`, and
  `animations` of `space` counts only the show's (`docs/commands.md`).
- The emulator's `--drive DIR` reports the drive present while `DIR/odrig` exists
  (`emulator/host.py`), so a drive with an empty folder is present with no animation.

## The client

`state.listBusy` is a boolean, false at the start and when the address changes. A `busy`
refusal of a `list` request sets it; a complete list and every other refusal clear it.
Nothing else in the client changes: the same requests at the same times.

## The words

`capacity.js` gains one function and two arguments:

```js
// The numbers of the dashboard: {internal, external}, each a number or null when it
// is not known. `external` is undefined while the external storage is absent.
export function counts(state)

export function internal(space, count)   // count: a number, or null for "not known"
export function external(space, count)   // count: a number, null, or undefined
```

`counts(state)`:

- `internal`: null when `state.space` is null or the newest status has an `error`;
  otherwise `state.space.animations`.
- `external`: undefined when `state.space` is null or its `external.present` is not true.
  Otherwise null when `state.listBusy` is true or `state.animations` is null. Otherwise,
  when every animation item has a boolean member `external`, the items where it is true;
  else the animation items less `state.space.animations`, and null when that is below 0.

The words, with `n animations` and `1 animation`:

| State | Internal line | External line |
|---|---|---|
| no reply to `space` | `-` (today's) | `External storage: capacity unavailable (read-only).` (today's) |
| absent | `84 animations, free 6.7 MB of 13.5 MB` | `External storage: absent (read-only).` |
| present, counted | as above | `External storage: 12 animations, free 3.1 GB of 31.9 GB (read-only).` |
| present, capacity unknown | as above | `External storage: 12 animations, capacity unavailable (read-only).` |
| present, number not known | as above | `External storage: animations not known yet, free … (read-only).` |
| invalid show | `animations not known, free 6.7 MB of 13.5 MB` | as the rows above |

The show screen writes `Internal storage: ` before the internal words, as today; the
storage screen writes them without it, as today.

## Tests

`tests/app/test_counts.py`, with the page reader `tests/app/page/reading.js` reading the
dashboard's two lines as `internalLine` and `externalLine`:

- The emulator with the demo show and no drive: `2 animations`, the external line
  `absent`.
- With `--drive` holding two animations: `External storage: 2 animations, …`.
- With an empty folder `odrig`: `0 animations`.
- Plugged in and pulled out while the page runs: the folder `odrig` made after the start
  and removed again; the line follows within the app's list and space intervals.
- A stand-in target whose `list` answers `busy`: the external line says
  `animations not known yet`, the internal line its number.
- A stand-in target whose status reports an invalid show: `animations not known`.
- The storage screen's lines say the same words.

## Documents

`docs/android-app.md`: the show screen's two numbers in "What it is", a step of the check
on a phone, and the lines of "What is verified" and "What is open".
