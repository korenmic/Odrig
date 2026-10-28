import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import test from "node:test";

import {inventory, motion, odrg, odrgx, strictjson} from "../lib/index.js";
import {runJs, temporary, utf8} from "./support.js";

const WIDTH = 12;
const HEIGHT = 10;
const CANVAS = {width: WIDTH, height: HEIGHT};

// A picture of the canvas, its top row first: a background of 0, a vessel of 1 with its
// top half empty and its bottom half filled with 2, and a bar of 3 across the middle.
function rows() {
  const made = [];
  for (let y = 0; y < HEIGHT; y += 1) {
    let row = "";
    for (let x = 0; x < WIDTH; x += 1) {
      if (x >= 2 && x < 6 && y >= 1 && y < 9) row += y >= 5 ? "2" : "1";
      else if (x >= 7 && x < 11 && y === 5) row += "3";
      else row += "0";
    }
    made.push(row);
  }
  return made;
}

const PALETTE = [0x000000, 0x203040, 0xd4a017, 0xf4ecd0];

function loaded(motionSource) {
  return motion.loadsMotion(strictjson.loads(utf8(JSON.stringify(motionSource))), WIDTH, HEIGHT, PALETTE.length);
}

function base() {
  return odrgx.loadsPicture(PALETTE, rows(), WIDTH, HEIGHT).picture;
}

// The index of pixel x, y from the top left of a picture of the format's order.
function at(picture, x, y) {
  return picture[(HEIGHT - 1 - y) * WIDTH + x];
}

function reasonOf(action) {
  try {
    action();
  } catch (error) {
    if (error.reason !== undefined) return error.reason;
    throw error;
  }
  return null;
}

const LEVEL = {kind: "level", box: [2, 1, 4, 8], inside: [1, 2], fill: 2, empty: 1, rests: "bottom", start: 50, half: 0};

test("a level falls and rises again over the loop", () => {
  const made = loaded({seconds: 10, frame_ms: 50, parts: [LEVEL]});
  const filledRows = (t) => {
    const picture = motion.pictureAt(base(), CANVAS, made, t);
    let count = 0;
    for (let y = 1; y < 9; y += 1) count += at(picture, 3, y) === 2 ? 1 : 0;
    return count;
  };
  assert.equal(filledRows(0), 4);
  assert.equal(filledRows(2500), 2);
  assert.equal(filledRows(5000), 0);
  assert.equal(filledRows(7500), 2);
  assert.deepEqual(motion.pictureAt(base(), CANVAS, made, 10000), motion.pictureAt(base(), CANVAS, made, 0));
  const rising = loaded({seconds: 10, frame_ms: 50, parts: [{...LEVEL, rests: "top", start: 0, half: 100}]});
  const picture = motion.pictureAt(base(), CANVAS, rising, 5000);
  assert.equal(at(picture, 3, 1), 2);
  assert.equal(at(picture, 3, 8), 2);
  assert.equal(at(picture, 1, 4), 0);
});

test("a flicker goes through its variants step by step, and a pulse there and back", () => {
  const flicker = loaded({seconds: 12, frame_ms: 50, parts: [{kind: "flicker", box: [7, 5, 4, 1], variants: [[], [[3, 2]], [[3, 1]]], step_ms: 200}]});
  assert.deepEqual([0, 200, 400, 600].map((t) => at(motion.pictureAt(base(), CANVAS, flicker, t), 8, 5)), [3, 2, 1, 3]);
  assert.equal(at(motion.pictureAt(base(), CANVAS, flicker, 200), 1, 1), 0);
  const pulse = loaded({seconds: 12, frame_ms: 50, parts: [{kind: "pulse", box: [7, 5, 4, 1], variants: [[], [[3, 2]], [[3, 1]]]}]});
  assert.deepEqual([0, 3000, 6000, 9000, 11999].map((t) => at(motion.pictureAt(base(), CANVAS, pulse, t), 8, 5)), [3, 2, 1, 2, 2]);
});

test("a turn turns the pixels of its colours about the centre and leaves its colour behind them", () => {
  const made = loaded({seconds: 10, frame_ms: 50, parts: [{kind: "turn", box: [6, 1, 6, 9], moving: [3], behind: 0, centre: [18, 11], degrees: 360}]});
  const quarter = motion.pictureAt(base(), CANVAS, made, 2500);
  let upright = 0;
  for (let y = 1; y < 10; y += 1) upright += [8, 9].filter((x) => at(quarter, x, y) === 3).length;
  assert.ok(upright >= 3, `a quarter turn stands the bar upright: ${upright} pixels`);
  assert.equal(at(quarter, 7, 5) === 3 && at(quarter, 10, 5) === 3, false);
  const half = motion.pictureAt(base(), CANVAS, made, 5000);
  assert.equal([7, 8, 9, 10].filter((x) => at(half, x, 5) === 3).length, 4);
  assert.deepEqual(motion.pictureAt(base(), CANVAS, made, 10000), motion.pictureAt(base(), CANVAS, made, 0));
});

