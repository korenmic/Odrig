#include "repeats.h"

#include <string.h>

#include "order.h"
#include "player.h"
#include "show.h"

namespace odrig {

namespace {

const char kRepeatsHeader[] = "odrig-repeats 1";
// The longest line: five figures, a space, the kind, a space and a name of 127 bytes.
const uint32_t kLineMost = 135;
const uint32_t kNameMost = 127;
// The saved repeat of an item stands in the high 16 bits of its `count`.
const uint32_t kSavedShift = 16;
const uint32_t kLoopsMask = 0xFFFFu;

// The length of a text that ends in a 0.
uint32_t text_length(const char *text) {
    uint32_t length = 0;
    while (text[length] != '\0') {
        ++length;
    }
    return length;
}

// One line of the file, read: its loops, its kind, `f` for a file of the board's own
// storage or `x` for one of a drive, and its name.
struct Line {
    uint32_t loops;
    char kind;
    const char *name;
    uint32_t length;
};

// The parts of a whole line without its line feed, false for a line out of form: `<n> f
// <name>` with a name `show.json` may give a file, or `<n> x <name>` with 1 to 127 bytes
// without NUL, `<n>` 1 to 65,535 without a leading zero. The line must have room for a 0
// after it.
bool parse(char *text, uint32_t length, Line *line) {
    uint32_t at = 0;
    uint32_t loops = 0;
    while (at < length && at < 6 && text[at] >= '0' && text[at] <= '9') {
        loops = loops * 10 + static_cast<uint32_t>(text[at] - '0');
        ++at;
    }
    if (at == 0 || at > 5 || text[0] == '0' || loops > 65535 || at + 3 > length || text[at] != ' ' || text[at + 2] != ' ') {
        return false;
    }
    line->loops = loops;
    line->kind = text[at + 1];
    line->name = text + at + 3;
    line->length = length - at - 3;
    if (line->kind == 'f') {
        text[length] = '\0';
        return is_file_name(line->name);
    }
    if (line->kind != 'x' || line->length == 0 || line->length > kNameMost) {
        return false;
    }
    for (uint32_t index = 0; index < line->length; ++index) {
        if (line->name[index] == '\0') {
            return false;
        }
    }
    return true;
}

// Whether the item at a position is an animation whose file has this name.
bool item_named(const Core &core, uint32_t position, const char *name, uint32_t length) {
    const ItemInfo &item = core.items[position];
    if (item.is_cycle) {
        return false;
    }
    const char *file = core.files[item.first].name;
    return text_length(file) == length && memcmp(file, name, length) == 0;
}

// Whether an item of the show names a file of this name.
bool show_names(const Core &core, const char *name, uint32_t length) {
    for (uint32_t position = 0; position < core.item_count; ++position) {
        if (item_named(core, position, name, length)) {
            return true;
        }
    }
    return false;
}

void clear_items(Core &core) {
    for (uint32_t position = 0; position < core.item_count; ++position) {
        if (!core.items[position].is_cycle) {
            core.items[position].count &= kLoopsMask;
        }
    }
}

void clear_drive(Core &core) {
    for (uint32_t at = 0; core.repeats_drive != nullptr && at < kRepeatsDriveMost; ++at) {
        core.repeats_drive[at].place = 0;
        core.repeats_drive[at].loops = 0;
    }
}

void clear_all(Core &core) {
    clear_items(core);
    clear_drive(core);
}

// The entry of the drive's table for a place, or kRepeatsDriveMost.
uint32_t entry_of(const Core &core, uint32_t place) {
    for (uint32_t at = 0; core.repeats_drive != nullptr && at < kRepeatsDriveMost; ++at) {
        if (core.repeats_drive[at].loops != 0 && core.repeats_drive[at].place == place) {
            return at;
        }
    }
    return kRepeatsDriveMost;
}

// Whether every entry of the drive's table is taken.
bool drive_full(const Core &core) {
    for (uint32_t at = 0; core.repeats_drive != nullptr && at < kRepeatsDriveMost; ++at) {
        if (core.repeats_drive[at].loops == 0) {
            return false;
        }
    }
    return core.repeats_drive != nullptr;
}

// Gives a line `x` to the place of the drive whose file has its name, when that place has
// no saved repeat yet: a new entry, or with every entry taken none; at the take-up of a
// drive, `taking_up`, the log says `repeats over` once then.
void apply_drive(Core &core, const Line &line, bool taking_up) {
    if (line.kind != 'x' || core.repeats_drive == nullptr) {
        return;
    }
    const uint32_t place = order_place_named(core, line.name, line.length);
    if (place == kDriveMost || entry_of(core, place) != kRepeatsDriveMost) {
        return;
    }
    for (uint32_t at = 0; at < kRepeatsDriveMost; ++at) {
        if (core.repeats_drive[at].loops == 0) {
            core.repeats_drive[at].place = static_cast<uint16_t>(place);
            core.repeats_drive[at].loops = static_cast<uint16_t>(line.loops);
            return;
        }
    }
    if (taking_up && !core.order_reader.over && core.host.log != nullptr) {
        core.host.log(core.host.ctx, "repeats over");
    }
    core.order_reader.over = 1;
}

// Gives a line read to the items that name its file and have no saved repeat yet: the first
// line of a file counts.
void apply(Core &core, const Line &line) {
    if (line.kind != 'f') {
        return;
    }
    for (uint32_t position = 0; position < core.item_count; ++position) {
        ItemInfo &item = core.items[position];
        if ((item.count >> kSavedShift) == 0 && item_named(core, position, line.name, line.length)) {
            item.count = (item.count & kLoopsMask) | line.loops << kSavedShift;
        }
    }
}

void reader_clear(Core &core) {
    OrderReader &reader = core.order_reader;
    reader.entries = 0;
    reader.length = 0;
    reader.header = 0;
    reader.over = 0;
}

// What a reading of the file came to so far: going on, or a line out of form found.
enum Taken { kTakenOn, kTakenBad };

// Takes one byte of the file. At a line feed the line is judged: the header first, then
// lines, each given to `each`. A line longer than any line of the file is out of form.
template <typename Each>
Taken take_byte(Core &core, uint8_t byte, Each each) {
    OrderReader &reader = core.order_reader;
    if (byte != '\n') {
        if (reader.length >= kLineMost) {
            return kTakenBad;
        }
        reader.line[reader.length++] = static_cast<char>(byte);
        return kTakenOn;
    }
    const uint32_t length = reader.length;
    reader.length = 0;
    if (reader.header == 0) {
        reader.header = 1;
        return length == sizeof kRepeatsHeader - 1 && memcmp(reader.line, kRepeatsHeader, length) == 0 ? kTakenOn : kTakenBad;
    }
    Line line;
    if (reader.entries >= kRepeatsLines || !parse(reader.line, length, &line)) {
        return kTakenBad;
    }
    ++reader.entries;
    each(line, length);
    return kTakenOn;
}

// How a whole reading of the file ended: the file is missing, it was read whole and in
// form, it is out of form, or its reading failed after it began.
enum Ending { kEndMissing, kEndSound, kEndBad, kEndFailed };

// Reads the file whole through the second source, each line in form given to `each`.
template <typename Each>
Ending read_through(Core &core, Each each) {
    FileSource &source = core.checker->file;
    source.open_at(core.host, kRepeatsFile);
    reader_clear(core);
    Taken taken = kTakenOn;
    int got;
    while (taken == kTakenOn && (got = source.get()) >= 0) {
        taken = take_byte(core, static_cast<uint8_t>(got), each);
    }
    const uint32_t read = source.taken;
    source.close();
    if (taken == kTakenBad) {
        return kEndBad;
    }
    if (got == -kReadError) {
        return read == 0 ? kEndMissing : kEndFailed;
    }
    // A file without its header, or with bytes after its last line feed, is out of form.
    return core.order_reader.header == 0 || core.order_reader.length != 0 ? kEndBad : kEndSound;
}

// The log says once for a reading that the file is out of form, and no saved repeat is in
// force then.
void unreadable(Core &core) {
    clear_all(core);
    if (core.host.log != nullptr) {
        core.host.log(core.host.ctx, "repeats unreadable");
    }
}

// Reads the whole file and gives its lines to the items, and with `drive` to the drive's
// places too.
void read_whole(Core &core, bool drive) {
    clear_items(core);
    if (drive) {
        clear_drive(core);
    }
    const Ending ending = read_through(core, [&core, drive](const Line &line, uint32_t) {
        apply(core, line);
        if (drive) {
            apply_drive(core, line, false);
        }
    });
    if (ending == kEndBad || ending == kEndFailed) {
        unreadable(core);
    }
}

// Whether the core has a saved repeat in force.
bool any_saved(const Core &core) {
    for (uint32_t position = 0; position < core.item_count; ++position) {
        if (!core.items[position].is_cycle && (core.items[position].count >> kSavedShift) != 0) {
            return true;
        }
    }
    for (uint32_t at = 0; core.repeats_drive != nullptr && at < kRepeatsDriveMost; ++at) {
        if (core.repeats_drive[at].loops != 0) {
            return true;
        }
    }
    return false;
}

// The listed animation with this id, its position in the playlist; kNothing with `in_use`
// for a cycle or a folder of the drive's tree, and without it for an id of nothing listed.
uint32_t animation_with(const Core &core, uint32_t id, bool *in_use) {
    *in_use = false;
    for (uint32_t position = 0; position < core.item_count; ++position) {
        if (core.items[position].id == id) {
            *in_use = core.items[position].is_cycle != 0;
            return *in_use ? kNothing : position;
        }
    }
    const uint32_t place = core.drive != nullptr ? drive_place_holding(core, id) : kDriveMost;
    if (place < kDriveMost) {
        const uint8_t state = core.drive[place].state;
        if (state == kDriveInPlaylist || state == kDriveLeftOut) {
            return kDriveBase + place;
        }
    }
    *in_use = tree_folder_with_id(core, id) != kFolderMost;
    return kNothing;
}

// The text of the next file goes through the first kWriteRoom bytes of the chunk; the
// animation's own line, its kind and its name, stands after them.
const uint32_t kWriteRoom = 1000;
const uint32_t kOwnLine = kWriteRoom;

struct Writer {
    void bytes(const char *text, uint32_t length) {
        for (uint32_t at = 0; at < length && !failed; ++at) {
            core->chunk[used++] = static_cast<uint8_t>(text[at]);
            if (used == kWriteRoom) {
                flush();
            }
        }
    }

