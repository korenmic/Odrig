#pragma once

#include <stdint.h>

class OdrigMiniOutput {
 public:
  bool begin(uint32_t revision, bool enabled) {
    if (busy()) return false;
    revision_ = revision;
    enabled_ = enabled;
    success_ = false;
    phase_ = ClearOld;
    return true;
  }

  bool busy() const { return phase_ != Idle; }
  uint32_t revision() const { return revision_; }
  bool enabled() const { return enabled_; }
  bool success() const { return success_; }
  void finish() { phase_ = Idle; }

  // The caller keeps the refresh producer paused. No driver operation owns the
  // core lock, and each pass performs at most one output operation.
  template <typename Driver>
  bool step(Driver &driver) {
    switch (phase_) {
      case ClearOld:
        if (driver.ready()) {
          driver.dark();
          phase_ = WaitOld;
        }
        break;
      case WaitOld:
        if (driver.ready()) phase_ = Configure;
        break;
      case Configure:
        if (!driver.ready()) break;
        driver.select(enabled_);
        success_ = driver.apply();
        phase_ = ClearNew;
        break;
      case ClearNew:
        if (driver.ready()) {
          driver.dark();
          phase_ = WaitNew;
        }
        break;
      case WaitNew:
        if (driver.ready()) phase_ = Complete;
        break;
      case Complete:
      case Idle:
        break;
    }
    return phase_ == Complete;
  }

 private:
  enum Phase { Idle, ClearOld, WaitOld, Configure, ClearNew, WaitNew, Complete };
  Phase phase_ = Idle;
  uint32_t revision_ = 0;
  bool enabled_ = false;
  bool success_ = false;
};
