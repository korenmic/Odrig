#ifndef ODRIG_COMMANDS_H
#define ODRIG_COMMANDS_H

#include <stdint.h>

#include "core_state.h"

namespace odrig {

// Reads one command line, carries it out and writes its reply, which is one JSON object on
// one line of at most ODRIG_REPLY_MAX bytes with its newline. Returns the length of the
// reply. This is the only place where a command is interpreted.
uint32_t command_answer(Core &core, uint64_t now_ms, const char *line, uint32_t length, char *reply);

}  // namespace odrig

#endif
