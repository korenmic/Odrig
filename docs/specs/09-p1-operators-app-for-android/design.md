# Design: Operators' app for Android (seed 09)

## Overview

The app is a folder of plain web code, `app/www/`, packaged by Capacitor into an Android
APK together with a copy of the converter library that the build makes. It is one more
client of the command list: everything it does is a `POST /odrig` with a command line of
`docs/commands.md`.

1. **`status` gains `width` and `height`**, in the core, so that the phone knows the
   canvas it converts for. This is the one change to the command list, and the owner
   approved it.
2. **The emulator gains `--lan`**, so that a phone can reach it.
3. **A tool, `python3 app/app.py`**, installs a JDK, the Android SDK and the Capacitor
   packages into the project folder, builds the debug APK with one command, and serves
   the web code to a browser on the Mac.
4. **On the phone a small plugin, the sender, carries every request** through the phone's
   Wi-Fi network with `Network.openConnection`, because Android does not route an app's
   traffic to a Wi-Fi network without internet while mobile data is there. In a browser
   the same web code sends with `fetch`.
5. **Media is decoded by the web view**: a GIF by `ImageDecoder`, a video by
   `VideoDecoder`, which the app feeds from the file's own table of samples. So every
   frame has the exact time the file records, and the library, unchanged, builds the same
   ticks as the converter on a computer.
6. **The suite drives the web code in headless Chrome against the emulator**, through
   the page itself. What only a phone can show is a numbered list for the owner.

Decisions taken where the seed left a point open are in `docs/drifts.md` under "Seed 09".
What goes beyond the seed is listed at the end.

## What this design relies on

Seeds 06, 07 and 08 are not implemented. Their designs were read for this one, and the
code of seeds 02 to 05 as it is. A task that finds one of these different follows the code
and records the difference in `docs/drifts.md`.

| Where | What is there |
|---|---|
| Seed 06 `design.md`, "The library", "How the library is given frames" | `converter/lib/index.js` offers every module. `timeline.importFrames(source, {width, height}, {fit, startMs, durationMs})` takes `source = {kind, frames}`, `kind` being `"video"` or `"gif"` and `frames` a synchronous or asynchronous iterable; a video frame is `{width, height, rgba, time}`, `time` a whole number of milliseconds or `[n, d]`; a GIF frame is `{width, height, rgba, delayMs}`. It takes one frame at a time, stops asking when the part is covered and then calls the iterable's `return`. `timeline.videoFrames` and `timeline.gifFrames` turn times and delays into starts and ends. `odrg.encode(animation, {compressed})` gives the file as a `Uint8Array`. A refusal is a `Rejection` with `reason` and `detail`. No file of `lib/` names `fetch`, `document`, `window` or a module of Node.js. |
| Seed 06 `requirements.md`, Requirement 12 criteria 7 and 8 | A source frame that is on screen at no tick is not fitted. Reading stops when the part is covered. |
| Seed 06 `design.md`, "GIF pictures" | The pictures of a GIF follow the rules of browsers, so that a web view and the command line agree. |
| Seed 07 `design.md`, "The text of docs/commands.md" | The commands `space`, `list`, `remove` and `upload`, their replies and the fourteen error codes with their order; a line of 2,048 characters, a reply of 1,024 bytes, an HTTP body of 4,096 bytes; `chunk` 1,500; base64 with `-` and `_` and no padding; the CRC-32 of zlib; `busy` while a file is checked; an upload given up after 60 seconds without progress; one upload for all routes. |
| Seed 07 `design.md`, "The emulator" | `--storage BYTES`, and the content commands applied to the folder the emulator was started on. |
| Seed 08 `design.md` | The network `odrig`, WPA2 with the password of `firmware/wifi.json`, the board at `4.3.2.1`, four devices at once as read in the source. |
| `core/src/commands.cpp` | `status()` writes the reply member by member and ends with `error`. `Core` has `width`, `height` and `leg_count`, set from the mapping file; without a valid mapping there are no legs. |
| `tests/core/support.py`, `test_status.py` | `ReferencePlayer._status` builds the same reply; a test compares its exact bytes and the example of `docs/commands.md`. |
| `emulator/httpd.py`, `app.py` | The server is bound to `("127.0.0.1", port)`. A reply to `POST /odrig` carries `Access-Control-Allow-Origin: *`; any other method on `/odrig` gets 405. `app.py` prints the lines `page:` and `serial:`. |
| `tests/emulator/` | `support.Emulator` starts the emulator as a child process on a free port. `test_scope.py` allows `127.0.0.1` as the only address a source names; `test_start.py` lists the options and refuses `--address`; `test_http.py` reads the listening sockets with `lsof`. |
| `firmware/usermod/odrig_http.cpp` | The body of `POST /odrig` goes to the core and the reply comes back as `application/json`; the handler adds no header of its own. |
| `tests/converter/media_fixtures.py` | `write_gif`, `save_gif`, and `write_video(path, colours, first_pts, codec="mpeg4", ...)`: 64 x 36, 25 frames a second, flat colours from `COLOURS`, with `nearest` to recognise a colour after a lossy codec. |

Read in WLED 16.0.1, in the checkout of the firmware tool's work folder:

| # | Fact | Where |
|---|---|---|
| W1 | WLED adds `Access-Control-Allow-Origin: *`, `Access-Control-Allow-Methods: *` and `Access-Control-Allow-Headers: *` to every response of its web server, ours included. | `wled00/wled_server.cpp`, `initServer` |
| W2 | While its access point is up, WLED runs a DNS server that answers every name with the board's address. | `wled00/wled.cpp` |
| W3 | A request for the start page, or for a page WLED does not have, whose `Host` is a name and not an address, is answered with a redirect to `http://4.3.2.1`. | `wled00/wled_server.cpp`, `captivePortal` |

On this Mac, read and not changed: macOS 26.5 on Apple Silicon, Node.js 26.5.0, npm 12.0.2,
Python 3.14.6, Google Chrome 154.0.8037.98, no Java, no Android tool. PyAV 17.1.0 in
`.venv` has the encoders `libx264` and `libx265`.

## Read for this design

Read on 2026-10-12. Nothing was installed, built or downloaded: sizes were read from the
sources' own lists and from the headers of the download addresses.

| # | Fact | Source |
|---|---|---|
| F1 | The newest Capacitor is 8.5.3: `@capacitor/core`, `@capacitor/cli` and `@capacitor/android`, all under the MIT licence, unpacked 375,957, 912,410 and 449,616 bytes. The command line needs Node.js 22 or later. | `registry.npmjs.org/@capacitor/core/latest`, `.../cli/latest`, `.../android/latest` |
| F2 | Capacitor 8 supports Android from API level 24, Android 7, and needs a web view of Chrome's version 60 or later. The platform is added with `npx cap add android`; `npx cap sync` copies the web files into the Android project and then updates the project. | `capacitorjs.com/docs/android`, `.../docs/cli/commands/sync` |
| F3 | The Android project that 8.5.3 creates: `minSdkVersion` 24, `compileSdkVersion` 36, `targetSdkVersion` 36, the Android Gradle plugin 8.13.0, Gradle 8.14.3 as `gradle-8.14.3-all.zip`, Java 21 for Capacitor's own module, the one permission `INTERNET`. Its `.gitignore` leaves out the copied web files, the generated configuration files, `build/`, `.gradle/` and `local.properties`. | `github.com/ionic-team/capacitor`, tag `8.5.3`: `android-template/` and `android/capacitor/build.gradle` |
| F4 | The Android Gradle plugin 8.13 needs Gradle 8.13 or later, JDK 17 or later and the SDK build tools 35.0.0, and supports API level 36.1 at most. | `developer.android.com/build/releases/past-releases/agp-8-13-0-release-notes` |
| F5 | Capacitor's Android code: media plays without a touch (`setMediaPlaybackRequiresUserGesture(false)`); mixed content is allowed only with `android.allowMixedContent`; the page is served under `https://localhost`; a file input opens the system's chooser with the intent the web view makes for it, and asks for the camera only when the input says `capture`; `android.minWebViewVersion`, 60 unless set, is compared with the web view's version and `server.errorPath` is shown when the web view is older; a plugin class of the app is registered in the activity with `registerPlugin(...)` before `super.onCreate`. | `@capacitor/android` 8.5.3: `Bridge.java`, `CapConfig.java`, `BridgeWebChromeClient.java`, `BridgeActivity.java`; `capacitorjs.com/docs/android/custom-code`, `.../docs/config` |
| F6 | The script Capacitor puts into every page of the app defines `window.Capacitor` with `isNativePlatform()`, `getPlatform()` and `nativePromise(pluginName, methodName, options)`, which calls a plugin method and gives a promise. `@capacitor/core` also ships `dist/capacitor.js`, 8,726 bytes, for a page without a bundler. | `core/native-bridge.ts` at tag `8.5.3`; the file list of `@capacitor/core` 8.5.3 |
| F7 | Temurin JDK 21.0.12.1+1 for macOS on Apple Silicon: `OpenJDK21U-jdk_aarch64_mac_hotspot_21.0.12.1_1.tar.gz`, 200,073,404 bytes, SHA-256 `3623232f33a9c3baadf304480b2535f9a3cba8a58d42ecbb438ba267315d9998`. | `api.adoptium.net/v3/assets/latest/21/hotspot`; the header of the download address |
| F8 | The Android SDK command-line tools for macOS on Apple Silicon: `commandlinetools-mac_arm64-15859902_latest.zip`, 156,083,281 bytes, SHA-256 `835b62a26162b229b441d1f6d4680383815a270809eb33522c0d480fa5002c4e`. The page asks for agreement to the Android Software Development Kit License Agreement before the download. | `developer.android.com/studio`; the header of `dl.google.com/android/repository/<file>` |
| F9 | `sdkmanager` is in that package and installs packages by name, with `--sdk_root=<path>`; the package is unpacked so that the tool is at `cmdline-tools/latest/bin/sdkmanager`. The page calls `sdkmanager` deprecated in favour of a newer program, the Android CLI, and still documents it. | `developer.android.com/tools/sdkmanager` |
| F10 | The SDK packages: `platforms;android-36`, revision 2, 65,878,410 bytes; `build-tools;35.0.0` for macOS, 76,857,898 bytes; `platform-tools` 37.0.1 for macOS, 16,110,554 bytes. All three are under the licence `android-sdk-license`. | `dl.google.com/android/repository/repository2-3.xml` |
| F11 | `gradle-8.14.3-all.zip` has 224,584,249 bytes and the SHA-256 `ed1a8d686605fd7c23bdf62c7fc7add1c5b23b2bbc3721e661934ef4a4911d7c`. | `services.gradle.org/distributions/`, the file's header and its `.sha256` |
| F12 | `ANDROID_HOME` is the SDK's folder. `ANDROID_USER_HOME` is the folder of the Android tools' own settings; without it they use `.android` in the home folder. | `developer.android.com/tools/variables` |
| F13 | For an app that targets API level 28 or higher, plain HTTP is refused unless the app allows it. A network security configuration with `<base-config cleartextTrafficPermitted="true">` allows it for every address. | `developer.android.com/privacy-and-security/security-config` |
| F14 | From Android 5 on, a phone that is on a Wi-Fi network without internet does not route an app's requests to that network. An app sends some of its traffic there with `Network#openConnection(URL)`, or all of it by binding its process. | Android Developers Blog, "Connecting your App to a Wi-Fi Device", July 2016 |
| F15 | `Network.openConnection(URL)` opens the address on that network, and all its traffic goes over that network. `ConnectivityManager.requestNetwork` needs the permission `CHANGE_NETWORK_STATE`. `bindProcessToNetwork` binds every later socket of the process; its own description prefers connections that are bound one by one. All three are there from API level 23 or earlier. | `developer.android.com/reference/android/net/Network`, `.../ConnectivityManager` |
| F16 | From Android 17 on, an app that targets API level 37 or higher needs the permission `ACCESS_LOCAL_NETWORK` to reach an address on the local network. An app that targets a lower level and has `INTERNET` keeps its access. A web view has the permission of its app. | `developer.android.com/privacy-and-security/local-network-permission` |
| F17 | `ImageDecoder`, `VideoDecoder` and `VideoFrame` are in Chrome from version 94 and in the Android web view from the same version. The `rotation` option of a decoder's configuration is there from 138. | `mdn/browser-compat-data`: `api/ImageDecoder.json`, `api/VideoDecoder.json`, `api/VideoFrame.json` |
| F18 | Chrome reads MP4 and QuickTime files. Google Chrome decodes H.264, and HEVC where the hardware decodes it. MPEG-4 Part 2, the codec of the Python suite's test mp4, is not in its list of codecs. | `chromium.org/audio-video` |

