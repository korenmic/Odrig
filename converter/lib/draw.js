// The pictures the player draws of a text and of a clock, by the rules of docs/format.md,
// in whole numbers only, so that they are the core's pixels exactly.

import {FONT_TABLES, SINE} from "./fonttables.js";
import {glyphIndex} from "./textlayout.js";

export const EFFECTS = ["static", "marquee", "slide", "pan"];
export const MOTIONS = ["left", "right", "up", "down"];
export const ALIGNS = ["left", "center", "right"];
export const VALIGNS = ["top", "middle", "bottom"];
export const DIRECTIONS = ["auto", "ltr", "rtl"];
export const FASTEST = 240;
export const LONGEST_PAUSE = 65535;
export const SHORTEST_STATIC = 20;

// The milliseconds `distance` pixels take at `speed` pixels a second, rounded up.
function steps(distance, speed) {
  return Math.floor((distance * 1000 + speed - 1) / speed);
}

// The pixels the block has moved `t` milliseconds into a motion.
function moved(t, speed) {
  return Math.floor((t * speed) / 1000);
}

function horizontal(motion) {
  return motion === "left" || motion === "right";
}

// Where the block rests on the canvas: x by the alignment, y by the vertical alignment.
export function rest(settings, block, canvas) {
  const free = canvas.width - block.width;
  const x = settings.align === "center" ? Math.floor(free / 2) : settings.align === "right" ? free : 0;
  const high = canvas.height - block.height;
  const y = settings.valign === "middle" ? Math.floor(high / 2) : settings.valign === "bottom" ? high : 0;
  return {x, y};
}

// Whether all of the block can be seen with these settings: a static or sliding block fits
// the canvas, and a moving one fits it across its motion.
export function fits(settings, block, canvas) {
  const wide = block.width <= canvas.width;
  const tall = block.height <= canvas.height;
  if (settings.effect === "static" || settings.effect === "slide") return wide && tall;
  return horizontal(settings.motion) ? tall : wide;
}

// The motion along one axis: the canvas's size, the block's and its rest, by the motion.
function axis(settings, block, canvas) {
  const at = rest(settings, block, canvas);
  if (horizontal(settings.motion)) {
    return {size: canvas.width, length: block.width, rest: at.x, forward: settings.motion === "right"};
  }
  return {size: canvas.height, length: block.height, rest: at.y, forward: settings.motion === "down"};
}

// The parts of a pass: for each, its milliseconds.
function parts(settings, block, canvas) {
  const {speed, pause} = settings;
  if (settings.effect === "static") return {hold: pause};
  const line = axis(settings, block, canvas);
  if (settings.effect === "marquee") return {move: steps(line.size + line.length, speed)};
  if (settings.effect === "slide") {
    const inward = line.forward ? line.rest + line.length : line.size - line.rest;
    const outward = line.forward ? line.size - line.rest : line.rest + line.length;
    return {inward: steps(inward, speed), hold: pause, outward: steps(outward, speed)};
  }
  const travel = Math.max(0, line.length - line.size);
  return {hold: pause, move: steps(travel, speed), travel};
}

// The length of a pass in milliseconds.
export function passMs(settings, block, canvas) {
  const made = parts(settings, block, canvas);
  if (settings.effect === "static") return made.hold;
  if (settings.effect === "marquee") return made.move;
  if (settings.effect === "slide") return made.inward + made.hold + made.outward;
  return Math.max(SHORTEST_STATIC, 2 * made.hold + 2 * made.move);
}

