#include "folders.h"

#include <string.h>

#include "catalog.h"
#include "order.h"
#include "player.h"
#include "playlist.h"
#include "show.h"
#include "storage.h"

namespace odrig {

namespace {

const char kFoldersHeader[] = "odrig-folders 1 ";
const uint32_t kNoLine = 0xFFFFFFFFu;

// The bytes a new folder needs at least: the blocks of its folder of the storage, and its
// line.
const uint32_t kFolderSpace = 8192 + 106;

// The ids a new folder's id is looked for among, one bit each in the chunk buffer.
const uint32_t kIdBits = 8192;

// How a reading of `folders.txt` stands.
const uint8_t kScanReading = 0;
const uint8_t kScanEnded = 1;
const uint8_t kScanFailed = 2;
const uint8_t kScanDamaged = 3;

// The reading of `folders.txt` from its start, a line at a time, each read where the last
// ended. The bytes read and not used yet are in `buffer`; the line given last stands at its
// start, ended by a 0, with its path at `path`, until the next line is asked for. Each line
// is checked for its form and its depth, and its Ignore is carried down the depths; the
// start checks the order of the lines once, in check_lines.
struct FolderScan {
    const Core *core;
    const char *path;
    uint32_t offset;
    uint32_t have;
    uint32_t taken;
    uint32_t length;
    uint8_t count;
    uint8_t next;
    uint8_t depth;
    uint8_t state;
    uint8_t held[4];
    char buffer[128];
};

uint32_t text_length(const char *text) {
    uint32_t length = 0;
    while (text[length] != '\0') {
        ++length;
    }
    return length;
}

// Where the first line feed of the buffer stands, or how many bytes it holds when it has none.
uint32_t line_end(const FolderScan &scan) {
    uint32_t at = 0;
    while (at < scan.have && scan.buffer[at] != '\n') {
        ++at;
    }
    return at;
}

// Reads more of the file into the buffer, until it holds a line feed or is full. False when
// the host could not read it.
bool fill(FolderScan &scan) {
    const odrig_host &host = scan.core->host;
    while (scan.have < sizeof scan.buffer && line_end(scan) == scan.have) {
        const int32_t got = host.read_at(host.ctx, kFoldersFile, scan.offset, reinterpret_cast<uint8_t *>(scan.buffer) + scan.have,
                                         sizeof scan.buffer - scan.have);
        if (got < 0) {
            return false;
        }
        if (got == 0) {
            return true;
        }
        scan.offset += static_cast<uint32_t>(got);
        scan.have += static_cast<uint32_t>(got);
    }
    return true;
}

// A decimal number from `least` to `most` without a leading zero, at `at`, which moves past
// it. False for anything else.
bool decimal(const char *text, uint32_t length, uint32_t *at, uint32_t least, uint32_t most, uint32_t *value) {
    uint32_t result = 0;
    const uint32_t begin = *at;
    while (*at < length && text[*at] >= '0' && text[*at] <= '9' && *at - begin < 6) {
        result = result * 10 + static_cast<uint32_t>(text[*at] - '0');
        ++*at;
    }
    if (*at == begin || (*at - begin > 1 && text[begin] == '0') || result < least || result > most) {
        return false;
    }
    *value = result;
    return true;
}

// The end of the part of a path that begins at `begin`: the next `/`, or the path's end.
uint32_t part_end(const char *path, uint32_t length, uint32_t begin) {
    while (begin < length && path[begin] != '/') {
        ++begin;
    }
    return begin;
}

// The place where part `part` of a path begins, counted from 1.
uint32_t part_begin(const char *path, uint32_t length, uint32_t part) {
    uint32_t at = 0;
    for (uint32_t passed = 1; passed < part && at < length; ++passed) {
        at = part_end(path, length, at) + 1;
    }
    return at;
}

}  // namespace

uint32_t folder_path_depth(const char *path, uint32_t length) {
    if (length == 0 || length > kFolderPathMost) {
        return 0;
    }
    uint32_t parts = 0;
    uint32_t begin = 0;
    while (begin <= length) {
        const uint32_t end = part_end(path, length, begin);
        if (end == begin || path[begin] == ' ' || path[begin] == '.' || path[end - 1] == ' ' || path[end - 1] == '.') {
            return 0;
        }
        for (uint32_t at = begin; at < end; ++at) {
            const char c = path[at];
            if (c < 0x20 || c > 0x7E || c == '\\' || c == ':' || c == '*' || c == '?' || c == '"' || c == '<' || c == '>' || c == '|') {
                return 0;
            }
        }
        if (++parts > kCatalogDeepest) {
            return 0;
        }
        if (end == length) {
            const uint32_t size = end - begin;
            const uint32_t ending = path[end - 1] == 'x' || path[end - 1] == 'X' ? 6 : 5;
            bool animation = size >= ending;
            for (uint32_t at = 0; animation && at < ending; ++at) {
                const char c = path[end - ending + at];
                animation = (c >= 'A' && c <= 'Z' ? static_cast<char>(c - 'A' + 'a') : c) == ".odrgx"[at];
            }
            return animation ? 0 : parts;
        }
        begin = end + 1;
    }
    return 0;
}

namespace {

// Reads a line, without its line feed, and gives it.
bool parse_line(FolderScan &scan, uint32_t length, FolderLine &line) {
    const char *text = scan.buffer;
    uint32_t at = 0;
    uint32_t number = 0;
    uint32_t id = 0;
    if (!decimal(text, length, &at, 1, 255, &number) || at >= length || text[at++] != ' ' || !decimal(text, length, &at, 1, kFolderIdMost, &id) ||
        at + 2 >= length || text[at++] != ' ' || (text[at] != '0' && text[at] != '1') || text[at + 1] != ' ') {
        return false;
    }
    const uint32_t ignored = text[at] == '1' ? 1 : 0;
    at += 2;
    const uint32_t depth = folder_path_depth(text + at, length - at);
    if (depth == 0 || depth > static_cast<uint32_t>(scan.depth) + 1 || scan.count >= kInternalFolderMost) {
        return false;
    }
    scan.held[depth] = static_cast<uint8_t>(ignored != 0 || scan.held[depth - 1] != 0);
    line.number = number;
    line.id = id;
    line.ignored = ignored;
    line.depth = depth;
    line.index = scan.count++;
    line.held = scan.held[depth];
    scan.depth = static_cast<uint8_t>(depth);
    scan.path = text + at;
    scan.length = length - at;
    return true;
}

// Begins the reading of the file with its header. False when it cannot be read, kScanFailed,
// or its header is not in its form, kScanDamaged.
ODRIG_NOINLINE bool begin_scan(FolderScan &scan, const Core &core) {
    scan.core = &core;
    scan.path = "";
    scan.offset = 0;
    scan.have = 0;
    scan.taken = 0;
    scan.length = 0;
    scan.count = 0;
    scan.next = 1;
    scan.depth = 0;
    memset(scan.held, 0, sizeof scan.held);
    scan.state = kScanFailed;
    if (core.host.read_at == nullptr || !fill(scan)) {
        return false;
    }
    scan.state = kScanDamaged;
    const uint32_t length = line_end(scan);
    const uint32_t head = sizeof kFoldersHeader - 1;
    if (length == scan.have || length <= head || memcmp(scan.buffer, kFoldersHeader, head) != 0) {
        return false;
    }
    uint32_t at = head;
    uint32_t next = 0;
    if (!decimal(scan.buffer, length, &at, 1, 255, &next) || at != length) {
        return false;
    }
    scan.next = static_cast<uint8_t>(next);
    scan.taken = length + 1;
    scan.state = kScanReading;
    return true;
}

// The next line. False at the file's end, kScanEnded, and when the rest cannot be read or a
// line is not as it must be.
ODRIG_NOINLINE bool next_line(FolderScan &scan, FolderLine &line) {
    if (scan.state != kScanReading) {
        return false;
    }
    if (scan.taken != 0) {
        memmove(scan.buffer, scan.buffer + scan.taken, scan.have - scan.taken);
        scan.have -= scan.taken;
        scan.taken = 0;
    }
    if (!fill(scan)) {
        scan.state = kScanFailed;
        return false;
    }
    if (scan.have == 0) {
        scan.state = kScanEnded;
        return false;
    }
    const uint32_t length = line_end(scan);
    if (length == scan.have) {
        scan.state = kScanDamaged;
        return false;
    }
    scan.buffer[length] = '\0';
    scan.taken = length + 1;
    if (!parse_line(scan, length, line)) {
        scan.state = kScanDamaged;
        return false;
    }
    return true;
}

// Whether `folders.txt` holds folders that the core may read in this boot.
bool readable(const Core &core) {
    return core.internal_folders != 0 && !core.folders_error && core.host.read_at != nullptr;
}

// The text of a number into room for 4 characters.
void number_text(uint32_t number, char *into) {
    char figures[4];
    uint32_t count = 0;
    do {
        figures[count++] = static_cast<char>('0' + number % 10);
        number /= 10;
    } while (number != 0);
    uint32_t length = 0;
    while (count != 0) {
        into[length++] = figures[--count];
    }
    into[length] = '\0';
}

uint32_t digits(uint32_t value) {
    uint32_t count = 1;
    while (value >= 10) {
        value /= 10;
        ++count;
    }
    return count;
}

// The text of the next `folders.txt`, gathered in the chunk buffer.
struct FolderWriter {
    void byte(char value) {
        if (failed) {
            return;
        }
        core->chunk[used++] = static_cast<uint8_t>(value);
        if (used == kChunkSize) {
            flush();
        }
    }

