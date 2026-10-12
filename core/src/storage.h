#ifndef ODRIG_STORAGE_H
#define ODRIG_STORAGE_H

#include "core_state.h"

namespace odrig {

// The files the core keeps in the folder of the show for itself, beside the files of the
// installed file set. No show names them: a name in `show.json` ends in `.odrg`.
const char kUploadPart[] = "upload.part";   // the bytes of the open upload
const char kShowPart[] = "show.part";       // the next `show.json`, until it is renamed
const char kPending[] = "pending.txt";      // the `.odrg` names a change makes or deletes

// Whether the host has storage that can be changed. A host without it sets `write_open`
// to a null pointer, and the core then calls none of the storage functions but `space`.
inline bool storage_changes(const Core &core) {
    return core.host.write_open != nullptr;
}

}  // namespace odrig

#endif
