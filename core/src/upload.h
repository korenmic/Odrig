#ifndef ODRIG_UPLOAD_H
#define ODRIG_UPLOAD_H

#include <stdint.h>

#include "commands.h"
#include "core_state.h"

namespace odrig {

// An upload on which nothing has moved for this long is discarded. Progress is
// `upload begin`, an `upload data` that was taken, and a step of the check.
const uint64_t kUploadQuietMs = 60000;

// The space a file needs beside its own bytes: a 256th of them, for the block pointers of
// the file system, and this many bytes for the other files a change writes.
const uint32_t kUploadReserve = 16384;

// The name of the part of the open upload: on the drive for an upload to it, whose id is 0
// until it is installed.
inline const char *upload_part(const Core &core) {
    return core.upload.id == 0 ? "drive/upload.part" : "upload.part";
}

// The number of bytes a text stands for as base64 with the alphabet of RFC 4648,
// section 5, without padding and with the unused bits of its last character zero; 0 when
// the text is not that, or stands for no byte or for more than kChunkSize.
uint32_t base64_size(const char *text, uint32_t length);

// Called by every entry of the core that carries a timestamp, before it does anything
// else: discards an open upload on which nothing has moved for kUploadQuietMs.
void upload_touch(Core &core, uint64_t now);

// Discards the open upload, if there is one: its bytes are removed from storage.
void upload_discard(Core &core);

// One step of the check of an uploaded file: the header, one frame record, the end of the
// file, or one slice of the settling of a defect. Called after a refresh that followed the
// refresh before it without a gap.
void upload_step(Core &core, uint64_t now);

// The four commands on a valid show, with their arguments read. Each writes its reply.
// `name` ends in a zero and is a file name; `count` is what base64_size gave for the text.
uint32_t upload_begin(Core &core, uint64_t now, uint32_t id, const char *name, uint32_t bytes, Reply &reply);

// `upload begin external <file> <bytes>`: opens an upload to the drive. `busy` while an
// upload is open or the drive's catalog is read, `read-only` when the core may not change the
// drive, `no-space` when the drive has no room or no place for it.
uint32_t upload_begin_external(Core &core, uint64_t now, const char *name, uint32_t bytes, Reply &reply);

// `upload begin` with the CRC-32 of the file: `{"ok":true,"unchanged":true}`, and no upload
// opened, when the last upload of this boot installed this file with this id, these bytes
// and this CRC-32, no upload has begun since, and the item still names it, usable;
// otherwise `upload_begin`.
uint32_t upload_begin_known(Core &core, uint64_t now, uint32_t id, const char *name, uint32_t bytes, uint32_t crc, Reply &reply);
uint32_t upload_data(Core &core, uint64_t now, uint32_t offset, const char *text, uint32_t length, uint32_t count, Reply &reply);
uint32_t upload_end(Core &core, uint32_t crc, Reply &reply);
uint32_t upload_cancel(Core &core, Reply &reply);

// The largest file `upload expect` compares: the CRC-32 is read from storage while the
// command waits.
const uint32_t kExpectLargest = 16384;

// `upload expect`: the open upload goes on only while the file of its item has this CRC-32
// now; otherwise it is discarded with `stale`.
uint32_t upload_expect(Core &core, uint32_t crc, Reply &reply);

}  // namespace odrig

#endif
