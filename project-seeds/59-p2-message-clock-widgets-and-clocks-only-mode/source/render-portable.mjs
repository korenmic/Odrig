// Render delivered widgets at the reference review's sample times.
import fs from "node:fs";
import {odrgx} from "../../../converter/lib/index.js";

const samples = JSON.parse(fs.readFileSync(process.argv[2], "utf8")).samples;
const names = ["consciousness", "symmetry", "temperature", "the-time", "countdown", "the-clock", "mistakes"];
for (const sample of samples) {
  const asset = new URL(`../../../collection/card/clocks/message/v7-${names[sample.tab-1]}.odrgx`, import.meta.url);
  const decoded = odrgx.decodeWidget(fs.readFileSync(asset));
  const bottom = odrgx.pictureAt(decoded, sample.t, sample.seed);
  const top = Buffer.alloc(10800);
  for(let y=0;y<60;y++)top.set(bottom.subarray((59-y)*180,(60-y)*180),y*180);
  sample.portable=top.toString("base64");
}
process.stdout.write(JSON.stringify({samples}));
