// The LED outputs of the standalone firmware: one for each leg, WS2812B on the leg's pin,
// made with the LED library. Four are on the chip's RMT driver and sixteen on its
// parallel driver, in the order of the legs.
#pragma once

#include <stdint.h>

#include "odrig_core.h"

namespace OdrigOutputs {

// The most legs that get an output, and how many of the first get RMT.
const uint32_t MOST = 20;
const uint32_t ON_RMT = 4;

// Makes the outputs for the legs, in their order. A leg beyond the twentieth gets none,
// and a leg whose pin the board cannot use gets none either; the others are made all
// the same. The legs' data must stay where it is. Called once.
void begin(const odrig_leg *legs, uint32_t count);

// The number of legs, and of the outputs that work.
uint32_t legs();
uint32_t working();

// One leg's output: whether it works, its pin, its LEDs, its driver as `rmt`, `parallel`
// or `none`, and the bytes it is about to send, three for each LED, or a null pointer
// for an output that does not work.
bool ok(uint32_t index);
uint32_t pin(uint32_t index);
uint32_t leds(uint32_t index);
const char *driver(uint32_t index);
uint8_t *bytes(uint32_t index);

// Copies each leg's data into its output. The core has applied the brightness.
void fill();

// Whether every output can take data, and sends them all.
bool canShow();
void show();

}  // namespace OdrigOutputs
