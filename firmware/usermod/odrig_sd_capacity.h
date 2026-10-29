// A read-only FAT allocation counter. Each step consumes one sector; IO and locking
// belong to the caller. A complete result describes media unchanged during the scan.
#pragma once

#include <stdint.h>

class OdrigSdCapacity {
 public:
  void reset(uint64_t sectors) {
    media = sectors;
    partition = 0;
    limit = sectors;
    next = 0;
    freeClusters = 0;
    totalBytes = freeBytes = 0;
    phase = sectors > 0 && sectors <= UINT64_C(0x100000000) ? BOOT : FAILED;
  }

  bool pending() const { return phase == BOOT || phase == PARTITION || phase == TABLE; }
  bool known() const { return phase == DONE; }
  uint32_t sector() const { return next; }
  uint64_t total() const { return totalBytes; }
  uint64_t free() const { return freeBytes; }
  void fail() { phase = FAILED; totalBytes = freeBytes = 0; }

  void consume(const uint8_t *bytes) {
    if (!pending()) return;
    if (phase == TABLE) {
      const uint32_t width = fat32 ? 4 : 2;
      const uint32_t first = tableRead * (512 / width);
      for (uint32_t at = 0; at < 512 / width; ++at) {
        const uint32_t cluster = first + at;
        if (cluster < 2 || cluster >= clusters + 2) continue;
        const uint32_t entry = fat32 ? u32(bytes + at * width) & 0x0fffffff : u16(bytes + at * width);
        if (entry == 0) ++freeClusters;
      }
      if (++tableRead == tableNeeded) {
        freeBytes = uint64_t(freeClusters) * clusterBytes;
        phase = DONE;
      } else {
        ++next;
      }
      return;
    }
    if (u16(bytes + 510) != 0xaa55) { fail(); return; }
    const bool bpb = (bytes[0] == 0xeb || bytes[0] == 0xe9) && u16(bytes + 11) == 512;
    if (phase == PARTITION || bpb) {
      if (!bpb || !geometry(bytes)) fail();
      return;
    }
    // Refuse ambiguous/multi-volume media instead of counting a different volume
    // from the one FatFs selected. Extended partitions and GPT are not guessed.
    unsigned found = 0;
    for (unsigned at = 0; at < 4; ++at) {
      const uint8_t *entry = bytes + 446 + at * 16;
      const uint8_t type = entry[4];
      const uint32_t start = u32(entry + 8), length = u32(entry + 12);
      if (type == 0 && start == 0 && length == 0) continue;
      if (++found > 1 || (entry[0] != 0 && entry[0] != 0x80) || !fatPartition(type) ||
          start == 0 || length == 0 || uint64_t(start) + length > media) { fail(); return; }
      partition = start;
      limit = length;
    }
    if (found != 1) { fail(); return; }
    next = partition;
    phase = PARTITION;
  }

 private:
  enum Phase { FAILED, BOOT, PARTITION, TABLE, DONE } phase = FAILED;
  uint64_t media = 0, limit = 0, clusterBytes = 0, totalBytes = 0, freeBytes = 0;
  uint32_t partition = 0, next = 0, clusters = 0, freeClusters = 0;
  uint32_t tableRead = 0, tableNeeded = 0;
  bool fat32 = false;

  static uint16_t u16(const uint8_t *p) { return uint16_t(p[0]) | uint16_t(p[1]) << 8; }
  static uint32_t u32(const uint8_t *p) { return uint32_t(u16(p)) | uint32_t(u16(p + 2)) << 16; }
  static bool fatPartition(uint8_t type) {
    return type == 0x04 || type == 0x06 || type == 0x0e || type == 0x0b || type == 0x0c ||
           type == 0x14 || type == 0x16 || type == 0x1e || type == 0x1b || type == 0x1c;
  }

  bool geometry(const uint8_t *b) {
    const uint32_t perCluster = b[13], reserved = u16(b + 14), fats = b[16];
    const uint32_t roots = u16(b + 17), smallFat = u16(b + 22);
    const uint32_t sectors = u16(b + 19) ? u16(b + 19) : u32(b + 32);
    const uint32_t fatSectors = smallFat ? smallFat : u32(b + 36);
    if (perCluster == 0 || perCluster > 128 || (perCluster & (perCluster - 1)) != 0 ||
        reserved == 0 || fats == 0 || fats > 2 || fatSectors == 0 || sectors == 0 || sectors > limit) return false;
    const uint64_t overhead = uint64_t(reserved) + uint64_t(fats) * fatSectors + (uint64_t(roots) * 32 + 511) / 512;
    if (overhead >= sectors) return false;
    const uint64_t count = (sectors - overhead) / perCluster;
    if (count < 4085 || count >= 0x0ffffff5) return false;
    fat32 = count >= 65525;
    if (fat32 ? (smallFat != 0 || roots != 0 || u16(b + 42) != 0) : (smallFat == 0 || roots == 0)) return false;
    uint32_t active = 0;
    if (fat32) {
      const uint16_t flags = u16(b + 40);
      const uint32_t root = u32(b + 44);
      if ((flags & ~0x008f) != 0 || root < 2 || root >= count + 2) return false;
      if (flags & 0x80) active = flags & 0x0f;
      if (active >= fats) return false;
    }
    clusters = uint32_t(count);
    const uint64_t needed = ((count + 2) * (fat32 ? 4 : 2) + 511) / 512;
    if (needed > fatSectors) return false;
    const uint64_t tableStart = uint64_t(partition) + reserved + uint64_t(active) * fatSectors;
    if (tableStart + needed > media || tableStart + needed > UINT64_C(0x100000000)) return false;
    next = uint32_t(tableStart);
    tableRead = freeClusters = 0;
    tableNeeded = uint32_t(needed);
    clusterBytes = uint64_t(perCluster) * 512;
    totalBytes = count * clusterBytes;
    phase = TABLE;
    return true;
  }
};
