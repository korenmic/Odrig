#pragma once

#include <algorithm>
#include <stdint.h>
#include <stdio.h>
#include <memory>
#include <vector>

const unsigned OUTPUT_MAX_PINS = 5;
const uint8_t TYPE_WS2812_RGB = 22;
const uint8_t COL_ORDER_GRB = 1;
const uint8_t RGBW_MODE_MANUAL_ONLY = 0;
const uint8_t LED_MILLIAMPS_DEFAULT = 55;
const uint32_t MAX_LEDS = 4000;
const int REALTIME_OVERRIDE_NONE = 0;
const int REALTIME_MODE_GENERIC = 1;
const uint32_t BLACK = 0;

inline uint32_t RGBW32(uint8_t r, uint8_t g, uint8_t b, uint8_t w) {
  return (uint32_t(w) << 24) | (uint32_t(r) << 16) | (uint32_t(g) << 8) | b;
}

struct BusConfig {
  uint8_t type, pin, order, ledMa;
  uint16_t start, length, maxMa;
  BusConfig(uint8_t t, const uint8_t *p, uint16_t s, uint16_t n,
            uint8_t co, bool, int, int, int, uint8_t ma, uint16_t maximum, int)
      : type(t), pin(p[0]), order(co), ledMa(ma), start(s), length(n), maxMa(maximum) {}
};

extern bool transferBusy;
extern bool configurationFails;

class Bus {
 public:
  explicit Bus(const BusConfig &value) : config(value), pixels(value.length, 0), valid(!configurationFails) {}
  bool isOk() const { return valid; }
  void begin() {}
  uint8_t getType() const { return config.type; }
  uint16_t getStart() const { return config.start; }
  uint16_t getLength() const { return config.length; }
  void getPins(uint8_t *out) const { out[0] = config.pin; }
  void setPixelColor(uint32_t n, uint32_t colour) { if (isOk()) pixels.at(n) = colour; }
  static void setCCT(int) {}
  BusConfig config;
  std::vector<uint32_t> pixels;
  bool valid;
};

struct ColorOrderMap { void reset() {} };
namespace BusManager {
uint16_t ablMilliampsMax();
size_t getNumBusses();
Bus *getBus(size_t n);
ColorOrderMap &getColorOrderMap();
void setBrightness(uint8_t brightness);
void show();
bool canAllShow();
}

struct Strip {
  void finalizeInit();
  void makeAutoSegments() {}
  void fill(uint32_t colour);
  void show();
};

extern std::vector<BusConfig> busConfigs;
extern Strip strip;
extern int realtimeOverride;
extern int realtimeMode;
extern bool useMainSegmentOnly;
extern bool doInitBusses;
void realtimeLock(uint32_t, int mode);
