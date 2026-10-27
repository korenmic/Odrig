# The operators' app

An Android app with which operators see and steer what the installation plays, from a
phone on the installation's Wi-Fi network. This page says what the app does, how it is
built, installed and used, what it says when something fails, and what has been checked.

## What it is

The app has four screens, and a tab for each at the bottom: `Animations`, `Upload`,
`Settings` and `Target`. Its look is the owner's Aurora Glass: a midnight background with
teal and violet aurora, translucent rounded panels with a restrained glow, light text, and
a top bar with the app's name and whether the installation answers.

- **Animations** says what the installation does and holds its animations. A panel says
  what plays, the animation on the LEDs with its id and its file name, `ON` or `OFF`, the
  brightness and the refreshes a second, with `On` and `Off` together in one pill and a
  slider for the brightness. Under the refreshes, while the installation reads its
  animations after a start, a line says how far it is, as `Reading the animations: 12
  read, 72 to read.`; see [Using it](#using-it). A compact panel has the two storage lines: each begins with
  the number of animations of that storage, as
  `Internal storage: 84 animations, free 6.7 MB of 13.5 MB` and
  `External storage: 12 animations, free 3.1 GB of 31.9 GB (read-only).`, without
  `(read-only)` while the installation can write its card: the board's
  own from `space`, the external storage's by `external` of `list`. A medium that is
  present without animations says `0 animations`; an absent one says `absent` with no
  number. While the board still reads its animations after a start, the external number
  is `animations not known yet`, and while the show is invalid the internal one is
  `animations not known`. Below them is `Add animation`, which opens Upload; then, when
  Settings says so, the pinned Tests group; then two filters and the one list of
  animations, one level of the card's folders at a time, as a file explorer shows them.
  Above the list stands the level's heading, `Root` or the folder's whole path, as
  `night/deep`, with `Back` inside a folder and the button `Play this folder`, which
  makes the level's playlist current. At the root the list holds the board's own
  animations and the loose files of the card, in the saved order of the playlist, then
  one row for each folder of the card, with the folder's name, how many animations it
  holds itself and a chevron; a tap on a folder row enters it, and the list then holds
  that folder's own files and the rows of its sub-folders. A folder with no file of its
  own keeps its row, `0 animations` and its way in. The heading is marked while the
  level's playlist is current, and so is the folder row that leads to the current
  playlist at every level above it. The list comes back to the root when the target
  changes, when the card goes out and when the folder shown is gone from the list. Each row
  names its file, its id and its size, or `size not read yet` while the installation has
  not read the file whole, has a badge `in` (internal storage) or `ex` (external storage,
  read-only unless the installation can write its card), and a small `...` button that
  opens its menu. Cycles are not listed. An
  animation that the installation found unavailable, because its file had a fault, is
  drawn grayed with its reason in words under it, such as `Unavailable: the file is
  damaged (truncated).`, and a tap on it plays nothing; one of a card that the
  installation cannot write adds `Fix it on a computer: the card is read-only here.` Its
  menu works as any other's. The
  other animations and every other control work as ever, also when every animation is
  unavailable.
- **Upload** makes an animation from a video or a GIF of the phone, or makes a text or a
  clock, and uploads it, with the free internal storage above it. While the installation
  can write its card, an animation of a video or a GIF goes to the card unless
  `This board` is chosen, and the card's free storage is there too.
- **Settings** has the checkbox `Show test animations`, the catalogs of the board's own
  storage and of the card with a rebuild of each, the mapping editor: the twenty saved
  snake-to-pin assignments, and the current limits: a budget in mA for the wall and one for
  each snake, each with the estimate of the current beside it. It has no copy of the power
  or brightness controls.
- **Target** has the address of the installation, says whether it answers, names the
  installation and the last fault it met in a file, and says how the phone's requests
  travel.

The app is one more client of the commands of [commands.md](commands.md). It sends
thirty-eight command lines and no other, each as `POST /odrig` to the address that is set:

| The operator | The line |
|---|---|
| Nothing: once a second while the app is on the screen | `status` |
| Nothing: when the target first answers, every ten seconds, when the list is out of date, and every second while the target answers `busy` | `list 0`, and `list <next>` for a long show |
| Taps a row of the list, or presses `Play this folder` inside a folder | `play <id>` |
| Presses `Play this folder` at the root | `play all` |
| Presses `On` or `Off` | `on`, `off` |
| Moves the slider | `brightness <n>` |
| Nothing: at boot, reconnect, return to the app, entering Animations or Upload, every ten seconds while either is visible, and after upload or deletion | `space` |
| Chooses Delete in a row's menu and then `Remove it` | `remove <id>` |
| Chooses Ignore in playlist or Restore to playlist in a row's menu | `ignore <id> <0-or-1>` |
| Confirms Delete selected | `remove many <ids>` |
| Presses `Upload to the installation` | `upload begin <id> <file> <bytes>`, then `upload data <offset> <base64>` for each piece, then `upload end <crc32>`, sent again while the installation still checks the file |
| Presses `Upload to the installation` with `The card` chosen | `upload begin external <file> <bytes>`, then the pieces and the end as for an upload |
| Presses `Cancel` while it uploads | `upload cancel` |
| Chooses Edit in the menu of a text's or a clock's row | `read <id> <offset>`, from offset 0 until the whole file is read |
| Presses `Save` for a text or a clock it edits | `upload begin <id> <file> <bytes>`, then `upload expect <crc32>` with the CRC-32 of the file it read, then the pieces and the end as for an upload |
| Opens Settings, reloads, or waits two seconds while Settings is visible; on Animations every two seconds while nothing plays, which is so during a test, and after a test is started or stopped | `mapping get` |
| Drags a pin of the mapping into another place, presses an arrow key on its handle, or presses Restore defaults | `mapping set <revision> <pins>` |
| Ticks or clears `Snake 10 is cross-wired` | `mapping cross on`, `mapping cross off` |
| Presses `Diagonal` in the Tests group, or `Stop test` | `mapping test on`, `mapping test off` |
| Presses a snake's test in the Tests group | `mapping test snake <n>` |
| Nothing: after every complete list, and its further parts for a long one | `order get`, and `order get <next>` |
| Lets go of a row it dragged, or presses Move up or Move down | `order move <revision> <id> <before>` |
| Opens the target screen while the installation answers | `fault` |
| Opens Settings, or waits two seconds while Settings is visible, and after it sent a rebuild or a cancel | `catalog` |
| Presses `Rebuild the board's catalog` or `Rebuild the card's catalog`, and then `Rebuild` | `catalog rebuild internal`, `catalog rebuild external` |
| Presses `Cancel the rebuild` | `catalog cancel` |
| Opens Settings, waits two seconds while Settings is visible, and after it saved a budget | `limits`, and `limits <next>` for a mapping of many legs |
| Changes the wall's budget in `Current limits` and presses Enter or leaves the field | `limits wall <mA>` |
| Changes a snake's budget there and presses Enter or leaves the field | `limits snake <n> <mA>` |

It uses the shared command protocol and shows only what a reply said. Mapping saves
require firmware that supports the mapping commands; an older target gives a readable
unsupported message.

Inclusion changes wait for acknowledgement before showing saved state. The list refreshes
periodically so changes from serial or another app become visible. Older targets whose
list lacks the inclusion flag keep playback controls but have no mutation controls.
Deletion sends at most 32 distinct ids per batch on the existing serialized command stream.
A refused batch preserves the remaining selection; a missing reply reports only the
confirmed count and refreshes the list before another attempt. It never retries a lost
delete reply automatically. Changing target clears selection and confirmation, and stale
replies cannot change the new target's screen. Leaving the app stops unsent batches.
Uploads and deletions disable conflicting controls until their operation has ended.

The web code, `app/www/`, is plain JavaScript, HTML and CSS: a browser runs the files as
they are. Capacitor wraps them into the Android app. One class of Java, the sender,
carries each line to the target; see [The phone and the installation's
network](#the-phone-and-the-installations-network).

## What you need

- For the web code in a browser, and for its suite: what the rest of the repository needs,
  and Chrome.
- For the APK: a Mac with Apple Silicon, Node.js 22 or later as `node`, and a network
  connection for the first setup. Nothing is installed in the system: everything goes into
  `app/node_modules/` and `build/app/`, which git ignores.
- For installing by cable: a phone with USB debugging switched on.

## The tool

```
python3 app/app.py setup
python3 app/app.py build
python3 app/app.py install
python3 app/app.py serve [--port N]
```

The tool uses the standard library of Python only. It ends with status 0 when the command
did its work, with 2 when the command line was not understood, and with 1 and one line
`error: <reason>: <detail>` on standard error when it could not do its work:

| Reason | Condition |
|---|---|
| `node-missing` | `node` is not found, or is older than 22. |
| `unsupported-platform` | `app/toolchain.json` has no entry for this system and processor. |
| `download-failed` | An archive could not be fetched. |
| `checksum-mismatch` | An archive has another size or SHA-256 than the tracked one. It is removed. |
| `licence-refused` | The SDK's tool accepted another licence than `android-sdk-license`, or left a package out. |
| `setup-failed` | A program of the setup ended with a status other than 0. The detail has the end of its output. |
| `build-failed` | Capacitor's `sync` or Gradle ended with a status other than 0, or left no APK. |
| `no-device` | `install`: no phone, or more than one, is connected by USB and ready. |
| `address-in-use` | `serve`: the port is taken. |

### setup

```
python3 app/app.py setup
```

Puts what a build needs into the project folder. A step whose result is there is skipped,
so a second run takes a second.

| What | Version | From | Where it goes |
|---|---|---|---|
| Capacitor: `@capacitor/core`, `@capacitor/cli`, `@capacitor/android` | 8.5.3 | npm, by `app/package-lock.json` | `app/node_modules/` |
| The Temurin JDK | 21.0.12.1+1 | Adoptium, 200 MB | `build/app/jdk/` |
| The Android SDK's command-line tools | 15859902 | Google, 156 MB | `build/app/android-sdk/` |
| The SDK packages `platform-tools`, `platforms;android-36`, `build-tools;35.0.0` | as the SDK's tool resolves them | Google, 159 MB | `build/app/android-sdk/` |

- The two archives are named in `app/toolchain.json` with their size and their SHA-256. A
  file that differs is refused and removed. The archives are kept in
  `build/app/downloads/`, so a setup can be repeated without the network.
- The SDK packages are under the licence `android-sdk-license`. The owner accepted the
  Android SDK's licence terms, and the tool accepts that one licence and no other: it
  refuses to go on when the SDK holds another accepted licence.
- Gradle 8.14.3, 225 MB, is fetched by the first build, by the Android project's own
  wrapper, which checks its SHA-256; it and what it fetches go into `build/app/gradle/`.
- After a build the work folder `build/app/` has about 2.2 GB. Removing it removes
  everything a setup and a build made, the debug key among it; see [Installing on a
  phone](#installing-on-a-phone).

### build

```
python3 app/app.py build
```

Runs the setup, copies the web code into `build/app/www/` with a note of the commit it
was built from, and beside it the scripts of the converter's library, `converter/lib/`,
into `build/app/www/converter/`; lets Capacitor copy that into the Android project
`app/android/`, lets Gradle build it, and prints three lines:

```
apk: /Users/you/odrig/build/app/odrig-debug.apk
bytes: 4137137
sha256: 43ab3067c7bd119157837774377a34b2965030036d4d9d7738ce540cd104bbe0
```

The first build takes about a minute, a later one about five seconds. A build of the same
files gives the same bytes. Nothing of a build stays running, and nothing is written
outside the repository's folder.

When distributing an update from another worktree, use the same ignored debug keystore
as the existing APK (`build/app/android-user/debug.keystore`). A freshly generated key
has a different certificate and Android cannot use it to update the installed package.
The mapping APK delivery retains the previously published certificate; no key is tracked.

### install

```
python3 app/app.py install
```

Installs `build/app/odrig-debug.apk` on the one phone that is connected by USB, with the
`adb` of the SDK in the work folder. The phone asks once whether this computer may debug
it.

### serve

```
python3 app/app.py serve
```

Serves the web code on `http://127.0.0.1:8610/`, or on the port `--port` names, for a
browser on this computer, and runs until it is stopped. The converter's library is served
beside it under `/converter/`, from `converter/lib/` as it is: the web code imports it
from there, and no copy of it is kept in `app/`. With an emulator running beside
it, write the emulator's address, `127.0.0.1:8600`, into the app's target screen.

The emulator shows the app by itself as well: its page has a view `Controller`, at
`http://127.0.0.1:8600/#controller`, with the app beside the LEDs and aimed at that
emulator. It serves the same files of `app/www/`, and the converter's library under
`/app/converter/`, so a change of the web code shows there after a reload. This is the quickest way to try the app: see
[emulator.md](emulator.md#the-controller-view).

## Installing on a phone

Either connect the phone by USB and run `python3 app/app.py install`, or copy
`build/app/odrig-debug.apk` to the phone and open it there; the phone then asks whether
apps from this source may be installed. The app is called `odrig`.

The APK is a debug build, signed with a key that the first build made in
`build/app/android-user/`. An app signed with another key does not replace it: after the
work folder was removed, or on another computer, remove the app from the phone before
installing a new build.

The app needs Android 7 or later, and a web view of version 80 or later. On a phone with
an older web view it says so, and says to update "Android System WebView" in the Play
Store. It asks for no permission that the phone shows a question for.

## Using it

1. Join the phone to the installation's Wi-Fi network, `odrig`, in the phone's Wi-Fi
   settings; [wifi.md](wifi.md) has the network. The app joins no network itself.
2. Start the app. It begins on the target screen with the installation's address,
   `4.3.2.1`, and says `Checking`, then `Answers` or `No answer`. As soon as the
   installation has answered once, the app shows Animations.
3. On Animations, tap an animation to play it: the playlist goes on with the
   animation after it. `Play this folder` at the root goes back to the first animation
   of the root playlist; a tap on a folder's row enters it, and `Play this folder` there
   makes that folder's playlist current, from its first animation; the installation
   keeps the choice across a restart. `Back` goes up one level. `Off`
   makes every LED dark and `On` lights them again; the playlist's time goes on while
   they are off. The slider sets the brightness from 0 to 255.

What the screens show comes from the installation's replies, about once a second: when
another phone changes something, this one shows it within two seconds. While the
installation does not answer, the values are dimmed and a line says for how long and why;
the app goes on asking and recovers by itself. While the app is not on the screen of the
phone it sends nothing, and the phone's screen stays on while the app is in front.

Right after the installation was switched on, Animations has the state and the rows
at once, in the saved order: the installation plays from its first moment, and `On`,
`Off`, the slider and `Play this folder` work. The installation reads what it has
installed while it plays; until it has read a file whole, its row says `size not read
yet`, and a file in which it finds a fault turns unavailable. Moving an animation waits
until it has read them all: the installation refuses a move with `busy` until then, and
the app says so. With a few small animations that is over within two seconds; with the
storage full of heavy ones it takes longer, see
[firmware.md](firmware.md#measurements-on-the-board).

Meanwhile a line under the refreshes says how far the installation has read, from
`readiness`, `checked`, `to_check` and `unavailable` of `status`:
`Reading the animations: <n> read, <m> to read.`, with `, <k> unavailable` before the
full stop when it has found some unavailable. When it has read them all and some are
unavailable, the line says `<k> animations unavailable; the others play.`, or
`1 animation unavailable; the others play.`; when it has read them all and every one plays,
and on an installation whose software does not say, there is no line. No time is given for
the rest, as the installation gives none. Every control works meanwhile, and the
refreshes are counted as refreshes a second as at any other time.

The target screen names the installation as its software names itself, from `host` of
`status`, as `Installation: odrig emulator on Darwin arm64`: the board gives its release,
the date and the time of its build, its storage and the reason of its last start. Each
time the screen is opened while the installation answers, the app asks for `fault` and
says the last fault the installation met in a file since its start, as
`Last fault: b.odrg, while it was played, at frame record 3 after 1234 bytes of its
frames: the file is damaged (truncated).` The work is `checked after the start`,
`played`, `checked after its upload` or `read from the external storage`, and the words
of the reason are those of an unavailable row. The reason is what the installation found
in the bytes it read; it does not say whether the storage is damaged. An installation that
names nothing, or met no fault, or whose software does not know `fault`, shows no such
line.

A cycle of the show is not in the list and cannot be started from the app. While one
plays, Animations says `Cycle` with its id, and `Play this folder` leaves it.

The filters count the rows of the level shown and hide only rows: a folder row stays
whatever the filters, and `No animation matches the filters.` speaks of the level's rows.
`Select` and `Select all` take the rows of the level shown. An upload to the card puts
the file in the card's folder `odrig` itself, the root level; a folder row is no
animation, so it is not counted in the storage lines, not offered by the filters and not
taken by `Select all`.

The line that says what plays names the current playlist and the time left in its window
of 24 hours of running time, from `status`: `Playlist · 23 h 12 min left` for the root
while the card has folders, `Playlist night · 23 h 12 min left` for a folder by its
path, and `Playlist night, the root plays for now · 23 h 12 min left` while the root
plays in a folder's place, because the folder has nothing to play yet or an animation
outside it was tapped. With no folder on the card, or none in, the line is `Playlist`
without a time, as before. A folder the list does not hold yet, right after a card is put
in, is named by its id until the list has come.

A tap on a row plays its animation. Its `...` button opens the row's menu and plays
nothing. The menu of an internal animation has `Ignore in playlist`, or `Restore to
playlist` when it is ignored, `Move up`, `Move down`, `Select` and `Delete`; the menu of an
animation of the external storage has `Move up` and `Move down`, and `Delete` while the
installation can write its card; otherwise it says that external storage is read-only. An ignored row says `Ignored` with a sign and its name is muted; it
keeps its place in the order and the playlist passes over it. A change of inclusion shows
`Saving...` on the row until the installation has confirmed it.

`Delete` asks `Remove animation <id> <file> from the installation?`, or for an animation
of the card `Remove animation <id> <file>? Its file is deleted from the card.`; `Remove it`
removes it, and `Keep it` sends nothing. Afterwards the app says `Removed animation <id>
<file>.`, and the list and the free storage are asked for again. An animation that a cycle
plays, or that a USB stick or a card the installation cannot write holds, cannot be
removed: the installation refuses it, and the app says why. A file of a card the
installation can write that has a fault is deleted from its menu, or uploaded again under
its name, which keeps its id. `Select`, in the menu or above the list, starts the selection mode: a checkbox on
each internal row, `Select all`, `Clear selection`, `Delete selected` and `Done`. The
question names the count and the files before anything is sent; the deletion goes in
batches of at most 32, and a refusal or a lost reply says how many were deleted. The back
gesture goes from Upload, Settings or the target screen to Animations.

Two filters stand above the list, each a row of choices with the number of animations it
would show beside each: `Storage` with `All`, `Internal` and `External`, and `Type` with
`All`, `Normal`, `Text` and `Widget`. A row is shown when it matches both; each choice
counts with the other filter as it is, as `External 12`, and a choice with 0 can still be
chosen. Storage goes by where the installation says an animation is; Type by its type, an
animation that names none being Normal, as every animation is until the installation's
software has text and widget animations. When no row matches, the list says
`No animation matches the filters.` with `Show all`, which sets both back to `All`. The
choices stay on the phone across a restart of the app, and another phone has its own. A
filter changes only what the list shows: not the playlist, its order, an animation's
inclusion or what plays. While a filter hides rows, an animation cannot be moved, by a
long press or by Move up and Move down, and the list says so; `Select all` takes the
shown rows only, and a row a filter hides leaves the selection. The Tests group is not
filtered. While the card is out, `External` counts 0.

To move an animation in the order of the playlist, hold its row for half a second: it
lifts, and a dashed place shows where it lands as the finger moves; near the top or the
tabs the list scrolls. Letting go saves the order on the installation; the row says
`Saving...` until the installation's order comes back. Letting go where it began, or a
cancelled touch, moves nothing. `Move up` and `Move down` in the row's menu do the same
without holding. A mouse drags as a finger does, in a browser and in the emulator's
Controller view. A row moves within the level shown only: the dashed place stays among
the rows of the level, above its folder rows, `Move up` is off for the first row of the
level and `Move down` for the last, and a row let go where it began, or at the level's
edge where it already stands, sends nothing. Internal and external animations stand in one order, which the
installation keeps; an external animation keeps its place by its file name while its
medium is out. The order cannot be changed, and the list says why, while the installation
does not answer, keeps no order (older software, whose list stays in its show's order), a
move, an upload or a deletion is under way, or the selection mode is on. When another
controller moved something meanwhile, the installation refuses the move with
`order-conflict`, the app says so and reads the order again; it never moves again by
itself.

To make an animation, open Upload, or press `Add animation`, press `Choose a video or a
GIF` and pick a file; the phone shows its own picker. The app shows the file's name, and for a video its
length. Then:

1. Choose how the picture fits the canvas: `Fill`, at first, covers the whole canvas and
   cuts off what does not fit at two sides; `Fit` shows all of the picture, with the rest
   of the canvas black; `Stretch` stretches it to the canvas, as wide and as high as it
   is. These are the fits of the converter, [converter.md](converter.md#import).
2. Choose the part: `Start at` in seconds, 0 at first, and `Length` in seconds, empty for
   the rest of the file. Up to three decimals, as `2.5`.
3. Press `Make the animation`. The app says how far it has come, as
   `Making the animation: 40%`, and `Stop` ends it. The rest of the app keeps working.
4. The animation is drawn in a loop, for the canvas of the installation, with what it is:
   `25 frames, 2.50 s, 31 KB`.

The canvas is the one the installation reports in `status`, so the app converts for the
installation it is pointed at. The phone's web view decodes the file: a GIF with its
`ImageDecoder`, and a video by showing it frame by frame in a video element, one picture
every 20 ms. The converter's library, the same that runs on a computer, fits the pictures
and makes the file. A GIF gives the very file the converter's command line makes of it; a
video gives the same frames, and colours that may differ by a little, as two decoders'
colours do. A video is drawn at most 1,280 pixels wide or high before it is fitted.

`Upload to the installation` sends the animation to the installation as a new item:

- Its id is the lowest from 1 up that no item has. Its file name is the name of the
  file it was made from, without its ending, in lower case, every character other than
  `a`-`z`, `0`-`9`, `-` and `_` turned into `-`, with `.odrg`, at most 32 characters,
  and `-2`, `-3` and so on when the name is taken: `Sunset Beach.mp4` becomes
  `sunset-beach.odrg`.
- First the app compares its size with the free storage; one that does not fit is not
  sent.
- While it sends, the app says `Sending: 45%, 12 KB a second`, and `Cancel` stops it.
  The app's status keeps coming meanwhile. While the app is not on the screen of the
  phone it sends nothing, and when it is back the upload goes on; when the installation
  dropped it meanwhile, after a minute, the app says so.
- The installation checks the whole file before it takes it, which takes about a
  fiftieth of a second for each frame. Then the app says
  `Uploaded as animation <id> <file>. It plays in the playlist.` The animation is last in
  the list of Animations and in the playlist until it is moved, and plays when it is
  tapped.

While the installation can write its card, `space` says so with `"read_only":false`, and
Upload has `Store on` above `Upload to the installation`, with `The card`, chosen at
first, and `This board`, and the card's free storage under the board's: the card holds the
animations, and the board's own storage keeps one or two to fall back on. An animation for
the card goes as `upload begin external <file> <bytes>` with the same file name, then its
pieces and its end as above; the card gives it its id, from 60001 up, and its place in the
playlist by its name, and the app says `Uploaded to the card as animation <id> <file>. It
plays in the playlist.` The app does not compare its size with the card's free storage
first: the installation refuses one that does not fit before anything is sent, and the app
says so. While the card cannot be written, or is out, Upload has no choice and stores on
the board, as before. Texts and clocks are stored on the board, though the card may hold
them too.

To make a text, press `Make a text` on Upload. A form opens under it: the text, written
with English letters, digits, signs and Hebrew letters, and line feeds; its font,
`Small`, `Medium` or `Large`; its colour and its background; its effect, `Still`,
`Marquee`, `Slide in and out` or `Pan`, and its motion, to the left, to the right, up or
down; its alignment and its height on the canvas; its direction, as the text begins,
left to right or right to left; whether long lines wrap; its speed in pixels a second and
its pause in milliseconds. Below the form the text moves in a preview of the
installation's canvas, drawn by the converter's library as the player draws it, and a
line says `One pass takes 4.50 seconds.`, or why the text cannot be made: a character no
font has, named with its code point, or a block that cannot be seen whole with the
effect, with the effects that show it. `Upload to the installation` sends it as a new
item, as a video's animation is sent, as an `.odrgx` file named after its first English
words, `hello-world.odrgx`, or `text.odrgx` when it has none; `Close` closes the form.
[format.md](format.md) has what a text holds.

To make a clock, press `Make a clock`. Its form has the kind, `With hands`, `With digits`
or `Melting watch`; the seconds of a loop, 30 at first; the colours of its face, its
hands, its rim and its background; and its least and its greatest speed, how many times
faster than real time its imaginary time runs. The preview shows it as the installation
will, with a time, a speed and, for the melting watch, a shape chosen at random as each
turn of it on the installation chooses them; `New random time` shows another. A line says
`One loop takes 30.00 seconds.`, or names a number that is out of its range. It is
uploaded as a text is, as `clock-<kind>.odrgx`, `clock-analog.odrgx` for one with hands.

A text or a clock of the board's own storage has `Edit` in its row's menu. The app reads its
file back from the installation, opens its form on Upload, titled with its id and its
file, as `Animation 5 hello.odrgx`, and fills it with what the file holds. `Save` sends
the changed file to the same id under the same name, so the animation keeps its place in
the list and the playlist and whether it is ignored, and says `Saved animation <id>
<file>.`. The installation takes it only while the file it holds is the one the app read:
when another controller changed or removed the animation meanwhile, it refuses with
`stale`, the app says so, nothing is overwritten, and the form keeps the edits. An
animation of the card or of a USB drive has no `Edit`: that storage is read-only here.

The animations of a microSD card or a USB drive plugged into the installation are rows
too, with the badge `ex`, each with its id from 60001 up and its file's name on the
medium, and a tap plays one as it plays an installed animation; see
[show.md](show.md#animations-from-a-usb-drive). They come a moment after the drive is
plugged in, once the installation has read them, and go about ten seconds after it is
pulled out, when the app asks for the list again. Besides Upload's choice and a row's
`Delete` while the installation can write the card, the app has no code of its own for
them.

To point the app at an emulator, write the emulator's address on the target screen and
press `Use`; `Board` puts `4.3.2.1` back. An address is a host name or an IPv4 address,
alone or with a port, as in `192.168.1.23:8600`. For a phone to reach an emulator, start
it with `--lan`; see [emulator.md](emulator.md#from-a-phone).

A long press marks text, and opens the phone's menu of copying and pasting, only in a
field one types into: the address on the target screen, and `Start at` and `Length` on
Upload. Anywhere else, on a word, a button, a list or an empty part of the screen, a long
press marks nothing and opens nothing, and a tap works as before; on a row of the list a
long press lifts the row to be moved, and nothing else. In a
browser a right click does the same: the browser's menu opens only in a field. A field
that the app gets later is the same as these three.

The app keeps clear of the phone's bars: its heading begins below the bar at the top,
with the clock and the icons, and its tabs end above the bar at the bottom, with
Android's three buttons or the line of gesture navigation. Held sideways, it keeps clear
of a bar or of the camera at a side too. The room comes from what the phone reports for
its bars and its camera, so it fits each phone; it shows the app's midnight, and the
bars' icons are light on it. What scrolls up goes under a band of midnight at the top, and the
last line of a list can be scrolled above the tabs. While the phone's keyboard is open
for a field, the tabs are hidden, so that they do not stand over the field, and the field
stays in view; they come back when the keyboard closes. In a browser there are no bars,
and the page keeps no room.

**Catalogs.** A catalog says what a storage holds, so that the installation reads no
animation at its start, or when the card goes in, for the files it has a catalog of; see
[catalog.md](catalog.md). Settings' panel `Catalogs` has a line for each storage, from
`catalog`, which the app asks when Settings is opened and every two seconds while it is
shown:

| The catalog | The line |
|---|---|
| `ok` | `Board: 84 animations, cataloged.`, with `; 2 more not cataloged yet` before the full stop for files of the show it has no entry for; `Card: 122 animations, cataloged.` |
| `none` | `Board: not cataloged yet; its 84 animations are read whole at every start.`; `Card: not cataloged yet; its animations are read whole each time it goes in.` |
| `loading` | `Card: reading its catalog.` |
| `damaged` | `Board: catalog damaged (a page); its animations are read whole at every start until a rebuild.`, the part named `its marker`, `a page`, `a line` or `a change was cut off`; `Card: catalog damaged (...); its animations play only after a rebuild.` |
| `incompatible` | `Board: catalog of another version; ...`, and the card's, as for a damaged one |
| `absent` | `Card: none in the installation.` |

`Rebuild the board's catalog` and `Rebuild the card's catalog` ask first, as `Rebuild the
catalog of the board? The installation reads every animation of the board whole, which
takes a while; it plays on meanwhile.`; `Rebuild` sends `catalog rebuild internal` or
`catalog rebuild external`, and `Not now` sends nothing. A rebuild of a storage without a
catalog is its first catalog. While a rebuild runs, from this phone or another controller,
the panel says `Rebuilding the catalog of the board: 12 of 84 animations read.` with
`Cancel the rebuild`, which ends it and leaves the catalog as it was; both buttons are off
meanwhile. Animations says how far the installation has read, as after a start, and every
control works; when the rebuild has ended, the list is asked for again. The card's rebuild
needs a card the installation can write; for one it cannot, the panel says `The
installation cannot write this card; a computer can make its catalog.`, as
[microsd.md](microsd.md#the-catalog-made-on-a-computer) has it. A refused rebuild is said
in the place for messages. An installation whose software keeps no catalogs says `This
installation's software keeps no catalogs.` and is not asked again.

**Mapping.** The twenty snakes stand in a fixed column, `Snake n · columns a–b`, left to
right when viewed from the front, each starting at the bottom and running up, down, up;
beside each snake stands the data pin that drives it, `GPIO p`. Only the installed 60x60
geometry is editable. A pin is moved by dragging its handle `≡` up or down, or by holding
it as a row of the playlist is held: the snakes keep their places, and the pins between
move one place. Every time the dragged pin passes into another place, the whole
permutation is saved at once with the revision it was read with, while the finger is
still down, so that the LEDs follow the drag; the summary says `Saved: GPIO p drives snake
n.`. Several quick places are saved one after another, the latest last; after the pin is
let go the assignment is read once and shown. The arrow keys on a handle move its pin one
place and save it the same way. When another controller changed the mapping meanwhile the
save is refused, said, the drag ends and the target's assignment is shown; when no reply
confirms a save, the drag ends, the assignment is read once again and nothing is sent
twice. Restore defaults saves the default assignment at once, offered only when the
installed pin set matches those defaults; Reload reads the assignment again. No new pin
can be entered. The read every two seconds changes the column only when the target's
mapping changed, and never while a pin is held or moves are saved.

**Snake 10 is cross-wired.** Under the column a checkbox, off by default, says whether the
installation's snake 10 is chained around its dead data output: up line 28, up line 30
and down line 29, where the other snakes run up, down, up. It shows what the installation
says, `cross` of `mapping get`, and the read every two seconds follows a change made by
another controller. A tap saves at once with `mapping cross on` or `mapping cross off`, as
a drag saves a move, and the summary says `Saved: snake 10 is cross-wired.` or `Saved:
snake 10 is wired as the others.`; a refusal is said as a save's is, and the box shows the
installation's state again. The box cannot be used while the mapping is not editable, while
a move is saved or a pin is held. It changes no pin: whatever pin drives position 10, its
three lines are wired as the box says. On, the snake's LEDs show the picture right, the
test of snake 10 climbs its three lines together, and the diagonal's stub at position 10
rises like the others.

**The mapping from a photo.** Under the mapping's column, `From a photo` takes an image
file of the phone, a JPEG or a PNG, through the phone's own chooser: no camera is part of
the app. The photo is taken with the whole wall in it and the diagonal showing, in a room
as dark as can be had, the edge where the wires come in at the bottom of the picture or,
when the wall is seen from the side, at its left; `Show the diagonal` starts the diagonal
while it is not showing. The diagonal lights, in each snake, three LEDs whose height tells
the snake's number, so one photo tells which snake each position drives. The app finds the
bright peaks of the picture and scans the brightness from the brightest level down, as if
brightening the picture little by little, until the count of peaks holds steady over a
long stretch of levels: the lit LEDs, all about as bright, come in together, and then
nothing new comes until the lenses of the unlit LEDs and the room's reflections flood in,
a few at every level. A lit room is the normal case; a picture whose count never settles
is refused. The app takes the slant out, places the LEDs on the grids of sixty columns and
sixty rows by the pitch between neighbours, tells from the slope of the stubs whether the
wall is seen upright or from the side, and reads for each position the snake its LEDs
vote for. It shows the photo scaled down with a circle and the snake's number at each
position, and the words `Position 3 shows snake 7.` for each position whose snake is not
its own, or `Every position shows its own snake.`; `Apply` saves the mapping that puts
every position right, with the revision last read, as a drag saves one, and the column
shows it; `Discard` drops the photo, as leaving Settings does. The reading is a best
effort: a snake that does not light leaves no LEDs, and its number goes to the position
that remains, `Position 5 shows no snake; snake 12 goes there.`, drawn dashed. Which edge
the wires are at, the picture cannot tell, nor a dark end of the wall from the other end:
the readings are offered as choices, `Wires at the bottom` or `Wires at the top` for a
wall seen upright, `Wires at the left` or `Wires at the right` for one seen from the
side, with `Position 1 dark`, `Position 20 dark`, `Lowest snake missing` or `Highest
snake missing` when an end is dark, the advised edge first; only the wall tells them
apart, and after Apply whether the diagonal begins at the bottom left; `Other reading`
applies the next one. Bright spots off the grid are ignored and counted; a photo with no
steady set of bright spots, with fewer than two lit LEDs, or with LEDs that fit no grid,
is refused with the count found and the advice, and `Try another photo`. Nothing of the
photo leaves the phone. A photo of the installation with snake 10 cross-wired and `Snake
10 is cross-wired` off shows position 10's stub broken: its first LED in its place, its
other two on the position's other two lines in the rows of another snake. The reading
leaves that snake with the position that shows it whole, gives position 10 no snake and
then the snake no other position shows, its own, and says `Position 10 shows no snake`;
apply the reading, then tick the box.

**The test animations.** `Show test animations` in Settings, off at first and
remembered on the phone, shows the pinned Tests group above the list of Animations: `Tests
· 21`, which can be folded, with `Diagonal` and `Snake 1` to `Snake 20`. The diagonal
shows one white line on black from bottom left to top right; the test of snake n a white
block of 3 x 3 pixels that runs up and down the snake's three columns, one row every 40
milliseconds, lighting each of its LEDs in turn, with every other LED dark. Each goes
through the saved mapping and keeps the target's
power and brightness. A test is never a row of the list: it cannot be ignored, selected,
deleted or moved, and no playlist, start, cycle or order includes it. While a test shows,
from this phone or another controller, the now-playing panel says `Test: Snake 3 is
showing. Normal playback is paused.` with `Stop test`, which restores the previous
playback selection; a tap on an animation ends the test too. The group says why its tests
are off for a mapping that is not the twenty-snake installation's, and for software
without them. Only the person looking at the LEDs can judge a test.

Mapping requests use the same single request stream as playback and uploads. Changing
the target clears the draft and discards older replies. A failed save is not retried: the
app reads the target once to reconcile, preserves the draft and asks for Reload before a
new attempt. Storage failures, busy/invalid shows, stale revisions and unsupported targets
have readable messages in Settings.

**Current limits.** Under the Mapping panel, Settings' panel `Current limits` holds the
budgets of the current the LEDs may draw, each a ceiling in mA on WLED's estimate of that
current, not a measurement: a picture estimated above a budget is dimmed until it is within
it, the wall as a whole or one snake, and a low wall budget also dims the diagonal that the
mapping from a photo reads. [commands.md](commands.md#current-limits) has the commands and
[core.md](core.md#current-limits) the estimate and the dimming. The field `The wall's
budget, mA` has the wall's estimate beside it, as `Estimate 3,616 mA`; under it, while
`mapping get` reports the installation's twenty snakes as editable, a row for each snake,
`Snake n · columns a–b`, with its field and its estimate. For another mapping, or none, the
panel has the wall's field alone. A field takes digits only, and a budget of 0, no limit,
shows as an empty field that says `No limit`.

Text that differs from the budget read last is saved when Enter is pressed in its field or
the field is left, with `limits wall <mA>` or `limits snake <n> <mA>`; an emptied field
saves 0, and text that is the budget read last, however written, sends nothing. Under the
field the panel says `Saving…`, then `Saved: the wall's budget is 2,000 mA.`, `Saved: the
wall has no limit.`, `Saved: snake 3's budget is 500 mA.` or `Saved: snake 3 has no
limit.`. Several fields changed quickly are saved one after another. A value above its
range is not sent: the panel says `The wall's budget is 0 to 250,000 mA, 0 for no limit.
Its saved budget is shown.` or `A snake's budget is 0 to 65,535 mA, 0 for no limit. Its
saved budget is shown.`, and shows the saved budget. A refused save is said under its field
in words, and the saved budget is shown again:

| The refusal | What the panel says |
|---|---|
| `bad-argument` | The installation cannot take this budget: the value is out of its range, or its mapping has no such snake. |
| `busy` | The installation is busy reading its animations, uploading or rebuilding a catalog. Try again after it finishes. |
| `show-invalid` | The installation has an invalid show. Fix its show before setting a budget. |
| `storage-error` | The installation could not save its budgets. Its saved budget is shown. |
| another code | The installation refused the budget: `<code>`. |
| no reply | No confirmed reply. The budgets were read again; check this one before setting it again. |

Beside a budget from 1 to the number of the LEDs, 3,600 mA for the wall and 180 mA for a
snake, the panel says `At this budget every LED is held at its lowest level.`, and never
beside 0. A wall or a snake that its budget dimmed at the latest refresh has `Dimmed`
beside its estimate. While no budgets are saved the panel says `No budgets are saved: the
wall's budget is the installation's default.`: on the board WLED's stored maximum less
120 mA, 730 mA with the tracked 850, which holds the installation's 3,600 LEDs at their
lowest level; in the emulator no limit. From the first save on, the budgets are saved, the
wall's default among them. The panel reads `limits`, and `limits <next>` in the same
request for a mapping of many legs, when Settings is opened, every two seconds while it is
shown, and after each save. A read updates every estimate, mark and warning, but never the
text of a field that has the focus or holds text not saved yet, and nothing is read while
a save is out or waits. An installation whose software does not know `limits` gets the
explanation, `This installation's software has no current limits.` and nothing to set, and
is not asked again until the target changes. The panel is the same in the APK, in a
browser and in the emulator's Controller view, whose LEDs show the limiting once budgets
are saved, as the board's do.

## Messages

The shared message panel gives each failure as a sentence with its code in brackets at
its end. Mapping shows its recovery message inline until Reload or Cancel. A panel message stays until
it is dismissed with `OK` or another takes its place.

| Code | When | The sentence |
|---|---|---|
| `bad-address` | The text written as the address is none. | That is not an address. Write it like 4.3.2.1 or 192.168.1.23:8600. |
| `no-wifi` | The phone is on no Wi-Fi network. | This phone is not on a Wi-Fi network. Join the network odrig in the phone's Wi-Fi settings. |
| `no-answer` | No reply came within five seconds. | No answer from `<address>`. Check that the phone is on the installation's Wi-Fi network and that the installation has power. |
| `bad-reply` | Something answered that is not an installation. | Something answered at `<address>`, but it is not an odrig installation. |
| `line-too-long`, `unknown-command`, `bad-argument` | The installation's software is older or newer than the app. | The installation did not understand the app. Its software and this app do not match. |
| `show-invalid` | The installed show cannot be played. | The installed show is invalid: `<reason>`. Nothing can be played until a show is installed over USB. |
| `unknown-id` | The animation that was pressed was removed meanwhile. The list is asked for again. | Animation `<id>` is not installed any more. |
| `unknown-id` | `Play this folder` at the root on a show without an animation. | No animation is installed. |
| `unavailable` | A play of an animation whose file had a fault in this boot, or of a cycle of only such. | Animation `<id>` cannot be played until it is replaced: its file has a fault. The list says which. |
| `busy` | A removal while the installation still reads what it has installed after a start, or while an upload is open; a rebuild while another runs or an upload is open; an upload to the card while its catalog is read. | The installation is busy. Try again in a moment. |
| `in-use` | A removal of an animation that a cycle plays or that a USB stick holds. | Animation `<id>` cannot be removed: a cycle plays it, or it is on a USB stick. |
| `read-only` | A removal of an animation of the card while the installation cannot write it. | Animation `<id>` cannot be removed: the card cannot be written now. |
| `read-only` | An upload to the card while the installation cannot write it. | The card cannot be written now. Choose This board to store the animation on the board. |
| `read-only` | A rebuild of the catalog of a storage the installation cannot write. | That storage cannot be written now, so its catalog cannot be rebuilt. |
| `storage-error` | The installation could not read or write its storage. | The installation could not use its storage. |
| `in-use` | An upload whose id or file name another item took meanwhile. | That name or id is in use on the installation. The list is asked for again; upload again. |
| `no-space` | An upload that does not fit, before it is sent or as the installation judges it. | The animation needs `<size>` KB, and the installation has `<free>` KB free. |
| `no-space` | An upload to the card that does not fit on it. | The animation needs `<size>` KB, and the card has `<free>` KB free. |
| `no-upload` | The installation dropped the upload: nothing came for a minute. | The installation dropped the upload, after the app was away for a minute or more. Upload again. |
| `bad-checksum`, `incomplete`, `bad-offset` | Bytes of the upload were lost on the way. | The upload did not arrive whole. Upload again. |
| `bad-file` | The installation refused the file it checked. | The installation refused the file: `<reason>`. |
| `mapping-conflict` | A save used an assignment another controller changed. | Mapping changed on the target. Reload before saving. |
| `order-conflict` | A move used an order that another controller, an upload or the card changed. | The order changed on the installation since the app read it. The list is read again; move the animation again. |
| `stale` | A text or a clock that was edited was changed or removed by another controller since it was read. | Another controller changed this animation since it was opened. Your changes are still here; open it again to see the new one. |
| any other | The installation refused a command for a reason the app has no sentence for. | The installation refused the command. |

Two more lines are not failures of a command. While the installation does not answer, the
show screen says `The installation has not answered for 12 seconds.`, with the number
counting up. While its show is invalid, both screens say `The installed show is invalid:
<reason>.`; [reasons.md](reasons.md) lists the reasons.

When an animation cannot be made, the app says why:

| Code | When | The sentence |
|---|---|---|
| `unsupported-character` | A text holds a character no font has. | The fonts have no letter for `<characters>`. Write English letters, digits, signs and Hebrew letters. |
| `does-not-fit` | A text cannot be seen whole on the canvas with its effect and motion. | The text cannot be seen whole on the canvas with this effect: `<the effects that show it>`. |
| `no-canvas` | The installation reports no canvas: it has no mapping it can use, or its software is older than the app. | The installation has no usable mapping, so the app does not know the canvas to convert for. |
| `no-gif-decoder` | The phone's web view has no `ImageDecoder`. | This phone's web view cannot read GIF files. Update Android System WebView. |
| `unreadable-media` | The web view cannot read the file as a video or a GIF. | The phone cannot read this file as a video or a GIF. |
| `bad-part` | `Start at` or `Length` is no number of seconds. | Write the start and the length in seconds, like 2.5, and leave the length empty for the rest of the file. |
| `bad-range` | The part does not lie inside the file. | The part does not lie inside the file. Make the start earlier or the length shorter. |

Any other reason of the converter is said as `The animation cannot be made:` with the
converter's own words and its reason in brackets.

A removal and an upload that succeeded are said in the same place, without a code:
`Removed animation <id> <file>.`, `Uploaded as animation <id> <file>. It plays in the
playlist.`, `Uploaded to the card as animation <id> <file>. It plays in the playlist.` and
`Saved animation <id> <file>.`

## The phone and the installation's network

The installation's network has no internet. A phone that joins such a network keeps
sending its apps' traffic over mobile data, and may say that the network has no internet
or offer to sign in to it. A request that an app sends in the ordinary way would then
leave through mobile data and never reach the installation.

So the app's Android code, the sender, asks the system for the phone's Wi-Fi network,
whether or not it has internet, and opens every request on that network. It sends each
command line once: a line that got no answer is not sent a second time by itself. The
operator leaves mobile data as it is.

The target screen says how requests travel:

| The line | It means |
|---|---|
| `Sent over Wi-Fi.` | The phone is on a Wi-Fi network that has internet, such as a home network with an emulator on it. |
| `Sent over Wi-Fi. This Wi-Fi network has no internet: the phone's other apps use mobile data.` | What is expected on the installation's network. |
| `Sent over Wi-Fi. This Wi-Fi network has no internet.` | The same, with mobile data off. |
| `The phone offers to sign in to it. That is not needed.` | Added when the phone takes the network for one with a sign-in page. |
| `This phone is not on a Wi-Fi network.` | Join `odrig` in the phone's Wi-Fi settings. |
| `Sent from this browser.` | The web code runs in a browser and not in the app. |

The app allows plain HTTP, because the installation speaks nothing else, and it sends to
no address but the one that is set. Anyone on the network can send the same commands with
any program: the network's password is what keeps others out.

## The check on a phone

This is the owner's. No program can do it. Each step says what must be seen.

**Before:** `python3 app/app.py build`; the board running the firmware, with its show
installed; the phone with mobile data on.

1. **Install.** `python3 app/app.py install` with the phone on USB, or copy
   `build/app/odrig-debug.apk` to the phone and open it. *Seen:* the app `odrig` is on the
   phone and starts on the target screen with the address `4.3.2.1`.
2. **The emulator.** On the Mac: `python -m emulator build/demo-20/show --lan`; allow
   incoming connections if macOS asks. Phone and Mac on the same Wi-Fi network. Give the
   app the address of the emulator's `lan:` line. *Seen:* `Answers`, `Sent over Wi-Fi.`,
   and then the show screen.
3. **Status.** *Seen:* the show screen has what the emulator's page has: on, the
   brightness, `Playlist`, the animation with its file name, about 50 refreshes a second.
   Send `python -m odrigctl --http 127.0.0.1:8600 brightness 40` on the Mac: the phone
   shows 40 within two seconds.
4. **Controls.** `Off`, `On`, the slider, each animation, `Play this folder` at the root.
   *Seen:* the emulator's page follows each, and its log has each line as `http`.
5. **No answer.** Stop the emulator. *Seen:* within five seconds the app says that
   nothing answers, in words. Start it again: the app recovers by itself.
6. **The installation's network.** Power the board. In the phone's Wi-Fi settings join
   `odrig` with the password. Leave mobile data on. Note what the phone says about the
   network and what you answered. In the app press `Board`. *Seen:* `Answers`, and a line
   that says the Wi-Fi network has no internet.
7. **Mobile data at the same time.** Open a web page in the phone's browser. *Seen:* it
   loads, and the app still shows the board's status.
8. **Every action on the board.** Steps 3 and 4 again. *Seen:* the LEDs follow each
   action. While one strip is fed from the board itself, as on the desk today, keep the
   brightness at 40 or less.
9. **Mobile data off.** Switch mobile data off and repeat step 3. *Seen:* the same.
10. **Removing.** With the emulator of step 2, on Animations, open the `...` menu of an
    animation that no cycle plays, choose `Delete`, and `Remove it`. *Seen:* the app says it
    removed the animation, the row is gone, and the free storage grew.
11. **Converting.** On `Upload`, choose a short video filmed with the phone, held
    sideways, and then a GIF; try each fit and a part of a few seconds, and press
    `Make the animation`. *Seen:* the progress, the animation drawn in a loop as the
    file looks, and its frames, length and size. Note how long a video of ten seconds
    took.
12. **Uploading.** Press `Upload to the installation`, to the emulator on the local
    network and then to the board on its own network. *Seen:* the progress with its speed,
    then `Uploaded as animation ...`; the animation is last in the list of Animations and
    plays on the emulator's page and on the LEDs when its row is tapped.
13. **A long press.** Hold a finger for a second on a line of Animations, on the button
    `On`, on the `...` of a row, on an empty part of the screen, and then on the address of
    the target screen. *Seen:* outside the address no text is marked and no menu opens; in
    the address a word is marked and the menu of copying and pasting opens. The buttons
    still work by a tap. Note whether a long press on a button pressed it too.
14. **The phone's bars.** Hold the phone upright, and then sideways, on each screen.
    *Seen:* the heading is below the clock and the icons at the top, and the tabs
    `Animations`, `Upload`, `Settings` and `Target` are wholly above Android's buttons or the
    line of gesture navigation; sideways, nothing of the app lies under a bar or the camera
    at a side. On Animations and on Settings, scroll to the end: nothing shows under the
    clock, and the last line stands above the tabs. On the target screen, tap the
    address: the keyboard opens, the tabs go away and the address stays in view; they
    come back when the keyboard closes. Note whether the phone has three buttons or
    gesture navigation.
15. **The numbers of animations.** On the board's network, with the microSD card in,
    once the list has come. *Seen:* `Internal storage:` begins with the number of the
    board's own animations and `External storage:` with the number of the card's, and
    both match what `python3 -m odrigctl --port … space` and `list` say. Take the card
    out: within twenty seconds the external line says `absent (read-only).` with no
    number; put it back: the number comes back.
16. **The look and the menus.** On each tab, upright and sideways. *Seen:* the midnight
    background with teal and violet, the panels, every text readable; each row has its
    `in` or `ex` badge and its `...`; a row's menu opens beside it without playing it, and
    an external row's menu says it is read-only. Choose `Ignore in playlist` and then
    `Restore to playlist`: the row says `Ignored`, and then not.
17. **Moving by a finger.** Hold a row for half a second and drag it up and down a long
    list, then let go. *Seen:* the row lifts, a dashed place follows the finger, the list
    scrolls near the tabs, the row stays where it was let go and says `Saving...` a
    moment; after a restart of the app the order is the same; the next animation of the
    playlist is the next of the new order. Use `Move up` in a row's menu too.
18. **The Tests group.** Turn on `Show test animations` in Settings and go back to
    Animations. *Seen:* the pinned group `Tests · 21` above the list; `Snake 1` lights
    the first snake's one-pixel line from its bottom left to its top right and no other
    snake, and so on to `Snake 20`; `Diagonal` the diagonal; the now-playing panel names the
    test, and `Stop test` brings the playlist back. While one strip is fed from the board
    itself, keep the brightness at 40 or less.
19. **The filters.** On the board's network with the card in, choose each choice of
    `Storage` and `Type`. *Seen:* the rows of that storage and type only, each count the
    number of rows it shows, `Show all` when none matches; after a restart of the app the
    choices are kept; while a filter hides rows, holding a row lifts nothing.
20. **A text and a clock.** On Upload, `Make a text`: write `שלום world`, choose
    `Marquee` and then each other effect and motion. *Seen:* the preview moves as the
    words say and `One pass takes` names a length; `Upload to the installation` adds a row,
    and the LEDs show the text as the preview did. Then `Make a clock` with each kind and
    upload one; choose `Edit` in its row's menu, change its seconds and `Save`. *Seen:* the
    clock's hands or digits move on the LEDs, the melting watch's hands bend with its
    face, and after the save the row is where it was.
21. **The card and the catalogs.** With firmware that writes the card, and the card in.
    On Upload, make an animation: `Store on` has `The card` chosen; upload it. *Seen:*
    `Uploaded to the card as animation ...`, its row with `ex`, and it plays on the LEDs
    when tapped. Choose `Delete` in its menu and `Remove it`. *Seen:* the row goes, and the
    card's free storage grows. In Settings, `Rebuild the card's catalog` and `Rebuild`.
    *Seen:* the count of the progress grows, Animations says how far the reading is, and the
    LEDs play on; `Cancel the rebuild` ends it, and a second rebuild that runs to its end
    leaves `Card: <n> animations, cataloged.` Keep the brightness at 40 or less while one
    strip is fed from the board itself.
22. **Note** the phone's model, its Android version, the web view's version from the
    target screen, and anything that was not as written.

## The suites

```
python3 -m unittest discover -s tests/app -t .
python3 -m unittest discover -s tests/apk -t .
```

The first runs the web code in Chrome without a window against an emulator and against
stand-in targets of its own, and takes about two minutes. It needs the core's library,
`make -C core shared`, and Chrome: the one in `/Applications`, or the program the
variable `ODRIG_CHROME` names. Nothing it does reaches another computer: what the app
would send to the installation's address ends at the suite's own server.

The second reads a built APK: its identifier, its permissions, that plain HTTP is
allowed, that the web code in it is the one of `app/www/` byte for byte, and that the
sender is in it. It needs `build/app/odrig-debug.apk` and the SDK of the work folder, and
says so when they are missing. Build again after a change of the web code, or it fails.

Neither needs a phone.

## What is verified

By programs, on a Mac:

- The four tabs and every action of the web code, in Chrome against the emulator:
  the address, the status, the list for shows of up to 40 animations, `play`,
  `play all`, `on`, `off`, the brightness with at most five commands a second, the free
  storage, a removal from a row's menu confirmed and one kept, each message, the back
  gesture across the four tabs and `Add animation`.
- The Aurora Glass look, in Chrome at 360 and 320 pixels upright and 740 sideways:
  every text at a contrast of 7:1 or more against what lies behind it, the translucent
  panels composited onto the midnight background, every control at least 44 pixels and
  the main ones 48, 8 pixels apart, the four tabs at equal width along the bottom, a
  row's menu, a message and a question above the tabs, nothing scrolling sideways.
- The rows and their menus, in Chrome against the emulator: `in` and `ex` badges by
  `external` of `list`, Ignore in playlist and Restore to playlist shown as saving until
  confirmed, a refused change read again, the selection mode with more than 32
  animations, a refused batch and a lost reply, a target change during a deletion.
- The saved order, in Chrome against the emulator: rows in the saved order with card
  animations among them; a drag by a finger and by a mouse saved where it was let go; a
  long list scrolled while a row is held near the tabs; a drag let go where it began and
  one cancelled moving nothing; Move up and Move down; a conflict, a refusal and a lost
  reply each said and read again without a second move; an older target without an order;
  moving off during the selection mode; a move of another controller shown.
- The filters, in Chrome against the emulator and against stand-in targets that report
  types: every combination of Storage and Type with its counts, the empty list and
  `Show all`, the choices kept across a reload, moving off while a filter hides rows,
  `Select all` and a filter change, the Tests group not filtered, a card pulled out and
  plugged in, a row without a type, and no request more than without the filters.
- The playlists of the card's folders, in Chrome against the emulator with a card of
  nested folders and against stand-in targets with a fixed time left: the root's rows
  and folder rows with their names and counts, a folder without a file of its own,
  entering a folder and `Back` up to the root, the heading of a level, the marks of the
  current playlist's level and of the folder rows that lead to it, the forms of the line
  that says what plays, `Play this folder` inside a folder and at the root, the Tests
  group left alone, the card out and in bringing the list to the root, a drag and `Move
  up` and `Move down` within the level only and nothing sent for a drop in place, the
  filter counts of the level, a folder row under every filter, `Select all` and the
  counts on rows only.
- The test animations, in Chrome against the emulator: the checkbox off at first and
  remembered across a reload, 21 entries pinned above the list, a snake test, stopping,
  the diagonal, a play that ends a test, a test of another controller named with the
  group hidden, a mapping of another installation explained, the tests in no list or
  order.
- Mapping in Chrome against the real emulator: twenty labelled swaps, saved/default
  drafts, Cancel/Reload, concurrent edits, uncertain save replies, target changes,
  native bridge reply validation with the snake test, and portrait/landscape layouts. See [the verification record](specs/30-p1-app-mapping-and-diagonal-check/verification.md).
- Converting in Chrome: a GIF with each fit and with a part gives the very file the
  converter's command line makes of it, and an mp4 in H.264, whole and as a part, gives
  its frames and lengths; stopping; a file that cannot be read; a target without a
  canvas.
- Uploading in Chrome: a GIF and an mp4 uploaded to the emulator, listed and played;
  `Cancel`; nothing sent while the app is away, and the upload finished when it is back;
  a file that does not fit; `upload end` answered `busy`; every refusal.
- That a long press or a right click marks text and opens a menu only in a field one
  types into, in Chrome: every element of the screens, of a message and of the
  question, fields and other elements made later, and the page for an old web view. A
  browser's "select all" marks nothing.
- That the page keeps the room of the phone's bars, in Chrome, with the room set at each
  side as the app's Android shell sets it: upright with a bar of three buttons and with
  gesture navigation, and sideways with a bar and the camera at the sides. The heading is
  below the room at the top, the tabs above the room at the bottom, nothing in the room at
  a side, nothing shows in the room at the top when the screens are scrolled, the last
  line of each list can be scrolled above the tabs, and with the keyboard open the field
  is in view and the tabs are hidden. Without the room the page is as before. The
  settings of the bars in the Android project, and in the APK.
- That the storage lines of Animations begin with the number
  of animations of each storage, in Chrome against the emulator with no drive, a drive of
  animations, an empty drive, and a drive plugged in and pulled out, and against stand-in
  targets that answer `list` with `busy` or report an invalid show.
- How far the installation has read its animations, in Chrome against a stand-in target
  that reads three and against the emulator: each count in turn, the unavailable ones,
  the end with unavailable animations, no line for an installation that has read every
  one or does not say, and the controls usable meanwhile; the target screen's name of
  the emulator and its last fault, asked once when the screen is opened, and neither line
  for a target that does not say.
- Texts and clocks, in Chrome against the emulator and against stand-in targets: the
  preview of a text and of each kind of clock is, at the time and with the seed it shows,
  the core's own drawing of the same file; a character no font has, a block that does
  not fit and numbers out of range said in words; a text and a clock uploaded, listed with
  their type and holding the converter's bytes; a cancelled upload; an edit of a text and
  of a clock saved in its place with its inclusion; another controller's change between
  reading and saving said and not overwritten; `Edit` only for the board's own texts and
  clocks.
- The catalogs and the card, in Chrome against stand-in targets and against the
  emulator: each state of each catalog in words; a rebuild asked about, answered `Not now`,
  refused, cancelled and run to its end, with its progress and Animations working
  meanwhile; a target without catalogs asked once; the emulator's board without a catalog
  and with one the PC tool wrote; an upload to a card the installation can write, with
  `This board` chosen instead, each refusal in words, and no choice for a card it cannot
  write; `Delete` of a card's animation, one with a fault among them, and none on a card
  that cannot be written; the storage lines and the badges of both kinds of card.
- The current limits, in Chrome against the emulator and against stand-in targets: the
  panel's rows for the wall and the twenty snakes, their labels, fields and estimates; a
  save by Enter and one by leaving a field, an emptied field saving 0, each saved sentence;
  text equal to the budget read and values out of range not sent, the range said; a field
  with the focus and text not saved kept through the reads while a budget set elsewhere is
  shown in another field; the reads in two parts every two seconds, and none while a save
  is out; each refusal in its own words with the saved budget shown again; the warning from
  1 to the LEDs' count and not above it, the line while no budgets are saved, the `Dimmed`
  marks; the wall's field alone for another mapping; an installation without limits asked
  once; the replies checked through the native bridge.
- That the web code sends the thirty-eight lines above and no other, and names no address
  but `4.3.2.1`.
- That a setup and a build write nothing outside the repository's folder, that every
  download has its tracked size and SHA-256, and that the SDK holds the one accepted
  licence.
- That the APK holds the web code and the converter's library byte for byte, the sender,
  the three permissions `INTERNET`, `ACCESS_NETWORK_STATE` and `CHANGE_NETWORK_STATE`,
  and the rule that allows plain HTTP.

## What is open

- **Mapping and the diagonal on the real installation.** No firmware was flashed for
  this run. Seed 30 task 5 requires the owner to inspect all twenty snakes, correct an
  assignment from the APK, see a continuous diagonal, restart and resume ordinary playback.
- **Seed 36 on the board and on a phone.** No program has dragged a row with a finger,
  seen the Aurora Glass look on a phone, or seen the snake tests and the saved order on
  the LEDs: steps 16 to 18 above, and seed 36's board session, which also removes the 21
  hand-uploaded line-test files from the board.

- **Seed 33 on a phone and on the board.** Nobody has seen the line of the reading, the
  name of the board and its last fault on a phone; that belongs to the seed's board
  session.
- **The check on a phone**, all of it. No program has run the app on a phone, and no test
  runs the sender. In particular nobody has seen yet that a request reaches the board
  while the phone has mobile data on, what the phone says about a network without
  internet, that the screen stays on, that the back gesture goes from the target screen
  to Animations and from there out of the app, that a long press marks text and
  opens its menu only in a field, and that the app keeps clear of Android's bars, upright
  and sideways, also with the keyboard open, and that the numbers of animations match the
  board's and the card's. On 2026-10-15 the owner ran the APK against
  the board on its own network and saw its state and its list; on 2026-10-16 the owner
  saw the app lie under the bars, before it kept clear of them.
- **Seed 35 against the board and on a phone.** The app's upload to the card, its
  `Delete` of a card's animation and its rebuilds were tried against stand-in targets that
  answer as [commands.md](commands.md) says, and its catalog lines against the emulator
  too; nobody has uploaded to the card, deleted from it or rebuilt a catalog from a phone:
  step 21 above, and the seed's board session.
- **Texts and clocks on a phone and on the LEDs.** No phone has made, previewed, uploaded
  or edited a text or a clock, and nobody has looked at one on the LEDs: step 20 above, and
  seed 37's board session.
- **Seed 41 on a phone and on the board.** Nobody has walked the card's folders on a
  phone, chosen a folder there and seen the board play it, restart and play it again, or
  seen the time left count down on a phone: the seed's board session.
- **Converting and uploading on a phone.** No phone has converted or uploaded an
  animation yet: whether its web view has `ImageDecoder`, how long a video of the phone
  takes to convert, and how fast an upload goes over the board's network are open.
- The build is verified on one system, macOS on Apple Silicon. `app/toolchain.json` has
  no entry for another.
- `npm audit` names three advisories of moderate severity in a package that Capacitor's
  command line uses at build time. Nothing of it is in the APK.
