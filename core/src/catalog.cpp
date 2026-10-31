#include "catalog.h"

#include <string.h>

#include "crc32.h"
#include "drive.h"
#include "fields.h"
#include "json_reader.h"
#include "order.h"
#include "player.h"
#include "repeats.h"
#include "brightness.h"
#include "ignored.h"
#include "storage.h"

namespace odrig {

namespace {

// The names of a catalog's files for the host: of the internal storage [kInternal], and of
// the drive [kExternal], which are the same after `drive/`.
const char *const kMarkerNames[2] = {"catalog.txt", "drive/catalog.txt"};
const char *const kNewMarkerNames[2] = {"catalog.new", "drive/catalog.new"};
const char *const kRecordNames[2] = {"catalog.do", "drive/catalog.do"};
const char *const kPartNames[2] = {"upload.part", "drive/upload.part"};
const char *const kPageNames[2][kCatalogPages] = {
    {
    "catalog-00.txt", "catalog-01.txt", "catalog-02.txt", "catalog-03.txt", "catalog-04.txt", "catalog-05.txt", "catalog-06.txt", "catalog-07.txt",
    "catalog-08.txt", "catalog-09.txt", "catalog-10.txt", "catalog-11.txt", "catalog-12.txt", "catalog-13.txt", "catalog-14.txt", "catalog-15.txt",
    },
    {
    "drive/catalog-00.txt", "drive/catalog-01.txt", "drive/catalog-02.txt", "drive/catalog-03.txt", "drive/catalog-04.txt", "drive/catalog-05.txt", "drive/catalog-06.txt", "drive/catalog-07.txt",
    "drive/catalog-08.txt", "drive/catalog-09.txt", "drive/catalog-10.txt", "drive/catalog-11.txt", "drive/catalog-12.txt", "drive/catalog-13.txt", "drive/catalog-14.txt", "drive/catalog-15.txt",
    },
};
const char *const kNewPageNames[2][kCatalogPages] = {
    {
    "catalog-00.new", "catalog-01.new", "catalog-02.new", "catalog-03.new", "catalog-04.new", "catalog-05.new", "catalog-06.new", "catalog-07.new",
    "catalog-08.new", "catalog-09.new", "catalog-10.new", "catalog-11.new", "catalog-12.new", "catalog-13.new", "catalog-14.new", "catalog-15.new",
    },
    {
    "drive/catalog-00.new", "drive/catalog-01.new", "drive/catalog-02.new", "drive/catalog-03.new", "drive/catalog-04.new", "drive/catalog-05.new", "drive/catalog-06.new", "drive/catalog-07.new",
    "drive/catalog-08.new", "drive/catalog-09.new", "drive/catalog-10.new", "drive/catalog-11.new", "drive/catalog-12.new", "drive/catalog-13.new", "drive/catalog-14.new", "drive/catalog-15.new",
    },
};

// The two files a rebuild of the drive's catalog writes for itself, which no reader reads:
// a line for each listed file, and the draft of the table.
const char kRebuildScan[] = "drive/rebuild.tmp";
const char kRebuildDraft[] = "drive/rebuild-folders.tmp";

// The ways a line comes out of a file.
enum LineRead { kLineGot, kLineEnd, kLineFailed };

// Reads the next line of a source, without its line feed, into `line` with a zero after
// it. A line longer than `room` - 1 characters is read to its end and given cut, with
// `over` set; a last line without a line feed is given with `unended` set. Every byte read
// is taken into `crc`.
struct LineReader {
    LineRead next(FileSource &source, char *line, uint32_t room) {
        length = 0;
        over = false;
        unended = false;
        for (;;) {
            const int got = source.get();
            if (got == -kEnd) {
                if (length == 0 && !over) {
                    return kLineEnd;
                }
                unended = true;
                break;
            }
            if (got < 0) {
                return kLineFailed;
            }
            ++bytes;
            crc = crc_add(crc, static_cast<uint8_t>(got));
            if (got == '\n') {
                break;
            }
            if (length + 1 < room) {
                line[length++] = static_cast<char>(got);
            } else {
                over = true;
            }
        }
        line[length] = '\0';
        return kLineGot;
    }

