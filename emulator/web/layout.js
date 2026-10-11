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

  /* The board in units of the distance between two pads. */
  var BOARD = {width: 11.5, height: 26.25, head: 2.75, inset: 0.5625, pad: 0.27};
  var PITCH = {least: 10, usual: 16, most: 20};

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

  /* The side of the canvas on which most legs have their first LED, "right" when the
     two sides are equal. The board is drawn on this side. */
  function side(m) {
    var balance = 0;
    m.legs.forEach(function (leg) {
      balance += leg.first_led === "right" ? 1 : -1;
    });
    return balance >= 0 ? "right" : "left";
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

  /* For each leg its track in the channel between the canvas and the board: the legs
     ordered by the y of their first row, highest first, get the tracks 0, 1, 2 and so
     on, track 0 nearest the canvas. */
  function tracks(m) {
    var order = m.legs.map(function (leg, i) { return i; });
    order.sort(function (a, b) {
      return m.legs[b].rows[0] - m.legs[a].rows[0] || a - b;
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

  /* The cell size in pixels and the place of every part, for a drawing area of a width
     and a height: the LEDs view, or with a board the mapping view. */
  function fit(m, width, height, board) {
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
    return f.arrangement === "below" ? wiresBelow(m, f) : wiresBeside(m, f);
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
     each row through the centres of its LEDs, and from the end of a row to the start of
     the next by a short piece outside the edge of the canvas. `turns` says, for every
     row but the first, where the chain comes back in and in which direction. */
  function chain(m, f, i) {
    var corners = path(m, i);
    var points = [];
    var turns = [];
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
    side: side,
    place: place,
    tracks: tracks,
    fit: fit,
    wires: wires,
    chain: chain,
    centre: centre,
    cellAt: cellAt
  };
}());
