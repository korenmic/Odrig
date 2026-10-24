import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import test from "node:test";
import {pathToFileURL} from "node:url";
import {inflateSync} from "node:zlib";

import {odrgx} from "../lib/index.js";
import {ROOT} from "./support.js";

const FOLDER = path.join(ROOT, "tests", "vectors", "procedural");
const builder = await import(pathToFileURL(path.join(FOLDER, "build.mjs")).href);

// The pixels of a picture vector in the pixel order of docs/format.md: 8-bit RGB rows with
// no filter, the PNG's bottom row first.
function pixelsOf(data) {
  let at = 8;
  let width = 0;
  let height = 0;
  const stream = [];
  while (at < data.length) {
    const length = data.readUInt32BE(at);
    const kind = data.toString("ascii", at + 4, at + 8);
    const body = data.subarray(at + 8, at + 8 + length);
    if (kind === "IHDR") {
      width = body.readUInt32BE(0);
      height = body.readUInt32BE(4);
      assert.deepEqual([body[8], body[9]], [8, 2]);
    } else if (kind === "IDAT") {
      stream.push(body);
    }
    at += 12 + length;
  }
  const raw = inflateSync(Buffer.concat(stream));
  const pixels = new Uint8Array(3 * width * height);
  for (let row = 0; row < height; row += 1) {
    assert.equal(raw[row * (3 * width + 1)], 0);
    pixels.set(raw.subarray(row * (3 * width + 1) + 1, (row + 1) * (3 * width + 1)), (height - 1 - row) * 3 * width);
  }
  return {width, height, pixels};
}

function colours(pixels) {
  const seen = new Set();
  for (let at = 0; at < pixels.length; at += 3) seen.add((pixels[at] << 16) | (pixels[at + 1] << 8) | pixels[at + 2]);
  return seen;
}

test("the reference pictures", async (t) => {
  const manifest = JSON.parse(fs.readFileSync(path.join(FOLDER, "manifest.json"), "utf8"));

  await t.test("they are what their builder makes", () => {
    const {manifest: made, made: pictures} = builder.pictures();
    assert.deepEqual(manifest, made, "run node tests/vectors/procedural/build.mjs");
    const onDisk = fs.readdirSync(FOLDER).filter((name) => name.endsWith(".png"));
    assert.deepEqual(onDisk.sort(), [...pictures.keys()].sort(), "run node tests/vectors/procedural/build.mjs");
    for (const [name, picture] of pictures) assert.deepEqual(fs.readFileSync(path.join(FOLDER, name)), builder.png(picture), name);
  });

  await t.test("each is the library's drawing of its container at its time, a clock's with its seed", () => {
    assert.ok(manifest.length >= 35);
    assert.ok(manifest.filter((entry) => "seed" in entry).length >= 16);
    for (const entry of manifest) {
      const decoded = odrgx.decode(new Uint8Array(fs.readFileSync(path.join(ROOT, "tests", "vectors", entry.file))));
      const {width, height, pixels} = pixelsOf(fs.readFileSync(path.join(FOLDER, entry.picture)));
      assert.deepEqual([width, height], [decoded.header.width, decoded.header.height], entry.picture);
      assert.deepEqual(odrgx.pictureAt(decoded, entry.ms, entry.seed), pixels, entry.picture);
    }
  });

  await t.test("a text shows its colour on its background, and the same picture a pass later", () => {
    for (const entry of manifest.filter((one) => !("seed" in one))) {
      const decoded = odrgx.decode(new Uint8Array(fs.readFileSync(path.join(ROOT, "tests", "vectors", entry.file))));
      const {settings} = decoded;
      const seen = colours(odrgx.pictureAt(decoded, entry.ms));
      assert.ok(seen.has(settings.background), entry.picture);
      assert.ok([...seen].every((colour) => colour === settings.color || colour === settings.background), entry.picture);
      assert.deepEqual(odrgx.pictureAt(decoded, entry.ms + decoded.header.loopMs), odrgx.pictureAt(decoded, entry.ms), entry.picture);
    }
  });

  await t.test("a marquee begins its pass with the canvas empty", () => {
    const decoded = odrgx.decode(new Uint8Array(fs.readFileSync(path.join(ROOT, "tests", "vectors", "texts", "valid", "hebrew.marquee.odrgx"))));
    assert.deepEqual(colours(odrgx.pictureAt(decoded, 0)), new Set([decoded.settings.background]));
    assert.equal(colours(odrgx.pictureAt(decoded, 2000)).size, 2);
  });
});
