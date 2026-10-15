import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import test from "node:test";
import zlib from "node:zlib";

import {ROOT} from "./support.js";
import {EXPECTED, EXPECTED_FILES, STORED_KINDS, answered, expected, mode, sha256} from "./stored.js";

// The kinds of request: those of reference.py, and the command lines of the Python tool
// and of its generators.
const REFERENCE = fs.readFileSync(path.join(ROOT, "converter", "tests", "reference.py"), "utf8");
const KINDS = [...new Set([...REFERENCE.matchAll(/^def ([a-z_]+)\(arguments, /gm)].map((match) => match[1]).concat(["cli", "generators"]))].sort();
const LARGEST = 8 * 1024 * 1024;

function storedNames() {
  return fs.existsSync(EXPECTED) ? fs.readdirSync(EXPECTED).filter((name) => name !== "files").sort() : [];
}

function kindOf(name) {
  return name.replace(/\.json(\.gz)?$/, "");
}

function sizeUnder(folder) {
  let total = 0;
  for (const entry of fs.readdirSync(folder, {withFileTypes: true})) {
    total += entry.isDirectory() ? sizeUnder(path.join(folder, entry.name)) : fs.statSync(path.join(folder, entry.name)).size;
  }
  return total;
}

test("the stored answers", async (t) => {
  await t.test("there is a file of answers for every kind of request, and for nothing else", () => {
    const names = storedNames();
    assert.ok(names.length > 0, `${EXPECTED} holds no stored answers`);
    for (const name of names) {
      assert.match(name, /^[a-z_]+\.json(\.gz)?$/, name);
    }
    assert.deepEqual(names.map(kindOf), KINDS);
  });

  await t.test("each is valid: every answer has its key, what it answered, and the files it made, wrote and removed", () => {
    const named = new Set();
    for (const kind of KINDS) {
      const entries = expected(kind);
      assert.ok(Object.keys(entries).length > 0, kind);
      for (const [key, entry] of Object.entries(entries)) {
        assert.match(key, /^[0-9a-f]{64}$/, kind);
        assert.deepEqual(Object.keys(entry), ["answer", "made", "written", "removed"], `${kind} ${key}`);
        for (const name of [...entry.made, ...Object.keys(entry.written), ...entry.removed]) {
          assert.match(name, /^<tmp\d+>\/[^\\]+$/, `${kind} ${key}`);
        }
        for (const stored of Object.values(entry.written)) {
          assert.ok("base64" in stored || /^[0-9a-f]{64}$/.test(stored.file), `${kind} ${key}`);
          if ("file" in stored) {
            named.add(stored.file);
          }
        }
        assert.doesNotMatch(JSON.stringify(entry), /\/Users\/|\/home\/|\/var\/folders\/|odrig-converter-/, `${kind} ${key} names a folder of the computer it was made on`);
      }
    }
    const files = fs.readdirSync(EXPECTED_FILES).sort();
    assert.deepEqual(files, [...named].sort().map((digest) => `${digest}.gz`), "every large file is named by an answer, and every one named is there");
    for (const name of files) {
      assert.equal(sha256(zlib.gunzipSync(fs.readFileSync(path.join(EXPECTED_FILES, name)))), name.replace(/\.gz$/, ""), name);
    }
  });

  await t.test("they take 8 MB at most", () => {
    const size = sizeUnder(EXPECTED);
    assert.ok(size <= LARGEST, `${size} bytes`);
  });

  await t.test("a request of a kind that is not stored-only is checked against Python", () => {
    for (const kind of KINDS) {
      assert.equal(mode(kind), process.env.ODRIG_EXPECTED ?? (STORED_KINDS.has(kind) ? "stored" : "verify"), kind);
    }
  });

  await t.test("in that check, an answer of Python that is not the stored one is a failure, and so is a request with none", {skip: process.env.ODRIG_EXPECTED === "record"}, () => {
    // The request for the mapping files asks nothing else, and names no file.
    const ask = {argv: [], input: null};
    const stored = expected("mappings")[sha256(JSON.stringify(["mappings", ask, {}, []]))];
    assert.ok(stored !== undefined);
    const given = process.env.ODRIG_EXPECTED;
    process.env.ODRIG_EXPECTED = "verify";
    try {
      assert.deepEqual(answered("mappings", ask, [], () => stored.answer), stored.answer);
      assert.throws(() => answered("mappings", ask, [], () => ({})), /differs from what Python answers/);
      assert.throws(() => answered("mappings", {argv: ["nothing any test asks"], input: null}, [], () => ({})), /no stored answer/);
    } finally {
      if (given === undefined) {
        delete process.env.ODRIG_EXPECTED;
      } else {
        process.env.ODRIG_EXPECTED = given;
      }
    }
  });
});
