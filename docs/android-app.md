# The operators' app

An Android app with which operators see and steer what the installation plays, from a
phone on the installation's Wi-Fi network. This page says what the app does, how it is
built, installed and used, what it says when something fails, and what has been checked.

## What it is

The app has three screens, and a button for each at the bottom: `Show`, `Storage` and
`Target`.

- **The show screen** says what the installation does: `ON` or `OFF`, the brightness, what
  plays, the animation on the LEDs with its id and its file name, and the refreshes a
  second. Below that are two buttons, `On` and `Off`, a slider for the brightness, the
  button `Playlist from the start`, and one button for each installed animation, in the
  order of the playlist.
- **The storage screen** says how much of the installation's storage is free, as
  `Free 3.2 MB of 10.4 MB`, and lists the installed animations in the order of the
  playlist, each with its id, its file name and its size in kilobytes, and a button
  `Remove`. Cycles are not listed. Below the list it makes an animation from a video or
  a GIF of the phone, and uploads it.
- **The target screen** has the address of the installation, says whether it answers, and
  says how the phone's requests travel.

The app is one more client of the commands of [commands.md](commands.md). It sends
fourteen command lines and no other, each as `POST /odrig` to the address that is set:

| The operator | The line |
|---|---|
| Nothing: once a second while the app is on the screen | `status` |
| Nothing: when the target first answers, every ten seconds, when the list is out of date, and every second while the target answers `busy` | `list 0`, and `list <next>` for a long show |
| Presses an animation | `play <id>` |
| Presses `Playlist from the start` | `play all` |
| Presses `On` or `Off` | `on`, `off` |
| Moves the slider | `brightness <n>` |
| Nothing: when the storage screen is shown, every ten seconds while it is, and after a removal | `space` |
| Presses `Remove` and then `Remove it` | `remove <id>` |
| Presses `Upload` | `upload begin <id> <file> <bytes>`, then `upload data <offset> <base64>` for each piece, then `upload end <crc32>`, sent again while the installation still checks the file |
| Presses `Cancel` while it uploads | `upload cancel` |

It adds no command, changes nothing of the installation's software, and shows only what a
reply said.

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
   installation has answered once, the app shows the show screen.
3. On the show screen, press an animation to play it: the playlist goes on with the
   animation after it. `Playlist from the start` goes back to the first animation. `Off`
   makes every LED dark and `On` lights them again; the playlist's time goes on while
   they are off. The slider sets the brightness from 0 to 255.

What the screens show comes from the installation's replies, about once a second: when
another phone changes something, this one shows it within two seconds. While the
installation does not answer, the values are dimmed and a line says for how long and why;
the app goes on asking and recovers by itself. While the app is not on the screen of the
phone it sends nothing, and the phone's screen stays on while the app is in front.

