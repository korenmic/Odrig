import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import test, {after} from "node:test";

import {deflate, inflate, jsonframes, odrg} from "../lib/index.js";
import {asStored, generated, hex, numbers, recordsOf, reference, runJs, runPython, storedLength, temporary, utf8} from "./support.js";

const BENCH = "mapping/legs-2.json";
const TARGET = "mapping/legs-20.json";
const HEADER = 16;

// The six bodies the compressor is measured on: the bytes after the header of the
// uncompressed file of a generator's animation, which the encoder writes as the Python tool
// does, with the length of the stream zlib makes of them at level 9, the body of the Python
// tool's compressed file.
const SOURCES = [
  ["Hello world, 60 x 6", {generator: "hello_world", mapping: BENCH}],
  ["DVD bounce, 60 x 6", {generator: "dvd_bounce", mapping: BENCH}],
  ["Dense, 60 x 6, 2 s", {generator: "dense", mapping: BENCH, seconds: 2}],
  ["Hello world, 60 x 60", {generator: "hello_world", mapping: TARGET}],
  ["DVD bounce, 60 x 60", {generator: "dvd_bounce", mapping: TARGET}],
  ["Dense, 60 x 60, 2 s", {generator: "dense", mapping: TARGET, seconds: 2}],
];

let made = null;
let folder = null;

after(() => {
  if (folder !== null) {
    fs.rmSync(folder, {recursive: true, force: true});
  }
});

function bodies() {
  if (made === null) {
    folder = fs.realpathSync(fs.mkdtempSync(path.join(os.tmpdir(), "odrig-converter-")));
    const files = reference("encode", [], SOURCES.map(([, source]) => source));
    made = SOURCES.map(([name, {generator, mapping, seconds}], i) => {
      const animation = jsonframes.loads(new Uint8Array(fs.readFileSync(generated(folder, generator, mapping, seconds ?? null))));
      const plain = odrg.encode(animation, {compressed: false});
      assert.deepEqual(asStored(plain, files[i].uncompressed), files[i].uncompressed, `${name}: the uncompressed file is the Python tool's`);
      const compressed = asStored(odrg.encode(animation), files[i].compressed);
      return {name, body: plain.subarray(HEADER), zlib: storedLength(files[i].compressed) - HEADER, same: JSON.stringify(compressed) === JSON.stringify(files[i].compressed)};
    });
  }
  return made;
}

// The inputs of Requirement 8 criterion 6, and more from seeds.
function inputs() {
  const from = numbers(8086);
  const noise = from.bytes(200000);
  const block = from.bytes(32768);
  const far = new Uint8Array(3 * 32768 + 500);
  far.set(block, 0);
  far.set(block, 32768);
  far.set(block, 65536);
  far.set(block.subarray(0, 500), 98304);
  // The same at the farthest distance at which the compressor looks for a match.
  const near = new Uint8Array(3 * 32506);
  near.set(block.subarray(0, 32506), 0);
  near.set(block.subarray(0, 32506), 32506);
  near.set(block.subarray(0, 32506), 65012);
  const text = utf8("the quick brown fox jumps over the lazy dog. ".repeat(40));
  const repeating = new Uint8Array(120000);
  for (let at = 0; at < repeating.length; at += 1) {
    repeating[at] = text[at % text.length];
  }
  // A piece of 40 bytes without a pattern, twice, the second time each of these distances
  // after the first.
  [1, 2, 3, 258, 259, 4096, 4097, 32505, 32506, 32507, 32767, 32768].forEach((distance, i) => {
    const at = 40000 + 4800 * i;
    repeating.set(noise.subarray(distance, distance + 40), at);
    repeating.set(noise.subarray(distance, distance + 40), at - distance);
  });
  // Symbols that appear 1, 1, 2, 3, 5, 8, ... times, which asks for codes longer than the
  // format allows.
  const skewed = [];
  let a = 1;
  let b = 1;
  for (let symbol = 0; symbol < 22 && skewed.length + a <= 16000; symbol += 1) {
    for (let i = 0; i < a; i += 1) {
      skewed.push(symbol * 11 + 3);
    }
    [a, b] = [b, a + b];
  }
  for (let i = skewed.length - 1; i > 0; i -= 1) {
    const j = from.below(i + 1);
    [skewed[i], skewed[j]] = [skewed[j], skewed[i]];
  }
  const list = [
    ["nothing", new Uint8Array(0)],
    ["one byte", Uint8Array.of(0x5a)],
    ["two bytes", Uint8Array.of(0, 0)],
    ["three equal bytes", Uint8Array.of(7, 7, 7)],
    ["70,000 equal bytes", new Uint8Array(70000).fill(0xa5)],
    ["200,000 bytes without a pattern", noise],
    ["a block that comes back twice, 32,768 bytes later", far],
    ["a block that comes back twice, 32,506 bytes later", near],
    ["text that repeats, with pieces at distances up to 32,768", repeating],
    ["symbols with the counts of Fibonacci", Uint8Array.from(skewed)],
    ["65,535 bytes without a pattern", noise.subarray(0, 65535)],
    ["65,536 bytes without a pattern", noise.subarray(0, 65536)],
    ["16,383 different symbols in a row", noise.subarray(1000, 1000 + 16383)],
    ["16,384 bytes without a pattern", noise.subarray(1000, 1000 + 16384)],
  ];
  for (let seed = 1; seed <= 150; seed += 1) {
    const local = numbers(9000 + seed);
    const length = local.pick([0, 1, 2, 3, 4, 5, 9, 17, 100, 258, 259, 600, 3000, 9000]) + local.below(7);
    const symbols = local.pick([1, 2, 3, 4, 16, 64, 256]);
    const runs = local.below(3) === 0;
    const bytes = new Uint8Array(length);
    for (let at = 0; at < length; at += 1) {
      bytes[at] = runs && at > 0 && local.below(4) !== 0 ? bytes[at - 1] : (local.below(symbols) * 37) & 0xff;
    }
    if (length > 50 && local.below(2) === 0) {
      const from2 = local.below(length - 30);
      bytes.copyWithin(local.below(length - 30), from2, from2 + 30);
    }
    list.push([`input ${seed} from a seed, ${length} bytes of ${symbols} symbols`, bytes]);
  }
  return list;
}

