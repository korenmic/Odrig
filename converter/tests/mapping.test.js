import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import test from "node:test";

import {errors, mapping} from "../lib/index.js";
import {ROOT, hex, reference, runBoth, runJsHere, runPythonMany, temporary, utf8} from "./support.js";

// What the library says of a mapping file, in the form reference.py gives for the Python
// reader.
function ours(bytes) {
  try {
    const canvas = mapping.loads(bytes);
    return {
      kind: canvas.kind,
      width: canvas.width,
      height: canvas.height,
      strip_length: mapping.stripLength(canvas),
      legs: canvas.legs.map((leg) => ({
        leg: leg.leg,
        pin: leg.pin,
        first_led: leg.firstLed,
        strips: leg.strips,
        led_count: mapping.ledCount(canvas, leg),
      })),
    };
  } catch (error) {
    if (!(error instanceof errors.Rejection)) {
      throw error;
    }
    return {reason: error.reason, detail: error.detail};
  }
}

// Compares the two readers on one file: the same mapping, or the same rejection. Where
// the Python tool's detail holds the words of its JSON module, the part before them.
function same(mine, theirs, label) {
  if (theirs.reason !== undefined && /^bad-json: line \d+, column \d+: /.test(theirs.detail)) {
    assert.equal(mine.reason, theirs.reason, label);
    assert.match(mine.detail, /^bad-json: line \d+, column \d+: /, label);
    return;
  }
  assert.deepEqual(mine, theirs, label);
}

const ROW_NAMES = {length: "width", other: "height", strips: "rows", otherStrips: "columns", ends: ["left", "right"], otherEnds: ["bottom", "top"]};
const COLUMN_NAMES = {length: "height", other: "width", strips: "columns", otherStrips: "rows", ends: ["bottom", "top"], otherEnds: ["left", "right"]};

// A file of two legs of two strips of four LEDs, of one kind.
function base(names) {
  return {
    version: 1,
    [names.length]: 4,
    legs: [
      {leg: 1, pin: 5, first_led: names.ends[0], [names.strips]: [1, 2]},
      {leg: 2, pin: 6, first_led: names.ends[1], [names.strips]: [4, 3]},
    ],
  };
}

function without(object, name) {
  const copy = {...object};
  delete copy[name];
  return copy;
}

