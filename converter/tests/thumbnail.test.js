import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import test from "node:test";
import zlib from "node:zlib";

import * as gif from "../cli/gif.js";
import {errors, odrg, odrgx, thumbnail} from "../lib/index.js";
import {ROOT, utf8} from "./support.js";

const VECTORS = path.join(ROOT, "tests", "vectors");
const found = await gif.reader();
if (found.failure !== undefined) {
  throw found.failure;
}
const {GifReader} = found;

// A row of whole numbers from a seed.
function numbers(seed) {
  let state = seed;
  return (below) => {
    state = (Math.imul(state, 1103515245) + 12345) >>> 0;
    return (state >>> 8) % below;
  };
}

function colourOf(picture, pixel) {
  return (picture[3 * pixel] << 16) | (picture[3 * pixel + 1] << 8) | picture[3 * pixel + 2];
}

// The parts of a GIF, read block by block: the screen, the global table, the extensions
// and every image with its control extension, its code size and its sub-blocks.
function blocks(bytes) {
  assert.equal(String.fromCharCode(...bytes.subarray(0, 6)), "GIF89a");
  const width = bytes[6] | (bytes[7] << 8);
  const height = bytes[8] | (bytes[9] << 8);
  const packed = bytes[10];
  assert.equal(packed & 0xf8, 0xf0, "a global table, a colour resolution of 8 bits, not sorted");
  const size = 2 << (packed & 7);
  const table = bytes.subarray(13, 13 + 3 * size);
  let at = 13 + 3 * size;
  const images = [];
  const applications = [];
  let control = null;
  for (;;) {
    const kind = bytes[at];
    if (kind === 0x3b) {
      assert.equal(at, bytes.length - 1, "the trailer is the last byte");
      break;
    }
    if (kind === 0x21) {
      const label = bytes[at + 1];
      at += 2;
      const parts = [];
      while (bytes[at] !== 0) {
        parts.push(bytes.subarray(at + 1, at + 1 + bytes[at]));
        at += 1 + bytes[at];
      }
      at += 1;
      if (label === 0xf9) {
        control = parts[0];
      } else {
        applications.push(parts);
      }
      continue;
    }
    assert.equal(kind, 0x2c, `a block at ${at}`);
    const descriptor = bytes.subarray(at + 1, at + 10);
    const minimum = bytes[at + 10];
    at += 11;
    const lengths = [];
    while (bytes[at] !== 0) {
      lengths.push(bytes[at]);
      at += 1 + bytes[at];
    }
    at += 1;
    images.push({control, descriptor, minimum, lengths});
    control = null;
  }
  return {width, height, size, table, images, applications};
}

// What a GIF shows: its size, its loop count, and for each picture its delay, its disposal
// and its pixels as colours, the top row first.
function shown(bytes) {
  const reader = new GifReader(Buffer.from(bytes));
  const pictures = [];
  const rgba = new Uint8Array(4 * reader.width * reader.height);
  for (let frame = 0; frame < reader.numFrames(); frame += 1) {
    const info = reader.frameInfo(frame);
    reader.decodeAndBlitFrameRGBA(frame, rgba);
    const colours = [];
    for (let pixel = 0; pixel < reader.width * reader.height; pixel += 1) {
      colours.push((rgba[4 * pixel] << 16) | (rgba[4 * pixel + 1] << 8) | rgba[4 * pixel + 2]);
    }
    pictures.push({delay: info.delay, disposal: info.disposal, transparent: info.transparent_index, colours});
  }
  return {width: reader.width, height: reader.height, loop: reader.loopCount(), pictures};
}

// The palette the rules give for some pictures, as numbers of 24 bits, padded with black.
function paletteFor(pictures) {
  const counts = new Map();
  for (const picture of pictures) {
    for (let pixel = 0; pixel < picture.length / 3; pixel += 1) {
      const colour = colourOf(picture, pixel);
      counts.set(colour, (counts.get(colour) || 0) + 1);
    }
  }
  const colours = [...counts.entries()]
    .sort((a, b) => b[1] - a[1] || a[0] - b[0])
    .slice(0, 256)
    .map(([colour]) => colour)
    .sort((a, b) => a - b);
  let size = 2;
  while (size < colours.length) {
    size *= 2;
  }
  return [...colours, ...new Array(size - colours.length).fill(0)];
}

function nearest(palette, colour) {
  let best = 0;
  let distance = Infinity;
  palette.forEach((entry, index) => {
    const d = [16, 8, 0].reduce((sum, shift) => sum + (((colour >> shift) & 255) - ((entry >> shift) & 255)) ** 2, 0);
    if (d < distance) {
      distance = d;
      best = index;
    }
  });
  return palette[best];
}

