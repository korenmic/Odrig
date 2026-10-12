# Design: the operators' app, command and control (seed 09)

## Overview

The app is a web page of two screens inside an Android shell made with Capacitor. The page
is plain JavaScript, HTML and CSS. It asks the target for `status` once a second and for
`list` now and then, shows what the replies say, and sends `play <id>`, `play all`, `on`,
`off` and `brightness <n>` when the operator presses something. Nothing else is sent.

One piece of Android code, the sender, carries each command line to the target on the
phone's Wi-Fi network, because the board's network has no internet and a phone would
otherwise send the request over mobile data. In a browser the same page sends with
`fetch`, which is how the suite runs it against an emulator.

A tool in Python installs the build tools into the project folder and builds the APK.
The emulator gets an option to listen on the local network, so that a phone reaches it.

Nothing of the core, of the firmware or of the command list changes.

## What this design relies on

Read in the repository as it is after seed 16:

| # | Fact | Where |
|---|---|---|
| R1 | `status` answers `{"ok":true,"on":…,"brightness":…,"playing":…,"animation":…,"fps":…,"error":…}`. `playing` is `"all"` for the playlist, the id of a cycle, or `null`; `animation` is the id of the animation on the LEDs, or `null`; `error` is `null` or the reason of an invalid show. It has no file name. | `docs/commands.md`, "Status reply" |
| R2 | `list` and `list <from>` answer the items in the order of the show: an animation as `{"id","file","bytes"}`, a cycle as `{"id","cycle","seconds"}`, and `next`, the position to ask for next, or `null`. It is refused with `show-invalid` while the show is invalid. | `docs/commands.md`, "Storage and the installed items" |
| R3 | `play <id>` of an animation plays the playlist from it; `play all` plays the playlist from its first animation and is refused with `unknown-id` by a show without an animation; both are refused with `show-invalid` by an invalid show. `on`, `off` and `brightness <n>` are never refused for a reason of the show. | `docs/commands.md`, `docs/show.md` |
| R4 | The emulator's server is bound to `("127.0.0.1", port)`. A reply to `POST /odrig` has `Access-Control-Allow-Origin: *`; of a body the first 4,096 bytes count; any other method on `/odrig` gets 405. | `emulator/httpd.py` |
| R5 | The emulator prints `page:`, then `serial:` where the system has a virtual serial port, then `tcp:` when it takes lines over TCP. Its line port is bound to the same address as the page. | `emulator/app.py`, `emulator/lineport.py` |
| R6 | A test allows `127.0.0.1` as the only address a source of the emulator names; another lists the options; another reads the listening sockets. | `tests/emulator/test_scope.py`, `test_start.py`, `test_http.py` |
| R7 | `tests.emulator.support.Emulator` starts the emulator as a child process on a free port and reads its event stream, in which every command line it took is a `log` event with its transport. | `tests/emulator/support.py` |
| R8 | On the board, `POST /odrig` reaches the core byte for byte when the content type is `application/octet-stream`, and for `text/plain` as long as the body has none of `&`, `=`, `+`, `%`. No command of this app has one. WLED adds `Access-Control-Allow-Origin: *` to every response. | `docs/firmware.md`, "Commands over HTTP" |
| R9 | The board hosts the network `odrig`, WPA2, and is at `4.3.2.1`. While its access point is up, WLED answers every name with its own address and redirects a page asked for by name to `http://4.3.2.1`. | `docs/wifi.md`; `wled00/wled.cpp` and `wled_server.cpp` of WLED 16.0.1 |
| R10 | The converter's suite starts Chrome without a window from Node.js, with the program `ODRIG_CHROME` names or the one in `/Applications`, serves a page on the loopback address and takes one `POST /result` from it. | `converter/tests/browser.test.js` |

On this Mac, read and not changed: Node.js 26.5.0, Google Chrome in `/Applications`, no
Java and no Android tool.

## Read for this design

Read on 2026-10-12 for the design of the whole app, from the sources named. Nothing was
installed. Versions move: task 6 reads each again before it pins it, and records what
changed in `docs/drifts.md`.

