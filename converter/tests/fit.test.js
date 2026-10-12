import assert from "node:assert/strict";
import test from "node:test";

import {errors, fit, whole} from "../lib/index.js";
import {hex, numbers, reference} from "./support.js";

const {fraction} = whole;
const FITS = ["fill", "fit", "stretch"];

function pairs(rect) {
  return [rect.left, rect.top, rect.width, rect.height].map((value) => [String(value.n), String(value.d)]);
}

// A source picture made from a seed: noise, one colour, or a ramp, with every pixel
// opaque, with alphas of every value, or with some pixels fully transparent.
function sourcePicture(from, width, height) {
  const pixels = width * height;
  const rgba = new Uint8Array(4 * pixels);
  const style = from.pick(["noise", "noise", "one colour", "ramp"]);
  const alphas = from.pick(["opaque", "opaque", "every value", "holes"]);
  const one = from.bytes(3);
  for (let pixel = 0; pixel < pixels; pixel += 1) {
    const colour = style === "noise" ? from.bytes(3) : style === "one colour" ? one : [(pixel % width) * 3, Math.floor(pixel / width) * 5, one[2]];
    rgba.set(colour, 4 * pixel);
    rgba[4 * pixel + 3] = alphas === "opaque" ? 255 : alphas === "every value" ? from.below(256) : from.pick([0, 255, 255, 255]);
  }
  return {width, height, rgba};
}

function sizeFrom(from, largestWidth, largestHeight) {
  const scale = from.below(3);
  if (scale === 0) {
    return [from.between(1, Math.min(8, largestWidth)), from.between(1, Math.min(8, largestHeight))];
  }
  if (scale === 1) {
    return [from.between(1, Math.min(60, largestWidth)), from.between(1, Math.min(45, largestHeight))];
  }
  return [from.between(1, largestWidth), from.between(1, largestHeight)];
}

function placed(source, w, h, name) {
  try {
    return hex(fit.place(source, w, h, name));
  } catch (error) {
    if (!(error instanceof errors.Rejection)) {
      throw error;
    }
    return {reason: error.reason, detail: error.detail};
  }
}

function resampled(rgb, columns, rows, rect, w, h) {
  try {
    return hex(fit.resample(rgb, columns, rows, rect, w, h));
  } catch (error) {
    if (!(error instanceof errors.Rejection)) {
      throw error;
    }
    return {reason: error.reason, detail: error.detail};
  }
}

test("the rectangle of a fit", async (t) => {
  await t.test("a source wider than the canvas shape", () => {
    assert.deepEqual(pairs(fit.sourceRect(40, 10, 2, 1, "fill")), [["10", "1"], ["0", "1"], ["20", "1"], ["10", "1"]]);
    assert.deepEqual(pairs(fit.sourceRect(40, 10, 2, 1, "fit")), [["0", "1"], ["-5", "1"], ["40", "1"], ["20", "1"]]);
    assert.deepEqual(pairs(fit.sourceRect(40, 10, 2, 1, "stretch")), [["0", "1"], ["0", "1"], ["40", "1"], ["10", "1"]]);
  });

  await t.test("a source narrower than the canvas shape", () => {
    assert.deepEqual(pairs(fit.sourceRect(10, 40, 2, 1, "fill")), [["0", "1"], ["35", "2"], ["10", "1"], ["5", "1"]]);
    assert.deepEqual(pairs(fit.sourceRect(10, 40, 2, 1, "fit")), [["-35", "1"], ["0", "1"], ["80", "1"], ["40", "1"]]);
    assert.deepEqual(pairs(fit.sourceRect(10, 40, 2, 1, "stretch")), [["0", "1"], ["0", "1"], ["10", "1"], ["40", "1"]]);
  });

  await t.test("a source of the canvas shape is shown whole by every fit", () => {
    for (const name of FITS) {
      assert.deepEqual(pairs(fit.sourceRect(120, 12, 60, 6, name)), [["0", "1"], ["0", "1"], ["120", "1"], ["12", "1"]]);
    }
  });

  await t.test("the rectangle is exact where it does not fall on whole pixels", () => {
    assert.deepEqual(pairs(fit.sourceRect(64, 36, 60, 6, "fill")), [["0", "1"], ["74", "5"], ["64", "1"], ["32", "5"]]);
    assert.deepEqual(pairs(fit.sourceRect(7, 3, 3, 7, "fill")), [["20", "7"], ["0", "1"], ["9", "7"], ["3", "1"]]);
    assert.deepEqual(pairs(fit.sourceRect(7, 3, 3, 7, "fit")), [["0", "1"], ["-20", "3"], ["7", "1"], ["49", "3"]]);
  });

  await t.test("400 sizes from seeds, with each fit, against the Python tool", () => {
    const from = numbers(13);
    const cases = [];
    for (let i = 0; i < 400; i += 1) {
      const [sw, sh] = sizeFrom(from, 4000, 3000);
      const [w, h] = sizeFrom(from, 60, 60);
      cases.push([sw, sh, w, h, from.pick(FITS)]);
    }
    const theirs = reference("rects", [], cases);
    cases.forEach((given, i) => {
      assert.deepEqual(pairs(fit.sourceRect(...given)), theirs[i], given.join(" "));
    });
  });

  await t.test("a fit that does not exist is a mistake of the program", () => {
    assert.throws(() => fit.sourceRect(4, 4, 2, 2, "crop"), RangeError);
    assert.deepEqual(fit.FITS, FITS);
  });
});

