// The pictures the player draws of a text and of a clock, by the rules of docs/format.md,
// in whole numbers only, so that they are the core's pixels exactly.

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
