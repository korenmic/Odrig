#include "outputs.h"

#include <NeoPixelBus.h>
#include <string.h>

#include "odrig_routing.h"

namespace {

typedef NeoPixelBus<NeoGrbFeature, NeoEsp32RmtNWs2812xMethod> RmtBus;
typedef NeoPixelBus<NeoGrbFeature, NeoEsp32LcdX16Ws2812xMethod> ParallelBus;

// One output behind what both kinds of bus offer.
struct Output {
  virtual ~Output() {}
  virtual uint8_t *bytes() = 0;
  virtual bool canShow() = 0;
  virtual void show() = 0;
};

template <typename Bus>
struct OutputOn : Output {
  template <typename... Arguments>
  explicit OutputOn(Arguments... arguments) : bus(arguments...) { bus.Begin(); }
  uint8_t *bytes() override { return bus.Pixels(); }
  bool canShow() override { return bus.CanShow(); }
  void show() override {
    bus.Dirty();
    bus.Show();
  }
  Bus bus;
};

const odrig_leg *legsNow = nullptr;
uint32_t legCount = 0;
Output *outputs[OdrigOutputs::MOST];
uint16_t physicalPins[OdrigOutputs::MOST];
uint32_t physicalCounts[OdrigOutputs::MOST];

// The pins of this board that can carry a signal: not 19 and 20, which are the USB
// port, not 22 to 32, which are not there or carry the flash, and not 33 to 37, which
// carry the external memory.
bool usable(uint32_t pin) { return pin <= 18 || pin == 21 || (pin >= 38 && pin <= 48); }

}  // namespace

void OdrigOutputs::begin(const odrig_leg *legs, uint32_t count) {
  legsNow = legs;
  legCount = count;
  for (uint32_t i = 0; i < MOST; i++) {
    outputs[i] = nullptr;
    physicalPins[i] = i < count ? legs[i].pin : 0;
    physicalCounts[i] = i < count ? legs[i].led_count : 0;
    if (i >= count || !usable(legs[i].pin) || legs[i].led_count == 0 || legs[i].led_count > UINT16_MAX) continue;
    const uint16_t leds = (uint16_t)legs[i].led_count;
    const uint8_t pin = (uint8_t)legs[i].pin;
    if (i < ON_RMT) {
      outputs[i] = new OutputOn<RmtBus>(leds, pin, (NeoBusChannel)i);
    } else {
      outputs[i] = new OutputOn<ParallelBus>(leds, pin);
    }
  }
}

uint32_t OdrigOutputs::legs() { return legCount; }

uint32_t OdrigOutputs::working() {
  uint32_t found = 0;
  for (uint32_t i = 0; i < MOST; i++) found += outputs[i] != nullptr ? 1 : 0;
  return found;
}

bool OdrigOutputs::ok(uint32_t index) { return index < MOST && outputs[index] != nullptr; }

uint32_t OdrigOutputs::pin(uint32_t index) { return index < legCount && index < MOST ? physicalPins[index] : 0; }

uint32_t OdrigOutputs::leds(uint32_t index) { return index < legCount && index < MOST ? physicalCounts[index] : 0; }

const char *OdrigOutputs::driver(uint32_t index) {
  if (!ok(index)) return "none";
  return index < ON_RMT ? "rmt" : "parallel";
}

uint8_t *OdrigOutputs::bytes(uint32_t index) { return ok(index) ? outputs[index]->bytes() : nullptr; }

// The LEDs take their colours in the order green, red, blue.
void OdrigOutputs::fill() {
  for (uint32_t i = 0; i < MOST; i++) {
    if (outputs[i] == nullptr) continue;
    const odrig_leg *leg = OdrigRouting::onPin(legsNow, legCount, physicalPins[i]);
    if (leg == nullptr || leg->led_count != physicalCounts[i]) {
      memset(outputs[i]->bytes(), 0, physicalCounts[i] * 3u);
      continue;
    }
    const uint8_t *rgb = leg->rgb;
    uint8_t *grb = outputs[i]->bytes();
    for (uint32_t n = 0; n < physicalCounts[i]; n++, rgb += 3, grb += 3) {
      grb[0] = rgb[1];
      grb[1] = rgb[0];
      grb[2] = rgb[2];
    }
  }
}

bool OdrigOutputs::canShow() {
  for (uint32_t i = 0; i < MOST; i++) {
    if (outputs[i] != nullptr && !outputs[i]->canShow()) return false;
  }
  return true;
}

void OdrigOutputs::show() {
  for (uint32_t i = 0; i < MOST; i++) {
    if (outputs[i] != nullptr) outputs[i]->show();
  }
}
