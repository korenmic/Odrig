// A USB flash drive on the chip's own USB socket, which is switched to host mode for it.
// When a drive comes, it is mounted at /usb, the animation files of its folder odrig are
// listed for the core, and the core reads them through the host functions made here.
// Nothing is written to the drive.
#pragma once

#include <stdint.h>

#include "odrig_core.h"

namespace OdrigDrive {

// Starts the USB host on the chip's own socket and the tasks that take a drive up and
// drop it. From here on that socket is no serial port to a computer.
void begin();

// The host functions of the core with a drive: `drive` and `drive_name`, and `open`,
// `read`, `close` and `read_at`, which take a name `drive/<place>` to the file at that
// place of the drive's list and every other name to the functions of `files`.
odrig_host withDrive(const odrig_host &files);

// What there is of a drive now, for WLED's information: no USB host, no drive, a drive
// that could not be read, or the number of animation files of the drive.
const char *summary();

}  // namespace OdrigDrive
