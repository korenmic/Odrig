// Makes a frames copy of each clock, turned 90 degrees clockwise as seen on the LEDs, so
// that its top edge becomes its right edge.
//
//   node rotate-clocks.mjs OUT_DIR [--step MS] [--seed N] FILE...
//
// A frames file (`.odrg`, or `.odrgx` of frames) is decoded with the converter, each frame
// turned, its duration kept, and encoded again. A widget is drawn with the converter's own
// drawing code over one loop of it, its `seconds`, with the seed N (1 when not given) at a
// frame every MS milliseconds (50 when not given); a widget whose result is over 2,000,000
// bytes is drawn again at twice the step. Each result is written as OUT_DIR/<name>.odrg
// and one line about it is printed: name, kind, frames, step and bytes.
//
// In the pixel order of docs/format.md, the new pixel (X, Y) of a W x H picture is the old
// pixel (W - 1 - Y, X): the old top-left corner ends at the top-right.

import {execFileSync} from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import {fileURLToPath} from "node:url";
import * as odrgx from "../../../converter/lib/odrgx.js";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..", "..", "..");
const ODRIG = path.join(ROOT, "converter", "odrig.js");
const LARGEST = 2000000;

function converter(...args) {
  execFileSync(process.execPath, [ODRIG, ...args], {stdio: ["ignore", "ignore", "inherit"], windowsHide: true});
}

export function rotate(pixels, width, height) {
  const turned = new Array(width * height);
  for (let y = 0; y < width; y += 1) {
    for (let x = 0; x < height; x += 1) turned[y * height + x] = pixels[x * width + (width - 1 - y)];
  }
  return turned;
}

function writeJson(file, animation) {
  const frames = animation.frames.map((frame) => `    {"ms": ${frame.ms}, "pixels": [${frame.pixels.join(", ")}]}`);
  const text = `{\n  "version": 1,\n  "width": ${animation.width},\n  "height": ${animation.height},\n  "frames": [\n${frames.join(",\n")}\n  ]\n}\n`;
  fs.writeFileSync(file, text, "utf8");
}

function drawn(decoded, step, seed) {
  const {width, height, loopMs} = decoded.header;
  const frames = [];
  for (let t = 0; t < loopMs; t += step) {
    const picture = odrgx.pictureAt(decoded, t, seed);
    const pixels = new Array(width * height);
    for (let i = 0; i < pixels.length; i += 1) pixels[i] = (picture[3 * i] << 16) | (picture[3 * i + 1] << 8) | picture[3 * i + 2];
    frames.push({ms: Math.min(step, loopMs - t), pixels});
  }
  return {width, height, frames};
}

function turnAndEncode(animation, json, out) {
  const turned = {
    width: animation.height,
    height: animation.width,
    frames: animation.frames.map((frame) => ({ms: frame.ms, pixels: rotate(frame.pixels, animation.width, animation.height)})),
  };
  writeJson(json, turned);
  converter("encode", json, out);
  return {frames: turned.frames.length, bytes: fs.statSync(out).size};
}

function main(argv) {
  let step = 50;
  let seed = 1;
  const files = [];
  const [outDir, ...rest] = argv;
  for (let i = 0; i < rest.length; i += 1) {
    if (rest[i] === "--step") step = Number(rest[(i += 1)]);
    else if (rest[i] === "--seed") seed = Number(rest[(i += 1)]);
    else files.push(rest[i]);
  }
  if (!outDir || files.length === 0) throw new Error("usage: node rotate-clocks.mjs OUT_DIR [--step MS] [--seed N] FILE...");
  fs.mkdirSync(outDir, {recursive: true});
  const work = fs.mkdtempSync(path.join(os.tmpdir(), "odrig-rotate-"));
  try {
    for (const file of files) {
      const name = path.basename(file).replace(/\.odrgx?$/, "");
      const out = path.join(outDir, `${name}.odrg`);
      const json = path.join(work, `${name}.json`);
      const data = new Uint8Array(fs.readFileSync(file));
      const decoded = odrgx.isContainer(data) ? odrgx.decode(data) : null;
      if (decoded && decoded.header.type === odrgx.TYPES.widget) {
        let used = step;
        let made = turnAndEncode(drawn(decoded, used, seed), json, out);
        if (made.bytes > LARGEST) {
          used = 2 * step;
          made = turnAndEncode(drawn(decoded, used, seed), json, out);
        }
        console.log(`${name}\twidget\t${made.frames}\t${used}\t${made.bytes}`);
      } else {
        converter("decode", file, json);
        const made = turnAndEncode(JSON.parse(fs.readFileSync(json, "utf8")), json, out);
        console.log(`${name}\tframes\t${made.frames}\t-\t${made.bytes}`);
      }
      fs.rmSync(json, {force: true});
    }
  } finally {
    fs.rmSync(work, {recursive: true, force: true});
  }
}

main(process.argv.slice(2));
