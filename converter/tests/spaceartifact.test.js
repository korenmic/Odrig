import assert from "node:assert/strict";
import {createHash} from "node:crypto";
import fs from "node:fs";
import path from "node:path";
import {fileURLToPath} from "node:url";
import test from "node:test";

import {odrg, thumbnail} from "../lib/index.js";
import {decodeReference, render} from "../../project-seeds/62-p2-deep-space-picture-zoom-and-row-scan/source/generate.mjs";

const ROOT = fileURLToPath(new URL("../../", import.meta.url));
const MANIFEST = path.join(ROOT, "project-seeds", "62-p2-deep-space-picture-zoom-and-row-scan", "source", "artifact.json");

test("space scan artifact preserves the full route, endpoint and converter preview", async () => {
  assert.ok(fs.existsSync(MANIFEST), "complete space-scan artifact manifest missing");
  const artifact = JSON.parse(fs.readFileSync(MANIFEST, "utf8"));
  assert.match(artifact.file, /^collection\/(card\/space|long)\/space-scan-10x\.odrg$/);
  const data = fs.readFileSync(path.join(ROOT, artifact.file));
  assert.equal(data.length, artifact.bytes);
  assert.equal(createHash("sha256").update(data).digest("hex"), artifact.sha256);
  assert.equal(thumbnail.keyOf(data), artifact.key);
  const read = odrg.reader(data);
  assert.equal(read.width, 60);
  assert.equal(read.height, 60);
  assert.ok(read.frameCount <= 18004 && read.frameCount > 0);
  const image = await decodeReference();
  const points = [[0, 0, 0], [30000, 486, 0], [63320, 972, 108 * 3320 / 6680]];
  for (let row = 0; row < 10; row += 1) {
    const start = row * 66680;
    points.push([start, row % 2 === 0 ? 0 : 972, row * 108]);
    points.push([start + 60000, row % 2 === 0 ? 972 : 0, row * 108]);
  }
  points.push([690120, 486, 972], [720120, 972, 972]);
  points.sort((a, b) => a[0] - b[0]);
  let elapsed = 0, point = 0, count = 0;
  for (let frame = read.next(); frame !== null; frame = read.next()) {
    assert.equal(Number(frame.ms) % 40, 0);
    while (point < points.length && points[point][0] < elapsed + Number(frame.ms)) {
      const [ms, x, y] = points[point];
      assert.ok(ms >= elapsed);
      assert.deepEqual(frame.picture, render(image, [x, y]), `picture at ${ms}ms`);
      point += 1;
    }
    elapsed += Number(frame.ms);
    count += 1;
  }
  assert.equal(point, points.length);
  assert.equal(elapsed, 720160);
  assert.equal(count, read.frameCount);
  const preview = fs.readFileSync(path.join(ROOT, artifact.file.replace(/\.odrg$/, ".gif")));
  assert.deepEqual(new Uint8Array(preview), thumbnail.make(data));
  assert.deepEqual(preview, fs.readFileSync(path.join(ROOT, "thumbnails", artifact.key + ".gif")));
});