| # | Fact | Source |
|---|---|---|
| F1 | The newest Capacitor is 8.5.3: `@capacitor/core`, `@capacitor/cli` and `@capacitor/android`, under the MIT licence. Its command line needs Node.js 22 or later. | `registry.npmjs.org/@capacitor/core/latest`, `…/cli/latest`, `…/android/latest` |
| F2 | Capacitor 8 supports Android from API level 24. The platform is added with `npx cap add android`; `npx cap sync` copies the web files into the Android project. | `capacitorjs.com/docs/android` |
| F3 | The Android project that 8.5.3 creates: `minSdkVersion` 24, `compileSdkVersion` and `targetSdkVersion` 36, the Android Gradle plugin 8.13.0, Gradle 8.14.3, Java 21 for Capacitor's own module, the one permission `INTERNET`. Its `.gitignore` leaves out the copied web files, the generated configuration files, `build/`, `.gradle/` and `local.properties`. | the template of `@capacitor/android` 8.5.3 |
| F4 | The Android Gradle plugin 8.13 needs JDK 17 or later and the SDK build tools 35.0.0. | its release notes on `developer.android.com` |
| F5 | In a Capacitor app the page is served under `https://localhost`. `android.minWebViewVersion` is compared with the phone's web view, and `server.errorPath` names the page shown when it is older. A plain request from the page is mixed content, blocked unless `android.allowMixedContent` is set. A plugin class inside the app's own project is registered in `MainActivity`. | `capacitorjs.com/docs/config`, the source of `@capacitor/android` |
| F6 | The script Capacitor puts into every page defines `window.Capacitor` with `isNativePlatform()` and `nativePromise(pluginName, methodName, options)`. | `core/native-bridge.ts` at tag `8.5.3` |
| F7 | Temurin JDK 21.0.12.1+1 for macOS on Apple Silicon: `OpenJDK21U-jdk_aarch64_mac_hotspot_21.0.12.1_1.tar.gz`, 200,073,404 bytes, SHA-256 `3623232f33a9c3baadf304480b2535f9a3cba8a58d42ecbb438ba267315d9998`. | `api.adoptium.net/v3/assets/latest/21/hotspot` |
| F8 | The Android SDK command-line tools for macOS: `commandlinetools-mac_arm64-15859902_latest.zip`, 156,083,281 bytes, SHA-256 `835b62a26162b229b441d1f6d4680383815a270809eb33522c0d480fa5002c4e`. The page asks for agreement to the Android SDK licence before the download. | `developer.android.com/studio` |
| F9 | `sdkmanager` is in that package, at `cmdline-tools/latest/bin/sdkmanager` once unpacked so, and installs packages by name with `--sdk_root=<path>`. The page calls it deprecated and still documents it. | `developer.android.com/tools/sdkmanager` |
| F10 | The SDK packages `platforms;android-36`, `build-tools;35.0.0` and `platform-tools` are all under the licence `android-sdk-license`. | `dl.google.com/android/repository/repository2-3.xml` |
| F11 | `gradle-8.14.3-all.zip` has 224,584,249 bytes and the SHA-256 `ed1a8d686605fd7c23bdf62c7fc7add1c5b23b2bbc3721e661934ef4a4911d7c`. | `services.gradle.org/distributions/` |
| F12 | `ANDROID_HOME` is the SDK's folder; `ANDROID_USER_HOME` the folder of the Android tools' own settings, `.android` in the home folder without it. | `developer.android.com/tools/variables` |
| F13 | For an app that targets API level 28 or higher, plain HTTP is refused unless a network security configuration allows it; `<base-config cleartextTrafficPermitted="true">` allows it for every address. | `developer.android.com/privacy-and-security/security-config` |
| F14 | From Android 5 on, a phone on a Wi-Fi network without internet does not route an app's requests to it. An app sends traffic there with `Network#openConnection(URL)`, or binds its process. | Android Developers Blog, "Connecting your App to a Wi-Fi Device" |
| F15 | `Network.openConnection(URL)` sends all its traffic over that network. `ConnectivityManager.requestNetwork` needs the permission `CHANGE_NETWORK_STATE`, which no question is asked for. Both are there from API level 23. | `developer.android.com/reference/android/net/Network`, `…/ConnectivityManager` |
| F16 | From Android 17 on, an app that targets API level 37 or higher needs the permission `ACCESS_LOCAL_NETWORK` to reach a local address. An app that targets a lower level keeps its access. | `developer.android.com/privacy-and-security/local-network-permission` |

## Assumed, to be verified

**By task 6, which builds the first APK:**

| # | Assumption | If it does not hold |
|---|---|---|
| T1 | `npm install --prefix app` with Node.js 26.5 installs the three packages at the version pinned, and `cap add android` creates the project of F3. | The newest 8.x that does; F3 is read again and the drift recorded. |
| T2 | Capacitor takes a `webDir` outside its own folder, `../build/app/www`. | The folder handed over is `app/dist/`, which `.gitignore` then names. |
| T3 | The archive of F8 holds `sdkmanager`, which runs on the JDK of F7 and, with `--sdk_root`, installs the three packages of F10 after one question, for `android-sdk-license`. | The program that F9 says replaces it; what it asks and installs is recorded first. |
| T4 | The build asks for no SDK package beyond the three of F10. | Exactly the package it names is added to `app/toolchain.json`. |
| T5 | With the variables of "The environment of every child process", a setup and a build write nothing outside the repository's folder. The task lists the entries of the home folder, of `~/Library/Caches`, `~/Library/Preferences`, `~/.gradle`, `~/.android` and `~/.npm` before and after. | What appears is named in `docs/android-app.md`, and a variable is added where one exists for it. |
| T6 | Gradle accepts `distributionSha256Sum` in the wrapper's properties and Capacitor's `sync` leaves that file alone. | The tool checks the checksum before Gradle runs. |
| T7 | After one build, a build with the network switched off succeeds. | The documentation says what a build fetches every time. |

**By task 2, in Chrome on this Mac:**

| # | Assumption | If it does not hold |
|---|---|---|
| C1 | A page from `127.0.0.1:A` may `POST` a text to `127.0.0.1:B/odrig` with `fetch` and read the reply, with no request before it and no question to anyone. | The suite's server passes `/odrig` on to the emulator, and the app is given the server's own address. |
| C2 | Chrome without a window lays the page out at the size `--window-size=360,740` names. | The driver gives the frame that holds the app that size. |
| C3 | A page in a frame of the driver's page, both from the suite's server, can be worked by the driver: its buttons pressed, its fields filled, its `localStorage` set before it loads. | The driver is loaded by the app's page itself, when the address has a mark the suite sets. |

