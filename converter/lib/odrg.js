// ODRG, the runtime format of docs/format.md: the decoder and the encoder.
//
// The decoder follows docs/format.md step by step and gives the reason the reference gives
// for a file with more than one defect. The encoder follows the converter guidance of
// docs/format.md and writes the same bytes for the same frames every time.

import {deflateRaw} from "./deflate.js";
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
  TOO_MANY_FRAMES,
  TOO_MUCH_PADDING,
  TRAILING_BYTES,
  TRUNCATED,
  ZERO_DURATION,
  ZERO_SIZE,
} from "./errors.js";
import {inflateRaw} from "./inflate.js";
import {merged} from "./jsonframes.js";
import {plus, times} from "./whole.js";

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

// The checked header of an ODRG file given as bytes, the file's first 16 bytes:
// `{width, height, paletteSize, frameCount, compressed, n}`.
export function header(data) {
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
  return {width, height, paletteSize, frameCount, compressed: (flags & COMPRESSED) !== 0, n};
}

// Reads an ODRG file given as bytes, one frame record at a time.
//
// The header is read, the body inflated and the palette read at once, each refused as
// `decode` refuses it. The result has the header's `width`, `height`, `paletteSize`,
// `frameCount` and `compressed`, and two functions:
//
// - `next()` reads the next frame record and gives `{ms, picture, mode}`: its duration, the
//   picture the pixel buffer holds after it and its mode byte. After the last record it
//   refuses bytes that follow it and gives null. Every refusal is the one `decode` gives,
//   at the same record.
// - `loopMs()` is the sum of the durations of the records, read from their starts alone.
//   It refuses nothing: it stops at the first start it cannot read or whose record does not
//   fit, a place where `next` refuses the file.
export function reader(data) {
  const {width, height, paletteSize, frameCount, compressed, n} = header(data);
  const bpp = paletteSize > 0 ? 1 : 3;
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
  const firstRecord = position;

  let buffer = new Uint8Array(n);
  let number = 0;
  let ended = false;
  const next = () => {
    if (number === frameCount) {
      if (!ended) {
        ended = true;
        if (position < body.length) {
          throw new Rejection(TRAILING_BYTES, `${body.length - position} bytes follow the last frame record`);
        }
      }
      return null;
    }
    number += 1;
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
    return {ms: duration, picture, mode};
  };

  const loopMs = () => {
    let at = firstRecord;
    let total = 0;
    for (let counted = 0; counted < frameCount; counted += 1) {
      if (at + RECORD_START_SIZE > body.length) {
        break;
      }
      const length = u16(body, at + 2);
      if (length < 2 || at + RECORD_START_SIZE + length - 1 > body.length) {
        break;
      }
      total += u16(body, at);
      at += RECORD_START_SIZE + length - 1;
    }
    return total;
  };

  return {width, height, paletteSize, frameCount, compressed, next, loopMs};
}

