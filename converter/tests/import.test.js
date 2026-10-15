import assert from "node:assert/strict";
import {spawnSync} from "node:child_process";
import fs from "node:fs";
import {createRequire} from "node:module";
import os from "node:os";
import path from "node:path";
import test, {after, before} from "node:test";

import * as gif from "../cli/gif.js";
import {ending, milliseconds} from "../cli/main.js";
import * as video from "../cli/video.js";
import {errors, jsonframes} from "../lib/index.js";
import {CONVERTER, ROOT, libraryText, numbers, runJs, runJsHere, sha256, storedAnswer, storedRun, storedRuns, utf8} from "./support.js";

const BENCH = path.join(ROOT, "mapping", "legs-2.json");
const TARGET = path.join(ROOT, "mapping", "legs-20.json");
const QUIET = {status: 0, out: "", err: ""};

// A folder with the media of the tests, which the Python package made with Pillow and PyAV
// and which are stored with its answers: the GIFs and the videos of the Python suite's
// import tests among them. The Python tool writes its files there too. What only the
// JavaScript side writes, the files `fresh` names for it and the list of files a program
// of the tests reads, goes into a folder of its own, `ours`. The key of each request of the
// Python tool holds the files of the folder the request names, and those files are not
// the same on every computer: the pictures decoded from a video differ by a colour value
// or two from one build of FFmpeg to another, and the list names the temporary folder.
let folder;
let ours;
let made;
let outputs = 0;

before(() => {
  folder = fs.realpathSync(fs.mkdtempSync(path.join(os.tmpdir(), "odrig-converter-")));
  ours = fs.realpathSync(fs.mkdtempSync(path.join(os.tmpdir(), "odrig-converter-")));
  made = storedAnswer("media", [], {folder});
});

after(() => {
  fs.rmSync(folder, {recursive: true, force: true});
  fs.rmSync(ours, {recursive: true, force: true});
});

function media(name) {
  return path.join(folder, name);
}

function fresh(side) {
  outputs += 1;
  return path.join(side === "js" ? ours : folder, `out-${side}-${outputs}.json`);
}

// Imports with both tools, each into a file of its own: the Python tool for all command
// lines in one Python, the JavaScript tool in this program. A command line is the
// arguments after the output file.
async function imports(cases) {
  const lines = cases.map(([name, options]) => ({name, options, js: fresh("js"), python: fresh("py")}));
  const argv = (line, side) => ["import", media(line.name), line[side], ...line.options];
  const theirs = storedRuns(lines.map((line) => argv(line, "python")));
  const results = [];
  for (let i = 0; i < lines.length; i += 1) {
    const ours = await runJsHere(argv(lines[i], "js"));
    results.push({...lines[i], label: `${lines[i].name} ${lines[i].options.slice(2).join(" ")}`, ours, theirs: theirs[i]});
  }
  return results;
}

function parsed(file) {
  return jsonframes.loads(new Uint8Array(fs.readFileSync(file)));
}

// The largest difference of a colour value between two animations of the same frames.
function largestDifference(a, b) {
  let largest = 0;
  a.frames.forEach((frame, i) => {
    const other = b.frames[i].picture;
    for (let at = 0; at < frame.picture.length; at += 1) {
      const difference = Math.abs(frame.picture[at] - other[at]);
      if (difference > largest) {
        largest = difference;
      }
    }
  });
  return largest;
}

// Compares the rejections of the two tools: the same status and the same reason, and the
// same line wherever the Python tool words the detail itself.
function sameRefusal(ours, theirs, label) {
  assert.equal(ours.status, theirs.status, `${label}: ${ours.err} / ${theirs.err}`);
  assert.equal(ours.out, "", label);
  if (libraryText(theirs.err)) {
    assert.equal(ours.err.split(": ")[1], theirs.err.split(": ")[1], label);
    assert.equal(ours.err.split(": ")[2], theirs.err.split(": ")[2], `${label}: the file that is named`);
  } else {
    assert.equal(ours.err, theirs.err, label);
  }
}

const PARTS = [
  ["--mapping", BENCH],
  ["--mapping", TARGET, "--fit", "fit"],
  ["--mapping", BENCH, "--fit", "stretch"],
  ["--mapping", TARGET, "--start", "0.02", "--duration", "0.06"],
];

test("the media of the tests are made while the suite runs", () => {
  assert.ok(made.gifs.length >= 90, `${made.gifs.length} GIFs`);
  for (const name of ["clip.gif", "delays.gif", "transparent.gif", "rows.gif", "still.gif", "index.gif", "smaller.gif", "disposal-0.gif", "disposal-1.gif", "disposal-2.gif", "disposal-3.gif"]) {
    assert.ok(made.gifs.includes(name), name);
  }
  for (const name of ["clip.mp4", "clip.mov", "late.mp4", "late.mov", "alpha.mov", "three.mp4", "one.mp4"]) {
    assert.ok(made.videos.includes(name), `${name}: ${JSON.stringify(made.skipped)}`);
  }
  const tracked = spawnSync("git", ["ls-files", "converter"], {cwd: ROOT, encoding: "utf8"});
  if (tracked.status === 0) {
    assert.deepEqual(tracked.stdout.split("\n").filter((name) => /\.(gif|mp4|mov|odrg)$/i.test(name)), [], "no media file is tracked");
  }
});