// Files of one kind that break each rule of docs/mapping.md once, in the order of the
// checks, and files that mix the two kinds. A file is given as a value or as its text.
function broken(names) {
  const file = base(names);
  const leg = file.legs[0];
  const withLeg = (changed, second = file.legs[1]) => ({...file, legs: [changed, second]});
  const text = JSON.stringify(file);
  const strips = names.strips;
  return [
    ["a text that is not JSON", "{"],
    ["a top level that is an array", []],
    ["a top level that is null", null],
    ["no version", without(file, "version")],
    ["a version that is a string", {...file, version: "1"}],
    ["a version with a fraction", text.replace('"version":1', '"version":1.0')],
    ["version 2", {...file, version: 2}],
    ["version 0", {...file, version: 0}],
    ["version 2 in a file that is nothing else", {version: 2}],
    ["both width and height", {...file, [names.other]: 2}],
    ["both width and height, and a member that is unknown", {...file, [names.other]: 2, name: "x"}],
    ["neither width nor height", without(file, names.length)],
    ["neither width nor height, and no legs", {version: 1}],
    ["the length under the name of the other kind", {...without(file, names.length), [names.other]: 4}],
    ["no legs", without(file, "legs")],
    ["an unknown member", {...file, name: "bench"}],
    [`${strips} at the top level`, {...file, [strips]: [1, 2]}],
    ["a member named twice", text.replace('"version":1', '"version":1,"version":1')],
    ["a length of 0", {...file, [names.length]: 0}],
    ["a negative length", {...file, [names.length]: -4}],
    ["a length of 65,536", {...file, [names.length]: 65536}],
    ["a length of forty digits", text.replace(`"${names.length}":4`, `"${names.length}":${"7".repeat(40)}`)],
    ["a length that is a string", {...file, [names.length]: "4"}],
    ["a length with a fraction", text.replace(`"${names.length}":4`, `"${names.length}":4.0`)],
    ["a length that is true", {...file, [names.length]: true}],
    ["legs that is an object", {...file, legs: {}}],
    ["legs that is a string", {...file, legs: "1"}],
    ["legs that is empty", {...file, legs: []}],
    ["an entry of legs that is a number", {...file, legs: [5]}],
    ["a second entry of legs that is null", {...file, legs: [leg, null]}],
    ["a leg without its number", withLeg(without(leg, "leg"))],
    ["a leg without its pin", withLeg(without(leg, "pin"))],
    ["a leg without first_led", withLeg(without(leg, "first_led"))],
    [`a leg without ${strips}`, withLeg(without(leg, strips))],
    ["a leg with an unknown member", withLeg({...leg, colour: "red"})],
    [`a leg with ${names.otherStrips} in place of ${strips}`, withLeg({...without(leg, strips), [names.otherStrips]: [1, 2]})],
    [`a leg with ${strips} and ${names.otherStrips}`, withLeg({...leg, [names.otherStrips]: [1, 2]})],
    ["a second leg without its pin", withLeg(leg, without(file.legs[1], "pin"))],
    ["a leg number of 0", withLeg({...leg, leg: 0})],
    ["a leg number of 256", withLeg({...leg, leg: 256})],
    ["a leg number that is a string", withLeg({...leg, leg: "1"})],
    ["a leg number with a fraction", text.replace('"leg":1', '"leg":1.5')],
    ["two legs with the same number", withLeg(leg, {...file.legs[1], leg: 1})],
    ["two legs with the same number and the same pin", withLeg(leg, {...file.legs[1], leg: 1, pin: 5})],
    ["a pin of -1", withLeg({...leg, pin: -1})],
    ["a pin of 256", withLeg({...leg, pin: 256})],
    ["a pin that is a string", withLeg({...leg, pin: "5"})],
    ["a pin that is null", withLeg({...leg, pin: null})],
    ["two legs with the same pin", withLeg(leg, {...file.legs[1], pin: 5})],
    ["two legs with the same pin, the second with a wrong first_led", withLeg(leg, {...file.legs[1], pin: 5, first_led: "x"})],
    ["a first_led of the other kind", withLeg({...leg, first_led: names.otherEnds[0]})],
    ["a first_led of the other kind in the second leg", withLeg(leg, {...file.legs[1], first_led: names.otherEnds[1]})],
    ["a first_led in capital letters", withLeg({...leg, first_led: names.ends[0].toUpperCase()})],
    ["a first_led that is a number", withLeg({...leg, first_led: 1})],
    ["a first_led that is null", withLeg({...leg, first_led: null})],
    ["a first_led that is empty", withLeg({...leg, first_led: ""})],
    [`${strips} that is a number`, withLeg({...leg, [strips]: 1})],
    [`${strips} that is an object`, withLeg({...leg, [strips]: {}})],
    [`${strips} that is empty`, withLeg({...leg, [strips]: []})],
    [`an entry of ${strips} that is a string`, withLeg({...leg, [strips]: [1, "2"]})],
    [`an entry of ${strips} with a fraction`, text.replace(`"${strips}":[1,2]`, `"${strips}":[1,2.0]`)],
    [`an entry of ${strips} that is null`, withLeg({...leg, [strips]: [null, 2]})],
    [`an entry of ${strips} that is 0`, withLeg({...leg, [strips]: [0, 2]})],
    [`an entry of ${strips} that is negative`, withLeg({...leg, [strips]: [1, -2]})],
    [`an entry of ${strips} one above the number of ${strips}`, withLeg({...leg, [strips]: [1, 5]})],
    [`an entry of ${strips} of thirty digits`, text.replace(`"${strips}":[1,2]`, `"${strips}":[1,${"9".repeat(30)}]`)],
    [`an entry of ${strips} of forty digits`, text.replace(`"${strips}":[1,2]`, `"${strips}":[1,${"9".repeat(40)}]`)],
    [`an entry of ${strips} twice in one leg`, withLeg({...leg, [strips]: [1, 1]})],
    [`an entry of ${strips} in two legs`, withLeg({...leg, [strips]: [1, 4]})],
    [`an entry of ${strips} out of range in the second leg, after one listed twice in the first`, withLeg({...leg, [strips]: [1, 1]}, {...file.legs[1], [strips]: [9, 3]})],
    ["a canvas of 65,535 pixels", {...file, [names.length]: 65535, legs: [{...leg, [strips]: [1]}]}],
    ["a canvas of 131,070 pixels", {...file, [names.length]: 65535, legs: [{...leg, [strips]: [1, 2]}]}],
    ["a canvas of 65,536 pixels", {...file, [names.length]: 16384}],
  ];
}

