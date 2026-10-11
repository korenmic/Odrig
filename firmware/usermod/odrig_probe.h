// The probe build's measurements, reported on the port in answer to the line `#probe`.
// This code is in the probe build only.
#pragma once

#ifdef ODRIG_PROBE

#include <stdint.h>

namespace OdrigProbe {

// How long the start of the player took, and where the report gets the reason the show is
// invalid: a text, or a null pointer for a valid show.
void started(uint32_t start_ms, const char *(*error)());

// One pass of loop().
void pass(uint64_t now_ms);

// How long one request for a refresh took.
void polled(uint32_t poll_us);

// Around one send: before it the outputs are compared with what they held after the
// send before; after it what they hold is kept.
void beforeSend();
void afterSend(uint64_t now_ms, uint32_t send_us);

// One byte from the port. Bytes at the start of a line are held back for as long as they
// are a beginning of `#probe` and a newline; the complete line is answered here, and every
// other byte is handed to `pass`, in order.
void feed(uint8_t byte, void (*pass)(uint8_t byte));

}  // namespace OdrigProbe

#endif
