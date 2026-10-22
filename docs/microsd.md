# microSD firmware preparation

The microSD build uses the existing read-only external-animation interface instead of
the USB-host transport. The installed mapping and show stay in internal storage. A card
contributes the `.odrg` files in its top-level `odrig` folder, using the same 60001-up
animation IDs, ordering and validation as a USB drive. Commands and LED outputs do not
change. The ordinary firmware build still uses USB storage.

## Build

```
python3 firmware/fw.py build --microsd
```

This builds `build/firmware/out/odrig-microsd.bin`, with its SHA-256 beside it, on the
Arduino 3 / ESP-IDF 5.5.5 platform used by the trial firmware. It does not flash a board.
The native USB socket stays a serial connection in this build; the SD transport never
starts the USB host or waits for a USB computer.

The SPI configuration is in `firmware/usermod/odrig_sd_config.h`. All four GPIOs default
to -1, so an unconfigured build initializes no SD GPIOs. The adapter's identity, voltage
requirements and pin labels must be confirmed by the owner before those values are set.
The twenty LED outputs, native USB, UART and module memory pins must stay available for
their existing uses. No pin assignment in this preparation is a wiring instruction.

## Card

Use FAT32, with animation files directly in `/odrig`. The firmware must not format the
card or write animation data to it. A missing or unreadable card leaves the installed
show available. Keep the installed show at brightness 40 or below on the present bench.

The reader retries mounting and checks a real card-sector read for removal. A failing
card can hold a read until the low-level driver's timeout, briefly delaying playback.
Host-side recovery tests do not establish the refresh rate during physical removal.

## Still required on hardware

- Identify the adapter and confirm its wiring and power requirements.
- Set the matching GPIO configuration and rebuild the image.
- Flash through `firmware/fw.py` only after the owner is ready for that step.
- Verify card mounting, the animation list, playback and Wi-Fi commands on the board.
- Measure playback with twenty outputs; the accepted refresh rate is 20 to 50 per second.

A successful compilation or a host-side test does not establish any of these hardware
checks.
