import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import test from "node:test";
import {pathToFileURL} from "node:url";

import {errors, jsonframes, odrg, odrgx, pack, show} from "../lib/index.js";
import {ROOT, runJs, temporary, utf8} from "./support.js";

const FOLDER = path.join(ROOT, "tests", "vectors", "containers");
const builder = await import(pathToFileURL(path.join(FOLDER, "build.mjs")).href);

function read(...parts) {
  return new Uint8Array(fs.readFileSync(path.join(...parts)));
}

function reasonOf(action) {
  try {
    action();
  } catch (error) {
    if (error instanceof errors.Rejection) {
      return error.reason;
    }
    throw error;
  }
  return null;
}

// The reasons docs/reasons.md lists under a heading of the second level.
function listedReasons(heading) {
  const text = fs.readFileSync(path.join(ROOT, "docs", "reasons.md"), "utf8");
  const section = text.split(`\n## ${heading}\n`)[1].split("\n## ")[0];
  return new Set([...section.matchAll(/^\| `([a-z0-9-]+)` \|/gm)].map((match) => match[1]));
}

function readContainer(data) {
  return odrgx.decodeFrames(data, odrgx.readHeader(data));
}

test("the vectors of containers are what their builder makes", () => {
  const made = builder.vectors();
  const onDisk = new Map();
  for (const folder of ["valid", "invalid"]) {
    for (const name of fs.readdirSync(path.join(FOLDER, folder))) {
      onDisk.set(`${folder}/${name}`, read(FOLDER, folder, name));
    }
  }
  assert.deepEqual([...onDisk.keys()].sort(), [...made.keys()].sort(), "run node tests/vectors/containers/build.mjs");
  for (const [name, data] of made) {
    assert.deepEqual(onDisk.get(name), data, name);
  }
});

test("a valid container of frames decodes to the frames of its ODRG file", () => {
  const names = fs.readdirSync(path.join(FOLDER, "valid")).filter((name) => name.endsWith(".odrgx"));
  assert.ok(names.length >= 3);
  for (const name of names) {
    const data = read(FOLDER, "valid", name);
    const expected = jsonframes.loads(read(FOLDER, "valid", name.replace(/\.odrgx$/, ".json")));
    const decoded = readContainer(data);
    assert.deepEqual([decoded.width, decoded.height], [expected.width, expected.height], name);
    assert.deepEqual(decoded.records, expected.frames, name);
    assert.deepEqual(decoded.records, odrg.decode(odrgx.payloadOf(data)).records, name);
    assert.equal(decoded.header.type, odrgx.TYPES.frames);
    assert.equal(decoded.header.loopMs, expected.frames.reduce((sum, frame) => sum + frame.ms, 0), name);
    assert.equal(decoded.header.payloadSize, data.length - odrgx.HEADER_SIZE);
  }
});

test("an invalid container is refused with the reason of its name", async (t) => {
  const names = fs.readdirSync(path.join(FOLDER, "invalid")).sort();

  await t.test("each one", () => {
    assert.ok(names.length >= 12);
    for (const name of names) {
      assert.equal(reasonOf(() => readContainer(read(FOLDER, "invalid", name))), name.split(".")[0], name);
    }
  });

  await t.test("together they have every reason of a container", () => {
    const named = new Set(names.map((name) => name.split(".")[0]));
    for (const reason of listedReasons("ODRGX files")) {
      assert.ok(named.has(reason), reason);
    }
    for (const reason of named) {
      assert.ok(listedReasons("ODRGX files").has(reason) || listedReasons("ODRG files").has(reason), reason);
    }
  });
});

test("a container is told by its first bytes, not by its name", () => {
  const container = read(FOLDER, "valid", "frames.durations.odrgx");
  const plain = read(ROOT, "tests", "vectors", "valid", "durations.odrg");
  assert.ok(odrgx.isContainer(container));
  assert.ok(!odrgx.isContainer(plain));
  assert.ok(!odrgx.isContainer(container.subarray(0, 3)));
  assert.equal(reasonOf(() => odrgx.readHeader(plain)), "bad-magic");
});

