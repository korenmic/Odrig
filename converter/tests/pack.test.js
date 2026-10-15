import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import test from "node:test";

import {errors, jsonframes, odrg, pack, show} from "../lib/index.js";
import {RIGHTS_HOLD, ROOT, allowAgain, filesUnder, forbid, hex, runJs, runJsAndStored, runJsHere, storedAnswer, storedRun, storedRuns, temporary, utf8} from "./support.js";

const BENCH = "mapping/legs-2.json";
const TARGET = "mapping/legs-20.json";

function read(...parts) {
  return new Uint8Array(fs.readFileSync(path.join(...parts)));
}

function equal(a, b) {
  return Buffer.from(a).equals(Buffer.from(b));
}

// Has a generator of the Python tool write its animation for a mapping file under a name.
function generate(generator, mapping, out, seconds = null) {
  const argv = [out, "--mapping", mapping, ...(seconds === null ? [] : ["--seconds", seconds])];
  const done = storedRun(argv, {module: `odrig.generators.${generator}`});
  assert.equal(done.status, 0, done.err);
}

// The three shows of Requirement 11: the example show on the bench canvas, the demo show
// on 60 x 60, and a show of one dense clip of 2 seconds on 60 x 60. The sources of the
// last two are written by the generators of the Python tool. Beside them, a show without
// items, which packs to the two JSON files, and one whose animations have a repeat count
// and a longest duration, which go into the installed show as the show file has them.
function shows(folder) {
  const demo = path.join(folder, "demo-sources");
  fs.mkdirSync(demo);
  generate("hello_world", TARGET, path.join(demo, "hello.json"));
  generate("dvd_bounce", TARGET, path.join(demo, "dvd.json"));
  const dense = path.join(folder, "dense-sources");
  fs.mkdirSync(dense);
  generate("dense", TARGET, path.join(dense, "dense.json"), 2);
  const denseShow = path.join(folder, "dense-show.json");
  fs.writeFileSync(denseShow, '{"version": 1, "brightness": 64, "items": [{"id": 7, "file": "dense.odrg"}], "start": 7}\n');
  const emptyShow = path.join(folder, "empty-show.json");
  fs.writeFileSync(emptyShow, '{"version": 1, "brightness": 40, "items": []}\n');
  const turnsShow = path.join(folder, "turns-show.json");
  fs.writeFileSync(turnsShow, '{"version": 1, "brightness": 40, "min_seconds": 45,\n "items": [{"id": 1, "file": "hello.odrg", "repeat": 3, "max_seconds": 120}, {"id": 2, "file": "dvd.odrg", "max_seconds": 9}]}\n');
  return [
    {label: "the example show on the bench canvas", show: "shows/example/show.json", mapping: BENCH, sources: "animations", names: ["dvd.odrg", "hello.odrg"]},
    {label: "the demo show on 60 x 60", show: "shows/demo-20/show.json", mapping: TARGET, sources: demo, names: ["dvd.odrg", "hello.odrg"]},
    {label: "a show of one dense clip on 60 x 60", show: denseShow, mapping: TARGET, sources: dense, names: ["dense.odrg"]},
    {label: "a show without items on the bench canvas", show: emptyShow, mapping: BENCH, sources: "animations", names: []},
    {label: "a show whose animations have turns of their own", show: turnsShow, mapping: BENCH, sources: "animations", names: ["dvd.odrg", "hello.odrg"]},
  ];
}

test("pack builds the folder the Python tool builds", async (t) => {
  const folder = temporary(t);
  const quiet = {status: 0, out: "", err: ""};
  let number = 0;
  for (const given of shows(folder)) {
    for (const flags of [["--uncompressed"], []]) {
      const compressed = flags.length === 0;
      await t.test(`${given.label}, ${compressed ? "compressed" : "uncompressed"}`, (inner) => {
        number += 1;
        const ours = path.join(folder, `ours-${number}`);
        const theirs = path.join(folder, `theirs-${number}`);
        const argv = (out) => ["pack", "--show", given.show, "--mapping", given.mapping, "--sources", given.sources, "--out", out, ...flags];
        assert.deepEqual(runJs(argv(ours)), quiet);
        assert.deepEqual(storedRun(argv(theirs)), quiet);

        const names = filesUnder(ours);
        assert.deepEqual(names, filesUnder(theirs));
        assert.deepEqual(names, [...given.names, "mapping.json", "show.json"].sort());
        assert.ok(equal(read(ours, "mapping.json"), read(ROOT, given.mapping)));
        assert.ok(equal(read(ours, "show.json"), fs.readFileSync(path.resolve(ROOT, given.show))));
        assert.equal(fs.existsSync(`${ours}.part`), false);

        for (const name of given.names) {
          const mine = read(ours, name);
          const reference9 = read(theirs, name);
          assert.equal(mine[5], compressed ? 1 : 0, name);
          if (!compressed) {
            assert.ok(equal(mine, reference9), `${name} has the bytes of the Python tool`);
          } else {
            const [a, b] = storedAnswer("decode", [], [hex(mine), hex(reference9)]);
            assert.ok(a.records.length > 0);
            assert.deepEqual(a, b, `${name} decodes to the frame records of the Python tool's file`);
            assert.ok(20 * mine.length <= 21 * reference9.length, `${name}: ${mine.length} bytes against ${reference9.length}`);
          }
          inner.diagnostic(`${name}: ${mine.length} bytes, the Python tool's ${reference9.length}`);
        }

        // The library packs the same files from bytes held in memory.
        const sources = new Map(given.names.map((name) => [name.replace(/\.odrg$/, ".json"), read(path.resolve(ROOT, given.sources), name.replace(/\.odrg$/, ".json"))]));
        const packed = pack.pack({mapping: read(ROOT, given.mapping), show: new Uint8Array(fs.readFileSync(path.resolve(ROOT, given.show))), sources}, {compressed});
        assert.deepEqual([...packed.keys()].slice(0, 2), ["mapping.json", "show.json"]);
        assert.deepEqual([...packed.keys()].sort(), names);
        for (const [name, bytes] of packed) {
          assert.ok(equal(bytes, read(ours, name)), `${name} from pack.pack is the file the command line writes`);
        }
      });
    }
  }
});

