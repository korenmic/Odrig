#include "order.h"

#include <string.h>

#include "arena.h"
#include "catalog.h"
#include "crc32.h"
#include "drive.h"
#include "breaks.h"
#include "repeats.h"
#include "brightness.h"
#include "storage.h"

namespace odrig {

namespace {

const char kOrderHeader[] = "odrig-order 1";
const uint32_t kUnnamedItem = 0x10000u;

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

// One whole line of the file, without its line feed. An entry `i <id>` gives the show's
// animation item of that id the entry's number; an entry `x <name>`, of a drive's file, is
// passed over, the drive's order being its own.
void take_line(Core &core) {
    OrderReader &reader = core.order_reader;
    const char *line = reader.line;
    const uint32_t length = reader.length;
    if (reader.header == 0) {
        const bool header = length == sizeof kOrderHeader - 1 && memcmp(line, kOrderHeader, length) == 0;
        reader.header = header ? 1 : 2;
        return;
    }
    if (reader.header != 1 || reader.entries >= kOrderMost || length < 3 || line[0] != 'i' || line[1] != ' ') {
        return;
    }
    const uint32_t id = entry_id(line + 2, length - 2);
    if (id == 0) {
        return;
    }
    const uint16_t entry = static_cast<uint16_t>(reader.entries++);
    for (uint32_t position = 0; position < core.item_count; ++position) {
        if (core.items[position].id == id) {
            if (!core.items[position].is_cycle && core.order_items[position] == kOrderUnnamed) {
                core.order_items[position] = entry;
            }
            break;
        }
    }
}

// Takes one byte of the file.
void take_byte(Core &core, uint8_t byte) {
    OrderReader &reader = core.order_reader;
    if (byte == '\n') {
        if (!reader.over) {
            take_line(core);
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

// Reads the whole file at once through the second source and sets the keys it names. A
// file that is not there, or cannot be read, names nothing more.
void read_whole(Core &core) {
    FileSource &source = core.checker->file;
    source.open_at(core.host, kOrderFile);
    reader_clear(core);
    int got;
    while ((got = source.get()) >= 0) {
        take_byte(core, static_cast<uint8_t>(got));
    }
    source.close();
}

uint32_t digits(uint64_t value) {
    uint32_t count = 1;
    while (value >= 10) {
        value /= 10;
        ++count;
    }
    return count;
}

// The depth of a name of the drive: the folders it is in.
uint32_t name_depth(const char *name) {
    uint32_t depth = 0;
    for (; *name != '\0'; ++name) {
        depth += *name == '/' ? 1 : 0;
    }
    return depth;
}

// Whether two names of the drive are in one folder at a depth: their first `parts` parts
// are the same, and each has that many folders at least.
bool same_folders(const char *a, const char *b, uint32_t parts) {
    uint32_t seen = 0;
    for (uint32_t at = 0;; ++at) {
        if (a[at] != b[at] || a[at] == '\0') {
            return false;
        }
        if (a[at] == '/' && ++seen == parts) {
            return true;
        }
    }
}

// The index after the last descendant of each folder of the table: the folders after it
// are its descendants while they are deeper than it.
void set_ends(Core &core) {
    for (uint32_t folder = 0; folder <= core.folder_count; ++folder) {
        uint32_t end = folder + 1;
        while (end <= core.folder_count && core.folders[end].depth > core.folders[folder].depth) {
            ++end;
        }
        core.folders[folder].end = static_cast<uint8_t>(end);
    }
}

}  // namespace

bool order_begin(Core &core) {
    if (!storage_changes(core) || core.checker == nullptr) {
        return true;
    }
    // The block: a key for each item, and with a drive the table of the folders, the room
    // for the current playlist's path and the saved repeats of the drive's files.
    const uint32_t tree = core.drive != nullptr ? kFolderMost * sizeof(Folder) + kPlaylistPathRoom : 0;
    const uint32_t repeats = core.drive != nullptr ? kRepeatsDriveMost * sizeof(RepeatOf) : 0;
    const uint32_t brightness = core.drive != nullptr ? kBrightnessDriveMost * sizeof(BrightnessOf) : 0;
    uint8_t *block = static_cast<uint8_t *>(arena_take(core, core.item_capacity * 2 + tree + repeats + brightness));
    if (block == nullptr) {
        return false;
    }
    core.order_items = reinterpret_cast<uint16_t *>(block);
    clear_items(core);
    if (tree != 0) {
        core.folders = reinterpret_cast<Folder *>(block + core.item_capacity * 2);
        core.playlist_path = reinterpret_cast<char *>(block + core.item_capacity * 2 + kFolderMost * sizeof(Folder));
        core.playlist_path[0] = '\0';
        core.repeats_drive = reinterpret_cast<RepeatOf *>(block + core.item_capacity * 2 + tree);
        core.brightness_drive = reinterpret_cast<BrightnessOf *>(block + core.item_capacity * 2 + tree + repeats);
        brightness_drive_found(core);
        tree_clear(core);
        repeats_drive_found(core);
    }
    return true;
}

void tree_clear(Core &core) {
    core.folder_count = 0;
    core.tree_known = 0;
    core.current = 0;
    core.current_folder.ordinal = 0;
    core.current_folder.id = 0;
    breaks_tree(core);
    if (core.folders == nullptr) {
        return;
    }
    Folder &root = core.folders[0];
    root.id = 0;
    root.first = 0;
    root.files = 0;
    root.depth = 0;
    root.end = 1;
}

void tree_build(Core &core) {
    tree_clear(core);
    if (core.folders == nullptr || core.drive == nullptr || core.drive_number == 0) {
        return;
    }
    // The places are in the listing's order, depth first: a place's folders that the place
    // before it does not share begin there. `chain` holds the folder of each depth of the
    // place before.
    char name[kDrivePathRoom];
    char before[kDrivePathRoom];
    before[0] = '\0';
    uint32_t before_depth = 0;
    uint32_t chain[kCatalogDeepest + 1] = {0, 0, 0, 0};
    for (uint32_t place = 0; place < core.drive_count; ++place) {
        if (core.host.drive_name(core.host.ctx, core.drive_number, place, name, sizeof name) != 1) {
            name[0] = '\0';
        }
        const uint32_t depth = name_depth(name);
        if (depth > kCatalogDeepest) {
            continue;
        }
        uint32_t shared = 0;
        while (shared < depth && shared < before_depth && same_folders(name, before, shared + 1)) {
            ++shared;
        }
        if (core.folder_count + (depth - shared) > kFolderMost - 1) {
            // This file's folder would be past the 32nd: it and every later place are dropped.
            core.drive_count = place;
            break;
        }
        for (uint32_t level = shared + 1; level <= depth; ++level) {
            Folder &made = core.folders[++core.folder_count];
            made.id = 0;
            made.first = static_cast<uint16_t>(place);
            made.files = 0;
            made.depth = static_cast<uint8_t>(level);
            made.end = 0;
            chain[level] = core.folder_count;
        }
        if (depth != 0) {
            ++core.folders[chain[depth]].files;
        }
        memcpy(before, name, sizeof before);
        before_depth = depth;
    }
    set_ends(core);
    core.tree_known = 1;
    breaks_tree(core);
}

void tree_find_current(Core &core) {
    core.current = 0;
    if (core.playlist_path != nullptr && core.playlist_path[0] != '\0') {
        const uint32_t found = drive_folder_with_path(core, core.playlist_path);
        if (found != kNoFolder) {
            core.current = found;
        } else {
            // The card has no playlist of the saved path: the root is current, with a fresh
            // window, and is saved as such at the next refresh.
            core.playlist_path[0] = '\0';
            core.window_started = core.latest;
            core.window_spent = 0;
            core.save_due = 1;
        }
    }
    drive_folder(core, core.current, core.current_folder);
    breaks_tree(core);
}

void tree_choose(Core &core, uint32_t folder) {
    core.current = folder;
    drive_folder(core, folder, core.current_folder);
    if (core.playlist_path != nullptr) {
        drive_folder_path(core, folder, core.playlist_path, kPlaylistPathRoom);
    }
}

uint32_t level_of(const Core &core, uint32_t position) {
    if (!is_drive(position)) {
        return 0;
    }
    const uint32_t folder = drive_folder_of(core, position - kDriveBase);
    return folder == kNoFolder ? 0 : folder;
}

uint32_t order_key(const Core &core, uint32_t position) {
    const uint16_t entry = core.order_items != nullptr ? core.order_items[position] : kOrderUnnamed;
    return entry != kOrderUnnamed ? entry : kUnnamedItem + position;
}

void order_start(Core &core) {
    if (core.order_items == nullptr) {
        return;
    }
    clear_items(core);
    read_whole(core);
    repeats_start(core);
    brightness_start(core);
}

void order_reload(Core &core) {
    if (core.order_items == nullptr) {
        return;
    }
    drive_check_yields(core);
    clear_items(core);
    read_whole(core);
    repeats_reload(core);
    brightness_start(core);
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

// Whether an item of the show is listed in the order: every animation item.
bool item_listed(const Core &core, uint32_t position) {
    return position < core.item_count && !core.items[position].is_cycle;
}

// The show's animation with the smallest key above `after`, or kNothing.
uint32_t item_after(const Core &core, uint32_t after, bool any) {
    uint32_t best = kNothing;
    uint32_t best_key = 0;
    for (uint32_t position = 0; position < core.item_count; ++position) {
        if (!item_listed(core, position)) {
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

// Hands each listed animation of a level to `visit`, in the saved order, until it gives
// false: at the root the show's animations by their keys and then the root's files of the
// drive, at a folder its own files, in the order of the drive's walk. Gives the count.
template <typename Visit>
uint32_t each_listed(const Core &core, uint32_t level, Visit visit) {
    uint32_t count = 0;
    if (level == 0) {
        uint32_t key = 0;
        for (uint32_t at = item_after(core, 0, true); at != kNothing; at = item_after(core, key, false)) {
            key = order_key(core, at);
            if (!visit(at, core.items[at].id)) {
                return count;
            }
            ++count;
        }
    }
    IndexFolder folder;
    if (!drive_folder(core, level, folder)) {
        return count;
    }
    for (uint32_t position = folder.first; position < folder.first + folder.files; ++position) {
        const DriveRow *row = drive_row(core, position);
        if (row == nullptr) {
            break;
        }
        if (!row->listed) {
            continue;
        }
        if (!visit(kDriveBase + position, row->id)) {
            return count;
        }
        ++count;
    }
    return count;
}

// The revision of a level's order: the CRC-32 of the ids of its listed animations in the
// saved order, each as four bytes, low byte first; and the number of them.
uint32_t revision_of(const Core &core, uint32_t level, uint32_t *total) {
    uint32_t crc = kCrcStart;
    *total = each_listed(core, level, [&crc](uint32_t, uint32_t id) {
        for (uint32_t shift = 0; shift < 32; shift += 8) {
            crc = crc_add(crc, static_cast<uint8_t>(id >> shift));
        }
        return true;
    });
    return crc_value(crc);
}

// What an id names for the order: an animation, its position in the playlist; or kNothing,
// with `cycle_or_folder` set for a cycle of the show or a folder of the drive.
uint32_t animation_with(const Core &core, uint32_t id, bool *cycle_or_folder) {
    *cycle_or_folder = false;
    for (uint32_t position = 0; position < core.item_count; ++position) {
        if (core.items[position].id == id) {
            *cycle_or_folder = core.items[position].is_cycle != 0;
            return core.items[position].is_cycle ? kNothing : position;
        }
    }
    uint32_t value = 0;
    const uint8_t kind = drive_find(core, id, &value);
    if (kind == 'd') {
        *cycle_or_folder = true;
    }
    if (kind == 'f') {
        const DriveRow *row = drive_row(core, value);
        if (row != nullptr && row->listed) {
            return kDriveBase + value;
        }
    }
    return kNothing;
}

// The text of the next `order.txt` goes through the first kWriteRoom bytes of the chunk;
// the entries looked for while it is written, and the entry of an animation the file does
// not name, stand after them.
const uint32_t kWriteRoom = 1000;
const uint32_t kMovedLine = kWriteRoom;
const uint32_t kBeforeLine = kMovedLine + kOrderLineRoom;
const uint32_t kUnnamedLine = kBeforeLine + kOrderLineRoom;

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

// The entry of a show's animation, `i <id>`, written at `at` in the chunk. Returns its
// length.
uint32_t entry_of(Core &core, uint32_t position, uint32_t at) {
    char *line = reinterpret_cast<char *>(core.chunk + at);
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

// One whole line of the file as it is, given to the next file when it is an entry of an
// animation the show has: an entry of a drive's file, of a cycle, or of an id no item has
// is left out.
void copy_line(Core &core, OrderWriter &out, Move &move) {
    OrderReader &reader = core.order_reader;
    const char *line = reader.line;
    const uint32_t length = reader.length;
    if (reader.header == 0) {
        reader.header = length == sizeof kOrderHeader - 1 && memcmp(line, kOrderHeader, length) == 0 ? 1 : 2;
        return;
    }
    if (reader.header != 1 || length < 3 || line[0] != 'i' || line[1] != ' ') {
        return;
    }
    const uint32_t id = entry_id(line + 2, length - 2);
    for (uint32_t position = 0; id != 0 && position < core.item_count; ++position) {
        if (core.items[position].id == id) {
            if (!core.items[position].is_cycle) {
                write_entry(core, out, move, line, length);
            }
            return;
        }
    }
}

// Writes `order.part`: the entries of `order.txt` with the move made, and after them every
// show's animation the file did not name. False when the host could not take it.
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
    for (uint32_t position = 0; position < core.item_count; ++position) {
        if (item_listed(core, position) && order_key(core, position) >= kUnnamedItem) {
            const uint32_t length = entry_of(core, position, kUnnamedLine);
            write_entry(core, out, move, reinterpret_cast<const char *>(core.chunk + kUnnamedLine), length);
        }
    }
    if (!move.placed) {
        out.entry(reinterpret_cast<const char *>(core.chunk + kMovedLine), move.moved_length);
    }
    out.flush();
    return host.write_close(host.ctx) == 1 && !out.failed;
}

}  // namespace

uint32_t order_get(const Core &core, uint32_t level, uint32_t from, Reply &reply) {
    uint32_t total = 0;
    const uint32_t revision = revision_of(core, level, &total);
    reply.text("{\"ok\":true,\"ids\":[");
    // The tail: `],"next":<n>,"revision":<r>}` and a line feed, with room for any position.
    const uint32_t tail = 9 + (digits(total) > 4 ? digits(total) : 4) + 12 + digits(revision) + 2;
    uint32_t position = 0;
    bool first = true;
    each_listed(core, level, [&](uint32_t, uint32_t id) {
        if (position < from) {
            ++position;
            return true;
        }
        const uint32_t size = (first ? 0 : 1) + digits(id);
        if (!reply.fits(size + tail)) {
            return false;
        }
        if (!first) {
            reply.text(",");
        }
        first = false;
        reply.number(id);
        ++position;
        return true;
    });
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
    bool moved_other = false;
    bool target_other = false;
    const uint32_t moved = animation_with(core, id, &moved_other);
    uint32_t target = before == 0 ? kNothing : animation_with(core, before, &target_other);
    // A cycle and a folder of the drive's tree have ids and no place in the order.
    if ((moved == kNothing && !moved_other) || (before != 0 && target == kNothing && !target_other)) {
        return refuse(reply, "unknown-id");
    }
    const uint32_t level = moved == kNothing ? 0 : level_of(core, moved);
    if (moved == kNothing || (before != 0 && target == kNothing) || (target != kNothing && level_of(core, target) != level)) {
        return refuse(reply, "in-use");
    }
    if (is_drive(moved) && !catalog_drive_writable(core)) {
        // A drive's file stands in its folder's rows, which only a drive read from its index
        // that the core may write keeps.
        return refuse(reply, "read-only");
    }
    uint32_t total = 0;
    if (revision != revision_of(core, level, &total)) {
        return refuse(reply, "order-conflict");
    }
    if (is_drive(moved)) {
        // Before another file of its folder, or last; a root's file before a show's animation
        // goes first among the root's files.
        const uint32_t before_position = target == kNothing ? kNothing : is_drive(target) ? target - kDriveBase : 0;
        return catalog_move_external(core, moved - kDriveBase, before_position) ? succeed(reply) : refuse(reply, "storage-error");
    }
    if (target != kNothing && is_drive(target)) {
        // A show's animation before a file of the root goes last among the show's.
        target = kNothing;
    }
    // Nothing changes when the animation already stands where it is to go among the show's.
    const uint32_t next = item_after(core, order_key(core, moved), false);
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
    if (!write_part(core, move) || host.rename(host.ctx, kOrderPart, kOrderFile) != 1) {
        host.remove(host.ctx, kOrderPart);
        return refuse(reply, "storage-error");
    }
    order_reload(core);
    return succeed(reply);
}

}  // namespace odrig
