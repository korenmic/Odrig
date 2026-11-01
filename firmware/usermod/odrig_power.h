#ifndef ODRIG_POWER_H
#define ODRIG_POWER_H

// Caller holds the power guard. Published visibility is feedback, not an operator request.
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
  void stateChange(bool observed, bool initial) {
    bool on = false;
    if (take(observed, initial, &on)) {
      queued_ = true;
      queuedOn_ = on;
    }
  }
  bool takeQueued(bool *on) {
    if (!queued_) return false;
    queued_ = false;
    *on = queuedOn_;
    return true;
  }

 private:
  bool known_ = false;
  bool on_ = false;
  bool pending_ = false;
  bool wanted_ = false;
  bool queued_ = false;
  bool queuedOn_ = false;
};

#endif