test("every stream of the compressor is a stream zlib reads", async (t) => {
  const list = [...inputs(), ...bodies().map(({name, body}) => [`the body of ${name}`, body])];
  const streams = list.map(([, bytes]) => deflate.deflateRaw(bytes));

  await t.test("zlib inflates each to its input, with nothing left over", () => {
    const theirs = reference("inflate", [], streams.map(hex));
    list.forEach(([label, bytes], i) => {
      assert.equal(theirs[i].reason, undefined, label);
      assert.equal(theirs[i].left, 0, label);
      assert.deepEqual(asStored(bytes, theirs[i].data), theirs[i].data, label);
    });
  });

  await t.test("the decoder of the library does the same", () => {
    list.forEach(([label, bytes], i) => {
      const {data, used} = inflate.inflateRaw(streams[i]);
      assert.equal(used, streams[i].length, label);
      assert.ok(Buffer.from(data).equals(Buffer.from(bytes)), label);
    });
  });

  await t.test("a second run gives the same bytes", () => {
    list.forEach(([label, bytes], i) => {
      assert.ok(Buffer.from(deflate.deflateRaw(bytes)).equals(Buffer.from(streams[i])), label);
      assert.ok(Buffer.from(deflate.deflateRaw(bytes.slice())).equals(Buffer.from(streams[i])), label);
    });
  });

  await t.test("the stream is a Uint8Array of its own, and the input is as it was", () => {
    const input = Uint8Array.of(1, 2, 3, 1, 2, 3, 1, 2, 3);
    const stream = deflate.deflateRaw(input);
    assert.ok(stream instanceof Uint8Array);
    assert.deepEqual([...input], [1, 2, 3, 1, 2, 3, 1, 2, 3]);
    assert.deepEqual([...deflate.deflateRaw(new Uint8Array(0))], [0x03, 0x00]);
  });

  await t.test("the stream is never much larger than its input, and much smaller where bytes repeat", () => {
    list.forEach(([label, bytes], i) => {
      assert.ok(streams[i].length <= bytes.length + 5 * (1 + Math.floor(bytes.length / 16383)) + 2, label);
    });
    const size = (name) => streams[list.findIndex(([label]) => label === name)].length;
    assert.ok(size("70,000 equal bytes") < 200);
    assert.ok(size("a block that comes back twice, 32,506 bytes later") < 34000);
    assert.ok(size("a block that comes back twice, 32,768 bytes later") > 98000);
    assert.ok(size("200,000 bytes without a pattern") > 200000);
  });

  await t.test("the three forms of a block are all among the streams", () => {
    const kinds = new Set(streams.map((stream) => (stream[0] >> 1) & 3));
    assert.deepEqual([...kinds].sort(), [0, 1, 2]);
  });
});

test("the stream of each of the six bodies is at most 5 percent larger than zlib's at level 9", async (t) => {
  for (const {name, body, zlib, same} of bodies()) {
    await t.test(name, (inner) => {
      const ours = deflate.deflateRaw(body);
      inner.diagnostic(`${name}: ${body.length} bytes; zlib at level 9 ${zlib}; deflateRaw ${ours.length}, ${same ? "the same bytes" : "other bytes"}`);
      assert.ok(20 * ours.length <= 21 * zlib, `${ours.length} bytes against zlib's ${zlib}`);
      assert.ok(ours.length < body.length);
    });
  }
});

