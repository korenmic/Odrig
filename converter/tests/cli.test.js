import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import test from "node:test";

import {NAMES, UsageError, parse} from "../cli/arguments.js";
import * as files from "../cli/files.js";
import {SUBCOMMANDS, errorLine, main} from "../cli/main.js";
import {refusal} from "../cli/version.js";
import {errors} from "../lib/index.js";
import {ROOT, python, pythonFrom, runBoth, runJs, runPython, temporary} from "./support.js";

function streams() {
  const written = {out: "", err: ""};
  return {
    written,
    out: {write: (text) => void (written.out += text)},
    err: {write: (text) => void (written.err += text)},
  };
}

// Runs `main` with a table that has `run` under the name of a subcommand.
async function probe(argv, run, name = "decode") {
  const to = streams();
  const status = await main(argv, to, new Map([[name, run]]));
  return {status, ...to.written};
}

const IMPORT = ["import", "clip.mp4", "out.json", "--mapping", "legs.json"];

test("the statuses", async (t) => {
  await t.test("a subcommand that does its work gives status 0 and writes nothing", async () => {
    assert.deepEqual(await probe(["decode", "a", "b"], () => {}), {status: 0, out: "", err: ""});
  });

  await t.test("a subcommand is waited for", async () => {
    let done = false;
    const run = () => new Promise((resolve) => setTimeout(() => resolve((done = true)), 5));
    assert.equal((await probe(["decode", "a", "b"], run)).status, 0);
    assert.equal(done, true);
  });

  await t.test("a rejection gives status 1 and the error line, alone", async () => {
    const reject = () => {
      throw new errors.Rejection(errors.NOT_FOUND, "missing.json: No such file or directory");
    };
    assert.deepEqual(await probe(["decode", "a", "b"], reject), {
      status: 1,
      out: "",
      err: "error: not-found: missing.json: No such file or directory\n",
    });
  });

  await t.test("a rejection of a subcommand that waits gives status 1 as well", async () => {
    const reject = async () => {
      await null;
      throw new errors.Rejection(errors.BAD_RANGE, "clip.mp4: the start is negative");
    };
    assert.deepEqual(await probe(["decode", "a", "b"], reject), {
      status: 1,
      out: "",
      err: "error: bad-range: clip.mp4: the start is negative\n",
    });
  });

  await t.test("a command line that is not understood gives status 2 and a usage message", async () => {
    for (const argv of [[], ["frobnicate"], ["decode", "a"], ["decode", "a", "b", "--no-such-option"]]) {
      const result = await probe(argv, () => assert.fail("the subcommand was run"));
      assert.equal(result.status, 2, argv.join(" "));
      assert.match(result.err, /^usage: node converter\/odrig\.js/);
      assert.match(result.err, /\n.*error: .+\n$/);
      assert.equal(result.out, "");
    }
  });

  await t.test("an error that is no rejection is thrown on", async () => {
    const broken = () => {
      throw new TypeError("a mistake of the program");
    };
    const to = streams();
    await assert.rejects(main(["decode", "a", "b"], to, new Map([["decode", broken]])), TypeError);
    assert.deepEqual(to.written, {out: "", err: ""});
  });

  await t.test("a subcommand that is not in the table is an unknown one", async () => {
    for (const name of NAMES) {
      const to = streams();
      assert.equal(await main([name, "--help"], to, new Map()), 2, name);
      assert.match(to.written.err, /^usage: node converter\/odrig\.js <subcommand>/);
      assert.ok(to.written.err.includes(`there is no subcommand ${name}`));
    }
  });

  await t.test("a subcommand can say that the command line is not understood", async () => {
    const refuse = () => {
      throw new UsageError("the name of x does not tell its format; give --format", "check");
    };
    const result = await probe(["check", "x"], refuse, "check");
    assert.equal(result.status, 2);
    assert.equal(result.out, "");
    assert.match(result.err, /^usage: node converter\/odrig\.js check FILE/);
    assert.ok(result.err.endsWith("node converter/odrig.js check: error: the name of x does not tell its format; give --format\n"));
  });
});

