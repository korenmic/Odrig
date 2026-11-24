#ifndef ODRIG_ROTATION_H
#define ODRIG_ROTATION_H

#include "core_state.h"
#include "commands.h"

namespace odrig {
void rotation_start(Core &core);
uint32_t rotation_reply(const Core &core, Reply &reply);
uint32_t rotation_set(Core &core, uint32_t revision, uint32_t degrees, Reply &reply);

inline uint32_t rotation_pixel(const Core &core, uint32_t at) {
    if (core.rotation == 0 || core.mapping_test || core.width != core.height || core.width == 0) return at;
    const uint32_t n = core.width;
    const uint32_t x = at % n;
    const uint32_t y = at / n;
    if (core.rotation == 1) return x * n + n - 1 - y;
    if (core.rotation == 2) return (n - 1 - y) * n + n - 1 - x;
    return (n - 1 - x) * n + y;
}
}
#endif
