# Commands

The board and the emulator accept the same commands, handled by the same code. A command
exists only if something really uses it.

## Lines

A command is one line of text ending in a newline; a carriage return before the newline is
ignored. Words are separated by single spaces. A line is at most 64 characters.

Every command gets exactly one reply: a JSON object on one line.

- Success: `{"ok":true}`, with more members for `status`.
- Failure: `{"ok":false,"error":"<code>"}`.

## Commands

| Command | Effect |
|---|---|
| `play <id>` | Plays the item with that id from [show.json](show.md), from its first frame. |
| `on` | Switches the LEDs on. |
| `off` | Switches the LEDs off: every LED is dark. Playback time keeps running. |
| `brightness <n>` | Sets brightness, 0 to 255. |
| `status` | Reports the current state. |

At power-on the LEDs are on, brightness is the value in `show.json`, and the `start` item is
playing if there is one. Changes made by commands are not kept across a restart.

Brightness scales every colour value v to `(v * brightness + 127) / 255`, rounded down.

## Status reply

```json
{"ok":true,"on":true,"brightness":128,"playing":3,"animation":1,"fps":50,"error":null}
```

| Member | Meaning |
|---|---|
| `on` | Whether the LEDs are switched on. |
| `brightness` | Current brightness, 0 to 255. |
| `playing` | The id of the item being played, or `null`. |
| `animation` | The id of the animation item on the LEDs right now, or `null`. It differs from `playing` when a cycle is playing. |
| `fps` | LED refreshes in the last full second. |
| `error` | `null`, or the reason the show is invalid. |

## Error codes

| Code | When |
|---|---|
| `unknown-command` | The first word is not a command. |
| `bad-argument` | An argument is missing, extra, not a number, or out of range. |
| `unknown-id` | `play` names an id that is not in `show.json`. |
| `show-invalid` | `play` was sent while the show is invalid. |
| `line-too-long` | The line is longer than 64 characters. |

## Transports

A transport only carries lines to the command front-end and replies back. The commands and
replies are the same on every transport.

| Where | Serial | Network |
|---|---|---|
| Board | The USB serial port. | HTTP over Wi-Fi, on the board's web server. |
| Emulator | A virtual serial port on a Mac. On Windows, and on a Mac when asked, the same lines on a TCP port of 127.0.0.1. | HTTP on the emulator's page address. |

**HTTP.** A command is sent as `POST /odrig` with the command line as the request body, with
or without the final newline. The response body is the reply line, with content type
`application/json`. The response status is 200 whenever the line reached the command
front-end, including replies with `"ok":false`. Any other method on `/odrig` gets status 405.