test("pack.pack, from bytes held in memory", async (t) => {
  const mappingBytes = read(ROOT, BENCH);
  const showBytes = read(ROOT, "shows", "example", "show.json");
  const sources = {"hello.json": read(ROOT, "animations", "hello.json"), "dvd.json": read(ROOT, "animations", "dvd.json")};

  await t.test("the files come in the order mapping.json, show.json, then the animations in the order of first use", () => {
    const files = pack.pack({mapping: mappingBytes, show: showBytes, sources});
    assert.deepEqual([...files.keys()], ["mapping.json", "show.json", "hello.odrg", "dvd.odrg"]);
    assert.equal(files.get("mapping.json"), mappingBytes);
    assert.equal(files.get("show.json"), showBytes);
    assert.ok(equal(files.get("hello.odrg"), odrg.encode(jsonframes.loads(sources["hello.json"]))));
    assert.equal(files.get("hello.odrg")[5], 1);
    assert.equal(pack.pack({mapping: mappingBytes, show: showBytes, sources}, {compressed: false}).get("dvd.odrg")[5], 0);
  });

  await t.test("the sources are a Map or an object, and a file that two items name is encoded once", () => {
    const twice = utf8('{"version": 1, "brightness": 1, "items": [{"id": 1, "file": "dvd.odrg"}, {"id": 2, "file": "hello.odrg"}, {"id": 3, "file": "dvd.odrg"}]}');
    const fromObject = pack.pack({mapping: mappingBytes, show: twice, sources});
    const fromMap = pack.pack({mapping: mappingBytes, show: twice, sources: new Map(Object.entries(sources))});
    assert.deepEqual([...fromObject.keys()], ["mapping.json", "show.json", "dvd.odrg", "hello.odrg"]);
    assert.deepEqual([...fromMap.keys()], [...fromObject.keys()]);
    for (const [name, bytes] of fromMap) {
      assert.ok(equal(bytes, fromObject.get(name)), name);
    }
  });

  await t.test("the rejections name the files by their installed names", () => {
    const refused = (given, reason, detail) => {
      assert.throws(() => pack.pack(given), (error) => {
        assert.ok(error instanceof errors.Rejection, String(error));
        assert.equal(error.reason, reason);
        if (detail instanceof RegExp) {
          assert.match(error.detail, detail);
        } else {
          assert.equal(error.detail, detail);
        }
        return true;
      });
    };
    refused({mapping: utf8("{}"), show: showBytes, sources}, "mapping-malformed", 'mapping.json: missing-member: the file has no member "version"');
    refused({mapping: mappingBytes, show: utf8("[]"), sources}, "show-malformed", "show.json: bad-json: the top level is not an object");
    refused({mapping: mappingBytes, show: showBytes, sources: {"dvd.json": sources["dvd.json"]}}, "file-missing", /^hello\.json: /);
    refused({mapping: mappingBytes, show: showBytes, sources: new Map()}, "file-missing", /^hello\.json: /);
    refused({mapping: mappingBytes, show: showBytes, sources: {...sources, "hello.json": utf8("{}")}}, "file-malformed", 'hello.json: missing-member: the file has no member "version"');
    refused({mapping: read(ROOT, TARGET), show: showBytes, sources}, "size-mismatch", "hello.json: the canvas is 60 x 6 and the mapping's is 60 x 60");
    const long = utf8('{"version": 1, "width": 60, "height": 6, "frames": [{"ms": 281470681677826, "pixels": [' + new Array(360).fill(0).join(", ") + "]}]}");
    refused({mapping: mappingBytes, show: showBytes, sources: {...sources, "hello.json": long}}, "too-many-frames", "hello.json: 4294967296 frame records would be needed, above 4294967295");
  });

  await t.test("the plan of a pack has the canvas, the show and the names", () => {
    const plan = pack.begin(mappingBytes, showBytes, {mapping: "m.json", show: "s.json"});
    assert.deepEqual([plan.canvas.width, plan.canvas.height], [60, 6]);
    assert.deepEqual(plan.names, ["hello.odrg", "dvd.odrg"]);
    assert.equal(plan.show.start, 3);
    assert.equal(pack.sourceName("hello.odrg"), "hello.json");
    assert.throws(() => pack.begin(utf8("{}"), showBytes, {mapping: "m.json", show: "s.json"}), {reason: "mapping-malformed", detail: /^m\.json: /});
    assert.throws(() => pack.begin(mappingBytes, utf8("{}"), {mapping: "m.json", show: "s.json"}), {reason: "show-malformed", detail: /^s\.json: /});
    const encoded = pack.encodeSource(plan, "dvd.odrg", sources["dvd.json"], "sources/dvd.json", {compressed: false});
    assert.ok(equal(encoded, odrg.encode(jsonframes.loads(sources["dvd.json"]), {compressed: false})));
    assert.throws(() => pack.encodeSource(plan, "dvd.odrg", null, "sources/dvd.json"), {reason: "file-missing", detail: /^sources\/dvd\.json: /});
  });
});

// A show of two animations and a cycle, with its parts given as values.
function showFile({version = 1, brightness = 128, items = null, start = 3, more = {}} = {}) {
  const file = {
    version,
    brightness,
    items: items === null ? [{id: 1, file: "a.odrg"}, {id: 2, file: "b.odrg"}, {id: 3, cycle: [1, 2], seconds: 15}] : items,
    ...more,
  };
  if (start !== null) {
    file.start = start;
  }
  return file;
}

function without(object, name) {
  const copy = {...object};
  delete copy[name];
  return copy;
}

const A = {id: 1, file: "a.odrg"};
const B = {id: 2, file: "b.odrg"};
const CYCLE = {id: 3, cycle: [1, 2], seconds: 15};
const TEXT = JSON.stringify(showFile());

