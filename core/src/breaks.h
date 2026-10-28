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

// The phases of a break: none, the clock's turn, the message's turn.
const uint8_t kBreakNone = 0;
const uint8_t kBreakClock = 1;
const uint8_t kBreakMessage = 2;

// A break comes once this many turns of the playlist, or this much of its time, are
// counted.
const uint8_t kBreakTurns = 5;
const uint64_t kBreakMs = 300000;

// The start, before the show is read: removes a `clocks.part` a cut left, and reads
// `clocks.txt` whole and strictly. A missing file is both settings off; a file out of its
// form is both off, and the log says `clocks unreadable`.
void breaks_start(Core &core);

// The reply to `clocks on`, `clocks off`, `clocks message on` and `clocks message off`,
// the words after `clocks` given. The file is written whole and renamed before the
// setting takes effect; a setting already in force writes nothing.
uint32_t breaks_command(Core &core, bool message, bool on, Reply &reply);

// The drive's tree was built, found again or cleared, or the positions of its walk moved:
// the clocks' folders are found again by their paths, and a new order of the clocks is
// drawn at the next break.
void breaks_tree(Core &core);

// Whether the position of the drive's walk is in the clocks' folders while the clocks are
// on, so that every playlist passes over it.
bool breaks_passes_over(const Core &core, uint32_t at);

// The clock of a break that begins at a moment: the next in the order that plays, as a
// position of the playlist, a new order drawn when it is used up; kNothing when none plays.
uint32_t breaks_pick(Core &core, uint64_t at);

// The message: the first file of `clocks/message` that plays, or kNothing.
uint32_t breaks_message(const Core &core);

}  // namespace odrig

#endif
