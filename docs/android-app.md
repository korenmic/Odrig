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
  `Remove`. Cycles are not listed.
- **The target screen** has the address of the installation, says whether it answers, and
  says how the phone's requests travel.

The app is one more client of the commands of [commands.md](commands.md). It sends ten
command lines and no other, each as `POST /odrig` to the address that is set:

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

It adds no command, changes nothing of the installation's software, and shows only what a
reply said. It does not convert a video or upload an animation yet: that part is being
built.

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
| any other | The installation refused a command for a reason the app has no sentence for. | The installation refused the command. |

Two more lines are not failures of a command. While the installation does not answer, the
show screen says `The installation has not answered for 12 seconds.`, with the number
counting up. While its show is invalid, both screens say `The installed show is invalid:
<reason>.`; [reasons.md](reasons.md) lists the reasons.

A removal that succeeded is said in the same place, without a code:
`Removed animation <id> <file>.` The other error codes of [commands.md](commands.md)
belong to `upload`, which the app does not send yet.

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
10. **Note** the phone's model, its Android version, the web view's version from the
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

- Both screens and every action of the web code, in Chrome against the emulator: the
  address, the status, the list for shows of up to 40 animations, `play`, `play all`,
  `on`, `off`, the brightness with at most five commands a second, each message, and the
  look at widths of 360 and 320 pixels.
- That the web code sends the eight lines above and no other, and names no address but
  `4.3.2.1`.
- That a setup and a build write nothing outside the repository's folder, that every
  download has its tracked size and SHA-256, and that the SDK holds the one accepted
  licence.
- That the APK holds the web code, the sender, the three permissions `INTERNET`,
  `ACCESS_NETWORK_STATE` and `CHANGE_NETWORK_STATE`, and the rule that allows plain HTTP.

## What is open

- **The check on a phone**, all of it. No program has run the app on a phone, and no test
  runs the sender. In particular nobody has seen yet that a request reaches the board
  while the phone has mobile data on, what the phone says about a network without
  internet, that the screen stays on, and that the back gesture goes from the target
  screen to the show screen and from there out of the app.
- The build is verified on one system, macOS on Apple Silicon. `app/toolchain.json` has
  no entry for another.
- `npm audit` names three advisories of moderate severity in a package that Capacitor's
  command line uses at build time. Nothing of it is in the APK.
- The app's second part, converting and uploading on the phone, is planned.
