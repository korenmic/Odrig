// Counts the colours of each animation file of a folder and draws a contact sheet of their
// first pictures.
//
//   node colours.mjs FOLDER SHEET.png
//
// A frames file's colours are those of every one of its pictures; a clock's those of its
// pictures every 250 ms over its loop with the seeds 1, 2 and 3. Prints one line for each
// file, `<name> <kind> <W>x<H> <colours>`, and the sheet: the picture at 0 of each file, a
// clock with the seed 1, 12 to a row, each at twice its size.

import fs from "node:fs";
import path from "node:path";
import {pathToFileURL} from "node:url";

import {png} from "./tile.mjs";

const TREE = process.env.ODRIG_TREE ?? "C:/Users/koren/src/Odrig/scratch/wt-seed52-impl";
const {odrg, odrgx} = await import(pathToFileURL(path.join(TREE, "converter", "lib", "index.js")).href);

function coloursOf(picture, into) {
  for (let at = 0; at < picture.length; at += 3) into.add((picture[at] << 16) | (picture[at + 1] << 8) | picture[at + 2]);
}

export function examine(bytes) {
  const colours = new Set();
  let first = null;
  let width = 0;
  let height = 0;
  let kind = "frames";
  if (odrgx.isContainer(bytes) && odrgx.readHeader(bytes).type !== odrgx.TYPES.frames) {
    const decoded = odrgx.decode(bytes);
    kind = decoded.settings.widget ?? decoded.type;
    ({width, height} = decoded.header);
    for (const seed of [1, 2, 3]) {
      for (let t = 0; t < decoded.header.loopMs; t += 250) coloursOf(odrgx.pictureAt(decoded, t, seed), colours);
    }
    first = odrgx.pictureAt(decoded, 0, 1);
  } else {
    const decoded = odrgx.isContainer(bytes) ? odrgx.decodeFrames(bytes) : odrg.decode(bytes);
    ({width, height} = decoded);
    for (const record of decoded.records) coloursOf(record.picture, colours);
    first = decoded.records[0].picture;
  }
  return {kind, width, height, colours: colours.size, first};
}

function main() {
  const [folder, sheetPath] = process.argv.slice(2);
  const names = fs.readdirSync(folder).filter((name) => /\.odrgx?$/.test(name)).sort();
  const results = names.map((name) => ({name, ...examine(new Uint8Array(fs.readFileSync(path.join(folder, name))))}));
  for (const one of results) console.log(`${one.name} ${one.kind} ${one.width}x${one.height} ${one.colours}`);
  const perRow = 12;
  const cell = 124;
  const rows = Math.ceil(results.length / perRow);
  const width = perRow * cell;
  const height = rows * cell;
  const rgb = new Uint8Array(3 * width * height).fill(24);
  results.forEach((one, index) => {
    const left = (index % perRow) * cell + 2;
    const top = Math.floor(index / perRow) * cell + 2;
    for (let y = 0; y < 120; y += 1) {
      for (let x = 0; x < 120; x += 1) {
        const from = 3 * ((one.height - 1 - Math.floor(y / 2)) * one.width + Math.floor(x / 2));
        rgb.set(one.first.subarray(from, from + 3), 3 * ((top + y) * width + left + x));
      }
    }
  });
  fs.mkdirSync(path.dirname(sheetPath), {recursive: true});
  fs.writeFileSync(sheetPath, png(width, height, rgb));
  const most = Math.max(...results.map((one) => one.colours));
  console.log(`${results.length} files, at most ${most} colours; sheet ${sheetPath}`);
}

if (process.argv[1] && path.resolve(process.argv[1]) === path.resolve(new URL(import.meta.url).pathname.replace(/^\/([A-Za-z]:)/, "$1"))) {
  main();
}