    uint32_t crc = kCrcStart;
    uint32_t bytes = 0;
    uint32_t length = 0;
    bool over = false;
    bool unended = false;
};

// Reads ten decimal digits, leading zeros allowed, of a number of at most 32 bits.
bool ten_digits(const char *line, uint32_t *at, uint32_t *value) {
    uint64_t found = 0;
    for (uint32_t digit = 0; digit < 10; ++digit) {
        const char c = line[*at + digit];
        if (c < '0' || c > '9') {
            return false;
        }
        found = found * 10 + static_cast<uint64_t>(c - '0');
    }
    if (found > 0xFFFFFFFFu) {
        return false;
    }
    *at += 10;
    *value = static_cast<uint32_t>(found);
    return true;
}

// Reads a line of a drive's marker that gives a file of its index: the word, the file's
// lines in ten digits and its CRC-32, which is 0 for a file without a line.
bool index_count(LineReader &reader, FileSource &source, char *line, uint32_t room, const char *head, uint32_t *lines, uint32_t *crc) {
    if (reader.next(source, line, room) != kLineGot || reader.over || reader.unended) {
        return false;
    }
    uint32_t at = 0;
    return word(line, &at, head) && ten_digits(line, &at, lines) && word(line, &at, " ") && hexadecimal(line, &at, 8, crc) && at == reader.length &&
           (*lines != 0 || *crc == 0);
}

// Reads the marker from an open source: kCatalogOk with `marker` filled, kCatalogDamaged
// or kCatalogIncompatible. A drive's marker is of version 2, with the lines of its index;
// the internal storage's of version 1. Each finds the other's incompatible.
uint8_t read_marker(FileSource &source, Marker &marker, bool drive, uint32_t *whole_crc = nullptr) {
    LineReader reader;
    char line[48];
    if (reader.next(source, line, sizeof line) != kLineGot || reader.over || reader.unended) {
        return kCatalogDamaged;
    }
    uint32_t at = 0;
    uint64_t format = 0;
    uint64_t check = 0;
    uint32_t generation = 0;
    if (word(line, &at, "odrig-catalog ") && decimal(line, &at, 9, 999999999, &format) && word(line, &at, " check ") &&
        decimal(line, &at, 9, 999999999, &check) && word(line, &at, " generation ") && hexadecimal(line, &at, 8, &generation) &&
        line[at] == '\0' && (format != (drive ? 2u : 1u) || check != 1)) {
        return kCatalogIncompatible;
    }
    if (at != reader.length || reader.length != 43) {
        return kCatalogDamaged;
    }
    marker.generation = generation;
    for (uint32_t page = 0; page < kCatalogPages; ++page) {
        if (reader.next(source, line, sizeof line) != kLineGot || reader.over || reader.unended || reader.length != 21) {
            return kCatalogDamaged;
        }
        at = 0;
        uint32_t number;
        uint32_t count;
        uint32_t value;
        if (!word(line, &at, "page ") || !fixed_decimal(line, &at, 2, &number) || number != page || !word(line, &at, " ") ||
            !fixed_decimal(line, &at, 4, &count) || !word(line, &at, " ") || !hexadecimal(line, &at, 8, &value) || (count == 0 && value != 0)) {
            return kCatalogDamaged;
        }
        marker.counts[page] = static_cast<uint16_t>(count);
        marker.crcs[page] = value;
    }
    marker.folders = 0;
    marker.folders_crc = 0;
    marker.ids = 0;
    marker.ids_crc = 0;
    if (drive && (!index_count(reader, source, line, sizeof line, "folders ", &marker.folders, &marker.folders_crc) || marker.folders == 0 ||
                  !index_count(reader, source, line, sizeof line, "ids ", &marker.ids, &marker.ids_crc))) {
        return kCatalogDamaged;
    }
    const uint32_t body = crc_value(reader.crc);
    uint32_t sealed;
    at = 0;
    if (reader.next(source, line, sizeof line) != kLineGot || reader.over || reader.unended || reader.length != 12 || !word(line, &at, "crc ") ||
        !hexadecimal(line, &at, 8, &sealed) || sealed != body) {
        return kCatalogDamaged;
    }
    if (reader.next(source, line, sizeof line) != kLineEnd || reader.bytes != (drive ? kDriveMarkerSize : kMarkerSize) || marker.generation == 0) {
        return kCatalogDamaged;
    }
    if (whole_crc != nullptr) {
        *whole_crc = crc_value(reader.crc);
    }
    return kCatalogOk;
}

// One entry of a page.
struct EntryLine {
    uint32_t crc;
    uint32_t bytes;
    uint16_t width;
    uint16_t height;
    uint8_t type;
    uint64_t total_ms;
    const char *name;
    uint32_t name_length;
};

// Reads the fields of an entry line, without its line feed, whatever page it is on.
bool parse_fields(const char *line, uint32_t length, EntryLine &entry) {
    uint32_t at = 0;
    uint64_t bytes;
    uint64_t width;
    uint64_t height;
    if (!hexadecimal(line, &at, 8, &entry.crc) || !word(line, &at, " ") || !decimal(line, &at, 10, 0xFFFFFFFFu, &bytes) || !word(line, &at, " ") ||
        !decimal(line, &at, 5, 65535, &width) || width == 0 || !word(line, &at, " ") || !decimal(line, &at, 5, 65535, &height) || height == 0 ||
        !word(line, &at, " ") || !decimal(line, &at, 20, 0xFFFFFFFFFFFFFFFFull, &entry.total_ms) || !word(line, &at, " ")) {
        return false;
    }
    if (word(line, &at, "frames ")) {
        entry.type = kTypeFrames;
    } else if (word(line, &at, "text ")) {
        entry.type = kTypeText;
    } else if (word(line, &at, "widget ")) {
        entry.type = kTypeWidget;
    } else {
        return false;
    }
    entry.bytes = static_cast<uint32_t>(bytes);
    entry.width = static_cast<uint16_t>(width);
    entry.height = static_cast<uint16_t>(height);
    entry.name = line + at;
    entry.name_length = length - at;
    return catalog_name_allowed(entry.name, entry.name_length);
}

// Reads an entry line of page `page`, without its line feed.
bool parse_entry(const char *line, uint32_t length, uint32_t page, EntryLine &entry) {
    return parse_fields(line, length, entry) && catalog_page_of(entry.name, entry.name_length) == page;
}

// Whether a name is the part of a change, `upload.part`.
bool is_part(const char *name, uint32_t length) {
    const char *part = kPartNames[kInternal];
    for (uint32_t at = 0; at < length; ++at) {
        if (name[at] != part[at]) {
            return false;
        }
    }
    return part[length] == '\0';
}

// Whether a name is one of the files of a drive's index, `index-<id>`, `index-folders` or
// `index-ids`, ending in `.txt`, or in `.new` when `fresh`.
bool is_index_name(const char *name, uint32_t length, bool fresh) {
    if (length < 11 || memcmp(name, "index-", 6) != 0 || memcmp(name + length - 4, fresh ? ".new" : ".txt", 4) != 0) {
        return false;
    }
    const char *middle = name + 6;
    const uint32_t size = length - 10;
    if ((size == 7 && memcmp(middle, "folders", 7) == 0) || (size == 3 && memcmp(middle, "ids", 3) == 0)) {
        return true;
    }
    if (size > 10 || (size > 1 && middle[0] == '0')) {
        return false;
    }
    uint64_t value = 0;
    for (uint32_t at = 0; at < size; ++at) {
        if (middle[at] < '0' || middle[at] > '9') {
            return false;
        }
        value = value * 10 + static_cast<uint64_t>(middle[at] - '0');
    }
    return value == 0 || (value >= kDriveFirstId && value <= 0xFFFFFFFFu);
}

// Where a catalog is read: its storage, and whether with the second source, which reads with
// `read_at` beside the player's file, or with the first, at the start.
struct Place {
    uint32_t storage;
    bool second;
};

// Whether a file of the host is there: one byte of it can be read.
bool is_there(Core &core, const char *name) {
    uint8_t probe;
    return core.host.read_at != nullptr && core.host.read_at(core.host.ctx, name, 0, &probe, 1) >= 0;
}

// The source a place reads with.
FileSource &source_of(Core &core, const Place &place) {
    return place.second ? core.checker->file : core.file;
}

// Opens a file of a place by its host's name, which must stay where it is while the file is
// read: kNone, kFileMissing, or kReadError. The second source cannot tell a missing file from
// one it cannot read: both are missing.
Reason open_for(Core &core, const Place &place, const char *name) {
    if (!place.second) {
        return core.file.open(core.host, name);
    }
    if (!is_there(core, name)) {
        return kFileMissing;
    }
    core.checker->file.open_at(core.host, name);
    return kNone;
}

// Renames a file that is there onto another, by their host's names. False when the rename
// failed.
bool rename_there(Core &core, const char *from, const char *to) {
    return !is_there(core, from) || core.host.rename(core.host.ctx, from, to) == 1;
}

// One action of a commit record: whether it moves the file `from` onto the name, else removes
// the file of the name, each with a zero after it.
struct Action {
    bool moves;
    char from[kIndexNameRoom];
    char name[kCatalogNameMost + 1];
};

// The host's name of a file of a storage by its name there: a drive's with `drive/` before
// it, into room for 6 + kCatalogNameMost + 1 characters.
void host_name_of(uint32_t storage, const char *name, char *into) {
    uint32_t at = 0;
    if (storage == kExternal) {
        memcpy(into, "drive/", 6);
        at = 6;
    }
    copy_text(into + at, name);
}

// Does an action of a commit record on a storage. False when the call failed. Kept apart
// from the reading of the record, whose frame has the line, as it needs room for the host's
// names of the files.
ODRIG_NOINLINE bool act(Core &core, uint32_t storage, const Action &action) {
    char to[6 + kCatalogNameMost + 1];
    host_name_of(storage, action.name, to);
    if (!action.moves) {
        return core.host.remove(core.host.ctx, to) != -1;
    }
    char from[6 + kCatalogNameMost + 1];
    host_name_of(storage, action.from, from);
    return rename_there(core, from, to);
}

// Copies so many characters of a line, with a zero after them.
void take_name(char *into, const char *line, uint32_t length) {
    memcpy(into, line, length);
    into[length] = '\0';
}

// Reads one action line of a commit record, the word `move` or `remove` first, of `length`
// characters. Returns whether it is valid. With `give` the action is given in `action`;
// with `acting` it is done, and the return is also false when that failed. Kept apart from
// the reading of the record, whose frame has the line, as it needs room for the action.
ODRIG_NOINLINE bool take_action(Core &core, const Place &place, const char *line, uint32_t length, bool give, Action *action, bool acting) {
    const bool drive = place.storage == kExternal;
    Action found;
    found.moves = false;
    found.from[0] = '\0';
    uint32_t at = 0;
    bool whole;
    if (word(line, &at, "move ")) {
        // `move <from> <to>`: the upload's part onto a name of the catalog, or a new file
        // of a drive's index onto a file of it.
        uint32_t space = at;
        while (space < length && line[space] != ' ') {
            ++space;
        }
        const uint32_t from_length = space - at;
        const uint32_t to_length = space < length ? length - space - 1 : 0;
        const char *to = line + space + 1;
        if (space < length && is_part(line + at, from_length)) {
            whole = catalog_name_allowed(to, to_length);
        } else {
            whole = space < length && drive && is_index_name(line + at, from_length, true) && is_index_name(to, to_length, false);
        }
        if (whole) {
            found.moves = true;
            take_name(found.from, line + at, from_length);
            take_name(found.name, to, to_length);
        }
    } else if (word(line, &at, "remove ")) {
        const char *name = line + at;
        const uint32_t name_length = length - at;
        whole = catalog_name_allowed(name, name_length) || is_part(name, name_length) ||
                (drive && (is_index_name(name, name_length, false) || is_index_name(name, name_length, true)));
        if (whole) {
            take_name(found.name, name, name_length);
        }
    } else {
        whole = false;
    }
    if (whole && give) {
        *action = found;
    }
    return whole && (!acting || act(core, place.storage, found));
}

// Reads the commit record of a place whole. Returns whether it is whole; `mask` is its pages
// and `actions` the number of its actions. With `wanted` below kNothing the action at that
// position is given in `action`. With `acting` each action is done as soon as it is read,
// which the second source allows, as `read_at` does not mind the files that change: then
// the return is also false when an action failed. Without it nothing is done while the
// record is read: the first source reads one file at a time.
ODRIG_NOINLINE bool read_record(Core &core, const Place &place, uint32_t *mask, uint32_t *actions, uint32_t wanted, Action *action, bool acting) {
    FileSource &source = source_of(core, place);
    *actions = 0;
    if (open_for(core, place, kRecordNames[place.storage]) != kNone) {
        return false;
    }
    LineReader reader;
    char line[kCatalogLineRoom];
    uint32_t at = 0;
    uint32_t generation;
    bool whole = reader.next(source, line, sizeof line) == kLineGot && !reader.over && !reader.unended && word(line, &at, "odrig-catalog-do 1 generation ") &&
                 hexadecimal(line, &at, 8, &generation) && line[at] == '\0';
    at = 0;
    whole = whole && reader.next(source, line, sizeof line) == kLineGot && !reader.over && !reader.unended && word(line, &at, "pages ") &&
            hexadecimal(line, &at, 4, mask) && line[at] == '\0';
    bool ended = false;
    while (whole && !ended) {
        const uint32_t before = crc_value(reader.crc);
        if (reader.next(source, line, sizeof line) != kLineGot || reader.over || reader.unended) {
            whole = false;
            break;
        }
        at = 0;
        uint32_t sealed;
        if (word(line, &at, "crc ")) {
            whole = hexadecimal(line, &at, 8, &sealed) && line[at] == '\0' && sealed == before && reader.next(source, line, sizeof line) == kLineEnd;
            ended = true;
            continue;
        }
        whole = take_action(core, place, line, reader.length, *actions == wanted && action != nullptr, action, acting);
        ++*actions;
    }
    source.close();
    return whole && ended;
}

// Reads a marker of a place by its host's name: kCatalogOk with `marker`, kCatalogNone when
// there is none, kCatalogDamaged or kCatalogIncompatible.
uint8_t read_marker_of(Core &core, const Place &place, const char *name, Marker &marker, uint32_t *whole_crc = nullptr) {
    const Reason opened = open_for(core, place, name);
    if (opened == kFileMissing) {
        return kCatalogNone;
    }
    const uint8_t found = opened == kNone ? read_marker(source_of(core, place), marker, place.storage == kExternal, whole_crc) : kCatalogDamaged;
    source_of(core, place).close();
    return found;
}

// Finishes the change whose commit record is whole, on a place whose storage can be
// written: its actions, its pages, its marker, and the record removed, each step once the
// one before it is done. Returns whether no whole record is left: false when a call failed,
// and the record stays for the next attempt, which goes on where this one stopped.
ODRIG_NOINLINE bool finish(Core &core, const Place &place) {
    uint32_t mask = 0;
    uint32_t actions = 0;
    if (!read_record(core, place, &mask, &actions, kNothing, nullptr, false)) {
        return true;
    }
    if (place.second) {
        // The record is whole: it is read once more, and each action done as it is read.
        if (!read_record(core, place, &mask, &actions, kNothing, nullptr, true)) {
            return false;
        }
    } else {
        // Each action is read again on its own, and done once the record is closed.
        for (uint32_t index = 0; index < actions; ++index) {
            Action action;
            uint32_t count = 0;
            if (!read_record(core, place, &mask, &count, index, &action, false) || !act(core, place.storage, action)) {
                return false;
            }
        }
    }
    // The counts of the new marker, or of the marker when it was renamed already; a page
    // whose count is not known counts as one, so that it is not removed.
    const uint32_t storage = place.storage;
    Marker marker = {};
    uint8_t found = read_marker_of(core, place, kNewMarkerNames[storage], marker);
    if (found == kCatalogNone) {
        found = read_marker_of(core, place, kMarkerNames[storage], marker);
    }
    for (uint32_t page = 0; page < kCatalogPages; ++page) {
        if ((mask & (1u << page)) == 0) {
            continue;
        }
        if (is_there(core, kNewPageNames[storage][page])) {
            if (core.host.rename(core.host.ctx, kNewPageNames[storage][page], kPageNames[storage][page]) != 1) {
                return false;
            }
        } else if (found == kCatalogOk && marker.counts[page] == 0 && core.host.remove(core.host.ctx, kPageNames[storage][page]) == -1) {
            return false;
        }
    }
    return rename_there(core, kNewMarkerNames[storage], kMarkerNames[storage]) && core.host.remove(core.host.ctx, kRecordNames[storage]) != -1;
}

uint32_t text_size(const char *text) {
    uint32_t size = 0;
    while (text[size] != '\0') {
        ++size;
    }
    return size;
}

// Writes text into the chunk buffer from `*length` on.
void put(Core &core, uint32_t *length, const char *text) {
    put_text(core.chunk, length, text);
}

void put_number(Core &core, uint32_t *length, uint64_t value) {
    put_decimal(core.chunk, length, value);
}

void put_hex(Core &core, uint32_t *length, uint32_t value, uint32_t digits) {
    put_hexadecimal(core.chunk, length, value, digits);
}

// The sum of a marker's counts: the entries of its catalog.
uint32_t entries_of(const Marker &marker) {
    uint32_t entries = 0;
    for (uint32_t page = 0; page < kCatalogPages; ++page) {
        entries += marker.counts[page];
    }
    return entries;
}

// The generation after this one.
uint32_t next_generation(uint32_t generation) {
    return generation == 0xFFFFFFFFu ? 1 : generation + 1;
}

// Writes the chunk buffer's first `length` bytes as a new file, by its host's name. A file
// that is not written whole is removed, and its writing ends with it.
bool write_whole(Core &core, const char *name, uint32_t length) {
    const odrig_host &host = core.host;
    if (host.write_open(host.ctx, name) != 1) {
        return false;
    }
    if (host.write(host.ctx, core.chunk, length) == 1 && host.write_close(host.ctx) == 1) {
        return true;
    }
    host.remove(host.ctx, name);
    return false;
}

// Gives up the new page being written: the page read is closed, and the new one removed when
// it was begun.
bool give_up_page(Core &core, const char *fresh, bool opened) {
    core.checker->file.close();
    if (opened) {
        core.host.remove(core.host.ctx, fresh);
    }
    return false;
}

// Puts a number as ten decimal digits, leading zeros included.
void put_ten(Core &core, uint32_t *length, uint32_t value) {
    for (uint32_t divisor = 1000000000u;; divisor /= 10) {
        put_number(core, length, value / divisor % 10);
        if (divisor == 1) {
            break;
        }
    }
}

// Puts a marker's text into the chunk buffer from 0 on, and returns its length: 409 bytes
// of version 1, or for a drive 461 of version 2 with the lines of its index.
uint32_t marker_text(Core &core, const Marker &marker, bool drive) {
    uint32_t length = 0;
    put(core, &length, drive ? "odrig-catalog 2 check 1 generation " : "odrig-catalog 1 check 1 generation ");
    put_hex(core, &length, marker.generation, 8);
    put(core, &length, "\n");
    for (uint32_t page = 0; page < kCatalogPages; ++page) {
        put(core, &length, "page ");
        put_number(core, &length, page / 10);
        put_number(core, &length, page % 10);
        put(core, &length, " ");
        for (uint32_t divisor = 1000; divisor != 0; divisor /= 10) {
            put_number(core, &length, marker.counts[page] / divisor % 10);
        }
        put(core, &length, " ");
        put_hex(core, &length, marker.crcs[page], 8);
        put(core, &length, "\n");
    }
    if (drive) {
        put(core, &length, "folders ");
        put_ten(core, &length, marker.folders);
        put(core, &length, " ");
        put_hex(core, &length, marker.folders_crc, 8);
        put(core, &length, "\nids ");
        put_ten(core, &length, marker.ids);
        put(core, &length, " ");
        put_hex(core, &length, marker.ids_crc, 8);
        put(core, &length, "\n");
    }
    uint32_t crc = kCrcStart;
    for (uint32_t at = 0; at < length; ++at) {
        crc = crc_add(crc, core.chunk[at]);
    }
    put(core, &length, "crc ");
    put_hex(core, &length, crc_value(crc), 8);
    put(core, &length, "\n");
    return length;
}

// Puts the fields of the added entry of a change, without a line feed, into the chunk
// buffer from `*length` on: its CRC-32, size, canvas, length, type and name.
void put_entry_fields(Core &core, uint32_t *length, const CatalogChange &change) {
    put_hex(core, length, change.added_crc, 8);
    put(core, length, " ");
    put_number(core, length, change.added_bytes);
    put(core, length, " ");
    put_number(core, length, core.width);
    put(core, length, " ");
    put_number(core, length, core.height);
    put(core, length, " ");
    put_number(core, length, change.added_total_ms);
    put(core, length, " ");
    put(core, length, type_name(change.added_type));
    put(core, length, " ");
    put(core, length, change.added);
}

// Puts the line of the added entry of a change into the chunk buffer from `*length` on.
void put_entry(Core &core, uint32_t *length, const CatalogChange &change) {
    put_entry_fields(core, length, change);
    put(core, length, "\n");
}

// The most bytes of a file gathered in the chunk buffer before they go to the host.
const uint32_t kPageFlush = 1200;

// Writes the new page of a change from the old one: every line but the dropped ones, the
// added entry in the place of the line of its name, or last. Gives its count and CRC-32.
ODRIG_NOINLINE bool write_page(Core &core, uint32_t storage, uint32_t page, const Marker &old, const CatalogChange &change, uint16_t *count, uint32_t *crc) {
    const odrig_host &host = core.host;
    const char *fresh = kNewPageNames[storage][page];
    const Place place = {storage, true};
    const uint32_t added_length = change.added != nullptr ? text_size(change.added) : 0;
    const bool adds_here = change.added != nullptr && catalog_page_of(change.added, added_length) == page;
    bool placed = false;
    bool opened = false;
    uint32_t length = 0;
    uint32_t lines = 0;
    uint32_t sum = kCrcStart;
    LineReader reader;
    char line[kCatalogLineRoom];
    if (old.counts[page] != 0 && open_for(core, place, kPageNames[storage][page]) != kNone) {
        return false;
    }
    for (;;) {
        bool got = false;
        if (old.counts[page] != 0) {
            const LineRead read = reader.next(core.checker->file, line, sizeof line);
            if (read == kLineFailed || (read == kLineGot && (reader.over || reader.unended))) {
                return give_up_page(core, fresh, opened);
            }
            got = read == kLineGot;
        }
        if (got) {
            EntryLine entry;
            if (!parse_entry(line, reader.length, page, entry)) {
                return give_up_page(core, fresh, opened);
            }
            if (adds_here && entry.name_length == added_length && same_text(entry.name, change.added)) {
                put_entry(core, &length, change);
                placed = true;
            } else if (change.drops == nullptr || !change.drops(core, entry.name, entry.name_length, change.context)) {
                put_bytes(core.chunk, &length, line, reader.length);
                put(core, &length, "\n");
            } else {
                continue;
            }
        } else if (adds_here && !placed) {
            put_entry(core, &length, change);
            placed = true;
        } else {
            break;
        }
        ++lines;
        if (length >= kPageFlush) {
            for (uint32_t at = 0; at < length; ++at) {
                sum = crc_add(sum, core.chunk[at]);
            }
            if (!opened && host.write_open(host.ctx, fresh) != 1) {
                return give_up_page(core, fresh, false);
            }
            opened = true;
            if (host.write(host.ctx, core.chunk, length) != 1) {
                return give_up_page(core, fresh, true);
            }
            length = 0;
        }
    }
    core.checker->file.close();
    for (uint32_t at = 0; at < length; ++at) {
        sum = crc_add(sum, core.chunk[at]);
    }
    if (lines == 0) {
        // A new page left by a change that was not committed must not be finished.
        *count = 0;
        *crc = 0;
        return host.remove(host.ctx, fresh) != -1;
    }
    if (!opened && host.write_open(host.ctx, fresh) != 1) {
        return false;
    }
    if ((length != 0 && host.write(host.ctx, core.chunk, length) != 1) || host.write_close(host.ctx) != 1) {
        host.remove(host.ctx, fresh);
        return false;
    }
    *count = static_cast<uint16_t>(lines);
    *crc = crc_value(sum);
    return true;
}

// A file written line by line through the chunk buffer from its start, by its host's name:
// its bytes go to the host whenever kPageFlush of them wait, and its lines and CRC-32 are
// counted. A file without a line is not written.
struct Writer {
    const char *name;
    uint32_t length;
    uint32_t lines;
    uint32_t crc;
    bool opened;
};

Writer writer_for(const char *name) {
    Writer writer = {name, 0, 0, kCrcStart, false};
    return writer;
}

// Sends the bytes that wait to the host. False on a failed call, the file then removed.
bool writer_flush(Core &core, Writer &writer) {
    const odrig_host &host = core.host;
    for (uint32_t at = 0; at < writer.length; ++at) {
        writer.crc = crc_add(writer.crc, core.chunk[at]);
    }
    if (!writer.opened) {
        if (host.write_open(host.ctx, writer.name) != 1) {
            return false;
        }
        writer.opened = true;
    }
    if (writer.length != 0 && host.write(host.ctx, core.chunk, writer.length) != 1) {
        host.remove(host.ctx, writer.name);
        return false;
    }
    writer.length = 0;
    return true;
}

// Ends a line put at `start` of the chunk buffer: padded with spaces to `width` bytes with
// its line feed, or as it is for a width of 0, whose line has its line feed already.
bool writer_line(Core &core, Writer &writer, uint32_t start, uint32_t width) {
    if (width != 0) {
        put_padding(core.chunk, &writer.length, start, width);
    }
    ++writer.lines;
    return writer.length < kPageFlush || writer_flush(core, writer);
}

// Gives up the file: it is removed when it was begun.
bool writer_drop(Core &core, Writer &writer) {
    if (writer.opened) {
        core.host.remove(core.host.ctx, writer.name);
    }
    return false;
}

// Ends the file: false on a failed call, the file then removed. A file without a line is
// not written, and one of its name that a change which was not committed left is removed.
bool writer_close(Core &core, Writer &writer) {
    const odrig_host &host = core.host;
    if (writer.lines == 0) {
        return host.remove(host.ctx, writer.name) != -1;
    }
    if (!writer_flush(core, writer)) {
        return false;
    }
    if (host.write_close(host.ctx) != 1) {
        host.remove(host.ctx, writer.name);
        return false;
    }
    return true;
}

// The CRC-32 of a file written: 0 for one without a line.
uint32_t writer_crc(const Writer &writer) {
    return writer.lines == 0 ? 0 : crc_value(writer.crc);
}

// A change of the file of a folder of a drive's index, rewritten from its old file a line
// at a time: its id and ordinal, its old file rows and all its old lines; the row left
// out, or the row given the added entry with its own id, kNothing for none; the id of an
// added row, put after the file rows, or 0; the id of a sub-folder whose row is given
// `child_files` own files, or left out for kNothing, or 0 for none; and the row moved from
// `move_from` to stand at `move_to`, the rows between following, kNothing for none.
struct FolderEdit {
    uint32_t id;
    uint32_t ordinal;
    uint32_t files;
    uint32_t lines;
    uint32_t drop_row;
    uint32_t replace_row;
    uint32_t add_id;
    uint32_t child;
    uint32_t child_files;
    uint32_t move_from;
    uint32_t move_to;
};

// A change of the table: the lines from `gone_from` that go, `gone_count` of them, with
// the ordinals and the ends after them less as many; the own files of the folder
// `files_of` less one or one more, by `files_delta`; the first position of every folder
// after `firsts_after` moved by `first_delta`; the sub-folders of `folders_of` one less.
// kNothing for no folder.
struct TableEdit {
    uint32_t gone_from;
    uint32_t gone_count;
    uint32_t files_of;
    int32_t files_delta;
    uint32_t firsts_after;
    int32_t first_delta;
    uint32_t folders_of;
};

// A change of the map: the line `<add_id> f 0 <add_row>` put before line `insert_at`, or
// none for kNothing; the line of the id `drop_id` left out, or none for 0; the lines of the
// folders whose ordinals are from `gone_from`, `gone_count` of them, left out and the
// ordinals after them less as many; the rows after `row` of the folder `ordinal` one less,
// or none for kNothing; the rows of the folder `move_ordinal` as a move of the row
// `move_from` to `move_to` leaves them, or none for kNothing.
struct MapEdit {
    uint32_t insert_at;
    uint32_t add_id;
    uint32_t add_row;
    uint32_t drop_id;
    uint32_t gone_from;
    uint32_t gone_count;
    uint32_t ordinal;
    uint32_t row;
    uint32_t move_ordinal;
    uint32_t move_from;
    uint32_t move_to;
};

// The change of a drive's index that goes with a change of its catalog: the files of the
// folders it writes, in the table's order, the table, and the map when it changes; the ids
// of the folders whose files go. What is written: whether each folder's file has a line,
// and its CRC-32.
struct IndexChange {
    FolderEdit folders[2];
    uint32_t folder_count;
    TableEdit table;
    MapEdit map;
    bool map_changes;
    uint32_t gone_ids[kCatalogDeepest];
    uint32_t gone_count;
    uint32_t crcs[2];
    bool has_lines[2];
    uint32_t map_lines;
};

// An index change that changes nothing yet.
void clear_change(IndexChange &change) {
    change.folder_count = 0;
    change.table = {0, 0, kNothing, 0, kNothing, 0, kNothing};
    change.map = {kNothing, 0, 0, 0, 0, 0, kNothing, 0, kNothing, 0, 0};
    change.map_changes = false;
    change.gone_count = 0;
}

// A folder's file left as it is but for what the edit says.
FolderEdit edit_of(const IndexFolder &folder) {
    FolderEdit edit = {folder.id, folder.ordinal, folder.files, folder.files + folder.folders, kNothing, kNothing, 0, 0, 0, kNothing, 0};
    return edit;
}

// The row a file stands at after a move of the row `from` to `to`, for its row before it:
// the rows between follow.
uint32_t row_after_move(uint32_t row, uint32_t from, uint32_t to) {
    if (row == from) {
        return to;
    }
    if (from < to && row > from && row <= to) {
        return row - 1;
    }
    if (to < from && row >= to && row < from) {
        return row + 1;
    }
    return row;
}

// The row before the move of the file that stands at a row after it.
uint32_t row_before_move(uint32_t row, uint32_t from, uint32_t to) {
    if (row == to) {
        return from;
    }
    if (from < to && row >= from && row < to) {
        return row + 1;
    }
    if (to < from && row > to && row <= from) {
        return row - 1;
    }
    return row;
}

// Puts a file row of the added entry of a change, with its id, into the chunk buffer.
void put_row(Core &core, uint32_t *length, uint32_t id, const CatalogChange &change) {
    put_number(core, length, id);
    put(core, length, " f ");
    put_entry_fields(core, length, change);
}

// Writes the new file of a folder of the index from its old one, as the edit says, and
// gives whether it has a line and its CRC-32. False on a failed call or a line that cannot
// be read, the new file then removed.
ODRIG_NOINLINE bool write_folder(Core &core, const FolderEdit &edit, const CatalogChange &change, bool *has_lines, uint32_t *crc) {
    char old_name[kIndexNameRoom];
    char fresh[kIndexNameRoom];
    index_folder_name(edit.id, false, old_name);
    index_folder_name(edit.id, true, fresh);
    Writer writer = writer_for(fresh);
    for (uint32_t line_at = 0; line_at <= edit.lines; ++line_at) {
        if (line_at == edit.files && edit.add_id != 0) {
            const uint32_t start = writer.length;
            put_row(core, &writer.length, edit.add_id, change);
            if (!writer_line(core, writer, start, kIndexRow)) {
                return false;
            }
        }
        if (line_at == edit.lines) {
            break;
        }
        if (line_at == edit.drop_row) {
            continue;
        }
        const uint32_t source = edit.move_from != kNothing && line_at < edit.files ? row_before_move(line_at, edit.move_from, edit.move_to) : line_at;
        uint32_t length = 0;
        const char *text = index_line(core, old_name, kIndexRow, source, &length);
        uint32_t at = 0;
        uint32_t id = 0;
        if (text == nullptr || !decimal32(text, &at, &id)) {
            return writer_drop(core, writer);
        }
        const uint32_t start = writer.length;
        if (line_at == edit.replace_row) {
            // The row of the replaced file: the added entry, with the file's id.
            put_row(core, &writer.length, id, change);
        } else if (line_at >= edit.files && edit.child != 0 && id == edit.child) {
            // The row of the sub-folder that changes: `<id> d <files> <path>`.
            uint32_t files = 0;
            if (!word(text, &at, " d ") || !decimal32(text, &at, &files) || !word(text, &at, " ")) {
                return writer_drop(core, writer);
            }
            if (edit.child_files == kNothing) {
                continue;
            }
            put_number(core, &writer.length, id);
            put(core, &writer.length, " d ");
            put_number(core, &writer.length, edit.child_files);
            put(core, &writer.length, " ");
            put_bytes(core.chunk, &writer.length, text + at, length - at);
        } else {
            put_bytes(core.chunk, &writer.length, text, length);
        }
        if (!writer_line(core, writer, start, kIndexRow)) {
            return false;
        }
    }
    if (!writer_close(core, writer)) {
        return false;
    }
    *has_lines = writer.lines != 0;
    *crc = writer_crc(writer);
    return true;
}

// Moves a number by a step that may be below 0.
uint32_t moved(uint32_t value, int32_t delta) {
    return static_cast<uint32_t>(static_cast<int64_t>(value) + delta);
}

// Writes the new table from the old one, as the change says, with the CRC-32s of the
// folders' files it wrote. Gives its lines and CRC-32.
ODRIG_NOINLINE bool write_table(Core &core, const IndexChange &change, uint32_t *lines, uint32_t *crc) {
    const TableEdit &edit = change.table;
    const uint32_t past = edit.gone_from + edit.gone_count;
    Writer writer = writer_for(kIndexTableNew);
    for (uint32_t ordinal = 0; ordinal < core.index->folders; ++ordinal) {
        if (ordinal >= edit.gone_from && ordinal < past) {
            continue;
        }
        uint32_t length = 0;
        const char *text = index_line(core, kIndexTable, kIndexRow, ordinal, &length);
        IndexFolder folder;
        uint32_t path_at = 0;
        uint32_t path_length = 0;
        if (text == nullptr || !index_parse_folder(text, length, ordinal, folder, &path_at, &path_length)) {
            return writer_drop(core, writer);
        }
        uint32_t folder_crc = folder.crc;
        for (uint32_t at = 0; at < change.folder_count; ++at) {
            if (change.folders[at].ordinal == ordinal) {
                folder_crc = change.has_lines[at] ? change.crcs[at] : 0;
            }
        }
        const uint32_t start = writer.length;
        put_number(core, &writer.length, ordinal >= past ? ordinal - edit.gone_count : ordinal);
        put(core, &writer.length, " ");
        put_number(core, &writer.length, folder.id);
        put(core, &writer.length, " ");
        put_number(core, &writer.length, folder.depth);
        put(core, &writer.length, " ");
        put_number(core, &writer.length, folder.end >= past ? folder.end - edit.gone_count : folder.end);
        put(core, &writer.length, " ");
        put_number(core, &writer.length, edit.firsts_after != kNothing && ordinal > edit.firsts_after ? moved(folder.first, edit.first_delta) : folder.first);
        put(core, &writer.length, " ");
        put_number(core, &writer.length, ordinal == edit.files_of ? moved(folder.files, edit.files_delta) : folder.files);
        put(core, &writer.length, " ");
        put_number(core, &writer.length, ordinal == edit.folders_of ? folder.folders - 1 : folder.folders);
        put(core, &writer.length, " ");
        put_hex(core, &writer.length, folder_crc, 8);
        if (path_length != 0) {
            put(core, &writer.length, " ");
            put_bytes(core.chunk, &writer.length, text + path_at, path_length);
        }
        if (!writer_line(core, writer, start, kIndexRow)) {
            return false;
        }
    }
    if (!writer_close(core, writer)) {
        return false;
    }
    *lines = writer.lines;
    *crc = writer_crc(writer);
    return true;
}

// Puts a line of the map into the chunk buffer.
void put_id_line(Core &core, uint32_t *length, uint32_t id, uint8_t kind, uint32_t ordinal, uint32_t row) {
    put_number(core, length, id);
    put(core, length, kind == 'f' ? " f " : " d ");
    put_number(core, length, ordinal);
    put(core, length, " ");
    put_number(core, length, row);
}

// Writes the new map from the old one, as the change says. Gives its lines and CRC-32.
ODRIG_NOINLINE bool write_map(Core &core, const IndexChange &change, uint32_t *lines, uint32_t *crc) {
    const MapEdit &edit = change.map;
    const uint32_t past = edit.gone_from + edit.gone_count;
    const uint32_t count = core.index->ids;
    Writer writer = writer_for(kIndexMapNew);
    for (uint32_t line_at = 0; line_at <= count; ++line_at) {
        if (line_at == edit.insert_at) {
            const uint32_t start = writer.length;
            put_id_line(core, &writer.length, edit.add_id, 'f', 0, edit.add_row);
            if (!writer_line(core, writer, start, kIndexIdRow)) {
                return false;
            }
        }
        if (line_at == count) {
            break;
        }
        uint32_t length = 0;
        const char *text = index_line(core, kIndexMap, kIndexIdRow, line_at, &length);
        uint32_t id = 0;
        uint8_t kind = 0;
        uint32_t ordinal = 0;
        uint32_t row = 0;
        if (text == nullptr || !index_parse_id(text, length, &id, &kind, &ordinal, &row)) {
            return writer_drop(core, writer);
        }
        if (id == edit.drop_id || (kind == 'd' && ordinal >= edit.gone_from && ordinal < past)) {
            continue;
        }
        if (kind == 'f' && ordinal == edit.ordinal && row > edit.row) {
            --row;
        }
        if (kind == 'f' && ordinal == edit.move_ordinal) {
            row = row_after_move(row, edit.move_from, edit.move_to);
        }
        const uint32_t start = writer.length;
        put_id_line(core, &writer.length, id, kind, ordinal >= past ? ordinal - edit.gone_count : ordinal, row);
        if (!writer_line(core, writer, start, kIndexIdRow)) {
            return false;
        }
    }
    if (!writer_close(core, writer)) {
        return false;
    }
    *lines = writer.lines;
    *crc = writer_crc(writer);
    return true;
}

// Writes the new files of the index that a change of the drive's catalog makes, and puts the
// lines and CRC-32s of the new table and map into the marker.
ODRIG_NOINLINE bool write_index(Core &core, IndexChange &index, const CatalogChange &change, Marker &marker) {
    for (uint32_t at = 0; at < index.folder_count; ++at) {
        if (!write_folder(core, index.folders[at], change, &index.has_lines[at], &index.crcs[at])) {
            return false;
        }
    }
    if (!write_table(core, index, &marker.folders, &marker.folders_crc)) {
        return false;
    }
    if (index.map_changes && !write_map(core, index, &marker.ids, &marker.ids_crc)) {
        return false;
    }
    index.map_lines = marker.ids;
    return true;
}

// Puts a line of a commit record into the writer, and sends what waits when it is enough.
bool record_line(Core &core, Writer &writer) {
    ++writer.lines;
    return writer.length < kPageFlush || writer_flush(core, writer);
}

// Puts `move index-<id>.new index-<id>.txt`, or `remove index-<id>.txt` for a file without
// a line, into a record.
bool record_folder(Core &core, Writer &writer, uint32_t id, bool has_lines) {
    char name[kIndexNameRoom];
    if (has_lines) {
        index_folder_name(id, true, name);
        put(core, &writer.length, "move ");
        put(core, &writer.length, name + 6);
        put(core, &writer.length, " ");
    } else {
        put(core, &writer.length, "remove ");
    }
    index_folder_name(id, false, name);
    put(core, &writer.length, name + 6);
    put(core, &writer.length, "\n");
    return record_line(core, writer);
}

// Puts the record's first two lines into a writer.
void record_head(Core &core, Writer &writer, uint32_t generation, uint32_t mask) {
    put(core, &writer.length, "odrig-catalog-do 1 generation ");
    put_hex(core, &writer.length, generation, 8);
    put(core, &writer.length, "\npages ");
    put_hex(core, &writer.length, mask, 4);
    put(core, &writer.length, "\n");
}

// Ends a record: its `crc` line, over every byte before it, those sent and those that wait,
// and the file closed: a record that fits in the chunk buffer goes in one write.
bool record_close(Core &core, Writer &writer) {
    uint32_t crc = writer.crc;
    for (uint32_t at = 0; at < writer.length; ++at) {
        crc = crc_add(crc, core.chunk[at]);
    }
    put(core, &writer.length, "crc ");
    put_hex(core, &writer.length, crc_value(crc), 8);
    put(core, &writer.length, "\n");
    ++writer.lines;
    return writer_close(core, writer);
}

// Writes the commit record of a change: the removals of the files of the folders that went,
// the animation's action, then the moves of the index's new files.
ODRIG_NOINLINE bool write_record(Core &core, uint32_t storage, uint32_t generation, uint32_t mask, const CatalogChange &change, const IndexChange *index) {
    Writer writer = writer_for(kRecordNames[storage]);
    record_head(core, writer, generation, mask);
    for (uint32_t at = 0; index != nullptr && at < index->gone_count; ++at) {
        if (!record_folder(core, writer, index->gone_ids[at], false)) {
            return false;
        }
    }
    if (change.moves_part) {
        put(core, &writer.length, "move upload.part ");
        put(core, &writer.length, change.added);
        put(core, &writer.length, "\n");
    }
    if (change.removed_file != nullptr) {
        put(core, &writer.length, "remove ");
        put(core, &writer.length, change.removed_file);
        put(core, &writer.length, "\n");
    }
    if (index != nullptr) {
        for (uint32_t at = 0; at < index->folder_count; ++at) {
            if (!record_folder(core, writer, index->folders[at].id, index->has_lines[at])) {
                return false;
            }
        }
        put(core, &writer.length, "move index-folders.new index-folders.txt\n");
        if (index->map_changes) {
            put(core, &writer.length, index->map_lines != 0 ? "move index-ids.new index-ids.txt\n" : "remove index-ids.txt\n");
        }
    }
    return record_close(core, writer);
}

// Commits a change of a storage's catalog and finishes it, as catalog_commit does; a change
// of a drive's catalog with the change of its index, after which the cursor reads the new
// index.
ODRIG_NOINLINE bool commit_change(Core &core, uint32_t storage, const CatalogChange &change, IndexChange *index) {
    if (!catalog_settle(core, storage)) {
        return false;
    }
    CatalogState &catalog = core.catalogs[storage];
    if (catalog.state != kCatalogOk) {
        return true;
    }
    const Place place = {storage, true};
    Marker marker = {};
    if (read_marker_of(core, place, kMarkerNames[storage], marker) != kCatalogOk) {
        return false;
    }
    uint32_t mask = change.drop_pages;
    if (change.added != nullptr) {
        mask |= 1u << catalog_page_of(change.added, text_size(change.added));
    }
    for (uint32_t page = 0; page < kCatalogPages; ++page) {
        if ((mask & (1u << page)) != 0 && !write_page(core, storage, page, marker, change, &marker.counts[page], &marker.crcs[page])) {
            return false;
        }
    }
    if (index != nullptr && !write_index(core, *index, change, marker)) {
        return false;
    }
    marker.generation = next_generation(marker.generation);
    const uint32_t marker_length = marker_text(core, marker, storage == kExternal);
    uint32_t marker_crc = kCrcStart;
    for (uint32_t at = 0; at < marker_length; ++at) {
        marker_crc = crc_add(marker_crc, core.chunk[at]);
    }
    if (!write_whole(core, kNewMarkerNames[storage], marker_length)) {
        return false;
    }
    if (!write_record(core, storage, marker.generation, mask, change, index)) {
        return false;
    }
    // Committed: when a call fails now, what is left of it is finished before the next change
    // of the storage, or at the next start or plug-in.
    finish(core, place);
    catalog.generation = marker.generation;
    catalog.entries = entries_of(marker);
    if (storage == kExternal) {
        // The drive's marker is now this one: the look does not take it for another.
        core.catalog_marker_crc = crc_value(marker_crc);
    }
    if (index != nullptr) {
        DriveIndex &cursor = *core.index;
        cursor.folders = marker.folders;
        cursor.ids = marker.ids;
        cursor.files = marker.ids - (marker.folders - 1);
        index_forget(core);
    }
    return true;
}

// Reads one page of the internal catalog. Without `apply` it checks the page and marks the
// files of the show it has entries for, so that a name twice is found; with `apply` it gives
// them their size and length, and quarantines a file of another canvas. False when the page
// is damaged; `detail` then says where.
bool read_internal_page(Core &core, uint32_t page, const Marker &marker, bool apply, uint8_t *detail) {
    FileSource &source = core.file;
    if (source.open(core.host, kPageNames[kInternal][page]) != kNone) {
        *detail = kDamagedPage;
        return false;
    }
    LineReader reader;
    char line[kCatalogLineRoom];
    uint32_t lines = 0;
    bool lines_sound = true;
    bool unended = false;
    LineRead read;
    while ((read = reader.next(source, line, sizeof line)) == kLineGot) {
        ++lines;
        unended = unended || reader.unended;
        EntryLine entry;
        if (reader.over || reader.unended || !parse_entry(line, reader.length, page, entry)) {
            lines_sound = false;
            continue;
        }
        for (uint32_t file = 0; file < core.file_count; ++file) {
            FileInfo &info = core.files[file];
            if (!same_text(info.name, entry.name)) {
                continue;
            }
            if (!apply) {
                // A file marked already has its name in the catalog twice.
                lines_sound = lines_sound && info.checked != kCheckedFromCatalog;
                info.checked = kCheckedFromCatalog;
                break;
            }
            info.bytes = entry.bytes;
            info.total_ms = entry.total_ms;
            info.type = entry.type;
            if (entry.width != core.width || entry.height != core.height) {
                quarantine_file(core, file, kSizeMismatch, kWorkStart, 0, 0);
            }
            break;
        }
    }
    source.close();
    if (read == kLineFailed || unended || lines != marker.counts[page] || crc_value(reader.crc) != marker.crcs[page]) {
        *detail = kDamagedPage;
        return false;
    }
    if (!lines_sound) {
        *detail = kDamagedLine;
        return false;
    }
    return true;
}

// The words of the states of a catalog and of where a damaged one is damaged.
const char *const kStates[] = {"none", "ok", "loading", "damaged", "incompatible", "absent"};
const char *const kDetails[] = {"", "marker", "page", "line", "interrupted"};

void write_state(const CatalogState &catalog, Reply &reply) {
    reply.text("{\"state\":\"");
    reply.text(kStates[catalog.state]);
    reply.text("\"");
    if (catalog.state == kCatalogDamaged) {
        reply.text(",\"detail\":\"");
        reply.text(kDetails[catalog.detail]);
        reply.text("\"");
    }
    if (catalog.state == kCatalogOk || catalog.state == kCatalogLoading) {
        reply.text(",\"generation\":");
        reply.number(catalog.generation);
        reply.text(",\"entries\":");
        reply.number(catalog.entries);
    }
}

// The drive is read neither from its index nor from its table: none of its files is an
// animation, and the positions the player holds of it go.
void drive_dropped(Core &core) {
    core.indexed = 0;
    index_forget(core);
    core.drive_count = 0;
    core.drive_check_at = 0;
    core.repeats_due = 0;
    tree_clear(core);
    repeats_drive_found(core);
    brightness_drive_found(core);
    ignored_drive_found(core);
    player_drive_changed(core);
}

// The external storage's state and its log line, once its catalog cannot be read: nothing
// of the drive is an animation.
void drive_unusable(Core &core, uint8_t state, uint8_t detail) {
    core.catalog_phase = kLoadIdle;
    CatalogState &catalog = core.catalogs[kExternal];
    catalog.state = state;
    catalog.detail = state == kCatalogDamaged ? detail : 0;
    if (core.host.log != nullptr) {
        core.host.log(core.host.ctx, state == kCatalogIncompatible ? "catalog external incompatible" : "catalog external damaged");
    }
    drive_dropped(core);
}

// A marker of version 2 that was read: the drive is read from its index at once. Every file
// it names is in the playlist and in `list`, and none of its rows is read until it is
// needed; the current playlist's folder is found again by its path.
void publish(Core &core, const Marker &marker) {
    DriveIndex &cursor = *core.index;
    core.drive_count = 0;
    core.drive_check_at = 0;
    tree_clear(core);
    index_forget(core);
    cursor.folders = marker.folders;
    cursor.ids = marker.ids;
    cursor.files = marker.ids - (marker.folders - 1);
    cursor.left_out = 0;
    cursor.broken = 0;
    core.indexed = 1;
    core.tree_known = 1;
    tree_find_current(core);
    core.catalog_phase = kLoadIdle;
    CatalogState &catalog = core.catalogs[kExternal];
    catalog.state = kCatalogOk;
    catalog.detail = 0;
    catalog.generation = marker.generation;
    catalog.entries = entries_of(marker);
    core.catalog_looked = core.latest;
    // The drive's saved repeats, before any of its files plays.
    repeats_drive_taken(core);
    brightness_start(core);
    ignored_start(core);
    if (core.playing == kNothing) {
        const uint32_t first = player_first_in_playlist(core);
        if (first != kNothing && is_drive(first)) {
            player_drive_joined(core, first - kDriveBase);
        }
    }
}

}  // namespace

bool catalog_name_allowed(const char *name, uint32_t length) {
    // A path from the card's folder: the names of at most kCatalogDeepest folders and the
    // file's name, joined by `/`, 1 to kCatalogNameMost bytes in all. Each part is printable
    // ASCII other than \ : * ? " < > |, neither beginning nor ending with a space or a dot;
    // a folder's may be digits alone, the file's is not and ends in `.odrg` or `.odrgx`.
    if (length < 6 || length > kCatalogNameMost) {
        return false;
    }
    uint32_t folders = 0;
    uint32_t start = 0;
    for (uint32_t at = 0; at <= length; ++at) {
        if (at < length && name[at] != '/') {
            const char c = name[at];
            if (c < 0x20 || c > 0x7E || c == '\\' || c == ':' || c == '*' || c == '?' || c == '"' || c == '<' || c == '>' || c == '|') {
                return false;
            }
            continue;
        }
        // A part ends here: at a `/` or at the end of the name.
        if (at == start || name[start] == '.' || name[start] == ' ' || name[at - 1] == '.' || name[at - 1] == ' ') {
            return false;
        }
        if (at < length) {
            if (++folders > kCatalogDeepest) {
                return false;
            }
            start = at + 1;
        }
    }
    // The file's part: not digits alone, and ending in `.odrg` or `.odrgx`, in any case.
    const uint32_t file_length = length - start;
    bool digits_only = true;
    for (uint32_t at = start; at < length; ++at) {
        digits_only = digits_only && name[at] >= '0' && name[at] <= '9';
    }
    const uint32_t ending = (name[length - 1] == 'x' || name[length - 1] == 'X') ? 6 : 5;
    const char tail[] = ".odrgx";
    if (file_length < ending + 1) {
        return false;
    }
    const char *end = name + length - ending;
    for (uint32_t at = 0; at < ending; ++at) {
        const char c = end[at] >= 'A' && end[at] <= 'Z' ? static_cast<char>(end[at] - 'A' + 'a') : end[at];
        if (c != tail[at]) {
            return false;
        }
    }
    return !digits_only;
}

uint32_t catalog_page_of(const char *name, uint32_t length) {
    uint32_t hash = 2166136261u;
    for (uint32_t at = 0; at < length; ++at) {
        hash = (hash ^ static_cast<uint8_t>(name[at])) * 16777619u;
    }
    return hash & 15u;
}

void catalog_finish_internal(Core &core) {
    CatalogState &catalog = core.catalogs[kInternal];
    catalog.state = kCatalogNone;
    catalog.detail = 0;
    const Place place = {kInternal, false};
    if (storage_changes(core) && core.host.read_at != nullptr && !finish(core, place)) {
        catalog.state = kCatalogDamaged;
        catalog.detail = kDamagedInterrupted;
    }
}

bool catalog_left(const Core &core, uint32_t storage) {
    const CatalogState &catalog = core.catalogs[storage];
    return catalog.state == kCatalogDamaged && catalog.detail == kDamagedInterrupted;
}

bool catalog_settle(Core &core, uint32_t storage) {
    CatalogState &catalog = core.catalogs[storage];
    if (catalog.state != kCatalogOk && !catalog_left(core, storage)) {
        // Without a catalog that is kept, no change of this boot has written a record.
        return true;
    }
    drive_check_yields(core);
    const Place place = {storage, true};
    if (!finish(core, place)) {
        return false;
    }
    Marker marker = {};
    if (catalog_left(core, storage) && read_marker_of(core, place, kMarkerNames[storage], marker) == kCatalogOk) {
        // The change the start could not finish is finished: the catalog is kept from here on.
        catalog.state = kCatalogOk;
        catalog.detail = 0;
        catalog.generation = marker.generation;
        catalog.entries = entries_of(marker);
    }
    return true;
}

bool catalog_commit(Core &core, uint32_t storage, const CatalogChange &change) {
    return commit_change(core, storage, change, nullptr);
}

void catalog_read_internal(Core &core) {
    CatalogState &catalog = core.catalogs[kInternal];
    const bool left = catalog_left(core, kInternal);
    catalog.state = kCatalogNone;
    catalog.detail = 0;
    catalog.generation = 0;
    catalog.entries = 0;
    uint32_t mask = 0;
    const Place place = {kInternal, false};
    uint32_t actions = 0;
    if (left || (!storage_changes(core) && read_record(core, place, &mask, &actions, kNothing, nullptr, false))) {
        // A whole commit record that this host cannot finish, or that the start could not.
        catalog.state = kCatalogDamaged;
        catalog.detail = kDamagedInterrupted;
    }
    FileSource &source = core.file;
    const Reason opened = catalog.state == kCatalogNone ? source.open(core.host, kMarkerNames[kInternal]) : kNone;
    if (catalog.state == kCatalogNone && opened == kFileMissing) {
        return;
    }
    Marker marker = {};
    if (catalog.state == kCatalogNone) {
        catalog.state = opened == kNone ? read_marker(source, marker, false) : kCatalogDamaged;
        catalog.detail = catalog.state == kCatalogDamaged ? kDamagedMarker : 0;
        source.close();
    }
    // Every page is checked before any entry is taken, and then read again to take them.
    for (uint32_t pass = 0; pass < 2; ++pass) {
        for (uint32_t page = 0; page < kCatalogPages && catalog.state == kCatalogOk; ++page) {
            if (marker.counts[page] != 0 && !read_internal_page(core, page, marker, pass == 1, &catalog.detail)) {
                catalog.state = kCatalogDamaged;
            }
        }
    }
    if (catalog.state != kCatalogOk) {
        // A catalog that cannot be read gives nothing: every file is read as without one.
        for (uint32_t file = 0; file < core.file_count; ++file) {
            core.files[file].fault = kNone;
            core.files[file].checked = 0;
            core.files[file].bytes = 0;
            core.files[file].total_ms = 0;
        }
        if (core.host.log != nullptr) {
            core.host.log(core.host.ctx, catalog.state == kCatalogIncompatible ? "catalog internal incompatible" : "catalog internal damaged");
        }
        return;
    }
    catalog.generation = marker.generation;
    catalog.entries = entries_of(marker);
}

void catalog_drive_plugged(Core &core) {
    CatalogState &catalog = core.catalogs[kExternal];
    catalog.generation = 0;
    catalog.entries = 0;
    catalog.detail = 0;
    const bool given_names = core.drive != nullptr && core.index != nullptr && core.host.drive_bind != nullptr && core.drive_number != 0;
    core.catalog_phase = given_names ? kLoadRecord : kLoadIdle;
    catalog.state = core.drive_number == 0 ? kCatalogAbsent : given_names ? kCatalogLoading : kCatalogNone;
}

bool catalog_drive_loading(const Core &core) {
    return core.drive != nullptr && core.catalog_phase != kLoadIdle;
}

void catalog_drive_step(Core &core) {
    const Place place = {kExternal, true};
    CatalogState &catalog = core.catalogs[kExternal];
    const bool writable = core.host.drive_writable != nullptr && core.host.drive_writable(core.host.ctx, core.drive_number) == 1;
    if (core.catalog_phase == kLoadRecord) {
        uint32_t mask = 0;
        uint32_t actions = 0;
        if (read_record(core, place, &mask, &actions, kNothing, nullptr, false)) {
            // A record that cannot be finished keeps the upload's part it may move.
            if (!writable || !finish(core, place)) {
                drive_unusable(core, kCatalogDamaged, kDamagedInterrupted);
                return;
            }
        }
        if (writable) {
            // What a change or a rebuild that was not committed left.
            if (is_there(core, kPartNames[kExternal])) {
                core.host.remove(core.host.ctx, kPartNames[kExternal]);
            }
            if (is_there(core, kRebuildScan)) {
                core.host.remove(core.host.ctx, kRebuildScan);
            }
            if (is_there(core, kRebuildDraft)) {
                core.host.remove(core.host.ctx, kRebuildDraft);
            }
        }
        core.catalog_phase = kLoadMarker;
        return;
    }
    Marker marker = {};
    const uint8_t found = read_marker_of(core, place, kMarkerNames[kExternal], marker, &core.catalog_marker_crc);
    if (found == kCatalogNone) {
        // A drive without a catalog is listed and checked as before.
        core.catalog_phase = kLoadIdle;
        catalog.state = kCatalogNone;
        drive_take_listed(core);
        return;
    }
    if (found != kCatalogOk || marker.ids < marker.folders - 1) {
        drive_unusable(core, found != kCatalogOk ? found : kCatalogDamaged, kDamagedMarker);
        return;
    }
    publish(core, marker);
}

void catalog_drive_look(Core &core) {
    if (core.drive == nullptr || core.drive_number == 0 || core.catalog_phase != kLoadIdle || core.catalogs[kExternal].state != kCatalogOk ||
        core.rebuild == 1 + kExternal) {
        return;
    }
    if (core.indexed && core.index->broken) {
        // A line of the index could not be read: the drive's animations go.
        drive_unusable(core, kCatalogDamaged, kDamagedLine);
        return;
    }
    if (core.latest - core.catalog_looked < kLookEveryMs || core.upload.state != kUploadNone || !check_complete(core) || core.check_header_read) {
        return;
    }
    core.catalog_looked = core.latest;
    const Place place = {kExternal, true};
    Marker marker = {};
    uint32_t crc = 0;
    if (read_marker_of(core, place, kMarkerNames[kExternal], marker, &crc) == kCatalogOk && crc == core.catalog_marker_crc) {
        return;
    }
    // Another marker: the drive's animations go, and its catalog is read again.
    drive_dropped(core);
    catalog_drive_plugged(core);
}

bool catalog_drive_writable(const Core &core) {
    return core.drive != nullptr && core.drive_number != 0 && core.catalogs[kExternal].state == kCatalogOk && core.catalog_phase == kLoadIdle &&
           core.indexed && core.host.drive_writable != nullptr && core.host.drive_writable(core.host.ctx, core.drive_number) == 1;
}

namespace {

// Whether a name is the one given as the context.
bool is_named(const Core &, const char *name, uint32_t length, const void *context) {
    const char *given = static_cast<const char *>(context);
    uint32_t at = 0;
    for (; at < length && given[at] == name[at]; ++at) {
    }
    return at == length && given[at] == '\0';
}

// The lowest id from kDriveFirstId up that the map does not hold: the first line whose id is
// not kDriveFirstId and its number, found by binary search, and that line's number. 0 when
// the map cannot be read.
uint32_t lowest_free_id(const Core &core, uint32_t *line_at) {
    uint32_t low = 0;
    uint32_t high = core.index->ids;
    while (low < high) {
        const uint32_t middle = low + (high - low) / 2;
        uint32_t length = 0;
        const char *text = index_line(core, kIndexMap, kIndexIdRow, middle, &length);
        uint32_t id = 0;
        uint8_t kind = 0;
        uint32_t ordinal = 0;
        uint32_t row = 0;
        if (text == nullptr || !index_parse_id(text, length, &id, &kind, &ordinal, &row)) {
            return 0;
        }
        if (id == kDriveFirstId + middle) {
            low = middle + 1;
        } else {
            high = middle;
        }
    }
    *line_at = low;
    return low <= 0xFFFFFFFFu - kDriveFirstId ? kDriveFirstId + low : 0;
}

// The positions of the drive's walk changed: the current playlist's folder is found again,
// and its record read anew.
void current_again(Core &core) {
    tree_find_current(core);
}

}  // namespace

bool catalog_install_external(Core &core, uint32_t *id) {
    const Upload &upload = core.upload;
    if (!core.indexed) {
        return false;
    }
    // A file of the root of this name is replaced, keeping its row and its id.
    IndexFolder root;
    if (!drive_folder(core, 0, root)) {
        return false;
    }
    uint32_t replaced = kNothing;
    uint32_t kept_id = 0;
    for (uint32_t row = 0; row < root.files && replaced == kNothing; ++row) {
        const DriveRow *found = drive_row(core, row);
        if (found == nullptr) {
            return false;
        }
        if (same_text(found->name, upload.name)) {
            replaced = row;
            kept_id = found->id;
        }
    }
    IndexChange index;
    clear_change(index);
    index.folder_count = 1;
    index.folders[0] = edit_of(root);
    uint32_t new_id = kept_id;
    if (replaced != kNothing) {
        player_releases_file(core, kDriveBase + replaced);
        index.folders[0].replace_row = replaced;
    } else {
        uint32_t line_at = 0;
        new_id = lowest_free_id(core, &line_at);
        if (new_id == 0) {
            return false;
        }
        index.folders[0].add_id = new_id;
        index.table.files_of = 0;
        index.table.files_delta = 1;
        index.table.firsts_after = 0;
        index.table.first_delta = 1;
        index.map_changes = true;
        index.map.insert_at = line_at;
        index.map.add_id = new_id;
        index.map.add_row = root.files;
    }
    CatalogChange change;
    change.added = upload.name;
    change.added_bytes = upload.size;
    change.added_crc = crc_value(upload.crc);
    change.added_total_ms = upload.total_ms;
    change.added_type = core.check_content.type;
    change.moves_part = true;
    if (!commit_change(core, kExternal, change, &index)) {
        return false;
    }
    current_again(core);
    // The positions of the walk after the new file moved: the saved repeats find their files
    // again.
    repeats_reload(core);
    brightness_start(core);
    ignored_start(core);
    if (replaced != kNothing) {
        // What plays it plays the new file from its start.
        player_file_replaced(core, kDriveBase + replaced);
    } else {
        // The new file is the root's last: every position at or after it moves on by one.
        player_drive_shifted(core, root.files, 1);
        player_drive_joined(core, root.files);
    }
    *id = new_id;
    return true;
}

namespace {

// The change of the index that removes the file at a position of the walk, of the folder at
// an ordinal: the folder's file without its row, or, when nothing is left at or below the
// folder, the folder and each ancestor left without a file out of the table, their files
// removed and the row of the topmost in its parent's file. Gives the row of the file in its
// folder. False when the table cannot be read.
ODRIG_NOINLINE bool plan_removal(const Core &core, uint32_t position, uint32_t ordinal, uint32_t file_id, IndexChange &index) {
    // The folder of the file and each of its ancestors, by depth, the root at 0.
    IndexFolder chain[kCatalogDeepest + 1];
    IndexFolder folder;
    if (!drive_folder(core, ordinal, folder)) {
        return false;
    }
    const uint32_t depth = folder.depth;
    chain[depth] = folder;
    for (uint32_t level = depth; level > 0; --level) {
        // The parent: the nearest folder before it in the table that is one level up.
        uint32_t before = chain[level].ordinal;
        do {
            if (before == 0 || !drive_folder(core, --before, folder)) {
                return false;
            }
        } while (folder.depth != level - 1);
        chain[level - 1] = folder;
    }
    const uint32_t row_at = position - chain[depth].first;
    // The levels from `top` down to the file's leave the table.
    uint32_t top = depth + 1;
    uint32_t files_left = chain[depth].files - 1;
    uint32_t folders_left = chain[depth].folders;
    for (uint32_t level = depth; level > 0 && files_left == 0 && folders_left == 0; --level) {
        top = level;
        files_left = chain[level - 1].files;
        folders_left = chain[level - 1].folders - 1;
    }
    clear_change(index);
    index.map_changes = true;
    index.map.drop_id = file_id;
    index.map.ordinal = ordinal;
    index.map.row = row_at;
    index.table.firsts_after = ordinal;
    index.table.first_delta = -1;
    if (top <= depth) {
        const uint32_t gone_from = chain[top].ordinal;
        const uint32_t gone_count = depth - top + 1;
        for (uint32_t level = top; level <= depth; ++level) {
            index.gone_ids[index.gone_count++] = chain[level].id;
        }
        index.table.gone_from = gone_from;
        index.table.gone_count = gone_count;
        index.table.folders_of = chain[top - 1].ordinal;
        index.map.gone_from = gone_from;
        index.map.gone_count = gone_count;
        // The parent of the topmost that goes loses its row for it.
        index.folder_count = 1;
        index.folders[0] = edit_of(chain[top - 1]);
        index.folders[0].child = chain[top].id;
        index.folders[0].child_files = kNothing;
        return true;
    }
    index.table.files_of = ordinal;
    index.table.files_delta = -1;
    if (depth > 0) {
        // The parent's row for the folder gives one own file less.
        index.folders[index.folder_count] = edit_of(chain[depth - 1]);
        index.folders[index.folder_count].child = chain[depth].id;
        index.folders[index.folder_count].child_files = chain[depth].files - 1;
        ++index.folder_count;
    }
    index.folders[index.folder_count] = edit_of(chain[depth]);
    index.folders[index.folder_count].drop_row = row_at;
    ++index.folder_count;
    return true;
}

}  // namespace

bool catalog_move_external(Core &core, uint32_t position, uint32_t before) {
    const uint32_t ordinal = core.indexed ? drive_folder_of(core, position) : kNoFolder;
    IndexFolder folder;
    if (ordinal == kNoFolder || !drive_folder(core, ordinal, folder) || folder.files == 0) {
        return false;
    }
    const uint32_t from = position - folder.first;
    uint32_t to = folder.files - 1;
    if (before != kNothing) {
        const uint32_t target = before - folder.first;
        to = target > from ? target - 1 : target;
    }
    if (to == from) {
        // The file stands there already: nothing is written.
        return true;
    }
    IndexChange index;
    clear_change(index);
    index.folder_count = 1;
    index.folders[0] = edit_of(folder);
    index.folders[0].move_from = from;
    index.folders[0].move_to = to;
    index.map_changes = true;
    index.map.move_ordinal = ordinal;
    index.map.move_from = from;
    index.map.move_to = to;
    const CatalogChange change;
    if (!commit_change(core, kExternal, change, &index)) {
        return false;
    }
    current_again(core);
    player_drive_moved(core, position, folder.first + to);
    repeats_reload(core);
    brightness_start(core);
    ignored_start(core);
    return true;
}

bool catalog_remove_external(Core &core, uint32_t position) {
    if (!core.indexed) {
        return false;
    }
    const DriveRow *row = drive_row(core, position);
    if (row == nullptr) {
        return false;
    }
    char name[kCatalogNameMost + 1];
    copy_text(name, row->name);
    const uint32_t file_id = row->id;
    const uint32_t ordinal = drive_folder_of(core, position);
    IndexChange index;
    if (ordinal == kNoFolder || !plan_removal(core, position, ordinal, file_id, index)) {
        return false;
    }
    player_releases_file(core, kDriveBase + position);
    CatalogChange change;
    change.drops = is_named;
    change.context = name;
    change.drop_pages = 1u << catalog_page_of(name, text_size(name));
    change.removed_file = name;
    if (!commit_change(core, kExternal, change, &index)) {
        return false;
    }
    current_again(core);
    player_drive_shifted(core, position, -1);
    player_drive_changed(core);
    repeats_reload(core);
    brightness_start(core);
    ignored_start(core);
    return true;
}

namespace {

// Where each page's count and CRC-32 wait while a rebuild runs: six bytes a page.
const uint32_t kKeptPages = 1400;

void keep_page(Core &core, uint32_t page, uint16_t count, uint32_t crc) {
    uint8_t *at = core.chunk + kKeptPages + 6 * page;
    at[0] = static_cast<uint8_t>(count);
    at[1] = static_cast<uint8_t>(count >> 8);
    for (uint32_t byte = 0; byte < 4; ++byte) {
        at[2 + byte] = static_cast<uint8_t>(crc >> (8 * byte));
    }
}

void kept_page(const Core &core, uint32_t page, uint16_t *count, uint32_t *crc) {
    const uint8_t *at = core.chunk + kKeptPages + 6 * page;
    *count = static_cast<uint16_t>(at[0] | at[1] << 8);
    *crc = 0;
    for (uint32_t byte = 0; byte < 4; ++byte) {
        *crc |= static_cast<uint32_t>(at[2 + byte]) << (8 * byte);
    }
}

// The phases of a rebuild of the drive's catalog, docs/catalog.md, "A drive's index in a
// change": the scan of the listed files, the check of the old index, the pages, the draft of
// the table, the folders' files, the map, the table and the commit.
const uint8_t kScanPhase = 0;
const uint8_t kSoundPhase = 1;
const uint8_t kPagesPhase = 2;
const uint8_t kDraftPhase = 3;
const uint8_t kFoldersPhase = 4;
const uint8_t kMapPhase = 5;
const uint8_t kTablePhase = 6;
const uint8_t kCommitPhase = 7;

// The most lines of its files a phase of a drive's rebuild takes in one step.
const uint32_t kPassLines = 8;

// The id of the folder of the draft at an ordinal: the root's 0, the others' after the
// files' ids, in the table's order.
uint32_t draft_id(const DriveIndex &cursor, uint32_t ordinal) {
    return ordinal == 0 ? 0 : kDriveFirstId - 1 + cursor.rebuild_passed + ordinal;
}

// The check after the start takes up the show's files that are neither checked nor faulted.
void check_takes_up(Core &core) {
    core.check_at = 0;
    while (core.check_at < core.file_count && (core.files[core.check_at].fault != kNone || core.files[core.check_at].checked)) {
        ++core.check_at;
    }
    core.check_done = core.check_at >= core.file_count ? 1 : 0;
}

// Removes every file a rebuild of the drive's catalog may have written: its new pages, its
// folders' new files, the new table and map, and its own two files.
void remove_rebuild_files(Core &core) {
    const DriveIndex &cursor = *core.index;
    const odrig_host &host = core.host;
    for (uint32_t page = 0; cursor.rebuild_phase >= kPagesPhase && page < kCatalogPages && page <= core.rebuild_page; ++page) {
        host.remove(host.ctx, kNewPageNames[kExternal][page]);
    }
    const uint32_t written = cursor.rebuild_phase > kFoldersPhase ? cursor.rebuild_kept : cursor.rebuild_phase == kFoldersPhase ? cursor.rebuild_ordinal + 1 : 0;
    for (uint32_t ordinal = 0; ordinal < written && ordinal < cursor.rebuild_kept; ++ordinal) {
        char name[kIndexNameRoom];
        index_folder_name(draft_id(cursor, ordinal), true, name);
        host.remove(host.ctx, name);
    }
    host.remove(host.ctx, kIndexTableNew);
    host.remove(host.ctx, kIndexMapNew);
    host.remove(host.ctx, kRebuildScan);
    host.remove(host.ctx, kRebuildDraft);
}

// Ends a rebuild without its commit: what it wrote is given up and removed, but from a
// drive that is gone; the check after the start, or a drive's own check, takes up the files
// the rebuild did not read.
void rebuild_ends(Core &core, bool removes) {
    const uint32_t storage = core.rebuild - 1;
    if (core.checker != nullptr) {
        core.checker->file.close();
    }
    core.check_header_read = 0;
    if (storage == kExternal) {
        if (core.rebuild_open) {
            core.host.write_close(core.host.ctx);
            core.rebuild_open = 0;
        }
        if (removes) {
            remove_rebuild_files(core);
        }
        index_forget(core);
        core.rebuild = 0;
        core.drive_check_at = 0;
        return;
    }
    if (core.rebuild_open) {
        core.host.remove(core.host.ctx, kNewPageNames[storage][core.rebuild_page]);
    }
    // The new pages already written go too: without their record they are never read.
    for (uint32_t page = 0; page < core.rebuild_page && page < kCatalogPages; ++page) {
        uint16_t count = 0;
        uint32_t crc = 0;
        kept_page(core, page, &count, &crc);
        if (count != 0) {
            core.host.remove(core.host.ctx, kNewPageNames[storage][page]);
        }
    }
    core.rebuild = 0;
    core.rebuild_open = 0;
    check_takes_up(core);
}

// A storage call of the rebuild failed: it ends, and the catalog stays as it was.
void rebuild_failed(Core &core) {
    if (core.host.log != nullptr) {
        core.host.log(core.host.ctx, "catalog rebuild failed: storage-error");
    }
    rebuild_ends(core, true);
}

// Whether the rebuild of the internal catalog reads the file `at` on its page.
bool rebuild_takes(const Core &core, uint32_t at, uint32_t page) {
    const FileInfo &info = core.files[at];
    const uint32_t length = text_size(info.name);
    return info.fault == kNone && catalog_name_allowed(info.name, length) && catalog_page_of(info.name, length) == page;
}

// Writes the chunk buffer's first `length` bytes, a line, to the file the rebuild writes, by
// its host's name: the file is opened at its first line, and its lines and CRC-32 counted.
bool rebuild_write(Core &core, const char *name, uint32_t length) {
    const odrig_host &host = core.host;
    if (!core.rebuild_open) {
        if (host.write_open(host.ctx, name) != 1) {
            return false;
        }
        core.rebuild_open = 1;
    }
    for (uint32_t at = 0; at < length; ++at) {
        core.rebuild_crc = crc_add(core.rebuild_crc, core.chunk[at]);
    }
    ++core.rebuild_lines;
    return host.write(host.ctx, core.chunk, length) == 1;
}

// The file the rebuild writes is done: closed, or, without a line, a file of its name that a
// rebuild which was not committed left removed. Gives its lines and CRC-32, 0 for none.
bool rebuild_end_file(Core &core, const char *name, uint32_t *lines, uint32_t *crc) {
    const odrig_host &host = core.host;
    *lines = core.rebuild_open ? core.rebuild_lines : 0;
    *crc = core.rebuild_open ? crc_value(core.rebuild_crc) : 0;
    core.rebuild_lines = 0;
    core.rebuild_crc = kCrcStart;
    if (!core.rebuild_open) {
        return host.remove(host.ctx, name) != -1;
    }
    core.rebuild_open = 0;
    if (host.write_close(host.ctx) != 1) {
        host.remove(host.ctx, name);
        return false;
    }
    return true;
}

// Writes one line of the page of the internal catalog being made.
bool rebuild_line(Core &core, const char *name, uint32_t crc, uint32_t bytes, uint64_t total_ms, uint8_t type) {
    uint32_t length = 0;
    put_hex(core, &length, crc, 8);
    put(core, &length, " ");
    put_number(core, &length, bytes);
    put(core, &length, " ");
    put_number(core, &length, core.width);
    put(core, &length, " ");
    put_number(core, &length, core.height);
    put(core, &length, " ");
    put_number(core, &length, total_ms);
    put(core, &length, " ");
    put(core, &length, type_name(type));
    put(core, &length, " ");
    put(core, &length, name);
    put(core, &length, "\n");
    return rebuild_write(core, kNewPageNames[kInternal][core.rebuild_page], length);
}

// The page is done: its count and CRC-32 kept, and the next page's turn.
bool rebuild_close_page(Core &core, uint32_t storage) {
    uint32_t lines = 0;
    uint32_t crc = 0;
    if (!rebuild_end_file(core, kNewPageNames[storage][core.rebuild_page], &lines, &crc)) {
        return false;
    }
    keep_page(core, core.rebuild_page, static_cast<uint16_t>(lines), crc);
    ++core.rebuild_page;
    return true;
}

// The last page of the internal catalog is done: the marker and the commit record for every
// page, and the finishing.
bool rebuild_commit(Core &core) {
    const Place place = {kInternal, true};
    Marker marker = {};
    const uint8_t old = read_marker_of(core, place, kMarkerNames[kInternal], marker);
    // The page summaries are taken from the chunk before the marker's text overwrites it.
    for (uint32_t page = 0; page < kCatalogPages; ++page) {
        kept_page(core, page, &marker.counts[page], &marker.crcs[page]);
    }
    marker.generation = old == kCatalogOk ? next_generation(marker.generation) : 1;
    if (!write_whole(core, kNewMarkerNames[kInternal], marker_text(core, marker, false))) {
        return false;
    }
    Writer record = writer_for(kRecordNames[kInternal]);
    record_head(core, record, marker.generation, 0xFFFF);
    if (!record_close(core, record)) {
        return false;
    }
    finish(core, place);
    CatalogState &catalog = core.catalogs[kInternal];
    catalog.state = kCatalogOk;
    catalog.detail = 0;
    catalog.generation = marker.generation;
    catalog.entries = entries_of(marker);
    // A file whose name the catalog cannot hold is checked as without a catalog.
    check_takes_up(core);
    return true;
}

// A line of the scan's file: whether its file passed, its text from the entry's fields on,
// and of a file that passed its entry.
struct ScanLine {
    bool passed;
    const char *text;
    uint32_t length;
    EntryLine entry;
};

// Reads line `number` of the scan's file.
bool scan_line(Core &core, uint32_t number, ScanLine &line) {
    uint32_t length = 0;
    const char *text = index_line(core, kRebuildScan, kIndexRow, number, &length);
    if (text == nullptr || length < 2 || text[1] != ' ' || (text[0] != '0' && text[0] != '1')) {
        return false;
    }
    line.passed = text[0] == '1';
    line.text = text + 2;
    line.length = length - 2;
    return !line.passed || parse_fields(line.text, line.length, line.entry);
}

// A line of the draft of the table: a folder's depth, the position of its first file in the
// walk, and its path, in the cursor's room.
struct DraftLine {
    uint32_t depth;
    uint32_t first;
    const char *path;
    uint32_t path_length;
};

// Reads the line of the draft of the folder at an ordinal.
bool draft_line(Core &core, uint32_t ordinal, DraftLine &line) {
    uint32_t length = 0;
    const char *text = index_line(core, kRebuildDraft, kIndexRow, ordinal, &length);
    uint32_t at = 0;
    uint32_t number = 0;
    if (text == nullptr || !decimal32(text, &at, &number) || number != ordinal || !word(text, &at, " ") || !decimal32(text, &at, &line.depth) ||
        !word(text, &at, " ") || !decimal32(text, &at, &line.first)) {
        return false;
    }
    line.path = text + at;
    line.path_length = 0;
    if (at < length) {
        if (!word(text, &at, " ")) {
            return false;
        }
        line.path = text + at;
        line.path_length = length - at;
    }
    return true;
}

// The own files of the folder of the draft at an ordinal, whose first position is `first`:
// to the next folder's first position, or to the end of the walk.
bool draft_files(Core &core, uint32_t ordinal, uint32_t first, uint32_t *files) {
    const DriveIndex &cursor = *core.index;
    uint32_t after = cursor.rebuild_passed;
    if (ordinal + 1 < cursor.rebuild_kept) {
        DraftLine next;
        if (!draft_line(core, ordinal + 1, next)) {
            return false;
        }
        after = next.first;
    }
    if (after < first) {
        return false;
    }
    *files = after - first;
    return true;
}

// The path of line `number` of the scan's file, in the cursor's room, its length and whether
// its file passed. False when the line is not in its form.
bool scan_path(Core &core, uint32_t number, const char **path, uint32_t *length, bool *passed) {
    ScanLine line;
    if (!scan_line(core, number, line)) {
        return false;
    }
    *passed = line.passed;
    if (line.passed) {
        *path = line.entry.name;
        *length = line.entry.name_length;
        return true;
    }
    // `00000000 0 0 0 0 frames <path>`.
    uint32_t spaces = 0;
    uint32_t at = 0;
    while (at < line.length && spaces < 6) {
        spaces += line.text[at++] == ' ' ? 1 : 0;
    }
    *path = line.text + at;
    *length = line.length - at;
    return spaces == 6 && *length != 0;
}

// Whether a path comes before another in the listing's order: a folder's files by the bytes
// of their names, then its sub-folders by the bytes of their names, each the same way.
bool listed_before(const char *a, uint32_t a_length, const char *b, uint32_t b_length) {
    uint32_t at = 0;
    while (at < a_length && at < b_length && a[at] == b[at]) {
        ++at;
    }
    bool a_file = true;
    for (uint32_t look = at; look < a_length; ++look) {
        a_file = a_file && a[look] != '/';
    }
    bool b_file = true;
    for (uint32_t look = at; look < b_length; ++look) {
        b_file = b_file && b[look] != '/';
    }
    if (a_file != b_file) {
        return a_file;
    }
    const uint32_t byte_a = at < a_length && a[at] != '/' ? static_cast<uint8_t>(a[at]) + 1u : 0;
    const uint32_t byte_b = at < b_length && b[at] != '/' ? static_cast<uint8_t>(b[at]) + 1u : 0;
    return byte_a < byte_b;
}

// The line of the scan's file of a path, found by binary search in the listing's order, and
// whether its file passed; kNothing when no line has it.
ODRIG_NOINLINE uint32_t scan_find(Core &core, const char *name, uint32_t length, bool *passed) {
    char wanted[kDrivePathRoom];
    if (length >= kDrivePathRoom) {
        return kNothing;
    }
    memcpy(wanted, name, length);
    uint32_t low = 0;
    uint32_t high = core.index->scan_lines;
    while (low < high) {
        const uint32_t middle = low + (high - low) / 2;
        const char *path = nullptr;
        uint32_t path_length = 0;
        bool found_passed = false;
        if (!scan_path(core, middle, &path, &path_length, &found_passed)) {
            return kNothing;
        }
        if (path_length == length && memcmp(path, wanted, length) == 0) {
            *passed = found_passed;
            return middle;
        }
        if (listed_before(path, path_length, wanted, length)) {
            low = middle + 1;
        } else {
            high = middle;
        }
    }
    return kNothing;
}

// Whether a name has a line on its page of the drive's old catalog, which a rebuild leaves in
// place until its commit.
ODRIG_NOINLINE bool on_old_page(Core &core, const char *name, uint32_t length) {
    const uint32_t page = catalog_page_of(name, length);
    const Place place = {kExternal, true};
    if (open_for(core, place, kPageNames[kExternal][page]) != kNone) {
        return false;
    }
    LineReader reader;
    char line[kCatalogLineRoom];
    bool found = false;
    while (!found && reader.next(core.checker->file, line, sizeof line) == kLineGot) {
        EntryLine entry;
        found = !reader.over && parse_entry(line, reader.length, page, entry) && entry.name_length == length && memcmp(entry.name, name, length) == 0;
    }
    core.checker->file.close();
    return found;
}

// Whether a page of the old catalog is sound: its lines in their form and on it, as many and
// of the CRC-32 the marker gives.
ODRIG_NOINLINE bool page_sound(Core &core, uint32_t page, const Marker &marker) {
    const Place place = {kExternal, true};
    if (open_for(core, place, kPageNames[kExternal][page]) != kNone) {
        return false;
    }
    LineReader reader;
    char line[kCatalogLineRoom];
    uint32_t lines = 0;
    bool sound = true;
    LineRead read;
    while ((read = reader.next(core.checker->file, line, sizeof line)) == kLineGot) {
        EntryLine entry;
        sound = sound && !reader.over && !reader.unended && parse_entry(line, reader.length, page, entry);
        ++lines;
    }
    core.checker->file.close();
    return sound && read == kLineEnd && lines == marker.counts[page] && crc_value(reader.crc) == marker.crcs[page];
}

// Whether a file of the old index of lines of `width` bytes is sound: of `lines` lines when
// they are given, kNothing for any whole number of them, and of the CRC-32 `crc`, 0 for a file
// without a line; each line in the form `form` takes. Gives its lines.
template <typename Form>
bool index_file_sound(Core &core, const char *name, uint32_t width, uint32_t lines, uint32_t crc, uint32_t *count, Form form) {
    uint32_t sum = kCrcStart;
    uint32_t bytes = 0;
    for (;;) {
        const int32_t got = core.host.read_at(core.host.ctx, name, bytes, core.chunk, kFileBufferSize);
        if (got < 0) {
            if (bytes != 0) {
                return false;
            }
            break;
        }
        if (got == 0) {
            break;
        }
        for (int32_t at = 0; at < got; ++at) {
            sum = crc_add(sum, core.chunk[at]);
        }
        bytes += static_cast<uint32_t>(got);
    }
    *count = bytes / width;
    if (bytes % width != 0 || (lines != kNothing && *count != lines) || (bytes == 0 ? 0u : crc_value(sum)) != crc) {
        return false;
    }
    for (uint32_t number = 0; number < *count; ++number) {
        uint32_t length = 0;
        const char *text = index_line(core, name, width, number, &length);
        if (text == nullptr || !form(text, length, number)) {
            return false;
        }
    }
    return true;
}

// The check of the old index, one of its files at each step: the marker of version 2, whole;
// each page with lines, its lines in their form, as many and of the CRC-32 the marker gives;
// the table and the map, of the lines and the CRC-32s the marker gives, each line in its
// form; each folder's file, of the CRC-32 its line of the table gives, each row in its form.
// A rebuild keeps the rows' order of an old index that is sound.
ODRIG_NOINLINE void sound_step(Core &core) {
    DriveIndex &cursor = *core.index;
    const uint32_t at = cursor.rebuild_ordinal;
    const Place place = {kExternal, true};
    Marker marker = {};
    bool sound = read_marker_of(core, place, kMarkerNames[kExternal], marker) == kCatalogOk;
    bool done = !sound;
    uint32_t count = 0;
    if (sound && at < kCatalogPages) {
        sound = marker.counts[at] == 0 || page_sound(core, at, marker);
    } else if (sound && at == kCatalogPages) {
        sound = index_file_sound(core, kIndexTable, kIndexRow, marker.folders, marker.folders_crc, &count, [](const char *text, uint32_t length, uint32_t number) {
            IndexFolder folder;
            uint32_t path_at = 0;
            uint32_t path_length = 0;
            return index_parse_folder(text, length, number, folder, &path_at, &path_length);
        });
    } else if (sound && at == kCatalogPages + 1) {
        sound = index_file_sound(core, kIndexMap, kIndexIdRow, marker.ids, marker.ids_crc, &count, [](const char *text, uint32_t length, uint32_t) {
            uint32_t id = 0;
            uint8_t kind = 0;
            uint32_t ordinal = 0;
            uint32_t row = 0;
            return index_parse_id(text, length, &id, &kind, &ordinal, &row);
        });
    } else if (sound) {
        const uint32_t ordinal = at - kCatalogPages - 2;
        if (ordinal >= marker.folders) {
            done = true;
            cursor.old_folders = marker.folders;
        } else {
            uint32_t length = 0;
            const char *text = index_line(core, kIndexTable, kIndexRow, ordinal, &length);
            IndexFolder folder = {};
            uint32_t path_at = 0;
            uint32_t path_length = 0;
            sound = text != nullptr && index_parse_folder(text, length, ordinal, folder, &path_at, &path_length);
            if (sound && folder.crc != 0) {
                char name[kIndexNameRoom];
                index_folder_name(folder.id, false, name);
                sound = index_file_sound(core, name, kIndexRow, kNothing, folder.crc, &count, [](const char *row_text, uint32_t row_length, uint32_t) {
                    DriveRow row;
                    return index_parse_row(row_text, row_length, row);
                });
            }
        }
    }
    if (!sound || done) {
        if (!sound) {
            cursor.old_folders = 0;
        }
        cursor.rebuild_phase = kPagesPhase;
        cursor.rebuild_at = 0;
        core.rebuild_page = 0;
        index_forget(core);
        return;
    }
    ++cursor.rebuild_ordinal;
}

// The ordinal of the old table's folder of a path, and its line: kNothing for none. The
// search begins where the last one found its folder, the tables being in the same order.
ODRIG_NOINLINE uint32_t old_folder_of(Core &core, const char *path, uint32_t path_length, IndexFolder &found) {
    DriveIndex &cursor = *core.index;
    char wanted[kDrivePathRoom];
    if (path_length >= kDrivePathRoom) {
        return kNothing;
    }
    memcpy(wanted, path, path_length);
    for (uint32_t step = 0; step < cursor.old_folders; ++step) {
        const uint32_t ordinal = (cursor.old_search + step) % cursor.old_folders;
        uint32_t length = 0;
        const char *text = index_line(core, kIndexTable, kIndexRow, ordinal, &length);
        uint32_t path_at = 0;
        uint32_t found_length = 0;
        if (text == nullptr || !index_parse_folder(text, length, ordinal, found, &path_at, &found_length)) {
            return kNothing;
        }
        if (found_length == path_length && memcmp(text + path_at, wanted, path_length) == 0) {
            cursor.old_search = ordinal + 1;
            return ordinal;
        }
    }
    return kNothing;
}

// Puts the row of a file of the scan's file, with its id, into the chunk buffer.
bool put_scan_row(Core &core, uint32_t number, uint32_t id, uint32_t *length) {
    ScanLine line;
    if (!scan_line(core, number, line) || !line.passed) {
        return false;
    }
    put_number(core, length, id);
    put(core, length, " f ");
    put_bytes(core.chunk, length, line.text, line.length);
    return true;
}

// The scan: each listed file is checked with the check's steps and gets its line in the
// scan's file, `1` and its entry for a file that passed, `0` and zeros for another. A file
// of the table of a drive without a catalog joins the playlist, or is left out, at once.
ODRIG_NOINLINE void scan_step(Core &core) {
    DriveIndex &cursor = *core.index;
    if (core.rebuild_at >= core.rebuild_total) {
        uint32_t crc = 0;
        if (!rebuild_end_file(core, kRebuildScan, &cursor.scan_lines, &crc)) {
            rebuild_failed(core);
            return;
        }
        cursor.rebuild_phase = kSoundPhase;
        cursor.rebuild_ordinal = 0;
        cursor.old_folders = 0;
        cursor.old_search = 1;
        return;
    }
    // The file is read as the place of the listing, `drive/<place>`, and named by its path.
    if (!core.check_header_read) {
        drive_file_name(core.rebuild_at, core.drive_check_name);
    }
    Reason reason = kNone;
    uint32_t record = 0;
    const StepOutcome outcome = check_file_step(core, core.drive_check_name, &reason, &record);
    if (outcome == kStepGoingOn) {
        return;
    }
    const uint32_t at = core.rebuild_at++;
    ++core.rebuild_read;
    char path[kDrivePathRoom];
    if (core.host.drive_name(core.host.ctx, core.drive_number, at, path, sizeof path) != 1) {
        // The listing has no file there any more: it is passed over.
        return;
    }
    const uint32_t path_length = text_size(path);
    const bool in_table = !core.indexed && at < core.drive_count;
    const bool passed = outcome == kStepWhole && catalog_name_allowed(path, path_length);
    if (outcome == kStepFault && in_table) {
        core.drive[at].state = kDriveLeftOut;
        drive_left_out(core, at, reason);
    } else if (outcome == kStepWhole && in_table) {
        // A file whose name a catalog cannot hold plays now, and is not in the catalog.
        DriveEntry &entry = core.drive[at];
        entry.bytes = core.checker->file.taken;
        entry.total_ms = drive_length(core.check_total_ms);
        entry.type = core.check_content.type & 0x0F;
        entry.state = kDriveInPlaylist;
        player_drive_joined(core, at);
    }
    uint32_t length = 0;
    if (passed) {
        put(core, &length, "1 ");
        put_hex(core, &length, crc_value(core.checker->file.crc), 8);
        put(core, &length, " ");
        put_number(core, &length, core.checker->file.taken);
        put(core, &length, " ");
        put_number(core, &length, core.width);
        put(core, &length, " ");
        put_number(core, &length, core.height);
        put(core, &length, " ");
        put_number(core, &length, core.check_total_ms);
        put(core, &length, " ");
        put(core, &length, type_name(core.check_content.type));
        put(core, &length, " ");
    } else {
        put(core, &length, "0 00000000 0 0 0 0 frames ");
    }
    put_bytes(core.chunk, &length, path, path_length);
    put_padding(core.chunk, &length, 0, kIndexRow);
    if (!rebuild_write(core, kRebuildScan, length)) {
        rebuild_failed(core);
        return;
    }
    cursor.rebuild_passed += passed ? 1 : 0;
}

// The pages: for each page one pass over the scan's file writes the entries of its names.
ODRIG_NOINLINE void pages_step(Core &core) {
    DriveIndex &cursor = *core.index;
    if (core.rebuild_page >= kCatalogPages) {
        cursor.rebuild_phase = kDraftPhase;
        cursor.rebuild_at = 0;
        cursor.rebuild_kept = 0;
        cursor.rebuild_row = 0;
        return;
    }
    const char *fresh = kNewPageNames[kExternal][core.rebuild_page];
    for (uint32_t step = 0; step < kPassLines; ++step) {
        if (cursor.rebuild_at >= cursor.scan_lines) {
            uint32_t lines = 0;
            uint32_t crc = 0;
            if (!rebuild_end_file(core, fresh, &lines, &crc)) {
                rebuild_failed(core);
                return;
            }
            keep_page(core, core.rebuild_page, static_cast<uint16_t>(lines), crc);
            ++core.rebuild_page;
            cursor.rebuild_at = 0;
            return;
        }
        ScanLine line;
        if (!scan_line(core, cursor.rebuild_at, line)) {
            rebuild_failed(core);
            return;
        }
        ++cursor.rebuild_at;
        if (!line.passed || catalog_page_of(line.entry.name, line.entry.name_length) != core.rebuild_page) {
            continue;
        }
        uint32_t length = 0;
        put_bytes(core.chunk, &length, line.text, line.length);
        put(core, &length, "\n");
        if (!rebuild_write(core, fresh, length)) {
            rebuild_failed(core);
            return;
        }
    }
}

// Writes a line of the draft: a folder's ordinal, depth, first position and path.
bool draft_put(Core &core, uint32_t ordinal, uint32_t depth, uint32_t first, const char *path, uint32_t path_length) {
    uint32_t length = 0;
    put_number(core, &length, ordinal);
    put(core, &length, " ");
    put_number(core, &length, depth);
    put(core, &length, " ");
    put_number(core, &length, first);
    if (path_length != 0) {
        put(core, &length, " ");
        put_bytes(core.chunk, &length, path, path_length);
    }
    put_padding(core.chunk, &length, 0, kIndexRow);
    return rebuild_write(core, kRebuildDraft, length);
}

// The path of the file of the scan's line before which the draft is at, the last that
// passed, into room for kDrivePathRoom: empty for none.
bool draft_before(Core &core, char *before) {
    const DriveIndex &cursor = *core.index;
    before[0] = '\0';
    if (cursor.rebuild_end == 0) {
        return true;
    }
    ScanLine line;
    if (!scan_line(core, cursor.rebuild_end - 1, line) || !line.passed) {
        return false;
    }
    memcpy(before, line.entry.name, line.entry.name_length);
    before[line.entry.name_length] = '\0';
    return true;
}

// The draft: the root's line, then, as one pass over the scan's file meets the files that
// passed in the listing's order, which is depth first, a line for each folder that begins
// at a file, the folders it does not share with the file passed before it.
ODRIG_NOINLINE void draft_step(Core &core) {
    DriveIndex &cursor = *core.index;
    char before[kDrivePathRoom];
    if (cursor.rebuild_kept == 0) {
        if (!draft_put(core, 0, 0, 0, "", 0)) {
            rebuild_failed(core);
            return;
        }
        cursor.rebuild_kept = 1;
        cursor.rebuild_end = 0;
        return;
    }
    for (uint32_t step = 0; step < kPassLines; ++step) {
        if (cursor.rebuild_at >= cursor.scan_lines) {
            uint32_t lines = 0;
            uint32_t crc = 0;
            if (!rebuild_end_file(core, kRebuildDraft, &lines, &crc)) {
                rebuild_failed(core);
                return;
            }
            cursor.rebuild_phase = kFoldersPhase;
            cursor.rebuild_ordinal = 0;
            cursor.rebuild_step = 0;
            cursor.rebuild_row = 0;
            cursor.rebuild_at = 0;
            return;
        }
        ScanLine line;
        if (!scan_line(core, cursor.rebuild_at, line)) {
            rebuild_failed(core);
            return;
        }
        if (!line.passed) {
            ++cursor.rebuild_at;
            continue;
        }
        if (!draft_before(core, before) || !scan_line(core, cursor.rebuild_at, line)) {
            rebuild_failed(core);
            return;
        }
        ++cursor.rebuild_at;
        const char *path = line.entry.name;
        const uint32_t length = line.entry.name_length;
        uint32_t depth = 0;
        for (uint32_t at = 0; at < length; ++at) {
            depth += path[at] == '/' ? 1 : 0;
        }
        uint32_t before_depth = 0;
        for (uint32_t at = 0; before[at] != '\0'; ++at) {
            before_depth += before[at] == '/' ? 1 : 0;
        }
        // The folders it shares with the file before it, part by part with their `/`.
        uint32_t shared = 0;
        uint32_t at = 0;
        while (shared < depth && shared < before_depth) {
            uint32_t end = at;
            while (path[end] != '/') {
                ++end;
            }
            if (memcmp(path + at, before + at, end - at + 1) != 0) {
                break;
            }
            ++shared;
            at = end + 1;
        }
        for (uint32_t level = shared + 1; level <= depth; ++level) {
            uint32_t end = at;
            while (path[end] != '/') {
                ++end;
            }
            if (!draft_put(core, cursor.rebuild_kept, level, cursor.rebuild_row, path, end)) {
                rebuild_failed(core);
                return;
            }
            ++cursor.rebuild_kept;
            at = end + 1;
        }
        cursor.rebuild_end = cursor.rebuild_at;
        ++cursor.rebuild_row;
    }
}

// The rows of the old index's file of the folder of the draft at an ordinal, of the files
// that passed, in their order, at the next ids of the walk; then its own files that passed
// that the old pages have no line for, in the listing's order. A folder without an old file,
// and every folder of a drive whose old index is not sound, takes its files in the listing's
// order. Steps 0 to 2 of the folder.
ODRIG_NOINLINE bool folder_rows(Core &core, const DraftLine &folder, uint32_t files, const char *fresh, bool *ended) {
    DriveIndex &cursor = *core.index;
    *ended = false;
    uint32_t length = 0;
    // The folder's path, kept before the room is read again.
    char path[kDrivePathRoom];
    if (folder.path_length >= kDrivePathRoom) {
        return false;
    }
    memcpy(path, folder.path, folder.path_length);
    if (cursor.rebuild_step == 0) {
        // The old folder of its path: its ordinal, own files and the next row to read.
        IndexFolder old = {};
        cursor.rebuild_end = cursor.old_folders != 0 ? old_folder_of(core, path, folder.path_length, old) : kNothing;
        cursor.rebuild_folders = cursor.rebuild_end != kNothing ? old.files : 0;
        cursor.rebuild_files = cursor.rebuild_end != kNothing ? old.id : 0;
        cursor.rebuild_sum = 0;
        cursor.rebuild_row = 0;
        cursor.rebuild_step = 1;
        return true;
    }
    if (cursor.rebuild_step == 1) {
        if (cursor.rebuild_row >= cursor.rebuild_folders) {
            cursor.rebuild_step = 2;
            cursor.rebuild_row = 0;
            return true;
        }
        char old_name[kIndexNameRoom];
        index_folder_name(cursor.rebuild_files, false, old_name);
        uint32_t line_length = 0;
        const char *text = index_line(core, old_name, kIndexRow, cursor.rebuild_row++, &line_length);
        DriveRow row;
        if (text == nullptr || !index_parse_row(text, line_length, row) || row.kind != 'f') {
            return false;
        }
        const uint32_t name_length = text_size(row.name);
        uint32_t slash = name_length;
        while (slash > 0 && row.name[slash - 1] != '/') {
            --slash;
        }
        const uint32_t folder_length = slash == 0 ? 0 : slash - 1;
        if (folder_length != folder.path_length || memcmp(row.name, path, folder_length) != 0) {
            return true;
        }
        bool passed = false;
        const uint32_t line = scan_find(core, row.name, name_length, &passed);
        if (line == kNothing || !passed) {
            return true;
        }
        if (!put_scan_row(core, line, kDriveFirstId + folder.first + cursor.rebuild_sum, &length)) {
            return false;
        }
    } else {
        // The folder's own files that passed, the next of the scan's: those without a line on
        // the old pages are new.
        if (cursor.rebuild_row >= files) {
            *ended = true;
            return cursor.rebuild_sum == files;
        }
        ScanLine line;
        if (!scan_line(core, cursor.rebuild_at, line)) {
            return false;
        }
        const uint32_t number = cursor.rebuild_at++;
        if (!line.passed) {
            return true;
        }
        ++cursor.rebuild_row;
        if (cursor.rebuild_end != kNothing && on_old_page(core, line.entry.name, line.entry.name_length)) {
            return true;
        }
        if (!put_scan_row(core, number, kDriveFirstId + folder.first + cursor.rebuild_sum, &length)) {
            return false;
        }
    }
    put_padding(core.chunk, &length, 0, kIndexRow);
    ++cursor.rebuild_sum;
    return rebuild_write(core, fresh, length);
}

// The folders' files: for each folder of the draft, its files' rows, then a row for each of
// its sub-folders.
ODRIG_NOINLINE void folders_step(Core &core) {
    DriveIndex &cursor = *core.index;
    const uint32_t ordinal = cursor.rebuild_ordinal;
    if (ordinal >= cursor.rebuild_kept) {
        cursor.rebuild_phase = kMapPhase;
        cursor.rebuild_ordinal = 0;
        cursor.rebuild_step = 0;
        cursor.rebuild_row = 0;
        return;
    }
    char fresh[kIndexNameRoom];
    index_folder_name(draft_id(cursor, ordinal), true, fresh);
    DraftLine folder;
    uint32_t files = 0;
    if (!draft_line(core, ordinal, folder) || !draft_files(core, ordinal, folder.first, &files) || !draft_line(core, ordinal, folder)) {
        rebuild_failed(core);
        return;
    }
    const uint32_t depth = folder.depth;
    for (uint32_t step = 0; step < kPassLines; ++step) {
        uint32_t length = 0;
        if (cursor.rebuild_step < 3) {
            bool ended = false;
            if (!folder_rows(core, folder, files, fresh, &ended)) {
                rebuild_failed(core);
                return;
            }
            if (ended) {
                cursor.rebuild_step = 3;
                cursor.rebuild_row = ordinal + 1;
            }
            // The draft's line is read again: the rows read the room.
            if (!draft_line(core, ordinal, folder)) {
                rebuild_failed(core);
                return;
            }
            continue;
        } else {
            const uint32_t child = cursor.rebuild_row;
            DraftLine below = {};
            if (child < cursor.rebuild_kept && !draft_line(core, child, below)) {
                rebuild_failed(core);
                return;
            }
            if (child >= cursor.rebuild_kept || below.depth <= depth) {
                uint32_t lines = 0;
                uint32_t crc = 0;
                if (!rebuild_end_file(core, fresh, &lines, &crc)) {
                    rebuild_failed(core);
                    return;
                }
                ++cursor.rebuild_ordinal;
                cursor.rebuild_step = 0;
                cursor.rebuild_row = 0;
                return;
            }
            ++cursor.rebuild_row;
            if (below.depth != depth + 1) {
                continue;
            }
            uint32_t child_files = 0;
            if (!draft_files(core, child, below.first, &child_files) || !draft_line(core, child, below)) {
                rebuild_failed(core);
                return;
            }
            put_number(core, &length, draft_id(cursor, child));
            put(core, &length, " d ");
            put_number(core, &length, child_files);
            put(core, &length, " ");
            put_bytes(core.chunk, &length, below.path, below.path_length);
        }
        put_padding(core.chunk, &length, 0, kIndexRow);
        if (!rebuild_write(core, fresh, length)) {
            rebuild_failed(core);
            return;
        }
    }
}

// The map: the files' ids in the walk's order, each with its folder and row, then the
// folders' ids in the table's order.
ODRIG_NOINLINE void map_step(Core &core) {
    DriveIndex &cursor = *core.index;
    for (uint32_t step = 0; step < kPassLines; ++step) {
        uint32_t length = 0;
        if (cursor.rebuild_step == 0) {
            if (cursor.rebuild_ordinal >= cursor.rebuild_kept) {
                cursor.rebuild_step = 1;
                cursor.rebuild_ordinal = 1;
                continue;
            }
            DraftLine folder;
            uint32_t files = 0;
            if (!draft_line(core, cursor.rebuild_ordinal, folder) || !draft_files(core, cursor.rebuild_ordinal, folder.first, &files)) {
                rebuild_failed(core);
                return;
            }
            if (cursor.rebuild_row >= files) {
                ++cursor.rebuild_ordinal;
                cursor.rebuild_row = 0;
                continue;
            }
            put_id_line(core, &length, kDriveFirstId + folder.first + cursor.rebuild_row, 'f', cursor.rebuild_ordinal, cursor.rebuild_row);
            ++cursor.rebuild_row;
        } else {
            if (cursor.rebuild_ordinal >= cursor.rebuild_kept) {
                if (!rebuild_end_file(core, kIndexMapNew, &cursor.map_lines, &cursor.map_crc)) {
                    rebuild_failed(core);
                    return;
                }
                cursor.rebuild_phase = kTablePhase;
                cursor.rebuild_ordinal = 0;
                cursor.rebuild_step = 0;
                cursor.rebuild_row = 0;
                return;
            }
            put_id_line(core, &length, draft_id(cursor, cursor.rebuild_ordinal), 'd', cursor.rebuild_ordinal, 0);
            ++cursor.rebuild_ordinal;
        }
        put_padding(core.chunk, &length, 0, kIndexIdRow);
        if (!rebuild_write(core, kIndexMapNew, length)) {
            rebuild_failed(core);
            return;
        }
    }
}

// The table: for each folder of the draft its end, its own files and its sub-folders, then
// the CRC-32 of its file, read again whole, and its line.
ODRIG_NOINLINE void table_step(Core &core) {
    DriveIndex &cursor = *core.index;
    const uint32_t ordinal = cursor.rebuild_ordinal;
    if (ordinal >= cursor.rebuild_kept) {
        if (!rebuild_end_file(core, kIndexTableNew, &cursor.table_lines, &cursor.table_crc)) {
            rebuild_failed(core);
            return;
        }
        cursor.rebuild_phase = kCommitPhase;
        return;
    }
    DraftLine folder;
    if (!draft_line(core, ordinal, folder)) {
        rebuild_failed(core);
        return;
    }
    const uint32_t depth = folder.depth;
    const uint32_t first = folder.first;
    if (cursor.rebuild_step == 0) {
        uint32_t end = ordinal + 1;
        uint32_t folders = 0;
        for (; end < cursor.rebuild_kept; ++end) {
            DraftLine below;
            if (!draft_line(core, end, below)) {
                rebuild_failed(core);
                return;
            }
            if (below.depth <= depth) {
                break;
            }
            folders += below.depth == depth + 1 ? 1 : 0;
        }
        if (!draft_files(core, ordinal, first, &cursor.rebuild_files)) {
            rebuild_failed(core);
            return;
        }
        cursor.rebuild_end = end;
        cursor.rebuild_folders = folders;
        cursor.rebuild_sum = kCrcStart;
        cursor.rebuild_row = 0;
        cursor.rebuild_step = cursor.rebuild_files + folders != 0 ? 1 : 2;
        return;
    }
    if (cursor.rebuild_step == 1) {
        char fresh[kIndexNameRoom];
        index_folder_name(draft_id(cursor, ordinal), true, fresh);
        for (uint32_t step = 0; step < kPassLines; ++step) {
            const int32_t count = core.host.read_at(core.host.ctx, fresh, cursor.rebuild_row, core.chunk, kFileBufferSize);
            if (count < 0) {
                rebuild_failed(core);
                return;
            }
            if (count == 0) {
                cursor.rebuild_step = 2;
                return;
            }
            for (int32_t at = 0; at < count; ++at) {
                cursor.rebuild_sum = crc_add(cursor.rebuild_sum, core.chunk[at]);
            }
            cursor.rebuild_row += static_cast<uint32_t>(count);
        }
        return;
    }
    uint32_t length = 0;
    put_number(core, &length, ordinal);
    put(core, &length, " ");
    put_number(core, &length, draft_id(cursor, ordinal));
    put(core, &length, " ");
    put_number(core, &length, depth);
    put(core, &length, " ");
    put_number(core, &length, cursor.rebuild_end);
    put(core, &length, " ");
    put_number(core, &length, first);
    put(core, &length, " ");
    put_number(core, &length, cursor.rebuild_files);
    put(core, &length, " ");
    put_number(core, &length, cursor.rebuild_folders);
    put(core, &length, " ");
    put_hex(core, &length, cursor.rebuild_row != 0 ? crc_value(cursor.rebuild_sum) : 0, 8);
    if (folder.path_length != 0) {
        put(core, &length, " ");
        put_bytes(core.chunk, &length, folder.path, folder.path_length);
    }
    put_padding(core.chunk, &length, 0, kIndexRow);
    if (!rebuild_write(core, kIndexTableNew, length)) {
        rebuild_failed(core);
        return;
    }
    ++cursor.rebuild_ordinal;
    cursor.rebuild_step = 0;
    cursor.rebuild_row = 0;
}

// The commit: the marker of version 2 and the record with every page, the removals of the
// old index's folder files whose ids the new table has not, and the moves of the new files;
// the finishing, and the rebuild's own files removed.
ODRIG_NOINLINE bool commit_drive(Core &core) {
    const DriveIndex &cursor = *core.index;
    const Place place = {kExternal, true};
    Marker marker = {};
    const uint8_t old = read_marker_of(core, place, kMarkerNames[kExternal], marker);
    // The files of the old table's folders are removed only of an old index that is sound.
    const uint32_t old_folders = cursor.old_folders;
    marker.generation = old == kCatalogOk ? next_generation(marker.generation) : 1;
    for (uint32_t page = 0; page < kCatalogPages; ++page) {
        kept_page(core, page, &marker.counts[page], &marker.crcs[page]);
    }
    marker.folders = cursor.table_lines;
    marker.folders_crc = cursor.table_crc;
    marker.ids = cursor.map_lines;
    marker.ids_crc = cursor.map_crc;
    if (!write_whole(core, kNewMarkerNames[kExternal], marker_text(core, marker, true))) {
        return false;
    }
    Writer record = writer_for(kRecordNames[kExternal]);
    record_head(core, record, marker.generation, 0xFFFF);
    const uint32_t lowest = draft_id(cursor, 1);
    const uint32_t highest = draft_id(cursor, cursor.rebuild_kept - 1);
    for (uint32_t ordinal = 1; ordinal < old_folders; ++ordinal) {
        uint32_t length = 0;
        const char *text = index_line(core, kIndexTable, kIndexRow, ordinal, &length);
        IndexFolder folder;
        uint32_t path_at = 0;
        uint32_t path_length = 0;
        if (text == nullptr || !index_parse_folder(text, length, ordinal, folder, &path_at, &path_length) ||
            (cursor.rebuild_kept > 1 && folder.id >= lowest && folder.id <= highest)) {
            continue;
        }
        if (!record_folder(core, record, folder.id, false)) {
            return false;
        }
    }
    for (uint32_t ordinal = 0; ordinal < cursor.rebuild_kept; ++ordinal) {
        // Only the root of a drive without a file has no line.
        if (!record_folder(core, record, draft_id(cursor, ordinal), ordinal != 0 || cursor.rebuild_passed != 0)) {
            return false;
        }
    }
    put(core, &record.length, "move index-folders.new index-folders.txt\n");
    if (!record_line(core, record)) {
        return false;
    }
    put(core, &record.length, cursor.map_lines != 0 ? "move index-ids.new index-ids.txt\n" : "remove index-ids.txt\n");
    if (!record_line(core, record) || !record_close(core, record)) {
        return false;
    }
    finish(core, place);
    core.host.remove(core.host.ctx, kRebuildScan);
    core.host.remove(core.host.ctx, kRebuildDraft);
    return true;
}

// One step of a rebuild of the drive's catalog, in its phase.
void drive_rebuild_step(Core &core) {
    switch (core.index->rebuild_phase) {
    case kScanPhase:
        scan_step(core);
        return;
    case kSoundPhase:
        sound_step(core);
        return;
    case kPagesPhase:
        pages_step(core);
        return;
    case kDraftPhase:
        draft_step(core);
        return;
    case kFoldersPhase:
        folders_step(core);
        return;
    case kMapPhase:
        map_step(core);
        return;
    case kTablePhase:
        table_step(core);
        return;
    default:
        break;
    }
    if (!commit_drive(core)) {
        rebuild_failed(core);
        return;
    }
    core.rebuild = 0;
    // The drive is read again from its new index, as after another marker.
    drive_dropped(core);
    catalog_drive_plugged(core);
    while (catalog_drive_loading(core)) {
        catalog_drive_step(core);
    }
}

}  // namespace

uint32_t catalog_rebuild(Core &core, uint32_t storage, Reply &reply) {
    if (core.upload.state != kUploadNone || core.rebuild != 0 || core.mapping_test || catalog_drive_loading(core)) {
        return refuse(reply, "busy");
    }
    if (!storage_changes(core) || core.checker == nullptr || core.host.read_at == nullptr) {
        return refuse(reply, "read-only");
    }
    if (storage == kExternal &&
        (core.drive == nullptr || core.index == nullptr || core.drive_number == 0 || core.host.drive_writable == nullptr || core.host.drive_list == nullptr ||
         core.host.drive_bind == nullptr || core.host.drive_writable(core.host.ctx, core.drive_number) != 1)) {
        return refuse(reply, "read-only");
    }
    // A change that a failed call left is finished first: its record must not finish later
    // on the pages the rebuild writes.
    if (!catalog_settle(core, storage)) {
        return refuse(reply, "storage-error");
    }
    drive_check_yields(core);
    core.checker->file.close();
    core.check_header_read = 0;
    uint32_t total = 0;
    if (storage == kInternal) {
        // The check after the start gives way: the rebuild reads every file.
        core.check_done = 1;
        for (uint32_t file = 0; file < core.file_count; ++file) {
            const FileInfo &info = core.files[file];
            total += info.fault == kNone && catalog_name_allowed(info.name, text_size(info.name)) ? 1 : 0;
        }
    } else {
        int32_t listed = -1;
        if (core.indexed) {
            // The drive plays from its index, which the rebuild does not change, while its
            // folder is listed once and every file read.
            listed = core.host.drive_list(core.host.ctx, core.drive_number);
        } else {
            // The drive's animations go; its folder is listed once, and each file of its
            // table joins again as the rebuild reads it.
            core.drive_count = 0;
            player_drive_changed(core);
            drive_take_listed(core, &listed);
            core.drive_check_at = core.drive_count;
            core.catalogs[kExternal].state = kCatalogNone;
        }
        // Its places are named `drive/<place>`, with at most nine digits.
        total = listed > 999999999 ? 999999999u : listed > 0 ? static_cast<uint32_t>(listed) : 0;
        DriveIndex &cursor = *core.index;
        index_forget(core);
        cursor.rebuild_phase = kScanPhase;
        cursor.rebuild_step = 0;
        cursor.rebuild_at = 0;
        cursor.scan_lines = 0;
        cursor.rebuild_passed = 0;
        cursor.rebuild_kept = 0;
        cursor.rebuild_ordinal = 0;
        cursor.rebuild_row = 0;
    }
    core.rebuild = static_cast<uint8_t>(1 + storage);
    core.rebuild_page = 0;
    core.rebuild_open = 0;
    core.rebuild_at = 0;
    core.rebuild_read = 0;
    core.rebuild_total = total;
    core.rebuild_lines = 0;
    core.rebuild_crc = kCrcStart;
    return succeed(reply);
}

uint32_t catalog_cancel(Core &core, Reply &reply) {
    if (core.rebuild != 0) {
        rebuild_ends(core, true);
    }
    return succeed(reply);
}

void catalog_drive_went(Core &core) {
    if (core.rebuild == 1 + kExternal) {
        // The drive is gone: what the rebuild wrote stays on it, and is never read without a
        // record.
        rebuild_ends(core, false);
    }
}

void catalog_rebuild_step(Core &core) {
    if (core.rebuild == 1 + kExternal) {
        drive_rebuild_step(core);
        return;
    }
    if (core.rebuild_page >= kCatalogPages) {
        if (!rebuild_commit(core)) {
            rebuild_failed(core);
            return;
        }
        core.rebuild = 0;
        return;
    }
    while (core.rebuild_at < core.file_count && !rebuild_takes(core, core.rebuild_at, core.rebuild_page)) {
        ++core.rebuild_at;
    }
    if (core.rebuild_at >= core.file_count) {
        if (!rebuild_close_page(core, kInternal)) {
            rebuild_failed(core);
            return;
        }
        core.rebuild_at = 0;
        return;
    }
    const uint32_t at = core.rebuild_at;
    Reason reason = kNone;
    uint32_t record = 0;
    const StepOutcome outcome = check_file_step(core, core.files[at].name, &reason, &record);
    if (outcome == kStepGoingOn) {
        return;
    }
    ++core.rebuild_read;
    ++core.rebuild_at;
    if (outcome == kStepFault) {
        quarantine_file(core, at, reason, kWorkStart, record, core.checker->decoder.body_read);
        return;
    }
    FileInfo &info = core.files[at];
    info.bytes = core.checker->file.taken;
    info.total_ms = core.check_total_ms;
    info.type = core.check_content.type;
    info.checked = kCheckedFromCatalog;
    if (!rebuild_line(core, info.name, crc_value(core.checker->file.crc), info.bytes, info.total_ms, info.type)) {
        rebuild_failed(core);
    }
}

uint32_t catalog_reply(const Core &core, Reply &reply) {
    reply.text("{\"ok\":true,\"internal\":");
    write_state(core.catalogs[kInternal], reply);
    uint32_t uncataloged = 0;
    for (uint32_t file = 0; file < core.file_count; ++file) {
        uncataloged += core.files[file].checked != kCheckedFromCatalog ? 1 : 0;
    }
    reply.text(",\"uncataloged\":");
    reply.number(uncataloged);
    reply.text("},\"external\":");
    CatalogState external = core.catalogs[kExternal];
    if (core.drive == nullptr || core.drive_number == 0) {
        external.state = kCatalogAbsent;
    }
    write_state(external, reply);
    if (external.state != kCatalogAbsent) {
        reply.text(",\"writable\":");
        reply.text(core.host.drive_writable != nullptr && core.host.drive_writable(core.host.ctx, core.drive_number) == 1 ? "true" : "false");
    }
    reply.text("},\"rebuild\":");
    if (core.rebuild == 0) {
        reply.text("null}\n");
        return reply.length;
    }
    reply.text(core.rebuild == 1 + kInternal ? "{\"storage\":\"internal\",\"read\":" : "{\"storage\":\"external\",\"read\":");
    reply.number(core.rebuild_read);
    reply.text(",\"to_read\":");
    reply.number(core.rebuild_total > core.rebuild_read ? core.rebuild_total - core.rebuild_read : 0);
    reply.text("}}\n");
    return reply.length;
}

uint32_t catalog_page(Core &core, uint32_t storage, uint32_t page, uint32_t offset, Reply &reply) {
    if (!storage_changes(core)) {
        // Only the second source reads a file beside the one that plays.
        return refuse(reply, "storage-error");
    }
    if (core.rebuild == 1 + storage) {
        return refuse(reply, "busy");
    }
    const bool card_out = storage == kExternal && (core.drive == nullptr || core.drive_number == 0);
    const CatalogState &catalog = core.catalogs[storage];
    if (card_out || catalog.state != kCatalogOk) {
        reply.text("{\"ok\":true,\"generation\":null,\"text\":\"\",\"next\":null}\n");
        return reply.length;
    }
    // The bytes are read into the chunk buffer, which holds nothing between commands.
    const odrig_host &host = core.host;
    const int32_t count = host.read_at(host.ctx, kPageNames[storage][page], offset, core.chunk, kFileBufferSize);
    reply.text("{\"ok\":true,\"generation\":");
    reply.number(catalog.generation);
    reply.text(",\"text\":\"");
    // The room the end of the reply needs: `","next":4294967295}` and the line's end.
    const uint32_t tail = 22;
    const char *digits = "0123456789abcdef";
    uint32_t given = 0;
    while (count > 0 && given < static_cast<uint32_t>(count)) {
        const uint8_t byte = core.chunk[given];
        const bool plain = byte >= 0x20 && byte <= 0x7E && byte != '"' && byte != '\\';
        const uint32_t size = plain ? 1 : byte == '\n' || byte == '"' || byte == '\\' ? 2 : 6;
        if (!reply.fits(size + tail)) {
            break;
        }
        if (plain) {
            reply.bytes[reply.length++] = static_cast<char>(byte);
        } else if (size == 2) {
            reply.bytes[reply.length++] = '\\';
            reply.bytes[reply.length++] = byte == '\n' ? 'n' : static_cast<char>(byte);
        } else {
            reply.text("\\u00");
            reply.bytes[reply.length++] = digits[byte >> 4];
            reply.bytes[reply.length++] = digits[byte & 0x0F];
        }
        ++given;
    }
    if (given == 0) {
        reply.text("\",\"next\":null}\n");
        return reply.length;
    }
    reply.text("\",\"next\":");
    reply.number(static_cast<uint64_t>(offset) + given);
    reply.text("}\n");
    return reply.length;
}

}  // namespace odrig
