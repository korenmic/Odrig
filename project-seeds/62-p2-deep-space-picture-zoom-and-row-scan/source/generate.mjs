import fs from "node:fs";
import path from "node:path";
import {createHash} from "node:crypto";
import {fileURLToPath} from "node:url";

import * as video from "../../../converter/cli/video.js";
import {thumbnail} from "../../../converter/lib/index.js";

const REFERENCE = fileURLToPath(new URL("../references/deep-space-james-webb-telescope-v0-jtypls13gcb91.webp", import.meta.url));
export const SOURCE_SHA256 = "e24ee5296bb539f15dfb5f693b233481a6c9598967963799340dbf4621339135";
export const settings = Object.freeze({sourceSize: 1080, viewport: 108, canvas: 60,
  horizontalMs: 60000, descentMs: 6680, stepMs: 40, travelMs: 720120, loopMs: 720160, frames: 18004});

export function segments() {
  const result = [];
  let point = [0, 0];
  const add = (to, ms) => { result.push({from: point, to, ms}); point = to; };
  for (let row = 0; row < 10; row += 1) {
    add([row % 2 === 0 ? 972 : 0, row * 108], settings.horizontalMs);
    if (row < 9) add([point[0], (row + 1) * 108], settings.descentMs);
  }
  add([972, 972], settings.horizontalMs);
  return result;
}

const ROUTE = segments();

export function cameraAt(ms) {
  if (!Number.isFinite(ms)) throw new RangeError("camera time must be finite");
  let left = Math.max(0, ms);
  for (const {from, to, ms: duration} of ROUTE) {
    if (left < duration) return from.map((start, axis) => start + (to[axis] - start) * left / duration);
    left -= duration;
  }
  return [972, 972];
}

export function render({width, height, rgb}, origin, size = settings.canvas) {
  const crop = width / 10;
  if (!Number.isInteger(width) || width < 10 || height !== width || width % 10 !== 0 ||
      !(rgb instanceof Uint8Array) || rgb.length !== width * height * 3 ||
      !Number.isInteger(size) || size < 1 || size > 60 || origin.length !== 2 ||
      origin.some((p) => !Number.isFinite(p) || p < 0 || p > width - crop)) {
    throw new RangeError("invalid image, canvas or viewport bounds");
  }
  const result = new Uint8Array(size * size * 3);
  for (let y = 0; y < size; y += 1) {
    const sy = Math.max(0, Math.min(height - 1, origin[1] + (y + 0.5) * crop / size - 0.5));
    const y0 = Math.floor(sy), y1 = Math.min(height - 1, y0 + 1), fy = sy - y0;
    for (let x = 0; x < size; x += 1) {
      const sx = Math.max(0, Math.min(width - 1, origin[0] + (x + 0.5) * crop / size - 0.5));
      const x0 = Math.floor(sx), x1 = Math.min(width - 1, x0 + 1), fx = sx - x0;
      const out = ((size - 1 - y) * size + x) * 3;
      for (let c = 0; c < 3; c += 1) {
        const top = rgb[(y0 * width + x0) * 3 + c] * (1 - fx) + rgb[(y0 * width + x1) * 3 + c] * fx;
        const bottom = rgb[(y1 * width + x0) * 3 + c] * (1 - fx) + rgb[(y1 * width + x1) * 3 + c] * fx;
        result[out + c] = Math.round(top * (1 - fy) + bottom * fy);
      }
    }
  }
  return result;
}

export async function decodeReference(file = REFERENCE) {
  const bytes = fs.readFileSync(file);
  if (createHash("sha256").update(bytes).digest("hex") !== SOURCE_SHA256) throw new Error("reference checksum differs");
  const decoder = video.program();
  if (decoder.failure) throw decoder.failure;
  let image = null;
  for await (const frame of video.frames(file, decoder.file)) {
    if (image !== null || frame.width !== 1080 || frame.height !== 1080) throw new Error("reference must be one 1080x1080 image");
    const rgb = new Uint8Array(1080 * 1080 * 3);
    for (let p = 0; p < 1080 * 1080; p += 1) rgb.set(frame.rgba.subarray(p * 4, p * 4 + 3), p * 3);
    image = {width: frame.width, height: frame.height, rgb};
  }
  if (image === null) throw new Error("reference has no image");
  return image;
}

