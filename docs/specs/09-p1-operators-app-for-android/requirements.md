# Requirements: Operators' app for Android (seed 09)

Source seed: `project-seeds/09-p1-operators-app-for-android/seed.md`. It depends on seed 06,
for the converter library the app runs on the phone, on seed 07, for the commands that
list, remove and upload, and on seed 08, for the network the phone joins. None of the three
is implemented while this spec is written: these requirements rely on the repository as
those seeds leave it, and take their designs,
`docs/specs/06-p1-javascript-converter/design.md`,
`docs/specs/07-p1-content-commands/design.md` and
`docs/specs/08-p1-wifi-name-and-password/design.md`, as the description of that state.
Where the code then differs from those designs, the code is what counts.

`docs/commands.md` defines the commands. This seed changes it in one place, which the
owner approved: the reply to `status` gains the canvas size. Where the seed leaves a point
open, the answer used here is recorded in `docs/drifts.md` under "Seed 09".

Terms:

- **the app**: the Android app this seed adds, in the folder `app/`.
- **the web code**: the app's own JavaScript, HTML and CSS, in `app/www/`.
- **the Android project**: the Capacitor project for Android, in `app/android/`.
- **the sender**: the app's one piece of code written for Android, a Capacitor plugin in
  the Android project that sends a command line through the phone's Wi-Fi network.
- **the library**: the converter library of seed 06, `converter/lib/`.
- **the target**: what the app sends commands to: the board or the emulator, by its
  address.
- **the board**, **the firmware**: as in the seed 04 requirements. The board's address on
  its own network is `4.3.2.1`.
- **the emulator**, **the command tool**: as in the seed 03 requirements.
- **the tool**: the program that sets up, builds and serves the app, started as
  `python3 app/app.py`.
- **the work folder**: `build/app/` under the repository root.
- **the web view**: the browser engine inside the app on the phone.
- **Chrome**: the Google Chrome that is installed on the Mac.
- **item**, **animation item**, **cycle**, **id**: as in `docs/show.md`.
- **the canvas**: the width and the height of the installed mapping, in LEDs.
- **picture**: the colours of every canvas pixel, three bytes for each, in the pixel order
  of `docs/format.md`.
- **tick**: one of the moments 20 ms apart at which the converted animation has a picture.
- **the part**: the stretch of a video or GIF that the operator chose to convert, by its
  start and its length.
- **a piece**: the bytes of one `upload data` line.
- **acknowledged**: the number `received` of the newest reply to `upload data`.
- **the suite**: the tests in `tests/app/`, which need no phone.
- **the check on a phone**: the numbered list the owner goes through with a real phone.

## Requirement 1: `status` reports the canvas size

**User Story:** As the developer of the app, I want the installation to tell me its canvas
size, so that the phone converts a video for the canvas that is really there.

### Acceptance Criteria

1. The reply to `status` SHALL have two more members after `error`, in this order:
   `"width":W,"height":H`.
2. W and H SHALL be the width and the height of the canvas of the mapping the core holds,
   in decimal digits.
3. WHILE the core holds no mapping, because `mapping.json` is missing, breaks a rule or
   could not be given memory, both SHALL be `null`.
4. WHILE the show is invalid for a reason other than its mapping, both SHALL still be the
   numbers.
5. Every other member of the reply SHALL keep its place, its name and its value, and every
   other reply of every command SHALL keep its bytes.
6. The reply SHALL be the same over serial and over HTTP, on the emulator and on the
   board, and the reference player of `tests/core/support.py` SHALL give it byte for byte.
7. `docs/commands.md` SHALL show the reply with the two members and describe them in its
   table. Every document that prints a `status` reply SHALL print it with them.
8. The firmware SHALL be built with this core and flashed, and on the board over USB
   `status` SHALL report the canvas of the installed mapping.
9. No command SHALL be added, and no reply other than that of `status` SHALL change.

## Requirement 2: The emulator can listen on the local network

**User Story:** As the owner, I want to point the app on a real phone at the emulator on my
Mac, so that I can try every action before the board is involved.

### Acceptance Criteria

1. Without the option the emulator SHALL listen on 127.0.0.1 only and SHALL print what it
   prints today.
2. WHEN the emulator is started with `--lan` THEN it SHALL listen on the same port on every
   IPv4 address of the Mac.
3. With `--lan` it SHALL print, after the lines `page:` and `serial:`, one more line to
   standard output: `lan: http://<address>:<port>/`, the address being the one the Mac
   has on the network that carries its default route.