test("importing a GIF gives the JSON frames file of the Python tool, byte for byte", async (t) => {
  const cases = [];
  for (const name of made.gifs) {
    for (const part of PARTS) {
      cases.push([name, part]);
    }
  }
  const results = await imports(cases);
  let written = 0;
  const failing = {};

  await t.test(`${cases.length} imports of ${made.gifs.length} GIFs`, () => {
    for (const {label, ours, theirs, js, python} of results) {
      if (theirs.status === 0) {
        assert.deepEqual(ours, QUIET, label);
        assert.ok(fs.readFileSync(js).equals(fs.readFileSync(python)), `${label}: the two files differ`);
        written += 1;
      } else {
        sameRefusal(ours, theirs, label);
        assert.equal(fs.existsSync(js), false, label);
        failing[theirs.err.split(": ")[1]] = true;
      }
    }
    assert.ok(written >= 300, `${written} files were written`);
    assert.deepEqual(Object.keys(failing), ["bad-range"], "a part of 60 ms from 20 ms is not inside the shortest GIFs");
  });

  for (const name of ["clip.gif", "transparent.gif", "index.gif", "smaller.gif", "disposal-0.gif", "disposal-1.gif", "disposal-2.gif", "disposal-3.gif"]) {
    await t.test(name, () => {
      const mine = results.filter((result) => result.name === name);
      assert.equal(mine.length, PARTS.length);
      for (const {label, ours, js, python} of mine) {
        assert.deepEqual(ours, QUIET, label);
        const a = fs.readFileSync(js);
        const b = fs.readFileSync(python);
        if (!a.equals(b)) {
          const mineFrames = parsed(js);
          const theirFrames = parsed(python);
          assert.deepEqual(mineFrames.frames.map((frame) => frame.ms), theirFrames.frames.map((frame) => frame.ms), `${label}: the durations`);
          const at = mineFrames.frames.findIndex((frame, i) => !jsonframes.same(frame.picture, theirFrames.frames[i].picture));
          assert.fail(`${label}: frame ${at + 1} has other pixels than the Python tool's`);
        }
      }
    });
  }

  await t.test("the delays 30, 50, 70 and 0 of clip.gif give frames of 40, 40, 80 and 100 ms", () => {
    const {js} = results.find((result) => result.name === "clip.gif" && result.options.length === 2);
    assert.deepEqual(parsed(js).frames.map((frame) => frame.ms), [40, 40, 80, 100]);
    assert.deepEqual([parsed(js).width, parsed(js).height], [60, 6]);
  });
});

test("importing a video gives the frames of the Python tool, no colour value more than 3 apart", async (t) => {
  const cases = [];
  for (const name of made.videos) {
    for (const part of PARTS) {
      cases.push([name, part]);
    }
  }
  const results = await imports(cases);
  let largest = 0;
  let identical = 0;
  let written = 0;

  for (const name of made.videos) {
    await t.test(name, () => {
      for (const {label, ours, theirs, js, python} of results.filter((result) => result.name === name)) {
        if (theirs.status !== 0) {
          sameRefusal(ours, theirs, label);
          continue;
        }
        assert.deepEqual(ours, QUIET, label);
        const a = parsed(js);
        const b = parsed(python);
        assert.deepEqual([a.width, a.height], [b.width, b.height], label);
        assert.equal(a.frames.length, b.frames.length, `${label}: the number of frames`);
        assert.deepEqual(a.frames.map((frame) => frame.ms), b.frames.map((frame) => frame.ms), `${label}: the durations`);
        const difference = largestDifference(a, b);
        assert.ok(difference <= 3, `${label}: a colour value differs by ${difference}`);
        largest = Math.max(largest, difference);
        identical += fs.readFileSync(js).equals(fs.readFileSync(python)) ? 1 : 0;
        written += 1;
      }
    });
  }

  await t.test("what was compared", (inner) => {
    inner.diagnostic(`${written} imports of ${made.videos.length} videos: the largest difference of a colour value is ${largest}; ${identical} files have the bytes of the Python tool's`);
    for (const [name, reason] of Object.entries(made.skipped)) {
      inner.diagnostic(`${name} could not be made here: ${reason}`);
    }
    assert.ok(written >= 40, `${written} files were written`);
  });

  await t.test("the frames of clip.mp4 are 40 ms each, in the order they are shown", () => {
    const {js} = results.find((result) => result.name === "clip.mp4" && result.options.length === 2);
    const animation = parsed(js);
    assert.deepEqual(animation.frames.map((frame) => frame.ms), new Array(10).fill(40));
    assert.equal(new Set(animation.frames.map((frame) => Buffer.from(frame.picture).toString("hex"))).size, 10);
  });

  await t.test("time is counted from the first frame of a video that does not begin at time zero", () => {
    for (const name of ["late.mp4", "late.mov"]) {
      const {js} = results.find((result) => result.name === name && result.options.length === 2);
      assert.deepEqual(parsed(js).frames.map((frame) => frame.ms), [40, 40, 40, 40], name);
    }
  });

  await t.test("the transparent half of a mov is black", () => {
    const {js} = results.find((result) => result.name === "alpha.mov" && result.options[2] === "--fit" && result.options[3] === "stretch");
    const {picture} = parsed(js).frames[0];
    assert.deepEqual([...picture.subarray(0, 3)], [255, 0, 0], "the left half shows the frame's colour");
    assert.deepEqual([...picture.subarray(3 * 59, 3 * 60)], [0, 0, 0], "the right half is transparent");
  });

  await t.test("a file with sound only has no video stream, and sound beside a video is ignored", () => {
    if (!made.videos.includes("only-sound.mp4") || !made.videos.includes("sound.mp4")) {
      return;
    }
    const only = results.find((result) => result.name === "only-sound.mp4" && result.options.length === 2);
    assert.equal(only.ours.err, `error: unreadable-media: ${media("only-sound.mp4")}: the file has no video stream\n`);
    assert.deepEqual(only.ours, only.theirs);
    const beside = results.find((result) => result.name === "sound.mp4" && result.options.length === 2);
    assert.deepEqual(parsed(beside.js).frames.map((frame) => frame.ms), [40, 40, 40, 40, 40]);
  });
});