## Assumed, to be verified

**By task 4, which builds the first APK:**

| # | Assumption | If it does not hold |
|---|---|---|
| T1 | `npm install --prefix app` with Node.js 26.5 and npm 12 installs the three packages at 8.5.3, and `cap add android` creates the project of F3. | The newest 8.x that does; the versions of F3 are read again and the drift recorded. |
| T2 | Capacitor takes a `webDir` outside its own folder, `../build/app/www`. | The folder handed over is `app/dist/`, which `.gitignore` then names. |
| T3 | The archive of F8 holds `bin/sdkmanager`, which runs on the JDK of F7 and, with `--sdk_root`, installs the three packages of F10 after one question, for `android-sdk-license`. | The Android CLI that F9 names takes its place; what it asks and installs is recorded first. |
| T4 | The build asks for no SDK package beyond the three of F10. | Exactly the package it names is added to `app/toolchain.json`. |
| T5 | With the variables of "The environment of every child process", a setup and a build write nothing outside the repository's folder. The task lists the entries of the home folder, of `~/Library/Caches`, `~/Library/Preferences`, `~/.gradle`, `~/.android` and `~/.npm` before and after. | What appears is named in `docs/android-app.md`, and a variable is added where one exists for it. |
| T6 | Gradle accepts `distributionSha256Sum` in the wrapper's properties and Capacitor's `sync` leaves that file alone. | The checksum is checked by the tool before Gradle runs. |
| T7 | After one build, a build with the network switched off succeeds. | The documentation says what a build fetches every time. |

**By task 5, in Chrome on this Mac:**

| # | Assumption | If it does not hold |
|---|---|---|
| C1 | `media_fixtures.write_video(..., codec="libx264")` writes an mp4 that Chrome 154 without a window decodes with `VideoDecoder`, in a module worker. | The mp4 is made with `h264_videotoolbox`, or by the decoder program of seed 06; the drift is recorded. |
| C2 | The decoder gives one frame for each sample, in the order of presentation, each with the `timestamp` its sample was given. | Frames are matched to samples by counting in the order of presentation. |
| C3 | In a worker, a frame drawn on an `OffscreenCanvas` with the operation `copy` and read with `getImageData` gives its pixels; for a GIF they are the colours of the file exactly, and a transparent pixel has the alpha 0. | The pixels are read with `VideoFrame.copyTo` in the format `RGBA`, which needs a web view of 127 or later; the minimum is raised and the drift recorded. |
| C4 | `ImageDecoder` gives every frame of a GIF as the whole logical screen with the earlier frames applied by the rules of seed 06's "GIF pictures", and counts the frames our reader of the blocks counts. | The difference is recorded with the GIF that shows it. Where a frame comes without the earlier ones, `gif.js` applies them itself by those rules, from the rectangle and the disposal of each frame, which the walk of the blocks reads. |
| C5 | Giving a file input its `files` from a `DataTransfer` and sending `change` stands in for the chooser. | The page takes a file through one function that the chooser's handler and the test both call. |
| C6 | A page from `127.0.0.1:A` may `POST` a text to `127.0.0.1:B/odrig` and read the reply, without a question to anyone and without a request before it. | The suite's server passes `/odrig` on to the emulator, and the app is given the server's own address. |
| C7 | Chrome without a window lays the page out at the size `--window-size=360,740` names. | The driver gives the frame that holds the app that size. |

**By the check on a phone, which only the owner can do:**

| # | Assumption | If it does not hold |
|---|---|---|
| P1 | On `odrig`, with mobile data on, `requestNetwork` for the Wi-Fi transport hands the sender the network, and a request opened on it reaches `4.3.2.1`. | The sender also binds the process to that network, and the finding is recorded; if the phone leaves the network by itself, the operators' part is in the documentation: stay connected, or switch mobile data off. |
| P2 | Android takes `odrig` for a network that asks for a sign-in or has no internet (W2, W3), stays joined, and keeps its other traffic on mobile data. | What the phone does is written into `docs/android-app.md` with what to answer. |
| P3 | `window.Capacitor.nativePromise("Target", "send", ...)` reaches the sender without any script of `@capacitor/core` in the page (F6). | The build copies `dist/capacitor.js` into the package and the web code calls the plugin through its `registerPlugin`. |
| P4 | The web view loads module scripts and a module worker from `https://localhost` and has `VideoDecoder`, `ImageDecoder` and `OffscreenCanvas` there. | The conversion runs in the page, which `convert.js` allows. |
| P5 | A video the phone recorded, H.264 or HEVC, upright or lying, is decoded and converted, and the preview is upright. | The finding names the file's codec and what the web view said; a reader on a `<video>` element is the alternative, see "Risks". |
| P6 | The file input opens the phone's chooser, and a large video is read in slices without being loaded whole. | The finding is recorded with the size at which it fails. |
| P7 | Plain HTTP to `4.3.2.1` and to the Mac's address is let through (F13). | The configuration is corrected from the error the sender reports. |
| P8 | The screen stays on while the app is in front, and the back gesture goes through the screens. | The finding is recorded. |

Read in the source and tried by nobody: the page for a web view older than 94 (F5).

## Repository layout

```
app/
  app.py                  the tool: python3 app/app.py <command>
  apptool/                its code, standard library only
    cli.py                commands, exit statuses, the error line
    paths.py              the repository, the work folder
    env.py                the environment of every child process
    toolchain.py          the downloads, their checks, the SDK packages
    stage.py              the folder handed to Capacitor
    build.py              Capacitor's sync, Gradle, the APK
    webserver.py          the web code and the library on 127.0.0.1
    device.py             install on a phone by USB
  toolchain.json          the JDK, the command-line tools and the SDK packages
  package.json            private; the three Capacitor packages at 8.5.3
  package-lock.json       tracked
  capacitor.config.json
  www/                    the web code
    index.html            the four screens and the four buttons
    old.html              shown when the web view is older than 94
    style.css
    main.js               start; which screen is shown; back
    target.js             the address; one line sent, by the sender or by fetch
    client.js             the queue, its order, the timers; what the replies told
    commands.js           each command as a function that checks its reply
    messages.js           every text
    bytes.js              base64 and CRC-32
    names.js              the id and the file name of a new item
    upload.js             the upload
    preview.js            the drawn canvas
    convert.js            one conversion: a reader, the library, the file
    convert-worker.js     convert.js in a worker
    media/sniff.js        the kind of a file
    media/gif.js          a GIF: delays from its blocks, pictures from ImageDecoder
    media/mp4.js          the table of samples of an MP4 or QuickTime file
    media/video.js        samples to VideoDecoder, frames with their times
    media/pixels.js       a frame drawn and read back
    screens/connection.js
    screens/show.js
    screens/items.js
    screens/add.js
  android/                the Capacitor project, tracked
    app/src/main/AndroidManifest.xml                          changed
    app/src/main/java/app/odrig/operators/MainActivity.java   changed
    app/src/main/java/app/odrig/operators/TargetPlugin.java   new: the sender
    app/src/main/res/xml/network_security_config.xml          new
    gradle/wrapper/gradle-wrapper.properties                  changed: the checksum
    ...                   every other file as `cap add android` made it
tests/
  app/                    the suite: needs no phone
    support.py            the emulator, the server, Chrome, a scenario run
    media.py              the test media, with the fixtures of the Python suite
    page/                 driver.html, driver.js, scenarios/
    test_*.py
  apk/                    checks of a built APK: needs the work folder, no phone
docs/
  android-app.md          rewritten: the app's page
```

Also changed: `core/src/commands.cpp`; `tests/core/support.py`, `test_status.py` and
`test_startup.py`; `emulator/app.py` and `httpd.py`; `tests/emulator/test_start.py`,
`test_http.py`, `test_scope.py` and `test_docs.py`; `tests/board/test_commands.py`;
`.gitignore`, which gains `/app/node_modules/`; `docs/commands.md`, `docs/core.md`,
`docs/emulator.md`, `docs/firmware.md`, `docs/wifi.md`, `docs/decisions.md` and
`README.md`.

