# Shows

A show is everything installed on the board besides the firmware: which animations exist,
how they are numbered, and what plays at power-on.

## Installed file set

A show is installed as one flat folder of files:

| File | Content |
|---|---|
| `mapping.json` | The layout of the physical LEDs. See [mapping.md](mapping.md). |
| `show.json` | The list of things that can be played. See below. |
| `*.odrg` | The animations named by `show.json`. See [format.md](format.md). |

The same folder is what the emulator runs and what is uploaded to the board. The player reads
these files when it starts. Nothing else defines the layout or the show.

## show.json

A UTF-8 JSON object with exactly these members:

| Member | Type | Meaning |
|---|---|---|
| `version` | integer | Format version. This document describes version 1. |
| `brightness` | integer | Brightness at power-on, 0 to 255. |
| `items` | array | One or more items that can be played. |
| `start` | integer | Optional. The `id` of the item that plays at power-on. Without it the LEDs stay dark until a play command arrives. |

Each item has an `id`, an integer from 1 to 65,535 that is unique in the file, and is one of
two kinds:

| Kind | Members | Meaning |
|---|---|---|
| Animation | `id`, `file` | `file` is the name of an `.odrg` file in the folder: 1 to 32 characters from `a`-`z`, `0`-`9`, `-`, `_` and `.`, ending in `.odrg`. |
| Cycle | `id`, `cycle`, `seconds` | `cycle` is a list of one or more ids of animation items. `seconds` is how long each one is shown, 1 to 65,535. |

Example: two animations, and a cycle that alternates them every 15 seconds and starts at
power-on.

```json
{
  "version": 1,
  "brightness": 128,
  "items": [
    {"id": 1, "file": "hello.odrg"},
    {"id": 2, "file": "dvd.odrg"},
    {"id": 3, "cycle": [1, 2], "seconds": 15}
  ],
  "start": 3
}
```

## Playing

- Playing an animation item shows it from its first frame and loops it forever.
- Playing a cycle shows each listed animation in order for `seconds`, then starts over, and
  repeats forever. Each turn starts its animation from the first frame.

## When a show is invalid

A show is invalid when `mapping.json` or `show.json` is missing or breaks its format, when an
id is used twice, when a cycle or `start` names an id that does not exist, when a cycle names
a cycle, or when a listed `.odrg` file is missing, breaks its format, or has a canvas size
different from the mapping's.

With an invalid show the LEDs stay dark, and the status command reports what is wrong.
