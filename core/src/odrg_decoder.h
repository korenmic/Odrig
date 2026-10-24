#ifndef ODRIG_ODRG_DECODER_H
#define ODRIG_ODRG_DECODER_H

#include <stdint.h>

#include "file_source.h"
#include "inflate.h"
#include "reasons.h"

namespace odrig {

// The largest picture of an ODRG file, in bytes.
const uint32_t kLargestPicture = 65534;

// The most bytes of a body one call of the decoder inflates, or reads of an uncompressed
// body, while it settles a defect: about a millisecond of work on the board.
const uint32_t kSettleSliceBytes = 32768;

// A reader of one ODRG file (docs/format.md), front to back. It holds no frame record: each
// record is decoded straight into the caller's pixel buffer, which holds the picture before
// it. The same reader checks a file at startup and decodes it for playback.
//
// A defect found inside the body is settled: the reader reads on to the end of the body to
// find the defect a reader holding the whole file meets first. Settling takes at most
// `settle_slice` bytes in one call and then gives kPendingWork, which is no reason: the next
// call of `next` or `finish` goes on from there, and the last one gives the reason.
struct OdrgDecoder {
    // Reads and checks the 16 bytes of the header of a file that has just been opened. The
    // window holds kWindowSize bytes and is used when the body is compressed.
    Reason open(FileSource *from, Inflate *with, uint8_t *window);

    // Decodes the next frame record into `pixels`, n bytes that hold the picture before the
    // record: all zero before the first one. The palette is read with the first record.
    // A record asked for after the last one of the file is kTruncated. kPendingWork while a
    // defect is being settled; the pixels then hold no picture.
    Reason next(uint8_t *pixels, uint16_t *duration);

    // After the last record: nothing may follow, in the body or in the file. kPendingWork as
    // for `next`.
    Reason finish();

    int body_get() {
        const int byte = compressed ? inflate->get() : file->get();
        if (byte >= 0) {
            ++body_read;
        }
        return byte;
    }
    Reason body_stopped(int got);
    Reason settled(Reason found, uint32_t record_bytes_left);
    Reason settle_more();
    Reason read_palette();
    Reason coded(uint8_t *pixels, uint32_t mode, uint32_t data_bytes);

    uint16_t width;         // W
    uint16_t height;        // H
    uint16_t colours;       // C: 0, or the number of palette entries
    uint8_t bpp;            // bytes for each pixel in the pixel buffer: 3, or 1 with a palette
    uint8_t compressed;
    uint32_t frames;        // F
    uint32_t n;             // N: the size of the pixel buffer in bytes
    uint32_t records_left;
    uint8_t palette_pending;
    uint8_t palette[768];

    // Settling: 0 when there is none, 1 while it goes on, 2 once it has ended with the
    // reason in `settle_found`; the defect that began it, the data bytes of its record not
    // yet read, and the bytes one call may take.
    uint8_t settling;
    Reason settle_found;
    uint32_t settle_missing;
    uint32_t settle_slice;
    // The bytes of the body taken so far: inflated bytes of a compressed body.
    uint64_t body_read;

    FileSource *file;
    Inflate *inflate;
};

}  // namespace odrig

#endif
