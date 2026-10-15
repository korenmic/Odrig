// What the tests share: where the repository is, how the tool is run, the stored answers
// of the Python package, temporary folders, and data made from a seed.

import {spawnSync} from "node:child_process";
import crypto from "node:crypto";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import {fileURLToPath} from "node:url";

import {errorLine, main, summary} from "../cli/main.js";
import {errors} from "../lib/index.js";
import {answered} from "./stored.js";

export {EXPECTED, asStored, expected, inStoredForm, isDigest, storedLength} from "./stored.js";

export const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..", "..");
export const CONVERTER = path.join(ROOT, "converter");
export const TOOL = path.join(CONVERTER, "odrig.js");

function finished(done, what) {
  if (done.error) {
    throw new Error(`${what} could not be started: ${done.error.message}`);
  }
  return {status: done.status, out: done.stdout, err: done.stderr};
}

const LARGEST_OUTPUT = 1 << 30;
// How long a program the tests start may run before it is ended and the test fails.
const LONGEST_RUN_MS = 600000;

// Runs `node converter/odrig.js` with the arguments. The result is `{status, out, err}`,
// the two streams as text. `options.cwd` is the folder it is started in, the repository
// root when it is not given; `options.node` is another Node.js to run it with.
export function runJs(argv, options = {}) {
  const done = spawnSync(options.node ?? process.execPath, [options.tool ?? TOOL, ...argv.map(String)], {
    cwd: options.cwd ?? ROOT,
    encoding: "utf8",
    env: {...process.env, ...options.env},
    maxBuffer: LARGEST_OUTPUT,
    stdio: ["ignore", "pipe", "pipe"],
    timeout: LONGEST_RUN_MS,
  });
  return finished(done, "node");
}

// What the Python tool, `python -m odrig`, did with the arguments in the same folder as
// `runJs`: `{status, out, err}`, from its stored answer, with the files it wrote written
// again.
export function storedRun(argv, options = {}) {
  const words = argv.map(String);
  const cwd = options.cwd ?? ROOT;
  const module = options.module ?? "odrig";
  const kind = module === "odrig" ? "cli" : "generators";
  return answered(kind, {argv: words, module, cwd, env: options.env ?? null}, [{cwd, argv: words}]);
}

// Runs the tool on the arguments and gives what the Python tool did with them:
// `{js, python}`.
export function runJsAndStored(argv, options = {}) {
  return {js: runJs(argv, options), python: storedRun(argv, options)};
}

// The stored answer of the Python package to a request: a question only it could answer,
// such as what zlib makes of a stream. The input is the value the request gave, and the
// result is the value of the answer.
export function storedAnswer(request, argv = [], input = null) {
  const commands = request === "run" ? input.commands.map((words) => ({cwd: input.cwd, argv: words})) : [];
  return answered(request, {argv: argv.map(String), input}, commands);
}

// A new temporary folder that is removed when the test `t` is over.
export function temporary(t) {
  const folder = fs.realpathSync(fs.mkdtempSync(path.join(os.tmpdir(), "odrig-converter-")));
  t.after(() => fs.rmSync(folder, {recursive: true, force: true}));
  return folder;
}

// Whether the tests may take a right away from themselves: not as root, who keeps every
// right on macOS and Linux.
export const RIGHTS_HOLD = process.getuid?.() !== 0;

// Everyone, in the access list of a file on Windows.
const EVERYONE = "*S-1-1-0";

function icacls(...argv) {
  const program = path.join(process.env.SystemRoot ?? "C:\\Windows", "System32", "icacls.exe");
  const done = spawnSync(program, argv, {encoding: "utf8"});
  if (done.error || done.status !== 0) {
    throw new Error(`icacls ${argv.join(" ")}: ${done.error ?? `${done.stdout}${done.stderr}`}`);
  }
}

// Takes away the right to read a file, `"read"`, or to make files in a folder, `"write"`:
// on macOS and Linux by the mode, on Windows by an entry of the access list that denies
// it to everyone. `allowAgain` gives it back.
export function forbid(target, right) {
  if (process.platform !== "win32") {
    fs.chmodSync(target, right === "read" ? 0o000 : 0o555);
    return;
  }
  icacls(target, "/deny", `${EVERYONE}:(${right === "read" ? "RD" : "WD,AD"})`);
}

export function allowAgain(target) {
  if (process.platform !== "win32") {
    fs.chmodSync(target, fs.statSync(target).isDirectory() ? 0o755 : 0o644);
    return;
  }
  icacls(target, "/remove:d", EVERYONE);
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

// What `python -m odrig check --format <kind>` gave for each of the files, which are given
// as bytes: `{status, out, err}`. The file was named case.json or case.odrg.
export function storedChecks(kind, files) {
  return storedAnswer("check", [kind], files.map(hex)).map(([status, out, err]) => ({status, out, err}));
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
  return (
    /^error: bad-json: [^:]+: line \d+, column \d+: /.test(line) ||
    /^error: bad-deflate: /.test(line) ||
    /^error: unreadable-media: .*: the (GIF|video) cannot be decoded: /.test(line)
  );
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

// The frame records of a decoded file in the form of the stored answers of the Python
// decoder: for each record its duration, its mode byte and the SHA-256 of the picture
// after it.
export function recordsOf(decoded) {
  return decoded.records.map((record, i) => [record.ms, decoded.modes[i], sha256(record.picture)]);
}

// An animation in the form the requests to the Python package gave it: the bytes as
// hexadecimal text and the durations as decimal text.
export function forPython(animation, more = {}) {
  return {
    width: animation.width,
    height: animation.height,
    frames: animation.frames.map((frame) => [String(frame.ms), hex(frame.picture)]),
    ...more,
  };
}

// Writes into a folder the animation a generator of the Python package wrote for a mapping
// file, from its stored answer, and gives the path of the JSON frames file. `seconds` is
// the length of the dense clip.
export function storedGenerated(folder, generator, mapping, seconds = null) {
  const canvas = path.basename(mapping, ".json");
  const out = path.join(folder, `${generator}-${canvas}${seconds === null ? "" : `-${seconds}s`}.json`);
  const argv = [out, "--mapping", mapping, ...(seconds === null ? [] : ["--seconds", seconds])];
  const done = storedRun(argv, {module: `odrig.generators.${generator}`});
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

// What the Python tool did with command lines run one after the other in one Python, in
// the folder `cwd`: for each `{status, out, err}`, from the stored answer, with the files
// they wrote written again.
export function storedRuns(commands, cwd = ROOT) {
  const results = storedAnswer("run", [], {cwd, commands: commands.map((argv) => argv.map(String))});
  return results.map(([status, out, err]) => ({status, out, err}));
}

// Runs one command line of the JavaScript tool in this program: `{status, out, err}`. Paths
// are taken from the folder this program runs in.
export async function runJsHere(argv) {
  const written = {out: "", err: ""};
  const streams = {
    out: {write: (text) => void (written.out += text)},
    err: {write: (text) => void (written.err += text)},
  };
  const status = await main(argv.map(String), streams);
  return {status, ...written};
}
