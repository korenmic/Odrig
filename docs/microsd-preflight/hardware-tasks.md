# microSD hardware verification

Task source: the owner's request to flash the prepared firmware and confirm the card
and animations, continued after connecting both board USB-C sockets to the Mac.

- [x] Verify all card animations and combined-playlist operation through the UART.
  All 122 external names and sizes match the source, plus one internal item. Four
  representative SD animations played across loop boundaries without losing entries,
  at 26–50 refreshes per second. The restored playlist advanced onto SD storage without
  another play command. See [the verification record](uart-verification.md).

This completes identification and representative playback in the current two-USB bench
configuration. It does not establish the earlier dropout's cause, autonomous power
behavior, Wi-Fi operation or the owner's visual checks.
