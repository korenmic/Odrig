#ifndef ODRIG_ARENA_H
#define ODRIG_ARENA_H

#include <stdint.h>
#include <string.h>

#include "core_state.h"

namespace odrig {

// A block of memory from the host, cleared, or a null pointer when the host has none. This
// is the only place where the core asks for memory.
inline void *host_memory(const odrig_host &host, uint32_t bytes) {
    void *block = host.alloc(host.ctx, bytes);
    if (block != nullptr) {
        memset(block, 0, bytes);
    }
    return block;
}

// A block for the core object to keep. It is refused once startup has ended.
inline void *arena_take(Core &core, uint32_t bytes) {
    if (!core.starting) {
        return nullptr;
    }
    return host_memory(core.host, bytes);
}

}  // namespace odrig

#endif
