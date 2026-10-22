# microSD local preflash checklist

Task source: the owner's four-step checklist in this conversation. This checklist covers
local preparation only; it does not authorize flashing or claim hardware verification.

- [x] Bridge: Prepare the SPI microSD firmware and local build checks.
  The preparatory transport, build variant, safety tests and documentation pass all
  544 firmware tests before the confirmed deployment pins are applied.
- [x] 1. Configure microSD GPIO39–42 without affecting snake legs.
  Use SCK 39, MISO/DO 40, MOSI/DI 41 and CS 42. Preserve LED pins 1–18, 21 and 47.
  The configured profile passes all 545 firmware tests; its pin test checks the actual
  twenty-leg mapping and USB/UART reservations.
- [x] 2. Rebuild SD-enabled firmware.
  Use `python3 firmware/fw.py build --microsd`; do not access the board.
  The configured image compiled successfully: 1,765,808 bytes. See [build.md](build.md).
- [x] 3. Rerun tests and verify checksum.
  Run the firmware suite by discovery and check the built image, its linked SD transport,
  mount path and checksum. Record the result without claiming on-board behavior.
  Final result: 545 firmware tests and 82 media/playlist integration tests pass; checksum,
  image copy, live SD symbols, mount path and SPI pin arguments are verified.
- [x] 4. Confirm wiring and readiness to flash.
  Local configuration can be checked now. Physical wiring and power remain the owner's
  check after the board is prepared; no local test can complete this step in advance.
  The software-side readiness checks were completed before board access. On 2026-10-22
  the owner reported the agreed wiring complete and authorized flashing. The flash
  succeeded and SD access was demonstrated, but the card repeatedly drops out. Stable
  operation is not confirmed; see [the board trial](board-trial.md).
