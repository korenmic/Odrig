// What the tests share: where the repository is, how the two tools are run, temporary
// folders, and data made from a seed.

import {spawnSync} from "node:child_process";
import crypto from "node:crypto";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import {fileURLToPath} from "node:url";

import {errorLine, summary} from "../cli/main.js";
import {errors} from "../lib/index.js";

export const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..", "..");
export const CONVERTER = path.join(ROOT, "converter");
export const TOOL = path.join(CONVERTER, "odrig.js");
export const REFERENCE = path.join(CONVERTER, "tests", "reference.py");

const VENV_PYTHON = path.join(ROOT, ".venv", ...(process.platform === "win32" ? ["Scripts", "python.exe"] : ["bin", "python"]));

// The Python program that runs the reference: `venv`, the one in `.venv` of the repository,
// when it is there, else the program `named`. With neither, the error says how to set one
// up.
export function pythonFrom(venv, named, exists) {
  if (exists(venv)) {
    return venv;
  }
  const given = named !== undefined && named !== "";
  if (given && exists(named)) {
    return named;
  }
  throw new Error(
    `the Python tool is needed for this test: there is no ${venv}` +
      (given ? ` and no ${named}, which ODRIG_PYTHON names` : "") +
      ". Set it up in the repository root with `python3 -m venv .venv` and" +
      " `.venv/bin/python -m pip install -r requirements.txt`, or set ODRIG_PYTHON to a" +
      " Python that has the libraries of requirements.txt.",
  );
}

// `.venv/bin/python` of the repository, or the program the environment variable
// ODRIG_PYTHON names.
export function python() {
  return pythonFrom(VENV_PYTHON, process.env.ODRIG_PYTHON, fs.existsSync);
}

function finished(done, what) {
  if (done.error) {
    throw new Error(`${what} could not be started: ${done.error.message}`);
  }
  return {status: done.status, out: done.stdout, err: done.stderr};
}

function environment(more) {
  const existing = process.env.PYTHONPATH;
  return {
    ...process.env,
    PYTHONPATH: existing ? `${ROOT}${path.delimiter}${existing}` : ROOT,
    PYTHONDONTWRITEBYTECODE: "1",
    ...more,
  };
}

const LARGEST_OUTPUT = 1 << 30;

// Runs `node converter/odrig.js` with the arguments. The result is `{status, out, err}`,
// the two streams as text. `options.cwd` is the folder it is started in, the repository
// root when it is not given; `options.node` is another Node.js to run it with.
export function runJs(argv, options = {}) {
  const done = spawnSync(options.node ?? process.execPath, [options.tool ?? TOOL, ...argv.map(String)], {
    cwd: options.cwd ?? ROOT,
    encoding: "utf8",
    env: environment(options.env),
    maxBuffer: LARGEST_OUTPUT,
  });
  return finished(done, "node");
}

// Runs `python -m odrig` with the arguments, in the same folder as `runJs`.
export function runPython(argv, options = {}) {
  const done = spawnSync(python(), ["-m", options.module ?? "odrig", ...argv.map(String)], {
    cwd: options.cwd ?? ROOT,
    encoding: "utf8",
    env: environment(options.env),
    maxBuffer: LARGEST_OUTPUT,
  });
  return finished(done, "python");
}

// Runs both tools on the same arguments: `{js, python}`.
export function runBoth(argv, options = {}) {
  return {js: runJs(argv, options), python: runPython(argv, options)};
}

// Asks `tests/reference.py` for something only Python has. `input` goes to its standard
// input, as bytes or as a value written as JSON; the result is its standard output as
// bytes.
export function referenceBytes(request, argv = [], input = null) {
  const given = input === null || input instanceof Uint8Array ? input : Buffer.from(JSON.stringify(input));
  const done = spawnSync(python(), [REFERENCE, request, ...argv.map(String)], {
    cwd: ROOT,
    env: environment(),
    input: given ?? undefined,
    maxBuffer: LARGEST_OUTPUT,
  });
  if (done.error) {
    throw new Error(`python could not be started: ${done.error.message}`);
  }
  if (done.status !== 0) {
    throw new Error(`reference.py ${request} ended with status ${done.status}: ${done.stderr.toString("utf8")}`);
  }
  return done.stdout;
}

