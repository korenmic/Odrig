// Previews: a short GIF that loops forever, made from an animation's own pictures, and the
// key that names an animation's file.
//
// A preview holds 24 pictures of the animation's canvas taken evenly over its first loop:
// picture k is the one on screen at floor(k * loop / 24) ms. Each is shown for a
// twenty-fourth of the loop rounded to 10 ms, at least 20 ms and at most 120 ms. A preview
// above 65,536 bytes is made again from the pictures at twelfths, each at most 240 ms, and
// then from those at sixths, each at most 480 ms; one above even then is refused.
//
// The palette is every colour of the pictures when they hold at most 256, otherwise the 256
// colours that cover the most pixels, a tie going to the smaller colour read as one number
// of 24 bits, red highest; it is sorted by that number and filled with black to a power of
// two. Each pixel takes the nearest colour of the palette by the sum of the squares of the
// differences, a tie going to the lower index. The same file gives the same bytes wherever
// the library runs.

import {CANVAS_MISMATCH, PREVIEW_TOO_LARGE, Rejection, TRAILING_BYTES, TRUNCATED} from "./errors.js";
import {inflateStream} from "./inflate.js";
import * as odrg from "./odrg.js";
import * as odrgx from "./odrgx.js";

export const PICTURES = 24;
export const LARGEST = 65536;
// How many records, or drawings of a text or a clock, one step of a maker reads.
export const RECORDS_A_STEP = 256;
export const DRAWINGS_A_STEP = 4;
// How many bytes of a body one step of a maker reads at most.
export const BYTES_A_STEP = 1048576;

const MOST_COLOURS = 256;
const MOST_CODES = 4096;
const SUB_BLOCK = 255;

const CRC_TABLE = (() => {
  const table = new Uint32Array(256);
  for (let n = 0; n < 256; n += 1) {
    let c = n;
    for (let bit = 0; bit < 8; bit += 1) {
      c = (c & 1) !== 0 ? 0xedb88320 ^ (c >>> 1) : c >>> 1;
    }
    table[n] = c >>> 0;
  }
  return table;
})();

// The CRC-32 of zlib and PNG of some bytes, as a number.
export function crc32(bytes) {
  let c = 0xffffffff;
  for (let at = 0; at < bytes.length; at += 1) {
    c = CRC_TABLE[(c ^ bytes[at]) & 0xff] ^ (c >>> 8);
  }
  return (c ^ 0xffffffff) >>> 0;
}

// The key of a file: its CRC-32 as eight lowercase hexadecimal digits, a dash, and its size
// in bytes.
export function keyOf(bytes) {
  return `${crc32(bytes).toString(16).padStart(8, "0")}-${bytes.length}`;
}

// The time each of `count` pictures of a loop of `loopMs` is shown, in hundredths of a
// second.
export function delayOf(loopMs, count) {
  const rounded = Math.floor((loopMs + 5 * count) / (10 * count));
  return Math.min(288 / count, Math.max(2, rounded));
}

// The times of the pictures of a loop: floor(k * loop / 24) for k from 0 to 23.
export function timesOf(loopMs) {
  const times = [];
  for (let k = 0; k < PICTURES; k += 1) {
    times.push(Math.floor((k * loopMs) / PICTURES));
  }
  return times;
}

// The body of an ODRG file read a part at a time: the output of its DEFLATE stream, or the
// bytes of one stored as it is, read in place. `pull(limit)` gives the next part, empty at the
// end; `check()` refuses bytes that follow a stream, as `odrg.reader` does.
function bodyParts(file, compressed) {
  const body = file.subarray(odrg.HEADER_SIZE);
  if (!compressed) {
    let at = 0;
    return {
      pull(limit) {
        const part = body.subarray(at, Math.min(body.length, at + limit));
        at += part.length;
        return part;
      },
      check() {},
      held: () => 0,
    };
  }
  const stream = inflateStream();
  stream.push(body);
  stream.end();
  return {
    pull: (limit) => stream.pull(limit),
    check() {
      if (stream.used < body.length) {
        throw new Rejection(TRAILING_BYTES, `${body.length - stream.used} bytes follow the DEFLATE stream`);
      }
    },
    held: () => stream.held,
  };
}

