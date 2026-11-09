#include "breaks.h"

#include "catalog.h"
#include "clock.h"
#include "drive.h"
#include "ignored.h"
#include "mapping_control.h"
#include "player.h"
#include "show.h"
#include "storage.h"

#include <string.h>

namespace odrig {

namespace {

const char kClocksHeader[] = "odrig-clocks 2\n";
const char kLegacyHeader[] = "odrig-clocks 1\n";
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

// Reads a complete bounded settings file; missing and failed reads are both errors.
int read_file(Core &core, const char *name, uint8_t *text, uint32_t &length) {
    length = 0;
    while (length < kClocksRead) {
        const int32_t got = core.host.read_at(core.host.ctx, name, length, text + length, kClocksRead - length);
        if (got < 0) return -1;
        if (static_cast<uint32_t>(got) > kClocksRead - length) return -1;
        if (got == 0) return 1;
        length += static_cast<uint32_t>(got);
    }
    return -1;
}

// Closes and verifies the complete part before atomically publishing both settings.
bool write_file(Core &core, uint8_t clocks, bool message) {
    const odrig_host &host = core.host;
    if (host.write == nullptr || host.write_close == nullptr || host.rename == nullptr || host.write_open(host.ctx, kClocksPart) != 1) {
        return false;
    }
    uint8_t text[kClocksRead];
    uint32_t length = 0;
    const char *mode = clocks == kClocksOnly ? "mode only\n" : clocks == kClocksBetween ? "mode between\n" : "mode off\n";
    const char *lines[3] = {kClocksHeader, mode, message ? "message on\n" : "message off\n"};
    for (const char *line : lines) {
        for (uint32_t at = 0; line[at] != '\0'; ++at) {
            text[length++] = static_cast<uint8_t>(line[at]);
        }
    }
    const bool written = host.write(host.ctx, text, length) == 1;
    if (host.write_close(host.ctx) != 1 || !written) return false;
    uint8_t verified[kClocksRead];
    uint32_t verified_length = 0;
    return read_file(core, kClocksPart, verified, verified_length) == 1 && verified_length == length &&
        memcmp(text, verified, length) == 0 && host.rename(host.ctx, kClocksPart, kClocksFile) == 1;
}

}  // namespace

static bool load_settings(Core &core) {
    uint8_t text[kClocksRead];
    uint32_t length = 0;
    const int read = read_file(core, kClocksFile, text, length);
    bool sound = read == 1;
    uint32_t at = 0;
    uint8_t clocks = kClocksOff;
    bool message = false;
    if (sound && takes(text, length, &at, kClocksHeader)) {
        if (takes(text, length, &at, "mode only\n")) clocks = kClocksOnly;
        else if (takes(text, length, &at, "mode between\n")) clocks = kClocksBetween;
        else if (!takes(text, length, &at, "mode off\n")) sound = false;
    } else if (sound && takes(text, length, &at, kLegacyHeader)) {
        if (takes(text, length, &at, "clocks on\n")) clocks = kClocksBetween;
        else if (!takes(text, length, &at, "clocks off\n")) sound = false;
    } else {
        sound = false;
    }
    if (sound && takes(text, length, &at, "message on\n")) {
        message = true;
    } else if (!(sound && takes(text, length, &at, "message off\n"))) {
        sound = false;
    }
    if (!sound || at != length) {
        return false;
    }
    core.clocks_on = clocks;
    core.clock_message_on = message ? 1 : 0;
    return true;
}

void breaks_start(Core &core) {
    core.clocks_on = kClocksOff;
    core.clock_message_on = 0;
    core.clocks_error = 0;
    core.clocks_retry = 0;
    core.clocks_first = core.clocks_last = core.clocks_files = 0;
    core.message_first = core.message_files = 0;
    core.clocks_id = 0;
    core.clocks_ordinal = kNoFolder;
    core.order_key = core.order_next = core.order_count = 0;
    core.message_order_key = core.message_order_next = core.message_order_count = 0;
    core.only_dirty = 1;
    if (!storage_changes(core) || core.host.read_at == nullptr) return;
    uint8_t part;
    if (core.host.read_at(core.host.ctx, kClocksPart, 0, &part, 1) >= 0) {
        core.host.remove(core.host.ctx, kClocksPart);
    }
    const int opened = core.host.open(core.host.ctx, kClocksFile);
    if (opened == 1) core.host.close(core.host.ctx);
    if (opened == 0) return;
    if (opened == 1 && load_settings(core)) return;
    core.clocks_on = kClocksOnly;
    core.clocks_error = 1;
    core.clocks_retry = core.latest + 1000;
    if (core.host.log != nullptr) core.host.log(core.host.ctx, "clocks unreadable");
}

void breaks_poll(Core &core, uint64_t now) {
    if (!core.clocks_error || now < core.clocks_retry) return;
    core.clocks_retry = now + 1000;
    const uint8_t previous = core.clocks_on;
    if (!load_settings(core)) return;
    core.clocks_error = 0;
    player_clock_mode_changed(core, previous);
}

uint32_t breaks_command(Core &core, bool message, uint8_t value, Reply &reply) {
    if (core.invalid) {
        return refuse(reply, "show-invalid");
    }
    if (catalog_rebuilding(core) || !check_complete(core) || core.upload.state != kUploadNone) {
        return refuse(reply, "busy");
    }
    if (!storage_changes(core) || core.host.read_at == nullptr) {
        return refuse(reply, "storage-error");
    }
    const uint8_t clocks = message ? core.clocks_on : value;
    const bool after = message ? value != 0 : core.clock_message_on != 0;
    if (message && core.clocks_error) return refuse(reply, "storage-error");
    if (!core.clocks_error && clocks == core.clocks_on && after == (core.clock_message_on != 0)) {
        return succeed(reply);
    }
    if (!write_file(core, clocks, after)) {
        core.host.remove(core.host.ctx, kClocksPart);
        return refuse(reply, "storage-error");
    }
    const uint8_t previous = core.clocks_on;
    if (clocks == kClocksOnly && previous != kClocksOnly) mapping_test_stop(core);
    if (clocks != kClocksOff && previous == kClocksOff) {
        player_counts_start(core, core.latest);
    }
    if (message && value != 0 && core.break_phase == kBreakClock) {
        core.break_message = 1;
    }
    core.clocks_on = clocks;
    core.clock_message_on = after ? 1 : 0;
    const bool was_uncertain = core.clocks_error != 0;
    core.clocks_error = 0;
    if (was_uncertain || previous != clocks) player_clock_mode_changed(core, previous);
    return succeed(reply);
}

void breaks_tree(Core &core) {
    core.clocks_first = core.clocks_last = core.clocks_files = 0;
    core.message_first = core.message_files = 0;
    core.clocks_id = 0;
    core.clocks_ordinal = kNoFolder;
    core.order_next = core.order_count = 0;
    core.message_order_next = core.message_order_count = 0;
    core.only_dirty = 1;
    if (!core.tree_known) {
        return;
    }
    IndexFolder folder;
    uint32_t ordinal = drive_folder_with_path(core, "clocks");
    if (ordinal != kNoFolder && ordinal != 0 && drive_folder(core, ordinal, folder)) {
        core.clocks_first = folder.first;
        core.clocks_last = folder.last;
        core.clocks_files = folder.files;
        core.clocks_id = folder.id;
        core.clocks_ordinal = ordinal;
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

namespace {

// Whether an item of the show is an animation whose file is of a class.
bool of_kind(const Core &core, uint32_t item, uint8_t kind) {
    return !core.items[item].is_cycle && core.files[core.items[item].first].clock == kind;
}

// The number of the show's animations of a class.
uint32_t kind_count(const Core &core, uint8_t kind) {
    uint32_t count = 0;
    for (uint32_t item = 0; item < core.item_count; ++item) {
        count += of_kind(core, item, kind) ? 1 : 0;
    }
    return count;
}

// The position of the show's n-th animation of a class, counted from 0 in the item table.
uint32_t kind_item(const Core &core, uint8_t kind, uint32_t nth) {
    for (uint32_t item = 0; item < core.item_count; ++item) {
        if (of_kind(core, item, kind) && nth-- == 0) {
            return item;
        }
    }
    return kNothing;
}

// Whether two names are the same but for the case of ASCII letters.
bool same_name(const char *one, const char *other) {
    for (;; ++one, ++other) {
        char a = *one;
        char b = *other;
        a = a >= 'A' && a <= 'Z' ? static_cast<char>(a - 'A' + 'a') : a;
        b = b >= 'A' && b <= 'Z' ? static_cast<char>(b - 'A' + 'a') : b;
        if (a != b) {
            return false;
        }
        if (a == '\0') {
            return true;
        }
    }
}

// Whether a text begins with another.
bool begins_with(const char *text, const char *head) {
    for (; *head != 0; ++text, ++head) {
        if (*text != *head) {
            return false;
        }
    }
    return true;
}

// Marks the show's files of a class that are copies of a file of the card's folder of that
// class that plays automatically: the same name in any case after the folder's path, and
// the same known type. Every other file of the class is unmarked. The card's `count` files
// from `first` on are each read once.
ODRIG_NOINLINE void mark_copies(Core &core, uint8_t kind, uint32_t first, uint32_t count) {
    for (uint32_t file = 0; file < core.file_count; ++file) {
        if (core.files[file].clock == kind) {
            core.files[file].copy = 0;
        }
    }
    const char *folder = kind == kClockMessage ? "clocks/message/" : "clocks/";
    const uint32_t length = kind == kClockMessage ? 15 : 7;
    for (uint32_t at = 0; at < count; ++at) {
        if (!drive_automatic(core, first + at)) {
            continue;
        }
        const DriveRow *row = drive_row(core, first + at);
        if (row == nullptr || row->type < kTypeFrames || row->type > kTypeWidget || !begins_with(row->name, folder)) {
            continue;
        }
        for (uint32_t file = 0; file < core.file_count; ++file) {
            FileInfo &info = core.files[file];
            if (info.clock == kind && info.type == row->type && same_name(stored_base(info.name), row->name + length)) {
                info.copy = 1;
            }
        }
    }
}

// The next clock or message in its bag: the card's files of its folder, then the show's
// animations of its class. A card's file is taken when it plays automatically; one of the
// show's when it plays and, while the card's copies are preferred, is no copy of a card's
// file that plays, which the draw marks once, the first time it comes to one of them.
uint32_t pick(Core &core, uint64_t at, bool message) {
    const uint8_t kind = message ? kClockMessage : kClockFace;
    const uint32_t first = message ? core.message_first : core.clocks_first;
    const uint32_t external = message ? core.message_files : core.clocks_files;
    const uint32_t count = external + kind_count(core, kind);
    uint32_t &key = message ? core.message_order_key : core.order_key;
    uint32_t &next = message ? core.message_order_next : core.order_next;
    uint32_t &size = message ? core.message_order_count : core.order_count;
    bool marked = false;
    // At most two whole orders are tried: what is left of this one, and a new one.
    for (uint32_t tried = 0; count != 0 && tried < 2 * count; ++tried) {
        if (next >= size || size != count) {
            key = clock_seed(core.noise ^ (message ? 0x9E3779B9u : 0u), count, at);
            size = count;
            next = 0;
        }
        const uint32_t place = clock_shuffle(key, size, next++);
        if (place < external) {
            if (drive_automatic(core, first + place)) {
                return kDriveBase + first + place;
            }
            continue;
        }
        const uint32_t item = kind_item(core, kind, place - external);
        if (item == kNothing || !player_plays(core, item)) {
            continue;
        }
        if (!core.clock_storage_internal) {
            if (!marked) {
                mark_copies(core, kind, first, external);
                marked = true;
            }
            if (core.files[core.items[item].first].copy) {
                continue;
            }
        }
        return item;
    }
    return kNothing;
}

}  // namespace

uint32_t breaks_pick(Core &core, uint64_t at) { return core.clocks_error ? kNothing : pick(core, at, false); }
uint32_t breaks_message(Core &core, uint64_t at) { return core.clocks_error ? kNothing : pick(core, at, true); }

const char *breaks_mode(const Core &core) {
    return core.clocks_on == kClocksOnly ? "only" : core.clocks_on == kClocksBetween ? "between" : "off";
}

const char *breaks_only_state(const Core &core) {
    if (core.clocks_internal_id != 0) return core.playing == kNothing ? "no-clocks" : "playing";
    if (core.drive_number == 0) return "no-card";
    if (core.clocks_id == 0) return "missing-folder";
    return core.playing == kNothing ? "no-clocks" : "playing";
}

bool breaks_position_allowed(const Core &core, uint32_t position) {
    if (core.clocks_error) return false;
    if (core.clocks_on != kClocksOnly) return true;
    if (!is_drive(position)) {
        return position < core.item_count && !core.items[position].is_cycle && core.files[core.items[position].first].clock != kNotClock;
    }
    return core.clocks_id != 0 && position - kDriveBase >= core.clocks_first && position - kDriveBase < core.clocks_last;
}

bool breaks_folder_allowed(const Core &core, uint32_t ordinal) {
    if (core.clocks_error) return false;
    if (core.clocks_on != kClocksOnly) return true;
    IndexFolder clocks;
    return core.clocks_id != 0 && drive_folder(core, core.clocks_ordinal, clocks) && ordinal >= clocks.ordinal && ordinal < clocks.end;
}

bool breaks_has_face(const Core &core) {
    for (uint32_t i = 0; i < core.clocks_files; ++i) {
        if (drive_automatic(core, core.clocks_first + i)) return true;
    }
    for (uint32_t item = 0; item < core.item_count; ++item) {
        if (of_kind(core, item, kClockFace) && player_plays(core, item)) return true;
    }
    return false;
}

}  // namespace odrig