4. IF no such address is found THEN that line SHALL be
   `lan: no address found, port <port>` and the emulator SHALL run all the same.
5. With `--lan` it SHALL write one line to standard error:
   `warning: --lan: anyone on the local network can send commands to this emulator and open its page`.
6. `--lan` SHALL belong to real time only: with `--record` it SHALL be a usage error.
7. The emulator SHALL have no other option that names an address, and SHALL not listen
   on the local network for any other reason.
8. The `page:` line and the `page` member of the `hello` event SHALL stay the address on
   127.0.0.1.
9. `docs/emulator.md` SHALL describe the option, the two lines and the warning.

## Requirement 3: The app's place in the repository

**User Story:** As a maintainer, I want the app's own code to be files I can read and
serve as they are, and I want to know which files are ours and which are made.

### Acceptance Criteria

1. The web code SHALL be plain JavaScript modules, HTML and CSS in `app/www/`. A browser
   SHALL run it from those files as they are: nothing is transpiled, bundled or generated.
2. The web code SHALL load the library from the path `lib/` beside its own files, and
   SHALL change no file of the library.
3. No copy of a file of `converter/lib/` SHALL be tracked outside `converter/`. The copy
   in the package SHALL be made by the build, into a folder git ignores.
4. The web code SHALL load nothing from outside its own folder and `lib/`: no script, no
   style sheet, no font and no picture from a network address.
5. The Android project SHALL be tracked as Capacitor creates it, with the changes this
   spec names and no other.
6. The code written for Android SHALL be the sender and the few lines of the activity
   that register it and keep the screen on. Everything an operator sees and does SHALL be
   in the web code.
7. The package SHALL contain no decoder of video or pictures: no file that is not from
   `app/www/`, `converter/lib/`, the build's stamp or Capacitor.
8. The app SHALL be for Android only; a version for PCs is no part of this seed. The
   board SHALL serve no page of the app, and no file of `firmware/` SHALL change for a
   page.

## Requirement 4: The tools install into the project folder

**User Story:** As the owner, I want everything the build needs to land inside the
repository's folder, so that the Mac stays as it is and the setup can be thrown away.

### Acceptance Criteria

1. `python3 app/app.py setup` SHALL install: the Capacitor packages into
   `app/node_modules/`, and a JDK, the Android SDK command-line tools and the SDK packages
   the build needs into the work folder.
2. The versions SHALL be fixed in tracked files: the three Capacitor packages at one exact
   version in `app/package.json` with `app/package-lock.json`, and the JDK and the
   command-line tools with their addresses, sizes and SHA-256 checksums in
   `app/toolchain.json`.
3. A downloaded archive whose size or SHA-256 differs from the tracked one SHALL be
   refused and removed, and nothing of it SHALL be unpacked.
4. The setup SHALL accept the licence `android-sdk-license`, which the owner accepted, when
   the SDK tool asks for it, and SHALL accept no other licence. IF a package asks for
   another licence THEN the setup SHALL fail and say which.
5. The setup SHALL install nothing for the whole computer and SHALL need no administrator
   rights.
6. Every process the tool starts SHALL keep its packages, caches and settings in the work
   folder or in `app/node_modules/`: npm's cache, Gradle's home with the Gradle
   distribution, the Android tools' settings with the debug key, and the settings of
   Capacitor's command line.
7. A step whose result is there SHALL be skipped. A second run of `setup` SHALL download
   nothing.
8. Node.js 22 or later and Python 3.10 or later SHALL be the only programs the tool takes
   from the Mac. IF Node.js is older or missing THEN the tool SHALL say so before it does
   anything else.
9. Git SHALL ignore `app/node_modules/` and everything in the work folder, and SHALL track
   no file a build made.
10. The documentation SHALL state the size of every download that its source documents,
    and the measured size of the work folder after a build.

## Requirement 5: One command builds a debug APK

**User Story:** As the owner, I want one command that gives me the file to install.

### Acceptance Criteria

1. `python3 app/app.py build` SHALL run the setup where it is needed, put the web code
   and the library together in the work folder, hand them to Capacitor, build the debug
   APK and write it to `build/app/odrig-debug.apk`.
2. It SHALL print the path of the APK, its size in bytes and its SHA-256, and exit with
   status 0. A failure SHALL be one line `error: <reason>: <detail>` on standard error
   and status 1.
3. The folder handed to Capacitor SHALL be made anew at every build: the files of
   `app/www/`, the files of `converter/lib/` under `lib/`, and `build.json`, which names
   the commit the build was made from and whether the work tree had changes.