test("import as a program", async (t) => {
  const run = (name, out, options = []) => ["import", media(name), out, "--mapping", BENCH, ...options];

  await t.test("it writes what the Python tool writes, and nothing on its streams", () => {
    for (const name of ["clip.gif", "smaller.gif", "clip.mp4", "clip.mov", "alpha.mov"]) {
      const ours = fresh("js");
      const theirs = fresh("py");
      assert.deepEqual(runJs(run(name, ours)), QUIET, name);
      assert.deepEqual(storedRun(run(name, theirs)), QUIET, name);
      assert.ok(fs.readFileSync(ours).equals(fs.readFileSync(theirs)), name);
      assert.equal(fs.existsSync(`${ours}.part`), false);
    }
  });

  await t.test("the same file and the same options give the same bytes on every run", () => {
    for (const name of ["clip.gif", "clip.mp4"]) {
      const first = fresh("js");
      const second = fresh("js");
      assert.deepEqual(runJs(run(name, first, ["--fit", "fit", "--start", "0.04"])), QUIET);
      assert.deepEqual(runJs(run(name, second, ["--fit", "fit", "--start", "0.04"])), QUIET);
      assert.ok(fs.readFileSync(first).equals(fs.readFileSync(second)), name);
    }
  });

  await t.test("an output that is there is replaced, and stays as it was when the media is refused", () => {
    const out = fresh("js");
    fs.writeFileSync(out, "before");
    assert.equal(runJs(run("clip.gif", out, ["--start", "9"])).status, 1);
    assert.equal(fs.readFileSync(out, "utf8"), "before");
    assert.deepEqual(runJs(run("clip.gif", out)), QUIET);
    assert.equal(parsed(out).frames.length, 4);
    assert.equal(fs.existsSync(`${out}.part`), false);
  });

  await t.test("paths are taken from the folder the tool is started in", () => {
    const inFolder = {cwd: folder};
    const ours = runJs(["import", "clip.gif", "relative-js.json", "--mapping", BENCH], inFolder);
    const theirs = storedRun(["import", "clip.gif", "relative-py.json", "--mapping", BENCH], inFolder);
    assert.deepEqual(ours, QUIET);
    assert.deepEqual(theirs, QUIET);
    assert.ok(fs.readFileSync(media("relative-js.json")).equals(fs.readFileSync(media("relative-py.json"))));
    const missing = ["import", "absent.gif", "x.json", "--mapping", BENCH];
    assert.deepEqual(runJs(missing, inFolder), storedRun(missing, inFolder));
    assert.equal(runJs(missing, inFolder).err, "error: not-found: absent.gif: there is no such file\n");
  });

  await t.test("it ends with the status of the Python tool", () => {
    const gifFile = media("clip.gif");
    const lines = [
      ["import"],
      ["import", gifFile],
      ["import", gifFile, fresh("x")],
      ["import", gifFile, fresh("x"), "--mapping"],
      ["import", gifFile, fresh("x"), "--mapping", BENCH, "extra"],
      ["import", gifFile, fresh("x"), "--mapping", BENCH, "--fit", "crop"],
      ["import", gifFile, fresh("x"), "--mapping", BENCH, "--fit"],
      ["import", gifFile, fresh("x"), "--mapping", BENCH, "--start", "soon"],
      ["import", gifFile, fresh("x"), "--mapping", BENCH, "--duration", "1e"],
      ["import", gifFile, fresh("x"), "--mapping", BENCH, "--speed", "2"],
      ["import", "--help"],
      ["import", gifFile, fresh("x"), "--mapping", BENCH, "--start", "-1"],
      ["import", gifFile, fresh("x"), "--mapping", BENCH, "--start", "-0.5"],
      ["import", gifFile, fresh("x"), "--mapping", BENCH, "--start=-1"],
      ["import", gifFile, fresh("x"), "--mapping", BENCH, "--duration", "-1"],
      ["import", gifFile, fresh("x"), "--mapping", BENCH, "--duration", "0"],
      ["import", "--start", "-1", gifFile, "--mapping", BENCH, fresh("x")],
      ["import", gifFile, fresh("x"), "--mapping", BENCH, "--start", "0.04", "--start", "0"],
      ["import", "--fit=stretch", "--mapping", BENCH, gifFile, fresh("x")],
    ];
    const statuses = new Set();
    for (const argv of lines) {
      const ours = runJs(argv);
      const theirs = storedRun(argv);
      const label = argv.slice(1).map((word) => word.replace(folder, "<folder>").replace(ROOT, "<root>")).join(" ");
      assert.equal(ours.status, theirs.status, `${label}: ${ours.err} / ${theirs.err}`);
      if (theirs.status === 1) {
        assert.deepEqual(ours, theirs, label);
      } else if (theirs.status === 2) {
        assert.match(ours.err, /^usage: node converter\/odrig\.js import MEDIA OUT\.json --mapping MAPPING/, label);
        assert.equal(ours.out, "");
      }
      statuses.add(theirs.status);
    }
    assert.deepEqual([...statuses].sort(), [0, 1, 2]);
  });
});

