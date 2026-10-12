#include "storage.h"

#include "content.h"
#include "json_reader.h"
#include "player.h"
#include "show.h"

namespace odrig {

namespace {

// Whether an item of the show names this file.
bool is_named(const Core &core, const char *name) {
    for (uint32_t file = 0; file < core.file_count; ++file) {
        if (same_text(core.files[file].name, name)) {
            return true;
        }
    }
    return false;
}

// Puts a name and a line feed into the chunk buffer, from `length` on. An absent name
// adds nothing. Returns the new length.
uint32_t add_line(Core &core, uint32_t length, const char *name) {
    if (name == nullptr) {
        return length;
    }
    for (uint32_t at = 0; name[at] != '\0'; ++at) {
        core.chunk[length++] = static_cast<uint8_t>(name[at]);
    }
    core.chunk[length++] = '\n';
    return length;
}

// Writes `pending.txt`: each name on a line of its own, ended by a line feed. The second
// name may be absent.
bool write_pending(Core &core, const char *first, const char *second) {
    const odrig_host &host = core.host;
    if (host.write_open(host.ctx, kPending) != 1) {
        return false;
    }
    const uint32_t length = add_line(core, add_line(core, 0, first), second);
    return host.write(host.ctx, core.chunk, length) == 1 && host.write_close(host.ctx) == 1;
}

}  // namespace

void storage_clear_parts(Core &core) {
    if (!storage_changes(core)) {
        return;
    }
    core.host.remove(core.host.ctx, kUploadPart);
    core.host.remove(core.host.ctx, kShowPart);
}

void storage_settle_pending(Core &core) {
    if (!storage_changes(core) || core.chunk == nullptr) {
        return;
    }
    if (core.file.open(core.host, kPending) != kNone) {
        return;
    }
    uint32_t length = 0;
    int got = 0;
    while (length < kPendingSize && (got = core.file.get()) >= 0) {
        core.chunk[length++] = static_cast<uint8_t>(got);
    }
    core.file.close();
    if (got == -kReadError) {
        return;
    }
    // Every line that ends in a line feed and is a file name is taken. A file named
    // there that no item names is what an interrupted change left behind.
    const odrig_host &host = core.host;
    bool all_gone = true;
    uint32_t begin = 0;
    for (uint32_t at = 0; at < length; ++at) {
        if (core.chunk[at] != '\n') {
            continue;
        }
        const uint32_t size = at - begin;
        char name[33];
        if (size >= 1 && size <= 32) {
            for (uint32_t index = 0; index < size; ++index) {
                name[index] = static_cast<char>(core.chunk[begin + index]);
            }
            name[size] = '\0';
            if (is_file_name(name) && !is_named(core, name) && host.remove(host.ctx, name) == -1) {
                all_gone = false;
            }
        }
        begin = at + 1;
    }
    // A file that could not be removed stays named, for the next start.
    if (all_gone) {
        host.remove(host.ctx, kPending);
    }
}

bool storage_install_upload(Core &core) {
    const odrig_host &host = core.host;
    const Upload &upload = core.upload;
    uint32_t position = 0;
    while (position < core.item_count && core.items[position].id != upload.id) {
        ++position;
    }

    if (position < core.item_count && same_text(core.files[core.items[position].first].name, upload.name)) {
        // The item's file is replaced under its own name: the show file stays as it is,
        // and the one rename is where the show changes.
        player_releases_file(core, position);
        if (host.rename(host.ctx, kUploadPart, upload.name) != 1) {
            return false;
        }
        content_change_file(core, position, upload.name, upload.size, upload.total_ms);
        player_file_replaced(core, position);
        return true;
    }

    // A new item, or an item that gets a file of another name. The old file goes when no
    // other item names it.
    const bool is_new = position == core.item_count;
    char old_file[33];
    old_file[0] = '\0';
    if (!is_new) {
        const ItemInfo &item = core.items[position];
        bool shared = false;
        for (uint32_t other = 0; other < core.item_count; ++other) {
            shared = shared || (other != position && !core.items[other].is_cycle && core.items[other].first == item.first);
        }
        if (!shared) {
            const char *name = core.files[item.first].name;
            uint32_t length = 0;
            for (; name[length] != '\0'; ++length) {
                old_file[length] = name[length];
            }
            old_file[length] = '\0';
        }
    }
    const bool with_old_file = old_file[0] != '\0';

    if (!write_pending(core, upload.name, with_old_file ? old_file : nullptr) ||
        host.rename(host.ctx, kUploadPart, upload.name) != 1) {
        host.remove(host.ctx, kPending);
        return false;
    }
    ShowChange change;
    if (is_new) {
        change.added_id = upload.id;
        change.added_name = upload.name;
    } else {
        change.renamed = position;
        change.name = upload.name;
    }
    if (!content_write_show(core, change) || host.rename(host.ctx, kShowPart, kShowFile) != 1) {
        host.remove(host.ctx, kShowPart);
        host.remove(host.ctx, upload.name);
        host.remove(host.ctx, kPending);
        return false;
    }

    // The show in storage is the new one from here on.
    if (is_new) {
        content_add_item(core, upload.id, upload.name, upload.size, upload.total_ms);
    } else {
        content_change_file(core, position, upload.name, upload.size, upload.total_ms);
        player_file_replaced(core, position);
    }
    if (!with_old_file || host.remove(host.ctx, old_file) != -1) {
        host.remove(host.ctx, kPending);
    }
    return true;
}

bool storage_remove_item(Core &core, uint32_t position) {
    const odrig_host &host = core.host;
    const ItemInfo &item = core.items[position];

    // The item's file goes with it when no other item names it.
    char file[33];
    file[0] = '\0';
    if (!item.is_cycle) {
        bool shared = false;
        for (uint32_t other = 0; other < core.item_count; ++other) {
            shared = shared || (other != position && !core.items[other].is_cycle && core.items[other].first == item.first);
        }
        if (!shared) {
            const char *name = core.files[item.first].name;
            uint32_t length = 0;
            for (; name[length] != '\0'; ++length) {
                file[length] = name[length];
            }
            file[length] = '\0';
        }
    }
    const bool with_file = file[0] != '\0';

    if (with_file && !write_pending(core, file, nullptr)) {
        host.remove(host.ctx, kPending);
        return false;
    }
    ShowChange change;
    change.without = position;
    if (!content_write_show(core, change) || host.rename(host.ctx, kShowPart, kShowFile) != 1) {
        host.remove(host.ctx, kShowPart);
        if (with_file) {
            host.remove(host.ctx, kPending);
        }
        return false;
    }

    // The show in storage is the new one from here on. What cannot be removed now is
    // named by `pending.txt` and is removed at the next start.
    player_item_leaves(core, position);
    content_take_out(core, position);
    if (with_file && host.remove(host.ctx, file) != -1) {
        host.remove(host.ctx, kPending);
    }
    return true;
}

}  // namespace odrig