// As `referenceBytes`, with the standard output read as JSON.
export function reference(request, argv = [], input = null) {
  return JSON.parse(referenceBytes(request, argv, input).toString("utf8"));
}

// A new temporary folder that is removed when the test `t` is over.
export function temporary(t) {
  const folder = fs.realpathSync(fs.mkdtempSync(path.join(os.tmpdir(), "odrig-converter-")));
  t.after(() => fs.rmSync(folder, {recursive: true, force: true}));
  return folder;
}

// Every file under a folder, as paths from the folder with `/` between the parts, sorted.
export function filesUnder(folder) {
  const found = [];
  const walk = (inner) => {
    for (const entry of fs.readdirSync(path.join(folder, inner), {withFileTypes: true})) {
      const name = inner === "" ? entry.name : `${inner}/${entry.name}`;
      if (entry.isDirectory()) {
        found.push(`${name}/`);
        walk(name);
      } else {
        found.push(name);
      }
    }
  };
  walk("");
  return found.sort();
}

// Numbers from a seed: the same seed gives the same numbers on every run and everywhere.
export function numbers(seed) {
  let state = (seed >>> 0) || 0x9e3779b9;
  const next = () => {
    state ^= state << 13;
    state >>>= 0;
    state ^= state >>> 17;
    state ^= state << 5;
    state >>>= 0;
    return state;
  };
  for (let i = 0; i < 8; i += 1) {
    next();
  }
  const below = (limit) => next() % limit;
  return {
    next,
    // A whole number from 0 to limit - 1.
    below,
    // A whole number from low to high, both included.
    between: (low, high) => low + below(high - low + 1),
    // One of the entries of a list.
    pick: (list) => list[below(list.length)],
    // `count` bytes.
    bytes: (count) => {
      const made = new Uint8Array(count);
      for (let i = 0; i < count; i += 1) {
        made[i] = next() >>> 24;
      }
      return made;
    },
  };
}

export function hex(bytes) {
  return Buffer.from(bytes).toString("hex");
}

export function unhex(text) {
  return new Uint8Array(Buffer.from(text, "hex"));
}

// The bytes of a text in UTF-8.
export function utf8(text) {
  return new Uint8Array(Buffer.from(text, "utf8"));
}

// What `python -m odrig check --format <kind>` gives for each of the files, which are given
// as bytes: `{status, out, err}`. The file is named case.json or case.odrg.
export function pythonChecks(kind, files) {
  return reference("check", [kind], files.map(hex)).map(([status, out, err]) => ({status, out, err}));
}

// What the tool says of a file of a kind, "json" or "odrg", named case.json or case.odrg,
// without a new program for each file: `{status, out, err}`, as `check` gives them.
export function libraryCheck(kind, bytes) {
  try {
    return {status: 0, out: errors.naming(`case.${kind}`, () => summary(kind, bytes)), err: ""};
  } catch (error) {
    if (!(error instanceof errors.Rejection)) {
      throw error;
    }
    return {status: 1, out: "", err: errorLine(error)};
  }
}

export function libraryJsonCheck(bytes) {
  return libraryCheck("json", bytes);
}

// Whether the detail of an error line of the Python tool holds text of a library, which
// the JavaScript tool words itself.
export function libraryText(line) {
  return /^error: bad-json: [^:]+: line \d+, column \d+: /.test(line) || /^error: bad-deflate: /.test(line);
}

// Compares what the two tools say of one file: the same status; for an accepted file the
// same standard output; for a rejected one the same reason, and the same error line where
// the Python tool words the detail itself.
export function sameVerdict(assert, ours, theirs, label) {
  assert.equal(ours.status, theirs.status, `${label}: ${ours.err || ours.out} / ${theirs.err || theirs.out}`);
  assert.equal(ours.out, theirs.out, label);
  if (theirs.status === 0) {
    assert.equal(ours.err, "", label);
    return;
  }
  const reason = (line) => line.split(": ")[1];
  assert.equal(reason(ours.err), reason(theirs.err), `${label}: ${ours.err} / ${theirs.err}`);
  if (!libraryText(theirs.err)) {
    assert.equal(ours.err, theirs.err, label);
  }
}

export function sha256(bytes) {
  return crypto.createHash("sha256").update(bytes).digest("hex");
}

