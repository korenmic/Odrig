import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import test from "node:test";

import {jsonframes} from "../lib/index.js";
import {ROOT, hex, libraryJsonCheck, numbers, pythonChecks, reference, sameVerdict, utf8} from "./support.js";

// A JSON frames file of 2 x 1 with two frames, with its parts given as texts.
function file({
  version = '"version": 1, ',
  width = '"width": 2, ',
  height = '"height": 1, ',
  frames = null,
  first = '{"ms": 20, "pixels": [0, 16777215]}',
  second = '{"ms": 40, "pixels": [255, 65280]}',
  extra = "",
} = {}) {
  return `{${version}${width}${height}"frames": ${frames === null ? `[${first}, ${second}]` : frames}${extra}}`;
}

// Every rule of docs/format.md, "JSON frames", broken once, in the order of the checks.
const BROKEN = [
  ["the top level is an array", "[]"],
  ["the top level is a number", "1"],
  ["the top level is a string", '"version"'],
  ["the top level is null", "null"],
  ["no version", file({version: ""})],
  ["no version and an unknown member", '{"vers": 1}'],
  ["an empty object", "{}"],
  ["a version with a fraction", file({version: '"version": 1.0, '})],
  ["a version that is a string", file({version: '"version": "1", '})],
  ["a version that is true", file({version: '"version": true, '})],
  ["a version that is null", file({version: '"version": null, '})],
  ["a version that is an array", file({version: '"version": [1], '})],
  ["version 2", file({version: '"version": 2, '})],
  ["version 0", file({version: '"version": 0, '})],
  ["version -1", file({version: '"version": -1, '})],
  ["version 2 in a file with nothing else", '{"version": 2}'],
  ["version 2 before a member that is unknown", '{"version": 2, "colour": 1}'],
  ["no width", file({width: ""})],
  ["no height", file({height: ""})],
  ["no frames", '{"version": 1, "width": 2, "height": 1}'],
  ["no width and no height", file({width: "", height: ""})],
  ["an unknown member", file({extra: ', "fps": 50'})],
  ["an unknown member at the front", `{"fps": 50, ${file().slice(1)}`],
  ["a missing member and an unknown one", file({height: "", extra: ', "fps": 50'})],
  ["a member with a capital letter", file({width: '"Width": 2, '})],
  ["a width with a fraction", file({width: '"width": 2.0, '})],
  ["a width that is a string", file({width: '"width": "2", '})],
  ["a width of 0", file({width: '"width": 0, '})],
  ["a negative width", file({width: '"width": -2, '})],
  ["a width of 0 and a height that is a string", file({width: '"width": 0, ', height: '"height": "1", '})],
  ["a height that is false", file({height: '"height": false, '})],
  ["a height of 0", file({height: '"height": 0, '})],
  ["a negative height", file({height: '"height": -1, '})],
  ["frames that is an object", file({frames: "{}"})],
  ["frames that is a number", file({frames: "1"})],
  ["frames that is null", file({frames: "null"})],
  ["frames that is empty", file({frames: "[]"})],
  ["a height of 0 and frames that is empty", file({height: '"height": 0, ', frames: "[]"})],
  ["a frame that is a number", file({first: "20"})],
  ["a frame that is an array", file({first: "[20, [0, 0]]"})],
  ["a frame that is null", file({second: "null"})],
  ["a frame without ms", file({first: '{"pixels": [0, 0]}'})],
  ["a frame without pixels", file({second: '{"ms": 40}'})],
  ["an empty frame", file({first: "{}"})],
  ["a frame with an unknown member", file({first: '{"ms": 20, "pixels": [0, 0], "name": "a"}'})],
  ["a frame without ms and with an unknown member", file({first: '{"pixels": [0, 0], "name": "a"}'})],
  ["ms with a fraction", file({first: '{"ms": 20.5, "pixels": [0, 0]}'})],
  ["ms that is a string", file({first: '{"ms": "20", "pixels": [0, 0]}'})],
  ["ms of 0", file({first: '{"ms": 0, "pixels": [0, 0]}'})],
  ["a negative ms", file({second: '{"ms": -20, "pixels": [0, 0]}'})],
  ["ms of 0 and pixels that is no array", file({first: '{"ms": 0, "pixels": 7}'})],
  ["pixels that is a number", file({first: '{"ms": 20, "pixels": 7}'})],
  ["pixels that is an object", file({second: '{"ms": 20, "pixels": {}}'})],
  ["pixels that is a string", file({second: '{"ms": 20, "pixels": "0, 0"}'})],
  ["one pixel too few", file({first: '{"ms": 20, "pixels": [0]}'})],
  ["one pixel too many", file({second: '{"ms": 20, "pixels": [0, 0, 0]}'})],
  ["no pixels", file({first: '{"ms": 20, "pixels": []}'})],
  ["too few pixels, of which one is no colour", file({first: '{"ms": 20, "pixels": [-1]}'})],
  ["a pixel with a fraction", file({first: '{"ms": 20, "pixels": [0, 1.5]}'})],
  ["a pixel that is a string", file({first: '{"ms": 20, "pixels": ["0", 0]}'})],
  ["a pixel that is true", file({first: '{"ms": 20, "pixels": [0, true]}'})],
  ["a pixel that is null", file({second: '{"ms": 20, "pixels": [null, 0]}'})],
  ["a pixel that is an array", file({second: '{"ms": 20, "pixels": [[0, 0, 0], 0]}'})],
  ["a negative pixel", file({first: '{"ms": 20, "pixels": [0, -1]}'})],
  ["a pixel above white", file({second: '{"ms": 20, "pixels": [16777216, 0]}'})],
  ["a pixel above white before one that is no integer", file({first: '{"ms": 20, "pixels": [16777216, "x"]}'})],
  ["a pixel that is no integer before one above white", file({first: '{"ms": 20, "pixels": ["x", 16777216]}'})],
  ["a negative pixel after one that is no integer", file({first: '{"ms": 20, "pixels": [0.5, -1]}'})],
  ["a mistake in the second frame and a later one in the first", file({first: '{"ms": 20, "pixels": [0, -1]}', second: "7"})],
  ["a mistake in the second frame only", file({second: '{"ms": 0, "pixels": [0, 0]}'})],
];