// The place of the block's top left corner on the canvas `t` milliseconds into a pass,
// with rows counted from the top.
export function placeAt(settings, block, canvas, t) {
  const at = rest(settings, block, canvas);
  if (settings.effect === "static") return at;
  const line = axis(settings, block, canvas);
  const made = parts(settings, block, canvas);
  const {speed} = settings;
  let place;
  if (settings.effect === "marquee") {
    place = line.forward ? -line.length + moved(t, speed) : line.size - moved(t, speed);
  } else if (settings.effect === "slide") {
    if (t < made.inward) {
      place = line.forward ? Math.min(line.rest, -line.length + moved(t, speed)) : Math.max(line.rest, line.size - moved(t, speed));
    } else if (t < made.inward + made.hold) {
      place = line.rest;
    } else {
      const out = moved(t - made.inward - made.hold, speed);
      place = line.forward ? line.rest + out : line.rest - out;
    }
  } else {
    // A pan shows the block from one end to the other and back, holding at each end; when
    // the block fits it rests where its alignment puts it.
    const from = made.travel === 0 ? line.rest : line.forward ? line.size - line.length : 0;
    const sign = line.forward ? 1 : -1;
    const far = from + sign * made.travel;
    if (t < made.hold) place = from;
    else if (t < made.hold + made.move) place = from + sign * Math.min(made.travel, moved(t - made.hold, speed));
    else if (t < 2 * made.hold + made.move) place = far;
    else place = far - sign * Math.min(made.travel, moved(t - 2 * made.hold - made.move, speed));
  }
  return horizontal(settings.motion) ? {x: place, y: at.y} : {x: at.x, y: place};
}

// Draws a text, decoded as `odrgx.decodeText` gives it, `t` milliseconds into its pass, into
// `picture`, three bytes for each pixel in the pixel order of docs/format.md: the
// background, and each lit pixel of each glyph that meets the canvas in the colour, a
// square of the font's scale.
export function drawText(decoded, font, t, picture) {
  const {width, height} = decoded.header;
  const {settings, block} = decoded;
  const colour = [(settings.color >>> 16) & 0xff, (settings.color >>> 8) & 0xff, settings.color & 0xff];
  const background = [(settings.background >>> 16) & 0xff, (settings.background >>> 8) & 0xff, settings.background & 0xff];
  for (let pixel = 0; pixel < width * height; pixel += 1) {
    picture.set(background, 3 * pixel);
  }
  const at = placeAt(settings, block, {width, height}, t);
  const rows = font.rows;
  const scale = font.scale;
  for (const glyph of decoded.glyphs) {
    const cellX = at.x + glyph.x;
    const cellY = at.y + glyph.y;
    const glyphWidth = font.table.widths[glyph.glyph];
    if (cellX >= width || cellY >= height || cellX + glyphWidth * scale <= 0 || cellY + rows * scale <= 0) continue;
    for (let row = 0; row < rows; row += 1) {
      const bits = font.table.rows[glyph.glyph * rows + row];
      for (let column = 0; bits !== 0 && column < glyphWidth; column += 1) {
        if ((bits & (0x80 >> column)) === 0) continue;
        for (let down = 0; down < scale; down += 1) {
          for (let across = 0; across < scale; across += 1) {
            const x = cellX + column * scale + across;
            const y = cellY + row * scale + down;
            if (x >= 0 && x < width && y >= 0 && y < height) {
              picture.set(colour, 3 * ((height - 1 - y) * width + x));
            }
          }
        }
      }
    }
  }
  return picture;
}

// The clocks. A clock shows an imaginary time, its virtual time, which its seed and the
// milliseconds since its turn began give. Positions are in half pixels from the canvas's
// centre, with y growing downwards; angles in 1/2^26 of a turn, from 12 o'clock clockwise;
// sines in units of 1/16,384.
export const WIDGETS = ["analog", "digital", "melting"];
export const LONGEST_CLOCK = 3600;
export const FASTEST_CLOCK = 3600;

const HALF_DAY = 43200000;
const HOUR = 3600000;
const MINUTE = 60000;
const TURN = 67108864;
const STEP = 65536;
const ONE = 16384;
// 2 pi times 16,384, rounded.
const TWO_PI = 102944;
// The parts of a dial, and what is drawn of each in which colour of the settings.
const NOTHING = 0;
const FACE = 1;
const RIM = 2;
const HANDS = 3;