test("the checks of import run in the order of the Python tool", async (t) => {
  const write = (name, bytes) => {
    fs.writeFileSync(media(name), bytes);
    return name;
  };
  const clip = () => fs.readFileSync(media("clip.gif"));
  const badMapping = write("legs-bad.json", "{}");
  fs.mkdirSync(media("folder.mp4"));
  fs.mkdirSync(media("folder.gif"));
  const text = "this is not a media file\n".repeat(20);
  const png = Buffer.from("89504e470d0a1a0a0000000d4948445200000001000000010802000000907753de0000000c4944415408d763f8cfc000000301010018dd8db00000000049454e44ae426082", "hex");
  const missing = path.join(folder, "no-legs.json");
  const good = ["--mapping", BENCH];

  const cases = [
    ["a mapping file that is not there, and a media name without a known ending", [write("picture.png", png), ["--mapping", missing]], "mapping-missing"],
    ["a mapping file that is not there, and a media file that is not there", ["absent.mp4", ["--mapping", missing]], "mapping-missing"],
    ["a mapping file that breaks a rule, and a media file that is not there", ["absent.mp4", ["--mapping", media(badMapping)]], "mapping-malformed"],
    ["a mapping file that breaks a rule, and a negative start", ["clip.gif", ["--mapping", media(badMapping), "--start", "-1"]], "mapping-malformed"],
    ["a PNG picture", ["picture.png", good], "unsupported-media"],
    ["a name that ends in .avi, of a file that is not there", ["clip.avi", good], "unsupported-media"],
    ["a name without an ending", [write("clip", clip()), good], "unsupported-media"],
    ["a name with an ending after .gif", [write("clip.gif.txt", clip()), good], "unsupported-media"],
    ["a name that is the ending without its point", [write("mp4", clip()), good], "unsupported-media"],
    ["a name that is the ending alone", [write(".gif", clip()), good], "unsupported-media"],
    ["a name that ends in a point", [write("clip.", clip()), good], "unsupported-media"],
    ["a name with the ending of a still picture and a negative start", ["picture.png", [...good, "--start", "-1"]], "unsupported-media"],
    ["a file that is not there", ["absent.mp4", good], "not-found"],
    ["a GIF that is not there", ["absent.gif", good], "not-found"],
    ["a folder with the name of a video", ["folder.mp4", good], "not-found"],
    ["a folder with the name of a GIF", ["folder.gif", good], "not-found"],
    ["a file that is not there, and a negative start", ["absent.mov", [...good, "--start", "-1"]], "not-found"],
    ["a negative start", ["clip.mp4", [...good, "--start", "-0.001"]], "bad-range"],
    ["a duration of 0", ["clip.mp4", [...good, "--duration", "0"]], "bad-range"],
    ["a duration that rounds to 0", ["clip.gif", [...good, "--duration", "0.0004"]], "bad-range"],
    ["a negative duration", ["clip.gif", [...good, "--duration", "-2"]], "bad-range"],
    ["a negative start and a duration of 0", ["clip.gif", [...good, "--start", "-1", "--duration", "0"]], "bad-range"],
    ["a negative start of a file that is no video", [write("text.mp4", text), [...good, "--start", "-1"]], "bad-range"],
    ["a duration of 0 of a file that is no GIF", [write("text.gif", text), [...good, "--duration", "0"]], "bad-range"],
    ["a text file named mp4", ["text.mp4", good], "unreadable-media"],
    ["a text file named mov", [write("text.mov", text), good], "unreadable-media"],
    ["a text file named gif", ["text.gif", good], "unreadable-media"],
    ["an empty file named mp4", [write("empty.mp4", ""), good], "unreadable-media"],
    ["an empty file named gif", [write("empty.gif", ""), good], "unreadable-media"],
    ["a GIF cut off in its first picture", [write("cut.gif", clip().subarray(0, 40)), good], "unreadable-media"],
    ["a PNG picture named gif", [write("really-png.gif", png), good], "unreadable-media"],
    ["a video named gif", [write("really-mp4.gif", fs.readFileSync(media("clip.mp4"))), good], "unreadable-media"],
    ["a text file named mp4, with a start beyond any media", ["text.mp4", [...good, "--start", "1000"]], "unreadable-media"],
    ["a start at the end of the media", ["clip.mp4", [...good, "--start", "0.4"]], "bad-range"],
    ["a start beyond the end of the media", ["clip.gif", [...good, "--start", "30"]], "bad-range"],
    ["a part that ends after the media", ["clip.mp4", [...good, "--start", "0.2", "--duration", "0.201"]], "bad-range"],
    ["a part that ends after the media, of a GIF", ["clip.gif", [...good, "--duration", "0.251"]], "bad-range"],
    ["a start of twenty digits", ["clip.gif", [...good, "--start", "9".repeat(20)]], "bad-range"],
  ];
  const results = await imports(cases.map(([, given]) => given));
  const details = new Set();
  for (let i = 0; i < cases.length; i += 1) {
    const [label, , reason] = cases[i];
    await t.test(label, () => {
      const {ours, theirs, js} = results[i];
      assert.equal(theirs.status, 1, `${label}: ${theirs.err}`);
      assert.equal(theirs.err.split(": ")[1], reason, theirs.err);
      sameRefusal(ours, theirs, label);
      assert.equal(fs.existsSync(js), false);
      assert.equal(fs.existsSync(`${js}.part`), false);
      details.add(theirs.err.split(": ").slice(3).join(": ").replace(/\d+(\.\d+)?/g, "N").trim());
    });
  }

  await t.test("the four cases of bad-range are among them, with the details of the Python tool", () => {
    for (const detail of [
      "the start is negative",
      "the duration is not above N",
      "the start of N ms is not before the end of the media at N ms",
      "the part ends at N ms, after the end of the media at N ms",
    ]) {
      assert.ok(details.has(detail), `${detail}: ${[...details].join(" | ")}`);
    }
  });

  const accepted = [
    ["a part that ends exactly at the end of the media", ["clip.mp4", [...good, "--start", "0.2", "--duration", "0.2"]]],
    ["a GIF named mp4", [write("really-gif.mp4", clip()), good]],
    ["the ending in capital letters, of a video", [write("CLIP.MP4", fs.readFileSync(media("clip.mp4"))), good]],
    ["the ending in mixed letters, of a mov", [write("Clip.MoV", fs.readFileSync(media("clip.mov"))), good]],
    ["the ending in capital letters, of a GIF", [write("CLIP.GIF", clip()), good]],
    ["a name with two points", [write("my.clip.v2.gif", clip()), good]],
    ["a name that begins with a point", [write(".hidden.gif", clip()), good]],
    ["a name with a space and letters of another script", [write("סרט one.gif", clip()), good]],
  ];
  const whole = await imports(accepted.map(([, given]) => given));
  for (let i = 0; i < accepted.length; i += 1) {
    await t.test(accepted[i][0], () => {
      const {ours, theirs, js, python} = whole[i];
      assert.deepEqual(theirs, QUIET);
      assert.deepEqual(ours, QUIET);
      assert.ok(fs.readFileSync(js).equals(fs.readFileSync(python)));
    });
  }

  await t.test("the ending of a name is what follows the last point of its last part", () => {
    const cases2 = {"a.MP4": ".mp4", "a.b/c": "", "a.b/c.Gif": ".gif", ".mp4": "", "..mp4": "", "x/.mov": "", "a.": ".", "a": "", "": "", "a.tar.gz": ".gz", "...a.gif": ".gif"};
    for (const [name, expected] of Object.entries(cases2)) {
      assert.equal(ending(name), expected, JSON.stringify(name));
    }
  });
});