test("compressing a body as long as that of a dense 60 x 60 clip of 10 seconds takes under 20 seconds", (t) => {
  // The body of the clip of 2 seconds five times over. Its repeats lie farther apart than
  // the compressor looks back for a match, so it has the work of five such bodies.
  const {name, body, zlib} = bodies()[5];
  assert.ok(body.length > 32768);
  const long = new Uint8Array(5 * body.length);
  for (let i = 0; i < 5; i += 1) {
    long.set(body, i * body.length);
  }
  assert.ok(long.length > 1400000, `${long.length} bytes`);
  const started = process.hrtime.bigint();
  const ours = deflate.deflateRaw(long);
  const seconds = Number(process.hrtime.bigint() - started) / 1e9;
  t.diagnostic(`${name}, five times: ${long.length} bytes; zlib at level 9 ${5 * zlib} for five bodies; deflateRaw ${ours.length}, in ${seconds.toFixed(3)} s`);
  assert.ok(seconds < 20, `it took ${seconds.toFixed(2)} s`);
  assert.ok(20 * ours.length <= 21 * 5 * zlib);
});

test("whole files, through the command line of both tools", async (t) => {
  const folder = temporary(t);
  const sources = [
    ["Hello world on the bench canvas", generated(folder, "hello_world", BENCH)],
    ["DVD bounce on the bench canvas", generated(folder, "dvd_bounce", BENCH)],
    ["Hello world on 60 x 60", generated(folder, "hello_world", TARGET)],
    ["DVD bounce on 60 x 60", generated(folder, "dvd_bounce", TARGET)],
    ["a dense clip of 2 seconds on 60 x 60", generated(folder, "dense", TARGET, 2)],
    ["the source of the vector encoded.pal", "tests/vectors/valid/encoded.pal.json"],
    ["the source of the vector encoded.rgb", "tests/vectors/valid/encoded.rgb.json"],
  ];
  const quiet = {status: 0, out: "", err: ""};
  for (const [label, source] of sources) {
    await t.test(label, (inner) => {
      const ours = path.join(folder, "ours.odrg");
      const plain = path.join(folder, "plain.odrg");
      const theirs = path.join(folder, "theirs.odrg");
      const theirPlain = path.join(folder, "their-plain.odrg");
      assert.deepEqual(runJs(["encode", source, ours]), quiet);
      assert.deepEqual(runJs(["encode", source, plain, "--uncompressed"]), quiet);
      assert.deepEqual(runPython(["encode", source, theirs]), quiet);
      assert.deepEqual(runPython(["encode", source, theirPlain, "--uncompressed"]), quiet);
      const files = [ours, plain, theirs, theirPlain].map((file) => new Uint8Array(fs.readFileSync(file)));
      const [compressed, uncompressed, reference9, referencePlain] = files;
      assert.equal(compressed[5], 1, "the flags byte says compressed");
      assert.equal(uncompressed[5], 0);
      assert.ok(Buffer.from(uncompressed).equals(Buffer.from(referencePlain)), "the uncompressed files are identical");

      // The reference decoder gives the same frame records for the compressed file as for
      // the uncompressed one, and so does the decoder of the library.
      const decoded = reference("decode", [], files.map(hex));
      assert.equal(decoded[0].compressed, true);
      assert.equal(decoded[1].compressed, false);
      assert.ok(decoded[1].records.length > 0);
      assert.deepEqual(decoded[0].records, decoded[1].records);
      assert.deepEqual(decoded[2].records, decoded[1].records);
      assert.equal(decoded[0].palette, decoded[1].palette);
      assert.deepEqual(recordsOf(odrg.decode(compressed)), decoded[1].records);
      assert.deepEqual(recordsOf(odrg.decode(uncompressed)), decoded[1].records);

      const bytes = Buffer.from(compressed).equals(Buffer.from(reference9)) ? "the same bytes" : "other bytes";
      inner.diagnostic(
        `${label}: uncompressed ${uncompressed.length} bytes in both tools; compressed ${compressed.length} bytes,` +
          ` the Python tool's ${reference9.length}, ${bytes}`,
      );
      assert.ok(20 * compressed.length <= 21 * reference9.length, `${compressed.length} bytes against the Python tool's ${reference9.length}`);
    });
  }

  await t.test("a source that compression makes larger is compressed anyway", () => {
    const source = path.join(folder, "noise.json");
    const from = numbers(31);
    fs.writeFileSync(source, jsonframes.dumps({width: 20, height: 20, frames: [{ms: 20, picture: from.bytes(1200)}]}));
    const ours = path.join(folder, "noise.odrg");
    const plain = path.join(folder, "noise-plain.odrg");
    assert.deepEqual(runJs(["encode", source, ours]), quiet);
    assert.deepEqual(runJs(["encode", source, plain, "--uncompressed"]), quiet);
    const compressed = fs.readFileSync(ours);
    assert.equal(compressed[5], 1);
    assert.ok(compressed.length > fs.readFileSync(plain).length);
    assert.deepEqual(recordsOf(odrg.decode(new Uint8Array(compressed))), recordsOf(odrg.decode(new Uint8Array(fs.readFileSync(plain)))));
  });
});