// Floor division of whole numbers by a positive one, exact below 2^53.
function fdiv(x, y) {
  let q = Math.floor(x / y);
  if (q * y > x) q -= 1;
  else if ((q + 1) * y <= x) q += 1;
  return q;
}

function fmod(x, y) {
  return x - fdiv(x, y) * y;
}

// MurmurHash3's finalizer: 32 bits in, 32 bits out, every bit of the input in each.
export function mix(value) {
  let h = value >>> 0;
  h = (h ^ (h >>> 16)) >>> 0;
  h = Math.imul(h, 0x85ebca6b) >>> 0;
  h = (h ^ (h >>> 13)) >>> 0;
  h = Math.imul(h, 0xc2b2ae35) >>> 0;
  return (h ^ (h >>> 16)) >>> 0;
}

// The noise after a refresh asked for at a timestamp, and the seed of a clock's turn: the
// noise mixed with the item's id and the turn's start, never 0.
export function stir(noise, timestamp) {
  return mix((noise ^ fmod(timestamp, 4294967296)) >>> 0);
}

export function seedOf(noise, id, start) {
  const seed = mix((noise ^ mix((id ^ fmod(start, 4294967296)) >>> 0)) >>> 0);
  return seed === 0 ? 1 : seed;
}

function xorshift(value) {
  let x = value;
  x = (x ^ (x << 13)) >>> 0;
  x = (x ^ (x >>> 17)) >>> 0;
  return (x ^ (x << 5)) >>> 0;
}

// What a seed chooses for a clock of these settings, in this order from xorshift32: the
// start of the virtual time, its base speed, the swing of the speed about it, the swing's
// period and its phase; then the melting watch's tilt in degrees, where it folds, as a
// percentage of its radius below its centre, how far the hanging face stretches and how
// fast it narrows, in percent, its shear and the wave of the fold in half pixels.
export function clockOf(settings, seed) {
  let state = seed === 0 ? 1 : seed;
  const next = () => {
    state = xorshift(state);
    return state;
  };
  const start = next() % HALF_DAY;
  const least = settings.speedMin;
  const greatest = settings.speedMax;
  const base = least + (next() % (greatest - least + 1));
  const swing = fdiv(Math.min(base - least, greatest - base) * (next() % 101), 102);
  const period = 6000 + (next() % 14001);
  const phase = next() % 1024;
  const tilt = 25 + (next() % 16);
  const fold = next() % 21;
  const stretch = 130 + (next() % 41);
  const narrow = 20 + (next() % 31);
  const shear = 10 + (next() % 21);
  const wave = 2 + (next() % 3);
  return {start, base, swing, period, phase, tilt, fold, stretch, narrow, shear, wave};
}

// The sine of an angle from the table, read between its entries in steps of 1/65,536.
export function sine(angle) {
  const at = fmod(angle, TURN);
  const index = Math.floor(at / STEP);
  const low = SINE[index];
  const high = SINE[(index + 1) % SINE.length];
  return low + fdiv((high - low) * (at % STEP), STEP);
}

export function cosine(angle) {
  return sine(angle + TURN / 4);
}

// The virtual time `t` milliseconds into the turn, in milliseconds and not yet taken
// modulo 12 hours: the start, the base speed's way and the swing of a cosine about it.
export function virtualTime(clock, t) {
  const turned = fdiv(TURN * (t % clock.period), clock.period);
  const from = clock.phase * STEP;
  const swung = fdiv(clock.swing * clock.period * (cosine(from) - cosine(from + turned)), TWO_PI);
  return clock.start + clock.base * t + swung;
}

