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

  /* The band behind the rows of each leg, the bracket with the leg's number and pin, the
     y of every row and the LED numbers at its two ends. */
  function labels(m, f, under, over) {
    var size = sizes(f);
    m.legs.forEach(function (leg, i) {
      var colour = OdrigLayout.colour(i);
      var group = svg("g", {"data-leg": i});
      OdrigLayout.runs(m, i).forEach(function (run) {
        var rows = span(m, f, run);
        under.appendChild(svg("rect", {
          "class": "tint", "data-leg": i, x: f.canvas.x, y: rows.top, width: f.canvas.width, height: rows.height, fill: colour
        }));
        var edge = f.bracket.x + f.bracket.width - 6;
        var hook = Math.min(6, rows.height / 3);
        group.appendChild(svg("path", {
          "class": "bracket", stroke: colour,
          d: "M" + edge + " " + (rows.top + 2) + "h" + (-hook) + "V" + (rows.top + rows.height - 2) + "h" + hook
        }));
        var middle = rows.top + rows.height / 2;
        var textEdge = edge - hook - 7;
        if (rows.height >= size.leg + size.pin + 4) {
          group.appendChild(svg("text", {"class": "t-leg", x: textEdge, y: middle - 2, "text-anchor": "end", "font-size": size.leg, fill: colour}, "leg " + leg.leg));
          group.appendChild(svg("text", {"class": "t-pin", x: textEdge, y: middle + size.pin, "text-anchor": "end", "font-size": size.pin, fill: colour}, "pin " + leg.pin));
        } else {
          var both = svg("text", {"class": "t-leg", x: textEdge, y: middle + size.pin * 0.36, "text-anchor": "end", "font-size": Math.min(size.pin, Math.max(6, rows.height)), fill: colour},
                         "leg " + leg.leg + " \u00b7 pin " + leg.pin);
          group.appendChild(both);
        }
      });
      OdrigLayout.rows(m, i).forEach(function (row) {
        var at = OdrigLayout.centre(m, f, 1, row.y)[1] + size.row * 0.36;
        var fromRight = row.start === "right";
        group.appendChild(svg("text", {"class": "t-y", x: f.yLabel.x + f.yLabel.width - 6, y: at, "text-anchor": "end", "font-size": size.row}, "y=" + row.y));
        group.appendChild(svg("text", {"class": "t-n", x: f.numberLeft.x + f.numberLeft.width - 6, y: at, "text-anchor": "end", "font-size": size.row, fill: colour},
                              String(fromRight ? row.last : row.first)));
        group.appendChild(svg("text", {"class": "t-n", x: f.numberRight.x + 6, y: at, "font-size": size.row, fill: colour},
                              String(fromRight ? row.first : row.last)));
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

  /* Builds the drawing of a mapping in an element, for the legs the core lists
     ([leg, pin, number of LEDs] each) and a fit of OdrigLayout. Returns the drawing:
     paint(bytes) shows a refresh, at(px, py) says which LED is at a pixel. */
  function build(host, m, legs, f) {
    host.textContent = "";
    host.style.width = f.width + "px";
    host.style.height = f.height + "px";

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

    labels(m, f, under, over);
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

    paint(new Uint8Array(3 * centres.length));

    return {paint: paint, at: at, fit: f};
  }

  return {build: build};
}());
