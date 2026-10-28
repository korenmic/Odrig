#include "drive.h"

#include <string.h>

#include "catalog.h"
#include "container.h"
#include "fields.h"
#include "json_reader.h"

namespace odrig {

const char kIndexTable[] = "drive/index-folders.txt";
const char kIndexTableNew[] = "drive/index-folders.new";
const char kIndexMap[] = "drive/index-ids.txt";
const char kIndexMapNew[] = "drive/index-ids.new";

void index_folder_name(uint32_t id, bool fresh, char *into) {
    uint8_t *made = reinterpret_cast<uint8_t *>(into);
    uint32_t length = 0;
    put_text(made, &length, "drive/index-");
    put_decimal(made, &length, id);
    put_text(made, &length, fresh ? ".new" : ".txt");
    into[length] = '\0';
}

const char *index_line(const Core &core, const char *name, uint32_t width, uint32_t number, uint32_t *length) {
    DriveIndex &cursor = *core.index;
    if (number >= 0xFFFFFFFFu / width) {
        return nullptr;
    }
    const uint32_t offset = number * width;
    const bool held = same_text(cursor.room_name, name) && offset >= cursor.room_offset && offset - cursor.room_offset + width <= cursor.room_length;
    if (!held) {
        // As many whole lines as the room holds, from this one on, in one read or more.
        cursor.room_name[0] = '\0';
        const uint32_t want = kFileBufferSize / width * width;
        uint32_t got = 0;
        while (got < want) {
            const int32_t count = core.host.read_at(core.host.ctx, name, offset + got, cursor.room + got, want - got);
            if (count < 0) {
                return nullptr;
            }
            if (count == 0) {
                break;
            }
            got += static_cast<uint32_t>(count);
        }
        if (got < width || text_length(name) >= kIndexNameRoom) {
            return nullptr;
        }
        copy_text(cursor.room_name, name);
        cursor.room_offset = offset;
        cursor.room_length = got;
    }
    const char *text = reinterpret_cast<const char *>(cursor.room) + (offset - cursor.room_offset);
    if (text[width - 1] != '\n') {
        return nullptr;
    }
    uint32_t end = width - 1;
    for (uint32_t at = 0; at < end; ++at) {
        if (text[at] < 0x20 || text[at] > 0x7E) {
            return nullptr;
        }
    }
    while (end > 0 && text[end - 1] == ' ') {
        --end;
    }
    if (end == 0) {
        return nullptr;
    }
    *length = end;
    return text;
}

void index_forget(const Core &core) {
    if (core.index == nullptr) {
        return;
    }
    DriveIndex &cursor = *core.index;
    cursor.room_name[0] = '\0';
    cursor.room_length = 0;
    cursor.rows[0].position = kNothing;
    cursor.rows[1].position = kNothing;
    cursor.walking.files = 0;
}

namespace {

// Copies a path of a line, 1 to 100 bytes, into room for kDrivePathRoom with its 0.
bool take_path(const char *line, uint32_t from, uint32_t length, char *into) {
    if (from >= length || length - from > kDrivePathRoom - 1) {
        return false;
    }
    memcpy(into, line + from, length - from);
    into[length - from] = '\0';
    return true;
}

// The depth of a path: its parts less one, the folders it is in.
uint32_t depth_of(const char *path, uint32_t length) {
    uint32_t slashes = 0;
    for (uint32_t at = 0; at < length; ++at) {
        slashes += path[at] == '/' ? 1 : 0;
    }
    return slashes;
}

}  // namespace

bool index_parse_folder(const char *line, uint32_t length, uint32_t ordinal, IndexFolder &folder, uint32_t *path_at, uint32_t *path_length) {
    uint32_t at = 0;
    uint32_t number = 0;
    uint32_t depth = 0;
    if (!decimal32(line, &at, &number) || number != ordinal || !word(line, &at, " ") || !decimal32(line, &at, &folder.id) || !word(line, &at, " ") ||
        !decimal32(line, &at, &depth) || depth > kCatalogDeepest || !word(line, &at, " ") || !decimal32(line, &at, &folder.end) || !word(line, &at, " ") ||
        !decimal32(line, &at, &folder.first) || !word(line, &at, " ") || !decimal32(line, &at, &folder.files) || !word(line, &at, " ") ||
        !decimal32(line, &at, &folder.folders) || !word(line, &at, " ") || !hexadecimal(line, &at, 8, &folder.crc)) {
        return false;
    }
    folder.ordinal = ordinal;
    folder.depth = static_cast<uint8_t>(depth);
    folder.last = folder.first;
    if (at == length) {
        // The root: no path, the id 0 and the depth 0, and only it.
        *path_at = length;
        *path_length = 0;
        return ordinal == 0 && folder.id == 0 && depth == 0 && folder.end > 0;
    }
    if (!word(line, &at, " ") || at >= length || length - at > kDrivePathRoom - 1) {
        return false;
    }
    *path_at = at;
    *path_length = length - at;
    return ordinal != 0 && folder.id >= kDriveFirstId && depth == depth_of(line + at, length - at) + 1 && folder.end > ordinal;
}

bool index_parse_row(const char *line, uint32_t length, DriveRow &row) {
    uint32_t at = 0;
    if (!decimal32(line, &at, &row.id) || row.id < kDriveFirstId || !word(line, &at, " ")) {
        return false;
    }
    if (word(line, &at, "d ")) {
        row.kind = 'd';
        row.crc = 0;
        row.bytes = 0;
        row.total_ms = 0;
        row.width = 0;
        row.height = 0;
        row.type = kTypeFrames;
        return decimal32(line, &at, &row.files) && word(line, &at, " ") && take_path(line, at, length, row.name);
    }
    uint64_t width = 0;
    uint64_t height = 0;
    uint64_t total_ms = 0;
    if (!word(line, &at, "f ") || !hexadecimal(line, &at, 8, &row.crc) || !word(line, &at, " ") || !decimal32(line, &at, &row.bytes) || !word(line, &at, " ") ||
        !decimal(line, &at, 5, 65535, &width) || width == 0 || !word(line, &at, " ") || !decimal(line, &at, 5, 65535, &height) || height == 0 ||
        !word(line, &at, " ") || !decimal(line, &at, 20, 0xFFFFFFFFFFFFFFFFull, &total_ms) || !word(line, &at, " ")) {
        return false;
    }
    row.total_ms = drive_length(total_ms);
    if (word(line, &at, "frames ")) {
        row.type = kTypeFrames;
    } else if (word(line, &at, "text ")) {
        row.type = kTypeText;
    } else if (word(line, &at, "widget ")) {
        row.type = kTypeWidget;
    } else {
        return false;
    }
    row.kind = 'f';
    row.files = 0;
    row.width = static_cast<uint16_t>(width);
    row.height = static_cast<uint16_t>(height);
    return take_path(line, at, length, row.name) && catalog_name_allowed(row.name, length - at);
}

bool index_parse_id(const char *line, uint32_t length, uint32_t *id, uint8_t *kind, uint32_t *ordinal, uint32_t *row) {
    uint32_t at = 0;
    if (!decimal32(line, &at, id) || *id < kDriveFirstId || !word(line, &at, " ")) {
        return false;
    }
    if (word(line, &at, "f ")) {
        *kind = 'f';
    } else if (word(line, &at, "d ")) {
        *kind = 'd';
    } else {
        return false;
    }
    return decimal32(line, &at, ordinal) && word(line, &at, " ") && decimal32(line, &at, row) && at == length;
}

namespace {

// Whether the drive is read from its index now.
bool indexed(const Core &core) {
    return core.drive != nullptr && core.index != nullptr && core.drive_number != 0 && core.indexed;
}

// The index can no longer be read: the drive's catalog is taken for damaged at the next
// refresh.
void broken(const Core &core) {
    core.index->broken = 1;
}

// The slot of the cursor to read a row into: the one not read the latest.
DriveRow &free_slot(const Core &core) {
    DriveIndex &cursor = *core.index;
    cursor.latest = cursor.latest == 0 ? 1 : 0;
    return cursor.rows[cursor.latest];
}

// Reads line `number` of the table into a folder, with its path when `path` is given; the
// position after its subtree's files from the line at its `end`. False when it cannot be.
bool table_folder(const Core &core, uint32_t ordinal, IndexFolder &folder, char *path) {
    const DriveIndex &cursor = *core.index;
    if (ordinal >= cursor.folders) {
        return false;
    }
    uint32_t length = 0;
    const char *line = index_line(core, kIndexTable, kIndexRow, ordinal, &length);
    uint32_t path_at = 0;
    uint32_t path_length = 0;
    if (line == nullptr || !index_parse_folder(line, length, ordinal, folder, &path_at, &path_length) || folder.end > cursor.folders ||
        folder.first > cursor.files || folder.files > cursor.files - folder.first) {
        broken(core);
        return false;
    }
    if (path != nullptr) {
        memcpy(path, line + path_at, path_length);
        path[path_length] = '\0';
    }
    if (folder.end >= cursor.folders) {
        folder.last = cursor.files;
        return true;
    }
    IndexFolder after;
    line = index_line(core, kIndexTable, kIndexRow, folder.end, &length);
    if (line == nullptr || !index_parse_folder(line, length, folder.end, after, &path_at, &path_length) || after.first < folder.first ||
        after.first > cursor.files) {
        broken(core);
        return false;
    }
    folder.last = after.first;
    return true;
}

// The ordinal of the folder of the index whose own files hold a position: the last folder
// of the table whose first position is at or before it, found by binary search.
uint32_t index_folder_of(const Core &core, uint32_t position) {
    DriveIndex &cursor = *core.index;
    if (cursor.walking.files != 0 && position >= cursor.walking.first && position - cursor.walking.first < cursor.walking.files) {
        return cursor.walking.ordinal;
    }
    uint32_t low = 0;
    uint32_t high = cursor.folders;
    while (high - low > 1) {
        const uint32_t middle = low + (high - low) / 2;
        uint32_t length = 0;
        const char *line = index_line(core, kIndexTable, kIndexRow, middle, &length);
        IndexFolder folder;
        uint32_t path_at = 0;
        uint32_t path_length = 0;
        if (line == nullptr || !index_parse_folder(line, length, middle, folder, &path_at, &path_length)) {
            broken(core);
            return kNoFolder;
        }
        if (folder.first <= position) {
            low = middle;
        } else {
            high = middle;
        }
    }
    IndexFolder found;
    if (!table_folder(core, low, found, nullptr) || position < found.first || position - found.first >= found.files) {
        broken(core);
        return kNoFolder;
    }
    cursor.walking.ordinal = found.ordinal;
    cursor.walking.id = found.id;
    cursor.walking.first = found.first;
    cursor.walking.files = found.files;
    return low;
}

// The row of a file of a drive without a catalog at its place, into a slot.
const DriveRow *listed_row(const Core &core, uint32_t place) {
    const DriveEntry &entry = core.drive[place];
    DriveRow &row = free_slot(core);
    row.position = kNothing;
    row.kind = 'f';
    row.id = entry.id;
    row.crc = 0;
    row.bytes = entry.bytes;
    row.total_ms = entry.total_ms;
    row.files = 0;
    row.width = core.width;
    row.height = core.height;
    row.type = entry.type;
    row.fault = entry.state == kDriveLeftOut ? entry.fault : static_cast<uint8_t>(kNone);
    row.listed = entry.state == kDriveInPlaylist || (entry.state == kDriveLeftOut && entry.id != 0) ? 1 : 0;
    if (core.host.drive_name(core.host.ctx, core.drive_number, place, row.name, sizeof row.name) != 1) {
        drive_file_name(place, row.name);
    }
    return &row;
}

// The index of a folder of the tree of a drive without a catalog: the root's own files are
// the places before the first sub-folder's.
uint32_t listed_root_files(const Core &core) {
    return core.tree_known && core.folders != nullptr && core.folder_count != 0 ? core.folders[1].first : core.drive_count;
}

}  // namespace

const Remembered *drive_remembered(const Core &core, const char *name, uint32_t crc) {
    for (uint32_t at = 0; core.remembered != nullptr && at < kRememberedMost; ++at) {
        const Remembered &one = core.remembered[at];
        if (one.reason == kNone || one.first_read != kRememberedWhole || one.crc != crc) {
            continue;
        }
        uint32_t index = 0;
        while (index + 1 < kFaultNameSize && name[index] != '\0' && one.name[index] == name[index]) {
            ++index;
        }
        if (one.name[index] == '\0' && (name[index] == '\0' || index + 1 == kFaultNameSize)) {
            return &one;
        }
    }
    return nullptr;
}

uint32_t drive_files(const Core &core) {
    if (core.drive == nullptr || core.drive_number == 0) {
        return 0;
    }
    return indexed(core) ? core.index->files : core.drive_count;
}

uint32_t drive_folder_count(const Core &core) {
    if (indexed(core)) {
        return core.index->folders;
    }
    return core.tree_known && core.folders != nullptr ? core.folder_count + 1 : 1;
}

const DriveRow *drive_row(const Core &core, uint32_t position) {
    if (core.drive == nullptr || core.index == nullptr || position >= drive_files(core)) {
        return nullptr;
    }
    if (!indexed(core)) {
        return listed_row(core, position);
    }
    DriveIndex &cursor = *core.index;
    for (uint32_t slot = 0; slot < 2; ++slot) {
        if (cursor.rows[slot].position == position) {
            cursor.latest = static_cast<uint8_t>(slot);
            return &cursor.rows[slot];
        }
    }
    const uint32_t ordinal = index_folder_of(core, position);
    if (ordinal == kNoFolder) {
        return nullptr;
    }
    char name[kIndexNameRoom];
    index_folder_name(cursor.walking.id, false, name);
    uint32_t length = 0;
    const char *line = index_line(core, name, kIndexRow, position - cursor.walking.first, &length);
    DriveRow &row = free_slot(core);
    row.position = kNothing;
    if (line == nullptr || !index_parse_row(line, length, row) || row.kind != 'f') {
        broken(core);
        return nullptr;
    }
    // A file of another canvas, and one that faulted in this boot, are left out.
    const Remembered *remembered = drive_remembered(core, row.name, row.crc);
    row.fault = static_cast<uint8_t>(row.width != core.width || row.height != core.height ? kSizeMismatch
                                     : remembered != nullptr ? static_cast<Reason>(remembered->reason) : kNone);
    row.listed = 1;
    row.position = position;
    return &row;
}

bool drive_plays(const Core &core, uint32_t position) {
    const DriveRow *row = drive_row(core, position);
    return row != nullptr && row->listed && row->fault == kNone;
}

bool drive_folder(const Core &core, uint32_t ordinal, IndexFolder &folder) {
    if (core.drive == nullptr || core.drive_number == 0 || ordinal >= drive_folder_count(core)) {
        return false;
    }
    if (indexed(core)) {
        return table_folder(core, ordinal, folder, nullptr);
    }
    const uint32_t count = drive_folder_count(core);
    folder.ordinal = ordinal;
    folder.crc = 0;
    if (ordinal == 0) {
        folder.id = 0;
        folder.depth = 0;
        folder.end = count;
        folder.first = 0;
        folder.files = listed_root_files(core);
        folder.last = core.drive_count;
    } else {
        const Folder &made = core.folders[ordinal];
        folder.id = made.id;
        folder.depth = made.depth;
        folder.end = made.end;
        folder.first = made.first;
        folder.files = made.files;
        folder.last = made.end < count ? core.folders[made.end].first : core.drive_count;
    }
    folder.folders = 0;
    for (uint32_t child = ordinal + 1; child < folder.end; child = core.folders[child].end) {
        ++folder.folders;
    }
    return true;
}

uint32_t drive_folder_path(const Core &core, uint32_t ordinal, char *into, uint32_t room) {
    into[0] = '\0';
    if (ordinal == 0 || ordinal >= drive_folder_count(core)) {
        return 0;
    }
    if (indexed(core)) {
        char path[kDrivePathRoom];
        IndexFolder folder;
        if (room < kDrivePathRoom || !table_folder(core, ordinal, folder, path)) {
            return 0;
        }
        return copy_text(into, path);
    }
    const Folder &made = core.folders[ordinal];
    if (core.host.drive_name(core.host.ctx, core.drive_number, made.first, into, room) != 1) {
        into[0] = '\0';
        return 0;
    }
    // The name of a file at or below the folder, cut to the folder's parts.
    uint32_t length = 0;
    uint32_t parts = 0;
    while (into[length] != '\0') {
        if (into[length] == '/' && ++parts == made.depth) {
            break;
        }
        ++length;
    }
    into[length] = '\0';
    return length;
}

const DriveRow *drive_subfolder(const Core &core, const IndexFolder &folder, uint32_t at) {
    if (at >= folder.folders) {
        return nullptr;
    }
    if (indexed(core)) {
        char name[kIndexNameRoom];
        index_folder_name(folder.id, false, name);
        uint32_t length = 0;
        const char *line = index_line(core, name, kIndexRow, folder.files + at, &length);
        DriveRow &row = free_slot(core);
        row.position = kNothing;
        if (line == nullptr || !index_parse_row(line, length, row) || row.kind != 'd') {
            broken(core);
            return nullptr;
        }
        row.fault = kNone;
        row.listed = 1;
        return &row;
    }
    uint32_t child = folder.ordinal + 1;
    for (uint32_t step = 0; step < at; ++step) {
        child = core.folders[child].end;
    }
    DriveRow &row = free_slot(core);
    row.position = kNothing;
    row.kind = 'd';
    row.id = core.folders[child].id;
    row.files = core.folders[child].files;
    row.fault = kNone;
    row.listed = 1;
    drive_folder_path(core, child, row.name, kDrivePathRoom);
    return &row;
}

uint32_t drive_folder_of(const Core &core, uint32_t position) {
    if (position >= drive_files(core)) {
        return kNoFolder;
    }
    if (indexed(core)) {
        return index_folder_of(core, position);
    }
    if (position < listed_root_files(core)) {
        return 0;
    }
    for (uint32_t folder = 1; core.folders != nullptr && folder <= core.folder_count; ++folder) {
        if (position >= core.folders[folder].first && position - core.folders[folder].first < core.folders[folder].files) {
            return folder;
        }
    }
    return kNoFolder;
}

uint8_t drive_find(const Core &core, uint32_t id, uint32_t *value) {
    if (core.drive == nullptr || core.drive_number == 0 || id < kDriveFirstId) {
        return 0;
    }
    if (!indexed(core)) {
        for (uint32_t place = 0; place < core.drive_count; ++place) {
            if (core.drive[place].id == id) {
                *value = place;
                return 'f';
            }
        }
        for (uint32_t folder = 1; core.tree_known && core.folders != nullptr && folder <= core.folder_count; ++folder) {
            if (core.folders[folder].id == id) {
                *value = folder;
                return 'd';
            }
        }
        return 0;
    }
    // The map is sorted by id: a binary search.
    uint32_t low = 0;
    uint32_t high = core.index->ids;
    while (low < high) {
        const uint32_t middle = low + (high - low) / 2;
        uint32_t length = 0;
        const char *line = index_line(core, kIndexMap, kIndexIdRow, middle, &length);
        uint32_t found = 0;
        uint8_t kind = 0;
        uint32_t ordinal = 0;
        uint32_t row = 0;
        if (line == nullptr || !index_parse_id(line, length, &found, &kind, &ordinal, &row)) {
            broken(core);
            return 0;
        }
        if (found == id) {
            if (kind == 'd') {
                *value = ordinal;
                return ordinal != 0 && ordinal < core.index->folders ? 'd' : 0;
            }
            IndexFolder folder;
            if (!table_folder(core, ordinal, folder, nullptr) || row >= folder.files) {
                broken(core);
                return 0;
            }
            *value = folder.first + row;
            return 'f';
        }
        if (found < id) {
            low = middle + 1;
        } else {
            high = middle;
        }
    }
    return 0;
}

bool drive_open_name(const Core &core, uint32_t position, char *into) {
    if (position >= drive_files(core)) {
        return false;
    }
    if (!indexed(core)) {
        drive_file_name(position, into);
        return true;
    }
    const DriveRow *row = drive_row(core, position);
    if (row == nullptr) {
        return false;
    }
    memcpy(into, "drive/", 6);
    copy_text(into + 6, row->name);
    return true;
}

uint32_t drive_folder_with_path(const Core &core, const char *path) {
    if (path[0] == '\0') {
        return 0;
    }
    const uint32_t count = drive_folder_count(core);
    char found[kDrivePathRoom];
    for (uint32_t ordinal = 1; ordinal < count; ++ordinal) {
        if (drive_folder_path(core, ordinal, found, sizeof found) != 0 && same_text(found, path)) {
            return ordinal;
        }
    }
    return kNoFolder;
}

}  // namespace odrig
