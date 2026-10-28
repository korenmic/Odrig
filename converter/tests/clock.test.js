import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import test from "node:test";
import {pathToFileURL} from "node:url";

import {draw, errors, fonttables, odrgx, textlayout} from "../lib/index.js";
import {ROOT, runJs, temporary, utf8} from "./support.js";

// A clock with every setting at a plain value, and some of them changed.
function clockOf(more = {}) {
  return {width: 60, height: 60, widget: "analog", seconds: 30, face: 0xf4ecd0, hands: 0x202020, rim: 0xd4a017, background: 0, speedMin: 60, speedMax: 600, ...more};
}

function sourceOf(more = {}) {
  const clock = clockOf(more);
  return {
    version: 1, type: "widget", width: clock.width, height: clock.height, widget: clock.widget, seconds: clock.seconds, face: clock.face,
    hands: clock.hands, rim: clock.rim, background: clock.background, speed_min: clock.speedMin, speed_max: clock.speedMax,
  };
}

function reasonOf(action) {
  try {
    action();
  } catch (error) {
    if (error instanceof errors.Rejection) return error.reason;
    throw error;
  }
  return null;
}

// A row of whole numbers from a seed, for choosing cases.
function numbers(seed) {
  let state = seed;
  return (below) => {
    state = (Math.imul(state, 1103515245) + 12345) >>> 0;
    return state % below;
  };
}

function pixelAt(picture, canvas, x, y) {
  const at = 3 * ((canvas.height - 1 - y) * canvas.width + x);
  return (picture[at] << 16) | (picture[at + 1] << 8) | picture[at + 2];
}

const HALF_DAY = 43200000;

test("the seed", async (t) => {
  await t.test("mix is MurmurHash3's finalizer", () => {
    assert.equal(draw.mix(0), 0);
    assert.equal(draw.mix(1), 0x514e28b7);
    assert.equal(draw.mix(0xdeadbeef), 0x0de5c6a9);
  });

  await t.test("a seed is never 0, and the noise, the id and the start each change it", () => {
    const seeds = new Set();
    for (let id = 1; id <= 50; id += 1) {
      for (const start of [0, 1000, 4294967296 + 1000]) seeds.add(draw.seedOf(7, id, start));
    }
    assert.ok(!seeds.has(0));
    assert.ok(seeds.size >= 100);
    assert.notEqual(draw.seedOf(7, 1, 1000), draw.seedOf(8, 1, 1000));
    assert.equal(draw.stir(0, 1000), draw.mix(1000));
  });

  await t.test("a seed chooses the start, the speed and the melting watch's shape within their ranges", () => {
    const next = numbers(3);
    for (let one = 0; one < 500; one += 1) {
      const least = 1 + next(3600);
      const greatest = least + next(3601 - least);
      const clock = draw.clockOf({speedMin: least, speedMax: greatest}, next(4294967296));
      assert.ok(clock.start >= 0 && clock.start < HALF_DAY);
      assert.ok(clock.base >= least && clock.base <= greatest);
      assert.ok(clock.base - clock.swing >= least && clock.base + clock.swing <= greatest);
      assert.ok(clock.period >= 6000 && clock.period <= 20000 && clock.phase < 1024);
      assert.ok(clock.tilt >= 25 && clock.tilt <= 40);
    }
  });
});

