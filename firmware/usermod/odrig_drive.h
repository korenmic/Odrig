// Read-only removable animations. The default is a USB drive on the chip's own socket.
// ODRIG_DRIVE_SD_SPI selects a SPI card, configured by odrig_sd_config.h, and keeps that
// socket a serial port. Each backend lists its folder odrig and serves the core's reads.
#pragma once

#include <stdint.h>

#include "odrig_core.h"

namespace OdrigDrive {

// Starts the selected reader's task. The USB backend looks for a computer for the
// wait, and leaves the socket a serial port when one is there. Otherwise it starts the USB
// host on the socket and takes drives up and drops them; from then on the socket is no
// serial port to a computer until the next start. The SPI backend touches no pin until
// all four configured pins and the clock are valid. It retries mounts and checks an
// actual card read once a second; a read fault drops the card before another mount.
void begin();

// The wait, in milliseconds: from 0 to 60,000, and 5,000 for any other value. It is set
// before `begin()`.
void setWait(uint32_t ms);
uint32_t wait();

// The host functions of the core with a drive: `drive` and `drive_name`, and `open`,
// `read`, `close` and `read_at`, which take a name `drive/<place>` to the file at that
// place of the drive's list and every other name to the functions of `files`.
odrig_host withDrive(const odrig_host &files);

// What the socket is now, for WLED's information: looking for a computer, a computer's,
// or what there is of a drive: no USB host, no drive, a drive that could not be read, or
// the number of animation files of the drive.
const char *summary();

}  // namespace OdrigDrive