4. A build SHALL change no tracked file.
5. WHEN the setup is complete and Gradle's packages are fetched THEN a build SHALL need no
   network.
6. The APK SHALL be signed with a debug key that the Android tools keep in the work
   folder. The documentation SHALL say that a new work folder means a new key, and that
   the app must then be removed from a phone before the new APK installs.
7. `python3 app/app.py install` SHALL install that APK on the one phone connected by USB,
   with the SDK's own tool. It needs a phone and is no part of a build or of a test.
8. `python3 app/app.py serve` SHALL serve the web code and the library on 127.0.0.1, for
   a browser on the Mac, and SHALL print the address.

## Requirement 6: What the app asks of the phone

**User Story:** As an operator, I want the app to install on my phone and start, and to
tell me plainly when my phone is too old for it.

### Acceptance Criteria

1. The app SHALL install on Android 7.0, API level 24, and later: the lowest level the
   chosen Capacitor supports.
2. The app SHALL need a web view of version 94 or later, the first that has every
   interface the app decodes media with. WHEN the web view is older THEN the app SHALL
   show a page that says so and how to update it, and nothing else.
3. The app SHALL declare three permissions and no other: `INTERNET`,
   `ACCESS_NETWORK_STATE` and `CHANGE_NETWORK_STATE`. It SHALL ask the operator for no
   permission while it runs.
4. The app SHALL allow plain HTTP to any address: the target is an address the operator
   sets, and neither the board nor the emulator speaks HTTPS.
5. WHILE the app is in front the screen SHALL stay on.
6. The app SHALL work with the phone held upright, from a screen 320 CSS pixels wide.
7. The app SHALL keep one thing on the phone: the target's address.
8. The app SHALL NOT join a Wi-Fi network, SHALL NOT hold the network's password, and
   SHALL NOT read the name of the network the phone is on.
9. The app's identifier SHALL be `app.odrig.operators` and its name on the phone `odrig`.

## Requirement 7: Requests reach a network without internet

**User Story:** As an operator at the event, I want the app to reach the board although
its Wi-Fi network has no internet and my phone has mobile data on.

### Acceptance Criteria

1. On the phone every request to the target SHALL be sent by the sender, through the
   phone's Wi-Fi network, whichever network Android uses for everything else.
2. The sender SHALL ask Android for a network by its transport, Wi-Fi, without asking
   that it has internet access, and SHALL open every connection on that network.
3. A request SHALL never travel over mobile data. IF the phone has no Wi-Fi network THEN
   the request SHALL fail at once with the failure `no-wifi`.
4. The web view's own `fetch` SHALL NOT be used for the target on the phone.
5. The sender SHALL do nothing but send: one line to one address, with a time limit, and
   give back the HTTP status and the body. It SHALL look into no line and no reply.
6. The sender SHALL open a new connection for every request and SHALL send a request
   once: no layer below the web code repeats a request by itself.
7. The app SHALL be able to say how its requests travel: whether a Wi-Fi network is
   there, whether Android found internet access on it, and what carries the phone's other
   traffic.
8. In a browser on a computer, where there is no sender, the web code SHALL send the same
   requests with `fetch`.

## Requirement 8: One more client of the command list

**User Story:** As the owner, I want the app to do exactly what the commands can do and
nothing else, so that the command list stays the one interface.

### Acceptance Criteria

1. The app SHALL talk to its target only with `POST http://<address>/odrig`, the command
   line as the body, as `docs/commands.md` defines for HTTP.
2. The app SHALL send only lines of the commands `docs/commands.md` lists: `status`,
   `on`, `off`, `brightness`, `play`, `space`, `list`, `remove` and the four `upload`
   commands. It SHALL request no other path and use no other method.
3. The app SHALL send one request at a time, the next when the one before is answered or
   has timed out.
4. A request SHALL time out after 5,000 ms without its reply.
5. A reply SHALL be taken only when the HTTP status is 200 and the body is one JSON object
   with the member `ok`, `true` or `false`. Anything else SHALL be the failure
   `bad-reply`.
6. The app SHALL keep no state of the installation beyond what replies told it, and SHALL
   show nothing as done before the reply that says so.
7. WHEN several things wait to be sent THEN they SHALL go in this order: what the operator
   just asked for, a `status` that is due, the next line of an upload, and last the
   refresh of the list.

## Requirement 9: The connection screen

**User Story:** As an operator, I want to see whether the installation answers, and to
point the app at another address.

### Acceptance Criteria

1. The address SHALL be `4.3.2.1` until the operator changes it, and a button SHALL set it
   back to that.
