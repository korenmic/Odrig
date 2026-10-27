// The analysis of a photo of the diagonal on photos this scenario makes, on the owner's
// photos of the unlit wall and of the diagonal, and on a JPEG turned by its orientation
// tag.

const DEFAULTS = [...Array.from({length: 18}, (_, at) => at + 1), 21, 47];
const SNAKES = 20;

// The snake that position p shows when the board's pins are these and the wall is wired
// as the defaults say: position p has the pin DEFAULTS[p - 1].
function shows(pins, p) {
  return pins.indexOf(DEFAULTS[p - 1]) + 1;
}

// A photo of the wall as a phone would take it: 60 x 60 faint lenses on a wooden board in
// a dark room, the diagonal's stubs of the mapping, the dead positions dark, turned and
// slanted, blurred and grainy. `flash` lights every lens as a flash does; `spots` adds
// bright spots off the grid. A position of `crossed` is cross-wired, its chain up its first
// column, up its third and down its second, and shown as the core places it with the box
// off: its second and third pixels land on the other two columns, in the rows of the snake
// 21 - s. Gives the canvas.
export function photoCanvas(app, {pins = DEFAULTS, dead = [], crossed = [], spots = 0, angle = 0, skew = 0, squeeze = 1, blur = 1.2, grain = 6, flash = false, width = 640, height = 400} = {}) {
  const doc = app.doc;
  const pitch = 8;
  const side = 60 * pitch;
  const board = doc.createElement("canvas");
  board.width = side;
  board.height = side;
  const b = board.getContext("2d");
  b.fillStyle = "#2a251f";
  b.fillRect(0, 0, side, side);
  // The lenses: faint in the dark, and lit white by a flash, each a square.
  b.fillStyle = flash ? "#f0f0f0" : "#3c3c3c";
  const lens = flash ? 4 : 2;
  for (let col = 0; col < 60; col += 1) {
    for (let row = 0; row < 60; row += 1) {
      b.fillRect(col * pitch + 2, row * pitch + 2, lens, lens);
    }
  }
  const glowAt = (cx, cy, radius) => {
    const glow = b.createRadialGradient(cx, cy, 0, cx, cy, radius);
    glow.addColorStop(0, "white");
    glow.addColorStop(0.4, "rgba(255,255,255,0.9)");
    glow.addColorStop(1, "rgba(255,255,255,0)");
    b.fillStyle = glow;
    b.fillRect(cx - radius, cy - radius, 2 * radius, 2 * radius);
  };
  if (!flash) {
    for (let p = 1; p <= SNAKES; p += 1) {
      if (dead.includes(p)) continue;
      const s = shows(pins, p);
      for (let i = 0; i < 3; i += 1) {
        let col = 3 * p - 2 + i;
        let row = 3 * s - 2 + i;
        if (crossed.includes(p) && i === 1) [col, row] = [3 * p, 62 - 3 * s];
        else if (crossed.includes(p) && i === 2) [col, row] = [3 * p - 1, 61 - 3 * s];
        glowAt((col - 0.5) * pitch, side - (row - 0.5) * pitch, pitch * 0.9);
      }
    }
  }
  // Spots of noise: a large glow near a corner of the board and a tiny one in its middle.
  if (spots >= 1) glowAt(side * 0.08, side * 0.9, pitch * 4);
  if (spots >= 2) glowAt(side * 0.52, side * 0.47, pitch * 0.25);
  const made = doc.createElement("canvas");
  made.width = width;
  made.height = height;
  const c = made.getContext("2d", {willReadFrequently: true});
  const room = c.createLinearGradient(0, 0, width, height);
  room.addColorStop(0, "#0c0c10");
  room.addColorStop(1, "#262228");
  c.fillStyle = room;
  c.fillRect(0, 0, width, height);
  c.save();
  c.translate(width / 2, height / 2);
  c.rotate((angle * Math.PI) / 180);
  c.transform(1, 0, skew, squeeze, 0, 0);
  const scale = (Math.min(width, height) * 0.82) / side;
  c.scale(scale, scale);
  c.filter = `blur(${blur}px)`;
  c.drawImage(board, -side / 2, -side / 2);
  c.restore();
  const data = c.getImageData(0, 0, width, height);
  let seed = 7;
  const random = () => {
    seed = (seed * 1103515245 + 12345) & 0x7fffffff;
    return seed / 0x7fffffff;
  };
  for (let at = 0; at < data.data.length; at += 4) {
    const g = (random() - 0.5) * 2 * grain;
    data.data[at] += g;
    data.data[at + 1] += g;
    data.data[at + 2] += g;
  }
  c.putImageData(data, 0, 0);
  return made;
}

