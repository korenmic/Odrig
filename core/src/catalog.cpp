#include "catalog.h"

#include "crc32.h"
#include "json_reader.h"
#include "order.h"
#include "player.h"
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

// Reads a word of exactly these characters at `*at`, and moves past it.
bool word(const char *line, uint32_t *at, const char *expected) {
    uint32_t place = *at;
    for (; *expected != '\0'; ++expected, ++place) {
        if (line[place] != *expected) {
            return false;
        }
    }
    *at = place;
    return true;
}

// Reads a decimal number of at most `most_digits` digits without a leading zero, and not
// above `most`, at `*at`.
bool decimal(const char *line, uint32_t *at, uint32_t most_digits, uint64_t most, uint64_t *value) {
    uint32_t place = *at;
    uint64_t found = 0;
    uint32_t digits = 0;
    while (line[place] >= '0' && line[place] <= '9') {
        if (digits == most_digits || (digits == 1 && found == 0)) {
            return false;
        }
        const uint64_t digit = static_cast<uint64_t>(line[place] - '0');
        if (found > (most - digit) / 10) {
            return false;
        }
        found = found * 10 + digit;
        ++digits;
        ++place;
    }
    if (digits == 0) {
        return false;
    }
    *value = found;
    *at = place;
    return true;
}

// Reads `count` lowercase hexadecimal digits at `*at`.
bool hexadecimal(const char *line, uint32_t *at, uint32_t count, uint32_t *value) {
    uint32_t found = 0;
    for (uint32_t digit = 0; digit < count; ++digit) {
        const char c = line[*at + digit];
        uint32_t nibble;
        if (c >= '0' && c <= '9') {
            nibble = static_cast<uint32_t>(c - '0');
        } else if (c >= 'a' && c <= 'f') {
            nibble = static_cast<uint32_t>(c - 'a' + 10);
        } else {
            return false;
        }
        found = found << 4 | nibble;
    }
    *at += count;
    *value = found;
    return true;
}

// Reads `count` decimal digits, leading zeros allowed, at `*at`.
bool fixed_decimal(const char *line, uint32_t *at, uint32_t count, uint32_t *value) {
    uint32_t found = 0;
    for (uint32_t digit = 0; digit < count; ++digit) {
        const char c = line[*at + digit];
        if (c < '0' || c > '9') {
            return false;
        }
        found = found * 10 + static_cast<uint32_t>(c - '0');
    }
    *at += count;
    *value = found;
    return true;
}

