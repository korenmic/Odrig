/* Prints what view.js draws for a mapping file and what it paints on its canvas, as one
   JSON document. Run in the JavaScript shell with the page's scripts as arguments:
   jsc dump_painted.js -- BOARD_JS LAYOUT_JS VIEW_JS MAPPING QUESTIONS
   QUESTIONS is the path of a JSON file: {"areas": [[width, height], ...], "board": true
   or false, "refreshes": [[byte, ...], ...]}. With "board" the drawing is the mapping
   view, without it the LEDs view. The scripts are loaded here, after a stand-in for the
   document of a browser that keeps every element they make and every dot they paint. For
   each area the output has the fit, the place and the size of the canvas, the elements of
   the drawing as dump_view.js lists them, the dots painted when the drawing is made, and
   the dots painted for each refresh in turn. A dot is [x, y, radius, fill, stroke, line
   width, cleared]: its centre in the pixels of the canvas, the colour it is filled with
   or the colour and the width of its ring, the other being null, and the rectangle
   [x, y, width, height] that was cleared before it. */

function Element(name) {
  this.name = name;
  this.attributes = {};
  this.children = [];
  this.text = "";
  this.style = {};
  this.dataset = {};
}

Element.prototype.setAttribute = function (key, value) {
  this.attributes[key] = String(value);
};

Element.prototype.getAttribute = function (key) {
  return this.attributes[key] === undefined ? null : this.attributes[key];
};

Element.prototype.appendChild = function (child) {
  this.children.push(child);
  return child;
};

Element.prototype.getContext = function () {
  var dots = this.dots = [];
  var scale = this.scale = [];
  var arc = null;
  var cleared = null;
  var context = {
    fillStyle: null,
    strokeStyle: null,
    lineWidth: null,
    setTransform: function (a, b, c, d, e, f) { scale.push([a, b, c, d, e, f]); },
    clearRect: function (x, y, width, height) { cleared = [x, y, width, height]; },
    beginPath: function () { arc = null; },
    arc: function (x, y, radius) { arc = [x, y, radius]; },
    fill: function () { dots.push([arc[0], arc[1], arc[2], context.fillStyle, null, null, cleared]); },
    stroke: function () { dots.push([arc[0], arc[1], arc[2], null, context.strokeStyle, context.lineWidth, cleared]); }
  };
  return context;
};

Object.defineProperty(Element.prototype, "textContent", {
  get: function () { return this.text; },
  set: function (text) {
    this.children = [];
    this.text = String(text);
  }
});

Object.defineProperty(Element.prototype, "innerHTML", {
  set: function () { this.firstChild = {namespaceURI: "http://www.w3.org/2000/svg"}; }
});

var document = {
  createElement: function (name) { return new Element(name); },
  createElementNS: function (namespace, name) { return new Element(name); }
};
var window = {devicePixelRatio: 1};

load(arguments[0]);
load(arguments[1]);
load(arguments[2]);

var m = OdrigLayout.read(read(arguments[3]));
var asked = JSON.parse(read(arguments[4]));
var legs = m.legs.map(function (leg) { return [leg.leg, leg.pin, leg.count]; });
var board = asked.board ? OdrigBoard : null;

function listed(host) {
  var found = [];
  function walk(element, leg) {
    element.children.forEach(function (child) {
      var own = child.attributes["data-leg"];
      var of = own === undefined ? leg : Number(own);
      found.push({name: child.name, attributes: child.attributes, text: child.text, leg: of});
      walk(child, of);
    });
  }
  walk(host, null);
  return found;
}

print(JSON.stringify(asked.areas.map(function (area) {
  var f = OdrigLayout.fit(m, area[0], area[1], board);
  var host = new Element("div");
  var drawing = OdrigView.build(host, m, legs, f, board);
  var canvas = host.children.filter(function (child) { return child.name === "canvas"; })[0];
  var made = canvas.dots.splice(0);
  return {
    fit: f,
    view: host.dataset.view,
    size: [host.style.width, host.style.height],
    layers: host.children.map(function (child) { return child.name; }),
    canvas: {width: canvas.width, height: canvas.height, style: canvas.style, scale: canvas.scale},
    elements: listed(host),
    made: made,
    painted: (asked.refreshes || []).map(function (bytes) {
      drawing.paint(new Uint8Array(bytes));
      return canvas.dots.splice(0);
    })
  };
})));
