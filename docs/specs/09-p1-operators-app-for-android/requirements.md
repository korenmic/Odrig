# Requirements: the operators' app, command and control (seed 09)

Seed: [`project-seeds/09-p1-operators-app-for-android/seed.md`](../../../project-seeds/09-p1-operators-app-for-android/seed.md).

The operators' app is built in two parts. This spec is the first: an Android app that
shows what the installation plays and steers it. It lists the installed animations by id
and file name, plays one, goes back to the playlist, switches the LEDs on and off and
sets the brightness. The second part, converting a video on the phone and uploading it,
is seed 17 and is not described here.

An earlier spec in this folder described the whole app. The owner split the app on
2026-10-12, before any of its tasks was done, and this spec takes its place.

In this document:

- "the target" is what the app sends commands to: the board, or an emulator;
- "the web code" is the app's HTML, CSS and JavaScript, the same files in the app and in
  a browser;
- "the sender" is the app's one piece of Android code, which sends a command line to the
  target;
- "the tool" is `python3 app/app.py`, which sets up the build tools and builds the app;
- "the suite" is `tests/app/`, which needs no phone.

## Requirement 1: what the app is and what it may send

**User story.** As the owner, I want a small app that works and can be installed, and
that can do nothing the command list cannot.

1. The app SHALL be an Android app built with Capacitor. Its web code SHALL be plain
   JavaScript, HTML and CSS, with no step that turns it into other files.
2. The app SHALL reach its target only with `POST /odrig`, with one command line of
   [commands.md](../../commands.md) as the body.
3. The app SHALL send these commands and no other: `status`, `list`, `list <from>`,
   `play <id>`, `play all`, `on`, `off` and `brightness <n>`.
4. The app SHALL add no command and SHALL change nothing of the core, of the firmware or
   of a reply.
5. The package SHALL hold no converter, SHALL read no media and SHALL upload nothing.
6. The app SHALL have two screens: the show screen and the target screen.

## Requirement 2: the target's address

1. The address SHALL be `4.3.2.1`, the board's, until the operator sets another.
2. The operator SHALL be able to set it on the target screen, as a host name or an IPv4
   address, alone or followed by `:` and a port from 1 to 65,535. `http://` in front and
   one `/` at the end SHALL be dropped.
3. Any other text SHALL be refused with a message, and the address in use SHALL stay.
4. The address SHALL be kept when the app is closed and opened again.
5. One button SHALL put the board's address back.

## Requirement 3: the target screen

1. The target screen SHALL show whether the target answers: `Checking`, `Answers` or
   `No answer`, and with `No answer` the message of the failure.
2. WHILE the target answers and its show is invalid, the screen SHALL show the reason.
3. In the app, the screen SHALL say how requests travel: over Wi-Fi, whether that Wi-Fi
   network has internet, and whether the phone's other apps use mobile data. In a
   browser it SHALL say that requests are sent from the browser.
4. The screen SHALL tell the operator to join the network `odrig` in the phone's Wi-Fi
   settings. The app SHALL NOT join a network itself, and SHALL NOT need the location
   permission.
5. WHEN the app starts THEN it SHALL show the target screen, and the show screen as soon
   as the target has answered once.

## Requirement 4: the status

**User story.** As an operator, I want to see at a glance what the installation does.

1. The show screen SHALL show: `ON` or `OFF`; the brightness; what plays, which is the
   playlist, a cycle with its id, or nothing; the id and the file name of the animation
   on the LEDs; and the refreshes a second.
2. The app SHALL ask for `status` once a second while it is on the screen of the phone,
   and at once after the reply to a command the operator gave.
3. WHILE the app is not on the screen of the phone, it SHALL send nothing.
4. WHILE the target does not answer, the values SHALL be dimmed, and a line SHALL say so
   and for how long.
5. WHILE the show is invalid, the reason SHALL stand in the place of what plays, in
   words.
6. The screen SHALL show only what replies said. A control MAY be shown as pressed or
   moved; the state shown SHALL come from a reply.

## Requirement 5: the list

1. The show screen SHALL list every animation item of the show, in the order of the
   show, which is the order of the playlist, each with its id and its file name.
2. The animation on the LEDs SHALL be marked in the list.
3. The list SHALL be asked for when the target first answers, every 10 seconds while the
   show screen is shown, at once when `status` names an animation the list does not
   have, and after a refusal with `unknown-id`.
