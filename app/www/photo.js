// The mapping from a photo of the diagonal: the lit LEDs found in a picture, the places
// they stand at on the two grids of sixty, the columns across the wall and the rows up it,
// the stubs those places make, and the readings of which snake each position shows.

export const SNAKES = 20;
const COLUMNS = 3 * SNAKES;
// The long side of a picture as it is analysed.
const LONG_SIDE = 900;
// The most lit LEDs a reading has: the sixty of the diagonal and some noise.
const MOST_PEAKS = 100;
// A peak counts from this far above the picture's median brightness.
const ABOVE_MEDIAN = 24;
// The count of peaks at or above a level of brightness stays the same over at least this
// many levels for the peaks to be the lit LEDs: the lit LEDs are all about as bright, and
// the lenses and the wall below them come in a few at every level.
const LEAST_PLATEAU = 12;
// Peaks nearer each other than this many glow widths are one LED.
const ONE_LED = 1.5;
// A peak whose glow is this much wider than the others' is noise.
const NOISE_WIDER = 2.5;
// The slant that is taken out of each axis, as a fraction of the other coordinate, and
// its step: a turned phone slants both axes, a keystone one.
const MOST_SLANT = 0.3;
const SLANT_STEP = 0.005;
// A step of less than this share of the pitch is the same place.
const SAME_PLACE = 0.6;
// The edge of the picture the wires are at: the bottom or the top when the wall is seen
// upright, the left or the right when it is seen from the side. The first of each pair is
// what the advice asks for.
const SIDES = {upright: ["bottom", "top"], turned: ["left", "right"]};

// The picture of a file, turned as its orientation metadata says and scaled to at most
// LONG_SIDE pixels on its long side: `{width, height, grey}`.
export async function readPhoto(file) {
  let image;
  try {
    image = await createImageBitmap(file, {imageOrientation: "from-image"});
  } catch (_) {
    image = await loaded(file);
  }
  const scale = Math.min(1, LONG_SIDE / Math.max(image.width, image.height));
  const width = Math.max(1, Math.round(image.width * scale));
  const height = Math.max(1, Math.round(image.height * scale));
  const canvas = document.createElement("canvas");
  canvas.width = width;
  canvas.height = height;
  const context = canvas.getContext("2d", {willReadFrequently: true});
  context.drawImage(image, 0, 0, width, height);
  if (typeof image.close === "function") image.close();
  return fromPixels(context.getImageData(0, 0, width, height).data, width, height);
}

function loaded(file) {
  return new Promise((resolve, reject) => {
    const image = new Image();
    const url = URL.createObjectURL(file);
    image.onload = () => {
      URL.revokeObjectURL(url);
      resolve(image);
    };
    image.onerror = () => {
      URL.revokeObjectURL(url);
      reject(new Error("the picture could not be read"));
    };
    image.src = url;
  });
}

// A picture from the RGBA bytes of a canvas: the grey of a pixel is (2R + 5G + B) / 8.
export function fromPixels(data, width, height) {
  const grey = new Uint8Array(width * height);
  for (let at = 0, pixel = 0; pixel < grey.length; at += 4, pixel += 1) {
    grey[pixel] = (2 * data[at] + 5 * data[at + 1] + data[at + 2]) >> 3;
  }
  return {width, height, grey};
}

// The grey smoothed over each pixel's 3 x 3 neighbourhood, so that grain makes no peaks.
function smoothed(picture) {
  const {width, height, grey} = picture;
  const out = new Uint8Array(grey.length);
  for (let y = 0; y < height; y += 1) {
    const y0 = Math.max(0, y - 1);
    const y1 = Math.min(height - 1, y + 1);
    for (let x = 0; x < width; x += 1) {
      const x0 = Math.max(0, x - 1);
      const x1 = Math.min(width - 1, x + 1);
      let sum = 0;
      let count = 0;
      for (let yy = y0; yy <= y1; yy += 1) {
        for (let xx = x0; xx <= x1; xx += 1) {
          sum += grey[yy * width + xx];
          count += 1;
        }
      }
      out[y * width + x] = Math.round(sum / count);
    }
  }
  return out;
}

// The median brightness of the picture.
function medianGrey(grey) {
  const bins = new Uint32Array(256);
  for (const value of grey) bins[value] += 1;
  let seen = 0;
  for (let value = 0; value < 256; value += 1) {
    seen += bins[value];
    if (seen >= grey.length / 2) return value;
  }
  return 255;
}

