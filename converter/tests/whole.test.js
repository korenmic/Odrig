import assert from "node:assert/strict";
import test from "node:test";

import {whole} from "../lib/index.js";
import {numbers, reference} from "./support.js";

const {fraction} = whole;
const pair = (value) => [value.n, value.d];

test("whole numbers", async (t) => {
  await t.test("a whole number is a Number while it is exact and a BigInt beyond", () => {
    assert.equal(whole.whole(7), 7);
    assert.equal(whole.whole(7n), 7);
    assert.ok(Object.is(whole.whole(-0), 0));
    assert.equal(whole.whole(9007199254740991n), 9007199254740991);
    assert.equal(whole.whole(-9007199254740991n), -9007199254740991);
    assert.equal(whole.whole(9007199254740992n), 9007199254740992n);
    assert.equal(whole.whole(-9007199254740992n), -9007199254740992n);
    assert.throws(() => whole.whole(1.5), RangeError);
    assert.throws(() => whole.whole(2 ** 53), RangeError);
    assert.throws(() => whole.whole(NaN), RangeError);
  });

  await t.test("fromDigits reads decimal digits of any length", () => {
    assert.equal(whole.fromDigits("0"), 0);
    assert.ok(Object.is(whole.fromDigits("-0"), 0));
    assert.equal(whole.fromDigits("-42"), -42);
    assert.equal(whole.fromDigits("9007199254740991"), 9007199254740991);
    assert.equal(whole.fromDigits("9007199254740993"), 9007199254740993n);
    assert.equal(whole.fromDigits("-123456789012345678901234567890"), -123456789012345678901234567890n);
  });

  await t.test("plus and times lose no digit", () => {
    assert.equal(whole.plus(2, 3), 5);
    assert.equal(whole.plus(9007199254740991, 1), 9007199254740992n);
    assert.equal(whole.plus(9007199254740992n, -1), 9007199254740991);
    assert.equal(whole.plus(10n ** 30n, 1), 10n ** 30n + 1n);
    assert.equal(whole.times(6, 7), 42);
    assert.ok(Object.is(whole.times(0, -5), 0));
    assert.equal(whole.times(94906267, 94906267), 9007199515875289n);
    assert.equal(whole.times(3037000500, 3037000499), 3037000500n * 3037000499n);
    assert.equal(whole.times(10n ** 20n, 10n ** 20n), 10n ** 40n);
    assert.equal(whole.times(10n ** 20n, 0), 0);
  });

  await t.test("floor division rounds toward minus infinity, also for negative numbers", () => {
    const cases = [
      [7n, 2n, 3n], [-7n, 2n, -4n], [7n, -2n, -4n], [-7n, -2n, 3n],
      [6n, 3n, 2n], [-6n, 3n, -2n], [6n, -3n, -2n], [-6n, -3n, 2n],
      [0n, 5n, 0n], [0n, -5n, 0n], [1n, 5n, 0n], [-1n, 5n, -1n], [1n, -5n, -1n], [-1n, -5n, 0n],
      [-(10n ** 30n) - 1n, 10n ** 15n, -(10n ** 15n) - 1n],
    ];
    for (const [a, b, expected] of cases) {
      assert.equal(whole.floorDiv(a, b), expected, `${a} // ${b}`);
    }
    assert.equal(-7n / 2n, -3n, "the division of BigInt rounds toward zero");
  });
});

