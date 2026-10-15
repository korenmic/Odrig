import assert from "node:assert/strict";
import {spawnSync} from "node:child_process";
import fs from "node:fs";
import path from "node:path";
import test from "node:test";
import {pathToFileURL} from "node:url";

import * as index from "../lib/index.js";
import {CONVERTER, ROOT} from "./support.js";

const LIB = path.join(CONVERTER, "lib");
const CLI = path.join(CONVERTER, "cli");

function sources(folder = LIB) {
  const names = fs.readdirSync(folder).sort();
  return names.map((name) => ({name, text: fs.readFileSync(path.join(folder, name), "utf8")}));
}

// Every module a source text imports from: `import ... from`, `export ... from`, a bare
// `import "..."` and `import("...")`.
function specifiers(text) {
  const found = [];
  const patterns = [
    /\bfrom\s*(["'])([^"']*)\1/g,
    /\bimport\s*(["'])([^"']*)\1/g,
    /\bimport\s*\(\s*(["'`])([^"'`]*)\1/g,
  ];
  for (const pattern of patterns) {
    for (const match of text.matchAll(pattern)) {
      found.push(match[2]);
    }
  }
  return found;
}

// The modules a source text of the command line part loads: its statements `import` and
// `export ... from`, which begin a line, and `import("...")`. A word in a text of the
// program, such as the name of the subcommand `import`, is no statement.
function statements(text) {
  const found = [];
  const patterns = [
    /^import\s+(?:[^"';]*?\sfrom\s*)?(["'])([^"']*)\1/gm,
    /^export\s[^"';=]*?\sfrom\s*(["'])([^"']*)\1/gm,
    /\bimport\s*\(\s*(["'`])([^"'`]*)\1/g,
  ];
  for (const pattern of patterns) {
    for (const match of text.matchAll(pattern)) {
      found.push(match[2]);
    }
  }
  return found;
}

// What the library may not name: what only Node.js has, what only a page has, the clock,
// random numbers, the compression of the platform, and words newer than ECMAScript 2020.
const FORBIDDEN = [
  ["node:", /\bnode:/],
  ["require", /\brequire\b/],
  ["process", /\bprocess\b/],
  ["Buffer", /\bBuffer\b/],
  ["fetch", /\bfetch\b/],
  ["document", /\bdocument\b/],
  ["window", /\bwindow\b/],
  ["globalThis", /\bglobalThis\b/],
  ["Worker", /\bWorker\b/],
  ["CompressionStream", /\bCompressionStream\b/],
  ["DecompressionStream", /\bDecompressionStream\b/],
  ["Date", /\bDate\b/],
  ["performance", /\bperformance\b/],
  ["Math.random", /\bMath\s*\.\s*random\b/],
  ["??=", /\?\?=/],
  ["||=", /\|\|=/],
  ["&&=", /&&=/],
  [".at(", /\.at\(/],
  [".replaceAll(", /\.replaceAll\(/],
  ["Object.hasOwn", /\bObject\.hasOwn\b/],
  ["structuredClone", /\bstructuredClone\b/],
];

test("the library is made of its own files only", async (t) => {
  const files = sources();

  await t.test("it has files, and each is a JavaScript module", () => {
    assert.ok(files.length >= 2);
    for (const {name} of files) {
      assert.match(name, /^[a-z]+\.js$/);
    }
  });

  await t.test("every file imports only ./<name>.js, a file of the library", () => {
    const names = new Set(files.map(({name}) => name));
    for (const {name, text} of files) {
      for (const specifier of specifiers(text)) {
        assert.match(specifier, /^\.\/[a-z]+\.js$/, `lib/${name} imports ${specifier}`);
        assert.ok(names.has(specifier.slice(2)), `lib/${name} imports ${specifier}, which is not there`);
      }
    }
  });

  await t.test("no file names what only Node.js or only a page has", () => {
    for (const {name, text} of files) {
      for (const [word, pattern] of FORBIDDEN) {
        assert.ok(!pattern.test(text), `lib/${name} names ${word}`);
      }
    }
  });

  await t.test("the checks find what they look for", () => {
    assert.deepEqual(specifiers('import fs from "node:fs";\nexport * as a from "./a.js";\nconst b = await import("omggif");\nimport "./c.js";'), [
      "node:fs", "./a.js", "./c.js", "omggif",
    ]);
    const named = (text) => FORBIDDEN.filter(([, pattern]) => pattern.test(text)).map(([word]) => word);
    assert.deepEqual(named('import fs from "node:fs";'), ["node:"]);
    assert.deepEqual(named("const a = new ArrayBuffer(8); required(a); reprocess();"), []);
    assert.deepEqual(named("Buffer.from(process.argv); require('x'); window.document; fetch(u);"), [
      "require", "process", "Buffer", "fetch", "document", "window",
    ]);
    assert.deepEqual(named("new Date(); Math.random(); new CompressionStream('deflate-raw'); a ??= 1; b.at(-1);"), [
      "CompressionStream", "Date", "Math.random", "??=", ".at(",
    ]);
  });
});

test("index.js offers every module of the library", async () => {
  for (const {name} of sources()) {
    if (name === "index.js") {
      continue;
    }
    const module = await import(pathToFileURL(path.join(LIB, name)).href);
    const offered = index[name.slice(0, -3)];
    assert.equal(offered, module, `index.js does not offer ${name}`);
    assert.ok(Object.keys(module).length > 0, `${name} offers nothing`);
  }
  assert.equal(index.Rejection, index.errors.Rejection);
});

test("the tool is the library and a command line part that is built on it", async (t) => {
  const files = sources(CLI);
  const start = fs.readFileSync(path.join(CONVERTER, "odrig.js"), "utf8");
  const manifest = JSON.parse(fs.readFileSync(path.join(CONVERTER, "package.json"), "utf8"));

  await t.test("the folder holds the two parts and the tests, and nothing is built before it runs", () => {
    for (const name of ["lib", "cli", "tests"]) {
      assert.ok(fs.statSync(path.join(CONVERTER, name)).isDirectory(), name);
    }
    assert.ok(files.length >= 2);
    for (const {name} of files) {
      assert.match(name, /^[a-z]+\.js$/);
    }
    assert.equal(manifest.type, "module");
    assert.equal(manifest.engines.node, ">=20");
    assert.deepEqual(manifest.scripts, {test: "node --test"}, "one script, which names no test file and builds nothing");
  });

  await t.test("the command line part imports Node.js, the library by its index, and its own files", () => {
    const names = new Set(files.map(({name}) => name));
    const packages = new Map();
    assert.ok(statements(files.find(({name}) => name === "main.js").text).includes("../lib/index.js"));
    for (const {name, text} of files) {
      for (const specifier of statements(text)) {
        if (/^node:(child_process|fs|path|url)$/.test(specifier) || specifier === "../lib/index.js") {
          continue;
        }
        if (/^\.\/[a-z]+\.js$/.test(specifier)) {
          assert.ok(names.has(specifier.slice(2)), `cli/${name} imports ${specifier}, which is not there`);
          continue;
        }
        packages.set(specifier, [...(packages.get(specifier) ?? []), name]);
      }
    }
    assert.deepEqual([...packages], [["omggif", ["gif.js"]]], "the one package that is loaded, where a GIF is read");
    assert.match(files.find(({name}) => name === "gif.js").text, /await import\("omggif"\)/);
    assert.deepEqual(statements(start).sort(), ["./cli/main.js", "./cli/version.js"]);
    assert.deepEqual(statements(files.find(({name}) => name === "version.js").text), []);
    assert.deepEqual(statements('import a from "node:fs";\nimport {\n  b,\n} from "./b.js";\nexport {c} from "./c.js";\nconst names = ["import", "x"];\nexport const D = "d";\nawait import("e");'), [
      "node:fs", "./b.js", "./c.js", "e",
    ]);
  });

  await t.test("it decodes, encodes, checks and fits with the library and has no such code of its own", () => {
    const text = (name) => files.find((file) => file.name === name).text;
    for (const call of ["timeline.importFrames(", "jsonframes.loads(", "jsonframes.dumps(", "odrg.encode(", "odrg.decode(", "mapping.loads("]) {
      assert.ok(text("main.js").includes(call), `cli/main.js calls ${call}`);
    }
    for (const call of ["packing.begin(", "packing.encodeSource("]) {
      assert.ok(text("folder.js").includes(call), `cli/folder.js calls ${call}`);
    }
    for (const name of ["gif.js", "video.js", "files.js"]) {
      assert.match(text(name), /^import \{errors\} from "\.\.\/lib\/index\.js";$/m, `cli/${name} takes the errors of the library and nothing else`);
    }
    for (const {name, text: source} of files) {
      assert.equal(/\bzlib\b|\bCompressionStream\b|\bDecompressionStream\b/.test(source), false, `cli/${name} names a compression of the platform`);
    }
  });

  await t.test("what is tracked of the tool is its sources: no media file, no generated source and no package", (inner) => {
    const listed = spawnSync("git", ["ls-files", "-z"], {cwd: ROOT, encoding: "utf8"});
    if (listed.status !== 0) {
      inner.skip("git does not list the files of this folder");
      return;
    }
    const tracked = listed.stdout.split("\0").filter((name) => name !== "");
    const ours = tracked.filter((name) => name.startsWith("converter/"));
    assert.ok(ours.includes("converter/package-lock.json"));
    const known = /^converter\/(package\.json|package-lock\.json|ffmpeg\.sha256|odrig\.js|(cli|lib|tests)\/[a-z]+\.js|tests\/[a-z]+\.test\.js|tests\/reference\.py|tests\/page\/(index\.html|page\.js)|tests\/expected\/[a-z_]+\.json(\.gz)?|tests\/expected\/files\/[0-9a-f]{64}\.gz)$/;
    assert.deepEqual(ours.filter((name) => !known.test(name)), []);
    assert.deepEqual(tracked.filter((name) => /\.(mp4|mov|gif)$/i.test(name)), []);
  });
});

test("the reasons are those of the Python tool", async (t) => {
  const python = fs.readFileSync(path.join(ROOT, "odrig", "errors.py"), "utf8");
  const expected = new Map();
  for (const match of python.matchAll(/^([A-Z][A-Z_]*) = "([a-z-]+)"$/gm)) {
    expected.set(match[1], match[2]);
  }
  const ours = new Map(Object.entries(index.errors).filter(([name, value]) => /^[A-Z][A-Z_]*$/.test(name) && typeof value === "string"));

  await t.test("there are 42 of them, with the same names for the same words", () => {
    assert.equal(expected.size, 42);
    assert.deepEqual([...ours].sort(), [...expected].sort());
    assert.equal(new Set(ours.values()).size, 42);
  });

  await t.test("the library offers nothing else but Rejection and naming", () => {
    const others = Object.keys(index.errors).filter((name) => !ours.has(name)).sort();
    assert.deepEqual(others, ["Rejection", "naming"]);
  });

  await t.test("a rejection is an error with a reason and a detail", () => {
    const rejection = new index.Rejection(index.errors.BAD_MAGIC, "the file starts with 00 00 00 00, not 4f 44 52 47");
    assert.ok(rejection instanceof Error);
    assert.equal(rejection.reason, "bad-magic");
    assert.equal(rejection.detail, "the file starts with 00 00 00 00, not 4f 44 52 47");
    assert.equal(rejection.message, "bad-magic: the file starts with 00 00 00 00, not 4f 44 52 47");
  });

  await t.test("naming puts the name of the file in front of the detail", async () => {
    const reject = () => {
      throw new index.Rejection(index.errors.NO_FRAMES, "frames is empty");
    };
    assert.throws(() => index.errors.naming("a.json", reject), {reason: "no-frames", detail: "a.json: frames is empty"});
    assert.equal(index.errors.naming("a.json", () => 7), 7);
    await assert.rejects(index.errors.naming("b.gif", async () => reject()), {reason: "no-frames", detail: "b.gif: frames is empty"});
    assert.equal(await index.errors.naming("b.gif", async () => 8), 8);
    assert.throws(() => index.errors.naming("a.json", () => {
      throw new RangeError("a mistake");
    }), RangeError);
  });
});