test("a swing goes to either side and back", () => {
  const made = loaded({seconds: 10, frame_ms: 50, parts: [{kind: "swing", box: [6, 0, 6, 10], moving: [3], behind: 0, centre: [15, 11], degrees: 45, swings: 1}]});
  const at0 = motion.pictureAt(base(), CANVAS, made, 0);
  const right = motion.pictureAt(base(), CANVAS, made, 2500);
  const left = motion.pictureAt(base(), CANVAS, made, 7500);
  assert.notDeepEqual(right, at0);
  assert.notDeepEqual(left, at0);
  assert.notDeepEqual(left, right);
  assert.deepEqual(motion.pictureAt(base(), CANVAS, made, 5000), at0);
});

test("the frames of a motion keep the palette's colours, loop whole, and are the same every time", () => {
  const made = loaded({seconds: 10, frame_ms: 100, parts: [LEVEL, {kind: "turn", box: [6, 1, 6, 9], moving: [3], behind: 0, centre: [18, 11], degrees: -180}]});
  const frames = motion.framesOf(base(), PALETTE, CANVAS, made);
  assert.equal(frames.frames.length, 100);
  assert.ok(frames.frames.every((frame) => frame.ms === 100));
  const colours = new Set();
  for (const frame of frames.frames) {
    for (let p = 0; p < frame.picture.length; p += 3) colours.add((frame.picture[p] << 16) | (frame.picture[p + 1] << 8) | frame.picture[p + 2]);
  }
  assert.ok([...colours].every((colour) => PALETTE.includes(colour)));
  assert.deepEqual(odrg.encode(frames), odrg.encode(motion.framesOf(base(), PALETTE, CANVAS, made)));
  assert.equal(odrg.decode(odrg.encode(frames)).records.reduce((sum, record) => sum + record.ms, 0), 10000);
});

test("a motion is read strictly", async (t) => {
  const good = {seconds: 10, frame_ms: 50, parts: [LEVEL]};
  const cases = [
    ["out-of-range", {...good, seconds: 9}],
    ["out-of-range", {...good, frame_ms: 30}],
    ["out-of-range", {...good, frame_ms: 55}],
    ["out-of-range", {...good, parts: []}],
    ["out-of-range", {...good, parts: [{...LEVEL, kind: "spin"}]}],
    ["out-of-range", {...good, parts: [{...LEVEL, box: [2, 1, 11, 8]}]}],
    ["out-of-range", {...good, parts: [{...LEVEL, inside: [4]}]}],
    ["out-of-range", {...good, parts: [{...LEVEL, rests: "middle"}]}],
    ["out-of-range", {...good, parts: [{...LEVEL, half: 101}]}],
    ["out-of-range", {...good, parts: [{kind: "flicker", box: [0, 0, 2, 2], variants: [[], [[1, 2]]], step_ms: 3000}]}],
    ["out-of-range", {...good, parts: [{kind: "flicker", box: [0, 0, 2, 2], variants: [[]], step_ms: 100}]}],
    ["out-of-range", {...good, parts: [{kind: "pulse", box: [0, 0, 2, 2], variants: [[], [[1, 2, 3]]]}]}],
    ["out-of-range", {...good, parts: [{kind: "turn", box: [0, 0, 2, 2], moving: [1], behind: 0, centre: [25, 0], degrees: 90}]}],
    ["out-of-range", {...good, parts: [{kind: "swing", box: [0, 0, 2, 2], moving: [1], behind: 0, centre: [2, 2], degrees: 0, swings: 1}]}],
    ["missing-member", {...good, parts: [{kind: "turn", box: [0, 0, 2, 2], moving: [1], behind: 0, centre: [2, 2]}]}],
    ["unknown-member", {...good, parts: [{...LEVEL, swings: 1}]}],
    ["bad-type", {...good, parts: [{...LEVEL, rests: 1}]}],
  ];
  for (const [index, [reason, source]] of cases.entries()) {
    await t.test(`${reason} ${index}`, () => {
      assert.equal(reasonOf(() => loaded(source)), reason);
    });
  }
});