No file of `converter/`, `odrig/`, `odrigctl/` or `firmware/` changes.

**Tracked and ignored.**

| Path | |
|---|---|
| `app/www/`, `app/apptool/`, `app/app.py`, `app/toolchain.json`, `app/package.json`, `app/package-lock.json`, `app/capacitor.config.json` | Tracked. |
| `app/android/` | Tracked, with the `.gitignore` Capacitor puts into it (F3). The Gradle wrapper's `jar` and the launcher pictures are binary files of the template. |
| `app/node_modules/` | Ignored, by the root `.gitignore`. |
| `app/android/app/src/main/assets/public/`, `.../assets/capacitor.config.json`, `.../assets/capacitor.plugins.json`, `app/android/**/build/`, `app/android/.gradle/`, `app/android/local.properties` | Ignored, by `app/android/.gitignore`. They are made by a build. |
| `build/app/` | Ignored: `/build/` is in the root `.gitignore` already. |

## `status` with the canvas size

`status()` in `core/src/commands.cpp` writes two members after `error`:

```
,"width":<W>,"height":<H>}
```

W and H are `core.width` and `core.height` when the core holds a mapping, which is when
`core.leg_count` is not 0, and `null` otherwise. Nothing else of the core changes: no
memory, no state, no host function. The reply grows by at most 30 bytes and stays far
below the 1,024 bytes that seed 07 allows.

The section "Status reply" of `docs/commands.md` after this seed:

~~~~markdown
## Status reply

```json
{"ok":true,"on":true,"brightness":128,"playing":3,"animation":1,"fps":50,"error":null,"width":60,"height":6}
```

| Member | Meaning |
|---|---|
| `on` | Whether the LEDs are switched on. |
| `brightness` | Current brightness, 0 to 255. |
| `playing` | The id of the item being played, or `null`. |
| `animation` | The id of the animation item on the LEDs right now, or `null`. It differs from `playing` when a cycle is playing. |
| `fps` | LED refreshes in the last full second. |
| `error` | `null`, or the reason the show is invalid. |
| `width` | The width of the canvas in LEDs, from the installed mapping, or `null` when there is no mapping that can be used. |
| `height` | The height of the canvas in LEDs, or `null` in the same case. |

A client that makes animations for the installation takes the canvas size from here. An
animation of another size is refused by `upload end`.
~~~~

`ReferencePlayer._status` gets the two members. `tests/core/test_status.py` has the exact
bytes for the example show, whose canvas is 60 x 6, and `tests/core/test_startup.py`
has, for every mapping file of the suite that the core refuses and for a missing one,
`"width":null,"height":null`, and for a show that is invalid for another reason the
numbers. The emulator and the firmware pass the reply through; the emulator's `status`
event carries the two members with the rest.

Seed 07's Requirement 1 criterion 6 says that `status` keeps its reply byte for byte. This
seed changes that reply by the owner's decision; everything else that criterion names
holds.

The firmware is built again with the changed core and flashed, with the tool of seed 04.
A board that still runs an older firmware answers `status` without the two members; the
app says so and converts nothing for it (see "Messages", `old-target`).

## The emulator on the local network

```
python -m emulator SHOW_DIR [--port N] [--serial-link PATH] [--core PATH] [--verbose] [--lan]
```

| Option | Meaning | Without it |
|---|---|---|
| `--lan` | Listen on every IPv4 address of this Mac, so that a phone on the same network reaches the emulator. | 127.0.0.1 only. |

- `emulator/httpd.py`: `Server(port, engine, show_dir, hello, lan=False)` binds
  `("0.0.0.0", port)` with `lan` and `("127.0.0.1", port)` without. `url` stays the
  address on 127.0.0.1. A new function gives the Mac's address on the local network:

  ```python
  def lan_address():
      """The address this Mac has on the network that carries its default route."""
      with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as probe:
          try:
              probe.connect(("192.0.2.1", 9))
          except OSError:
              return None
          address = probe.getsockname()[0]
      return None if address.startswith("127.") else address
  ```

  Connecting a datagram socket sends nothing: it asks the system which of the Mac's
  addresses would be used. `192.0.2.1` is an address reserved for documents.
- `emulator/app.py`: the flag `--lan`; with `--record` it is a usage error, like `--port`.
  After the lines `page:` and `serial:` it prints the line `lan:`, and it writes the
  warning to standard error before the server starts.

With `--lan`:

```
page: http://127.0.0.1:8600/
serial: /Users/you/odrig/build/emulator/serial
lan: http://192.168.1.23:8600/
```

and on standard error:

```
warning: --lan: anyone on the local network can send commands to this emulator and open its page
```

The whole server is on the network then: the commands, the page, the event stream and
the mapping file. The emulator has no password. `docs/emulator.md` says so, and that
macOS may ask whether Python may accept incoming connections: a phone reaches the
emulator only when that is allowed.

The address the app is given is the one of the `lan:` line, `192.168.1.23:8600`.

Tests that change: `test_scope.py` allows the addresses `127.0.0.1`, `0.0.0.0` and
`192.0.2.1`, all in `emulator/httpd.py`; `test_start.py` has `--lan` among the options,
keeps `--address` a usage error, refuses `--lan` with `--record`, and reads the third
line and the warning; `test_http.py` keeps its test that the emulator without the option
listens on 127.0.0.1 only, and with `--lan` finds the listening socket at `*:<port>`, a
reply on 127.0.0.1, and a reply on the address of the `lan:` line when there is one.

## The tool

```
python3 app/app.py setup
python3 app/app.py build
python3 app/app.py serve [--port N]
python3 app/app.py install
```

`app/app.py` and `app/apptool/` use the standard library of Python only, as
`firmware/fw.py` does, and run on Python 3.10 or later.

| Status | Meaning |
|---:|---|
| 0 | The command did its work. |
| 1 | It could not. One line `error: <reason>: <detail>` is on standard error. |
| 2 | The command line was not understood. |

| Reason | Condition |
|---|---|
| `node-missing` | `node` is not found, or is older than 22. |
| `unsupported-platform` | `app/toolchain.json` has no entry for this system and processor. |
| `download-failed` | An archive could not be fetched. |
| `checksum-mismatch` | An archive has another size or SHA-256 than the tracked one. It is removed. |
| `licence-refused` | The SDK tool asked for a licence other than `android-sdk-license`, or installed none. |
| `setup-failed` | A program of the setup ended with a status other than 0. The detail has the end of its output. |
| `build-failed` | Capacitor's `sync` or Gradle ended with a status other than 0, or left no APK. |
| `no-device` | `install`: no phone, or more than one, is connected by USB. |
| `address-in-use` | `serve`: the port is taken. |

### `app/toolchain.json`

```json
{
  "jdk": {
    "version": "21.0.12.1+1",
    "darwin-arm64": {
      "url": "https://github.com/adoptium/temurin21-binaries/releases/download/jdk-21.0.12.1%2B1/OpenJDK21U-jdk_aarch64_mac_hotspot_21.0.12.1_1.tar.gz",
      "bytes": 200073404,
      "sha256": "3623232f33a9c3baadf304480b2535f9a3cba8a58d42ecbb438ba267315d9998"
    }
  },
  "command-line-tools": {
    "version": "15859902",
    "darwin-arm64": {
      "url": "https://dl.google.com/android/repository/commandlinetools-mac_arm64-15859902_latest.zip",
      "bytes": 156083281,
      "sha256": "835b62a26162b229b441d1f6d4680383815a270809eb33522c0d480fa5002c4e"
    }
  },
  "sdk-packages": ["platform-tools", "platforms;android-36", "build-tools;35.0.0"],
  "licence": "android-sdk-license"
}
```

It has an entry for the one system the build is verified on. On another system the tool
ends with `unsupported-platform` and names the file.

`app/package.json`:

```json
{
  "name": "odrig-app",
  "private": true,
  "engines": {"node": ">=22"},
  "dependencies": {"@capacitor/android": "8.5.3", "@capacitor/core": "8.5.3"},
  "devDependencies": {"@capacitor/cli": "8.5.3"}
}
```

**Why these versions.** Capacitor 8.5.3 is the newest release on the day, and its
project is at the API level, the Gradle and the Java that are current (F3). The JDK is
21, the level Capacitor's own module is compiled for, in its newest Temurin build (F7).
The command-line tools are the build the download page offers (F8). The SDK packages are
what the Android Gradle plugin 8.13 asks for at API level 36 (F3, F4), and
`platform-tools` for `install`. No version is a range, and the lock file fixes what npm
fetches below the three packages.

### What is installed where

| What | Where | Download |
|---|---|---:|
| The Capacitor packages and what they need | `app/node_modules/` | not documented as a whole; the three are 1,737,983 bytes unpacked |
| The JDK | `build/app/jdk/` | 200,073,404 |
| The command-line tools | `build/app/android-sdk/cmdline-tools/latest/` | 156,083,281 |
| `platforms;android-36` | `build/app/android-sdk/platforms/` | 65,878,410 |
| `build-tools;35.0.0` | `build/app/android-sdk/build-tools/` | 76,857,898 |
| `platform-tools` | `build/app/android-sdk/platform-tools/` | 16,110,554 |
| Gradle 8.14.3, fetched by the project's wrapper | `build/app/gradle/` | 224,584,249 |
| What Gradle fetches for the build: the Android Gradle plugin, the AndroidX libraries | `build/app/gradle/` | not documented |
| The archives as fetched | `build/app/downloads/` | kept, so a setup can be repeated without the network |
| The Android tools' settings and the debug key | `build/app/android-user/` | |
| npm's cache | `build/app/npm-cache/` | |
| The settings of Capacitor's command line | `build/app/home/` | |
| The folder handed to Capacitor | `build/app/www/` | |
| The APK | `build/app/odrig-debug.apk` | |

The downloads that are documented add up to 739,587,796 bytes. Task 4 measures the work
folder after a build and the time of a first and of a second build, and task 12 writes
both into the documentation.

### The environment of every child process

