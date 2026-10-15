import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import test from "node:test";

import {errors, jsonframes, odrg} from "../lib/index.js";
import {ROOT, animationFrom, asStored, forPython, generated, hex, isDigest, numbers, reference, runBoth, runJs, runPython, storedLength, temporary, unhex, utf8} from "./support.js";

const BENCH = "mapping/legs-2.json";
const TARGET = "mapping/legs-20.json";

function firstDifference(a, b) {
  const length = Math.min(a.length, b.length);
  for (let at = 0; at < length; at += 1) {
    if (a[at] !== b[at]) {
      return `byte ${at} is 0x${a[at].toString(16).padStart(2, "0")}, not 0x${b[at].toString(16).padStart(2, "0")}`;
    }
  }
  return a.length === b.length ? "no byte differs" : `the lengths are ${a.length} and ${b.length}`;
}

// Checks bytes against those of the Python tool: bytes, or its answer's hexadecimal digits,
// kept whole or as a digest.
function sameBytes(ours, theirs, label) {
  if (isDigest(theirs)) {
    assert.deepEqual(asStored(ours, theirs), theirs, label);
    return;
  }
  const bytes = typeof theirs === "string" ? unhex(theirs) : theirs;
  assert.ok(Buffer.from(ours).equals(Buffer.from(bytes)), `${label}: ${firstDifference(ours, bytes)}`);
}

test("the uncompressed files of the two command lines are identical", async (t) => {
  const folder = temporary(t);
  const sources = [
    ["Hello world, as tracked", "animations/hello.json"],
    ["DVD bounce, as tracked", "animations/dvd.json"],
    ["Hello world on the bench canvas", generated(folder, "hello_world", BENCH)],
    ["DVD bounce on the bench canvas", generated(folder, "dvd_bounce", BENCH)],
    ["a dense clip of 2 seconds on the bench canvas", generated(folder, "dense", BENCH, 2)],
    ["Hello world on 60 x 60", generated(folder, "hello_world", TARGET)],
    ["DVD bounce on 60 x 60", generated(folder, "dvd_bounce", TARGET)],
    ["a dense clip of 2 seconds on 60 x 60", generated(folder, "dense", TARGET, 2)],
  ];
  for (const [label, source] of sources) {
    await t.test(label, (inner) => {
      const ours = path.join(folder, "ours.odrg");
      const theirs = path.join(folder, "theirs.odrg");
      assert.deepEqual(runJs(["encode", source, ours, "--uncompressed"]), {status: 0, out: "", err: ""});
      assert.deepEqual(runPython(["encode", source, theirs, "--uncompressed"]), {status: 0, out: "", err: ""});
      const written = fs.readFileSync(ours);
      sameBytes(written, fs.readFileSync(theirs), source);
      assert.equal(written[5], 0, "the file is not compressed");
      inner.diagnostic(`${label}: ${written.length} bytes uncompressed`);
    });
  }

  await t.test("the tracked sources are what the generators write for the bench canvas", () => {
    assert.ok(fs.readFileSync(path.join(folder, "hello_world-legs-2.json")).equals(fs.readFileSync(path.join(ROOT, "animations", "hello.json"))));
    assert.ok(fs.readFileSync(path.join(folder, "dvd_bounce-legs-2.json")).equals(fs.readFileSync(path.join(ROOT, "animations", "dvd.json"))));
  });
});

