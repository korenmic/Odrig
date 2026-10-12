#include "content.h"

#include <string.h>

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
const char kListHead[] = "{\"ok\":true,\"items\":[";

// The bytes an item takes in a reply of `list`. A cycle is counted with its entries, or
// with none.
uint32_t listed_size(const Core &core, const ItemInfo &item, bool with_entries) {
    uint32_t size = text_length(kListId) + digits(item.id);
    if (!item.is_cycle) {
        const FileInfo &file = core.files[item.first];
        return size + text_length(kListFile) + text_length(file.name) + text_length(kListBytes) + digits(file.bytes) + 1;
    }
    size += text_length(kListCycle) + text_length(kListSeconds) + digits(item.seconds) + 1;
    for (uint32_t entry = 0; with_entries && entry < item.count; ++entry) {
        size += digits(core.items[core.entries[item.first + entry]].id) + (entry != 0 ? 1 : 0);
    }
    return size;
}

// The bytes that end a reply of `list` whose first item left out is at this position.
uint32_t list_tail_size(const Core &core, uint32_t next) {
    return text_length(kListNext) + (next < core.item_count ? digits(next) : 4) + 2;
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
    reply.text("}\n");
    return reply.length;
}

uint32_t content_list(const Core &core, uint32_t from, Reply &reply) {
    reply.text(kListHead);
    uint32_t position = from;
    for (; position < core.item_count; ++position) {
        const ItemInfo &item = core.items[position];
        const uint32_t tail = list_tail_size(core, position + 1);
        // A cycle that would not fit into a reply even alone is listed without its entries.
        bool with_entries = true;
        uint32_t size = listed_size(core, item, true);
        if (item.is_cycle && text_length(kListHead) + size + tail > ODRIG_REPLY_MAX) {
            with_entries = false;
            size = listed_size(core, item, false);
        }
        const uint32_t comma = position != from ? 1 : 0;
        if (!reply.fits(comma + size + tail)) {
            break;
        }
        if (comma != 0) {
            reply.text(",");
        }
        reply.text(kListId);
        reply.number(item.id);
        if (!item.is_cycle) {
            const FileInfo &file = core.files[item.first];
            reply.text(kListFile);
            reply.text(file.name);
            reply.text(kListBytes);
            reply.number(file.bytes);
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
    if (position < core.item_count) {
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
        return refuse(reply, "unknown-id");
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
    out.text(",\"items\":[");
    bool first = true;
    for (uint32_t position = 0; position < core.item_count; ++position) {
        if (position == change.without) {
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
            out.text("\"}");
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
    if (core.has_start && core.start_item != change.without) {
        out.text(",\"start\":");
        out.number(core.items[core.start_item].id);
    }
    out.text("}\n");
    out.flush();
    return !out.failed && host.write_close(host.ctx) == 1;
}

namespace {

void set_file(FileInfo &file, const char *name, uint32_t bytes, uint64_t total_ms) {
    uint32_t length = 0;
    for (; name[length] != '\0'; ++length) {
        file.name[length] = name[length];
    }
    file.name[length] = '\0';
    file.bytes = bytes;
    file.total_ms = total_ms;
}

}  // namespace

void content_add_item(Core &core, uint32_t id, const char *name, uint32_t bytes, uint64_t total_ms) {
    ItemInfo &item = core.items[core.item_count++];
    item.id = static_cast<uint16_t>(id);
    item.seconds = 0;
    item.is_cycle = 0;
    item.first = core.file_count++;
    item.count = 0;
    set_file(core.files[item.first], name, bytes, total_ms);
}

void content_change_file(Core &core, uint32_t position, const char *name, uint32_t bytes, uint64_t total_ms) {
    ItemInfo &item = core.items[position];
    for (uint32_t other = 0; other < core.item_count; ++other) {
        if (other != position && !core.items[other].is_cycle && core.items[other].first == item.first) {
            // The old file stays another item's. There are fewer files than items here,
            // so the file table has room.
            item.first = core.file_count++;
            break;
        }
    }
    set_file(core.files[item.first], name, bytes, total_ms);
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
            for (uint32_t item = 0; item < core.item_count; ++item) {
                if (!core.items[item].is_cycle && core.items[item].first > removed.first) {
                    --core.items[item].first;
                }
            }
        }
    }

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
