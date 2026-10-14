# Requirements: preview one animation in the emulator

Seed: [`project-seeds/19-p1-preview-one-animation-in-the-emulator/seed.md`](../../../project-seeds/19-p1-preview-one-animation-in-the-emulator/seed.md).

Today a finished `.odrg` file is looked at in the emulator only after a show folder was
made for it by hand. This spec adds one command that takes the path of the file, starts
the emulator with that animation alone, opens the emulator's page and plays it until the
command is stopped.

The seed leaves three questions to the spec. They are answered here:

1. The command is a small program of the emulator's package: `python -m emulator.preview`.
   It is the emulator's matter, it needs nothing of the command tool's command line, and
   the emulator's own command line stays as it is.
2. The file gets into the emulator the way the board gets one: the converter builds a
   show without items, the emulator starts on it, and the file is uploaded with the
   content commands. No converter code is added, and the file is checked by the core.
3. One file, an `.odrg` file, is all this seed takes.

In this document "the command" is `python -m emulator.preview`, "the file" is the `.odrg`
file it is given, and "the mapping" is the mapping file the preview uses.

## Requirement 1: one command, one animation

**User story.** As whoever makes an animation, I want to see a finished file on the
installation's canvas with one line, before it goes to the board.

1. The command with the path of a file, absolute or relative, SHALL start the emulator
   with that animation as the only item of its show, and SHALL print the address of the
   page.
2. The page SHALL open in the default browser. With `--no-browser` no browser SHALL be
   opened.
3. The animation SHALL play from its first frame, again and again, until the command is
   stopped with Ctrl-C.
4. The mapping SHALL be `mapping/legs-20.json`, the installation's 60 x 60 canvas, unless
   `--mapping FILE` names another.
5. The bytes that play SHALL be the bytes of the file. The file SHALL NOT be changed.

## Requirement 2: what is refused

1. A path with nothing there, or that is no file, SHALL end the command with status 1 and
   one line that says so, before anything is started.
2. A file that the player refuses SHALL end the command with status 1 and one line with
   the reason the player gives, as [reasons.md](../../reasons.md) lists it: a file that is
   no ODRG file is `bad-magic`.
3. A file whose canvas is not the mapping's SHALL end the command with status 1 and one
   line that names both canvases.
4. WHEN the command ends with status 1 THEN no emulator SHALL be left running and no
   browser SHALL have been opened.

## Requirement 3: what it needs, and what it leaves

1. WHEN the core's library is not built, or Node.js is not there THEN the command SHALL
   name the step of [getting-started.md](../../../agent/getting-started.md) that is
   missing, end with status 1, and start nothing.
2. WHEN the port of the page, 8600, is taken THEN the command SHALL take a free one and
   SHALL say so. The ports of the virtual serial port and of the line port SHALL be ones
   of its own, so that a preview runs beside another emulator.
3. The command SHALL write nothing beside the file and nothing into a tracked folder. What
   it makes it SHALL make under `build/preview/`, and SHALL remove when it ends.
4. WHEN the command has ended THEN no process of it SHALL be running.

## Requirement 4: no second converter

1. The command SHALL hold no converter logic: what is built of a show, the JavaScript
   converter builds, started as a program; what the file holds, the converter's `check`
   says, started as a program; whether it plays, the core decides.
2. The command SHALL write no file of a show itself. The show without items that it
   packs is a tracked source, `shows/preview/show.json`.
3. The emulator, the command tool and the converter SHALL keep the command lines they have.

## Requirement 5: tests and documents

1. The emulator's suite SHALL have a test for every point of Requirements 1 to 4 that
   needs no person, and a test SHALL say that the command's code imports nothing of a
   converter and writes no show file.
2. [getting-started.md](../../../agent/getting-started.md) and
   [emulator.md](../../emulator.md) SHALL show the command.
3. The owner SHALL look at one animation with the command. Only a person can make that
   check.

## Left out on purpose

- More than one file, a folder of files, and a video or a GIF that is converted first.
- Choosing among animations: the operators' app does that.
- Watching the file for changes and showing them again.