// A source of a body's bytes for `odrg.records`, which takes from the parts only what a
// record needs, and counts what it took.
function partSource(parts) {
  let pending = new Uint8Array(0);
  let offset = 0;
  const source = {
    taken: 0,
    take(count, what) {
      while (pending.length - offset < count) {
        const more = parts.pull(count - (pending.length - offset));
        if (more.length === 0) {
          throw new Rejection(TRUNCATED, `the file ends inside ${what}`);
        }
        source.taken += more.length;
        const joined = new Uint8Array(pending.length - offset + more.length);
        joined.set(pending.subarray(offset));
        joined.set(more, pending.length - offset);
        pending = joined;
        offset = 0;
      }
      const taken = pending.subarray(offset, offset + count);
      offset += count;
      return taken;
    },
    rest() {
      let left = pending.length - offset;
      for (let more = parts.pull(BYTES_A_STEP); more.length > 0; more = parts.pull(BYTES_A_STEP)) {
        left += more.length;
      }
      return left;
    },
  };
  return source;
}

// Makes the preview of an ODRG file or an ODRGX container in steps. `step()` does a bounded
// part of the work and gives whether the preview is made; `preview` is then its bytes. A
// file the library's readers refuse is refused by the step that reads the fault, and one
// whose preview stays too large by the last step. The frames of a file are read in two
// passes over its body, the second after the first has judged the whole of it, so that a
// compressed body is never held inflated: at most 256 records and 1 MiB of body a step.
// `held()` is the bytes of the body's output the maker holds.
export function maker(data) {
  let stage = "start";
  let width = 0;
  let height = 0;
  let loop = 0;
  let times = [];
  const samples = [];
  let file = null;
  let head = null;
  let container = null;
  let parts = null;
  let read = null;
  let source = null;
  let decoded = null;
  let elapsed = 0;
  let total = 0;
  let last = null;
  let made = null;
  // The first pass: the palette to pass over, the start of the record being read, and the
  // bytes of it still to come.
  let skip = 0;
  const start = new Uint8Array(odrg.RECORD_START_SIZE);
  let have = 0;
  let inRecord = false;
  let waitingMs = 0;
  let counted = 0;
  let counting = true;

  const begin = () => {
    if (odrgx.isContainer(data)) {
      container = odrgx.readHeader(data);
      width = container.width;
      height = container.height;
      if (container.type !== odrgx.TYPES.frames) {
        decoded = odrgx.decode(data);
        loop = container.loopMs;
        times = timesOf(loop);
        stage = "drawings";
        return;
      }
      file = odrgx.payloadOf(data);
      head = odrg.header(file);
      if (head.width !== container.width || head.height !== container.height) {
        throw new Rejection(CANVAS_MISMATCH, `the container's canvas is ${container.width} x ${container.height} and its frames' ${head.width} x ${head.height}`);
      }
    } else {
      file = data;
      head = odrg.header(data);
      width = head.width;
      height = head.height;
    }
    parts = bodyParts(file, head.compressed);
    skip = 3 * head.paletteSize;
    stage = "first";
  };

  // Reads a part of the body for the stream's verdicts and, of a file, the loop: the
  // durations of the records whose bytes all came, as `odrg.reader`'s `loopMs` sums them.
  const firstPass = () => {
    const part = parts.pull(BYTES_A_STEP);
    if (part.length === 0) {
      parts.check();
      if (skip > 0 && !inRecord) {
        throw new Rejection(TRUNCATED, "the file ends inside the palette");
      }
      loop = container === null ? total : container.loopMs;
      times = timesOf(loop);
      parts = bodyParts(file, head.compressed);
      source = partSource(parts);
      read = odrg.records(head, source);
      stage = "records";
      return;
    }
    for (let at = 0; at < part.length && counting;) {
      if (skip > 0) {
        const passed = Math.min(skip, part.length - at);
        skip -= passed;
        at += passed;
        if (skip === 0 && inRecord) {
          total += waitingMs;
          counted += 1;
          inRecord = false;
          counting = counted < head.frameCount;
        }
        continue;
      }
      start[have] = part[at];
      have += 1;
      at += 1;
      if (have === odrg.RECORD_START_SIZE) {
        have = 0;
        const length = start[2] | (start[3] << 8);
        if (length < 2) {
          counting = false;
          break;
        }
        waitingMs = start[0] | (start[1] << 8);
        skip = length - 1;
        inRecord = true;
      }
    }
  };

  const records = () => {
    const before = source.taken;
    for (let count = 0; count < RECORDS_A_STEP && source.taken - before < BYTES_A_STEP; count += 1) {
      const record = read.next();
      if (record === null) {
        if (container !== null) {
          odrgx.checkPayloadSize(container, data);
          odrgx.checkLoop(container, elapsed);
        }
        while (samples.length < PICTURES) {
          samples.push(last === null ? new Uint8Array(3 * width * height) : new Uint8Array(last));
        }
        stage = "encode";
        return;
      }
      while (samples.length < PICTURES && times[samples.length] < elapsed + record.ms) {
        samples.push(new Uint8Array(record.picture));
      }
      elapsed += record.ms;
      last = record.picture;
    }
  };

  const drawings = () => {
    for (let count = 0; count < DRAWINGS_A_STEP && samples.length < PICTURES; count += 1) {
      samples.push(odrgx.pictureAt(decoded, times[samples.length], 1));
    }
    if (samples.length === PICTURES) {
      stage = "encode";
    }
  };

  const encodeAll = () => {
    let size = 0;
    for (const count of [24, 12, 6]) {
      const every = PICTURES / count;
      const chosen = samples.filter((picture, k) => k % every === 0);
      const gif = encode(chosen, width, height, delayOf(loop, count));
      if (gif.length <= LARGEST) {
        made = gif;
        return;
      }
      size = gif.length;
    }
    throw new Rejection(PREVIEW_TOO_LARGE, `the preview of 6 pictures is ${size} bytes, above ${LARGEST}`);
  };

  const step = () => {
    if (made !== null) {
      return true;
    }
    if (stage === "start") {
      begin();
    } else if (stage === "first") {
      firstPass();
    } else if (stage === "records") {
      records();
    } else if (stage === "drawings") {
      drawings();
    } else {
      encodeAll();
    }
    return made !== null;
  };

  return {
    step,
    get done() {
      return made !== null;
    },
    get preview() {
      return made;
    },
    held: () => (parts === null ? 0 : parts.held()),
  };
}

