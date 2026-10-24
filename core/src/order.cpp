#include "order.h"

#include <string.h>

#include "arena.h"
#include "crc32.h"
#include "storage.h"

namespace odrig {

namespace {

const char kOrderHeader[] = "odrig-order 1";
const uint32_t kUnnamedItem = 0x10000u;
const uint32_t kUnnamedPlace = 0x20000u;

// What a reading of the file sets: the keys of the internal animations, of the drive's, or
// both.
const uint8_t kReadItems = 1;
const uint8_t kReadDrive = 2;

// The low byte of the FNV-1a hash of a name of so many bytes.
uint8_t name_hash(const char *name, uint32_t length) {
    uint32_t hash = 2166136261u;
    for (uint32_t at = 0; at < length; ++at) {
        hash = (hash ^ static_cast<uint8_t>(name[at])) * 16777619u;
    }
    return static_cast<uint8_t>(hash);
}

// The id of an entry `i <id>`: decimal digits, 1 to 65,535, without a leading zero; 0 for
// anything else.
uint32_t entry_id(const char *text, uint32_t length) {
    if (length == 0 || length > 5 || text[0] == '0') {
        return 0;
    }
    uint32_t id = 0;
    for (uint32_t at = 0; at < length; ++at) {
        if (text[at] < '0' || text[at] > '9') {
            return 0;
        }
        id = id * 10 + static_cast<uint32_t>(text[at] - '0');
    }
    return id <= 65535 ? id : 0;
}

// Whether the file at a place of the drive has this name, as the drive gives it.
bool place_named(const Core &core, uint32_t place, const char *name, uint32_t length) {
    char found[kDriveListedName];
    if (core.host.drive_name(core.host.ctx, core.drive_number, place, found, sizeof found) != 1) {
        return false;
    }
    uint32_t size = 0;
    while (found[size] != '\0') {
        ++size;
    }
    return size == length && memcmp(found, name, length) == 0;
}

// One whole line of the file, without its line feed.
void take_line(Core &core, uint8_t what) {
    OrderReader &reader = core.order_reader;
    const char *line = reader.line;
    const uint32_t length = reader.length;
    if (reader.header == 0) {
        const bool header = length == sizeof kOrderHeader - 1 && memcmp(line, kOrderHeader, length) == 0;
        reader.header = header ? 1 : 2;
        return;
    }
    if (reader.header != 1 || reader.entries >= kOrderMost || length < 3 || line[1] != ' ') {
        return;
    }
    if (line[0] == 'i') {
        const uint32_t id = entry_id(line + 2, length - 2);
        if (id == 0) {
            return;
        }
        const uint16_t entry = static_cast<uint16_t>(reader.entries++);
        for (uint32_t position = 0; (what & kReadItems) != 0 && position < core.item_count; ++position) {
            if (core.items[position].id == id) {
                if (!core.items[position].is_cycle && core.order_items[position] == kOrderUnnamed) {
                    core.order_items[position] = entry;
                }
                break;
            }
        }
        return;
    }
    if (line[0] == 'x') {
        const char *name = line + 2;
        const uint32_t size = length - 2;
        for (uint32_t at = 0; at < size; ++at) {
            if (name[at] == '\0') {
                return;
            }
        }
        const uint16_t entry = static_cast<uint16_t>(reader.entries++);
        if ((what & kReadDrive) == 0 || core.order_drive == nullptr) {
            return;
        }
        const uint8_t hash = name_hash(name, size);
        for (uint32_t place = 0; place < core.drive_count; ++place) {
            if (core.order_hash[place] == hash && core.order_drive[place] == kOrderUnnamed && place_named(core, place, name, size)) {
                core.order_drive[place] = entry;
                break;
            }
        }
    }
}

// Takes one byte of the file.
void take_byte(Core &core, uint8_t byte, uint8_t what) {
    OrderReader &reader = core.order_reader;
    if (byte == '\n') {
        if (!reader.over) {
            take_line(core, what);
        }
        reader.length = 0;
        reader.over = 0;
    } else if (reader.length < kOrderLineRoom - 1) {
        reader.line[reader.length++] = static_cast<char>(byte);
    } else {
        reader.over = 1;
    }
}

void reader_clear(Core &core) {
    core.order_reader.entries = 0;
    core.order_reader.length = 0;
    core.order_reader.header = 0;
    core.order_reader.over = 0;
}

void clear_items(Core &core) {
    for (uint32_t position = 0; position < core.item_capacity; ++position) {
        core.order_items[position] = kOrderUnnamed;
    }
}

void clear_drive(Core &core) {
    for (uint32_t place = 0; core.order_drive != nullptr && place < kDriveMost; ++place) {
        core.order_drive[place] = kOrderUnnamed;
    }
}

// Reads the whole file at once through the second source and sets the keys it names. A
// file that is not there, or cannot be read, names nothing more.
void read_whole(Core &core, uint8_t what) {
    FileSource &source = core.checker->file;
    source.open_at(core.host, kOrderFile);
    reader_clear(core);
    int got;
    while ((got = source.get()) >= 0) {
        take_byte(core, static_cast<uint8_t>(got), what);
    }
    source.close();
}

// Whether an animation of the playlist is listed by `list`: every animation item, and the
// drive's animations that are in the playlist.
bool listed(const Core &core, uint32_t position) {
    if (is_drive(position)) {
        const uint32_t place = position - kDriveBase;
        return core.drive != nullptr && place < core.drive_count && core.drive[place].state == kDriveInPlaylist;
    }
    return position < core.item_count && !core.items[position].is_cycle;
}

// The id of a listed animation.
uint32_t id_of(const Core &core, uint32_t position) {
    return is_drive(position) ? core.drive[position - kDriveBase].id : core.items[position].id;
}

// The listed animation with the smallest key above `after`, or kNothing.
uint32_t listed_after(const Core &core, uint64_t after, bool any) {
    uint32_t best = kNothing;
    uint32_t best_key = 0;
    const uint32_t places = core.drive != nullptr ? core.drive_count : 0;
    for (uint32_t at = 0; at < core.item_count + places; ++at) {
        const uint32_t position = at < core.item_count ? at : kDriveBase + (at - core.item_count);
        if (!listed(core, position)) {
            continue;
        }
        const uint32_t key = order_key(core, position);
        if ((any || key > after) && (best == kNothing || key < best_key)) {
            best = position;
            best_key = key;
        }
    }
    return best;
}

uint32_t digits(uint64_t value) {
    uint32_t count = 1;
    while (value >= 10) {
        value /= 10;
        ++count;
    }
    return count;
}

}  // namespace

bool order_begin(Core &core) {
    if (!storage_changes(core) || core.checker == nullptr) {
        return true;
    }
    const uint32_t places = core.drive != nullptr ? kDriveMost : 0;
    uint8_t *block = static_cast<uint8_t *>(arena_take(core, core.item_capacity * 2 + places * 3));
    if (block == nullptr) {
        return false;
    }
    core.order_items = reinterpret_cast<uint16_t *>(block);
    clear_items(core);
    if (places != 0) {
        core.order_drive = reinterpret_cast<uint16_t *>(block + core.item_capacity * 2);
        core.order_hash = block + core.item_capacity * 2 + places * 2;
        clear_drive(core);
    }
    return true;
}

uint32_t order_key(const Core &core, uint32_t position) {
    if (is_drive(position)) {
        const uint32_t place = position - kDriveBase;
        const uint16_t entry = core.order_drive != nullptr ? core.order_drive[place] : kOrderUnnamed;
        return entry != kOrderUnnamed ? entry : kUnnamedPlace + place;
    }
    const uint16_t entry = core.order_items != nullptr ? core.order_items[position] : kOrderUnnamed;
    return entry != kOrderUnnamed ? entry : kUnnamedItem + position;
}

void order_start(Core &core) {
    if (core.order_items == nullptr) {
        return;
    }
    clear_items(core);
    read_whole(core, kReadItems);
}

void order_drive_named(Core &core, uint32_t place, const char *name) {
    if (core.order_hash == nullptr) {
        return;
    }
    uint32_t length = 0;
    while (name[length] != '\0') {
        ++length;
    }
    core.order_hash[place] = name_hash(name, length);
}

void order_drive_found(Core &core) {
    if (core.order_drive == nullptr) {
        return;
    }
    clear_drive(core);
    core.order_reading = 0;
    core.order_due = core.drive_count != 0 ? 1 : 0;
}

bool order_drive_due(const Core &core) {
    return core.order_due != 0;
}

void order_drive_step(Core &core) {
    FileSource &source = core.checker->file;
    if (!core.order_reading) {
        clear_drive(core);
        source.open_at(core.host, kOrderFile);
        reader_clear(core);
        core.order_reading = 1;
    }
    int got = source.get();
    while (got >= 0) {
        take_byte(core, static_cast<uint8_t>(got), kReadDrive);
        if (source.position >= source.length) {
            return;
        }
        got = source.get();
    }
    source.close();
    core.order_reading = 0;
    core.order_due = 0;
}

void order_drive_yields(Core &core) {
    if (core.order_reading) {
        core.checker->file.close();
        core.order_reading = 0;
    }
}

void order_reload(Core &core) {
    if (core.order_items == nullptr) {
        return;
    }
    drive_check_yields(core);
    clear_items(core);
    clear_drive(core);
    read_whole(core, kReadItems | kReadDrive);
    core.order_due = 0;
}

void order_item_leaves(Core &core, uint32_t position) {
    if (core.order_items == nullptr) {
        return;
    }
    memmove(core.order_items + position, core.order_items + position + 1, (core.item_count - position - 1) * sizeof(uint16_t));
    core.order_items[core.item_count - 1] = kOrderUnnamed;
}

void order_item_added(Core &core, uint32_t position) {
    if (core.order_items != nullptr) {
        core.order_items[position] = kOrderUnnamed;
    }
}

uint32_t order_get(const Core &core, uint32_t from, Reply &reply) {
    // The revision: each listed animation's id and key, in the order of `list`.
    uint32_t crc = kCrcStart;
    uint32_t total = 0;
    const uint32_t places = core.drive != nullptr ? core.drive_count : 0;
    for (uint32_t at = 0; at < core.item_count + places; ++at) {
        const uint32_t position = at < core.item_count ? at : kDriveBase + (at - core.item_count);
        if (!listed(core, position)) {
            continue;
        }
        ++total;
        const uint32_t id = id_of(core, position);
        const uint32_t key = order_key(core, position);
        crc = crc_add(crc, static_cast<uint8_t>(id));
        crc = crc_add(crc, static_cast<uint8_t>(id >> 8));
        for (uint32_t shift = 0; shift < 32; shift += 8) {
            crc = crc_add(crc, static_cast<uint8_t>(key >> shift));
        }
    }
    const uint32_t revision = crc_value(crc);

    reply.text("{\"ok\":true,\"ids\":[");
    // The tail: `],"next":<n>,"revision":<r>}` and a line feed, with room for any position.
    const uint32_t tail = 9 + 5 + 12 + digits(revision) + 2;
    uint32_t position = 0;
    uint32_t at = kNothing;
    uint32_t key = 0;
    bool first = true;
    for (; position < total; ++position) {
        at = listed_after(core, key, at == kNothing);
        key = order_key(core, at);
        if (position < from) {
            continue;
        }
        const uint32_t id = id_of(core, at);
        const uint32_t size = (first ? 0 : 1) + digits(id);
        if (!reply.fits(size + tail)) {
            break;
        }
        if (!first) {
            reply.text(",");
        }
        first = false;
        reply.number(id);
    }
    reply.text("],\"next\":");
    if (position < total) {
        reply.number(position);
    } else {
        reply.text("null");
    }
    reply.text(",\"revision\":");
    reply.number(revision);
    reply.text("}\n");
    return reply.length;
}

}  // namespace odrig
