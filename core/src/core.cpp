#include <string.h>

#include "arena.h"
#include "core_state.h"
#include "mapping.h"
#include "odrig_core.h"
#include "player.h"
#include "reasons.h"
#include "show.h"

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

// Decodes one file of the show from its first frame record to its last, and notes its
// number of frames and its total duration. The header is checked first, then the size
// against the mapping, then the body.
void check_file(Core &core, FileInfo &info) {
    Reason reason = core.file.open(core.host, info.name);
    if (reason != kNone) {
        fail(core, reason, info.name, kNone);
        return;
    }
    reason = core.decoder.open(&core.file, &core.inflate, core.window);
    if (reason == kNone && (core.decoder.width != core.width || core.decoder.height != core.height)) {
        core.file.close();
        fail(core, kSizeMismatch, info.name, kNone);
        return;
    }
    uint64_t total = 0;
    if (reason == kNone) {
        memset(core.pixels, 0, core.decoder.n);
        for (uint32_t record = 0; record < core.decoder.frames && reason == kNone; ++record) {
            uint16_t duration = 0;
            reason = core.decoder.next(core.pixels, &duration);
            total += duration;
        }
    }
    if (reason == kNone) {
        reason = core.decoder.finish();
    }
    core.file.close();
    if (reason == kReadError) {
        fail(core, kReadError, info.name, kNone);
    } else if (reason != kNone) {
        fail(core, kFileMalformed, info.name, reason);
    } else {
        info.frames = core.decoder.frames;
        info.total_ms = total;
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

    char id_text[kIdTextSize];
    reason = read_show(core, id_text);
    if (reason != kNone) {
        const char *about = id_text[0] != '\0' ? id_text : nullptr;
        fail(core, reason, reason == kReadError ? "show.json" : about, kNone);
        return;
    }

    // The files are checked in the order in which the show first names them.
    for (uint32_t index = 0; index < core.file_count && !core.invalid; ++index) {
        check_file(core, core.files[index]);
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
    odrig::player_start(core->state);
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