test("a picture is laid over black", async (t) => {
  await t.test("each channel v of a pixel with an alpha below 255 becomes (v * alpha + 127) div 255", () => {
    const source = {width: 4, height: 1, rgba: Uint8Array.of(200, 100, 50, 255, 200, 100, 50, 128, 255, 255, 255, 0, 255, 1, 3, 254)};
    assert.deepEqual([...fit.overBlack(source)], [200, 100, 50, 100, 50, 25, 0, 0, 0, 254, 1, 3]);
  });

  await t.test("for every value and every alpha", () => {
    const rgba = new Uint8Array(4 * 256 * 256);
    for (let value = 0; value < 256; value += 1) {
      for (let alpha = 0; alpha < 256; alpha += 1) {
        rgba.set([value, value, value, alpha], 4 * (256 * value + alpha));
      }
    }
    const rgb = fit.overBlack({width: 256, height: 256, rgba});
    for (let value = 0; value < 256; value += 1) {
      for (let alpha = 0; alpha < 256; alpha += 1) {
        const expected = alpha === 255 ? value : Math.floor((value * alpha + 127) / 255);
        assert.equal(rgb[3 * (256 * value + alpha)], expected, `${value} with alpha ${alpha}`);
      }
    }
  });

  await t.test("a Uint8ClampedArray is a source picture as well", () => {
    const rgba = Uint8ClampedArray.of(10, 20, 30, 255, 40, 50, 60, 0);
    assert.deepEqual([...fit.overBlack({width: 2, height: 1, rgba})], [10, 20, 30, 0, 0, 0]);
  });

  await t.test("a picture without pixels is unreadable-media, and a wrong number of bytes a mistake of the program", () => {
    assert.throws(() => fit.overBlack({width: 0, height: 3, rgba: new Uint8Array(0)}), {reason: "unreadable-media", detail: "a picture has no pixels"});
    assert.throws(() => fit.overBlack({width: 3, height: 0, rgba: new Uint8Array(0)}), {reason: "unreadable-media", detail: "a picture has no pixels"});
    assert.throws(() => fit.overBlack({width: 2, height: 2, rgba: new Uint8Array(15)}), RangeError);
  });
});