| Variable | Value | For |
|---|---|---|
| `JAVA_HOME` | the JDK's home in `build/app/jdk/` | Gradle, `sdkmanager` |
| `ANDROID_HOME` | `build/app/android-sdk` | the Android Gradle plugin (F12) |
| `ANDROID_USER_HOME` | `build/app/android-user` | the Android tools' settings, the debug key (F12) |
| `GRADLE_USER_HOME` | `build/app/gradle` | the Gradle distribution and everything Gradle fetches |
| `npm_config_cache` | `build/app/npm-cache` | npm |
| `npm_config_update_notifier` | `false` | npm |
| `HOME` | `build/app/home` | Capacitor's command line only, which keeps a settings file in the user's folder |
| `PATH` | the JDK's `bin` first | all |

Gradle runs with `--no-daemon`, so nothing of a build stays running.

### `setup`

Every step is skipped when its result is there. `build/app/setup.json` records what was
installed: the SHA-256 of `app/package-lock.json` and of `app/toolchain.json`.

1. `node --version` is 22 or later, else `node-missing`. This is first.
2. `npm ci --prefix app`.
3. The JDK: fetched into `build/app/downloads/`, its size and SHA-256 compared, unpacked
   into `build/app/jdk/`. The first line of `java -version` is printed.
4. The command-line tools: fetched and compared in the same way, unpacked so that
   `build/app/android-sdk/cmdline-tools/latest/bin/sdkmanager` is there, with the
   executable bits of the archive kept.
5. The SDK packages: `sdkmanager --sdk_root=build/app/android-sdk` with the names of
   `sdk-packages`. The tool gives it one `y` and a newline on standard input and then
   closes it: the answer to the one licence the three packages are under (F10).
   Afterwards the folder `licenses/` of the SDK must hold `android-sdk-license` and no
   other file, and each package's folder must be there; else `licence-refused`.

The tool does not run `sdkmanager --licenses`, which would accept every licence the SDK
has, the preview licences among them. The owner accepted the SDK's licence terms; the
build accepts the one licence the build needs.

### `build`

1. `setup`.
2. The folder for Capacitor, `build/app/www/`, is removed and made: every file of
   `app/www/`; every file of `converter/lib/` under `lib/`; and `build.json`,
   `{"commit":"<the commit>","changed":<true or false>}`, from `git rev-parse HEAD` and
   from whether `git status --porcelain -- app converter/lib` prints anything.
3. `app/node_modules/.bin/cap sync android`, in `app/`. It copies that folder into
   `app/android/app/src/main/assets/public/` and writes the generated configuration files
   beside it.
4. `app/android/gradlew --no-daemon -p app/android assembleDebug`.
5. `app/android/app/build/outputs/apk/debug/app-debug.apk` is copied to
   `build/app/odrig-debug.apk`. The tool prints three lines: `apk: <path>`,
   `bytes: <size>` and `sha256: <digest>`.

The library gets into the package in step 2 and nowhere else. `app/www/` has no folder
`lib/`; a test says so, and that no tracked file outside `converter/` has the content of
a file of `converter/lib/`.

### `serve`

`python3 app/app.py serve` starts `webserver.py` on `127.0.0.1`, port 8610 unless
`--port` names another, and prints `app: http://127.0.0.1:8610/`. It serves `app/www/`
at `/` and `converter/lib/` at `/lib/`, each file with the content type of its ending and
`Cache-Control: no-store`, and nothing else. With the emulator running on the same Mac,
the app in a browser is given the address `127.0.0.1:8600`. The suite uses the same
server.

### `install`

`build/app/android-sdk/platform-tools/adb install -r build/app/odrig-debug.apk`, with
`ANDROID_USER_HOME` set. `adb devices` must list exactly one device, else `no-device`.

## The Capacitor project

`app/capacitor.config.json`:

```json
{
  "appId": "app.odrig.operators",
  "appName": "odrig",
  "webDir": "../build/app/www",
  "android": {"minWebViewVersion": 94, "backgroundColor": "#000000"},
  "server": {"errorPath": "old.html"}
}
```

Nothing else is set. The page is served inside the app under `https://localhost`, as
Capacitor does by default (F5). Mixed content stays forbidden and `CapacitorHttp` stays
off: the web view sends nothing to the target itself.

The Android project is made once, by `cap add android` in task 4, and tracked. Changed in
it:

| File | Change |
|---|---|
| `AndroidManifest.xml` | `android:networkSecurityConfig="@xml/network_security_config"` on `application`; the permissions `ACCESS_NETWORK_STATE` and `CHANGE_NETWORK_STATE` beside `INTERNET`. |
| `res/xml/network_security_config.xml` | `<network-security-config><base-config cleartextTrafficPermitted="true" /></network-security-config>` |
| `MainActivity.java` | `registerPlugin(TargetPlugin.class)` before `super.onCreate`, and `getWindow().addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON)` after it. |
| `TargetPlugin.java` | The sender. |
| `gradle/wrapper/gradle-wrapper.properties` | `distributionSha256Sum` with the value of F11. |

`minSdkVersion`, `compileSdkVersion` and `targetSdkVersion` stay as the template has
them: 24, 36 and 36. The launcher picture and the splash screen are the template's.

**Plain HTTP for every address.** The target is an address the operator sets: the
board's, or a Mac's on any network. A rule for one address cannot cover that, so the
configuration allows plain HTTP as a whole (F13). The app sends to no address but the
one that is set.

**The lowest Android.** API level 24, Android 7.0, is the lowest that Capacitor 8
supports (F2, F3), and nothing in the app needs more: the interfaces of the sender are
there from level 23 (F15). The web view counts for more than the Android version: the
app needs version 94, the first with `ImageDecoder` and `VideoDecoder` (F17). On a phone
with an older web view Capacitor shows `old.html`, a page without scripts that says the
phone's "Android System WebView" must be updated in the Play Store.

**Android 17.** The app targets API level 36. On Android 17 such an app keeps its access
to the local network (F16). When the target level is raised to 37, the app has to declare
`ACCESS_LOCAL_NETWORK` and ask the operator for it before its first request; that is not
part of this seed.

**Permissions.** `aapt2 dump permissions` also lists a permission that an AndroidX
library declares for the app itself: the app's identifier followed by
`.DYNAMIC_RECEIVER_NOT_EXPORTED_PERMISSION`. It is the app's own and asks nothing of the
phone. The test allows it by its name.

## Reaching the target

### What the phone does with the board's network

`odrig` has no internet. From Android 5 on, a phone that is on such a network keeps
using mobile data for its apps, and an app's request is not routed to it (F14).
WLED's access point also answers every name and redirects every page (W2, W3), so
Android's own probe finds a page where it expects none: the phone is expected to offer a
sign-in for `odrig`, or to say that it has no internet (P2). Either way the phone's
default network is mobile data, and a request from the web view would leave through it
and never reach `4.3.2.1`.

### The sender

`TargetPlugin.java`, a plugin class inside the app's own Android project (F5), named
`Target`:

```java
@CapacitorPlugin(name = "Target")
public class TargetPlugin extends Plugin {
    private ConnectivityManager networks;
    private volatile Network wifi;
    private final ExecutorService worker = Executors.newSingleThreadExecutor();

    private final ConnectivityManager.NetworkCallback watch =
        new ConnectivityManager.NetworkCallback() {
            @Override public void onAvailable(Network network) { wifi = network; }
            @Override public void onLost(Network network) {
                if (network.equals(wifi)) wifi = null;
            }
        };

    @Override public void load() {
        networks = (ConnectivityManager)
            getContext().getSystemService(Context.CONNECTIVITY_SERVICE);
        NetworkRequest request = new NetworkRequest.Builder()
            .addTransportType(NetworkCapabilities.TRANSPORT_WIFI)
            .removeCapability(NetworkCapabilities.NET_CAPABILITY_INTERNET)
            .build();
        networks.requestNetwork(request, watch);
    }

    @PluginMethod public void send(PluginCall call) { ... }
    @PluginMethod public void route(PluginCall call) { ... }
}
```

- **The network.** The request names the Wi-Fi transport and does not ask for internet
  access, so the network of `odrig` satisfies it whatever Android thinks of it, and the
  request tells Android that an app needs that network. The callback is released in
  `handleOnDestroy`.
- **`send({address, line, timeoutMs})`.** Without a network it is refused at once with
  the code `no-wifi`. Otherwise, on the worker thread:
  `wifi.openConnection(new URL("http://" + address + "/odrig"), Proxy.NO_PROXY)`, which
  sends all its traffic on that network (F15); method `POST`; the headers
  `Content-Type: text/plain` and `Connection: close`; the line's bytes in UTF-8, with
  `setFixedLengthStreamingMode`; `timeoutMs` as the limit for connecting and for reading.
  It resolves with `{status, body}`, the body being at most 4,096 bytes read as UTF-8,
  from the error stream when the status is not 200. Any `IOException` is the code
  `no-answer` with the exception's text as the detail.
- **Sent once.** A body of fixed length cannot be sent a second time by the HTTP layer,
  and with `Connection: close` no kept connection is tried that the board has closed
  meanwhile. So a line reaches the target once or not at all, and the web code alone
  decides about a second try.
- **`route()`** resolves with `{wifi, validated, portal, others}`: whether there is a
  Wi-Fi network; whether it has the capabilities `VALIDATED` and `CAPTIVE_PORTAL`; and
  the transport of the phone's default network, `"wifi"`, `"mobile"`, `"other"` or
  `"none"`. It reads the network's name nowhere, which would need the location
  permission.
- The sender looks into no line and no reply.

The plugin is about 120 lines of Java. Nothing else in the app is written for Android.

### How a `fetch` of the web view is affected, and why the app does not use one

| A `fetch` to `http://4.3.2.1/odrig` from the page | |
|---|---|
| leaves through the default network | Mobile data, while `odrig` has no internet (F14). It reaches the board only when the whole process is bound to the Wi-Fi network. |
| is mixed content | The page is `https://localhost`; a plain request from it is blocked unless `android.allowMixedContent` is set, which Capacitor's documentation calls not intended for production (F5). |
| needs plain HTTP allowed | As the sender does (F13). |
| needs the reply's permission to be read | WLED and the emulator give it (W1). |

Binding the process with `bindProcessToNetwork` would carry a `fetch` to the board on the
phones where the web view's own network code follows the binding. That is how the web
view is built today, not something Android's interface promises, and the interface's own
description prefers connections bound one by one (F15). `Network.openConnection` is the
interface whose description says that the traffic goes over that network. The price is
that the phone's way of sending is not the one the suite runs: about 120 lines of Java
and 20 of JavaScript are proven by the check on a phone alone.