// The bright peaks at or above a floor: pixels that no neighbour of their 3 x 3 beats,
// and that the earlier of two equal ones takes.
function peaks(width, height, grey, floor) {
  const found = [];
  for (let y = 0; y < height; y += 1) {
    for (let x = 0; x < width; x += 1) {
      const value = grey[y * width + x];
      if (value < floor) continue;
      let top = true;
      for (let dy = -1; dy <= 1 && top; dy += 1) {
        const yy = y + dy;
        if (yy < 0 || yy >= height) continue;
        for (let dx = -1; dx <= 1; dx += 1) {
          const xx = x + dx;
          if (xx < 0 || xx >= width || (dx === 0 && dy === 0)) continue;
          const other = grey[yy * width + xx];
          if (other > value || (other === value && (dy < 0 || (dy === 0 && dx < 0)))) {
            top = false;
            break;
          }
        }
      }
      if (top) found.push({x, y, value});
    }
  }
  return found;
}

// The level of brightness that tells the lit LEDs from the lenses and the wall: the
// middle of the longest stretch of levels, from the brightest down to the floor, over
// which the count of peaks at or above the level stays the same, at one to MOST_PEAKS
// peaks. Null when no stretch is LEAST_PLATEAU levels long: the count never settles, and
// the picture holds no steady set of lit LEDs.
function levelOf(found, floor) {
  const counts = new Uint32Array(256);
  for (const peak of found) counts[peak.value] += 1;
  for (let level = 254; level >= floor; level -= 1) counts[level] += counts[level + 1];
  let best = null;
  for (let high = 255; high >= floor;) {
    let low = high;
    while (low > floor && counts[low - 1] === counts[high]) low -= 1;
    const length = high - low + 1;
    if (counts[high] >= 1 && counts[high] <= MOST_PEAKS && (best === null || length > best.length)) best = {length, high, low};
    high = low - 1;
  }
  return best !== null && best.length >= LEAST_PLATEAU ? (best.high + best.low) >> 1 : null;
}

function median(values) {
  const sorted = [...values].sort((a, b) => a - b);
  const middle = sorted.length >> 1;
  return sorted.length % 2 ? sorted[middle] : (sorted[middle - 1] + sorted[middle]) / 2;
}

// The groups of the indices 0 to count - 1 that `together(a, b)` chains.
function chained(count, together) {
  const parent = Array.from({length: count}, (_, at) => at);
  const root = (at) => {
    while (parent[at] !== at) {
      parent[at] = parent[parent[at]];
      at = parent[at];
    }
    return at;
  };
  for (let a = 0; a < count; a += 1) {
    for (let b = a + 1; b < count; b += 1) {
      if (together(a, b)) parent[root(a)] = root(b);
    }
  }
  const groups = new Map();
  for (let at = 0; at < count; at += 1) {
    const key = root(at);
    if (!groups.has(key)) groups.set(key, []);
    groups.get(key).push(at);
  }
  return [...groups.values()];
}

// Peaks nearer each other than `near` are one LED, at their mean, as wide as the widest.
function oneLedEach(found, near) {
  const groups = chained(found.length, (a, b) => Math.hypot(found[a].x - found[b].x, found[a].y - found[b].y) < near);
  return groups.map((group) => ({
    x: group.reduce((sum, at) => sum + found[at].x, 0) / group.length,
    y: group.reduce((sum, at) => sum + found[at].y, 0) / group.length,
    width: Math.max(...group.map((at) => found[at].width)),
  }));
}

// How wide a peak's glow is: the mean of the three shortest bright runs from it along the
// eight directions, so that the runs along a stub's own diagonal, through its other
// LEDs, or into a glow beside it do not count.
function glowWidth(width, height, grey, level, point) {
  const runs = [];
  for (let dy = -1; dy <= 1; dy += 1) {
    for (let dx = -1; dx <= 1; dx += 1) {
      if (dx === 0 && dy === 0) continue;
      let steps = 0;
      let x = Math.round(point.x) + dx;
      let y = Math.round(point.y) + dy;
      while (x >= 0 && x < width && y >= 0 && y < height && grey[y * width + x] >= level && steps < width) {
        steps += 1;
        x += dx;
        y += dy;
      }
      runs.push(steps);
    }
  }
  runs.sort((a, b) => a - b);
  return (runs[0] + runs[1] + runs[2]) / 3;
}

