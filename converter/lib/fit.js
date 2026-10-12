// Fitting a picture to the canvas: the rectangle of a fit, pictures laid over black, and
// the area mean.
//
// A source picture is `{width, height, rgba}`: rows from the top, four bytes for each
// pixel, red, green, blue and alpha. A canvas picture is a `Uint8Array` in the pixel order
// of docs/format.md, the bottom row first. Everything is computed in whole numbers, so the
// same source picture gives the same canvas picture wherever this runs.

import {Rejection, UNREADABLE_MEDIA} from "./errors.js";
import {compare, div, floorDiv, fraction, mul, sub} from "./whole.js";

export const FITS = ["fill", "fit", "stretch"];

// The largest whole number a `Number` holds exactly, plus one.
const NUMBER_LIMIT = 2n ** 53n;
// The limit of the whole-number arithmetic of the reference.
const LIMIT = 2n ** 63n;

// The rectangle of the source, in source pixels, that a canvas of w x h shows:
// `{left, top, width, height}` as exact fractions.
//
// Canvas pixels are square, so the canvas has the shape w to h. `fill` covers the canvas
// and cuts off the overflow equally on two opposite sides; `fit` shows the whole picture,
// with a rectangle that reaches beyond it equally on two sides; `stretch` shows the whole
// picture whatever its shape.
export function sourceRect(sw, sh, w, h, fit) {
  if (!FITS.includes(fit)) {
    throw new RangeError(`there is no fit "${fit}"`);
  }
  const zero = fraction(0);
  const sourceWidth = fraction(sw);
  const sourceHeight = fraction(sh);
  const wider = compare(mul(sourceWidth, h), mul(sourceHeight, w)) >= 0;
  if (fit === "stretch") {
    return {left: zero, top: zero, width: sourceWidth, height: sourceHeight};
  }
  if ((fit === "fill") === wider) {
    const width = div(mul(sourceHeight, w), h);
    return {left: div(sub(sourceWidth, width), 2), top: zero, width, height: sourceHeight};
  }
  const height = div(mul(sourceWidth, h), w);
  return {left: zero, top: div(sub(sourceHeight, height), 2), width: sourceWidth, height};
}

// The colours of a source picture laid over black, three bytes for each pixel: a channel v
// of a pixel with an alpha below 255 becomes (v * alpha + 127) div 255.
export function overBlack(source) {
  const {width, height, rgba} = source;
  if (width === 0 || height === 0) {
    throw new Rejection(UNREADABLE_MEDIA, "a picture has no pixels");
  }
  const pixels = width * height;
  if (!Number.isSafeInteger(pixels) || pixels < 0 || rgba.length !== 4 * pixels) {
    throw new RangeError(`a source picture of ${width} x ${height} has four bytes for each of its pixels`);
  }
  const rgb = new Uint8Array(3 * pixels);
  for (let pixel = 0; pixel < pixels; pixel += 1) {
    const alpha = rgba[4 * pixel + 3];
    if (alpha === 255) {
      rgb[3 * pixel] = rgba[4 * pixel];
      rgb[3 * pixel + 1] = rgba[4 * pixel + 1];
      rgb[3 * pixel + 2] = rgba[4 * pixel + 2];
    } else {
      for (let channel = 0; channel < 3; channel += 1) {
        const value = rgba[4 * pixel + channel] * alpha + 127;
        rgb[3 * pixel + channel] = (value - (value % 255)) / 255;
      }
    }
  }
  return rgb;
}

// The source pixels that the slice from `start` to `start + length` covers, of `count`
// pixels in a line. Lengths are `BigInt`s in units of 1 / `unit` source pixel. The result
// is the index of the first pixel and, for it and each one after it, the length it shares
// with the slice. A slice that begins before the first pixel has a negative start.
function shares(start, length, count, unit) {
  const end = start + length;
  const below = floorDiv(start, unit);
  const first = below > 0n ? below : 0n;
  const above = -floorDiv(-end, unit);
  const last = above < count ? above : count;
  const weights = [];
  for (let index = first; index < last; index += 1n) {
    const right = (index + 1n) * unit;
    const left = index * unit;
    weights.push((end < right ? end : right) - (start > left ? start : left));
  }
  return {first, weights};
}

function whole(value, what) {
  if (value.d !== 1n) {
    throw new RangeError(`the rectangle does not fall on the grid of 1 / (2 * w * h) source pixel: ${what}`);
  }
  return value.n;
}