test("the error line", async (t) => {
  await t.test("white space in the detail is written as one space", () => {
    const rejection = new errors.Rejection(errors.BAD_JSON, "  a.json:\n\tline 2,\r\n   column 3:  no value \n");
    assert.equal(errorLine(rejection), "error: bad-json: a.json: line 2, column 3: no value\n");
  });

  await t.test("it is one line whatever the detail holds", () => {
    const separators = [0x0b, 0x0c, 0x1c, 0x1d, 0x1e, 0x1f, 0x85, 0xa0, 0x2028, 0x2029, 0x3000];
    for (const code of separators) {
      const rejection = new errors.Rejection(errors.UNKNOWN_MEMBER, `the file has the unknown member "a${String.fromCharCode(code)}b"`);
      assert.equal(errorLine(rejection), 'error: unknown-member: the file has the unknown member "a b"\n', code.toString(16));
    }
  });

  await t.test("a character that is no white space for Python stays", () => {
    const mark = String.fromCharCode(0xfeff);
    const rejection = new errors.Rejection(errors.UNKNOWN_MEMBER, `a${mark}b`);
    assert.equal(errorLine(rejection), `error: unknown-member: a${mark}b\n`);
  });
});

test("--help", async (t) => {
  await t.test("alone, it names the five subcommands on standard output", async () => {
    for (const flag of ["--help", "-h"]) {
      const to = streams();
      assert.equal(await main([flag], to, new Map()), 0);
      assert.equal(to.written.err, "");
      assert.match(to.written.out, /^usage: node converter\/odrig\.js /);
      for (const name of NAMES) {
        assert.match(to.written.out, new RegExp(`\\n  ${name} +\\S`));
      }
    }
  });

  await t.test("after a subcommand, it gives the arguments and options of the subcommand", async () => {
    const expected = {
      import: ["MEDIA", "OUT.json", "--mapping", "--fit", "fill", "stretch", "--start", "--duration", "SECONDS"],
      encode: ["IN.json", "OUT.odrg", "--uncompressed"],
      decode: ["IN.odrg", "OUT.json"],
      check: ["FILE", "--format", "json", "odrg"],
      pack: ["--show", "--mapping", "--sources", "--out", "--uncompressed"],
    };
    assert.deepEqual(Object.keys(expected), NAMES);
    for (const name of NAMES) {
      for (const argv of [[name, "--help"], [name, "-h"], [name, "a", "--bogus", "--help", "b", "c", "d"]]) {
        const result = await probe(argv, () => assert.fail("the subcommand was run"), name);
        assert.equal(result.status, 0, argv.join(" "));
        assert.equal(result.err, "");
        assert.ok(result.out.startsWith(`usage: node converter/odrig.js ${name}`));
        for (const word of expected[name]) {
          assert.ok(result.out.includes(word), `${name}: ${word}`);
        }
      }
    }
  });
});

