#include "show.h"

#include "arena.h"
#include "json_reader.h"

namespace odrig {

namespace {

const uint32_t kNameSize = 12;
const uint32_t kLargestId = 65535;
// How long an animation without a number of loops plays at least, in a show that does not say.
const uint32_t kMinSeconds = 30;
const uint32_t kMostToCount = 0xFFFFFFFFu;

// What one reading of the file has seen so far.
struct Seen {
    uint32_t items;
    uint32_t entries;
    uint32_t animations;
    uint32_t brightness;

    // An entry of a cycle that is not from 1 to 65,535 is no id of an item. The entry
    // table holds 0 for it, and this is the first such entry of the file.
    bool odd_entry;
    bool odd_entry_negative;
    uint32_t odd_entry_size;

    bool has_start;
    bool start_negative;
    uint32_t start_size;

    bool has_min_seconds;
    uint32_t min_seconds;
};

void count_one(uint32_t *counter) {
    if (*counter < kMostToCount) {
        ++*counter;
    }
}

// Writes an id as text: a minus sign when it is below zero, and its digits.
void write_id(char *text, bool negative, uint32_t size) {
    char digits[10];
    uint32_t count = 0;
    do {
        digits[count++] = static_cast<char>('0' + size % 10);
        size /= 10;
    } while (size != 0);
    if (negative) {
        *text++ = '-';
    }
    while (count != 0) {
        *text++ = digits[--count];
    }
    *text = '\0';
}

// The entry of the file table with this name; a new one when no item named it before.
uint32_t file_entry(Core &core, const char *name) {
    for (uint32_t index = 0; index < core.file_count; ++index) {
        if (same_text(core.files[index].name, name)) {
            return index;
        }
    }
    FileInfo &file = core.files[core.file_count];
    uint32_t length = 0;
    for (; name[length] != '\0'; ++length) {
        file.name[length] = name[length];
    }
    file.name[length] = '\0';
    return core.file_count++;
}

// Reads one entry of `items`. The second reading of the file also fills the tables, and
// `limits` holds what the first reading counted.
bool read_item(Core &core, JsonReader &json, const Seen *limits, Seen &seen) {
    const bool fill = limits != nullptr;
    char name[kNameSize];
    char file[33];
    uint32_t members = 0;
    uint32_t id = 0;
    uint32_t seconds = 0;
    uint32_t repeat = 0;
    uint32_t max_seconds = 0;
    uint32_t own_entries = 0;

    if (!json.object_begin()) {
        return false;
    }
    while (json.object_next(name, sizeof name)) {
        uint32_t member;
        if (same_text(name, "id")) {
            member = 1;
        } else if (same_text(name, "file")) {
            member = 2;
        } else if (same_text(name, "cycle")) {
            member = 4;
        } else if (same_text(name, "seconds")) {
            member = 8;
        } else if (same_text(name, "repeat")) {
            member = 16;
        } else if (same_text(name, "max_seconds")) {
            member = 32;
        } else {
            return false;
        }
        if ((members & member) != 0) {
            return false;
        }
        members |= member;

        if (member == 1) {
            if (!json.integer(&id) || id < 1 || id > kLargestId) {
                return false;
            }
        } else if (member == 16) {
            if (!json.integer(&repeat) || repeat < 1 || repeat > 65535) {
                return false;
            }
        } else if (member == 32) {
            if (!json.integer(&max_seconds) || max_seconds < 1 || max_seconds > 65535) {
                return false;
            }
        } else if (member == 2) {
            if (!json.string(file, sizeof file) || !is_file_name(file)) {
                return false;
            }
        } else if (member == 8) {
            if (!json.integer(&seconds) || seconds < 1 || seconds > 65535) {
                return false;
            }
        } else {
            if (!json.array_begin()) {
                return false;
            }
            while (json.array_next()) {
                bool negative;
                uint32_t size;
                if (!json.any_integer(&negative, &size)) {
                    return false;
                }
                const bool is_id = !negative && size >= 1 && size <= kLargestId;
                if (fill) {
                    if (seen.entries + own_entries >= limits->entries) {
                        return false;
                    }
                    core.entries[seen.entries + own_entries] = is_id ? static_cast<uint16_t>(size) : 0;
                    if (!is_id && !seen.odd_entry) {
                        seen.odd_entry = true;
                        seen.odd_entry_negative = negative;
                        seen.odd_entry_size = size;
                    }
                }
                count_one(&own_entries);
            }
            if (json.failed || own_entries == 0) {
                return false;
            }
        }
    }
    if (json.failed) {
        return false;
    }
    // An item with `file` is an animation: it has `id`, and may have `repeat` and
    // `max_seconds`, and no other member. Any other item is a cycle and has exactly `id`,
    // `cycle` and `seconds`.
    const bool is_animation = (members & 2) != 0;
    if (is_animation ? (members & ~48u) != 3u : members != 13u) {
        return false;
    }

    if (fill) {
        if (seen.items >= limits->items || (is_animation && seen.animations >= limits->animations)) {
            return false;
        }
        ItemInfo &item = core.items[seen.items];
        item.id = static_cast<uint16_t>(id);
        item.seconds = static_cast<uint16_t>(is_animation ? max_seconds : seconds);
        item.is_cycle = is_animation ? 0 : 1;
        item.first = is_animation ? file_entry(core, file) : seen.entries;
        item.count = is_animation ? repeat : own_entries;
    }
    count_one(&seen.items);
    if (is_animation) {
        count_one(&seen.animations);
    }
    seen.entries = own_entries > kMostToCount - seen.entries ? kMostToCount : seen.entries + own_entries;
    return true;
}

// Reads the whole file once. False when it breaks its format.
bool read_file(Core &core, JsonReader &json, const Seen *limits, Seen &seen) {
    char name[kNameSize];
    uint32_t members = 0;
    if (!json.object_begin()) {
        return false;
    }
    while (json.object_next(name, sizeof name)) {
        uint32_t member;
        if (same_text(name, "version")) {
            member = 1;
        } else if (same_text(name, "brightness")) {
            member = 2;
        } else if (same_text(name, "items")) {
            member = 4;
        } else if (same_text(name, "start")) {
            member = 8;
        } else if (same_text(name, "min_seconds")) {
            member = 16;
        } else {
            return false;
        }
        if ((members & member) != 0) {
            return false;
        }
        members |= member;

        if (member == 16) {
            if (!json.integer(&seen.min_seconds) || seen.min_seconds < 1 || seen.min_seconds > 65535) {
                return false;
            }
            seen.has_min_seconds = true;
        } else if (member == 1) {
            uint32_t version;
            if (!json.integer(&version) || version != 1) {
                return false;
            }
        } else if (member == 2) {
            if (!json.integer(&seen.brightness) || seen.brightness > 255) {
                return false;
            }
        } else if (member == 8) {
            if (!json.any_integer(&seen.start_negative, &seen.start_size)) {
                return false;
            }
            seen.has_start = true;
        } else {
            if (!json.array_begin()) {
                return false;
            }
            while (json.array_next()) {
                if (!read_item(core, json, limits, seen)) {
                    return false;
                }
            }
            if (json.failed) {
                return false;
            }
        }
    }
    return !json.failed && (members & 7) == 7 && json.end();
}

// Opens the file and reads it once. With `limits` it is the second reading.
Reason read_once(Core &core, const Seen *limits, Seen &seen) {
    seen.items = 0;
    seen.entries = 0;
    seen.animations = 0;
    seen.brightness = 0;
    seen.odd_entry = false;
    seen.odd_entry_negative = false;
    seen.odd_entry_size = 0;
    seen.has_start = false;
    seen.start_negative = false;
    seen.start_size = 0;
    seen.has_min_seconds = false;
    seen.min_seconds = 0;
    Reason opened = core.file.open(core.host, "show.json");
    if (opened == kFileMissing) {
        return kShowMissing;
    }
    if (opened != kNone) {
        return kReadError;
    }
    JsonReader json;
    json.start(&core.file);
    bool sound = read_file(core, json, limits, seen);
    core.file.close();
    if (json.read_failed) {
        return kReadError;
    }
    return sound ? kNone : kShowMalformed;
}

// The position of the item with this id, or the number of items when no item has it.
uint32_t find_item(const Core &core, uint32_t id) {
    uint32_t index = 0;
    while (index < core.item_count && core.items[index].id != id) {
        ++index;
    }
    return index;
}

// The three checks of the ids, each over the items in the order of the file.
Reason check_ids(Core &core, const Seen &seen, char *id_text) {
    for (uint32_t later = 1; later < core.item_count; ++later) {
        for (uint32_t earlier = 0; earlier < later; ++earlier) {
            if (core.items[earlier].id == core.items[later].id) {
                write_id(id_text, false, core.items[later].id);
                return kDuplicateId;
            }
        }
    }

    for (uint32_t index = 0; index < core.item_count; ++index) {
        const ItemInfo &item = core.items[index];
        for (uint32_t entry = 0; item.is_cycle && entry < item.count; ++entry) {
            const uint32_t named = core.entries[item.first + entry];
            if (named == 0) {
                write_id(id_text, seen.odd_entry_negative, seen.odd_entry_size);
                return kUndefinedId;
            }
            if (find_item(core, named) == core.item_count) {
                write_id(id_text, false, named);
                return kUndefinedId;
            }
        }
    }
    uint32_t start_item = 0;
    if (seen.has_start) {
        const bool is_id = !seen.start_negative && seen.start_size >= 1 && seen.start_size <= kLargestId;
        start_item = is_id ? find_item(core, seen.start_size) : core.item_count;
        if (start_item == core.item_count) {
            write_id(id_text, seen.start_negative, seen.start_size);
            return kUndefinedId;
        }
    }

    for (uint32_t index = 0; index < core.item_count; ++index) {
        const ItemInfo &item = core.items[index];
        for (uint32_t entry = 0; item.is_cycle && entry < item.count; ++entry) {
            if (core.items[find_item(core, core.entries[item.first + entry])].is_cycle) {
                write_id(id_text, false, item.id);
                return kNestedCycle;
            }
        }
    }

    // Every entry names an animation item. From here on it holds that item's position.
    for (uint32_t entry = 0; entry < core.entry_count; ++entry) {
        core.entries[entry] = static_cast<uint16_t>(find_item(core, core.entries[entry]));
    }
    core.has_start = seen.has_start ? 1 : 0;
    core.start_item = start_item;
    core.has_min_seconds = seen.has_min_seconds ? 1 : 0;
    core.min_seconds = static_cast<uint16_t>(seen.has_min_seconds ? seen.min_seconds : kMinSeconds);
    return kNone;
}

}  // namespace

bool is_file_name(const char *name) {
    uint32_t length = 0;
    for (; name[length] != '\0'; ++length) {
        char c = name[length];
        bool allowed = (c >= 'a' && c <= 'z') || (c >= '0' && c <= '9') || c == '-' || c == '_' || c == '.';
        if (!allowed) {
            return false;
        }
    }
    return length >= 5 && same_text(name + length - 5, ".odrg");
}

Reason read_show(Core &core, char *id_text) {
    id_text[0] = '\0';

    // The first reading checks the format of the file and counts what the tables hold.
    Seen first;
    Reason reason = read_once(core, nullptr, first);
    if (reason != kNone) {
        return reason;
    }
    // The item and the file table get room for more items than the show has now. A show
    // with more items than there are ids is refused below, and until then has its room.
    uint32_t capacity = first.items < kMostItems - kSpareItems ? first.items + kSpareItems : kMostItems;
    if (capacity < kFewestItems) {
        capacity = kFewestItems;
    }
    if (capacity < first.items) {
        capacity = first.items;
    }
    if (capacity > kMostToCount / sizeof(FileInfo) || first.entries > kMostToCount / 2) {
        return kOutOfMemory;
    }
    core.items = static_cast<ItemInfo *>(arena_take(core, capacity * static_cast<uint32_t>(sizeof(ItemInfo))));
    core.entries = static_cast<uint16_t *>(arena_take(core, (first.entries != 0 ? first.entries : 1) * 2));
    core.files = static_cast<FileInfo *>(arena_take(core, capacity * static_cast<uint32_t>(sizeof(FileInfo))));
    if (core.items == nullptr || core.entries == nullptr || core.files == nullptr) {
        return kOutOfMemory;
    }
    core.item_capacity = capacity;

    // The second reading fills the tables. The items count only when it has ended well.
    Seen second;
    core.file_count = 0;
    reason = read_once(core, &first, second);
    if (reason == kNone && (second.items != first.items || second.entries != first.entries || second.animations != first.animations)) {
        reason = kShowMalformed;
    }
    if (reason != kNone) {
        core.file_count = 0;
        return reason;
    }
    core.item_count = second.items;
    core.entry_count = second.entries;

    reason = check_ids(core, second, id_text);
    if (reason != kNone) {
        core.item_count = 0;
        core.entry_count = 0;
        core.file_count = 0;
        return reason;
    }
    core.brightness = static_cast<uint8_t>(second.brightness);
    core.show_brightness = core.brightness;
    return kNone;
}

}  // namespace odrig
