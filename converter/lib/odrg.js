// ODRG, the runtime format of docs/format.md: the decoder.
//
// The decoder follows docs/format.md step by step and gives the reason the reference gives
// for a file with more than one defect.

import {
  BAD_CODE,
  BAD_LENGTH,
  BAD_MAGIC,
  BAD_PALETTE_INDEX,
  BAD_PALETTE_SIZE,
  BAD_STORED_LENGTH,
  BAD_VERSION,
  CANVAS_TOO_LARGE,
  NO_FRAMES,
  OUT_OF_BITS,
  RESERVED_BITS,
  RUN_PAST_END,
  Rejection,
  TOO_MUCH_PADDING,
  TRAILING_BYTES,
  TRUNCATED,
  ZERO_DURATION,
  ZERO_SIZE,
} from "./errors.js";
import {inflateRaw} from "./inflate.js";

export const MAGIC = Uint8Array.of(0x4f, 0x44, 0x52, 0x47);
export const VERSION = 1;
export const HEADER_SIZE = 16;
export const RECORD_START_SIZE = 5;
export const COMPRESSED = 0x01;
export const STORED = 0x40;
export const LARGEST_PALETTE = 256;
export const LARGEST_N = 65534;
export const LARGEST_CODE = 255;
export const LONGEST_DURATION = 65535;
export const MOST_FRAMES = 0xffffffff;

// The longest Gamma code whose value is read as a `Number`; a longer one is a `BigInt`.
const LONGEST_SMALL_GAMMA = 30;

function hex2(value) {
  return value.toString(16).padStart(2, "0");
}

function u16(bytes, at) {
  return bytes[at] | (bytes[at + 1] << 8);
}

// Reads an ODRG file given as bytes.
//
// The result is `{width, height, paletteSize, compressed, records, modes}`. `records` has
// one `{ms, picture}` for every frame record, in order: its duration and the picture the
// pixel buffer holds after it. `modes` has the mode byte of every record.
export function decode(data) {
  if (data.length < HEADER_SIZE) {
    throw new Rejection(TRUNCATED, `the file ends inside the ${HEADER_SIZE}-byte header`);
  }
  const magic = data.subarray(0, 4);
  const version = data[4];
  const flags = data[5];
  const width = u16(data, 6);
  const height = u16(data, 8);
  const paletteSize = u16(data, 10);
  const frameCount = u16(data, 12) + 65536 * u16(data, 14);
  if (magic.some((byte, i) => byte !== MAGIC[i])) {
    throw new Rejection(BAD_MAGIC, `the file starts with ${Array.from(magic, hex2).join(" ")}, not 4f 44 52 47`);
  }
  if (version !== VERSION) {
    throw new Rejection(BAD_VERSION, `version is ${version}, not ${VERSION}`);
  }
  if ((flags & ~COMPRESSED) !== 0) {
    throw new Rejection(RESERVED_BITS, `the flags byte is 0x${hex2(flags)}`);
  }
  if (width === 0 || height === 0) {
    throw new Rejection(ZERO_SIZE, `the canvas is ${width} x ${height}`);
  }
  if (paletteSize > LARGEST_PALETTE) {
    throw new Rejection(BAD_PALETTE_SIZE, `the palette size is ${paletteSize}`);
  }
  const bpp = paletteSize > 0 ? 1 : 3;
  const n = width * height * bpp;
  if (n > LARGEST_N) {
    throw new Rejection(CANVAS_TOO_LARGE, `a picture of ${width} x ${height} is ${n} bytes, above ${LARGEST_N}`);
  }
  if (frameCount === 0) {
    throw new Rejection(NO_FRAMES, "the frame count is 0");
  }

  const compressed = (flags & COMPRESSED) !== 0;
  const body = compressed ? inflated(data.subarray(HEADER_SIZE)) : data.subarray(HEADER_SIZE);
  let position = 0;
  const take = (count, what) => {
    const end = position + count;
    if (end > body.length) {
      throw new Rejection(TRUNCATED, `the file ends inside ${what}`);
    }
    const taken = body.subarray(position, end);
    position = end;
    return taken;
  };

  const palette = new Uint8Array(3 * paletteSize);
  for (let entry = 0; entry < paletteSize; entry += 1) {
    palette.set(take(3, "the palette"), 3 * entry);
  }

  let buffer = new Uint8Array(n);
  const records = [];
  const modes = [];
  for (let number = 1; number <= frameCount; number += 1) {
    const what = `frame record ${number}`;
    const start = take(RECORD_START_SIZE, what);
    const duration = u16(start, 0);
    const length = u16(start, 2);
    const mode = start[4];
    if (duration === 0) {
      throw new Rejection(ZERO_DURATION, `the duration of ${what} is 0`);
    }
    if (length < 2 || length > n + 1) {
      throw new Rejection(BAD_LENGTH, `the length of ${what} is ${length}, not 2 to ${n + 1}`);
    }
    if ((mode & 0x80) !== 0 || ((mode & STORED) !== 0 && mode !== STORED)) {
      throw new Rejection(RESERVED_BITS, `the mode byte of ${what} is 0x${hex2(mode)}`);
    }
    if (mode === STORED && length !== n + 1) {
      throw new Rejection(BAD_STORED_LENGTH, `the length of stored ${what} is ${length}, not ${n + 1}`);
    }
    const dataBytes = take(length - 1, what);
    buffer = mode === STORED ? new Uint8Array(dataBytes) : coded(dataBytes, mode, buffer, width * bpp, bpp, what);
    let picture = buffer;
    if (paletteSize > 0) {
      picture = new Uint8Array(3 * n);
      for (let pixel = 0; pixel < n; pixel += 1) {
        const index = buffer[pixel];
        if (index >= paletteSize) {
          throw new Rejection(
            BAD_PALETTE_INDEX,
            `pixel ${pixel} of ${what} has index ${index}; the palette has ${paletteSize} entries`,
          );
        }
        picture[3 * pixel] = palette[3 * index];
        picture[3 * pixel + 1] = palette[3 * index + 1];
        picture[3 * pixel + 2] = palette[3 * index + 2];
      }
    }
    records.push({ms: duration, picture});
    modes.push(mode);
  }
  if (position < body.length) {
    throw new Rejection(TRAILING_BYTES, `${body.length - position} bytes follow the last frame record`);
  }
  return {width, height, paletteSize, compressed, records, modes};
}

