// The motions of a still picture: the frames of a tile that shows no time, made from its
// base picture of palette indices and the parts of its motion, as docs/converter.md,
// "clocks", says. Whole numbers only, with the sine table of the clocks, so that the same
// motion gives the same frames everywhere.

import {cosine, sine} from "./draw.js";
import {BAD_TYPE, OUT_OF_RANGE, Rejection} from "./errors.js";
import * as strictjson from "./strictjson.js";

export const KINDS = ["level", "flicker", "pulse", "turn", "swing"];
export const RESTS = ["bottom", "top", "left", "right"];
export const SHORTEST_LOOP = 10;
export const LONGEST_LOOP = 600;
export const SHORTEST_FRAME = 20;
export const LONGEST_FRAME = 1000;
export const MOST_PARTS = 8;
export const LONGEST_STEP = 60000;
export const MOST_DEGREES = 3600;
export const MOST_SWINGS = 60;

const TURN = 67108864;
const ONE = 16384;

// The members of a motion and of each kind of part, in the order in which they are written.
export const MOTION_MEMBERS = ["seconds", "frame_ms", "parts"];
export const PART_MEMBERS = {
  level: ["kind", "box", "inside", "fill", "empty", "rests", "start", "half"],
  flicker: ["kind", "box", "variants", "step_ms"],
  pulse: ["kind", "box", "variants"],
  turn: ["kind", "box", "moving", "behind", "centre", "degrees"],
  swing: ["kind", "box", "moving", "behind", "centre", "degrees", "swings"],
};

function fdiv(x, y) {
  let q = Math.floor(x / y);
  if (q * y > x) q -= 1;
  else if ((q + 1) * y <= x) q += 1;
  return q;
}

function whole(value, low, high, what) {
  return Number(strictjson.integer(value, low, high, what));
}

function indexOf(value, colours, what) {
  return whole(value, 0, colours - 1, what);
}

function indices(value, colours, what) {
  const list = strictjson.array(value, what);
  if (list.length < 1 || list.length > colours) throw new Rejection(OUT_OF_RANGE, `${what} has ${list.length} indices, not 1 to ${colours}`);
  return list.map((one, at) => indexOf(one, colours, `index ${at} of ${what}`));
}

function boxOf(value, width, height, what) {
  const box = strictjson.array(value, what);
  if (box.length !== 4) throw new Rejection(OUT_OF_RANGE, `${what} has ${box.length} numbers, not 4`);
  const left = whole(box[0], 0, width - 1, `the left of ${what}`);
  const top = whole(box[1], 0, height - 1, `the top of ${what}`);
  const wide = whole(box[2], 1, width - left, `the width of ${what}`);
  const high = whole(box[3], 1, height - top, `the height of ${what}`);
  return {left, top, width: wide, height: high};
}

function variantsOf(value, colours, least, most, what) {
  const list = strictjson.array(value, what);
  if (list.length < least || list.length > most) throw new Rejection(OUT_OF_RANGE, `${what} has ${list.length} variants, not ${least} to ${most}`);
  return list.map((variant, at) => {
    const name = `variant ${at} of ${what}`;
    return strictjson.array(variant, name).map((pair, place) => {
      const pairName = `pair ${place} of ${name}`;
      const both = strictjson.array(pair, pairName);
      if (both.length !== 2) throw new Rejection(OUT_OF_RANGE, `${pairName} has ${both.length} indices, not 2`);
      return [indexOf(both[0], colours, pairName), indexOf(both[1], colours, pairName)];
    });
  });
}

