# Vocabulary

The words of this project, as they are used now. Each entry uses only words explained
above it, so the page can be read from top to bottom. Where a document specifies the thing,
the entry links to it.

## The installation

- **board**: The small computer that drives the LEDs, an ESP32-S3 development board. A
  computer reaches it over USB, and it can open a Wi-Fi network of its own. See
  [firmware.md](../docs/firmware.md) and [wifi.md](../docs/wifi.md).
- **pin**: One of the board's numbered connectors. A data pin carries the signal for one
  chain of LEDs. A pin is named by the number printed beside it on the board.
- **canvas**: All the LEDs seen as one picture: a grid W columns wide and H rows high. A
  place on it is written (x, y). Both numbers start at 1, (1,1) is the bottom-left LED, x
  grows to the right and y grows upward. See [mapping.md](../docs/mapping.md#coordinates).
- **strip**: One straight run of 60 LEDs. A strip that lies flat is a row of the canvas,
  and a strip that stands upright is a column.
- **leg**: One data pin together with the three strips wired to it as one chain of 180
  LEDs. Legs are not chained to each other. In a row leg the strips are rows, and in a
  column leg they are columns. Leg N is on pin N, except legs 19 and 20, which are on pins
  21 and 47. See [mapping.md](../docs/mapping.md#legs-and-pins).
- **snake**: The way a leg's chain runs through its three strips: along the first, back
  along the second, and along the third in the direction of the first.
- **mapping**: The rule that says which LED of which leg sits at which place of the canvas.
  It is written in a mapping file, one for each physical build, kept in `mapping/`. The
  programs read the mapping file and nothing else defines the layout. See
  [mapping.md](../docs/mapping.md).
- **bench build**: The build that `mapping/legs-2.json` describes: two row legs, a canvas
  of 60 x 6, 360 LEDs. A picture drawn for it has been seen correctly on the hardware. Less
  than that is wired to the board at present: one strip of 60 LEDs, on pin 1.
- **target**: The build the installation is to have, which `mapping/legs-20.json`
  describes: twenty column legs, a canvas of 60 x 60, 3,600 LEDs. Its legs are not wired
  yet. Every program of this repository already works with it.

## What is played

- **animation**: A list of pictures of the whole canvas, each shown for a number of
  milliseconds. It plays in order and then starts again from the first picture.
- **frame**: One picture of an animation together with the time it is shown.
- **refresh**: One sending of colours to every LED. Refreshes are due every 20
  milliseconds, 50 a second, and each one puts the frame that is due at that moment on the
  LEDs. The board refreshes more slowly when the pictures are costly to work out;
  [working-rules.md](working-rules.md#the-frame-rate) says which rates are acceptable.
- **source**: The file in which an animation is kept and changed. It is tracked by git
  like program code.
- **JSON frames**: The format of a source: a JSON file that lists every frame with its
  time and the colour of every place on the canvas. It loses nothing and can be read by
  eye. It is never played. See [format.md](../docs/format.md).
- **ODRG**: The format that is played: a compact binary file, ending in `.odrg`, made
  from a JSON frames file. It holds the same picture for every millisecond as its source.
  Its body is compressed or not, as whoever makes it chooses. See [format.md](../docs/format.md).
- **generator**: A Python program that writes a source for the canvas of a mapping file.
  The generators are in `odrig/generators/`.
- **show**: What can be played and what plays at power-on, written in a file named
  `show.json`. See [show.md](../docs/show.md).
- **item**: One numbered entry of a show: one animation, or a list of animations to play
  one after the other. An item is asked for by its number.
- **cycle**: An item of the second kind: it plays several animations one after the other,
  each for a number of seconds, and then starts over.
- **playlist**: Every animation of a show, one after the other in the saved order, which
  is the order of the show file until an animation is moved, and then from the first
  again. It is what a show plays by itself. With a card whose animation folder has
  sub-folders there is a playlist for each folder, and one of them is current for 24
  hours of running time before the next one is: the root's plays the show's animations
  and the loose files of the card, then each sub-folder's once, and a folder's plays its
  own files and then its sub-folders'. A chosen playlist stays current across a restart.
- **turn**: The time an animation has in the playlist before the next one starts: unless
  the show says otherwise, the fewest whole loops that last 30 seconds. See
  [show.md](../docs/show.md#the-turn-of-an-animation).
- **installed file set**: The one folder of files that a show is installed as:
  `mapping.json`, `show.json` and the `.odrg` files the show names. Whatever plays a show
  reads this folder and nothing else. A folder made this way is also called a packed show.
  See [show.md](../docs/show.md#installed-file-set).
- **command**: One line of text sent to whatever is playing a show. The command families include:
  `play <id>`, `play all`, `on`, `off`, `brightness <n>`, `status`, `fault`, `space`, `list`,
  `read <id> <offset>`, which reads a file back, `catalog` for the catalogs of storage,
  `remove <id>`, `ignore` for playlist inclusion, `order` for the saved order of the
  playlist, `mapping` for assignments and the diagonal check, and `upload`, which
  sends a file as several lines. Each is answered by one
  line of JSON. See
  [commands.md](../docs/commands.md).

## The programs

- **converter**: The command-line tool in `converter/`, written in JavaScript and started
  as `node converter/odrig.js`. It turns a video or a GIF into a source, a source into an
  ODRG file and back, checks a file, and packs a show into an installed file set. Its
  library, `converter/lib/`, also runs in a web page. See
  [converter.md](../docs/converter.md).
- **Python library**: The Python package `odrig/`. It reads and writes the project's files,
  JSON frames, ODRG files, mapping files and shows, for the tests and the tools, and holds
  the generators. It converts nothing; it was the converter before, and what it answered to
  the converter's tests is stored with them, so that they compare the converter with it.
  See [python-library.md](../docs/python-library.md).
- **core**: The C++ library in `core/` that plays an installed file set: it reads the
  files, keeps time, handles commands and gives the colour of every LED of every leg.
  Everything that must behave the same wherever a show plays is in the core. See
  [core.md](../docs/core.md).
- **host**: A program around the core. It supplies the time, the files and a way to carry
  commands in and LED colours out, and decides nothing else. See
  [core.md](../docs/core.md#the-host-interface).
- **emulator**: The host that runs on a Mac or a Windows computer. It plays an installed file set and draws
  every LED in a web page, each placed by the mapping, so a show can be tried without the
  board. It takes the same commands as the board. See [emulator.md](../docs/emulator.md).
- **firmware**: The program on the board: WLED, a widely used open program for LED
  controllers, built with one addition that hosts the core. WLED supplies the LED output,
  the storage and the Wi-Fi. The tool `firmware/fw.py` builds it and puts it and a show on
  the board. See [firmware.md](../docs/firmware.md).
- **command tool**: The tool `odrigctl`, started as `python -m odrigctl`. It sends one
  command to the emulator or to the board, through a serial port or over HTTP, and prints
  the answer. See [emulator.md](../docs/emulator.md#the-command-tool).
- **operators' app**: The Android app in `app/` with which operators see and steer, from
  a phone, what the installation plays. It sends the same commands over HTTP. See
  [android-app.md](../docs/android-app.md).

## How the work is organised

- **owner**: The person who owns the installation and decides what this project does.
  [working-rules.md](working-rules.md#what-needs-the-owner) lists what only the owner
  decides.
- **seed**: One piece of planned work, written down before it is started: a folder in
  `project-seeds/` that holds the text, `seed.md`, and the seed's state, `state.json`.
- **spec**: What a seed is turned into before it is built: the three files
  `requirements.md`, `design.md` and `tasks.md`, in a folder of `docs/specs/` that has the
  seed's name.
- **task**: One numbered step in the `tasks.md` of a spec, with a checkbox. One task is
  one commit.
- **drift**: A question met while a spec was written or built, which was answered without
  asking the owner. Each one is recorded in [drifts.md](../docs/drifts.md) with the question, the
  answer and where the answer now stands.