// Shows that break each rule of docs/show.md once, in the order of the checks. A show is
// given as a value or as its text.
const BROKEN_SHOWS = [
  ["a text that is not JSON", '{"version": 1,'],
  ["a top level that is an array", []],
  ["a top level that is a number", 1],
  ["no version", without(showFile(), "version")],
  ["a version that is a string", showFile({version: "1"})],
  ["a version with a fraction", TEXT.replace('"version":1', '"version":1.0')],
  ["version 2", showFile({version: 2})],
  ["version 2 in a file that is nothing else", {version: 2}],
  ["no brightness", without(showFile(), "brightness")],
  ["no items", without(showFile(), "items")],
  ["no brightness and an unknown member", {...without(showFile(), "brightness"), speed: 2}],
  ["an unknown member", showFile({more: {speed: 2}})],
  ["a member named twice", TEXT.replace('"brightness":128', '"brightness":128,"brightness":128')],
  ["a brightness of -1", showFile({brightness: -1})],
  ["a brightness of 256", showFile({brightness: 256})],
  ["a brightness that is a string", showFile({brightness: "128"})],
  ["a brightness with a fraction", TEXT.replace('"brightness":128', '"brightness":128.0')],
  ["a brightness that is null", showFile({brightness: null})],
  ["items that is an object", showFile({items: {}})],
  ["items that is a string", showFile({items: "a.odrg"})],
  ["items that is empty, with a start", showFile({items: []})],
  ["an item that is a number", showFile({items: [5]})],
  ["an item that is null", showFile({items: [A, null]})],
  ["an item that is an array", showFile({items: [[1, "a.odrg"]]})],
  ["an animation item without an id", showFile({items: [{file: "a.odrg"}]})],
  ["an animation item with seconds", showFile({items: [{...A, seconds: 5}]})],
  ["an item with a file and a cycle", showFile({items: [A, {id: 2, file: "b.odrg", cycle: [1]}]})],
  ["an item with a file, a cycle and seconds", showFile({items: [A, {id: 2, file: "b.odrg", cycle: [1], seconds: 5}]})],
  ["an item with an id only", showFile({items: [{id: 1}]})],
  ["an empty item", showFile({items: [{}]})],
  ["an id of 0", showFile({items: [{...A, id: 0}]})],
  ["an id of 65,536", showFile({items: [{...A, id: 65536}]})],
  ["an id that is a string", showFile({items: [{...A, id: "1"}]})],
  ["an id with a fraction", TEXT.replace('"id":1', '"id":1.0')],
  ["an id of a cycle that is negative", showFile({items: [A, B, {...CYCLE, id: -3}]})],
  ["a file that is a number", showFile({items: [{id: 1, file: 5}]})],
  ["a file that is null", showFile({items: [{id: 1, file: null}]})],
  ["a file that is an array", showFile({items: [{id: 1, file: ["a.odrg"]}]})],
  ["a file name that is empty", showFile({items: [{id: 1, file: ""}]})],
  ["a file name with a capital letter", showFile({items: [{id: 1, file: "A.odrg"}]})],
  ["a file name with a capital ending", showFile({items: [{id: 1, file: "a.ODRG"}]})],
  ["a file name with a space", showFile({items: [{id: 1, file: "a b.odrg"}]})],
  ["a file name with a slash", showFile({items: [{id: 1, file: "a/b.odrg"}]})],
  ["a file name with a letter outside a to z", showFile({items: [{id: 1, file: "ä.odrg"}]})],
  ["a file name of 33 characters", showFile({items: [{id: 1, file: `${"a".repeat(28)}.odrg`}]})],
  ["a file name with another ending", showFile({items: [{id: 1, file: "a.json"}]})],
  ["a file name without an ending", showFile({items: [{id: 1, file: "odrg"}]})],
  ["a file name with a line feed after it", showFile({items: [{id: 1, file: "a.odrg\n"}]})],
  ["a file name in the second item", showFile({items: [A, {id: 2, file: "B.odrg"}]})],
  ["a cycle item without seconds", showFile({items: [A, B, without(CYCLE, "seconds")]})],
  ["a cycle item without an id", showFile({items: [A, B, without(CYCLE, "id")]})],
  ["a cycle item with an unknown member", showFile({items: [A, B, {...CYCLE, name: "x"}]})],
  ["a cycle that is a number", showFile({items: [A, B, {...CYCLE, cycle: 1}]})],
  ["a cycle that is an object", showFile({items: [A, B, {...CYCLE, cycle: {}}]})],
  ["a cycle that is empty", showFile({items: [A, B, {...CYCLE, cycle: []}]})],
  ["an entry of a cycle that is a string", showFile({items: [A, B, {...CYCLE, cycle: [1, "2"]}]})],
  ["an entry of a cycle with a fraction", TEXT.replace('"cycle":[1,2]', '"cycle":[1,2.0]')],
  ["an entry of a cycle that is null", showFile({items: [A, B, {...CYCLE, cycle: [null]}]})],
  ["seconds of 0", showFile({items: [A, B, {...CYCLE, seconds: 0}]})],
  ["seconds of 65,536", showFile({items: [A, B, {...CYCLE, seconds: 65536}]})],
  ["seconds that is a string", showFile({items: [A, B, {...CYCLE, seconds: "15"}]})],
  ["seconds of 0 in a cycle that is empty", showFile({items: [A, B, {...CYCLE, cycle: [], seconds: 0}]})],
  ["a start that is a string", showFile({start: "3"})],
  ["a start with a fraction", TEXT.replace('"start":3', '"start":3.0')],
  ["a start that is true", showFile({start: true})],
  ["a mistake in the second item and a start that is a string", showFile({items: [A, {id: 0, file: "b.odrg"}], start: "1"})],

  ["two animation items with the same id", showFile({items: [A, {...B, id: 1}, CYCLE]})],
  ["an animation item and a cycle with the same id", showFile({items: [A, B, {...CYCLE, id: 2}]})],
  ["three items with the same id", showFile({items: [A, {...B, id: 1}, {...CYCLE, id: 1}]})],
  ["the same id twice and an id no item has", showFile({items: [A, {...B, id: 1}, {...CYCLE, cycle: [9]}]})],
  ["a cycle that names an id no item has", showFile({items: [A, B, {...CYCLE, cycle: [1, 9]}]})],
  ["a cycle that names the id 0", showFile({items: [A, B, {...CYCLE, cycle: [0]}]})],
  ["a cycle that names a negative id", showFile({items: [A, B, {...CYCLE, cycle: [-1]}]})],
  ["a cycle that names an id of thirty digits", TEXT.replace('"cycle":[1,2]', `"cycle":[1,${"9".repeat(30)}]`)],
  ["a cycle that names an id of forty digits", TEXT.replace('"cycle":[1,2]', `"cycle":[1,${"9".repeat(40)}]`)],
  ["a start that no item has", showFile({start: 9})],
  ["a start of 0", showFile({start: 0})],
  ["a start beyond 2 to the power 53", TEXT.replace('"start":3', '"start":9007199254740993')],
  ["a cycle that names an id no item has, and a start that no item has", showFile({items: [A, B, {...CYCLE, cycle: [8]}], start: 9})],
  ["a second cycle that names an id no item has, after a first that names a cycle", showFile({items: [A, {id: 3, cycle: [4], seconds: 1}, {id: 4, cycle: [9], seconds: 1}], start: 1})],
  ["a start that no item has, and a cycle that names a cycle", showFile({items: [A, {id: 3, cycle: [4], seconds: 1}, {id: 4, cycle: [1], seconds: 1}], start: 9})],
  ["a cycle that names a cycle", showFile({items: [A, B, CYCLE, {id: 4, cycle: [1, 3], seconds: 5}]})],
  ["a cycle that names itself", showFile({items: [A, B, {...CYCLE, cycle: [3]}]})],
  ["a cycle that names a cycle that comes after it", showFile({items: [A, {id: 3, cycle: [4, 1], seconds: 1}, {id: 4, cycle: [1], seconds: 1}], start: 1})],
  ["a repeat count of 0", showFile({items: [{...A, repeat: 0}], start: null})],
  ["a repeat count of 65536", showFile({items: [{...A, repeat: 65536}], start: null})],
  ["a repeat count that is a string", showFile({items: [{...A, repeat: "3"}], start: null})],
  ["a repeat count with a fraction", JSON.stringify(showFile({items: [{...A, repeat: 3}], start: null})).replace('"repeat":3', '"repeat":3.0')],
  ["a repeat count that is null", showFile({items: [{...A, repeat: null}], start: null})],
  ["a longest duration of 0", showFile({items: [{...A, max_seconds: 0}], start: null})],
  ["a longest duration of 65536", showFile({items: [{...A, max_seconds: 65536}], start: null})],
  ["a longest duration that is a list", showFile({items: [{...A, max_seconds: [60]}], start: null})],
  ["a repeat count on a cycle", showFile({items: [A, B, {...CYCLE, repeat: 2}]})],
  ["a longest duration on a cycle", showFile({items: [A, B, {...CYCLE, max_seconds: 60}]})],
  ["a shortest time on an item", showFile({items: [{...A, min_seconds: 30}], start: null})],
  ["a shortest time of 0", showFile({more: {min_seconds: 0}})],
  ["a shortest time of 65536", showFile({more: {min_seconds: 65536}})],
  ["a shortest time that is a string", showFile({more: {min_seconds: "30"}})],
  ["a repeat count of the show", showFile({more: {repeat: 2}})],
  ["a bad repeat count and a bad longest duration", showFile({items: [{...A, repeat: 0, max_seconds: 0}], start: null})],
  ["a bad file name and a bad repeat count", showFile({items: [{id: 1, file: "A.odrg", repeat: 0}], start: null})],
  ["a bad start and a bad shortest time", {...showFile({more: {min_seconds: 0}}), start: "3"}],
];

