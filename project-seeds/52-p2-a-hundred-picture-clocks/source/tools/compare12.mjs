// Compares each of the twelve time animations of seed 52 with its reference GIF, frame for
// frame at the same times: each GIF frame, its pixels mapped to the file's colours as the
// file's were, against the file's frame at the frame's start. Prints, for each, the number
// of frames compared, the largest and the mean number of pixels that differ, of 3,600.
//
//   node compare12.mjs REFERENCES FILES_DIR
//
// The GIF reader is omggif, from the converter's packages of the worktree named by
// ODRIG_TREE, by default the seed's worktree.

import {createRequire} from "node:module";
import fs from "node:fs";
import path from "node:path";
import {pathToFileURL} from "node:url";

import {mapper} from "./make12.mjs";

const TREE = process.env.ODRIG_TREE ?? "C:/Users/koren/src/Odrig/scratch/wt-seed52-impl";
const require = createRequire(path.join(TREE, "converter", "package.json"));
const {GifReader} = require("omggif");
const {odrg} = await import(pathToFileURL(path.join(TREE, "converter", "lib", "index.js")).href);

const GIFS = {
  "time-original-1-two-times": "original/original-1-two-times.gif",
  "time-original-2-never-zero": "original/original-2-never-zero.gif",
  "time-original-3-sand-goes-back-up": "original/original-3-sand-goes-back-up.gif",
  "time-original-4-we-were-here": "original/original-4-we-were-here.gif",
  "time-original-5-every-row-another-time": "original/original-5-every-row-another-time.gif",
  "time-original-6-the-clock-melts": "original/original-6-the-clock-melts.gif",
  "time-standalone-1-two-times": "standalone/standalone-1-two-times.gif",
  "time-standalone-2-never-zero": "standalone/standalone-2-never-zero.gif",
  "time-standalone-3-reverse-hourglass": "standalone/standalone-3-reverse-hourglass.gif",
  "time-standalone-4-we-were-here": "standalone/standalone-4-we-were-here.gif",
  "time-standalone-5-time-bands": "standalone/standalone-5-time-bands.gif",
  "time-standalone-6-melting-clock": "standalone/standalone-6-melting-clock.gif",
};

// Each frame of a GIF as RGBA of its whole canvas, with its start in milliseconds.
export function gifFrames(bytes) {
  const reader = new GifReader(bytes);
  const canvas = new Uint8Array(reader.width * reader.height * 4);
  const frames = [];
  let start = 0;
  let restore = null;
  for (let index = 0; index < reader.numFrames(); index += 1) {
    const info = reader.frameInfo(index);
    if (restore !== null) {
      canvas.set(restore);
      restore = null;
    }
    const before = info.disposal === 3 ? Uint8Array.from(canvas) : null;
    reader.decodeAndBlitFrameRGBA(index, canvas);
    frames.push({start, rgba: Uint8Array.from(canvas), width: reader.width, height: reader.height});
    start += 10 * info.delay;
    if (info.disposal === 2) {
      for (let y = info.y; y < info.y + info.height; y += 1) {
        for (let x = info.x; x < info.x + info.width; x += 1) canvas.fill(0, 4 * (y * reader.width + x), 4 * (y * reader.width + x) + 4);
      }
    } else if (before !== null) {
      restore = before;
    }
  }
  return frames;
}

// The palette of an ODRG file as numbers, and its pictures with their starts.
function fileFrames(bytes) {
  const decoded = odrg.decode(bytes);
  const palette = new Set();
  const frames = [];
  let start = 0;
  for (const record of decoded.records) {
    frames.push({start, picture: record.picture});
    for (let at = 0; at < record.picture.length; at += 3) palette.add((record.picture[at] << 16) | (record.picture[at + 1] << 8) | record.picture[at + 2]);
    start += record.ms;
  }
  return {palette: [...palette].sort((a, b) => a - b), frames, loop: start};
}

function frameAt(frames, time) {
  let found = frames[0];
  for (const frame of frames) {
    if (frame.start <= time) found = frame;
    else break;
  }
  return found;
}

export function compare(gifBytes, fileBytes) {
  const file = fileFrames(fileBytes);
  const nearest = mapper(file.palette);
  const results = [];
  for (const gif of gifFrames(gifBytes)) {
    if (gif.width !== 60 || gif.height !== 60 || gif.start >= file.loop) continue;
    const ours = frameAt(file.frames, gif.start).picture;
    let differ = 0;
    for (let y = 0; y < 60; y += 1) {
      for (let x = 0; x < 60; x += 1) {
        const from = 4 * (y * 60 + x);
        const colour = nearest(gif.rgba[from], gif.rgba[from + 1], gif.rgba[from + 2]);
        const at = 3 * ((59 - y) * 60 + x);
        if (colour !== ((ours[at] << 16) | (ours[at + 1] << 8) | ours[at + 2])) differ += 1;
      }
    }
    results.push(differ);
  }
  return results;
}

function main() {
  const [references, files] = process.argv.slice(2);
  const report = [];
  for (const [name, gif] of Object.entries(GIFS)) {
    const results = compare(new Uint8Array(fs.readFileSync(path.join(references, gif))), new Uint8Array(fs.readFileSync(path.join(files, `${name}.odrg`))));
    const largest = Math.max(...results);
    const mean = results.reduce((sum, value) => sum + value, 0) / results.length;
    report.push({name, frames: results.length, largest, mean: Number(mean.toFixed(2))});
    console.log(`${name}: ${results.length} frames compared, at most ${largest} and on average ${mean.toFixed(2)} of 3600 pixels differ`);
  }
  fs.writeFileSync(path.join(files, "comparison.json"), `${JSON.stringify(report, null, 1)}\n`);
}

if (process.argv[1] && path.resolve(process.argv[1]) === path.resolve(new URL(import.meta.url).pathname.replace(/^\/([A-Za-z]:)/, "$1"))) {
  main();
}