test("the area mean, worked out by hand", async (t) => {
  const grey = (values, width) => {
    const rgba = new Uint8Array(4 * values.length);
    values.forEach((value, i) => rgba.set([value, value, value, 255], 4 * i));
    return {width, height: values.length / width, rgba};
  };
  const reds = (picture) => Array.from({length: picture.length / 3}, (unused, i) => picture[3 * i]);

  await t.test("a 4 by 4 source of blocks shrunk to 2 by 2 is the mean of each block", () => {
    const source = grey([10, 20, 100, 110, 30, 40, 120, 130, 1, 2, 201, 202, 3, 4, 203, 204], 4);
    assert.deepEqual(reds(fit.place(source, 2, 2, "stretch")), [3, 203, 25, 115], "the bottom row first: (1+2+3+4)/4 is 2.5, which rounds up");
  });

  await t.test("the top row of the source lands on the last row of the canvas picture", () => {
    const source = grey([1, 2, 3, 4, 5, 6], 2);
    assert.deepEqual(reds(fit.place(source, 2, 3, "stretch")), [5, 6, 3, 4, 1, 2]);
  });

  await t.test("a half rounds up, and less than a half down", () => {
    assert.deepEqual(reds(fit.place(grey([0, 1], 2), 1, 1, "stretch")), [1]);
    assert.deepEqual(reds(fit.place(grey([0, 0, 1], 3), 1, 1, "stretch")), [0]);
    assert.deepEqual(reds(fit.place(grey([0, 1, 1], 3), 1, 1, "stretch")), [1]);
    assert.deepEqual(reds(fit.place(grey([254, 255], 2), 1, 1, "stretch")), [255]);
  });

  await t.test("growing repeats source pixels, and a canvas pixel on two source pixels is blended", () => {
    assert.deepEqual(reds(fit.place(grey([10, 200], 2), 4, 1, "stretch")), [10, 10, 200, 200]);
    assert.deepEqual(reds(fit.place(grey([10, 200], 2), 3, 1, "stretch")), [10, 105, 200]);
  });

  await t.test("the bars of fit are black, and an edge inside a canvas pixel is blended", () => {
    const source = grey([200, 200], 1);
    assert.deepEqual(reds(fit.place(source, 4, 2, "fit")), [0, 100, 100, 0, 0, 100, 100, 0]);
    assert.deepEqual(reds(fit.place(grey([200], 1), 3, 1, "fit")), [0, 200, 0]);
  });

  await t.test("each channel is averaged on its own", () => {
    const source = {width: 2, height: 1, rgba: Uint8Array.of(10, 0, 255, 255, 30, 100, 0, 255)};
    assert.deepEqual([...fit.place(source, 1, 1, "stretch")], [20, 50, 128]);
  });
});

test("300 source pictures from seeds get the canvas pictures of the Python tool, with each fit", async (t) => {
  const from = numbers(1300);
  const cases = [];
  for (let i = 0; i < 300; i += 1) {
    const [width, height] = sizeFrom(from, 200, 150);
    const [w, h] = sizeFrom(from, 60, 60);
    cases.push({source: sourcePicture(from, width, height), w, h});
  }
  const theirs = reference("resample", [], cases.map(({source, w, h}) => ({columns: source.width, rows: source.height, rgba: hex(source.rgba), fits: FITS, w, h})));

  await t.test("byte for byte", () => {
    cases.forEach(({source, w, h}, i) => {
      FITS.forEach((name, j) => {
        assert.equal(placed(source, w, h, name), theirs[i][j], `picture ${i + 1}: ${source.width} x ${source.height} on ${w} x ${h}, ${name}`);
      });
    });
  });

  await t.test("the pictures have sizes from 1 x 1 to 200 x 150 and the canvases from 1 x 1 to 60 x 60", () => {
    const widths = cases.map(({source}) => source.width);
    const heights = cases.map(({source}) => source.height);
    assert.equal(Math.min(...widths), 1);
    assert.equal(Math.min(...heights), 1);
    assert.ok(Math.max(...widths) >= 190, String(Math.max(...widths)));
    assert.ok(Math.max(...heights) >= 140, String(Math.max(...heights)));
    assert.equal(Math.min(...cases.map(({w}) => w)), 1);
    assert.ok(Math.max(...cases.map(({w}) => w)) >= 58);
    assert.ok(Math.max(...cases.map(({h}) => h)) >= 58);
    assert.ok(cases.some(({source}) => source.width === 1 && source.height === 1));
    assert.ok(cases.some(({w, h}) => w === 1 && h === 1));
  });
});

