# Operators' app for Android

## Summary

An Android app, built with Capacitor, that operators use at the event: it shows what the
installation is doing, plays items, switches the LEDs on and off, sets brightness, lists and
removes installed animations, and converts a video or GIF on the phone and uploads it with a
progress bar.

## Priority

- `P1`

## Depends On

- Seed 06, for the JavaScript converter the app runs on the phone.
- Seed 07, for the commands that list, remove and upload.
- Seed 08, for the network the phone joins.

## Product Context

Operators control the installation from their phones. The board hosts the Wi-Fi network and
the phone joins it.

The owner wants an installed app, not a web page served by the board: the board's own server
offers commands only, so that joining the network is not enough to find a control panel.

The app is one more client of the command list. It can do exactly what the serial and HTTP
commands can do and nothing else. A feature the app needs that no command provides is first
added to the command list, with the owner's approval.

Converting media is heavy work and belongs on the phone. The app converts with the same
converter that runs on PCs.

A PC version built with Tauri is intended later and is not part of this seed.

## Technical Constraints

- Capacitor, Android only. The app's own code is plain JavaScript, HTML and CSS with no
  build step beyond what Capacitor needs to package it.
- The app talks to its target only with the commands of `docs/commands.md`, over HTTP.
- The converter library from seed 06 is used as it is. Any copy placed in the app's package
  is made by the build, not kept in the repository.
- Video and GIF files are decoded with what the phone's web view provides. No decoder is
  bundled.
- The board's network has no internet access. The app's requests must still go to the board,
  and plain HTTP to the board's address must be allowed.
- The target's address is a setting, with the board's own address as the default, so the app
  can also be pointed at the emulator.
- The emulator listens only on the Mac itself unless started with an option to listen on the
  local network. That option is added here so a phone can reach the emulator.
- Tools needed to build the app install into the project folder. The owner has accepted the
  Android SDK's licence terms, so the build may accept them when it installs the SDK.
- The screen is used outdoors at night: a dark design with large controls.
- Tests that need a phone are kept apart from those that do not.

## Required Behavior

1. A connection screen shows whether the target answers, and lets the operator change the
   target's address.
2. A main screen shows the status: on or off, brightness, what is playing, and the refresh
   rate. It refreshes on its own.
3. The operator can switch the LEDs on and off, set brightness, and play any installed item.
4. A list shows the installed items with their sizes, and the free storage.
5. The operator can remove an animation, after confirming.
6. The operator can pick a video or GIF from the phone, choose how it fits the canvas and
   which part to use, see a preview of the result on a drawn canvas, and upload it. The
   upload shows the percentage sent and the speed, and can be cancelled.
7. Every failure is shown in plain words: the target not answering, a refused command with
   its error code, a file that cannot be converted, not enough space.
8. The emulator accepts an option to listen on the local network.

## Definition Of Done

1. Tests drive the app's web code in headless Chrome against the emulator and cover every
   screen and action, including converting and uploading the test GIF and the test mp4 and
   then playing them.
2. A debug APK is built with one documented command.
3. The owner installs the APK on a phone and, against the emulator on the local network and
   against the board on its own network, checks every action, including that requests reach
   the board while the phone has no internet through that network.
4. Building, installing and using the app are documented.

## Open Questions

None. Use the resolved behavior in this seed.
