#ifndef ODRIG_MESSAGE_CLOCK_H
#define ODRIG_MESSAGE_CLOCK_H

#include "container.h"

namespace odrig {

// Reads a message-clock after its subtype byte, retaining the payload when requested.
Reason message_clock_read(FileSource *file, const ContentHeader &header, uint8_t *into);

// Draws at elapsed virtual time without keeping state between calls.
void message_clock_draw(const uint8_t *payload, uint32_t seed, uint64_t elapsed, uint8_t *pixels);

}  // namespace odrig
#endif