**By the check on a phone, which only the owner can do:**

| # | Assumption | If it does not hold |
|---|---|---|
| P1 | On `odrig`, with mobile data on, `requestNetwork` for the Wi-Fi transport hands the sender the network, and a request opened on it reaches `4.3.2.1`. | The sender also binds the process to that network; what the phone did is recorded. If the phone leaves the network by itself, the documentation says what the operator sets on the phone. |
| P2 | Android takes `odrig` for a network without internet or with a sign-in (R9), stays joined when the operator says so, and keeps its other traffic on mobile data. | What the phone asks, and what to answer, is written into `docs/android-app.md`. |
| P3 | `window.Capacitor.nativePromise("Target", "send", …)` reaches the sender with no script of `@capacitor/core` in the page (F6). | The build copies Capacitor's script for pages without a bundler into the package, and the web code calls the plugin through its `registerPlugin`. |
| P4 | Plain HTTP to `4.3.2.1` and to a Mac's address is let through (F13). | The configuration is corrected from the error the sender reports. |
| P5 | The screen stays on while the app is in front, and the back gesture does what Requirement 11 says. | The finding is recorded. |

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
    webserver.py          the web code on 127.0.0.1
    device.py             install on a phone by USB
  toolchain.json          the JDK, the command-line tools and the SDK packages
  package.json            private; the three Capacitor packages at one exact version
  package-lock.json       tracked
  capacitor.config.json
  www/                    the web code
    index.html            the two screens and the two buttons
    old.html              shown when the web view is too old
    style.css
    main.js               start; which screen is shown; back
    target.js             the address; one line sent, by the sender or by fetch
    client.js             the queue, its order, the timers; what the replies told
    commands.js           each command as a function that checks its reply
    messages.js           every text
    screens/show.js
    screens/target.js
  android/                the Capacitor project, tracked
    app/src/main/AndroidManifest.xml                          changed
    app/src/main/java/app/odrig/operators/MainActivity.java   changed
    app/src/main/java/app/odrig/operators/TargetPlugin.java   new: the sender
    app/src/main/res/xml/network_security_config.xml          new
    gradle/wrapper/gradle-wrapper.properties                  changed: the checksum
    ...                   every other file as `cap add android` made it
tests/
  app/                    the suite: needs no phone
    support.py            the emulator, a stand-in target, the server, Chrome, a scenario run
    page/                 driver.html, driver.js, scenarios/
    test_*.py
  apk/                    checks of a built APK: needs the work folder, no phone
docs/
  android-app.md          rewritten: the app's page