4. A show whose items do not fit into one reply SHALL be listed whole: the app SHALL ask
   with `list <from>` until `next` is `null`.
5. A show without an animation SHALL be shown as a line that says so.
6. Cycles SHALL NOT be listed. WHILE a cycle plays, the status SHALL name it by its id.

## Requirement 6: playing

1. WHEN the operator presses an animation of the list THEN the app SHALL send
   `play <id>`. The playlist goes on after that animation, as the core does it.
2. One button SHALL send `play all`: the playlist from its first animation.
3. A refusal SHALL be shown as its message. After `unknown-id` the list SHALL be asked
   for again.
4. The app SHALL NOT offer to play a cycle.

## Requirement 7: on, off and brightness

1. Two buttons SHALL send `on` and `off`. The one in effect, by the newest `status`,
   SHALL be marked.
2. A slider SHALL set the brightness from 0 to 255 and show its number.
3. WHILE the slider is moved, the app SHALL send at most five `brightness` commands a
   second, and the value at which it is let go SHALL always be sent.
4. A `status` reply SHALL NOT move the slider while it is held, nor for one second after
   the last `brightness` command.

## Requirement 8: requests

1. One request SHALL be under way at a time.
2. A command the operator gave SHALL be sent before a `status` or a `list` that waits.
3. A `brightness` that waits SHALL be replaced by a newer one.
4. A request SHALL end as `no-answer` after 5 seconds without a reply.
5. A command the operator gave SHALL be sent once. The app SHALL NOT send it again by
   itself.
6. WHEN a reply arrives after a failure THEN the app SHALL show `Answers` again, with no
   action of the operator.

## Requirement 9: failures in plain words

1. Every failure SHALL be shown as a sentence, with its code in brackets at its end.
2. There SHALL be a message for each of: an address that is none; no Wi-Fi network; no
   answer; an answer that is not an odrig target; and each error code of
   [commands.md](../../commands.md) that one of the app's commands can get.
3. A message SHALL stay until the operator dismisses it or another one takes its place.
4. A test SHALL read the error codes from `docs/commands.md` and find, for each, a
   message or the statement that no command of the app can get it.

## Requirement 10: the board's network

**User story.** As an operator at the event, I want the app to reach the installation
although its network has no internet and my phone keeps mobile data on.

1. In the app, every request SHALL be sent on the phone's Wi-Fi network, whatever
   network the phone uses for its other traffic.
2. Plain HTTP to the address that is set SHALL be allowed.
3. The app SHALL ask for no permission that the phone shows the operator a question
   for.
4. The sender SHALL look into no command line and no reply.
5. That requests reach the board while the phone has no internet through that network
   SHALL be checked by the owner on a phone; no test can check it.

## Requirement 11: the look

1. The design SHALL be dark: a black background, and no bright area.
2. Every button, field and slider SHALL be at least 56 pixels high and 8 pixels from the
   next.
3. Every text colour SHALL have a contrast of 7 to 1 or more against its background.
4. At a width of 360 pixels, and at 320, nothing SHALL scroll sideways.
5. Nothing SHALL depend on a pointer hovering, on a long press or on a swipe.
6. The app SHALL load no picture, font or script from outside its package.
7. The screen of the phone SHALL stay on while the app is in front.
8. The system's back gesture SHALL go from the target screen to the show screen when
   the target has answered, and SHALL leave the app from the show screen.

## Requirement 12: the emulator on the local network

1. `python -m emulator` SHALL accept the option `--lan`. With it the page and the
   commands over HTTP SHALL be reachable from other devices of the local network;
   without it, from this computer only, as today.
2. With `--lan` the emulator SHALL print one more line, `lan:`, with the address a phone
   is given, and SHALL warn on standard error that anyone on the network can send
   commands.
3. `--lan` SHALL be a usage error in record mode.
4. The port that takes command lines over TCP and the virtual serial port SHALL stay on
   this computer only.

## Requirement 13: the tool and the build

**User story.** As a contributor, I want one command that builds the app, and I want
everything it installs to be inside the project folder.

1. `python3 app/app.py build` SHALL make a debug APK at `build/app/odrig-debug.apk` and
   print its path, its size and its SHA-256.
