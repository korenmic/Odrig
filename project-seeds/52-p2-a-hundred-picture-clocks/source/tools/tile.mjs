// Checks and draws the entries of the inventory of seed 52 with the converter's library.
//
//   node tile.mjs check ENTRY.json...
//       Makes each entry's file as the subcommand `clocks` makes it and reads it back;
//       prints `ok <name> <kind> <bytes>` or `refused <name> <reason>: <detail>`.
//   node tile.mjs sheet OUT.png ENTRY.json... [--times 0,15000] [--seeds 1,2] [--scale 4]
//       One row for each entry: the tile reduced to its colours before erasing (from
//       skeleton.json), its base picture, then its picture at each time with each seed.
//
// An entry is one tile of the inventory: name, tile, kind, about, palette, picture, and
// clock (a dial or a display) or motion. The library is that of the worktree named by the
// environment variable ODRIG_TREE, by default the seed's worktree.

import fs from "node:fs";
import path from "node:path";
import {pathToFileURL} from "node:url";
import {deflateSync} from "node:zlib";

const TREE = process.env.ODRIG_TREE ?? "C:/Users/koren/src/Odrig/scratch/wt-seed52-impl";
const HERE = path.dirname(new URL(import.meta.url).pathname.replace(/^\/([A-Za-z]:)/, "$1"));
const lib = await import(pathToFileURL(path.join(TREE, "converter", "lib", "index.js")).href);
const {odrgx, odrg, strictjson} = lib;
let motion = null;
try {
  motion = await import(pathToFileURL(path.join(TREE, "converter", "lib", "motion.js")).href);
} catch {
  motion = null;
}

const SIZE = 60;

function loadEntries(files) {
  const entries = [];
  for (const file of files) {
    const value = JSON.parse(fs.readFileSync(file, "utf8"));
    if (Array.isArray(value)) entries.push(...value);
    else if (Array.isArray(value.tiles)) entries.push(...value.tiles);
    else entries.push(value);
  }
  return entries;
}

// The JSON source of a dial's or a display's picture clock.
export function sourceOf(entry) {
  return {
    version: 1, type: "widget", width: SIZE, height: SIZE, widget: entry.kind === "dial" ? "picture-dial" : "picture-display",
    seconds: entry.clock.seconds, speed_min: entry.clock.speed_min, speed_max: entry.clock.speed_max, direction: entry.clock.direction,
    turns: entry.clock.turns, palette: entry.palette, picture: entry.picture,
    ...(entry.kind === "dial" ? {hands: entry.clock.hands, caps: entry.clock.caps} : {fields: entry.clock.fields}),
  };
}

function fileOf(entry) {
  if (entry.kind === "motion") {
    if (motion === null) throw new Error("the library has no motion.js yet");
    const bytes = new TextEncoder().encode(JSON.stringify({version: 1, width: SIZE, height: SIZE, tiles: [entry]}));
    const inventory = lib.inventory.loads(bytes);
    return lib.inventory.filesOf(inventory)[0].bytes;
  }
  const source = odrgx.loadsSource(new TextEncoder().encode(JSON.stringify(sourceOf(entry))));
  return odrgx.encodeSource(source);
}

// The pictures of a file at times, three bytes for each pixel in the format's order.
function picturesOf(bytes, times, seed) {
  if (odrgx.isContainer(bytes)) {
    const decoded = odrgx.decode(bytes);
    return times.map((ms) => odrgx.pictureAt(decoded, ms, seed));
  }
  const decoded = odrg.decode(bytes);
  const ends = [];
  let total = 0;
  for (const record of decoded.records) {
    total += record.ms;
    ends.push(total);
  }
  return times.map((ms) => {
    const within = ms % total;
    const index = ends.findIndex((end) => end > within);
    return decoded.records[index].picture;
  });
}

function rgbOfIndices(palette, rows) {
  const picture = new Uint8Array(3 * SIZE * SIZE);
  rows.forEach((row, y) => {
    for (let x = 0; x < SIZE; x += 1) {
      const colour = palette[row.charCodeAt(x) - 48];
      const at = 3 * ((SIZE - 1 - y) * SIZE + x);
      picture[at] = colour >> 16;
      picture[at + 1] = (colour >> 8) & 0xff;
      picture[at + 2] = colour & 0xff;
    }
  });
  return picture;
}

