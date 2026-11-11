#ifndef ODRIG_SHOW_H
#define ODRIG_SHOW_H

#include <stdint.h>

#include "core_state.h"
#include "reasons.h"

namespace odrig {

// Room for the text of an id: a sign and ten digits.
const uint32_t kIdTextSize = 12;

// The item table has room for this many items more than the show has at startup, and for
// this many at least, and never for more than there are ids.
const uint32_t kSpareItems = 32;
const uint32_t kFewestItems = 128;
const uint32_t kMostItems = 65535;

// The naming rule of a file: 1 to 32 characters from a-z, 0-9, `-`, `_` and `.`, ending in
// `.odrg`. The text is known to be at most 32 characters long.
bool is_file_name(const char *name);

// The rule of a stored name: a file name of 32 characters at most, alone or after `<n>/`,
// the number of a folder of the storage, 1 to 255 without a leading zero.
bool is_stored_name(const char *name);

// The number of the folder of a stored name, 0 for a name without one.
uint32_t stored_folder(const char *name);

// The file name of a stored name, after its folder's number.
const char *stored_base(const char *name);

// Reads `show.json` under the rules of docs/show.md, sets up the item, entry and file tables
// of the core, with room to spare in the item and the file table, and checks the ids. A
// host without a show file has the empty show: no item, brightness 128. Returns kNone,
// kShowMalformed, kDuplicateId, kUndefinedId, kNestedCycle, kReadError or kOutOfMemory. For
// the three reasons about an id, `id_text` receives that id as text; it holds kIdTextSize
// characters.
Reason read_show(Core &core, char *id_text);

}  // namespace odrig

#endif