Not chosen: `CapacitorHttp`, which sends from Java but on the default network; a
package that joins and binds Wi-Fi networks for an app, which would bring a dependency
and the location permission for what is one request to the system.

### `target.js`

```js
export const BOARD = "4.3.2.1";
export function parse(text)        // "host" or "host:port" -> the address as kept, or throws
export function address()          // from localStorage "odrig.target", else BOARD
export function setAddress(text)
export async function send(line, limit = 5000)   // -> the reply, or throws a Failure
export async function route()      // -> {sender, wifi, validated, portal, others}
```

`parse` takes a host name or an IPv4 address, alone or with `:` and a port from 1 to
65,535. It drops `http://` in front and one `/` at the end first, and keeps the address
as `host` or `host:port`; without a port the request goes to port 80. Anything else is
`bad-address`, and the address in use stays.

A `Failure` has a `kind` and a `detail`:

| Kind | When |
|---|---|
| `bad-address` | The text is no address. |
| `no-wifi` | The sender has no Wi-Fi network. |
| `no-answer` | No reply within the limit, or no connection. |
| `bad-reply` | A status other than 200, a body that is no JSON object, or an object without `ok` as `true` or `false`. |

`send` goes through the sender when `window.Capacitor` is there and says it is a native
platform (F6): `window.Capacitor.nativePromise("Target", "send", {address, line,
timeoutMs})`, with a timer of its own one second longer than the limit, in case the call
never comes back. Otherwise it is a `fetch` of `"http://" + address + "/odrig"` with
`{method: "POST", body: line, cache: "no-store", signal}`, ended by an `AbortController`
at the limit. A text body makes it a request that needs no request before it, and the
emulator's reply may be read from another origin.

`target.js` is the one file that knows how a line travels. A later shell for PCs brings
its own way of sending here.

## The web code

`index.html` holds the four screens as four sections, the four buttons, the line that
says the target does not answer, and the place for messages. It loads `style.css` and
`main.js` as a module. No screen is built from a template on the phone, and no page is
loaded after the first.

At its start the app shows the connection screen. As soon as the target has answered
once, it shows the show screen. The four buttons are `Show`, `Items`, `Add` and
`Target`.

### The client (`client.js`)

One object holds what the replies told: the state of the connection, the newest
`status`, the items, the storage, and the time of the newest reply. Screens read it and
are told when it changes. It never holds what the app hopes: a button is shown as
pressed, a slider as moved, but the state shown comes from replies.

**The queue.** One request is under way at a time. What waits is in four classes, taken
in this order:

1. what the operator asked for: `on`, `off`, `brightness`, `play`, `remove`,
   `upload cancel`;
2. a `status` that is due;
3. the next line of an upload;
4. `list` and `space`.

A `brightness` that waits is replaced by a newer one. A `status` is due 1,000 ms after
the one before was sent, and at once after the reply to a command of class 1. `list`
and `space` are due as Requirement 12 criterion 5 says. While the document is hidden
nothing of classes 2 and 4 is made due.

**The state of the connection** follows every request: a reply makes it `answers`; a
`no-wifi`, `no-answer` or `bad-reply` makes it `no answer` with that failure. So it turns
within one time limit, 5,000 ms, and turns back with the first reply.

**`commands.js`** has a function for each command. Each builds its line and checks that
a reply with `"ok":true` has the members the command promises, with the types they must
have: `width` and `height` for `status`, `items` and `next` for `list`, and so on. A
reply that lacks them is `bad-reply`; a `status` without `width` and `height` is
`old-target`.

### The connection screen

- A field with the address, 56 pixels high, with the keyboard for addresses. `Use`
  takes it; `Board` puts `4.3.2.1` back.
- The state: `Checking`, `Answers` or `No answer`, with the message of the failure.
- While it answers: `Canvas 60 x 60`, or the message for no canvas; the reason of an
  invalid show.
- How requests travel, from `route()`, asked with every `status` while this screen is
  shown:

  | `route()` | The line |
  |---|---|
  | no sender | `Sent from this browser.` |
  | no Wi-Fi | `This phone is not on a Wi-Fi network.` |
  | Wi-Fi, validated | `Sent over Wi-Fi.` |
  | Wi-Fi, not validated, others `mobile` | `Sent over Wi-Fi. This Wi-Fi network has no internet: the phone's other apps use mobile data.` |
  | Wi-Fi, not validated, others not `mobile` | `Sent over Wi-Fi. This Wi-Fi network has no internet.` |

  With `portal` the line adds: `The phone offers to sign in to it. That is not needed.`
- `Join the Wi-Fi network odrig in the phone's Wi-Fi settings.`
- In small print: the web view's version, from the user agent, and `build <commit>`
  from `build.json`, with `changed` when the build says so.

### The show screen

- The state, large: `ON` or `OFF`; `Brightness 128`; `Playing 3, a cycle: now 1
  hello.odrg`, or `Playing 2 dvd.odrg`, or `Nothing plays`; `50 refreshes a second`. With
  an invalid show its message stands in place of what plays.
- `On` and `Off`, two buttons side by side; the one in effect is marked.
- The brightness slider, as wide as the screen, with its number. While it is moved a
  command goes out at most every 200 ms, and the value at which it is let go is always
  sent. A `status` reply does not move the slider while it is held, nor for 1,000 ms
  after the last brightness command.
- One play button for each item, in the order of the show, with the id and the file
  name, or `cycle of 1, 2`. The one that plays is marked.
- While the target does not answer, the values are dimmed and a line says for how long.

### The items screen

- The storage: `8.4 MB free of 10.4 MB, 2 animations`. A size is written in bytes below
  1,000, in kB with one decimal below 1,000,000 and in MB with one decimal above, 1 kB
  being 1,000 bytes.
- One row for each item: the id; the file name and the size, or `cycle of 1, 2, 15 s
  each`; a `Remove` button. A cycle that the target lists without its ids is shown as
  `cycle, too long to list`.
- While the app's own upload runs, the `Remove` buttons are out of use: the target
  would refuse with `busy`.
- The question before a removal is a panel over the screen with two buttons, `Remove`
  and `Keep`:

  | Item | The question |
  |---|---|
  | An animation | `Remove 2 dvd.odrg? Its file is deleted from the installation.` |
  | A cycle | `Remove cycle 3? Its animations stay.` |
  | The item that plays | adds `It is playing now: the LEDs will go dark.` |

### The add screen

The screen is one column that grows with the work:

| State | What is on the screen |
|---|---|
| empty | `Choose a video or GIF`. |
| read | The file's name, kind, picture size, length and number of frames; the three fit buttons; the start and the length, each a slider with a field in seconds; the still preview; `Compressed`, a switch that is on; `Convert`. |
| converting | A bar with the part done; `Cancel`. |
| converted | The preview playing; the length, the ticks, the size of the file and the free storage; `New item` or `In place of`, with the id and the file name; `Upload`. |
| uploading | A bar with the percentage; the bytes; the speed; `Cancel`. |
| checking | `The installation is checking the file`; the time so far; `Cancel`. |
| installed | `Installed as 4 clip.odrg`; `Play it`; `Add another`. |

A change of the fit, the start, the length or the switch in the state `converted` throws
the result away and goes back to `read`. A failure goes back to the state before, with
its message.

The input is `<input type="file" accept="video/*,image/gif">`. Capacitor opens the
phone's chooser for it (F5). The kind of the file is judged from its content, not from
what the chooser calls it.

## Reading media

### The kind of a file (`media/sniff.js`)

The first 12 bytes: `GIF87a` or `GIF89a` is a GIF. A file whose bytes 4 to 7 are one of
`ftyp`, `moov`, `mdat`, `free`, `skip` and `wide` is taken for an MP4 or QuickTime file
and judged further by `mp4.js`. Anything else is `not-media`.

### A GIF (`media/gif.js`)

- **The delays** are read from the file by walking its blocks, in slices of 1 MiB: the
  header, the logical screen with its colour table, and then extensions and pictures to
  the trailer. Each picture has the delay of the graphic control extension before it, in
  hundredths of a second, or 0 without one. This gives the size of the logical screen,
  the number of frames and each delay as the file records it. The library applies its
  own rule to a delay of 10 ms or less.
- **The pictures** come from `new ImageDecoder({data: file.stream(), type: "image/gif"})`.
  `decode({frameIndex})` gives a `VideoFrame` of the whole logical screen (C4), which
  `pixels.js` reads.
- `frames(startMs)` gives the library every frame with its delay, in the file's order.
  A frame that ends at or before the start of the part, by the starts and ends that
  `timeline.gifFrames` gives for the delays alone, is given as a stand-in of 1 x 1 and is
  not decoded; the decoder brings a later frame with everything before it applied.
- A file of more than 67,108,864 bytes is `gif-too-large`. A file whose blocks do not
  end in a trailer, or for which the decoder counts other frames than the walk, is
  `unreadable-media`.

### An MP4 or QuickTime file (`media/mp4.js`)

`index(blob)` reads the boxes at the top of the file by their headers alone, until it
has `moov`, which it reads whole when it is 64 MiB or less. A `moof` box at the top, or
`mvex` in `moov`, is `fragmented`. In `moov` it takes the first track whose handler is
`vide` and that has samples; without one the file is `no-video`.

From that track:

| Box | Taken |
|---|---|
| `tkhd` | The matrix: a rotation of 0, 90, 180 or 270 degrees. Any other matrix counts as 0. |
| `mdhd` | The time scale. |
| `stsd` | The first entry: its name, the coded width and height, and the box with the decoder's configuration, `avcC` or `hvcC`, as bytes. |
| `stts`, `ctts` | For each sample its decoding time and the offset to its composition time, in units of the time scale. |
| `stss` | The sync samples; without the box every sample is one. |
| `stsc`, `stsz` or `stz2`, `stco` or `co64` | For each sample its place in the file and its size. |

It gives `{codec, description, codedWidth, codedHeight, rotation, timescale, samples}`,
each sample with `offset`, `size`, `dts`, `cts` and `sync`, and the samples also in the
order of their composition times.

- The codec's name for the web view is built from the configuration: `avc1.` and the
  three bytes after the first of `avcC` in hexadecimal; for HEVC the text that
  ISO/IEC 14496-15 gives for `hvcC`. An entry named anything but `avc1`, `avc3`, `hvc1`
  or `hev1` is `codec-unsupported` with its name.