```

Also changed: `emulator/app.py` and `httpd.py`; `tests/emulator/test_start.py`,
`test_http.py`, `test_scope.py` and `test_docs.py`; `.gitignore`, which gains
`/app/node_modules/`; `docs/emulator.md`, `docs/wifi.md`, `docs/decisions.md`,
`AGENTS.md`, `README.md` and the pages of `agent/`.

No file of `core/`, `converter/`, `odrig/`, `odrigctl/` or `firmware/` changes.

| Path | |
|---|---|
| `app/www/`, `app/apptool/`, `app/app.py`, `app/toolchain.json`, `app/package.json`, `app/package-lock.json`, `app/capacitor.config.json` | Tracked. |
| `app/android/` | Tracked, with the `.gitignore` Capacitor puts into it (F3). |
| `app/node_modules/` | Ignored, by the root `.gitignore`. |
| What a build copies or generates inside `app/android/` | Ignored, by `app/android/.gitignore`. |
| `build/app/` | Ignored: `/build/` is in the root `.gitignore` already. |

## The emulator on the local network

```
python -m emulator SHOW_DIR [--port N] [--serial-link PATH] [--tcp-port N] [--core PATH] [--verbose] [--storage BYTES] [--lan]
```

| Option | Meaning | Without it |
|---|---|---|
| `--lan` | The page and the commands over HTTP are reachable on every IPv4 address of this computer, so that a phone on the same network reaches the emulator. | 127.0.0.1 only. |

- `emulator/httpd.py`: `Server(port, engine, show_dir, hello, lan=False)` binds
  `("0.0.0.0", port)` with `lan` and `("127.0.0.1", port)` without. `url` stays the
  address on 127.0.0.1. A new function gives this computer's address on the local
  network:

  ```python
  def lan_address():
      """The address this computer has on the network that carries its default route."""
      with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as probe:
          try:
              probe.connect(("192.0.2.1", 9))
          except OSError:
              return None
          address = probe.getsockname()[0]
      return None if address.startswith("127.") else address
  ```

  Connecting a datagram socket sends nothing: it asks the system which of the computer's
  addresses would be used. `192.0.2.1` is an address reserved for documents.
- The line port of `emulator/lineport.py` and the virtual serial port are not touched:
  they stay on this computer (R5).
- `emulator/app.py`: the flag `--lan`; with `--record` it is a usage error, like
  `--port`. After the lines it prints today it prints the line `lan:`, or
  `lan: no address` when the computer is on no network, and it writes the warning to
  standard error before the server starts.

With `--lan`, on a Mac:

```
page: http://127.0.0.1:8600/
serial: /Users/you/odrig/build/emulator/serial
lan: http://192.168.1.23:8600/
```

and on standard error:

```
warning: --lan: anyone on the local network can send commands to this emulator and open its page
```

The emulator has no password. `docs/emulator.md` says so, and that macOS may ask whether
Python may accept incoming connections: a phone reaches the emulator only when that is
allowed. The address the app is given is the one of the `lan:` line, `192.168.1.23:8600`.

Tests that change: `test_scope.py` allows the addresses `127.0.0.1`, `0.0.0.0` and
`192.0.2.1`, all in `emulator/httpd.py`; `test_start.py` has `--lan` among the options,
refuses it with `--record`, and reads the `lan:` line and the warning; `test_http.py`
keeps its test that the emulator without the option listens on 127.0.0.1 only, and with
`--lan` finds the page's socket at `*:<port>`, a reply on 127.0.0.1, a reply on the
address of the `lan:` line when there is one, and the line port still on 127.0.0.1.

## The tool

```
python3 app/app.py setup
python3 app/app.py build
python3 app/app.py serve [--port N]
python3 app/app.py install
```

`app/app.py` and `app/apptool/` use the standard library of Python only, as
`firmware/fw.py` does.

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

### `app/toolchain.json` and `app/package.json`

`toolchain.json` names the JDK and the command-line tools, each with its version and, for
`darwin-arm64`, its address, size and SHA-256 (F7, F8); the SDK packages
`platform-tools`, `platforms;android-36` and `build-tools;35.0.0`; and the licence
`android-sdk-license` (F10). It has an entry for the one system the build is verified on.
On another system the tool ends with `unsupported-platform` and names the file.

`package.json` is private and names `@capacitor/android` and `@capacitor/core` as
dependencies and `@capacitor/cli` as a development dependency, each at one exact version,
8.5.3 unless task 6 finds a newer 8.x (F1, T1). No version is a range, and the lock file
fixes what npm fetches below the three.

### What is installed where

| What | Where |
|---|---|
| The Capacitor packages and what they need | `app/node_modules/` |
| The JDK | `build/app/jdk/` |
| The command-line tools and the SDK packages | `build/app/android-sdk/` |
| Gradle, fetched by the project's wrapper, and everything Gradle fetches | `build/app/gradle/` |
| The archives as fetched, kept so that a setup can be repeated without the network | `build/app/downloads/` |
| The Android tools' settings and the debug key | `build/app/android-user/` |
| npm's cache | `build/app/npm-cache/` |
| The settings of Capacitor's command line | `build/app/home/` |
| The folder handed to Capacitor | `build/app/www/` |
| The APK | `build/app/odrig-debug.apk` |

The downloads that have a known size add up to about 740 MB. Task 6 measures the work
folder after a build and the time of a first and of a second build, and task 8 writes
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

Gradle runs with `--no-daemon`, so nothing of a build stays running, and with
`-Duser.home=build/app/home`: Java takes the user's folder from the system and not from
`HOME`, and the Android build keeps a settings file in it.

### `setup`

Every step is skipped when its result is there. `build/app/setup.json` records the
SHA-256 of `app/package-lock.json` and of `app/toolchain.json` that were installed.

1. `node --version` is 22 or later, else `node-missing`. This is first.
2. `npm ci --prefix app`.
3. The JDK: fetched into `build/app/downloads/`, its size and SHA-256 compared, unpacked
   into `build/app/jdk/`. The first line of `java -version` is printed.
4. The command-line tools: fetched and compared in the same way, unpacked so that
   `build/app/android-sdk/cmdline-tools/latest/bin/sdkmanager` is there, with the
   executable bits of the archive kept.
5. The SDK packages: `sdkmanager --sdk_root=build/app/android-sdk` with the names of the
   file. The tool gives it one `y` and a newline on standard input and then closes it:
   the answer to the one licence the three packages are under. Afterwards the folder
   `licenses/` of the SDK must hold `android-sdk-license` and no other file, and each
   package's folder must be there; else `licence-refused`.

The tool does not run `sdkmanager --licenses`, which would accept every licence the SDK
has. The owner accepted the SDK's licence terms; the build accepts the one licence the
build needs.

### `build`

1. `setup`.
2. The folder for Capacitor, `build/app/www/`, is removed and made: every file of
   `app/www/`, and `build.json`, `{"commit":"<the commit>","changed":<true or false>}`,
   from `git rev-parse HEAD` and from whether `git status --porcelain -- app` prints
   anything.
3. `app/node_modules/.bin/cap sync android`, in `app/`.
4. `app/android/gradlew --no-daemon -p app/android assembleDebug`.
5. `app/android/app/build/outputs/apk/debug/app-debug.apk` is copied to
   `build/app/odrig-debug.apk`. The tool prints three lines: `apk: <path>`,
   `bytes: <size>` and `sha256: <digest>`.

### `serve` and `install`

`python3 app/app.py serve` starts `webserver.py` on `127.0.0.1`, port 8610 unless
`--port` names another, and prints `app: http://127.0.0.1:8610/`. It serves `app/www/`
at `/`, each file with the content type of its ending and `Cache-Control: no-store`, and
nothing else. With an emulator on the same computer, the app in a browser is given the
address `127.0.0.1:8600`. The suite uses the same server.