2. An address SHALL be a host name or an IPv4 address, with or without `:<port>`, the
   port from 1 to 65,535 and 80 without it. `http://` in front and one `/` at the end
   SHALL be dropped. Anything else SHALL be refused with a message, and the address in use
   SHALL stay.
3. The address SHALL be kept on the phone and used again when the app is started again.
4. The screen SHALL show one of three states: checking, answers, no answer. It SHALL
   follow every request: `answers` when the newest request got a reply, `no answer` with
   the reason in plain words when it did not.
5. WHILE the target answers the screen SHALL show the canvas as `W x H`, or why there is
   none, and the reason of an invalid show.
6. On the phone the screen SHALL show how requests travel, from Requirement 7
   criterion 7, and the version of the web view. It SHALL show the commit of the build.
7. The screen SHALL name the network to join, `odrig`, and say that it is joined in the
   phone's Wi-Fi settings.
8. WHEN the app starts THEN it SHALL show the connection screen until the target has
   answered once, and then the show screen.
9. On every other screen a line SHALL say so while the target does not answer.

## Requirement 10: The show screen and its status

**User Story:** As an operator, I want to see at a glance what the installation is doing,
without pressing anything.

### Acceptance Criteria

1. WHILE the app is in front it SHALL ask for `status` every 1,000 ms, whatever screen is
   shown.
2. The show screen SHALL show: on or off; the brightness, 0 to 255; what is playing, by
   its id and its file name or as a cycle; the animation on the LEDs when a cycle plays;
   the refresh rate; and the reason when the show is invalid.
3. A change another client made SHALL be on the screen within 2 seconds.
4. WHEN a request gets no reply THEN the screen SHALL say within the time limit that the
   target does not answer, and SHALL mark what it still shows as old. WHEN replies come
   again THEN the mark SHALL go by itself.
5. WHILE the app is not in front it SHALL NOT ask for `status`.

## Requirement 11: On, off, brightness and play

**User Story:** As an operator, I want to switch the LEDs, dim them and choose what plays,
with controls I can hit in the dark.

### Acceptance Criteria

1. Two buttons SHALL send `on` and `off`. Which of the two is in effect SHALL be shown from
   the newest `status`.
2. A slider SHALL set the brightness, a whole number from 0 to 255, with `brightness <n>`.
   While it is moved the app SHALL send at most five commands a second, and the value at
   which it is let go SHALL be the last one sent.
3. A `status` reply SHALL NOT move the slider while the operator holds it and for 1,000 ms
   after the last brightness command.
4. Every item of the list SHALL have a play button that sends `play <id>`. The item that
   plays SHALL be marked.
5. After the reply to each of these commands the app SHALL ask for `status` at once.
6. A command that is refused SHALL be shown with its message, and nothing SHALL be shown
   as changed.
7. These controls SHALL work while the app converts and while it uploads.

## Requirement 12: The items, their sizes and the free storage

**User Story:** As an operator, I want to see what is installed and how much room is left
before I add something.

### Acceptance Criteria

1. The items screen SHALL list every item in the order of the show: an animation item
   with its id, its file name and the size of its file; a cycle with its id, the ids of
   its animations and its seconds.
2. The app SHALL read the whole list: `list`, then `list <next>` for as long as `next` is
   not `null`. Every item SHALL appear once. IF a `next` is not above the position asked
   for THEN the reading SHALL stop as `bad-reply`.
3. The screen SHALL show the free and the total storage and the number of animations, from
   `space`.
4. A size SHALL be written in bytes below 1,000, in kB with one decimal below 1,000,000,
   and in MB with one decimal from there on, 1 kB being 1,000 bytes.
5. The list and the storage SHALL be read when the show screen or the items screen is
   opened, after every change the app made, every 5,000 ms while one of the two is in
   front, and when `status` names an id the list does not have.
6. WHILE the show is invalid the screen SHALL show the reason in place of the items, and
   the storage all the same.
7. A cycle that the target lists with `"cycle":[]` SHALL be shown as a cycle too long to
   list.

## Requirement 13: Removing an item, after confirming

**User Story:** As an operator, I want to delete an animation, and not by a slip of the
finger.

### Acceptance Criteria

1. Every item of the items screen SHALL have a remove button.
2. Pressing it SHALL open a question that names the item by its id and its file name, or
   as a cycle, and says what follows: that an animation's file is deleted, that a cycle's
   animations stay, and, when the item is the one playing, that the LEDs go dark.
3. `remove <id>` SHALL be sent only when the operator confirms. Declining SHALL send
   nothing and change nothing.
