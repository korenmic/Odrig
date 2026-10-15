import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import test from "node:test";

import {errors, inflate} from "../lib/index.js";
import {ROOT, asStored, hex, numbers, storedAnswer, unhex, utf8} from "./support.js";

// What the library says of a stream, in the form of zlib's stored verdicts.
function verdict(stream) {
  try {
    const {data, used} = inflate.inflateRaw(stream);
    return {data: hex(data), left: stream.length - used};
  } catch (error) {
    if (!(error instanceof errors.Rejection)) {
      throw error;
    }
    return {reason: error.reason};
  }
}

// A verdict of the library in the form of zlib's: its output as zlib's verdict has it,
// whole or as a digest.
function asTheirs(ours, theirs) {
  return "data" in ours && "data" in theirs ? {...ours, data: asStored(ours.data, theirs.data)} : ours;
}

function sameVerdicts(streams, labels) {
  const theirs = storedAnswer("inflate", [], streams.map(hex));
  const counts = {whole: 0, "bad-deflate": 0, truncated: 0};
  streams.forEach((stream, i) => {
    assert.deepEqual(asTheirs(verdict(stream), theirs[i]), theirs[i], `${labels(i)}: ${hex(stream).slice(0, 200)}`);
    counts[theirs[i].reason ?? "whole"] += 1;
  });
  return counts;
}

// The inputs the streams are made of.
function inputs() {
  const from = numbers(1951);
  const text = utf8("Hello world, hello strips, hello world of sixty by sixty. ".repeat(12));
  const noise = from.bytes(300);
  const block = from.bytes(32768);
  const far = new Uint8Array(70000);
  far.set(block, 0);
  far.set(block, 32768);
  far.set(block.subarray(0, 70000 - 65536), 65536);
  const steps = new Uint8Array(4000);
  for (let i = 0; i < steps.length; i += 1) {
    steps[i] = (i >> 4) & 0xff;
  }
  const vector = new Uint8Array(fs.readFileSync(path.join(ROOT, "tests", "vectors", "valid", "rgb-modes.odrg"))).subarray(16);
  return {
    nothing: new Uint8Array(0),
    "one byte": Uint8Array.of(0x41),
    "three bytes": Uint8Array.of(1, 2, 3),
    text,
    noise,
    zeros: new Uint8Array(2000),
    steps,
    "the body of a vector": vector,
    "a block that comes back 32,768 bytes later": far,
  };
}

// Every stream zlib makes of the inputs: each level, and each strategy at level 6.
function zlibStreams() {
  const made = inputs();
  const asked = [];
  for (const [name, data] of Object.entries(made)) {
    for (let level = 0; level <= 9; level += 1) {
      asked.push({name: `${name}, level ${level}`, data, level, strategy: "default"});
    }
    for (const strategy of ["fixed", "huffman", "rle", "filtered"]) {
      asked.push({name: `${name}, ${strategy}`, data, level: 6, strategy});
    }
  }
  const streams = storedAnswer("deflate", [], asked.map(({data, level, strategy}) => ({data: hex(data), level, strategy})));
  return asked.map((entry, i) => ({...entry, stream: unhex(streams[i])}));
}

// Bits of a stream as DEFLATE packs them: the first bit of a byte is its lowest.
function writer() {
  const bytes = [];
  let filled = 8;
  const bit = (value) => {
    if (filled === 8) {
      bytes.push(0);
      filled = 0;
    }
    bytes[bytes.length - 1] |= value << filled;
    filled += 1;
  };
  return {
    // A number, its lowest bit first.
    number(value, count) {
      for (let i = 0; i < count; i += 1) {
        bit((value >> i) & 1);
      }
      return this;
    },
    // A Huffman code, its highest bit first.
    code(value, count) {
      for (let i = count - 1; i >= 0; i -= 1) {
        bit((value >> i) & 1);
      }
      return this;
    },
    bytes: () => Uint8Array.from(bytes),
  };
}

