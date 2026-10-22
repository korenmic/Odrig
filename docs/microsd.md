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
build is configured. The owner reported the agreed wiring complete before the first
board trial; the agent has not independently measured the wiring or supply voltage.

## Card

Use FAT32, with animation files directly in `/odrig`. The firmware must not format the
card or write animation data to it. A missing or unreadable card leaves the installed
show available. Keep the installed show at brightness 40 or below on the present bench.

The reader retries mounting and checks a real card-sector read for removal. A failing
card can hold a read until the low-level driver's timeout, briefly delaying playback.
Host-side recovery tests do not establish the refresh rate during physical removal.

## Hardware verification

- The owner confirmed the agreed wiring and authorized the first flash. The flash,
  initial card access and brief software-reported SD playback succeeded.
- Verify stable access to all 122 card animations and sustained SD playback.
- Verify Wi-Fi commands and the owner's visual LED checks on the board.
- Measure playback with twenty outputs; the accepted refresh rate is 20 to 50 per second.

A successful compilation or a host-side test does not establish any of these hardware
checks.

The [first board trial](microsd-preflight/board-trial.md) mounted the card, validated
animation files and played an SD animation, but repeated dropouts prevent a claim of
stable operation. Trials at 1 MHz and 400 kHz also dropped files; the prepared 4 MHz
configuration was restored. UART diagnostics and stable validation of all 122 card
animations remain open.
