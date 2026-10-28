// Builds the vectors of clocks of this folder with the converter's library. Run from the
// repository root: node tests/vectors/widgets/build.mjs
//
// valid/ holds containers of clocks with their JSON sources: X.odrgx and X.json. invalid/
// holds containers that every reader refuses, each named by its reason and what is wrong.

import {mkdirSync, readdirSync, rmSync, writeFileSync} from "node:fs";
import {dirname, join} from "node:path";
import {fileURLToPath} from "node:url";

const HERE = dirname(fileURLToPath(import.meta.url));
const {odrgx} = await import(new URL("../../../converter/lib/index.js", import.meta.url).href);

function clock(more) {
  return {
    width: 60, height: 60, widget: "analog", seconds: 30, face: 0xf4ecd0, hands: 0x202020, rim: 0xd4a017, background: 0x000000,
    speedMin: 60, speedMax: 600, ...more,
  };
}

// The clocks of valid/, by name.
export const CLOCKS = {
  "analog": clock({}),
  "digital": clock({widget: "digital", face: 0x40c0ff, rim: 0xffd040, seconds: 20}),
  "melting": clock({widget: "melting", seconds: 45, speedMin: 1, speedMax: 3600}),
  "small.analog": clock({width: 21, height: 13, seconds: 1, speedMin: 3600, speedMax: 3600}),
};

function changed(data, at, ...bytes) {
  const made = Uint8Array.from(data);
  made.set(bytes, at);
  return made;
}

function u16(value) {
  return [value & 0xff, (value >>> 8) & 0xff];
}

function u32(value) {
  return [...u16(value & 0xffff), ...u16(Math.floor(value / 65536))];
}

// Every vector, by its place in the folder.
export function vectors() {
  const made = new Map();
  for (const [name, one] of Object.entries(CLOCKS)) {
    made.set(`valid/${name}.odrgx`, odrgx.encodeWidget(one));
    made.set(`valid/${name}.json`, odrgx.dumpsWidget(one));
  }
  const good = odrgx.encodeWidget(clock({}));
  const p = odrgx.HEADER_SIZE;
  made.set("invalid/canvas-too-large.odrgx", changed(good, 8, ...u16(200), ...u16(200)));
  made.set("invalid/payload-size.header.odrgx", changed(good, 16, ...u32(21)));
  made.set("invalid/payload-size.short.odrgx", changed(good, 16, ...u32(19)));
  made.set("invalid/truncated.odrgx", good.subarray(0, p + 12));
  made.set("invalid/unknown-widget.zero.odrgx", changed(good, p, 0));
  made.set("invalid/unknown-widget.six.odrgx", changed(good, p, 6));
  made.set("invalid/bad-settings.reserved.odrgx", changed(good, p + 1, 1));
  made.set("invalid/bad-settings.seconds.odrgx", changed(good, p + 2, ...u16(0)));
  made.set("invalid/bad-settings.long.odrgx", changed(good, p + 2, ...u16(3601)));
  made.set("invalid/bad-settings.least.odrgx", changed(good, p + 16, ...u16(0)));
  made.set("invalid/bad-settings.greatest.odrgx", changed(good, p + 18, ...u16(59)));
  made.set("invalid/bad-settings.fastest.odrgx", changed(good, p + 18, ...u16(3601)));
  made.set("invalid/trailing-bytes.odrgx", Uint8Array.of(...good, 0));
  made.set("invalid/loop-mismatch.odrgx", changed(good, 12, ...u32(30001)));
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
