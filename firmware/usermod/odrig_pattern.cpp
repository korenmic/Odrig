#include "odrig_pattern.h"

namespace {

const uint32_t LEG_COUNT = 10;
const uint32_t LEDS_PER_LEG = 180;
const uint64_t REFRESH_MS = 20;

uint8_t colours[LEG_COUNT][LEDS_PER_LEG * 3];
bool started = false;
uint64_t firstMs = 0;
uint64_t nextTick = 0;

uint32_t count() { return LEG_COUNT; }

bool leg(uint32_t index, OdrigLeg *out) {
  if (index >= LEG_COUNT) return false;
  out->leg = (uint16_t)(index + 1);
  out->pin = (uint16_t)(index + 1);
  out->led_count = LEDS_PER_LEG;
  out->rgb = colours[index];
  return true;
}

}  // namespace

// Red rises along the leg from 1 to 40, green runs through 0 to 40 again and again from a
// start of the leg's own, and blue is the same along a leg and differs from leg to leg.
void OdrigPattern::begin() {
  for (uint32_t l = 0; l < LEG_COUNT; l++) {
    for (uint32_t n = 0; n < LEDS_PER_LEG; n++) {
      uint8_t *rgb = &colours[l][n * 3];
      rgb[0] = (uint8_t)(1 + (n * 39) / (LEDS_PER_LEG - 1));
      rgb[1] = (uint8_t)((n + l * 7) % 41);
      rgb[2] = (uint8_t)(l * 4);
    }
  }
}

bool OdrigPattern::poll(uint64_t now_ms) {
  if (!started) {
    started = true;
    firstMs = now_ms;
    nextTick = 0;
  }
  const uint64_t tick = (now_ms - firstMs) / REFRESH_MS;
  if (tick < nextTick) return false;
  nextTick = tick + 1;
  return true;
}

OdrigLegSource OdrigPattern::legs() {
  OdrigLegSource source = {count, leg};
  return source;
}
