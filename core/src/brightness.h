#ifndef ODRIG_BRIGHTNESS_H
#define ODRIG_BRIGHTNESS_H

#include "commands.h"
#include "core_state.h"

namespace odrig {
const char kBrightnessFile[] = "brightness.txt";
const char kBrightnessPart[] = "brightness.part";
const uint32_t kBrightnessLines = 512;
bool brightness_supported(const Core &core);
int brightness_saved(const Core &core, uint32_t position);
uint8_t brightness_selected(const Core &core);
void brightness_start(Core &core);
void brightness_drive_found(Core &core);
uint32_t brightness_change(Core &core, uint32_t id, int value, Reply &reply);
}
#endif
