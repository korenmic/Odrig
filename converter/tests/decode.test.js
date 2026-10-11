import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import test from "node:test";

import {errors, jsonframes, odrg} from "../lib/index.js";
import {ROOT, hex, libraryCheck, libraryText, numbers, pythonChecks, runBoth, runJs, runPython, sameVerdict, temporary} from "./support.js";

const VALID = path.join(ROOT, "tests", "vectors", "valid");
const INVALID = path.join(ROOT, "tests", "vectors", "invalid");

const validNames = fs.readdirSync(VALID).filter((name) => name.endsWith(".odrg")).sort();
const invalidNames = fs.readdirSync(INVALID).filter((name) => name.endsWith(".odrg")).sort();

function bytesOf(folder, name) {
  return new Uint8Array(fs.readFileSync(path.join(folder, name)));
}

function sameLines(js, python, label) {
  assert.equal(js.status, python.status, `${label}: ${js.err} / ${python.err}`);
  assert.equal(js.out, python.out, label);
  if (libraryText(python.err)) {
    assert.equal(js.err.split(": ")[1], python.err.split(": ")[1], label);
    assert.match(js.err, /^error: [a-z-]+: \S+: .+\n$/, label);
  } else {
    assert.equal(js.err, python.err, label);
  }
}

test("the vectors are all there", () => {
  assert.equal(validNames.length, 22);
  assert.equal(invalidNames.length, 34);
});

test("every valid vector is decoded to the frames of its JSON file, record by record", async (t) => {
  for (const name of validNames) {
    await t.test(name, () => {
      const decoded = odrg.decode(bytesOf(VALID, name));
      const expected = jsonframes.loads(bytesOf(VALID, name.replace(/\.odrg$/, ".json")));
      assert.equal(decoded.width, expected.width);
      assert.equal(decoded.height, expected.height);
      assert.equal(decoded.records.length, expected.frames.length);
      assert.equal(decoded.modes.length, decoded.records.length);
      decoded.records.forEach((record, i) => {
        assert.equal(record.ms, expected.frames[i].ms, `the duration of record ${i + 1}`);
        assert.equal(hex(record.picture), hex(expected.frames[i].picture), `the picture after record ${i + 1}`);
      });
      const file = bytesOf(VALID, name);
      assert.equal(decoded.paletteSize, file[10] + 256 * file[11]);
      assert.equal(decoded.compressed, file[5] === 1);
    });
  }

  await t.test("the mode bytes are those of the records", () => {
    const decoded = odrg.decode(bytesOf(VALID, "stored.rgb.odrg"));
    assert.ok(decoded.modes.includes(0x40));
    const modes = new Set([...odrg.decode(bytesOf(VALID, "rgb-modes.odrg")).modes, ...odrg.decode(bytesOf(VALID, "pal-modes.odrg")).modes]);
    assert.ok(modes.size >= 32, `${modes.size} different mode bytes`);
  });
});

test("every invalid vector is rejected with the reason its name gives", async (t) => {
  const theirs = pythonChecks("odrg", invalidNames.map((name) => bytesOf(INVALID, name)));
  for (let i = 0; i < invalidNames.length; i += 1) {
    const name = invalidNames[i];
    await t.test(name, () => {
      const reason = name.split(".")[0];
      assert.throws(() => odrg.decode(bytesOf(INVALID, name)), (error) => {
        assert.ok(error instanceof errors.Rejection, String(error));
        assert.equal(error.reason, reason);
        return true;
      });
      assert.equal(theirs[i].err.split(": ")[1], reason);
      sameVerdict(assert, libraryCheck("odrg", bytesOf(INVALID, name)), theirs[i], name);
    });
  }

  await t.test("the reasons of an ODRG file are all among them", () => {
    const reasons = new Set(invalidNames.map((name) => name.split(".")[0]));
    assert.deepEqual([...reasons].sort(), [
      "bad-code", "bad-deflate", "bad-length", "bad-magic", "bad-palette-index", "bad-palette-size", "bad-stored-length",
      "bad-version", "canvas-too-large", "no-frames", "out-of-bits", "reserved-bits", "run-past-end", "too-much-padding",
      "trailing-bytes", "truncated", "zero-duration", "zero-size",
    ]);
  });
});

