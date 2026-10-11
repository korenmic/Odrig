#ifndef ODRIG_SHOW_H
#define ODRIG_SHOW_H

#include <stdint.h>

#include "core_state.h"
#include "reasons.h"

namespace odrig {

// Room for the text of an id: a sign and ten digits.
const uint32_t kIdTextSize = 12;

// Reads `show.json` under the rules of docs/show.md, sets up the item, entry and file tables
// of the core, and checks the ids. Returns kNone, kShowMissing, kShowMalformed,
// kDuplicateId, kUndefinedId, kNestedCycle, kReadError or kOutOfMemory. For the three
// reasons about an id, `id_text` receives that id as text; it holds kIdTextSize characters.
Reason read_show(Core &core, char *id_text);

}  // namespace odrig

#endif
