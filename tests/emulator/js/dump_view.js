/* Prints what view.js draws for a mapping file in its mapping view, as one JSON document.
   Run in the JavaScript shell with the page's scripts as arguments:
   jsc dump_view.js -- BOARD_JS LAYOUT_JS VIEW_JS MAPPING AREAS [LEG]
   AREAS is a JSON list of [width, height]. The scripts are loaded here, after a stand-in
   for the document of a browser that keeps every element they make. For each area the
   output lists the elements of the drawing in the order they are drawn, each with its
   name, its attributes, its text and the leg it belongs to, which is its own `data-leg`
   or that of the nearest element around it that has one. It lists them once more after
   the leg with index LEG, 0 when it is left out, has been pointed at. */

function Element(name) {
  var element = this;
  this.name = name;
  this.attributes = {};
  this.children = [];
  this.text = "";
  this.style = {};
  this.dataset = {};
  this.classList = {
    toggle: function (word, on) {
      var words = (element.attributes["class"] || "").split(" ").filter(function (given) { return given && given !== word; });
      if (on) {
        words.push(word);
      }
      element.attributes["class"] = words.join(" ");
    }
  };
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

Element.prototype.each = function (visit) {
  this.children.forEach(function (child) {
    visit(child);
    child.each(visit);
  });
};

/* Only the one selector the view asks for. */
Element.prototype.querySelectorAll = function (selector) {
  if (selector !== "[data-leg]") {
    throw new Error("the stand-in knows no selector " + selector);
  }
  var found = [];
  this.each(function (element) {
    if (element.attributes["data-leg"] !== undefined) {
      found.push(element);
    }
  });
  return found;
};

Element.prototype.getContext = function () {
  var drawn = this.drawn = {arcs: 0};
  return {
    setTransform: function () {},
    clearRect: function () {},
    beginPath: function () {},
    arc: function () { drawn.arcs += 1; },
    fill: function () {},
    stroke: function () {}
  };
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
var areas = JSON.parse(arguments[4]);
var pointed = arguments.length > 5 ? Number(arguments[5]) : 0;
var legs = m.legs.map(function (leg) { return [leg.leg, leg.pin, leg.count]; });

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

print(JSON.stringify(areas.map(function (area) {
  var f = OdrigLayout.fit(m, area[0], area[1], OdrigBoard);
  var host = new Element("div");
  var drawing = OdrigView.build(host, m, legs, f, OdrigBoard);
  var canvas = host.children.filter(function (child) { return child.name === "canvas"; })[0];
  var drawn = JSON.parse(JSON.stringify(listed(host)));
  drawing.focus(pointed);
  return {
    fit: f,
    view: host.dataset.view,
    size: [host.style.width, host.style.height],
    layers: host.children.map(function (child) { return child.name; }),
    dots: canvas.drawn.arcs,
    elements: drawn,
    pointing: listed(host),
    host: host.attributes["class"] || "",
    at: drawing.at(f.canvas.x + f.cell / 2, f.canvas.y + f.canvas.height - f.cell / 2)
  };
})));