test("check on the command line prints what the Python tool prints", async (t) => {
  for (const name of validNames) {
    await t.test(name, () => {
      const {js, python} = runBoth(["check", `tests/vectors/valid/${name}`]);
      assert.equal(python.status, 0);
      assert.match(python.out, /^format: odrg\ncanvas: \d+x\d+\nframes: \d+\nduration_ms: \d+\ncolours: \d+\nfile_bytes: \d+\npalette: \d+\ncompressed: (yes|no)\n$/);
      assert.deepEqual(js, python);
    });
  }
  for (const name of validNames) {
    const source = name.replace(/\.odrg$/, ".json");
    await t.test(source, () => {
      const {js, python} = runBoth(["check", `tests/vectors/valid/${source}`]);
      assert.equal(python.status, 0);
      assert.match(python.out, /^format: json-frames\ncanvas: \d+x\d+\nframes: \d+\nduration_ms: \d+\ncolours: \d+\nfile_bytes: \d+\n$/);
      assert.deepEqual(js, python);
    });
  }
  for (const name of invalidNames) {
    await t.test(name, () => {
      const {js, python} = runBoth(["check", `tests/vectors/invalid/${name}`]);
      assert.equal(python.status, 1);
      assert.equal(python.err.split(": ")[1], name.split(".")[0]);
      sameLines(js, python, name);
    });
  }
});

test("decode on the command line writes what the Python tool writes", async (t) => {
  await t.test("for every valid vector, the same JSON frames file byte for byte", () => {
    const folder = temporary(t);
    for (const name of validNames) {
      const ours = path.join(folder, `${name}.js.json`);
      const theirs = path.join(folder, `${name}.py.json`);
      const js = runJs(["decode", `tests/vectors/valid/${name}`, ours]);
      const python = runPython(["decode", `tests/vectors/valid/${name}`, theirs]);
      assert.deepEqual(js, {status: 0, out: "", err: ""}, name);
      assert.deepEqual(python, {status: 0, out: "", err: ""}, name);
      assert.ok(fs.readFileSync(ours).equals(fs.readFileSync(theirs)), name);
    }
    const left = fs.readdirSync(folder).filter((name) => name.endsWith(".part"));
    assert.deepEqual(left, []);
  });

  await t.test("records with the same picture are written as one frame", () => {
    const folder = temporary(t);
    const out = path.join(folder, "durations.json");
    assert.equal(runBoth(["decode", "tests/vectors/valid/durations.odrg", out]).js.status, 0);
    const decoded = odrg.decode(bytesOf(VALID, "durations.odrg"));
    const written = jsonframes.loads(new Uint8Array(fs.readFileSync(out)));
    assert.ok(written.frames.length < decoded.records.length);
    assert.equal(written.frames.length, jsonframes.merged(decoded.records).length);
    assert.equal(hex(fs.readFileSync(out)), hex(jsonframes.dumps({width: decoded.width, height: decoded.height, frames: decoded.records})));
  });

  await t.test("for every invalid vector, the same error line, status 1 and no output", () => {
    const folder = temporary(t);
    for (const name of invalidNames) {
      const out = path.join(folder, "out.json");
      const {js, python} = runBoth(["decode", `tests/vectors/invalid/${name}`, out]);
      assert.equal(python.status, 1, name);
      sameLines(js, python, name);
      assert.deepEqual(fs.readdirSync(folder), [], name);
    }
  });

  await t.test("an output that was there stays as it was when the input is rejected", () => {
    const folder = temporary(t);
    const out = path.join(folder, "out.json");
    fs.writeFileSync(out, "before");
    const {js, python} = runBoth(["decode", "tests/vectors/invalid/bad-magic.odrg", out]);
    assert.deepEqual(js, python);
    assert.equal(js.status, 1);
    assert.equal(fs.readFileSync(out, "utf8"), "before");
    assert.deepEqual(fs.readdirSync(folder), ["out.json"]);
  });

  await t.test("a missing input, and an output that cannot be written", () => {
    const folder = temporary(t);
    const missing = runBoth(["decode", path.join(folder, "none.odrg"), path.join(folder, "out.json")]);
    assert.deepEqual(missing.js, missing.python);
    assert.equal(missing.js.err, `error: not-found: ${path.join(folder, "none.odrg")}: No such file or directory\n`);
    const unwritable = runBoth(["decode", "tests/vectors/valid/pal-1.odrg", path.join(folder, "none", "out.json")]);
    assert.deepEqual(unwritable.js, unwritable.python);
    assert.equal(unwritable.js.status, 1);
    assert.deepEqual(fs.readdirSync(folder), []);
  });
});