test("the uncompressed files of 200 animations from seeds are identical", async (t) => {
  const animations = Array.from({length: 200}, (unused, i) => animationFrom(i + 1));
  const theirs = reference("encode", [], animations.map((animation) => forPython(animation)));
  const kinds = {palette: 0, rgb: 0, stored: 0, coded: 0, long: 0, merged: 0};
  const modes = new Set();

  await t.test("byte for byte", () => {
    animations.forEach((animation, i) => {
      const ours = odrg.encode(animation, {compressed: false});
      sameBytes(ours, theirs[i].uncompressed, `seed ${i + 1}, ${animation.width} x ${animation.height}`);
      const decoded = odrg.decode(ours);
      kinds[decoded.paletteSize > 0 ? "palette" : "rgb"] += 1;
      decoded.modes.forEach((mode) => modes.add(mode));
      kinds.stored += decoded.modes.includes(0x40) ? 1 : 0;
      kinds.coded += decoded.modes.some((mode) => mode !== 0x40) ? 1 : 0;
      kinds.long += animation.frames.some((frame) => frame.ms > 65535) ? 1 : 0;
      kinds.merged += jsonframes.merged(animation.frames).length < animation.frames.length ? 1 : 0;
    });
  });

  await t.test("the animations have canvases from 1 x 1 to 40 x 30, with and without a palette", () => {
    assert.ok(animations.some((animation) => animation.width === 1 && animation.height === 1));
    assert.ok(animations.some((animation) => animation.width === 40));
    assert.ok(animations.some((animation) => animation.height === 30));
    for (const [kind, count] of Object.entries(kinds)) {
      assert.ok(count >= 10, `${count} animations are ${kind}: ${JSON.stringify(kinds)}`);
    }
    assert.ok(modes.size >= 30, `${modes.size} different mode bytes`);
  });

  await t.test("the compressed file of each decodes to the records of the uncompressed one", () => {
    animations.forEach((animation, i) => {
      const plain = odrg.decode(odrg.encode(animation, {compressed: false}));
      const compressed = odrg.encode(animation);
      assert.equal(compressed[5], 1);
      const decoded = odrg.decode(compressed);
      assert.equal(decoded.compressed, true);
      assert.deepEqual(decoded.modes, plain.modes, `seed ${i + 1}`);
      assert.deepEqual(decoded.records.map((record) => [record.ms, hex(record.picture)]), plain.records.map((record) => [record.ms, hex(record.picture)]));
      const size = storedLength(theirs[i].compressed);
      assert.ok(20 * compressed.length <= 21 * size, `seed ${i + 1}: ${compressed.length} bytes against ${size}`);
    });
  });

  await t.test("what is decoded is the merged animation", () => {
    animations.slice(0, 60).forEach((animation, i) => {
      const decoded = odrg.decode(odrg.encode(animation, {compressed: false}));
      const back = jsonframes.dumps({width: decoded.width, height: decoded.height, frames: decoded.records});
      assert.ok(Buffer.from(back).equals(Buffer.from(jsonframes.dumps(animation))), `seed ${i + 1}`);
    });
  });
});

// An animation of one frame on a canvas one row high, with the colours given.
function row(colours, ms = 20) {
  return {width: colours.length, height: 1, frames: [{ms, picture: Uint8Array.from(colours.flat())}]};
}

