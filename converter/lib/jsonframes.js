// JSON frames, the tracked source format of an animation: strict reading, canonical
// writing.
//
// A picture is a `Uint8Array` of 3 * W * H bytes: red, green and blue for each pixel, in
// the pixel order of docs/format.md (bottom row first, each row left to right). A frame is
// `{ms, picture}` and an animation `{width, height, frames}`. `ms` is a whole number of
// `whole.js`.

import {BAD_JSON, BAD_PIXEL_COUNT, BAD_VERSION, MISSING_MEMBER, NO_FRAMES, Rejection} from "./errors.js";
import * as strictjson from "./strictjson.js";
import {plus, times} from "./whole.js";

export const VERSION = 1;
export const WHITE = 0xffffff;

const MEMBERS = ["version", "width", "height", "frames"];
const FRAME_MEMBERS = ["ms", "pixels"];

// Reads a JSON frames file given as bytes. Frames are kept as the file lists them.
export function loads(bytes) {
  const top = strictjson.loads(bytes);
  if (!(top instanceof Map)) {
    throw new Rejection(BAD_JSON, "the top level is not an object");
  }
  if (!top.has("version")) {
    throw new Rejection(MISSING_MEMBER, 'the file has no member "version"');
  }
  const version = strictjson.integer(top.get("version"), null, null, "version");
  if (version !== VERSION) {
    throw new Rejection(BAD_VERSION, `version is ${version}, not ${VERSION}`);
  }
  strictjson.members(top, MEMBERS);
  const width = strictjson.integer(top.get("width"), 1, null, "width");
  const height = strictjson.integer(top.get("height"), 1, null, "height");
  const listed = strictjson.array(top.get("frames"), "frames");
  if (listed.length === 0) {
    throw new Rejection(NO_FRAMES, "frames is empty");
  }
  const count = times(width, height);
  const frames = [];
  for (let number = 1; number <= listed.length; number += 1) {
    const frame = listed[number - 1];
    const what = `frame ${number}`;
    strictjson.members(frame, FRAME_MEMBERS, [], what);
    const ms = strictjson.integer(frame.get("ms"), 1, null, `ms of ${what}`);
    const pixels = strictjson.array(frame.get("pixels"), `pixels of ${what}`);
    if (pixels.length !== count) {
      throw new Rejection(BAD_PIXEL_COUNT, `${what} has ${pixels.length} pixels, not ${width} * ${height} = ${count}`);
    }
    frames.push({ms, picture: pictureOf(pixels, what)});
  }
  return {width, height, frames};
}

// The picture of a `pixels` array. The entries are gone through in order, so the first one
// that is no colour decides the reason.
function pictureOf(pixels, what) {
  const count = pixels.length;
  const picture = new Uint8Array(3 * count);
  for (let position = 0; position < count; position += 1) {
    const pixel = pixels[position];
    if (typeof pixel !== "number" || pixel < 0 || pixel > WHITE) {
      strictjson.integer(pixel, 0, WHITE, `pixel ${position} of ${what}`);
    }
    picture[3 * position] = pixel >> 16;
    picture[3 * position + 1] = (pixel >> 8) & 0xff;
    picture[3 * position + 2] = pixel & 0xff;
  }
  return picture;
}

// Whether two pictures hold the same bytes.
export function same(a, b) {
  if (a === b) {
    return true;
  }
  if (a.length !== b.length) {
    return false;
  }
  for (let i = 0; i < a.length; i += 1) {
    if (a[i] !== b[i]) {
      return false;
    }
  }
  return true;
}

// The frames with consecutive identical pictures joined into one, durations added.
export function merged(frames) {
  const result = [];
  for (const {ms, picture} of frames) {
    const last = result.length > 0 ? result[result.length - 1] : null;
    if (last !== null && same(last.picture, picture)) {
      result[result.length - 1] = {ms: plus(last.ms, ms), picture: last.picture};
    } else {
      result.push({ms, picture});
    }
  }
  return result;
}

// The canonical bytes of a JSON frames file, with identical neighbours merged.
//
// `merge: false` keeps every frame as given: one frame for every frame record, as the
// expected frames of the test vectors are written.
export function dumps(animation, {merge = true} = {}) {
  const {width, height} = animation;
  if (!(width >= 1) || !(height >= 1) || animation.frames.length === 0) {
    throw new RangeError("an animation has a canvas and at least one frame");
  }
  const size = 3 * width * height;
  const lines = [];
  for (const {ms, picture} of merge ? merged(animation.frames) : animation.frames) {
    if (!(ms >= 1) || picture.length !== size) {
      throw new RangeError("a frame lasts at least 1 ms and has 3 * W * H bytes");
    }
    lines.push(`    {"ms": ${ms}, "pixels": [${colours(picture).join(", ")}]}`);
  }
  const text =
    "{\n" +
    `  "version": ${VERSION},\n` +
    `  "width": ${width},\n` +
    `  "height": ${height},\n` +
    '  "frames": [\n' +
    lines.join(",\n") +
    "\n" +
    "  ]\n" +
    "}\n";
  return new TextEncoder().encode(text);
}

// The colour of every pixel of a picture as the whole number
// red * 65536 + green * 256 + blue.
export function colours(picture) {
  const count = (picture.length - (picture.length % 3)) / 3;
  const result = new Array(count);
  for (let position = 0; position < count; position += 1) {
    result[position] = picture[3 * position] * 65536 + picture[3 * position + 1] * 256 + picture[3 * position + 2];
  }
  return result;
}

// The number of different colours that appear in the pictures of the frames.
export function colourCount(frames) {
  const seen = new Uint8Array(1 << 21);
  let count = 0;
  let before = null;
  for (const {picture} of frames) {
    if (picture === before) {
      continue;
    }
    before = picture;
    for (let i = 0; i + 2 < picture.length; i += 3) {
      const colour = picture[i] * 65536 + picture[i + 1] * 256 + picture[i + 2];
      const bit = 1 << (colour & 7);
      if ((seen[colour >> 3] & bit) === 0) {
        seen[colour >> 3] |= bit;
        count += 1;
      }
    }
  }
  return count;
}
