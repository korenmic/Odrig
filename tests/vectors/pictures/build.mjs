// Builds the vectors of picture clocks of this folder with the converter's library. Run
// from the repository root: node tests/vectors/pictures/build.mjs
//
// valid/ holds containers of picture dials and picture displays with their JSON sources:
// X.odrgx and X.json. invalid/ holds containers that every reader refuses, each named by
// its reason and what is wrong.

import {mkdirSync, readdirSync, rmSync, writeFileSync} from "node:fs";
import {dirname, join} from "node:path";
import {fileURLToPath} from "node:url";

const HERE = dirname(fileURLToPath(import.meta.url));
const {odrgx} = await import(new URL("../../../converter/lib/index.js", import.meta.url).href);

// A dial's picture: a background of 0, a rim of 1 and a face of 2 in a disc about the
// centre of the canvas, twelve marks of 3 on the face, the top row first.
function dialPicture(width, height) {
  const rows = [];
  const radius = Math.floor(Math.min(width, height) / 2) - 1;
  for (let y = 0; y < height; y += 1) {
    let row = "";
    for (let x = 0; x < width; x += 1) {
      const u = 2 * x + 1 - width;
      const w = 2 * y + 1 - height;
      const distance = u * u + w * w;
      let index = 0;
      if (distance <= 4 * radius * radius) index = distance > 4 * (radius - 2) * (radius - 2) ? 1 : 2;
      const mark = index === 2 && distance > 4 * (radius - 5) * (radius - 5) && (Math.abs(u) <= 1 || Math.abs(w) <= 1);
      row += String(mark ? 3 : index);
    }
    rows.push(row);
  }
  return rows;
}

// A display's picture: a case of 1 about a screen of 2 on a background of 0.
function displayPicture(width, height, screen) {
  const rows = [];
  for (let y = 0; y < height; y += 1) {
    let row = "";
    for (let x = 0; x < width; x += 1) {
      const inCase = x >= screen.left - 3 && x < screen.left + screen.width + 3 && y >= screen.top - 3 && y < screen.top + screen.height + 3;
      const inScreen = x >= screen.left && x < screen.left + screen.width && y >= screen.top && y < screen.top + screen.height;
      row += inScreen ? "2" : inCase ? "1" : "0";
    }
    rows.push(row);
  }
  return rows;
}

function dial(more = {}) {
  const width = more.width ?? 60;
  const height = more.height ?? 60;
  const x = width;
  const y = height;
  return {
    width, height, widget: "picture-dial", seconds: 30, speedMin: 60, speedMax: 600, direction: "random", turns: 30,
    palette: [0x000000, 0xd4a017, 0xf4ecd0, 0x404040, 0xc02020], picture: dialPicture(width, height),
    hands: [
      {unit: "hour", color: 0, x, y, length: Math.floor(width * 0.45), tail: 2, half: 2, offset: 0},
      {unit: "minute", color: 0, x, y, length: Math.floor(width * 0.75), tail: 3, half: 1, offset: 0},
      {unit: "second", color: 4, x, y, length: Math.floor(width * 0.8), tail: 6, half: 1, offset: 0},
    ],
    caps: [{x, y, radius: 3, color: 4}],
    ...more,
  };
}

function display(more = {}) {
  const screen = {left: 8, top: 22, width: 44, height: 16};
  return {
    width: 60, height: 60, widget: "picture-display", seconds: 20, speedMin: 2, speedMax: 30, direction: "forward", turns: 0,
    palette: [0x000000, 0x808080, 0x103010, 0x40ff40, 0xffd040], picture: displayPicture(60, 60, screen),
    fields: [
      {...screen, top: 23, height: 7, font: "small", pattern: "Ih:Mm", digits: 3, colons: 4, blink: true, offset: 0},
      {...screen, top: 31, height: 6, font: "tiny", pattern: "Mm:Ss", digits: 4, colons: 3, blink: false, offset: -5},
    ],
    ...more,
  };
}

// The clocks of valid/, by name, as `loadsSource` gives them.
export const CLOCKS = {
  "dial": dial({}),
  "dial.backward": dial({direction: "backward", turns: 0, hands: dial().hands.slice(0, 2), caps: []}),
  "dial.small": dial({width: 21, height: 13, seconds: 1, speedMin: 3600, speedMax: 3600, turns: 100}),
  "display": display({}),
  "display.large": display({direction: "random", turns: 50, fields: [{left: 4, top: 20, width: 52, height: 20, font: "large", pattern: "Hh:Mm", digits: 3, colons: 4, blink: true, offset: 3}]}),
  "display.medium": display({fields: [
    {left: 8, top: 22, width: 21, height: 16, font: "medium", pattern: "Hh", digits: 3, colons: 3, blink: false, offset: 0},
    {left: 31, top: 22, width: 21, height: 16, font: "medium", pattern: "Mm", digits: 4, colons: 4, blink: false, offset: 0},
  ]}),
};