// A picture of the library, bottom row first, as the colours of a GIF, top row first, each
// the nearest colour of the palette.
function asShown(picture, width, height, palette) {
  const colours = [];
  for (let row = 0; row < height; row += 1) {
    for (let column = 0; column < width; column += 1) {
      colours.push(nearest(palette, colourOf(picture, (height - 1 - row) * width + column)));
    }
  }
  return colours;
}

function tableOf(bytes) {
  const {table, size} = blocks(bytes);
  return Array.from({length: size}, (unused, index) => (table[3 * index] << 16) | (table[3 * index + 1] << 8) | table[3 * index + 2]);
}

// The picture of decoded records on screen at a time.
function pictureAt(records, t) {
  let start = 0;
  for (const record of records) {
    if (t < start + record.ms) {
      return record.picture;
    }
    start += record.ms;
  }
  return records[records.length - 1].picture;
}

// The pictures of a file's preview as the rules give them, and its loop.
function expectedPictures(data, count) {
  let loop;
  let at;
  if (odrgx.isContainer(data)) {
    const decoded = odrgx.decode(data);
    loop = decoded.header.loopMs;
    at = decoded.type === "frames" ? (t) => pictureAt(decoded.records, t) : (t) => odrgx.pictureAt(decoded, t, 1);
  } else {
    const decoded = odrg.decode(data);
    loop = decoded.records.reduce((sum, record) => sum + record.ms, 0);
    at = (t) => pictureAt(decoded.records, t);
  }
  return {loop, pictures: Array.from({length: count}, (unused, k) => at(Math.floor((k * loop) / count)))};
}

function checkPreview(data, preview, count) {
  const {width, height} = odrgx.isContainer(data) ? odrgx.readHeader(data) : odrg.header(data);
  const {loop, pictures} = expectedPictures(data, count);
  const palette = paletteFor(pictures);
  assert.deepEqual(tableOf(preview), palette, "the palette");
  const gifShown = shown(preview);
  assert.equal(gifShown.width, width);
  assert.equal(gifShown.height, height);
  assert.equal(gifShown.loop, 0, "it loops forever");
  assert.equal(gifShown.pictures.length, count);
  gifShown.pictures.forEach((picture, k) => {
    assert.equal(picture.delay, thumbnail.delayOf(loop, count), `the delay of picture ${k}`);
    assert.equal(picture.disposal, 1);
    assert.equal(picture.transparent, null);
    assert.deepEqual(picture.colours, asShown(pictures[k], width, height, palette), `picture ${k}`);
  });
  const parts = blocks(preview);
  assert.deepEqual(parts.applications.map((application) => Buffer.from(application[0]).toString("latin1")), ["NETSCAPE2.0"]);
  assert.deepEqual([...parts.applications[0][1]], [1, 0, 0]);
  for (const image of parts.images) {
    assert.deepEqual([...image.control], [0x04, thumbnail.delayOf(loop, count) & 255, thumbnail.delayOf(loop, count) >> 8, 0]);
    assert.deepEqual([...image.descriptor], [0, 0, 0, 0, width & 255, width >> 8, height & 255, height >> 8, 0]);
    assert.equal(image.minimum, Math.max(2, Math.log2(parts.size)));
    assert.ok(image.lengths.slice(0, -1).every((length) => length === 255), "full sub-blocks before the last");
    assert.ok(image.lengths.at(-1) >= 1 && image.lengths.at(-1) <= 255);
  }
}

function animation(width, height, frames) {
  return odrg.encode({width, height, frames});
}

// Frames of one colour each, from a list of colours and durations.
function plainFrames(width, height, list) {
  return list.map(([colour, ms]) => {
    const picture = new Uint8Array(3 * width * height);
    for (let pixel = 0; pixel < width * height; pixel += 1) {
      picture.set([colour >> 16, (colour >> 8) & 255, colour & 255], 3 * pixel);
    }
    return {ms, picture};
  });
}

// Frames of random colours from a palette of 256, at 40 ms each.
function noise(width, height, count, seed) {
  const from = numbers(seed);
  const palette = Array.from({length: 256}, () => [from(256), from(256), from(256)]);
  return Array.from({length: count}, () => {
    const picture = new Uint8Array(3 * width * height);
    for (let pixel = 0; pixel < width * height; pixel += 1) {
      picture.set(palette[from(256)], 3 * pixel);
    }
    return {ms: 40, picture};
  });
}

