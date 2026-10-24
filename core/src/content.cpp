#include "content.h"

#include <string.h>

#include "order.h"
#include "player.h"
#include "storage.h"

namespace odrig {

namespace {

// The number of decimal digits of a value.
uint32_t digits(uint32_t value) {
    uint32_t count = 1;
    while (value >= 10) {
        value /= 10;
        ++count;
    }
    return count;
}

uint32_t text_length(const char *text) {
    uint32_t length = 0;
    while (text[length] != '\0') {
        ++length;
    }
    return length;
}

// The parts of an item as `list` writes it.
const char kListId[] = "{\"id\":";
const char kListFile[] = ",\"file\":\"";
const char kListBytes[] = "\",\"bytes\":";
const char kListCycle[] = ",\"cycle\":[";
const char kListSeconds[] = "],\"seconds\":";
const char kListNext[] = "],\"next\":";
const char kListType[] = ",\"type\":\"";
const char kListHead[] = "{\"ok\":true,\"items\":[";
const char kListInternal[] = ",\"external\":false";
const char kListExternal[] = ",\"external\":true";

// The member that ends an animation of `list` whose file is quarantined, before its reason
// and the closing quotation mark.
const char kListFault[] = ",\"fault\":\"";

// The bytes an item takes in a reply of `list`. A cycle is counted with its entries, or
// with none. An animation whose file is quarantined has `null` for its bytes, which are not
// known, and its fault.
uint32_t listed_size(const Core &core, const ItemInfo &item, bool with_entries) {
    uint32_t size = text_length(kListId) + digits(item.id);
    if (!item.is_cycle) {
        const FileInfo &file = core.files[item.first];
        const Reason fault = static_cast<Reason>(file.fault);
        const uint32_t bytes = fault != kNone || !file.checked ? 4 : digits(file.bytes);
        const uint32_t fault_size = fault != kNone ? text_length(kListFault) + text_length(reason_name(fault)) + 1 : 0;
        return size + text_length(kListFile) + text_length(file.name) + text_length(kListBytes) + bytes + (item.ignored ? 15 : 16) +
               text_length(kListInternal) + text_length(kListType) + text_length(type_name(file.type)) + 1 + fault_size + 1;
    }
    size += text_length(kListCycle) + text_length(kListSeconds) + digits(item.seconds) + 1;
    for (uint32_t entry = 0; with_entries && entry < item.count; ++entry) {
        size += digits(core.items[core.entries[item.first + entry]].id) + (entry != 0 ? 1 : 0);
    }
    return size;
}

// The bytes that end a reply of `list` whose first item left out is at this position, of
// all that are listed.
uint32_t list_tail_size(uint32_t next, uint32_t total) {
    return text_length(kListNext) + (next < total ? digits(next) : 4) + 2;
}

// Whether a file of the drive is listed: an animation of the playlist, or a file left out
// for a fault, which has an id.
bool drive_is_listed(const DriveEntry &entry) {
    return entry.state == kDriveInPlaylist || (entry.state == kDriveLeftOut && entry.id != 0);
}

// The number of the drive's listed files: they are listed after the items.
uint32_t drive_listed(const Core &core) {
    uint32_t count = 0;
    for (uint32_t place = 0; core.drive != nullptr && place < core.drive_count; ++place) {
        count += drive_is_listed(core.drive[place]) ? 1 : 0;
    }
    return count;
}

// The place of the drive's file that is listed at this place among them.
uint32_t drive_listed_place(const Core &core, uint32_t listed) {
    for (uint32_t place = 0; place < core.drive_count; ++place) {
        if (drive_is_listed(core.drive[place])) {
            if (listed == 0) {
                return place;
            }
            --listed;
        }
    }
    return core.drive_count;
}

// The text of a file the core writes, gathered in the chunk buffer and given to the host
// whenever the buffer is full.
struct Writer {
    void byte(char value) {
        if (failed) {
            return;
        }
        core->chunk[used++] = static_cast<uint8_t>(value);
        if (used == kChunkSize) {
            flush();
        }
    }

    void text(const char *more) {
        while (*more != '\0') {
            byte(*more++);
        }
    }

