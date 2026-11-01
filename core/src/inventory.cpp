#include "inventory.h"

#include "catalog.h"
#include "civil_time.h"
#include "crc32.h"
#include "ignored.h"

namespace odrig {
namespace {
uint32_t number(uint32_t crc, uint32_t value) {
    for (uint32_t i = 0; i < 4; ++i) crc = crc_add(crc, static_cast<uint8_t>(value >> (i * 8)));
    return crc;
}
uint32_t catalog_crc(uint32_t crc, const CatalogState &state) {
    crc = number(crc, state.state);
    crc = number(crc, state.fingerprint);
    crc = number(crc, state.generation);
    return number(crc, state.entries);
}
uint32_t internal_crc(const Core &core) {
    uint32_t crc = catalog_crc(kCrcStart, core.catalogs[kInternal]);
    if (core.invalid) return crc_value(number(crc, 0xFFFFFFFFu));
    crc = number(crc, core.item_count);
    for (uint32_t i = 0; i < core.item_count; ++i) {
        const ItemInfo &item = core.items[i];
        crc = number(crc, item.id);
        crc = number(crc, item.is_cycle);
        crc = number(crc, core.order_items == nullptr ? i : core.order_items[i]);
        if (item.is_cycle) {
            crc = number(crc, item.count);
            for (uint32_t entry = 0; entry < item.count; ++entry) crc = number(crc, core.entries[item.first + entry]);
        } else {
            const FileInfo &file = core.files[item.first];
            for (uint32_t at = 0; file.name[at] != '\0'; ++at) crc = crc_add(crc, static_cast<uint8_t>(file.name[at]));
            crc = crc_add(crc, 0);
            crc = number(crc, file.bytes);
            crc = number(crc, file.fault);
            crc = number(crc, file.checked != 0);
            crc = number(crc, file.type);
            crc = number(crc, item.ignored);
        }
    }
    return crc_value(crc);
}
uint32_t external_crc(const Core &core) {
    uint32_t crc = number(kCrcStart, core.drive_number);
    crc = catalog_crc(crc, core.catalogs[kExternal]);
    crc = number(crc, core.indexed);
    if (core.indexed && core.index != nullptr) {
        crc = number(crc, core.index->files);
        crc = number(crc, core.index->left_out);
    }
    for (uint32_t at = 0; core.remembered != nullptr && at < kRememberedMost; ++at) {
        const Remembered &one = core.remembered[at];
        if (one.reason == kNone) continue;
        for (uint32_t i = 0; one.name[i] != '\0'; ++i) crc = crc_add(crc, static_cast<uint8_t>(one.name[i]));
        crc = crc_add(crc, 0);
        crc = number(crc, one.reason);
        crc = number(crc, one.first_read);
        crc = number(crc, one.crc);
    }
    return crc_value(number(crc, ignored_fingerprint(core)));
}
}

void inventory_reply(const Core &core, Reply &reply) {
    char board[32];
    if (!civil_board(core, board)) return;
    reply.text(",\"inventory\":{\"board\":\"");
    reply.text(board);
    reply.text("\",\"internal\":");
    reply.number(internal_crc(core));
    reply.text(",\"external\":");
    reply.number(external_crc(core));
    reply.text(",\"internal_keys\":");
    reply.number(core.catalogs[kInternal].fingerprint);
    reply.text(",\"external_keys\":");
    reply.number(core.catalogs[kExternal].fingerprint);
    reply.text(",\"authoritative\":");
    const bool external = core.drive_number == 0 ||
        (core.indexed && core.index != nullptr && !core.index->broken && core.tree_known && core.catalogs[kExternal].state == kCatalogOk);
    reply.text(!core.invalid && check_complete(core) && !catalog_rebuilding(core) &&
        !core.ignored_error && external ? "true}" : "false}");
}
}