// Copies of a file with one change each: cut at a length, a byte added, a byte changed.
function copies(name, file, from, limit) {
  const made = [];
  const lengths = file.length <= limit ? Array.from({length: file.length}, (unused, i) => i) : Array.from({length: limit}, () => from.below(file.length));
  for (const length of lengths) {
    made.push({label: `${name} cut to ${length} bytes`, bytes: file.subarray(0, length)});
  }
  for (const extra of [0x00, 0xff]) {
    const longer = new Uint8Array(file.length + 1);
    longer.set(file);
    longer[file.length] = extra;
    made.push({label: `${name} with the byte ${extra} added`, bytes: longer});
  }
  const places = file.length <= limit ? Array.from({length: file.length}, (unused, i) => i) : Array.from({length: limit}, () => from.below(file.length));
  for (const at of places) {
    for (const change of [1 << (at % 8), from.between(1, 255)]) {
      const damaged = file.slice();
      damaged[at] ^= change;
      made.push({label: `${name} with byte ${at} changed by ${change}`, bytes: damaged});
    }
  }
  return made;
}

test("damaged and cut copies of valid files get the verdict of the reference", async (t) => {
  const from = numbers(1606);
  const cases = [];
  for (const name of validNames) {
    cases.push(...copies(name, bytesOf(VALID, name), from, 420));
  }
  const theirs = pythonChecks("odrg", cases.map((entry) => entry.bytes));
  const reasons = new Map();

  await t.test(`${cases.length} copies`, () => {
    assert.ok(cases.length > 12000, `${cases.length} copies`);
    cases.forEach((entry, i) => {
      sameVerdict(assert, libraryCheck("odrg", entry.bytes), theirs[i], entry.label);
      const reason = theirs[i].status === 0 ? "accepted" : theirs[i].err.split(": ")[1];
      reasons.set(reason, (reasons.get(reason) ?? 0) + 1);
    });
  });

  await t.test("the copies meet the reasons of an ODRG file but no-frames, and some are accepted", () => {
    for (const reason of [
      "accepted", "bad-code", "bad-deflate", "bad-length", "bad-magic", "bad-palette-index", "bad-palette-size", "bad-stored-length",
      "bad-version", "canvas-too-large", "out-of-bits", "reserved-bits", "run-past-end", "too-much-padding",
      "trailing-bytes", "truncated", "zero-duration", "zero-size",
    ]) {
      assert.ok(reasons.has(reason), `no copy is ${reason}: ${JSON.stringify([...reasons])}`);
    }
  });
});

test("a file with more than one defect gets the reason of the first check", async (t) => {
  const good = bytesOf(VALID, "one-pixel.pal.odrg");
  const with_ = (changes) => {
    const file = good.slice();
    for (const [at, value] of changes) {
      file[at] = value;
    }
    return file;
  };
  const cases = [
    ["a wrong magic and a wrong version", with_([[0, 0x58], [4, 2]]), "bad-magic"],
    ["a wrong version and a reserved flag", with_([[4, 2], [5, 0x82]]), "bad-version"],
    ["a reserved flag and a width of 0", with_([[5, 0x02], [6, 0], [7, 0]]), "reserved-bits"],
    ["a width of 0 and a palette of 257", with_([[6, 0], [7, 0], [10, 1], [11, 1]]), "zero-size"],
    ["a palette of 257 and a canvas too large", with_([[10, 1], [11, 1], [6, 0xff], [7, 0xff], [8, 0xff], [9, 0xff]]), "bad-palette-size"],
    ["a canvas too large and no frames", with_([[6, 0xff], [7, 0xff], [8, 0xff], [9, 0xff], [12, 0], [13, 0], [14, 0], [15, 0]]), "canvas-too-large"],
    ["no frames in a file cut after its header", with_([[12, 0], [13, 0], [14, 0], [15, 0]]).subarray(0, 16), "no-frames"],
    ["a header alone", good.subarray(0, 16), "truncated"],
    ["fifteen bytes that are not ODRG", new Uint8Array(15), "truncated"],
    ["sixteen bytes that are not ODRG", new Uint8Array(16), "bad-magic"],
    ["the largest frame count", with_([[12, 0xff], [13, 0xff], [14, 0xff], [15, 0xff]]), "truncated"],
  ];
  const theirs = pythonChecks("odrg", cases.map(([, bytes]) => bytes));
  for (let i = 0; i < cases.length; i += 1) {
    const [label, bytes, reason] = cases[i];
    await t.test(label, () => {
      assert.equal(theirs[i].err.split(": ")[1], reason);
      assert.deepEqual(libraryCheck("odrg", bytes), theirs[i]);
    });
  }
});

