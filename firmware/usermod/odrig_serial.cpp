#include "odrig_serial.h"

#include "wled.h"

#include "hal/usb_serial_jtag_ll.h"

#include "odrig_core.h"
#include "odrig_files.h"

#ifdef ODRIG_PROBE
#include "odrig_probe.h"
#endif

namespace {

const int BYTES_PER_PASS = 256;
const uint32_t ASK_AGAIN_MS = 2;
// The port keeps what it received in a queue until a pass takes it. A line may have
// 2,048 characters and arrive in one piece while a pass is held back, so the queue has
// room for two of them.
const size_t RECEIVE_QUEUE = 4096;

int emptyBuffer = 0;
uint32_t lastAsked = 0;

// The port's driver hands a reply to the chip's USB unit when that unit reports that the
// computer took the packet before. It can miss that report, and then holds the reply in its
// buffer until the next byte arrives. So for as long as something waits in the buffer, the
// USB unit is asked every few milliseconds to offer the computer a packet again, which
// brings the report back.
void keepSending() {
  if (Serial.availableForWrite() >= emptyBuffer) return;
  const uint32_t now = millis();
  if (now - lastAsked < ASK_AGAIN_MS) return;
  lastAsked = now;
  usb_serial_jtag_ll_txfifo_flush();
  usb_serial_jtag_ll_ena_intr_mask(USB_SERIAL_JTAG_INTR_SERIAL_IN_EMPTY);
}

OdrigSerial::Feed feedNow = nullptr;

#ifdef ODRIG_PROBE
String longLine;
size_t longWritten = 0;

// Writes the next piece of the long line. Returns whether some of it still waits.
bool longLineWaits() {
  if (longWritten >= longLine.length()) return false;
  const int room = Serial.availableForWrite();
  if (room > 0) {
    const size_t piece = std::min((size_t)room, longLine.length() - longWritten);
    OdrigSerial::write(longLine.c_str() + longWritten, piece);
    longWritten += piece;
  }
  if (longWritten < longLine.length()) return true;
  longLine = String();
  longWritten = 0;
  return false;
}
#endif

// The bytes of this pass that wait to be handed on: at most a line, and what the probe
// build held back of a line that was not its own.
uint8_t waiting[BYTES_PER_PASS + 16];
size_t waitingBytes = 0;
// A line has been handed on since the pacing was last asked.
bool lineHandedOn = false;

// Hands the waiting bytes on in one call and writes the reply they completed. The reply
// is written after the player has returned. Its room is not on the stack.
void handOn() {
  if (waitingBytes == 0) return;
  static char reply[ODRIG_REPLY_MAX];
  const size_t length = feedNow != nullptr ? feedNow(waiting, waitingBytes, reply, sizeof(reply)) : 0;
  waitingBytes = 0;
  if (length > 0) OdrigSerial::write(reply, length);
}

// Takes one byte for the player. A line is handed on when it has ended.
void pass(uint8_t byte) {
  waiting[waitingBytes++] = byte;
  if (byte == '\n') lineHandedOn = true;
  if (byte == '\n' || waitingBytes == sizeof(waiting)) handOn();
}

}  // namespace

// The port's interrupt puts what arrives into the queue, so it is kept out while the
// queue is replaced.
void OdrigSerial::begin() {
  usb_serial_jtag_ll_disable_intr_mask(USB_SERIAL_JTAG_INTR_SERIAL_OUT_RECV_PKT);
  Serial.setRxBufferSize(RECEIVE_QUEUE);
  usb_serial_jtag_ll_ena_intr_mask(USB_SERIAL_JTAG_INTR_SERIAL_OUT_RECV_PKT);
}

void OdrigSerial::poll(Feed feed) {
  feedNow = feed;
  if (emptyBuffer == 0) emptyBuffer = Serial.availableForWrite();
  keepSending();
#ifdef ODRIG_PROBE
  if (longLineWaits()) return;
#endif
  // While the pacing holds lines back, what arrives stays in the port's queue.
  if (OdrigFiles::holding()) return;
  for (int taken = 0; taken < BYTES_PER_PASS && Serial.available() > 0; taken++) {
    const int byte = Serial.read();
    if (byte < 0) break;
#ifdef ODRIG_PROBE
    OdrigProbe::feed((uint8_t)byte, pass);
#else
    pass((uint8_t)byte);
#endif
    if (lineHandedOn) {
      lineHandedOn = false;
      if (OdrigFiles::holding()) break;
    }
  }
  handOn();
}

void OdrigSerial::write(const char *bytes, size_t length) {
  Serial.write((const uint8_t *)bytes, length);
  lastAsked = millis();
}

#ifdef ODRIG_PROBE
void OdrigSerial::writeLong(const char *bytes, size_t length) {
  longLine.concat(bytes, length);
}
#endif
