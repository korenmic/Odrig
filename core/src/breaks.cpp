#include "breaks.h"

#include "catalog.h"
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
    core.clocks_on = clocks ? 1 : 0;
    core.clock_message_on = after ? 1 : 0;
    return succeed(reply);
}

}  // namespace odrig