test("the parser", async (t) => {
  const values = (argv) => parse(argv).values;
  const refused = (argv, subcommand, words) => {
    assert.throws(
      () => parse(argv),
      (error) => {
        assert.ok(error instanceof UsageError, `${argv.join(" ")}: ${error}`);
        assert.equal(error.subcommand, subcommand, argv.join(" "));
        assert.match(error.message, words, argv.join(" "));
        return true;
      },
    );
  };

  await t.test("it reads the arguments of each subcommand", () => {
    assert.deepEqual(parse([...IMPORT, "--fit", "fit", "--start", "1.5", "--duration", "2"]), {
      subcommand: "import",
      values: {input: "clip.mp4", output: "out.json", mapping: "legs.json", fit: "fit", start: "1.5", duration: "2"},
    });
    assert.deepEqual(values(IMPORT), {
      input: "clip.mp4", output: "out.json", mapping: "legs.json", fit: "fill", start: "0", duration: null,
    });
    assert.deepEqual(values(["encode", "in.json", "out.odrg"]), {input: "in.json", output: "out.odrg", uncompressed: false});
    assert.deepEqual(values(["encode", "in.json", "out.odrg", "--uncompressed"]), {
      input: "in.json", output: "out.odrg", uncompressed: true,
    });
    assert.deepEqual(values(["decode", "in.odrg", "out.json"]), {input: "in.odrg", output: "out.json"});
    assert.deepEqual(values(["check", "a.bin"]), {file: "a.bin", format: null});
    assert.deepEqual(values(["check", "a.bin", "--format", "odrg"]), {file: "a.bin", format: "odrg"});
    assert.deepEqual(values(["pack", "--show", "s", "--mapping", "m", "--sources", "d", "--out", "o"]), {
      show: "s", mapping: "m", sources: "d", out: "o", uncompressed: false,
    });
  });

  await t.test("an option is --name value or --name=value", () => {
    const spaced = values([...IMPORT, "--fit", "stretch", "--start", "3", "--duration", "0.5"]);
    const joined = values(["import", "clip.mp4", "out.json", "--mapping=legs.json", "--fit=stretch", "--start=3", "--duration=0.5"]);
    assert.deepEqual(joined, spaced);
    assert.equal(values(["import", "a.gif", "b.json", "--mapping=a=b.json"]).mapping, "a=b.json");
    assert.equal(values(["import", "a.gif", "b.json", "--mapping="]).mapping, "");
  });

  await t.test("an option is taken in every place among the positional arguments", () => {
    const expected = values([...IMPORT, "--fit", "fit"]);
    const options = [["--mapping", "legs.json"], ["--fit=fit"]];
    const places = [0, 1, 2];
    for (const first of places) {
      for (const second of places) {
        const slots = [[], [], []];
        slots[first].push(...options[0]);
        slots[second].push(...options[1]);
        const argv = ["import", ...slots[0], "clip.mp4", ...slots[1], "out.json", ...slots[2]];
        assert.deepEqual(values(argv), expected, argv.join(" "));
      }
    }
    assert.equal(values(["encode", "--uncompressed", "a", "b"]).uncompressed, true);
    assert.equal(values(["encode", "a", "--uncompressed", "b"]).uncompressed, true);
  });

  await t.test("a minus sign with a number after an option is its value", () => {
    assert.equal(values([...IMPORT, "--start", "-1"]).start, "-1");
    assert.equal(values([...IMPORT, "--start", "-0.5"]).start, "-0.5");
    assert.equal(values([...IMPORT, "--start", "-.5"]).start, "-.5");
    assert.equal(values([...IMPORT, "--duration", "-2"]).duration, "-2");
    assert.equal(values(["import", "--start", "-1", "clip.mp4", "out.json", "--mapping", "legs.json"]).start, "-1");
    assert.equal(values([...IMPORT, "--start=-1"]).start, "-1");
    assert.equal(values(["check", "-1", "--format", "json"]).file, "-1");
  });

  await t.test("a minus sign alone, and a text with a space, are values", () => {
    assert.equal(values(["import", "a.gif", "b.json", "--mapping", "-"]).mapping, "-");
    assert.equal(values(["import", "a.gif", "b.json", "--mapping", "-a b"]).mapping, "-a b");
    assert.equal(values(["encode", "-", "b"]).input, "-");
    assert.equal(values(["encode", "", "b"]).input, "");
  });

  await t.test("an option given twice takes its last value", () => {
    assert.equal(values([...IMPORT, "--fit", "fit", "--fit", "stretch"]).fit, "stretch");
    assert.equal(values([...IMPORT, "--mapping=other.json"]).mapping, "other.json");
    assert.equal(values(["check", "x", "--format", "json", "--format=odrg"]).format, "odrg");
    assert.equal(values(["encode", "a", "b", "--uncompressed", "--uncompressed"]).uncompressed, true);
  });

  await t.test("-- ends the options", () => {
    assert.deepEqual(values(["encode", "--", "--uncompressed", "b"]), {input: "--uncompressed", output: "b", uncompressed: false});
    assert.deepEqual(values(["encode", "a", "--", "b"]), {input: "a", output: "b", uncompressed: false});
    assert.deepEqual(values(["encode", "a", "b", "--"]), {input: "a", output: "b", uncompressed: false});
    assert.deepEqual(values(["decode", "--", "--", "b"]), {input: "--", output: "b"});
  });

  await t.test("seconds are a sign, digits with a fraction, and an exponent", () => {
    for (const text of ["0", "7", "12.5", ".5", "1.", "1e3", "1E3", "2.5e-3", "+1", "-1", "-0.0005", "007", "1e+2"]) {
      assert.equal(values([...IMPORT, `--start=${text}`]).start, text);
      assert.equal(values([...IMPORT, `--duration=${text}`]).duration, text);
    }
    for (const text of ["x", "", ".", "1e", "e3", "1.5.2", "Infinity", "NaN", " 1", "1 ", "1_0", "0x10", "1,5", "--1", "1e10000"]) {
      refused([...IMPORT, `--start=${text}`], "import", /--start .*not a number of seconds/);
      refused([...IMPORT, `--duration=${text}`], "import", /--duration .*not a number of seconds/);
    }
  });

  await t.test("no subcommand and an unknown subcommand are not understood", () => {
    refused([], null, /no subcommand/);
    refused(["frobnicate"], null, /no subcommand frobnicate/);
    refused(["--bogus", "encode", "a", "b"], null, /no subcommand --bogus/);
    refused(["Encode", "a", "b"], null, /no subcommand Encode/);
    assert.throws(() => parse(["encode", "a", "b"], ["decode"]), UsageError);
  });

  await t.test("an unknown option is not understood", () => {
    refused(["encode", "a", "b", "--compressed"], "encode", /no option --compressed/);
    refused(["encode", "a", "b", "-u"], "encode", /no option -u/);
    refused(["decode", "a", "b", "--uncompressed"], "decode", /no option --uncompressed/);
    refused(["check", "a.json", "--fit", "fill"], "check", /no option --fit/);
    refused([...IMPORT, "--map", "other.json"], "import", /no option --map/);
    refused(["encode", "a", "b", "--uncompressed=yes"], "encode", /--uncompressed takes no value/);
    refused(["encode", "--help=1"], "encode", /--help takes no value/);
  });

  await t.test("a missing and an extra positional argument are not understood", () => {
    refused(["encode"], "encode", /IN\.json and OUT\.odrg are missing/);
    refused(["encode", "a"], "encode", /OUT\.odrg is missing/);
    refused(["encode", "a", "b", "c"], "encode", /too many: c/);
    refused(["decode", "a"], "decode", /OUT\.json is missing/);
    refused(["decode", "a", "b", "c", "d"], "decode", /too many: c d/);
    refused(["check"], "check", /FILE is missing/);
    refused(["check", "a.json", "b.json"], "check", /too many: b\.json/);
    refused(["import", "a.gif", "--mapping", "m"], "import", /OUT\.json is missing/);
    refused(["pack", "--show", "s", "--mapping", "m", "--sources", "d", "--out", "o", "extra"], "pack", /too many: extra/);
  });

  await t.test("a required option that is missing is not understood", () => {
    refused(["import", "a.gif", "b.json"], "import", /--mapping is missing/);
    refused(["pack"], "pack", /--show, --mapping, --sources and --out are missing/);
    for (const left of ["--show", "--mapping", "--sources", "--out"]) {
      const argv = ["pack"];
      for (const name of ["--show", "--mapping", "--sources", "--out"]) {
        if (name !== left) {
          argv.push(name, "x");
        }
      }
      refused(argv, "pack", new RegExp(`^${left} is missing$`));
    }
  });

  await t.test("an option without its value is not understood", () => {
    refused(["import", "a.gif", "b.json", "--mapping"], "import", /--mapping is given without its value/);
    refused(["import", "a.gif", "b.json", "--mapping", "--fit", "fit"], "import", /--mapping is given without its value/);
    refused(["import", "a.gif", "b.json", "--mapping", "-x"], "import", /--mapping is given without its value/);
    refused(["import", "a.gif", "b.json", "--mapping", "--"], "import", /--mapping is given without its value/);
    refused(["check", "a", "--format"], "check", /--format is given without its value/);
    refused(["check", "a", "--format", "--help"], "check", /--format is given without its value/);
    refused([...IMPORT, "--start"], "import", /--start is given without its value/);
  });

  await t.test("a --fit or a --format that is not listed is not understood", () => {
    refused([...IMPORT, "--fit", "crop"], "import", /--fit is "crop", which is not fill, fit or stretch/);
    refused([...IMPORT, "--fit", "FILL"], "import", /--fit/);
    refused([...IMPORT, "--fit="], "import", /--fit/);
    refused(["check", "a", "--format", "gif"], "check", /--format is "gif", which is not json or odrg/);
    refused(["check", "a", "--format", "JSON"], "check", /--format/);
    refused(["check", "--format", "bad", "--help"], "check", /--format/);
  });

  await t.test("--help before a mistake wins, and after one that is found at once does not", () => {
    assert.ok(parse(["import", "--help", "--start", "x"]).help.startsWith("usage: node converter/odrig.js import"));
    refused(["import", "--start", "x", "--help"], "import", /--start/);
  });
});