`install` runs `adb install -r build/app/odrig-debug.apk` with the `adb` of the SDK in
the work folder. `adb devices` must list exactly one device, else `no-device`.

## The Capacitor project

`app/capacitor.config.json`:

```json
{
  "appId": "app.odrig.operators",
  "appName": "odrig",
  "webDir": "../build/app/www",
  "android": {"minWebViewVersion": 80, "backgroundColor": "#000000"},
  "server": {"errorPath": "old.html"}
}
```

The page is served inside the app under `https://localhost` (F5). Mixed content stays
forbidden and `CapacitorHttp` stays off: the web view sends nothing to the target itself.

The Android project is made once, by `cap add android` in task 6, and tracked. Changed in
it, in task 7:

| File | Change |
|---|---|
| `AndroidManifest.xml` | `android:networkSecurityConfig="@xml/network_security_config"` on `application`; the permissions `ACCESS_NETWORK_STATE` and `CHANGE_NETWORK_STATE` beside `INTERNET`. |
| `res/xml/network_security_config.xml` | `<network-security-config><base-config cleartextTrafficPermitted="true" /></network-security-config>` |
| `MainActivity.java` | `registerPlugin(TargetPlugin.class)` before `super.onCreate`, and `getWindow().addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON)` after it. |
| `TargetPlugin.java` | The sender. |
| `gradle/wrapper/gradle-wrapper.properties` | `distributionSha256Sum` with the value of F11, in task 6. |

`minSdkVersion`, `compileSdkVersion` and `targetSdkVersion` stay as the template has
them. The launcher picture and the splash screen are the template's.

- **Plain HTTP for every address.** The target is an address the operator sets: the
  board's, or a computer's on any network. A rule for one address cannot cover that, so
  the configuration allows plain HTTP as a whole (F13). The app sends to no address but
  the one that is set.
- **The web view.** The web code uses module scripts, `fetch`, `AbortController` and the
  JavaScript of 2020. A web view of version 80 has all of it. On a phone with an older
  one Capacitor shows `old.html`, a page without scripts that says the phone's "Android
  System WebView" must be updated in the Play Store.
- **Permissions.** None of the three asks the operator a question (F15). The app does
  not read the network's name, which would need the location permission.
- **Android 17.** The app targets API level 36 and keeps its access to the local network
  there (F16). Raising the target level is not part of this seed.

## Reaching the target

### What the phone does with the board's network

`odrig` has no internet. A phone on such a network keeps using mobile data for its apps,
and an app's request is not routed to it (F14). WLED's access point also answers every
name and redirects every page (R9), so the phone is expected to offer a sign-in for
`odrig`, or to say that it has no internet (P2). Either way a request from the web view
would leave through mobile data and never reach `4.3.2.1`.

### The sender

`TargetPlugin.java`, a plugin class inside the app's own Android project, named `Target`.
It holds the Wi-Fi network that the system hands it and a worker thread.

- **The network.** At its load it asks the system, with `requestNetwork`, for a network
  with the Wi-Fi transport and without the need for internet access, and keeps the
  network of the callback `onAvailable`, until `onLost`. The network of `odrig` satisfies
  that request whatever Android thinks of it, and the request tells Android that an app
  needs that network. The callback is released when the plugin is destroyed.
- **`send({address, line, timeoutMs})`.** Without a network it is refused at once with
  the code `no-wifi`. Otherwise, on the worker thread, it opens
  `http://<address>/odrig` on that network with `Network.openConnection(url,
  Proxy.NO_PROXY)`, which sends all its traffic there (F15): method `POST`; the headers
  `Content-Type: application/octet-stream` (R8) and `Connection: close`; the line's bytes
  in UTF-8 with a fixed length; `timeoutMs` as the limit for connecting and for reading.
  It resolves with `{status, body}`, the body being at most 4,096 bytes read as UTF-8,
  from the error stream when the status is not 200. Any `IOException` is the code
  `no-answer`, with the exception's text as the detail.
- **Sent once.** A body of fixed length cannot be sent a second time by the HTTP layer,
  and with `Connection: close` no kept connection is tried that the board has closed
  meanwhile. So a line reaches the target once or not at all.
- **`route()`** resolves with `{wifi, validated, portal, others}`: whether there is a
  Wi-Fi network; whether it has the capabilities `VALIDATED` and `CAPTIVE_PORTAL`; and
  the transport of the phone's default network, `"wifi"`, `"mobile"`, `"other"` or
  `"none"`.
- The sender looks into no line and no reply.

The plugin is about 120 lines of Java. Nothing else in the app is written for Android.

A `fetch` from the page is not used in the app: it would leave through the phone's
default network, which is mobile data while `odrig` has no internet, and from
`https://localhost` it is mixed content. `CapacitorHttp` sends from Java, but on the
default network too.

### `target.js`

```js
export const BOARD = "4.3.2.1";
export function parse(text)        // "host" or "host:port" -> the address as kept, or throws
export function address()          // from localStorage "odrig.target", else BOARD
export function setAddress(text)
export async function send(line, limit = 5000)   // -> the reply as an object, or throws a Failure
export async function route()      // -> {sender, wifi, validated, portal, others}
```

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
at the limit. A text body needs no request before it (C1), and the content type the
browser gives it reaches the core unchanged for every command of the app (R8).

