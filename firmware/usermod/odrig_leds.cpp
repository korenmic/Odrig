#include "odrig_leds.h"

#include "wled.h"

namespace {

OdrigLegSource legSource = {nullptr, nullptr};

// Room for `<working>/<legs>` and for ` leg <n> pin <p>` of each of the 32 outputs WLED
// holds at most.
char summaryText[8 + 32 * 16] = "0/0";
bool summaryIsOld = true;

bool legAt(uint32_t index, OdrigLeg *out) {
  return legSource.leg != nullptr && legSource.leg(index, out);
}

// The start and the length WLED keeps for an output: 16 bits each, and no length of 0.
uint16_t keptStart(uint32_t start) { return (uint16_t)start; }
uint16_t keptLength(uint32_t count) { return std::max((uint16_t)count, (uint16_t)1); }

// Fills WLED's list of outputs to make with one output for each leg, in the legs' order:
// WS2812B, colour order green, red, blue, on the leg's pin.
void describeOutputs() {
  busConfigs.clear();
  const uint32_t count = OdrigLeds::legs();
  uint32_t total = 0;
  for (uint32_t i = 0; i < count; i++) {
    OdrigLeg leg;
    if (legAt(i, &leg)) total += leg.led_count;
  }
  uint32_t start = 0;
  for (uint32_t i = 0; i < count; i++) {
    OdrigLeg leg;
    if (!legAt(i, &leg)) break;
    uint8_t pins[OUTPUT_MAX_PINS] = {(uint8_t)leg.pin, 255, 255, 255, 255};
    const uint32_t share = total ? ((uint32_t)BusManager::ablMilliampsMax() * leg.led_count) / total : 0;
    busConfigs.emplace_back(TYPE_WS2812_RGB, pins, keptStart(start), keptLength(leg.led_count), COL_ORDER_GRB,
                            false, 0, RGBW_MODE_MANUAL_ONLY, 0,
                            LED_MILLIAMPS_DEFAULT, (uint16_t)share, 0);
    start += leg.led_count;
  }
}

// WLED starts its outputs in order and stops at the first that does not work. The ones
// after it are started here, so that one failed output does not take the rest with it.
void startOutputsAfterAFailedOne() {
  bool failed = false;
  for (size_t i = 0; i < BusManager::getNumBusses(); i++) {
    Bus *bus = BusManager::getBus(i);
    if (!bus) continue;
    if (failed && bus->isOk()) bus->begin();
    if (!bus->isOk() || bus->getStart() + bus->getLength() > MAX_LEDS) failed = true;
  }
}

// Writes the outputs in words, for WLED's information.
void summarize() {
  const uint32_t count = OdrigLeds::legs();
  size_t length = snprintf(summaryText, sizeof(summaryText), "%u/%u", (unsigned)OdrigLeds::working(), (unsigned)count);
  for (uint32_t i = 0; i < count && length < sizeof(summaryText) - 1; i++) {
    OdrigLeg leg;
    Bus *bus = BusManager::getBus(i);
    if ((bus && bus->isOk()) || !legAt(i, &leg)) continue;
    length += snprintf(summaryText + length, sizeof(summaryText) - length, " leg %u pin %u", (unsigned)leg.leg, (unsigned)leg.pin);
  }
  summaryIsOld = false;
}

}  // namespace

void OdrigLeds::source(const OdrigLegSource &legs) { legSource = legs; }

const char *OdrigLeds::summary() { return summaryText; }

uint32_t OdrigLeds::legs() { return legSource.count != nullptr ? legSource.count() : 0; }

uint32_t OdrigLeds::working() {
  uint32_t found = 0;
  const uint32_t count = legs();
  for (uint32_t i = 0; i < count && i < BusManager::getNumBusses(); i++) {
    Bus *bus = BusManager::getBus(i);
    if (bus && bus->isOk()) found++;
  }
  return found;
}

bool OdrigLeds::matches() {
  const uint32_t count = legs();
  if (count == 0) return true;
  if (BusManager::getNumBusses() != count) return false;
  uint32_t start = 0;
  for (uint32_t i = 0; i < count; i++) {
    OdrigLeg leg;
    Bus *bus = BusManager::getBus(i);
    if (!bus || !legAt(i, &leg)) return false;
    if (bus->getType() != TYPE_WS2812_RGB || bus->getStart() != keptStart(start) || bus->getLength() != keptLength(leg.led_count)) return false;
    if (bus->isOk()) {
      uint8_t pins[OUTPUT_MAX_PINS] = {255, 255, 255, 255, 255};
      bus->getPins(pins);
      if (pins[0] != (uint8_t)leg.pin) return false;
    }
    start += leg.led_count;
  }
  return true;
}

void OdrigLeds::apply() {
  if (legs() == 0) return;
  describeOutputs();
  BusManager::getColorOrderMap().reset();
  strip.finalizeInit();
  strip.makeAutoSegments();
  startOutputsAfterAFailedOne();
  BusManager::setBrightness(255);
}

void OdrigLeds::hold() {
  if (realtimeOverride != REALTIME_OVERRIDE_NONE) realtimeOverride = REALTIME_OVERRIDE_NONE;
  if (useMainSegmentOnly) useMainSegmentOnly = false;
  if (realtimeMode != REALTIME_MODE_GENERIC) realtimeLock(65000, REALTIME_MODE_GENERIC);
  if (doInitBusses) {
    // WLED's LED settings were saved: WLED makes the outputs again in this pass of its
    // loop, from the list that is filled here.
    if (legs() != 0) describeOutputs();
    summaryIsOld = true;
  } else if (!matches()) {
    apply();
    summaryIsOld = true;
  } else if (summaryIsOld) {
    summarize();
  }
}

void OdrigLeds::fill() {
  BusManager::setBrightness(255);
  Bus::setCCT(-1);
  const uint32_t count = legs();
  for (uint32_t i = 0; i < count; i++) {
    OdrigLeg leg;
    Bus *bus = BusManager::getBus(i);
    if (!bus || !bus->isOk() || !legAt(i, &leg)) continue;
    const uint8_t *rgb = leg.rgb;
    const uint32_t length = std::min((uint32_t)bus->getLength(), leg.led_count);
    for (uint32_t n = 0; n < length; n++, rgb += 3) {
      bus->setPixelColor(n, RGBW32(rgb[0], rgb[1], rgb[2], 0));
    }
  }
}

void OdrigLeds::show() { BusManager::show(); }

void OdrigLeds::dark() {
  strip.fill(BLACK);
  strip.show();
}
