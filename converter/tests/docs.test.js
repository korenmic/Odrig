import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import test from "node:test";

import {NAMES, usage} from "../cli/arguments.js";
import {CONVERTER, ROOT, runJs, temporary} from "./support.js";

const TOOL = "node converter/odrig.js";

function read(...parts) {
  return fs.readFileSync(path.join(ROOT, ...parts), "utf8");
}

// The text under a heading of the second level, to the next one, or null.
function section(text, heading) {
  const start = text.indexOf(`\n## ${heading}\n`);
  if (start < 0) {
    return null;
  }
  const from = start + heading.length + 5;
  const end = text.indexOf("\n## ", from);
  return text.slice(from, end < 0 ? text.length : end);
}

// The lines of the code blocks of a text that name no language, each without the space
// around it. A line that ends in a backslash, and a line set further in than its block, is
// joined with the line it continues.
function commands(text) {
  const lines = [];
  let inset = null;
  let plain = false;
  let first = 0;
  let joining = false;
  for (const line of text.split("\n")) {
    const fence = /^(\s*)```(.*)$/.exec(line);
    if (fence !== null) {
      plain = inset === null && fence[2] === "";
      inset = inset === null ? fence[1].length : null;
      first = lines.length;
      joining = false;
      continue;
    }
    if (inset === null || !plain) {
      continue;
    }
    const own = line.slice(Math.min(inset, line.length - line.trimStart().length));
    const continues = (joining || /^\s/.test(own)) && lines.length > first;
    joining = own.endsWith("\\");
    const piece = (joining ? own.slice(0, -1) : own).trim();
    if (piece === "") {
      continue;
    }
    if (continues) {
      lines[lines.length - 1] += ` ${piece}`;
    } else {
      lines.push(piece);
    }
  }
  return lines;
}

function words(text) {
  return text.split(/\s+/).join(" ");
}

test("docs/converter.md presents the JavaScript tool as the converter", async (t) => {
  const page = read("docs", "converter.md");
  const flat = words(page);

  await t.test("every subcommand has a section with its usage line and an example", () => {
    for (const name of NAMES) {
      const body = section(page, name);
      assert.notEqual(body, null, `docs/converter.md has no section "## ${name}"`);
      const given = commands(body).filter((line) => line.startsWith(`${TOOL} ${name} `));
      assert.ok(given.length >= 2, `the section "## ${name}" of docs/converter.md has no example of ${TOOL} ${name}: it has ${given.length} command lines of it and needs the usage line and an example`);
      const usageLine = words(usage(name).slice("usage: ".length, usage(name).indexOf("\n\n")));
      assert.ok(given.map(words).includes(usageLine), `the section "## ${name}" has the usage line of the tool: ${usageLine}`);
    }
    assert.deepEqual(NAMES, ["import", "encode", "decode", "check", "pack"]);
  });

  await t.test("no command of the page starts the Python tool as the converter", () => {
    for (const line of commands(page)) {
      assert.equal(/^python\S* -m odrig (import|encode|decode|check|pack)\b/.test(line), false, line);
    }
  });

  await t.test("the setup is Node.js 20 or later and one npm command", () => {
    const setup = section(page, "Setup");
    assert.notEqual(setup, null);
    assert.match(words(setup), /Node\.js 20 or later/);
    assert.ok(commands(setup).includes("npm ci --prefix converter"));
    assert.match(words(setup), /`encode`, `decode`, `check` and `pack` need Node\.js alone/);
  });

  await t.test("the two packages are named with their versions and licences, and what their install leaves", () => {
    const manifest = JSON.parse(read("converter", "package.json"));
    const lock = JSON.parse(read("converter", "package-lock.json"));
    const setup = section(page, "Setup");
    assert.deepEqual(Object.keys(manifest.dependencies).sort(), ["ffmpeg-static", "omggif"]);
    for (const [name, version] of Object.entries(manifest.dependencies)) {
      const licence = lock.packages[`node_modules/${name}`].license;
      assert.match(licence, /^[A-Za-z0-9.-]+$/);
      const row = setup.split("\n").find((line) => line.startsWith(`| \`${name}\` |`));
      assert.notEqual(row, undefined, `the table of packages has a row for ${name}`);
      assert.ok(row.includes(`| ${version} |`), `${name}: version ${version} in ${row}`);
      assert.ok(row.includes(`| ${licence} |`), `${name}: licence ${licence} in ${row}`);
    }
    for (const phrase of ["~/Library/Caches/ffmpeg-static-nodejs", "~/.npm", "converter/node_modules/", "converter/ffmpeg.sha256", "allowScripts"]) {
      assert.ok(setup.includes(phrase), phrase);
    }
  });

  await t.test("the exit statuses are those of the tool", () => {
    const statuses = section(page, "Exit statuses");
    assert.notEqual(statuses, null);
    for (const status of [0, 1, 2, 70]) {
      assert.match(statuses, new RegExp(`\\n\\| ${status} \\| \\S`), `status ${status}`);
    }
    assert.ok(statuses.includes("error: <reason>: <detail>"));
    assert.ok(statuses.includes("decoder-missing"));
    assert.equal(read("docs", "reasons.md").includes("decoder-missing"), false, "decoder-missing is no reason of docs/reasons.md");
  });

  await t.test("the lines check prints are the lines of the page", () => {
    const folder = temporary(t);
    const out = path.join(folder, "hello.odrg");
    assert.equal(runJs(["encode", "animations/hello.json", out]).status, 0);
    const printed = runJs(["check", out]).out;
    const body = section(page, "check");
    assert.ok(body.includes(`\`\`\`\n${printed}\`\`\``), `the section "## check" shows:\n${printed}`);
  });

  await t.test("the example show is packed into build/example-show", () => {
    assert.ok(commands(section(page, "pack")).includes(`${TOOL} pack --show shows/example/show.json --mapping mapping/legs-2.json --sources animations --out build/example-show`));
  });

  await t.test("the three fits, the timeline and the pictures of a GIF are described", () => {
    const body = section(page, "import");
    for (const name of ["fill", "fit", "stretch"]) {
      assert.ok(body.includes(`| \`${name}\` |`), name);
    }
    for (const phrase of ["50 frames-per-second timeline", "`--start`", "`--duration`", "`bad-range`", "disposal", "Pillow"]) {
      assert.ok(body.includes(phrase), phrase);
    }
  });

  await t.test("the library is described: every file of it, how a page loads it and how it is given frames", () => {
    const body = section(page, "The library");
    assert.notEqual(body, null);
    for (const name of fs.readdirSync(path.join(CONVERTER, "lib"))) {
      assert.ok(body.includes(`\`${name}\``), `the section "## The library" names ${name}`);
    }
    for (const phrase of ["converter/lib/index.js", '<script type="module">', "importFrames", "`time`", "`delayMs`", "`rgba`", "Uint8Array"]) {
      assert.ok(body.includes(phrase), phrase);
    }
  });

  await t.test("the test command is given, and no test file is listed", () => {
    const body = section(page, "Tests");
    assert.notEqual(body, null);
    assert.ok(commands(body).includes("npm test --prefix converter"));
    assert.ok(body.includes("`converter/tests/expected/`"));
    assert.equal(body.includes("ODRIG_PYTHON"), false);
    assert.ok(body.includes("ODRIG_CHROME"));
    for (const name of ["docs/converter.md", "docs/python-library.md", "docs/emulator.md", "docs/firmware.md", "README.md"]) {
      assert.equal(/[a-z]+\.test\.js/.test(read(...name.split("/"))), false, `${name} lists a test file`);
    }
  });

  await t.test("what is verified is said, with the versions that were used, and what was not run", () => {
    const body = section(page, "What is verified");
    assert.notEqual(body, null);
    for (const pattern of [/macOS \d+\.\d+/, /Node\.js \d+\.\d+\.\d+/, /npm \d+\.\d+\.\d+/, /Chrome \d+\.\d+\.\d+\.\d+/, /Python \d+\.\d+\.\d+/, /zlib \d+\.\d+\.\d+/, /ffmpeg \d+\.\d+/]) {
      assert.match(body, pattern);
    }
    for (const phrase of ["Windows", "Linux", "not verified"]) {
      assert.ok(body.includes(phrase), phrase);
    }
    assert.match(flat, /Windows and Linux are supported by construction and not verified/);
  });
});