- A number of 64 bits is read whole and refused as `unreadable-media` when it is not a
  safe integer. A table of more than 1,000,000 samples is refused in the same way.
- Edit lists are not read. Time is counted from the first frame, so an edit list that
  only shifts the track changes nothing; one that hides the beginning of a track does
  not hide it here.

About 350 lines. It is a reader of tables, not a decoder: no picture is made by it.

### A video (`media/video.js`)

`open(blob)` reads the index and asks `VideoDecoder.isConfigSupported` with the codec,
the description and the coded size; a refusal is `codec-unsupported`.

`frames(startMs)` is an asynchronous generator that gives the library every frame of the
track, in the order of presentation, with its time as `[cts * 1000, timescale]`:

1. With the starts that `timeline.videoFrames` gives for the times alone, the frame `f`
   on screen at the start of the part is the last whose start is not after `startMs`.
2. Every frame before `f` is given as a stand-in: a picture of 1 x 1 with its true time.
   No tick shows such a frame, so the library never looks at its picture (seed 06,
   Requirement 12 criterion 7), and its time keeps the timeline exact: time zero is the
   first frame of the file, and the length of the last frame is the mean of all.
3. Decoding begins at `k`, the last sync sample in decoding order that is not after `f`
   in either order. The samples from `k` on are read from the file in runs that lie next
   to each other, at most 4 MiB a read, and given to the decoder as chunks, `key` for a
   sync sample, each with a timestamp in microseconds that no other sample has.
4. A decoded frame is matched to its sample by that timestamp. One that is before `f`
   is closed unread. Every other one is read by `pixels.js`, closed, and given to the
   library with its true time.
5. The generator feeds the decoder only while fewer than 8 chunks wait in it and fewer
   than 4 frames are held, and waits otherwise. After the last sample it flushes.
6. When the library stops asking, the generator's `return` closes the decoder and every
   frame still held.

So a part costs what the part costs: the frames from the sync sample before it to its
end, wherever in a long file it lies.

### A frame read back (`media/pixels.js`)

One `OffscreenCanvas` with a 2D context made with `willReadFrequently`. For each frame:
the canvas gets the size of the picture as shown, the frame is drawn with the operation
`copy`, so that nothing of the frame before shows through, and `getImageData` gives the
`rgba` the library takes.

- **Rotation.** For 90, 180 and 270 degrees the frame is drawn turned, and for 90 and
  270 the canvas has the width and the height exchanged.
- **Large frames.** With more than 1,048,576 pixels the frame is drawn at
  `ceil(width / k)` by `ceil(height / k)`, k the smallest whole number that brings it to
  that many or fewer, with the smoothing quality `high`: 1,920 x 1,080 is drawn at
  960 x 540, 3,840 x 2,160 at 1,280 x 720, and 1,280 x 720 as it is. The library then
  fits a picture of at most 4 MiB.

These two are where a file converted on the phone differs from the same file converted
on a computer: the converter there applies no rotation, and fits the full picture. The
documentation says so.

### Long and large files

| | |
|---|---|
| A long video | Only the part is decoded. The index of a video of an hour is a few megabytes. |
| A part | At most 120 seconds, which is 6,000 ticks. On the 60 x 60 canvas that is 64,800,000 bytes of pictures; storage holds 65 to 74 seconds of a dense clip. |
| A large picture | Made smaller before it is read; one read frame is at most 4,194,304 bytes. |
| The decoder | Holds at most 4 frames of the video's own size, and 8 chunks. |
| A large GIF | Refused above 64 MiB. |
| Memory that runs out | An error of the kind `RangeError`, or one that names memory, during a conversion is `too-large`. The worker is ended, which gives everything back. |

## Converting

`convert.js` has three functions that run in a worker or in the page:

```js
// what the screen shows of a file
export async function describe(file)
// the picture of the first tick
export async function still(file, {canvas, fit, startMs})
// -> {file, pictures}
export async function convert(file, {canvas, fit, startMs, durationMs, compressed},
                              progress)
```

`convert` is:

```js
const reader = kind === "gif" ? await gif.open(file) : await video.open(file);
const animation = await lib.timeline.importFrames(
    {kind, frames: reader.frames(startMs, progress)}, canvas, {fit, startMs, durationMs});
const bytes = lib.odrg.encode(animation, {compressed});
```

`describe` takes the length of a file from `timeline.videoFrames` or `timeline.gifFrames`
on the times and delays alone: the end of the last frame. `still` is `convert` with a
length of 20 ms and without `encode`.

Everything that decides a tick, fits a picture or writes the file is the library's. The
readers decide one thing: which frames are worth decoding.

**The worker.** `convert-worker.js` imports `convert.js` and answers messages:
`{describe}`, `{still}` and `{convert}` come in with the `File`; `{progress, done, of}`,
`{result, ...}` and `{failed, reason, detail}` go back. The file and the pictures of the
ticks go back by moving their buffers, not by copying; a picture that several ticks
share is moved once. The page starts the worker as a module, and ends it with
`terminate()` for `Cancel`, which stops the decoder and frees everything at once. Where
a module worker cannot be started, the page imports `convert.js` itself (P4); `Cancel`
then takes effect at the next frame.

**Progress** is the time of the newest frame the reader gave, within the part. The
encoding after the last frame is shown as `Writing the file`.

**The canvas** is the `width` and `height` of the newest `status`, read when `Convert`
is pressed.

**Compressed or not.** `Compressed` is on at first. For a picture that changes little a
compressed file is far smaller. For a video it is about 5 percent smaller, and the board
needs more time for each of its frames (`docs/decisions.md`, "Open questions"), so the
switch is there for an operator who wants the faster file.

**The same result twice.** For a GIF the pixels are the file's own, so the same file and
the same choices give the same bytes on every phone and in Chrome, and the bytes of the
converter on a computer. For a video the pixels come from the phone's decoder, and two
decoders may differ by a step of colour.

## The preview

`preview.js` draws on a `<canvas>` as wide as the screen, with a height that keeps the
dots round. A picture is put into an image of W by H pixels, bottom row last, and drawn
enlarged without smoothing; a mask of round holes on black, drawn once for the size, is
laid over it. That is two drawing calls for a picture of any size.

- The still preview shows the picture `still` gives. It is asked for when a file is
  read and 300 ms after the last change of the fit or the start.
- The moving preview shows the picture of tick `floor(elapsed / 20) mod ticks` at every
  animation frame of the page, and the time within the part beside it.

The pictures are the ones the encoder was given. The format is lossless, so they are the
pictures of the file; a test decodes the uploaded file and compares.

## Uploading (`upload.js`)

`upload(client, {id, name, bytes}, watch)` runs one upload and tells `watch` of every
step. It asks the client to send its lines in class 3 of the queue.

**The id and the name** come from `names.js`: `nextId(items)` is the smallest whole
number from 1 that no item has; `fileName(picked, items)` follows Requirement 17
criterion 2, with at most 27 characters before `.odrg`, and with `-2`, `-3` and so on
in place of the name's end while an item has the name; `valid(name)` is the rule of
`docs/show.md`. The list is read anew before either is used.

**The steps:**

1. `space`. When `bytes + floor(bytes / 256) + 16384 > free`: `no-space`, with both
   figures, and nothing more is sent. The rule is the one the core applies.
2. The CRC-32 of the whole file, with a table of 256 entries.
3. `upload begin <id> <name> <bytes>`. The piece size is `min(chunk, 1500)`.
4. For each piece: `upload data <offset> <base64>`. The reply's `received` must be the
   offset plus the piece; it becomes `acknowledged`.
5. `upload end <crc32>`. While the reply is `busy`: 200 ms, and again.
6. `list` and `space`.

A line with a piece of 1,500 bytes has at most 2,023 characters.

**What a reply means:**

| Line | Reply | The app |
|---|---|---|
| any | none in time | sends the same line again after 1,000 ms, up to four more times; then fails as `no-answer` |
| `upload begin` | `busy`, the first time or after it was sent again | does not clear it; says an upload is open and offers `Clear it` |
| `upload begin` | another refusal | fails with its message; nothing is open |
| `upload data` | `bad-offset` | sends the next piece, or `upload end` after the last; acknowledged there, it goes on; refused there too, it fails as `bad-offset` |
| `upload data` | `no-upload` | fails: the target gave the upload up |
| `upload end` | `busy` | waits 200 ms and sends it again, for at most 600 seconds; then cancels and fails |
| `upload end` | `no-upload`, after it was sent again | reads `list`: an item with the id, the name and the size means it succeeded |
| `upload end` | `incomplete` | fails: a piece is missing |
| `upload end` | `bad-checksum`, `bad-file`, `storage-error` | fails with its message; the target has discarded the upload |

Five sendings of one line take at most 29 seconds, which is inside the 60 seconds the
target waits.

**A `bad-offset` is not an end at once**, because a reply can be lost after its line was
taken: the same line sent again then finds the target one piece further. The next piece
tells the two cases apart, with the offset rule alone: the target takes it only when it
holds exactly the bytes before it.

**`busy` to `upload begin`** may be this phone's own upload from a try that died, or
another operator's. It is also what a lost reply to `upload begin` leads to: the line
sent again finds the upload that the first one opened. The app cannot tell these apart,
and an `upload cancel` ends whichever it is. So the operator decides: `Clear it` asks
once more, `Clear the open upload? If someone else is uploading, their upload is lost.`,
and then sends `upload cancel` and begins again.

**Cancel.** The button sets a flag. When the request under way has ended, no further
line of the upload is sent, and `upload cancel` goes out in class 1. Its reply may be
`{"ok":true}` or `no-upload`; both are the end.

**After a failure** the app sends `upload cancel` when the upload may still be open:
after `no-answer` once, without waiting on it; after `bad-offset`, `incomplete` and the
600 seconds. Not after `no-upload`, `bad-checksum`, `bad-file` and `storage-error`.

**The percentage** is `floor(acknowledged * 100 / bytes)`.

**The speed.** Every acknowledgement is noted with its time. The speed is the bytes
acknowledged since the note that is 5 seconds old, or since the reply to `upload begin`
when the upload is younger, divided by the time since then. It is shown in kB a second,
1 kB being 1,000 bytes, with one decimal, and with the time left at that speed. The
clock is `performance.now()`, given to `upload.js` from outside so that a test can set
it.

