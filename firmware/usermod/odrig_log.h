// The log of the firmware: lines about what the chip's own USB socket sees, and every
// line the player logs. They wait in a small queue, and the UART's code writes them to
// the serial chip's port between replies. A line is
// `#log <seconds>.<milliseconds> <kind>: <text>`, one line of printable ASCII.
#pragma once

#include <stddef.h>

#include "odrig_core.h"

namespace OdrigLog {

// The room for a line, with its line feed. A longer text is cut.
const size_t LINE_ROOM = 160;

// Adds a line: its kind, such as `usb` or `player`, and its text. From any task; it never
// waits. When the queue is full, the oldest line gives way, and the lines that gave way
// are counted.
void add(const char *kind, const char *text);

// The next line to write, with its line feed, into `line`, when it fits into both `room`
// and `most` bytes; its length, or 0 when no line waits or the next one does not fit.
// After lines gave way, the first line is one that says how many.
size_t take(char *line, size_t room, size_t most);

// The host functions of the core with its `log` wrapped: each line goes to the given
// `log`, and to the log as a line of the kind `player`.
odrig_host withLog(const odrig_host &given);

}  // namespace OdrigLog