    void number(uint32_t value) {
        char figures[10];
        uint32_t count = 0;
        do {
            figures[count++] = static_cast<char>('0' + value % 10);
            value /= 10;
        } while (value != 0);
        while (count != 0) {
            byte(figures[--count]);
        }
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

}  // namespace

uint32_t content_space(const Core &core, Reply &reply) {
    uint32_t free_bytes = 0;
    uint32_t total_bytes = 0;
    if (core.host.space == nullptr || core.host.space(core.host.ctx, &free_bytes, &total_bytes) != 1) {
        return refuse(reply, "storage-error");
    }
    uint32_t animations = 0;
    for (uint32_t item = 0; !core.invalid && item < core.item_count; ++item) {
        if (!core.items[item].is_cycle) {
            ++animations;
        }
    }
    reply.text("{\"ok\":true,\"free\":");
    reply.number(free_bytes);
    reply.text(",\"total\":");
    reply.number(total_bytes);
    reply.text(",\"animations\":");
    reply.number(animations);
    const uint32_t generation = core.host.drive != nullptr && core.host.drive_name != nullptr && storage_changes(core) ? core.host.drive(core.host.ctx) : 0;
    uint64_t external_free = 0, external_total = 0;
    const bool known = generation != 0 && core.host.drive_space != nullptr &&
        core.host.drive_space(core.host.ctx, generation, &external_free, &external_total) == 1 &&
        external_free <= external_total && external_total <= 9007199254740991ull;
    reply.text(",\"external\":{\"present\":");
    reply.text(generation != 0 ? "true" : "false");
    reply.text(",\"free\":");
    if (known) reply.number(external_free); else reply.text("null");
    reply.text(",\"total\":");
    if (known) reply.number(external_total); else reply.text("null");
    reply.text(",\"read_only\":true}}\n");
    return reply.length;
}

uint32_t content_list(const Core &core, uint32_t from, Reply &reply) {
    reply.text(kListHead);
    // The items of the show, then the drive's animations in the playlist.
    const uint32_t total = core.item_count + drive_listed(core);
    uint32_t position = from;
    bool first = true;
    for (; position < total; ++position) {
        const uint32_t tail = list_tail_size(position + 1, total);
        if (position >= core.item_count) {
            const uint32_t place = drive_listed_place(core, position - core.item_count);
            const DriveEntry &entry = core.drive[place];
            char name[kDriveListedName];
            if (core.host.drive_name(core.host.ctx, core.drive_number, place, name, sizeof name) != 1) {
                // The drive went while the list was written: it is no more.
                continue;
            }
            const bool left_out = entry.state == kDriveLeftOut;
            const char *fault = reason_name(static_cast<Reason>(entry.fault));
            const uint32_t size = (first ? 0 : 1) + text_length(kListId) + digits(entry.id) + text_length(kListFile) + json_escaped(name, nullptr) +
                                  text_length(kListBytes) + (left_out ? 4 + text_length(kListFault) + text_length(fault) + 1 : digits(entry.bytes)) +
                                  text_length(kListExternal) + text_length(kListType) + text_length(type_name(entry.type)) + 1 + 1;
            if (!reply.fits(size + tail)) {
                break;
            }
            if (!first) {
                reply.text(",");
            }
            first = false;
            reply.text(kListId);
            reply.number(entry.id);
            reply.text(kListFile);
            reply.escaped(name);
            reply.text(kListBytes);
            if (left_out) {
                reply.text("null");
            } else {
                reply.number(entry.bytes);
            }
            reply.text(kListExternal);
            reply.text(kListType);
            reply.text(type_name(entry.type));
            reply.text("\"");
            if (left_out) {
                reply.text(kListFault);
                reply.text(fault);
                reply.text("\"");
            }
            reply.text("}");
            continue;
        }
        const ItemInfo &item = core.items[position];
        // A cycle that would not fit into a reply even alone is listed without its entries.
        bool with_entries = true;
        uint32_t size = listed_size(core, item, true);
        if (item.is_cycle && text_length(kListHead) + size + tail > ODRIG_REPLY_MAX) {
            with_entries = false;
            size = listed_size(core, item, false);
        }
        const uint32_t comma = first ? 0 : 1;
        if (!reply.fits(comma + size + tail)) {
            break;
        }
        if (comma != 0) {
            reply.text(",");
        }
        first = false;
        reply.text(kListId);
        reply.number(item.id);
        if (!item.is_cycle) {
            const FileInfo &file = core.files[item.first];
            reply.text(kListFile);
            reply.text(file.name);
            reply.text(kListBytes);
            if (file.fault != kNone || !file.checked) {
                reply.text("null");
            } else {
                reply.number(file.bytes);
            }
            reply.text(item.ignored ? ",\"ignored\":true" : ",\"ignored\":false");
            reply.text(kListInternal);
            reply.text(kListType);
            reply.text(type_name(file.type));
            reply.text("\"");
            if (file.fault != kNone) {
                reply.text(kListFault);
                reply.text(reason_name(static_cast<Reason>(file.fault)));
                reply.text("\"");
            }
        } else {
            reply.text(kListCycle);
            for (uint32_t entry = 0; with_entries && entry < item.count; ++entry) {
                if (entry != 0) {
                    reply.text(",");
                }
                reply.number(core.items[core.entries[item.first + entry]].id);
            }
            reply.text(kListSeconds);
            reply.number(item.seconds);
        }
        reply.text("}");
    }
    reply.text(kListNext);
    if (position < total) {
        reply.number(position);
    } else {
        reply.text("null");
    }
    reply.text("}\n");
    return reply.length;
}

uint32_t content_remove(Core &core, uint32_t id, Reply &reply) {
    if (core.upload.state != kUploadNone) {
        return refuse(reply, "busy");
    }
    uint32_t position = 0;
    while (position < core.item_count && core.items[position].id != id) {
        ++position;
    }
    if (position == core.item_count) {
        // An animation of the drive is the drive's: no command removes it.
        return refuse(reply, drive_place_holding(core, id) != kDriveMost ? "in-use" : "unknown-id");
    }
    // An animation that a cycle lists stays until the cycle is gone.
    for (uint32_t entry = 0; entry < core.entry_count; ++entry) {
        if (core.entries[entry] == position) {
            return refuse(reply, "in-use");
        }
    }
    if (!storage_changes(core) || !storage_remove_item(core, position)) {
        return refuse(reply, "storage-error");
    }
    return succeed(reply);
}

bool content_removed(const Core &core, uint32_t position, const ShowChange &change) {
    if (position == change.without) return true;
    for (uint32_t at = 0; at < change.removed_count; ++at) {
        if (core.items[position].id == change.removed[at]) return true;
    }
    return false;
}

uint32_t content_ignore(Core &core, uint32_t id, bool ignored, Reply &reply) {
    if (core.upload.state != kUploadNone) return refuse(reply, "busy");
    uint32_t position = 0;
    while (position < core.item_count && core.items[position].id != id) ++position;
    if (position == core.item_count) return refuse(reply, drive_place_holding(core, id) != kDriveMost ? "in-use" : "unknown-id");
    ItemInfo &item = core.items[position];
    if (item.is_cycle) return refuse(reply, "in-use");
    if ((item.ignored != 0) == ignored) return succeed(reply);
    if (!storage_changes(core) || core.pending_cleanup) return refuse(reply, "storage-error");
    ShowChange change;
    change.inclusion = position;
    change.ignored = ignored;
    if (!content_write_show(core, change) || core.host.rename(core.host.ctx, kShowPart, kShowFile) != 1) {
        core.host.remove(core.host.ctx, kShowPart);
        return refuse(reply, "storage-error");
    }
    item.ignored = ignored ? 1 : 0;
    item.has_ignored = 1;
    player_inclusion_changed(core, position);
    return succeed(reply);
}

uint32_t content_remove_many(Core &core, const uint16_t *ids, uint32_t count, Reply &reply) {
    if (core.upload.state != kUploadNone) return refuse(reply, "busy");
    for (uint32_t at = 0; at < count; ++at) {
        uint32_t position = 0;
        while (position < core.item_count && core.items[position].id != ids[at]) ++position;
        if (position == core.item_count) return refuse(reply, drive_place_holding(core, ids[at]) != kDriveMost ? "in-use" : "unknown-id");
    }
    for (uint32_t at = 0; at < count; ++at) {
        uint32_t position = 0;
        while (core.items[position].id != ids[at]) ++position;
        if (core.items[position].is_cycle) return refuse(reply, "in-use");
        for (uint32_t entry = 0; entry < core.entry_count; ++entry) {
            if (core.entries[entry] == position) return refuse(reply, "in-use");
        }
    }
    if (!storage_changes(core) || !storage_remove_many(core, ids, count)) return refuse(reply, "storage-error");
    return succeed(reply);
}

bool content_write_show(Core &core, const ShowChange &change) {
    const odrig_host &host = core.host;
    if (host.write_open(host.ctx, kShowPart) != 1) {
        return false;
    }
    Writer out;
    out.core = &core;
    out.used = 0;
    out.failed = false;
    out.text("{\"version\":1,\"brightness\":");
    out.number(core.show_brightness);
    if (core.has_min_seconds) {
        out.text(",\"min_seconds\":");
        out.number(core.min_seconds);
    }
    out.text(",\"items\":[");
    bool first = true;
    for (uint32_t position = 0; position < core.item_count; ++position) {
        if (content_removed(core, position, change)) {
            continue;
        }
        const ItemInfo &item = core.items[position];
        if (!first) {
            out.byte(',');
        }
        first = false;
        out.text("{\"id\":");
        out.number(item.id);
        if (!item.is_cycle) {
            out.text(",\"file\":\"");
            out.text(position == change.renamed ? change.name : core.files[item.first].name);
            out.byte('"');
            // What the show says of the animation's turn: its loops, and its longest time.
            if (item.count != 0) {
                out.text(",\"repeat\":");
                out.number(item.count);
            }
            if (item.seconds != 0) {
                out.text(",\"max_seconds\":");
                out.number(item.seconds);
            }
            if (item.has_ignored || position == change.inclusion) {
                out.text(",\"ignored\":");
                out.text((position == change.inclusion ? change.ignored : item.ignored != 0) ? "true" : "false");
            }
            out.byte('}');
        } else {
            out.text(",\"cycle\":[");
            for (uint32_t entry = 0; entry < item.count; ++entry) {
                if (entry != 0) {
                    out.byte(',');
                }
                out.number(core.items[core.entries[item.first + entry]].id);
            }
            out.text("],\"seconds\":");
            out.number(item.seconds);
            out.byte('}');
        }
    }
    if (change.added_id != 0) {
        if (!first) {
            out.byte(',');
        }
        out.text("{\"id\":");
        out.number(change.added_id);
        out.text(",\"file\":\"");
        out.text(change.added_name);
        out.text("\"}");
    }
    out.byte(']');
    if (core.has_start && !content_removed(core, core.start_item, change)) {
        out.text(",\"start\":");
        out.number(core.items[core.start_item].id);
    }
    out.text("}\n");
    out.flush();
    return !out.failed && host.write_close(host.ctx) == 1;
}

namespace {

// The file of an upload whose check has passed: a new content, which is usable and was
// read whole.
void set_file(FileInfo &file, const char *name, uint32_t bytes, uint64_t total_ms, uint8_t type) {
    uint32_t length = 0;
    for (; name[length] != '\0'; ++length) {
        file.name[length] = name[length];
    }
    file.name[length] = '\0';
    file.fault = kNone;
    file.checked = 1;
    file.bytes = bytes;
    file.total_ms = total_ms;
    file.type = type;
}

}  // namespace

void content_add_item(Core &core, uint32_t id, const char *name, uint32_t bytes, uint64_t total_ms, uint8_t type) {
    ItemInfo &item = core.items[core.item_count++];
    item.id = static_cast<uint16_t>(id);
    item.seconds = 0;
    item.is_cycle = 0;
    item.ignored = 0;
    item.has_ignored = 0;
    item.first = core.file_count++;
    item.count = 0;
    set_file(core.files[item.first], name, bytes, total_ms, type);
    order_item_added(core, core.item_count - 1);
}

void content_change_file(Core &core, uint32_t position, const char *name, uint32_t bytes, uint64_t total_ms, uint8_t type) {
    ItemInfo &item = core.items[position];
    for (uint32_t other = 0; other < core.item_count; ++other) {
        if (other != position && !core.items[other].is_cycle && core.items[other].first == item.first) {
            // The old file stays another item's. There are fewer files than items here,
            // so the file table has room.
            item.first = core.file_count++;
            break;
        }
    }
    set_file(core.files[item.first], name, bytes, total_ms, type);
}

void content_take_out(Core &core, uint32_t position) {
    const ItemInfo removed = core.items[position];
    if (removed.is_cycle) {
        // Its entries leave the entry table, and the cycles after it follow.
        const uint32_t after = removed.first + removed.count;
        memmove(core.entries + removed.first, core.entries + after, (core.entry_count - after) * sizeof(uint16_t));
        core.entry_count -= removed.count;
        for (uint32_t item = 0; item < core.item_count; ++item) {
            if (core.items[item].is_cycle && core.items[item].first > removed.first) {
                core.items[item].first -= removed.count;
            }
        }
    } else {
        bool shared = false;
        for (uint32_t item = 0; item < core.item_count; ++item) {
            shared = shared || (item != position && !core.items[item].is_cycle && core.items[item].first == removed.first);
        }
        if (!shared) {
            // Its file leaves the file table, and the files after it follow.
            const uint32_t after = removed.first + 1;
            memmove(core.files + removed.first, core.files + after, (core.file_count - after) * sizeof(FileInfo));
            --core.file_count;
            check_file_left(core, removed.first);
            for (uint32_t item = 0; item < core.item_count; ++item) {
                if (!core.items[item].is_cycle && core.items[item].first > removed.first) {
                    --core.items[item].first;
                }
            }
        }
    }

    order_item_leaves(core, position);
    memmove(core.items + position, core.items + position + 1, (core.item_count - position - 1) * sizeof(ItemInfo));
    --core.item_count;

    // Every position above the one that is gone is one lower now. No entry of a cycle is
    // the position itself: an animation that a cycle lists is not taken out.
    for (uint32_t entry = 0; entry < core.entry_count; ++entry) {
        if (core.entries[entry] > position) {
            --core.entries[entry];
        }
    }
    if (core.has_start && core.start_item == position) {
        core.has_start = 0;
        core.start_item = 0;
    } else if (core.has_start && core.start_item > position) {
        --core.start_item;
    }
}

}  // namespace odrig