// Shows that are as docs/show.md says.
const WHOLE_SHOWS = [
  ["two animations and a cycle", showFile()],
  ["no start", showFile({start: null})],
  ["one animation", showFile({items: [A], start: 1})],
  ["a start that is an animation", showFile({start: 2})],
  ["a cycle that names an animation twice", showFile({items: [A, B, {...CYCLE, cycle: [2, 2, 1]}]})],
  ["two items with the same file", showFile({items: [B, A, {id: 9, file: "b.odrg"}, {id: 65535, file: "a.odrg"}], start: 9})],
  ["a file name of 32 characters", showFile({items: [{id: 1, file: `${"a".repeat(27)}.odrg`}], start: null})],
  ["a file name of every kind of character", showFile({items: [{id: 1, file: "a-b_c.0.9.odrg"}], start: null})],
  ["a file name that is only the ending", showFile({items: [{id: 1, file: ".odrg"}], start: null})],
  ["the largest numbers", showFile({brightness: 255, items: [A, {id: 65535, cycle: [1], seconds: 65535}], start: 65535})],
  ["a brightness of 0", showFile({brightness: 0})],
  ["items that is empty", showFile({items: [], start: null})],
  ["an animation with a repeat count and a longest duration", showFile({items: [{...A, repeat: 3, max_seconds: 120}, B, CYCLE]})],
  ["the largest repeat count and the largest longest duration", showFile({items: [{...A, repeat: 65535, max_seconds: 65535}], start: 1})],
  ["a repeat count of 1 and a longest duration of 1", showFile({items: [{...A, repeat: 1}, {...B, max_seconds: 1}], start: null})],
  ["a shortest time of 1", showFile({more: {min_seconds: 1}})],
  ["a shortest time of 65535, with no start", showFile({start: null, more: {min_seconds: 65535}})],
  ["all three, with the members of an item in another order", {version: 1, min_seconds: 45, brightness: 9, items: [{max_seconds: 7, repeat: 2, file: "a.odrg", id: 1}]}],
  ["the members in another order", {start: 3, items: showFile().items, brightness: 1, version: 1}],
];

function bytesOf(file) {
  return utf8(typeof file === "string" ? file : JSON.stringify(file));
}

// What the library says of a show file, in the form of the stored answers of the Python
// reader.
function readShow(bytes) {
  try {
    const listed = show.loads(bytes);
    return {brightness: listed.brightness, start: listed.start, minSeconds: listed.minSeconds, items: listed.items, files: show.files(listed)};
  } catch (error) {
    if (!(error instanceof errors.Rejection)) {
      throw error;
    }
    return {reason: error.reason, detail: error.detail};
  }
}