// The coefficient of variation of the gaps between sorted values.
function unevenness(values) {
  const sorted = [...values].sort((a, b) => a - b);
  const gaps = sorted.slice(1).map((value, at) => value - sorted[at]);
  const mean = gaps.reduce((sum, gap) => sum + gap, 0) / gaps.length;
  if (mean <= 0) return Infinity;
  const variance = gaps.reduce((sum, gap) => sum + (gap - mean) * (gap - mean), 0) / gaps.length;
  return Math.sqrt(variance) / mean;
}

// The points with the slant of each axis taken out: u = x - k y and v = y - m x, with
// the k and the m that make the gaps between the sorted u, and between the sorted v,
// most even.
function unslanted(points) {
  const slant = (along, across) => {
    if (points.length < 4) return 0;
    let best = 0;
    let least = Infinity;
    for (let k = -MOST_SLANT; k <= MOST_SLANT + 1e-9; k += SLANT_STEP) {
      const score = unevenness(points.map((point) => point[along] - k * point[across]));
      if (score < least - 1e-9) {
        least = score;
        best = k;
      }
    }
    return best;
  };
  const k = slant("x", "y");
  const m = slant("y", "x");
  return {k, m, points: points.map((point) => ({...point, u: point.x - k * point.y, v: point.y - m * point.x}))};
}

// The places, from 0, of sorted values on a grid whose pitch is taken from the gaps
// between neighbours: each step from the last place's value, against the median of the
// four nearest other gaps between two places; a step of less than SAME_PLACE of a pitch is
// the same place. A gap of less than SAME_PLACE of the typical gap lies between two values
// at one place, two LEDs in one row, and tells nothing of the pitch. When the span passes
// the grid, the sixty places that hold the most values are kept, from 0 again, and the
// others' places are null.
function places(values) {
  const order = values.map((value, at) => ({value, at})).sort((a, b) => a.value - b.value);
  const gaps = order.slice(1).map((entry, at) => entry.value - order[at].value);
  const typical = gaps.length ? median(gaps) : 0;
  const between = gaps.map((gap) => gap >= SAME_PLACE * typical);
  const result = new Array(values.length);
  let place = 0;
  let anchor = order[0].value;
  result[order[0].at] = 0;
  for (let at = 0; at < gaps.length; at += 1) {
    const others = [];
    for (let near = 1; others.length < 4 && (at - near >= 0 || at + near < gaps.length); near += 1) {
      if (at - near >= 0 && between[at - near]) others.push(gaps[at - near]);
      if (others.length < 4 && at + near < gaps.length && between[at + near]) others.push(gaps[at + near]);
    }
    const pitch = others.length ? median(others) : gaps[at];
    const value = order[at + 1].value;
    const steps = pitch > 0 ? (value - anchor) / pitch : 1;
    if (steps >= SAME_PLACE) {
      place += Math.max(1, Math.round(steps));
      anchor = value;
    }
    result[order[at + 1].at] = place;
  }
  if (place < COLUMNS) return result;
  let bestStart = 0;
  let most = -1;
  for (let start = 0; start + COLUMNS - 1 <= place; start += 1) {
    const inside = result.filter((at) => at >= start && at < start + COLUMNS).length;
    if (inside > most) {
      most = inside;
      bestStart = start;
    }
  }
  const kept = result.map((at) => (at >= bestStart && at < bestStart + COLUMNS ? at : null));
  const first = Math.min(...kept.filter((at) => at !== null));
  return kept.map((at) => (at === null ? null : at - first));
}

// The stubs: the points chained by standing one place apart on both grids. Neighbouring
// stubs of neighbouring snakes chain into one.
function stubsOf(points) {
  return chained(points.length, (a, b) => Math.abs(points[a].xPlace - points[b].xPlace) === 1 && Math.abs(points[a].yPlace - points[b].yPlace) === 1);
}

// Whether the wall is seen from the side: the diagonal's stubs rise to the right when it
// is seen upright, and fall to the right when it is turned a quarter either way.
function isTurned(stubs, points) {
  let rising = 0;
  let falling = 0;
  for (const stub of stubs) {
    const sorted = [...stub].sort((a, b) => points[a].xPlace - points[b].xPlace);
    for (let at = 1; at < sorted.length; at += 1) {
      if (points[sorted[at]].yPlace > points[sorted[at - 1]].yPlace) rising += 1;
      else falling += 1;
    }
  }
  return falling > rising;
}