`target.js` is the one file that knows how a line travels, and the only one with `fetch`
or `window.Capacitor` in it.

## The web code

`index.html` holds the two screens as two sections, the two buttons `Show` and `Target`
along the bottom edge, the line that says the target does not answer, and the place for a
message. It loads `style.css` and `main.js` as a module. No page is loaded after the
first.

### The client (`client.js`)

One object holds what the replies told: the state of the connection, `checking`,
`answers` or `no-answer`, with the failure; the newest `status`; the animations of the
newest complete `list`, each as `{id, file}`, and the ids of its cycles; and the time of
the newest reply. Screens read it and are told when it changes. It never holds what the
app hopes.

**The queue.** One request is under way at a time. What waits is taken in this order:

1. what the operator asked for: `on`, `off`, `brightness <n>`, `play <id>`, `play all`;
2. a `status` that is due;
3. a `list` that is due, or the next part of one.

A list that waited while a `status` was sent goes before the next `status`, so that a
target that answers slowly does not keep the list away.

A `brightness` that waits is replaced by a newer one. A `status` is due 1,000 ms after
the one before was sent, and at once after the reply to a command of the first kind. A
`list` is due when the target first answers, 10 seconds after the one before ended while
the show screen is shown, when a `status` names an animation the list does not have, and
after a refusal with `unknown-id`. While the document is hidden nothing of the second and
third kind is made due; when it is shown again, a `status` is due at once.

**A list in parts.** `list` is followed by `list <next>` until `next` is `null`. The new
list takes the place of the old one only when it is complete. When a part fails, the old
list stays.

**The state of the connection** follows every request: a reply makes it `answers`; a
`no-wifi`, `no-answer` or `bad-reply` makes it `no-answer` with that failure. A refusal,
`"ok":false`, is a reply: the target answers.

**`commands.js`** has a function for each command. Each builds its line and checks that a
reply with `"ok":true` has the members the command promises, with the types they must
have (R1, R2); a reply that lacks them is `bad-reply`. A reply with `"ok":false` becomes
a `Refusal` with its code.

### The show screen

- The state, large: `ON` or `OFF`; `Brightness 128`; what plays, `Playlist`, `Cycle 3` or
  `Nothing plays`; `Now 2 dvd.odrg`; `50 refreshes a second`. An animation the list does
  not have yet is `Now 2`. With an invalid show its message stands in the place of what
  plays.
- `On` and `Off`, two buttons side by side; the one in effect is marked.
- The brightness slider, as wide as the screen, with its number. While it is moved a
  command goes out at most every 200 ms, and the value at which it is let go is always
  sent. A `status` reply does not move the slider while it is held, nor for 1,000 ms
  after the last brightness command.
- `Playlist from the start`, which sends `play all`.
- One button for each animation, in the order of the show, with its id and its file name.
  The one on the LEDs is marked. A show without an animation is the line `No animation is
  installed.`
- While the target does not answer, the values are dimmed and a line says for how long.

### The target screen

- A field with the address, with the keyboard for addresses. `Use` takes it; `Board`
  puts `4.3.2.1` back.
- The state: `Checking`, `Answers` or `No answer`, with the message of the failure; and
  the reason of an invalid show while the target answers.
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
- In small print: the web view's version, from the user agent, and `build <commit>` from
  `build.json`, with `changed` when the build says so.

### Messages (`messages.js`)

One table. A message is its text with the code in brackets at its end, and stays until it
is dismissed or replaced.

| Failure or code | From | Text |
|---|---|---|
| `bad-address` | the field | That is not an address. Write it like 4.3.2.1 or 192.168.1.23:8600. |
| `no-wifi` | any | This phone is not on a Wi-Fi network. Join the network odrig in the phone's Wi-Fi settings. |
| `no-answer` | any | No answer from `<address>`. Check that the phone is on the installation's Wi-Fi network and that the installation has power. |
| `bad-reply` | any | Something answered at `<address>`, but it is not an odrig installation. |
| `line-too-long`, `unknown-command`, `bad-argument` | any | The installation did not understand the app. Its software and this app do not match. |
| `show-invalid` | `play`, `list` | The installed show is invalid: `<reason>`. Nothing can be played until a show is installed over USB. |
| `unknown-id` | `play <id>` | Animation `<id>` is not installed any more. |
| `unknown-id` | `play all` | No animation is installed. |
| any other code | any | The installation refused the command. |

The other codes of `docs/commands.md` belong to `remove`, `space` and `upload`, which the
app does not send; `messages.js` names them as codes the app cannot get, and the test of
Requirement 9 reads that list.

### The look and back

- Black, `#000000`, behind everything. Text `#e8e8e8`; lesser text `#b0b0b0`; what is in
  effect and what a touch will do, amber, `#ffb000`. Buttons are dark, `#1c1c1c`, with a
  border; none is a bright area. Each text colour has a contrast of 7 to 1 or more
  against black and against the dark of the buttons.
- The system's font, 18 pixels for text, 20 for buttons, 28 for the state.
- Every button, field and slider is 56 pixels high or more and has 8 pixels around it.
  The two screen buttons lie along the bottom edge, each half the width.
- One column. No pictures, fonts or scripts from anywhere but the package.
- Each change of screen adds an entry to the page's history, so the system's back
  gesture shows the screen before, and from the first screen it leaves the app.