test("seconds on the command line are rounded to whole milliseconds as the Python tool rounds them", async (t) => {
  await t.test("for the texts of --start and --duration", () => {
    const texts = ["0", "0.04", ".04", "4e-2", "0.0405", "0.0395", "0.0404999", "+0.02", "1.", "0.0005", "0.0004", "-0.0005", "-0.0004", "12.3456", "1e3", "007.5"];
    const theirs = storedAnswer("milliseconds", [], texts);
    texts.forEach((text, i) => {
      assert.equal(String(milliseconds(text)), theirs[i], text);
    });
    assert.equal(milliseconds("0.0405"), 41);
    assert.equal(milliseconds("-0.0005"), -1);
    assert.equal(milliseconds("1e30"), 10n ** 33n);
  });

  await t.test("for imports of a part given in every form", async () => {
    const parts = [["0.04", "0.1"], [".04", ".1"], ["4e-2", "1e-1"], ["0.0405", "0.1"], ["0.0395", "0.1005"], ["+0.02", "0.2"], ["0.1", null], ["0.0004", "0.0005"], ["0.3994", null], ["0.3996", null]];
    const cases = parts.map(([start, duration]) => ["clip.mp4", ["--mapping", BENCH, "--start", start, ...(duration === null ? [] : ["--duration", duration])]]);
    for (const {label, ours, theirs, js, python} of await imports(cases)) {
      assert.equal(ours.status, theirs.status, `${label}: ${ours.err} / ${theirs.err}`);
      if (theirs.status === 0) {
        assert.ok(fs.readFileSync(js).equals(fs.readFileSync(python)), label);
      } else {
        assert.deepEqual(ours, theirs, label);
      }
    }
  });
});

test("both command lines read a mapping file the same way, through import", async (t) => {
  const texts = storedAnswer("mappings");
  const names = Object.keys(texts).sort();

  await t.test("every mapping file that is as the format says gives the same canvas and the same file", async () => {
    const cases = names.map((name) => {
      fs.writeFileSync(media(`mapping-${name}.json`), texts[name]);
      return ["corners.gif", ["--mapping", media(`mapping-${name}.json`), "--fit", "stretch"]];
    });
    const results = await imports(cases);
    results.forEach(({ours, theirs, js, python}, i) => {
      assert.deepEqual(theirs, QUIET, names[i]);
      assert.deepEqual(ours, QUIET, names[i]);
      assert.ok(fs.readFileSync(js).equals(fs.readFileSync(python)), names[i]);
    });
    const bench = parsed(results[names.indexOf("legs-2")].js);
    const target = parsed(results[names.indexOf("legs-20")].js);
    assert.deepEqual([bench.width, bench.height], [60, 6]);
    assert.deepEqual([target.width, target.height], [60, 60]);
  });

  await t.test("the corners of a picture are the corners of the canvas, for row legs and for column legs", async () => {
    const [rows, columns] = await imports([["corners.gif", ["--mapping", media("mapping-two-and-four-rows.json"), "--fit", "stretch"]], ["corners.gif", ["--mapping", media("mapping-two-and-four-columns.json"), "--fit", "stretch"]]]);
    for (const {js, python} of [rows, columns]) {
      assert.ok(fs.readFileSync(js).equals(fs.readFileSync(python)));
    }
  });

  await t.test("a mapping file that breaks a rule gives the same error line", async () => {
    const broken = [
      "{",
      "[]",
      '{"version": 2}',
      '{"version": 1, "legs": []}',
      '{"version": 1, "width": 4, "height": 4, "legs": []}',
      '{"version": 1, "width": 0, "legs": [{"leg": 1, "pin": 1, "first_led": "left", "rows": [1]}]}',
      '{"version": 1, "width": 4, "legs": []}',
      '{"version": 1, "width": 4, "legs": [{"leg": 1, "pin": 1, "first_led": "top", "rows": [1]}]}',
      '{"version": 1, "height": 4, "legs": [{"leg": 1, "pin": 1, "first_led": "top", "rows": [1]}]}',
      '{"version": 1, "height": 4, "legs": [{"leg": 1, "pin": 1, "first_led": "top", "columns": [2]}]}',
      '{"version": 1, "width": 4, "legs": [{"leg": 1, "pin": 1, "first_led": "left", "rows": [1]}, {"leg": 1, "pin": 2, "first_led": "left", "rows": [2]}]}',
      '{"version": 1, "width": 65535, "legs": [{"leg": 1, "pin": 1, "first_led": "left", "rows": [1, 2]}]}',
    ];
    const cases = broken.map((text, i) => {
      fs.writeFileSync(media(`broken-${i}.json`), text);
      return ["clip.gif", ["--mapping", media(`broken-${i}.json`)]];
    });
    for (const {label, ours, theirs} of await imports(cases)) {
      assert.equal(theirs.err.split(": ")[1], "mapping-malformed", theirs.err);
      if (/: bad-json: line \d+, column \d+: /.test(theirs.err)) {
        assert.equal(ours.status, 1);
        assert.match(ours.err, /^error: mapping-malformed: .*: bad-json: line \d+, column \d+: /);
      } else {
        assert.deepEqual(ours, theirs, label);
      }
    }
  });
});