4. After `{"ok":true}` the list and the storage SHALL be read again.
5. A refusal SHALL be shown with its message: an animation that a cycle lists, an upload
   that is open, an id that is gone, an invalid show, storage that cannot be written.
6. WHILE the app's own upload runs the remove buttons SHALL be out of use.

## Requirement 14: Picking a video or GIF and reading it

**User Story:** As an operator, I want to take a video or GIF from my phone and have the
app read it with what the phone has, at the exact times of its frames.

### Acceptance Criteria

1. A button SHALL open the phone's own file chooser for videos and GIF files. The app
   SHALL need no permission for it.
2. The kind of a file SHALL be told from its content: a GIF by its first six bytes, a
   video by the boxes of an MP4 or QuickTime file. Any other file SHALL be refused as
   `not-media`.
3. The pictures of a GIF SHALL come from the web view's `ImageDecoder`: each frame as it
   is on screen, the whole logical screen with every earlier frame applied.
4. The delays of a GIF SHALL be read from the file's own blocks, in whole hundredths of a
   second as the file records them, and given to the library in milliseconds.
5. The frames of a video SHALL come from the web view's `VideoDecoder`. The app SHALL
   read the file's table of samples itself and give the decoder the samples.
6. The app SHALL read a video that is an MP4 or QuickTime file, not fragmented, whose
   first video track is H.264 or HEVC, when the web view says it can decode it. It SHALL
   refuse: a fragmented file as `fragmented`; a file without a video track as `no-video`;
   another codec, or one the web view cannot decode, as `codec-unsupported` with the
   codec's name.
7. The presentation time of every frame SHALL be taken from the file as a whole number of
   units of the track's time scale and given to the library as an exact fraction. No time
   SHALL pass through a floating-point number.
8. A rotation of 90, 180 or 270 degrees that the file records SHALL be applied, so that
   the picture is upright as the phone shows it.
9. A frame of more than 1,048,576 pixels SHALL be drawn at 1/k of its width and height
   before the library fits it, k being the smallest whole number that brings it to
   1,048,576 pixels or fewer.
10. A video SHALL never be read whole: the app SHALL read its index and the samples it
    decodes, so a video of any size is read. A GIF SHALL be handed to the web view as a
    stream, and a GIF of more than 67,108,864 bytes SHALL be refused as `gif-too-large`:
    the web view holds a GIF whole while it decodes it.
11. Only the part SHALL be decoded: decoding SHALL begin at the last sync sample that is
    not after the frame on screen at the start of the part, and SHALL end when the library
    asks for no more frames.
12. At most 8 samples SHALL wait in the decoder and at most 4 decoded frames SHALL be
    held. A frame SHALL be released as soon as its pixels are read.
13. After a file is read the screen SHALL show its name, its kind, the size of its
    picture, its length in seconds and its number of frames.

## Requirement 15: Converting with the library

**User Story:** As an operator, I want the phone to convert my file the way the converter
on a computer does, and to stay usable while it works.

### Acceptance Criteria

1. The app SHALL convert with the library as it is: `importFrames` builds the pictures of
   the ticks and `encode` writes the ODRG file. The web code SHALL NOT choose the picture
   of a tick, fit a picture or write a byte of the format itself, and SHALL take the
   length of a file from the library's own rules for frame times.
2. The canvas SHALL be the `width` and `height` of the newest `status`. WHILE they are
   `null` the app SHALL NOT convert and SHALL say why. IF the reply has no such members
   THEN the app SHALL say that the installation's software is older than the app.
3. The operator SHALL choose how the picture fits: `fill`, which is chosen at first,
   `fit` or `stretch`, as the library defines them.
4. The operator SHALL choose the part: a start and a length in whole milliseconds. The
   start is 0 at first and the length the whole file, or 30 seconds when the file is
   longer.
5. A part SHALL be at least 20 ms and at most 120 seconds, SHALL lie inside the file, and
   SHALL have pictures of at most 134,217,728 bytes in all. The controls SHALL not let a
   part outside these limits be chosen.
6. The result SHALL be a compressed ODRG file, or an uncompressed one when the operator
   chooses so.
7. For the GIFs of the suite the file SHALL decode to exactly the frames that
   `node converter/odrig.js import` gives for the same file, canvas, fit and part.
8. For the H.264 video of the suite the file SHALL have the number of frames and the
   durations that `node converter/odrig.js import` gives, and every picture SHALL be the
   colour of the source frame that is on screen at its tick.