// The points with their places on the wall's own grids, the columns of the positions and
// the rows of the heights, when the wires' edge is at this side of the picture.
function framed(points, side, xSpan, ySpan) {
  return points.map((point) => {
    const {xPlace, yPlace} = point;
    if (side === "bottom") return {...point, col: xPlace, row: yPlace};
    if (side === "top") return {...point, col: xSpan - xPlace, row: ySpan - yPlace};
    if (side === "left") return {...point, col: ySpan - yPlace, row: xPlace};
    return {...point, col: yPlace, row: xSpan - xPlace};
  });
}

// The places of the picture's grids of a column and a row of the wall, with the wires'
// edge at this side: the inverse of `framed`.
function unframed(col, row, side, xSpan, ySpan) {
  if (side === "bottom") return {xPlace: col, yPlace: row};
  if (side === "top") return {xPlace: xSpan - col, yPlace: ySpan - row};
  if (side === "left") return {xPlace: row, yPlace: ySpan - col};
  return {xPlace: xSpan - row, yPlace: col};
}

// The residue, 0 to 2, that the first place of an axis is shifted by for the LEDs to
// stand in threes: the one at which the most stubs part into threes of consecutive
// places, and then the most into twos.
function residueOf(stubs, points, axis) {
  let best = 0;
  let most = -1;
  for (let r = 0; r < 3; r += 1) {
    let score = 0;
    for (const stub of stubs) {
      const parts = new Map();
      for (const at of stub) {
        const place = points[at][axis];
        const key = Math.floor((place + r) / 3);
        parts.set(key, (parts.get(key) || new Set()).add(place));
      }
      for (const part of parts.values()) {
        if (part.size === 3) score += 3;
        else if (part.size === 2) score += 1;
      }
    }
    if (score > most) {
      most = score;
      best = r;
    }
  }
  return best;
}

// The reading of one side and one pair of offsets: which snake each position shows, by
// the most votes of its LEDs, and the positions no LED is at filled with the numbers no
// position shows, in order. A snake two positions claim stays with the one with more
// votes.
function reading(points, side, xOffset, yOffset, xEnd, yEnd) {
  const votes = Array.from({length: SNAKES}, () => new Map());
  for (const point of points) {
    const position = Math.floor((point.col + xOffset) / 3);
    const snake = Math.floor((point.row + yOffset) / 3) + 1;
    if (position < 0 || position >= SNAKES || snake < 1 || snake > SNAKES) continue;
    votes[position].set(snake, (votes[position].get(snake) || 0) + 1);
  }
  const claims = votes.map((counts) => {
    let chosen = null;
    let most = 0;
    for (const [snake, count] of [...counts.entries()].sort((a, b) => a[0] - b[0])) {
      if (count > most) {
        most = count;
        chosen = snake;
      }
    }
    return {snake: chosen, count: most};
  });
  const positions = new Array(SNAKES).fill(null);
  const holders = new Map();
  claims.forEach((claim, at) => {
    if (claim.snake === null) return;
    const other = holders.get(claim.snake);
    if (other === undefined || claims[other].count < claim.count) {
      if (other !== undefined) positions[other] = null;
      holders.set(claim.snake, at);
      positions[at] = claim.snake;
    }
  });
  const taken = new Set(positions.filter((snake) => snake !== null));
  const free = [];
  for (let snake = 1; snake <= SNAKES; snake += 1) {
    if (!taken.has(snake)) free.push(snake);
  }
  const filled = [];
  positions.forEach((snake, at) => {
    if (snake === null) filled.push({position: at + 1, snake: free.shift()});
  });
  return {side, xOffset, yOffset, xEnd, yEnd, positions, filled};
}

