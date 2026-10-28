// Makes the twelve time animations of seed 52 from their rendered frames: 8 colours each,
// black and then the colours its script names, most used first, every other pixel the
// nearest of them; frames 50 ms apart, or 100 ms apart when the file would be larger than
// 2 MB at 50 ms. Writes OUT_DIR/<name>.odrg and OUT_DIR/twelve.json, what was chosen.
//
//   node make12.mjs REFERENCES RAW50_DIR OUT_DIR
//
// The library is that of the worktree named by ODRIG_TREE, by default the seed's worktree.

import fs from "node:fs";
import path from "node:path";
import {pathToFileURL} from "node:url";

import {ORIGINAL, STANDALONE} from "./render12.mjs";

const TREE = process.env.ODRIG_TREE ?? "C:/Users/koren/src/Odrig/scratch/wt-seed52-impl";
const {odrg} = await import(pathToFileURL(path.join(TREE, "converter", "lib", "index.js")).href);

const FRAME = 60 * 60 * 4;
const LARGEST = 2 * 1024 * 1024;
const COLOURS = 8;
const DARK = 16;

// The colours a script names, as numbers 0xRRGGBB: every #rgb and #rrggbb of its text.
export function namedColours(text) {
  const found = new Set();
  for (const match of text.matchAll(/#([0-9a-fA-F]{6}|[0-9a-fA-F]{3})\b/g)) {
    let hex = match[1].toLowerCase();
    if (hex.length === 3) hex = [...hex].map((digit) => digit + digit).join("");
    found.add(parseInt(hex, 16));
  }
  return [...found];
}

function channels(colour) {
  return [colour >> 16, (colour >> 8) & 0xff, colour & 0xff];
}

function isDark(colour) {
  return Math.max(...channels(colour)) <= DARK;
}

// The named colour a pixel was drawn with: the one whose blend with the background, at
// any strength, comes nearest the pixel; null for a pixel of the background.
function sourceOf(pixel, background, named) {
  let best = Infinity;
  let found = null;
  const fromBackground = pixel.map((value, at) => value - background[at]);
  if (fromBackground.reduce((sum, value) => sum + value * value, 0) <= 3 * DARK * DARK) return null;
  for (const [colour, rgb] of named) {
    const towards = rgb.map((value, at) => value - background[at]);
    const length = towards.reduce((sum, value) => sum + value * value, 0);
    if (length === 0) continue;
    const share = Math.max(0, Math.min(1, towards.reduce((sum, value, at) => sum + value * fromBackground[at], 0) / length));
    const distance = fromBackground.reduce((sum, value, at) => sum + (value - share * towards[at]) ** 2, 0);
    if (distance < best) {
      best = distance;
      found = colour;
    }
  }
  return found;
}

// The palette of a scene: black, then the colours its script names, the most used first:
// each pixel counts for the named colour it was drawn with. The colours as dark as black,
// the background among them, are black.
export function paletteOf(raw, named) {
  const bright = named.filter((colour) => !isDark(colour)).map((colour) => [colour, channels(colour)]);
  const darkest = named.filter(isDark).sort((a, b) => channels(a).reduce((s, v) => s + v, 0) - channels(b).reduce((s, v) => s + v, 0));
  const background = darkest.length > 0 ? channels(darkest[0]) : [0, 0, 0];
  const counts = new Map(bright.map(([colour]) => [colour, 0]));
  const seen = new Map();
  for (let at = 0; at < raw.length; at += 4) {
    const key = (raw[at] << 16) | (raw[at + 1] << 8) | raw[at + 2];
    if (!seen.has(key)) seen.set(key, sourceOf([raw[at], raw[at + 1], raw[at + 2]], background, bright));
    const source = seen.get(key);
    if (source !== null) counts.set(source, counts.get(source) + 1);
  }
  const used = [...counts].filter(([, count]) => count > 0);
  used.sort((a, b) => b[1] - a[1] || a[0] - b[0]);
  return [0x000000, ...used.slice(0, COLOURS - 1).map(([colour]) => colour)];
}

// The nearest colour of a palette to each pixel, the first of equals.
export function mapper(palette) {
  const cache = new Map();
  return (r, g, b) => {
    const key = (r << 16) | (g << 8) | b;
    let found = cache.get(key);
    if (found === undefined) {
      let best = Infinity;
      for (const colour of palette) {
        const dr = r - (colour >> 16);
        const dg = g - ((colour >> 8) & 0xff);
        const db = b - (colour & 0xff);
        const distance = dr * dr + dg * dg + db * db;
        if (distance < best) {
          best = distance;
          found = colour;
        }
      }
      cache.set(key, found);
    }
    return found;
  };
}

// The frames of a scene, every `every`-th of those rendered 50 ms apart, as odrg.encode
// takes them, each pixel the nearest colour of the palette; and the frames' picture rows.
export function framesOf(raw, palette, every) {
  const nearest = mapper(palette);
  const frames = [];
  const count = raw.length / FRAME;
  for (let index = 0; index < count; index += every) {
    const frame = raw.subarray(index * FRAME, (index + 1) * FRAME);
    const picture = new Uint8Array(60 * 60 * 3);
    for (let y = 0; y < 60; y += 1) {
      for (let x = 0; x < 60; x += 1) {
        const from = 4 * (y * 60 + x);
        const colour = nearest(frame[from], frame[from + 1], frame[from + 2]);
        const to = 3 * ((59 - y) * 60 + x);
        picture[to] = colour >> 16;
        picture[to + 1] = (colour >> 8) & 0xff;
        picture[to + 2] = colour & 0xff;
      }
    }
    frames.push({ms: 50 * every, picture});
  }
  return {width: 60, height: 60, frames};
}

function main() {
  const [references, rawDir, out] = process.argv.slice(2);
  fs.mkdirSync(out, {recursive: true});
  const scripts = {
    original: fs.readFileSync(path.join(references, "original", "animation.js"), "utf8"),
    standalone: fs.readFileSync(path.join(references, "standalone", "standalone-script.js"), "utf8"),
  };
  const made = [];
  for (const [set, scenes] of [["original", ORIGINAL], ["standalone", STANDALONE]]) {
    const named = namedColours(scripts[set]);
    for (const [name, seconds] of scenes) {
      const raw = new Uint8Array(fs.readFileSync(path.join(rawDir, `${name}.rgba`)));
      const palette = paletteOf(raw, named);
      let every = 1;
      let bytes = odrg.encode(framesOf(raw, palette, every));
      if (bytes.length > LARGEST) {
        every = 2;
        bytes = odrg.encode(framesOf(raw, palette, every));
      }
      fs.writeFileSync(path.join(out, `${name}.odrg`), bytes);
      made.push({name, seconds, frame_ms: 50 * every, bytes: bytes.length, palette: palette.map((colour) => `#${colour.toString(16).padStart(6, "0")}`)});
      console.log(`${name}: ${seconds} s, ${50 * every} ms, ${bytes.length} bytes, ${palette.length} colours`);
    }
  }
  fs.writeFileSync(path.join(out, "twelve.json"), `${JSON.stringify(made, null, 1)}\n`);
}

if (process.argv[1] && path.resolve(process.argv[1]) === path.resolve(new URL(import.meta.url).pathname.replace(/^\/([A-Za-z]:)/, "$1"))) {
  main();
}
