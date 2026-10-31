import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import {fileURLToPath} from "node:url";
import test from "node:test";

import {cameraAt, decodeReference, render, segments, settings, writeSource} from "../../project-seeds/62-p2-deep-space-picture-zoom-and-row-scan/source/generate.mjs";

test("space scan covers ten rows then the final rightward bottom pass", () => {
  const route = segments();
  const expected = [[0, 0]];
  for (let row = 0; row < 10; row += 1) {
    const x = row % 2 === 0 ? 972 : 0;
    expected.push([x, row * 108]);
    if (row < 9) expected.push([x, (row + 1) * 108]);
  }
  expected.push([972, 972]);
  assert.deepEqual([route[0].from, ...route.map((leg) => leg.to)], expected);
  assert.equal(route.filter((leg) => leg.from[1] === leg.to[1]).length, 11);
  assert.equal(route.filter((leg) => leg.from[0] === leg.to[0]).length, 9);
  assert.equal(route.reduce((sum, leg) => sum + leg.ms, 0), 720120);
  assert.equal(settings.frames, 18004);
  assert.equal(settings.loopMs, 720160);
  assert.ok(route.every((leg) => leg.ms % 40 === 0));
});

test("space scan interpolates every turn without a jump or out-of-bounds origin", () => {
  assert.deepEqual(cameraAt(-20), [0, 0]);
  assert.deepEqual(cameraAt(30000), [486, 0]);
  assert.deepEqual(cameraAt(63340), [972, 54]);
  assert.deepEqual(cameraAt(96680), [486, 108]);
  let at = 0;
  for (const leg of segments()) {
    assert.deepEqual(cameraAt(at), leg.from);
    at += leg.ms;
    assert.deepEqual(cameraAt(at), leg.to);
  }
  for (let ms = 0; ms <= 720120; ms += 137) {
    const [x, y] = cameraAt(ms);
    assert.ok(x >= 0 && x <= 972 && y >= 0 && y <= 972);
  }
  assert.deepEqual(cameraAt(720120), [972, 972]);
  assert.deepEqual(cameraAt(720159), [972, 972]);
  assert.deepEqual(cameraAt(999999), [972, 972]);
  assert.throws(() => cameraAt(NaN), RangeError);
});

function grid() {
  const rgb = new Uint8Array(20 * 20 * 3);
  for (let y = 0; y < 20; y += 1) {
    for (let x = 0; x < 20; x += 1) rgb.set([x * 10, y * 10, 50], (y * 20 + x) * 3);
  }
  return {width: 20, height: 20, rgb};
}

test("space scan preserves asymmetric image orientation in bottom-row-first LED RGB", () => {
  assert.deepEqual([...render(grid(), [0, 0], 2)], [0, 10, 50, 10, 10, 50, 0, 0, 50, 10, 0, 50]);
  assert.deepEqual([...render(grid(), [18, 18], 2)], [180, 190, 50, 190, 190, 50, 180, 180, 50, 190, 180, 50]);
});

test("space scan samples fractional positions and refuses invalid bounds", () => {
  assert.deepEqual([...render(grid(), [0.5, 0.5], 2)], [5, 15, 50, 15, 15, 50, 5, 5, 50, 15, 5, 50]);
  assert.throws(() => render(grid(), [19, 0], 2), RangeError);
  assert.throws(() => render(grid(), [0, -1], 2), RangeError);
  assert.throws(() => render({...grid(), rgb: new Uint8Array(3)}, [0, 0], 2), RangeError);
});

test("space scan decodes the exact reference and refuses a changed source", async () => {
  const image = await decodeReference();
  assert.equal(image.width, 1080);
  assert.equal(image.height, 1080);
  assert.equal(image.rgb.length, 1080 * 1080 * 3);
  const folder = fs.mkdtempSync(path.join(os.tmpdir(), "odrig-space-"));
  try {
    const changed = path.join(folder, "changed.webp");
    const original = fileURLToPath(new URL("../../project-seeds/62-p2-deep-space-picture-zoom-and-row-scan/references/deep-space-james-webb-telescope-v0-jtypls13gcb91.webp", import.meta.url));
    const data = fs.readFileSync(original);
    data[data.length - 1] ^= 1;
    fs.writeFileSync(changed, data);
    await assert.rejects(() => decodeReference(changed), /reference checksum/);
  } finally {
    fs.rmSync(folder, {recursive: true, force: true});
  }
});

test("space scan refuses to replace an existing output folder", async () => {
  const folder = fs.mkdtempSync(path.join(os.tmpdir(), "odrig-space-output-"));
  try {
    const marker = path.join(folder, "keep.txt");
    fs.writeFileSync(marker, "keep");
    await assert.rejects(() => writeSource(folder), /exist/i);
    assert.equal(fs.readFileSync(marker, "utf8"), "keep");
  } finally {
    fs.rmSync(folder, {recursive: true, force: true});
  }
});
