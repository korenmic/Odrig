/* Drawing: one canvas for the LEDs, SVG for everything else.
   The LEDs are placed by the pin and the place along the chain alone, through
   OdrigLayout.position: the bytes of a refresh are never reordered. */

var OdrigView = (function () {
  "use strict";

  var NAMESPACE = (function () {
    var probe = document.createElement("div");
    probe.innerHTML = "<svg></svg>";
    return probe.firstChild.namespaceURI;
  }());

  var DARK_LED = "#2a2f36";
  var TAU = 2 * Math.PI;

  var CURVE = [];
  for (var value = 0; value < 256; value += 1) {
    CURVE.push(OdrigLayout.shown(value));
  }

  function svg(name, attributes, text) {
    var node = document.createElementNS(NAMESPACE, name);
    Object.keys(attributes || {}).forEach(function (key) {
      node.setAttribute(key, attributes[key]);
    });
    if (text !== undefined) {
      node.textContent = text;
    }
    return node;
  }

  function layer(f) {
    return svg("svg", {width: f.width, height: f.height, viewBox: "0 0 " + f.width + " " + f.height});
  }

  function round(number) {
    return Math.round(number * 100) / 100;
  }

  /* The path data of a line through corner points, with its corners rounded. */
  function rounded(points, radius) {
    var d = "M" + round(points[0][0]) + " " + round(points[0][1]);
    for (var i = 1; i < points.length - 1; i += 1) {
      var before = points[i - 1];
      var corner = points[i];
      var after = points[i + 1];
      var inLength = Math.hypot(corner[0] - before[0], corner[1] - before[1]);
      var outLength = Math.hypot(after[0] - corner[0], after[1] - corner[1]);
      var r = Math.min(radius, inLength / 2, outLength / 2);
      if (r < 0.5) {
        d += "L" + round(corner[0]) + " " + round(corner[1]);
      } else {
        d += "L" + round(corner[0] - (corner[0] - before[0]) / inLength * r) + " " + round(corner[1] - (corner[1] - before[1]) / inLength * r) +
             "Q" + round(corner[0]) + " " + round(corner[1]) + " " +
             round(corner[0] + (after[0] - corner[0]) / outLength * r) + " " + round(corner[1] + (after[1] - corner[1]) / outLength * r);
      }
    }
    var last = points[points.length - 1];
    return d + "L" + round(last[0]) + " " + round(last[1]);
  }

  /* An arrow head with its tip at a point, pointing along a direction. */
  function arrowHead(tip, dx, dy, size, colour, leg) {
    var length = Math.hypot(dx, dy) || 1;
    var ux = dx / length;
    var uy = dy / length;
    var backX = tip[0] - ux * size;
    var backY = tip[1] - uy * size;
    var half = size * 0.62;
    return svg("path", {
      "class": "head", "data-leg": leg, fill: colour,
      d: "M" + round(tip[0]) + " " + round(tip[1]) +
         "L" + round(backX - uy * half) + " " + round(backY + ux * half) +
         "L" + round(backX + uy * half) + " " + round(backY - ux * half) + "Z"
    });
  }

  /* The font sizes of the labels for a cell size. */
  function sizes(f) {
    var row = Math.max(6, Math.min(f.roomy ? 11 : 9.5, f.cell - 1));
    return {row: row, leg: f.roomy ? 13 : 11, pin: f.roomy ? 11.5 : 10, x: f.roomy ? 10.5 : 9};
  }

  /* The pixel rows of a run of neighbouring canvas rows. */
  function span(m, f, run) {
    var top = f.canvas.y + (m.height - run.top) * f.cell;
    return {top: top, height: (run.top - run.bottom + 1) * f.cell};
  }

  /* Presses a text into a width where its characters need more than that. */
  function pressed(text, characters, size, room) {
    if (characters * size * 0.6 > room) {
      text.setAttribute("textLength", round(Math.max(1, room)));
      text.setAttribute("lengthAdjust", "spacingAndGlyphs");
    }
    return text;
  }

  /* The labels of a column-leg file. For each leg: the band behind its columns and, in the
     leg band, over each run of its columns a bracket with the leg's number and under the
     number its pin. The words leg and pin stand once, at the left end of the leg band. The
     rows are marked at the left of the canvas and the columns in the header: the first,
     every tenth and the last. Where the drawing has the two number bands, the LED numbers
     at the two ends of every column stand in them, written upright. In the mapping view
     also a frame round each run of columns and the veil that fades it while another leg
     is pointed at. */
  function uprightLabels(m, f, under, over, top) {
    var size = sizes(f);
    var mapped = f.view === "mapping";
    var band = f.legBand;
    var above = f.feed === "bottom";
    /* From the canvas outward the band holds the bracket and the two lines of text. */
    var hook = 4;
    var inward = above ? hook : -hook;
    var spine = above ? band.y + band.height - 2 - hook : band.y + 2 + hook;
    var legLine = above ? band.y + size.leg : spine + 3 + size.leg;
    var pinLine = legLine + size.pin + 1;
    var groups = m.legs.map(function (leg, i) {
      return svg("g", {"class": "of-leg", "data-leg": i});
    });
    OdrigLayout.legSpans(m, f).forEach(function (span) {
      var leg = m.legs[span.leg];
      var colour = OdrigLayout.colour(span.leg);
      var group = groups[span.leg];
      var middle = span.x + span.width / 2;
      under.appendChild(svg("rect", {
        "class": "tint", "data-leg": span.leg, x: span.x, y: f.canvas.y, width: span.width, height: f.canvas.height, fill: colour
      }));
      if (mapped) {
        under.appendChild(svg("rect", {
          "class": "outline", "data-leg": span.leg, x: span.x + 1, y: f.canvas.y - 1.5, width: span.width - 2, height: f.canvas.height + 3,
          rx: Math.min(5, f.cell / 2), stroke: colour
        }));
        over.appendChild(svg("rect", {"class": "veil", "data-leg": span.leg, x: span.x, y: f.canvas.y, width: span.width, height: f.canvas.height}));
      }
      group.appendChild(svg("rect", {"class": "reach", x: span.x, y: band.y, width: span.width, height: band.height}));
      group.appendChild(svg("path", {
        "class": "bracket", stroke: colour,
        d: "M" + (span.x + 2) + " " + (spine + inward) + "v" + (-inward) + "H" + (span.x + span.width - 2) + "v" + inward
      }));
      group.appendChild(pressed(svg("text", {
        "class": "t-leg", x: middle, y: round(legLine), "text-anchor": "middle", "font-size": size.leg, fill: colour
      }, String(leg.leg)), String(leg.leg).length, size.leg, span.width - 2));
      group.appendChild(pressed(svg("text", {
        "class": "t-pin", x: middle, y: round(pinLine), "text-anchor": "middle", "font-size": size.pin, fill: colour
      }, String(leg.pin)), String(leg.pin).length, size.pin, span.width - 2));
    });
    var wordsEdge = f.legWords.x + f.legWords.width - 6;
    over.appendChild(svg("text", {"class": "t-y", x: wordsEdge, y: round(legLine), "text-anchor": "end", "font-size": size.pin}, "leg"));
    over.appendChild(svg("text", {"class": "t-y", x: wordsEdge, y: round(pinLine), "text-anchor": "end", "font-size": size.pin}, "pin"));

    var marksEdge = f.yLabel.x + f.yLabel.width - 6;
    OdrigLayout.marks(m.height).forEach(function (y) {
      var named = y === 1 || y === m.height;
      over.appendChild(svg("text", {
        "class": named ? "t-y" : "t-x", x: marksEdge, y: round(OdrigLayout.centre(m, f, 1, y)[1] + size.x * 0.36), "text-anchor": "end", "font-size": size.x
      }, named ? "y=" + y : String(y)));
    });
    var baseline = above ? f.header.y + f.header.height - 5 : f.header.y + size.x + 2;
    OdrigLayout.marks(m.width).forEach(function (x) {
      var named = x === 1 || x === m.width;
      over.appendChild(svg("text", {
        "class": named ? "t-y" : "t-x", x: OdrigLayout.centre(m, f, x, 1)[0], y: baseline, "text-anchor": "middle", "font-size": size.x
      }, named ? "x=" + x : String(x)));
    });

    if (f.numberTop && f.numberBottom) {
      /* An upright number is read from bottom to top. The one above the canvas begins at
         the canvas, and the one below the canvas ends there. In the mapping view the
         numbers stand clear of the turns of the chain. */
      var clear = mapped ? 11 : 4;
      var ends = [
        {y: f.numberTop.y + f.numberTop.height - clear, anchor: "start", room: f.numberTop.height - clear - 2, outward: -1},
        {y: f.numberBottom.y + clear, anchor: "end", room: f.numberBottom.height - clear - 2, outward: 1}
      ];
      m.legs.forEach(function (leg, i) {
        var colour = OdrigLayout.colour(i);
        OdrigLayout.strips(m, i).forEach(function (strip, s) {
          var middle = OdrigLayout.centre(m, f, strip.x, 1)[0];
          var x = middle + size.row * 0.36;
          var fromBottom = strip.start === "bottom";
          [fromBottom ? strip.last : strip.first, fromBottom ? strip.first : strip.last].forEach(function (number, e) {
            var text = String(number);
            if (mapped && s === 0 && e === (fromBottom ? 1 : 0)) {
              /* The number of the first LED is a tag on the line that feeds it. */
              var length = size.row * 0.62 + 9;
              var at = ends[e].y + ends[e].outward * (2 + length / 2);
              top.appendChild(svg("rect", {
                "class": "tag", "data-leg": i, x: round(middle - size.row * 0.66), y: round(at - length / 2), width: round(size.row * 1.32), height: round(length),
                rx: round(size.row * 0.66), stroke: colour
              }));
              top.appendChild(svg("text", {
                "class": "t-n", "data-leg": i, transform: "translate(" + round(x) + " " + round(at) + ") rotate(-90)", "text-anchor": "middle", "font-size": size.row, fill: colour
              }, text));
            } else {
              groups[i].appendChild(pressed(svg("text", {
                "class": "t-n", transform: "translate(" + round(x) + " " + ends[e].y + ") rotate(-90)", "text-anchor": ends[e].anchor, "font-size": size.row, fill: colour
              }, text), text.length, size.row, ends[e].room));
            }
          });
        });
      });
    }
    groups.forEach(function (group) {
      over.appendChild(group);
    });
  }

  /* The labels of a row-leg file: the band behind the rows of each leg, the bracket with
     the leg's number and pin, the y of every row and the LED numbers at its two ends. In
     the mapping view also the outline of the rows and the veil that fades them while
     another leg is pointed at. */
  function labels(m, f, under, over, top) {
    var size = sizes(f);
    var mapped = f.view === "mapping";
    var bracketAtRight = mapped && f.boardSide === "left";
    var firstOf = {};
    if (mapped) {
      m.legs.forEach(function (leg, i) {
        var first = OdrigLayout.position(m, leg.pin, 1);
        firstOf[i] = {y: first[1], atRight: first[0] === m.width};
      });
    }
    m.legs.forEach(function (leg, i) {
      var colour = OdrigLayout.colour(i);
      var group = svg("g", {"class": "of-leg", "data-leg": i});
      OdrigLayout.runs(m, i).forEach(function (run) {
        var rows = span(m, f, run);
        under.appendChild(svg("rect", {
          "class": "tint", "data-leg": i, x: f.canvas.x, y: rows.top, width: f.canvas.width, height: rows.height, fill: colour
        }));
        if (mapped) {
          under.appendChild(svg("rect", {
            "class": "outline", "data-leg": i, x: f.canvas.x - 1.5, y: rows.top + 1, width: f.canvas.width + 3, height: rows.height - 2,
            rx: Math.min(5, f.cell / 2), stroke: colour
          }));
          over.appendChild(svg("rect", {"class": "veil", "data-leg": i, x: f.canvas.x, y: rows.top, width: f.canvas.width, height: rows.height}));
        }
        var hook = Math.min(6, rows.height / 3);
        var edge = bracketAtRight ? f.bracket.x + 6 : f.bracket.x + f.bracket.width - 6;
        var inward = bracketAtRight ? hook : -hook;
        group.appendChild(svg("rect", {"class": "reach", x: f.bracket.x, y: rows.top, width: f.bracket.width, height: rows.height}));
        group.appendChild(svg("path", {
          "class": "bracket", stroke: colour,
          d: "M" + edge + " " + (rows.top + 2) + "h" + inward + "V" + (rows.top + rows.height - 2) + "h" + (-inward)
        }));
        var middle = rows.top + rows.height / 2;
        var textEdge = edge + inward + (bracketAtRight ? 7 : -7);
        var anchor = bracketAtRight ? "start" : "end";
        if (rows.height >= 16) {
          /* Two lines, smaller where the rows leave less room. */
          var legSize = Math.min(size.leg, 0.5 * (rows.height - 3));
          var pinSize = Math.min(size.pin, 0.46 * (rows.height - 3));
          group.appendChild(svg("text", {"class": "t-leg", x: textEdge, y: middle - 2, "text-anchor": anchor, "font-size": round(legSize), fill: colour}, "leg " + leg.leg));
          group.appendChild(svg("text", {"class": "t-pin", x: textEdge, y: middle + pinSize, "text-anchor": anchor, "font-size": round(pinSize), fill: colour}, "pin " + leg.pin));
        } else {
          /* One line, pressed into the width of the column where it is longer. */
          var words = "leg " + leg.leg + " \u00b7 pin " + leg.pin;
          var oneSize = Math.min(size.pin, Math.max(6, rows.height));
          var room = f.bracket.width - hook - 15;
          var one = svg("text", {"class": "t-leg", x: textEdge, y: middle + oneSize * 0.36, "text-anchor": anchor, "font-size": oneSize, fill: colour}, words);
          if (words.length * oneSize * 0.56 > room) {
            one.setAttribute("textLength", round(room));
            one.setAttribute("lengthAdjust", "spacingAndGlyphs");
          }
          group.appendChild(one);
        }
      });
      OdrigLayout.strips(m, i).forEach(function (row) {
        var at = OdrigLayout.centre(m, f, 1, row.y)[1];
        var baseline = at + size.row * 0.36;
        var fromRight = row.start === "right";
        var yEdge = bracketAtRight ? f.yLabel.x + 6 : f.yLabel.x + f.yLabel.width - 6;
        group.appendChild(svg("text", {"class": "t-y", x: yEdge, y: baseline, "text-anchor": bracketAtRight ? "start" : "end", "font-size": size.row}, "y=" + row.y));
        /* In the mapping view the numbers stand clear of the turns of the chain, and the
           number of the first LED sits on the line that feeds it. */
        var gap = mapped ? 11 : 6;
        [
          {number: fromRight ? row.last : row.first, x: f.numberLeft.x + f.numberLeft.width - gap, anchor: "end", atRight: false},
          {number: fromRight ? row.first : row.last, x: f.numberRight.x + gap, anchor: "start", atRight: true}
        ].forEach(function (end) {
          var text = String(end.number);
          if (mapped && end.number === 1 && firstOf[i].y === row.y && firstOf[i].atRight === end.atRight) {
            /* The number of the first LED is a tag on the line that feeds it. */
            var width = size.row * 0.62 + 9;
            var middle = end.atRight ? end.x + 2 + width / 2 : end.x - 2 - width / 2;
            top.appendChild(svg("rect", {
              "class": "tag", "data-leg": i, x: middle - width / 2, y: at - size.row * 0.66, width: width, height: size.row * 1.32,
              rx: size.row * 0.66, stroke: colour
            }));
            top.appendChild(svg("text", {"class": "t-n", "data-leg": i, x: middle, y: baseline, "text-anchor": "middle", "font-size": size.row, fill: colour}, text));
          } else {
            group.appendChild(svg("text", {"class": "t-n", x: end.x, y: baseline, "text-anchor": end.anchor, "font-size": size.row, fill: colour}, text));
          }
        });
      });
      over.appendChild(group);
    });
    var baseline = f.header.y + f.header.height - 7;
    var marks = [1, m.width];
    if (f.cell >= 9) {
      for (var x = 10; x < m.width - 2; x += 10) {
        marks.push(x);
      }
    }
    marks.forEach(function (x) {
      var named = x === 1 || x === m.width;
      over.appendChild(svg("text", {
        "class": named ? "t-y" : "t-x", x: OdrigLayout.centre(m, f, x, 1)[0], y: baseline, "text-anchor": "middle", "font-size": size.x
      }, named ? "x=" + x : String(x)));
    });
  }

  /* The path of each chain through its rows, drawn behind the dots, with an arrow head
     where the chain comes into a row and a bar where it ends. */
  function chains(m, f, under, over) {
    m.legs.forEach(function (leg, i) {
      var colour = OdrigLayout.colour(i);
      var chain = OdrigLayout.chain(m, f, i);
      var d = rounded(chain.points, Math.min(4, f.cell / 2));
      under.appendChild(svg("path", {"class": "chain", "data-leg": i, d: d, stroke: colour, "stroke-width": Math.max(1.2, Math.min(2, f.cell / 7))}));
      /* Small arrows along each row, between two LEDs, say which way the chain runs. */
      var marks = m.width >= 12 ? [0.25, 0.5, 0.75] : (m.width >= 3 ? [0.5] : []);
      var reach = Math.max(2, f.cell * 0.26);
      OdrigLayout.strips(m, i).forEach(function (row) {
        var way = row.start === "right" ? -1 : 1;
        var y = OdrigLayout.centre(m, f, 1, row.y)[1];
        marks.forEach(function (share) {
          var x = f.canvas.x + Math.round(m.width * share) * f.cell;
          under.appendChild(svg("path", {
            "class": "chevron", "data-leg": i, stroke: colour,
            d: "M" + round(x - way * reach / 2) + " " + round(y - reach) + "l" + round(way * reach) + " " + round(reach) + "l" + round(-way * reach) + " " + round(reach)
          }));
        });
      });
      var head = Math.max(4, Math.min(6, f.cell / 2));
      chain.turns.forEach(function (turn) {
        over.appendChild(arrowHead([turn.x + turn.direction, turn.y], turn.direction, 0, head, colour, i));
      });
      var end = chain.points[chain.points.length - 1];
      var before = chain.points[chain.points.length - 2];
      var outward = end[0] >= before[0] ? 1 : -1;
      var edge = outward > 0 ? f.canvas.x + f.canvas.width : f.canvas.x;
      over.appendChild(svg("path", {
        "class": "wire ending", "data-leg": i, stroke: colour, "stroke-width": 1.6,
        d: "M" + (edge + outward * 1) + " " + end[1] + "h" + (outward * 4) + "m0 " + (-head / 2) + "v" + head
      }));
    });
  }

  /* The path of each chain of a column-leg file through its columns, drawn behind the
     dots, with small arrows along every column, between two LEDs, that point the way the
     LED numbers grow, an arrow head where the chain comes back into the canvas after a
     turn, and a bar where it ends. */
  function uprightChains(m, f, under, over) {
    var shares = m.height >= 12 ? [0.25, 0.5, 0.75] : (m.height >= 3 ? [0.5] : []);
    var reach = Math.max(2, f.cell * 0.26);
    var head = Math.max(4, Math.min(6, f.cell / 2));
    m.legs.forEach(function (leg, i) {
      var colour = OdrigLayout.colour(i);
      var chain = OdrigLayout.chain(m, f, i);
      under.appendChild(svg("path", {
        "class": "chain", "data-leg": i, d: rounded(chain.points, Math.min(4, f.cell / 2)), stroke: colour, "stroke-width": Math.max(1.2, Math.min(2, f.cell / 7))
      }));
      var columns = OdrigLayout.strips(m, i);
      columns.forEach(function (column) {
        /* Down the drawing for a column that starts at the top, up it otherwise. */
        var way = column.start === "top" ? 1 : -1;
        var x = OdrigLayout.centre(m, f, column.x, 1)[0];
        shares.forEach(function (share) {
          var y = f.canvas.y + Math.round(m.height * share) * f.cell;
          under.appendChild(svg("path", {
            "class": "chevron", "data-leg": i, stroke: colour,
            d: "M" + round(x - reach) + " " + round(y - way * reach / 2) + "l" + round(reach) + " " + round(way * reach) + "l" + round(reach) + " " + round(-way * reach)
          }));
        });
      });
      chain.turns.forEach(function (turn) {
        over.appendChild(arrowHead([turn.x, turn.y + turn.direction], 0, turn.direction, head, colour, i));
      });
      var outward = columns[columns.length - 1].start === "top" ? 1 : -1;
      var end = chain.points[chain.points.length - 1];
      var edge = outward > 0 ? f.canvas.y + f.canvas.height : f.canvas.y;
      over.appendChild(svg("path", {
        "class": "wire ending", "data-leg": i, stroke: colour, "stroke-width": 1.6,
        d: "M" + round(end[0]) + " " + (edge + outward) + "v" + (outward * 4) + "m" + (-head / 2) + " 0h" + head
      }));
    });
  }

  /* The board: its body, the module with its antenna, the USB sockets, and a pad with
     its label for every pin. */
  function boardDrawing(f, board, used) {
    var b = f.board;
    var p = b.pitch;
    var group = svg("g", {"class": "board", transform: "translate(" + b.x + " " + b.y + ")"});
    var defs = svg("defs");
    var pcb = svg("linearGradient", {id: "odrig-pcb", x1: 0, y1: 0, x2: 1, y2: 1});
    pcb.appendChild(svg("stop", {offset: 0, "stop-color": "#1b4a35"}));
    pcb.appendChild(svg("stop", {offset: 1, "stop-color": "#0f2c20"}));
    var can = svg("linearGradient", {id: "odrig-can", x1: 0, y1: 0, x2: 1, y2: 1});
    can.appendChild(svg("stop", {offset: 0, "stop-color": "#d5dae0"}));
    can.appendChild(svg("stop", {offset: 1, "stop-color": "#8f98a3"}));
    defs.appendChild(pcb);
    defs.appendChild(can);
    group.appendChild(defs);

    group.appendChild(svg("rect", {"class": "pcb", x: 0, y: 0, width: b.width, height: b.height, rx: 0.6 * p, fill: "url(#odrig-pcb)"}));

    /* The module: a small board of its own, the antenna at its top, the metal can below. */
    var moduleWidth = 5.7 * p;
    var moduleX = (b.width - moduleWidth) / 2;
    var moduleTop = 0.3 * p;
    var antennaHeight = 2.2 * p;
    var canHeight = 6.6 * p;
    group.appendChild(svg("rect", {"class": "module", x: moduleX, y: moduleTop, width: moduleWidth, height: antennaHeight + canHeight, rx: 0.2 * p}));
    var trace = "M" + round(moduleX + 0.5 * p) + " " + round(moduleTop + antennaHeight - 0.35 * p);
    var step = (moduleWidth - 1.0 * p) / 9;
    for (var k = 0; k < 9; k += 1) {
      trace += (k % 2 === 0 ? "V" + round(moduleTop + 0.45 * p) : "V" + round(moduleTop + antennaHeight - 0.35 * p)) + "h" + round(step);
    }
    trace += "V" + round(moduleTop + antennaHeight - 0.35 * p);
    group.appendChild(svg("path", {"class": "antenna", d: trace, "stroke-width": Math.max(1.2, 0.13 * p)}));
    var canTop = moduleTop + antennaHeight;
    group.appendChild(svg("rect", {"class": "can", x: moduleX + 0.2 * p, y: canTop, width: moduleWidth - 0.4 * p, height: canHeight - 0.2 * p, rx: 0.25 * p, fill: "url(#odrig-can)"}));
    var words = board.name.split(" ");
    group.appendChild(svg("text", {"class": "t-chip", x: b.width / 2, y: canTop + canHeight * 0.44, "text-anchor": "middle", "font-size": round(0.8 * p)}, words[0]));
    group.appendChild(svg("text", {"class": "t-chip small", x: b.width / 2, y: canTop + canHeight * 0.44 + 1.05 * p, "text-anchor": "middle", "font-size": round(0.66 * p)}, words.slice(1).join(" ")));

    /* The lower half: a chip, the two buttons, a light, and the two USB sockets. */
    var middle = b.width / 2;
    group.appendChild(svg("rect", {"class": "part", x: middle - 1.0 * p, y: 13.2 * p, width: 2.0 * p, height: 2.0 * p, rx: 0.12 * p}));
    group.appendChild(svg("rect", {"class": "part", x: middle - 0.3 * p, y: 16.6 * p, width: 0.6 * p, height: 0.6 * p, rx: 0.1 * p, fill: "#e9ecef"}));
    [-1, 1].forEach(function (way) {
      var x = middle + way * 1.55 * p;
      group.appendChild(svg("rect", {"class": "button", x: x - 0.6 * p, y: 19.0 * p, width: 1.2 * p, height: 0.95 * p, rx: 0.15 * p}));
      group.appendChild(svg("circle", {"class": "button-top", cx: x, cy: 19.475 * p, r: 0.28 * p}));
      var socketWidth = 2.3 * p;
      group.appendChild(svg("rect", {"class": "socket", x: x - socketWidth / 2, y: b.height - 2.2 * p, width: socketWidth, height: 2.45 * p, rx: 0.3 * p, fill: "url(#odrig-can)"}));
      group.appendChild(svg("rect", {"class": "slot", x: x - socketWidth / 2 + 0.3 * p, y: b.height - 0.55 * p, width: socketWidth - 0.6 * p, height: 0.5 * p, rx: 0.25 * p}));
      group.appendChild(svg("text", {"class": "t-usb", x: x, y: b.height - 1.05 * p, "text-anchor": "middle", "font-size": round(0.62 * p)}, "USB"));
    });

    /* The pads and their labels. */
    var inset = 0.5625 * p;
    var radius = 0.27 * p;
    ["left", "right"].forEach(function (row) {
      board[row].forEach(function (label, index) {
        var y = (2.75 + index + 0.5) * p;
        var x = row === "left" ? inset : b.width - inset;
        var leg = used[row + ":" + index];
        var taken = leg !== undefined;
        var holder = svg("g", taken ? {"class": "pin taken", "data-leg": leg} : {"class": "pin"});
        if (taken) {
          var colour = OdrigLayout.colour(leg);
          holder.appendChild(svg("circle", {"class": "halo", cx: x, cy: y, r: radius + 3, fill: colour}));
          holder.appendChild(svg("circle", {"class": "pad", cx: x, cy: y, r: radius, fill: colour}));
          holder.appendChild(svg("text", {
            "class": "t-pad", x: row === "left" ? x + radius + 5 : x - radius - 5, y: y + 0.21 * p, "text-anchor": row === "left" ? "start" : "end",
            "font-size": round(0.62 * p), fill: colour
          }, label));
        } else {
          holder.appendChild(svg("circle", {"class": "pad", cx: x, cy: y, r: radius}));
          holder.appendChild(svg("text", {
            "class": "t-pad", x: row === "left" ? x + radius + 5 : x - radius - 5, y: y + 0.21 * p, "text-anchor": row === "left" ? "start" : "end",
            "font-size": round(0.6 * p)
          }, label));
        }
        group.appendChild(holder);
      });
    });
    return group;
  }

  /* The board, and for each leg the line from its pad to the first LED of its chain. */
  function wiring(m, f, board, over) {
    var wires = OdrigLayout.wires(m, f, board);
    var used = {};
    wires.forEach(function (wire) {
      if (wire.pad.row !== null) {
        used[wire.pad.row + ":" + wire.pad.index] = wire.leg;
      }
    });
    /* The lines of a column-leg file lie on tracks close to each other. */
    var lines = svg("g", {"class": m.kind === "columns" ? "wires close" : "wires"});
    over.appendChild(lines);
    over.appendChild(boardDrawing(f, board, used));
    wires.forEach(function (wire) {
      var leg = m.legs[wire.leg];
      var colour = OdrigLayout.colour(wire.leg);
      var d = rounded(wire.points, 5);
      lines.appendChild(svg("path", {"class": "wire", "data-leg": wire.leg, d: d, stroke: colour, "stroke-width": 2}));
      lines.appendChild(svg("path", {"class": "reach-line", "data-leg": wire.leg, d: d}));
      var last = wire.points[wire.points.length - 1];
      var before = wire.points[wire.points.length - 2];
      lines.appendChild(arrowHead(last, last[0] - before[0], last[1] - before[1], Math.max(5, Math.min(7, f.cell / 2 + 1)), colour, wire.leg));
      if (wire.kind === "off") {
        var holder = svg("g", {"class": "pin taken", "data-leg": wire.leg});
        holder.appendChild(svg("circle", {"class": "halo", cx: wire.pad.x, cy: wire.pad.y, r: wire.pad.radius + 3, fill: colour}));
        holder.appendChild(svg("circle", {"class": "pad", cx: wire.pad.x, cy: wire.pad.y, r: wire.pad.radius, fill: colour}));
        var inward = f.boardSide === "left" ? -1 : 1;
        holder.appendChild(svg("text", {
          "class": "t-pad", x: wire.pad.x + inward * (wire.pad.radius + 6), y: wire.pad.y + 3.5, "text-anchor": inward > 0 ? "start" : "end", "font-size": 10, fill: colour
        }, "GPIO " + leg.pin));
        over.appendChild(holder);
      }
      over.appendChild(svg("text", {
        "class": "t-leg t-wire", "data-leg": wire.leg, x: round(wire.label.x), y: round(wire.label.y), "text-anchor": wire.label.anchor, "font-size": 10.5, fill: colour
      }, "leg " + leg.leg));
    });
  }

  /* Builds the drawing of a mapping in an element, for the legs the core lists
     ([leg, pin, number of LEDs] each) and a fit of OdrigLayout; with a board, the
     mapping view. Returns the drawing: paint(bytes) shows a refresh, at(px, py) says
     which LED is at a pixel, and focus(leg) highlights one leg and fades the others. */
  function build(host, m, legs, f, board) {
    host.textContent = "";
    host.style.width = f.width + "px";
    host.style.height = f.height + "px";
    host.dataset.view = f.view;

    var under = layer(f);
    var over = layer(f);
    var canvas = document.createElement("canvas");
    var ratio = window.devicePixelRatio || 1;
    canvas.width = Math.round(f.canvas.width * ratio);
    canvas.height = Math.round(f.canvas.height * ratio);
    canvas.style.left = f.canvas.x + "px";
    canvas.style.top = f.canvas.y + "px";
    canvas.style.width = f.canvas.width + "px";
    canvas.style.height = f.canvas.height + "px";
    var context = canvas.getContext("2d");
    context.setTransform(ratio, 0, 0, ratio, 0, 0);

    var top = svg("g", {"class": "tags"});
    var upright = m.kind === "columns";
    if (upright) {
      uprightLabels(m, f, under, over, top);
    } else {
      labels(m, f, under, over, top);
    }
    if (f.view === "mapping") {
      if (upright) {
        uprightChains(m, f, under, over);
      } else {
        chains(m, f, under, over);
      }
      wiring(m, f, board, over);
    }
    over.appendChild(top);
    host.appendChild(under);
    host.appendChild(canvas);
    host.appendChild(over);

    /* Where each LED of a refresh is drawn: for the legs in the core's order, for the
       LEDs in chain order, the centre of the dot, or null for an LED the mapping file
       does not place. */
    var centres = [];
    legs.forEach(function (leg) {
      for (var n = 1; n <= leg[2]; n += 1) {
        var place = OdrigLayout.position(m, leg[1], n);
        centres.push(place ? [(place[0] - 0.5) * f.cell, (m.height - place[1] + 0.5) * f.cell] : null);
      }
    });

    var radius = 0.38 * f.cell;
    var half = f.cell / 2;
    var painted = null;

    function dot(centre, red, green, blue) {
      context.clearRect(centre[0] - half, centre[1] - half, f.cell, f.cell);
      context.beginPath();
      if (red || green || blue) {
        context.arc(centre[0], centre[1], radius, 0, TAU);
        context.fillStyle = "rgb(" + CURVE[red] + "," + CURVE[green] + "," + CURVE[blue] + ")";
        context.fill();
      } else {
        /* A dark LED: a faint ring, through which the path of the chain behind the dots
           is seen. */
        context.arc(centre[0], centre[1], Math.max(0.5, radius - 0.5), 0, TAU);
        context.strokeStyle = DARK_LED;
        context.lineWidth = 1;
        context.stroke();
      }
    }

    /* Shows a refresh: three bytes for each LED, as the core gave them. Only the LEDs
       whose bytes changed since the last refresh shown are drawn again. */
    function paint(bytes) {
      var whole = !painted || painted.length !== bytes.length;
      for (var i = 0; i < centres.length; i += 1) {
        var at = 3 * i;
        if (centres[i] && (whole || bytes[at] !== painted[at] || bytes[at + 1] !== painted[at + 1] || bytes[at + 2] !== painted[at + 2])) {
          dot(centres[i], bytes[at] || 0, bytes[at + 1] || 0, bytes[at + 2] || 0);
        }
      }
      painted = bytes;
    }

    /* The LED at a pixel of the drawing: its leg by index, its LED number and its canvas
       position, or null. */
    function at(px, py) {
      var cell = OdrigLayout.cellAt(m, f, px, py);
      if (!cell) {
        return null;
      }
      var found = OdrigLayout.find(m, cell[0], cell[1]);
      return found ? {leg: found.leg, led: found.led, x: cell[0], y: cell[1]} : null;
    }

    /* Highlights every part of one leg, by its index, and fades the parts of the other
       legs; null ends it. */
    var focused = null;
    function focus(leg) {
      if (leg === focused) {
        return;
      }
      focused = leg;
      host.classList.toggle("pointing", leg !== null);
      Array.prototype.forEach.call(host.querySelectorAll("[data-leg]"), function (part) {
        var own = leg !== null && Number(part.getAttribute("data-leg")) === leg;
        part.classList.toggle("hot", own);
        part.classList.toggle("dim", leg !== null && !own);
      });
    }

    paint(new Uint8Array(3 * centres.length));

    return {paint: paint, at: at, focus: focus, fit: f};
  }

  return {build: build};
}());