// Files that are as the format says.
const WHOLE = [
  ["two frames", file()],
  ["the members in another order", '{"frames": [{"pixels": [1, 2], "ms": 5}], "height": 1, "width": 2, "version": 1}'],
  ["one pixel", '{"version": 1, "width": 1, "height": 1, "frames": [{"ms": 1, "pixels": [16777215]}]}'],
  ["two frames with the same picture", file({second: '{"ms": 40, "pixels": [0, 16777215]}'})],
  ["a frame of a very long time", file({first: '{"ms": 123456789012345678901234567890, "pixels": [0, 0]}'})],
];

test("every rule of the format, broken once, gets the error line of the Python tool", async (t) => {
  const theirs = pythonChecks("json", BROKEN.map(([, text]) => utf8(text)));
  const reasons = new Set();
  for (let i = 0; i < BROKEN.length; i += 1) {
    const [label, text] = BROKEN[i];
    await t.test(label, () => {
      const ours = libraryJsonCheck(utf8(text));
      assert.equal(theirs[i].status, 1, label);
      assert.deepEqual(ours, theirs[i], label);
      reasons.add(ours.err.split(": ")[1]);
    });
  }
  await t.test("every reason of a JSON frames file is among them", () => {
    assert.deepEqual([...reasons].sort(), [
      "bad-json", "bad-pixel-count", "bad-type", "bad-version", "missing-member", "no-frames", "out-of-range", "unknown-member",
    ]);
  });
});

test("a file that is as the format says is read as the Python tool reads it", async (t) => {
  const theirs = pythonChecks("json", WHOLE.map(([, text]) => utf8(text)));
  for (let i = 0; i < WHOLE.length; i += 1) {
    const [label, text] = WHOLE[i];
    await t.test(label, () => {
      assert.equal(theirs[i].status, 0, label);
      sameVerdict(assert, libraryJsonCheck(utf8(text)), theirs[i], label);
    });
  }

  await t.test("the frames are kept as the file lists them", () => {
    const animation = jsonframes.loads(utf8(file({second: '{"ms": 40, "pixels": [0, 16777215]}'})));
    assert.equal(animation.width, 2);
    assert.equal(animation.height, 1);
    assert.equal(animation.frames.length, 2);
    assert.deepEqual(animation.frames.map((frame) => frame.ms), [20, 40]);
    assert.deepEqual([...animation.frames[0].picture], [0, 0, 0, 255, 255, 255]);
    assert.ok(animation.frames[0].picture instanceof Uint8Array);
  });

  await t.test("a colour is red * 65536 + green * 256 + blue", () => {
    const animation = jsonframes.loads(utf8(file({first: '{"ms": 20, "pixels": [1193046, 255]}'})));
    assert.deepEqual([...animation.frames[0].picture], [0x12, 0x34, 0x56, 0, 0, 0xff]);
  });
});