// Reads the marker from an open source: kCatalogOk with `marker` filled, kCatalogDamaged
// or kCatalogIncompatible.
uint8_t read_marker(FileSource &source, Marker &marker, uint32_t *whole_crc = nullptr) {
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
        line[at] == '\0' && (format != 1 || check != 1)) {
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
    const uint32_t body = crc_value(reader.crc);
    uint32_t sealed;
    at = 0;
    if (reader.next(source, line, sizeof line) != kLineGot || reader.over || reader.unended || reader.length != 12 || !word(line, &at, "crc ") ||
        !hexadecimal(line, &at, 8, &sealed) || sealed != body) {
        return kCatalogDamaged;
    }
    if (reader.next(source, line, sizeof line) != kLineEnd || reader.bytes != kMarkerSize || marker.generation == 0) {
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

// Reads an entry line of page `page`, without its line feed.
bool parse_entry(const char *line, uint32_t length, uint32_t page, EntryLine &entry) {
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
    return catalog_name_allowed(entry.name, entry.name_length) && catalog_page_of(entry.name, entry.name_length) == page;
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

// An action of a commit record on a file of a storage, given by its name there, with a zero
// after it: `upload.part` moved onto it, or it removed. False when the call failed. Kept
// apart from the reading of the record, whose frame has the line, as it may need room for
// the host's name of the file.
__attribute__((noinline)) bool act(Core &core, uint32_t storage, bool moves, const char *name, uint32_t length) {
    char given[6 + kCatalogNameMost + 1];
    const char *host_name = name;
    if (storage == kExternal) {
        uint32_t at = 0;
        for (const char *head = "drive/"; *head != '\0'; ++head) {
            given[at++] = *head;
        }
        for (uint32_t index = 0; index < length; ++index) {
            given[at++] = name[index];
        }
        given[at] = '\0';
        host_name = given;
    }
    if (moves) {
        return rename_there(core, kPartNames[storage], host_name);
    }
    return core.host.remove(core.host.ctx, host_name) != -1;
}

// One action of a commit record: whether it moves `upload.part` onto the name, else removes
// the file of the name, and the name with a zero after it.
struct Action {
    bool moves;
    char name[kCatalogNameMost + 1];
};

// Reads the commit record of a place whole, and gives its action at position `wanted`, when
// it has one, in `action`. Returns whether the record is whole; `mask` is its pages and
// `actions` the number of its actions. Nothing is done while it is read: the source reads one
// file at a time.
__attribute__((noinline)) bool read_record(Core &core, const Place &place, uint32_t *mask, uint32_t *actions, uint32_t wanted, Action *action) {
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
        bool moves = false;
        if (word(line, &at, "crc ")) {
            whole = hexadecimal(line, &at, 8, &sealed) && line[at] == '\0' && sealed == before && reader.next(source, line, sizeof line) == kLineEnd;
            ended = true;
            continue;
        } else if (word(line, &at, "move upload.part ")) {
            whole = catalog_name_allowed(line + at, reader.length - at);
            moves = true;
        } else if (word(line, &at, "remove ")) {
            whole = catalog_name_allowed(line + at, reader.length - at) || is_part(line + at, reader.length - at);
        } else {
            whole = false;
        }
        if (whole && *actions == wanted && action != nullptr) {
            action->moves = moves;
            uint32_t length = 0;
            for (; at + length < reader.length; ++length) {
                action->name[length] = line[at + length];
            }
            action->name[length] = '\0';
        }
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
    const uint8_t found = opened == kNone ? read_marker(source_of(core, place), marker, whole_crc) : kCatalogDamaged;
    source_of(core, place).close();
    return found;
}

// Finishes the change whose commit record is whole, on a place whose storage can be
// written: its actions, its pages, its marker, and the record removed, each step once the
// one before it is done. Returns whether no whole record is left: false when a call failed,
// and the record stays for the next attempt, which goes on where this one stopped.
__attribute__((noinline)) bool finish(Core &core, const Place &place) {
    uint32_t mask = 0;
    uint32_t actions = 0;
    if (!read_record(core, place, &mask, &actions, kNothing, nullptr)) {
        return true;
    }
    // Each action is read again on its own, and done once the record is closed.
    for (uint32_t index = 0; index < actions; ++index) {
        Action action;
        uint32_t count = 0;
        if (!read_record(core, place, &mask, &count, index, &action)) {
            return false;
        }
        uint32_t length = 0;
        while (action.name[length] != '\0') {
            ++length;
        }
        if (!act(core, place.storage, action.moves, action.name, length)) {
            return false;
        }
    }
    // The counts of the new marker, or of the marker when it was renamed already; a page
    // whose count is not known counts as one, so that it is not removed.
    const uint32_t storage = place.storage;
    Marker marker;
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
    while (*text != '\0') {
        core.chunk[(*length)++] = static_cast<uint8_t>(*text++);
    }
}

void put_bytes(Core &core, uint32_t *length, const char *text, uint32_t size) {
    for (uint32_t at = 0; at < size; ++at) {
        core.chunk[(*length)++] = static_cast<uint8_t>(text[at]);
    }
}

void put_number(Core &core, uint32_t *length, uint64_t value) {
    char digits[20];
    uint32_t count = 0;
    do {
        digits[count++] = static_cast<char>('0' + value % 10);
        value /= 10;
    } while (value != 0);
    while (count != 0) {
        core.chunk[(*length)++] = static_cast<uint8_t>(digits[--count]);
    }
}

void put_hex(Core &core, uint32_t *length, uint32_t value, uint32_t digits) {
    for (uint32_t digit = 0; digit < digits; ++digit) {
        core.chunk[(*length)++] = static_cast<uint8_t>("0123456789abcdef"[value >> (4 * (digits - 1 - digit)) & 0xFu]);
    }
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

// Puts a marker's text into the chunk buffer from 0 on, and returns its length, 409.
uint32_t marker_text(Core &core, const Marker &marker) {
    uint32_t length = 0;
    put(core, &length, "odrig-catalog 1 check 1 generation ");
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
    uint32_t crc = kCrcStart;
    for (uint32_t at = 0; at < length; ++at) {
        crc = crc_add(crc, core.chunk[at]);
    }
    put(core, &length, "crc ");
    put_hex(core, &length, crc_value(crc), 8);
    put(core, &length, "\n");
    return length;
}

// Puts the line of the added entry of a change into the chunk buffer from `*length` on.
void put_entry(Core &core, uint32_t *length, const CatalogChange &change) {
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
    put(core, length, "\n");
}

// The most bytes of a page gathered in the chunk buffer before they go to the host.
const uint32_t kPageFlush = 1200;

// Writes the new page of a change from the old one: every line but the dropped ones, the
// added entry in the place of the line of its name, or last. Gives its count and CRC-32.
__attribute__((noinline)) bool write_page(Core &core, uint32_t storage, uint32_t page, const Marker &old, const CatalogChange &change, uint16_t *count, uint32_t *crc) {
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
                put_bytes(core, &length, line, reader.length);
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

// The external storage's state and its log line, once its catalog cannot be read: nothing
// of the drive is an animation.
void drive_unusable(Core &core, uint8_t state, uint8_t detail) {
    core.checker->file.close();
    core.catalog_open = 0;
    core.drive_count = 0;
    core.drive_check_at = 0;
    tree_clear(core);
    core.catalog_phase = kLoadIdle;
    CatalogState &catalog = core.catalogs[kExternal];
    catalog.state = state;
    catalog.detail = state == kCatalogDamaged ? detail : 0;
    if (core.host.log != nullptr) {
        core.host.log(core.host.ctx, state == kCatalogIncompatible ? "catalog external incompatible" : "catalog external damaged");
    }
    player_drive_changed(core);
    order_drive_found(core);
}

// The file of the drive left out in this boot with this name and entry, or null.
const Remembered *remembered_entry(const Core &core, const char *name, uint32_t crc) {
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

// An entry of the drive's catalog becomes a place, published later; a name twice makes the
// page's lines unsound.
__attribute__((noinline)) void stage(Core &core, const EntryLine &entry) {
    if (core.drive_count >= kDriveMost) {
        return;
    }
    const uint32_t place = core.drive_count;
    char *name = const_cast<char *>(entry.name);
    name[entry.name_length] = '\0';
    if (core.host.drive_bind(core.host.ctx, core.drive_number, place, name) != 1) {
        core.catalog_bad_line = 1;
        return;
    }
    order_drive_named(core, place, name);
    for (uint32_t other = core.catalog_first_place; core.order_hash != nullptr && other < place; ++other) {
        char known[kCatalogNameMost + 1];
        if (core.order_hash[other] == core.order_hash[place] && core.host.drive_name(core.host.ctx, core.drive_number, other, known, sizeof known) == 1 &&
            same_text(known, name)) {
            core.catalog_bad_line = 1;
        }
    }
    DriveEntry &made = core.drive[place];
    made.bytes = entry.bytes;
    made.total_ms = drive_length(entry.total_ms);
    made.type = entry.type & 0x0F;
    made.id = free_drive_id(core);
    made.state = kDriveStaged;
    made.fault = kNone;
    if (entry.width != core.width || entry.height != core.height) {
        made.fault = kSizeMismatch;
    } else if (const Remembered *found = remembered_entry(core, name, entry.crc)) {
        made.fault = found->reason;
    }
    core.drive_count = place + 1;
}

// Reads the marker's line of the page the reading is at: false when the marker is not the
// one read before.
bool page_expected(Core &core) {
    const Place place = {kExternal, true};
    Marker marker;
    uint32_t crc = 0;
    if (read_marker_of(core, place, kMarkerNames[kExternal], marker, &crc) != kCatalogOk || crc != core.catalog_marker_crc) {
        return false;
    }
    core.catalog_expected_lines = marker.counts[core.catalog_page];
    core.catalog_expected_crc = marker.crcs[core.catalog_page];
    return true;
}

// One step of the pages: the next page's line of the marker, or one read of the page.
__attribute__((noinline)) void page_step(Core &core) {
    FileSource &source = core.checker->file;
    if (!core.catalog_open) {
        if (core.catalog_page >= kCatalogPages) {
            core.catalog_phase = kLoadOrder;
            core.drive_check_at = core.drive_count;
            order_drive_found(core);
            return;
        }
        if (!page_expected(core)) {
            // The marker changed while it was read: everything is read again.
            catalog_drive_plugged(core);
            core.drive_count = 0;
            tree_clear(core);
            return;
        }
        core.catalog_first_place = static_cast<uint16_t>(core.drive_count);
        core.catalog_lines = 0;
        core.catalog_bad_line = 0;
        core.catalog_page_crc = kCrcStart;
        core.order_reader.length = 0;
        core.order_reader.over = 0;
        if (core.catalog_expected_lines == 0) {
            ++core.catalog_page;
            return;
        }
        const Place place = {kExternal, true};
        if (open_for(core, place, kPageNames[kExternal][core.catalog_page]) != kNone) {
            drive_unusable(core, kCatalogDamaged, kDamagedPage);
            return;
        }
        core.catalog_open = 1;
        return;
    }
    OrderReader &line = core.order_reader;
    bool refilled = false;
    for (;;) {
        if (source.position >= source.length) {
            if (refilled) {
                return;
            }
            refilled = true;
        }
        const int got = source.get();
        if (got == -kEnd) {
            break;
        }
        if (got < 0) {
            drive_unusable(core, kCatalogDamaged, kDamagedPage);
            return;
        }
        core.catalog_page_crc = crc_add(core.catalog_page_crc, static_cast<uint8_t>(got));
        if (got != '\n') {
            if (line.length + 1 < kOrderLineRoom) {
                line.line[line.length++] = static_cast<char>(got);
            } else {
                line.over = 1;
            }
            continue;
        }
        ++core.catalog_lines;
        EntryLine entry;
        if (line.over || !parse_entry(line.line, line.length, core.catalog_page, entry)) {
            core.catalog_bad_line = 1;
        } else {
            stage(core, entry);
        }
        line.length = 0;
        line.over = 0;
    }
    source.close();
    core.catalog_open = 0;
    if (line.length != 0 || line.over || core.catalog_lines != core.catalog_expected_lines || crc_value(core.catalog_page_crc) != core.catalog_expected_crc) {
        drive_unusable(core, kCatalogDamaged, kDamagedPage);
        return;
    }
    if (core.catalog_bad_line) {
        drive_unusable(core, kCatalogDamaged, kDamagedLine);
        return;
    }
    ++core.catalog_page;
}

// Every place read from the catalog becomes an animation of the playlist at once, or is
// left out for its fault; the tree is built from them first, since the pages name a
// folder's files in any order.
void publish(Core &core) {
    tree_build(core);
    for (uint32_t place = 0; place < core.drive_count; ++place) {
        DriveEntry &entry = core.drive[place];
        if (entry.state != kDriveStaged) {
            continue;
        }
        if (entry.fault != kNone) {
            entry.state = kDriveLeftOut;
            drive_left_out(core, place, static_cast<Reason>(entry.fault));
        } else {
            entry.state = kDriveInPlaylist;
            player_drive_joined(core, place);
        }
    }
    core.drive_check_at = core.drive_count;
    core.catalog_phase = kLoadIdle;
    core.catalogs[kExternal].state = kCatalogOk;
    core.catalog_looked = core.latest;
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
    Marker marker;
    if (catalog_left(core, storage) && read_marker_of(core, place, kMarkerNames[storage], marker) == kCatalogOk) {
        // The change the start could not finish is finished: the catalog is kept from here on.
        catalog.state = kCatalogOk;
        catalog.detail = 0;
        catalog.generation = marker.generation;
        uint32_t entries = 0;
        for (uint32_t page = 0; page < kCatalogPages; ++page) {
            entries += marker.counts[page];
        }
        catalog.entries = static_cast<uint16_t>(entries);
    }
    return true;
}

bool catalog_commit(Core &core, uint32_t storage, const CatalogChange &change) {
    if (!catalog_settle(core, storage)) {
        return false;
    }
    CatalogState &catalog = core.catalogs[storage];
    if (catalog.state != kCatalogOk) {
        return true;
    }
    const Place place = {storage, true};
    Marker marker;
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
    marker.generation = marker.generation == 0xFFFFFFFFu ? 1 : marker.generation + 1;
    const uint32_t marker_length = marker_text(core, marker);
    uint32_t marker_crc = kCrcStart;
    for (uint32_t at = 0; at < marker_length; ++at) {
        marker_crc = crc_add(marker_crc, core.chunk[at]);
    }
    if (!write_whole(core, kNewMarkerNames[storage], marker_length)) {
        return false;
    }
    uint32_t length = 0;
    put(core, &length, "odrig-catalog-do 1 generation ");
    put_hex(core, &length, marker.generation, 8);
    put(core, &length, "\npages ");
    put_hex(core, &length, mask, 4);
    put(core, &length, "\n");
    if (change.moves_part) {
        put(core, &length, "move upload.part ");
        put(core, &length, change.added);
        put(core, &length, "\n");
    }
    if (change.removed_file != nullptr) {
        put(core, &length, "remove ");
        put(core, &length, change.removed_file);
        put(core, &length, "\n");
    }
    uint32_t crc = kCrcStart;
    for (uint32_t at = 0; at < length; ++at) {
        crc = crc_add(crc, core.chunk[at]);
    }
    put(core, &length, "crc ");
    put_hex(core, &length, crc_value(crc), 8);
    put(core, &length, "\n");
    if (!write_whole(core, kRecordNames[storage], length)) {
        return false;
    }
    // Committed: when a call fails now, what is left of it is finished before the next change
    // of the storage, or at the next start or plug-in.
    finish(core, place);
    catalog.generation = marker.generation;
    uint32_t entries = 0;
    for (uint32_t page = 0; page < kCatalogPages; ++page) {
        entries += marker.counts[page];
    }
    catalog.entries = static_cast<uint16_t>(entries);
    if (storage == kExternal) {
        // The drive's marker is now this one: the look does not take it for another.
        core.catalog_marker_crc = crc_value(marker_crc);
    }
    return true;
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
    if (left || (!storage_changes(core) && read_record(core, place, &mask, &actions, kNothing, nullptr))) {
        // A whole commit record that this host cannot finish, or that the start could not.
        catalog.state = kCatalogDamaged;
        catalog.detail = kDamagedInterrupted;
    }
    FileSource &source = core.file;
    const Reason opened = catalog.state == kCatalogNone ? source.open(core.host, kMarkerNames[kInternal]) : kNone;
    if (catalog.state == kCatalogNone && opened == kFileMissing) {
        return;
    }
    Marker marker;
    if (catalog.state == kCatalogNone) {
        catalog.state = opened == kNone ? read_marker(source, marker) : kCatalogDamaged;
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
    uint32_t entries = 0;
    for (uint32_t page = 0; page < kCatalogPages; ++page) {
        entries += marker.counts[page];
    }
    catalog.entries = static_cast<uint16_t>(entries);
}

void catalog_drive_plugged(Core &core) {
    CatalogState &catalog = core.catalogs[kExternal];
    catalog.generation = 0;
    catalog.entries = 0;
    catalog.detail = 0;
    core.catalog_open = 0;
    core.catalog_page = 0;
    const bool given_names = core.drive != nullptr && core.host.drive_bind != nullptr && core.drive_number != 0;
    core.catalog_phase = given_names ? kLoadRecord : kLoadIdle;
    catalog.state = core.drive_number == 0 ? kCatalogAbsent : given_names ? kCatalogLoading : kCatalogNone;
}

bool catalog_drive_loading(const Core &core) {
    return core.drive != nullptr && core.catalog_phase != kLoadIdle;
}

void catalog_drive_step(Core &core) {
    const Place place = {kExternal, true};
    CatalogState &catalog = core.catalogs[kExternal];
    if (core.catalog_phase == kLoadRecord) {
        uint32_t mask = 0;
        uint32_t actions = 0;
        if (read_record(core, place, &mask, &actions, kNothing, nullptr)) {
            // A record that cannot be finished keeps the upload's part it may move.
            if (core.host.drive_writable == nullptr || core.host.drive_writable(core.host.ctx, core.drive_number) != 1 || !finish(core, place)) {
                drive_unusable(core, kCatalogDamaged, kDamagedInterrupted);
                return;
            }
        }
        if (core.host.drive_writable != nullptr && core.host.drive_writable(core.host.ctx, core.drive_number) == 1 && is_there(core, kPartNames[kExternal])) {
            core.host.remove(core.host.ctx, kPartNames[kExternal]);
        }
        core.catalog_phase = kLoadMarker;
    } else if (core.catalog_phase == kLoadMarker) {
        Marker marker;
        const uint8_t found = read_marker_of(core, place, kMarkerNames[kExternal], marker, &core.catalog_marker_crc);
        if (found == kCatalogNone) {
            // A drive without a catalog is listed and checked as before.
            core.catalog_phase = kLoadIdle;
            catalog.state = kCatalogNone;
            drive_take_listed(core);
            return;
        }
        if (found != kCatalogOk) {
            drive_unusable(core, found, kDamagedMarker);
            return;
        }
        catalog.generation = marker.generation;
        uint32_t entries = 0;
        for (uint32_t page = 0; page < kCatalogPages; ++page) {
            entries += marker.counts[page];
        }
        catalog.entries = static_cast<uint16_t>(entries);
        core.catalog_page = 0;
        core.catalog_open = 0;
        core.catalog_phase = kLoadPages;
    } else if (core.catalog_phase == kLoadPages) {
        page_step(core);
    } else if (order_drive_due(core)) {
        order_drive_step(core);
    } else {
        publish(core);
    }
}

void catalog_drive_yields(Core &core) {
    if (core.catalog_phase == kLoadPages && core.catalog_open) {
        // The page is read again from its start; what was taken of it is dropped.
        core.catalog_open = 0;
        core.drive_count = core.catalog_first_place;
        tree_clear(core);
    }
}

void catalog_drive_look(Core &core) {
    if (core.drive == nullptr || core.drive_number == 0 || core.catalog_phase != kLoadIdle || core.catalogs[kExternal].state != kCatalogOk ||
        core.latest - core.catalog_looked < kLookEveryMs || core.upload.state != kUploadNone || !check_complete(core) || core.check_header_read) {
        return;
    }
    core.catalog_looked = core.latest;
    const Place place = {kExternal, true};
    Marker marker;
    uint32_t crc = 0;
    if (read_marker_of(core, place, kMarkerNames[kExternal], marker, &crc) == kCatalogOk && crc == core.catalog_marker_crc) {
        return;
    }
    // Another marker: the drive's animations go, and its catalog is read again.
    core.drive_count = 0;
    core.drive_check_at = 0;
    tree_clear(core);
    player_drive_changed(core);
    order_drive_found(core);
    catalog_drive_plugged(core);
}

void catalog_drive_left_out(Core &core, uint32_t place, Reason reason) {
    if (core.catalogs[kExternal].state != kCatalogOk || core.remembered == nullptr || !is_file_fault(reason) || core.upload.state != kUploadNone ||
        !check_complete(core) || core.check_header_read) {
        return;
    }
    // The entry's CRC-32, from the line of its name on its page.
    char name[kCatalogNameMost + 1];
    if (core.host.drive_name(core.host.ctx, core.drive_number, place, name, sizeof name) != 1) {
        return;
    }
    uint32_t length = 0;
    while (name[length] != '\0') {
        ++length;
    }
    const Place where = {kExternal, true};
    if (open_for(core, where, kPageNames[kExternal][catalog_page_of(name, length)]) != kNone) {
        return;
    }
    LineReader reader;
    OrderReader &line = core.order_reader;
    while (reader.next(core.checker->file, line.line, kOrderLineRoom) == kLineGot) {
        EntryLine entry;
        if (!reader.over && parse_entry(line.line, reader.length, catalog_page_of(name, length), entry) && entry.name_length == length &&
            same_text(entry.name, name)) {
            Remembered &one = core.remembered[core.remembered_next];
            core.remembered_next = (core.remembered_next + 1) % kRememberedMost;
            uint32_t at = 0;
            for (; name[at] != '\0' && at + 1 < kFaultNameSize; ++at) {
                one.name[at] = name[at];
            }
            one.name[at] = '\0';
            one.reason = static_cast<uint8_t>(reason);
            one.first_read = kRememberedWhole;
            one.crc = entry.crc;
            break;
        }
    }
    core.checker->file.close();
    line.length = 0;
    line.over = 0;
}

bool catalog_drive_writable(const Core &core) {
    return core.drive != nullptr && core.drive_number != 0 && core.catalogs[kExternal].state == kCatalogOk && core.catalog_phase == kLoadIdle &&
           core.host.drive_writable != nullptr && core.host.drive_writable(core.host.ctx, core.drive_number) == 1;
}

namespace {

// Whether the drive's file at a place has this name.
bool place_has_name(const Core &core, uint32_t place, const char *name) {
    char given[kCatalogNameMost + 1];
    return core.host.drive_name(core.host.ctx, core.drive_number, place, given, sizeof given) == 1 && same_text(given, name);
}

// Whether a name is the one given as the context.
bool is_named(const Core &, const char *name, uint32_t length, const void *context) {
    const char *given = static_cast<const char *>(context);
    uint32_t at = 0;
    for (; at < length && given[at] == name[at]; ++at) {
    }
    return at == length && given[at] == '\0';
}

}  // namespace

uint32_t catalog_drive_place_for(const Core &core, const char *name) {
    uint32_t gone = kDriveMost;
    for (uint32_t place = 0; place < core.drive_count; ++place) {
        if (core.drive[place].state == kDriveGone) {
            gone = gone == kDriveMost ? place : gone;
        } else if (place_has_name(core, place, name)) {
            return place;
        }
    }
    if (gone != kDriveMost) {
        return gone;
    }
    return core.drive_count < kDriveMost ? core.drive_count : kDriveMost;
}

bool catalog_install_external(Core &core, uint16_t *id) {
    const Upload &upload = core.upload;
    uint32_t place = catalog_drive_place_for(core, upload.name);
    if (place == kDriveMost) {
        return false;
    }
    const bool replaces = place < core.drive_count && core.drive[place].state != kDriveGone;
    if (replaces) {
        player_releases_file(core, kDriveBase + place);
    }
    CatalogChange change;
    change.added = upload.name;
    change.added_bytes = upload.size;
    change.added_crc = crc_value(upload.crc);
    change.added_total_ms = upload.total_ms;
    change.added_type = core.check_content.type;
    change.moves_part = true;
    if (!catalog_commit(core, kExternal, change)) {
        return false;
    }
    DriveEntry &entry = core.drive[place];
    if (!replaces) {
        if (place == core.drive_count) {
            core.drive_count = place + 1;
        }
        entry.id = 0;
        core.host.drive_bind(core.host.ctx, core.drive_number, place, upload.name);
        order_drive_named(core, place, upload.name);
        entry.id = free_drive_id(core);
        // The file goes into the drive's folder itself: the root's.
        if (core.drive_folder != nullptr) {
            core.drive_folder[place] = 0;
        }
    }
    entry.bytes = upload.size;
    entry.total_ms = drive_length(upload.total_ms);
    entry.type = core.check_content.type & 0x0F;
    entry.fault = kNone;
    entry.state = kDriveInPlaylist;
    core.drive_check_at = core.drive_count;
    if (!replaces) {
        // An entry of the saved order may name the new file: it stands there at once.
        order_reload(core);
        player_drive_joined(core, place);
    } else {
        // What plays it plays the new file from its start.
        player_file_replaced(core, kDriveBase + place);
    }
    *id = entry.id;
    return true;
}

bool catalog_remove_external(Core &core, uint32_t place) {
    char name[kCatalogNameMost + 1];
    if (core.host.drive_name(core.host.ctx, core.drive_number, place, name, sizeof name) != 1) {
        return false;
    }
    uint32_t length = 0;
    while (name[length] != '\0') {
        ++length;
    }
    player_releases_file(core, kDriveBase + place);
    CatalogChange change;
    change.drops = is_named;
    change.context = name;
    change.drop_pages = 1u << catalog_page_of(name, length);
    change.removed_file = name;
    if (!catalog_commit(core, kExternal, change)) {
        return false;
    }
    DriveEntry &entry = core.drive[place];
    entry.state = kDriveGone;
    entry.id = 0;
    tree_place_gone(core, place);
    player_drive_changed(core);
    return true;
}

namespace {

// Where each page's count and CRC-32 wait while a rebuild runs: six bytes a page.
const uint32_t kRebuildPages = 1400;

void keep_page(Core &core, uint32_t page, uint16_t count, uint32_t crc) {
    uint8_t *at = core.chunk + kRebuildPages + 6 * page;
    at[0] = static_cast<uint8_t>(count);
    at[1] = static_cast<uint8_t>(count >> 8);
    for (uint32_t byte = 0; byte < 4; ++byte) {
        at[2 + byte] = static_cast<uint8_t>(crc >> (8 * byte));
    }
}

void kept_page(const Core &core, uint32_t page, uint16_t *count, uint32_t *crc) {
    const uint8_t *at = core.chunk + kRebuildPages + 6 * page;
    *count = static_cast<uint16_t>(at[0] | at[1] << 8);
    *crc = 0;
    for (uint32_t byte = 0; byte < 4; ++byte) {
        *crc |= static_cast<uint32_t>(at[2 + byte]) << (8 * byte);
    }
}

// The check after the start takes up the show's files that are neither checked nor faulted.
void check_takes_up(Core &core) {
    core.check_at = 0;
    while (core.check_at < core.file_count && (core.files[core.check_at].fault != kNone || core.files[core.check_at].checked)) {
        ++core.check_at;
    }
    core.check_done = core.check_at >= core.file_count ? 1 : 0;
}

// Ends a rebuild without its commit: the page being written is given up and removed; the
// check after the start, or a drive's own check, takes up the files the rebuild did not read.
void rebuild_ends(Core &core) {
    const uint32_t storage = core.rebuild - 1;
    if (core.checker != nullptr) {
        core.checker->file.close();
    }
    core.check_header_read = 0;
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
    if (storage == kInternal) {
        check_takes_up(core);
    } else {
        core.drive_check_at = 0;
    }
}

// Whether the file or place `at` is one the rebuild reads on its page.
bool rebuild_takes(const Core &core, uint32_t storage, uint32_t at, uint32_t page) {
    if (storage == kInternal) {
        const FileInfo &info = core.files[at];
        uint32_t length = 0;
        while (info.name[length] != '\0') {
            ++length;
        }
        return info.fault == kNone && catalog_name_allowed(info.name, length) && catalog_page_of(info.name, length) == page;
    }
    return core.drive[at].state == kDriveToCheck && core.order_hash != nullptr && (core.order_hash[at] & 15u) == page;
}

// Writes one line of the page being made: its new file is opened at its first line.
bool rebuild_line(Core &core, uint32_t storage, const char *name, uint32_t crc, uint32_t bytes, uint64_t total_ms, uint8_t type) {
    const odrig_host &host = core.host;
    if (!core.rebuild_open) {
        if (host.write_open(host.ctx, kNewPageNames[storage][core.rebuild_page]) != 1) {
            return false;
        }
        core.rebuild_open = 1;
    }
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
    for (uint32_t at = 0; at < length; ++at) {
        core.rebuild_crc = crc_add(core.rebuild_crc, core.chunk[at]);
    }
    ++core.rebuild_lines;
    return host.write(host.ctx, core.chunk, length) == 1;
}

// The page is done: its file closed, or a stale new page removed when it has no line.
bool rebuild_close_page(Core &core, uint32_t storage) {
    const odrig_host &host = core.host;
    if (core.rebuild_open) {
        core.rebuild_open = 0;
        if (host.write_close(host.ctx) != 1) {
            host.remove(host.ctx, kNewPageNames[storage][core.rebuild_page]);
            return false;
        }
        keep_page(core, core.rebuild_page, core.rebuild_lines, crc_value(core.rebuild_crc));
    } else {
        keep_page(core, core.rebuild_page, 0, 0);
        if (host.remove(host.ctx, kNewPageNames[storage][core.rebuild_page]) == -1) {
            return false;
        }
    }
    ++core.rebuild_page;
    core.rebuild_at = 0;
    core.rebuild_lines = 0;
    core.rebuild_crc = kCrcStart;
    return true;
}

// The last page is done: the marker and the commit record for every page, and the finishing.
bool rebuild_commit(Core &core, uint32_t storage) {
    const Place place = {storage, true};
    Marker marker;
    const uint8_t old = read_marker_of(core, place, kMarkerNames[storage], marker);
    const uint32_t generation = old == kCatalogOk ? (marker.generation == 0xFFFFFFFFu ? 1 : marker.generation + 1) : 1;
    // The page summaries are taken from the chunk before the marker's text overwrites it.
    uint32_t entries = 0;
    for (uint32_t page = 0; page < kCatalogPages; ++page) {
        kept_page(core, page, &marker.counts[page], &marker.crcs[page]);
        entries += marker.counts[page];
    }
    marker.generation = generation;
    const uint32_t marker_length = marker_text(core, marker);
    uint32_t marker_crc = kCrcStart;
    for (uint32_t at = 0; at < marker_length; ++at) {
        marker_crc = crc_add(marker_crc, core.chunk[at]);
    }
    if (!write_whole(core, kNewMarkerNames[storage], marker_length)) {
        return false;
    }
    uint32_t length = 0;
    put(core, &length, "odrig-catalog-do 1 generation ");
    put_hex(core, &length, generation, 8);
    put(core, &length, "\npages ffff\n");
    uint32_t crc = kCrcStart;
    for (uint32_t at = 0; at < length; ++at) {
        crc = crc_add(crc, core.chunk[at]);
    }
    put(core, &length, "crc ");
    put_hex(core, &length, crc_value(crc), 8);
    put(core, &length, "\n");
    if (!write_whole(core, kRecordNames[storage], length)) {
        return false;
    }
    finish(core, place);
    CatalogState &catalog = core.catalogs[storage];
    catalog.state = kCatalogOk;
    catalog.detail = 0;
    catalog.generation = generation;
    catalog.entries = static_cast<uint16_t>(entries);
    if (storage == kInternal) {
        // A file whose name the catalog cannot hold is checked as without a catalog.
        check_takes_up(core);
    }
    if (storage == kExternal) {
        // The drive's marker is now this one: the look does not take it for another.
        core.catalog_marker_crc = crc_value(marker_crc);
        core.catalog_looked = core.latest;
        core.drive_check_at = core.drive_count;
        order_reload(core);
    }
    return true;
}

// A storage call of the rebuild failed: it ends, and the catalog stays as it was.
void rebuild_failed(Core &core) {
    if (core.host.log != nullptr) {
        core.host.log(core.host.ctx, "catalog rebuild failed: storage-error");
    }
    rebuild_ends(core);
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
        (core.drive == nullptr || core.drive_number == 0 || core.host.drive_writable == nullptr || core.host.drive_list == nullptr ||
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
            uint32_t length = 0;
            while (info.name[length] != '\0') {
                ++length;
            }
            total += info.fault == kNone && catalog_name_allowed(info.name, length) ? 1 : 0;
        }
    } else {
        // The drive's animations go; its folder is listed once, and each file joins again
        // as the rebuild reads it.
        core.drive_count = 0;
        player_drive_changed(core);
        drive_take_listed(core);
        core.drive_check_at = core.drive_count;
        core.catalogs[kExternal].state = kCatalogNone;
        total = core.drive_count;
    }
    core.rebuild = static_cast<uint8_t>(1 + storage);
    core.rebuild_page = 0;
    core.rebuild_open = 0;
    core.rebuild_at = 0;
    core.rebuild_read = 0;
    core.rebuild_total = static_cast<uint16_t>(total);
    core.rebuild_lines = 0;
    core.rebuild_crc = kCrcStart;
    return succeed(reply);
}

uint32_t catalog_cancel(Core &core, Reply &reply) {
    if (core.rebuild != 0) {
        rebuild_ends(core);
    }
    return succeed(reply);
}

void catalog_drive_went(Core &core) {
    if (core.rebuild == 1 + kExternal) {
        // The drive is gone: its page is given up as it is, and is never read without a
        // record.
        if (core.rebuild_open) {
            core.host.write_close(core.host.ctx);
            core.rebuild_open = 0;
        }
        rebuild_ends(core);
    }
}

void catalog_rebuild_step(Core &core) {
    const uint32_t storage = core.rebuild - 1;
    if (core.rebuild_page >= kCatalogPages) {
        if (!rebuild_commit(core, storage)) {
            rebuild_failed(core);
            return;
        }
        core.rebuild = 0;
        return;
    }
    const uint32_t count = storage == kInternal ? core.file_count : core.drive_count;
    while (core.rebuild_at < count && !rebuild_takes(core, storage, core.rebuild_at, core.rebuild_page)) {
        ++core.rebuild_at;
    }
    if (core.rebuild_at >= count) {
        if (!rebuild_close_page(core, storage)) {
            rebuild_failed(core);
        }
        return;
    }
    const uint32_t at = core.rebuild_at;
    const char *name = core.files[at < core.file_count ? at : 0].name;
    if (storage == kExternal) {
        drive_file_name(at, core.drive_check_name);
        name = core.drive_check_name;
    }
    Reason reason = kNone;
    uint32_t record = 0;
    const StepOutcome outcome = check_file_step(core, name, &reason, &record);
    if (outcome == kStepGoingOn) {
        return;
    }
    ++core.rebuild_read;
    ++core.rebuild_at;
    if (outcome == kStepFault) {
        if (storage == kInternal) {
            quarantine_file(core, at, reason, kWorkStart, record, core.checker->decoder.body_read);
        } else {
            core.drive[at].state = kDriveLeftOut;
            drive_left_out(core, at, reason);
        }
        return;
    }
    const uint32_t bytes = core.checker->file.taken;
    const uint32_t crc = crc_value(core.checker->file.crc);
    const uint64_t total = core.check_total_ms;
    const uint8_t type = core.check_content.type;
    bool written = true;
    if (storage == kInternal) {
        FileInfo &info = core.files[at];
        info.bytes = bytes;
        info.total_ms = total;
        info.type = type;
        info.checked = kCheckedFromCatalog;
        written = rebuild_line(core, storage, info.name, crc, bytes, total, type);
    } else {
        DriveEntry &entry = core.drive[at];
        entry.bytes = bytes;
        entry.total_ms = drive_length(total);
        entry.type = type & 0x0F;
        entry.state = kDriveInPlaylist;
        player_drive_joined(core, at);
        char given[kCatalogNameMost + 1];
        uint32_t length = 0;
        if (core.host.drive_name(core.host.ctx, core.drive_number, at, given, sizeof given) == 1) {
            while (given[length] != '\0') {
                ++length;
            }
            // A file whose name a catalog cannot hold plays now, and is not in the catalog.
            if (catalog_name_allowed(given, length)) {
                written = rebuild_line(core, storage, given, crc, bytes, total, type);
            }
        }
    }
    if (!written) {
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

}  // namespace odrig