// The picture of such a photo, as `fromPixels` takes it.
function photo(app, photoModule, options = {}) {
  const canvas = photoCanvas(app, options);
  const context = canvas.getContext("2d", {willReadFrequently: true});
  return photoModule.fromPixels(context.getImageData(0, 0, canvas.width, canvas.height).data, canvas.width, canvas.height);
}

// The reading's facts the test compares: the readings' positions and fills, and the pins
// the first reading, or the one with this side and these ends, gives from the pins the
// photo was made with.
function facts(app, photoModule, result, pins, pick = null) {
  if (result.refused) return {refused: true, found: result.found, why: result.why};
  const fits = (reading) => ["side", "xEnd", "yEnd"].every((key) => pick[key] === undefined || reading[key] === pick[key]);
  const chosen = pick === null ? result.readings[0] : result.readings.find(fits);
  return {
    points: result.points.length,
    turned: result.turned,
    xSpan: Math.max(...result.points.map((point) => point.xPlace)),
    ySpan: Math.max(...result.points.map((point) => point.yPlace)),
    readings: result.readings.map((reading) => ({side: reading.side, xEnd: reading.xEnd, yEnd: reading.yEnd, filled: reading.filled, nulls: reading.positions.filter((snake) => snake === null).length})),
    ignored: result.ignored,
    found: result.found,
    positions: chosen ? chosen.positions : null,
    pins: chosen ? photoModule.assignment(pins, chosen) : null,
  };
}

export default async function(app) {
  const photoModule = await app.frame.contentWindow.eval('import("/photo.js")');
  const seen = {};
  const swapped = [...DEFAULTS];
  [swapped[0], swapped[9]] = [swapped[9], swapped[0]];
  const shuffled = [2, 3, 4, 5, 6, 7, 8, 9, 10, 12, 13, 14, 47, 15, 16, 17, 18, 21, 1, 11];
  const cases = {
    plain: {pins: DEFAULTS},
    shuffled: {pins: shuffled, angle: 4, skew: 0.06, squeeze: 0.85, blur: 1.5, grain: 8},
    keystone: {pins: shuffled, skew: -0.12, squeeze: 0.7, blur: 1.0},
    deadMiddle: {pins: shuffled, dead: [7]},
    deadEnd: {pins: swapped, dead: [1], angle: 2},
    twoDead: {pins: DEFAULTS, dead: [5, 12]},
    noise: {pins: shuffled, spots: 2, angle: -3},
    flash: {flash: true},
    // The wall seen from its right side, the wires' edge at the left of the picture, and
    // seen from its far edge, the wires at the top.
    fromTheSide: {pins: shuffled, angle: 93, skew: 0.04},
    fromTheFarEdge: {pins: shuffled, angle: 178},
    // Position 10 cross-wired and read with the box off.
    crossedTen: {pins: shuffled, crossed: [10]},
  };
  const picks = {deadEnd: {xEnd: "left", yEnd: null}, fromTheFarEdge: {side: "top"}};
  for (const [name, options] of Object.entries(cases)) {
    const picture = photo(app, photoModule, options);
    const started = performance.now();
    const result = photoModule.analyse(picture);
    seen[name] = {...facts(app, photoModule, result, options.pins || DEFAULTS, picks[name] || null), ms: Math.round(performance.now() - started)};
  }
  // The owner's photos of the unlit wall and of the diagonal, and the JPEG turned by its
  // orientation tag.
  seen.owner = {};
  for (const name of app.settings.photos) {
    const blob = await (await fetch(`/m/${name}`)).blob();
    const picture = await photoModule.readPhoto(blob);
    const result = photoModule.analyse(picture);
    seen.owner[name] = {width: picture.width, height: picture.height, refused: result.refused === true, found: result.found, why: result.why};
    if (!result.refused) {
      const first = result.readings[0];
      Object.assign(seen.owner[name], {points: result.points.length, ignored: result.ignored, turned: result.turned, side: first.side, readings: result.readings.length,
        positions: first.positions, filled: first.filled, distinct: new Set(first.positions.filter((snake) => snake !== null)).size});
    }
  }
  const turned = await (await fetch("/m/turned.jpg")).blob();
  const picture = await photoModule.readPhoto(turned);
  seen.turned = {width: picture.width, height: picture.height, ...facts(app, photoModule, photoModule.analyse(picture), DEFAULTS)};
  // The same wall as a PNG file of the phone, read through readPhoto and scaled.
  const canvas = photoCanvas(app, {pins: shuffled, angle: 3, width: 1280, height: 800});
  const png = await new Promise((resolve) => canvas.toBlob(resolve, "image/png"));
  const fromPng = await photoModule.readPhoto(new File([png], "wall.png", {type: "image/png"}));
  seen.png = {width: fromPng.width, height: fromPng.height, bytes: png.size, ...facts(app, photoModule, photoModule.analyse(fromPng), shuffled)};
  return seen;
}