test("the palette", async (t) => {
  const paletteOf = (file) => {
    const count = file[10] + 256 * file[11];
    return Array.from({length: count}, (unused, i) => [...file.subarray(16 + 3 * i, 19 + 3 * i)]);
  };
  const cases = [
    ["colours of equal hue and other saturation", row([[255, 0, 0], [255, 128, 128], [255, 64, 64], [128, 0, 0], [64, 32, 32], [255, 254, 254]])],
    ["colours without hue, with reds between them", row([[128, 128, 128], [0, 0, 0], [255, 255, 255], [255, 0, 0], [1, 1, 1], [2, 0, 0], [200, 200, 200]])],
    ["the six corners of the colour wheel, black and white", row([[0, 0, 255], [255, 0, 255], [0, 255, 0], [255, 255, 0], [255, 255, 255], [0, 255, 255], [255, 0, 0], [0, 0, 0]])],
    ["hues just below red, which come last", row([[255, 0, 1], [255, 1, 0], [255, 0, 0], [254, 0, 1], [3, 0, 1], [3, 1, 0], [200, 0, 199]])],
    ["two channels that are both the largest", row([[200, 200, 0], [200, 200, 100], [0, 200, 200], [200, 0, 200], [100, 100, 0], [100, 100, 99]])],
    ["equal hue and saturation, another largest channel", row([[2, 1, 0], [4, 2, 0], [200, 100, 0], [100, 50, 0], [254, 127, 0]])],
    ["hues that differ in the last digit of a fraction", row([[255, 127, 0], [254, 127, 0], [253, 126, 0], [255, 128, 0], [127, 63, 0], [129, 64, 0]])],
    ["one colour", row([[9, 8, 7], [9, 8, 7], [9, 8, 7]])],
  ];
  const from = numbers(77);
  for (let i = 0; i < 12; i += 1) {
    const colours = Array.from({length: from.pick([2, 5, 64, 255, 256])}, () => [...from.bytes(3)].map((channel) => (from.below(3) === 0 ? channel & 0xf0 : channel)));
    cases.push([`colours from seed ${i + 1}`, row(colours)]);
  }
  const theirs = reference("encode", [], cases.map(([, animation]) => forPython(animation)));

  for (let i = 0; i < cases.length; i += 1) {
    const [label, animation] = cases[i];
    await t.test(label, () => {
      const ours = odrg.encode(animation, {compressed: false});
      sameBytes(ours, theirs[i].uncompressed, label);
    });
  }

  await t.test("it has exactly the colours of the animation, ordered by hue, saturation and the largest channel", () => {
    const file = odrg.encode(cases[2][1], {compressed: false});
    assert.deepEqual(paletteOf(file), [[0, 0, 0], [255, 255, 255], [255, 0, 0], [255, 255, 0], [0, 255, 0], [0, 255, 255], [0, 0, 255], [255, 0, 255]]);
    assert.deepEqual(paletteOf(odrg.encode(cases[0][1], {compressed: false})), [[255, 254, 254], [255, 128, 128], [64, 32, 32], [255, 64, 64], [128, 0, 0], [255, 0, 0]]);
  });

  await t.test("256 colours get a palette and 257 get none", () => {
    const colours = Array.from({length: 257}, (unused, i) => [i & 0xff, i >> 8, 77]);
    const with256 = odrg.encode(row(colours.slice(0, 256)), {compressed: false});
    const with257 = odrg.encode(row(colours), {compressed: false});
    assert.equal(with256[10] + 256 * with256[11], 256);
    assert.equal(with257[10] + 256 * with257[11], 0);
    assert.equal(odrg.paletteFor(row(colours).frames), null);
    assert.equal(odrg.paletteFor(row(colours.slice(0, 256)).frames).length, 768);
    const both = reference("encode", [], [forPython(row(colours.slice(0, 256))), forPython(row(colours))]);
    sameBytes(with256, both[0].uncompressed, "256 colours");
    sameBytes(with257, both[1].uncompressed, "257 colours");
  });

  await t.test("the colours of every frame count, and the order does not depend on where a colour is met", () => {
    const one = {width: 2, height: 1, frames: [{ms: 1, picture: Uint8Array.of(1, 2, 3, 200, 0, 0)}, {ms: 1, picture: Uint8Array.of(0, 200, 0, 1, 2, 3)}]};
    const other = {width: 2, height: 1, frames: [{ms: 1, picture: Uint8Array.of(0, 200, 0, 1, 2, 3)}, {ms: 1, picture: Uint8Array.of(1, 2, 3, 200, 0, 0)}]};
    assert.deepEqual([...odrg.paletteFor(one.frames)], [...odrg.paletteFor(other.frames)]);
    assert.equal(odrg.paletteFor(one.frames).length, 9);
  });
});

