# Tasks

Each task is one proof commit with only its own checkbox ticked. A test for a fault is
seen failing first.

- [x] 1. Give the Target screen one Wi-Fi control and the link switch
  - The switch kept on the phone, `Connect over Wi-Fi` in place of `Use` and `Board`, the
    USB block, `USB serial` disabled in a browser; app tests and `docs/android-app.md`.
  - Requirements: 1.1–1.6.

- [x] 2. Send the app's lines over USB serial
  - `target.js`: the link, `replyIn`, the serial sending with draining and the limit, the
    new failure kinds and their messages; the stand-in sender scenario and its tests.
  - Requirements: 2.1–2.5.

- [x] 3. Give the APK's sender the board's USB serial port
  - `TargetPlugin`'s `usb`, `connect`, `write` and `read`, the detach, the manifest's
    feature and filter and `usb_device.xml`; the Android checks; `docs/commands.md`.
  - Requirements: 3.1–3.4, 4.1–4.2.

- [x] 4. Build and deliver the APK
  - Built from the pushed head and signed; the Drive; `verification.md`.
  - Requirements: 4.3.