test("shows that break a rule get the rejection of the Python reader", async (t) => {
  const theirs = storedAnswer("read_shows", [], BROKEN_SHOWS.map(([, file]) => hex(bytesOf(file))));
  const reasons = new Set();
  for (let i = 0; i < BROKEN_SHOWS.length; i += 1) {
    const [label, file] = BROKEN_SHOWS[i];
    await t.test(label, () => {
      assert.notEqual(theirs[i].reason, undefined, `the Python reader accepts it: ${JSON.stringify(theirs[i])}`);
      const mine = readShow(bytesOf(file));
      if (/^bad-json: line \d+, column \d+: /.test(theirs[i].detail)) {
        assert.equal(mine.reason, theirs[i].reason);
        assert.match(mine.detail, /^bad-json: line \d+, column \d+: /);
      } else {
        assert.deepEqual(mine, theirs[i]);
      }
      reasons.add(theirs[i].reason);
    });
  }
  await t.test("the four reasons of a show file are among them", () => {
    assert.deepEqual([...reasons].sort(), ["duplicate-id", "nested-cycle", "show-malformed", "undefined-id"]);
  });
});

test("shows that are as the format says are read as the Python reader reads them", async (t) => {
  const theirs = storedAnswer("read_shows", [], WHOLE_SHOWS.map(([, file]) => hex(bytesOf(file))));
  for (let i = 0; i < WHOLE_SHOWS.length; i += 1) {
    const [label, file] = WHOLE_SHOWS[i];
    await t.test(label, () => {
      assert.equal(theirs[i].reason, undefined, JSON.stringify(theirs[i]));
      assert.deepEqual(readShow(bytesOf(file)), theirs[i]);
    });
  }
});

// A folder with a mapping of 2 x 1, sources a.json and b.json of that canvas, and what a
// case needs beside them.
function bench(t) {
  const folder = temporary(t);
  const sources = path.join(folder, "sources");
  fs.mkdirSync(sources);
  const mapping = path.join(folder, "legs.json");
  fs.writeFileSync(mapping, '{"version": 1, "width": 2, "legs": [{"leg": 1, "pin": 1, "first_led": "left", "rows": [1]}]}');
  const source = (pixels, width = 2, height = 1, ms = 20) => `{"version": 1, "width": ${width}, "height": ${height}, "frames": [{"ms": ${ms}, "pixels": [${pixels}]}]}`;
  fs.writeFileSync(path.join(sources, "a.json"), source("1, 2"));
  fs.writeFileSync(path.join(sources, "b.json"), source("3, 4"));
  const showPath = path.join(folder, "show.json");
  fs.writeFileSync(showPath, JSON.stringify(showFile()));
  return {folder, sources, mapping, show: showPath, source};
}

// Runs the same pack in both tools, each into a folder of its own that does not exist yet,
// and compares what they say.
async function samePacks(cases, at) {
  const commands = (side) => cases.map(([, given], i) => {
    const out = path.join(at.folder, `${side}-out-${i}`);
    return ["pack", "--show", given.show ?? at.show, "--mapping", given.mapping ?? at.mapping, "--sources", given.sources ?? at.sources, "--out", given.out ?? out, ...(given.flags ?? [])];
  });
  const theirs = storedRuns(commands("py"));
  const ours = [];
  for (const argv of commands("js")) {
    ours.push(await runJsHere(argv));
  }
  return cases.map(([label], i) => ({label, js: ours[i], python: theirs[i], jsOut: commands("js")[i][8], pythonOut: commands("py")[i][8]}));
}

