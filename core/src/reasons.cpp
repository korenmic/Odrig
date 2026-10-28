#include "reasons.h"

namespace odrig {

const char *reason_name(Reason reason) {
    switch (reason) {
        case kReadError: return "read-error";
        case kOutOfMemory: return "out-of-memory";
        case kMappingMissing: return "mapping-missing";
        case kMappingMalformed: return "mapping-malformed";
        case kShowMissing: return "show-missing";
        case kShowMalformed: return "show-malformed";
        case kDuplicateId: return "duplicate-id";
        case kUndefinedId: return "undefined-id";
        case kNestedCycle: return "nested-cycle";
        case kFileMissing: return "file-missing";
        case kFileMalformed: return "file-malformed";
        case kSizeMismatch: return "size-mismatch";
        case kTooManyFolders: return "too-many-folders";
        case kTruncated: return "truncated";
        case kBadMagic: return "bad-magic";
        case kBadVersion: return "bad-version";
        case kReservedBits: return "reserved-bits";
        case kZeroSize: return "zero-size";
        case kBadPaletteSize: return "bad-palette-size";
        case kCanvasTooLarge: return "canvas-too-large";
        case kNoFrames: return "no-frames";
        case kBadDeflate: return "bad-deflate";
        case kZeroDuration: return "zero-duration";
        case kBadLength: return "bad-length";
        case kBadStoredLength: return "bad-stored-length";
        case kOutOfBits: return "out-of-bits";
        case kRunPastEnd: return "run-past-end";
        case kBadCode: return "bad-code";
        case kTooMuchPadding: return "too-much-padding";
        case kBadPaletteIndex: return "bad-palette-index";
        case kTrailingBytes: return "trailing-bytes";
        case kBadContainer: return "bad-container";
        case kUnknownType: return "unknown-type";
        case kUnknownTypeVersion: return "unknown-type-version";
        case kPayloadSize: return "payload-size";
        case kCanvasMismatch: return "canvas-mismatch";
        case kLoopMismatch: return "loop-mismatch";
        case kUnknownFont: return "unknown-font";
        case kBadSettings: return "bad-settings";
        case kBadText: return "bad-text";
        case kDoesNotFit: return "does-not-fit";
        case kBadGlyph: return "bad-glyph";
        case kUnknownWidget: return "unknown-widget";
        case kBadPicture: return "bad-picture";
        case kNone:
        case kEnd:
        case kReasonCount:
        case kPendingWork:
            break;
    }
    return "";
}

}  // namespace odrig