// Files of one kind that are as docs/mapping.md says.
function whole(names) {
  const file = base(names);
  const leg = file.legs[0];
  return [
    ["two legs of two strips", file],
    ["the members in another order", {legs: file.legs, [names.length]: 4, version: 1}],
    ["one leg of one LED", {version: 1, [names.length]: 1, legs: [{leg: 255, pin: 0, first_led: names.ends[1], [names.strips]: [1]}]}],
    ["a canvas of 65,534 pixels", {version: 1, [names.length]: 32767, legs: [{...leg, [names.strips]: [2, 1]}]}],
    ["the longest strip", {version: 1, [names.length]: 65534, legs: [{...leg, [names.strips]: [1]}]}],
    ["legs in another order than their numbers", {...file, legs: [file.legs[1], leg]}],
    ["white space around everything", JSON.stringify(file, null, 4)],
  ];
}

function bytesOf(file) {
  return utf8(typeof file === "string" ? file : JSON.stringify(file));
}

test("the tracked mapping files and the made-up ones of the core's suite", async (t) => {
  const texts = reference("mappings");
  const names = Object.keys(texts).sort();
  const theirs = reference("read_mappings", [], names.map((name) => hex(utf8(texts[name]))));

  await t.test("every file of mapping/ is among them, and files of both kinds", () => {
    const tracked = fs.readdirSync(path.join(ROOT, "mapping")).filter((name) => name.endsWith(".json")).map((name) => name.slice(0, -5));
    assert.ok(tracked.length >= 2);
    for (const name of tracked) {
      assert.ok(names.includes(name), name);
      assert.equal(texts[name], fs.readFileSync(path.join(ROOT, "mapping", `${name}.json`), "utf8"));
    }
    assert.ok(names.length >= tracked.length + 8, names.join(" "));
    assert.ok(theirs.some((canvas) => canvas.kind === "rows"));
    assert.ok(theirs.some((canvas) => canvas.kind === "columns"));
  });

  for (let i = 0; i < names.length; i += 1) {
    await t.test(names[i], () => {
      assert.equal(theirs[i].reason, undefined);
      assert.deepEqual(ours(utf8(texts[names[i]])), theirs[i]);
    });
  }

  await t.test("legs-2.json gives a canvas of 60 x 6 and legs-20.json one of 60 x 60", () => {
    const bench = mapping.loads(new Uint8Array(fs.readFileSync(path.join(ROOT, "mapping", "legs-2.json"))));
    assert.deepEqual([bench.kind, bench.width, bench.height, bench.legs.length], ["rows", 60, 6, 2]);
    assert.equal(mapping.stripLength(bench), 60);
    assert.deepEqual(bench.legs.map((leg) => mapping.ledCount(bench, leg)), [180, 180]);
    const target = mapping.loads(new Uint8Array(fs.readFileSync(path.join(ROOT, "mapping", "legs-20.json"))));
    assert.deepEqual([target.kind, target.width, target.height, target.legs.length], ["columns", 60, 60, 20]);
    assert.equal(mapping.stripLength(target), 60);
    assert.ok(target.legs.every((leg) => mapping.ledCount(target, leg) === 180 && leg.strips.length === 3));
    assert.deepEqual(Object.keys(target.legs[0]).sort(), ["firstLed", "leg", "pin", "strips"]);
  });
});

for (const [kind, names] of [["row-leg", ROW_NAMES], ["column-leg", COLUMN_NAMES]]) {
  test(`${kind} files that break a rule get the rejection of the Python reader`, async (t) => {
    const cases = broken(names);
    const theirs = reference("read_mappings", [], cases.map(([, file]) => hex(bytesOf(file))));
    const details = new Set();
    for (let i = 0; i < cases.length; i += 1) {
      const [label, file] = cases[i];
      await t.test(label, () => {
        assert.equal(theirs[i].reason, "mapping-malformed", `${label}: ${JSON.stringify(theirs[i])}`);
        same(ours(bytesOf(file)), theirs[i], label);
        details.add(theirs[i].detail.replace(/\d+/g, "N"));
      });
    }
    await t.test("the files meet many different rules", () => {
      assert.ok(details.size >= 38, `${details.size} different details`);
    });
  });

  test(`${kind} files that are as the format says are read as the Python reader reads them`, async (t) => {
    const cases = whole(names);
    const theirs = reference("read_mappings", [], cases.map(([, file]) => hex(bytesOf(file))));
    for (let i = 0; i < cases.length; i += 1) {
      const [label, file] = cases[i];
      await t.test(label, () => {
        assert.equal(theirs[i].reason, undefined, JSON.stringify(theirs[i]));
        assert.deepEqual(ours(bytesOf(file)), theirs[i]);
      });
    }
  });
}