test("pack refuses what the Python tool refuses, with its error line", async (t) => {
  const at = bench(t);
  const write = (name, text) => {
    const file = path.join(at.folder, name);
    fs.mkdirSync(path.dirname(file), {recursive: true});
    fs.writeFileSync(file, typeof text === "string" ? text : JSON.stringify(text));
    return file;
  };
  const sourcesWith = (name, files) => {
    const folder = path.join(at.folder, name);
    fs.mkdirSync(folder);
    for (const [file, text] of Object.entries(files)) {
      if (text === "folder") {
        fs.mkdirSync(path.join(folder, file));
      } else {
        fs.writeFileSync(path.join(folder, file), text);
      }
    }
    return folder;
  };
  const good = at.source("1, 2");

  await t.test("a show that breaks a rule, for every rule", async () => {
    const cases = BROKEN_SHOWS.map(([label, file], i) => [label, {show: write(`broken/show-${i}.json`, file)}]);
    for (const {label, js, python, jsOut, pythonOut} of await samePacks(cases, at)) {
      assert.equal(python.status, 1, label);
      assert.equal(js.status, 1, label);
      assert.equal(js.out, "");
      if (/: bad-json: line \d+, column \d+: /.test(python.err)) {
        assert.equal(js.err.split(": ")[1], "show-malformed", label);
      } else {
        assert.equal(js.err, python.err, label);
      }
      assert.equal(fs.existsSync(jsOut), false, label);
      assert.equal(fs.existsSync(pythonOut), false, label);
    }
  });

  const cases = [
    ["a show file that is not there", {show: path.join(at.folder, "none.json")}, "show-missing"],
    ["a show file that is a folder", {show: at.sources}, "show-missing"],
    ["a mapping file and a show file that are not there", {mapping: path.join(at.folder, "none.json"), show: path.join(at.folder, "none.json")}, "mapping-missing"],
    ["a mapping file that breaks a rule and a show file that is not there", {mapping: write("bad-legs.json", "{}"), show: path.join(at.folder, "none.json")}, "mapping-malformed"],
    ["a mapping file that breaks a rule and a show that breaks one", {mapping: write("bad-legs-2.json", "[]"), show: write("bad-show.json", "[]")}, "mapping-malformed"],
    ["a source that is not there", {sources: sourcesWith("s1", {"a.json": good})}, "file-missing"],
    ["no source at all", {sources: sourcesWith("s2", {})}, "file-missing"],
    ["a sources folder that is not there", {sources: path.join(at.folder, "no-sources")}, "file-missing"],
    ["a sources folder that is a file", {sources: at.show}, "file-missing"],
    ["a source that is a folder", {sources: sourcesWith("s3", {"a.json": "folder", "b.json": good})}, "file-missing"],
    ["a source that is not JSON", {sources: sourcesWith("s4", {"a.json": "{", "b.json": good})}, "file-malformed"],
    ["a source that is empty", {sources: sourcesWith("s5", {"a.json": "", "b.json": good})}, "file-malformed"],
    ["a source without a version", {sources: sourcesWith("s6", {"a.json": "{}", "b.json": good})}, "file-malformed"],
    ["a source of version 2", {sources: sourcesWith("s7", {"a.json": good.replace('"version": 1', '"version": 2'), "b.json": good})}, "file-malformed"],
    ["a source with a pixel too few", {sources: sourcesWith("s8", {"a.json": at.source("1"), "b.json": good})}, "file-malformed"],
    ["a source with a colour above white", {sources: sourcesWith("s9", {"a.json": good, "b.json": at.source("1, 16777216")})}, "file-malformed"],
    ["a source that is an ODRG file", {sources: sourcesWith("s10", {"a.json": fs.readFileSync(path.join(ROOT, "tests", "vectors", "valid", "pal-1.odrg")), "b.json": good})}, "file-malformed"],
    ["a source of another width", {sources: sourcesWith("s11", {"a.json": at.source("1, 2, 3", 3, 1), "b.json": good})}, "size-mismatch"],
    ["a source of another height", {sources: sourcesWith("s12", {"a.json": good, "b.json": at.source("1, 2, 3, 4", 2, 2)})}, "size-mismatch"],
    ["a source with the width and the height the other way round", {sources: sourcesWith("s13", {"a.json": at.source("1, 2", 1, 2), "b.json": good})}, "size-mismatch"],
    ["a source that needs too many frame records", {sources: sourcesWith("s14", {"a.json": at.source("1, 2", 2, 1, "281470681677826"), "b.json": good})}, "too-many-frames"],
    ["a first source of another size and a second that is not there", {sources: sourcesWith("s15", {"a.json": at.source("1", 1, 1)})}, "size-mismatch"],
    ["a first source that is not there and a second of another size", {sources: sourcesWith("s16", {"b.json": at.source("1", 1, 1)})}, "file-missing"],
    ["a first source that is malformed and a second that is not there", {sources: sourcesWith("s17", {"a.json": "[]"})}, "file-malformed"],
    ["a source too large for ODRG, on a mapping of its size", {
      mapping: write("wide.json", {version: 1, width: 32767, legs: [{leg: 1, pin: 1, first_led: "left", rows: [1, 2]}]}),
      show: write("one.json", showFile({items: [A], start: null})),
      sources: sourcesWith("s18", {"a.json": at.source(Array.from({length: 65534}, (unused, i) => i % 300).join(", "), 32767, 2)}),
    }, "canvas-too-large"],
  ];

  await t.test("a file that is missing, malformed or of another size, in the order of the checks", async () => {
    const results = await samePacks(cases.map(([label, given]) => [label, given]), at);
    results.forEach(({label, js, python, jsOut, pythonOut}, i) => {
      assert.equal(python.err.split(": ")[1], cases[i][2], `${label}: ${python.err}`);
      assert.equal(python.status, 1, label);
      if (/: bad-json: line \d+, column \d+: /.test(python.err)) {
        assert.equal(js.status, 1, label);
        assert.equal(js.err.split(": ").slice(0, 2).join(": "), python.err.split(": ").slice(0, 2).join(": "), label);
        assert.match(js.err, /: bad-json: line \d+, column \d+: /, label);
      } else {
        assert.deepEqual(js, python, label);
      }
      assert.equal(fs.existsSync(jsOut), false, label);
      assert.equal(fs.existsSync(`${jsOut}.part`), false, label);
      assert.equal(fs.existsSync(pythonOut), false, label);
    });
  });

  await t.test("the reasons of docs/reasons.md, Shows, are all among the cases", () => {
    const listed = fs.readFileSync(path.join(ROOT, "docs", "reasons.md"), "utf8");
    const section = listed.slice(listed.indexOf("\n## Shows\n"), listed.indexOf("\n## Media files\n"));
    const named = new Set([...section.matchAll(/^\| (`[a-z-]+`(?:, `[a-z-]+`)*) \|/gm)].flatMap((match) => [...match[1].matchAll(/`([a-z-]+)`/g)].map((inner) => inner[1])));
    const met = new Set([...cases.map(([, , reason]) => reason), "show-malformed", "duplicate-id", "undefined-id", "nested-cycle", "output-not-empty"]);
    assert.ok(named.size >= 12, [...named].join(" "));
    for (const reason of named) {
      assert.ok(met.has(reason), `no case meets ${reason}`);
    }
  });

  await t.test("a few of them once more as programs of their own", () => {
    for (const [label, given] of [cases[0], cases[5], cases[10], cases[17]]) {
      const out = path.join(at.folder, "program-out");
      const argv = ["pack", "--show", given.show ?? at.show, "--mapping", given.mapping ?? at.mapping, "--sources", given.sources ?? at.sources, "--out", out];
      const {js, python} = runJsAndStored(argv);
      assert.equal(js.status, 1, label);
      if (!/: bad-json: line \d+, column \d+: /.test(python.err)) {
        assert.deepEqual(js, python, label);
      }
      assert.equal(fs.existsSync(out), false);
    }
  });
});