// The straight parts of a dial of a radius: the hour hand, the minute hand and the twelve
// marks, each a direction and the band along it that is drawn.
function strokes(time, radius) {
  const made = [];
  const add = (angle, from, to, half) => made.push({x: sine(angle), y: -cosine(angle), from, to, half});
  add(fdiv(TURN * (time % HALF_DAY), HALF_DAY), 0, fdiv(radius * 55, 100), 2);
  add(fdiv(TURN * (time % HOUR), HOUR), 0, fdiv(radius * 85, 100), 1);
  const outer = radius - 6;
  const inner = outer - fdiv(radius, 7);
  for (let mark = 0; mark < 12; mark += 1) add(fdiv(mark * TURN, 12), inner, outer, 1);
  return made;
}

// What a point of a dial is: nothing outside its disc, the rim, the pivot, a hand or a mark,
// or the face. Where the canvas shows the dial narrower, `wide` percent widens the strokes
// so that none falls between the pixels.
function dialAt(u, w, radius, made, wide = 100) {
  const distance = u * u + w * w;
  if (distance > radius * radius) return NOTHING;
  if (distance > (radius - 4) * (radius - 4)) return RIM;
  if (distance <= 16) return HANDS;
  for (const stroke of made) {
    const along = u * stroke.x + w * stroke.y;
    if (along < stroke.from * ONE || along > stroke.to * ONE) continue;
    if (100 * Math.abs(u * stroke.y - w * stroke.x) <= stroke.half * ONE * wide) return HANDS;
  }
  return FACE;
}

function colourOf(value) {
  return [(value >>> 16) & 0xff, (value >>> 8) & 0xff, value & 0xff];
}

function put(picture, canvas, x, y, colour) {
  picture.set(colour, 3 * ((canvas.height - 1 - y) * canvas.width + x));
}

// The radius of the largest dial the canvas holds, in half pixels, a pixel from its edge.
function dialRadius(canvas) {
  return 2 * (Math.floor(Math.min(canvas.width, canvas.height) / 2) - 1);
}

function drawAnalog(settings, time, canvas, picture) {
  const colours = [settings.background, settings.face, settings.rim, settings.hands].map(colourOf);
  const radius = dialRadius(canvas);
  const made = strokes(time, radius);
  for (let y = 0; y < canvas.height; y += 1) {
    for (let x = 0; x < canvas.width; x += 1) {
      const part = radius > 0 ? dialAt(2 * x + 1 - canvas.width, 2 * y + 1 - canvas.height, radius, made) : NOTHING;
      put(picture, canvas, x, y, colours[part]);
    }
  }
}

// The digital clock: h:mm in the large font, centred, the colon shown in the first half of
// each real second.
function drawDigital(settings, time, t, canvas, picture) {
  const background = colourOf(settings.background);
  for (let y = 0; y < canvas.height; y += 1) {
    for (let x = 0; x < canvas.width; x += 1) put(picture, canvas, x, y, background);
  }
  const table = FONT_TABLES[1];
  const scale = 2;
  const rows = table.ascent + table.descent;
  const hour = Math.floor(time / HOUR) % 12 || 12;
  const minute = Math.floor(time / MINUTE) % 60;
  const shown = `${hour}:${String(minute).padStart(2, "0")}`;
  const glyphs = [...shown].map((character) => glyphIndex(table, character.charCodeAt(0)));
  const width = glyphs.reduce((sum, glyph) => sum + (table.widths[glyph] + 1) * scale, 0) - scale;
  let left = fdiv(canvas.width - width, 2);
  const top = fdiv(canvas.height - rows * scale, 2);
  const colon = t % 1000 < 500;
  for (const [place, glyph] of glyphs.entries()) {
    const isColon = shown[place] === ":";
    const colour = colourOf(isColon ? settings.rim : settings.face);
    for (let row = 0; (!isColon || colon) && row < rows; row += 1) {
      const bits = table.rows[glyph * rows + row];
      for (let column = 0; column < table.widths[glyph]; column += 1) {
        if ((bits & (0x80 >> column)) === 0) continue;
        for (let down = 0; down < scale; down += 1) {
          for (let across = 0; across < scale; across += 1) {
            const x = left + column * scale + across;
            const y = top + row * scale + down;
            if (x >= 0 && x < canvas.width && y >= 0 && y < canvas.height) put(picture, canvas, x, y, colour);
          }
        }
      }
    }
    left += (table.widths[glyph] + 1) * scale;
  }
}

