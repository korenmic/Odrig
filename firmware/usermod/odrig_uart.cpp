#include "odrig_uart.h"

#include "wled.h"

#include "odrig_core.h"
#include "odrig_files.h"
#include "odrig_log.h"

namespace {

const unsigned long BITS_PER_SECOND = 115200;
const int BYTES_PER_PASS = 256;
const size_t RECEIVE_QUEUE = 4096;
// The queue of what is written, so that a reply or a line of the log is taken at once.
// A line of the log is written only when there is room for it and for what the queue
// keeps beside each write.
const size_t SEND_QUEUE = 2048;
const int WRITE_MARGIN = 32;

// The line that is arriving: its characters so far, and whether its line feed has come.
char arriving[ODRIG_LINE_MAX + 1];
size_t arrived = 0;
bool ended = false;

// Writes the log's waiting lines, each whole, as many as the UART takes now without
// waiting.
void writeLog() {
  static char line[OdrigLog::LINE_ROOM];
  for (;;) {
    const int space = Serial0.availableForWrite() - WRITE_MARGIN;
    if (space <= 0) return;
    const size_t length = OdrigLog::take(line, sizeof(line), (size_t)space);
    if (length == 0) return;
    Serial0.write((const uint8_t *)line, length);
  }
}

}  // namespace

void OdrigUart::begin() {
  Serial0.setRxBufferSize(RECEIVE_QUEUE);
  Serial0.setTxBufferSize(SEND_QUEUE);
  Serial0.begin(BITS_PER_SECOND);
}

void OdrigUart::poll(Line line) {
  writeLog();
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
