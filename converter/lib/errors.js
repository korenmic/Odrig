// The one way the library refuses an input: a rejection with a named reason.
//
// Every reason is a constant of this module. docs/reasons.md lists them with their
// conditions.

export const NOT_FOUND = "not-found";
export const CANNOT_WRITE = "cannot-write";

export const BAD_JSON = "bad-json";
export const MISSING_MEMBER = "missing-member";
export const BAD_TYPE = "bad-type";
export const BAD_VERSION = "bad-version";
export const UNKNOWN_MEMBER = "unknown-member";
export const OUT_OF_RANGE = "out-of-range";
export const NO_FRAMES = "no-frames";
export const BAD_PIXEL_COUNT = "bad-pixel-count";

export const TRUNCATED = "truncated";
export const BAD_MAGIC = "bad-magic";
export const RESERVED_BITS = "reserved-bits";
export const ZERO_SIZE = "zero-size";
export const BAD_PALETTE_SIZE = "bad-palette-size";
export const CANVAS_TOO_LARGE = "canvas-too-large";
export const BAD_DEFLATE = "bad-deflate";
export const ZERO_DURATION = "zero-duration";
export const BAD_LENGTH = "bad-length";
export const BAD_STORED_LENGTH = "bad-stored-length";
export const OUT_OF_BITS = "out-of-bits";
export const RUN_PAST_END = "run-past-end";
export const BAD_CODE = "bad-code";
export const TOO_MUCH_PADDING = "too-much-padding";
export const BAD_PALETTE_INDEX = "bad-palette-index";
export const TRAILING_BYTES = "trailing-bytes";

export const TOO_MANY_FRAMES = "too-many-frames";

export const BAD_CONTAINER = "bad-container";
export const UNKNOWN_TYPE = "unknown-type";
export const UNKNOWN_TYPE_VERSION = "unknown-type-version";
export const PAYLOAD_SIZE = "payload-size";
export const CANVAS_MISMATCH = "canvas-mismatch";
export const LOOP_MISMATCH = "loop-mismatch";
export const BAD_SETTINGS = "bad-settings";
export const BAD_TEXT = "bad-text";
export const UNKNOWN_FONT = "unknown-font";
export const BAD_GLYPH = "bad-glyph";
export const DOES_NOT_FIT = "does-not-fit";
export const UNSUPPORTED_CHARACTER = "unsupported-character";

export const MAPPING_MISSING = "mapping-missing";
export const MAPPING_MALFORMED = "mapping-malformed";

export const CANVAS_TOO_SMALL = "canvas-too-small";

export const SHOW_MISSING = "show-missing";
export const SHOW_MALFORMED = "show-malformed";
export const DUPLICATE_ID = "duplicate-id";
export const UNDEFINED_ID = "undefined-id";
export const NESTED_CYCLE = "nested-cycle";
export const FILE_MISSING = "file-missing";
export const FILE_MALFORMED = "file-malformed";
export const SIZE_MISMATCH = "size-mismatch";
export const OUTPUT_NOT_EMPTY = "output-not-empty";

export const UNSUPPORTED_MEDIA = "unsupported-media";
export const UNREADABLE_MEDIA = "unreadable-media";
export const BAD_RANGE = "bad-range";

// An input that is refused. `reason` is a fixed name, `detail` is text for people.
export class Rejection extends Error {
  constructor(reason, detail) {
    super(`${reason}: ${detail}`);
    this.name = "Rejection";
    this.reason = reason;
    this.detail = detail;
  }
}

// Runs `action` and puts `label`, the name of the file concerned, in front of the detail
// of a rejection. An action that gives a promise is waited for.
export function naming(label, action) {
  const named = (error) => {
    if (error instanceof Rejection) {
      throw new Rejection(error.reason, `${label}: ${error.detail}`);
    }
    throw error;
  };
  let result;
  try {
    result = action();
  } catch (error) {
    named(error);
  }
  if (result !== null && typeof result === "object" && typeof result.then === "function") {
    return result.then((value) => value, named);
  }
  return result;
}