## Testing

| Check | Needs |
|---|---|
| `python3 -m unittest discover -s tests/app -t .` | The suite: Chrome and the core's library; no phone and no Android tool. |
| `python3 -m unittest discover -s tests/apk -t .` | A built APK and the SDK in the work folder; no phone. |
| `docs/android-app.md`, "The check on a phone" | A person with a phone. |

### How the suite drives the app

`tests/app/support.py`:

- **The emulator**: `tests.emulator.support.Emulator` (R7), on a show in a temporary
  folder: the demo show of the target file, or a show the test writes, such as one of 40
  animations, one without an animation, and one with a file missing.
- **A stand-in target**: a small server of the test on a free port of 127.0.0.1 that
  answers `POST /odrig` as the test said: fixed replies in their order, a status other
  than 200, a body that is no JSON, or no reply at all. It gives what an emulator cannot
  be made to give: an answer that is not odrig's, an old target that refuses `play all`
  with `bad-argument`, and silence.
- **The server**: `app/apptool/webserver.py` on a free port of 127.0.0.1, with more
  paths for the test: `/t/` is `tests/app/page/`, and `POST /result` takes what a
  scenario found.
- **Chrome**: the program `ODRIG_CHROME` names, or the one the converter's suite finds
  (R10), with `--headless=new --no-first-run --no-default-browser-check
  --disable-extensions --disable-background-networking --disable-sync
  --disable-component-update --window-size=360,740 --user-data-dir=<a new temporary
  folder>` and the address of the driver. It is ended, and its folder removed, when the
  result has come or after 60 seconds. Without a Chrome the suite fails and says where it
  looked.
- **The driver**, `page/driver.html` with `driver.js`: it sets the address the app is to
  use, puts the app's `index.html` into a frame of its own page (C3), and runs the
  scenario the test named, a module of `page/scenarios/`. A scenario works the app the
  way an operator does: it finds a button by its words and presses it, fills the field,
  moves the slider, and waits for words to appear. What it read off the screen goes to
  `/result`.
- A test is: start a target and the server, run a scenario, and compare what the screen
  showed with what the emulator says over HTTP and with the command lines its log has.

Nothing drives Chrome from outside, and no package is installed for it.

### What each test file holds

| File | Tests |
|---|---|
| `test_tool.py` | `toolchain.json` and `package.json` name exact versions; an archive of another size or SHA-256, served by the test, is refused and removed and nothing is unpacked; the environment of a child has every variable of the design and each folder lies in the work folder; the staged folder holds the files of `app/www/` and `build.json`; `serve` gives each file with its type and nothing outside `app/www/`; each reason of the error line. No test downloads a real archive. |
| `test_scope.py` | Every script of `app/www/` imports only `./…`; none names a network address but the board's in `target.js`, a path other than `/odrig`, or a command word outside the eight lines of Requirement 1; `fetch` and `Capacitor` are in `target.js` only; `index.html` loads nothing from another host; no file of `converter/lib/` is in `app/`. |
| `test_target.py` | The first address is `4.3.2.1`; an address is kept over a reload; each form of an address and each refusal; `Answers` against the emulator; `No answer` for a port nothing listens on, and for a target that stays silent for 5 seconds, and `Answers` again when an emulator starts there; `bad-reply` for a status that is not 200 and for a body that is no JSON; the reason of an invalid show; `Sent from this browser.`; the screen the app starts on and the one it shows after the first answer. |
| `test_show.py` | Every value of the state against `status`, for the playlist, for a cycle that plays, for a show without an animation and for an invalid show; a brightness the test sets through the emulator is on the screen within 2 seconds; the rows against `list`, for the demo show and for a show of 40 animations, which takes more than one reply; the mark moves when the playlist moves on; an animation uploaded through the emulator appears within 12 seconds. |
| `test_controls.py` | `On`, `Off`, each animation's button and `Playlist from the start`, each against the emulator's log and `status` afterwards; the slider: at most five `brightness` lines a second and the last value sent, counted in the log, and the slider not moved by a `status` while held; the operator's command is sent before a `status` that waits; nothing is sent while the document is hidden. |
| `test_messages.py` | Each failure and each code of the table with its text and its code in brackets: `unknown-id` after the test removed the animation through the emulator, with the list asked for again; `show-invalid`; `bad-argument` from the stand-in target; a message stays until dismissed; every code of `docs/commands.md` has a text or is named as one the app cannot get. |
| `test_look.py` | At 360 by 740, on each screen: every button, field and slider is 56 pixels high or more and 8 from the next; the background is black; the text colours have a contrast of 7 or more; nothing scrolls sideways, also at 320; back from the target screen and from the show screen. |
| `test_docs.py` | `docs/android-app.md` has every command of the tool with an example, the versions of `toolchain.json` and `package.json`, each message of `messages.js`, the check on a phone as numbered steps, and what is verified and what is open; `docs/emulator.md` has `--lan`. |

`tests/apk/test_apk.py`, on `build/app/odrig-debug.apk`, with `aapt2` of the SDK in the
work folder and Python's `zipfile`: the identifier and the label; `minSdkVersion`; the
three permissions, and the one an AndroidX library declares for the app itself, by its
name; the network security configuration with plain HTTP allowed; every file of
`app/www/` under `assets/public/` with its bytes, and `build.json` with the commit of the
work tree; the sender's class in the package. Without the APK the suite fails and names
the command that builds it.

