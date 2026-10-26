#include "order.h"

#include <string.h>

#include "arena.h"
#include "catalog.h"
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
    } else if (reader.length < kOrderLineMost) {
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
// drive's animations that are in the playlist or left out for a fault with an id.
bool listed(const Core &core, uint32_t position) {
    if (is_drive(position)) {
        const uint32_t place = position - kDriveBase;
        if (core.drive == nullptr || place >= core.drive_count) {
            return false;
        }
        const DriveEntry &entry = core.drive[place];
        return entry.state == kDriveInPlaylist || (entry.state == kDriveLeftOut && entry.id != 0);
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
    // The block: a key for each item and for each place, a hash byte and a folder byte for
    // each place, the folder table and the room for the current playlist's path.
    const uint32_t places = core.drive != nullptr ? kDriveMost : 0;
    const uint32_t tree = places != 0 ? kFolderMost * sizeof(Folder) + kPlaylistPathRoom : 0;
    uint8_t *block = static_cast<uint8_t *>(arena_take(core, core.item_capacity * 2 + places * 4 + tree));
    if (block == nullptr) {
        return false;
    }
    core.order_items = reinterpret_cast<uint16_t *>(block);
    clear_items(core);
    if (places != 0) {
        core.order_drive = reinterpret_cast<uint16_t *>(block + core.item_capacity * 2);
        core.order_hash = block + core.item_capacity * 2 + places * 2;
        core.drive_folder = block + core.item_capacity * 2 + places * 3;
        core.folders = reinterpret_cast<Folder *>(block + core.item_capacity * 2 + places * 4);
        core.playlist_path = reinterpret_cast<char *>(block + core.item_capacity * 2 + places * 4 + kFolderMost * sizeof(Folder));
        core.playlist_path[0] = '\0';
        clear_drive(core);
        tree_clear(core);
    }
    return true;
}

namespace {

// A byte of a path as the listing's order ranks it: a `/` and the end below every other
// byte, so that a folder comes before the folders below it and siblings go by the bytes
// of their names.
int path_byte(char c) {
    return c == '/' || c == '\0' ? 0 : static_cast<unsigned char>(c);
}

// The length of the first `parts` parts of a path, without the `/` after them: of the
// whole path when it has no more parts.
uint32_t parts_length(const char *path, uint32_t parts) {
    if (parts == 0) {
        return 0;
    }
    uint32_t length = 0;
    uint32_t seen = 0;
    while (path[length] != '\0') {
        if (path[length] == '/' && ++seen == parts) {
            break;
        }
        ++length;
    }
    return length;
}

// Compares the first `a_parts` parts of one path with the first `b_parts` of another in
// the listing's order: negative when the first comes first, 0 when they are one path.
int paths_compare(const char *a, uint32_t a_parts, const char *b, uint32_t b_parts) {
    const uint32_t a_length = parts_length(a, a_parts);
    const uint32_t b_length = parts_length(b, b_parts);
    for (uint32_t at = 0; at < a_length && at < b_length; ++at) {
        const int difference = path_byte(a[at]) - path_byte(b[at]);
        if (difference != 0) {
            return difference;
        }
    }
    return a_length < b_length ? -1 : a_length > b_length ? 1 : 0;
}

// Compares the path of a folder of the table with the first `parts` parts of a name. A
// folder whose place has no name now comes first.
int folder_compare(const Core &core, uint32_t folder, const char *name, uint32_t parts) {
    if (folder == 0) {
        return parts == 0 ? 0 : -1;
    }
    char path[kDriveListedName];
    if (core.host.drive_name(core.host.ctx, core.drive_number, core.folders[folder].place, path, sizeof path) != 1) {
        return -1;
    }
    return paths_compare(path, core.folders[folder].depth, name, parts);
}

// The folder of the table whose path is the first `parts` parts of a name, or kFolderMost.
uint32_t find_folder(const Core &core, const char *name, uint32_t parts) {
    if (parts == 0) {
        return 0;
    }
    for (uint32_t folder = 1; folder <= core.folder_count; ++folder) {
        if (core.folders[folder].depth == parts && folder_compare(core, folder, name, parts) == 0) {
            return folder;
        }
    }
    return kFolderMost;
}

// Puts the folder of the first `parts` parts of a name into the table at its index in the
// listing's order, with this place as its; the folders after it move up by one, and so do
// the bytes of the places in them. Returns its index.
uint32_t insert_folder(Core &core, const char *name, uint32_t parts, uint32_t place) {
    uint32_t at = 1;
    while (at <= core.folder_count && folder_compare(core, at, name, parts) < 0) {
        ++at;
    }
    memmove(core.folders + at + 1, core.folders + at, (core.folder_count + 1 - at) * sizeof(Folder));
    Folder &made = core.folders[at];
    made.id = 0;
    made.place = static_cast<uint16_t>(place);
    made.depth = static_cast<uint8_t>(parts);
    made.end = 0;
    made.spare[0] = made.spare[1] = 0;
    ++core.folder_count;
    for (uint32_t other = 0; other < core.drive_count; ++other) {
        if (core.drive_folder[other] != kNoFolder && core.drive_folder[other] >= at) {
            ++core.drive_folder[other];
        }
    }
    if (core.current >= at) {
        ++core.current;
    }
    return at;
}

// The index after the last descendant of a folder: the folders after it are its
// descendants while they are deeper than it.
uint32_t subtree_end(const Core &core, uint32_t folder) {
    uint32_t end = folder + 1;
    while (end <= core.folder_count && core.folders[end].depth > core.folders[folder].depth) {
        ++end;
    }
    return end;
}

void set_ends(Core &core) {
    for (uint32_t folder = 0; folder <= core.folder_count; ++folder) {
        core.folders[folder].end = static_cast<uint8_t>(subtree_end(core, folder));
    }
}

// A place at or below a folder, or kDriveMost when none is.
uint32_t place_within(const Core &core, uint32_t folder) {
    const uint32_t end = subtree_end(core, folder);
    for (uint32_t place = 0; place < core.drive_count; ++place) {
        const uint8_t byte = core.drive_folder[place];
        if (byte != kNoFolder && byte >= folder && byte < end) {
            return place;
        }
    }
    return kDriveMost;
}

}  // namespace

void tree_clear(Core &core) {
    core.folder_count = 0;
    core.tree_known = 0;
    core.current = 0;
    if (core.folders == nullptr) {
        return;
    }
    for (uint32_t place = 0; place < kDriveMost; ++place) {
        core.drive_folder[place] = kNoFolder;
    }
    Folder &root = core.folders[0];
    root.id = 0;
    root.place = static_cast<uint16_t>(kDriveMost);
    root.depth = 0;
    root.end = 1;
    root.spare[0] = root.spare[1] = 0;
}

void tree_build(Core &core) {
    tree_clear(core);
    if (core.folders == nullptr || core.drive == nullptr || core.drive_number == 0) {
        return;
    }
    char name[kDriveListedName];
    for (uint32_t place = 0; place < core.drive_count; ++place) {
        DriveEntry &entry = core.drive[place];
        if (entry.state == kDriveGone || core.host.drive_name(core.host.ctx, core.drive_number, place, name, sizeof name) != 1) {
            continue;
        }
        uint32_t depth = 0;
        for (uint32_t at = 0; name[at] != '\0'; ++at) {
            depth += name[at] == '/' ? 1 : 0;
        }
        if (depth > kCatalogDeepest) {
            continue;
        }
        // The folders of the path that the table has, from the top down, and the index of
        // the deepest of them.
        uint32_t known = 0;
        uint32_t folder = 0;
        for (uint32_t parts = 1; parts <= depth; ++parts) {
            const uint32_t found = find_folder(core, name, parts);
            if (found == kFolderMost) {
                break;
            }
            known = parts;
            folder = found;
        }
        if (core.folder_count + (depth - known) > kFolderMost - 1) {
            entry.fault = kTooManyFolders;
            if (entry.state != kDriveStaged) {
                entry.state = kDriveLeftOut;
                drive_left_out(core, place, kTooManyFolders);
            }
            continue;
        }
        for (uint32_t parts = known + 1; parts <= depth; ++parts) {
            folder = insert_folder(core, name, parts, place);
        }
        core.drive_folder[place] = static_cast<uint8_t>(folder);
    }
    set_ends(core);
    // The folders' ids come after the files', in the order of the table.
    for (uint32_t folder = 1; folder <= core.folder_count; ++folder) {
        core.folders[folder].id = free_drive_id(core);
    }
    core.tree_known = 1;
    // The current playlist's folder, found from its path; a path that no folder of the
    // tree has makes the root current.
    core.current = 0;
    if (core.playlist_path[0] != '\0') {
        uint32_t parts = 1;
        for (const char *at = core.playlist_path; *at != '\0'; ++at) {
            parts += *at == '/' ? 1 : 0;
        }
        const uint32_t found = find_folder(core, core.playlist_path, parts);
        if (found != kFolderMost) {
            core.current = static_cast<uint8_t>(found);
        } else {
            core.playlist_path[0] = '\0';
        }
    }
}

void tree_place_gone(Core &core, uint32_t place) {
    if (core.folders == nullptr || !core.tree_known || place >= kDriveMost) {
        return;
    }
    core.drive_folder[place] = kNoFolder;
    for (uint32_t folder = core.folder_count; folder >= 1; --folder) {
        const uint32_t within = place_within(core, folder);
        if (within != kDriveMost) {
            if (core.folders[folder].place == place) {
                core.folders[folder].place = static_cast<uint16_t>(within);
            }
            continue;
        }
        // Nothing is at or below the folder: it leaves the table, and the bytes of the
        // places in the folders after it, and the current index, move down by one.
        memmove(core.folders + folder, core.folders + folder + 1, (core.folder_count - folder) * sizeof(Folder));
        --core.folder_count;
        for (uint32_t other = 0; other < core.drive_count; ++other) {
            if (core.drive_folder[other] != kNoFolder && core.drive_folder[other] > folder) {
                --core.drive_folder[other];
            }
        }
        if (core.current == folder) {
            // The current playlist is gone: the root is current.
            core.current = 0;
            core.playlist_path[0] = '\0';
        } else if (core.current > folder) {
            --core.current;
        }
    }
    set_ends(core);
}

uint32_t tree_folder_with_id(const Core &core, uint32_t id) {
    for (uint32_t folder = 1; core.folders != nullptr && core.tree_known && folder <= core.folder_count; ++folder) {
        if (core.folders[folder].id == id) {
            return folder;
        }
    }
    return kFolderMost;
}

void tree_choose(Core &core, uint32_t folder) {
    core.current = static_cast<uint8_t>(folder);
    if (core.playlist_path != nullptr) {
        tree_folder_path(core, folder, core.playlist_path, kPlaylistPathRoom);
    }
}

uint32_t tree_folder_path(const Core &core, uint32_t folder, char *into, uint32_t room) {
    into[0] = '\0';
    if (core.folders == nullptr || folder == 0 || folder > core.folder_count) {
        return 0;
    }
    if (core.host.drive_name(core.host.ctx, core.drive_number, core.folders[folder].place, into, room) != 1) {
        into[0] = '\0';
        return 0;
    }
    const uint32_t length = parts_length(into, core.folders[folder].depth);
    into[length] = '\0';
    return length;
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

namespace {

// The revision of the order: the CRC-32 of each listed animation's id, as two bytes, and
// key, as four, low byte first, in the order of `list`; and the number of them.
uint32_t revision_of(const Core &core, uint32_t *total) {
    uint32_t crc = kCrcStart;
    *total = 0;
    const uint32_t places = core.drive != nullptr ? core.drive_count : 0;
    for (uint32_t at = 0; at < core.item_count + places; ++at) {
        const uint32_t position = at < core.item_count ? at : kDriveBase + (at - core.item_count);
        if (!listed(core, position)) {
            continue;
        }
        ++*total;
        const uint32_t id = id_of(core, position);
        const uint32_t key = order_key(core, position);
        crc = crc_add(crc, static_cast<uint8_t>(id));
        crc = crc_add(crc, static_cast<uint8_t>(id >> 8));
        for (uint32_t shift = 0; shift < 32; shift += 8) {
            crc = crc_add(crc, static_cast<uint8_t>(key >> shift));
        }
    }
    return crc_value(crc);
}

// The listed animation with this id, or kNothing.
uint32_t listed_with(const Core &core, uint32_t id) {
    for (uint32_t position = 0; position < core.item_count; ++position) {
        if (core.items[position].id == id) {
            return core.items[position].is_cycle ? kNothing : position;
        }
    }
    const uint32_t place = core.drive != nullptr ? drive_place_holding(core, id) : kDriveMost;
    if (place < kDriveMost && listed(core, kDriveBase + place)) {
        return kDriveBase + place;
    }
    return kNothing;
}

// Whether an item of the show with this id is a cycle.
bool is_cycle_id(const Core &core, uint32_t id) {
    for (uint32_t position = 0; position < core.item_count; ++position) {
        if (core.items[position].id == id) {
            return core.items[position].is_cycle != 0;
        }
    }
    return false;
}

// The text of the next `order.txt` goes through the first kWriteRoom bytes of the chunk;
// the entries looked for while it is written, and a name of the drive, stand after them.
const uint32_t kWriteRoom = 1000;
const uint32_t kMovedLine = kWriteRoom;
const uint32_t kBeforeLine = kMovedLine + kOrderLineRoom;
const uint32_t kNameRoom = kBeforeLine + kOrderLineRoom;

struct OrderWriter {
    void bytes(const char *text, uint32_t length) {
        for (uint32_t at = 0; at < length && !failed; ++at) {
            core->chunk[used++] = static_cast<uint8_t>(text[at]);
            if (used == kWriteRoom) {
                flush();
            }
        }
    }

    void flush() {
        if (used != 0 && !failed && core->host.write(core->host.ctx, core->chunk, used) != 1) {
            failed = true;
        }
        used = 0;
    }

    // One entry and its line feed, when the file has room for it.
    void entry(const char *text, uint32_t length) {
        if (entries < kOrderMost) {
            bytes(text, length);
            bytes("\n", 1);
            ++entries;
        }
    }

    Core *core;
    uint32_t used;
    uint32_t entries;
    bool failed;
};

// The entry of a listed animation, written at `at` in the chunk: `i <id>` or `x <name>`.
// Returns its length.
uint32_t entry_of(Core &core, uint32_t position, uint32_t at) {
    char *line = reinterpret_cast<char *>(core.chunk + at);
    if (!is_drive(position)) {
        uint32_t id = core.items[position].id;
        char figures[5];
        uint32_t count = 0;
        do {
            figures[count++] = static_cast<char>('0' + id % 10);
            id /= 10;
        } while (id != 0);
        line[0] = 'i';
        line[1] = ' ';
        uint32_t length = 2;
        while (count != 0) {
            line[length++] = figures[--count];
        }
        return length;
    }
    line[0] = 'x';
    line[1] = ' ';
    if (core.host.drive_name(core.host.ctx, core.drive_number, position - kDriveBase, line + 2, kDriveListedName) != 1) {
        return 0;
    }
    uint32_t length = 2;
    while (line[length] != '\0') {
        ++length;
    }
    return length;
}

// What the writing of the next file knows: the entries of the moved animation and of the
// one it goes before, of these lengths in the chunk, 0 for `end`, and whether the moved one
// was written.
struct Move {
    uint32_t moved_length;
    uint32_t before_length;
    bool placed;
};

bool same_line(const Core &core, uint32_t at, uint32_t length, const char *text, uint32_t size) {
    return length != 0 && length == size && memcmp(core.chunk + at, text, size) == 0;
}

// Writes one entry of the next file: not the moved one where it stood, and the moved one
// before the entry it goes before.
void write_entry(Core &core, OrderWriter &out, Move &move, const char *text, uint32_t size) {
    if (same_line(core, kMovedLine, move.moved_length, text, size)) {
        return;
    }
    if (!move.placed && same_line(core, kBeforeLine, move.before_length, text, size)) {
        out.entry(reinterpret_cast<const char *>(core.chunk + kMovedLine), move.moved_length);
        move.placed = true;
    }
    out.entry(text, size);
}

// One whole line of the file as it is, given to the next file when it is an entry that
// still names something that can be there: every external name, and the ids of items.
void copy_line(Core &core, OrderWriter &out, Move &move) {
    OrderReader &reader = core.order_reader;
    const char *line = reader.line;
    const uint32_t length = reader.length;
    if (reader.header == 0) {
        reader.header = length == sizeof kOrderHeader - 1 && memcmp(line, kOrderHeader, length) == 0 ? 1 : 2;
        return;
    }
    if (reader.header != 1 || length < 3 || line[1] != ' ') {
        return;
    }
    if (line[0] == 'i') {
        const uint32_t id = entry_id(line + 2, length - 2);
        if (id != 0 && listed_with(core, id) != kNothing && !is_drive(listed_with(core, id))) {
            write_entry(core, out, move, line, length);
        }
    } else if (line[0] == 'x') {
        for (uint32_t at = 2; at < length; ++at) {
            if (line[at] == '\0') {
                return;
            }
        }
        write_entry(core, out, move, line, length);
    }
}

// Writes `order.part`: the entries of `order.txt` with the move made, and after them every
// listed animation the file did not name. False when the host could not take it.
bool write_part(Core &core, Move &move) {
    const odrig_host &host = core.host;
    if (host.write_open(host.ctx, kOrderPart) != 1) {
        return false;
    }
    OrderWriter out;
    out.core = &core;
    out.used = 0;
    out.entries = 0;
    out.failed = false;
    out.bytes(kOrderHeader, sizeof kOrderHeader - 1);
    out.bytes("\n", 1);

    drive_check_yields(core);
    FileSource &source = core.checker->file;
    source.open_at(host, kOrderFile);
    reader_clear(core);
    OrderReader &reader = core.order_reader;
    int got;
    while ((got = source.get()) >= 0) {
        if (got == '\n') {
            if (!reader.over) {
                copy_line(core, out, move);
            }
            reader.length = 0;
            reader.over = 0;
        } else if (reader.length < kOrderLineRoom - 1) {
            reader.line[reader.length++] = static_cast<char>(got);
        } else {
            reader.over = 1;
        }
    }
    source.close();
    if (got == -kReadError && reader.header != 0) {
        // A file that could be read in part is not written again from that part.
        host.write_close(host.ctx);
        return false;
    }

    const uint32_t places = core.drive != nullptr ? core.drive_count : 0;
    for (uint32_t at = 0; at < core.item_count + places; ++at) {
        const uint32_t position = at < core.item_count ? at : kDriveBase + (at - core.item_count);
        if (listed(core, position) && order_key(core, position) >= kUnnamedItem) {
            const uint32_t length = entry_of(core, position, kNameRoom);
            if (length != 0) {
                write_entry(core, out, move, reinterpret_cast<const char *>(core.chunk + kNameRoom), length);
            }
        }
    }
    if (!move.placed) {
        out.entry(reinterpret_cast<const char *>(core.chunk + kMovedLine), move.moved_length);
    }
    out.flush();
    return host.write_close(host.ctx) == 1 && !out.failed;
}

}  // namespace

uint32_t order_get(const Core &core, uint32_t from, Reply &reply) {
    uint32_t total = 0;
    const uint32_t revision = revision_of(core, &total);
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

uint32_t order_move(Core &core, uint32_t revision, uint32_t id, uint32_t before, Reply &reply) {
    if (core.invalid) {
        return refuse(reply, "show-invalid");
    }
    if (!check_complete(core) || core.upload.state != kUploadNone) {
        return refuse(reply, "busy");
    }
    const uint32_t moved = listed_with(core, id);
    const uint32_t target = before == 0 ? kNothing : listed_with(core, before);
    // A cycle and a folder of the drive's tree have ids and no place in the order.
    if ((moved == kNothing && !is_cycle_id(core, id) && tree_folder_with_id(core, id) == kFolderMost) ||
        (before != 0 && target == kNothing && !is_cycle_id(core, before) && tree_folder_with_id(core, before) == kFolderMost)) {
        return refuse(reply, "unknown-id");
    }
    if (moved == kNothing || (before != 0 && target == kNothing)) {
        return refuse(reply, "in-use");
    }
    uint32_t total = 0;
    if (revision != revision_of(core, &total)) {
        return refuse(reply, "order-conflict");
    }
    // Nothing changes when the animation already stands where it is to go.
    const uint32_t next = listed_after(core, order_key(core, moved), false);
    if (moved == target || next == target) {
        return succeed(reply);
    }
    if (core.order_items == nullptr || core.chunk == nullptr) {
        return refuse(reply, "storage-error");
    }
    Move move;
    move.moved_length = entry_of(core, moved, kMovedLine);
    move.before_length = target == kNothing ? 0 : entry_of(core, target, kBeforeLine);
    move.placed = false;
    const odrig_host &host = core.host;
    if (move.moved_length == 0 || (target != kNothing && move.before_length == 0) || !write_part(core, move) ||
        host.rename(host.ctx, kOrderPart, kOrderFile) != 1) {
        host.remove(host.ctx, kOrderPart);
        return refuse(reply, "storage-error");
    }
    order_reload(core);
    return succeed(reply);
}

}  // namespace odrig