// A motion as an inventory has it, read strictly for a canvas and a palette of `colours`
// colours: `{seconds, frameMs, parts}`, each part with its kind's members.
export function loadsMotion(motion, width, height, colours, what = "the motion") {
  strictjson.members(motion, MOTION_MEMBERS, [], what);
  const seconds = whole(motion.get("seconds"), SHORTEST_LOOP, LONGEST_LOOP, `the seconds of ${what}`);
  const loopMs = 1000 * seconds;
  const frameMs = whole(motion.get("frame_ms"), SHORTEST_FRAME, LONGEST_FRAME, `the frame_ms of ${what}`);
  if (frameMs % 10 !== 0 || loopMs % frameMs !== 0) throw new Rejection(OUT_OF_RANGE, `frames of ${frameMs} ms of ${what} are not a multiple of 10 that divides its loop`);
  const list = strictjson.array(motion.get("parts"), `the parts of ${what}`);
  if (list.length < 1 || list.length > MOST_PARTS) throw new Rejection(OUT_OF_RANGE, `${what} has ${list.length} parts, not 1 to ${MOST_PARTS}`);
  const parts = list.map((part, at) => {
    const name = `part ${at + 1} of ${what}`;
    if (!(part instanceof Map)) throw new Rejection(BAD_TYPE, `${name} is not an object`);
    const kind = part.get("kind");
    if (typeof kind !== "string") throw new Rejection(BAD_TYPE, `the kind of ${name} is not a string`);
    if (!KINDS.includes(kind)) throw new Rejection(OUT_OF_RANGE, `the kind of ${name} is ${JSON.stringify(kind)}, not one of ${KINDS.join(", ")}`);
    strictjson.members(part, PART_MEMBERS[kind], [], name);
    const made = {kind, box: boxOf(part.get("box"), width, height, `the box of ${name}`)};
    if (kind === "level") {
      made.inside = indices(part.get("inside"), colours, `inside of ${name}`);
      made.fill = indexOf(part.get("fill"), colours, `the fill of ${name}`);
      made.empty = indexOf(part.get("empty"), colours, `the empty of ${name}`);
      const rests = part.get("rests");
      if (typeof rests !== "string") throw new Rejection(BAD_TYPE, `rests of ${name} is not a string`);
      if (!RESTS.includes(rests)) throw new Rejection(OUT_OF_RANGE, `rests of ${name} is ${JSON.stringify(rests)}, not one of ${RESTS.join(", ")}`);
      made.rests = rests;
      made.start = whole(part.get("start"), 0, 100, `start of ${name}`);
      made.half = whole(part.get("half"), 0, 100, `half of ${name}`);
    } else if (kind === "flicker" || kind === "pulse") {
      made.variants = variantsOf(part.get("variants"), colours, 2, kind === "flicker" ? 3 : 8, `the variants of ${name}`);
      if (kind === "flicker") {
        made.stepMs = whole(part.get("step_ms"), SHORTEST_FRAME, LONGEST_STEP, `the step_ms of ${name}`);
        if (loopMs % (made.stepMs * made.variants.length) !== 0) {
          throw new Rejection(OUT_OF_RANGE, `the loop of ${what} is not a whole number of rounds of the ${made.variants.length} variants of ${name}`);
        }
      }
    } else {
      made.moving = indices(part.get("moving"), colours, `moving of ${name}`);
      made.behind = indexOf(part.get("behind"), colours, `behind of ${name}`);
      const centre = strictjson.array(part.get("centre"), `the centre of ${name}`);
      if (centre.length !== 2) throw new Rejection(OUT_OF_RANGE, `the centre of ${name} has ${centre.length} numbers, not 2`);
      made.centre = [whole(centre[0], 0, 2 * width, `the centre of ${name}`), whole(centre[1], 0, 2 * height, `the centre of ${name}`)];
      if (kind === "turn") {
        made.degrees = whole(part.get("degrees"), -MOST_DEGREES, MOST_DEGREES, `the degrees of ${name}`);
      } else {
        made.degrees = whole(part.get("degrees"), 1, 180, `the degrees of ${name}`);
        made.swings = whole(part.get("swings"), 1, MOST_SWINGS, `the swings of ${name}`);
      }
    }
    return made;
  });
  return {seconds, frameMs, parts};
}

// The motion as an inventory writes it.
export function dumpsMotion(motion) {
  return {
    seconds: motion.seconds,
    frame_ms: motion.frameMs,
    parts: motion.parts.map((part) => {
      const box = [part.box.left, part.box.top, part.box.width, part.box.height];
      if (part.kind === "level") return {kind: part.kind, box, inside: part.inside, fill: part.fill, empty: part.empty, rests: part.rests, start: part.start, half: part.half};
      if (part.kind === "flicker") return {kind: part.kind, box, variants: part.variants, step_ms: part.stepMs};
      if (part.kind === "pulse") return {kind: part.kind, box, variants: part.variants};
      if (part.kind === "turn") return {kind: part.kind, box, moving: part.moving, behind: part.behind, centre: part.centre, degrees: part.degrees};
      return {kind: part.kind, box, moving: part.moving, behind: part.behind, centre: part.centre, degrees: part.degrees, swings: part.swings};
    }),
  };
}

// The place of pixel x, y, counted from the top left, in the pixel order of docs/format.md.
function at(height, width, x, y) {
  return (height - 1 - y) * width + x;
}