// Streams with one defect each, written out by hand.
function broken() {
  const dynamic = (lengthCodes, distanceCodes, listed) => writer().number(1, 1).number(2, 2).number(lengthCodes - 257, 5).number(distanceCodes - 1, 5).number(listed - 4, 4);
  const fixed = () => writer().number(1, 1).number(1, 2);
  return [
    ["a block of kind 3", writer().number(1, 1).number(3, 2).bytes()],
    ["a block of kind 3 that is not the last", writer().number(0, 1).number(3, 2).bytes()],
    ["a stored block whose lengths do not agree", Uint8Array.of(0x01, 0x05, 0x00, 0x00, 0x00, 1, 2, 3, 4, 5)],
    ["a stored block cut inside its lengths", Uint8Array.of(0x01, 0x05, 0x00, 0xfa)],
    ["a stored block cut inside its bytes", Uint8Array.of(0x01, 0x05, 0x00, 0xfa, 0xff, 1, 2)],
    ["a stored block of no bytes", Uint8Array.of(0x01, 0x00, 0x00, 0xff, 0xff)],
    ["a stored block of no bytes and a byte after it", Uint8Array.of(0x01, 0x00, 0x00, 0xff, 0xff, 0x00)],
    ["a fixed block that is only its end", fixed().code(0, 7).bytes()],
    ["a fixed block with a distance before the start", fixed().code(1, 7).code(0, 5).bytes()],
    ["a fixed block with a distance of one too far", fixed().code(0x30 + 65, 8).code(1, 7).code(1, 5).code(0, 7).bytes()],
    ["a fixed block with the length symbol 286", fixed().code(0xc0 + 6, 8).code(0, 5).bytes()],
    ["a fixed block with the length symbol 287", fixed().code(0xc0 + 7, 8).code(0, 5).bytes()],
    ["a fixed block with the distance symbol 30", fixed().code(0x30 + 65, 8).code(1, 7).code(30, 5).bytes()],
    ["a fixed block with the distance symbol 31", fixed().code(0x30 + 65, 8).code(1, 7).code(31, 5).bytes()],
    ["a fixed block cut inside a length's extra bits", fixed().code(0x30 + 65, 8).code(0x30 + 65, 8).code(9 + 0, 7).bytes().subarray(0, 3)],
    ["a dynamic block with 287 length codes", dynamic(287, 1, 4).number(0, 12).bytes()],
    ["a dynamic block with 31 distance codes", dynamic(257, 31, 4).number(0, 12).bytes()],
    ["a dynamic block with 31 distance codes, cut after its counts", dynamic(257, 31, 4).bytes()],
    ["a dynamic block cut inside its counts", dynamic(257, 1, 4).bytes().subarray(0, 1)],
    ["a dynamic block whose code of code lengths has too many codes", dynamic(257, 1, 4).number(1, 3).number(1, 3).number(1, 3).number(0, 3).number(0, 16).bytes()],
    ["a dynamic block whose code of code lengths has one code", dynamic(257, 1, 4).number(0, 3).number(0, 3).number(0, 3).number(1, 3).number(0, 16).bytes()],
    ["a dynamic block whose code of code lengths has no code", dynamic(257, 1, 4).number(0, 12).number(0, 300).bytes()],
    ["a dynamic block whose code of code lengths has no code, cut", dynamic(257, 1, 4).number(0, 12).number(0, 100).bytes()],
    ["a dynamic block that repeats before the first length", dynamic(257, 1, 4).number(1, 3).number(0, 3).number(0, 3).number(1, 3).code(1, 1).number(0, 2).number(0, 16).bytes()],
    ["a dynamic block that repeats before the first length, cut inside the repeat", dynamic(257, 1, 4).number(1, 3).number(0, 3).number(0, 3).number(1, 3).code(1, 1).bytes().subarray(0, 3)],
    ["a dynamic block that repeats beyond its last code", dynamic(257, 1, 4).number(0, 3).number(0, 3).number(1, 3).number(1, 3).code(1, 1).number(127, 7).code(1, 1).number(127, 7).code(1, 1).number(127, 7).number(0, 16).bytes()],
    ["a dynamic block without a code for its end", dynamic(257, 1, 4).number(0, 3).number(0, 3).number(1, 3).number(1, 3).code(1, 1).number(127, 7).code(1, 1).number(109, 7).number(0, 16).bytes()],
  ];
}

test("the three vectors with a compressed body", async (t) => {
  const kinds = {"deflate-stored": 0, "deflate-fixed": 1, "deflate-dynamic": 2};
  for (const [name, kind] of Object.entries(kinds)) {
    await t.test(name, () => {
      const file = new Uint8Array(fs.readFileSync(path.join(ROOT, "tests", "vectors", "valid", `${name}.odrg`)));
      assert.equal(file[5], 1, "the file is compressed");
      const stream = file.subarray(16);
      assert.equal((stream[0] >> 1) & 3, kind, "the kind of the first block");
      const [theirs] = storedAnswer("inflate", [], [hex(stream)]);
      assert.equal(theirs.left, 0);
      assert.deepEqual(asTheirs(verdict(stream), theirs), theirs);
      const {data, used} = inflate.inflateRaw(stream);
      assert.ok(data instanceof Uint8Array);
      assert.equal(used, stream.length);
    });
  }
});

test("streams of zlib at every level", async (t) => {
  const streams = zlibStreams();

  await t.test("each is decoded to its input, with nothing left", () => {
    for (const {name, data, stream} of streams) {
      const {data: output, used} = inflate.inflateRaw(stream);
      assert.equal(used, stream.length, name);
      assert.ok(Buffer.from(output).equals(Buffer.from(data)), name);
    }
    assert.equal(streams.length, 9 * 14);
  });

  await t.test("the kinds of block are all among them", () => {
    const kinds = new Set(streams.map(({stream}) => (stream[0] >> 1) & 3));
    assert.deepEqual([...kinds].sort(), [0, 1, 2]);
  });

  await t.test("bytes after a stream are counted, not read", () => {
    const from = numbers(7);
    const longer = streams.map(({stream}, i) => {
      const extra = from.bytes(1 + (i % 5));
      const both = new Uint8Array(stream.length + extra.length);
      both.set(stream);
      both.set(extra, stream.length);
      return both;
    });
    const counts = sameVerdicts(longer, (i) => `${streams[i].name}, with bytes after it`);
    assert.equal(counts.whole, streams.length);
    longer.forEach((stream, i) => {
      assert.equal(inflate.inflateRaw(stream).used, streams[i].stream.length);
    });
  });
});

