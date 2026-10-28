#include "playlist.h"

#include "drive.h"
#include "file_source.h"
#include "player.h"
#include "storage.h"

namespace odrig {

namespace {

const char kPlaylistHeader[] = "odrig-playlist 1";

uint32_t put_text(char *into, uint32_t at, const char *text) {
    while (*text != '\0') {
        into[at++] = *text++;
    }
    return at;
}

uint32_t put_number(char *into, uint32_t at, uint64_t value) {
    char figures[20];
    uint32_t count = 0;
    do {
        figures[count++] = static_cast<char>('0' + value % 10);
        value /= 10;
    } while (value != 0);
    while (count != 0) {
        into[at++] = figures[--count];
    }
    return at;
}

// The milliseconds spent in the current playlist's window, at most the window.
uint64_t spent_in_window(const Core &core) {
    const uint64_t since = core.latest > core.window_started ? core.latest - core.window_started : 0;
    const uint64_t spent = core.window_spent + since;
    return spent < kWindowMs ? spent : kWindowMs;
}

// Whether the file may be written now: not while an upload receives its bytes, since
// `write_open` would give up its part, nor while a rebuild holds a new page open.
bool free_to_write(const Core &core) {
    return core.upload.state != kUploadReceiving && !core.rebuild_open;
}

// Writes the file as its part and renames it, with the pattern of `order.txt`. A host
// that fails leaves the file as it was, and the part is removed: nothing is refused.
void write_file(Core &core) {
    const odrig_host &host = core.host;
    char text[kPlaylistPathRoom + 32];
    uint32_t length = put_text(text, 0, kPlaylistHeader);
    text[length++] = '\n';
    length = put_text(text, length, core.playlist_path);
    text[length++] = '\n';
    length = put_number(text, length, spent_in_window(core));
    text[length++] = '\n';
    const bool written = host.write_open(host.ctx, kPlaylistPart) == 1 && host.write(host.ctx, reinterpret_cast<const uint8_t *>(text), length) == 1 &&
                         host.write_close(host.ctx) == 1 && host.rename(host.ctx, kPlaylistPart, kPlaylistFile) == 1;
    if (!written) {
        host.remove(host.ctx, kPlaylistPart);
        return;
    }
    core.file_present = 1;
}

// One line of the file as it is read: the header, the path, or the time spent. False when
// the line is not what the file holds there.
bool take_line(Core &core, uint32_t number, const char *line, uint32_t length, uint64_t *spent) {
    if (number == 0) {
        uint32_t at = 0;
        while (at < length && kPlaylistHeader[at] != '\0' && line[at] == kPlaylistHeader[at]) {
            ++at;
        }
        return at == length && kPlaylistHeader[at] == '\0';
    }
    if (number == 1) {
        if (length >= kPlaylistPathRoom) {
            return false;
        }
        for (uint32_t at = 0; at < length; ++at) {
            core.playlist_path[at] = line[at];
        }
        core.playlist_path[length] = '\0';
        return true;
    }
    if (number == 2) {
        if (length == 0 || length > 10) {
            return false;
        }
        uint64_t value = 0;
        for (uint32_t at = 0; at < length; ++at) {
            if (line[at] < '0' || line[at] > '9') {
                return false;
            }
            value = value * 10 + static_cast<uint64_t>(line[at] - '0');
        }
        *spent = value < kWindowMs ? value : kWindowMs;
        return true;
    }
    return false;
}

}  // namespace

void playlist_start(Core &core) {
    core.save_due = 0;
    core.file_present = 0;
    core.playlist_saved = 0;
    if (!storage_changes(core) || core.checker == nullptr || core.playlist_path == nullptr) {
        return;
    }
    core.playlist_path[0] = '\0';
    core.window_spent = 0;
    FileSource &source = core.checker->file;
    source.open_at(core.host, kPlaylistFile);
    char line[kPlaylistPathRoom];
    uint32_t length = 0;
    uint32_t number = 0;
    uint64_t spent = 0;
    bool sound = true;
    int got;
    while (sound && (got = source.get()) >= 0) {
        if (got == '\n') {
            sound = number < 3 && take_line(core, number, line, length, &spent);
            ++number;
            length = 0;
        } else if (length < sizeof line) {
            line[length++] = static_cast<char>(got);
        } else {
            sound = false;
        }
    }
    source.close();
    if (!sound || number != 3) {
        // No file, or not one of the core's: the root with a fresh window.
        core.playlist_path[0] = '\0';
        return;
    }
    core.window_spent = static_cast<uint32_t>(spent);
    core.file_present = 1;
}

void playlist_changed(Core &core) {
    core.save_due = 1;
    playlist_touch(core, core.latest);
}

void playlist_touch(Core &core, uint64_t now) {
    if (core.playlist_path == nullptr || !storage_changes(core)) {
        return;
    }
    const bool periodic = drive_folder_count(core) > 1 && now - core.playlist_saved >= kPlaylistSaveEveryMs;
    if (!core.save_due && !periodic) {
        return;
    }
    if (drive_folder_count(core) <= 1 && !core.file_present) {
        // The root with a fresh window is what an absent file means: nothing to write.
        core.save_due = 0;
        return;
    }
    if (!free_to_write(core)) {
        return;
    }
    write_file(core);
    core.save_due = 0;
    core.playlist_saved = now;
}

}  // namespace odrig