function tracked(...parts) {
  return new Uint8Array(fs.readFileSync(path.join(ROOT, ...parts)));
}

// An animation made from a seed: a small canvas, a few colours or many, some frames with
// the picture of the frame before, and now and then a very long frame.
function animationFrom(seed) {
  const from = numbers(seed);
  const width = from.between(1, 7);
  const height = from.between(1, 5);
  const palette = from.below(3) === 0 ? null : Array.from({length: from.between(1, 5)}, () => from.bytes(3));
  const frames = [];
  const count = from.between(1, 6);
  for (let i = 0; i < count; i += 1) {
    let picture;
    if (i > 0 && from.below(3) === 0) {
      picture = frames[i - 1].picture.slice();
    } else if (palette === null) {
      picture = from.bytes(3 * width * height);
    } else {
      picture = new Uint8Array(3 * width * height);
      for (let pixel = 0; pixel < width * height; pixel += 1) {
        picture.set(from.pick(palette), 3 * pixel);
      }
    }
    const ms = from.below(8) === 0 ? 2n ** 60n + BigInt(from.below(1000)) : from.between(1, 70000);
    frames.push({ms, picture});
  }
  return {width, height, frames};
}

function forPython(animation, merge) {
  return {
    width: animation.width,
    height: animation.height,
    merge,
    frames: animation.frames.map((frame) => [String(frame.ms), hex(frame.picture)]),
  };
}

test("dumps writes the bytes of the Python tool", async (t) => {
  await t.test("for the tracked sources", () => {
    for (const name of ["hello.json", "dvd.json"]) {
      const bytes = tracked("animations", name);
      assert.ok(Buffer.from(jsonframes.dumps(jsonframes.loads(bytes))).equals(Buffer.from(bytes)), name);
    }
  });

  await t.test("for the frames of the test vectors, one frame for each record", () => {
    const folder = path.join(ROOT, "tests", "vectors", "valid");
    const names = fs.readdirSync(folder).filter((name) => name.endsWith(".json")).sort();
    assert.ok(names.length >= 20);
    for (const name of names) {
      const bytes = tracked("tests", "vectors", "valid", name);
      const written = jsonframes.dumps(jsonframes.loads(bytes), {merge: false});
      assert.ok(Buffer.from(written).equals(Buffer.from(bytes)), name);
    }
  });

  await t.test("for 120 animations from seeds, merged and as given", () => {
    const animations = Array.from({length: 120}, (unused, seed) => animationFrom(seed + 1));
    const asked = [...animations.map((animation) => forPython(animation, true)), ...animations.map((animation) => forPython(animation, false))];
    const theirs = reference("dumps", [], asked);
    let merges = 0;
    animations.forEach((animation, i) => {
      const merged = jsonframes.dumps(animation);
      const given = jsonframes.dumps(animation, {merge: false});
      assert.equal(hex(merged), theirs[i], `seed ${i + 1}, merged`);
      assert.equal(hex(given), theirs[animations.length + i], `seed ${i + 1}, as given`);
      merges += hex(merged) === hex(given) ? 0 : 1;
    });
    assert.ok(merges >= 20, `${merges} of the animations have frames to merge`);
  });

  await t.test("what it wrote is read back as the merged frames", () => {
    for (let seed = 1; seed <= 40; seed += 1) {
      const animation = animationFrom(seed);
      const back = jsonframes.loads(jsonframes.dumps(animation));
      const merged = jsonframes.merged(animation.frames);
      assert.equal(back.width, animation.width);
      assert.equal(back.height, animation.height);
      assert.deepEqual(back.frames.map((frame) => String(frame.ms)), merged.map((frame) => String(frame.ms)));
      assert.deepEqual(back.frames.map((frame) => hex(frame.picture)), merged.map((frame) => hex(frame.picture)));
    }
  });

  await t.test("the layout", () => {
    const animation = {
      width: 2,
      height: 1,
      frames: [
        {ms: 20, picture: Uint8Array.of(0, 0, 0, 255, 255, 255)},
        {ms: 20, picture: Uint8Array.of(0, 0, 0, 255, 255, 255)},
        {ms: 5, picture: Uint8Array.of(1, 2, 3, 0, 0, 9)},
      ],
    };
    assert.equal(
      Buffer.from(jsonframes.dumps(animation)).toString("utf8"),
      '{\n  "version": 1,\n  "width": 2,\n  "height": 1,\n  "frames": [\n' +
        '    {"ms": 40, "pixels": [0, 16777215]},\n    {"ms": 5, "pixels": [66051, 9]}\n  ]\n}\n',
    );
    assert.equal(
      Buffer.from(jsonframes.dumps(animation, {merge: false})).toString("utf8"),
      '{\n  "version": 1,\n  "width": 2,\n  "height": 1,\n  "frames": [\n' +
        '    {"ms": 20, "pixels": [0, 16777215]},\n    {"ms": 20, "pixels": [0, 16777215]},\n' +
        '    {"ms": 5, "pixels": [66051, 9]}\n  ]\n}\n',
    );
  });

  await t.test("an animation that is none is a mistake of the program, not a rejection", () => {
    const picture = Uint8Array.of(0, 0, 0);
    for (const animation of [
      {width: 0, height: 1, frames: [{ms: 1, picture}]},
      {width: 1, height: 0, frames: [{ms: 1, picture}]},
      {width: 1, height: 1, frames: []},
      {width: 1, height: 1, frames: [{ms: 0, picture}]},
      {width: 1, height: 1, frames: [{ms: 1, picture: Uint8Array.of(0, 0)}]},
      {width: 2, height: 1, frames: [{ms: 1, picture}]},
    ]) {
      assert.throws(() => jsonframes.dumps(animation), RangeError);
    }
  });
});