test("damaged and cut streams get the verdict of zlib", async (t) => {
  const streams = zlibStreams().filter(({stream}) => stream.length <= 400);

  await t.test("each stream cut at every length", () => {
    const cases = [];
    for (const {name, stream} of streams) {
      for (let length = 0; length < stream.length; length += 1) {
        cases.push({name: `${name}, cut to ${length} bytes`, stream: stream.subarray(0, length)});
      }
    }
    assert.ok(cases.length > 6000, `${cases.length} cases`);
    const counts = sameVerdicts(cases.map((entry) => entry.stream), (i) => cases[i].name);
    assert.equal(counts.truncated, cases.length);
  });

  await t.test("each stream damaged in every byte", () => {
    const from = numbers(303);
    const cases = [];
    for (const {name, stream} of streams) {
      for (let at = 0; at < stream.length; at += 1) {
        for (const change of [1 << (at % 8), from.between(1, 255)]) {
          const damaged = stream.slice();
          damaged[at] ^= change;
          cases.push({name: `${name}, byte ${at} changed by ${change}`, stream: damaged});
        }
      }
    }
    assert.ok(cases.length > 12000, `${cases.length} cases`);
    const counts = sameVerdicts(cases.map((entry) => entry.stream), (i) => cases[i].name);
    assert.ok(counts.whole > 1000, JSON.stringify(counts));
    assert.ok(counts["bad-deflate"] > 500, JSON.stringify(counts));
    assert.ok(counts.truncated > 200, JSON.stringify(counts));
  });

  await t.test("each damaged stream cut as well, for 6000 cases from seeds", () => {
    const from = numbers(404);
    const cases = [];
    while (cases.length < 6000) {
      const {name, stream} = from.pick(streams);
      if (stream.length < 2) {
        continue;
      }
      const damaged = stream.slice();
      const at = from.below(stream.length);
      damaged[at] ^= from.between(1, 255);
      const length = from.between(1, stream.length);
      cases.push({name: `${name}, byte ${at} changed, cut to ${length}`, stream: damaged.subarray(0, length)});
    }
    const counts = sameVerdicts(cases.map((entry) => entry.stream), (i) => cases[i].name);
    assert.ok(counts["bad-deflate"] > 300, JSON.stringify(counts));
    assert.ok(counts.truncated > 300, JSON.stringify(counts));
  });

  await t.test("noise, for 3000 inputs from seeds", () => {
    const from = numbers(505);
    const cases = Array.from({length: 3000}, () => from.bytes(from.between(0, 40)));
    sameVerdicts(cases, (i) => `noise ${i}`);
  });
});

test("streams with one defect each, written by hand", async (t) => {
  const cases = broken();
  const theirs = storedAnswer("inflate", [], cases.map(([, stream]) => hex(stream)));
  for (let i = 0; i < cases.length; i += 1) {
    const [label, stream] = cases[i];
    await t.test(label, () => {
      assert.deepEqual(asTheirs(verdict(stream), theirs[i]), theirs[i], hex(stream));
    });
  }

  await t.test("both verdicts of a stream that is not whole are among them", () => {
    const reasons = theirs.map((result) => result.reason ?? "whole");
    assert.ok(reasons.filter((reason) => reason === "bad-deflate").length >= 12, reasons.join(" "));
    assert.ok(reasons.filter((reason) => reason === "truncated").length >= 5, reasons.join(" "));
    assert.ok(reasons.filter((reason) => reason === "whole").length >= 3, reasons.join(" "));
  });

  await t.test("every cut of them as well", () => {
    const cuts = [];
    for (const [label, stream] of cases) {
      for (let length = 0; length < stream.length; length += 1) {
        cuts.push({name: `${label}, cut to ${length}`, stream: stream.subarray(0, length)});
      }
    }
    sameVerdicts(cuts.map((entry) => entry.stream), (i) => cuts[i].name);
  });
});

test("what a rejection of a stream says", () => {
  assert.throws(() => inflate.inflateRaw(new Uint8Array(0)), {reason: "truncated", detail: "the file ends inside the DEFLATE stream"});
  assert.throws(() => inflate.inflateRaw(Uint8Array.of(0x07)), {reason: "bad-deflate", detail: "a block of a kind that does not exist"});
  assert.throws(() => inflate.inflateRaw(Uint8Array.of(0x01, 0x05, 0x00, 0x00, 0x00)), {
    reason: "bad-deflate",
    detail: "the two lengths of a stored block do not agree",
  });
});