function jsonFrame(picture) {
  const pixels = new Array(picture.length / 3);
  for (let p = 0; p < pixels.length; p += 1) pixels[p] = picture[p * 3] * 65536 + picture[p * 3 + 1] * 256 + picture[p * 3 + 2];
  return JSON.stringify({ms: settings.stepMs, pixels});
}

export async function writeSource(folder, progress = null) {
  if (fs.existsSync(folder)) throw new Error("output directory already exists");
  const image = await decodeReference();
  fs.mkdirSync(folder);
  const descriptor = fs.openSync(path.join(folder, "space-scan.json"), "wx");
  try {
    fs.writeSync(descriptor, '{"version":1,"width":60,"height":60,"frames":[\n');
    for (let frame = 0; frame < settings.frames; frame += 1) {
      fs.writeSync(descriptor, (frame === 0 ? "" : ",\n") + jsonFrame(render(image, cameraAt(frame * settings.stepMs))));
      if (frame % 1500 === 0 || frame + 1 === settings.frames) progress?.(frame + 1, settings.frames);
    }
    fs.writeSync(descriptor, "\n]}\n");
    fs.fsyncSync(descriptor);
  } finally {
    fs.closeSync(descriptor);
  }
  const overviewTimes = new Set([0, settings.travelMs]);
  for (let at = 0; at <= settings.travelMs; at += 2000) overviewTimes.add(at);
  let boundary = 0;
  for (const leg of ROUTE) { boundary += leg.ms; overviewTimes.add(boundary); }
  const times = [...overviewTimes].sort((a, b) => a - b);
  fs.writeFileSync(path.join(folder, "overview.gif"), thumbnail.encode(times.map((at) => render(image, cameraAt(at))), 60, 60, 4));
  fs.writeFileSync(path.join(folder, "pace.gif"), thumbnail.encode(Array.from({length: 125}, (_, n) => render(image, cameraAt(n * 40))), 60, 60, 4));
  const manifest = {version: 1, reference: path.basename(REFERENCE), sourceSha256: SOURCE_SHA256,
    settings, route: ROUTE, sampling: "bilinear pixel centres in encoded RGB; round half up; bottom-row-first LED output",
    overview: {frameTimesMs: times, displayFrameMs: 40, description: "accelerated, sampled full route including all vertices"},
    pace: {startMs: 0, durationMs: 5000, displayFrameMs: 40}};
  fs.writeFileSync(path.join(folder, "manifest.json"), JSON.stringify(manifest, null, 2) + "\n", "utf8");
  const reference = fs.readFileSync(REFERENCE).toString("base64");
  fs.writeFileSync(path.join(folder, "review.html"), `<!doctype html><html lang="en"><meta charset="utf-8"><title>Deep-space scan review</title>
<style>body{font:18px system-ui;background:#090a20;color:#eee;max-width:1000px;margin:2em auto}img{max-width:100%;image-rendering:pixelated}.view{width:360px}section{display:inline-block;vertical-align:top;margin-right:24px}</style>
<h1>Deep-space scan</h1><p>Fixed10x zoom · 60×60 LEDs · full loop12min0.16s.</p>
<section><h2>Full route: accelerated samples</h2><img class="view" src="overview.gif" alt="Sampled overview of all rows and the final bottom pass"><p>This GIF is accelerated, not the installation's pace.</p></section>
<section><h2>Actual pace: first5seconds</h2><img class="view" src="pace.gif" alt="First five seconds at actual speed"></section>
<h2>Original reference</h2><img width="540" src="data:image/webp;base64,${reference}" alt="Original deep-space pixel-art image">
<p>Ten alternating rows, nine descents, then one extra left-to-right bottom-row pass. The endpoint is bottom-right; the loop restarts top-left.</p>
<p>Horizontal passes60s; descents6.68s; frames40ms. See manifest.json for exact positions and time.</p></html>\n`, "utf8");
  return manifest;
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  if (process.argv.length !== 3) {
    console.error("usage: node generate.mjs NEW_OUTPUT_DIRECTORY");
    process.exitCode = 2;
  } else {
    try {
      await writeSource(path.resolve(process.argv[2]), (done, total) => console.log(`frames ${done}/${total}`));
      console.log(`source complete: ${settings.frames} frames, ${settings.loopMs}ms`);
    } catch (error) {
      console.error(error.message);
      process.exitCode = 1;
    }
  }
}