test("fractions", async (t) => {
  await t.test("a fraction is two BigInts in lowest terms with a denominator above 0", () => {
    assert.deepEqual(pair(fraction(6, 4)), [3n, 2n]);
    assert.deepEqual(pair(fraction(6, -4)), [-3n, 2n]);
    assert.deepEqual(pair(fraction(-6, -4)), [3n, 2n]);
    assert.deepEqual(pair(fraction(0, -7)), [0n, 1n]);
    assert.deepEqual(pair(fraction(5)), [5n, 1n]);
    assert.deepEqual(pair(fraction(10n ** 40n, 10n ** 38n)), [100n, 1n]);
    assert.deepEqual(pair(fraction(fraction(1, 2), 3)), [1n, 6n]);
    assert.deepEqual(pair(fraction(fraction(1, 2))), [1n, 2n]);
    assert.throws(() => fraction(1, 0), RangeError);
    assert.throws(() => fraction(0.5), RangeError);
  });

  await t.test("add, sub, mul and div are exact", () => {
    assert.deepEqual(pair(whole.add(fraction(1, 3), fraction(1, 6))), [1n, 2n]);
    assert.deepEqual(pair(whole.add(fraction(1, 3), 2)), [7n, 3n]);
    assert.deepEqual(pair(whole.sub(fraction(1, 3), fraction(1, 2))), [-1n, 6n]);
    assert.deepEqual(pair(whole.sub(5, fraction(1, 2))), [9n, 2n]);
    assert.deepEqual(pair(whole.mul(fraction(2, 3), fraction(9, 4))), [3n, 2n]);
    assert.deepEqual(pair(whole.mul(fraction(-2, 3), 6n)), [-4n, 1n]);
    assert.deepEqual(pair(whole.div(fraction(2, 3), fraction(4, 9))), [3n, 2n]);
    assert.deepEqual(pair(whole.div(1, -3)), [-1n, 3n]);
    assert.throws(() => whole.div(1, 0), RangeError);
    let tenth = fraction(0);
    for (let i = 0; i < 10; i += 1) {
      tenth = whole.add(tenth, fraction(1, 10));
    }
    assert.deepEqual(pair(tenth), [1n, 1n]);
    const third = fraction(1001, 30000);
    assert.deepEqual(pair(whole.mul(whole.mul(third, 1000), 30)), [1001n, 1n]);
  });

  await t.test("compare", () => {
    assert.equal(whole.compare(fraction(1, 3), fraction(1, 2)), -1);
    assert.equal(whole.compare(fraction(1, 2), fraction(1, 3)), 1);
    assert.equal(whole.compare(fraction(2, 4), fraction(1, 2)), 0);
    assert.equal(whole.compare(fraction(-1, 2), fraction(-1, 3)), -1);
    assert.equal(whole.compare(fraction(-1, 2), 0), -1);
    assert.equal(whole.compare(3, fraction(6, 2)), 0);
    assert.equal(whole.compare(fraction(10n ** 40n + 1n, 10n ** 40n), 1), 1);
  });

  await t.test("floor and ceil, also of negative fractions", () => {
    const cases = [
      [fraction(7, 2), 3n, 4n], [fraction(-7, 2), -4n, -3n], [fraction(6, 2), 3n, 3n], [fraction(-6, 2), -3n, -3n],
      [fraction(1, 3), 0n, 1n], [fraction(-1, 3), -1n, 0n], [fraction(0), 0n, 0n],
      [fraction(-(10n ** 30n) - 1n, 10n ** 15n), -(10n ** 15n) - 1n, -(10n ** 15n)],
    ];
    for (const [value, down, up] of cases) {
      assert.equal(whole.floor(value), down, `floor of ${value.n}/${value.d}`);
      assert.equal(whole.ceil(value), up, `ceil of ${value.n}/${value.d}`);
    }
  });

  await t.test("isWhole", () => {
    assert.equal(whole.isWhole(fraction(4, 2)), true);
    assert.equal(whole.isWhole(fraction(5, 2)), false);
    assert.equal(whole.isWhole(0), true);
  });

  await t.test("rounded takes halves away from zero", () => {
    const cases = [
      [fraction(1, 2), 1n], [fraction(-1, 2), -1n], [fraction(5, 2), 3n], [fraction(-5, 2), -3n], [fraction(3, 2), 2n],
      [fraction(49, 100), 0n], [fraction(-49, 100), 0n], [fraction(51, 100), 1n], [fraction(-51, 100), -1n],
      [fraction(7), 7n], [fraction(-7), -7n], [fraction(0), 0n],
    ];
    for (const [value, expected] of cases) {
      assert.equal(whole.rounded(value), expected, `${value.n}/${value.d}`);
    }
  });
});

test("fromDecimal reads a number from its digits", async (t) => {
  await t.test("the five texts of the task, in milliseconds", () => {
    assert.deepEqual(pair(whole.fromDecimal("12.5", 1000)), [12500n, 1n]);
    assert.deepEqual(pair(whole.fromDecimal(".5", 1000)), [500n, 1n]);
    assert.deepEqual(pair(whole.fromDecimal("1e3", 1000)), [1000000n, 1n]);
    assert.deepEqual(pair(whole.fromDecimal("-0.0005", 1000)), [-1n, 2n]);
    assert.deepEqual(pair(whole.fromDecimal("0.0005", 1000)), [1n, 2n]);
    assert.equal(whole.rounded(whole.fromDecimal("-0.0005", 1000)), -1n);
    assert.equal(whole.rounded(whole.fromDecimal("0.0005", 1000)), 1n);
  });

  await t.test("without a scale, and with every part of the form", () => {
    assert.deepEqual(pair(whole.fromDecimal("0")), [0n, 1n]);
    assert.deepEqual(pair(whole.fromDecimal("-0")), [0n, 1n]);
    assert.deepEqual(pair(whole.fromDecimal("1.")), [1n, 1n]);
    assert.deepEqual(pair(whole.fromDecimal("+2.50")), [5n, 2n]);
    assert.deepEqual(pair(whole.fromDecimal("0.1")), [1n, 10n]);
    assert.deepEqual(pair(whole.fromDecimal("1E-3")), [1n, 1000n]);
    assert.deepEqual(pair(whole.fromDecimal("12.5e+1")), [125n, 1n]);
    assert.deepEqual(pair(whole.fromDecimal("0.30000000000000004")), [7500000000000001n, 25000000000000000n]);
    assert.deepEqual(pair(whole.fromDecimal("007")), [7n, 1n]);
  });

  await t.test("a text that is no decimal number is a mistake of the program", () => {
    for (const text of ["", ".", "e3", "1e", "x", "1.5.2", " 1", "1_0", "0x10", "Infinity", "--1"]) {
      assert.throws(() => whole.fromDecimal(text), RangeError, text);
    }
  });

  await t.test("the milliseconds are those the Python tool reads from the same text", () => {
    const texts = [
      "0", "7", "12.5", ".5", "1.", "1e3", "1E3", "2.5e-3", "+1", "-1", "-0.0005", "0.0005", "0.0004", "-0.0004",
      "0.0015", "0.0025", "-0.0015", "-0.0025", "0.00049999999999999999", "0.00050000000000000001", "1.2345", "1.2355",
      "3.14159", "59.9995", "59.9994", "86400", "0.001", "0.0009", "1e-3", "1e-4", "5e-4", "4e-4", "123456789.0005",
      "007", "1e+2", "0.1", "0.2", "0.3", "-.5", "-12.3456",
    ];
    const theirs = reference("milliseconds", [], texts);
    texts.forEach((text, i) => {
      assert.equal(String(whole.rounded(whole.fromDecimal(text, 1000))), theirs[i], text);
    });
  });
});

