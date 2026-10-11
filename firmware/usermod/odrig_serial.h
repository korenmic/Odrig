// The USB serial port.
#pragma once

namespace OdrigSerial {

// Takes what the port has received, at most 256 bytes in one call.
void poll();

}  // namespace OdrigSerial
