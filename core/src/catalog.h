#ifndef ODRIG_CATALOG_H
#define ODRIG_CATALOG_H

#include <stdint.h>

#include "commands.h"
#include "container.h"
#include "core_state.h"

namespace odrig {

// The catalog of a storage, as docs/catalog.md states it: the marker `catalog.txt`, the
// pages `catalog-00.txt` to `catalog-15.txt`, and while a change is made the new pages
// `catalog-NN.new`, the new marker `catalog.new` and the commit record `catalog.do`.
const uint32_t kCatalogPages = 16;
const uint32_t kMarkerSize = 409;
// The longest line of a page, with its line feed, and of a commit record without it.
const uint32_t kCatalogLineRoom = 162;
// The longest name a catalog holds, a path from the card's folder, and the most folders a
// path may have.
const uint32_t kCatalogNameMost = 100;
const uint32_t kCatalogDeepest = 3;

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
// commit record is whole, on a host that can change its storage. A record that a failed call
// leaves makes the catalog damaged, `interrupted`, for this boot.
void catalog_finish_internal(Core &core);

// Whether a whole commit record of the storage is left that the start or the plug-in could
// not finish.
bool catalog_left(const Core &core, uint32_t storage);

// Before a change of a storage writes anything: finishes the change whose commit record a
// failed call left; false while it is still left, and the change is refused. A catalog that
// the start found interrupted is kept again once its change is finished.
bool catalog_settle(Core &core, uint32_t storage);

// The start, once the show is read: reads the internal catalog with the first source, and
// gives every file of the show it has an entry for its size, length and type without opening
// it.
void catalog_read_internal(Core &core);

// A change of a storage's catalog: the entry `added` (a name, with its size, CRC-32, length,
// the loop of a text or a clock, and type, for the mapping's canvas) put in the place of the
// entry of its name or added; the entries whose names `drops` gives true for taken out, on
// the pages of `drop_pages`; and the actions of the commit record, `move upload.part
// <added>` and `remove <removed_file>`.
struct CatalogChange {
    const char *added = nullptr;
    uint32_t added_bytes = 0;
    uint32_t added_crc = 0;
    uint64_t added_total_ms = 0;
    uint8_t added_type = kTypeFrames;
    bool (*drops)(const Core &core, const char *name, uint32_t length, const void *context) = nullptr;
    const void *context = nullptr;
    uint32_t drop_pages = 0;
    bool moves_part = false;
    const char *removed_file = nullptr;
};

// Commits a change of a storage's catalog and finishes it, with the second source and the
// chunk buffer, once a change a failed call left is finished. A storage whose catalog is not
// ok is not changed: true. False on a failed storage call before the commit record is whole:
// nothing changed. After it, what a failed call leaves is finished before the next change of
// the storage, or at the next start or plug-in.
bool catalog_commit(Core &core, uint32_t storage, const CatalogChange &change);

// The phases of reading a drive's catalog: none; its commit record; its marker; its pages;
// the saved order and the publication.
const uint8_t kLoadIdle = 0;
const uint8_t kLoadRecord = 1;
const uint8_t kLoadMarker = 2;
const uint8_t kLoadPages = 3;
const uint8_t kLoadOrder = 4;
// How long a drive's catalog stays read before its marker is looked at again, in ms.
const uint64_t kLookEveryMs = 10000;

// A drive was plugged in or pulled out: for a host that can be given the names of its
// files, its catalog is to be read; otherwise, and without a drive, nothing is.
void catalog_drive_plugged(Core &core);

// Whether a drive's catalog is being read.
bool catalog_drive_loading(const Core &core);

// One step of reading a drive's catalog, at most one read of a page: its commit record,
// its marker, its pages, the saved order, and the publication of every entry at once.
void catalog_drive_step(Core &core);

// The second source was taken: the page being read is read again from its start.
void catalog_drive_yields(Core &core);

// At a refresh: the marker of a drive whose catalog is read is read again once in
// kLookEveryMs; another marker drops the drive's animations and reads the catalog again.
void catalog_drive_look(Core &core);

// The player left out a file of a drive whose catalog is read: it is remembered by its
// name and its entry's CRC-32, so that a catalog read again leaves it out again.
void catalog_drive_left_out(Core &core, uint32_t place, Reason reason);

// Whether the core may change the drive: a host that can write it, and its catalog read.
bool catalog_drive_writable(const Core &core);

// The place an upload of this name to the drive takes: the place of the drive's file of that
// name, else the first place a removal freed, else the next one; kDriveMost when none is left.
uint32_t catalog_drive_place_for(const Core &core, const char *name);

// Puts the upload whose check has passed onto the drive: one commit of the drive's catalog
// moves `upload.part` onto its name with its entry; its place keeps its id when the file
// replaces one, and gets the lowest free id otherwise. False on a failed storage call.
bool catalog_install_external(Core &core, uint16_t *id);

// Removes the drive's animation at a place: one commit takes its entry out and removes its
// file, and the place is free. False on a failed storage call.
bool catalog_remove_external(Core &core, uint32_t place);

// `catalog rebuild internal` and `catalog rebuild external`: reads every animation of the
// storage with the check's steps and commits its catalog anew at the end. `busy` while an
// upload is open, a test shows, a rebuild runs or the drive's catalog is read; `read-only` on
// a host that cannot change the storage.
uint32_t catalog_rebuild(Core &core, uint32_t storage, Reply &reply);

// `catalog cancel`: ends a rebuild, and the catalog stays as it was.
uint32_t catalog_cancel(Core &core, Reply &reply);

// Whether a rebuild runs.
inline bool catalog_rebuilding(const Core &core) {
    return core.rebuild != 0;
}

// One step of a rebuild, in the schedule of the check after the start.
void catalog_rebuild_step(Core &core);

// The drive went or another came: a rebuild of its catalog ends.
void catalog_drive_went(Core &core);

// The reply to `catalog`.
uint32_t catalog_reply(const Core &core, Reply &reply);

}  // namespace odrig

#endif