test("the command line as a program", async (t) => {
  await t.test("it is started with node, from any folder", () => {
    const here = runJs([]);
    assert.equal(here.status, 2);
    assert.match(here.err, /^usage: node converter\/odrig\.js/);
    assert.equal(here.out, "");
    const elsewhere = runJs(["--help"], {cwd: temporary(t)});
    assert.equal(elsewhere.status, 0);
    assert.equal(elsewhere.err, "");
    assert.match(elsewhere.out, /^usage: node converter\/odrig\.js/);
  });

  await t.test("it ends with the status of the Python tool", () => {
    for (const argv of [[], ["frobnicate"], ["--help"], ["-h"], ["--bogus"], ["frobnicate", "--help"]]) {
      const {js, python} = runBoth(argv);
      assert.equal(js.status, python.status, argv.join(" "));
      assert.equal(js.out === "", python.out === "", argv.join(" "));
      assert.equal(js.err === "", python.err === "", argv.join(" "));
    }
  });

  await t.test("the table of subcommands holds only names the parser knows", () => {
    for (const name of SUBCOMMANDS.keys()) {
      assert.ok(NAMES.includes(name), name);
    }
  });
});

test("an old version of Node.js is refused", async (t) => {
  await t.test("the check knows which versions are too old", () => {
    for (const version of ["20.0.0", "20.18.0", "22.11.0", "26.5.0", "100.0.0"]) {
      assert.equal(refusal(version), null, version);
    }
    for (const version of ["19.9.0", "18.20.4", "9.11.2", "4.0.0", "0.12.18"]) {
      assert.equal(refusal(version), `node converter/odrig.js needs Node.js 20 or later; this is Node.js ${version}`);
    }
  });

  await t.test("the tool writes one line and ends with status 2", () => {
    const folder = temporary(t);
    const pretend = path.join(folder, "old.mjs");
    fs.writeFileSync(pretend, 'Object.defineProperty(process.versions, "node", {value: "18.20.4"});\n');
    const result = runJs(["--help"], {env: {NODE_OPTIONS: `--import=${pretend}`}});
    assert.deepEqual(result, {
      status: 2,
      out: "",
      err: "node converter/odrig.js needs Node.js 20 or later; this is Node.js 18.20.4\n",
    });
  });

  await t.test("this Node.js is not refused", () => {
    assert.equal(refusal(process.versions.node), null);
    assert.equal(runJs(["--help"]).status, 0);
  });
});