test("the output folder", async (t) => {
  const at = bench(t);
  const argv = (out, more = {}) => ["pack", "--show", more.show ?? at.show, "--mapping", at.mapping, "--sources", more.sources ?? at.sources, "--out", out, ...(more.flags ?? [])];
  const packed = ["a.odrg", "b.odrg", "mapping.json", "show.json"];
  const both = async (make, more) => {
    const results = {};
    for (const side of ["js", "py"]) {
      const out = make(side);
      results[side] = {out, result: side === "js" ? await runJsHere(argv(out, more)) : storedRuns([argv(out, more)])[0]};
    }
    return results;
  };
  const sameResult = (results, label) => {
    const text = (side) => results[side].result.err.split(results[side].out).join("<out>").replace(/(js|py)-/g, "");
    assert.equal(results.js.result.status, results.py.result.status, `${label}: ${results.js.result.err} / ${results.py.result.err}`);
    assert.equal(text("js"), text("py"), label);
    assert.equal(results.js.result.out, "");
  };

  await t.test("a folder that does not exist is made, with the folders above it", async () => {
    const results = await both((side) => path.join(at.folder, `${side}-new`, "deep", "deeper", "out"));
    sameResult(results, "new folders");
    for (const side of ["js", "py"]) {
      assert.equal(results[side].result.status, 0);
      assert.deepEqual(filesUnder(results[side].out), packed);
      assert.deepEqual(fs.readdirSync(path.dirname(results[side].out)), ["out"]);
    }
    for (const name of packed) {
      assert.ok(equal(read(results.js.out, name), read(results.py.out, name)), name);
    }
  });

  await t.test("a folder that is there and empty is filled", async () => {
    const results = await both((side) => {
      const out = path.join(at.folder, `${side}-empty`);
      fs.mkdirSync(out);
      return out;
    }, {flags: ["--uncompressed"]});
    sameResult(results, "an empty folder");
    for (const side of ["js", "py"]) {
      assert.equal(results[side].result.status, 0);
      assert.deepEqual(filesUnder(results[side].out), packed);
      assert.equal(fs.existsSync(`${results[side].out}.part`), false);
    }
  });

  await t.test("a path that ends in a slash, and a path from the folder the tool is started in", () => {
    assert.deepEqual(runJs(argv(`${path.join(at.folder, "slash-js")}/`)), {status: 0, out: "", err: ""});
    assert.deepEqual(storedRun(argv(`${path.join(at.folder, "slash-py")}/`)), {status: 0, out: "", err: ""});
    assert.deepEqual(filesUnder(path.join(at.folder, "slash-js")), packed);
    assert.deepEqual(filesUnder(path.join(at.folder, "slash-py")), packed);
    const inFolder = {cwd: at.folder};
    const relative = (out) => ["pack", "--show", "show.json", "--mapping", "legs.json", "--sources", "sources", "--out", out];
    assert.deepEqual(runJs(relative("rel-js/out"), inFolder), {status: 0, out: "", err: ""});
    assert.deepEqual(storedRun(relative("rel-py/out"), inFolder), {status: 0, out: "", err: ""});
    assert.deepEqual(filesUnder(path.join(at.folder, "rel-js", "out")), packed);
    assert.deepEqual(filesUnder(path.join(at.folder, "rel-py", "out")), packed);
    const missing = ["pack", "--show", "show.json", "--mapping", "legs.json", "--sources", "nowhere", "--out", "rel-out"];
    const refused = runJsAndStored(missing, inFolder);
    assert.deepEqual(refused.js, refused.python);
    assert.equal(refused.js.err, `error: file-missing: nowhere${path.sep}a.json: No such file or directory\n`);
    for (const sources of ["sources/", "./sources", ""]) {
      const dotted = runJsAndStored(["pack", "--show", "show.json", "--mapping", "legs.json", "--sources", sources, "--out", "sources"], inFolder);
      assert.deepEqual(dotted.js, dotted.python, sources);
      assert.equal(dotted.js.err, "error: output-not-empty: sources: the output folder is not empty\n");
    }
    const joinedNames = runJsAndStored(["pack", "--show", "show.json", "--mapping", "legs.json", "--sources", "./nowhere/", "--out", "rel-out"], inFolder);
    assert.deepEqual(joinedNames.js, joinedNames.python);
    assert.equal(joinedNames.js.err, "error: file-missing: ./nowhere/a.json: No such file or directory\n");
    const empty = runJsAndStored(["pack", "--show", "show.json", "--mapping", "legs.json", "--sources", "", "--out", "rel-out"], inFolder);
    assert.deepEqual(empty.js, empty.python);
    assert.equal(empty.js.err, "error: file-missing: a.json: No such file or directory\n");
    assert.equal(fs.existsSync(path.join(at.folder, "rel-out")), false);
  });

  await t.test("a folder that is not empty, and a file, are refused and stay as they were", async () => {
    const makers = {
      "a folder with a file": (out) => {
        fs.mkdirSync(out);
        fs.writeFileSync(path.join(out, "keep.txt"), "kept");
      },
      "a folder with a hidden file": (out) => {
        fs.mkdirSync(out);
        fs.writeFileSync(path.join(out, ".keep"), "kept");
      },
      "a folder with an empty folder": (out) => {
        fs.mkdirSync(path.join(out, "inner"), {recursive: true});
      },
      "a file": (out) => {
        fs.writeFileSync(out, "kept");
      },
      "a folder that holds an earlier pack": (out) => {
        fs.mkdirSync(out);
        for (const name of packed) {
          fs.writeFileSync(path.join(out, name), "old");
        }
      },
    };
    let number = 0;
    for (const [label, make] of Object.entries(makers)) {
      number += 1;
      const results = await both((side) => {
        const out = path.join(at.folder, `${side}-taken-${number}`);
        make(out);
        return out;
      });
      sameResult(results, label);
      for (const side of ["js", "py"]) {
        const {out, result} = results[side];
        assert.equal(result.status, 1, label);
        assert.equal(result.err, `error: output-not-empty: ${out}: the output folder is not empty\n`);
        assert.equal(fs.existsSync(`${out}.part`), false);
      }
      const kept = (out) => (fs.statSync(out).isDirectory() ? filesUnder(out).map((name) => [name, name.endsWith("/") ? "" : fs.readFileSync(path.join(out, name), "utf8")]) : fs.readFileSync(out, "utf8"));
      assert.deepEqual(kept(results.js.out), kept(results.py.out), label);
    }
  });

  await t.test("the output folder is looked at before the sources", async () => {
    const results = await both((side) => {
      const out = path.join(at.folder, `${side}-order`);
      fs.mkdirSync(out);
      fs.writeFileSync(path.join(out, "keep.txt"), "kept");
      return out;
    }, {sources: path.join(at.folder, "no-such-sources")});
    sameResult(results, "a folder that is not empty and a source that is missing");
    assert.equal(results.js.result.err, `error: output-not-empty: ${results.js.out}: the output folder is not empty\n`);
    assert.deepEqual(filesUnder(results.js.out), ["keep.txt"]);
  });

  await t.test("and after the show", async () => {
    const results = await both((side) => {
      const out = path.join(at.folder, `${side}-order-2`);
      fs.mkdirSync(out);
      fs.writeFileSync(path.join(out, "keep.txt"), "kept");
      return out;
    }, {show: path.join(at.folder, "no-such-show.json")});
    sameResult(results, "a folder that is not empty and a show that is missing");
    assert.equal(results.js.result.err.split(": ")[1], "show-missing");
  });

  await t.test("a rejected pack leaves a new output folder unmade, an empty one empty, and no part folder", async () => {
    const more = {sources: path.join(at.folder, "no-such-sources")};
    const fresh = await both((side) => path.join(at.folder, `${side}-unmade`, "out"), more);
    sameResult(fresh, "a new folder");
    const empty = await both((side) => {
      const out = path.join(at.folder, `${side}-still-empty`);
      fs.mkdirSync(out);
      return out;
    }, more);
    sameResult(empty, "an empty folder");
    for (const side of ["js", "py"]) {
      assert.equal(fresh[side].result.status, 1);
      assert.equal(fs.existsSync(path.dirname(fresh[side].out)), false, "the folder above is not made either");
      assert.deepEqual(fs.readdirSync(empty[side].out), []);
      assert.equal(fs.existsSync(`${empty[side].out}.part`), false);
    }
  });

  await t.test("a folder that cannot be made is cannot-write, with the path the system named", async () => {
    const below = await both((side) => {
      fs.writeFileSync(path.join(at.folder, `${side}-file`), "x");
      return path.join(at.folder, `${side}-file`, "out");
    });
    sameResult(below, "a folder below a file");
    assert.equal(below.js.result.status, 1);
    assert.equal(below.js.result.err.split(": ")[1], "cannot-write");
    assert.equal(fs.readFileSync(path.join(at.folder, "js-file"), "utf8"), "x");

    const taken = await both((side) => {
      const out = path.join(at.folder, `${side}-part-taken`);
      fs.mkdirSync(`${out}.part`);
      fs.writeFileSync(path.join(`${out}.part`, "theirs.txt"), "x");
      return out;
    });
    sameResult(taken, "a part folder that is there already");
    assert.equal(taken.js.result.err, `error: cannot-write: ${taken.js.out}.part: File exists\n`);
    assert.equal(fs.existsSync(taken.js.out), false);
    assert.deepEqual(fs.readdirSync(`${taken.js.out}.part`), ["theirs.txt"], "a part folder the tool did not make is not removed");
  });

  await t.test("a folder that may not be written into is cannot-write", {skip: !RIGHTS_HOLD}, async () => {
    const locked = [];
    try {
      const results = await both((side) => {
        const parent = path.join(at.folder, `${side}-locked`);
        fs.mkdirSync(parent);
        forbid(parent, "write");
        locked.push(parent);
        return path.join(parent, "out");
      });
      sameResult(results, "a parent folder without the right to write");
      assert.equal(results.js.result.err, `error: cannot-write: ${results.js.out}.part: Permission denied\n`);
      assert.deepEqual(fs.readdirSync(path.dirname(results.js.out)), []);
    } finally {
      for (const parent of locked) {
        allowAgain(parent);
      }
    }
  });
});