    void bytes(const char *text, uint32_t length) {
        for (uint32_t at = 0; at < length; ++at) {
            byte(text[at]);
        }
    }

    void number(uint32_t value) {
        char text[11];
        uint32_t count = 0;
        do {
            text[count++] = static_cast<char>('0' + value % 10);
            value /= 10;
        } while (value != 0);
        while (count != 0) {
            byte(text[--count]);
        }
    }

    void line(uint32_t number_of, uint32_t id, uint32_t ignored, const char *path, uint32_t length) {
        number(number_of);
        byte(' ');
        number(id);
        byte(' ');
        byte(ignored != 0 ? '1' : '0');
        byte(' ');
        bytes(path, length);
        byte('\n');
    }

    void flush() {
        if (used != 0 && !failed && core->host.write(core->host.ctx, core->chunk, used) != 1) {
            failed = true;
        }
        used = 0;
    }

    Core *core;
    uint32_t used;
    bool failed;
};

// What changes in the next `folders.txt`: its next number; a new line, at its place in the
// tree's order; the Ignore of one line; the id of one line; and the lines left out, a bit
// for each index.
struct FolderEdit {
    uint32_t next;
    const char *insert;
    uint32_t insert_length;
    uint32_t insert_depth;
    uint32_t insert_number;
    uint32_t insert_id;
    uint32_t flag_index;
    uint32_t flag;
    uint32_t id_index;
    uint32_t new_id;
    uint32_t drops;
};

void edit_clear(FolderEdit &edit, uint32_t next) {
    edit.next = next;
    edit.insert = nullptr;
    edit.insert_length = 0;
    edit.insert_depth = 0;
    edit.insert_number = 0;
    edit.insert_id = 0;
    edit.flag_index = kNoLine;
    edit.flag = 0;
    edit.id_index = kNoLine;
    edit.new_id = 0;
    edit.drops = 0;
}

// Whether the last part of a path comes after the last part of another by its bytes.
bool last_part_after(const char *path, uint32_t length, const char *other, uint32_t other_length) {
    uint32_t begin = length;
    while (begin != 0 && path[begin - 1] != '/') {
        --begin;
    }
    uint32_t other_begin = other_length;
    while (other_begin != 0 && other[other_begin - 1] != '/') {
        --other_begin;
    }
    while (begin < length && other_begin < other_length && path[begin] == other[other_begin]) {
        ++begin;
        ++other_begin;
    }
    return begin < length && (other_begin == other_length || static_cast<uint8_t>(path[begin]) > static_cast<uint8_t>(other[other_begin]));
}

// Writes `folders.part`: the lines of `folders.txt` with the edit made, or, when `fresh`, a
// file of the new line alone. False when the host could not take it or the file could not
// be read whole.
ODRIG_NOINLINE bool write_part(Core &core, const FolderEdit &edit, bool fresh) {
    const odrig_host &host = core.host;
    if (host.write_open(host.ctx, kFoldersPart) != 1) {
        return false;
    }
    FolderWriter out;
    out.core = &core;
    out.used = 0;
    out.failed = false;
    out.bytes(kFoldersHeader, sizeof kFoldersHeader - 1);
    out.number(edit.next);
    out.byte('\n');
    bool pending = edit.insert != nullptr;
    // The new line's parent is the root, or the line whose path is the new path without its
    // last part: the new line goes among the parent's sub-folders, before the first whose
    // name comes after its own.
    const uint32_t parent_length = pending && edit.insert_depth > 1 ? part_begin(edit.insert, edit.insert_length, edit.insert_depth) - 1 : 0;
    bool inside = edit.insert_depth <= 1;
    bool sound = true;
    if (!fresh) {
        FolderScan scan;
        FolderLine line;
        sound = begin_scan(scan, core);
        while (sound && next_line(scan, line)) {
            if (pending && inside && (line.depth < edit.insert_depth ||
                                      (line.depth == edit.insert_depth && last_part_after(scan.path, scan.length, edit.insert, edit.insert_length)))) {
                out.line(edit.insert_number, edit.insert_id, 0, edit.insert, edit.insert_length);
                pending = false;
            }
            if (pending && !inside && scan.length == parent_length && memcmp(scan.path, edit.insert, parent_length) == 0) {
                inside = true;
            }
            if ((edit.drops >> line.index & 1u) != 0) {
                continue;
            }
            out.line(line.number, line.index == edit.id_index ? edit.new_id : line.id, line.index == edit.flag_index ? edit.flag : line.ignored, scan.path,
                     scan.length);
        }
        sound = sound && scan.state == kScanEnded;
    }
    if (pending) {
        out.line(edit.insert_number, edit.insert_id, 0, edit.insert, edit.insert_length);
    }
    out.flush();
    return host.write_close(host.ctx) == 1 && !out.failed && sound;
}

// Puts `folders.part` in place of `folders.txt`. False, with the part removed, when it could
// not.
bool commit_part(Core &core) {
    if (core.host.rename(core.host.ctx, kFoldersPart, kFoldersFile) == 1) {
        return true;
    }
    core.host.remove(core.host.ctx, kFoldersPart);
    return false;
}

// Marks in the chunk buffer, a bit for each id below kIdBits, the ids of the show's items and
// of the folders, and gives the lowest id that none has, 0 for none.
uint32_t lowest_free_id(Core &core, const uint16_t *ids, uint32_t count) {
    memset(core.chunk, 0, kIdBits / 8);
    for (uint32_t item = 0; item < core.item_count; ++item) {
        const uint32_t id = core.items[item].id;
        if (id < kIdBits) {
            core.chunk[id / 8] = static_cast<uint8_t>(core.chunk[id / 8] | (1u << (id % 8)));
        }
    }
    for (uint32_t at = 0; at < count; ++at) {
        if (ids[at] < kIdBits) {
            core.chunk[ids[at] / 8] = static_cast<uint8_t>(core.chunk[ids[at] / 8] | (1u << (ids[at] % 8)));
        }
    }
    for (uint32_t id = 1; id < kIdBits && id <= kFolderIdMost; ++id) {
        if ((core.chunk[id / 8] & (1u << (id % 8))) == 0) {
            return id;
        }
    }
    return 0;
}

// The lines of the file as the start checks them: their number, the header's next number,
// and their ids by index.
struct Checked {
    uint32_t count;
    uint32_t next;
    uint16_t ids[kInternalFolderMost];
};

// Whether a line's path, of a depth, stands after the line before it in the tree's order: its
// parent is the line before or a folder above that one, so that their paths share the
// parent's, and a sibling before it comes before it by the bytes of its name.
bool in_order(const char *path, uint32_t length, uint32_t depth, const char *previous, uint32_t previous_length, uint32_t previous_depth) {
    if (depth > 1) {
        const uint32_t parent = part_begin(path, length, depth) - 1;
        if (parent > previous_length || memcmp(path, previous, parent) != 0 || (previous_length != parent && previous[parent] != '/')) {
            return false;
        }
    }
    if (depth > previous_depth) {
        return true;
    }
    const uint32_t begin = part_begin(path, length, depth);
    const uint32_t end = part_end(path, length, begin);
    const uint32_t before_end = part_end(previous, previous_length, begin);
    uint32_t index = 0;
    while (begin + index < end && begin + index < before_end && path[begin + index] == previous[begin + index]) {
        ++index;
    }
    return begin + index < end &&
           (begin + index == before_end || static_cast<uint8_t>(path[begin + index]) > static_cast<uint8_t>(previous[begin + index]));
}

// Reads the whole file and checks each line against the one before it, and that no two
// lines have one number or one id. False when the file is damaged or cannot be read.
ODRIG_NOINLINE bool check_lines(const Core &core, Checked &checked) {
    FolderScan scan;
    FolderLine line;
    char previous[kFolderPathMost + 1];
    uint32_t previous_length = 0;
    uint32_t previous_depth = 0;
    uint8_t numbers[32];
    memset(numbers, 0, sizeof numbers);
    if (!begin_scan(scan, core)) {
        return false;
    }
    while (next_line(scan, line)) {
        if ((numbers[line.number / 8] & (1u << (line.number % 8))) != 0 ||
            !in_order(scan.path, scan.length, line.depth, previous, previous_length, previous_depth)) {
            return false;
        }
        for (uint32_t before = 0; before < line.index; ++before) {
            if (checked.ids[before] == line.id) {
                return false;
            }
        }
        numbers[line.number / 8] = static_cast<uint8_t>(numbers[line.number / 8] | (1u << (line.number % 8)));
        checked.ids[line.index] = static_cast<uint16_t>(line.id);
        memcpy(previous, scan.path, scan.length);
        previous_length = scan.length;
        previous_depth = line.depth;
    }
    checked.count = scan.count;
    checked.next = scan.next;
    return scan.state == kScanEnded;
}

void unreadable(Core &core) {
    core.folders_error = 1;
    core.internal_folders = 0;
    if (core.host.log != nullptr) {
        core.host.log(core.host.ctx, "folders unreadable");
    }
}

// The root is current again in place of an internal playlist that is gone, with a fresh
// window, saved at the next refresh.
void root_again(Core &core) {
    tree_choose(core, 0);
    core.window_started = core.latest;
    core.window_spent = 0;
    core.save_due = 1;
}

// Looks a folder up by its number, its id or its index. `path`, when given, gets its path.
enum Key { kByNumber, kById, kByIndex };

ODRIG_NOINLINE bool find_folder(const Core &core, Key key, uint32_t value, FolderLine &found, char *path) {
    if (!readable(core)) {
        return false;
    }
    FolderScan scan;
    FolderLine line;
    if (!begin_scan(scan, core)) {
        return false;
    }
    while (next_line(scan, line)) {
        const uint32_t compared = key == kByNumber ? line.number : key == kById ? line.id : line.index;
        if (compared == value) {
            found = line;
            if (path != nullptr) {
                memcpy(path, scan.path, scan.length + 1);
            }
            return true;
        }
    }
    return false;
}

// Whether a text of this length holds a `/`.
bool has_slash(const char *text, uint32_t length) {
    for (uint32_t at = 0; at < length; ++at) {
        if (text[at] == '/') {
            return true;
        }
    }
    return false;
}

// Whether two names are the same but for the case of ASCII letters.
bool same_any_case(const char *one, uint32_t length, const char *other, uint32_t other_length) {
    if (length != other_length) {
        return false;
    }
    for (uint32_t at = 0; at < length; ++at) {
        char a = one[at];
        char b = other[at];
        a = a >= 'A' && a <= 'Z' ? static_cast<char>(a - 'A' + 'a') : a;
        b = b >= 'A' && b <= 'Z' ? static_cast<char>(b - 'A' + 'a') : b;
        if (a != b) {
            return false;
        }
    }
    return true;
}

// The number of the show's animations whose file is in the folder with this number.
uint32_t own_animations(const Core &core, uint32_t number) {
    uint32_t count = 0;
    for (uint32_t item = 0; item < core.item_count; ++item) {
        if (!core.items[item].is_cycle && core.files[core.items[item].first].rank != 0 && stored_folder(core.files[core.items[item].first].name) == number) {
            ++count;
        }
    }
    return count;
}

// Whether a file of this stored name is a file of a folder whose path has this length: its
// path, the folder's, `/` and its name, is 100 bytes at most.
bool path_fits(uint32_t folder_length, const char *stored) {
    return folder_length + 1 + text_length(stored_base(stored)) < kDrivePathRoom;
}

// Whether a file of the show is in the folder with this number.
bool holds_files(const Core &core, uint32_t number) {
    for (uint32_t file = 0; file < core.file_count; ++file) {
        if (stored_folder(core.files[file].name) == number) {
            return true;
        }
    }
    return false;
}

}  // namespace

bool folder_by_number(const Core &core, uint32_t number, FolderLine &line, char *path) {
    return number != 0 && find_folder(core, kByNumber, number, line, path);
}

bool folder_by_id(const Core &core, uint32_t id, FolderLine &line, char *path) {
    return id != 0 && id <= kFolderIdMost && find_folder(core, kById, id, line, path);
}

bool internal_folder_id(const Core &core, uint32_t id) {
    FolderLine line;
    return folder_by_id(core, id, line, nullptr);
}

ODRIG_NOINLINE int32_t folder_by_path(const Core &core, const char *path, uint32_t length, FolderLine &found, bool *twin) {
    *twin = false;
    if (!readable(core)) {
        return core.folders_error ? -1 : 0;
    }
    FolderScan scan;
    FolderLine line;
    if (!begin_scan(scan, core)) {
        return -1;
    }
    uint32_t parent = length;
    while (parent != 0 && path[parent - 1] != '/') {
        --parent;
    }
    int32_t result = 0;
    while (next_line(scan, line)) {
        if (scan.length == length && memcmp(scan.path, path, length) == 0) {
            found = line;
            result = 1;
        } else if (scan.length > parent && memcmp(scan.path, path, parent) == 0 && !has_slash(scan.path + parent, scan.length - parent) &&
                   same_any_case(scan.path + parent, scan.length - parent, path + parent, length - parent)) {
            *twin = true;
        }
    }
    return scan.state == kScanEnded ? result : -1;
}

ODRIG_NOINLINE void logical_path(const Core &core, const char *stored, char *into) {
    const uint32_t number = stored_folder(stored);
    FolderLine line;
    uint32_t length = 0;
    if (number != 0 && folder_by_number(core, number, line, into)) {
        length = text_length(into);
        if (path_fits(length, stored)) {
            into[length++] = '/';
            stored = stored_base(stored);
        } else {
            length = 0;
        }
    }
    for (; *stored != '\0' && length + 1 < kDrivePathRoom; ++stored) {
        into[length++] = *stored;
    }
    into[length] = '\0';
}

void folders_derive(Core &core) {
    for (uint32_t file = 0; file < core.file_count; ++file) {
        core.files[file].rank = 0;
        core.files[file].held = 0;
    }
    const bool internal_current = (core.current & kInternalLevel) != 0;
    if (core.folders_error || core.host.read_at == nullptr || (core.internal_folders == 0 && !internal_current)) {
        if (internal_current) {
            root_again(core);
        }
        return;
    }
    FolderScan scan;
    FolderLine line;
    uint32_t found = kNoLine;
    uint32_t found_depth = 0;
    uint32_t end = 0;
    const bool begun = begin_scan(scan, core);
    while (begun && next_line(scan, line)) {
        for (uint32_t file = 0; file < core.file_count; ++file) {
            if (stored_folder(core.files[file].name) == line.number && path_fits(scan.length, core.files[file].name)) {
                core.files[file].rank = static_cast<uint8_t>((line.index + 1) & 0x3Fu);
                core.files[file].held = static_cast<uint8_t>(line.held != 0 ? 1 : 0);
            }
        }
        if (!internal_current) {
            continue;
        }
        if (found == kNoLine && line.number == (core.current & 0xFFu)) {
            found = line.index;
            found_depth = line.depth;
            core.current_folder.id = line.id;
            core.current_folder.depth = static_cast<uint8_t>(line.depth);
        } else if (found != kNoLine && end == 0 && line.depth <= found_depth) {
            end = line.index + 1;
        }
    }
    if (begun && scan.state == kScanEnded) {
        core.internal_folders = static_cast<uint8_t>(scan.count & 0x3Fu);
    }
    if (internal_current) {
        if (found == kNoLine) {
            root_again(core);
            return;
        }
        core.current_folder.ordinal = core.current & 0xFFu;
        core.current_folder.first = found + 1;
        core.current_folder.end = end != 0 ? end : scan.count + 1;
    }
}

void folders_start(Core &core) {
    core.internal_folders = 0;
    core.folders_error = 0;
    for (uint32_t file = 0; file < core.file_count; ++file) {
        core.files[file].rank = 0;
        core.files[file].held = 0;
    }
    if (!storage_changes(core) || core.host.read_at == nullptr || core.chunk == nullptr) {
        return;
    }
    const Reason opened = core.file.open(core.host, kFoldersFile);
    if (opened == kFileMissing) {
        return;
    }
    if (opened == kNone) {
        core.file.close();
    }
    // A folder whose id an item has gets the lowest id that is free, one folder at a time.
    for (uint32_t round = 0;; ++round) {
        Checked checked;
        if (opened != kNone || round > kInternalFolderMost || !check_lines(core, checked)) {
            unreadable(core);
            return;
        }
        uint32_t clash = kNoLine;
        for (uint32_t index = 0; index < checked.count && clash == kNoLine; ++index) {
            for (uint32_t item = 0; item < core.item_count; ++item) {
                if (core.items[item].id == checked.ids[index]) {
                    clash = index;
                    break;
                }
            }
        }
        if (clash == kNoLine) {
            core.internal_folders = static_cast<uint8_t>(checked.count & 0x3Fu);
            break;
        }
        FolderEdit edit;
        edit_clear(edit, checked.next);
        edit.id_index = clash;
        edit.new_id = lowest_free_id(core, checked.ids, checked.count);
        if (edit.new_id == 0 || !write_part(core, edit, false) || !commit_part(core)) {
            core.host.remove(core.host.ctx, kFoldersPart);
            unreadable(core);
            return;
        }
    }
    folders_derive(core);
}

namespace {

// What `folder make internal` finds in `folders.txt` before it writes.
struct MakePlan {
    bool fresh;         // there is no file
    bool exact;         // a folder has the path
    bool twin;          // a sibling's name differs only in case
    bool parent;        // the parent is there
    uint32_t id;        // of the folder of the path, or the new folder's
    uint32_t number;    // the new folder's, 0 for none free
    uint32_t count;     // the lines
};

ODRIG_NOINLINE bool make_plan(Core &core, const char *path, uint32_t length, uint32_t depth, MakePlan &plan) {
    FolderScan scan;
    FolderLine line;
    uint16_t ids[kInternalFolderMost];
    uint8_t numbers[32];
    memset(numbers, 0, sizeof numbers);
    plan.fresh = !begin_scan(scan, core);
    plan.exact = false;
    plan.twin = false;
    plan.parent = depth == 1;
    plan.count = 0;
    if (plan.fresh && (scan.state != kScanFailed || core.internal_folders != 0)) {
        return false;
    }
    uint32_t parent = length;
    while (parent != 0 && path[parent - 1] != '/') {
        --parent;
    }
    while (!plan.fresh && next_line(scan, line)) {
        ids[line.index] = static_cast<uint16_t>(line.id);
        numbers[line.number / 8] = static_cast<uint8_t>(numbers[line.number / 8] | (1u << (line.number % 8)));
        if (scan.length == length && memcmp(scan.path, path, length) == 0) {
            plan.exact = true;
            plan.id = line.id;
        } else if (scan.length > parent && memcmp(scan.path, path, parent) == 0 && !has_slash(scan.path + parent, scan.length - parent) &&
                   same_any_case(scan.path + parent, scan.length - parent, path + parent, length - parent)) {
            plan.twin = true;
        }
        if (depth > 1 && scan.length + 1 == parent && memcmp(scan.path, path, parent - 1) == 0) {
            plan.parent = true;
        }
    }
    if (!plan.fresh && scan.state != kScanEnded) {
        return false;
    }
    plan.count = plan.fresh ? 0 : scan.count;
    if (plan.exact) {
        return true;
    }
    // The number: the first from the header's next on, round to 1 after 255, that no line
    // and no file of the show has.
    for (uint32_t file = 0; file < core.file_count; ++file) {
        const uint32_t number = stored_folder(core.files[file].name);
        numbers[number / 8] = static_cast<uint8_t>(numbers[number / 8] | (1u << (number % 8)));
    }
    plan.number = 0;
    uint32_t candidate = plan.fresh ? 1 : scan.next;
    for (uint32_t tried = 0; tried < 255 && plan.number == 0; ++tried) {
        if ((numbers[candidate / 8] & (1u << (candidate % 8))) == 0) {
            plan.number = candidate;
        }
        candidate = candidate % 255 + 1;
    }
    plan.id = lowest_free_id(core, ids, plan.count);
    return true;
}

uint32_t folder_reply(Reply &reply, uint32_t id, bool made) {
    reply.text("{\"ok\":true,\"id\":");
    reply.number(id);
    reply.text(made ? ",\"made\":true}\n" : ",\"made\":false}\n");
    return reply.length;
}

}  // namespace

uint32_t internal_folder_make(Core &core, const char *path, Reply &reply) {
    const odrig_host &host = core.host;
    if (!storage_changes(core) || host.make_folder == nullptr || host.read_at == nullptr || core.chunk == nullptr) {
        return refuse(reply, "unsupported");
    }
    if (core.upload.state != kUploadNone || catalog_rebuilding(core)) {
        return refuse(reply, "busy");
    }
    if (core.folders_error) {
        return refuse(reply, "storage-error");
    }
    const uint32_t length = text_length(path);
    const uint32_t depth = folder_path_depth(path, length);
    MakePlan plan;
    if (depth == 0 || !make_plan(core, path, length, depth, plan)) {
        return refuse(reply, "storage-error");
    }
    if (plan.exact) {
        return folder_reply(reply, plan.id, false);
    }
    if (plan.twin) {
        return refuse(reply, "in-use");
    }
    if (!plan.parent) {
        return refuse(reply, "unknown-id");
    }
    uint32_t free_bytes = 0;
    uint32_t total_bytes = 0;
    const bool told = host.space != nullptr && host.space(host.ctx, &free_bytes, &total_bytes) == 1;
    if (plan.count >= kInternalFolderMost || plan.number == 0 || plan.id == 0 || (told && free_bytes < kFolderSpace)) {
        return refuse(reply, "no-space");
    }
    // The line is written first, which makes the storage's folder of the show when it has
    // none; then the folder of the storage, and the rename puts both in place.
    FolderEdit edit;
    edit_clear(edit, plan.number % 255 + 1);
    edit.insert = path;
    edit.insert_length = length;
    edit.insert_depth = depth;
    edit.insert_number = plan.number;
    edit.insert_id = plan.id;
    if (!write_part(core, edit, plan.fresh)) {
        host.remove(host.ctx, kFoldersPart);
        return refuse(reply, "storage-error");
    }
    char name[4];
    number_text(plan.number, name);
    const int made = host.make_folder(host.ctx, name);
    if (made != 1) {
        host.remove(host.ctx, kFoldersPart);
        return refuse(reply, made == 0 ? "unsupported" : "storage-error");
    }
    if (!commit_part(core)) {
        return refuse(reply, "storage-error");
    }
    core.internal_folders = static_cast<uint8_t>((plan.count + 1) & 0x3Fu);
    folders_derive(core);
    return folder_reply(reply, plan.id, true);
}

uint32_t internal_folder_ignore(Core &core, uint32_t id, bool ignored, Reply &reply) {
    FolderLine line;
    if (!folder_by_id(core, id, line, nullptr)) {
        return refuse(reply, "unknown-id");
    }
    if ((line.ignored != 0) == ignored) {
        return succeed(reply);
    }
    if (core.upload.state != kUploadNone || catalog_rebuilding(core) || core.chunk == nullptr) {
        return refuse(reply, "busy");
    }
    // The next number is the one the file has: the scan of the edit keeps it.
    FolderScan scan;
    if (!begin_scan(scan, core)) {
        return refuse(reply, "storage-error");
    }
    FolderEdit edit;
    edit_clear(edit, scan.next);
    edit.flag_index = line.index;
    edit.flag = ignored ? 1 : 0;
    if (!write_part(core, edit, false)) {
        core.host.remove(core.host.ctx, kFoldersPart);
        return refuse(reply, "storage-error");
    }
    if (!commit_part(core)) {
        return refuse(reply, "storage-error");
    }
    folders_derive(core);
    player_internal_inclusion_changed(core);
    return succeed(reply);
}

namespace {

// The lines of the file as a prune sees them: their numbers and depths, by index.
struct Tree {
    uint32_t count;
    uint32_t next;
    uint8_t numbers[kInternalFolderMost];
    uint8_t depths[kInternalFolderMost];
};

ODRIG_NOINLINE bool read_tree(const Core &core, Tree &tree) {
    FolderScan scan;
    FolderLine line;
    if (!begin_scan(scan, core)) {
        return false;
    }
    while (next_line(scan, line)) {
        tree.numbers[line.index] = static_cast<uint8_t>(line.number);
        tree.depths[line.index] = static_cast<uint8_t>(line.depth);
    }
    tree.count = scan.count;
    tree.next = scan.next;
    return scan.state == kScanEnded;
}

}  // namespace

void internal_folders_prune(Core &core, uint32_t number) {
    if (number == 0 || !readable(core) || core.chunk == nullptr || core.upload.state == kUploadReceiving || catalog_rebuilding(core)) {
        return;
    }
    Tree tree;
    if (!read_tree(core, tree)) {
        return;
    }
    uint32_t at = 0;
    while (at < tree.count && tree.numbers[at] != number) {
        ++at;
    }
    // The folder goes when it holds no file and has no sub-folder that stays; then its parent
    // is judged the same way.
    uint32_t drops = 0;
    while (at < tree.count) {
        if (holds_files(core, tree.numbers[at])) {
            break;
        }
        bool kept_below = false;
        for (uint32_t below = at + 1; below < tree.count && tree.depths[below] > tree.depths[at]; ++below) {
            kept_below = kept_below || (drops >> below & 1u) == 0;
        }
        if (kept_below) {
            break;
        }
        drops |= 1u << at;
        uint32_t parent = at;
        while (parent != 0 && tree.depths[parent - 1] >= tree.depths[at]) {
            --parent;
        }
        at = parent != 0 && tree.depths[at] > 1 ? parent - 1 : tree.count;
    }
    if (drops == 0) {
        return;
    }
    FolderEdit edit;
    edit_clear(edit, tree.next);
    edit.drops = drops;
    if (!write_part(core, edit, false) || !commit_part(core)) {
        core.host.remove(core.host.ctx, kFoldersPart);
        return;
    }
    uint32_t left = tree.count;
    for (uint32_t index = tree.count; index != 0;) {
        --index;
        if ((drops >> index & 1u) != 0) {
            char name[4];
            number_text(tree.numbers[index], name);
            core.host.remove(core.host.ctx, name);
            --left;
        }
    }
    core.internal_folders = static_cast<uint8_t>(left & 0x3Fu);
    const uint32_t before = core.current;
    folders_derive(core);
    if (core.current != before) {
        player_playlist_chosen(core, core.latest);
        playlist_changed(core);
    }
}

bool internal_choose(Core &core, uint32_t id) {
    FolderLine line;
    char path[kFolderPathMost + 1];
    if (core.playlist_path == nullptr || !folder_by_id(core, id, line, path)) {
        return false;
    }
    core.current = kInternalLevel | line.number;
    core.current_folder.ordinal = line.number;
    core.current_folder.id = line.id;
    core.playlist_path[0] = ':';
    memcpy(core.playlist_path + 1, path, text_length(path) + 1);
    folders_derive(core);
    return (core.current & kInternalLevel) != 0;
}

uint32_t internal_id_at(const Core &core, uint32_t rank) {
    FolderLine line;
    return rank != 0 && find_folder(core, kByIndex, rank - 1, line, nullptr) ? line.id : 0;
}

ODRIG_NOINLINE uint32_t internal_folder_children(const Core &core, uint32_t parent) {
    if (!readable(core)) {
        return 0;
    }
    FolderScan scan;
    FolderLine line;
    if (!begin_scan(scan, core)) {
        return 0;
    }
    uint32_t count = 0;
    uint32_t inside_depth = parent == 0 ? 0 : kNoLine;
    while (next_line(scan, line)) {
        if (inside_depth != kNoLine && line.depth <= inside_depth) {
            inside_depth = parent == 0 ? 0 : kNoLine;
        }
        if (inside_depth == kNoLine) {
            if (line.number == parent) {
                inside_depth = line.depth;
            }
            continue;
        }
        count += line.depth == inside_depth + 1 ? 1 : 0;
    }
    return count;
}

ODRIG_NOINLINE uint32_t internal_folder_rows(const Core &core, uint32_t parent, uint32_t skip, uint32_t total, uint32_t from, Reply &reply, bool *first) {
    if (!readable(core)) {
        return 0;
    }
    FolderScan scan;
    FolderLine line;
    if (!begin_scan(scan, core)) {
        return 0;
    }
    uint32_t child = 0;
    uint32_t written = 0;
    uint32_t inside_depth = parent == 0 ? 0 : kNoLine;
    while (next_line(scan, line)) {
        if (inside_depth != kNoLine && line.depth <= inside_depth) {
            inside_depth = parent == 0 ? 0 : kNoLine;
        }
        if (inside_depth == kNoLine) {
            if (line.number == parent) {
                inside_depth = line.depth;
            }
            continue;
        }
        if (line.depth != inside_depth + 1 || child++ < skip) {
            continue;
        }
        const bool inherited = scan.held[line.depth - 1] != 0;
        const uint32_t files = own_animations(core, line.number);
        const uint32_t position = from + written;
        const uint32_t tail = 9 + (position + 1 < total ? digits(position + 1) : 4) + 2;
        const uint32_t size = (*first ? 0 : 1) + 6 + digits(line.id) + 13 + json_escaped(scan.path, nullptr) + 1 + 17 + 9 + digits(files) +
                              (line.ignored != 0 ? 15 : 16) + (inherited ? 25 : 26) + 1;
        if (!reply.fits(size + tail)) {
            break;
        }
        if (!*first) {
            reply.text(",");
        }
        *first = false;
        reply.text("{\"id\":");
        reply.number(line.id);
        reply.text(",\"playlist\":\"");
        reply.escaped(scan.path);
        reply.text("\",\"external\":false,\"files\":");
        reply.number(files);
        reply.text(line.ignored != 0 ? ",\"ignored\":true" : ",\"ignored\":false");
        reply.text(inherited ? ",\"inherited_ignored\":true}" : ",\"inherited_ignored\":false}");
        ++written;
    }
    return written;
}

namespace {

// One file of an internal folder as `list` writes it, its folder's path given: false when it
// does not fit with the tail after it.
ODRIG_NOINLINE bool file_row(const Core &core, const ItemInfo &item, const char *path, uint32_t position, uint32_t total, Reply &reply, bool *first) {
    const FileInfo &file = core.files[item.first];
    const char *base = stored_base(file.name);
    const Reason fault = static_cast<Reason>(file.fault);
    const bool known = fault == kNone && file.checked != 0;
    const uint32_t tail = 9 + (position + 1 < total ? digits(position + 1) : 4) + 2;
    const uint32_t size = (*first ? 0 : 1) + 6 + digits(item.id) + 9 + json_escaped(path, nullptr) + 1 + text_length(base) + 10 + (known ? digits(file.bytes) : 4) +
                          (item.ignored ? 15 : 16) + 17 + 9 + text_length(type_name(file.type)) + 1 + 11 + text_length(file.name) + 1 + (file.held ? 25 : 26) +
                          (fault != kNone ? 10 + text_length(reason_name(fault)) + 1 : 0) + 1;
    if (!reply.fits(size + tail)) {
        return false;
    }
    if (!*first) {
        reply.text(",");
    }
    *first = false;
    reply.text("{\"id\":");
    reply.number(item.id);
    reply.text(",\"file\":\"");
    reply.escaped(path);
    reply.text("/");
    reply.text(base);
    reply.text("\",\"bytes\":");
    if (known) {
        reply.number(file.bytes);
    } else {
        reply.text("null");
    }
    reply.text(item.ignored ? ",\"ignored\":true" : ",\"ignored\":false");
    reply.text(",\"external\":false,\"type\":\"");
    reply.text(type_name(file.type));
    reply.text("\",\"stored\":\"");
    reply.text(file.name);
    reply.text(file.held ? "\",\"inherited_ignored\":true" : "\",\"inherited_ignored\":false");
    if (fault != kNone) {
        reply.text(",\"fault\":\"");
        reply.text(reason_name(fault));
        reply.text("\"");
    }
    reply.text("}");
    return true;
}

// Whether the item at a position is an animation whose file is in the internal folder with
// this number.
bool in_folder(const Core &core, uint32_t item, uint32_t number) {
    const ItemInfo &info = core.items[item];
    return !info.is_cycle && core.files[info.first].rank != 0 && stored_folder(core.files[info.first].name) == number;
}

}  // namespace

ODRIG_NOINLINE uint32_t internal_list_level(const Core &core, uint32_t number, uint32_t from, Reply &reply) {
    char path[kFolderPathMost + 1];
    FolderLine line;
    if (!folder_by_number(core, number, line, path)) {
        return refuse(reply, "unknown-id");
    }
    const uint32_t children = internal_folder_children(core, number);
    const uint32_t total = children + own_animations(core, number);
    reply.text("{\"ok\":true,\"items\":[");
    bool first = true;
    uint32_t position = from;
    if (position < children) {
        position += internal_folder_rows(core, number, position, total, position, reply, &first);
    }
    uint32_t seen = children;
    for (uint32_t item = 0; position >= children && position < total && item < core.item_count; ++item) {
        if (!in_folder(core, item, number) || seen++ < position) {
            continue;
        }
        if (!file_row(core, core.items[item], path, position, total, reply, &first)) {
            break;
        }
        ++position;
    }
    reply.text("],\"next\":");
    if (position < total) {
        reply.number(position);
    } else {
        reply.text("null");
    }
    reply.text("}\n");
    return reply.length;
}

}  // namespace odrig
