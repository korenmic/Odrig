import assert from "node:assert/strict";
import test from "node:test";

import {errors, strictjson} from "../lib/index.js";
import {libraryJsonCheck, sameVerdict, storedChecks, utf8} from "./support.js";

const BACKSLASH = String.fromCharCode(0x5c);
const ESCAPED = (hex) => `${BACKSLASH}u${hex}`;
const MARK = Uint8Array.of(0xef, 0xbb, 0xbf);

// A JSON frames file of one black pixel, with its members given as texts.
function file({version = "1", width = "1", height = "1", ms = "1", pixels = "[0]", extra = ""} = {}) {
  return `{"version": ${version}, "width": ${width}, "height": ${height}, "frames": [{"ms": ${ms}, "pixels": ${pixels}}]${extra}}`;
}

function joined(...parts) {
  const total = parts.reduce((sum, part) => sum + part.length, 0);
  const whole = new Uint8Array(total);
  let at = 0;
  for (const part of parts) {
    whole.set(part, at);
    at += part.length;
  }
  return whole;
}

const NINES = "9".repeat(30);
const DEEP = (levels) => "[".repeat(levels) + "]".repeat(levels);

// Each text with what it is. Both tools read every one of them.
const TEXTS = [
  ["a file of one pixel", file()],
  ["white space of every kind between the tokens", ` \t\r\n{ "version" :\t1 ,\n"width":1,\r\n"height" : 1, "frames" : [ { "ms" : 1 , "pixels" : [ 0 ] } ] } \n\t\r `],
  ["member names spelled with escapes", file().replace('"version"', `"${ESCAPED("0076")}ersion"`).replace('"ms"', `"m${ESCAPED("0073")}"`)],
  ["an escaped solidus and quote in an unknown name", file({extra: `, "a${BACKSLASH}/b${BACKSLASH}"c${BACKSLASH}${BACKSLASH}d": 1`})],
  ["every simple escape in an unknown name", file({extra: `, "${BACKSLASH}b${BACKSLASH}f${BACKSLASH}n${BACKSLASH}r${BACKSLASH}t": 1`})],
  ["a pair of escapes that spells one character", file({extra: `, "${ESCAPED("D83D")}${ESCAPED("de00")}": 1`})],
  ["a character outside the basic plane", file({extra: `, "${String.fromCodePoint(0x1f600)}": 1`})],
  ["text in two scripts in an unknown name", file({extra: ', "שלום grüße": 1'})],

  ["nothing", ""],
  ["white space only", " \n\t "],
  ["bytes that are not UTF-8", joined(utf8(file()), Uint8Array.of(0xff))],
  ["a character cut short", joined(utf8('{"a": "'), Uint8Array.of(0xe2, 0x82), utf8('"}'))],
  ["a character written too long", joined(utf8('{"a": "'), Uint8Array.of(0xc0, 0x80), utf8('"}'))],
  ["half of a pair in UTF-8", joined(utf8('{"a": "'), Uint8Array.of(0xed, 0xa0, 0x80), utf8('"}'))],
  ["a byte-order mark", joined(MARK, utf8(file()))],
  ["a byte-order mark alone", MARK],
  ["a byte-order mark after the first character", joined(utf8(" "), MARK, utf8(file()))],
  ["UTF-16", Uint8Array.of(0xff, 0xfe, 0x7b, 0x00, 0x7d, 0x00)],

  ["two values", `${file()}${file()}`],
  ["text after the value", `${file()} x`],
  ["a comma after the value", `${file()},`],
  ["an object that does not end", file().slice(0, -1)],
  ["an array that does not end", '{"version": 1, "frames": ['],
  ["a comma before the end of an object", file({extra: ","})],
  ["a comma before the end of an array", file({pixels: "[0,]"})],
  ["two commas", file({pixels: "[0,,0]"})],
  ["no comma between members", '{"version": 1 "width": 1}'],
  ["no colon", '{"version" 1}'],
  ["a name without quotes", "{version: 1}"],
  ["a name in single quotes", "{'version': 1}"],
  ["a number as a name", '{1: 1}'],
  ["a comment", `${file()} // done`],
  ["a comment inside", '{/* */"version": 1}'],
  ["a closing bracket of the wrong kind", '{"version": [1}'],
  ["a closing bracket alone", "]"],

  ["NaN as a pixel", file({pixels: "[NaN]"})],
  ["Infinity as a pixel", file({pixels: "[Infinity]"})],
  ["-Infinity as a pixel", file({pixels: "[-Infinity]"})],
  ["NaN as the whole text", "NaN"],
  ["NaN before a mistake", '{"version": NaN, "version" 1'],
  ["NaN with a letter after it", '{"version": NaNx}'],
  ["Infinity as the version", file({version: "Infinity"})],
  ["nan in small letters", file({version: "nan"})],
  ["-NaN", file({version: "-NaN"})],

  ["a member named twice", file({extra: ', "version": 1'})],
  ["a member named twice with other values", '{"version": 2, "version": 1}'],
  ["a member named twice, once by an escape", file({extra: `, "${ESCAPED("0076")}ersion": 1`})],
  ["a member of a frame named twice", file({pixels: '[0], "ms": 1'})],
  ["an unknown member named twice", '{"a": 1, "b": 2, "a": 3}'],
  ["a member named twice in an inner object first", '{"a": {"b": 1, "b": 2}, "a": 3}'],
  ["a name of two lines named twice", `{"a${BACKSLASH}n  b": 1, "a${BACKSLASH}n  b": 2}`],
  ["a member named twice before NaN", '{"a": 1, "a": NaN}'],
  ["a member named twice in an object that does not end", '{"a": 1, "a": 2'],
  ["an empty name named twice", '{"": 1, "": 2}'],
  ["three names of which the last two are the same", '{"x": 1, "y": 2, "y": 3, "x": 4}'],

  ["a number with a leading zero", file({version: "01"})],
  ["a number that ends in a point", file({version: "1."})],
  ["a number that begins with a point", file({version: ".5"})],
  ["a number with a plus sign", file({version: "+1"})],
  ["an exponent without digits", file({version: "1e"})],
  ["an exponent with a sign and no digits", file({version: "1e+"})],
  ["a minus sign alone", file({version: "-"})],
  ["a hexadecimal number", file({version: "0x1"})],
  ["a number with an underscore", file({version: "1_0"})],
  ["minus zero one", file({version: "-01"})],

  ["a tab inside a string", '{"a\tb": 1}'],
  ["a line feed inside a string", '{"a\nb": 1}'],
  ["an escape JSON does not have", `{"a${BACKSLASH}x41": 1}`],
  ["an escape of three digits", `{"a${ESCAPED("12G")}4": 1}`],
  ["an escape at the end of the text", `{"a${BACKSLASH}`],
  ["a string that does not end", '{"version'],
  ["True with a capital letter", file({version: "True"})],
  ["null cut short", file({version: "nul"})],
  ["true with a letter after it", file({version: "truex"})],

  ["a version with a fraction of zero", file({version: "1.0"})],
  ["a version with an exponent", file({version: "1e0"})],
  ["a version with a capital exponent", file({version: "1E0"})],
  ["a version that is a string", file({version: '"1"'})],
  ["a version that is true", file({version: "true"})],
  ["a version that is null", file({version: "null"})],
  ["a version of minus zero", file({version: "-0"})],
  ["a width with a fraction", file({width: "1.5"})],
  ["a width with a negative exponent", file({width: "10e-1"})],
  ["a pixel with a fraction of zero", file({pixels: "[0.0]"})],
  ["a pixel of minus zero", file({pixels: "[-0]"})],
  ["ms of minus zero", file({ms: "-0"})],
  ["ms with a fraction", file({ms: "20.0"})],

  ["a version just below 2 to the power 53", file({version: "9007199254740991"})],
  ["a version of 2 to the power 53", file({version: "9007199254740992"})],
  ["a version just above 2 to the power 53", file({version: "9007199254740993"})],
  ["a negative version beyond 2 to the power 53", file({version: "-9007199254740993"})],
  ["a version of 30 digits", file({version: NINES})],
  ["a version of 31 digits", file({version: `${NINES}9`})],
  ["a negative version of 31 characters", file({version: `-${NINES}`})],
  ["a negative version of 30 characters", file({version: `-${NINES.slice(1)}`})],
  ["a version of 400 digits", file({version: "7".repeat(400)})],
  ["ms just above 2 to the power 53", file({ms: "9007199254740993"})],
  ["ms of 30 digits", file({ms: NINES})],
  ["ms of 31 digits", file({ms: `1${"0".repeat(30)}`})],
  ["ms of 5000 digits", file({ms: "8".repeat(5000)})],
  ["a width and a height of 21 digits", file({width: `1${"0".repeat(20)}`, height: `1${"0".repeat(20)}`})],
  ["a width beyond 2 to the power 53", file({width: "9007199254740993"})],
  ["a width of 31 digits", file({width: `${NINES}9`, height: "3"})],
  ["a negative width of 40 digits", file({width: `-${"4".repeat(40)}`})],
  ["a pixel beyond 2 to the power 53", file({pixels: "[9007199254740993]"})],
  ["a negative pixel of 31 characters", file({pixels: `[-${NINES}]`})],

  ["arrays nested 512 deep", DEEP(512)],
  ["a pixel that is arrays nested 508 deep", file({pixels: `[${DEEP(508)}]`})],
  ["arrays nested a million deep", "[".repeat(1000000)],
];

