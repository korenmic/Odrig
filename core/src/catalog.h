#ifndef ODRIG_CATALOG_H
#define ODRIG_CATALOG_H

#include <stdint.h>

#include "commands.h"
#include "core_state.h"

namespace odrig {

// The catalog of a storage, as docs/catalog.md states it: the marker `catalog.txt`, the
// pages `catalog-00.txt` to `catalog-15.txt`, and while a change is made the new pages
// `catalog-NN.new`, the new marker `catalog.new` and the commit record `catalog.do`.
const uint32_t kCatalogPages = 16;
const uint32_t kMarkerSize = 409;
// The longest line of a page, with its line feed, and of a commit record without it.
const uint32_t kCatalogLineRoom = 162;
// The longest name a catalog holds.
const uint32_t kCatalogNameMost = 100;

// What the start or a drive's plug-in found of a catalog.
struct Marker {
    uint32_t generation;
    uint16_t counts[kCatalogPages];
    uint32_t crcs[kCatalogPages];
};

// Whether a catalog may hold a file of this name.
bool catalog_name_allowed(const char *name, uint32_t length);

// The page of a name: the low four bits of the FNV-1a hash of its bytes.
uint32_t catalog_page_of(const char *name, uint32_t length);

// The start, before anything else is read: finishes the change of the internal catalog whose
// commit record is whole, on a host that can change its storage.
void catalog_finish_internal(Core &core);

// The start, once the show is read: reads the internal catalog with the first source, and
// gives every file of the show it has an entry for its size and length without opening it.
void catalog_read_internal(Core &core);

// A change of a storage's catalog: the entry `added` (a name, with its size, CRC-32 and
// length, for the mapping's canvas) put in the place of the entry of its name or added; the
// entries whose names `drops` gives true for taken out, on the pages of `drop_pages`; and the
// actions of the commit record, `move upload.part <added>` and `remove <removed_file>`.
struct CatalogChange {
    const char *added = nullptr;
    uint32_t added_bytes = 0;
    uint32_t added_crc = 0;
    uint64_t added_total_ms = 0;
    bool (*drops)(const Core &core, const char *name, uint32_t length, const void *context) = nullptr;
    const void *context = nullptr;
    uint32_t drop_pages = 0;
    bool moves_part = false;
    const char *removed_file = nullptr;
};

// Commits a change of a storage's catalog and finishes it, with the second source and the
// chunk buffer. A storage whose catalog is not ok is not changed: true. False on a failed
// storage call: before the commit record nothing changed; after it the rest is finished at
// the next start.
bool catalog_commit(Core &core, uint32_t storage, const CatalogChange &change);

// The reply to `catalog`.
uint32_t catalog_reply(const Core &core, Reply &reply);

}  // namespace odrig

#endif
