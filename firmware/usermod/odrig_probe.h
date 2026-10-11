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

// How long one request for a refresh took. Called by the task that makes the requests.
void polled(uint32_t poll_us);

// Around one send. After the show the time of the send is kept, the fill and the show
// together, and the wire time begins: a timer looks every tenth of a millisecond whether
// the parallel driver can take data again. Then some of the outputs are read back, each
// in its turn, and before the next fill the same outputs are compared with what they
// held: a difference means that something else wrote to them. Before the outputs are
// shown, when they can all take data, the chip's pulse counter is put on the pin of one
// output, each output in its turn.
void beforeFill();
void beforeShow();
void afterShow(uint64_t now_ms, uint32_t send_us);

// One byte from the port. Bytes at the start of a line are held back for as long as they
// are a beginning of `#probe` and a newline; the complete line is answered here, and every
// other byte is handed to `pass`, in order.
void feed(uint8_t byte, void (*pass)(uint8_t byte));

}  // namespace OdrigProbe

#endif
