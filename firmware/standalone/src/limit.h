// The limit on LED current, with the arithmetic of WLED's limiter: the current of a
// refresh is estimated from the colours, and when the estimate is above what the limit
// allows, every LED is dimmed. This code knows nothing of the chip, so that it is tested
// on a computer.
#pragma once

#include <stdint.h>

// What the estimate takes for one LED at full white, for one LED at rest, and for the
// chip itself, in milliamps.
const uint32_t ODRIG_LED_MA = 55;
const uint32_t ODRIG_REST_MA = 1;
const uint32_t ODRIG_CHIP_MA = 120;

// The colours of one output as they are about to be sent: three bytes for each LED. The
// order of the three does not matter.
struct OdrigLimitOutput {
  uint8_t *bytes;
  uint32_t leds;
};

struct OdrigLimited {
  // What the limit allows the LEDs: the maximum less the chip's share, or 0 when the
  // maximum is not above that share, and 0 without a limit.
  uint16_t limit_ma;
  // The estimate for this refresh after dimming; 0 without a limit.
  uint16_t used_ma;
  // The estimate reached what the limit allows.
  bool limited;
};

// Applies the limit to the outputs of one refresh, dimming their colours in place when
// the estimate is above what the maximum allows. A maximum of 0 means no limit: nothing
// is estimated and nothing changes.
//
// The estimate of an output is the sum of all its bytes times 55, divided by 765, plus
// one for each LED. What is allowed is the maximum less 120, or 1 when the maximum is
// 120 or less. When the allowed is above the number of all LEDs and the estimate above
// the allowed, the level is allowed * 255 / estimate + 1. When the allowed is not above
// the number of all LEDs, the level is 1. With a level below 255, each byte of an LED
// that is not black becomes (byte * level + 127) / 256, with its lowest bit set when
// the byte was above a quarter of the LED's largest byte, plus 1.
OdrigLimited odrigLimit(OdrigLimitOutput *outputs, uint32_t count, uint16_t maximum_ma);
