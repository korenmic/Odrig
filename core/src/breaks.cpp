#include "breaks.h"

#include "catalog.h"
#include "clock.h"
#include "drive.h"
#include "ignored.h"
#include "player.h"
#include "storage.h"

namespace odrig {

namespace {

const char kClocksHeader[] = "odrig-clocks 1\n";
// The most bytes the file is read into: more than its longest form has.
const uint32_t kClocksRead = 64;

// Whether `text`, `length` bytes from `at`, begins with the text `word`; `at` then moves
// past it.
bool takes(const uint8_t *text, uint32_t length, uint32_t *at, const char *word) {
    uint32_t size = 0;
    while (word[size] != '\0') {
        ++size;
    }
    if (length - *at < size) {
        return false;
    }
    for (uint32_t index = 0; index < size; ++index) {
        if (text[*at + index] != static_cast<uint8_t>(word[index])) {
            return false;
        }
    }
    *at += size;
    return true;
}

// Writes `clocks.part` with the two settings and renames it onto the file. False when a
// call of the host failed.
bool write_file(Core &core, bool clocks, bool message) {
    const odrig_host &host = core.host;
    if (host.write == nullptr || host.write_close == nullptr || host.rename == nullptr || host.write_open(host.ctx, kClocksPart) != 1) {
        return false;
    }
    uint8_t text[kClocksRead];
    uint32_t length = 0;
    const char *lines[3] = {kClocksHeader, clocks ? "clocks on\n" : "clocks off\n", message ? "message on\n" : "message off\n"};
    for (const char *line : lines) {
        for (uint32_t at = 0; line[at] != '\0'; ++at) {
            text[length++] = static_cast<uint8_t>(line[at]);
        }
    }
    const bool written = host.write(host.ctx, text, length) == 1;
    return host.write_close(host.ctx) == 1 && written && host.rename(host.ctx, kClocksPart, kClocksFile) == 1;
}

}  // namespace

void breaks_start(Core &core) {
    core.clocks_on = 0;
    core.clock_message_on = 0;
    core.clocks_first = core.clocks_last = core.clocks_files = 0;
    core.message_first = core.message_files = 0;
    core.order_key = core.order_next = core.order_count = 0;
    if (!storage_changes(core) || core.host.read_at == nullptr) {
        return;
    }
    uint8_t text[kClocksRead];
    if (core.host.read_at(core.host.ctx, kClocksPart, 0, text, 1) >= 0) {
        core.host.remove(core.host.ctx, kClocksPart);
    }
    uint32_t length = 0;
    bool sound = true;
    for (;;) {
        const int32_t got = core.host.read_at(core.host.ctx, kClocksFile, length, text + length, kClocksRead - length);
        if (got < 0 && length == 0) {
            return;
        }
        if (got < 0) {
            sound = false;
            break;
        }
        if (got == 0) {
            break;
        }
        length += static_cast<uint32_t>(got);
        if (length == kClocksRead) {
            sound = false;
            break;
        }
    }
    uint32_t at = 0;
    bool clocks = false;
    bool message = false;
    sound = sound && takes(text, length, &at, kClocksHeader);
    if (sound && takes(text, length, &at, "clocks on\n")) {
        clocks = true;
    } else if (!(sound && takes(text, length, &at, "clocks off\n"))) {
        sound = false;
    }
    if (sound && takes(text, length, &at, "message on\n")) {
        message = true;
    } else if (!(sound && takes(text, length, &at, "message off\n"))) {
        sound = false;
    }
    if (!sound || at != length) {
        if (core.host.log != nullptr) {
            core.host.log(core.host.ctx, "clocks unreadable");
        }
        return;
    }
    core.clocks_on = clocks ? 1 : 0;
    core.clock_message_on = message ? 1 : 0;
}

uint32_t breaks_command(Core &core, bool message, bool on, Reply &reply) {
    if (core.invalid) {
        return refuse(reply, "show-invalid");
    }
    if (catalog_rebuilding(core) || !check_complete(core) || core.upload.state != kUploadNone) {
        return refuse(reply, "busy");
    }
    if (!storage_changes(core)) {
        return refuse(reply, "storage-error");
    }
    const bool clocks = message ? core.clocks_on != 0 : on;
    const bool after = message ? on : core.clock_message_on != 0;
    if (clocks == (core.clocks_on != 0) && after == (core.clock_message_on != 0)) {
        return succeed(reply);
    }
    if (!write_file(core, clocks, after)) {
        core.host.remove(core.host.ctx, kClocksPart);
        return refuse(reply, "storage-error");
    }
    if (clocks && core.clocks_on == 0) {
        player_counts_start(core, core.latest);
    }
    if (message && on && core.break_phase == kBreakClock) {
        core.break_message = 1;
    }
    core.clocks_on = clocks ? 1 : 0;
    core.clock_message_on = after ? 1 : 0;
    return succeed(reply);
}

void breaks_tree(Core &core) {
    core.clocks_first = core.clocks_last = core.clocks_files = 0;
    core.message_first = core.message_files = 0;
    core.order_next = core.order_count = 0;
    if (!core.tree_known) {
        return;
    }
    IndexFolder folder;
    uint32_t ordinal = drive_folder_with_path(core, "clocks");
    if (ordinal != kNoFolder && ordinal != 0 && drive_folder(core, ordinal, folder)) {
        core.clocks_first = folder.first;
        core.clocks_last = folder.last;
        core.clocks_files = folder.files;
    }
    ordinal = drive_folder_with_path(core, "clocks/message");
    if (ordinal != kNoFolder && ordinal != 0 && drive_folder(core, ordinal, folder)) {
        core.message_first = folder.first;
        core.message_files = folder.files;
    }
}

bool breaks_passes_over(const Core &core, uint32_t at) {
    return core.clocks_on != 0 && at >= core.clocks_first && at < core.clocks_last;
}

uint32_t breaks_pick(Core &core, uint64_t at) {
    // At most two whole orders are tried: what is left of this one, and a new one.
    for (uint32_t tried = 0; core.clocks_files != 0 && tried < 2 * core.clocks_files; ++tried) {
        if (core.order_next >= core.order_count || core.order_count != core.clocks_files) {
            core.order_key = clock_seed(core.noise, core.clocks_files, at);
            core.order_count = core.clocks_files;
            core.order_next = 0;
        }
        const uint32_t position = core.clocks_first + clock_shuffle(core.order_key, core.order_count, core.order_next++);
        if (drive_automatic(core, position)) {
            return kDriveBase + position;
        }
    }
    return kNothing;
}

uint32_t breaks_message(const Core &core) {
    for (uint32_t position = core.message_first; position < core.message_first + core.message_files; ++position) {
        if (drive_automatic(core, position)) {
            return kDriveBase + position;
        }
    }
    return kNothing;
}

}  // namespace odrig
