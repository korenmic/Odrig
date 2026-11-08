# Requirements

Seed 82, `project-seeds/82-p1-the-app-over-the-boards-usb-serial-port/seed.md`. The shared
app's web code, the APK's native code and manifest, the app's tests and documents. No
command, reply, core, firmware, wiring or power change.

## 1. The Target screen

1.1 The screen has a switch of two choices, `Wi-Fi` and `USB serial`, kept on the phone
across restarts, `Wi-Fi` until the operator chooses otherwise.
1.2 With `Wi-Fi`: the address field, filled with the kept address or `4.3.2.1`, and one
button, `Connect over Wi-Fi`, which takes the address in the field; a field the operator
emptied is filled with `4.3.2.1` again before the button takes it. The buttons `Use` and
`Board` are gone.
1.3 With `USB serial`: the address field and the Wi-Fi button are hidden; a line says
whether a board is connected by USB, and `Connect over USB` connects to it.
1.4 Choosing the other link is a change of target: what is under way for the old link ends,
and the new one is read from the beginning.
1.5 In a browser, the Controller of the emulator among them, `USB serial` is disabled with
the reason, `This browser has no USB serial port; the Android app has.`, and `Wi-Fi` is used.
1.6 The line of how requests travel says `Sent over USB serial.` on that link.

## 2. The lines over USB serial

2.1 On `USB serial` every line the app sends goes over the serial port, one at a time, and
its reply is taken from the port: every screen and job works as on Wi-Fi, since the rest of
the app sends its lines through `target.js` alone.
2.2 A reply is the first whole line after the line was sent that is a JSON object with a
boolean `ok`; a line that begins with `#`, and any other line, is passed over.
2.3 Before a line is sent, what the port holds already is read and dropped, so that a late
reply of an earlier line, or the log, is never taken for the reply.
2.4 A reply that does not come within the same limit as on Wi-Fi is a lost reply,
`no-answer`, handled as today.
2.5 Without a device the line fails with `no-usb`; when Android's permission was refused,
with `usb-refused`. Each has a message that says what to do.

## 3. The APK's USB side

3.1 The sender finds the board by the ids of the ESP32-S3's USB serial port, `303a:1001`,
asks Android for the permission to use it, opens its CDC data interface, sets 115,200 baud,
8 data bits, no parity and one stop bit, and lowers both modem lines at once, so that the
pair that resets the chip, DTR low while RTS is high, is never made.
3.2 It writes the bytes it is given and gives back the bytes that arrive, waiting at most
the time it is given; it looks into no line.
3.3 A device unplugged closes the link: the next line fails with `no-usb`, and `Connect over
USB` connects again.
3.4 The manifest says the app may use USB host where the phone has it, without requiring
it, and offers the app when the board is plugged in.

## 4. Documents and checks

4.1 `docs/android-app.md` describes the switch, the USB link and the owner's check of it;
`docs/commands.md`, "Transports", names the app among the clients of the board's serial port.
4.2 The app suite checks the screen, the line transport through a stand-in of the sender
with log lines, replies in pieces, a lost reply, a missing device and a change of link; the
Android checks name the new methods and the modem line request.
4.3 The APK is built and delivered; the owner's check with the cable stays open.
