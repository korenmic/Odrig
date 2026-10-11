/* Where everything on the page is: positions, paths, colours and sizes.
   One global object of pure functions. Nothing here needs a browser.
   Canvas coordinates are those of docs/format.md: x from 1 to W, y from 1 to H,
   with (1,1) at the bottom-left. Pixel coordinates have y growing downward. */

var OdrigLayout = (function () {
  "use strict";

  var COLOURS = ["#ff6b6b", "#ffa94d", "#ffd43b", "#a9e34b", "#51cf66", "#38d9a9",
                 "#3bc9db", "#4dabf7", "#748ffc", "#b197fc", "#f783ac", "#ced4da"];

  var MIN_CELL = 4;
  var MAX_CELL = 28;

  /* The parts around the canvas, in pixels: roomy where the cells are large, compact
     where they are small. */
  var ROOMY = {gutter: 16, bracket: 84, yLabel: 40, number: 34, top: 22, bottom: 10};
  var COMPACT = {gutter: 10, bracket: 56, yLabel: 30, number: 24, top: 18, bottom: 8};
  var ROOMY_FROM = 13;

  /* The mapping of a mapping file: the width, the height (the number of rows of all
     legs) and the legs, each with its number of LEDs. */
  function read(text) {
    var file = JSON.parse(text);
    var height = 0;
    var legs = file.legs.map(function (leg) {
      height += leg.rows.length;
      return {
        leg: leg.leg,
        pin: leg.pin,
        first_led: leg.first_led,
        rows: leg.rows.slice(),
        count: file.width * leg.rows.length
      };
    });
    return {width: file.width, height: height, legs: legs};
  }

  /* The index in the file of the leg on a pin, or -1. */
  function legOfPin(m, pin) {
    for (var i = 0; i < m.legs.length; i += 1) {
      if (m.legs[i].pin === pin) {
        return i;
      }
    }
    return -1;
  }

  /* Whether row r of a leg, counted in chain order from 0, starts on the right. */
  function startsRight(leg, r) {
    return (leg.first_led === "right") === (r % 2 === 0);
  }

  /* [x, y] of LED n, counted from 1, of the leg on a pin: the rule of docs/mapping.md,
     "Where each LED is". Null when the pin has no leg or the leg no such LED. */
  function position(m, pin, n) {
    var i = legOfPin(m, pin);
    if (i < 0) {
      return null;
    }
    var leg = m.legs[i];
    if (n !== Math.floor(n) || n < 1 || n > leg.count) {
      return null;
    }
    var r = Math.floor((n - 1) / m.width);
    var along = (n - 1) % m.width;
    return [startsRight(leg, r) ? m.width - along : 1 + along, leg.rows[r]];
  }

  /* The leg, by its index in the file, and the LED number at a canvas position, or null. */
  function find(m, x, y) {
    if (x !== Math.floor(x) || x < 1 || x > m.width) {
      return null;
    }
    for (var i = 0; i < m.legs.length; i += 1) {
      var r = m.legs[i].rows.indexOf(y);
      if (r >= 0) {
        var along = startsRight(m.legs[i], r) ? m.width - x : x - 1;
        return {leg: i, led: r * m.width + along + 1};
      }
    }
    return null;
  }

  /* For each row of leg i in chain order: its y, the side it starts on, and the LED
     numbers at its start and at its end. */
  function rows(m, i) {
    var leg = m.legs[i];
    return leg.rows.map(function (y, r) {
      return {
        y: y,
        start: startsRight(leg, r) ? "right" : "left",
        first: r * m.width + 1,
        last: (r + 1) * m.width
      };
    });
  }

  /* The corner points of the chain of leg i in canvas coordinates: for each row in
     chain order, where it starts and where it ends. */
  function path(m, i) {
    var points = [];
    rows(m, i).forEach(function (row) {
      var fromRight = row.start === "right";
      points.push([fromRight ? m.width : 1, row.y]);
      points.push([fromRight ? 1 : m.width, row.y]);
    });
    return points;
  }

  /* The rows of leg i as runs of neighbouring rows, from the top of the canvas down:
     the highest and the lowest y of each run. */
  function runs(m, i) {
    var ys = m.legs[i].rows.slice().sort(function (a, b) { return b - a; });
    var found = [];
    ys.forEach(function (y) {
      var last = found[found.length - 1];
      if (last && last.bottom === y + 1) {
        last.bottom = y;
      } else {
        found.push({top: y, bottom: y});
      }
    });
    return found;
  }

  /* The colour of the leg at index i of the file. */
  function colour(i) {
    return COLOURS[i % COLOURS.length];
  }

  /* The display value of a colour value: one fixed curve, so that dim values can be
     seen on a screen. */
  function shown(v) {
    return Math.round(255 * Math.pow(v / 255, 1 / 2.2));
  }

  function clamp(value, low, high) {
    return Math.max(low, Math.min(high, value));
  }

  /* The cell size and the place of every part of the LEDs view for a drawing area. */
  function fitLeds(m, width, height) {
    function cellFor(parts) {
      var freeWidth = width - 2 * parts.gutter - parts.bracket - parts.yLabel - 2 * parts.number;
      var freeHeight = height - parts.top - parts.bottom;
      return clamp(Math.floor(Math.min(freeWidth / m.width, freeHeight / m.height)), MIN_CELL, MAX_CELL);
    }
    var parts = ROOMY;
    var cell = cellFor(parts);
    if (cell < ROOMY_FROM) {
      parts = COMPACT;
      cell = cellFor(parts);
    }
    var canvasWidth = m.width * cell;
    var canvasHeight = m.height * cell;
    var contentWidth = 2 * parts.gutter + parts.bracket + parts.yLabel + 2 * parts.number + canvasWidth;
    var contentHeight = parts.top + canvasHeight + parts.bottom;
    var left = Math.max(0, Math.floor((width - contentWidth) / 2));
    var top = Math.max(0, Math.floor((height - contentHeight) / 2));
    var x = left + parts.gutter;
    var bracket = {x: x, y: top + parts.top, width: parts.bracket, height: canvasHeight};
    x += parts.bracket;
    var yLabel = {x: x, y: top + parts.top, width: parts.yLabel, height: canvasHeight};
    x += parts.yLabel;
    var numberLeft = {x: x, y: top + parts.top, width: parts.number, height: canvasHeight};
    x += parts.number;
    var canvas = {x: x, y: top + parts.top, width: canvasWidth, height: canvasHeight};
    x += canvasWidth;
    var numberRight = {x: x, y: top + parts.top, width: parts.number, height: canvasHeight};
    return {
      view: "leds",
      cell: cell,
      roomy: parts === ROOMY,
      width: Math.max(width, contentWidth),
      height: Math.max(height, contentHeight),
      content: {x: left, y: top, width: contentWidth, height: contentHeight},
      gutters: [
        {x: left, y: top, width: parts.gutter, height: contentHeight},
        {x: left + contentWidth - parts.gutter, y: top, width: parts.gutter, height: contentHeight}
      ],
      header: {x: canvas.x, y: top, width: canvasWidth, height: parts.top},
      bracket: bracket,
      yLabel: yLabel,
      numberLeft: numberLeft,
      numberRight: numberRight,
      canvas: canvas
    };
  }

  /* The cell size in pixels and the place of every part, for a drawing area of a
     width and a height. */
  function fit(m, width, height) {
    return fitLeds(m, width, height);
  }

  /* The centre of a canvas position in the pixels of a fitted drawing. */
  function centre(m, f, x, y) {
    return [f.canvas.x + (x - 0.5) * f.cell, f.canvas.y + (m.height - y + 0.5) * f.cell];
  }

  /* The canvas position under a pixel of a fitted drawing, or null outside the canvas. */
  function cellAt(m, f, px, py) {
    var x = Math.floor((px - f.canvas.x) / f.cell) + 1;
    var y = m.height - Math.floor((py - f.canvas.y) / f.cell);
    if (x < 1 || x > m.width || y < 1 || y > m.height) {
      return null;
    }
    return [x, y];
  }

  return {
    colours: COLOURS,
    read: read,
    legOfPin: legOfPin,
    position: position,
    find: find,
    rows: rows,
    path: path,
    runs: runs,
    colour: colour,
    shown: shown,
    fit: fit,
    centre: centre,
    cellAt: cellAt
  };
}());
