#include "odrig_uart.h"

#include "wled.h"

#include "odrig_core.h"
#include "odrig_files.h"

namespace {

const unsigned long BITS_PER_SECOND = 115200;
const int BYTES_PER_PASS = 256;
const size_t RECEIVE_QUEUE = 4096;

// The line that is arriving: its characters so far, and whether its line feed has come.
char arriving[ODRIG_LINE_MAX + 1];
size_t arrived = 0;
bool ended = false;

}  // namespace

void OdrigUart::begin() {
  Serial0.setRxBufferSize(RECEIVE_QUEUE);
  Serial0.begin(BITS_PER_SECOND);
}

void OdrigUart::poll(Line line) {
  for (int taken = 0; taken < BYTES_PER_PASS; taken++) {
    if (ended) {
      if (OdrigFiles::holding()) return;
      // The reply's room is not on the stack.
      static char reply[ODRIG_REPLY_MAX];
      const size_t length = line(arriving, arrived, reply, sizeof(reply));
      if (length > 0) Serial0.write((const uint8_t *)reply, length);
      arrived = 0;
      ended = false;
    }
    if (Serial0.available() <= 0) return;
    const int byte = Serial0.read();
    if (byte < 0) return;
    if (byte == '\n') {
      ended = true;
    } else if (arrived < sizeof(arriving)) {
      arriving[arrived++] = (char)byte;
    }
  }
}