test("both command lines read a mapping file the same way", async (t) => {
  const folder = temporary(t);
  const sources = path.join(folder, "sources");
  fs.mkdirSync(sources);
  // A source of a canvas no mapping of this test has, so that pack names the canvas of
  // the mapping in the detail of size-mismatch.
  fs.writeFileSync(path.join(sources, "a.json"), '{"version": 1, "width": 1, "height": 3, "frames": [{"ms": 1, "pixels": [0, 0, 0]}]}');
  const show = path.join(folder, "show.json");
  fs.writeFileSync(show, '{"version": 1, "brightness": 1, "items": [{"id": 1, "file": "a.odrg"}]}');
  const out = path.join(folder, "out");
  const packWith = (file) => runBoth(["pack", "--mapping", file, "--show", show, "--sources", sources, "--out", out]);

  await t.test("a file of every kind that is as the format says: the same canvas", () => {
    const texts = reference("mappings");
    const cases = [
      ...Object.entries(texts).map(([name, text]) => [name, text]),
      ...whole(ROW_NAMES).map(([label, file]) => [`rows: ${label}`, file]),
      ...whole(COLUMN_NAMES).map(([label, file]) => [`columns: ${label}`, file]),
    ];
    cases.forEach(([label, file], i) => {
      const name = path.join(folder, `whole-${i}.json`);
      fs.writeFileSync(name, bytesOf(file));
      const canvas = mapping.loads(bytesOf(file));
      const {js, python} = packWith(name);
      assert.equal(python.status, 1, label);
      assert.deepEqual(js, python, label);
      assert.equal(js.err, `error: size-mismatch: ${path.join(sources, "a.json")}: the canvas is 1 x 3 and the mapping's is ${canvas.width} x ${canvas.height}\n`);
    });
  });

  await t.test("a file that breaks a rule, for every rule and each kind: the same error line", async () => {
    const cases = [
      ...broken(ROW_NAMES).map(([label, file]) => [`rows: ${label}`, file]),
      ...broken(COLUMN_NAMES).map(([label, file]) => [`columns: ${label}`, file]),
    ];
    const commands = cases.map(([, file], i) => {
      const name = path.join(folder, `broken-${i}.json`);
      fs.writeFileSync(name, bytesOf(file));
      return ["pack", "--mapping", name, "--show", show, "--sources", sources, "--out", out];
    });
    const theirs = runPythonMany(commands);
    for (let i = 0; i < cases.length; i += 1) {
      const [label] = cases[i];
      const name = commands[i][2];
      const python = theirs[i];
      const js = await runJsHere(commands[i]);
      assert.equal(python.status, 1, label);
      assert.equal(js.status, 1, label);
      assert.ok(python.err.startsWith(`error: mapping-malformed: ${name}: `), python.err);
      if (/: bad-json: line \d+, column \d+: /.test(python.err)) {
        assert.ok(js.err.startsWith(`error: mapping-malformed: ${name}: bad-json: line `), js.err);
      } else {
        assert.deepEqual(js, python, label);
      }
    }
    // A few of them once more as programs of their own.
    for (const i of [0, 9, 20, 40, 60, cases.length - 1]) {
      const {js, python} = packWith(commands[i][2]);
      assert.deepEqual({status: js.status, out: js.out}, {status: 1, out: ""});
      assert.deepEqual(python, theirs[i]);
      assert.deepEqual(js, await runJsHere(commands[i]));
    }
  });

  await t.test("a file that is not there is mapping-missing", () => {
    const {js, python} = packWith(path.join(folder, "none.json"));
    assert.deepEqual(js, python);
    assert.equal(js.err, `error: mapping-missing: ${path.join(folder, "none.json")}: No such file or directory\n`);
    const below = packWith(path.join(show, "legs.json"));
    assert.deepEqual(below.js, below.python);
    assert.equal(below.js.err.split(": ")[1], "mapping-missing");
    const dir = packWith(folder);
    assert.deepEqual(dir.js, dir.python);
    assert.equal(dir.js.err, `error: mapping-missing: ${folder}: Is a directory\n`);
  });

  await t.test("nothing was written", () => {
    assert.equal(fs.existsSync(out), false);
    assert.equal(fs.existsSync(`${out}.part`), false);
  });
});
