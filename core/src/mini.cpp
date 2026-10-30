#include <string.h>

#include "core_state.h"
#include "mini.h"

namespace odrig {

uint8_t mini_brightness(const Core &core) {
    return !core.on ? 0 : core.brightness < 40 ? core.brightness : 40;
}

void mini_clear(Core &core) {
    if (core.mini == nullptr) return;
    memset(core.mini->rgb, 0, sizeof core.mini->rgb);
}

void mini_render(Core &core, const uint8_t *layer) {
    if (core.mini == nullptr || !core.mini->active) return;
    Mini &mini = *core.mini;
    const uint32_t brightness = mini_brightness(core);
    for (uint32_t y = 0; y < 6; ++y) {
        for (uint32_t x = 0; x < 6; ++x) {
            uint32_t sums[3] = {};
            for (uint32_t dy = 0; dy < 10; ++dy) {
                for (uint32_t dx = 0; dx < 10; ++dx) {
                    const uint32_t at = (y * 10 + dy) * 60 + x * 10 + dx;
                    const uint8_t *colour;
                    if (core.decoder.colours != 0) {
                        const uint8_t index = layer != nullptr && layer[at] != 0 ?
                            static_cast<uint8_t>(layer[at] - 1) : core.pixels[at];
                        colour = core.decoder.palette + 3u * index;
                    } else {
                        colour = core.pixels + 3u * at;
                    }
                    for (uint32_t c = 0; c < 3; ++c) sums[c] += (colour[c] * brightness + 127) / 255;
                }
            }
            for (uint32_t c = 0; c < 3; ++c) {
                const uint8_t value = static_cast<uint8_t>(sums[c] / 100);
                mini.rgb[3u * ((x + 2) * 6 + y) + c] = value;
            }
        }
    }
}
}

void odrig_core_mini_support(odrig_core *core) {
    if (core != nullptr && core->state.mini != nullptr) core->state.mini->supported = 1;
}

int odrig_core_mini(const odrig_core *core, odrig_mini *out) {
    if (core == nullptr || out == nullptr || core->state.mini == nullptr) return 0;
    const odrig::Mini &mini = *core->state.mini;
    out->revision = mini.revision;
    out->active = mini.active;
    out->requested = mini.requested;
    out->pending = mini.pending;
    out->failed = mini.failed;
    out->rgb = mini.rgb;
    return mini.supported ? 1 : 0;
}

int odrig_core_mini_complete(odrig_core *core, uint32_t revision, int success) {
    if (core == nullptr || core->state.mini == nullptr) return 0;
    odrig::Mini &mini = *core->state.mini;
    if (!mini.supported || !mini.pending || revision != mini.revision) return 0;
    mini.pending = 0;
    mini.failed = success ? 0 : 1;
    mini.active = success ? mini.requested : 0;
    odrig::mini_clear(core->state);
    return 1;
}