// The preview of an ODRG file or an ODRGX container, made at once.
export function make(data) {
  const making = maker(data);
  while (!making.step()) {
    // Each step does its part.
  }
  return making.preview;
}

// The GIF of some pictures of a canvas, each three bytes a pixel with the bottom row first,
// each shown for `delay` hundredths of a second.
export function encode(pictures, width, height, delay) {
  const counts = new Map();
  for (const picture of pictures) {
    for (let at = 0; at < picture.length; at += 3) {
      const colour = (picture[at] << 16) | (picture[at + 1] << 8) | picture[at + 2];
      counts.set(colour, (counts.get(colour) || 0) + 1);
    }
  }
  let colours = [...counts.keys()];
  if (colours.length > MOST_COLOURS) {
    colours.sort((a, b) => counts.get(b) - counts.get(a) || a - b);
    colours = colours.slice(0, MOST_COLOURS);
  }
  colours.sort((a, b) => a - b);
  let size = 2;
  let bits = 1;
  while (size < colours.length) {
    size *= 2;
    bits += 1;
  }
  const table = new Uint8Array(3 * size);
  colours.forEach((colour, index) => {
    table[3 * index] = (colour >> 16) & 0xff;
    table[3 * index + 1] = (colour >> 8) & 0xff;
    table[3 * index + 2] = colour & 0xff;
  });
  const indexes = new Map();
  const indexOf = (colour) => {
    let found = indexes.get(colour);
    if (found === undefined) {
      const r = (colour >> 16) & 0xff;
      const g = (colour >> 8) & 0xff;
      const b = colour & 0xff;
      let nearest = Infinity;
      for (let index = 0; index < size; index += 1) {
        const dr = r - table[3 * index];
        const dg = g - table[3 * index + 1];
        const db = b - table[3 * index + 2];
        const distance = dr * dr + dg * dg + db * db;
        if (distance < nearest) {
          nearest = distance;
          found = index;
        }
      }
      indexes.set(colour, found);
    }
    return found;
  };

  const out = [];
  const push = (...bytes) => {
    for (const byte of bytes) {
      out.push(byte);
    }
  };
  const u16 = (value) => push(value & 0xff, (value >> 8) & 0xff);
  for (const character of "GIF89a") {
    push(character.charCodeAt(0));
  }
  u16(width);
  u16(height);
  push(0x80 | 0x70 | (bits - 1), 0, 0);
  for (const byte of table) {
    push(byte);
  }
  push(0x21, 0xff, 0x0b);
  for (const character of "NETSCAPE2.0") {
    push(character.charCodeAt(0));
  }
  push(0x03, 0x01, 0x00, 0x00, 0x00);
  const minimum = Math.max(2, bits);
  const pixels = new Uint8Array(width * height);
  for (const picture of pictures) {
    for (let row = 0; row < height; row += 1) {
      const from = (height - 1 - row) * width;
      for (let column = 0; column < width; column += 1) {
        const at = 3 * (from + column);
        pixels[row * width + column] = indexOf((picture[at] << 16) | (picture[at + 1] << 8) | picture[at + 2]);
      }
    }
    push(0x21, 0xf9, 0x04, 0x04);
    u16(delay);
    push(0x00, 0x00);
    push(0x2c);
    u16(0);
    u16(0);
    u16(width);
    u16(height);
    push(0x00, minimum);
    const codes = lzw(pixels, minimum);
    for (let at = 0; at < codes.length; at += SUB_BLOCK) {
      const block = codes.subarray(at, Math.min(codes.length, at + SUB_BLOCK));
      push(block.length);
      for (const byte of block) {
        push(byte);
      }
    }
    push(0x00);
  }
  push(0x3b);
  return Uint8Array.from(out);
}

