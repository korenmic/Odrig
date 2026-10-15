import assert from "node:assert/strict";
import {spawnSync} from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import test from "node:test";
import {pathToFileURL} from "node:url";
import zlib from "node:zlib";

import * as support from "./support.js";
import {EXPECTED, EXPECTED_FILES, expected, sha256} from "./stored.js";

const {ROOT} = support;
const TESTS = path.join(ROOT, "converter", "tests");

// The kinds of request whose answers are stored, and the helpers by which a test asks each.
const KINDS = {
  check: /\bstoredChecks\(/,
  cli: /\b(storedRun|runJsAndStored)\(/,
  decode: /\bstoredAnswer\("decode"/,
  deflate: /\bstoredAnswer\("deflate"/,
  dumps: /\bstoredAnswer\("dumps"/,
  encode: /\bstoredAnswer\("encode"/,
  forms: /\bstoredAnswer\("forms"/,
  generators: /\bstoredGenerated\(/,
  inflate: /\bstoredAnswer\("inflate"/,
  mappings: /\bstoredAnswer\("mappings"/,
  media: /\bstoredAnswer\("media"/,
  milliseconds: /\bstoredAnswer\("milliseconds"/,
  read_mappings: /\bstoredAnswer\("read_mappings"/,
  read_shows: /\bstoredAnswer\("read_shows"/,
  rects: /\bstoredAnswer\("rects"/,
  resample: /\bstoredAnswer\("resample"/,
  run: /\bstoredRuns\(/,
  sixdigits: /\bstoredAnswer\("sixdigits"/,
  ticks: /\bstoredAnswer\("ticks"/,
  timeline: /\bstoredAnswer\("timeline"/,
};
const LARGEST = 8 * 1024 * 1024;

function storedNames() {
  return fs.existsSync(EXPECTED) ? fs.readdirSync(EXPECTED).filter((name) => name !== "files").sort() : [];
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
    assert.deepEqual(names.map((name) => name.replace(/\.json(\.gz)?$/, "")), Object.keys(KINDS).sort());
  });

  await t.test("each is valid: every answer has its key, what it answered, and the files it made, wrote and removed", () => {
    const named = new Set();
    for (const kind of Object.keys(KINDS)) {
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

  await t.test("every kind is asked for by a test", () => {
    const sources = fs.readdirSync(TESTS).filter((name) => name.endsWith(".test.js")).map((name) => fs.readFileSync(path.join(TESTS, name), "utf8")).join("\n");
    for (const [kind, asked] of Object.entries(KINDS)) {
      assert.match(sources, asked, `no test asks for the stored answers of ${kind}`);
    }
  });
});

test("no test starts Python", async (t) => {
  await t.test("the support of the tests has no helper that starts it, and names none", () => {
    for (const name of ["python", "pythonFrom", "runPython", "runBoth", "reference", "generated", "pythonChecks", "runPythonMany", "REFERENCE"]) {
      assert.equal(name in support, false, `support.js offers ${name}`);
    }
    for (const name of ["support.js", "stored.js"]) {
      assert.doesNotMatch(fs.readFileSync(path.join(TESTS, name), "utf8"), /\.venv|ODRIG_PYTHON|reference\.py|PYTHONPATH/, name);
    }
    assert.equal(fs.existsSync(path.join(TESTS, "reference.py")), false);
  });

  await t.test("the helpers give the stored answers with no Python on the path, and start no program named python", (inner) => {
    const folder = fs.realpathSync(fs.mkdtempSync(path.join(os.tmpdir(), "odrig-converter-")));
    inner.after(() => fs.rmSync(folder, {recursive: true, force: true}));
    const only = path.join(folder, "bin");
    fs.mkdirSync(only);
    fs.symlinkSync(process.execPath, path.join(only, "node"));
    const work = fs.realpathSync(fs.mkdtempSync(path.join(os.tmpdir(), "odrig-converter-")));
    inner.after(() => fs.rmSync(work, {recursive: true, force: true}));
    const program = `
      import cp from "node:child_process";
      import fs from "node:fs";
      import {syncBuiltinESMExports} from "node:module";
      for (const name of ["spawn", "spawnSync", "execFile", "execFileSync", "exec", "execSync"]) {
        const original = cp[name];
        cp[name] = (command, ...rest) => {
          const words = [command, ...(Array.isArray(rest[0]) ? rest[0] : [])].map(String).join(" ");
          if (/python/i.test(words)) {
            throw new Error("a helper started Python: " + words);
          }
          return original(command, ...rest);
        };
      }
      syncBuiltinESMExports();
      const support = await import(${JSON.stringify(pathToFileURL(path.join(TESTS, "support.js")).href)});
      const mappings = support.storedAnswer("mappings");
      const help = support.storedRun(["--help"]);
      const both = support.runJsAndStored(["--help"]);
      const made = support.storedGenerated(${JSON.stringify(work)}, "hello_world", "mapping/legs-2.json");
      process.stdout.write(JSON.stringify({mappings: Object.keys(mappings).length > 0, help: help.status, js: both.js.status, made: fs.existsSync(made)}));
    `;
    const environment = {...process.env, PATH: only};
    delete environment.ODRIG_PYTHON;
    const done = spawnSync(process.execPath, ["--input-type=module", "-e", program], {cwd: ROOT, encoding: "utf8", env: environment, timeout: 120000});
    assert.equal(done.status, 0, done.stderr);
    assert.deepEqual(JSON.parse(done.stdout), {mappings: true, help: 0, js: 0, made: true});
  });
});
