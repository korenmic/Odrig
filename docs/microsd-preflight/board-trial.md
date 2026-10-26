# First microSD board trial

The owner reported the agreed wiring complete and authorized flashing and testing on
2026-10-22. This trial establishes real card access, but not stable operation.

## Established

- `firmware/fw.py flash --image build/firmware/out/odrig-microsd.bin --wait 60`
  succeeded on `/dev/cu.usbmodem1101`, the native USB serial interface.
- The board has the bigger layout, with 13,500,416 bytes of internal storage. The
  installed mapping and show were preserved: one 60x60 animation at brightness 32.
- The board listed external animation 60001, `01-062cd029337681-5_crop.odrg`,
  22,103 bytes, and 60002, `01-062cd029337681-5_cropfit.odrg`, 129,539 bytes.
  External files are listed only after the core validates their complete contents.
- `play 60001` succeeded. The following status reported animation 60001, brightness
  32, fps 41 and no show error. This is software-reported playback, not an observation
  of LEDs by a person.
- The source folder contains 122 animations, 16,475,328 bytes in total. All 122 have
  not been confirmed on the board.

## Failed stability checks

Already-validated external entries disappear and are gradually discovered again.
This also happens in one persistent `odrigctl.client.Session`, without reopening the
serial port. It is not merely a delay while new files are validated.

Only the SD clock was changed for two controlled diagnostics; the pins, wiring, power,
card contents, LED mapping and installed show were unchanged.

| SD clock | Observation |
|---|---|
| 4 MHz, prepared firmware | Two external files were seen; repeated counts of 2, 0, 1, 2, 0. A monotonic-list assertion failed after an already-listed file disappeared. |
| 1 MHz | Thirteen files validated, matching source names and sizes, before the list fell to zero. The monotonic-list assertion failed at 30.6 seconds of observation. |
| 400 kHz | One validated file disappeared at 5.4 seconds. The same assertion failed. |

Both diagnostic configurations passed all 545 firmware tests. The lower clocks did
not solve the problem and do not prove a hardware cause.

Source review found that either a file-operation error or a failed sector heartbeat
causes a whole-card unmount; the card is retried one second later. The current summary
does not distinguish those triggers. No shared-handle race was established in review.

## Handoff

The temporary clock changes were reverted and the original prepared 4 MHz image rebuilt
with the exact original checksum:

`fd089753d86c92d9cbfbb2e4823d49428e4b037213b656736636b9dd9a1950a5`

The board is being left on that microSD image, with the existing show and brightness 32.
No whole-flash erase, eFuse operation, SD format/write, or hardware/power change was
performed. USB storage is not active in this image.

The next required owner action is to move only the Mac USB cable to the ESP32's other
USB-C socket, leaving the SD wiring unchanged, for the existing UART diagnostic log.
Native USB carries commands but not that log. Stable access to all 122 files, sustained
SD playback and Wi-Fi verification remain open. Local logs and diagnostic artifacts
are under the ignored `build/microsd-*` paths in this worktree.

The [later UART verification](uart-verification.md) on 2026-10-23 confirmed all 122
animations and representative playback with the same firmware in the two-USB bench
setup. This first-trial record remains the account of the earlier failures.
