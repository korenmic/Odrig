// The USB serial port: it carries bytes to the player and the player's replies back.
#pragma once

#include <stddef.h>
#include <stdint.h>

namespace OdrigSerial {

// Takes bytes for the player: what the port received in one pass, up to the end of a
// line at most. When they completed a line, the reply is put into `reply` and its length
// returned; otherwise 0. `capacity` is at least ODRIG_REPLY_MAX.
typedef size_t (*Feed)(const uint8_t *bytes, size_t length, char *reply, size_t capacity);

// Takes what the port has received, at most 256 bytes in one call, hands the bytes to
// `feed` unchanged and in order, a line at a time, and writes every reply to the port.
// It also sees to it that what was written before leaves the chip.
void poll(Feed feed);

// Writes bytes to the port.
void write(const char *bytes, size_t length);

#ifdef ODRIG_PROBE
// Takes a long line for the port. poll() writes it in the pieces the port takes without
// waiting, one piece in each call, and reads nothing from the port until all of it is
// written, so that no reply lands inside it.
void writeLong(const char *bytes, size_t length);
#endif

}  // namespace OdrigSerial
