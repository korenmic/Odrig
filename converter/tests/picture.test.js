import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import test from "node:test";
import {pathToFileURL} from "node:url";

import {draw, odrg, odrgx, textlayout} from "../lib/index.js";
import {ROOT, utf8} from "./support.js";

const WIDTH = 20;
const HEIGHT = 12;
const P = odrgx.HEADER_SIZE;
const HOUR = 3600000;
const MINUTE = 60000;
const HALF_DAY = 43200000;

// A picture of the canvas in three colours, its top row first: a frame of 1, a face of 2.
function rows() {
  const made = [];
  for (let y = 0; y < HEIGHT; y += 1) {
    let row = "";
    for (let x = 0; x < WIDTH; x += 1) row += y === 0 || y === HEIGHT - 1 || x === 0 || x === WIDTH - 1 ? "1" : "2";
    made.push(row);
  }
  return made;
}

function dialSource(more = {}) {
  return {
    version: 1, type: "widget", width: WIDTH, height: HEIGHT, widget: "picture-dial", seconds: 30, speed_min: 60, speed_max: 600,
    direction: "random", turns: 30, palette: [0x000000, 0xd4a017, 0xf4ecd0], picture: rows(),
    hands: [
      {unit: "hour", color: 0, x: 20, y: 12, length: 6, tail: 1, half: 2, offset: 0},
      {unit: "minute", color: 0, x: 20, y: 12, length: 9, tail: 2, half: 1, offset: 0},
      {unit: "second", color: 1, x: 20, y: 12, length: 10, tail: 3, half: 1, offset: -3},
    ],
    caps: [{x: 20, y: 12, radius: 2, color: 1}],
    ...more,
  };
}

function displaySource(more = {}) {
  return {
    version: 1, type: "widget", width: WIDTH, height: HEIGHT, widget: "picture-display", seconds: 20, speed_min: 2, speed_max: 30,
    direction: "forward", turns: 0, palette: [0x000000, 0x40c0ff, 0x102030], picture: rows(),
    fields: [{left: 1, top: 2, width: 18, height: 7, font: "tiny", pattern: "Ih:Mm", digits: 1, colons: 0, blink: true, offset: 0}],
    ...more,
  };
}

