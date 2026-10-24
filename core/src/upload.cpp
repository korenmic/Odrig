#include "upload.h"

#include <string.h>

#include "crc32.h"
#include "json_reader.h"
#include "storage.h"

namespace odrig {

namespace {

// The value of a character of the base64 alphabet, 0 to 63, or 64 for any other.
uint32_t base64_value(char character) {
    if (character >= 'A' && character <= 'Z') {
        return static_cast<uint32_t>(character - 'A');
    }
    if (character >= 'a' && character <= 'z') {
        return static_cast<uint32_t>(character - 'a') + 26;
    }
    if (character >= '0' && character <= '9') {
        return static_cast<uint32_t>(character - '0') + 52;
    }
    if (character == '-') {
        return 62;
    }
    return character == '_' ? 63 : 64;
}

// Decodes a text that base64_size has accepted into the bytes it stands for.
void base64_decode(const char *text, uint32_t length, uint8_t *bytes) {
    uint32_t held = 0;
    uint32_t bits = 0;
    for (uint32_t at = 0; at < length; ++at) {
        held = (held << 6) | base64_value(text[at]);
        bits += 6;
        if (bits >= 8) {
            bits -= 8;
            *bytes++ = static_cast<uint8_t>(held >> bits);
        }
    }
}

// The check has ended: its outcome waits for `upload end`.
void check_ended(Core &core, uint8_t outcome, Reason reason) {
    core.checker->file.close();
    core.upload.state = kUploadChecked;
    core.upload.outcome = outcome;
    core.upload.reason = static_cast<uint8_t>(reason);
}

}  // namespace

uint32_t base64_size(const char *text, uint32_t length) {
    const uint32_t rest = length % 4;
    if (length == 0 || rest == 1) {
        return 0;
    }
    for (uint32_t at = 0; at < length; ++at) {
        if (base64_value(text[at]) == 64) {
            return 0;
        }
    }
    // The last character of a group that is not whole carries bits of no byte.
    const uint32_t last = base64_value(text[length - 1]);
    if ((rest == 2 && (last & 0x0Fu) != 0) || (rest == 3 && (last & 0x03u) != 0)) {
        return 0;
    }
    const uint32_t size = length / 4 * 3 + (rest == 0 ? 0 : rest - 1);
    return size <= kChunkSize ? size : 0;
}

void upload_touch(Core &core, uint64_t now) {
    if (core.upload.state != kUploadNone && now - core.upload.progress >= kUploadQuietMs) {
        upload_discard(core);
    }
}

void upload_discard(Core &core) {
    if (core.upload.state == kUploadNone) {
        return;
    }
    core.checker->file.close();
    core.host.remove(core.host.ctx, kUploadPart);
    core.upload.state = kUploadNone;
}

void upload_step(Core &core, uint64_t now) {
    Upload &upload = core.upload;
    if (upload.state != kUploadChecking) {
        return;
    }
    Checker &checker = *core.checker;
    upload.progress = now;
    Reason reason;
    if (!upload.header_read) {
        // The header is judged first, then the size against the mapping.
        checker.file.open_at(core.host, kUploadPart);
        reason = checker.decoder.open(&checker.file, &checker.inflate, core.check_window);
        if (reason == kNone && (checker.decoder.width != core.width || checker.decoder.height != core.height)) {
            reason = kSizeMismatch;
        }
        if (reason == kNone) {
            memset(core.check_pixels, 0, checker.decoder.n);
            upload.records_left = checker.decoder.frames;
            upload.total_ms = 0;
            upload.header_read = 1;
            return;
        }
    } else if (upload.records_left != 0) {
        uint16_t duration = 0;
        reason = checker.decoder.next(core.check_pixels, &duration);
        if (reason == kPendingWork) {
            // A slice of the settling of a defect: the next step goes on with it.
            return;
        }
        upload.total_ms += duration;
        --upload.records_left;
        if (reason == kNone) {
            return;
        }
    } else {
        // After the last record nothing may follow, and what was read back from storage
        // must be what was received.
        reason = checker.decoder.finish();
        if (reason == kPendingWork) {
            return;
        }
        if (reason == kNone) {
            const bool stored = checker.file.taken == upload.size && checker.file.crc == upload.crc;
            check_ended(core, stored ? kCheckPassed : kCheckStorageFailed, kNone);
            return;
        }
    }
    check_ended(core, reason == kReadError ? kCheckStorageFailed : kCheckBadFile, reason);
}

uint32_t upload_begin(Core &core, uint64_t now, uint32_t id, const char *name, uint32_t bytes, Reply &reply) {
    Upload &upload = core.upload;
    if (upload.state != kUploadNone) {
        return refuse(reply, "busy");
    }
    uint32_t position = 0;
    while (position < core.item_count && core.items[position].id != id) {
        ++position;
    }
    const bool is_new = position == core.item_count;
    if (!is_new && core.items[position].is_cycle) {
        return refuse(reply, "in-use");
    }
    if (is_new && core.drive != nullptr && drive_has_id(core, id)) {
        // The id is an animation of the drive's.
        return refuse(reply, "in-use");
    }
    // The file name is the item's own, or one that no item has.
    for (uint32_t other = 0; other < core.item_count; ++other) {
        const ItemInfo &item = core.items[other];
        if (other != position && !item.is_cycle && same_text(core.files[item.first].name, name)) {
            return refuse(reply, "in-use");
        }
    }
    if (is_new && (core.item_count >= core.item_capacity || core.file_count >= core.item_capacity)) {
        return refuse(reply, "no-space");
    }
    const odrig_host &host = core.host;
    uint32_t free_bytes = 0;
    uint32_t total_bytes = 0;
    const bool told = host.space != nullptr && host.space(host.ctx, &free_bytes, &total_bytes) == 1;
    if (told && static_cast<uint64_t>(bytes) + bytes / 256 + kUploadReserve > free_bytes) {
        return refuse(reply, "no-space");
    }
    if (!told || !storage_changes(core) || core.checker == nullptr || host.write_open(host.ctx, kUploadPart) != 1) {
        return refuse(reply, "storage-error");
    }
    // The upload's check takes the second decoders from the check of a drive's file.
    drive_check_yields(core);
    upload.state = kUploadReceiving;
    upload.id = static_cast<uint16_t>(id);
    uint32_t length = 0;
    for (; name[length] != '\0'; ++length) {
        upload.name[length] = name[length];
    }
    upload.name[length] = '\0';
    upload.size = bytes;
    upload.received = 0;
    upload.crc = kCrcStart;
    upload.header_read = 0;
    upload.progress = now;
    reply.text("{\"ok\":true,\"chunk\":");
    reply.number(kChunkSize);
    reply.text("}\n");
    return reply.length;
}

uint32_t upload_data(Core &core, uint64_t now, uint32_t offset, const char *text, uint32_t length, uint32_t count, Reply &reply) {
    Upload &upload = core.upload;
    if (upload.state == kUploadNone) {
        return refuse(reply, "no-upload");
    }
    // The bytes follow the ones received so far and stay inside the size of the file.
    if (offset != upload.received || count > upload.size - upload.received) {
        return refuse(reply, "bad-offset");
    }
    const odrig_host &host = core.host;
    base64_decode(text, length, core.chunk);
    if (host.write(host.ctx, core.chunk, count) != 1) {
        upload_discard(core);
        return refuse(reply, "storage-error");
    }
    for (uint32_t at = 0; at < count; ++at) {
        upload.crc = crc_add(upload.crc, core.chunk[at]);
    }
    upload.received += count;
    upload.progress = now;
    if (upload.received == upload.size) {
        // The last byte: the file is closed, and its check begins with the next refresh.
        if (host.write_close(host.ctx) != 1) {
            upload_discard(core);
            return refuse(reply, "storage-error");
        }
        upload.state = kUploadChecking;
    }
    reply.text("{\"ok\":true,\"received\":");
    reply.number(upload.received);
    reply.text("}\n");
    return reply.length;
}

uint32_t upload_end(Core &core, uint32_t crc, Reply &reply) {
    Upload &upload = core.upload;
    if (upload.state == kUploadNone) {
        return refuse(reply, "no-upload");
    }
    if (upload.received < upload.size) {
        return refuse(reply, "incomplete");
    }
    if (crc_value(upload.crc) != crc) {
        upload_discard(core);
        return refuse(reply, "bad-checksum");
    }
    if (upload.state == kUploadChecking) {
        return refuse(reply, "busy");
    }
    if (upload.outcome == kCheckBadFile) {
        const Reason reason = static_cast<Reason>(upload.reason);
        upload_discard(core);
        reply.text("{\"ok\":false,\"error\":\"bad-file\",\"reason\":\"");
        reply.text(reason_name(reason));
        reply.text("\"}\n");
        return reply.length;
    }
    if (upload.outcome != kCheckPassed || !storage_install_upload(core)) {
        upload_discard(core);
        return refuse(reply, "storage-error");
    }
    upload.state = kUploadNone;
    return succeed(reply);
}

uint32_t upload_cancel(Core &core, Reply &reply) {
    if (core.upload.state == kUploadNone) {
        return refuse(reply, "no-upload");
    }
    upload_discard(core);
    return succeed(reply);
}

}  // namespace odrig