// Texts of which the two tools give the same reason and another detail: a detail of the
// Python tool that cannot be written to a terminal as it is, and texts nested deeper than
// 512 levels and less deep than Python's own limit, which the Python tool reads on.
const REASON_ONLY = [
  ["half of a pair spelled by an escape", file({extra: `, "${ESCAPED("d800")}": 1`})],
  ["arrays nested 513 deep", DEEP(513)],
  ["arrays nested 600 deep", DEEP(600)],
];

function bytesOf(text) {
  return typeof text === "string" ? utf8(text) : text;
}

test("both tools say the same of every text", async (t) => {
  const theirs = storedChecks("json", TEXTS.map(([, text]) => bytesOf(text)));
  for (let i = 0; i < TEXTS.length; i += 1) {
    const [label, text] = TEXTS[i];
    await t.test(label, () => {
      sameVerdict(assert, libraryJsonCheck(bytesOf(text)), theirs[i], label);
    });
  }

  await t.test("the table has accepted texts, texts that are not JSON, and texts with other reasons", () => {
    const reasons = theirs.map((result) => (result.status === 0 ? "accepted" : result.err.split(": ")[1]));
    assert.ok(reasons.filter((reason) => reason === "accepted").length >= 6);
    assert.ok(reasons.filter((reason) => reason === "bad-json").length >= 50);
    for (const reason of ["bad-type", "bad-version", "out-of-range", "bad-pixel-count", "unknown-member"]) {
      assert.ok(reasons.includes(reason), reason);
    }
  });

  await t.test("the same reason where the two tools have another detail", () => {
    const results = storedChecks("json", REASON_ONLY.map(([, text]) => bytesOf(text)));
    REASON_ONLY.forEach(([label, text], i) => {
      const ours = libraryJsonCheck(bytesOf(text));
      assert.equal(ours.status, results[i].status, label);
      assert.equal(ours.err.split(": ")[1], results[i].err.split(": ")[1], label);
    });
  });
});