test("the virtual time", async (t) => {
  await t.test("it moves at a speed within the clock's range at any spacing of the refreshes, and never back", () => {
    const next = numbers(11);
    for (let one = 0; one < 200; one += 1) {
      const least = 1 + next(3600);
      const greatest = least + next(3601 - least);
      const clock = draw.clockOf({speedMin: least, speedMax: greatest}, 1 + next(4294967295));
      let before = 0;
      let then = draw.virtualTime(clock, 0);
      assert.equal(then, clock.start);
      for (let step = 0; step < 300; step += 1) {
        const now = before + 1 + next(next(2) === 0 ? 40 : 5000);
        const value = draw.virtualTime(clock, now);
        const spent = now - before;
        assert.ok(value - then >= least * spent - 1 && value - then <= greatest * spent + 1, `${value - then} in ${spent} ms at ${least} to ${greatest}`);
        assert.ok(value >= then);
        [before, then] = [now, value];
      }
    }
  });

  await t.test("it is the same however the time was reached", () => {
    const clock = draw.clockOf({speedMin: 5, speedMax: 900}, 99);
    const at = draw.virtualTime(clock, 123456);
    for (let first = 0; first < 123456; first += 9999) draw.virtualTime(clock, first);
    assert.equal(draw.virtualTime(clock, 123456), at);
  });

  await t.test("the sine table read between its entries", () => {
    assert.equal(draw.sine(0), 0);
    assert.equal(draw.sine(16777216), 16384);
    assert.equal(draw.cosine(0), 16384);
    assert.equal(draw.sine(33554432), 0);
    assert.equal(draw.sine(-16777216), -16384);
    assert.equal(draw.sine(32768), 50);
  });
});

test("the clocks draw the virtual time", async (t) => {
  const canvas = {width: 60, height: 60};
  const time = (settings, seed, ms) => {
    const value = draw.virtualTime(draw.clockOf(settings, seed), ms);
    return value - Math.floor(value / HALF_DAY) * HALF_DAY;
  };

  await t.test("the analog clock's hands point at its hour and its minute", () => {
    const next = numbers(5);
    const settings = clockOf();
    for (let one = 0; one < 60; one += 1) {
      const seed = 1 + next(1000000);
      const ms = next(30000);
      const picture = draw.drawClock(settings, seed, ms, canvas, new Uint8Array(3 * 60 * 60));
      const shown = time(settings, seed, ms);
      for (const [fraction, length] of [[(shown % 3600000) / 3600000, 0.8], [shown / HALF_DAY, 0.5]]) {
        const angle = 2 * Math.PI * fraction;
        const x = Math.round(29.5 + 29 * length * Math.sin(angle) - 0.5);
        const y = Math.round(29.5 - 29 * length * Math.cos(angle) - 0.5);
        const near = [-1, 0, 1].flatMap((dx) => [-1, 0, 1].map((dy) => pixelAt(picture, canvas, x + dx, y + dy)));
        assert.ok(near.includes(settings.hands), `seed ${seed} at ${ms} ms`);
      }
    }
  });

  await t.test("the digital clock shows the hour and the minute of the same time, the colon in each first half second", () => {
    const settings = clockOf({widget: "digital", face: 0x40c0ff, rim: 0xffd040});
    const table = fonttables.FONT_TABLES[1];
    const rows = table.ascent + table.descent;
    const next = numbers(9);
    for (let one = 0; one < 40; one += 1) {
      const seed = 1 + next(1000000);
      const ms = next(30000);
      const shown = time(settings, seed, ms);
      const words = `${Math.floor(shown / 3600000) % 12 || 12}:${String(Math.floor(shown / 60000) % 60).padStart(2, "0")}`;
      // The digits as the large font has them, centred, drawn here a second time.
      const expected = new Uint8Array(3 * 60 * 60);
      const glyphs = [...words].map((character) => textlayout.glyphIndex(table, character.charCodeAt(0)));
      const width = glyphs.reduce((sum, glyph) => sum + 2 * (table.widths[glyph] + 1), 0) - 2;
      let left = Math.floor((60 - width) / 2);
      const top = Math.floor((60 - 2 * rows) / 2);
      glyphs.forEach((glyph, place) => {
        const colon = words[place] === ":";
        for (let row = 0; row < rows && (!colon || ms % 1000 < 500); row += 1) {
          for (let column = 0; column < table.widths[glyph]; column += 1) {
            if ((table.rows[glyph * rows + row] & (0x80 >> column)) === 0) continue;
            for (const [across, down] of [[0, 0], [1, 0], [0, 1], [1, 1]]) {
              const at = 3 * ((59 - (top + 2 * row + down)) * 60 + left + 2 * column + across);
              expected.set(colon ? [0xff, 0xd0, 0x40] : [0x40, 0xc0, 0xff], at);
            }
          }
        }
        left += 2 * (table.widths[glyph] + 1);
      });
      assert.deepEqual(draw.drawClock(settings, seed, ms, canvas, new Uint8Array(3 * 60 * 60)), expected, `${words} for seed ${seed} at ${ms} ms`);
    }
  });

  await t.test("the melting watch's hands move, and it has its rim's colour, its face's and its hands'", () => {
    const settings = clockOf({widget: "melting"});
    const pictures = [0, 10000, 20000].map((ms) => draw.drawClock(settings, 5, ms, canvas, new Uint8Array(3 * 60 * 60)));
    assert.notDeepEqual(pictures[0], pictures[1]);
    const seen = new Set();
    for (let y = 0; y < 60; y += 1) for (let x = 0; x < 60; x += 1) seen.add(pixelAt(pictures[0], canvas, x, y));
    for (const colour of [settings.background, settings.face, settings.rim, settings.hands]) assert.ok(seen.has(colour), colour.toString(16));
  });

  await t.test("a canvas too small for a dial shows the background", () => {
    for (const widget of draw.WIDGETS.filter((name) => !draw.PICTURE_WIDGETS.includes(name))) {
      const picture = draw.drawClock(clockOf({widget, background: 0x010203}), 3, 0, {width: 2, height: 1}, new Uint8Array(6));
      assert.deepEqual([...picture], widget === "digital" ? [...picture] : [1, 2, 3, 1, 2, 3]);
    }
  });
});

