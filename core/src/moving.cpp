#include "moving.h"

#include <string.h>

#include "brightness.h"
#include "catalog.h"
#include "drive.h"
#include "fields.h"
#include "ignored.h"
#include "repeats.h"
#include "storage.h"
#include "upload.h"

namespace odrig {

namespace {

const char kHeader[] = "odrig-moving 1 ";
// The longest journal: its first line of 24 bytes, and two paths of kCatalogNameMost bytes,
// each line with its line feed.
const uint32_t kJournalMost = 24 + 2 * (kCatalogNameMost + 1);
// The longest line of a file of saved settings that a move rewrites, and the bytes gathered
// in the chunk buffer before they go to the host.
const uint32_t kLineRoom = 140;
const uint32_t kWriteRoom = 1000;

// A file of the board's storage, read a piece at a time with `read_at`.
struct Pieces {
    const odrig_host &host;
    const char *name;
    uint32_t offset;
    uint32_t at;
    uint32_t length;
    uint8_t piece[128];

    // The next byte; -1 at the end, -2 when it cannot be read.
    int get() {
        if (at == length) {
            const int32_t got = host.read_at(host.ctx, name, offset, piece, sizeof piece);
            if (got < 0 || static_cast<uint32_t>(got) > sizeof piece) {
                return -2;
            }
            if (got == 0) {
                return -1;
            }
            offset += static_cast<uint32_t>(got);
            at = 0;
            length = static_cast<uint32_t>(got);
        }
        return piece[at++];
    }
};

// The ways the lines of a file come out.
enum Lines { kLinesSound, kLinesMissing, kLinesBad, kLinesFailed };

// The name a line of saved settings gives a file of the kind wanted, `<number> <kind> <name>`
// or `<kind> <name>`, and its length; null for a line of another kind.
const char *key_of(const char *line, uint32_t length, char kind, uint32_t *key_length) {
    uint32_t at = 0;
    if (length != 0 && line[0] >= '0' && line[0] <= '9') {
        while (at < length && line[at] >= '0' && line[at] <= '9') {
            ++at;
        }
        if (at == length || line[at] != ' ') {
            return nullptr;
        }
        ++at;
    }
    if (at + 2 > length || line[at] != kind || line[at + 1] != ' ') {
        return nullptr;
    }
    *key_length = length - at - 2;
    return line + at + 2;
}

bool is_name(const char *key, uint32_t length, const char *name) {
    return length == text_length(name) && memcmp(key, name, length) == 0;
}

// Reads the lines of a file of saved settings, each without its line feed, and gives each to
// `each` with whether it is the first, the file's header; `each` says whether to go on.
template <typename Each>
ODRIG_NOINLINE Lines read_lines(Core &core, const char *file, Each each) {
    Pieces pieces = {core.host, file, 0, 0, 0, {0}};
    char line[kLineRoom];
    uint32_t length = 0;
    bool first = true;
    for (;;) {
        const int got = pieces.get();
        if (got == -2) {
            return pieces.offset == 0 ? kLinesMissing : kLinesFailed;
        }
        if (got == -1) {
            return length == 0 ? kLinesSound : kLinesBad;
        }
        if (got != '\n') {
            if (length + 1 >= sizeof line) {
                return kLinesBad;
            }
            line[length++] = static_cast<char>(got);
            continue;
        }
        line[length] = '\0';
        if (!each(line, length, first)) {
            return kLinesSound;
        }
        first = false;
        length = 0;
    }
}

// The output of a file rewritten: its lines gathered in the chunk buffer and sent to the host.
struct Out {
    Core &core;
    uint32_t used;
    bool failed;

    void flush() {
        if (used != 0 && !failed && core.host.write(core.host.ctx, core.chunk, used) != 1) {
            failed = true;
        }
        used = 0;
    }

