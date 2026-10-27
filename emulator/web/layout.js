/* Where everything on the page is: positions, paths, colours and sizes.
   One global object of pure functions. Nothing here needs a browser.
   Canvas coordinates are those of docs/format.md: x from 1 to W, y from 1 to H,
   with (1,1) at the bottom-left. Pixel coordinates have y growing downward. */

var OdrigLayout = (function () {
  "use strict";

  var COLOURS = ["#ff6b6b", "#ffa94d", "#ffd43b", "#a9e34b", "#51cf66", "#38d9a9",
                 "#3bc9db", "#4dabf7", "#748ffc", "#b197fc", "#f783ac", "#ced4da",
                 "#e599f7", "#c98f5a", "#a5d8ff", "#7fa650", "#96f2d7", "#868e96",
                 "#1098ad", "#ffa8a8"];

  var MIN_CELL = 4;
  var MAX_CELL = 28;

  /* The parts around the canvas, in pixels: roomy where the cells are large, compact
     where they are small. */
  var ROOMY = {gutter: 16, bracket: 84, yLabel: 40, number: 34, top: 22, bottom: 10};
  var COMPACT = {gutter: 10, bracket: 56, yLabel: 30, number: 24, top: 18, bottom: 8};
  var ROOMY_FROM = 13;

  /* The parts around the canvas of a column-leg file: the gutters, the marks of the rows
     at the left, the header with the marks of the columns, the band with the bracket, the
     number and the pin of every leg, the two bands with the LED numbers at the ends of the
     columns, and the margins above and below. */
  var UPRIGHT_ROOMY = {gutter: 16, yLabel: 40, header: 20, legBand: 42, number: 34, margin: 10};
  var UPRIGHT_COMPACT = {gutter: 10, yLabel: 30, header: 16, legBand: 32, number: 24, margin: 6};
  /* The LED numbers at the ends of the columns are drawn where the cells are this large. */
  var NUMBERED_FROM = 9;

  /* The mapping view with the board beside the canvas: the parts around the canvas, the
     channel of the lines between canvas and board, and the room for the leg labels and
     for the lines that go round the board to its far row of pins. */
  var BESIDE = {gutter: 12, bracket: 54, yLabel: 30, number: 28, top: 18, bottom: 8, margin: 8,
                trackGap: 9, channelPad: 5, nearLabel: 42, farLabel: 40, loopFirst: 10, loopGap: 8, loopEnd: 6,
                offPad: 18, turn: 6, tip: 2};
  /* Where the cells are large the labels of the mapping view take the roomy widths. */
  var BESIDE_ROOMY = {bracket: 84, yLabel: 40, number: 38, top: 22, bottom: 10};
  var BESIDE_ROOMY_FROM = 16;

  /* In a narrow area the board stands below the canvas: the lines run down a channel
     beside the canvas, and those for the row of pins on the other side of the board go
     through a band between canvas and board and down a second channel. */
  var BELOW = {gap: 10, legible: 9};

  /* The mapping view of a column-leg file. Two channels carry the lines: the level
     channel along the feed edge of the canvas, with a level track for each leg, and the
     upright channel at the left of the board, with an upright track for each leg that
     needs one. A track takes `track` pixels, and a channel has `channelPad` more at each
     side. At the left of the board stand the names of the legs of its left row of pads.
     At its right is the far zone: the loops of the lines for its right row, `track`
     apart from `loopFirst` on, and the names of those legs. A pin the board lacks gets a
     pad of its own, `offPad` from the next. A turn of a chain is `turn` outside the
     canvas, and a line ends `tip` outside it. */
  var WIRED = {track: 7, channelPad: 5, nearLabel: 42, farLabel: 40, loopFirst: 10, loopEnd: 6, offPad: 18, gap: 10,
               turn: 6, tip: 2, legible: 9};
  /* The parts around the canvas in that view: those of the LEDs view, with number bands
     that hold the numbers clear of the turns. */
  var WIRED_ROOMY = {gutter: 16, yLabel: 40, header: 20, legBand: 42, number: 40, margin: 10};
  var WIRED_COMPACT = {gutter: 10, yLabel: 30, header: 16, legBand: 32, number: 30, margin: 6};

  /* The board in units of the distance between two pads. */
  var BOARD = {width: 11.5, height: 26.25, head: 2.75, inset: 0.5625, pad: 0.27};
  var PITCH = {least: 10, usual: 16, most: 20};

  /* The mapping of a mapping file: its kind, "rows" or "columns", the width and the
     height of the canvas, and the legs, each with its strips in chain order (the y of each
     row, or the x of each column) and its number of LEDs. A file with `height` is a
     column-leg file: its height is that member and its width the number of columns of all
     legs. A row-leg file has `width`, and its height is the number of rows of all legs. */
  function read(text) {
    var file = JSON.parse(text);
    var columns = file.height !== undefined;
    var length = columns ? file.height : file.width;
    var total = 0;
    var legs = file.legs.map(function (leg) {
      var strips = (columns ? leg.columns : leg.rows).slice();
      total += strips.length;
      var entry = {
        leg: leg.leg,
        pin: leg.pin,
        first_led: leg.first_led,
        strips: strips,
        count: length * strips.length
      };
      if (leg.starts !== undefined) {
        entry.starts = leg.starts.slice();
      }
      return entry;
    });
    return {
      kind: columns ? "columns" : "rows",
      width: columns ? total : length,
      height: columns ? length : total,
      legs: legs
    };
  }

  /* The number of LEDs in every strip: in every row, or in every column. */
  function stripLength(m) {
    return m.kind === "columns" ? m.height : m.width;
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

  /* Whether strip s of a leg, counted in chain order from 0, starts at the end where the
     canvas coordinate along it is 1: the left end of a row, the bottom end of a column.
     With `starts` each strip starts at the end it names. Without it the first strip starts
     at the `first_led` end, and every strip after it at the end opposite to the one
     before. */
  function startsLow(leg, s) {
    if (leg.starts !== undefined) {
      return leg.starts[s] === "left" || leg.starts[s] === "bottom";
    }
    return (leg.first_led === "left" || leg.first_led === "bottom") === (s % 2 === 0);
  }

  /* [x, y] of LED n, counted from 1, of the leg on a pin: the rule of docs/mapping.md,
     "Where each LED is", for the kind of the file. Null when the pin has no leg or the
     leg no such LED. */
  function position(m, pin, n) {
    var i = legOfPin(m, pin);
    if (i < 0) {
      return null;
    }
    var leg = m.legs[i];
    if (n !== Math.floor(n) || n < 1 || n > leg.count) {
      return null;
    }
    var length = stripLength(m);
    var s = Math.floor((n - 1) / length);
    var passed = (n - 1) % length;
    var along = startsLow(leg, s) ? 1 + passed : length - passed;
    return m.kind === "columns" ? [leg.strips[s], along] : [along, leg.strips[s]];
  }

  /* The leg, by its index in the file, and the LED number at a canvas position, or null. */
  function find(m, x, y) {
    var columns = m.kind === "columns";
    var across = columns ? x : y;
    var along = columns ? y : x;
    var length = stripLength(m);
    if (along !== Math.floor(along) || along < 1 || along > length) {
      return null;
    }
    for (var i = 0; i < m.legs.length; i += 1) {
      var s = m.legs[i].strips.indexOf(across);
      if (s >= 0) {
        var passed = startsLow(m.legs[i], s) ? along - 1 : length - along;
        return {leg: i, led: s * length + passed + 1};
      }
    }
    return null;
  }

  /* For each strip of leg i in chain order: its place across the strips, as `y` for a row
     and as `x` for a column, the end it starts at ("left" or "right" for a row, "bottom"
     or "top" for a column), and the LED numbers at its start and at its end. */
  function strips(m, i) {
    var leg = m.legs[i];
    var columns = m.kind === "columns";
    var length = stripLength(m);
    return leg.strips.map(function (across, s) {
      var low = startsLow(leg, s);
      var strip = {
        start: columns ? (low ? "bottom" : "top") : (low ? "left" : "right"),
        first: s * length + 1,
        last: (s + 1) * length
      };
      strip[columns ? "x" : "y"] = across;
      return strip;
    });
  }

  /* The corner points of the chain of leg i in canvas coordinates: for each strip in
     chain order, where it starts and where it ends. */
  function path(m, i) {
    var columns = m.kind === "columns";
    var length = stripLength(m);
    var points = [];
    strips(m, i).forEach(function (strip) {
      var low = strip.start === "left" || strip.start === "bottom";
      [low ? 1 : length, low ? length : 1].forEach(function (along) {
        points.push(columns ? [strip.x, along] : [along, strip.y]);
      });
    });
    return points;
  }

  /* The strips of leg i as runs of neighbouring strips. The rows of a row leg from the
     top of the canvas down: the highest and the lowest y of each run, as `top` and
     `bottom`. The columns of a column leg from the left: the lowest and the highest x of
     each run, as `left` and `right`. */
  function runs(m, i) {
    var columns = m.kind === "columns";
    var first = columns ? "left" : "top";
    var last = columns ? "right" : "bottom";
    var step = columns ? 1 : -1;
    var sorted = m.legs[i].strips.slice().sort(function (a, b) { return step * (a - b); });
    var found = [];
    sorted.forEach(function (across) {
      var run = found[found.length - 1];
      if (run && run[last] + step === across) {
        run[last] = across;
      } else {
        run = {};
        run[first] = across;
        run[last] = across;
        found.push(run);
      }
    });
    return found;
  }

  /* The rows, or the columns, that are marked beside a canvas that has `count` of them:
     the first, every tenth and the last. A tenth nearer than three to the last is left
     out, so that no mark stands on another. */
  function marks(count) {
    var found = [1];
    for (var tenth = 10; tenth < count - 2; tenth += 10) {
      found.push(tenth);
    }
    if (count > 1) {
      found.push(count);
    }
    return found;
  }

  /* The colour of the leg at index i of the file. A leg beyond the last colour takes the
     colours again from the start. */
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

  /* The feed edge: the edge of the canvas at which most legs have their first LED. For a
     row-leg file "right" or "left", "right" when the two are equal; the board is drawn on
     this side. For a column-leg file "bottom" or "top", "bottom" when the two are equal. */
  function side(m) {
    var edges = m.kind === "columns" ? ["bottom", "top"] : ["right", "left"];
    var balance = 0;
    m.legs.forEach(function (leg) {
      balance += leg.first_led === edges[0] ? 1 : -1;
    });
    return balance >= 0 ? edges[0] : edges[1];
  }

  /* The row of pins of a board and the place in it of the pad for a GPIO, or null when
     the board has no such pad. */
  function place(board, pin) {
    var label = String(pin);
    var names = ["left", "right"];
    for (var r = 0; r < names.length; r += 1) {
      var index = board[names[r]].indexOf(label);
      if (index >= 0) {
        return {row: names[r], index: index};
      }
    }
    return null;
  }

  /* For each leg its place among the legs along the feed edge, from 0. The legs of a
     row-leg file are ordered by the y of their first row, highest first, and the place of
     a leg is its track in the channel between the canvas and the board, track 0 nearest
     the canvas. The legs of a column-leg file are ordered by the x of their first column,
     from the left. */
  function tracks(m) {
    var way = m.kind === "columns" ? -1 : 1;
    var order = m.legs.map(function (leg, i) { return i; });
    order.sort(function (a, b) {
      return way * (m.legs[b].strips[0] - m.legs[a].strips[0]) || a - b;
    });
    var track = [];
    order.forEach(function (i, k) {
      track[i] = k;
    });
    return track;
  }

  /* How each leg reaches the board that stands on one side of the canvas: "near" for a
     pad in the row of pins that faces the canvas, "far" for one in the other row, whose
     line goes round the board over its top or under its bottom, and "off" for a pin the
     board does not have, which gets a pad of its own under the board. */
  function reaches(m, board, nearRow) {
    var half = board[nearRow].length / 2;
    var track = tracks(m);
    var found = m.legs.map(function (leg, i) {
      var at = place(board, leg.pin);
      if (!at) {
        return {leg: i, kind: "off", at: null, track: track[i]};
      }
      if (at.row === nearRow) {
        return {leg: i, kind: "near", at: at, track: track[i]};
      }
      return {leg: i, kind: "far", at: at, track: track[i], over: at.index < half};
    });
    /* The loops round the board nest: the leg whose track is nearest the board takes the
       innermost loop. */
    [true, false].forEach(function (over) {
      found.filter(function (reach) { return reach.kind === "far" && reach.over === over; })
        .sort(function (a, b) { return b.track - a.track; })
        .forEach(function (reach, loop) { reach.loop = loop; });
    });
    found.filter(function (reach) { return reach.kind === "off"; })
      .sort(function (a, b) { return a.track - b.track; })
      .forEach(function (reach, index) { reach.index = index; });
    return found;
  }

  function count(reached, test) {
    return reached.filter(test).length;
  }

  /* The cell size and the place of every part of the mapping view for a drawing area,
     with the board beside the canvas: the LEDs view with the channel of lines and the
     board next to it. */
  function fitBeside(m, width, height, board) {
    var roomy = fitBesideWith(m, width, height, board, BESIDE_ROOMY);
    return roomy.cell >= BESIDE_ROOMY_FROM ? roomy : fitBesideWith(m, width, height, board, {});
  }

  function fitBesideWith(m, width, height, board, wider) {
    var parts = {};
    Object.keys(BESIDE).forEach(function (name) {
      parts[name] = wider[name] === undefined ? BESIDE[name] : wider[name];
    });
    var boardSide = side(m);
    var reached = reaches(m, board, boardSide === "right" ? "left" : "right");
    var over = count(reached, function (reach) { return reach.kind === "far" && reach.over; });
    var under = count(reached, function (reach) { return reach.kind === "far" && !reach.over; });
    var off = count(reached, function (reach) { return reach.kind === "off"; });
    var loops = Math.max(over, under);
    var farZone = loops ? parts.loopFirst + parts.loopGap * (loops - 1) + parts.loopEnd + parts.farLabel : parts.margin;
    var aboveBoard = over ? parts.loopFirst + parts.loopGap * (over - 1) : 0;
    var belowBoard = (under ? parts.loopFirst + parts.loopGap * (under - 1) : 0) + off * parts.offPad;
    var channelWidth = parts.trackGap * m.legs.length + 2 * parts.channelPad;

    var roomForBoard = height - 2 * parts.margin - aboveBoard - belowBoard;
    var pitch = clamp(Math.floor(roomForBoard / BOARD.height), PITCH.least, PITCH.usual);
    var fixed = 2 * parts.gutter + parts.bracket + parts.yLabel + 2 * parts.number + channelWidth + parts.nearLabel + farZone;
    var freeWidth = width - fixed - BOARD.width * pitch;
    var freeHeight = height - parts.top - parts.bottom;
    var cell = clamp(Math.floor(Math.min(freeWidth / m.width, freeHeight / m.height)), MIN_CELL, MAX_CELL);
    var canvasWidth = m.width * cell;
    var canvasHeight = m.height * cell;
    /* Room that the canvas leaves goes to the board. */
    while (pitch < PITCH.most && fixed + BOARD.width * (pitch + 1) + canvasWidth <= width && BOARD.height * (pitch + 1) <= roomForBoard) {
      pitch += 1;
    }
    var boardWidth = Math.round(BOARD.width * pitch);
    var boardHeight = Math.round(BOARD.height * pitch);

    var contentWidth = fixed + boardWidth + canvasWidth;
    var canvasBlock = parts.top + canvasHeight + parts.bottom;
    var boardBlock = parts.margin + aboveBoard + boardHeight + belowBoard + parts.margin;
    var contentHeight = Math.max(canvasBlock, boardBlock);
    var left = Math.max(0, Math.floor((width - contentWidth) / 2));
    var top = Math.max(0, Math.floor((height - contentHeight) / 2));
    var canvasY = top + Math.floor((contentHeight - canvasBlock) / 2) + parts.top;
    var boardY = top + Math.floor((contentHeight - boardBlock) / 2) + parts.margin + aboveBoard;

    /* The parts from the side away from the board to the side of the board. */
    var widths = [
      ["gutterAway", parts.gutter], ["bracket", parts.bracket], ["yLabel", parts.yLabel], ["numberAway", parts.number],
      ["canvas", canvasWidth], ["numberBoard", parts.number], ["channel", channelWidth], ["nearLabel", parts.nearLabel],
      ["board", boardWidth], ["farZone", farZone], ["gutterBoard", parts.gutter]
    ];
    var at = {};
    var x = left;
    (boardSide === "right" ? widths : widths.slice().reverse()).forEach(function (part) {
      at[part[0]] = x;
      x += part[1];
    });
    function column(name, partWidth) {
      return {x: at[name], y: canvasY, width: partWidth, height: canvasHeight};
    }
    var right = boardSide === "right";
    return {
      view: "mapping",
      arrangement: "beside",
      cell: cell,
      roomy: wider === BESIDE_ROOMY,
      boardSide: boardSide,
      width: Math.max(width, contentWidth),
      height: Math.max(height, contentHeight),
      content: {x: left, y: top, width: contentWidth, height: contentHeight},
      gutters: [
        {x: left, y: top, width: parts.gutter, height: contentHeight},
        {x: left + contentWidth - parts.gutter, y: top, width: parts.gutter, height: contentHeight}
      ],
      header: {x: at.canvas, y: canvasY - parts.top, width: canvasWidth, height: parts.top},
      bracket: column("bracket", parts.bracket),
      yLabel: column("yLabel", parts.yLabel),
      numberLeft: column(right ? "numberAway" : "numberBoard", parts.number),
      numberRight: column(right ? "numberBoard" : "numberAway", parts.number),
      canvas: column("canvas", canvasWidth),
      channel: {x: at.channel, y: top, width: channelWidth, height: contentHeight},
      nearLabel: {x: at.nearLabel, y: boardY, width: parts.nearLabel, height: boardHeight},
      board: {x: at.board, y: boardY, width: boardWidth, height: boardHeight, pitch: pitch},
      farZone: {x: at.farZone, y: boardY - aboveBoard, width: farZone, height: aboveBoard + boardHeight + belowBoard},
      reaches: reached
    };
  }

  /* The same for an area too narrow for the board beside the canvas: the canvas takes
     the width and the board stands below it. The drawing may be higher than the area. */
  function fitBelow(m, width, height, board) {
    var parts = BESIDE;
    var boardSide = side(m);
    var right = boardSide === "right";
    var reached = reaches(m, board, boardSide);
    var far = count(reached, function (reach) { return reach.kind === "far"; });
    var off = count(reached, function (reach) { return reach.kind === "off"; });
    var channelWidth = parts.trackGap * m.legs.length + 2 * parts.channelPad;
    var secondWidth = far ? parts.trackGap * far + 2 * parts.channelPad : 0;
    var bandHeight = far ? parts.trackGap * far + 2 * parts.channelPad : parts.margin;

    var fixed = 2 * parts.gutter + parts.bracket + parts.yLabel + 2 * parts.number + channelWidth;
    var cell = clamp(Math.floor((width - fixed) / m.width), MIN_CELL, MAX_CELL);
    var canvasWidth = m.width * cell;
    var canvasHeight = m.height * cell;
    var contentWidth = fixed + canvasWidth;
    var boardRoom = contentWidth - 2 * parts.gutter - channelWidth - secondWidth - 2 * parts.nearLabel;
    var pitch = clamp(Math.floor(boardRoom / BOARD.width), PITCH.least, PITCH.usual);
    var boardWidth = Math.round(BOARD.width * pitch);
    var boardHeight = Math.round(BOARD.height * pitch);
    var contentHeight = parts.top + canvasHeight + parts.bottom + bandHeight + BELOW.gap + boardHeight + off * parts.offPad + parts.margin;
    var left = Math.max(0, Math.floor((width - contentWidth) / 2));
    var top = Math.max(0, Math.floor((height - contentHeight) / 2));
    var canvasY = top + parts.top;

    var widths = [
      ["gutterAway", parts.gutter], ["bracket", parts.bracket], ["yLabel", parts.yLabel], ["numberAway", parts.number],
      ["canvas", canvasWidth], ["numberBoard", parts.number], ["channel", channelWidth], ["gutterBoard", parts.gutter]
    ];
    var at = {};
    var x = left;
    (right ? widths : widths.slice().reverse()).forEach(function (part) {
      at[part[0]] = x;
      x += part[1];
    });
    function column(name, partWidth) {
      return {x: at[name], y: canvasY, width: partWidth, height: canvasHeight};
    }
    var bandY = canvasY + canvasHeight + parts.bottom;
    var boardY = bandY + bandHeight + BELOW.gap;
    var boardX = right ? at.channel - parts.nearLabel - boardWidth : at.channel + channelWidth + parts.nearLabel;
    var secondX = right ? boardX - parts.nearLabel - secondWidth : boardX + boardWidth + parts.nearLabel;
    return {
      view: "mapping",
      arrangement: "below",
      cell: cell,
      roomy: false,
      boardSide: boardSide,
      width: Math.max(width, contentWidth),
      height: Math.max(height, contentHeight),
      content: {x: left, y: top, width: contentWidth, height: contentHeight},
      gutters: [
        {x: left, y: top, width: parts.gutter, height: contentHeight},
        {x: left + contentWidth - parts.gutter, y: top, width: parts.gutter, height: contentHeight}
      ],
      header: {x: at.canvas, y: top, width: canvasWidth, height: parts.top},
      bracket: column("bracket", parts.bracket),
      yLabel: column("yLabel", parts.yLabel),
      numberLeft: column(right ? "numberAway" : "numberBoard", parts.number),
      numberRight: column(right ? "numberBoard" : "numberAway", parts.number),
      canvas: column("canvas", canvasWidth),
      channel: {x: at.channel, y: top, width: channelWidth, height: contentHeight},
      band: {x: Math.min(secondX, at.channel), y: bandY, width: Math.abs(at.channel - secondX) + (right ? 0 : channelWidth), height: bandHeight},
      second: {x: secondX, y: bandY, width: secondWidth, height: boardY + boardHeight - bandY},
      nearLabel: {x: right ? boardX + boardWidth : boardX - parts.nearLabel, y: boardY, width: parts.nearLabel, height: boardHeight},
      farLabel: {x: right ? boardX - parts.nearLabel : boardX + boardWidth, y: boardY, width: parts.nearLabel, height: boardHeight},
      board: {x: boardX, y: boardY, width: boardWidth, height: boardHeight, pitch: pitch},
      reaches: reached
    };
  }

  /* The mapping view: the board beside the canvas, or below it where the area is so
     narrow that the cells beside a board would be too small to read. */
  function fitMapping(m, width, height, board) {
    var beside = fitBeside(m, width, height, board);
    if (beside.cell >= BELOW.legible) {
      return beside;
    }
    var below = fitBelow(m, width, height, board);
    return below.cell > beside.cell ? below : beside;
  }

  /* The place of every part of the drawing of a column-leg file, for a cell size and for
     the point where the marks of the rows begin at the left and the drawing at the top.
     From the top down: the header with the marks of the columns, the leg band, the upper
     number band, the canvas and the lower number band. Where the feed edge is the top the
     order is the other way round, so that the leg band lies on the side of the canvas away
     from the feed edge. Without `numbered` the two number bands are left out. */
  function uprightParts(m, parts, cell, numbered, x, y) {
    var feed = side(m);
    var canvasWidth = m.width * cell;
    var canvasHeight = m.height * cell;
    var number = numbered ? parts.number : 0;
    var heights = [["header", parts.header], ["legBand", parts.legBand], ["numberAway", number], ["canvas", canvasHeight], ["numberFeed", number]];
    var at = {};
    var down = y;
    (feed === "bottom" ? heights : heights.slice().reverse()).forEach(function (part) {
      at[part[0]] = down;
      down += part[1];
    });
    var canvasX = x + parts.yLabel;
    function across(name, partHeight) {
      return {x: canvasX, y: at[name], width: canvasWidth, height: partHeight};
    }
    return {
      feed: feed,
      header: across("header", parts.header),
      legBand: across("legBand", parts.legBand),
      legWords: {x: x, y: at.legBand, width: parts.yLabel, height: parts.legBand},
      yLabel: {x: x, y: at.canvas, width: parts.yLabel, height: canvasHeight},
      numberTop: numbered ? across(feed === "bottom" ? "numberAway" : "numberFeed", number) : null,
      numberBottom: numbered ? across(feed === "bottom" ? "numberFeed" : "numberAway", number) : null,
      canvas: across("canvas", canvasHeight)
    };
  }

  /* The cell size and the place of every part of the drawing of a column-leg file for a
     drawing area. The cell is the largest at which the drawing with its two number bands
     fits the area. Where that is too small for the numbers, the bands are left out and
     the cell is the largest that fits without them and is still too small for them. */
  function fitUpright(m, width, height) {
    function fixedHeight(parts, numbered) {
      return 2 * parts.margin + parts.header + parts.legBand + (numbered ? 2 * parts.number : 0);
    }
    function cellFor(parts, numbered) {
      var freeWidth = width - 2 * parts.gutter - parts.yLabel;
      var freeHeight = height - fixedHeight(parts, numbered);
      return clamp(Math.floor(Math.min(freeWidth / m.width, freeHeight / m.height)), MIN_CELL, MAX_CELL);
    }
    var parts = UPRIGHT_ROOMY;
    var numbered = true;
    var cell = cellFor(parts, numbered);
    if (cell < ROOMY_FROM) {
      parts = UPRIGHT_COMPACT;
      cell = cellFor(parts, numbered);
    }
    if (cell < NUMBERED_FROM) {
      numbered = false;
      cell = Math.min(cellFor(parts, numbered), NUMBERED_FROM - 1);
    }
    var contentWidth = 2 * parts.gutter + parts.yLabel + m.width * cell;
    var contentHeight = fixedHeight(parts, numbered) + m.height * cell;
    var left = Math.max(0, Math.floor((width - contentWidth) / 2));
    var top = Math.max(0, Math.floor((height - contentHeight) / 2));
    var placed = uprightParts(m, parts, cell, numbered, left + parts.gutter, top + parts.margin);
    return {
      view: "leds",
      feed: placed.feed,
      cell: cell,
      roomy: parts === UPRIGHT_ROOMY,
      width: Math.max(width, contentWidth),
      height: Math.max(height, contentHeight),
      content: {x: left, y: top, width: contentWidth, height: contentHeight},
      gutters: [
        {x: left, y: top, width: parts.gutter, height: contentHeight},
        {x: left + contentWidth - parts.gutter, y: top, width: parts.gutter, height: contentHeight}
      ],
      header: placed.header,
      legBand: placed.legBand,
      legWords: placed.legWords,
      yLabel: placed.yLabel,
      numberTop: placed.numberTop,
      numberBottom: placed.numberBottom,
      canvas: placed.canvas
    };
  }

  /* Where the line of leg i of a column-leg file comes to its first LED, for a feed edge
     and a cell size: the column of that LED, whether the LED is at the feed edge, and how
     far from the left edge of the canvas the last upright piece of the line runs. To a
     first LED at the feed edge it runs in the middle of the column. To one at the far
     edge it runs in the gap at the left of the column. */
  function entryOf(m, feed, cell, i) {
    var first = position(m, m.legs[i].pin, 1);
    var atFeed = m.height === 1 || (first[1] === 1) === (feed === "bottom");
    return {column: first[0], atFeed: atFeed, across: (atFeed ? first[0] - 0.5 : first[0] - 1) * cell};
  }

  /* The mapping view of a column-leg file for one cell size: the place of every part,
     and for every leg how its line runs. `wide` puts the board beside the canvas, with
     the level channel reaching on under the upright channel, the board and the far zone.
     Otherwise the level channel lies between the canvas and the board, and the canvas
     begins to the right of the upright channel. With the feed edge at the top both are
     turned over from top to bottom, all but the board itself.

     A reach says of a leg: `kind`, "near" for a pad in the left row of the board, "far"
     for one in the right row and "off" for a pin the board lacks; `at`, the pad; `level`,
     its level track, counted from the canvas; `upright`, its upright track, counted from
     the board; and for a far pad `way`, "short" or "long", `loop`, its place among the
     loops in the far zone, counted from the board, and on the long way `beyond`, its
     place among the lines that pass beyond the end of the board, counted from the board.
     An off pad has `index`, its place among the pads beyond the board, counted from the
     board.

     Beside the canvas the pads of the board are `wanted` apart or more, as far as the
     height lets them be: a drawing that has no room for that is wider than the area. */
  function placeWired(m, board, wide, parts, cell, wanted, width, height) {
    var wired = WIRED;
    var feed = side(m);
    var down = feed === "bottom" ? 1 : -1;
    /* The way from the board to the level channel: down or up the drawing. */
    var toChannel = wide ? down : -down;
    var legs = m.legs.length;
    var canvasWidth = m.width * cell;
    var canvasHeight = m.height * cell;
    var canvasBlock = parts.header + parts.legBand + 2 * parts.number + canvasHeight;
    var levelDepth = wired.track * legs + 2 * wired.channelPad;

    /* The lines reach the level channel from the right where the board stands beside the
       canvas, and from the left otherwise. The leg whose first LED is farthest from that
       side takes the level track farthest from the canvas. */
    var order = tracks(m);
    var reached = m.legs.map(function (leg, i) {
      var at = place(board, leg.pin);
      return {leg: i, kind: at ? (at.row === "left" ? "near" : "far") : "off", at: at, level: wide ? legs - 1 - order[i] : order[i]};
    });
    function ofKind(kind) {
      return reached.filter(function (reach) { return reach.kind === kind; });
    }
    var far = ofKind("far");
    var off = ofKind("off");
    var farZone = far.length ? wired.loopFirst + wired.track * (far.length - 1) + wired.loopEnd + wired.farLabel : parts.margin;

    /* A board that does not stand beside the canvas is as wide as the canvas lets it be. */
    var pitch = wide ? PITCH.least : clamp(Math.floor((canvasWidth - wired.nearLabel - farZone) / BOARD.width), PITCH.least, PITCH.usual);
    /* How far to the right of the left edge of the canvas the outermost loop is then. */
    var lastLoop = wired.nearLabel + Math.round(BOARD.width * pitch) + wired.loopFirst + wired.track * (far.length - 1);

    /* A line from the right row of pads goes round the board. The short way is round the
       end that faces the level channel, and reaches the level track from the far side of
       the board. The long way is round the other end and then along the left side of the
       board. A leg takes the short way when its level track is in the half of the level
       channel farthest from the canvas. Where the board does not stand beside the canvas,
       a leg whose first LED is not to the right of every loop takes the long way too: on
       the short way its line would turn back along its level track. */
    far.forEach(function (reach) {
      var farHalf = 2 * reach.level + 1 >= legs;
      var turnsOneWay = wide || entryOf(m, feed, cell, reach.leg).across >= lastLoop + wired.track;
      reach.way = farHalf && turnsOneWay ? "short" : "long";
    });

    /* The nearer to the level channel of two pads first. A pad beyond the board is nearer
       than every pad of the board, and of two such pads the one whose level track is
       farther from the canvas is the nearer. */
    function nearerFirst(a, b) {
      if ((a.kind === "off") !== (b.kind === "off")) {
        return a.kind === "off" ? -1 : 1;
      }
      if (a.kind === "off") {
        return b.level - a.level;
      }
      return toChannel * (b.at.index - a.at.index) || a.leg - b.leg;
    }
    /* Of the pads whose lines leave the board at its left, the nearest to the level
       channel takes the upright track nearest the board. */
    var beside = reached.filter(function (reach) { return reach.kind !== "far"; }).sort(nearerFirst);
    beside.forEach(function (reach, track) {
      reach.upright = track;
    });
    off.sort(nearerFirst).reverse().forEach(function (reach, index) {
      reach.index = index;
    });
    /* The loops of each way nest. On the short way the pad farthest from the level
       channel takes the outer loop. On the long way the pad nearest the level channel
       takes the outer loop, which passes farthest beyond the end of the board and takes
       the upright track farthest from the board, beyond every other upright track. */
    var shorts = far.filter(function (reach) { return reach.way === "short"; }).sort(nearerFirst);
    shorts.forEach(function (reach, loop) {
      reach.loop = loop;
    });
    var longs = far.filter(function (reach) { return reach.way === "long"; }).sort(nearerFirst).reverse();
    longs.forEach(function (reach, loop) {
      reach.loop = shorts.length + loop;
      reach.beyond = loop;
      reach.upright = beside.length + loop;
    });

    var uprightWidth = wired.track * (beside.length + longs.length) + 2 * wired.channelPad;
    /* Beyond the end of the board that faces the level channel stand the pads the board
       lacks, and beyond its other end pass the lines of the long way. */
    var offZone = wired.offPad * off.length;
    var longZone = longs.length ? wired.loopFirst + wired.track * (longs.length - 1) + wired.loopEnd : 0;

    /* Beside the canvas the board takes the room that the canvas and the area leave. */
    var fixed = 2 * parts.gutter + parts.yLabel + uprightWidth + wired.nearLabel + farZone;
    if (wide) {
      var room = Math.max(canvasBlock, height - 2 * parts.margin - levelDepth) - offZone - longZone;
      pitch = Math.min(wanted, clamp(Math.floor(room / BOARD.height), PITCH.least, PITCH.most));
      while (pitch < PITCH.most && fixed + canvasWidth + Math.round(BOARD.width * (pitch + 1)) <= width && Math.round(BOARD.height * (pitch + 1)) <= room) {
        pitch += 1;
      }
    }
    var boardWidth = Math.round(BOARD.width * pitch);
    var boardHeight = Math.round(BOARD.height * pitch);
    var boardBlock = offZone + boardHeight + longZone;
    var block = Math.max(canvasBlock, boardBlock);
    /* Where the board does not stand beside the canvas, the canvas begins to the right of
       the upright channel, so that every first LED is to the right of every upright
       track. The marks of the rows stand in that margin. */
    var lead = wide ? parts.yLabel : Math.max(parts.yLabel, uprightWidth);
    var contentWidth = wide ? fixed + canvasWidth + boardWidth : 2 * parts.gutter + lead + Math.max(canvasWidth, wired.nearLabel + boardWidth + farZone);
    var contentHeight = 2 * parts.margin + levelDepth + (wide ? block : canvasBlock + wired.gap + boardBlock);
    var left = Math.max(0, Math.floor((width - contentWidth) / 2));
    var top = Math.max(0, Math.floor((height - contentHeight) / 2));
    var inner = top + parts.margin;
    var end = top + contentHeight - parts.margin;
    var canvasX = left + parts.gutter + lead;

    var canvasBlockY;
    var levelY;
    var boardBlockY;
    var upright;
    if (wide) {
      /* The canvas with its bands lies against the level channel, and the board stands
         in the middle of the height beside it. */
      var blockY = down > 0 ? inner : inner + levelDepth;
      levelY = down > 0 ? blockY + block : inner;
      canvasBlockY = down > 0 ? levelY - canvasBlock : blockY;
      boardBlockY = blockY + Math.floor((block - boardBlock) / 2);
      upright = {x: canvasX + canvasWidth, y: blockY, width: uprightWidth, height: block};
    } else {
      canvasBlockY = down > 0 ? inner : end - canvasBlock;
      levelY = down > 0 ? canvasBlockY + canvasBlock : canvasBlockY - levelDepth;
      boardBlockY = down > 0 ? levelY + levelDepth + wired.gap : inner;
      upright = {x: canvasX - uprightWidth, y: down > 0 ? levelY + levelDepth : inner, width: uprightWidth, height: wired.gap + boardBlock};
    }
    var nearX = wide ? upright.x + uprightWidth : canvasX;
    var boardX = nearX + wired.nearLabel;
    var boardY = boardBlockY + (toChannel > 0 ? longZone : offZone);
    var levelX = wide ? canvasX : upright.x;
    var placed = uprightParts(m, parts, cell, true, canvasX - parts.yLabel, canvasBlockY);
    return {
      view: "mapping",
      arrangement: wide ? "wide" : "narrow",
      feed: feed,
      cell: cell,
      roomy: parts === WIRED_ROOMY,
      width: Math.max(width, contentWidth),
      height: Math.max(height, contentHeight),
      content: {x: left, y: top, width: contentWidth, height: contentHeight},
      gutters: [
        {x: left, y: top, width: parts.gutter, height: contentHeight},
        {x: left + contentWidth - parts.gutter, y: top, width: parts.gutter, height: contentHeight}
      ],
      header: placed.header,
      legBand: placed.legBand,
      legWords: placed.legWords,
      yLabel: placed.yLabel,
      numberTop: placed.numberTop,
      numberBottom: placed.numberBottom,
      canvas: placed.canvas,
      level: {x: levelX, y: levelY, width: left + contentWidth - parts.gutter - levelX, height: levelDepth},
      upright: upright,
      nearLabel: {x: nearX, y: boardY, width: wired.nearLabel, height: boardHeight},
      board: {x: boardX, y: boardY, width: boardWidth, height: boardHeight, pitch: pitch},
      farZone: {x: boardX + boardWidth, y: boardBlockY, width: farZone, height: boardBlock},
      reaches: reached
    };
  }

  /* The mapping view of a column-leg file for a drawing area. The board stands beside
     the canvas where the area is wide enough for that with cells large enough to read.
     The cell is the largest at which the drawing fits the area in both directions. Where
     that is too small to read, it is the largest up to the readable size that fits the
     width: the drawing is then higher than the area. A board beside the canvas keeps its
     usual size before the cells grow, and gives way only to cells of the readable size. */
  function fitWired(m, width, height, board) {
    function placed(wide, parts, cell, wanted) {
      return placeWired(m, board, wide, parts, cell, wanted, width, height);
    }
    var wide = placed(true, WIRED_COMPACT, WIRED.legible, PITCH.least).content.width <= width;
    function largest(parts, wanted) {
      var readable = null;
      for (var cell = MAX_CELL; cell >= MIN_CELL; cell -= 1) {
        var f = placed(wide, parts, cell, wanted);
        if (f.content.width <= width) {
          if (cell >= WIRED.legible && f.content.height <= height) {
            return f;
          }
          if (cell <= WIRED.legible && !readable) {
            readable = f;
          }
        }
      }
      return readable;
    }
    function best(parts) {
      var usual = largest(parts, PITCH.usual);
      if (usual && usual.cell >= WIRED.legible) {
        return usual;
      }
      return largest(parts, PITCH.least) || usual || placed(wide, parts, MIN_CELL, PITCH.least);
    }
    var roomy = best(WIRED_ROOMY);
    return roomy.cell >= ROOMY_FROM ? roomy : best(WIRED_COMPACT);
  }

  /* The cell size in pixels and the place of every part, for a drawing area of a width
     and a height: the LEDs view, or with a board the mapping view, each as the kind of
     the file has it. */
  function fit(m, width, height, board) {
    if (m.kind === "columns") {
      return board ? fitWired(m, width, height, board) : fitUpright(m, width, height);
    }
    return board ? fitMapping(m, width, height, board) : fitLeds(m, width, height);
  }

  /* The centre of a pad of the board in a fitted mapping view. */
  function padAt(f, row, index) {
    var inset = BOARD.inset * f.board.pitch;
    return [
      row === "left" ? f.board.x + inset : f.board.x + f.board.width - inset,
      f.board.y + (BOARD.head + index + 0.5) * f.board.pitch
    ];
  }

  /* For each leg of a fitted mapping view: its pad, the label of the leg beside the pad,
     and the corner points of the line from the pad to the first LED of the chain. */
  function wires(m, f, board) {
    if (m.kind === "columns") {
      return wiresWired(m, f);
    }
    return f.arrangement === "below" ? wiresBelow(m, f) : wiresBeside(m, f);
  }

  /* The lines of a column-leg file. A line runs level from its pad to its upright track,
     along that to its level track, along that to the x of its first LED, and upright to
     that LED. A line from the right row of pads first runs level to its loop in the far
     zone. On the short way the loop leads to the level track. On the long way it leads
     beyond the other end of the board, and the line comes back across there to its
     upright track. */
  function wiresWired(m, f) {
    var wired = WIRED;
    var down = f.feed === "bottom" ? 1 : -1;
    var toChannel = f.arrangement === "wide" ? down : -down;
    var radius = BOARD.pad * f.board.pitch;
    var feedEdge = down > 0 ? f.canvas.y + f.canvas.height : f.canvas.y;
    var farEdge = down > 0 ? f.canvas.y : f.canvas.y + f.canvas.height;
    var firstLevel = (down > 0 ? f.level.y : f.level.y + f.level.height) + down * (wired.channelPad + wired.track / 2);
    var firstUpright = f.upright.x + f.upright.width - wired.channelPad - wired.track / 2;
    var firstLoop = f.board.x + f.board.width + wired.loopFirst;
    var facingEnd = toChannel > 0 ? f.board.y + f.board.height : f.board.y;
    var otherEnd = toChannel > 0 ? f.board.y : f.board.y + f.board.height;

    return f.reaches.map(function (reach) {
      var levelY = firstLevel + down * wired.track * reach.level;
      var trackX = firstUpright - wired.track * reach.upright;
      var pad = reach.at
        ? padAt(f, reach.at.row, reach.at.index)
        : [padAt(f, "left", 0)[0], facingEnd + toChannel * wired.offPad * (reach.index + 0.6)];
      var points = [pad];
      var label;
      if (reach.kind === "far") {
        var loopX = firstLoop + wired.track * reach.loop;
        label = {x: f.farZone.x + f.farZone.width - wired.farLabel, y: pad[1] + 3.5, anchor: "start"};
        points.push([loopX, pad[1]]);
        if (reach.way === "long") {
          var beyondY = otherEnd - toChannel * (wired.loopFirst + wired.track * reach.beyond);
          points.push([loopX, beyondY], [trackX, beyondY], [trackX, levelY]);
        } else {
          points.push([loopX, levelY]);
        }
      } else {
        label = {x: pad[0] - radius - 5, y: pad[1] - 4, anchor: "end"};
        points.push([trackX, pad[1]], [trackX, levelY]);
      }
      var entry = entryOf(m, f.feed, f.cell, reach.leg);
      var columnX = f.canvas.x + (entry.column - 0.5) * f.cell;
      if (entry.atFeed) {
        points.push([columnX, levelY], [columnX, feedEdge + down * wired.tip]);
      } else {
        /* The first LED is at the far edge of the canvas: the line runs in the gap at
           the left of the leg's first column to that edge and turns into the LED. */
        var gapX = f.canvas.x + entry.across;
        var turnY = farEdge - down * wired.turn;
        points.push([gapX, levelY], [gapX, turnY], [columnX, turnY], [columnX, farEdge - down * wired.tip]);
      }
      return {
        leg: reach.leg,
        kind: reach.kind,
        pad: {x: pad[0], y: pad[1], radius: radius, row: reach.at ? reach.at.row : null, index: reach.at ? reach.at.index : null},
        label: label,
        points: points
      };
    });
  }

  /* The last part of a line, from its track in the channel to the first LED. */
  function entry(m, f, leg, trackX) {
    var parts = BESIDE;
    var right = f.boardSide === "right";
    var out = right ? 1 : -1;
    var canvasEdge = right ? f.canvas.x + f.canvas.width : f.canvas.x;
    var awayEdge = right ? f.canvas.x : f.canvas.x + f.canvas.width;
    var first = position(m, leg.pin, 1);
    var rowY = centre(m, f, first[0], first[1])[1];
    if (m.width === 1 || (first[0] === m.width) === right) {
      return [[trackX, rowY], [canvasEdge + out * parts.tip, rowY]];
    }
    /* The first LED is at the far edge of the canvas: the line runs in the gap above the
       leg's first row to that edge and turns down to the LED. */
    var gapY = rowY - f.cell / 2;
    return [[trackX, gapY], [awayEdge - out * parts.turn, gapY], [awayEdge - out * parts.turn, rowY], [awayEdge - out * parts.tip, rowY]];
  }

  function wiresBelow(m, f) {
    var parts = BESIDE;
    var right = f.boardSide === "right";
    var out = right ? 1 : -1;
    var radius = BOARD.pad * f.board.pitch;
    var legs = m.legs.length;
    /* The highest leg takes the track farthest from the canvas, so that no line crosses
       another on its way down. */
    function trackOf(reach) {
      var k = legs - 1 - reach.track;
      return right ? f.channel.x + parts.channelPad + parts.trackGap * (k + 0.5) : f.channel.x + f.channel.width - parts.channelPad - parts.trackGap * (k + 0.5);
    }
    /* The lines for the far row of pins: the one nearest the canvas takes the top of
       the band and the outermost track of the second channel. */
    var far = f.reaches.filter(function (reach) { return reach.kind === "far"; })
      .sort(function (a, b) { return b.track - a.track; });
    var bandOf = {};
    far.forEach(function (reach, k) {
      bandOf[reach.leg] = k;
    });
    return f.reaches.map(function (reach) {
      var leg = m.legs[reach.leg];
      var trackX = trackOf(reach);
      var pad;
      var label;
      var points;
      if (reach.kind === "far") {
        var k = bandOf[reach.leg];
        var bandY = f.band.y + parts.channelPad + parts.trackGap * (k + 0.5);
        var secondX = right ? f.second.x + parts.channelPad + parts.trackGap * (k + 0.5) : f.second.x + f.second.width - parts.channelPad - parts.trackGap * (k + 0.5);
        pad = padAt(f, reach.at.row, reach.at.index);
        label = {x: pad[0] - out * (radius + 5), y: pad[1] - 4, anchor: right ? "end" : "start"};
        points = [pad, [secondX, pad[1]], [secondX, bandY], [trackX, bandY]];
      } else {
        pad = reach.kind === "near"
          ? padAt(f, reach.at.row, reach.at.index)
          : [padAt(f, f.boardSide, 0)[0], f.board.y + f.board.height + parts.offPad * (reach.index + 0.6)];
        label = {x: pad[0] + out * (radius + 5), y: pad[1] - 4, anchor: right ? "start" : "end"};
        points = [pad, [trackX, pad[1]]];
      }
      return {
        leg: reach.leg,
        kind: reach.kind,
        pad: {x: pad[0], y: pad[1], radius: radius, row: reach.at ? reach.at.row : null, index: reach.at ? reach.at.index : null},
        label: label,
        points: points.concat(entry(m, f, leg, trackX))
      };
    });
  }

  function wiresBeside(m, f) {
    var parts = BESIDE;
    var right = f.boardSide === "right";
    var out = right ? 1 : -1;
    var nearRow = right ? "left" : "right";
    var firstTrack = right ? f.channel.x + parts.channelPad : f.channel.x + f.channel.width - parts.channelPad;
    var boardFar = right ? f.board.x + f.board.width : f.board.x;
    var radius = BOARD.pad * f.board.pitch;
    var under = 0;
    f.reaches.forEach(function (reach) {
      if (reach.kind === "far" && !reach.over) {
        under += 1;
      }
    });
    var belowLoops = under ? parts.loopFirst + parts.loopGap * (under - 1) : 0;

    return f.reaches.map(function (reach) {
      var leg = m.legs[reach.leg];
      var trackX = firstTrack + out * parts.trackGap * (reach.track + 0.5);
      var pad;
      var label;
      var points;
      if (reach.kind === "off") {
        pad = [padAt(f, nearRow, 0)[0], f.board.y + f.board.height + belowLoops + parts.offPad * (reach.index + 0.6)];
        label = {x: pad[0] - out * (radius + 5), y: pad[1] - 4, anchor: right ? "end" : "start"};
        points = [pad, [trackX, pad[1]]];
      } else if (reach.kind === "near") {
        pad = padAt(f, reach.at.row, reach.at.index);
        label = {x: pad[0] - out * (radius + 5), y: pad[1] - 4, anchor: right ? "end" : "start"};
        points = [pad, [trackX, pad[1]]];
      } else {
        pad = padAt(f, reach.at.row, reach.at.index);
        var loopX = boardFar + out * (parts.loopFirst + parts.loopGap * reach.loop);
        var loopY = reach.over
          ? f.board.y - parts.loopFirst - parts.loopGap * reach.loop
          : f.board.y + f.board.height + parts.loopFirst + parts.loopGap * reach.loop;
        label = {x: f.farZone.x + (right ? f.farZone.width - parts.farLabel : parts.farLabel), y: pad[1] + 3.5, anchor: right ? "start" : "end"};
        points = [pad, [loopX, pad[1]], [loopX, loopY], [trackX, loopY]];
      }
      return {
        leg: reach.leg,
        kind: reach.kind,
        pad: {x: pad[0], y: pad[1], radius: radius, row: reach.at ? reach.at.row : null, index: reach.at ? reach.at.index : null},
        label: label,
        points: points.concat(entry(m, f, leg, trackX))
      };
    });
  }

  /* The corner points, in the pixels of a fitted drawing, of the chain of leg i: along
     each strip through the centres of its LEDs, and from the end of a strip to the start
     of the next by a short piece outside the edge of the canvas. `turns` says, for every
     strip but the first, where the chain comes back in and in which direction: for a row
     along x, for a column down the drawing. */
  function chain(m, f, i) {
    return m.kind === "columns" ? chainOfColumns(m, f, i) : chainOfRows(m, f, i);
  }

  function chainOfColumns(m, f, i) {
    var points = [];
    var turns = [];
    var top = f.canvas.y;
    var bottom = f.canvas.y + f.canvas.height;
    var corners = path(m, i);
    strips(m, i).forEach(function (strip, s) {
      var start = centre(m, f, corners[2 * s][0], corners[2 * s][1]);
      var end = centre(m, f, corners[2 * s + 1][0], corners[2 * s + 1][1]);
      var fromTop = strip.start === "top";
      if (s > 0) {
        var outside = fromTop ? top - WIRED.turn : bottom + WIRED.turn;
        points.push([points[points.length - 1][0], outside]);
        points.push([start[0], outside]);
        turns.push({x: start[0], y: fromTop ? top - 1 : bottom + 1, direction: fromTop ? 1 : -1});
      }
      points.push(start);
      points.push(end);
    });
    return {points: points, turns: turns};
  }

  function chainOfRows(m, f, i) {
    var points = [];
    var turns = [];
    var corners = path(m, i);
    for (var r = 0; r < corners.length; r += 2) {
      var start = centre(m, f, corners[r][0], corners[r][1]);
      var end = centre(m, f, corners[r + 1][0], corners[r + 1][1]);
      var fromRight = corners[r][0] > corners[r + 1][0] || (m.width === 1 && m.legs[i].first_led === "right");
      if (r > 0) {
        var outside = fromRight ? f.canvas.x + f.canvas.width + BESIDE.turn : f.canvas.x - BESIDE.turn;
        points.push([outside, points[points.length - 1][1]]);
        points.push([outside, start[1]]);
        turns.push({x: fromRight ? f.canvas.x + f.canvas.width + 1 : f.canvas.x - 1, y: start[1], direction: fromRight ? -1 : 1});
      }
      points.push(start);
      points.push(end);
    }
    return {points: points, turns: turns};
  }

  /* For each run of neighbouring columns of each leg of a column-leg file, the legs in
     the order of the file: the leg by its index, the first and the last x of the run, and
     the pixels the run takes across a fitted drawing, which the bracket of the run spans. */
  function legSpans(m, f) {
    var spans = [];
    m.legs.forEach(function (leg, i) {
      runs(m, i).forEach(function (run) {
        spans.push({
          leg: i,
          left: run.left,
          right: run.right,
          x: f.canvas.x + (run.left - 1) * f.cell,
          width: (run.right - run.left + 1) * f.cell
        });
      });
    });
    return spans;
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
    strips: strips,
    path: path,
    runs: runs,
    marks: marks,
    colour: colour,
    shown: shown,
    side: side,
    place: place,
    tracks: tracks,
    fit: fit,
    wires: wires,
    chain: chain,
    legSpans: legSpans,
    centre: centre,
    cellAt: cellAt
  };
}());