test("codes are read whole before they are judged, and padding is not looked at", async (t) => {
  // A file of 16 x 1 with a palette of two colours and one coded record with the data
  // given. The modes: 0x30 is plain with k of 0, 0x37 plain with k of 7, 0x38 run mode with
  // k of 0, each with the predictor that takes the residuals as the pixels.
  const file = (mode, data) => Uint8Array.of(
    0x4f, 0x44, 0x52, 0x47, 1, 0, 16, 0, 1, 0, 2, 0, 1, 0, 0, 0,
    0, 0, 0, 255, 255, 255,
    20, 0, data.length + 1, 0, mode, ...data,
  );
  const cases = [
    ["fifteen codes of 0 and a code of 2, the padding all zero", file(0x30, [0x00, 0x01, 0b10000000])],
    ["the same with every padding bit set", file(0x30, [0x00, 0x01, 0b10111111])],
    ["sixteen Rice codes of eight bits, of which the last is missing", file(0x37, new Array(15).fill(0))],
    ["a Rice code that ends without its zero bit", file(0x30, [0b01111111])],
    ["a Rice escape without its value", file(0x30, [0b11111111])],
    ["a Rice code of 256 in plain mode", file(0x37, [0b11000000, 0b00000000])],
    ["a Rice escape of 255 in run mode, which is code 256", file(0x38, [0b11111111, 0b11111111, 0b10000000])],
    ["a Gamma code of 40 zero bits and no one bit", file(0x38, [0, 0, 0, 0, 0])],
    ["a Gamma code of 39 zero bits, a one bit, and too few bits after it", file(0x38, [0, 0, 0, 0, 1, 0, 0, 0, 0])],
    ["a Gamma code of 39 zero bits and its 40 bits", file(0x38, [0, 0, 0, 0, 1, 0x23, 0x45, 0x67, 0x89, 0xab])],
    ["a Gamma code of 60 bits", file(0x38, [0, 0, 0, 0, 0, 0, 0, 0b00010110, 0xde, 0xad, 0xbe, 0xef, 0x01, 0x23, 0x45])],
    ["a run of 17 zero codes where 16 are left", file(0x38, [0b00001001, 0b00000000])],
    ["a run to the end and seven bits of padding", file(0x38, [0b00001000, 0b10000000])],
    ["a run to the end and fifteen bits of padding", file(0x38, [0b00001000, 0b10000000, 0])],
    ["a palette index of 2", file(0x30, [0b11110000, 0, 0])],
  ];
  const theirs = pythonChecks("odrg", cases.map(([, bytes]) => bytes));
  for (let i = 0; i < cases.length; i += 1) {
    const [label, bytes] = cases[i];
    await t.test(label, () => {
      assert.deepEqual(libraryCheck("odrg", bytes), theirs[i]);
    });
  }

  await t.test("the cases meet the five reasons of the bits of a record", () => {
    const reasons = new Set(theirs.map((result) => (result.status === 0 ? "accepted" : result.err.split(": ")[1])));
    for (const reason of ["accepted", "out-of-bits", "bad-code", "run-past-end", "too-much-padding", "bad-palette-index"]) {
      assert.ok(reasons.has(reason), `${reason}: ${[...reasons].join(" ")}`);
    }
  });
});