test("docs/python-library.md presents the Python package as a library for the tests and the tools", async (t) => {
  const page = fs.existsSync(path.join(ROOT, "docs", "python-library.md")) ? read("docs", "python-library.md") : "";

  await t.test("it says what the package is for now, and that it converts nothing", () => {
    assert.notEqual(page, "", "there is no docs/python-library.md");
    const opening = words(page.split("\n## ")[0]);
    assert.match(opening, /a library for the tests and the tools/);
    assert.match(opening, /It converts nothing/);
    assert.ok(opening.includes("[converter.md](converter.md)"));
    assert.ok(opening.includes("`converter/tests/expected/`"));
  });

  await t.test("it has the setup, the generators, the test vectors, the tool that writes docs/mapping.md, and its use from Python, and no command that converts", () => {
    for (const heading of ["Setup", "Generators", "Test vectors", "Tests", "From Python"]) {
      assert.notEqual(section(page, heading), null, `docs/python-library.md has no section "## ${heading}"`);
    }
    assert.equal(section(page, "Command line"), null);
    const lines = commands(page);
    for (const name of NAMES) {
      assert.equal(lines.some((line) => line.startsWith(`python -m odrig ${name}`)), false, name);
    }
    for (const line of ["python3 -m venv .venv", "python -m unittest discover -s tests/converter -t .", "python -m tests.converter.build_vectors"]) {
      assert.ok(lines.includes(line), line);
    }
    assert.equal(lines.some((line) => line.includes("pip install")), false);
    for (const name of ["hello_world", "dvd_bounce", "dense"]) {
      assert.ok(lines.some((line) => line.startsWith(`python -m odrig.generators.${name} `)), name);
    }
    assert.ok(page.includes("python -m odrig.mapdoc"));
  });
});

