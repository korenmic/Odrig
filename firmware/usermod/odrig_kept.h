// The latest reason text the player logged, kept in memory that a software or watchdog
// reset leaves as it was and a power cut clears: a record with a mark, the text's length
// and a CRC-32 of the length and the text. Nothing of it is written to flash or to a card.
// The code knows nothing of the chip, so that the suite runs it on a computer.
#pragma once

#include <stddef.h>
#include <stdint.h>

struct OdrigKept {
  uint32_t mark;
  uint32_t crc;
  uint16_t length;
  char text[96];
};

namespace OdrigKeep {

// The mark of a record that was written.
const uint32_t MARK = 0x6b64726fu;

// The CRC-32 of zlib over the two bytes of the length, low first, and the text.
inline uint32_t crcOf(const OdrigKept &kept) {
  uint32_t crc = 0xFFFFFFFFu;
  const uint8_t length[2] = {(uint8_t)(kept.length & 0xFF), (uint8_t)(kept.length >> 8)};
  for (size_t at = 0; at < 2 + (size_t)kept.length; ++at) {
    crc ^= at < 2 ? length[at] : (uint8_t)kept.text[at - 2];
    for (int bit = 0; bit < 8; ++bit) {
      crc = (crc >> 1) ^ (0xEDB88320u & (0u - (crc & 1u)));
    }
  }
  return crc ^ 0xFFFFFFFFu;
}

// Keeps a text, cut to 95 bytes, in place of the one before.
inline void put(OdrigKept &kept, const char *text) {
  size_t length = 0;
  while (text[length] != 0 && length < sizeof(kept.text) - 1) {
    kept.text[length] = text[length];
    ++length;
  }
  kept.text[length] = 0;
  kept.length = (uint16_t)length;
  kept.crc = crcOf(kept);
  kept.mark = MARK;
}

// The text of a sound record into `out`, which has room for 96 bytes, with the record
// cleared; false, with the record cleared too, for a record that is absent or damaged.
inline bool take(OdrigKept &kept, char *out) {
  const bool sound = kept.mark == MARK && kept.length < sizeof(kept.text) && kept.crc == crcOf(kept);
  for (size_t at = 0; sound && at < kept.length; ++at) {
    out[at] = kept.text[at];
  }
  if (sound) out[kept.length] = 0;
  kept.mark = 0;
  kept.crc = 0;
  kept.length = 0;
  for (size_t at = 0; at < sizeof(kept.text); ++at) {
    kept.text[at] = 0;
  }
  return sound;
}

}  // namespace OdrigKeep