test("a clock's container", async (t) => {
  await t.test("encodeWidget writes the 20 bytes and the loop of the seconds", () => {
    const clock = clockOf({widget: "melting", seconds: 45, speedMin: 1, speedMax: 3600});
    const data = odrgx.encodeWidget(clock);
    assert.equal(data.length, 40);
    const decoded = odrgx.decode(data);
    assert.equal(decoded.type, "widget");
    assert.equal(decoded.header.loopMs, 45000);
    assert.deepEqual(odrgx.widgetOf(decoded), clock);
    assert.deepEqual([...data.subarray(20)], [3, 0, 45, 0, 0xf4, 0xec, 0xd0, 0x20, 0x20, 0x20, 0xd4, 0xa0, 0x17, 0, 0, 0, 1, 0, 0x10, 0x0e]);
    assert.equal(reasonOf(() => odrgx.encodeWidget(clockOf({width: 200, height: 200}))), "canvas-too-large");
  });

  await t.test("the JSON source is read strictly and written canonically", () => {
    const read = odrgx.loadsSource(utf8(JSON.stringify(sourceOf({widget: "digital"}))));
    assert.equal(read.type, "widget");
    assert.deepEqual(read.widget, clockOf({widget: "digital"}));
    assert.deepEqual(odrgx.loadsSource(odrgx.dumpsWidget(read.widget)), read);
    const refused = (source) => reasonOf(() => odrgx.loadsSource(utf8(JSON.stringify(source))));
    const without = sourceOf();
    delete without.rim;
    assert.equal(refused(without), "missing-member");
    assert.equal(refused({...sourceOf(), hour: 3}), "unknown-member");
    assert.equal(refused({...sourceOf(), widget: "sundial"}), "out-of-range");
    assert.equal(refused({...sourceOf(), widget: 1}), "bad-type");
    assert.equal(refused({...sourceOf(), seconds: 0}), "out-of-range");
    assert.equal(refused({...sourceOf(), seconds: 3601}), "out-of-range");
    assert.equal(refused({...sourceOf(), face: 0x1000000}), "out-of-range");
    assert.equal(refused({...sourceOf(), speed_min: 0}), "out-of-range");
    assert.equal(refused({...sourceOf(), speed_min: 50, speed_max: 49}), "out-of-range");
    assert.equal(refused({...sourceOf(), speed_max: 3601}), "out-of-range");
  });

  await t.test("a clock is drawn with the seed it is given", () => {
    const decoded = odrgx.decode(odrgx.encodeWidget(clockOf()));
    assert.deepEqual(odrgx.pictureAt(decoded, 1000, 8), odrgx.pictureAt(decoded, 1000, 8));
    assert.notDeepEqual(odrgx.pictureAt(decoded, 1000, 8), odrgx.pictureAt(decoded, 1000, 9));
  });
});

