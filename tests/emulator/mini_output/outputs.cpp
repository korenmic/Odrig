#include <stdlib.h>
#include <string.h>
#include <string>

#include "wled.h"
#include "odrig_leds.h"
#include "odrig_mini_output.h"

bool transferBusy = false;
bool configurationFails = false;
std::vector<BusConfig> busConfigs;
Strip strip;
int realtimeOverride = 3;
int realtimeMode = 0;
bool useMainSegmentOnly = true;
bool doInitBusses = false;

namespace {
std::vector<std::unique_ptr<Bus> > buses;
ColorOrderMap orderMap;
uint8_t brightness = 0;
bool miniature = false;
bool coreLocked = false;
bool limiterEnabled = true;
uint32_t applications = 0;
uint32_t darkFrames = 0;
uint32_t totalActiveLeds = 0;
uint8_t normalRgb[20][540];
uint8_t miniRgb[180];
uint8_t pins[20] = {1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,21,47};

void require(bool condition, const char *reason) {
  if (!condition) { fprintf(stderr, "%s\n", reason); exit(1); }
}

bool allDark() {
  for (const auto &bus : buses) for (uint32_t colour : bus->pixels) if (colour != 0) return false;
  return true;
}

uint32_t count() { return miniature ? 1 : 20; }
bool leg(uint32_t n, OdrigLeg *out) {
  if (n >= count()) return false;
  *out = OdrigLeg{static_cast<uint16_t>(n + 1), miniature ? uint16_t(1) : uint16_t(pins[n]), miniature ? 60u : 180u,
                 miniature ? miniRgb : normalRgb[n]};
  return true;
}

struct Driver {
  bool ready() const { return BusManager::canAllShow(); }
  void dark() const { require(!coreLocked, "dark owns core lock"); OdrigLeds::dark(); }
  void select(bool enabled) const { miniature = enabled; }
  bool apply() const {
    require(!coreLocked, "setup owns core lock");
    require(!transferBusy, "setup during transfer");
    OdrigLeds::apply();
    return OdrigLeds::matches() && OdrigLeds::working() == OdrigLeds::legs();
  }
};

void complete(OdrigMiniOutput &change, Driver &driver) {
  bool done = false;
  for (unsigned pass = 0; pass < 20 && !done; ++pass) {
    transferBusy = false;
    done = change.step(driver);
  }
  require(done, "transition did not finish");
}

void setup() {
  memset(normalRgb, 120, sizeof normalRgb);
  memset(miniRgb, 40, sizeof miniRgb);
  OdrigLeds::source(OdrigLegSource{count, leg});
  OdrigLeds::hold();
  OdrigLeds::hold();
  require(std::string(OdrigLeds::summary()) == "20/20", "normal summary");
  OdrigLeds::fill();
  OdrigLeds::show();
}
}

namespace BusManager {
uint16_t ablMilliampsMax() { return 850; }
size_t getNumBusses() { return buses.size(); }
Bus *getBus(size_t n) { return n < buses.size() ? buses[n].get() : nullptr; }
ColorOrderMap &getColorOrderMap() { return orderMap; }
void setBrightness(uint8_t value) { brightness = value; }
bool canAllShow() { return !transferBusy; }
void show() {
  require(!transferBusy, "show during transfer");
  totalActiveLeds = 0;
  for (const auto &bus : buses) if (bus->isOk()) totalActiveLeds += bus->getLength();
  if (allDark()) ++darkFrames;
  transferBusy = totalActiveLeds != 0;
}
}

void Strip::finalizeInit() {
  require(!coreLocked && !transferBusy, "locked or busy reconfiguration");
  require(allDark(), "old outputs were not cleared");
  ++applications;
  buses.clear();
  for (const BusConfig &config : busConfigs) buses.emplace_back(new Bus(config));
}
void Strip::fill(uint32_t colour) {
  for (auto &bus : buses) for (uint32_t &pixel : bus->pixels) pixel = colour;
}
void Strip::show() { BusManager::show(); }
void realtimeLock(uint32_t, int mode) { realtimeMode = mode; }

int main(int argc, char **argv) {
  require(argc == 2, "one case required");
  if (strcmp(argv[1], "mapping") == 0) std::swap(pins[0], pins[19]);
  setup();
  Driver driver;
  OdrigMiniOutput change;
  require(change.begin(7, true), "request not taken");
  require(!change.begin(8, false), "stacked setup allowed");
  require(!change.step(driver), "completed during old transfer");
  require(applications == 1, "configured before old transfer drained");
  if (strcmp(argv[1], "wait") == 0) {
    transferBusy = false;
    require(!change.step(driver), "ack before old clear");
    require(transferBusy, "old clear not sent");
    require(!change.step(driver), "ack during old clear");
    transferBusy = false;
    change.step(driver);
    transferBusy = true;
    require(!change.step(driver), "ack while transfer resumed");
    require(applications == 1, "reconfigured while transfer resumed");
  }
  configurationFails = strcmp(argv[1], "failure") == 0;
  complete(change, driver);
  require(change.revision() == 7 && change.enabled(), "lost request identity");
  require(change.success() != configurationFails, "wrong setup result");
  require(allDark(), "new outputs were not cleared");
  require(buses.size() == 1 && buses[0]->config.pin == 1 && buses[0]->config.length == 60, "mini pin or length");
  require(buses[0]->config.order == COL_ORDER_GRB && buses[0]->config.ledMa == 55, "colour or current model");
  require(buses[0]->config.maxMa == 850 && limiterEnabled, "current limiter bypassed");
  require(brightness == 255, "driver rescales core RGB");
  change.finish();
  if (strcmp(argv[1], "summary") == 0) {
    OdrigLeds::hold();
    require(std::string(OdrigLeds::summary()) == "1/1", "stale output summary after switch");
  }
  if (!configurationFails) {
    OdrigLeds::fill();
    OdrigLeds::show();
    require(totalActiveLeds == 60 && buses[0]->pixels[0] == RGBW32(40,40,40,0), "mini frame data");
  }
  transferBusy = false;
  configurationFails = false;
  const bool restoreFails = strcmp(argv[1], "restore-failure") == 0;
  if (restoreFails) {
    configurationFails = true;
    require(change.begin(8, false), "failed restoration not taken");
    complete(change, driver);
    require(!change.success() && allDark(), "failed restoration was not dark");
    change.finish();
    configurationFails = false;
    require(change.begin(9, true), "miniature retry not taken");
    complete(change, driver);
    require(change.success(), "miniature retry failed");
    change.finish();
  }
  require(change.begin(restoreFails ? 10 : 8, false), "retry or restore refused");
  complete(change, driver);
  require(change.success() && !change.enabled(), "restore failed");
  require(buses.size() == 20 && allDark(), "normal outputs not restored dark");
  for (size_t n = 0; n < buses.size(); ++n) {
    require(buses[n]->config.pin == pins[n] && buses[n]->config.length == 180, "normal routing changed");
  }
  change.finish();
  OdrigLeds::fill();
  OdrigLeds::show();
  require(totalActiveLeds == 3600 && buses[19]->pixels[179] == RGBW32(120,120,120,0), "normal frame not restored");
  require(darkFrames >= 4, "missing transition clears");
  printf("{\"ok\":true,\"mini_leds\":60,\"normal_leds\":3600,\"dark_frames\":%u}\n", darkFrames);
}