// The canvas picture of the part `rect` of a picture of `columns` x `rows` pixels, three
// bytes each, rows from the top.
//
// Every canvas pixel is the mean of the source area it covers, each source pixel weighted
// by the area they share, for each colour channel, rounded to the nearest whole number
// with halves rounded up. Area outside the picture counts as black. Every length is
// counted in units of 1 / (2 * w * h) source pixel. The top row of the source lands on
// the last row of the canvas picture, which is canvas row h.
export function resample(rgb, columns, rows, rect, w, h) {
  const unit = 2n * BigInt(w) * BigInt(h);
  const x0 = whole(mul(rect.left, unit), "left");
  const y0 = whole(mul(rect.top, unit), "top");
  const dx = whole(div(mul(rect.width, unit), w), "width");
  const dy = whole(div(mul(rect.height, unit), h), "height");
  const area = dx * dy;
  if (dx <= 0n || dy <= 0n) {
    throw new RangeError("the rectangle has no area");
  }
  if (511n * area >= LIMIT) {
    throw new Rejection(UNREADABLE_MEDIA, `a picture of ${columns} x ${rows} is too large for a canvas of ${w} x ${h}`);
  }
  if (rgb.length !== 3 * columns * rows) {
    throw new RangeError(`a picture of ${columns} x ${rows} has three bytes for each of its pixels`);
  }
  const across = [];
  for (let c = 0; c < w; c += 1) {
    across.push(shares(x0 + BigInt(c) * dx, dx, BigInt(columns), unit));
  }
  const down = [];
  for (let r = 0; r < h; r += 1) {
    down.push(shares(y0 + BigInt(r) * dy, dy, BigInt(rows), unit));
  }
  const picture = new Uint8Array(3 * w * h);
  if (511n * area < NUMBER_LIMIT) {
    meanInNumbers(rgb, columns, across, down, Number(area), w, h, picture);
  } else {
    meanInBigInts(rgb, columns, across, down, area, w, h, picture);
  }
  return picture;
}

// No sum is above 511 * area, which a `Number` holds exactly here.
function meanInNumbers(rgb, columns, across, down, area, w, h, picture) {
  const columnShares = across.map(({first, weights}) => ({first: Number(first), weights: Float64Array.from(weights, Number)}));
  const sums = new Float64Array(3 * columns);
  const twice = 2 * area;
  for (let r = 0; r < h; r += 1) {
    const first = Number(down[r].first);
    const weights = down[r].weights;
    sums.fill(0);
    for (let i = 0; i < weights.length; i += 1) {
      const weight = Number(weights[i]);
      const row = 3 * columns * (first + i);
      for (let at = 0; at < 3 * columns; at += 1) {
        sums[at] += weight * rgb[row + at];
      }
    }
    const out = 3 * w * (h - 1 - r);
    for (let c = 0; c < w; c += 1) {
      const share = columnShares[c];
      for (let channel = 0; channel < 3; channel += 1) {
        let sum = 0;
        for (let j = 0; j < share.weights.length; j += 1) {
          sum += share.weights[j] * sums[3 * (share.first + j) + channel];
        }
        const value = 2 * sum + area;
        picture[out + 3 * c + channel] = (value - (value % twice)) / twice;
      }
    }
  }
}

function meanInBigInts(rgb, columns, across, down, area, w, h, picture) {
  const twice = 2n * area;
  for (let r = 0; r < h; r += 1) {
    const first = Number(down[r].first);
    const weights = down[r].weights;
    const sums = new Array(3 * columns).fill(0n);
    for (let i = 0; i < weights.length; i += 1) {
      const row = 3 * columns * (first + i);
      for (let at = 0; at < 3 * columns; at += 1) {
        sums[at] += weights[i] * BigInt(rgb[row + at]);
      }
    }
    const out = 3 * w * (h - 1 - r);
    for (let c = 0; c < w; c += 1) {
      const share = across[c];
      const start = Number(share.first);
      for (let channel = 0; channel < 3; channel += 1) {
        let sum = 0n;
        for (let j = 0; j < share.weights.length; j += 1) {
          sum += share.weights[j] * sums[3 * (start + j) + channel];
        }
        picture[out + 3 * c + channel] = Number((2n * sum + area) / twice);
      }
    }
  }
}

// The canvas picture of a source picture for a canvas of w x h and a fit: the picture laid
// over black, the rectangle of the fit, and the area mean.
export function place(source, w, h, fit) {
  const rgb = overBlack(source);
  return resample(rgb, source.width, source.height, sourceRect(source.width, source.height, w, h, fit), w, h);
}