test("the command line makes, reads and checks a clock", (t) => {
  const folder = temporary(t);
  const source = path.join(folder, "clock.json");
  fs.writeFileSync(source, JSON.stringify(sourceOf({widget: "melting"})));
  const out = path.join(folder, "clock.odrgx");
  assert.equal(runJs(["encode", source, out]).status, 0);
  const back = path.join(folder, "back.json");
  assert.equal(runJs(["decode", out, back]).status, 0);
  assert.deepEqual(JSON.parse(fs.readFileSync(back, "utf8")), sourceOf({widget: "melting"}));
  const checked = runJs(["check", out]);
  assert.equal(checked.status, 0, checked.err);
  assert.equal(checked.out, "format: odrgx\ntype: widget\ncanvas: 60x60\nloop_ms: 30000\nwidget: melting\nspeed: 60 to 600\nfile_bytes: 40\n");
  const refused = runJs(["encode", source, path.join(folder, "clock.odrg")]);
  assert.equal(refused.status, 2);
  assert.match(refused.err, /a text or a widget is written as \.odrgx/);
});

test("the vectors of clocks", async (t) => {
  const folder = path.join(ROOT, "tests", "vectors", "widgets");
  const builder = await import(pathToFileURL(path.join(folder, "build.mjs")).href);
  const read = (...parts) => new Uint8Array(fs.readFileSync(path.join(folder, ...parts)));

  await t.test("they are what their builder makes", () => {
    const made = builder.vectors();
    const onDisk = ["valid", "invalid"].flatMap((part) => fs.readdirSync(path.join(folder, part)).map((name) => `${part}/${name}`));
    assert.deepEqual(onDisk.sort(), [...made.keys()].sort(), "run node tests/vectors/widgets/build.mjs");
    for (const [name, data] of made) assert.deepEqual(read(name), data, name);
  });

  await t.test("a valid one decodes to its source", () => {
    const names = fs.readdirSync(path.join(folder, "valid")).filter((name) => name.endsWith(".odrgx"));
    assert.ok(names.length >= 4);
    for (const name of names) {
      const decoded = odrgx.decode(read("valid", name));
      assert.deepEqual(odrgx.loadsSource(read("valid", name.replace(/\.odrgx$/, ".json"))).widget, odrgx.widgetOf(decoded), name);
    }
  });

  await t.test("an invalid one is refused with the reason of its name, and with those of picture clocks they have every reason of a widget", () => {
    const names = fs.readdirSync(path.join(folder, "invalid"));
    for (const name of names) assert.equal(reasonOf(() => odrgx.decode(read("invalid", name))), name.split(".")[0], name);
    const text = fs.readFileSync(path.join(ROOT, "docs", "reasons.md"), "utf8");
    const section = text.split("\n## Widgets in ODRGX\n")[1].split("\n## ")[0];
    const listed = new Set([...section.matchAll(/^\| `([a-z0-9-]+)` \|/gm)].map((match) => match[1]));
    const ofWidgets = new Set(names.map((name) => name.split(".")[0]));
    const pictures = fs.readdirSync(path.join(ROOT, "tests", "vectors", "pictures", "invalid"));
    const ofPictures = new Set(pictures.map((name) => name.split(".")[0]).filter((reason) => listed.has(reason)));
    assert.ok([...ofWidgets].every((reason) => listed.has(reason)));
    assert.deepEqual(ofWidgets.union(ofPictures), listed);
  });
});