// The output of the one raw DEFLATE stream that follows the header.
function inflated(stream) {
  const {data, used} = inflateRaw(stream);
  if (used < stream.length) {
    throw new Rejection(TRAILING_BYTES, `${stream.length - used} bytes follow the DEFLATE stream`);
  }
  return data;
}

// The same channel of the pixel to the left, or of the first pixel of the row before.
function neighbour(a, i, stride, bpp) {
  if (i % stride >= bpp) {
    return a[i - bpp];
  }
  if (i >= stride) {
    return a[i - stride];
  }
  return 0;
}

// The pixel buffer after a coded frame: codes, then residuals, then the predictor.
function coded(data, mode, old, stride, bpp, what) {
  const k = mode & 0x07;
  const run = (mode & 0x08) !== 0;
  const predictor = (mode >> 4) & 0x03;
  const n = old.length;

  // The data as bits, the most significant bit of each byte first.
  const total = 8 * data.length;
  let position = 0;
  const outOfBits = () => new Rejection(OUT_OF_BITS, `${what} needs a bit after the last bit of its data`);
  const bit = (at) => (data[at >> 3] >> (7 - (at & 7))) & 1;
  // The next `count` bits as a number; `count` is at most 30.
  const take = (count) => {
    if (position + count > total) {
      throw outOfBits();
    }
    let value = 0;
    for (let i = 0; i < count; i += 1) {
      value = value * 2 + bit(position + i);
    }
    position += count;
    return value;
  };
  // Reads one Rice(k) code: one-bits are counted up to a zero-bit or up to eight.
  const rice = () => {
    const limit = Math.min(position + 8, total);
    let zero = position;
    while (zero < limit && bit(zero) === 1) {
      zero += 1;
    }
    if (zero === limit) {
      take(8);
      return take(8);
    }
    const q = zero - position;
    position = zero + 1;
    return q * 2 ** k + take(k);
  };
  // Reads one Gamma code whole: b - 1 zero-bits, then the b bits of the value.
  const gamma = () => {
    let one = position;
    while (one < total && bit(one) === 0) {
      one += 1;
    }
    if (one === total) {
      throw outOfBits();
    }
    const length = one - position + 1;
    position = one;
    if (length <= LONGEST_SMALL_GAMMA) {
      return take(length);
    }
    if (position + length > total) {
      throw outOfBits();
    }
    let value = 0n;
    for (let i = 0; i < length; i += 1) {
      value = value * 2n + BigInt(bit(position + i));
    }
    position += length;
    return value;
  };
  const checked = (code, i) => {
    if (code > LARGEST_CODE) {
      throw new Rejection(BAD_CODE, `code ${i} of ${what} is ${code}, above ${LARGEST_CODE}`);
    }
    return code;
  };

  const codes = new Uint8Array(n);
  if (run) {
    let i = 0;
    while (i < n) {
      const g = gamma();
      if (typeof g === "bigint" || i + g - 1 > n) {
        const zeros = typeof g === "bigint" ? g - 1n : g - 1;
        throw new Rejection(RUN_PAST_END, `a run of ${zeros} zero codes at code ${i} of ${what} passes ${n}`);
      }
      i += g - 1;
      if (i === n) {
        break;
      }
      codes[i] = checked(rice() + 1, i);
      i += 1;
    }
  } else {
    for (let i = 0; i < n; i += 1) {
      codes[i] = checked(rice(), i);
    }
  }
  if (total - position >= 8) {
    throw new Rejection(TOO_MUCH_PADDING, `${total - position} bits of ${what} are unread after its ${n} codes`);
  }

  const residuals = new Uint8Array(n);
  for (let i = 0; i < n; i += 1) {
    const code = codes[i];
    residuals[i] = code % 2 === 0 ? code / 2 : 256 - (code + 1) / 2;
  }

  if (predictor === 3) {
    return residuals;
  }
  const fresh = new Uint8Array(n);
  if (predictor === 0) {
    for (let i = 0; i < n; i += 1) {
      fresh[i] = old[i] + residuals[i];
    }
  } else if (predictor === 1) {
    const change = new Uint8Array(n);
    for (let i = 0; i < n; i += 1) {
      change[i] = residuals[i] + neighbour(change, i, stride, bpp);
      fresh[i] = old[i] + change[i];
    }
  } else {
    for (let i = 0; i < n; i += 1) {
      fresh[i] = residuals[i] + neighbour(fresh, i, stride, bpp);
    }
  }
  return fresh;
}