    void bytes(const char *text, uint32_t length) {
        for (uint32_t at = 0; at < length && !failed; ++at) {
            core.chunk[used++] = static_cast<uint8_t>(text[at]);
            if (used == kWriteRoom) {
                flush();
            }
        }
    }
};

// Gives a file of saved settings the name `to` for the name `from` in its lines of a kind,
// and drops its lines of that kind for `to` then: written through its part and renamed onto
// it. A file without a line for `from`, which a move done already leaves, a missing file and
// a file out of form are left as they are. False on a failed storage call.
ODRIG_NOINLINE bool rename_key(Core &core, const char *file, const char *part, char kind, const char *from, const char *to) {
    bool found = false;
    const Lines scanned = read_lines(core, file, [&](const char *line, uint32_t length, bool first) {
        uint32_t key_length = 0;
        const char *key = first ? nullptr : key_of(line, length, kind, &key_length);
        found = key != nullptr && is_name(key, key_length, from);
        return !found;
    });
    if (scanned == kLinesFailed) {
        return false;
    }
    if (scanned != kLinesSound || !found) {
        return true;
    }
    const odrig_host &host = core.host;
    if (host.write_open(host.ctx, part) != 1) {
        return false;
    }
    Out out = {core, 0, false};
    const Lines written = read_lines(core, file, [&](const char *line, uint32_t length, bool first) {
        uint32_t key_length = 0;
        const char *key = first ? nullptr : key_of(line, length, kind, &key_length);
        if (key != nullptr && is_name(key, key_length, to)) {
            return true;
        }
        if (key != nullptr && is_name(key, key_length, from)) {
            out.bytes(line, static_cast<uint32_t>(key - line));
            out.bytes(to, text_length(to));
        } else {
            out.bytes(line, length);
        }
        out.bytes("\n", 1);
        return true;
    });
    out.flush();
    const bool closed = host.write_close(host.ctx) == 1;
    if (written != kLinesSound || out.failed || !closed || host.rename(host.ctx, part, file) != 1) {
        host.remove(host.ctx, part);
        return false;
    }
    return true;
}

}  // namespace

bool moving_begin(Core &core, uint32_t generation, const char *from, const char *to) {
    uint8_t text[kJournalMost];
    uint32_t length = 0;
    put_text(text, &length, kHeader);
    put_hexadecimal(text, &length, generation, 8);
    put_text(text, &length, "\n");
    put_text(text, &length, from);
    put_text(text, &length, "\n");
    put_text(text, &length, to);
    put_text(text, &length, "\n");
    const odrig_host &host = core.host;
    if (host.write_open(host.ctx, kMovingPart) != 1) {
        return false;
    }
    if (host.write(host.ctx, text, length) == 1 && host.write_close(host.ctx) == 1 && host.rename(host.ctx, kMovingPart, kMovingFile) == 1) {
        return true;
    }
    host.remove(host.ctx, kMovingPart);
    return false;
}

void moving_given_up(Core &core) {
    core.host.remove(core.host.ctx, kMovingFile);
}

void moving_end(Core &core, const char *from, const char *to) {
    if (storage_changes(core) && core.host.read_at != nullptr &&
        (!rename_key(core, kRepeatsFile, kRepeatsPart, 'x', from, to) || !rename_key(core, kBrightnessFile, kBrightnessPart, 'x', from, to) ||
         !rename_key(core, kIgnoredFile, kIgnoredPart, 'f', from, to))) {
        return;
    }
    core.host.remove(core.host.ctx, kMovingFile);
}

void moving_settle(Core &core) {
    if (!catalog_drive_writable(core) || core.upload.state != kUploadNone || catalog_rebuilding(core) || core.host.read_at == nullptr) {
        return;
    }
    // The journal whole, a read of it giving any part of what is asked: none, or one that
    // cannot be read, is left; one byte more than the longest makes it out of form.
    char text[kJournalMost + 1];
    uint32_t length = 0;
    for (;;) {
        const int32_t got = core.host.read_at(core.host.ctx, kMovingFile, length, reinterpret_cast<uint8_t *>(text) + length, sizeof text - length);
        if (got < 0 || static_cast<uint32_t>(got) > sizeof text - length) {
            return;
        }
        if (got == 0) {
            break;
        }
        length += static_cast<uint32_t>(got);
        if (length == sizeof text) {
            break;
        }
    }
    text[length <= kJournalMost ? length : kJournalMost] = '\0';
    // Its three lines: its generation, the old path and the new one.
    uint32_t at = 0;
    uint32_t generation = 0;
    bool sound = length <= kJournalMost && word(text, &at, kHeader) && hexadecimal(text, &at, 8, &generation) && text[at] == '\n';
    const char *paths[2] = {nullptr, nullptr};
    for (uint32_t line = 0; sound && line < 2; ++line) {
        const uint32_t start = ++at;
        while (at < length && text[at] != '\n') {
            ++at;
        }
        sound = at < length && catalog_name_allowed(text + start, at - start);
        text[at] = '\0';
        paths[line] = text + start;
    }
    if (sound && at + 1 == length && generation == core.catalogs[kExternal].generation &&
        drive_position_named(core, paths[1], text_length(paths[1])) != kNothing) {
        moving_end(core, paths[0], paths[1]);
        return;
    }
    moving_given_up(core);
}

}  // namespace odrig
