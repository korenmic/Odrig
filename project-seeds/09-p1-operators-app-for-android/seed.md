# Operators' app for Android: command and control

## Summary

An Android app, built with Capacitor, that operators use at the event to see and steer
what the installation plays: it shows what is playing, lists the installed animations by
id and file name, plays one, goes back to the playlist, switches the LEDs on and off, and
sets the brightness. This is the app's first part. Converting a video on the phone and
uploading it is its second part, seed 17.

## Priority

- `P1`

## Depends On

- Seed 07, for the command that lists what is installed.
- Seed 08, for the network the phone joins.
- Seed 16, for the playlist and the command `play all`.

## Product Context

Operators control the installation from their phones. The board hosts the Wi-Fi network
and the phone joins it.

The owner wants an installed app, not a web page served by the board: the board's own
server offers commands only, so that joining the network is not enough to find a control
panel.

The app is one more client of the command list. It can do exactly what the serial and
HTTP commands can do and nothing else. A feature the app needs that no command provides is
first added to the command list, with the owner's approval.

On 2026-10-12 the owner split the app into parts. This part is command and control, and
it comes first: a small app that works and can be installed. It needs no command that
does not exist once seed 16 is done.

A PC version built with Tauri is intended later and is not part of this seed.

## Technical Constraints

- Capacitor, Android only. The app's own code is plain JavaScript, HTML and CSS with no
  build step beyond what Capacitor needs to package it.
- The app talks to its target only with the commands of `docs/commands.md`, over HTTP. It
  adds no command and changes no reply.
- The board's network has no internet access. The app's requests must still go to the
  board, and plain HTTP to the board's address must be allowed.
- The target's address is a setting, with the board's own address as the default, so the
  app can also be pointed at the emulator.
- The emulator listens only on the Mac itself unless started with an option to listen on
  the local network. That option is added here so a phone can reach the emulator.
- Tools needed to build the app install into the project folder. The owner has accepted
  the Android SDK's licence terms, so the build may accept them when it installs the SDK.
- The screen is used outdoors at night: a dark design with large controls.
- What the second part needs is left out: no converter in the package, no reading of
  media, no upload.
- Tests that need a phone are kept apart from those that do not.

## Required Behavior

1. A connection screen shows whether the target answers, and lets the operator change the
   target's address.
2. A main screen shows the status: on or off, the brightness, what is playing, which is
   the playlist or a cycle, the file name of the animation on the LEDs, and the refresh
   rate. It refreshes on its own.
3. A list shows the installed animations, each with its id and its file name, in the
   order of the playlist, with the one on the LEDs marked.
4. The operator can play any animation of the list: the playlist jumps to it.
5. The operator can go back to the playlist from its first animation.
6. The operator can switch the LEDs on and off and set the brightness.
7. Every failure is shown in plain words: the target not answering, and a refused command
   with its error code.
8. The emulator accepts an option to listen on the local network.

## Definition Of Done

1. Tests drive the app's web code in headless Chrome against the emulator and cover every
   screen and every action.
2. A debug APK is built with one documented command.
3. The owner installs the APK on a phone and, against the emulator on the local network
   and against the board on its own network, checks every action, including that requests
   reach the board while the phone has no internet through that network.
4. Building, installing and using the app are documented.

## Open Questions

None. Use the resolved behavior in this seed.