test("the search for the smallest record", async (t) => {
  // Pairs of pixel buffers: what the buffer held, what it holds now, the width and the bytes
  // of a pixel.
  const pairs = [];
  const from = numbers(64);
  for (let i = 0; i < 40; i += 1) {
    const bpp = from.pick([1, 3]);
    const width = from.between(1, 12);
    const height = from.between(1, 6);
    const n = width * height * bpp;
    const style = from.pick(["noise", "small", "sparse", "zero", "equal", "ramp"]);
    const old = style === "zero" ? new Uint8Array(n) : from.bytes(n);
    const fresh = new Uint8Array(n);
    for (let at = 0; at < n; at += 1) {
      if (style === "noise") {
        fresh[at] = from.below(256);
      } else if (style === "small") {
        fresh[at] = old[at] + from.between(-2, 2);
      } else if (style === "sparse") {
        fresh[at] = from.below(9) === 0 ? from.below(256) : old[at];
      } else if (style === "equal" || style === "zero") {
        fresh[at] = old[at];
      } else {
        fresh[at] = 3 * at;
      }
    }
    pairs.push({label: `pair ${i + 1}: ${style}, ${width} x ${height}, ${bpp} bytes a pixel`, old, fresh, width, bpp});
  }
  const one = (old, fresh, width, bpp, label) => ({label, old: Uint8Array.from(old), fresh: Uint8Array.from(fresh), width, bpp});
  pairs.push(one([0], [0], 1, 1, "one byte that stays 0"));
  pairs.push(one([0], [1], 1, 1, "one byte that becomes 1"));
  pairs.push(one([0], [255], 1, 1, "one byte that becomes 255"));
  pairs.push(one([7], [7], 1, 1, "one byte that stays 7"));
  pairs.push(one([0, 0, 0], [0, 0, 0], 1, 3, "one black pixel that stays black"));
  pairs.push(one([0, 0, 0], [255, 255, 255], 1, 3, "one pixel that becomes white"));
  pairs.push(one(new Array(16).fill(0), new Array(16).fill(0), 16, 1, "sixteen bytes that stay 0"));
  pairs.push(one(new Array(16).fill(0), new Array(16).fill(1), 16, 1, "sixteen bytes that become 1"));
  pairs.push(one(new Array(16).fill(0), new Array(16).fill(128), 4, 1, "sixteen bytes that become 128"));
  pairs.push(one(new Array(18).fill(9), [...new Array(17).fill(9), 10], 2, 3, "a run to the last byte, which changes"));
  pairs.push(one(new Array(18).fill(9), [10, ...new Array(17).fill(9)], 2, 3, "a change in the first byte and a run to the end"));

  const theirs = reference("forms", [], pairs.map(({old, fresh, width, bpp}) => ({old: hex(old), new: hex(fresh), width, bpp})));
  let ties = 0;
  let storedCount = 0;

  await t.test("each of the 64 coded forms is the record the Python tool writes", () => {
    pairs.forEach(({label, old, fresh, width, bpp}, i) => {
      let form = 0;
      for (let predictor = 0; predictor < 4; predictor += 1) {
        const sizes = odrg.dataSizes(odrg.codes(old, fresh, width, bpp, predictor));
        for (const run of [false, true]) {
          for (let k = 0; k < 8; k += 1) {
            const expected = theirs[i].records[form];
            const what = `${label}, predictor ${predictor}, ${run ? "run" : "plain"} mode, k ${k}`;
            if (expected === null) {
              assert.ok(sizes[(run ? 8 : 0) + k] > fresh.length, what);
              assert.throws(() => odrg.codedRecord(old, fresh, width, bpp, 20, predictor, run, k), RangeError, what);
            } else {
              const record = odrg.codedRecord(old, fresh, width, bpp, 20, predictor, run, k);
              assert.deepEqual(asStored(record, expected), expected, what);
              assert.equal(sizes[(run ? 8 : 0) + k], record.length - 5, what);
            }
            form += 1;
          }
        }
      }
    });
  });

  await t.test("the record that is chosen is the one the Python tool chooses", () => {
    pairs.forEach(({label, old, fresh, width, bpp}, i) => {
      const best = odrg.bestRecord(old, fresh, width, bpp, 20);
      assert.deepEqual(asStored(best, theirs[i].best), theirs[i].best, label);
      const sizes = theirs[i].records.filter((record) => record !== null).map(storedLength);
      const smallest = Math.min(...sizes);
      ties += sizes.filter((size) => size === smallest).length > 1 ? 1 : 0;
      storedCount += best[4] === 0x40 ? 1 : 0;
    });
    assert.ok(ties >= 20, `${ties} pairs have several forms of the smallest size`);
    assert.ok(storedCount >= 5, `${storedCount} pairs are stored`);
  });

  await t.test("among forms of the same size the lowest predictor wins, then plain mode, then the lowest k", () => {
    const many = new Uint8Array(64);
    assert.equal(odrg.bestRecord(many, many, 64, 1, 20)[4], 0x08, "run mode with k of 0: two bytes, where plain mode needs eight");
    const zeros = new Uint8Array(16);
    assert.equal(odrg.bestRecord(zeros, zeros, 16, 1, 20)[4], 0x00, "plain mode with k of 0: two bytes, as run mode has");
    const ones = new Uint8Array(16).fill(1);
    assert.equal(odrg.bestRecord(zeros, ones, 16, 1, 20)[4], 0x18, "predictor 1 in run mode: two bytes, as predictor 2 has");
    const eight = new Uint8Array(8);
    assert.equal(odrg.bestRecord(eight, eight, 8, 1, 20)[4], 0x00, "plain mode with k of 0: one byte, as run mode has");
    const single = odrg.bestRecord(Uint8Array.of(0), Uint8Array.of(0), 1, 1, 20);
    assert.deepEqual([...single], [20, 0, 2, 0, 0x40, 0], "a buffer of one byte is stored: no coded form has less than a byte");
  });

  await t.test("a record is stored when no coded form has fewer bytes than the buffer", () => {
    const from2 = numbers(5);
    const old = new Uint8Array(300);
    const fresh = from2.bytes(300);
    const record = odrg.bestRecord(old, fresh, 100, 3, 77);
    assert.deepEqual([...record.subarray(0, 5)], [77, 0, 301 & 0xff, 301 >> 8, 0x40]);
    assert.equal(hex(record.subarray(5)), hex(fresh));
    assert.equal(hex(odrg.storedRecord(fresh, 77)), hex(record));
  });

  await t.test("a predictor that does not exist is a mistake of the program", () => {
    assert.throws(() => odrg.codes(new Uint8Array(3), new Uint8Array(3), 1, 3, 4), RangeError);
  });
});