// The melting watch. Its dial is drawn as the analog clock's, smaller, tilted, and folded:
// above the fold it lies flat; below it the face hangs straight down, stretched, narrowing
// towards a drip, and darker the deeper it hangs. The fold waves with the real time. A
// crown and a ring sit at the top of the rim.
function drawMelting(settings, clock, time, t, canvas, picture) {
  const background = colourOf(settings.background);
  const colours = [settings.background, settings.face, settings.rim, settings.hands].map(colourOf);
  const whole = dialRadius(canvas);
  const radius = fdiv(whole * 66, 100);
  const made = strokes(time, radius);
  const tilt = fdiv(clock.tilt * TURN, 360);
  const c = cosine(tilt);
  const s = sine(tilt);
  const centreX = -fdiv(whole * 6, 100);
  const centreY = -fdiv(whole * 12, 100);
  const foldAt = fdiv(radius * clock.fold, 100);
  const phase = fdiv(TURN * (t % 7000), 7000);
  const ring = radius + 9;
  for (let y = 0; y < canvas.height; y += 1) {
    for (let x = 0; x < canvas.width; x += 1) {
      let colour = background;
      if (radius > 4) {
        const dx = 2 * x + 1 - canvas.width - centreX;
        const dy = 2 * y + 1 - canvas.height - centreY;
        // The place along the fold above this pixel, and the fold's height there.
        const guess = fdiv(dx * ONE - foldAt * s, c);
        const fold = foldAt + fdiv(clock.wave * sine(fdiv(guess * TURN, 2 * radius) + phase), ONE);
        const along = fdiv(dx * ONE - fold * s, c);
        const foldY = fdiv(fold * c - along * s, ONE);
        let u;
        let w;
        let shade = 256;
        let wide = 100;
        if (dy <= foldY) {
          u = fdiv(dx * c - dy * s, ONE);
          w = fdiv(dx * s + dy * c, ONE);
        } else {
          const deep = dy - foldY;
          const narrowed = radius + fdiv(deep * clock.narrow, 100);
          w = fold + fdiv(deep * 100, clock.stretch);
          u = fdiv((along - fdiv(deep * clock.shear, 100)) * narrowed, radius);
          wide = fdiv(100 * narrowed, radius);
          shade = deep <= 2 ? 150 : 256 - Math.min(140, fdiv(deep * 140, radius));
        }
        let part = dialAt(u, w, radius, made, wide);
        if (part === NOTHING && dy <= foldY) {
          const toRing = u * u + (w + ring) * (w + ring);
          if ((Math.abs(u) <= 2 && w < 0 && w >= -(radius + 5)) || (toRing >= 9 && toRing <= 36)) part = RIM;
        }
        if (part !== NOTHING) colour = colours[part].map((value) => fdiv(value * shade, 256));
      }
      put(picture, canvas, x, y, colour);
    }
  }
}

// Draws a clock of these settings with this seed `t` milliseconds into its turn into
// `picture`, three bytes for each pixel in the pixel order of docs/format.md.
export function drawClock(settings, seed, t, canvas, picture) {
  const clock = clockOf(settings, seed);
  const time = fmod(virtualTime(clock, t), HALF_DAY);
  if (settings.widget === "analog") drawAnalog(settings, time, canvas, picture);
  else if (settings.widget === "digital") drawDigital(settings, time, t, canvas, picture);
  else drawMelting(settings, clock, time, t, canvas, picture);
  return picture;
}