test("merged, colours and colourCount", async (t) => {
  const a = Uint8Array.of(1, 2, 3, 4, 5, 6);
  const b = Uint8Array.of(1, 2, 3, 4, 5, 7);

  await t.test("merged joins neighbours with the same picture and adds their times", () => {
    const frames = [{ms: 1, picture: a}, {ms: 2, picture: a.slice()}, {ms: 3, picture: b}, {ms: 4, picture: a}, {ms: 5, picture: a}];
    const result = jsonframes.merged(frames);
    assert.deepEqual(result.map((frame) => frame.ms), [3, 3, 9]);
    assert.deepEqual(result.map((frame) => hex(frame.picture)), [hex(a), hex(b), hex(a)]);
    assert.equal(frames.length, 5);
    assert.equal(frames[0].ms, 1);
  });

  await t.test("merged adds times beyond 2 to the power 53 without losing a digit", () => {
    const frames = [{ms: 9007199254740991, picture: a}, {ms: 2, picture: a}, {ms: 10n ** 30n, picture: a}];
    assert.deepEqual(jsonframes.merged(frames).map((frame) => frame.ms), [10n ** 30n + 9007199254740993n]);
  });

  await t.test("colours gives one whole number for each pixel", () => {
    assert.deepEqual(jsonframes.colours(Uint8Array.of(0, 0, 0, 255, 255, 255, 0x12, 0x34, 0x56)), [0, 16777215, 0x123456]);
    assert.deepEqual(jsonframes.colours(new Uint8Array(0)), []);
  });

  await t.test("colourCount counts the different colours of all the frames", () => {
    assert.equal(jsonframes.colourCount([{ms: 1, picture: a}]), 2);
    assert.equal(jsonframes.colourCount([{ms: 1, picture: a}, {ms: 1, picture: b}, {ms: 1, picture: a}]), 3);
    assert.equal(jsonframes.colourCount([{ms: 1, picture: Uint8Array.of(0, 0, 0, 0, 0, 0, 255, 255, 255, 255, 255, 255)}]), 2);
  });

  await t.test("same compares the bytes of two pictures", () => {
    assert.equal(jsonframes.same(a, a.slice()), true);
    assert.equal(jsonframes.same(a, b), false);
    assert.equal(jsonframes.same(a, a.subarray(0, 3)), false);
  });
});

test("a file of 20 MB is read in under 10 seconds", () => {
  const from = numbers(2026);
  const width = 60;
  const height = 60;
  const frames = [];
  for (let i = 0; i < 600; i += 1) {
    frames.push({ms: 20, picture: from.bytes(3 * width * height)});
  }
  const bytes = jsonframes.dumps({width, height, frames});
  assert.ok(bytes.length >= 20_000_000, `the file has ${bytes.length} bytes`);
  const started = process.hrtime.bigint();
  const animation = jsonframes.loads(bytes);
  const seconds = Number(process.hrtime.bigint() - started) / 1e9;
  assert.ok(seconds < 10, `reading took ${seconds.toFixed(2)} s`);
  assert.equal(animation.frames.length, 600);
  assert.equal(hex(animation.frames[599].picture), hex(frames[599].picture));
  const again = jsonframes.dumps(animation);
  assert.ok(Buffer.from(again).equals(Buffer.from(bytes)));
});