test("sixDigits writes a fraction as Python's format(x, '.6g')", async (t) => {
  const ask = (pairs) => reference("sixdigits", [], pairs.map(([n, d]) => [String(n), String(d)]));

  await t.test("for values worked out by hand", () => {
    const cases = [
      [fraction(0), "0"], [fraction(400), "400"], [fraction(1000, 3), "333.333"], [fraction(1, 3), "0.333333"],
      [fraction(2, 3), "0.666667"], [fraction(1000000), "1e+06"], [fraction(1234567), "1.23457e+06"],
      [fraction(999999), "999999"], [fraction(1, 10000), "0.0001"], [fraction(1, 100000), "1e-05"],
      [fraction(5, 2), "2.5"], [fraction(40040, 1001), "40"], [fraction(-1000, 3), "-333.333"],
      [fraction(123456789, 1000), "123457"], [fraction(10n ** 21n), "1e+21"], [fraction(15, 10n ** 11n), "1.5e-10"],
    ];
    for (const [value, expected] of cases) {
      assert.equal(whole.sixDigits(value), expected, `${value.n}/${value.d}`);
    }
  });

  await t.test("a half at the sixth digit goes to the even digit", () => {
    const halves = [[246913, 2], [246915, 2], [200001, 2], [200003, 2], [1999999, 2], [1234565, 10], [1234575, 10], [2000001, 2000], [8000004, 64]];
    const theirs = ask(halves);
    halves.forEach(([n, d], i) => {
      assert.equal(whole.sixDigits(fraction(n, d)), theirs[i], `${n}/${d}`);
    });
    assert.equal(whole.sixDigits(fraction(246913, 2)), "123456");
    assert.equal(whole.sixDigits(fraction(246915, 2)), "123458");
    assert.equal(whole.sixDigits(fraction(1999999, 2)), "1e+06");
  });

  await t.test("for 600 fractions from seeds, of every size", () => {
    const from = numbers(606);
    const pairs = [];
    const bigOf = (bytes) => BigInt(`0x${Buffer.from(from.bytes(bytes)).toString("hex")}`) + 1n;
    for (let i = 0; i < 200; i += 1) {
      pairs.push([from.between(0, 2000000), from.between(1, 2000)]);
    }
    for (let i = 0; i < 100; i += 1) {
      pairs.push([from.between(1, 999), 10 ** from.between(0, 12)]);
      pairs.push([from.between(1, 999) * 10 ** from.between(0, 12), from.between(1, 7)]);
    }
    for (let i = 0; i < 100; i += 1) {
      pairs.push([bigOf(from.between(1, 14)), bigOf(from.between(1, 14))]);
      pairs.push([bigOf(from.between(7, 9)) * 1000n, bigOf(from.between(7, 9))]);
    }
    assert.equal(pairs.length, 600);
    const theirs = ask(pairs);
    pairs.forEach(([n, d], i) => {
      assert.equal(whole.sixDigits(fraction(BigInt(n), BigInt(d))), theirs[i], `${n}/${d}`);
    });
    assert.ok(theirs.some((text) => text.includes("e+")));
    assert.ok(theirs.some((text) => text.includes("e-")));
    assert.ok(theirs.some((text) => /^\d+$/.test(text)));
  });

  await t.test("for fractions that lie beside a half of the floating-point grid", () => {
    const pairs = [];
    for (const shift of [0n, 1n, 7n, 60n]) {
      const d = 1n << (53n + shift);
      for (const odd of [1n, 3n, 5n, 7n]) {
        const half = ((1n << 53n) + odd) << shift;
        pairs.push([2n * half - 1n, 2n * d], [2n * half, 2n * d], [2n * half + 1n, 2n * d]);
      }
    }
    const theirs = ask(pairs);
    pairs.forEach(([n, d], i) => {
      assert.equal(whole.sixDigits(fraction(n, d)), theirs[i], `${n}/${d}`);
    });
  });
});
