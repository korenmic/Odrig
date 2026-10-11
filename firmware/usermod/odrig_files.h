// What the core needs from its host on the board: memory, the time, the files of the
// installed show in the folder /odrig of storage, and a place for its diagnostic text.
#pragma once

#include <stdint.h>

#include "odrig_core.h"

namespace OdrigFiles {

// The host functions to start the core with.
odrig_host host();

// Milliseconds since the chip started, from a 64-bit clock that does not go backwards
// and does not wrap.
uint64_t nowMs();

// The core's last line of diagnostic text, or an empty text.
const char *lastLog();

}  // namespace OdrigFiles
