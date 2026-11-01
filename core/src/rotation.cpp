#include "rotation.h"

#include <string.h>

#include "catalog.h"
#include "crc32.h"
#include "mini.h"
#include "player.h"
#include "storage.h"

namespace odrig {
namespace {
const char kFile[] = "rotation.txt";
const char kPart[] = "rotation.part";
const char *const kSaved[] = {"1 0\n", "1 90\n", "1 180\n", "1 270\n"};

bool supported(const Core &core) {
    return !core.invalid && core.width != 0 && core.width == core.height;
}

uint32_t revision_of(const Core &core) {
    return crc_value(crc_add(kCrcStart, core.rotation));
}
}

void rotation_start(Core &core) {
    core.rotation = 0;
    core.rotation_error = 0;
    if (!supported(core)) return;
    const Reason opened = core.file.open(core.host, kFile);
    if (opened == kFileMissing) return;
    core.rotation_error = 1;
    if (opened != kNone) return;
    char text[8];
    uint32_t size = 0;
    int got = 0;
    while (size < sizeof text && (got = core.file.get()) >= 0) text[size++] = static_cast<char>(got);
    core.file.close();
    if (got != -kEnd) return;
    for (uint8_t q = 0; q < 4; ++q) {
        if (size == strlen(kSaved[q]) && memcmp(text, kSaved[q], size) == 0) {
            core.rotation = q;
            core.rotation_error = 0;
            return;
        }
    }
}

uint32_t rotation_reply(const Core &core, Reply &reply) {
    reply.text("{\"ok\":true,\"supported\":"); reply.text(supported(core) ? "true" : "false");
    reply.text(",\"degrees\":"); reply.number(core.rotation * 90u);
    reply.text(",\"revision\":"); reply.number(revision_of(core));
    reply.text(",\"error\":"); reply.text(core.rotation_error ? "\"unreadable\"" : "null");
    reply.text("}\n");
    return reply.length;
}

uint32_t rotation_set(Core &core, uint32_t revision, uint32_t degrees, Reply &reply) {
    if (degrees > 270 || degrees % 90 != 0) return refuse(reply, "bad-argument");
    if (core.invalid) return refuse(reply, "show-invalid");
    if (!supported(core)) return refuse(reply, "unsupported");
    if (core.mapping_test) return refuse(reply, "in-use");
    if (!check_complete(core) || core.upload.state != kUploadNone || catalog_rebuilding(core) ||
        (core.mini != nullptr && core.mini->pending)) return refuse(reply, "busy");
    if (revision != revision_of(core)) return refuse(reply, "rotation-conflict");
    const uint8_t q = static_cast<uint8_t>(degrees / 90);
    if (q == core.rotation && !core.rotation_error) return rotation_reply(core, reply);
    const odrig_host &host = core.host;
    if (!storage_changes(core)) return refuse(reply, "storage-error");
    if (host.write_open(host.ctx, kPart) != 1 ||
        host.write(host.ctx, reinterpret_cast<const uint8_t *>(kSaved[q]), strlen(kSaved[q])) != 1 ||
        host.write_close(host.ctx) != 1 || host.rename(host.ctx, kPart, kFile) != 1) {
        host.remove(host.ctx, kPart);
        return refuse(reply, "storage-error");
    }
    core.rotation = q;
    core.rotation_error = 0;
    return rotation_reply(core, reply);
}
}