test("the pictures of a GIF are built by the rules of the format as browsers apply them", async (t) => {
  const require = createRequire(import.meta.url);
  const {GifReader, GifWriter} = require("omggif");
  const palette = [0x000000, 0xff0000, 0x00ff00, 0x0000ff];
  // A GIF with a screen of 4 x 2 and the frames given: each a rectangle, the palette
  // indexes of its pixels, and the options of the package's writer.
  const build = (frames, width = 4, height = 2) => {
    const bytes = new Uint8Array(4096);
    const writer = new GifWriter(bytes, width, height, {palette});
    for (const {x, y, w, h, indexes, ...options} of frames) {
      writer.addFrame(x, y, w, h, Uint8Array.from(indexes), options);
    }
    return bytes.subarray(0, writer.end());
  };
  const pictures = (bytes) => {
    const file = media(`built-${(outputs += 1)}.gif`);
    fs.writeFileSync(file, bytes);
    return [...gif.frames(file, GifReader)].map((frame) => ({delayMs: frame.delayMs, pixels: Array.from({length: frame.width * frame.height}, (unused, i) => (frame.rgba[4 * i + 3] === 0 ? "." : "KRGB"[palette.indexOf((frame.rgba[4 * i] << 16) | (frame.rgba[4 * i + 1] << 8) | frame.rgba[4 * i + 2])])).join("")}));
  };
  const full = (index) => new Array(8).fill(index);

  await t.test("a frame is drawn into its rectangle and the rest stays", () => {
    const frames = pictures(build([{x: 0, y: 0, w: 4, h: 2, indexes: full(1), delay: 3}, {x: 1, y: 0, w: 2, h: 1, indexes: [2, 2], delay: 5}]));
    assert.deepEqual(frames, [{delayMs: 30, pixels: "RRRRRRRR"}, {delayMs: 50, pixels: "RGGRRRRR"}]);
  });

  await t.test("a pixel with the transparent index is left as it is", () => {
    const frames = pictures(build([{x: 0, y: 0, w: 4, h: 2, indexes: full(1)}, {x: 0, y: 0, w: 4, h: 2, indexes: [0, 2, 0, 2, 2, 0, 2, 0], transparent: 0}]));
    assert.deepEqual(frames.map((frame) => frame.pixels), ["RRRRRRRR", "RGRGGRGR"]);
  });

  await t.test("where nothing was drawn the screen is transparent", () => {
    const frames = pictures(build([{x: 2, y: 1, w: 2, h: 1, indexes: [3, 3]}]));
    assert.deepEqual(frames.map((frame) => frame.pixels), ["......BB"]);
    const transparentOnly = pictures(build([{x: 0, y: 0, w: 4, h: 2, indexes: [0, 1, 0, 1, 1, 0, 1, 0], transparent: 0}]));
    assert.deepEqual(transparentOnly.map((frame) => frame.pixels), [".R.RR.R."]);
  });

  await t.test("disposal 0 and 1 leave the frame, 2 makes its rectangle transparent, 3 gives back what was there", () => {
    const sequence = (disposal) => pictures(build([
      {x: 0, y: 0, w: 4, h: 2, indexes: full(1), disposal: 1},
      {x: 1, y: 0, w: 2, h: 2, indexes: [2, 2, 2, 2], disposal},
      {x: 3, y: 1, w: 1, h: 1, indexes: [3], disposal: 1},
    ])).map((frame) => frame.pixels);
    assert.deepEqual(sequence(0), ["RRRRRRRR", "RGGRRGGR", "RGGRRGGB"]);
    assert.deepEqual(sequence(1), ["RRRRRRRR", "RGGRRGGR", "RGGRRGGB"]);
    assert.deepEqual(sequence(2), ["RRRRRRRR", "RGGRRGGR", "R..RR..B"]);
    assert.deepEqual(sequence(3), ["RRRRRRRR", "RGGRRGGR", "RRRRRRRB"]);
  });

  await t.test("a disposal of the last frame changes no picture, and one of the first frame clears the screen for the second", () => {
    const frames = pictures(build([{x: 0, y: 0, w: 4, h: 2, indexes: full(1), disposal: 2}, {x: 0, y: 0, w: 1, h: 1, indexes: [2], disposal: 3}])).map((frame) => frame.pixels);
    assert.deepEqual(frames, ["RRRRRRRR", "G......."]);
  });

  await t.test("a delay is the file's hundredths of a second in milliseconds, and the frames are decoded one by one", () => {
    const bytes = build([{x: 0, y: 0, w: 4, h: 2, indexes: full(1), delay: 0}, {x: 0, y: 0, w: 4, h: 2, indexes: full(2), delay: 1}, {x: 0, y: 0, w: 4, h: 2, indexes: full(3), delay: 700}]);
    assert.deepEqual(pictures(bytes).map((frame) => frame.delayMs), [0, 10, 7000]);
    const file = media("lazy.gif");
    fs.writeFileSync(file, bytes);
    const iterator = gif.frames(file, GifReader);
    fs.rmSync(file);
    assert.throws(() => iterator.next(), {reason: "unreadable-media"}, "the file is read when the first frame is asked for");
  });

  await t.test("a frame that reaches beyond the screen, and a file that is no GIF, are unreadable-media", () => {
    const beyond = build([{x: 0, y: 0, w: 4, h: 2, indexes: full(1)}]);
    const copy = beyond.slice();
    const descriptor = copy.indexOf(0x2c, 13 + 12);
    copy[descriptor + 1] = 2;
    assert.throws(() => pictures(copy), {reason: "unreadable-media", detail: "the GIF cannot be decoded: frame 1 reaches beyond the screen of 4 x 2"});
    assert.deepEqual(pictures(utf8("GIF89a")), [], "a file that ends after its first six bytes has no frame");
    assert.throws(() => pictures(utf8("not a GIF at all")), {reason: "unreadable-media", detail: "the GIF cannot be decoded: Invalid GIF 87a/89a header."});
    assert.throws(() => pictures(new Uint8Array(0)), {reason: "unreadable-media"});
  });
});

// Damaged videos that one tool reads and the other refuses. The two tools decode with
// different builds of FFmpeg, and one may recover a picture from a file the other gives up on.
const KNOWN_DIFFERENCES = [
  "alpha.mov byte 1137 changed by 245: JavaScript reads it, Python refuses it",
];