## The check on a phone

`docs/android-app.md` gets this list. Each step says what must be seen.

**Before:** `python3 app/app.py build`; the firmware of seed 16 on the board, with the
dim example show; the phone with mobile data on.

1. **Install.** `python3 app/app.py install` with the phone on USB, or copy
   `build/app/odrig-debug.apk` to the phone and open it. *Seen:* the app `odrig` is on
   the phone and starts on the target screen with the address `4.3.2.1`.
2. **The emulator.** On the Mac: `python -m emulator build/demo-20/show --lan`; allow
   incoming connections if macOS asks. Phone and Mac on the same Wi-Fi. Give the app the
   address of the `lan:` line. *Seen:* `Answers`, `Sent over Wi-Fi.`, and then the show
   screen.
3. **Status.** *Seen:* the show screen has what the emulator's page has: on, the
   brightness, `Playlist`, the animation with its file name, about 50 refreshes a second.
   Send `python -m odrigctl --http 127.0.0.1:8600 brightness 40` on the Mac: the phone
   shows 40 within two seconds.
4. **Controls.** `Off`, `On`, the slider, each animation, `Playlist from the start`.
   *Seen:* the emulator's page follows each, and its log has each line as `http`.
5. **No answer.** Stop the emulator. *Seen:* within five seconds the app says that
   nothing answers, in words. Start it again: the app recovers by itself.
6. **The board's network.** Power the board. In the phone's Wi-Fi settings join `odrig`
   with the password. Leave mobile data on. Note what the phone says about the network
   and what you answered. In the app press `Board`. *Seen:* `Answers`, and a line that
   says the Wi-Fi network has no internet.
7. **Mobile data at the same time.** Open a web page in the phone's browser. *Seen:* it
   loads, and the app still shows the board's status.
8. **Every action on the board.** Steps 3 and 4 again, with the brightness kept at 40 or
   less: one strip is fed from the board's 3.3 V pin. *Seen:* the LEDs follow each
   action.
9. **Mobile data off.** Switch mobile data off and repeat step 3. *Seen:* the same.
10. **Note** the phone's model, its Android version, the web view's version from the
    target screen, and anything that was not as written.

## Documents

| Document | What changes |
|---|---|
| `docs/android-app.md` | Rewritten as the app's page, with the sections of Requirement 15. The first notes and their questions go: the owner answered them. |
| `docs/emulator.md` | `--lan` in the usage line and the table of options, the `lan:` line, the warning, and a section on reaching the emulator from a phone. |
| `docs/wifi.md` | A section on what a phone does on a network without internet, which points to the app's page. |
| `docs/decisions.md` | The app as it is, and a line in the change log. |
| `AGENTS.md`, `agent/README.md`, `agent/getting-started.md`, `README.md` | The app among the parts; seed 09 leaves "What is coming" when its tasks are done, with the owner's check named as open. |

## Order of work

1. The emulator's `--lan`.
2. The tool with its command `serve`, the suite's harness, `target.js`, the client and
   the target screen.
3. The show screen: the state and the list.
4. The controls: on, off, the brightness, an animation, the playlist.
5. Every message, the look and back.
6. The toolchain and a first APK of the web code: everything about the build that this
   design assumes.
7. The sender and the app's own Android files; the APK; `tests/apk/`.
8. The documents and the last run.
9. The check on a phone, which is the owner's.

The web code and its suite need nothing of the toolchain, so they come first: the app
works in a browser against an emulator before anything is downloaded. Task 6 downloads
about 740 MB and accepts the SDK's licence; before its first download the owner is told
the files, their sources and their sizes.

## Risks

1. **The phone and the network without internet** (P1, P2). Nothing of it can be tried
   without a phone, and it decides whether the app works at the event. The design uses
   the one interface Android documents for this case; the fallback is named, and the
   target screen shows what the phone reports, so that a failure can be read off it.
2. **The sender is not run by any test.** It is small, compiled by every build, and
   looked into by `tests/apk/` only as far as that it is there.
3. **The toolchain is about 740 MB of downloads** on first use, from four sources that
   each can change: npm, Adoptium, Google's SDK repository and Gradle's. The checksums
   catch a changed file; they do not bring back a removed one. `build/app/downloads/`
   keeps what was fetched.
4. **`sdkmanager` is called deprecated** (F9). It is in the pinned archive.
5. **Plain HTTP and no password of its own.** Whoever is on `odrig` can send commands
   with any program, as before this seed.
6. **Several phones.** Each learns the state by asking; the installation obeys the last
   command.
7. **A full brightness on the bench.** The slider goes to 255, and on the bench one strip
   is fed from the board's 3.3 V pin. The board's limit on LED current, 850 mA, is in
   force there; the check on a phone tells the owner to stay at 40 or less.
8. **A debug key that lives in the work folder.** A new work folder cannot update an
   installed app: the app is removed from the phone first.

## What goes beyond the seed

Each is recorded in `docs/drifts.md`:

1. The tool's commands `serve` and `install`, and the suite `tests/apk/`.
2. The line of the target screen that says how requests travel, and `build.json`.
3. `old.html`, for a web view that is too old.