// The frame records of a decoded file as reference.py gives them for the Python decoder:
// for each record its duration, its mode byte and the SHA-256 of the picture after it.
export function recordsOf(decoded) {
  return decoded.records.map((record, i) => [record.ms, decoded.modes[i], sha256(record.picture)]);
}

// An animation in the form reference.py reads: the bytes as hexadecimal text and the
// durations as decimal text.
export function forPython(animation, more = {}) {
  return {
    width: animation.width,
    height: animation.height,
    frames: animation.frames.map((frame) => [String(frame.ms), hex(frame.picture)]),
    ...more,
  };
}

// Has a generator of the Python tool write its animation for a mapping file into a folder,
// and gives the path of the JSON frames file. `seconds` is the length of the dense clip.
export function generated(folder, generator, mapping, seconds = null) {
  const canvas = path.basename(mapping, ".json");
  const out = path.join(folder, `${generator}-${canvas}${seconds === null ? "" : `-${seconds}s`}.json`);
  const argv = [out, "--mapping", mapping, ...(seconds === null ? [] : ["--seconds", seconds])];
  const done = runPython(argv, {module: `odrig.generators.${generator}`});
  if (done.status !== 0) {
    throw new Error(`the generator ${generator} ended with status ${done.status}: ${done.err}`);
  }
  return out;
}

const LONG_TIMES = [65535, 65536, 131070, 131071, 200000];

// An animation made from a seed, for the encoder: a canvas of up to 40 x 30, a handful of
// colours or very many, and frames that are new, nearly the frame before, the frame before
// moved by a pixel, the frame before itself, one colour, or a ramp. Now and then a frame
// lasts longer than one frame record can say.
export function animationFrom(seed, {largestWidth = 40, largestHeight = 30} = {}) {
  const from = numbers(seed);
  const width = from.below(4) === 0 ? from.between(1, 3) : from.between(1, largestWidth);
  const height = from.below(4) === 0 ? from.between(1, 3) : from.between(1, largestHeight);
  const pixels = width * height;
  const colourCount = from.pick([1, 2, 3, 16, 200, 256, 257, 100000]);
  const palette = Array.from({length: Math.min(colourCount, 300)}, () => from.bytes(3));
  const colour = () => (colourCount > 300 ? from.bytes(3) : from.pick(palette));
  const fresh = () => {
    const picture = new Uint8Array(3 * pixels);
    for (let pixel = 0; pixel < pixels; pixel += 1) {
      picture.set(colour(), 3 * pixel);
    }
    return picture;
  };
  const frames = [];
  const count = from.between(1, 6);
  for (let i = 0; i < count; i += 1) {
    const kind = i === 0 ? from.pick(["new", "one colour", "ramp"]) : from.pick(["new", "nearly", "nearly", "moved", "same", "one colour", "ramp"]);
    const before = i === 0 ? null : frames[i - 1].picture;
    let picture;
    if (kind === "new") {
      picture = fresh();
    } else if (kind === "nearly") {
      picture = before.slice();
      for (let change = from.between(1, 4); change > 0; change -= 1) {
        picture.set(colour(), 3 * from.below(pixels));
      }
    } else if (kind === "moved") {
      picture = new Uint8Array(3 * pixels);
      picture.set(before.subarray(0, 3 * pixels - 3), 3);
      picture.set(colour(), 0);
    } else if (kind === "same") {
      picture = before.slice();
    } else if (kind === "one colour") {
      picture = new Uint8Array(3 * pixels);
      const one = colour();
      for (let pixel = 0; pixel < pixels; pixel += 1) {
        picture.set(one, 3 * pixel);
      }
    } else {
      picture = new Uint8Array(3 * pixels);
      const start = colour();
      const step = from.between(0, 3);
      for (let pixel = 0; pixel < pixels; pixel += 1) {
        const x = pixel % width;
        picture.set([(start[0] + step * x) & 0xff, start[1], colourCount <= 300 ? start[2] : (start[2] + pixel) & 0xff], 3 * pixel);
      }
    }
    const ms = from.below(10) === 0 ? from.pick(LONG_TIMES) : from.between(1, 300);
    frames.push({ms, picture});
  }
  return {width, height, frames};
}