// The reading of a picture: `{points, readings, ignored, found, turned, frame}`, or
// `{refused: true, found, why}` when the picture holds no steady set of bright peaks
// (`"many"`), fewer than two lit LEDs (`"few"`), or LEDs that fit no grid of sixty places
// (`"grid"`). `found` counts the bright peaks at the level read, or at the floor when no
// level is. The readings come in the order of the sides, the wires' edge at the bottom or
// the left first, and for each side of the offsets that keep the threes whole.
export function analyse(picture) {
  const grey = smoothed(picture);
  const floor = medianGrey(grey) + ABOVE_MEDIAN;
  const all = peaks(picture.width, picture.height, grey, floor);
  const level = levelOf(all, floor);
  if (level === null) return {refused: true, found: all.length, why: "many"};
  const found = all.filter((peak) => peak.value >= level);
  const widths = found.map((peak) => glowWidth(picture.width, picture.height, grey, level, peak));
  const typical = widths.length ? median(widths) : 0;
  const leds = oneLedEach(found.map((peak, at) => ({...peak, width: widths[at]})), Math.max(2, ONE_LED * typical));
  const kept = leds.filter((led) => led.width <= NOISE_WIDER * typical);
  let ignored = leds.length - kept.length;
  if (kept.length < 2) return {refused: true, found: found.length, why: "few"};
  const {k, m, points: slanted} = unslanted(kept);
  const xPlaces = places(slanted.map((point) => point.u));
  // Rows count from the bottom: the larger v, the lower the place.
  const yPlaces = places(slanted.map((point) => -point.v));
  // A point beyond the sixty places of either grid is noise.
  const points = slanted.map((point, at) => ({x: point.x, y: point.y, u: point.u, v: point.v, xPlace: xPlaces[at], yPlace: yPlaces[at]}))
    .filter((point) => point.xPlace !== null && point.yPlace !== null);
  ignored += slanted.length - points.length;
  if (points.length < 2) return {refused: true, found: found.length, why: "grid"};
  const xSpan = Math.max(...points.map((point) => point.xPlace));
  const ySpan = Math.max(...points.map((point) => point.yPlace));
  const stubs = stubsOf(points);
  const turned = isTurned(stubs, points);
  // The offsets that keep the threes whole: the first of each axis's possible ones and the
  // last; one reading when they are the same.
  const offsets = (first, span) => {
    const most = COLUMNS - 1 - span;
    const last = first + 3 * Math.floor((most - first) / 3);
    return last > first ? [first, last] : [first];
  };
  const readings = [];
  for (const side of SIDES[turned ? "turned" : "upright"]) {
    const onWall = framed(points, side, xSpan, ySpan);
    const xOffsets = offsets(residueOf(stubs, onWall, "col"), Math.max(...onWall.map((point) => point.col)));
    const yOffsets = offsets(residueOf(stubs, onWall, "row"), Math.max(...onWall.map((point) => point.row)));
    for (const xOffset of xOffsets) {
      for (const yOffset of yOffsets) {
        const xEnd = xOffsets.length === 1 ? null : xOffset === xOffsets[0] ? "right" : "left";
        const yEnd = yOffsets.length === 1 ? null : yOffset === yOffsets[0] ? "highest" : "lowest";
        readings.push(reading(onWall, side, xOffset, yOffset, xEnd, yEnd));
      }
    }
  }
  return {points, readings, ignored, found: found.length, turned, frame: frameOf(points, k, m, xSpan, ySpan)};
}

// Where a column and a row of the wall lie in the picture: a line fitted through the
// points' places on each axis of the unslanted frame, and the slant put back.
function frameOf(points, k, m, xSpan, ySpan) {
  const fit = (pairs) => {
    const n = pairs.length;
    const sumP = pairs.reduce((sum, [p]) => sum + p, 0);
    const sumC = pairs.reduce((sum, [, c]) => sum + c, 0);
    const sumPP = pairs.reduce((sum, [p]) => sum + p * p, 0);
    const sumPC = pairs.reduce((sum, [p, c]) => sum + p * c, 0);
    const div = n * sumPP - sumP * sumP;
    const slope = div === 0 ? 0 : (n * sumPC - sumP * sumC) / div;
    return {slope, start: (sumC - slope * sumP) / n};
  };
  const across = fit(points.map((point) => [point.xPlace, point.u]));
  const up = fit(points.map((point) => [point.yPlace, -point.v]));
  const div = 1 - k * m;
  return {
    // The picture's point of a position and a snake's height, from 1, with the side and
    // the offsets of a reading: the middle LED of the stub.
    point(position, snake, chosen) {
      const col = 3 * position - 2 - chosen.xOffset;
      const row = 3 * snake - 2 - chosen.yOffset;
      const {xPlace, yPlace} = unframed(col, row, chosen.side, xSpan, ySpan);
      const u = across.start + across.slope * xPlace;
      const v = -(up.start + up.slope * yPlace);
      return {x: (u + k * v) / div, y: (v + m * u) / div};
    },
    pitch: (Math.abs(across.slope) + Math.abs(up.slope)) / 2,
  };
}

// The pins of snakes 1 to 20 after a reading: position p gets the pin that drives the
// snake it shows today.
export function assignment(current, chosen) {
  const next = new Array(SNAKES);
  const filled = new Map(chosen.filled.map((entry) => [entry.position, entry.snake]));
  for (let position = 1; position <= SNAKES; position += 1) {
    const snake = chosen.positions[position - 1] ?? filled.get(position);
    next[position - 1] = current[snake - 1];
  }
  return next;
}
