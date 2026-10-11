/* Prints what layout.js computes for a mapping file, as one JSON document.
   Run in the JavaScript shell after the page's scripts:
   jsc board.js layout.js dump_layout.js -- MAPPING [QUESTIONS]
   QUESTIONS is a JSON object: {"areas": [[width, height], ...], "points": [[x, y], ...],
   "leds": [[pin, n], ...], "pins": [pin, ...]}. */

var text = read(arguments[0]);
var asked = arguments.length > 1 ? JSON.parse(arguments[1]) : {};
var m = OdrigLayout.read(text);

var out = {
  mapping: m,
  positions: m.legs.map(function (leg) {
    var places = [];
    for (var n = 1; n <= leg.count; n += 1) {
      places.push(OdrigLayout.position(m, leg.pin, n));
    }
    return places;
  }),
  found: [],
  rows: m.legs.map(function (leg, i) { return OdrigLayout.rows(m, i); }),
  paths: m.legs.map(function (leg, i) { return OdrigLayout.path(m, i); }),
  runs: m.legs.map(function (leg, i) { return OdrigLayout.runs(m, i); }),
  colours: m.legs.map(function (leg, i) { return OdrigLayout.colour(i); }),
  manyColours: [],
  shown: [],
  fits: (asked.areas || []).map(function (area) { return OdrigLayout.fit(m, area[0], area[1]); }),
  board: OdrigBoard,
  side: OdrigLayout.side(m),
  tracks: OdrigLayout.tracks(m),
  places: (asked.pins || []).map(function (pin) { return OdrigLayout.place(OdrigBoard, pin); }),
  mapped: (asked.areas || []).map(function (area) {
    var f = OdrigLayout.fit(m, area[0], area[1], OdrigBoard);
    return {
      fit: f,
      wires: OdrigLayout.wires(m, f, OdrigBoard),
      chains: m.legs.map(function (leg, i) { return OdrigLayout.chain(m, f, i); }),
      firsts: m.legs.map(function (leg) {
        var first = OdrigLayout.position(m, leg.pin, 1);
        return OdrigLayout.centre(m, f, first[0], first[1]);
      })
    };
  }),
  asked: {
    points: (asked.points || []).map(function (point) { return OdrigLayout.find(m, point[0], point[1]); }),
    leds: (asked.leds || []).map(function (led) { return OdrigLayout.position(m, led[0], led[1]); })
  },
  centres: [],
  cells: []
};

for (var y = 1; y <= m.height; y += 1) {
  var row = [];
  for (var x = 1; x <= m.width; x += 1) {
    row.push(OdrigLayout.find(m, x, y));
  }
  out.found.push(row);
}
for (var i = 0; i < 30; i += 1) {
  out.manyColours.push(OdrigLayout.colour(i));
}
for (var v = 0; v <= 255; v += 1) {
  out.shown.push(OdrigLayout.shown(v));
}
out.fits.forEach(function (f) {
  var corners = [[1, 1], [m.width, 1], [1, m.height], [m.width, m.height]];
  out.centres.push(corners.map(function (corner) { return OdrigLayout.centre(m, f, corner[0], corner[1]); }));
  out.cells.push(corners.map(function (corner) {
    var at = OdrigLayout.centre(m, f, corner[0], corner[1]);
    return OdrigLayout.cellAt(m, f, at[0], at[1]);
  }).concat([OdrigLayout.cellAt(m, f, f.canvas.x - 1, f.canvas.y), OdrigLayout.cellAt(m, f, f.canvas.x, f.canvas.y + f.canvas.height)]));
});

print(JSON.stringify(out));
