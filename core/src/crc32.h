#ifndef ODRIG_CRC32_H
#define ODRIG_CRC32_H

#include <stdint.h>

namespace odrig {

// The CRC-32 of zlib, PNG and Ethernet: the reflected polynomial 0xEDB88320, a start value
// of all ones, and the final value inverted. It is computed four bits at a time.
const uint32_t kCrcStart = 0xFFFFFFFFu;

const uint32_t kCrcTable[16] = {
    0x00000000u, 0x1DB71064u, 0x3B6E20C8u, 0x26D930ACu, 0x76DC4190u, 0x6B6B51F4u, 0x4DB26158u, 0x5005713Cu,
    0xEDB88320u, 0xF00F9344u, 0xD6D6A3E8u, 0xCB61B38Cu, 0x9B64C2B0u, 0x86D3D2D4u, 0xA00AE278u, 0xBDBDF21Cu,
};

// Takes one byte into a running CRC-32, which begins as kCrcStart.
inline uint32_t crc_add(uint32_t crc, uint8_t byte) {
    crc = kCrcTable[(crc ^ byte) & 0x0Fu] ^ (crc >> 4);
    crc = kCrcTable[(crc ^ (byte >> 4)) & 0x0Fu] ^ (crc >> 4);
    return crc;
}

// The CRC-32 a running value stands for.
inline uint32_t crc_value(uint32_t crc) {
    return crc ^ 0xFFFFFFFFu;
}

}  // namespace odrig

#endif
