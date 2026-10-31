#ifndef ODRIG_MINI_H
#define ODRIG_MINI_H

#include <stdint.h>

namespace odrig {
struct Core;

struct Mini {
    uint32_t revision;
    uint8_t supported : 1;
    uint8_t active : 1;
    uint8_t requested : 1;
    uint8_t pending : 1;
    uint8_t failed : 1;
    uint8_t rgb[180];
};

void mini_clear(Core &core);
void mini_render(Core &core, const uint8_t *layer);
uint8_t mini_brightness(const Core &core);
}
#endif