9. The conversion SHALL run apart from the page, so that the page answers the operator
   throughout. The screen SHALL show how much of the part is done.
10. A cancel button SHALL end a conversion at once and free what it held.
11. A file that cannot be converted SHALL be refused with its message, and the screen
    SHALL be as it was before the conversion.
12. IF the web view runs out of memory during a conversion THEN the app SHALL say that
    the part is too long for this phone, and SHALL keep running.

## Requirement 16: The preview

**User Story:** As an operator, I want to see what the LEDs will show before I send
anything.

### Acceptance Criteria

1. WHEN a file is read, and after every change of the fit or of the start, the screen
   SHALL show the picture of the first tick of the part.
2. WHEN a conversion is done THEN the screen SHALL play the result in a loop, one picture
   every 20 ms.
3. The preview SHALL be drawn on a canvas element: one dot for each LED, W dots wide and H
   high, (1,1) at the bottom-left, on black, as wide as the screen allows. The colours
   SHALL be those of the file; brightness is not applied.
4. The pictures of the preview SHALL be the pictures of the file that is uploaded.
5. Beside the preview the screen SHALL show the length of the result, its number of
   ticks, the size of the file, and the free storage, and SHALL say so when the file does
   not fit.

## Requirement 17: Uploading with a percentage and a speed

**User Story:** As an operator, I want to send the animation to the installation and
watch it arrive.

### Acceptance Criteria

1. The operator SHALL choose between a new item, which is chosen at first, and the place
   of an animation item of the list.
2. For a new item the id SHALL be the smallest from 1 on that the list, read anew, does
   not have. The file name SHALL be made from the name of the picked file without its
   ending: lower case, every character outside `a`-`z`, `0`-`9`, `-` and `_` made `-`,
   `clip` when nothing is left, at most 32 characters with `.odrg` at the end, and
   changed by a number at its end until no item has it.
3. In the place of an item the id SHALL be that item's and the file name that item's.
4. The operator MAY change the file name. A name outside the rule of `docs/show.md` SHALL
   be refused before anything is sent.
5. Before `upload begin` the app SHALL ask for `space`. IF
   `bytes + bytes div 256 + 16,384` is above the free bytes THEN it SHALL say that the
   file does not fit and send nothing more.
6. The app SHALL send `upload begin <id> <file> <bytes>`, then the file in pieces, each as
   one `upload data <offset> <base64>` line, in order, the next when the one before is
   acknowledged, and then `upload end <crc32>`.
7. A piece SHALL have the number of bytes the reply to `upload begin` names as `chunk`,
   and never more than 1,500; the last piece has what is left.
8. The base64 and the CRC-32 SHALL have the form of `docs/commands.md`: the alphabet with
   `-` and `_` and no `=`; eight hexadecimal digits in lower case, which for the nine
   bytes `123456789` are `cbf43926`.
9. WHILE the reply to `upload end` is `busy` the app SHALL say that the installation is
   checking the file and SHALL send `upload end` again every 200 ms, for at most 600
   seconds.
10. During the upload the screen SHALL show the percentage sent, which is
    `acknowledged * 100 div bytes`, the acknowledged and the total bytes, and the speed.
11. The speed SHALL be the bytes acknowledged in the last 5 seconds divided by that time,
    and from `upload begin` on while the upload is younger than that. It SHALL be written
    in kB a second with one decimal and renewed at least once a second.
12. WHEN `upload end` succeeds THEN the screen SHALL say so with the id and the name,
    SHALL read the list and the storage again, and SHALL offer to play the item.
13. The file in the target's folder SHALL be the converted file, byte for byte.

## Requirement 18: An upload that meets trouble

**User Story:** As an operator on a crowded Wi-Fi channel, I want a lost reply not to cost
me the upload, and a cancelled upload to leave nothing behind.

### Acceptance Criteria

1. WHEN a line of an upload gets no reply in time THEN the app SHALL send the same line
   again, up to four more times, 1,000 ms after each failure.
2. WHEN a piece is answered with `bad-offset` THEN the app SHALL send the next piece. IF
   that one is acknowledged THEN the piece before had arrived and the upload goes on. IF
   it is refused too THEN the upload is out of step and SHALL end as failed. After the
   last piece `upload end` decides in the same way.
3. WHEN `upload begin` is answered with `busy` THEN the app SHALL NOT clear the open
   upload by itself. It SHALL say that an upload is open and offer to clear it, and SHALL
   send `upload cancel` for it only when the operator confirms.
4. WHEN an `upload end` that was sent again is answered with `no-upload` THEN the app
   SHALL read the list: with an item of that id, name and size the upload succeeded;
   without it, it failed.
