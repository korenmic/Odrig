#include <string.h>

#include "arena.h"
#include "core_state.h"
#include "mapping.h"
#include "odrig_core.h"
#include "reasons.h"

namespace odrig {

namespace {

// Adds a text to the reason text, as far as it fits.
void append(Core &core, const char *text) {
    uint32_t length = 0;
    while (core.error_text[length] != '\0') {
        ++length;
    }
    while (*text != '\0' && length + 1 < kErrorTextSize) {
        core.error_text[length++] = *text++;
    }
    core.error_text[length] = '\0';
}

// Makes the show invalid: `<reason>`, `<reason> <about>` or `<reason> <about> <detail>`.
// The first failure decides; a later one changes nothing.
void fail(Core &core, Reason reason, const char *about, Reason detail) {
    if (core.invalid) {
        return;
    }
    core.invalid = 1;
    core.error_text[0] = '\0';
    append(core, reason_name(reason));
    if (about != nullptr) {
        append(core, " ");
        append(core, about);
    }
    if (detail != kNone) {
        append(core, " ");
        append(core, reason_name(detail));
    }
    if (core.host.log != nullptr) {
        core.host.log(core.host.ctx, core.error_text);
    }
}

void start(Core &core) {
    Reason reason = read_mapping(core);
    if (reason != kNone) {
        fail(core, reason, reason == kReadError ? "mapping.json" : nullptr, kNone);
        return;
    }

    const uint32_t rgb_picture = 3u * core.led_total;
    core.pixels = static_cast<uint8_t *>(arena_take(core, rgb_picture < kLargestPicture ? rgb_picture : kLargestPicture));
    core.window = static_cast<uint8_t *>(arena_take(core, kWindowSize));
    if (core.pixels == nullptr || core.window == nullptr) {
        fail(core, kOutOfMemory, nullptr, kNone);
        return;
    }
}

}  // namespace

}  // namespace odrig

odrig_core *odrig_core_begin(const odrig_host *host) {
    odrig_core *core = static_cast<odrig_core *>(odrig::host_memory(*host, sizeof(odrig_core)));
    if (core == nullptr) {
        return nullptr;
    }
    core->state.host = *host;
    core->state.starting = 1;
    odrig::start(core->state);
    core->state.starting = 0;
    return core;
}

uint32_t odrig_core_leg_count(const odrig_core *core) {
    return core != nullptr ? core->state.leg_count : 0;
}

int odrig_core_leg(const odrig_core *core, uint32_t index, odrig_leg *out) {
    if (core == nullptr || out == nullptr || index >= core->state.leg_count) {
        return 0;
    }
    const odrig::LegInfo &info = core->state.legs[index];
    out->leg = info.leg;
    out->pin = info.pin;
    out->led_count = info.count;
    out->rgb = core->state.led_data + 3u * info.first;
    return 1;
}

const char *odrig_core_error(const odrig_core *core) {
    if (core == nullptr || !core->state.invalid) {
        return nullptr;
    }
    return core->state.error_text;
}
