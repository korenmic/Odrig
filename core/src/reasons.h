#ifndef ODRIG_REASONS_H
#define ODRIG_REASONS_H

namespace odrig {

// Why a file, a show or a step of startup is refused. Every function of the core that can
// fail returns one of these; kNone is success.
enum Reason {
    kNone = 0,

    // The end of a stream. It is passed between the parts of the core and never reported.
    kEnd,

    // What only a host can cause.
    kReadError,
    kOutOfMemory,

    // The installed file set.
    kMappingMissing,
    kMappingMalformed,
    kShowMissing,
    kShowMalformed,
    kDuplicateId,
    kUndefinedId,
    kNestedCycle,
    kFileMissing,
    kFileMalformed,
    kSizeMismatch,

    // An ODRG file.
    kTruncated,
    kBadMagic,
    kBadVersion,
    kReservedBits,
    kZeroSize,
    kBadPaletteSize,
    kCanvasTooLarge,
    kNoFrames,
    kBadDeflate,
    kZeroDuration,
    kBadLength,
    kBadStoredLength,
    kOutOfBits,
    kRunPastEnd,
    kBadCode,
    kTooMuchPadding,
    kBadPaletteIndex,
    kTrailingBytes,

    // An ODRGX container.
    kBadContainer,
    kUnknownType,
    kUnknownTypeVersion,
    kPayloadSize,
    kCanvasMismatch,
    kLoopMismatch,

    // A text of an ODRGX container.
    kUnknownFont,
    kBadSettings,
    kBadText,
    kDoesNotFit,
    kBadGlyph,

    kReasonCount,

    // Work that is not finished: the same call is made again later and goes on. It is
    // passed between the parts of the core and is never the reason of anything.
    kPendingWork
};

// The fixed name of a reason, as docs/reasons.md lists it. A value that is never reported
// has the empty name.
const char *reason_name(Reason reason);

}  // namespace odrig

#endif