test("reading and writing files", async (t) => {
  const vector = path.join(ROOT, "tests", "vectors", "valid", "one-pixel.rgb.odrg");
  const rejected = (action) => {
    try {
      action();
    } catch (error) {
      assert.ok(error instanceof errors.Rejection, String(error));
      return errorLine(error);
    }
    return assert.fail("nothing was rejected");
  };

  await t.test("read gives the bytes of a file", () => {
    const folder = temporary(t);
    const file = path.join(folder, "a.bin");
    fs.writeFileSync(file, Uint8Array.of(0, 1, 2, 255));
    const bytes = files.read(file);
    assert.ok(bytes instanceof Uint8Array);
    assert.deepEqual([...bytes], [0, 1, 2, 255]);
  });

  await t.test("read of a missing file has the words of the Python tool", () => {
    const folder = temporary(t);
    const missing = path.join(folder, "missing.json");
    const python = runPython(["check", missing]);
    assert.equal(python.status, 1);
    assert.equal(rejected(() => files.read(missing)), python.err);
    assert.equal(python.err, `error: not-found: ${missing}: No such file or directory\n`);
    assert.equal(rejected(() => files.read(missing, errors.MAPPING_MISSING)), `error: mapping-missing: ${missing}: No such file or directory\n`);
  });

  await t.test("read of a folder has the words of the Python tool", () => {
    const folder = temporary(t);
    const python = runPython(["check", "--format", "json", folder]);
    assert.equal(python.status, 1);
    assert.equal(rejected(() => files.read(folder)), python.err);
    assert.equal(python.err, `error: not-found: ${folder}: Is a directory\n`);
  });

  await t.test("read below a file has the words of the Python tool", () => {
    const folder = temporary(t);
    fs.writeFileSync(path.join(folder, "file"), "x");
    const below = path.join(folder, "file", "a.json");
    const python = runPython(["check", below]);
    assert.equal(python.status, 1);
    assert.equal(rejected(() => files.read(below)), python.err);
    assert.equal(python.err, `error: not-found: ${below}: Not a directory\n`);
  });

  await t.test("read of a file that may not be read has the words of the Python tool", {skip: process.platform === "win32" || process.getuid() === 0}, () => {
    const folder = temporary(t);
    const locked = path.join(folder, "locked.json");
    fs.writeFileSync(locked, "{}");
    fs.chmodSync(locked, 0o000);
    const python = runPython(["check", locked]);
    assert.equal(python.status, 1);
    assert.equal(rejected(() => files.read(locked)), python.err);
    assert.equal(python.err, `error: not-found: ${locked}: Permission denied\n`);
  });

  await t.test("write puts the bytes in the file and leaves no part file", () => {
    const folder = temporary(t);
    const file = path.join(folder, "out.bin");
    files.write(file, Uint8Array.of(1, 2, 3));
    assert.deepEqual([...fs.readFileSync(file)], [1, 2, 3]);
    files.write(file, Uint8Array.of(9));
    assert.deepEqual([...fs.readFileSync(file)], [9]);
    assert.deepEqual(fs.readdirSync(folder), ["out.bin"]);
  });

  await t.test("write into a folder that does not exist has the words of the Python tool", () => {
    const folder = temporary(t);
    const out = path.join(folder, "none", "out.json");
    const python = runPython(["decode", vector, out]);
    assert.equal(python.status, 1);
    assert.equal(rejected(() => files.write(out, Uint8Array.of(1))), python.err);
    assert.equal(python.err, `error: cannot-write: ${out}: No such file or directory\n`);
    assert.deepEqual(fs.readdirSync(folder), []);
  });

  await t.test("write over a folder has the words of the Python tool and leaves no part file", () => {
    const folder = temporary(t);
    const out = path.join(folder, "taken");
    fs.mkdirSync(out);
    const python = runPython(["decode", vector, out]);
    assert.equal(python.status, 1);
    assert.deepEqual(fs.readdirSync(folder), ["taken"]);
    assert.equal(rejected(() => files.write(out, Uint8Array.of(1))), python.err);
    assert.equal(python.err, `error: cannot-write: ${out}: Is a directory\n`);
    assert.deepEqual(fs.readdirSync(folder), ["taken"]);
    assert.deepEqual(fs.readdirSync(out), []);
  });

  await t.test("write that fails leaves an existing file as it was", {skip: process.platform === "win32" || process.getuid() === 0}, () => {
    const folder = temporary(t);
    const inner = path.join(folder, "inner");
    fs.mkdirSync(inner);
    const out = path.join(inner, "out.json");
    fs.writeFileSync(out, "before");
    fs.chmodSync(inner, 0o555);
    try {
      const python = runPython(["decode", vector, out]);
      assert.equal(python.status, 1);
      assert.equal(rejected(() => files.write(out, Uint8Array.of(1))), python.err);
      assert.equal(python.err, `error: cannot-write: ${out}: Permission denied\n`);
      assert.equal(fs.readFileSync(out, "utf8"), "before");
      assert.deepEqual(fs.readdirSync(inner), ["out.json"]);
    } finally {
      fs.chmodSync(inner, 0o755);
    }
  });

  await t.test("a failure the system has other words for is named by its code", () => {
    const failure = Object.assign(new Error("ELOOP: too many symbolic links"), {code: "ELOOP", syscall: "open"});
    assert.equal(files.why(failure), "ELOOP");
    assert.equal(files.why(Object.assign(new Error("x"), {code: "ENOTEMPTY", syscall: "rmdir"})), "Directory not empty");
    assert.equal(files.why(Object.assign(new Error("x"), {code: "EEXIST", syscall: "mkdir"})), "File exists");
  });

  await t.test("a mistake of the program is not turned into a rejection", () => {
    const folder = temporary(t);
    assert.throws(() => files.write(path.join(folder, "a"), 12), TypeError);
    assert.throws(() => files.read({}), TypeError);
  });
});