5. A cancel button SHALL be there while pieces are sent and while the file is checked.
   WHEN it is pressed THEN the app SHALL send `upload cancel` as soon as the request in
   flight has ended, and the converted file SHALL stay ready to be uploaded again.
6. WHEN an upload the app opened fails and may still be open THEN the app SHALL send
   `upload cancel`. It SHALL NOT send it after `no-upload`, `bad-checksum`, `bad-file` and
   `storage-error`, which leave no upload open.
7. After a cancel and after a failure with a reachable target, the target SHALL have no
   open upload and no file of it: the next `upload begin` SHALL succeed.
8. IF the target answers none of the repeated lines THEN the app SHALL say that it does
   not answer, SHALL send `upload cancel` once without waiting for its reply, and SHALL
   otherwise leave the upload to the target, which gives it up after 60 seconds.
9. Every failure of an upload SHALL leave the converted file and the screen ready for
   another try.

## Requirement 19: Every failure in plain words

**User Story:** As an operator, I want to be told what went wrong and what to do, in words
and not only in a code.

### Acceptance Criteria

1. Every error code of `docs/commands.md` SHALL have a text of its own in the app, and a
   code that can come from several commands SHALL have a text for each of them where the
   meaning differs.
2. Every failure to reach the target SHALL have a text: no Wi-Fi network, no answer,
   something else answering at the address, an installation older than the app, an
   address that is no address.
3. Every refusal of a file SHALL have a text: not a video or GIF, a fragmented video, no
   video in the file, a codec the phone cannot decode, a decoding that failed, a GIF that
   is too large, a part too long for the phone's memory, and each reason the library can
   give for an import or an encoding.
4. A text SHALL say what happened and, where there is something to do, what to do. It
   SHALL end with the code or the reason in brackets.
5. A `bad-file` SHALL be shown with its `reason`, and a `show-invalid` with the reason
   `status` gives.
6. A message SHALL stay on the screen until the operator dismisses it or another message
   takes its place. No message SHALL go away by itself.
7. A failure SHALL never be silent, and SHALL never leave the app waiting without a way
   on.
8. The texts SHALL be in one file, in English.

## Requirement 20: Made for outdoors at night

**User Story:** As an operator standing in the desert in the dark, I want a screen that
does not blind me and controls I cannot miss.

### Acceptance Criteria

1. The background of every screen SHALL be black, `#000000`. No screen SHALL have a light
   surface larger than a control, apart from the preview's own colours.
2. Text SHALL have a contrast of at least 7 to 1 against its background, and SHALL be at
   least 18 CSS pixels high.
3. Everything the operator presses SHALL be at least 56 CSS pixels high and 56 wide, and
   at least 8 CSS pixels from the next thing to press.
4. Nothing SHALL be reachable only by a long press, a swipe or a second finger.
5. No screen SHALL scroll sideways at a width of 320 CSS pixels or more.
6. The state of the installation, on or off and what plays, SHALL be readable at arm's
   length: at least 28 CSS pixels high.
7. The four screens SHALL be reached by four buttons that are always on the screen.
8. The system's back gesture SHALL go to the screen shown before. WHILE a conversion or
   an upload runs it SHALL NOT leave the app.

## Requirement 21: Tests that need no phone

**User Story:** As a maintainer, I want one command that drives the app's real web code in
a real browser engine against the real command front-end.

### Acceptance Criteria

1. `.venv/bin/python -m unittest discover -s tests/app -t .` SHALL run the whole suite
   and SHALL pass on the Mac.
2. The suite SHALL load the web code from `app/www/` and the library from
   `converter/lib/`, as they are, in Chrome without a window, and SHALL point the app at
   an emulator it starts on a folder of its own.
3. The suite SHALL work the app through its page as an operator does: it presses the
   page's buttons, fills its fields and gives its file chooser a file.
4. The suite SHALL cover every screen and every action: the address and each of its
   refusals; the three states of the connection; the status and its refreshing by itself;
   on, off, brightness and play; the list across more than one reply, the sizes and the
   storage; removing, declined and confirmed, and each refusal; picking, each fit, a part,
   both previews; converting a GIF and an H.264 mp4, each uploaded, found in `list`, and
   played; an upload in the place of an item; a cancelled upload; a lost reply to each of
   the three upload lines; `busy` waited out; a file that does not fit; and the message
   of every error code and of every other failure.
5. The suite SHALL build its media while it runs, with the fixtures of the Python suite:
   GIFs, and mp4 files encoded as H.264, which Chrome decodes. It SHALL track no media
   file.
