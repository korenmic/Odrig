// Builds the reference pictures of this folder: what the player draws of a text or a clock of
// tests/vectors/ at a time, as the converter's library draws it. Run from the repository
// root: node tests/vectors/procedural/build.mjs
//
// manifest.json lists every picture: its PNG file, the container it is of, the milliseconds
// into the turn, and for a clock the seed of the turn. The core's suite, the converter's
// and the emulator's draw each and find every pixel the same.

import {mkdirSync, readFileSync, readdirSync, rmSync, writeFileSync} from "node:fs";
import {dirname, join} from "node:path";
import {fileURLToPath} from "node:url";
import {deflateSync} from "node:zlib";

const HERE = dirname(fileURLToPath(import.meta.url));
const VECTORS = join(HERE, "..");
const {odrgx} = await import(new URL("../../../converter/lib/index.js", import.meta.url).href);

// Each case: the container, relative to tests/vectors/, the times to draw it at, and for a
// clock the seed of its turn.
export const CASES = [
  ["texts/valid/english.static.odrgx", [0]],
  ["texts/valid/hebrew.marquee.odrgx", [0, 800, 2000, 3500]],
  ["texts/valid/mixed.pan.odrgx", [0, 1500, 4000, 7000]],
  ["texts/valid/multiline.wrap.odrgx", [0]],
  ["texts/valid/finals.slide.odrgx", [300, 1200, 2400]],
  ["texts/valid/tall.up.odrgx", [1000, 5000, 9000]],
  ["texts/valid/rtl.down.odrgx", [0, 900, 2000]],
  ["widgets/valid/analog.odrgx", [0, 15000], 1],
  ["widgets/valid/analog.odrgx", [0, 29980], 2864038069],
  ["widgets/valid/digital.odrgx", [0, 500, 12000], 1],
  ["widgets/valid/digital.odrgx", [250, 750], 77],
  ["widgets/valid/melting.odrgx", [0, 3500, 44980], 1],
  ["widgets/valid/melting.odrgx", [0, 20000], 424242],
  ["widgets/valid/small.analog.odrgx", [0, 980], 9],
];

// The picture of a case: three bytes for each pixel in the pixel order of docs/format.md.
export function picture(file, ms, seed) {
  const decoded = odrgx.decode(new Uint8Array(readFileSync(join(VECTORS, file))));
  return {width: decoded.header.width, height: decoded.header.height, pixels: odrgx.pictureAt(decoded, ms, seed)};
}

const CRC_TABLE = Array.from({length: 256}, (_, n) => {
  let c = n;
  for (let k = 0; k < 8; k += 1) c = c & 1 ? 0xedb88320 ^ (c >>> 1) : c >>> 1;
  return c >>> 0;
});

function crc32(bytes) {
  let c = 0xffffffff;
  for (const byte of bytes) c = CRC_TABLE[(c ^ byte) & 0xff] ^ (c >>> 8);
  return (c ^ 0xffffffff) >>> 0;
}

function chunk(type, data) {
  const head = Buffer.alloc(4);
  head.writeUInt32BE(data.length);
  const body = Buffer.concat([Buffer.from(type, "ascii"), Buffer.from(data)]);
  const tail = Buffer.alloc(4);
  tail.writeUInt32BE(crc32(body));
  return Buffer.concat([head, body, tail]);
}

// A PNG of a picture, its top row first, as an image is stored; the format's bottom row
// comes last.
export function png({width, height, pixels}) {
  const rows = Buffer.alloc((3 * width + 1) * height);
  for (let row = 0; row < height; row += 1) {
    const from = (height - 1 - row) * width * 3;
    pixels.subarray(from, from + 3 * width).forEach((byte, at) => {
      rows[row * (3 * width + 1) + 1 + at] = byte;
    });
  }
  const header = Buffer.alloc(13);
  header.writeUInt32BE(width, 0);
  header.writeUInt32BE(height, 4);
  header[8] = 8;
  header[9] = 2;
  return Buffer.concat([Buffer.from([137, 80, 78, 71, 13, 10, 26, 10]), chunk("IHDR", header), chunk("IDAT", deflateSync(rows, {level: 9})), chunk("IEND", Buffer.alloc(0))]);
}

// The manifest and the pixels of every picture, by the name of its PNG file.
export function pictures() {
  const manifest = [];
  const made = new Map();
  for (const [file, times, seed] of CASES) {
    for (const ms of times) {
      const stem = file.split("/").pop().replace(/\.odrgx$/, "");
      const name = seed === undefined ? `${stem}.${ms}.png` : `${stem}.${seed}.${ms}.png`;
      manifest.push(seed === undefined ? {picture: name, file, ms} : {picture: name, file, ms, seed});
      made.set(name, picture(file, ms, seed));
    }
  }
  return {manifest, made};
}

function main() {
  for (const name of readdirSync(HERE)) {
    if (name.endsWith(".png") || name === "manifest.json") rmSync(join(HERE, name));
  }
  const {manifest, made} = pictures();
  for (const [name, one] of made) writeFileSync(join(HERE, name), png(one));
  writeFileSync(join(HERE, "manifest.json"), `${JSON.stringify(manifest, null, 2)}\n`);
  console.log(`${made.size} pictures`);
}

if (process.argv[1] === fileURLToPath(import.meta.url)) {
  mkdirSync(HERE, {recursive: true});
  main();
}