function encoded(source) {
  return odrgx.encodeSource(odrgx.loadsSource(utf8(JSON.stringify(source))));
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

function changed(data, at, ...bytes) {
  const made = Uint8Array.from(data);
  made.set(bytes, at);
  return made;
}

function u32(value) {
  return [value & 0xff, (value >>> 8) & 0xff, (value >>> 16) & 0xff, value >>> 24];
}

const decodeReason = (data) => reasonOf(() => odrgx.decode(data));
const sourceReason = (source) => reasonOf(() => encoded(source));

test("a picture dial and a picture display are written and read back", async (t) => {
  for (const source of [dialSource(), displaySource()]) {
    await t.test(source.widget, () => {
      const data = encoded(source);
      const decoded = odrgx.decode(data);
      assert.equal(decoded.type, "widget");
      assert.equal(decoded.header.loopMs, 1000 * source.seconds);
      assert.equal(decoded.header.payloadSize, data.length - P);
      assert.equal(new TextDecoder().decode(odrgx.dumpsWidget(odrgx.widgetOf(decoded))), `${JSON.stringify(source, null, 2)}\n`);
      assert.deepEqual(encoded(source), data);
    });
  }
});

test("the payload's bytes", () => {
  const data = encoded(dialSource());
  assert.deepEqual(Array.from(data.subarray(P, P + 12)), [4, 0, 30, 0, 60, 0, 88, 2, 2, 30, 3, 1]);
  assert.deepEqual(Array.from(data.subarray(P + 12, P + 22)), [0, 0, 20, 0, 12, 0, 6, 1, 2, 0]);
  assert.deepEqual(Array.from(data.subarray(P + 32, P + 42)), [2, 1, 20, 0, 12, 0, 10, 3, 1, 253]);
  assert.deepEqual(Array.from(data.subarray(P + 42, P + 48)), [20, 0, 12, 0, 2, 1]);
  const picture = odrg.decode(data.subarray(P + 48));
  assert.equal(picture.records.length, 1);
  assert.equal(picture.paletteSize, 3);
  assert.equal(picture.records[0].ms, odrgx.PICTURE_MS);
  assert.ok(picture.compressed);
  const display = encoded(displaySource({fields: [{...displaySource().fields[0], offset: -7}]}));
  assert.deepEqual(Array.from(display.subarray(P, P + 12)), [5, 0, 20, 0, 2, 0, 30, 0, 0, 0, 1, 0]);
  assert.deepEqual(Array.from(display.subarray(P + 12, P + 34)), [1, 0, 2, 0, 18, 0, 7, 0, 4, 1, 0, 1, 249, 0, 73, 104, 58, 77, 109, 0, 0, 0]);
});

test("the palette keeps the order of the source and the picture its rows", () => {
  const source = dialSource({palette: [0xf4ecd0, 0x000000, 0xd4a017]});
  const decoded = odrgx.decode(encoded(source));
  assert.deepEqual(decoded.settings.palette, [0xf4ecd0, 0x000000, 0xd4a017]);
  assert.deepEqual(odrgx.pictureRows(decoded.settings.picture, WIDTH, HEIGHT), rows());
  const pixels = odrgx.pictureAt(decoded, 0, 1);
  const bottomLeft = (pixels[0] << 16) | (pixels[1] << 8) | pixels[2];
  assert.equal(bottomLeft, 0x000000);
});

test("a picture widget is refused with the reasons of the core, in their order", async (t) => {
  const dial = encoded(dialSource());
  const display = encoded(displaySource());
  const at = P + 48;
  const cases = [
    ["unknown-widget", changed(dial, P, 0)],
    ["unknown-widget", changed(dial, P, 6)],
    ["truncated", dial.subarray(0, P + 8)],
    ["truncated", dial.subarray(0, P + 20)],
    ["bad-settings", changed(dial, P + 1, 1)],
    ["bad-settings", changed(dial, P + 2, 0, 0)],
    ["bad-settings", changed(dial, P + 2, 0x11, 0x0e)],
    ["bad-settings", changed(dial, P + 4, 0, 0)],
    ["bad-settings", changed(dial, P + 6, 59, 0)],
    ["bad-settings", changed(dial, P + 8, 3)],
    ["bad-settings", changed(dial, P + 9, 101)],
    ["bad-settings", changed(dial, P + 8, 0)],
    ["bad-settings", changed(dial, P + 10, 0)],
    ["bad-settings", changed(dial, P + 10, 9)],
    ["bad-settings", changed(dial, P + 11, 5)],
    ["bad-settings", changed(display, P + 11, 1)],
    ["bad-settings", changed(display, P + 10, 5)],
    ["bad-settings", changed(dial, P + 12, 3)],
    ["bad-settings", changed(dial, P + 14, 41, 0)],
    ["bad-settings", changed(dial, P + 16, 25, 0)],
    ["bad-settings", changed(dial, P + 18, 0)],
    ["bad-settings", changed(dial, P + 20, 0)],
    ["bad-settings", changed(dial, P + 20, 16)],
    ["bad-settings", changed(dial, P + 21, 13)],
    ["bad-settings", changed(dial, P + 21, 243)],
    ["bad-settings", changed(dial, P + 42, 41, 0)],
    ["bad-settings", changed(dial, P + 46, 0)],
    ["bad-settings", changed(display, P + 16, 0, 0)],
    ["bad-settings", changed(display, P + 12, 3, 0)],
    ["bad-settings", changed(display, P + 18, 11, 0)],
    ["unknown-font", changed(display, P + 20, 5)],
    ["unknown-font", changed(display, P + 20, 0)],
    ["bad-settings", changed(display, P + 23, 2)],
    ["bad-settings", changed(display, P + 24, 243)],
    ["bad-settings", changed(display, P + 25, 1)],
    ["bad-settings", changed(display, P + 26, 0, 0, 0, 0, 0)],
    ["bad-settings", changed(display, P + 27, 120)],
    ["bad-settings", changed(display, P + 27, 0)],
    ["bad-magic", changed(dial, at, 0)],
    ["canvas-mismatch", changed(dial, at + 6, 21)],
    ["bad-picture", changed(dial, at + 12, 2)],
    ["bad-picture", changed(dial, at + 10, 0)],
    ["bad-picture", changed(dial, at + 10, 9)],
    ["bad-settings", changed(dial, P + 13, 3)],
    ["bad-settings", changed(dial, P + 47, 3)],
    ["bad-settings", changed(display, P + 22, 3)],
    ["bad-deflate", changed(dial, at + 16, 0xff, 0xff, 0xff)],
    ["trailing-bytes", Uint8Array.of(...dial, 0)],
    ["payload-size", changed(dial, 16, ...u32(dial.length - P + 1))],
    ["payload-size", changed(dial, 16, ...u32(dial.length - P - 1))],
    ["loop-mismatch", changed(dial, 12, 0x31, 0x75)],
    ["bad-picture", changed(changed(dial, P + 13, 3), at + 10, 0)],
    ["bad-settings", changed(changed(dial, P + 9, 101), at, 0)],
    ["bad-settings", changed(changed(dial, P + 12, 3), at, 0)],
  ];
  for (const [reason, data] of cases) {
    await t.test(`${reason} ${cases.findIndex((one) => one[1] === data)}`, () => {
      assert.equal(decodeReason(data), reason);
    });
  }
  await t.test("the clocks of 20 bytes keep their reasons", () => {
    const clock = odrgx.encodeWidget({width: 60, height: 60, widget: "analog", seconds: 30, face: 1, hands: 2, rim: 3, background: 0, speedMin: 60, speedMax: 600});
    assert.equal(decodeReason(changed(clock, 16, 21)), "payload-size");
    assert.equal(decodeReason(changed(clock, 16, 19)), "payload-size");
    assert.equal(decodeReason(changed(clock, P, 6)), "unknown-widget");
    assert.equal(decodeReason(clock), null);
  });
});

test("the JSON source of a picture clock is read strictly", async (t) => {
  const hand = dialSource().hands[0];
  const field = displaySource().fields[0];
  const cases = [
    ["missing-member", dialSource({widget: "picture-clock"})],
    ["out-of-range", dialSource({direction: "sideways"})],
    ["out-of-range", dialSource({direction: "forward", turns: 5})],
    ["out-of-range", dialSource({turns: 101})],
    ["out-of-range", dialSource({palette: []})],
    ["out-of-range", dialSource({palette: [1, 2, 3, 4, 5, 6, 7, 8, 9]})],
    ["out-of-range", dialSource({palette: [1, 2, 1]})],
    ["out-of-range", dialSource({palette: [0x1000000, 2, 3]})],
    ["out-of-range", dialSource({picture: rows().slice(1)})],
    ["out-of-range", dialSource({picture: [rows()[0].slice(1), ...rows().slice(1)]})],
    ["out-of-range", dialSource({picture: [`3${rows()[0].slice(1)}`, ...rows().slice(1)]})],
    ["out-of-range", dialSource({hands: []})],
    ["out-of-range", dialSource({hands: Array(9).fill(hand)})],
    ["out-of-range", dialSource({hands: [{...hand, color: 3}]})],
    ["out-of-range", dialSource({hands: [{...hand, x: 41}]})],
    ["out-of-range", dialSource({hands: [{...hand, unit: "day"}]})],
    ["out-of-range", dialSource({hands: [{...hand, half: 16}]})],
    ["out-of-range", dialSource({hands: [{...hand, offset: 13}]})],
    ["out-of-range", dialSource({caps: Array(5).fill(dialSource().caps[0])})],
    ["out-of-range", displaySource({fields: [{...field, width: 20}]})],
    ["out-of-range", displaySource({fields: [{...field, font: "huge"}]})],
    ["out-of-range", displaySource({fields: [{...field, pattern: "Ih:Mmx"}]})],
    ["out-of-range", displaySource({fields: [{...field, pattern: ""}]})],
    ["out-of-range", displaySource({fields: [{...field, pattern: "Ih:Mm:Ss "}]})],
    ["out-of-range", displaySource({fields: [{...field, digits: 3}]})],
    ["bad-type", displaySource({fields: [{...field, blink: 1}]})],
    ["bad-type", dialSource({picture: [1, ...rows().slice(1)]})],
    ["missing-member", dialSource({hands: [{unit: "hour", color: 0, x: 20, y: 12, length: 6, half: 2, offset: 0}]})],
    ["unknown-member", displaySource({fields: [{...field, colour: 1}]})],
    ["unknown-member", dialSource({fields: []})],
    ["missing-member", (({caps, ...rest}) => rest)(dialSource())],
  ];
  for (const [reason, source] of cases) {
    await t.test(`${reason} ${cases.findIndex((one) => one[1] === source)}`, () => {
      assert.equal(sourceReason(source), reason);
    });
  }
});

test("the time of a picture widget", async (t) => {
  const settings = (direction, turns = 0) => ({speedMin: 60, speedMax: 600, direction, turns});

  await t.test("the seed chooses what it chose for the clocks, then the way and the chance", () => {
    for (let seed = 1; seed < 400; seed += 7) {
      const analog = draw.clockOf({speedMin: 60, speedMax: 600}, seed);
      const picture = draw.clockOf(settings("random", 40), seed);
      assert.deepEqual({...picture, back: undefined, chance: undefined}, {...analog, back: undefined, chance: undefined});
      assert.ok(picture.back === 0 || picture.back === 1);
      assert.ok(picture.chance >= 0 && picture.chance <= 40);
      assert.equal(analog.chance, 0);
    }
  });

  await t.test("forward is the time of the clocks, backward its way back from the same start", () => {
    for (let seed = 1; seed < 2000; seed += 97) {
      const clock = draw.clockOf(settings("forward"), seed);
      for (const at of [0, 1, 999, 7000, 33333, 600000, 3600000]) {
        assert.equal(draw.pictureTime(settings("forward"), clock, seed, at), draw.virtualTime(clock, at));
        assert.equal(draw.pictureTime(settings("backward"), clock, seed, at), 2 * clock.start - draw.virtualTime(clock, at));
      }
    }
  });

  await t.test("a random way turns only at the swing's slowest points, as the seed says", () => {
    let turned = 0;
    for (let seed = 3; seed < 3000; seed += 131) {
      const chosen = settings("random", 100);
      const clock = draw.clockOf(chosen, seed);
      const first = Math.floor((clock.period * ((3 * 16777216 - clock.phase * 65536 + 67108864 * 4) % 67108864)) / 67108864);
      const slowest = new Set();
      for (let k = 0; k < 8; k += 1) slowest.add(first + k * clock.period);
      let way = clock.back === 1 ? -1 : 1;
      let point = 0;
      let before = draw.pictureTime(chosen, clock, seed, 0);
      for (let at = 1; at < first + 7 * clock.period; at += 1) {
        const now = draw.pictureTime(chosen, clock, seed, at);
        const step = now - before;
        assert.ok(step * way >= 0, `seed ${seed} at ${at}: a step of ${step} on a way of ${way}`);
        assert.ok(Math.abs(step) <= chosen.speedMax + 1, `seed ${seed} at ${at}: a jump of ${step}`);
        before = now;
        if (slowest.has(at)) {
          point += 1;
          if (draw.mix((seed ^ point) >>> 0) % 100 < clock.chance) {
            way = -way;
            turned += 1;
          }
        }
      }
    }
    assert.ok(turned > 10);
  });

  await t.test("a field's pattern", () => {
    const at = (hours, minutes, seconds) => hours * HOUR + minutes * MINUTE + seconds * 1000;
    assert.equal(draw.patternText("Ih:Mm:Ss", at(1, 23, 45)), "1:23:45");
    assert.equal(draw.patternText("Ih:Mm:Ss", at(10, 5, 9)), "10:05:09");
    assert.equal(draw.patternText("Hh:Mm", at(1, 23, 0)), "01:23");
    assert.equal(draw.patternText("Hh:Mm", 0), "12:00");
    assert.equal(draw.patternText("Ih", at(11, 59, 59)), "11");
    assert.equal(draw.patternText("Mm:Ss", at(3, 7, 2)), "07:02");
    assert.equal(draw.patternText("H h M m", at(12, 34, 0)), "1 2 3 4");
  });
});

// The pixel of a picture at x, y from the top left.
function layerAt(layer, x, y) {
  return layer[(HEIGHT - 1 - y) * WIDTH + x];
}

test("drawing a picture widget", async (t) => {
  await t.test("a hand lies along the angle of its unit's time, and a cap over it", () => {
    const source = dialSource({hands: [{unit: "minute", color: 0, x: 20, y: 12, length: 10, tail: 0, half: 1, offset: 0}], caps: []});
    const decoded = odrgx.decode(encoded(source));
    const settings = decoded.settings;
    for (const [seed, ms] of [[1, 0], [7, 5000], [99, 12345], [4242, 99999]]) {
      const time = draw.pictureTime(settings, draw.clockOf(settings, seed), seed, ms);
      const angle = (2 * Math.PI * (((time % HOUR) + HOUR) % HOUR)) / HOUR;
      const layer = draw.overlayOf(settings, seed, ms, {width: WIDTH, height: HEIGHT});
      let marked = 0;
      for (let y = 0; y < HEIGHT; y += 1) {
        for (let x = 0; x < WIDTH; x += 1) {
          if (layerAt(layer, x, y) === 0) continue;
          marked += 1;
          assert.equal(layerAt(layer, x, y), 1);
          const u = 2 * x + 1 - 20;
          const w = 2 * y + 1 - 12;
          const along = u * Math.sin(angle) - w * Math.cos(angle);
          const across = Math.abs(u * Math.cos(angle) + w * Math.sin(angle));
          assert.ok(along >= -0.01 && along <= 10.01 && across <= 1.01, `seed ${seed}: ${x}, ${y} is off the hand`);
        }
      }
      assert.ok(marked >= 3, `seed ${seed}: ${marked} pixels`);
    }
    const capped = odrgx.decode(encoded(dialSource())).settings;
    const layer = draw.overlayOf(capped, 5, 0, {width: WIDTH, height: HEIGHT});
    assert.equal(layerAt(layer, 9, 5), 2);
    assert.equal(layerAt(layer, 10, 6), 2);
  });

  await t.test("a display draws its pattern in its box, and the colons blink", () => {
    const settings = odrgx.decode(encoded(displaySource({speed_min: 1, speed_max: 1}))).settings;
    const canvas = {width: WIDTH, height: HEIGHT};
    let compared = 0;
    for (let seed = 1; compared < 5; seed += 1) {
      const time = draw.pictureTime(settings, draw.clockOf(settings, seed), seed, 0);
      if (((time % MINUTE) + MINUTE) % MINUTE > MINUTE - 1000) continue;
      compared += 1;
      const shown = draw.overlayOf(settings, seed, 0, canvas);
      const hidden = draw.overlayOf(settings, seed, 500, canvas);
      const unblinking = {...settings, fields: [{...settings.fields[0], blink: false}]};
      assert.deepEqual(draw.overlayOf(unblinking, seed, 500, canvas), shown);
      let colon = 0;
      for (let y = 0; y < HEIGHT; y += 1) {
        for (let x = 0; x < WIDTH; x += 1) {
          const inBox = x >= 1 && x < 19 && y >= 2 && y < 9;
          if (!inBox) assert.equal(layerAt(shown, x, y), 0);
          if (layerAt(shown, x, y) !== layerAt(hidden, x, y)) {
            assert.deepEqual([layerAt(shown, x, y), layerAt(hidden, x, y)], [1, 0]);
            colon += 1;
          }
        }
      }
      assert.equal(colon, 2);
      const text = draw.patternText("Ih:Mm", ((time % HALF_DAY) + HALF_DAY) % HALF_DAY);
      const lit = Array.from(shown).filter((value) => value === 2).length;
      assert.ok(lit > 4 * text.replace(":", "").length, `${text}: ${lit} pixels of digits`);
    }
  });

  await t.test("the picture shows where the layer has nothing", () => {
    const decoded = odrgx.decode(encoded(displaySource()));
    const pixels = odrgx.pictureAt(decoded, 0, 1);
    const layer = draw.overlayOf(decoded.settings, 1, 0, {width: WIDTH, height: HEIGHT});
    for (let pixel = 0; pixel < WIDTH * HEIGHT; pixel += 1) {
      const index = layer[pixel] !== 0 ? layer[pixel] - 1 : decoded.settings.picture[pixel];
      const colour = decoded.settings.palette[index];
      assert.deepEqual(Array.from(pixels.subarray(3 * pixel, 3 * pixel + 3)), [colour >> 16, (colour >> 8) & 0xff, colour & 0xff]);
    }
  });

  await t.test("a field clips what does not fit its box", () => {
    const settings = odrgx.decode(encoded(displaySource({fields: [{...displaySource().fields[0], left: 4, width: 5, font: "large"}]}))).settings;
    const layer = draw.overlayOf(settings, 3, 0, {width: WIDTH, height: HEIGHT});
    for (let y = 0; y < HEIGHT; y += 1) {
      for (let x = 0; x < WIDTH; x += 1) {
        if (x < 4 || x >= 9 || y < 2 || y >= 9) assert.equal(layerAt(layer, x, y), 0);
      }
    }
  });
});

test("the font tiny is for displays, not for texts", () => {
  assert.equal(draw.displayFont("tiny").table.name, "tiny");
  assert.equal(draw.displayFont("large").scale, 2);
  assert.ok(!("tiny" in textlayout.FONTS));
  assert.equal(textlayout.fontOf(4), null);
  const text = odrgx.encodeSource(odrgx.loadsSource(utf8(JSON.stringify({
    version: 1, type: "text", width: 60, height: 60, text: "12", font: "small", color: 16777215, background: 0, align: "center",
    valign: "middle", direction: "auto", wrap: false, effect: "static", motion: "left", speed: 20, pause_ms: 1000,
  }))));
  assert.equal(decodeReason(changed(text, P, 4)), "unknown-font");
});

test("the vectors of picture clocks", async (t) => {
  const folder = path.join(ROOT, "tests", "vectors", "pictures");
  const builder = await import(pathToFileURL(path.join(folder, "build.mjs")).href);
  const read = (...parts) => new Uint8Array(fs.readFileSync(path.join(folder, ...parts)));

  await t.test("they are what their builder makes", () => {
    const made = builder.vectors();
    const onDisk = ["valid", "invalid"].flatMap((part) => fs.readdirSync(path.join(folder, part)).map((name) => `${part}/${name}`));
    assert.deepEqual(onDisk.sort(), [...made.keys()].sort(), "run node tests/vectors/pictures/build.mjs");
    for (const [name, data] of made) assert.deepEqual(read(name), data, name);
  });

  await t.test("a valid one decodes to its source, and its source is written as it is", () => {
    const names = fs.readdirSync(path.join(folder, "valid")).filter((name) => name.endsWith(".odrgx"));
    assert.ok(names.length >= 6);
    for (const name of names) {
      const data = read("valid", name);
      const source = read("valid", name.replace(/\.odrgx$/, ".json"));
      assert.deepEqual(odrgx.dumpsWidget(odrgx.widgetOf(odrgx.decode(data))), source, name);
      assert.deepEqual(odrgx.encodeSource(odrgx.loadsSource(source)), data, name);
    }
  });

  await t.test("an invalid one is refused with the reason of its name", () => {
    const names = fs.readdirSync(path.join(folder, "invalid"));
    assert.ok(names.length >= 20);
    for (const name of names) assert.equal(decodeReason(read("invalid", name)), name.split(".")[0], name);
  });
});