test("a frame longer than 65,535 ms becomes several records with the same picture", async (t) => {
  const picture = Uint8Array.of(1, 2, 3, 4, 5, 6);
  const other = Uint8Array.of(9, 9, 9, 4, 5, 6);
  const times = [65535, 65536, 131070, 131071, 200000, 1000000];
  const animations = times.map((ms) => ({width: 2, height: 1, frames: [{ms: 5, picture: other}, {ms, picture}, {ms: 7, picture: other}]}));
  animations.push({width: 2, height: 1, frames: [{ms: 40000, picture}, {ms: 40000, picture}, {ms: 1, picture: other}]});
  const theirs = reference("encode", [], animations.map((animation) => forPython(animation)));

  for (let i = 0; i < animations.length; i += 1) {
    await t.test(i < times.length ? `${times[i]} ms` : "two frames of 40,000 ms with the same picture", () => {
      const ours = odrg.encode(animations[i], {compressed: false});
      sameBytes(ours, theirs[i].uncompressed, "the file");
      const decoded = odrg.decode(ours);
      const durations = decoded.records.map((record) => record.ms);
      const ms = i < times.length ? times[i] : 80000;
      const middle = i < times.length ? durations.slice(1, -1) : durations.slice(0, -1);
      assert.equal(middle.reduce((sum, duration) => sum + duration, 0), ms);
      assert.ok(middle.slice(0, -1).every((duration) => duration === 65535));
      assert.equal(middle.length, Math.ceil(ms / 65535));
    });
  }
});