test("a damaged or cut media file ends the import with a result or with unreadable-media, and never keeps it busy", async (t) => {
  const from = numbers(808);
  const copies = (name, limit) => {
    const bytes = fs.readFileSync(media(name));
    const ending2 = path.extname(name);
    const files = [];
    const lengths = bytes.length <= limit ? Array.from({length: bytes.length}, (unused, i) => i) : Array.from({length: limit}, (unused, i) => Math.floor((bytes.length * i) / limit));
    for (const length of lengths) {
      const file = media(`cut-${(outputs += 1)}${ending2}`);
      fs.writeFileSync(file, bytes.subarray(0, length));
      files.push({file, label: `${name} cut after ${length}`});
    }
    const places = bytes.length <= limit ? Array.from({length: bytes.length}, (unused, i) => i) : Array.from({length: limit}, () => from.below(bytes.length));
    for (const at of places) {
      for (const change of bytes.length <= limit ? [1 << (at % 8), from.between(1, 255)] : [from.between(1, 255)]) {
        const damaged = Buffer.from(bytes);
        damaged[at] ^= change;
        const file = media(`damaged-${(outputs += 1)}${ending2}`);
        fs.writeFileSync(file, damaged);
        files.push({file, label: `${name} byte ${at} changed by ${change}`});
      }
    }
    return files;
  };

  await t.test("every cut and every changed byte of four GIFs, in a program with a limit of two minutes", () => {
    const files = ["clip.gif", "smaller.gif", "disposal-2.gif", "disposal-3.gif"].flatMap((name) => copies(name, 400)).map((copy) => copy.file);
    assert.ok(files.length > 3000, `${files.length} files`);
    const list = path.join(ours, "gifs.json");
    fs.writeFileSync(list, JSON.stringify(files));
    const done = spawnSync(process.execPath, [path.join(CONVERTER, "tests", "gifs.js"), list], {encoding: "utf8", timeout: 120000, maxBuffer: 1 << 28});
    assert.equal(done.error, undefined, `the program did not come to an end: ${done.error}`);
    assert.equal(done.status, 0, done.stderr);
    const results = JSON.parse(done.stdout);
    assert.equal(results.length, files.length);
    const counts = {frames: 0, none: 0, refused: 0};
    for (const result of results) {
      if (result.reason === undefined) {
        assert.ok(Number.isInteger(result.frames) && result.frames >= 0, JSON.stringify(result));
        counts[result.frames === 0 ? "none" : "frames"] += 1;
      } else {
        assert.equal(result.reason, "unreadable-media");
        assert.match(result.detail, /^the GIF cannot be decoded: \S/);
        counts.refused += 1;
      }
    }
    assert.ok(counts.frames > 300 && counts.refused > 1000, JSON.stringify(counts));
  });

  await t.test("80 cuts and 80 changed bytes of an mp4 and of a mov", async () => {
    const files = ["clip.mp4", "alpha.mov"].flatMap((name) => copies(name, 40));
    const counts = {written: 0, refused: 0};
    const ours = [];
    for (const {file} of files) {
      const out = fresh("js");
      const result = await runJsHere(["import", file, out, "--mapping", BENCH]);
      if (result.status === 0) {
        assert.ok(parsed(out).frames.length >= 1);
        counts.written += 1;
      } else {
        assert.equal(result.status, 1, result.err);
        assert.match(result.err, /^error: unreadable-media: .+: (the video cannot be decoded: \S|the file has no video stream|the file holds no picture|a frame has no presentation time|the frames are not in the order of their times)/);
        assert.equal(fs.existsSync(out), false);
        counts.refused += 1;
      }
      ours.push(result);
    }
    assert.equal(counts.written + counts.refused, 160);
    assert.ok(counts.written >= 20 && counts.refused >= 60, JSON.stringify(counts));

    // The Python tool reads the same files, each of them, and ends with a file or a reason.
    const theirs = storedRuns(files.map(({file}) => ["import", file, fresh("py"), "--mapping", BENCH]));
    const reason = (err) => (/^error: ([a-z-]+): /.exec(err) ?? [])[1];
    const different = [];
    files.forEach(({label}, i) => {
      assert.ok(theirs[i].status === 0 || theirs[i].status === 1, `${label}: the Python tool ended with ${theirs[i].status}: ${theirs[i].err}`);
      assert.doesNotMatch(theirs[i].err, /Traceback/, label);
      if (ours[i].status === 1 && theirs[i].status === 1) {
        assert.equal(reason(theirs[i].err), reason(ours[i].err), label);
      } else if (ours[i].status !== theirs[i].status) {
        different.push(`${label}: ${ours[i].status === 0 ? "JavaScript reads it, Python refuses it" : "Python reads it, JavaScript refuses it"}`);
      }
    });
    assert.deepEqual(different, KNOWN_DIFFERENCES);
  });
});

test("the packages", async (t) => {
  const manifest = JSON.parse(fs.readFileSync(path.join(CONVERTER, "package.json"), "utf8"));
  const lock = JSON.parse(fs.readFileSync(path.join(CONVERTER, "package-lock.json"), "utf8"));

  await t.test("package.json names ffmpeg-static and omggif at one exact version each, and no other", () => {
    assert.deepEqual(manifest.dependencies, {"ffmpeg-static": "5.3.0", omggif: "1.0.10"});
    assert.equal(manifest.devDependencies, undefined);
    assert.equal(manifest.private, true);
    assert.equal(manifest.type, "module");
    assert.deepEqual(manifest.allowScripts, {"ffmpeg-static@5.3.0": true}, "the one install script that npm may run");
    assert.equal(lock.packages["node_modules/ffmpeg-static"].version, "5.3.0");
    assert.equal(lock.packages["node_modules/omggif"].version, "1.0.10");
    assert.ok(fs.readFileSync(path.join(ROOT, ".gitignore"), "utf8").split("\n").includes("/converter/node_modules/"));
  });

  await t.test("the decoder program is the one in converter/node_modules/, whatever FFMPEG_BIN says", () => {
    const program = video.programPath();
    assert.equal(program, path.join(CONVERTER, "node_modules", "ffmpeg-static", process.platform === "win32" ? "ffmpeg.exe" : "ffmpeg"));
    assert.deepEqual(video.program(), {file: program});
    assert.ok(video.argumentsFor("a.mp4").includes("file:a.mp4"));
    const out = fresh("js");
    const elsewhere = runJs(["import", media("clip.mp4"), out, "--mapping", BENCH], {env: {FFMPEG_BIN: "/usr/bin/false", PATH: "/nowhere"}});
    assert.deepEqual(elsewhere, QUIET);
    assert.equal(parsed(out).frames.length, 10);
  });

  await t.test("the installed decoder program has the checksum that is tracked for this platform", (inner) => {
    const lines = fs.readFileSync(path.join(CONVERTER, "ffmpeg.sha256"), "utf8").trim().split("\n");
    const entries = new Map(lines.map((line) => {
      const match = /^([0-9a-f]{64}) {2}([a-z0-9]+-[a-z0-9_]+)$/.exec(line);
      assert.notEqual(match, null, `a line of ffmpeg.sha256: ${line}`);
      return [match[2], match[1]];
    }));
    const platform = `${process.platform}-${process.arch}`;
    if (!entries.has(platform)) {
      inner.diagnostic(`ffmpeg.sha256 has no entry for ${platform}; the installed program is ${sha256(fs.readFileSync(video.programPath()))}`);
      return;
    }
    assert.equal(sha256(fs.readFileSync(video.programPath())), entries.get(platform));
    const version = spawnSync(video.programPath(), ["-version"], {encoding: "utf8"});
    inner.diagnostic(version.stdout.split("\n")[0]);
    assert.match(version.stdout, /^ffmpeg version \d/);
  });
});