test("what the reader gives", async (t) => {
  const read = (text) => strictjson.loads(bytesOf(text));
  const refused = (text, detail) => {
    assert.throws(() => read(text), (error) => {
      assert.ok(error instanceof errors.Rejection, String(error));
      assert.equal(error.reason, "bad-json");
      if (detail instanceof RegExp) {
        assert.match(error.detail, detail);
      } else {
        assert.equal(error.detail, detail);
      }
      return true;
    });
  };

  await t.test("an object is a Map in the order of the text, an array an Array", () => {
    const value = read('{"b": [1, [2, {}], []], "a": {"z": null, "y": true, "x": false}, "": "text"}');
    assert.ok(value instanceof Map);
    assert.deepEqual([...value.keys()], ["b", "a", ""]);
    assert.deepEqual(value.get("b"), [1, [2, new Map()], []]);
    assert.deepEqual([...value.get("a")], [["z", null], ["y", true], ["x", false]]);
    assert.equal(value.get(""), "text");
  });

  await t.test("a value of any kind may be the whole text", () => {
    assert.equal(read("7"), 7);
    assert.equal(read(' "a" '), "a");
    assert.equal(read("null"), null);
    assert.equal(read("true"), true);
    assert.deepEqual(read("[]"), []);
    assert.deepEqual(read("{}"), new Map());
  });

  await t.test("a name that an object of JavaScript has anyway is a member like any other", () => {
    const value = read('{"__proto__": 1, "constructor": 2, "toString": 3}');
    assert.deepEqual([...value], [["__proto__", 1], ["constructor", 2], ["toString", 3]]);
  });

  await t.test("a string holds what its escapes spell", () => {
    const text = `"a${BACKSLASH}"b${BACKSLASH}${BACKSLASH}c${BACKSLASH}/d${BACKSLASH}be${BACKSLASH}ff${BACKSLASH}ng${BACKSLASH}rh${BACKSLASH}ti${ESCAPED("00e9")}${ESCAPED("D83D")}${ESCAPED("DE00")}${ESCAPED("d800")}"`;
    const expected = ['a"b', BACKSLASH, "c/d", "\be", "\ff", "\ng", "\rh", "\ti", String.fromCharCode(0xe9, 0xd83d, 0xde00, 0xd800)].join("");
    assert.equal(read(text), expected);
  });

  await t.test("an integer keeps every digit up to 30 characters", () => {
    assert.equal(read("0"), 0);
    assert.ok(Object.is(read("-0"), 0));
    assert.ok(Object.is(read("[-0]")[0], 0));
    assert.equal(read("-17"), -17);
    assert.equal(read("123456789012345"), 123456789012345);
    assert.equal(read("-12345678901234"), -12345678901234);
    assert.equal(read("9007199254740991"), 9007199254740991);
    assert.equal(read("-9007199254740991"), -9007199254740991);
    assert.equal(read("9007199254740992"), 9007199254740992n);
    assert.equal(read("9007199254740993"), 9007199254740993n);
    assert.equal(read("-9007199254740993"), -9007199254740993n);
    assert.equal(read(NINES), BigInt(NINES));
    assert.equal(read(`-${NINES.slice(1)}`), -BigInt(NINES.slice(1)));
  });

  await t.test("an integer of more than 30 characters counts as plus or minus 10 to the power 30", () => {
    assert.equal(read(`${NINES}9`), 10n ** 30n);
    assert.equal(read(`-${NINES}`), -(10n ** 30n));
    assert.equal(read("1".repeat(100000)), 10n ** 30n);
  });

  await t.test("a number with a fraction or an exponent is no integer", () => {
    for (const text of ["1.0", "0.5", "-0.0", "1e3", "1E3", "1e+3", "1e-3", "12.5e10", "0e0", "1E400", "-1.5E-400"]) {
      assert.equal(read(text), strictjson.NOT_AN_INTEGER, text);
      assert.throws(() => strictjson.integer(read(text), null, null, "it"), {reason: "bad-type", detail: "it is not an integer"});
    }
  });

  await t.test("the position of a text that is not JSON is a line and a column", () => {
    refused("", /^line 1, column 1: /);
    refused('{\n  "a": 1,\n  "b": ?\n}', /^line 3, column 8: /);
    refused('{"a": 1} x', /^line 1, column 10: /);
    refused('[1,\r\n 2,\r\n ]', /^line 3, column 2: /);
  });

  await t.test("the details the Python tool words itself", () => {
    refused(Uint8Array.of(0xff), "not UTF-8");
    refused(joined(MARK, utf8("{}")), "starts with a byte-order mark");
    refused("[1, NaN]", "NaN is not a JSON value");
    refused("Infinity", "Infinity is not a JSON value");
    refused("[-Infinity", "-Infinity is not a JSON value");
    refused('{"a": 1, "a": 1}', 'member "a" appears twice in one object');
    refused(DEEP(513), "nested too deeply");
  });

  await t.test("512 levels are read and 513 are not, for arrays, objects and both", () => {
    const objects = (levels) => '{"a": '.repeat(levels) + "1" + "}".repeat(levels);
    const mixed = (levels) => '[{"a": '.repeat(levels / 2) + "1" + "}]".repeat(levels / 2);
    let value = read(DEEP(512));
    let depth = 0;
    while (Array.isArray(value) && value.length === 1) {
      value = value[0];
      depth += 1;
    }
    assert.equal(depth, 511);
    assert.deepEqual(value, []);
    assert.ok(read(objects(512)) instanceof Map);
    assert.ok(Array.isArray(read(mixed(512))));
    refused(DEEP(513), "nested too deeply");
    refused(objects(513), "nested too deeply");
    refused(`[${mixed(512)}]`, "nested too deeply");
    refused("[".repeat(513), "nested too deeply");
    refused("[".repeat(512), /^line 1, column 513: /);
  });

  await t.test("a text nested a million deep is refused without harm", () => {
    refused("[".repeat(1000000), "nested too deeply");
    refused('{"a":'.repeat(1000000), "nested too deeply");
  });

  await t.test("only bytes are read", () => {
    assert.throws(() => strictjson.loads("{}"), TypeError);
  });
});

