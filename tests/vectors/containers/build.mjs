// Builds the ODRGX vectors of this folder from the ODRG vectors beside it. Run from the
// repository root: node tests/vectors/containers/build.mjs
//
// valid/ holds containers with what they decode to: X.odrgx and X.json. invalid/ holds
// containers that every reader refuses, each named by its reason and what is wrong.

import {mkdirSync, readFileSync, readdirSync, rmSync, writeFileSync} from "node:fs";
import {dirname, join} from "node:path";
import {fileURLToPath} from "node:url";

const HERE = dirname(fileURLToPath(import.meta.url));
const ODRG = join(HERE, "..", "valid");
const {odrg, odrgx} = await import(new URL("../../../converter/lib/index.js", import.meta.url).href);

function source(name) {
  return new Uint8Array(readFileSync(join(ODRG, name)));
}

function loopOf(data) {
  return odrg.decode(data).records.reduce((sum, record) => sum + record.ms, 0);
}

// A container of frames around an ODRG vector, its header as `odrgx.wrap` writes it.
function framesOf(name) {
  const data = source(name);
  const decoded = odrg.decode(data);
  return odrgx.wrap("frames", decoded.width, decoded.height, loopOf(data), data);
}

// The bytes with some of them put in the place of what they had.
function changed(data, at, ...bytes) {
  const made = Uint8Array.from(data);
  made.set(bytes, at);
  return made;
}

function u32(value) {
  return [value & 0xff, (value >>> 8) & 0xff, (value >>> 16) & 0xff, (value >>> 24) & 0xff];
}

// Every vector, by its place in the folder.
export function vectors() {
  const made = new Map();
  for (const name of ["encoded.rgb", "pal-modes", "durations"]) {
    made.set(`valid/frames.${name}.odrgx`, framesOf(`${name}.odrg`));
    made.set(`valid/frames.${name}.json`, source(`${name}.json`));
  }
  const good = framesOf("encoded.rgb.odrg");
  const payload = good.subarray(odrgx.HEADER_SIZE);
  made.set("invalid/truncated.header.odrgx", good.subarray(0, 12));
  made.set("invalid/bad-container.version.odrgx", changed(good, 4, 2));
  made.set("invalid/bad-container.reserved.odrgx", changed(good, 7, 1));
  made.set("invalid/unknown-type.odrgx", changed(good, 5, 9));
  made.set("invalid/unknown-type-version.odrgx", changed(good, 6, 2));
  made.set("invalid/zero-size.odrgx", changed(good, 8, 0, 0));
  made.set("invalid/payload-size.short.odrgx", changed(good, 16, ...u32(payload.length + 1)));
  made.set("invalid/payload-size.long.odrgx", changed(good, 16, ...u32(payload.length - 1)));
  made.set("invalid/canvas-mismatch.odrgx", changed(good, 8, 8, 0));
  made.set("invalid/loop-mismatch.odrgx", changed(good, 12, ...u32(loopOf(payload) + 20)));
  made.set("invalid/bad-magic.payload.odrgx", changed(good, odrgx.HEADER_SIZE + 3, 0x58));
  made.set("invalid/truncated.payload.odrgx", changed(good.subarray(0, good.length - 3), 16, ...u32(payload.length - 3)));
  return made;
}

function main() {
  for (const folder of ["valid", "invalid"]) {
    rmSync(join(HERE, folder), {recursive: true, force: true});
    mkdirSync(join(HERE, folder));
  }
  for (const [name, data] of vectors()) {
    writeFileSync(join(HERE, name), data);
  }
  for (const folder of ["valid", "invalid"]) {
    console.log(`${folder}: ${readdirSync(join(HERE, folder)).length} files`);
  }
}

if (process.argv[1] === fileURLToPath(import.meta.url)) {
  main();
}
