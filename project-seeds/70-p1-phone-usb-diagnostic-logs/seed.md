# Phone USB diagnostic logs

## Summary

Capture and share the board's serial diagnostics from the Android app over USB OTG,
including when its Wi-Fi is unavailable. The operator has only a phone and flasher.

## Product Context

A successfully written firmware image does not establish why a board cannot boot or
host Wi-Fi. The app currently has no way to collect serial evidence. Its Target screen
should offer an explicit diagnostic capture that does not require working firmware Wi-Fi.

## Required Behavior

1. On Android, enumerate supported USB serial devices and ports and let the operator
   select one and start capture with the system's USB permission prompt. Work offline.
2. Read at 115200, 8N1, without an automatic reset/bootloader sequence or flash writes.
   Deassert RTS before DTR, matching the existing non-resetting command tools.
3. Keep a bounded log, show the arriving text and capture state, and allow sharing a
   UTF-8 text file through Android. Preserve the captured log after stop or disconnect.
4. An explicit diagnostic button sends only the existing `status` and `fault` commands.
   Merely starting capture sends no commands. No terminal, flashing or recovery controls.
5. Handle absent hardware, unsupported devices, denied permission, occupied ports,
   unplugging, backgrounding and capture limits without changing Wi-Fi operation.
6. Explain that COM/UART is needed for the full firmware log and that native USB may
   disappear during a crash. Silence is not proof that the board is healthy.

## Technical Constraints

Use a pinned Android USB serial driver, one active capture and bounded memory.
All USB I/O runs off the UI thread. The browser shares the same UI code and clearly
says that physical USB capture needs the Android app. No firmware change is required.
The already reported board incident remains unconfirmed until real logs are obtained.

## Open Questions

None. The owner authorized phone USB log extraction; no board command is added and no
hardware, power or WLED configuration is changed. Physical phone/board verification is open.

## Definition Of Done

Host tests, native compilation and Android VM checks pass; the implementation is pushed
for review and the same-signer APK replaces the usual Drive file with byte verification.
The operator can then capture/share real evidence. Physical acceptance is reported honestly.
