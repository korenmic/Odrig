import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import test from "node:test";
import zlib from "node:zlib";

import {errors, inflate, odrg, thumbnail} from "../lib/index.js";
import {ROOT} from "./support.js";

const VECTORS = path.join(ROOT, "tests", "vectors");

// What `inflateRaw` gives of a stream: its output and the bytes it took, or its verdict.
function whole(stream) {
  try {
    const {data, used} = inflate.inflateRaw(stream);
    return {data: Buffer.from(data), used};
  } catch (error) {
    if (!(error instanceof errors.Rejection)) {
      throw error;
    }
    return {reason: error.reason, detail: error.detail};
  }
}

// The same stream fed to `inflateStream` in parts of `size` bytes and pulled after each:
// its output and the bytes it took, or its verdict and the output it gave before it.
function inParts(stream, size) {
  const reading = inflate.inflateStream();
  const given = [];
  try {
    for (let at = 0; at < stream.length; at += size) {
      reading.push(stream.subarray(at, at + size));
      for (let part = reading.pull(4096); part.length > 0; part = reading.pull(4096)) {
        given.push(part);
      }
    }
    reading.end();
    for (let part = reading.pull(4096); part.length > 0; part = reading.pull(4096)) {
      given.push(part);
    }
    assert.ok(reading.finished);
    return {data: Buffer.concat(given), used: reading.used};
  } catch (error) {
    if (!(error instanceof errors.Rejection)) {
      throw error;
    }
    return {reason: error.reason, detail: error.detail, before: Buffer.concat(given)};
  }
}

// The DEFLATE streams of the tests: of the library's inputs at several levels, cut, with a
// byte changed, and the bodies of the compressed vectors.
function streams() {
  const found = [];
  const text = Buffer.from("Hello world, hello strips, hello world of sixty by sixty. ".repeat(40));
  const noise = Buffer.alloc(5000);
  for (let at = 0; at < noise.length; at += 1) {
    noise[at] = (at * 2654435761) >>> 24;
  }
  const far = Buffer.alloc(70000);
  for (let at = 0; at < far.length; at += 1) {
    far[at] = (at % 32768) * 31 & 0xff;
  }
  for (const input of [Buffer.alloc(0), Buffer.from([0x41]), text, noise, far, Buffer.alloc(3000)]) {
    for (const level of [0, 1, 6, 9]) {
      const stream = zlib.deflateRawSync(input, {level});
      found.push(stream);
      found.push(stream.subarray(0, Math.floor(stream.length / 2)));
      if (stream.length > 8) {
        for (const at of [2, Math.floor(stream.length / 3), stream.length - 3]) {
          const changed = Buffer.from(stream);
          changed[at] ^= 0x5a;
          found.push(changed);
        }
      }
    }
  }
  for (const folder of ["valid", "invalid"]) {
    for (const name of fs.readdirSync(path.join(VECTORS, folder)).sort()) {
      if (!name.endsWith(".odrg")) {
        continue;
      }
      const data = new Uint8Array(fs.readFileSync(path.join(VECTORS, folder, name)));
      if (data.length > 16 && (data[5] & odrg.COMPRESSED) !== 0) {
        found.push(Buffer.from(data.subarray(16)));
      }
    }
  }
  return found;
}

test("the stream gives the output and the verdicts of inflateRaw, fed in parts of 1, 7 and 4,096 bytes", () => {
  const all = streams();
  assert.ok(all.length > 100, String(all.length));
  let refused = 0;
  for (const stream of all) {
    const expected = whole(stream);
    refused += "reason" in expected ? 1 : 0;
    for (const size of [1, 7, 4096]) {
      const got = inParts(stream, size);
      if ("reason" in expected) {
        assert.deepEqual({reason: got.reason, detail: got.detail}, expected, `${stream.length} bytes in parts of ${size}`);
        const prefix = (() => {
          try {
            return Buffer.from(zlib.inflateRawSync(stream, {finishFlush: zlib.constants.Z_SYNC_FLUSH}));
          } catch {
            return null;
          }
        })();
        if (prefix !== null) {
          assert.ok(prefix.subarray(0, got.before.length).equals(got.before), "the output before a verdict is a prefix of zlib's");
        }
      } else {
        assert.deepEqual(got, expected, `${stream.length} bytes in parts of ${size}`);
      }
    }
  }
  assert.ok(refused > 20, String(refused));
});

test("truncated comes only after the end of the input is told", () => {
  const stream = zlib.deflateRawSync(Buffer.alloc(100000, 7), {level: 1});
  const reading = inflate.inflateStream();
  reading.push(stream.subarray(0, stream.length - 2));
  while (reading.pull().length > 0) {
    // The output that the input gives.
  }
  assert.ok(reading.wanting);
  assert.ok(!reading.finished);
  reading.end();
  assert.throws(() => reading.pull(), {reason: "truncated", detail: "the file ends inside the DEFLATE stream"});
});

// An ODRG file of `frames` stored records of the full canvas of 60 x 60 without a palette,
// each of one colour, compressed or not.
function large(frames, compressed) {
  const n = 60 * 60 * 3;
  const body = Buffer.alloc(frames * (5 + n));
  for (let frame = 0; frame < frames; frame += 1) {
    const at = frame * (5 + n);
    body.writeUInt16LE(20, at);
    body.writeUInt16LE(n + 1, at + 2);
    body[at + 4] = odrg.STORED;
    body.fill((frame * 37) & 0xff, at + 5, at + 5 + n);
  }
  const header = Buffer.alloc(16);
  Buffer.from(odrg.MAGIC).copy(header, 0);
  header[4] = odrg.VERSION;
  header[5] = compressed ? odrg.COMPRESSED : 0;
  header.writeUInt16LE(60, 6);
  header.writeUInt16LE(60, 8);
  header.writeUInt16LE(0, 10);
  header.writeUInt16LE(frames & 0xffff, 12);
  header.writeUInt16LE(Math.floor(frames / 65536), 14);
  return new Uint8Array(Buffer.concat([header, compressed ? zlib.deflateRawSync(body, {level: 1}) : body]));
}

test("a compressed file of more than 16 MB is previewed with at most the window and one record held, as its uncompressed twin", () => {
  const frames = 1600;
  const packed = large(frames, true);
  const plain = large(frames, false);
  assert.ok(plain.length > 16 * 1024 * 1024, String(plain.length));
  const making = thumbnail.maker(packed);
  let most = 0;
  let steps = 0;
  while (!making.step()) {
    most = Math.max(most, making.held());
    steps += 1;
  }
  assert.ok(most <= 32768 + 60 * 60 * 3 + 5, String(most));
  assert.ok(steps > 30, String(steps));
  assert.deepEqual(making.preview, thumbnail.make(plain));
});

test("a compressed file and its uncompressed twin give the same preview, byte for byte", () => {
  for (const name of fs.readdirSync(path.join(VECTORS, "valid")).sort()) {
    if (!name.endsWith(".odrg")) {
      continue;
    }
    const data = new Uint8Array(fs.readFileSync(path.join(VECTORS, "valid", name)));
    const decoded = odrg.decode(data);
    const animation = {width: decoded.width, height: decoded.height, frames: decoded.records.map((record) => ({ms: record.ms, picture: record.picture}))};
    let packed;
    let plain;
    try {
      packed = odrg.encode(animation, {compressed: true});
      plain = odrg.encode(animation, {compressed: false});
    } catch {
      continue;
    }
    assert.deepEqual(thumbnail.make(packed), thumbnail.make(plain), name);
  }
});
