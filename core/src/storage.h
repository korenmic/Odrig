#ifndef ODRIG_STORAGE_H
#define ODRIG_STORAGE_H

#include <stdint.h>

#include "core_state.h"

namespace odrig {

// The show file, and the files the core keeps in the folder of the show for itself beside
// the files of the installed file set. No show names them: a name in `show.json` ends in
// `.odrg`.
const char kShowFile[] = "show.json";
const char kUploadPart[] = "upload.part";   // the bytes of the open upload
const char kShowPart[] = "show.part";       // the next `show.json`, until it is renamed
const char kPending[] = "pending.txt";      // the `.odrg` names a change makes or deletes

// The most bytes the core gives the host's `write` in one call, and the size of the block
// it gathers them in.
const uint32_t kChunkSize = 1500;

// The most bytes of `pending.txt` the core reads at its start.
const uint32_t kPendingSize = 1500;

// Whether the host has storage that can be changed. A host without it sets `write_open`
// to a null pointer, and the core then calls none of the storage functions but `space`.
inline bool storage_changes(const Core &core) {
    return core.host.write_open != nullptr;
}

// The start, before anything is read: removes the two temporary files an interrupted
// change can have left.
void storage_clear_parts(Core &core);

// The start, once the show file is read and its ids are checked: removes every file that
// `pending.txt` names and no item names, and then `pending.txt`. A folder without that
// file is asked for it and nothing else.
void storage_settle_pending(Core &core);

// Puts the upload whose check has passed in place: its file under its name, and its item
// into the show in storage and then into the tables, as a new last item or in place of
// the animation the item with its id had. What plays starts again when its file was
// replaced. False when storage could not be written; the show is then as it was.
bool storage_install_upload(Core &core);

// Takes the item at a position out of the show in storage, and then out of the tables:
// the names concerned into `pending.txt`, the show without the item into `show.part`,
// that file renamed onto `show.json`, and then the item's file removed when no other item
// names it. False when storage could not be written; the show is then as it was, in
// storage and in the tables.
bool storage_remove_item(Core &core, uint32_t position);
bool storage_remove_many(Core &core, const uint16_t *ids, uint32_t count);

}  // namespace odrig

#endif
