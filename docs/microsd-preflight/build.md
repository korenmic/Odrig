# Configured microSD build

- Source profile commit: `551a52b`.
- Command: `python3 firmware/fw.py build --microsd`.
- Environment: `odrig_microsd`, Arduino 3.3.12 / ESP-IDF 5.5.5.
- SPI assignment: SCK39, MISO40, MOSI41, CS42, 4 MHz.
- Output: `build/firmware/out/odrig-microsd.bin`, 1,765,808 bytes.
- Application slot: 3,145,728 bytes; the image fits.
- Build-reported SHA-256:
  `fd089753d86c92d9cbfbb2e4823d49428e4b037213b656736636b9dd9a1950a5`.

The build completed successfully and generated its adjacent `.sha256` file. Independent
checksum, linked-driver and regression verification belong to checklist step 3. Nothing
was flashed, and no physical wiring or on-board behavior is established by this build.