function reasonOf(action) {
  try {
    action();
  } catch (error) {
    if (error instanceof errors.Rejection) {
      return error.reason;
    }
    throw error;
  }
  return null;
}

function filesOf(folder) {
  return fs.readdirSync(folder).filter((name) => /\.odrgx?$/.test(name)).sort().map((name) => path.join(folder, name));
}

test("the key is the CRC-32 of zlib and PNG and the size", () => {
  assert.equal(thumbnail.crc32(utf8("123456789")), 0xcbf43926);
  assert.equal(thumbnail.crc32(new Uint8Array(0)), 0);
  for (const file of filesOf(path.join(ROOT, "test-animations"))) {
    const data = new Uint8Array(fs.readFileSync(file));
    assert.equal(thumbnail.keyOf(data), `${zlib.crc32(data).toString(16).padStart(8, "0")}-${data.length}`);
  }
  assert.match(thumbnail.keyOf(Uint8Array.of(1)), /^[0-9a-f]{8}-1$/);
});

test("the times are at twenty-fourths of the loop and the delays rounded to 10 ms within their bounds", () => {
  assert.deepEqual(thumbnail.timesOf(2400), Array.from({length: 24}, (unused, k) => 100 * k));
  assert.deepEqual(thumbnail.timesOf(25).slice(0, 4), [0, 1, 2, 3]);
  assert.equal(thumbnail.timesOf(900000)[23], 862500);
  assert.equal(thumbnail.delayOf(100, 24), 2);
  assert.equal(thumbnail.delayOf(1200, 24), 5);
  assert.equal(thumbnail.delayOf(1320, 24), 6);
  assert.equal(thumbnail.delayOf(2880, 24), 12);
  assert.equal(thumbnail.delayOf(900000, 24), 12);
  assert.equal(thumbnail.delayOf(900000, 12), 24);
  assert.equal(thumbnail.delayOf(900000, 6), 48);
  assert.equal(thumbnail.delayOf(600, 6), 10);
});

test("a preview of frames shows the picture on screen at each time, the top row first", () => {
  const width = 7;
  const height = 3;
  const frames = plainFrames(width, height, [[0x102030, 100], [0xff0000, 50], [0x00ff00, 250], [0x0000ff, 1000], [0xffffff, 1]]);
  // The bottom row of the second frame, the library's first, is another colour, which the
  // GIF shows as its last row.
  for (let column = 0; column < width; column += 1) {
    frames[1].picture.set([1, 2, 3], 3 * column);
  }
  const data = animation(width, height, frames);
  const preview = thumbnail.make(data);
  checkPreview(data, preview, 24);
  const top = shown(preview).pictures[2].colours;
  assert.equal(top[0], 0xff0000);
  assert.equal(top[width * (height - 1)], 0x010203);
});

test("short, three-second and long loops give their own delays", () => {
  for (const ms of [20, 120, 2880, 60000]) {
    const data = animation(4, 2, plainFrames(4, 2, [[0x123456, ms], [0x654321, ms]]));
    checkPreview(data, thumbnail.make(data), 24);
  }
});

test("a text and a clock are drawn at the times of their loop, a clock with the seed 1", () => {
  for (const name of ["texts/valid/finals.slide.odrgx", "texts/valid/multiline.wrap.odrgx", "widgets/valid/analog.odrgx", "widgets/valid/digital.odrgx",
    "widgets/valid/melting.odrgx", "widgets/valid/small.analog.odrgx"]) {
    const data = new Uint8Array(fs.readFileSync(path.join(VECTORS, name)));
    checkPreview(data, thumbnail.make(data), 24);
  }
});

test("every valid vector has its preview, and every invalid one is refused with the reason of the reader", () => {
  for (const folder of ["valid", "containers/valid", "texts/valid", "widgets/valid"]) {
    for (const file of filesOf(path.join(VECTORS, folder))) {
      const data = new Uint8Array(fs.readFileSync(file));
      checkPreview(data, thumbnail.make(data), 24);
    }
  }
  let refused = 0;
  for (const folder of ["invalid", "containers/invalid", "texts/invalid", "widgets/invalid"]) {
    for (const file of filesOf(path.join(VECTORS, folder))) {
      const data = new Uint8Array(fs.readFileSync(file));
      const wanted = reasonOf(() => (odrgx.isContainer(data) ? odrgx.decode(data) : odrg.decode(data)));
      assert.notEqual(wanted, null, file);
      assert.equal(reasonOf(() => thumbnail.make(data)), wanted, file);
      refused += 1;
    }
  }
  assert.ok(refused >= 80, `${refused} invalid vectors`);
});