function sourceOf(clock) {
  const {palette, picture, ...rest} = clock;
  const loaded = odrgx.loadsSource(new TextEncoder().encode(JSON.stringify({
    version: 1, type: "widget", width: rest.width, height: rest.height, widget: rest.widget, seconds: rest.seconds, speed_min: rest.speedMin,
    speed_max: rest.speedMax, direction: rest.direction, turns: rest.turns, palette, picture,
    ...(rest.widget === "picture-dial" ? {hands: rest.hands, caps: rest.caps} : {fields: rest.fields}),
  })));
  return loaded.widget;
}

function changed(data, at, ...bytes) {
  const made = Uint8Array.from(data);
  made.set(bytes, at);
  return made;
}

function u32(value) {
  return [value & 0xff, (value >>> 8) & 0xff, (value >>> 16) & 0xff, value >>> 24];
}

// Every vector, by its place in the folder.
export function vectors() {
  const made = new Map();
  for (const [name, one] of Object.entries(CLOCKS)) {
    const widget = sourceOf(one);
    made.set(`valid/${name}.odrgx`, odrgx.encodeWidget(widget));
    made.set(`valid/${name}.json`, odrgx.dumpsWidget(widget));
  }
  const good = odrgx.encodeWidget(sourceOf(dial()));
  const shown = odrgx.encodeWidget(sourceOf(display()));
  const p = odrgx.HEADER_SIZE;
  const picture = p + odrgx.PICTURE_HEAD_SIZE + 3 * odrgx.HAND_SIZE + odrgx.CAP_SIZE;
  made.set("invalid/truncated.head.odrgx", good.subarray(0, p + 9));
  made.set("invalid/truncated.hand.odrgx", good.subarray(0, p + 25));
  made.set("invalid/bad-settings.direction.odrgx", changed(good, p + 8, 3));
  made.set("invalid/bad-settings.turns.odrgx", changed(good, p + 9, 101));
  made.set("invalid/bad-settings.forward-turns.odrgx", changed(good, p + 8, 0));
  made.set("invalid/bad-settings.no-hands.odrgx", changed(good, p + 10, 0));
  made.set("invalid/bad-settings.unit.odrgx", changed(good, p + 12, 3));
  made.set("invalid/bad-settings.pivot.odrgx", changed(good, p + 14, 121, 0));
  made.set("invalid/bad-settings.half.odrgx", changed(good, p + 20, 16));
  made.set("invalid/bad-settings.offset.odrgx", changed(good, p + 21, 13));
  made.set("invalid/bad-settings.radius.odrgx", changed(good, p + 46, 0));
  made.set("invalid/bad-settings.box.odrgx", changed(shown, p + 16, 53, 0));
  made.set("invalid/bad-settings.blink.odrgx", changed(shown, p + 23, 2));
  made.set("invalid/bad-settings.pattern.odrgx", changed(shown, p + 27, 0));
  made.set("invalid/bad-settings.character.odrgx", changed(shown, p + 27, 120));
  made.set("invalid/bad-settings.colour.odrgx", changed(good, p + 13, 5));
  made.set("invalid/unknown-font.odrgx", changed(shown, p + 20, 5));
  made.set("invalid/bad-magic.picture.odrgx", changed(good, picture, 0));
  made.set("invalid/canvas-mismatch.odrgx", changed(good, picture + 6, 59));
  made.set("invalid/bad-picture.frames.odrgx", changed(good, picture + 12, 2));
  made.set("invalid/bad-picture.no-palette.odrgx", changed(good, picture + 10, 0));
  made.set("invalid/bad-picture.palette.odrgx", changed(good, picture + 10, 9));
  made.set("invalid/trailing-bytes.odrgx", Uint8Array.of(...good, 0));
  made.set("invalid/payload-size.odrgx", changed(good, 16, ...u32(good.length - p - 1)));
  made.set("invalid/loop-mismatch.odrgx", changed(good, 12, ...u32(30001)));
  return made;
}

function main() {
  for (const folder of ["valid", "invalid"]) {
    rmSync(join(HERE, folder), {recursive: true, force: true});
    mkdirSync(join(HERE, folder));
  }
  for (const [name, data] of vectors()) {
    writeFileSync(join(HERE, name), data);
  }
  for (const folder of ["valid", "invalid"]) {
    console.log(`${folder}: ${readdirSync(join(HERE, folder)).length} files`);
  }
}

if (process.argv[1] === fileURLToPath(import.meta.url)) {
  main();
}