const CRC = Array.from({length: 256}, (_, n) => {
  let c = n;
  for (let k = 0; k < 8; k += 1) c = c & 1 ? 0xedb88320 ^ (c >>> 1) : c >>> 1;
  return c >>> 0;
});

function crc32(bytes) {
  let c = 0xffffffff;
  for (const byte of bytes) c = CRC[(c ^ byte) & 0xff] ^ (c >>> 8);
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

// A PNG of an image of rows of RGB, its top row first.
export function png(width, height, rgb) {
  const rows = Buffer.alloc((3 * width + 1) * height);
  for (let y = 0; y < height; y += 1) {
    rgb.subarray(3 * width * y, 3 * width * (y + 1)).forEach((byte, at) => {
      rows[y * (3 * width + 1) + 1 + at] = byte;
    });
  }
  const header = Buffer.alloc(13);
  header.writeUInt32BE(width, 0);
  header.writeUInt32BE(height, 4);
  header[8] = 8;
  header[9] = 2;
  return Buffer.concat([Buffer.from([137, 80, 78, 71, 13, 10, 26, 10]), chunk("IHDR", header), chunk("IDAT", deflateSync(rows)), chunk("IEND", Buffer.alloc(0))]);
}

function check(files) {
  let bad = 0;
  for (const entry of loadEntries(files)) {
    try {
      const bytes = fileOf(entry);
      if (odrgx.isContainer(bytes)) odrgx.decode(bytes);
      else odrg.decode(bytes);
      console.log(`ok ${entry.name} ${entry.kind} ${bytes.length}`);
    } catch (error) {
      bad += 1;
      console.log(`refused ${entry.name} ${error.reason ?? "error"}: ${error.detail ?? error.message}`);
    }
  }
  process.exitCode = bad === 0 ? 0 : 1;
}

function option(argv, name, fallback) {
  const at = argv.indexOf(name);
  if (at === -1) return fallback;
  const value = argv[at + 1];
  argv.splice(at, 2);
  return value;
}

function sheet(argv) {
  const times = option(argv, "--times", "0,15000").split(",").map(Number);
  const seeds = option(argv, "--seeds", "1").split(",").map(Number);
  const scale = Number(option(argv, "--scale", "4"));
  const [out, ...files] = argv;
  const entries = loadEntries(files);
  const skeleton = new Map(JSON.parse(fs.readFileSync(path.join(HERE, "..", "skeleton.json"), "utf8")).map((one) => [one.name, one]));
  const columns = 2 + times.length * seeds.length;
  const cell = SIZE * scale + 4;
  const width = columns * cell;
  const height = entries.length * cell;
  const rgb = new Uint8Array(3 * width * height).fill(40);
  const put = (row, column, picture) => {
    for (let y = 0; y < SIZE * scale; y += 1) {
      for (let x = 0; x < SIZE * scale; x += 1) {
        const from = 3 * ((SIZE - 1 - Math.floor(y / scale)) * SIZE + Math.floor(x / scale));
        const to = 3 * ((row * cell + 2 + y) * width + column * cell + 2 + x);
        rgb[to] = picture[from];
        rgb[to + 1] = picture[from + 1];
        rgb[to + 2] = picture[from + 2];
      }
    }
  };
  entries.forEach((entry, row) => {
    const before = skeleton.get(entry.name);
    if (before) put(row, 0, rgbOfIndices(before.palette, before.picture));
    put(row, 1, rgbOfIndices(entry.palette, entry.picture));
    try {
      const bytes = fileOf(entry);
      let column = 2;
      for (const seed of seeds) {
        for (const picture of picturesOf(bytes, times, seed)) put(row, column++, picture);
      }
    } catch (error) {
      console.log(`refused ${entry.name} ${error.reason ?? "error"}: ${error.detail ?? error.message}`);
    }
  });
  fs.writeFileSync(out, png(width, height, rgb));
  console.log(`${out}: ${entries.length} rows of ${columns} pictures`);
}

if (process.argv[1] && path.resolve(process.argv[1]) === path.resolve(HERE, "tile.mjs")) {
  const [command, ...rest] = process.argv.slice(2);
  if (command === "check") check(rest);
  else if (command === "sheet") sheet(rest);
  else {
    console.error("usage: node tile.mjs check ENTRY.json... | sheet OUT.png ENTRY.json... [--times T,T] [--seeds S,S] [--scale N]");
    process.exitCode = 2;
  }
}