test("fit, with a source narrower than the canvas shape, has the bars of the Python tool", () => {
  const from = numbers(404);
  const cases = [];
  for (const [width, height, w, h] of [[3, 7, 60, 6], [10, 40, 2, 1], [5, 5, 60, 6], [9, 16, 16, 9], [1, 1, 7, 2], [31, 97, 60, 60], [2, 3, 5, 3]]) {
    cases.push({source: sourcePicture(from, width, height), w, h});
  }
  const theirs = reference("resample", [], cases.map(({source, w, h}) => ({columns: source.width, rows: source.height, rgba: hex(source.rgba), fits: ["fit"], w, h})));
  cases.forEach(({source, w, h}, i) => {
    const ours = fit.place(source, w, h, "fit");
    const expected = Buffer.from(theirs[i][0], "hex");
    for (let at = 0; at < expected.length; at += 1) {
      if (ours[at] !== expected[at]) {
        const pixel = Math.floor(at / 3);
        assert.fail(`${source.width} x ${source.height} on ${w} x ${h}: column ${(pixel % w) + 1} of row ${Math.floor(pixel / w) + 1} has ${ours[at]} where the Python tool has ${expected[at]}`);
      }
    }
    assert.equal(ours.length, expected.length);
    const left = fit.sourceRect(source.width, source.height, w, h, "fit").left;
    assert.ok(left.n < 0n, "the rectangle begins left of the picture");
  });
});

test("a rectangle that reaches beyond the picture, or lies beside it", async (t) => {
  const from = numbers(77);
  const columns = 5;
  const rows = 4;
  const rgb = from.bytes(3 * columns * rows);
  const rects = [
    ["the picture itself", [0, 0, 5, 4]],
    ["a part inside it, on whole pixels", [1, 1, 3, 2]],
    ["a part inside it, between pixels", (w, h) => [[1, 2 * w * h], [3, 2 * w * h], [6 * h + 1, 2 * h], [4 * w + 1, 2 * w]]],
    ["beyond its left edge", [-2, 0, 5, 4]],
    ["beyond its left edge by a part of a pixel", (w, h) => [[-1, 2 * w * h], 0, 5, 4]],
    ["beyond its top", [0, -3, 5, 4]],
    ["beyond its right edge and its bottom", [3, 2, 6, 6]],
    ["around it on all sides", [-5, -4, 15, 12]],
    ["wholly left of it", [-9, 0, 5, 4]],
    ["wholly left of it, touching its edge", [-5, 0, 5, 4]],
    ["wholly right of it", [5, 0, 5, 4]],
    ["wholly above it", [0, -8, 5, 4]],
    ["wholly below it", [0, 4, 5, 4]],
    ["far away from it", [100000, -100000, 3, 3]],
    ["the smallest part of a pixel the grid of the canvas has", (w, h) => [2, 2, [1, 2 * h], [1, 2 * w]]],
  ];
  const canvases = [[3, 3], [1, 1], [6, 2], [2, 6]];
  const cases = [];
  for (const [label, rect] of rects) {
    for (const [w, h] of canvases) {
      cases.push({label: `${label}, on ${w} x ${h}`, rect: typeof rect === "function" ? rect(w, h) : rect, w, h});
    }
  }
  const asFraction = (value) => (Array.isArray(value) ? fraction(value[0], value[1]) : fraction(value));
  const asText = (value) => (Array.isArray(value) ? value.map(String) : String(value));
  const theirs = reference("resample", [], cases.map(({rect, w, h}) => ({columns, rows, rgb: hex(rgb), rect: rect.map(asText), w, h})));
  for (let i = 0; i < cases.length; i += 1) {
    const {label, rect, w, h} = cases[i];
    await t.test(label, () => {
      const [left, top, width, height] = rect.map(asFraction);
      assert.equal(resampled(rgb, columns, rows, {left, top, width, height}, w, h), theirs[i]);
    });
  }
  await t.test("a rectangle beside the picture is all black, and one inside it is not", () => {
    const all = (picture) => new Set(picture).size === 1 && picture[0] === 0;
    const at = (label) => {
      const [left, top, width, height] = rects.find(([text]) => text === label)[1].map(asFraction);
      return fit.resample(rgb, columns, rows, {left, top, width, height}, 3, 3);
    };
    assert.ok(all(at("wholly left of it")));
    assert.ok(all(at("wholly left of it, touching its edge")));
    assert.ok(all(at("wholly below it")));
    assert.ok(!all(at("the picture itself")));
  });

  await t.test("a rectangle off the grid of the canvas, or without area, is a mistake of the program", () => {
    const rect = (left, top, width, height) => ({left: fraction(left), top: fraction(top), width: fraction(width), height: fraction(height)});
    assert.throws(() => fit.resample(rgb, columns, rows, {...rect(0, 0, 5, 4), left: fraction(1, 7)}, 3, 3), RangeError);
    assert.throws(() => fit.resample(rgb, columns, rows, rect(0, 0, 0, 4), 3, 3), RangeError);
    assert.throws(() => fit.resample(rgb, columns, rows, rect(0, 0, 5, -4), 3, 3), RangeError);
    assert.throws(() => fit.resample(rgb.subarray(3), columns, rows, rect(0, 0, 5, 4), 3, 3), RangeError);
  });
});