test("the three checks", async (t) => {
  const rejection = (action) => {
    try {
      action();
    } catch (error) {
      assert.ok(error instanceof errors.Rejection, String(error));
      return `${error.reason}: ${error.detail}`;
    }
    return "accepted";
  };
  const object = (text) => strictjson.loads(utf8(text));

  await t.test("members", () => {
    const required = ["a", "b"];
    assert.equal(rejection(() => strictjson.members(object('{"b": 1, "a": 2}'), required)), "accepted");
    assert.equal(rejection(() => strictjson.members(object('{"b": 1, "a": 2, "c": 3}'), required, ["c"])), "accepted");
    assert.equal(rejection(() => strictjson.members(object("[]"), required)), "bad-type: the file is not an object");
    assert.equal(rejection(() => strictjson.members(null, required, [], "frame 3")), "bad-type: frame 3 is not an object");
    assert.equal(rejection(() => strictjson.members("a", required, [], "frame 3")), "bad-type: frame 3 is not an object");
    assert.equal(rejection(() => strictjson.members(object('{"c": 1}'), required)), 'missing-member: the file has no member "a"');
    assert.equal(rejection(() => strictjson.members(object('{"a": 1, "c": 1}'), required, [], "entry 2 of legs")), 'missing-member: entry 2 of legs has no member "b"');
    assert.equal(rejection(() => strictjson.members(object('{"d": 1, "a": 1, "c": 1, "b": 2}'), required)), 'unknown-member: the file has the unknown member "d"');
    assert.equal(rejection(() => strictjson.members(object('{"a": 1, "c": 1, "b": 2}'), required, ["d"], "it")), 'unknown-member: it has the unknown member "c"');
  });

  await t.test("integer", () => {
    assert.equal(strictjson.integer(5), 5);
    assert.equal(strictjson.integer(5, 5, 5), 5);
    assert.equal(strictjson.integer(-(10n ** 30n)), -(10n ** 30n));
    assert.equal(rejection(() => strictjson.integer(4, 5, 9, "x")), "out-of-range: x is below 5");
    assert.equal(rejection(() => strictjson.integer(10, 5, 9, "x")), "out-of-range: x is above 9");
    assert.equal(rejection(() => strictjson.integer(10n ** 30n, 0, 16777215, "pixel 0 of frame 1")), "out-of-range: pixel 0 of frame 1 is above 16777215");
    assert.equal(rejection(() => strictjson.integer(-(10n ** 30n), 1, null, "width")), "out-of-range: width is below 1");
    assert.equal(rejection(() => strictjson.integer(10n ** 30n, 1, null, "width")), "accepted");
    for (const value of [strictjson.NOT_AN_INTEGER, "1", true, false, null, [], new Map()]) {
      assert.equal(rejection(() => strictjson.integer(value, 0, 9, "x")), "bad-type: x is not an integer");
    }
    assert.equal(rejection(() => strictjson.integer(null)), "bad-type: a value is not an integer");
  });

  await t.test("array", () => {
    const list = [1];
    assert.equal(strictjson.array(list), list);
    for (const value of [new Map(), "[]", 1, null, true]) {
      assert.equal(rejection(() => strictjson.array(value, "frames")), "bad-type: frames is not an array");
    }
    assert.equal(rejection(() => strictjson.array(null)), "bad-type: a value is not an array");
  });
});
