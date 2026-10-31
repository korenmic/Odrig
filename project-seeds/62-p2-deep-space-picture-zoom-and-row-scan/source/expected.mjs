import assert from "node:assert/strict";
import {createHash} from "node:crypto";
import fs from "node:fs";
import {odrg} from "../../../converter/lib/index.js";

const artifact = JSON.parse(fs.readFileSync(new URL("artifact.json", import.meta.url), "utf8"));
const data = fs.readFileSync(process.argv[2]);
const sha256 = createHash("sha256").update(data).digest("hex");
assert.equal(sha256, artifact.sha256);
const wanted = new Set([0, 40, 720120, 720140]);
for (let ms = 30000; ms < 720160; ms += 30000) wanted.add(ms);
for (let row = 0; row < 10; row += 1) {
  const start = row * 66680;
  wanted.add(start);
  wanted.add(start + 60000);
  if (row < 9) wanted.add(Math.floor((start + 63340) / 40) * 40);
}
const times = [...wanted].sort((a, b) => a - b);
const read = odrg.reader(data);
const samples = [];
let elapsed = 0, index = 0;
for (let frame = read.next(); frame !== null; frame = read.next()) {
  while (index < times.length && times[index] < elapsed + Number(frame.ms)) {
    samples.push({ms: times[index], rgb: Buffer.from(frame.picture).toString("base64")});
    index += 1;
  }
  elapsed += Number(frame.ms);
}
assert.equal(index, times.length);
assert.equal(elapsed, 720160);
process.stdout.write(JSON.stringify({sha256, loopMs: elapsed, frames: read.frameCount, samples}));
