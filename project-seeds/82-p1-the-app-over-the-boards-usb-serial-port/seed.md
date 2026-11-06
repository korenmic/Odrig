# The app over the board's USB serial port

## Summary

Let the Android app reach the installation through the board's USB serial port, with a
cable from the phone, as fully as it reaches it over Wi-Fi: every command the app sends
over Wi-Fi is sent over serial, with the same replies, so that every screen and every job
of the app works on either link. The Target screen gets one Wi-Fi connection control in
place of the two buttons `Use` and `Board`, which do the same thing, and a switch between
`Wi-Fi` and `USB serial`.

## Priority

`P1`.

## Product Context

The owner asked on 2026-11-06 whether the phone could give the full interface through the
board's USB serial COM port, and then asked for this seed: "the final interface in the app
after the seed would have been implemented would be a switch, allowing me to decide if I
want to do the connection through serial or through Wi-Fi", and "I want the full
capabilities of Wi-Fi in the serial as well. Any command that exists over Wi-Fi should also
exist over serial." The owner already connects the phone to the board by USB to install
firmware, so the cable and the port are in use today.

Today the app talks to the board only over HTTP, `POST /odrig` on `4.3.2.1`, through
`app/www/target.js`, the only file that knows how a line travels, and the APK's native
`TargetPlugin`. The board's firmware already takes the same command lines on its USB serial
port, with the same replies, as `docs/commands.md`, "Transports", says, and writes its log
there as lines beginning with `#` between replies, which a client passes over. `odrigctl`
uses that port from a computer and opens it without resetting the chip: the modem lines are
lowered RTS first, DTR second, since DTR low while RTS is high resets it.

The Target screen has an address field and two buttons: `Use`, which takes the typed
address, and `Board`, which takes `4.3.2.1`. Both connect over Wi-Fi to an address.

## Required Behavior

1. **One Wi-Fi control.** The Target screen keeps the address field, filled with
   `4.3.2.1` when nothing else was kept, and one button, `Connect over Wi-Fi`, that takes
   the address in the field. `Use` and `Board` go. A kept address stays kept, and a field
   emptied by the operator is filled with `4.3.2.1` again before the button takes it.
2. **The switch.** Above it, a switch of two choices, `Wi-Fi` and `USB serial`, kept on the
   phone across restarts, `Wi-Fi` until the operator chooses otherwise. With `USB serial`
   the address field and the Wi-Fi button are hidden, and the screen says which USB device
   is used, or that none is connected, with `Connect over USB`.
3. **The whole app on serial.** On `USB serial` every line the app sends today over HTTP is
   sent over the serial port and its reply taken from it: status, lists, catalogs and their
   pages, reads, uploads with their pieces, `ignore`, `order`, brightness, repeats, clocks,
   mapping, removals, and every command later seeds add through `target.js`. Every screen and
   every job of the app, Animations, Upload, Settings and Target, works as on Wi-Fi. No
   command, reply or firmware change is made; the replies are those of `docs/commands.md`.
4. **One line at a time.** The app sends one line and waits for its reply before the next,
   as on HTTP. A line that begins with `#`, and any line that is not a JSON object with
   `ok`, is passed over; the board's log does not end a wait. A reply that does not come
   within the wait HTTP has is a lost reply, handled as today.
5. **Opening the port without a reset.** The port is opened at 115,200 baud, 8 data bits,
   no parity, one stop bit, with RTS lowered first and DTR second, as `odrigctl` does; the
   app never makes the pair that resets the chip, and never enters its loader.
6. **The phone's permission.** The app asks Android for the permission to use the USB
   device, once per device as Android keeps it, and says plainly when it was refused. The
   board is found by the vendor and product ids of the ESP32-S3's USB serial port,
   `303a:1001`; another USB device is not used. A device unplugged ends the link as a lost
   link does today: the screen says `Not connected`, the jobs that wait for a link wait,
   and plugging it in again and pressing `Connect over USB` reconnects.
7. **One link at a time.** The app uses one link at a time. Switching from one to the other
   is a change of target as today: what is under way for the old one ends, and the new one
   is read from the beginning.
8. **The emulator's page.** The Controller in a browser has no USB serial port: it shows the
   switch with `USB serial` disabled and the reason, and works over HTTP as today.
9. **What stays on Wi-Fi.** Installing firmware stays with the existing ways, since it is no
   command line but the chip's loader. Everything the app does with command lines is on
   both links.

## Technical Constraints

- The line transport is added beside the HTTP one in `app/www/target.js`, which stays the
  only file of the web app that knows how a line travels. The rest of the app is unchanged
  by the link, so that a command added later works on both.
- The APK gets the USB side natively, in `TargetPlugin` or a plugin beside it, with
  Android's own USB host API (`UsbManager`, the CDC-ACM data interface and its two bulk
  endpoints, and the control request that sets the line); no third-party library is added.
- No firmware, core, command or reply change; no change of wiring or power; the board's USB
  port is the one `odrigctl` uses. The installation's board and the spare both have it.
- Tests: the line transport against the emulator's TCP lines, which carry the same lines as
  a serial port, including log lines between replies, a lost reply, a long upload and a
  change of link; the native USB side by unit tests of the line framing and the modem line
  order; the Target screen's controls by the app suite.
- Documents: `docs/android-app.md` describes the switch and the USB link, and the owner's
  phone check of it; `docs/commands.md`, "Transports", names the app among the clients of
  the serial port.

## Open Questions

None. The owner asked for the switch, the single Wi-Fi control and the whole interface over
serial; the cable and the port are those the owner already uses with the phone. The choices
the seed makes without the owner are routine: the button's words, the switch's default, the
device ids, and that firmware installation stays where it is.

## Definition Of Done

1. A requirements/design/tasks specification of the switch, the Wi-Fi control, the line
   transport and the native USB side.
2. The APK connects over USB serial and every screen and job works on it as on Wi-Fi; the
   emulator's page shows the switch with USB serial disabled.
3. The app, APK and emulator suites cover the transport, its log lines and lost replies,
   the switch and the Wi-Fi control.
4. The owner's check on the phone with the cable: connect over USB, play, upload, change
   settings, switch back to Wi-Fi.