function isqrt(value) {
  let low = 0n;
  let high = value;
  while (low < high) {
    const middle = (low + high + 1n) / 2n;
    if (middle * middle <= value) {
      low = middle;
    } else {
      high = middle - 1n;
    }
  }
  return low;
}

test("the border of the whole-number arithmetic", async (t) => {
  await t.test("a case on each side of 2 to the power 53 is the Python tool's picture", () => {
    // A picture of 64 columns stretched on a canvas of 64 columns: the area, in the units
    // of the tool, is (2 * h * 64) * (2 * 64 * rows) for `rows` rows on a canvas of h rows.
    const rows = 32768;
    const times511 = (h) => 511n * (2n * BigInt(h) * 64n) * (2n * 64n * BigInt(rows));
    const below = Number((2n ** 53n - 1n) / times511(1));
    const above = below + 1;
    assert.ok(times511(below) < 2n ** 53n);
    assert.ok(times511(above) >= 2n ** 53n);
    const from = numbers(53);
    const source = {width: 64, height: rows, rgba: from.bytes(4 * 64 * rows)};
    const theirs = reference("resample", [], [below, above].map((h) => ({columns: 64, rows, rgba: hex(source.rgba), fits: ["stretch"], w: 64, h})));
    [below, above].forEach((h, i) => {
      const ours = fit.place(source, 64, h, "stretch");
      assert.ok(Buffer.from(ours).equals(Buffer.from(theirs[i][0], "hex")), `a canvas of 64 x ${h}`);
      assert.ok(new Set(ours).size > 100);
    });
  });

  await t.test("at 2 to the power 63 a picture is unreadable-media, with the detail of the Python tool", () => {
    const rgb = Uint8Array.of(1, 2, 3, 4, 5, 6);
    const side = (n) => ({left: fraction(0), top: fraction(0), width: fraction(n), height: fraction(n)});
    // On a canvas of 1 x 1 the area is (2 * n) ** 2 for a rectangle of n x n.
    const largest = isqrt((2n ** 63n - 1n) / 511n) / 2n;
    assert.ok(511n * (2n * largest) ** 2n < 2n ** 63n);
    assert.ok(511n * (2n * (largest + 1n)) ** 2n >= 2n ** 63n);
    const cases = [largest, largest + 1n, 10n ** 12n];
    const theirs = reference("resample", [], cases.map((n) => ({columns: 2, rows: 1, rgb: hex(rgb), rect: ["0", "0", String(n), String(n)], w: 1, h: 1})));
    cases.forEach((n, i) => {
      assert.deepEqual(resampled(rgb, 2, 1, side(n), 1, 1), theirs[i], String(n));
    });
    assert.equal(typeof theirs[0], "string", "the largest rectangle the arithmetic takes is fitted");
    assert.deepEqual(theirs[1], {reason: "unreadable-media", detail: "a picture of 2 x 1 is too large for a canvas of 1 x 1"});
    assert.deepEqual(theirs[2], theirs[1]);
  });
});
