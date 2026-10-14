#include <string.h>

#include "arena.h"
#include "core_state.h"
#include "mapping.h"
#include "odrig_core.h"
#include "player.h"
#include "reasons.h"
#include "show.h"
#include "storage.h"
#include "upload.h"

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

// Makes the show invalid for a file that cannot be used.
void fail_file(Core &core, const FileInfo &info, Reason reason) {
    if (reason == kFileMissing || reason == kReadError || reason == kSizeMismatch) {
        core_fail(core, reason, info.name, kNone);
    } else {
        core_fail(core, kFileMalformed, info.name, reason);
    }
}

// Opens one file of the show and the decoder on it, which reads the header, and compares
// the canvas with the mapping's. The palette and the frame records are not read.
void open_file(Core &core, const FileInfo &info) {
    Reason reason = core.file.open(core.host, info.name);
    if (reason == kNone) {
        reason = core.decoder.open(&core.file, &core.inflate, core.window);
        if (reason == kNone && (core.decoder.width != core.width || core.decoder.height != core.height)) {
            reason = kSizeMismatch;
        }
        core.file.close();
    }
    if (reason != kNone) {
        fail_file(core, info, reason);
    }
}

// Decodes one file of the show from its first frame record to its last, and notes its
// size and its total duration. The header is checked first, then the size
// against the mapping, then the body.
void check_file(Core &core, FileInfo &info) {
    Reason reason = core.file.open(core.host, info.name);
    if (reason != kNone) {
        core_fail(core, reason, info.name, kNone);
        return;
    }
    reason = core.decoder.open(&core.file, &core.inflate, core.window);
    if (reason == kNone && (core.decoder.width != core.width || core.decoder.height != core.height)) {
        core.file.close();
        core_fail(core, kSizeMismatch, info.name, kNone);
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
    // A file that was read to its end was read whole.
    const uint32_t bytes = core.file.taken;
    core.file.close();
    if (reason == kReadError) {
        core_fail(core, kReadError, info.name, kNone);
    } else if (reason != kNone) {
        core_fail(core, kFileMalformed, info.name, reason);
    } else {
        info.bytes = bytes;
        info.total_ms = total;
    }
}

// One step of the check after the start, on the file it is at.
void check_step(Core &core) {
    FileInfo &info = core.files[core.check_at];
    Checker &checker = *core.checker;
    Reason reason;
    if (!core.check_header_read) {
        checker.file.open_at(core.host, info.name);
        reason = checker.decoder.open(&checker.file, &checker.inflate, core.check_window);
        if (reason == kNone && (checker.decoder.width != core.width || checker.decoder.height != core.height)) {
            reason = kSizeMismatch;
        }
        if (reason == kNone) {
            memset(core.check_pixels, 0, checker.decoder.n);
            core.check_records_left = checker.decoder.frames;
            core.check_total_ms = 0;
            core.check_header_read = 1;
            return;
        }
    } else if (core.check_records_left != 0) {
        uint16_t duration = 0;
        reason = checker.decoder.next(core.check_pixels, &duration);
        core.check_total_ms += duration;
        --core.check_records_left;
        if (reason == kNone) {
            return;
        }
    } else {
        // After the last record nothing may follow. A file read to its end was read whole.
        reason = checker.decoder.finish();
        if (reason == kNone) {
            info.bytes = checker.file.taken;
            info.total_ms = core.check_total_ms;
            checker.file.close();
            core.check_header_read = 0;
            ++core.check_at;
            core.check_done = core.check_at == core.file_count;
            return;
        }
    }
    checker.file.close();
    fail_file(core, info, reason);
}

void start(Core &core) {
    storage_clear_parts(core);

    core.line = static_cast<char *>(arena_take(core, ODRIG_LINE_MAX + 1));
    core.feed_reply = static_cast<char *>(arena_take(core, ODRIG_REPLY_MAX));
    if (core.line == nullptr || core.feed_reply == nullptr) {
        core_fail(core, kOutOfMemory, nullptr, kNone);
        return;
    }

    Reason reason = read_mapping(core);
    if (reason != kNone) {
        core_fail(core, reason, reason == kReadError ? "mapping.json" : nullptr, kNone);
        return;
    }

    const uint32_t rgb_picture = 3u * core.led_total;
    core.pixels = static_cast<uint8_t *>(arena_take(core, rgb_picture < kLargestPicture ? rgb_picture : kLargestPicture));
    core.window = static_cast<uint8_t *>(arena_take(core, kWindowSize));
    if (core.pixels == nullptr || core.window == nullptr) {
        core_fail(core, kOutOfMemory, nullptr, kNone);
        return;
    }
    if (storage_changes(core)) {
        // What only a change of the show needs: the chunk buffer, and for the check of an
        // uploaded file a second set of decoders with a pixel buffer and a window.
        core.chunk = static_cast<uint8_t *>(arena_take(core, kChunkSize));
        core.checker = static_cast<Checker *>(arena_take(core, sizeof(Checker)));
        core.check_pixels = static_cast<uint8_t *>(arena_take(core, rgb_picture < kLargestPicture ? rgb_picture : kLargestPicture));
        core.check_window = static_cast<uint8_t *>(arena_take(core, kWindowSize));
        if (core.chunk == nullptr || core.checker == nullptr || core.check_pixels == nullptr || core.check_window == nullptr) {
            core_fail(core, kOutOfMemory, nullptr, kNone);
            return;
        }
    }

    char id_text[kIdTextSize];
    reason = read_show(core, id_text);
    if (reason != kNone) {
        const char *about = id_text[0] != '\0' ? id_text : nullptr;
        core_fail(core, reason, reason == kReadError ? kShowFile : about, kNone);
        return;
    }
    storage_settle_pending(core);

    // The files are opened in the order in which the show first names them. Their bodies
    // are read while the show plays, by the second decoders. A host whose storage cannot
    // be changed has none: for it every file is read to its end here.
    for (uint32_t index = 0; index < core.file_count && !core.invalid; ++index) {
        if (core.checker == nullptr) {
            check_file(core, core.files[index]);
        } else {
            open_file(core, core.files[index]);
        }
    }
    core.check_done = core.checker == nullptr || core.file_count == 0;
}

}  // namespace

bool check_complete(const Core &core) {
    return core.check_done != 0;
}

void check_after_start(Core &core, bool in_step) {
    if (core.invalid || check_complete(core)) {
        return;
    }
    if (!in_step) {
        core.check_row = 0;
        return;
    }
    if (core.check_row < kCheckMostSteps) {
        ++core.check_row;
    }
    for (uint8_t step = 0; step < core.check_row && !core.invalid && !check_complete(core); ++step) {
        check_step(core);
    }
}

void core_fail(Core &core, Reason reason, const char *about, Reason detail) {
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
    // An invalid show takes no upload and plays nothing.
    upload_discard(core);
    player_halt(core);
}

}  // namespace odrig

odrig_core *odrig_core_begin(const odrig_host *host) {
    if (host == nullptr) {
        return nullptr;
    }
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
