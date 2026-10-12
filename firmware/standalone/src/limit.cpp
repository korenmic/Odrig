#include "limit.h"

namespace {

const uint32_t FULL_WHITE = 3 * 255;
const uint32_t NO_DIMMING = 255;

void dim(OdrigLimitOutput &output, uint32_t level) {
  uint8_t *led = output.bytes;
  for (uint32_t n = 0; n < output.leds; n++, led += 3) {
    const uint8_t a = led[0], b = led[1], c = led[2];
    if (a == 0 && b == 0 && c == 0) continue;
    const uint8_t largest = a > b ? (a > c ? a : c) : (b > c ? b : c);
    const uint8_t kept = (uint8_t)((largest >> 2) + 1);
    for (uint32_t i = 0; i < 3; i++) {
      const uint8_t was = led[i];
      led[i] = (uint8_t)(((was * level + 127) >> 8) | (was > kept ? 1 : 0));
    }
  }
}

}  // namespace

OdrigLimited odrigLimit(OdrigLimitOutput *outputs, uint32_t count, uint16_t maximum_ma) {
  OdrigLimited result = {0, 0, false};
  if (maximum_ma == 0) return result;

  uint32_t estimate = 0, leds = 0;
  for (uint32_t i = 0; i < count; i++) {
    uint64_t sum = 0;
    const uint64_t bytes = (uint64_t)outputs[i].leds * 3;
    for (uint64_t n = 0; n < bytes; n++) sum += outputs[i].bytes[n];
    estimate += (uint32_t)(sum * ODRIG_LED_MA / FULL_WHITE) + outputs[i].leds * ODRIG_REST_MA;
    leds += outputs[i].leds;
  }

  const uint32_t allowed = maximum_ma > ODRIG_CHIP_MA ? maximum_ma - ODRIG_CHIP_MA : 1;
  uint32_t level = NO_DIMMING;
  if (allowed > leds) {
    if (estimate > allowed) {
      level = allowed * 255 / estimate + 1;
      estimate = allowed;
    }
  } else {
    level = 1;
    estimate = leds;
  }
  if (level < NO_DIMMING) {
    for (uint32_t i = 0; i < count; i++) dim(outputs[i], level);
  }

  result.limit_ma = (uint16_t)(maximum_ma > ODRIG_CHIP_MA ? maximum_ma - ODRIG_CHIP_MA : 0);
  result.used_ma = (uint16_t)(estimate > 0xFFFF ? 0xFFFF : estimate);
  result.limited = result.used_ma >= result.limit_ma;
  return result;
}