test("the palette is every colour, or the 256 that cover the most pixels, and a pixel takes the nearest", () => {
  // 300 colours: the first 200 cover two pixels each, the other 100 one each, so the 56
  // smallest of those are kept on the tie.
  const width = 50;
  const height = 10;
  const picture = new Uint8Array(3 * width * height);
  const colour = (n) => [n & 255, (7 * n) & 255, (n >> 2) & 255];
  let pixel = 0;
  for (let n = 0; n < 300; n += 1) {
    for (let copy = 0; copy < (n < 200 ? 2 : 1); copy += 1) {
      picture.set(colour(n), 3 * pixel);
      pixel += 1;
    }
  }
  const data = animation(width, height, [{ms: 100, picture}]);
  const preview = thumbnail.make(data);
  checkPreview(data, preview, 24);
  assert.equal(tableOf(preview).length, 256);
  // Three colours: the palette is padded with black to four entries.
  const three = animation(2, 2, plainFrames(2, 2, [[0x000005, 10], [0xff0000, 10], [0x00ff00, 10]]));
  assert.deepEqual(tableOf(thumbnail.make(three)), [0x000005, 0x00ff00, 0xff0000, 0]);
  // One colour: two entries.
  const one = animation(2, 2, plainFrames(2, 2, [[0x808080, 10]]));
  assert.deepEqual(tableOf(thumbnail.make(one)), [0x808080, 0]);
  checkPreview(one, thumbnail.make(one), 24);
});

test("a preview above 65,536 bytes is made again with 12 pictures, then 6, and refused above even then", () => {
  const twelve = animation(60, 60, noise(60, 60, 24, 1));
  const madeTwelve = thumbnail.make(twelve);
  assert.ok(madeTwelve.length <= thumbnail.LARGEST);
  assert.equal(shown(madeTwelve).pictures.length, 12);
  checkPreview(twelve, madeTwelve, 12);
  const six = animation(90, 70, noise(90, 70, 24, 2));
  const madeSix = thumbnail.make(six);
  assert.equal(shown(madeSix).pictures.length, 6);
  checkPreview(six, madeSix, 6);
  const tooLarge = animation(147, 147, noise(147, 147, 24, 3));
  assert.equal(reasonOf(() => thumbnail.make(tooLarge)), errors.PREVIEW_TOO_LARGE);
});

test("the walk reads a long file in bounded steps and keeps no picture it does not sample", () => {
  const count = 3000;
  const frames = Array.from({length: count}, (unused, i) => plainFrames(3, 2, [[i % 2 === 0 ? 0x111111 : 0x222222, 1]])[0]);
  const data = animation(3, 2, frames);
  const read = odrg.reader(data);
  assert.equal(read.frameCount, count);
  assert.equal(read.loopMs(), count);
  const seen = new Set();
  for (let record = read.next(); record !== null; record = read.next()) {
    assert.ok(!seen.has(record.picture), "each record gives its own picture");
    seen.add(record.picture);
  }
  assert.equal(seen.size, count);
  assert.equal(read.next(), null);
  const making = thumbnail.maker(data);
  let steps = 0;
  while (!making.step()) {
    steps += 1;
  }
  steps += 1;
  assert.equal(steps, 1 + Math.ceil((count + 1) / thumbnail.RECORDS_A_STEP) + 1);
  assert.ok(making.done);
  assert.deepEqual(making.preview, thumbnail.make(data));
  checkPreview(data, making.preview, 24);
});

test("the readers decode as before and sum a file they would refuse without refusing", () => {
  for (const file of filesOf(path.join(VECTORS, "valid"))) {
    const data = new Uint8Array(fs.readFileSync(file));
    const decoded = odrg.decode(data);
    assert.equal(odrg.reader(data).loopMs(), decoded.records.reduce((sum, record) => sum + record.ms, 0), file);
  }
  for (const file of filesOf(path.join(VECTORS, "invalid"))) {
    const data = new Uint8Array(fs.readFileSync(file));
    let read = null;
    try {
      read = odrg.reader(data);
    } catch (error) {
      assert.ok(error instanceof errors.Rejection);
      continue;
    }
    assert.equal(typeof read.loopMs(), "number", file);
  }
  for (const file of filesOf(path.join(VECTORS, "containers", "valid"))) {
    const data = new Uint8Array(fs.readFileSync(file));
    const read = odrgx.framesReader(data);
    assert.equal(read.loopMs(), odrgx.readHeader(data).loopMs);
  }
});
