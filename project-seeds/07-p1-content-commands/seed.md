# Content commands

## Summary

Four additions to the command list, on every route: report storage space, list what is
installed, remove an item, and upload an animation in chunks. They are added to the shared
core, both hosts, the command tool and the documents.

## Priority

- `P1`

## Depends On

- Seeds 02, 03 and 04, which hold the command front-end, the emulator, the command tool and
  the firmware.
- Seed 05, which changes the same code first.

## Product Context

Today a show reaches the board only over USB, by rewriting its storage with the board
stopped. Operators at the event need to see what is installed, see how much room is left,
delete an animation and add a new one, from the app, while the installation runs.

There is one list of commands for every route, and the owner approves every addition. The
owner asked for these four and approved them in the form below.

An upload has to show progress and speed, so a file travels in numbered chunks and the
receiver acknowledges each one.

## Technical Constraints

- The commands live in the shared core's command front-end. Serial and HTTP carry the same
  lines and get the same replies, on the board and in the emulator.
- `docs/commands.md` and `docs/show.md` are updated in the same change as the code and stay
  the authority.
- The host interface grows only by what these commands need: writing a file, renaming,
  deleting, and asking for free and total space.
- A change to the installed show survives a power cut at any moment: the old show or the new
  one is intact, never a mixture. New content is written to a temporary file and put in
  place by renaming.
- No heap allocation after startup in the core, as before.
- Playback continues during an upload.
- Tests that need the board are kept apart from those that do not. On the board, brightness
  stays at 40 or less.

## Required Behavior

1. A line may be up to 2,048 characters and a reply up to 1,024 bytes.
2. `space` replies `{"ok":true,"free":F,"total":T,"animations":N}`: free and total storage in
   bytes, and the number of animation items installed.
3. `list` and `list <from>` reply `{"ok":true,"items":[...],"next":X}`. Items come in the
   order of `show.json`, starting at position `from`, 0 when omitted. An animation item is
   `{"id":1,"file":"hello.odrg","bytes":1138}` and a cycle is
   `{"id":3,"cycle":[1,2],"seconds":15}`. The reply holds as many items as fit; `next` is the
   position of the first item left out, or `null`.
4. `remove <id>` removes the item from the show.
   - An animation that a cycle lists is refused with `in-use`.
   - If the item is the `start` item, the show no longer has one.
   - If the item is playing, playback stops and the LEDs go dark.
   - The animation's file is deleted when no remaining item names it.
5. Uploading an animation takes three commands:
   - `upload begin <id> <file> <bytes>` opens an upload. The id is new, or belongs to an
     animation item that the upload will replace. It is refused with `in-use` when the id
     belongs to a cycle, `bad-argument` when the file name breaks the rules of
     `docs/show.md`, `no-space` when the file would not fit, and `busy` when an upload is
     already open. The reply is `{"ok":true,"chunk":C}`, where C is the most data bytes one
     `upload data` line may carry.
   - `upload data <offset> <base64>` adds data. The offset must equal the number of bytes
     received so far, otherwise the reply is `bad-offset`. The reply is
     `{"ok":true,"received":R}`.
   - `upload end <crc32>` closes the upload. It is refused with `incomplete` when bytes are
     missing, `bad-checksum` when the CRC-32 of the data differs, and `bad-file` when the data
     is not a valid ODRG file for the canvas, with the format reason in a `reason` member. On
     success the file is in place and the item is added to the show or replaced.
   - `upload cancel` discards an open upload. An upload with no data for 60 seconds is
     discarded.
6. Changes take effect at once, without a restart, and are kept across a restart.
7. The command tool gains `space`, `list`, `remove <id>` and `upload <id> <file>`. Upload
   shows the percentage sent and the speed, and ends with a non-zero status on any failure.
8. The emulator applies these commands to the folder it was started on.

## Definition Of Done

1. Tests of the core cover every command, every error code, an upload interrupted at each
   step, and a power cut simulated at each write.
2. In the emulator, the command tool uploads an animation over serial and over HTTP, the item
   appears in `list`, plays, survives an emulator restart, and can be removed.
3. On the board over USB, the same session works. The upload speed is measured and reported.
4. On the board, `status` during an upload reports 25 or more refreshes per second, and the
   rate returns to 49 or more afterwards.
5. `docs/commands.md` and `docs/show.md` describe the new commands and error codes.
6. Uploading over the board's Wi-Fi is checked by the owner.

## Open Questions

None. Use the resolved behavior in this seed.