**Pacing.** The app sends the next piece when the one before is acknowledged, and adds
no wait of its own: the board holds a line back for as long as its storage needs (seed
07, "Pacing"), and the time a reply takes is the pace. Between two pieces the queue lets
through what the operator asks and one `status` a second, so the show screen stays live
and the rate the board reports during an upload is on it.

**When the app is closed or put behind another app** during an upload, no line is sent
any more. The target gives the upload up after 60 seconds. Nothing of the show has
changed.

## Messages

`messages.js` is one table. A message is its text, with the code or the reason in
brackets at its end, and stays until it is dismissed or replaced. `<address>`, `<id>`
and the like are filled in.

**Reaching the target**

| Failure | Text |
|---|---|
| `bad-address` | That is not an address. Write it like 4.3.2.1 or 192.168.1.23:8600. |
| `no-wifi` | This phone is not on a Wi-Fi network. Join the network odrig in the phone's Wi-Fi settings. |
| `no-answer` | No answer from `<address>`. Check that the phone is on the installation's Wi-Fi network and that the installation has power. |
| `bad-reply` | Something answered at `<address>`, but it is not an odrig installation. |
| `old-target` | The installation's software is older than this app: it does not say how large its canvas is. Nothing can be converted for it until its firmware is updated. |
| `no-canvas` | The installation has no mapping it can use, so there is no canvas to convert for. |

**Error codes**

| Code | From | Text |
|---|---|---|
| `line-too-long`, `unknown-command`, `bad-argument` | any | The installation did not understand the app. Its software and this app do not match. |
| `show-invalid` | `play`, `list`, `remove`, `upload` | The installed show is invalid: `<reason>`. Nothing can be played, removed or uploaded until a show is installed over USB. |
| `unknown-id` | `play`, `remove` | Item `<id>` is not installed any more. |
| `in-use` | `remove` | Animation `<id>` is part of a cycle. Remove the cycle first. |
| `in-use` | `upload begin`, the id | Item `<id>` is a cycle. An animation cannot take its place. |
| `in-use` | `upload begin`, the name | Another item already has the file name `<name>`. Give this animation another name. |
| `busy` | `remove` | An upload is running on the installation. Remove the item when it is done. |
| `busy` | `upload begin` | An upload is already open on the installation. Wait a minute, or clear it. |
| `busy` | `upload end`, after 600 seconds | The installation was still checking the file after ten minutes. The upload was cancelled. |
| `no-space` | the file does not fit | Not enough room: the animation needs `<size>` and `<free>` is free. Remove an animation, or convert a shorter part. |
| `no-space` | the file fits | The show has no room for another item. Remove an item first. |
| `no-upload` | `upload data`, `upload end` | The installation gave the upload up: it waits one minute for data. Upload again. |
| `incomplete` | `upload end` | The installation did not get the whole file. Upload again. |
| `bad-checksum` | `upload end` | The file arrived damaged. Upload again. |
| `bad-offset` | `upload data` | The upload got out of step. Another phone may be uploading at the same time. Upload again. |
| `bad-file` | `upload end`, `size-mismatch` | The installation's canvas is not `<W>` x `<H>` any more. Convert the file again. |
| `bad-file` | `upload end`, any other reason | The installation refused the file. Convert it again. |
| `storage-error` | any | The installation could not write to its storage. Try again. |

Which of the two texts of `no-space` and of `in-use` applies, the app tells from what it
sent and from the storage it read.

**Files**

| Failure | Text |
|---|---|
| `not-media` | This file is not a video or GIF the app can read. It reads MP4 and MOV videos and GIF files. |
| `fragmented` | This video is stored in fragments, which the app cannot read. Convert it on a computer. |
| `no-video` | This file has no video in it. |
| `codec-unsupported` | This phone cannot decode this video. Convert it on a computer, or try another video. |
| `decode-failed` | The video could not be decoded. |
| `gif-too-large` | This GIF is too large for the phone: it has more than 64 MB. |
| `too-large` | The phone ran out of memory. Choose a shorter part. |
| `unreadable-media` | This file cannot be read: it is damaged, or not what its name says. |
| `bad-range` | The part is not inside the file. |
| `canvas-too-large`, `too-many-frames` | The animation is too large for the format. |
| any other reason of the library | The file cannot be converted. |

The detail of a `Rejection`, the name of a codec and the text of a decoder's error are
shown under the message in small print. A test reads the error codes from the table of
`docs/commands.md` and finds a text for each, and reads the library's reason names from
`converter/lib/errors.js` and finds that each either has a text of its own or is one the
app cannot meet.

## The look

- Black, `#000000`, behind everything. Text `#e8e8e8`; lesser text `#b0b0b0`; what is in
  effect and what a touch will do, amber, `#ffb000`; what removes or cancels, `#ff8a7f`.
  Buttons are dark, `#1c1c1c`, with a border; none is a bright area. Each of the four
  text colours has a contrast of 7 to 1 or more against black and against the dark of
  the buttons.
- The system's font, 18 pixels for text, 20 for buttons, 28 for the state of the
  installation.
- Every button, field and slider is 56 pixels high or more and has 8 pixels around it.
  The four screen buttons lie along the bottom edge, each a quarter of the width.
- One column. Nothing depends on a pointer hovering, a long press or a swipe.
- No pictures, no fonts and no scripts from anywhere but the package.

**Back.** Each change of screen adds an entry to the page's history, so the system's
back gesture shows the screen before, and from the first screen it leaves the app as it
does in any app. While a conversion or an upload runs, the entry is put back and a
message says `Cancel the work first`.

## Testing strategy

Three kinds of check, kept apart:

| Check | Needs |
|---|---|
| `.venv/bin/python -m unittest discover -s tests/app -t .` | The suite: no phone and no Android tool. |
| `python3 -m unittest discover -s tests/apk -t .` | A built APK and the SDK in the work folder; no phone. |
| `docs/android-app.md`, "The check on a phone" | A person with a phone. |

### How the suite drives the app

`tests/app/support.py`:

- **The emulator**: `tests.emulator.support.Emulator`, on a copy of a packed show in a
  temporary folder: the demo show of the target file, or a show the test writes. The
  folder is the test's to look into afterwards.
- **The server**: `app/apptool/webserver.py` on a free port of 127.0.0.1, with more
  paths for the test: `/t/` is `tests/app/page/`; `/media/<name>` is a file the test
  made; `POST /result` takes what a scenario found; and `/hop/<name>/odrig` passes a
  command on to the emulator, or answers it as the test said: drop the reply to the n-th
  line that begins with given words, after the emulator took the line or before; delay
  every reply; or give fixed replies in place of the emulator's.
- **Chrome**: the program `ODRIG_CHROME` names, or the one in `/Applications`, as in
  seed 06, with `--headless=new --no-first-run --no-default-browser-check
  --disable-extensions --disable-background-networking --disable-sync
  --disable-component-update --window-size=360,740 --user-data-dir=<a new temporary
  folder>` and the address of the driver. It is ended, and its folder removed, when the
  result has come or after 120 seconds.
- **The driver**, `page/driver.html` with `driver.js`: it puts the app's `index.html`
  into a frame of its own page, sets the address the app is to use, and runs the
  scenario the test named, a module of `page/scenarios/`. A scenario works the app the
  way an operator does: it finds a button by its words and presses it, fills a field,
  gives the file input a file it fetched from `/media/`, and waits for words to appear.
  What it read off the screen goes to `/result`.
- A test is: start the emulator and the server, run a scenario, and compare what the
  screen showed with what the emulator says and holds: its replies over HTTP, and the
  files of its folder.

Nothing drives Chrome from outside, and no package is installed for it.

### The media (`tests/app/media.py`)

Made while the suite runs, into a temporary folder:

- GIFs with `media_fixtures.write_gif` and `save_gif`: the GIFs of the Python suite's
  import tests, with delays of 30, 50, 70 and 0 ms; one with a transparent index; one
  whose later frames are smaller than the screen.
- Videos with `media_fixtures.write_video(..., codec="libx264")`: the flat colours at 25
  frames a second; and from PyAV directly: one with B-frames, one with its index at the
  end of the file, one at 30,000/1,001 frames a second, one in HEVC, one of 2,000 x
  1,200 pixels, and one whose frames have four different quarters, with the matrix of
  `tkhd` set to each rotation by the test.

The mp4 of the Python suite is MPEG-4 Part 2, which Chrome does not decode (F18). The
suite's own are H.264.

**How frames are decoded in Chrome.** By the app's own readers and the same two
interfaces as on the phone: `ImageDecoder` for a GIF and `VideoDecoder` for an mp4, in
the worker. Chrome on the Mac decodes H.264 itself; it needs no window and no package.
The HEVC file is used for the reader of the tables in every run, and for decoding only
when `VideoDecoder.isConfigSupported` says yes on this Mac.

### What each test file holds

