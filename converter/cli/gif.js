// GIF files through the reader of the package omggif, and the pictures of their frames.
//
// The package draws one frame. The picture that is on screen with each frame is built
// here, by the rules of the GIF format as browsers apply them:
//
// 1. The canvas has the size of the logical screen, and every pixel of it is transparent.
// 2. Before a frame is drawn, the disposal of the frame before is applied to the rectangle
//    of the frame before: 0 and 1 leave it, 2 makes it transparent, 3 gives it back what it
//    held before that frame was drawn.
// 3. The frame is drawn into its rectangle: a pixel whose index is the frame's transparent
//    index is left as it is, every other pixel gets the colour of the frame's palette and
//    is opaque.
// 4. The picture of the frame is the canvas as it is then.

import fs from "node:fs";

import {errors} from "../lib/index.js";
import * as files from "./files.js";
import {DECODER_MISSING, installCommand} from "./video.js";

const MAKE_TRANSPARENT = 2;
const GIVE_BACK = 3;

// The reader of the package, or the failure that says how to install the package.
export async function reader() {
  try {
    const module = await import("omggif");
    return {GifReader: module.default.GifReader};
  } catch (error) {
    if (error === null || typeof error !== "object" || error.code !== "ERR_MODULE_NOT_FOUND") {
      throw error;
    }
    const detail = `the package omggif, which reads GIF files, is not installed; install it with: ${installCommand()}`;
    return {failure: new errors.Rejection(DECODER_MISSING, detail)};
  }
}

function unreadable(what) {
  return new errors.Rejection(errors.UNREADABLE_MEDIA, `the GIF cannot be decoded: ${what}`);
}

// Runs an action of the package and gives what the package wrote meanwhile: it reports a
// frame whose data is shorter or longer than the frame by writing a warning.
function watched(action) {
  const written = [];
  const log = console.log;
  console.log = (...words) => {
    written.push(words.join(" "));
  };
  try {
    action();
  } finally {
    console.log = log;
  }
  return written;
}

const LARGEST_CODES = 4096;

// What is wrong with the codes of a frame's data, or null when they spell exactly the
// pixels of the frame.
//
// The package draws a frame without judging its codes, and data that is damaged can keep
// it busy without end. So the codes are gone through here first, as the package reads
// them: the first byte is the size of the first codes, then come blocks of bytes, each led
// by its length. A code must be one the table has, or the one the table gets next; the
// first code after the table was cleared must be a plain colour.
function codeFault(bytes, start, pixels) {
  let p = start;
  const smallest = bytes[p];
  p += 1;
  if (!(smallest >= 1 && smallest <= 11)) {
    return `the size of its first codes is ${smallest}`;
  }
  const clear = 1 << smallest;
  const end = clear + 1;
  let next = end + 1;
  let size = smallest + 1;
  let mask = (1 << size) - 1;
  let held = 0;
  let bits = 0;
  let left = bytes[p];
  p += 1;
  // For each code of the table, how many pixels it spells.
  const lengths = new Uint16Array(LARGEST_CODES);
  let before = -1;
  let beforeLength = 0;
  let spelled = 0;
  for (;;) {
    while (bits < 16 && left !== 0) {
      held |= bytes[p] << bits;
      p += 1;
      bits += 8;
      if (left === 1) {
        left = bytes[p];
        p += 1;
      } else {
        left -= 1;
      }
    }
    if (bits < size) {
      break;
    }
    const code = held & mask;
    held >>= size;
    bits -= size;
    if (code === clear) {
      next = end + 1;
      size = smallest + 1;
      mask = (1 << size) - 1;
      before = -1;
      continue;
    }
    if (code === end) {
      break;
    }
    let length;
    if (code < clear) {
      length = 1;
    } else if (before < 0) {
      return "the code after a cleared table is no colour";
    } else if (code < next) {
      length = lengths[code];
    } else if (code === next && next < LARGEST_CODES) {
      length = beforeLength + 1;
    } else {
      return "a code that the table does not have";
    }
    spelled += length;
    if (spelled > pixels) {
      return "its data spells more pixels than it has";
    }
    if (before >= 0 && next < LARGEST_CODES) {
      lengths[next] = beforeLength + 1;
      next += 1;
      if (next >= mask + 1 && size < 12) {
        size += 1;
        mask = (mask << 1) | 1;
      }
    }
    before = code;
    beforeLength = length;
  }
  return spelled === pixels ? null : "its data spells fewer pixels than it has";
}

function rectangle(canvas, screenWidth, frame) {
  const saved = new Uint8Array(4 * frame.width * frame.height);
  for (let row = 0; row < frame.height; row += 1) {
    const from = 4 * ((frame.y + row) * screenWidth + frame.x);
    saved.set(canvas.subarray(from, from + 4 * frame.width), 4 * row * frame.width);
  }
  return saved;
}

function dispose(canvas, screenWidth, before) {
  if (before.disposal !== MAKE_TRANSPARENT && before.disposal !== GIVE_BACK) {
    return;
  }
  for (let row = 0; row < before.height; row += 1) {
    const at = 4 * ((before.y + row) * screenWidth + before.x);
    if (before.disposal === MAKE_TRANSPARENT) {
      canvas.fill(0, at, at + 4 * before.width);
    } else {
      canvas.set(before.saved.subarray(4 * row * before.width, 4 * (row + 1) * before.width), at);
    }
  }
}

// The frames of a GIF file as the library takes them: `{width, height, rgba, delayMs}`,
// the picture that is on screen with the frame and the delay the file records. The file is
// read when the first frame is asked for, and each frame is decoded when it is asked for.
export function* frames(file, GifReader) {
  let bytes;
  try {
    bytes = fs.readFileSync(file);
  } catch (error) {
    if (!files.isSystemError(error)) {
      throw error;
    }
    throw unreadable(files.why(error));
  }
  let gif;
  try {
    gif = new GifReader(bytes);
  } catch (error) {
    throw unreadable(error instanceof Error ? error.message : String(error));
  }
  const {width, height} = gif;
  const canvas = new Uint8Array(4 * width * height);
  let before = null;
  for (let number = 0; number < gif.numFrames(); number += 1) {
    const frame = gif.frameInfo(number);
    if (frame.x + frame.width > width || frame.y + frame.height > height) {
      throw unreadable(`frame ${number + 1} reaches beyond the screen of ${width} x ${height}`);
    }
    if (frame.palette_offset === null) {
      throw unreadable(`frame ${number + 1} has no palette`);
    }
    const fault = codeFault(bytes, frame.data_offset, frame.width * frame.height);
    if (fault !== null) {
      throw unreadable(`frame ${number + 1}: ${fault}`);
    }
    if (before !== null) {
      dispose(canvas, width, before);
    }
    const saved = frame.disposal === GIVE_BACK ? rectangle(canvas, width, frame) : null;
    let warnings;
    try {
      warnings = watched(() => gif.decodeAndBlitFrameRGBA(number, canvas));
    } catch (error) {
      throw unreadable(`frame ${number + 1}: ${error instanceof Error ? error.message : String(error)}`);
    }
    if (warnings.length > 0) {
      throw unreadable(`frame ${number + 1}: ${warnings[0]}`);
    }
    before = {x: frame.x, y: frame.y, width: frame.width, height: frame.height, disposal: frame.disposal, saved};
    yield {width, height, rgba: canvas.slice(), delayMs: 10 * frame.delay};
  }
}