test("a tool without its packages", async (t) => {
  const copy = path.join(fs.realpathSync(fs.mkdtempSync(path.join(os.tmpdir(), "odrig-converter-"))), "converter");
  t.after(() => fs.rmSync(path.dirname(copy), {recursive: true, force: true}));
  fs.mkdirSync(copy);
  for (const name of ["cli", "lib"]) {
    fs.cpSync(path.join(CONVERTER, name), path.join(copy, name), {recursive: true});
  }
  for (const name of ["odrig.js", "package.json"]) {
    fs.copyFileSync(path.join(CONVERTER, name), path.join(copy, name));
  }
  const bare = {tool: path.join(copy, "odrig.js")};
  const command = `npm ci --prefix ${copy}`;

  await t.test("import of a GIF and of a video end with decoder-missing and the command that installs the packages", () => {
    const out = path.join(copy, "out.json");
    assert.deepEqual(runJs(["import", media("clip.gif"), out, "--mapping", BENCH], bare), {
      status: 1,
      out: "",
      err: `error: decoder-missing: the package omggif, which reads GIF files, is not installed; install it with: ${command}\n`,
    });
    for (const name of ["clip.mp4", "clip.mov"]) {
      assert.deepEqual(runJs(["import", media(name), out, "--mapping", BENCH], bare), {
        status: 1,
        out: "",
        err: `error: decoder-missing: the package ffmpeg-static, which reads mp4 and mov files, is not installed; install it with: ${command}\n`,
      });
    }
    assert.equal(fs.existsSync(out), false);
  });

  await t.test("the checks before the content come first", () => {
    const out = path.join(copy, "out.json");
    assert.equal(runJs(["import", media("clip.gif"), out, "--mapping", media("no-legs.json")], bare).err.split(": ")[1], "mapping-missing");
    assert.equal(runJs(["import", media("picture.png"), out, "--mapping", BENCH], bare).err.split(": ")[1], "unsupported-media");
    assert.equal(runJs(["import", media("absent.mp4"), out, "--mapping", BENCH], bare).err.split(": ")[1], "not-found");
  });

  await t.test("a package that is there without its program is decoder-missing as well", () => {
    fs.mkdirSync(path.join(copy, "node_modules", "ffmpeg-static"), {recursive: true});
    const result = runJs(["import", media("clip.mp4"), path.join(copy, "out.json"), "--mapping", BENCH], bare);
    assert.equal(result.status, 1);
    assert.equal(result.err, `error: decoder-missing: the package ffmpeg-static is installed without its program ${path.join(copy, "node_modules", "ffmpeg-static", process.platform === "win32" ? "ffmpeg.exe" : "ffmpeg")}; install it with: ${command}\n`);
    fs.rmSync(path.join(copy, "node_modules"), {recursive: true});
  });

  await t.test("encode, decode, check and pack run without node_modules", () => {
    const real = (name) => path.join(copy, `real-${name}`);
    const lone = (name) => path.join(copy, `bare-${name}`);
    const hello = path.join(ROOT, "animations", "hello.json");
    for (const [make, name] of [[real, "real"], [lone, "bare"]]) {
      const options = name === "bare" ? bare : {};
      assert.deepEqual(runJs(["encode", hello, make("hello.odrg")], options), QUIET);
      assert.deepEqual(runJs(["decode", make("hello.odrg"), make("hello.json")], options), QUIET);
      assert.deepEqual(runJs(["pack", "--show", path.join(ROOT, "shows", "example", "show.json"), "--mapping", BENCH, "--sources", path.join(ROOT, "animations"), "--out", make("show")], options), QUIET);
    }
    assert.ok(fs.readFileSync(real("hello.odrg")).equals(fs.readFileSync(lone("hello.odrg"))));
    assert.ok(fs.readFileSync(lone("hello.json")).equals(fs.readFileSync(hello)));
    assert.deepEqual(fs.readdirSync(lone("show")).sort(), fs.readdirSync(real("show")).sort());
    const checked = runJs(["check", lone("hello.odrg")], bare);
    assert.equal(checked.status, 0);
    assert.equal(checked.out, runJs(["check", real("hello.odrg")]).out.replace("real-", "bare-"));
    assert.equal(fs.existsSync(path.join(copy, "node_modules")), false);
  });
});

test("the words of a failure of the setup", () => {
  assert.equal(video.DECODER_MISSING, "decoder-missing");
  assert.ok(!Object.values(errors).includes("decoder-missing"), "it is no reason of docs/reasons.md");
  assert.equal(video.installCommand(), `npm ci --prefix ${CONVERTER}`);
});
