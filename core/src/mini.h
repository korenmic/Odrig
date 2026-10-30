#ifndef ODRIG_MINI_H
#define ODRIG_MINI_H

#include <stdint.h>

namespace odrig {
struct Core;

struct Mini {
    uint32_t revision;
    uint8_t supported;
    uint8_t active;
    uint8_t requested;
    uint8_t pending;
    uint8_t failed;
    uint8_t rgb[180];
};

void mini_clear(Core &core);
void mini_render(Core &core, const uint8_t *layer);
uint8_t mini_brightness(const Core &core);
}
#endif