2. `python3 app/app.py setup` SHALL install what a build needs: the Capacitor packages
   into `app/node_modules/`, and a JDK, the Android SDK's command-line tools and the SDK
   packages into `build/app/`. `build` SHALL run it first.
3. Every download SHALL be named by its exact version and checked by its size and its
   SHA-256, which are tracked. A file that differs SHALL be refused and removed.
4. The setup SHALL accept the one licence the SDK packages of the build are under, and
   no other.
5. A setup and a build SHALL write nothing outside the repository's folder.
6. `python3 app/app.py serve` SHALL serve the web code on `127.0.0.1`, so that it runs
   in a browser on this computer against an emulator.
7. `python3 app/app.py install` SHALL install the APK on the one phone that is connected
   by USB.
8. The tool SHALL use only the standard library of Python, and SHALL end a failure with
   one line `error: <reason>: <detail>` and status 1.

## Requirement 14: the tests

1. The suite, `tests/app/`, SHALL drive the web code in Chrome without a window against
   an emulator, and SHALL cover both screens and every action: the address, the status,
   the list, `play`, `play all`, `on`, `off`, the brightness, each message and the look.
2. The suite SHALL need no phone, no Android tool and no package beyond what the
   repository's suites need today.
3. A second suite, `tests/apk/`, SHALL check a built APK: its identifier, its
   permissions, plain HTTP allowed, the web code in it byte for byte, and the sender's
   class. It SHALL need the work folder of the tool and no phone.
4. What needs a phone SHALL be a list of numbered steps for the owner, in the app's
   page, and SHALL be in neither suite.

## Requirement 15: the documents

1. `docs/android-app.md` SHALL be the app's page: what the app does, how it is built,
   installed and used, every message, the check on a phone, and what is verified and
   what is open.
2. `docs/emulator.md` SHALL describe `--lan`.
3. `AGENTS.md`, the pages for newcomers and `docs/decisions.md` SHALL say what exists
   after this seed and what is still to come.

## Requirement 16: the owner's check

1. The owner SHALL install the APK on a phone and check every action against an emulator
   on the local network and against the board on its own network, by the steps of the
   app's page.
2. The seed SHALL stay `in_progress` until the owner has done so. What the owner finds
   SHALL be recorded in the app's page.

## Requirement 17: the app in the emulator's page

Added on 2026-10-14. The owner asked for it as a refinement of what was agreed, not as a
seed of its own: the emulator's page is to show the app as well, running the code the
phone runs, so that the app is tried without a phone.

1. The emulator's page SHALL have a third view, `Controller`, beside `LEDs` and
   `Mapping`. It SHALL show the LEDs and, beside them, the operators' app.
2. What runs in that view SHALL be the files of `app/www/` as they are, the files the
   APK holds, served by the emulator. No copy of them SHALL be kept anywhere.
3. The app in that view SHALL be aimed at the emulator that serves it, without an
   address being written.
4. WHILE another view is shown THEN the app SHALL NOT run, and SHALL send nothing.
5. The address of the page with `#controller` at its end SHALL open the view.
6. The emulator's own page SHALL send no command, as before: the lines come from the
   app. Of the repository the emulator SHALL serve its page and `app/www/`, and nothing
   else.

## Requirement 18: commands on the board's second USB socket

Added on 2026-10-14. The owner asked that the board take commands "via serial/usbc/wifi".
The board has two USB sockets: the chip's own, which the firmware has listened on from
the start, and one marked COM, which a bridge chip connects to the chip's UART.

1. The firmware SHALL take command lines on the UART of the socket marked COM, at
   115,200 bits a second, and SHALL write every reply there, as it does on the other
   socket and over HTTP.
2. A line that is arriving one way SHALL NOT be disturbed by a line on another way.
3. The command tool and the firmware tool SHALL work with the board on either socket.
4. No command SHALL be added, and no reply SHALL change.

## Left out on purpose

- Converting, reading media and uploading: seed 17.
- `remove` and `space`: nothing of this part needs them.
- Starting a cycle from the app, and editing a show.
- A limit on the brightness the slider can set. On the bench, where one strip is fed
  from the board's 3.3 V pin, the operator keeps it at 40 or less; the check on a phone
  says so.
- An iPhone app and a PC app.
- The phone talking to the board over a USB cable. The app reaches the board over Wi-Fi;
  the board's USB sockets are for a computer.
