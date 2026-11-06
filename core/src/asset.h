#ifndef ODRIG_ASSET_H
#define ODRIG_ASSET_H

#include <stddef.h>
#include <stdint.h>
#include <string.h>

#include "odrig_core.h"

namespace odrig {

// Bytes the core holds, read as a host reads a file: the diagonal's ODRG file and the
// installation's mapping file. A reader opens them under any name.
struct Asset {
    const uint8_t *bytes;
    uint32_t size;
    uint32_t offset;
};

inline int asset_open(void *ctx, const char *) {
    static_cast<Asset *>(ctx)->offset = 0;
    return 1;
}

inline int32_t asset_read(void *ctx, uint8_t *out, size_t capacity) {
    Asset &asset = *static_cast<Asset *>(ctx);
    size_t count = asset.size - asset.offset;
    if (count > capacity) count = capacity;
    memcpy(out, asset.bytes + asset.offset, count);
    asset.offset += static_cast<uint32_t>(count);
    return static_cast<int32_t>(count);
}

inline void asset_close(void *) {}

// A host that has this asset as its one file and nothing else.
inline odrig_host asset_host(Asset &asset) {
    odrig_host host = {};
    host.ctx = &asset;
    host.open = asset_open;
    host.read = asset_read;
    host.close = asset_close;
    return host;
}

}  // namespace odrig

#endif
