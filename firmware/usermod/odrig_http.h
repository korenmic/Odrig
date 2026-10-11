// Commands over HTTP: `POST /odrig` on WLED's web server, as docs/commands.md defines it.
#pragma once

#include <stddef.h>

namespace OdrigHttp {

// Takes one command line for the player and puts the reply into `reply`. Returns the
// reply's length, or 0 when there is no player. `capacity` is at least ODRIG_REPLY_MAX.
typedef size_t (*Command)(const char *line, size_t length, char *reply, size_t capacity);

// Registers the handler on WLED's web server. Called once, before the server starts.
void begin(Command command);

}  // namespace OdrigHttp