// Reads an ODRG file given as bytes.
//
// The result is `{width, height, paletteSize, compressed, records, modes}`. `records` has
// one `{ms, picture}` for every frame record, in order: its duration and the picture the
// pixel buffer holds after it. `modes` has the mode byte of every record.
export function decode(data) {
  const read = reader(data);
  const records = [];
  const modes = [];
  for (let record = read.next(); record !== null; record = read.next()) {
    records.push({ms: record.ms, picture: record.picture});
    modes.push(record.mode);
  }
  return {width: read.width, height: read.height, paletteSize: read.paletteSize, compressed: read.compressed, records, modes};
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

// ---- the encoder ----

// For a residual, its code: 2r for a residual below 128, else 2 * (256 - r) - 1.
const CODE_OF_RESIDUAL = Uint8Array.from({length: 256}, (unused, r) => (r < 128 ? 2 * r : 2 * (256 - r) - 1));

// For k and a value, the number of bits of the Rice(k) code of the value.
const RICE_BITS = Array.from({length: 8}, (unused, k) =>
  Uint8Array.from({length: 256}, (alsoUnused, value) => (value >> k >= 8 ? 16 : (value >> k) + 1 + k)),
);

function bitLength(value) {
  return 32 - Math.clz32(value);
}

// The bytes of an ODRG file that shows the animation, with the smallest frame records.
export function encode(animation, {compressed = true} = {}) {
  const {width, height} = animation;
  const frames = merged(animation.frames);
  const palette = paletteFor(frames);
  const bpp = palette === null ? 3 : 1;
  const n = times(times(width, height), bpp);
  if (n > LARGEST_N) {
    throw new Rejection(CANVAS_TOO_LARGE, `a picture of ${width} x ${height} would be ${n} bytes, above ${LARGEST_N}`);
  }
  let count = 0;
  for (const {ms} of frames) {
    count = plus(count, recordsFor(ms));
  }
  if (count > MOST_FRAMES) {
    throw new Rejection(TOO_MANY_FRAMES, `${count} frame records would be needed, above ${MOST_FRAMES}`);
  }
  const records = [];
  let old = new Uint8Array(n);
  for (const frame of frames) {
    const fresh = toBuffer(frame.picture, palette);
    let left = Number(frame.ms);
    while (left > 0) {
      const duration = left < LONGEST_DURATION ? left : LONGEST_DURATION;
      records.push(bestRecord(old, fresh, width, bpp, duration));
      old = fresh;
      left -= duration;
    }
  }
  return container(width, height, palette, records, compressed ? deflateRaw : null);
}

// The number of frame records a frame of `ms` milliseconds needs: `ms` divided by the
// longest duration, rounded up, as a whole number.
function recordsFor(ms) {
  if (typeof ms === "bigint") {
    const count = (ms + BigInt(LONGEST_DURATION - 1)) / BigInt(LONGEST_DURATION);
    return count <= BigInt(Number.MAX_SAFE_INTEGER) ? Number(count) : count;
  }
  const below = ms - 1;
  return (below - (below % LONGEST_DURATION)) / LONGEST_DURATION + 1;
}

// The colours of the frames ordered by hue, as three bytes each in one `Uint8Array`, or
// null when there are more than 256.
export function paletteFor(frames) {
  const seen = new Set();
  let before = null;
  for (const {picture} of frames) {
    if (picture === before) {
      continue;
    }
    before = picture;
    for (let i = 0; i + 2 < picture.length; i += 3) {
      seen.add(picture[i] * 65536 + picture[i + 1] * 256 + picture[i + 2]);
    }
    if (seen.size > LARGEST_PALETTE) {
      return null;
    }
  }
  const ordered = Array.from(seen, (colour) => ({colour, order: hueOrder(colour >> 16, (colour >> 8) & 0xff, colour & 0xff)}));
  ordered.sort((a, b) => compareOrders(a.order, b.order));
  const palette = new Uint8Array(3 * ordered.length);
  ordered.forEach(({colour}, position) => {
    palette[3 * position] = colour >> 16;
    palette[3 * position + 1] = (colour >> 8) & 0xff;
    palette[3 * position + 2] = colour & 0xff;
  });
  return palette;
}

// Hue, then saturation, then the largest channel, as exact fractions: `[hue, of, saturation,
// of, largest]`, the hue being hue / of and the saturation saturation / of. A colour without
// hue counts as hue 0.
export function hueOrder(r, g, b) {
  const mx = Math.max(r, g, b);
  const mn = Math.min(r, g, b);
  const d = mx - mn;
  let hue;
  if (d === 0) {
    hue = 0;
  } else if (mx === r) {
    hue = (((g - b) % (6 * d)) + 6 * d) % (6 * d);
  } else if (mx === g) {
    hue = b - r + 2 * d;
  } else {
    hue = r - g + 4 * d;
  }
  return [hue, d === 0 ? 1 : d, mx === 0 ? 0 : d, mx === 0 ? 1 : mx, mx];
}

function compareOrders(a, b) {
  const hue = a[0] * b[1] - b[0] * a[1];
  if (hue !== 0) {
    return hue;
  }
  const saturation = a[2] * b[3] - b[2] * a[3];
  if (saturation !== 0) {
    return saturation;
  }
  return a[4] - b[4];
}

// The pixel buffer of a picture: its bytes, or one palette index for each pixel.
export function toBuffer(picture, palette) {
  if (palette === null) {
    return picture;
  }
  const index = new Map();
  for (let position = 0; 3 * position < palette.length; position += 1) {
    index.set(palette[3 * position] * 65536 + palette[3 * position + 1] * 256 + palette[3 * position + 2], position);
  }
  const count = (picture.length - (picture.length % 3)) / 3;
  const buffer = new Uint8Array(count);
  for (let pixel = 0; pixel < count; pixel += 1) {
    buffer[pixel] = index.get(picture[3 * pixel] * 65536 + picture[3 * pixel + 1] * 256 + picture[3 * pixel + 2]);
  }
  return buffer;
}

function recordStart(duration, length, mode) {
  return [duration & 0xff, duration >> 8, length & 0xff, length >> 8, mode];
}

// A frame record that holds the new pixel buffer as it is.
export function storedRecord(fresh, duration) {
  const record = new Uint8Array(RECORD_START_SIZE + fresh.length);
  record.set(recordStart(duration, fresh.length + 1, STORED));
  record.set(fresh, RECORD_START_SIZE);
  return record;
}

// The N codes that turn the buffer `old` into `fresh` with a predictor, one byte each.
export function codes(old, fresh, width, bpp, predictor) {
  const n = fresh.length;
  const stride = width * bpp;
  const result = new Uint8Array(n);
  if (predictor === 0) {
    for (let i = 0; i < n; i += 1) {
      result[i] = CODE_OF_RESIDUAL[(fresh[i] - old[i]) & 0xff];
    }
  } else if (predictor === 1) {
    const change = new Uint8Array(n);
    for (let i = 0; i < n; i += 1) {
      change[i] = fresh[i] - old[i];
    }
    for (let i = 0; i < n; i += 1) {
      result[i] = CODE_OF_RESIDUAL[(change[i] - neighbour(change, i, stride, bpp)) & 0xff];
    }
  } else if (predictor === 2) {
    for (let i = 0; i < n; i += 1) {
      result[i] = CODE_OF_RESIDUAL[(fresh[i] - neighbour(fresh, i, stride, bpp)) & 0xff];
    }
  } else if (predictor === 3) {
    for (let i = 0; i < n; i += 1) {
      result[i] = CODE_OF_RESIDUAL[fresh[i]];
    }
  } else {
    throw new RangeError(`there is no predictor ${predictor}`);
  }
  return result;
}

// The bytes of data of a record for plain mode with k from 0 to 7 and then for run mode
// with k from 0 to 7, worked out from the codes without writing a bit.
export function dataSizes(recordCodes) {
  const histogram = new Uint32Array(256);
  let gammaBits = 0;
  let zeros = 0;
  for (let i = 0; i < recordCodes.length; i += 1) {
    const code = recordCodes[i];
    histogram[code] += 1;
    if (code === 0) {
      zeros += 1;
    } else {
      // The Gamma code of the run before this code: of 1, one bit, when there is none.
      gammaBits += 2 * bitLength(zeros + 1) - 1;
      zeros = 0;
    }
  }
  if (zeros > 0) {
    gammaBits += 2 * bitLength(zeros + 1) - 1;
  }
  const sizes = [];
  for (let k = 0; k < 8; k += 1) {
    const bits = RICE_BITS[k];
    let plain = 0;
    for (let code = 0; code < 256; code += 1) {
      plain += histogram[code] * bits[code];
    }
    sizes.push((plain + 7 - ((plain + 7) % 8)) / 8);
  }
  for (let k = 0; k < 8; k += 1) {
    const bits = RICE_BITS[k];
    let rice = 0;
    for (let code = 1; code < 256; code += 1) {
      rice += histogram[code] * bits[code - 1];
    }
    const total = gammaBits + rice + 7;
    sizes.push((total - (total % 8)) / 8);
  }
  return sizes;
}

// The data of a coded record: the codes written with a mode and k, the most significant bit
// of each byte first, the last byte filled up with zero bits. `size` is the number of bytes
// they take.
function codedData(recordCodes, run, k, size) {
  const data = new Uint8Array(size);
  let position = 0;
  const put = (value, count) => {
    for (let i = count - 1; i >= 0; i -= 1) {
      if ((value >> i) & 1) {
        data[position >> 3] |= 0x80 >> (position & 7);
      }
      position += 1;
    }
  };
  const rice = (value) => {
    const q = value >> k;
    if (q >= 8) {
      put(0xff, 8);
      put(value, 8);
    } else {
      put((1 << (q + 1)) - 2, q + 1);
      put(value & ((1 << k) - 1), k);
    }
  };
  const gamma = (g) => {
    const length = bitLength(g);
    position += length - 1;
    put(g, length);
  };
  if (run) {
    let zeros = 0;
    for (let i = 0; i < recordCodes.length; i += 1) {
      const code = recordCodes[i];
      if (code === 0) {
        zeros += 1;
      } else {
        gamma(zeros + 1);
        rice(code - 1);
        zeros = 0;
      }
    }
    if (zeros > 0) {
      gamma(zeros + 1);
    }
  } else {
    for (let i = 0; i < recordCodes.length; i += 1) {
      rice(recordCodes[i]);
    }
  }
  return data;
}

function codedRecordOf(recordCodes, duration, predictor, run, k, size, n) {
  if (size > n) {
    throw new RangeError(`${size} bytes of data do not fit a record for a picture of ${n} bytes`);
  }
  const record = new Uint8Array(RECORD_START_SIZE + size);
  record.set(recordStart(duration, size + 1, k | (run ? 0x08 : 0) | (predictor << 4)));
  record.set(codedData(recordCodes, run, k, size), RECORD_START_SIZE);
  return record;
}

// A coded frame record written with the given predictor, mode and k.
export function codedRecord(old, fresh, width, bpp, duration, predictor, run, k) {
  const recordCodes = codes(old, fresh, width, bpp, predictor);
  const size = dataSizes(recordCodes)[(run ? 8 : 0) + k];
  return codedRecordOf(recordCodes, duration, predictor, run, k, size, fresh.length);
}

// The frame record with the fewest bytes of data; a stored one when coding saves nothing.
//
// Among equally small coded records the lowest predictor wins, then plain mode, then the
// lowest k.
export function bestRecord(old, fresh, width, bpp, duration) {
  let best = null;
  for (let predictor = 0; predictor < 4; predictor += 1) {
    const recordCodes = codes(old, fresh, width, bpp, predictor);
    const sizes = dataSizes(recordCodes);
    for (let form = 0; form < 16; form += 1) {
      if (best === null || sizes[form] < best.size) {
        best = {size: sizes[form], predictor, run: form >= 8, k: form % 8, recordCodes};
      }
    }
  }
  if (best.size >= fresh.length) {
    return storedRecord(fresh, duration);
  }
  return codedRecordOf(best.recordCodes, duration, best.predictor, best.run, best.k, best.size, fresh.length);
}

// A whole file: the header, then the palette and the records, through `deflate` if given.
// `palette` is three bytes for each colour, or null.
export function container(width, height, palette, records, deflate = null) {
  const paletteBytes = palette === null ? 0 : palette.length;
  let size = paletteBytes;
  for (const record of records) {
    size += record.length;
  }
  let body = new Uint8Array(size);
  if (palette !== null) {
    body.set(palette);
  }
  let at = paletteBytes;
  for (const record of records) {
    body.set(record, at);
    at += record.length;
  }
  let flags = 0;
  if (deflate !== null) {
    body = deflate(body);
    flags = COMPRESSED;
  }
  const colours = paletteBytes / 3;
  const count = records.length;
  const file = new Uint8Array(HEADER_SIZE + body.length);
  file.set(MAGIC);
  file.set(
    [
      VERSION,
      flags,
      width & 0xff,
      width >> 8,
      height & 0xff,
      height >> 8,
      colours & 0xff,
      colours >> 8,
      count & 0xff,
      (count >>> 8) & 0xff,
      (count >>> 16) & 0xff,
      count >>> 24,
    ],
    4,
  );
  file.set(body, HEADER_SIZE);
  return file;
}