| File | Tests |
|---|---|
| `test_tool.py` | `toolchain.json` and `package.json` name exact versions; an archive of another size or SHA-256, served by the test, is refused and removed and nothing is unpacked; the environment of a child has every variable of the design and each folder lies in the work folder; the staged folder holds the files of `app/www/` and `converter/lib/` and `build.json` and nothing else, and is made anew; an old Node.js is refused first; usage errors; `serve` listens on 127.0.0.1 only and prints its line. Nothing is downloaded. |
| `test_scope.py` | Every script of `app/www/` imports only `./...` and the library; none names a network address, a path other than `/odrig`, or a command word outside `docs/commands.md`; `fetch` is in `target.js` only; no file of the library is tracked outside `converter/`, and `app/www/lib` does not exist; `index.html` loads nothing from outside; `messages.js` has a text for every error code of `docs/commands.md` and for every reason of `converter/lib/errors.js` the app can meet; the Java sources hold no command word; the tracked manifest declares the three permissions and names the network security configuration, which allows plain HTTP; `capacitor.config.json` has the identifier, the lowest web view and the page for an older one. |
| `test_readers.py` | In Chrome: for each test video the table `mp4.js` gives, against PyAV's packets: every size, decoding time, composition time and sync flag, the time scale, the picture size, the rotation; `fragmented`, `no-video` and `codec-unsupported` for files made for it; for each GIF the delays and the frame count of `gif.js` against Pillow; `sniff` on each kind and on a text file. |
| `test_convert.py` | The GIFs: the file the app makes decodes to the JSON frames of `node converter/odrig.js import`, byte for byte, for each fit and for a part; compressed and uncompressed. The H.264 video: the same number of frames and durations, each picture the list colour of the frame on screen, the largest difference to the converter printed; a part from the middle, where decoding begins at a sync sample; B-frames; the index at the end. A rotated video comes out turned. A frame of 2,000 x 1,200 is read at 1,000 x 600. The same through the worker and in the page. `Cancel` ends the worker. Each refusal with its message. |
| `test_connection.py` | The first address is `4.3.2.1`; an address is kept over a reload; each form of an address and each refusal; `Answers` with the canvas against the emulator, on the bench mapping and on the target; `No answer` for a port nothing listens on, and its return when an emulator starts there; `bad-reply` for a server that is not ours; `old-target` and `no-canvas` for replies the hop gives; the line that says how requests travel, with a stand-in for `window.Capacitor`. |
| `test_show.py` | Every value of the screen against `status`; a brightness the test sets through the emulator is on the screen within 2 seconds; `On`, `Off`, the slider and each play button, each against `status` afterwards; at most five brightness commands a second and the last value sent, counted in the emulator's log; a refusal shown; the values marked old when the emulator is stopped. |
| `test_items.py` | The rows against `list`, for a show of 40 items, which takes more than one reply; the sizes and the storage against `space`; a removal declined sends nothing; a removal confirmed removes the item and its file from the folder; each refusal with its message; the question for a cycle and for the item that plays. |
| `test_add.py` | For a GIF and for the H.264 video: pick, the still preview, each fit, a part, convert, the moving preview, upload, the item in `list` with its size, the file in the folder equal to the file the app made, `Play it`, and `status` with that id playing. An upload in the place of an item. The id and the name the app proposes; a name that is refused. The pictures of the preview against the decoded file. |
| `test_upload.py` | Through the hop, which drops a reply by closing the connection: the reply to `upload begin`, to a piece and to `upload end` dropped once; the reply to a piece dropped four times, and five times, which ends the upload as `no-answer`; a piece delivered twice; `busy` to `upload begin`, with `Clear it` declined and confirmed; `busy` to `upload end` waited out, with a long animation; `Cancel` while sending and while checking, after which the folder holds no `upload.part` and an upload succeeds; a file that does not fit, with `--storage`; each error code a fixed reply gives; the percentage and the speed for acknowledgements at set times. |
| `test_look.py` | At 360 by 740: on each screen and in each state of the add screen, every button, field and slider is 56 by 56 or more and 8 from the next; the background is black; the text colours have a contrast of 7 or more; nothing scrolls sideways, also at 320; the back entry of each screen, and back while a conversion runs; a message stays until it is dismissed or another takes its place. |
| `test_docs.py` | `docs/android-app.md` has every command of the tool with an example, the versions and the sizes of `toolchain.json` and `package.json`, each message of `messages.js`, the check on a phone as numbered steps, and what is verified; `docs/emulator.md` has `--lan`; `docs/commands.md` has the two members. |

`tests/apk/test_apk.py`, on `build/app/odrig-debug.apk`, with `aapt2` of the SDK in the
work folder and Python's `zipfile`: the identifier and the label; `minSdkVersion` 24;
the three permissions and the app's own one; the network security configuration with
plain HTTP allowed; every file of `app/www/` and of `converter/lib/` under
`assets/public/` with its bytes, and `build.json` with the commit of the work tree; no
other file there but the ones Capacitor adds, which the test names; the two Java classes
in the package.

### Who checks what

| Item of the definition of done | Checked by |
|---|---|
| 1. The web code in headless Chrome against the emulator, every screen and action, the test GIF and the test mp4 converted, uploaded and played | `tests/app/` |
| 2. A debug APK with one documented command | Task 4 and task 11, by running it; `tests/apk/` |
| 3. The APK on a phone, against the emulator and the board | The owner, with "The check on a phone" |
| 4. Building, installing and using documented | `tests/app/test_docs.py` |

## The check on a phone

`docs/android-app.md` gets this list. Each step says what must be seen.

**Before:** `python3 app/app.py build`; the firmware with this core on the board, with
the dim example show; the phone charged, with mobile data on.

1. **Install.** `python3 app/app.py install` with the phone on USB, or copy
   `build/app/odrig-debug.apk` to the phone and open it. *Seen:* the app `odrig` is on
   the phone and starts on the connection screen with the address `4.3.2.1`.
2. **The emulator.** On the Mac: `python -m emulator build/demo-20/show --lan`; allow
   incoming connections if macOS asks. Phone and Mac on the same Wi-Fi. Give the app the
   address of the `lan:` line. *Seen:* `Answers`, `Canvas 60 x 60`, and `Sent over
   Wi-Fi.`
3. **Status.** *Seen:* the show screen has what the emulator's page has: on, the
   brightness, what plays, about 50 refreshes a second. Send `python -m odrigctl --http
   127.0.0.1:8600 brightness 40` on the Mac: the phone shows 40 within two seconds.
4. **Controls.** `Off`, `On`, the slider, each play button. *Seen:* the emulator's page
   follows each, and its log has each line as `http`.
5. **Items.** *Seen:* the two animations with their sizes, the cycle, the free storage.
6. **A GIF.** Pick a GIF from the phone. *Seen:* the still preview; it changes with each
   fit; `Convert`; the moving preview; `Upload` with a percentage and a speed;
   `Installed`; `Play it` shows it on the emulator's page.
7. **A video.** The same with a video the phone recorded upright and one it recorded
   lying, each of ten seconds or more, with a part of five seconds from the middle.
   *Seen:* both previews are upright; the time each conversion took.
8. **Cancel.** Start an upload of the larger file and press `Cancel` half way. *Seen:*
   the bar stops; the emulator's folder has no `upload.part`; `Upload` works again.
9. **Remove.** Remove the new items, declining once first. *Seen:* the question; the
   list without them.
10. **No answer.** Stop the emulator. *Seen:* within five seconds the app says that
    nothing answers, in words. Start it again: the app recovers by itself.
11. **The board's network.** Power the board. In the phone's Wi-Fi settings join `odrig`
    with the password. Leave mobile data on. Note what the phone says about the network
    and what you answered. In the app press `Board`. *Seen:* `Answers`, `Canvas 60 x 6`,
    and a line that says the Wi-Fi network has no internet.
12. **Mobile data at the same time.** Open a web page in the phone's browser. *Seen:* it
    loads, and the app still shows the board's status.
13. **Every action on the board.** Steps 3 to 9 again, with the brightness at 40 or
    less. *Seen:* the LEDs keep playing during an upload; the speed of the upload.
14. **Mobile data off.** Switch mobile data off and repeat step 3. *Seen:* the same.
15. **Note** the phone's model, its Android version, the web view's version from the
    connection screen, and anything that was not as written.

## Documents

| Document | What changes |
|---|---|
| `docs/android-app.md` | Rewritten as the app's page, with the sections Requirement 23 lists. The first notes and their questions go: the owner answered them. |
| `docs/commands.md` | "Status reply", as printed above. |
| `docs/core.md` | The two members where it describes `status`. |
| `docs/emulator.md` | `--lan` in the usage line and the table of options, the `lan:` line, the warning, a section on reaching the emulator from a phone; the `status` replies it prints. |
| `docs/firmware.md` | The `status` reply it prints; what was measured in task 2. |
| `docs/wifi.md` | A section on what a phone does on a network without internet, which points to the app's page. |
| `docs/decisions.md` | "Commands": `status` reports the canvas size. The app as it is. A line in the change log. |
| `README.md` | The sentence that calls `docs/android-app.md` first notes. |

## Order of work

1. `status` with the canvas size.
2. The firmware with it, on the board.
3. The emulator's `--lan`.
4. The tool, the toolchain and a first APK of an empty page: everything about the build
   that this design assumes is settled before the app is written.
5. The suite's harness and the readers of media in Chrome: everything about decoding
   that this design assumes.
6. The client and the connection screen.
7. The show screen and the items screen.
8. Converting and the previews.
9. Uploading.
10. Every message, the look and back.
11. The sender and the app's own Android files; the APK; `tests/apk/`.
12. The documents and the last run.
13. The check on a phone.

## Risks

1. **The phone and the network without internet** (P1, P2). Nothing of it can be tried
   without a phone, and it decides whether the app works at the event. The design uses
   the one interface Android documents for this case; the fallbacks are named, and the
   connection screen shows what the phone reports, so that a failure can be read off it.
2. **The sender is not run by any test.** It is small, compiled by every build, and
   looked into by `tests/apk/` only as far as that it is there.
3. **Video on real phones** (P5). The reader of the tables is ours and is tested against
   PyAV on files made for the test, not on files from many phones. Decoding is the
   phone's, and whether a phone decodes HEVC through this interface differs from phone to
   phone. If the check on a phone finds videos that cannot be read, the alternative is a
   second reader on a `<video>` element, which plays everything the phone plays but
   takes its times from the player and must seek for every tick.
4. **A fragmented video, WebM and other containers are refused.** Phone cameras write
   plain MP4 files; videos from other sources may not be.
5. **The app differs from the converter on a computer in two places**: rotation, and
   large frames made smaller by the web view.
6. **The toolchain is 740 MB of downloads and more** on first use, from four sources
   that each can change: npm, Adoptium, Google's SDK repository and Gradle's. The
   checksums catch a changed file; they do not bring back a removed one.
   `build/app/downloads/` keeps what was fetched.
7. **`sdkmanager` is deprecated** (F9). It is in the pinned archive, and the archive is
   pinned by its checksum.
8. **Plain HTTP and no password of its own.** Whoever is on `odrig` can send commands
   with any program, as before this seed. The app adds no protection and needs none
   removed.
9. **Several phones.** One upload can be open; `Clear it` on one phone ends another
   phone's upload. The app asks before it does so.
10. **A debug key that lives in the work folder.** A new work folder cannot update an
    installed app.

## What goes beyond the seed

Each is recorded in `docs/drifts.md`:

1. The two members of `status`, which the owner approved for this seed.
2. The tool's commands `serve` and `install`, and the suite `tests/apk/`.
3. The switch between a compressed and an uncompressed file.
4. A rotation that is applied and large frames that are made smaller, where the
   converter on a computer does neither.
5. The line of the connection screen that says how requests travel, and `build.json`.
6. `Clear it`, for an upload that is open on the installation.