test("the Python tool the suite compares with", async (t) => {
  const venv = path.join(ROOT, ".venv", "bin", "python");

  await t.test("it is .venv of the repository when that is there", () => {
    assert.equal(pythonFrom(venv, undefined, () => true), venv);
    assert.equal(pythonFrom(venv, "/elsewhere/python", () => true), venv);
  });

  await t.test("else it is the program ODRIG_PYTHON names", () => {
    assert.equal(pythonFrom(venv, "/elsewhere/python", (file) => file === "/elsewhere/python"), "/elsewhere/python");
  });

  await t.test("with neither, the error says how to set it up", () => {
    for (const named of [undefined, "", "/elsewhere/python"]) {
      assert.throws(() => pythonFrom(venv, named, () => false), (error) => {
        assert.ok(error.message.includes(venv));
        assert.ok(error.message.includes("python3 -m venv .venv"));
        assert.ok(error.message.includes("pip install -r requirements.txt"));
        assert.ok(error.message.includes("ODRIG_PYTHON"));
        assert.equal(error.message.includes("/elsewhere/python"), named === "/elsewhere/python");
        return true;
      });
    }
  });

  await t.test("on this computer there is one, and it runs the reference", () => {
    assert.ok(fs.existsSync(python()));
    assert.equal(runPython(["--help"]).status, 0);
  });
});
