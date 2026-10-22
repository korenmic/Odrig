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

The `odrig_microsd` environment in `firmware/platformio_override.ini.in` selects the
agreed SPI pins for the SparkFun Shifting microSD adapter:

| Adapter | ESP32-S3 |
|---|---|
| SCK | GPIO39 |
| DO / MISO | GPIO40 |
| DI / MOSI | GPIO41 |
| CS | GPIO42 |
| VCC | 3V3, never 5V with direct ESP32 signals |
| GND | GND |
| CD | Unconnected |

The twenty LED outputs on GPIO1–18, 21 and 47, native USB, UART and module memory
pins keep their existing uses. The generic `odrig_sd_config.h` defaults remain -1, so
another build that omits the pin flags initializes no SD GPIOs. The selected microSD
build is configured, but actual wiring and power still need the owner's confirmation.

## Card

Use FAT32, with animation files directly in `/odrig`. The firmware must not format the
card or write animation data to it. A missing or unreadable card leaves the installed
show available. Keep the installed show at brightness 40 or below on the present bench.

The reader retries mounting and checks a real card-sector read for removal. A failing
card can hold a read until the low-level driver's timeout, briefly delaying playback.
Host-side recovery tests do not establish the refresh rate during physical removal.

## Still required on hardware

- Confirm the physical wiring matches the configured pins and uses 3.3 V.
- Flash through `firmware/fw.py` only after the owner is ready for that step.
- Verify card mounting, the animation list, playback and Wi-Fi commands on the board.
- Measure playback with twenty outputs; the accepted refresh rate is 20 to 50 per second.

A successful compilation or a host-side test does not establish any of these hardware
checks.
