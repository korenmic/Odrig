// Removable animations. The default is a USB drive on the chip's own socket.
// ODRIG_DRIVE_SD_SPI selects a SPI card, configured by odrig_sd_config.h, and keeps that
// socket a serial port. Each backend lists its folder odrig when the core asks, gives a
// place the name the core binds to it, and serves the core's reads. The card's backend
// also makes the core's changes of the files of that folder; a stick is never written.
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

// The host functions of the core with a drive: `drive`, `drive_name`, `drive_space`,
// `drive_list`, `drive_bind` and `drive_writable`; `open`, `read`, `close` and `read_at`,
// which take a name `drive/<place>` to the file at that place of the drive's list, a name
// `drive/<name>` to the file of that name in its folder odrig, and every other name to the
// functions of `files`; and, when `files` can change its storage, the five functions that
// change files, which take the names `drive/<name>` to the card and the others to `files`.
odrig_host withDrive(const odrig_host &files);

// What the socket is now, for WLED's information: looking for a computer, a computer's,
// or what there is of a drive: no USB host, no drive, a drive that could not be read, or
// the number of animation files of the drive.
const char *summary();

}  // namespace OdrigDrive