// A small inventory: a dial, a display and a motion of the canvas.
function smallInventory(more = {}) {
  return {
    version: 1, width: WIDTH, height: HEIGHT,
    tiles: [
      {
        name: "clock-001", tile: 1, kind: "dial", about: "a dial", palette: PALETTE, picture: rows(),
        clock: {seconds: 30, speed_min: 60, speed_max: 600, direction: "random", turns: 30,
          hands: [{unit: "hour", color: 0, x: 12, y: 10, length: 4, tail: 0, half: 1, offset: 0}], caps: []},
      },
      {
        name: "clock-002", tile: 2, kind: "display", about: "a display", palette: PALETTE, picture: rows(),
        clock: {seconds: 30, speed_min: 2, speed_max: 30, direction: "backward", turns: 0,
          fields: [{left: 0, top: 2, width: 12, height: 6, font: "tiny", pattern: "Ss", digits: 3, colons: 3, blink: false, offset: 0}]},
      },
      {name: "clock-003", tile: 3, kind: "motion", about: "a vessel", palette: PALETTE, picture: rows(), motion: {seconds: 10, frame_ms: 50, parts: [LEVEL]}},
    ],
    ...more,
  };
}

test("an inventory makes a file for each tile, which the readers read", () => {
  const read = inventory.loads(utf8(JSON.stringify(smallInventory())));
  const files = inventory.filesOf(read);
  assert.deepEqual(files.map((file) => [file.name, file.kind, file.file]), [
    ["clock-001", "dial", "clock-001.odrgx"], ["clock-002", "display", "clock-002.odrgx"], ["clock-003", "motion", "clock-003.odrg"],
  ]);
  const dial = odrgx.decode(files[0].bytes);
  assert.equal(dial.settings.widget, "picture-dial");
  assert.deepEqual(dial.settings.palette, PALETTE);
  assert.equal(odrgx.decode(files[1].bytes).settings.direction, "backward");
  const frames = odrg.decode(files[2].bytes);
  assert.equal(frames.records.reduce((sum, record) => sum + record.ms, 0), 10000);
  assert.ok(frames.paletteSize <= PALETTE.length);
  assert.deepEqual(inventory.filesOf(inventory.loads(utf8(JSON.stringify(smallInventory())))), files);
});

test("an inventory is read strictly and its refusals name the tile", async (t) => {
  const tiles = smallInventory().tiles;
  const cases = [
    ["bad-version", smallInventory({version: 2})],
    ["missing-member", (({tiles: _, ...rest}) => rest)(smallInventory())],
    ["out-of-range", smallInventory({tiles: []})],
    ["out-of-range", smallInventory({tiles: [{...tiles[0], kind: "sundial"}]})],
    ["duplicate-id", smallInventory({tiles: [tiles[0], {...tiles[1], name: "clock-001"}]})],
    ["out-of-range", smallInventory({tiles: [{...tiles[0], name: "clock 1"}]})],
    ["unknown-member", smallInventory({tiles: [{...tiles[2], clock: tiles[0].clock}]})],
    ["missing-member", smallInventory({tiles: [{...tiles[0], clock: {...tiles[0].clock, caps: undefined}}]})],
    ["out-of-range", smallInventory({tiles: [{...tiles[0], clock: {...tiles[0].clock, hands: [{...tiles[0].clock.hands[0], color: 4}]}}]})],
    ["out-of-range", smallInventory({tiles: [{...tiles[2], palette: [...PALETTE, 1, 2, 3, 4, 5]}]})],
  ];
  for (const [index, [reason, source]] of cases.entries()) {
    await t.test(`${reason} ${index}`, () => {
      let caught = null;
      try {
        inventory.loads(utf8(JSON.stringify(source)));
      } catch (error) {
        caught = error;
      }
      assert.equal(caught?.reason, reason);
      if (index >= 3) assert.match(caught.detail, /^clock[- ][0-9]+: /);
    });
  }
});

test("the command line makes the files of an inventory", (t) => {
  const folder = temporary(t);
  const given = path.join(folder, "inventory.json");
  fs.writeFileSync(given, JSON.stringify(smallInventory()));
  const out = path.join(folder, "made");
  const done = runJs(["clocks", given, "--out", out]);
  assert.equal(done.status, 0, done.err);
  const lines = done.out.trim().split("\n");
  assert.deepEqual(lines.map((line) => line.split(" ").slice(0, 2)), [["clock-001.odrgx", "dial"], ["clock-002.odrgx", "display"], ["clock-003.odrg", "motion"]]);
  assert.deepEqual(fs.readdirSync(out).sort(), ["clock-001.odrgx", "clock-002.odrgx", "clock-003.odrg"]);
  for (const name of fs.readdirSync(out)) assert.equal(runJs(["check", path.join(out, name)]).status, 0, name);
  fs.writeFileSync(given, JSON.stringify(smallInventory({version: 2})));
  const refused = runJs(["clocks", given, "--out", path.join(folder, "other")]);
  assert.equal(refused.status, 1);
  assert.match(refused.err, /bad-version/);
  assert.equal(fs.existsSync(path.join(folder, "other")), false);
  assert.equal(runJs(["clocks", given]).status, 2);
});
