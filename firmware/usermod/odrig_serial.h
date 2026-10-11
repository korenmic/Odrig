// The USB serial port: it carries bytes to the player and the player's replies back.
#pragma once

#include <stddef.h>
#include <stdint.h>

namespace OdrigSerial {

// Takes one byte for the player. When the byte completed a line, the reply is put into
// `reply` and its length returned; otherwise 0. `capacity` is at least ODRIG_REPLY_MAX.
typedef size_t (*Feed)(uint8_t byte, char *reply, size_t capacity);

// Takes what the port has received, at most 256 bytes in one call, hands every byte to
// `feed` unchanged and in order, and writes every reply to the port. It also sees to it
// that what was written before leaves the chip.
void poll(Feed feed);

// Writes bytes to the port.
void write(const char *bytes, size_t length);

}  // namespace OdrigSerial
