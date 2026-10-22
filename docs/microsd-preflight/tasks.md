# microSD local preflash checklist

Task source: the owner's four-step checklist in this conversation. This checklist covers
local preparation only; it does not authorize flashing or claim hardware verification.

- [x] Bridge: Prepare the SPI microSD firmware and local build checks.
  The preparatory transport, build variant, safety tests and documentation pass all
  544 firmware tests before the confirmed deployment pins are applied.
- [ ] 1. Configure microSD GPIO39–42 without affecting snake legs.
  Use SCK 39, MISO/DO 40, MOSI/DI 41 and CS 42. Preserve LED pins 1–18, 21 and 47.
- [ ] 2. Rebuild SD-enabled firmware.
  Use `python3 firmware/fw.py build --microsd`; do not access the board.
- [ ] 3. Rerun tests and verify checksum.
  Run the firmware suite by discovery and check the built image, its linked SD transport,
  mount path and checksum. Record the result without claiming on-board behavior.
- [ ] 4. Confirm wiring and readiness to flash.
  Local configuration can be checked now. Physical wiring and power remain the owner's
  check after the board is prepared; no local test can complete this step in advance.