test("encodeFrames writes the ODRG file of the frames into a container", () => {
  const animation = {
    width: 2,
    height: 1,
    frames: [
      {ms: 20, picture: Uint8Array.of(255, 0, 0, 0, 0, 255)},
      {ms: 1000, picture: Uint8Array.of(0, 255, 0, 0, 0, 0)},
    ],
  };
  for (const compressed of [true, false]) {
    const data = odrgx.encodeFrames(animation, {compressed});
    assert.deepEqual(Array.from(data.subarray(0, 8)), [0x4f, 0x44, 0x52, 0x58, 1, 1, 1, 0]);
    assert.deepEqual(odrgx.payloadOf(data), odrg.encode(animation, {compressed}));
    const decoded = readContainer(data);
    assert.deepEqual([decoded.header.width, decoded.header.height, decoded.header.loopMs], [2, 1, 1020]);
    assert.deepEqual(decoded.records, animation.frames);
  }
});

test("a show may name .odrgx files, and pack makes them from JSON frames", async (t) => {
  const mapping = read(ROOT, "mapping", "legs-2.json");
  const frames = (colour) => utf8(JSON.stringify({version: 1, width: 60, height: 6, frames: [{ms: 500, pixels: Array(360).fill(colour)}]}));

  await t.test("the names", () => {
    assert.ok(show.fileNamed("a.odrgx"));
    assert.ok(show.fileNamed("a.odrg"));
    assert.ok(!show.fileNamed("a.odrgy"));
    assert.ok(!show.fileNamed("A.odrgx"));
    const refused = () => show.loads(utf8('{"version":1,"brightness":9,"items":[{"id":1,"file":"a.odrgy"}]}'));
    assert.throws(refused, (error) => error.reason === "show-malformed" && /ending in \.odrg or \.odrgx$/.test(error.detail));
    assert.equal(pack.sourceName("clip.odrgx"), "clip.json");
    assert.equal(pack.sourceName("clip.odrg"), "clip.json");
  });

  await t.test("pack", () => {
    const showFile = utf8(JSON.stringify({version: 1, brightness: 9, items: [{id: 1, file: "red.odrgx"}, {id: 2, file: "blue.odrg"}]}));
    const files = pack.pack({mapping, show: showFile, sources: {"red.json": frames(0xff0000), "blue.json": frames(0x0000ff)}});
    assert.deepEqual([...files.keys()], ["mapping.json", "show.json", "red.odrgx", "blue.odrg"]);
    const red = readContainer(files.get("red.odrgx"));
    assert.equal(red.records[0].picture[0], 255);
    assert.equal(odrgx.isContainer(files.get("blue.odrg")), false);
  });
});

test("the command line", async (t) => {
  const folder = temporary(t);
  const source = path.join(ROOT, "tests", "vectors", "valid", "rgb-modes.json");
  const out = path.join(folder, "out.odrgx");

  await t.test("encode writes a container for a name that ends in .odrgx", () => {
    const done = runJs(["encode", source, out]);
    assert.equal(done.status, 0, done.err);
    const decoded = readContainer(read(out));
    assert.deepEqual(decoded.records, jsonframes.loads(read(source)).frames);
    const plain = path.join(folder, "out.odrg");
    assert.equal(runJs(["encode", source, plain]).status, 0);
    assert.ok(!odrgx.isContainer(read(plain)));
  });

  await t.test("decode reads a container, and an ODRG file whatever its name", () => {
    const back = path.join(folder, "back.json");
    assert.equal(runJs(["decode", out, back]).status, 0);
    assert.deepEqual(jsonframes.loads(read(back)).frames, jsonframes.loads(read(source)).frames);
    const named = path.join(folder, "plain.odrgx");
    fs.copyFileSync(path.join(ROOT, "tests", "vectors", "valid", "rgb-modes.odrg"), named);
    assert.equal(runJs(["decode", named, back]).status, 0);
    assert.deepEqual(jsonframes.loads(read(back)).frames, jsonframes.loads(read(source)).frames);
  });

  await t.test("check says what a container is", () => {
    const done = runJs(["check", out]);
    assert.equal(done.status, 0, done.err);
    assert.match(done.out, /^format: odrgx\ntype: frames\ncanvas: 4x3\nframes: 64\n/);
    const refused = runJs(["check", path.join(FOLDER, "invalid", "loop-mismatch.odrgx")]);
    assert.equal(refused.status, 1);
    assert.match(refused.err, /^error: loop-mismatch: .*loop-mismatch\.odrgx: the header gives a loop of \d+ ms and the payload one of \d+ ms\n$/);
  });
});