Right after the installation was switched on, the show screen has the state at once:
the installation plays from its first moment, and `On`, `Off`, the slider and `Playlist
from the start` work. The buttons of the animations come a moment later. The
installation reads what it has installed while it plays, and until it has, it answers
the app's request for the list with `busy`. The app takes that for what it is: it shows
no message, keeps what it knows, and asks again every second. With a few small
animations that is over within two seconds; with the storage full of heavy ones it takes
longer, see [firmware.md](firmware.md#measurements-on-the-board).

A cycle of the show is not in the list and cannot be started from the app. While one
plays, the show screen says `Cycle` with its id, and `Playlist from the start` leaves it.

To remove an animation, open the storage screen and press `Remove` beside it. The app
asks `Remove animation <id> <file> from the installation?`; `Remove it` removes it, and
`Keep it` sends nothing. Afterwards the app says `Removed animation <id> <file>.`, and the
list and the free storage are asked for again. An animation that a cycle plays, or that a
USB stick holds, cannot be removed: the installation refuses it, and the app says why.
The back gesture goes from the storage screen or the target screen to the show screen.

To make an animation, press `Choose a video or a GIF` on the storage screen and pick a
file; the phone shows its own picker. The app shows the file's name, and for a video its
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

`Upload` sends the animation to the installation as a new item:

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
  `Uploaded as animation <id> <file>. It plays in the playlist.` The animation is in the
  list of both screens, has its turn in the playlist, and plays when it is pressed.

The animations of a USB drive plugged into the installation are buttons too, after the
installed ones, each with its id from 60001 up and its file's name on the drive, and a
press plays one as it plays an installed animation; see
[show.md](show.md#animations-from-a-usb-drive). They come a moment after the drive is
plugged in, once the installation has read them, and go about ten seconds after it is
pulled out, when the app asks for the list again. The app has no code of its own for
them.

To point the app at an emulator, write the emulator's address on the target screen and
press `Use`; `Board` puts `4.3.2.1` back. An address is a host name or an IPv4 address,
alone or with a port, as in `192.168.1.23:8600`. For a phone to reach an emulator, start
it with `--lan`; see [emulator.md](emulator.md#from-a-phone).

A long press marks text, and opens the phone's menu of copying and pasting, only in a
field one types into: the address on the target screen, and `Start at` and `Length` on
the storage screen. Anywhere else, on a word, a button, a list or an empty part of the
screen, a long press marks nothing and opens nothing, and a tap works as before. In a
browser a right click does the same: the browser's menu opens only in a field. A field
that the app gets later is the same as these three.

## Messages

Every failure is a sentence with its code in brackets at its end. A message stays until
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
| `unknown-id` | `Playlist from the start` on a show without an animation. | No animation is installed. |
| `busy` | A removal while the installation still reads what it has installed after a start, or while an upload is open. | The installation is busy. Try again in a moment. |
| `in-use` | A removal of an animation that a cycle plays or that a USB stick holds. | Animation `<id>` cannot be removed: a cycle plays it, or it is on a USB stick. |
| `storage-error` | The installation could not read or write its storage. | The installation could not use its storage. |
| `in-use` | An upload whose id or file name another item took meanwhile. | That name or id is in use on the installation. The list is asked for again; upload again. |
| `no-space` | An upload that does not fit, before it is sent or as the installation judges it. | The animation needs `<size>` KB, and the installation has `<free>` KB free. |
| `no-upload` | The installation dropped the upload: nothing came for a minute. | The installation dropped the upload, after the app was away for a minute or more. Upload again. |
| `bad-checksum`, `incomplete`, `bad-offset` | Bytes of the upload were lost on the way. | The upload did not arrive whole. Upload again. |
| `bad-file` | The installation refused the file it checked. | The installation refused the file: `<reason>`. |
| any other | The installation refused a command for a reason the app has no sentence for. | The installation refused the command. |

Two more lines are not failures of a command. While the installation does not answer, the
show screen says `The installation has not answered for 12 seconds.`, with the number
counting up. While its show is invalid, both screens say `The installed show is invalid:
<reason>.`; [reasons.md](reasons.md) lists the reasons.

When an animation cannot be made, the app says why:

| Code | When | The sentence |
|---|---|---|
| `no-canvas` | The installation reports no canvas: it has no mapping it can use, or its software is older than the app. | The installation has no usable mapping, so the app does not know the canvas to convert for. |
| `no-gif-decoder` | The phone's web view has no `ImageDecoder`. | This phone's web view cannot read GIF files. Update Android System WebView. |
| `unreadable-media` | The web view cannot read the file as a video or a GIF. | The phone cannot read this file as a video or a GIF. |
| `bad-part` | `Start at` or `Length` is no number of seconds. | Write the start and the length in seconds, like 2.5, and leave the length empty for the rest of the file. |
| `bad-range` | The part does not lie inside the file. | The part does not lie inside the file. Make the start earlier or the length shorter. |

Any other reason of the converter is said as `The animation cannot be made:` with the
converter's own words and its reason in brackets.

A removal and an upload that succeeded are said in the same place, without a code:
`Removed animation <id> <file>.` and `Uploaded as animation <id> <file>. It plays in the
playlist.`

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
4. **Controls.** `Off`, `On`, the slider, each animation, `Playlist from the start`.
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
10. **Removing.** With the emulator of step 2, open `Storage`, press `Remove` beside an
    animation that no cycle plays, and `Remove it`. *Seen:* the app says it removed the
    animation, the row is gone, and the free storage grew.
11. **Converting.** On `Storage`, choose a short video filmed with the phone, held
    sideways, and then a GIF; try each fit and a part of a few seconds, and press
    `Make the animation`. *Seen:* the progress, the animation drawn in a loop as the
    file looks, and its frames, length and size. Note how long a video of ten seconds
    took.
12. **Uploading.** Press `Upload`, to the emulator on the local network and then to the
    board on its own network. *Seen:* the progress with its speed, then
    `Uploaded as animation ...`; the animation is in both lists and plays on the
    emulator's page and on the LEDs when it is pressed.
13. **A long press.** Hold a finger for a second on a line of the show screen, on the
    button `On`, on an animation, on a row of `Storage`, on an empty part of the screen,
    and then on the address of the target screen. *Seen:* outside the address no text
    is marked and no menu opens; in the address a word is marked and the menu of
    copying and pasting opens. The buttons still work by a tap. Note whether a long
    press on a button pressed it too.
14. **Note** the phone's model, its Android version, the web view's version from the
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

- The three screens and every action of the web code, in Chrome against the emulator:
  the address, the status, the list for shows of up to 40 animations, `play`,
  `play all`, `on`, `off`, the brightness with at most five commands a second, the free
  storage, a removal confirmed and one kept, each message, the look at widths of 360 and
  320 pixels, and the back gesture across the three screens.
- Converting in Chrome: a GIF with each fit and with a part gives the very file the
  converter's command line makes of it, and an mp4 in H.264, whole and as a part, gives
  its frames and lengths; stopping; a file that cannot be read; a target without a
  canvas.
- Uploading in Chrome: a GIF and an mp4 uploaded to the emulator, listed and played;
  `Cancel`; nothing sent while the app is away, and the upload finished when it is back;
  a file that does not fit; `upload end` answered `busy`; every refusal.
- That a long press or a right click marks text and opens a menu only in a field one
  types into, in Chrome: every element of the three screens, of a message and of the
  question, fields and other elements made later, and the page for an old web view. A
  browser's "select all" marks nothing.
- That the web code sends the fourteen lines above and no other, and names no address
  but `4.3.2.1`.
- That a setup and a build write nothing outside the repository's folder, that every
  download has its tracked size and SHA-256, and that the SDK holds the one accepted
  licence.
- That the APK holds the web code and the converter's library byte for byte, the sender,
  the three permissions `INTERNET`, `ACCESS_NETWORK_STATE` and `CHANGE_NETWORK_STATE`,
  and the rule that allows plain HTTP.

## What is open

- **The check on a phone**, all of it. No program has run the app on a phone, and no test
  runs the sender. In particular nobody has seen yet that a request reaches the board
  while the phone has mobile data on, what the phone says about a network without
  internet, that the screen stays on, that the back gesture goes from the target screen
  to the show screen and from there out of the app, and that a long press marks text and
  opens its menu only in a field. On 2026-10-15 the owner ran the APK against the board
  on its own network and saw its state and its list.
- **Converting and uploading on a phone.** No phone has converted or uploaded an
  animation yet: whether its web view has `ImageDecoder`, how long a video of the phone
  takes to convert, and how fast an upload goes over the board's network are open.
- The build is verified on one system, macOS on Apple Silicon. `app/toolchain.json` has
  no entry for another.
- `npm audit` names three advisories of moderate severity in a package that Capacitor's
  command line uses at build time. Nothing of it is in the APK.