test("sources that cannot be written as ODRG", async (t) => {
  const folder = temporary(t);
  const source = (name, width, height, ms, colours) => {
    const pixels = Array.from({length: width * height}, (unused, i) => i % colours);
    const file = path.join(folder, name);
    fs.writeFileSync(file, `{"version": 1, "width": ${width}, "height": ${height}, "frames": [{"ms": ${ms}, "pixels": [${pixels.join(", ")}]}]}`);
    return file;
  };
  const out = path.join(folder, "out.odrg");
  const cases = [
    ["a picture of 65,535 bytes with a palette", source("a.json", 65535, 1, 20, 3), "canvas-too-large"],
    ["a picture of 65,535 bytes without a palette", source("b.json", 21845, 1, 20, 300), "canvas-too-large"],
    ["a picture of 65,535 bytes in five rows without a palette", source("c.json", 4369, 5, 20, 257), "canvas-too-large"],
    ["a frame that needs one record too many", source("d.json", 1, 1, "281470681677826", 1), "too-many-frames"],
    ["a frame of 10 to the power 29 ms", source("e.json", 1, 1, `1${"0".repeat(29)}`, 1), "too-many-frames"],
    ["a frame of more than 30 digits of ms", source("f.json", 1, 1, "9".repeat(40), 1), "too-many-frames"],
    ["a canvas too large and too many records", source("g.json", 65535, 1, "281470681677826", 2), "canvas-too-large"],
  ];
  for (const [label, file, reason] of cases) {
    await t.test(label, () => {
      for (const flags of [[], ["--uncompressed"]]) {
        const {js, python} = runBoth(["encode", file, out, ...flags]);
        assert.equal(python.status, 1);
        assert.equal(python.err.split(": ")[1], reason);
        assert.deepEqual(js, python);
        assert.equal(fs.existsSync(out), false);
        assert.equal(fs.existsSync(`${out}.part`), false);
      }
    });
  }

  await t.test("the largest picture with a palette, and the largest without, are written", () => {
    const withPalette = source("h.json", 65534, 1, 20, 2);
    const without = source("i.json", 21844, 1, 20, 400);
    for (const [file, n] of [[withPalette, 65534], [without, 65532]]) {
      const ours = path.join(folder, "ours.odrg");
      const theirs = path.join(folder, "theirs.odrg");
      assert.deepEqual(runJs(["encode", file, ours, "--uncompressed"]), {status: 0, out: "", err: ""});
      assert.deepEqual(runPython(["encode", file, theirs, "--uncompressed"]), {status: 0, out: "", err: ""});
      sameBytes(fs.readFileSync(ours), fs.readFileSync(theirs), `N of ${n}`);
      fs.rmSync(ours);
      fs.rmSync(theirs);
    }
  });

  await t.test("the library gives the same rejections for an animation it is handed", () => {
    const picture = new Uint8Array(3);
    assert.throws(() => odrg.encode({width: 1, height: 1, frames: [{ms: 65535 * 4294967295 + 1, picture}]}), {
      reason: "too-many-frames",
      detail: "4294967296 frame records would be needed, above 4294967295",
    });
    assert.throws(() => odrg.encode({width: 1, height: 1, frames: [{ms: 10n ** 30n, picture}]}), (error) => {
      assert.ok(error instanceof errors.Rejection);
      assert.equal(error.detail, `${(10n ** 30n + 65534n) / 65535n} frame records would be needed, above 4294967295`);
      return true;
    });
    assert.throws(() => odrg.encode({width: 65535, height: 1, frames: [{ms: 1, picture: new Uint8Array(3 * 65535)}]}), {
      reason: "canvas-too-large",
      detail: "a picture of 65535 x 1 would be 65535 bytes, above 65534",
    });
  });
});