6. In Chrome a GIF's frames SHALL be decoded by `ImageDecoder` and a video's by
   `VideoDecoder`, the same interfaces as on the phone.
7. The suite SHALL compare what the app's readers find in a file, the times, the sizes,
   the sync samples and the delays, with what PyAV and Pillow find in it.
8. The suite SHALL check the look where a program can: the sizes of the controls, the
   contrast of the text, the black background and no sideways scrolling, at a window of
   360 by 740 CSS pixels.
9. The suite SHALL use the Chrome that is installed, with a profile folder of its own in
   a temporary folder, SHALL install nothing, and SHALL need no network beyond the
   loopback address. WHEN no Chrome is found THEN the tests that need it SHALL be reported
   as skipped with the place it looked; on the Mac of this project they SHALL run.
10. The suite SHALL need no phone, no Android tool, no JDK and no package of
    `app/node_modules/`.
11. The suites that exist SHALL still pass:
    `.venv/bin/python -m unittest discover -s tests/converter -t .`, `make -C core test`,
    `python3 -m unittest discover -s tests/emulator -t .`, `python3 firmware/fw.py test`
    and `npm test --prefix converter`.
12. Each suite SHALL be selected by discovery. No command, script or document SHALL list
    test files.

## Requirement 22: Checks of the package, and checks that need a phone, kept apart

**User Story:** As a maintainer, I want to know which checks I can run at my desk and
which need a phone in my hand.

### Acceptance Criteria

1. `python3 -m unittest discover -s tests/apk -t .` SHALL check a built APK without a
   phone: its permissions, that plain HTTP is allowed, its lowest Android version, its
   identifier, that it holds every file of `app/www/` and of `converter/lib/` with their
   bytes, and that it holds nothing Requirement 3 criterion 7 excludes.
2. That suite SHALL need the APK and the SDK in the work folder. WHEN they are not there
   THEN it SHALL fail with the command that makes them.
3. No test of `tests/app/` and none of `tests/apk/` SHALL need a phone.
4. What needs a phone SHALL be a numbered list in `docs/android-app.md`, each step with
   what must be seen, and SHALL be no program.
5. The tests of the tool in `tests/app/` SHALL download nothing: they give the tool
   archives and an address of their own.

## Requirement 23: Documentation

**User Story:** As an operator or a newcomer, I want one page that tells me how to build
the app, put it on a phone and use it.

### Acceptance Criteria

1. `docs/android-app.md` SHALL become the app's page: what the app is and is not; what
   the build needs and what it installs where, with the versions, the sources and the
   sizes; the one command; installing the APK, by USB and by copying the file; the four
   screens; converting, with the files it reads and its limits; every message; the
   emulator on the local network; the tests; the check on a phone; and what is verified.
2. The page SHALL say what an operator does with the phone's Wi-Fi: join `odrig`, and
   what to answer when the phone says the network has no internet or asks to sign in.
3. The page SHALL say where the app differs from the converter on a computer: a rotation
   is applied, and a large frame is made smaller first.
4. `docs/commands.md` SHALL have the `status` reply of Requirement 1.
5. `docs/emulator.md` SHALL have `--lan`.
6. `docs/decisions.md` SHALL state the app as it is, with a line in its change log, and
   `README.md` SHALL name the page for what it now is.
7. The documents and the code SHALL change in the same commits.
8. What was read and not tried SHALL be given as read.

## Requirement 24: Accepted on a phone

**User Story:** As the owner, I want every action checked on a real phone, against the
emulator and against the board, and to know which a person checked.

### Acceptance Criteria

1. The owner SHALL install the APK on a phone.
2. With the emulator started with `--lan` and the phone on the Mac's network, the owner
   SHALL do every action: set the address, see the status follow, switch on and off, set
   the brightness, play each item, read the list and the storage, pick a GIF and a video
   the phone recorded, choose each fit and a part, see both previews, convert, upload with
   its percentage and speed, cancel an upload, play the new item, and remove it after
   confirming.
3. With the phone joined to `odrig`, mobile data on, and the address `4.3.2.1`, the owner
   SHALL do every action again on the board, with a brightness of 40 or less.
4. In that state the phone SHALL reach a page on the internet with its browser while the
   app's requests reach the board.
5. The owner SHALL note the phone, its Android version and its web view version, what the
   phone said about the network and what was answered, the speed of an upload to the
   board, and the time a conversion took.
6. The seed SHALL be completed only when the owner's check is done.