    void line(const char *text, uint32_t length) {
        bytes(text, length);
        bytes("\n", 1);
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

// The animation's own line, `<n> <kind> <name>`, written at kOwnLine in the chunk with `n`
// as its loops; the kind and the name at `*name` and `*length`. False when the host gives
// no name for a drive's file.
bool own_line(Core &core, uint32_t position, uint32_t loops, uint32_t *size, const char **name, uint32_t *length) {
    char *line = reinterpret_cast<char *>(core.chunk + kOwnLine);
    char figures[5];
    uint32_t count = 0;
    do {
        figures[count++] = static_cast<char>('0' + loops % 10);
        loops /= 10;
    } while (loops != 0);
    uint32_t at = 0;
    while (count != 0) {
        line[at++] = figures[--count];
    }
    line[at++] = ' ';
    line[at++] = is_drive(position) ? 'x' : 'f';
    line[at++] = ' ';
    *name = line + at;
    if (is_drive(position)) {
        if (core.host.drive_name(core.host.ctx, core.drive_number, position - kDriveBase, line + at, kNameMost + 1) != 1) {
            return false;
        }
    } else {
        const char *file = core.files[core.items[position].first].name;
        memcpy(line + at, file, text_length(file) + 1);
    }
    *length = text_length(line + at);
    *size = at + *length;
    return *length != 0;
}

// Whether a line read is the animation's own: of its kind and its name.
bool is_own(const Line &line, char kind, const char *name, uint32_t length) {
    return line.kind == kind && line.length == length && memcmp(line.name, name, length) == 0;
}

// What a change of the file writes: the animation's own line, its kind and its name, its
// new loops or 0 to remove its line, whether the old file is sound, and whether it is full,
// so that the lines of files the show no longer names are dropped.
struct Plan {
    uint32_t size;
    const char *name;
    uint32_t length;
    char kind;
    uint32_t loops;
    bool sound;
    bool full;
};

// Reads the old file: the lines of the other animations, and of them those of files the
// show no longer names.
__attribute__((noinline)) Ending count_others(Core &core, const Plan &plan, uint32_t *others, uint32_t *gone) {
    return read_through(core, [&](const Line &line, uint32_t) {
        if (!is_own(line, plan.kind, plan.name, plan.length)) {
            ++*others;
            *gone += line.kind == 'f' && !show_names(core, line.name, line.length) ? 1 : 0;
        }
    });
}

// Writes `repeats.part` and renames it onto the file: the header, every line of a sound
// old file but the animation's own and the dropped ones, and its new line in the place of
// its first one or at the end. False when a call of the host failed.
__attribute__((noinline)) bool write_file(Core &core, const Plan &plan) {
    const odrig_host &host = core.host;
    if (host.write_open(host.ctx, kRepeatsPart) != 1) {
        return false;
    }
    Writer out;
    out.core = &core;
    out.used = 0;
    out.failed = false;
    out.line(kRepeatsHeader, sizeof kRepeatsHeader - 1);
    const char *own = reinterpret_cast<const char *>(core.chunk + kOwnLine);
    bool placed = false;
    Ending ending = kEndSound;
    if (plan.sound) {
        ending = read_through(core, [&](const Line &line, uint32_t whole) {
            if (is_own(line, plan.kind, plan.name, plan.length)) {
                if (plan.loops != 0 && !placed) {
                    out.line(own, plan.size);
                }
                placed = true;
            } else if (!(plan.full && line.kind == 'f' && !show_names(core, line.name, line.length))) {
                out.line(core.order_reader.line, whole);
            }
        });
    }
    if (plan.loops != 0 && !placed) {
        out.line(own, plan.size);
    }
    out.flush();
    return host.write_close(host.ctx) == 1 && !out.failed && ending == kEndSound && host.rename(host.ctx, kRepeatsPart, kRepeatsFile) == 1;
}

// A change of the file for one animation: its new loops, or 0 to remove its line.
uint32_t change(Core &core, uint32_t id, uint32_t loops, uint64_t now, Reply &reply) {
    bool in_use = false;
    const uint32_t position = animation_with(core, id, &in_use);
    if (position == kNothing) {
        return refuse(reply, in_use ? "in-use" : "unknown-id");
    }
    if (core.order_items == nullptr || core.chunk == nullptr || core.checker == nullptr) {
        return refuse(reply, "storage-error");
    }
    // The turn of the animation as it was before its count changes.
    TurnCounts before;
    const bool reported = player_counts(core, now, &before) && before.id == id;
    if (loops != 0 && is_drive(position) && repeats_of(core, position) == 0 && drive_full(core)) {
        return refuse(reply, "no-space");
    }
    if (repeats_of(core, position) != loops) {
        Plan plan;
        plan.kind = is_drive(position) ? 'x' : 'f';
        plan.loops = loops;
        if (!own_line(core, position, loops == 0 ? 1 : loops, &plan.size, &plan.name, &plan.length)) {
            return refuse(reply, "storage-error");
        }
        drive_check_yields(core);
        uint32_t others = 0;
        uint32_t gone = 0;
        const Ending ending = count_others(core, plan, &others, &gone);
        if (ending == kEndFailed || (ending == kEndMissing && any_saved(core))) {
            return refuse(reply, "storage-error");
        }
        plan.sound = ending == kEndSound;
        plan.full = loops != 0 && plan.sound && others >= kRepeatsLines;
        if (plan.full && others - gone >= kRepeatsLines) {
            return refuse(reply, "no-space");
        }
        if (!write_file(core, plan)) {
            core.host.remove(core.host.ctx, kRepeatsPart);
            return refuse(reply, "storage-error");
        }
        repeats_reload(core);
    }
    if (reported && loops != 0) {
        player_hold_turn(core, before.loop > loops ? static_cast<uint32_t>(before.loop) : loops);
    } else if (reported) {
        player_default_again(core, now, before.loop);
    }
    return succeed(reply);
}

}  // namespace

uint32_t repeats_of(const Core &core, uint32_t position) {
    if (is_drive(position)) {
        const uint32_t at = entry_of(core, position - kDriveBase);
        return at == kRepeatsDriveMost ? 0 : core.repeats_drive[at].loops;
    }
    return core.items[position].count >> kSavedShift;
}

void repeats_start(Core &core) {
    if (core.checker == nullptr || core.order_items == nullptr) {
        return;
    }
    read_whole(core, false);
}

void repeats_reload(Core &core) {
    if (core.checker == nullptr || core.order_items == nullptr) {
        return;
    }
    read_whole(core, true);
}

void repeats_drive_found(Core &core) {
    clear_drive(core);
}

void repeats_drive_step(Core &core) {
    FileSource &source = core.checker->file;
    OrderReader &reader = core.order_reader;
    if (!core.order_reading) {
        clear_drive(core);
        source.open_at(core.host, kRepeatsFile);
        reader_clear(core);
        core.order_reading = 1;
    }
    Taken taken = kTakenOn;
    int got = source.get();
    while (got >= 0) {
        taken = take_byte(core, static_cast<uint8_t>(got), [&core](const Line &line, uint32_t) { apply_drive(core, line, true); });
        if (taken == kTakenBad) {
            break;
        }
        if (source.position >= source.length) {
            // The rest at the next step.
            return;
        }
        got = source.get();
    }
    const uint32_t read = source.taken;
    source.close();
    core.order_reading = 0;
    core.order_due = 0;
    const bool missing = taken == kTakenOn && got == -kReadError && read == 0;
    if (!missing && (taken == kTakenBad || got == -kReadError || reader.header == 0 || reader.length != 0)) {
        unreadable(core);
    }
}

uint32_t repeats_save(Core &core, uint32_t id, uint32_t loops, uint64_t now, Reply &reply) {
    return change(core, id, loops, now, reply);
}

uint32_t repeats_restore(Core &core, uint32_t id, uint64_t now, Reply &reply) {
    return change(core, id, 0, now, reply);
}

}  // namespace odrig
