# Commands

The board and the emulator accept the same commands, handled by the same code. A command
exists only if something really uses it.

## Lines

A command is one line of text ending in a newline; a carriage return before the newline is
ignored. Words are separated by single spaces. A line is at most 2,048 characters.

Every command gets exactly one reply: a JSON object on one line of at most 1,024 bytes.

- Success: `{"ok":true}`, with more members for `status`, `space` and `list`.
- Failure: `{"ok":false,"error":"<code>"}`.

## Commands

| Command | Effect |
|---|---|
| `play <id>` | Plays the item with that id from [show.json](show.md), from its first frame. |
| `on` | Switches the LEDs on. |
| `off` | Switches the LEDs off: every LED is dark. Playback time keeps running. |
| `brightness <n>` | Sets brightness, 0 to 255. |
| `status` | Reports the current state. |
| `space` | Reports the free and the total storage and the number of animations. |
| `list`, `list <from>` | Lists the items of the show. |
| `remove <id>` | Removes an item from the show. |

At power-on the LEDs are on, brightness is the value in `show.json`, and the `start` item
is playing if there is one. What `play`, `on`, `off` and `brightness` change is not kept
across a restart. What `remove` changes is: it changes the installed show.

Brightness scales every colour value v to `(v * brightness + 127) / 255`, rounded down.

A number in a command is written in decimal digits.

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

## Storage and the installed items

```
space
{"ok":true,"free":8372224,"total":10354688,"animations":2}
```

`free` and `total` are bytes of the storage the show is in. `animations` is the number of
animation items of the show, and 0 while the show is invalid.

```
list
{"ok":true,"items":[{"id":1,"file":"hello.odrg","bytes":1138},{"id":2,"file":"dvd.odrg","bytes":1612},{"id":3,"cycle":[1,2],"seconds":15}],"next":null}
```

The items come in the order of `show.json`, beginning at the position `<from>`, counted
from 0, which is 0 when it is left out. `<from>` is 0 to 65,535. An animation item has its
`id`, its `file` and the size of that file in `bytes`. A cycle has its `id`, the ids of its
animations in `cycle`, and its `seconds`. The reply holds as many items as fit into it.
`next` is the position of the first item that was left out, to be asked for with
`list <next>`, or `null` when the last item is in the reply. A position at or after the end
gives no items and `null`, and so does a show without items:
`{"ok":true,"items":[],"next":null}`. While the show is invalid, `list` is refused with
`show-invalid`. A cycle too long to fit into a reply by itself is listed with
`"cycle":[]`.

## Removing an item

```
remove 2
{"ok":true}
```

The item leaves the show, and the items after it move up.

- An animation that a cycle lists is refused with `in-use`: remove the cycle first.
- If the item is the `start` item, the show has no `start` afterwards.
- If the item is playing, playback stops and the LEDs go dark. Anything else that plays
  goes on undisturbed.
- The animation's file is deleted when no remaining item names it.

## Error codes

| Code | When |
|---|---|
| `unknown-command` | The first word is not a command. |
| `bad-argument` | An argument is missing, extra, not a number, or out of range. |
| `unknown-id` | `play` or `remove` names an id that is not in `show.json`. |
| `show-invalid` | `play`, `list` or `remove` was sent while the show is invalid. |
| `line-too-long` | The line is longer than 2,048 characters. |
| `in-use` | `remove` names an animation that a cycle lists. |
| `storage-error` | The storage could not be read or written. The show is as it was. |

## Transports

A transport only carries lines to the command front-end and replies back. The commands and
replies are the same on every transport.

| Where | Serial | Network |
|---|---|---|
| Board | The USB serial port. | HTTP over Wi-Fi, on the board's web server. |
| Emulator | A virtual serial port on the Mac. | HTTP on the emulator's page address. |

**HTTP.** A command is sent as `POST /odrig` with the command line as the request body, with
or without the final newline. The response body is the reply line, with content type
`application/json`. The response status is 200 whenever the line reached the command
front-end, including replies with `"ok":false`. Any other method on `/odrig` gets status 405.