// The LZW code stream of a GIF image: a clear code first and whenever the table is full,
// the codes packed least significant bit first, the end code last.
function lzw(indexes, minimum) {
  const clear = 1 << minimum;
  const end = clear + 1;
  const bytes = [];
  let width = minimum + 1;
  let next = end + 1;
  let held = 0;
  let count = 0;
  let table = new Map();
  const emit = (code) => {
    held |= code << count;
    count += width;
    while (count >= 8) {
      bytes.push(held & 0xff);
      held >>>= 8;
      count -= 8;
    }
  };
  emit(clear);
  let prefix = indexes[0];
  for (let at = 1; at < indexes.length; at += 1) {
    const index = indexes[at];
    const key = prefix * 256 + index;
    const known = table.get(key);
    if (known !== undefined) {
      prefix = known;
      continue;
    }
    emit(prefix);
    if (next === MOST_CODES) {
      emit(clear);
      table = new Map();
      width = minimum + 1;
      next = end + 1;
    } else {
      if (next >= 1 << width) {
        width += 1;
      }
      table.set(key, next);
      next += 1;
    }
    prefix = index;
  }
  emit(prefix);
  emit(end);
  if (count > 0) {
    bytes.push(held & 0xff);
  }
  return Uint8Array.from(bytes);
}