test("pack on the command line", async (t) => {
  const at = bench(t);
  // Each tool builds into folders of its own, named after it.
  const lines = (side) => [
    ["pack"],
    ["pack", "--show", at.show],
    ["pack", "--show", at.show, "--mapping", at.mapping, "--sources", at.sources],
    ["pack", "--show", at.show, "--mapping", at.mapping, "--sources", at.sources, "--out"],
    ["pack", "--show", at.show, "--mapping", at.mapping, "--sources", at.sources, "--out", path.join(at.folder, side, "x1"), "extra"],
    ["pack", "--show", at.show, "--mapping", at.mapping, "--sources", at.sources, "--out", path.join(at.folder, side, "x2"), "--fast"],
    ["pack", "--help"],
    ["pack", `--show=${at.show}`, `--mapping=${at.mapping}`, `--sources=${at.sources}`, `--out=${path.join(at.folder, side, "x3")}`],
    ["pack", "--uncompressed", "--out", path.join(at.folder, side, "x4"), "--sources", at.sources, "--mapping", at.mapping, "--show", at.show],
    ["pack", "--show", "nowhere.json", "--show", at.show, "--mapping", at.mapping, "--sources", at.sources, "--out", path.join(at.folder, side, "x5")],
  ];
  for (let i = 0; i < lines("js").length; i += 1) {
    const argv = lines("js")[i];
    await t.test(`odrig ${argv.map((argument) => argument.replace(at.folder, "<folder>")).join(" ")}`, () => {
      const js = runJs(argv);
      const python = storedRun(lines("py")[i]);
      assert.equal(js.status, python.status, `${js.err} / ${python.err}`);
      if (python.status === 2) {
        assert.match(js.err, /^usage: node converter\/odrig\.js pack/);
        assert.equal(js.out, "");
      } else if (python.status === 0 && python.out !== "") {
        assert.match(js.out, /^usage: node converter\/odrig\.js pack/);
      } else {
        assert.deepEqual(js, python);
      }
    });
  }
  await t.test("the folders that were built, and no other", () => {
    for (const side of ["js", "py"]) {
      assert.deepEqual(fs.readdirSync(path.join(at.folder, side)).sort(), ["x3", "x4", "x5"]);
      assert.equal(read(at.folder, side, "x3", "a.odrg")[5], 1);
      assert.equal(read(at.folder, side, "x4", "a.odrg")[5], 0);
    }
    assert.deepEqual(filesUnder(path.join(at.folder, "js")), filesUnder(path.join(at.folder, "py")));
  });
});
