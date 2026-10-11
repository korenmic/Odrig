// WLED's LED outputs under the usermod: one output for each leg, held against everything
// else in WLED that draws, and filled with the legs' LED data.
#pragma once

#include <stddef.h>
#include <stdint.h>

// One leg: its number, its data pin, its number of LEDs, and its LED data, three bytes
// for each LED: red, green, blue, in chain order.
struct OdrigLeg {
  uint16_t leg;
  uint16_t pin;
  uint32_t led_count;
  const uint8_t *rgb;
};

// Where the legs come from.
struct OdrigLegSource {
  uint32_t (*count)();
  bool (*leg)(uint32_t index, OdrigLeg *out);
};

namespace OdrigLeds {

// Names the source of the legs. Called once, before anything else.
void source(const OdrigLegSource &legs);

// Keeps WLED in its live mode and keeps the outputs those of the legs. Called from
// setup() and at the start of every loop().
void hold();

// Whether WLED's outputs are the ones apply() makes.
bool matches();

// Replaces WLED's outputs with one output for each leg. With no legs it leaves them.
void apply();

// Sends the legs' LED data to the outputs: LED n of leg i to position n of output i.
void send();

// Sends one dark picture through WLED's own path.
void dark();

// The number of legs, and how many of their outputs work.
uint32_t legs();
uint32_t working();

// The outputs in words: `<working>/<legs>`, and ` leg <n> pin <p>` for each output that
// does not work. The text is renewed by hold().
const char *summary();

}  // namespace OdrigLeds
