#include "catalog.h"

#include "crc32.h"
#include "json_reader.h"
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
uint8_t read_marker(FileSource &source, Marker &marker) {
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
    return kCatalogOk;
}

// One entry of a page.
struct EntryLine {
    uint32_t crc;
    uint32_t bytes;
    uint16_t width;
    uint16_t height;
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
    if (!word(line, &at, "frames ") && !word(line, &at, "text ") && !word(line, &at, "widget ")) {
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

// Renames a file that is there onto another, by their host's names.
void rename_there(Core &core, const char *from, const char *to) {
    if (is_there(core, from)) {
        core.host.rename(core.host.ctx, from, to);
    }
}

// An action of a commit record on a file of a storage, given by its name there, with a zero
// after it: `upload.part` moved onto it, or it removed. Kept apart from the reading of the
// record, whose frame has the line, as it may need room for the host's name of the file.
__attribute__((noinline)) void act(Core &core, uint32_t storage, bool moves, const char *name, uint32_t length) {
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
        rename_there(core, kPartNames[storage], host_name);
    } else {
        core.host.remove(core.host.ctx, host_name);
    }
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
uint8_t read_marker_of(Core &core, const Place &place, const char *name, Marker &marker) {
    const Reason opened = open_for(core, place, name);
    if (opened == kFileMissing) {
        return kCatalogNone;
    }
    const uint8_t found = opened == kNone ? read_marker(source_of(core, place), marker) : kCatalogDamaged;
    source_of(core, place).close();
    return found;
}

// Finishes the change whose commit record is whole, on a place whose storage can be
// written. True when there was one.
bool finish(Core &core, const Place &place) {
    uint32_t mask = 0;
    uint32_t actions = 0;
    if (!read_record(core, place, &mask, &actions, kNothing, nullptr)) {
        return false;
    }
    // Each action is read again on its own, and done once the record is closed.
    for (uint32_t index = 0; index < actions; ++index) {
        Action action;
        uint32_t count = 0;
        if (read_record(core, place, &mask, &count, index, &action)) {
            uint32_t length = 0;
            while (action.name[length] != '\0') {
                ++length;
            }
            act(core, place.storage, action.moves, action.name, length);
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
            core.host.rename(core.host.ctx, kNewPageNames[storage][page], kPageNames[storage][page]);
        } else if (found == kCatalogOk && marker.counts[page] == 0) {
            core.host.remove(core.host.ctx, kPageNames[storage][page]);
        }
    }
    rename_there(core, kNewMarkerNames[storage], kMarkerNames[storage]);
    core.host.remove(core.host.ctx, kRecordNames[storage]);
    return true;
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

// Writes the chunk buffer's first `length` bytes as a new file, by its host's name.
bool write_whole(Core &core, const char *name, uint32_t length) {
    const odrig_host &host = core.host;
    return host.write_open(host.ctx, name) == 1 && host.write(host.ctx, core.chunk, length) == 1 && host.write_close(host.ctx) == 1;
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
    put(core, length, " frames ");
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
                core.checker->file.close();
                return false;
            }
            got = read == kLineGot;
        }
        if (got) {
            EntryLine entry;
            if (!parse_entry(line, reader.length, page, entry)) {
                core.checker->file.close();
                return false;
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
            if ((!opened && host.write_open(host.ctx, fresh) != 1) || host.write(host.ctx, core.chunk, length) != 1) {
                core.checker->file.close();
                return false;
            }
            opened = true;
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
    if ((!opened && host.write_open(host.ctx, fresh) != 1) || (length != 0 && host.write(host.ctx, core.chunk, length) != 1) || host.write_close(host.ctx) != 1) {
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

}  // namespace

bool catalog_name_allowed(const char *name, uint32_t length) {
    if (length < 6 || length > kCatalogNameMost || name[0] == '.' || name[0] == ' ') {
        return false;
    }
    bool digits_only = true;
    for (uint32_t at = 0; at < length; ++at) {
        const char c = name[at];
        if (c < 0x20 || c > 0x7E || c == '/' || c == '\\' || c == ':' || c == '*' || c == '?' || c == '"' || c == '<' || c == '>' || c == '|') {
            return false;
        }
        digits_only = digits_only && c >= '0' && c <= '9';
    }
    const char *end = name + length - 5;
    const char tail[] = ".odrg";
    for (uint32_t at = 0; at < 5; ++at) {
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
    if (!storage_changes(core) || core.host.read_at == nullptr) {
        return;
    }
    const Place place = {kInternal, false};
    finish(core, place);
}

bool catalog_commit(Core &core, uint32_t storage, const CatalogChange &change) {
    CatalogState &catalog = core.catalogs[storage];
    if (catalog.state != kCatalogOk) {
        return true;
    }
    drive_check_yields(core);
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
    if (!write_whole(core, kNewMarkerNames[storage], marker_text(core, marker))) {
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
    // Committed: what is left of it is finished at the next start when a call fails now.
    finish(core, place);
    catalog.generation = marker.generation;
    uint32_t entries = 0;
    for (uint32_t page = 0; page < kCatalogPages; ++page) {
        entries += marker.counts[page];
    }
    catalog.entries = static_cast<uint16_t>(entries);
    return true;
}

void catalog_read_internal(Core &core) {
    CatalogState &catalog = core.catalogs[kInternal];
    catalog.state = kCatalogNone;
    catalog.detail = 0;
    catalog.generation = 0;
    catalog.entries = 0;
    uint32_t mask = 0;
    const Place place = {kInternal, false};
    uint32_t actions = 0;
    if (!storage_changes(core) && read_record(core, place, &mask, &actions, kNothing, nullptr)) {
        // A whole commit record that this host cannot finish.
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
    reply.text("},\"rebuild\":null}\n");
    return reply.length;
}

}  // namespace odrig