test("the other documents show the JavaScript tool where they convert or pack", async (t) => {
  await t.test("README.md names both pages", () => {
    const text = read("README.md");
    assert.ok(text.includes("(docs/converter.md)"));
    assert.ok(text.includes("(docs/python-library.md)"));
  });

  await t.test("docs/emulator.md and docs/firmware.md pack with the JavaScript tool, and generate with the Python programs", () => {
    for (const name of ["emulator.md", "firmware.md"]) {
      const text = read("docs", name);
      const lines = commands(text).map((line) => line.trim());
      assert.ok(lines.filter((line) => line.startsWith(`${TOOL} pack `)).length >= 3, `${name} packs with ${TOOL}`);
      assert.equal(/python\S* -m odrig (import|encode|decode|check|pack)\b/.test(text), false, `${name} starts the Python tool to convert or pack`);
    }
    const emulator = commands(read("docs", "emulator.md"));
    assert.equal(emulator.filter((line) => line.startsWith("python -m odrig.generators.")).length, 3);
  });

  await t.test("docs/reasons.md says that the converter and the programs of the Python library use its names", () => {
    const opening = words(read("docs", "reasons.md").split("\n## ")[0]);
    assert.ok(opening.includes("[converter.md](converter.md)"));
    assert.ok(opening.includes("[python-library.md](python-library.md)"));
  });

  await t.test("docs/decisions.md states the converter as it is, with a line in its change log", () => {
    const text = read("docs", "decisions.md");
    const conversion = words(section(text, "Conversion"));
    assert.ok(conversion.includes("`converter/`"));
    assert.match(conversion, /JavaScript/);
    assert.match(conversion, /Python/);
    assert.equal(/It will be written in JavaScript/.test(conversion), false);
    const log = text.split("\n## Change log\n")[1];
    const entries = log.trim().split("\n- ").map(words);
    assert.ok(entries.some((entry) => /JavaScript converter/.test(entry)));
  });

  await t.test("no page points at a section of docs/converter.md that has moved", () => {
    for (const name of ["format.md", "mapping.md", "core.md", "emulator.md", "firmware.md"]) {
      const text = words(read("docs", name));
      assert.equal(/\[converter\.md\]\(converter\.md\), "(Generators|Setup|Test vectors|From Python)"/.test(text), false, name);
    }
  });
});
