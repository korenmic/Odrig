#ifndef ODRIG_IGNORED_H
#define ODRIG_IGNORED_H

#include "commands.h"
#include "core_state.h"

namespace odrig {
const char kIgnoredFile[] = "ignored.txt";
const char kIgnoredPart[] = "ignored.part";
void ignored_drive_found(Core &core);
void ignored_start(Core &core);
bool ignored_own(const Core &core, uint8_t kind, uint32_t position);
bool ignored_inherited(const Core &core, uint8_t kind, uint32_t position);
bool drive_automatic(const Core &core, uint32_t position);
uint32_t ignored_change(Core &core, uint32_t id, bool ignored, Reply &reply);
}
#endif