function recolour(picture, canvas, box, pairs) {
  const map = new Map(pairs);
  for (let y = box.top; y < box.top + box.height; y += 1) {
    for (let x = box.left; x < box.left + box.width; x += 1) {
      const p = at(canvas.height, canvas.width, x, y);
      if (map.has(picture[p])) picture[p] = map.get(picture[p]);
    }
  }
}

// The pixels of a box that are of `moving` turned about the centre by the angle `angle`,
// in 2^26ths of a turn, clockwise on the canvas; where they were and are no longer, `behind`.
function turned(picture, canvas, part, angle) {
  const before = picture.slice();
  const moving = new Set(part.moving);
  const c = cosine(angle);
  const s = sine(angle);
  const [cx, cy] = part.centre;
  const {box} = part;
  for (let y = box.top; y < box.top + box.height; y += 1) {
    for (let x = box.left; x < box.left + box.width; x += 1) {
      const du = 2 * x + 1 - cx;
      const dv = 2 * y + 1 - cy;
      const fromX = fdiv(cx + fdiv(du * c + dv * s, ONE), 2);
      const fromY = fdiv(cy + fdiv(-du * s + dv * c, ONE), 2);
      const p = at(canvas.height, canvas.width, x, y);
      const inside = fromX >= box.left && fromX < box.left + box.width && fromY >= box.top && fromY < box.top + box.height;
      const source = inside ? before[at(canvas.height, canvas.width, fromX, fromY)] : -1;
      if (inside && moving.has(source)) picture[p] = source;
      else if (moving.has(before[p])) picture[p] = part.behind;
    }
  }
}

function level(picture, canvas, part, t, loopMs) {
  const {box} = part;
  const across = part.rests === "bottom" || part.rests === "top" ? box.height : box.width;
  const share = fdiv(across * (part.start * loopMs + (part.half - part.start) * (loopMs - Math.abs(2 * t - loopMs))), 100 * loopMs);
  const inside = new Set(part.inside);
  for (let y = box.top; y < box.top + box.height; y += 1) {
    for (let x = box.left; x < box.left + box.width; x += 1) {
      const p = at(canvas.height, canvas.width, x, y);
      if (!inside.has(picture[p])) continue;
      const from = {bottom: box.top + box.height - 1 - y, top: y - box.top, left: x - box.left, right: box.left + box.width - 1 - x}[part.rests];
      picture[p] = from < share ? part.fill : part.empty;
    }
  }
}

// The picture of palette indices a motion shows `t` milliseconds into its loop, in the
// pixel order of docs/format.md: the parts applied in their order to the base picture.
export function pictureAt(base, canvas, motion, t) {
  const loopMs = 1000 * motion.seconds;
  const picture = Uint8Array.from(base);
  for (const part of motion.parts) {
    if (part.kind === "level") {
      level(picture, canvas, part, t, loopMs);
    } else if (part.kind === "flicker") {
      recolour(picture, canvas, part.box, part.variants[Math.floor(t / part.stepMs) % part.variants.length]);
    } else if (part.kind === "pulse") {
      const count = part.variants.length;
      const step = fdiv(t * (2 * count - 2), loopMs);
      recolour(picture, canvas, part.box, part.variants[step < count ? step : 2 * count - 2 - step]);
    } else if (part.kind === "turn") {
      turned(picture, canvas, part, fdiv(TURN * part.degrees * t, 360 * loopMs));
    } else {
      turned(picture, canvas, part, fdiv(part.degrees * TURN * sine(fdiv(TURN * part.swings * t, loopMs)), 360 * ONE));
    }
  }
  return picture;
}

// The frames of a motion, as `odrg.encode` takes them: a picture of three bytes for each
// pixel every `frameMs` milliseconds over the loop.
export function framesOf(base, palette, canvas, motion) {
  const loopMs = 1000 * motion.seconds;
  const frames = [];
  for (let t = 0; t < loopMs; t += motion.frameMs) {
    const indicesNow = pictureAt(base, canvas, motion, t);
    const picture = new Uint8Array(3 * indicesNow.length);
    indicesNow.forEach((index, p) => {
      const colour = palette[index];
      picture[3 * p] = colour >>> 16;
      picture[3 * p + 1] = (colour >>> 8) & 0xff;
      picture[3 * p + 2] = colour & 0xff;
    });
    frames.push({ms: motion.frameMs, picture});
  }
  return {width: canvas.width, height: canvas.height, frames};
}
