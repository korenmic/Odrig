// The board's UART, which its second USB socket carries through a bridge chip: it takes
// command lines for the player and writes the player's replies back.
#pragma once

#include <stddef.h>

namespace OdrigUart {

// One command line for the player, as it arrived, without its line feed. The reply is
// put into `reply` and its length returned. `capacity` is at least ODRIG_REPLY_MAX.
typedef size_t (*Line)(const char *line, size_t length, char *reply, size_t capacity);

// Opens the UART at 115,200 bits a second, with eight data bits, no parity and one stop
// bit, and gives it a queue of 4,096 bytes for what it receives. Called once, in setup().
void begin();

// Takes what the UART has received, at most 256 bytes in one call. A line that has ended
// is handed to `line`, and the reply is written to the UART. Of a line that is longer
// than a command line may be, one character more than that is kept, so that the player
// refuses the line as too long. While the pacing of odrig_files.h holds lines back, a
// line that has ended waits.
void poll(Line line);

}  // namespace OdrigUart