test("encode on the command line", async (t) => {
  const folder = temporary(t);
  const good = path.join(folder, "good.json");
  fs.writeFileSync(good, jsonframes.dumps(animationFrom(3)));
  fs.writeFileSync(path.join(folder, "bad.json"), utf8('{"version": 1, "width": 1}'));
  fs.writeFileSync(path.join(folder, "not.json"), utf8("{"));
  const inFolder = {cwd: folder};

  const lines = [
    ["encode"],
    ["encode", "good.json"],
    ["encode", "good.json", "a.odrg", "b.odrg"],
    ["encode", "good.json", "a.odrg", "--compressed"],
    ["encode", "good.json", "a.odrg", "--uncompressed=yes"],
    ["encode", "--help"],
    ["encode", "good.json", "a.odrg"],
    ["encode", "good.json", "b.odrg", "--uncompressed"],
    ["encode", "--uncompressed", "good.json", "c.odrg"],
    ["encode", "good.json", "--uncompressed", "d.odrg"],
    ["encode", "good.json", "e.odrg", "--uncompressed", "--uncompressed"],
    ["encode", "--", "good.json", "f.odrg"],
    ["encode", "missing.json", "g.odrg"],
    ["encode", "bad.json", "g.odrg"],
    ["encode", "not.json", "g.odrg"],
    ["encode", "good.json", "none/g.odrg"],
    ["encode", ".", "g.odrg"],
  ];
  for (const argv of lines) {
    await t.test(`odrig ${argv.join(" ")}`, () => {
      const {js, python} = runBoth(argv, inFolder);
      assert.equal(js.status, python.status, `${js.err} / ${python.err}`);
      if (python.status === 1 && !/: line \d+, column \d+: /.test(python.err)) {
        assert.equal(js.err, python.err);
      }
      if (python.status === 1) {
        assert.equal(js.err.split(": ")[1], python.err.split(": ")[1]);
        assert.equal(js.out, "");
      }
      if (python.status === 2) {
        assert.match(js.err, /^usage: node converter\/odrig\.js encode/);
      }
    });
  }

  await t.test("the files that were written, and nothing else", () => {
    const written = fs.readdirSync(folder).sort();
    assert.deepEqual(written, ["a.odrg", "b.odrg", "bad.json", "c.odrg", "d.odrg", "e.odrg", "f.odrg", "good.json", "not.json"]);
    const read = (name) => fs.readFileSync(path.join(folder, name));
    assert.equal(read("a.odrg")[5], 1);
    assert.ok(read("f.odrg").equals(read("a.odrg")));
    for (const name of ["b.odrg", "c.odrg", "d.odrg", "e.odrg"]) {
      assert.equal(read(name)[5], 0, name);
      assert.ok(read(name).equals(read("b.odrg")), name);
    }
  });

  await t.test("the same source and the same options give the same file on every run", () => {
    const first = path.join(folder, "first.odrg");
    const second = path.join(folder, "second.odrg");
    for (const flags of [[], ["--uncompressed"]]) {
      assert.equal(runJs(["encode", "animations/hello.json", first, ...flags]).status, 0);
      assert.equal(runJs(["encode", "animations/hello.json", second, ...flags]).status, 0);
      assert.ok(fs.readFileSync(first).equals(fs.readFileSync(second)));
    }
    fs.rmSync(first);
    fs.rmSync(second);
  });

  await t.test("an output that was there stays as it was when the source is rejected", () => {
    const out = path.join(folder, "kept.odrg");
    fs.writeFileSync(out, "before");
    assert.equal(runJs(["encode", "bad.json", out], inFolder).status, 1);
    assert.equal(fs.readFileSync(out, "utf8"), "before");
    assert.equal(fs.existsSync(`${out}.part`), false);
    fs.rmSync(out);
  });
});
