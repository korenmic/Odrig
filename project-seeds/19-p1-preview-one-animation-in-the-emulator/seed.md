# Preview one animation in the emulator

## Summary

One command takes the path of one finished animation file, an `.odrg` file, and shows it:
it starts the emulator with that animation alone, opens the emulator's page, and plays the
animation until the command is stopped.

## Priority

- `P1`

## Depends On

- Seed 03, the emulator, and seed 11, which made it run on Windows.
- Seed 06, the JavaScript converter, which builds the folder of an installed show.
- Seed 07, the content commands: `upload` puts an animation file into a running emulator.
- Seed 16: with one animation installed, the playlist of everything is that animation.
- Seed 18, one converter: nothing but the converter runs converter logic. This seed keeps
  to that, whether it is built before seed 18 or after it.

## Product Context

Whoever makes an animation wants to see it on the canvas before it goes to the board. The
emulator shows an installed show: a folder with a show file, a mapping file and the
animation files. For a file that is already finished, that folder is made by hand today:
`pack` builds the animation files of a show from JSON frames sources, and takes no
finished `.odrg` file. Then the emulator is started on the folder, and the page is opened
by hand. That is several steps and two programs for one look at one file.

On 2026-10-13 the owner asked for one line: the full path of an `.odrg` file goes in, and
the emulator's page playing that animation comes out.

## Technical Constraints

- The command holds no converter logic, and it is no second writer of an installed show.
  What has to be built of a show, the JavaScript converter builds, started as a program.
  What has to be put into a running emulator goes through the content commands.
- The animation file is not changed and not converted again: the bytes that play are the
  bytes of the file.
- The file is checked by the code that would check it on the board. A file the board
  would refuse is refused here, with the reason.
- Nothing is written beside the animation file, and nothing into a tracked folder of the
  repository. What the command makes, it makes under `build/` or in a temporary folder,
  and it removes it when it ends.
- It runs on macOS and on Windows with what the getting-started page sets up, and it
  installs nothing.
- It leaves no process behind: stopping the command stops the emulator.
- A preview can be started while another emulator runs: a port that is taken is not a
  failure.
- The emulator, the command tool and the converter keep the command lines they have.

## Required Behavior

1. The command with the path of an `.odrg` file, absolute or relative, starts the emulator
   with that animation as the only one installed, and prints the address of the page.
2. The page opens in the default browser. An option leaves the browser alone.
3. The animation plays at once. When it ends it starts again, until the command is
   stopped with Ctrl-C.
4. The canvas is the installation's, 60 by 60, from `mapping/legs-20.json`, unless an
   option names another mapping file. An animation whose canvas is not the mapping's is
   refused, and the message names both sizes.
5. A path with nothing there, a file that is no ODRG file, and a file the player refuses
   each end the command with status 1 and one line that says why. No emulator is left
   running, and no browser is opened.
6. When the port of the page or the port for command lines is taken, the command takes a
   free one, and prints what it took.
7. When the core's library is not built, or Node.js or the converter's packages are not
   there, the command names the step of the getting-started page that is missing, and
   starts nothing.
8. The getting-started page and the emulator's page of the documents show the command.

## Definition Of Done

1. On Windows and on macOS the one line, with the path of an animation file, opens the
   page, and the animation plays.
2. The emulator's suite has a test for every point of the required behaviour that needs
   no person, and it passes on both systems.
3. A test says that the command's code takes nothing from the converter's code and
   writes no file of a show itself.
4. After the command has ended, no process of it runs and nothing it made is left.
5. The owner has looked at one animation with it. Only a person can make that check.

## Open Questions

1. Where the command lives and what it is called: an option of `python -m emulator`, a
   subcommand of the command tool, or a small program of its own. The spec decides, inside
   the first constraint.
2. How the file gets into the emulator. One way: the emulator starts on a show without
   items, which the converter builds, and the file is uploaded with `upload`, as the
   operators' app will do it on the board. The other way: the converter learns to build a
   show from finished `.odrg` files. The first needs no new converter code and uses the
   path the board has; it is proposed. The spec decides.
3. More than one file, and a video or a GIF that is converted first, are not in this
   seed. Choosing among many animations is planned apart, with the interface of the
   operators' app. Converting is one more command before this one.
