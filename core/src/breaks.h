#ifndef ODRIG_BREAKS_H
#define ODRIG_BREAKS_H

#include <stdint.h>

#include "commands.h"
#include "core_state.h"

namespace odrig {

// The file of the two settings of the clocks between the animations, and the file its next
// version is written into until it is renamed. No show names them.
const char kClocksFile[] = "clocks.txt";
const char kClocksPart[] = "clocks.part";

// The start, before the show is read: removes a `clocks.part` a cut left, and reads
// `clocks.txt` whole and strictly. A missing file is both settings off; a file out of its
// form is both off, and the log says `clocks unreadable`.
void breaks_start(Core &core);

// The reply to `clocks on`, `clocks off`, `clocks message on` and `clocks message off`,
// the words after `clocks` given. The file is written whole and renamed before the
// setting takes effect; a setting already in force writes nothing.
uint32_t breaks_command(Core &core, bool message, bool on, Reply &reply);

}  // namespace odrig

#endif
