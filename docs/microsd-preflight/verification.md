# Local verification of the configured image

Image: `build/firmware/out/odrig-microsd.bin`, 1,765,808 bytes.

SHA-256: `fd089753d86c92d9cbfbb2e4823d49428e4b037213b656736636b9dd9a1950a5`.

## Results

- `python3 firmware/fw.py test`: 545 tests pass after configuration, and again after
  the configured build. The final run took 44.625 seconds.
- Core tests selected by discovery patterns `test_drive*.py` and `test_playlist*.py`:
  19 external-media tests and 63 playlist tests pass. They cover installed and external
  animations together, IDs, frames, ordering, timing, removal and internal fallback.
- `shasum -a 256 -c odrig-microsd.bin.sha256` reports OK. The output image matches
  `WLED/.pio/build/odrig_microsd/firmware.bin` byte-for-byte.
- Defined symbols in the matching ELF include `fs::SDFS::begin`, `fs::SDFS::readRAW`,
  `sdcard_init`, `sdcard_mount` and the SD worker `driveEvents` at live code addresses.
- The loadable image contains `/sd/odrig`, `card opened:` and `odrig-drive`.
- Worker disassembly passes 39, 40, 41 and 42 to `SPIClass::begin` as SCK, MISO, MOSI
  and CS respectively. It calls `SD.begin` with CS42 and a 4 MHz clock.
- Both native USB serial and the bridge UART are linked. USB-host takeover and probe
  symbols are absent from this image.
- The twenty-leg mapping, LED implementation and sixteen-lane patch are unchanged
  from the source base; the configured SD pins do not overlap the LED or USB/UART pins.

## Remaining checks

Actual wiring, 3.3 V power, card mounting, playback and performance on the ESP32-S3
are not established. The owner has not prepared the board yet, and no board access or
flashing was performed.

The whole core suite remains incomplete: its earlier run was stopped at the unchanged
large-memory fixture in `test_memory.py`. The 82 relevant media/playlist checks above
passed; this is not a claim that every core test has completed.
