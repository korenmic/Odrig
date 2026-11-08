#ifndef ODRIG_POWER_H
#define ODRIG_POWER_H

// Caller holds the core lock. Published visibility is feedback, not an operator request.
class OdrigPower {
 public:
  void publish(bool on) { known_ = true; on_ = on; }
  bool on() const { return on_; }
  void explicitRequest(bool on) { pending_ = true; wanted_ = on; }
  bool take(bool observed, bool initial, bool *on) {
    const bool explicitOn = pending_;
    pending_ = false;
    if (initial || (!explicitOn && (!known_ || observed == on_))) return false;
    *on = explicitOn ? wanted_ : observed;
    return true;
  }

 private:
  bool known_ = false;
  bool on_ = false;
  bool pending_ = false;
  bool wanted_ = false;
};

#endif
