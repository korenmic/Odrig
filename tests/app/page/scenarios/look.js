// The measures of everything on the screens, of a row's menu, of a message and of a
// question.

import {menuOf, shown, spaceKnown, storage} from "../reading.js";

function displayed(element) {
  return element.getClientRects().length > 0;
}

function rgba(colour) {
  const found = colour.match(/[0-9.]+/g) || ["255", "255", "255"];
  return [Number(found[0]), Number(found[1]), Number(found[2]), found.length > 3 ? Number(found[3]) : 1];
}

// The colour behind an element: the backgrounds up the tree, each laid over the one
// below it by its opacity, down to the first that is not see-through.
function behind(view, element) {
  const layers = [];
  for (let at = element; at !== null; at = at.parentElement) {
    const colour = rgba(view.getComputedStyle(at).backgroundColor);
    if (colour[3] > 0) {
      layers.push(colour);
      if (colour[3] >= 1) {
        break;
      }
    }
  }
  let mixed = [255, 255, 255];
  if (layers.length > 0 && layers[layers.length - 1][3] >= 1) {
    mixed = layers.pop().slice(0, 3);
  }
  while (layers.length > 0) {
    const [r, g, b, a] = layers.pop();
    mixed = [r * a + mixed[0] * (1 - a), g * a + mixed[1] * (1 - a), b * a + mixed[2] * (1 - a)];
  }
  return `rgb(${mixed.map((value) => Math.round(value)).join(", ")})`;
}

function measure(app) {
  const doc = app.doc;
  const view = app.frame.contentWindow;
  const box = (element) => {
    const rect = element.getBoundingClientRect();
    return {left: rect.left, top: rect.top, right: rect.right, bottom: rect.bottom};
  };
  // A control that the panel staying at the top covers is not seen: the list scrolls under it.
  const top = doc.getElementById("now-panel");
  const topBox = top.getBoundingClientRect();
  const covered = (element) => {
    const at = element.getBoundingClientRect();
    return top.classList.contains("frozen") && !top.contains(element) && at.top < topBox.bottom && at.bottom > topBox.top;
  };
  const controls = [...doc.querySelectorAll("button, input, select, label.button")].filter((element) => displayed(element) && !covered(element)).map((element) => ({
    what: element.id || element.getAttribute("aria-label") || element.textContent.trim(),
    group: element.closest("nav") !== null ? "nav" : element.closest("#message") !== null ? "message" : element.closest("#confirm") !== null ? "question" :
      element.closest("#row-menu") !== null ? "menu" : "screen",
    ...box(element.type === "checkbox" ? element.closest("label") : element),
  }));
  const texts = [...doc.querySelectorAll("p, label, h1, h2, button, input, span")]
    .filter((element) => displayed(element) && [...element.childNodes].some((node) => node.nodeType === 3 && node.textContent.trim() !== ""))
    .map((element) => {
      const style = view.getComputedStyle(element);
      return {what: element.id || element.className || element.textContent.trim().slice(0, 30), colour: style.color, behind: behind(view, element), size: parseFloat(style.fontSize),
        stale: element.closest(".stale") !== null};
    });
  const message = doc.getElementById("message");
  const question = doc.getElementById("confirm");
  const menu = doc.getElementById("row-menu");
  // The line of the brightness: its label, its field and the slider under them, with the
  // inside of their panel.
  const field = doc.getElementById("level-number");
  const panel = doc.getElementById("now-panel");
  const panelStyle = view.getComputedStyle(panel);
  const panelBox = panel.getBoundingClientRect();
  const level = displayed(field) ? {
    label: box(doc.querySelector("#level-line label")),
    field: box(field),
    slider: box(doc.getElementById("level")),
    left: panelBox.left + parseFloat(panelStyle.borderLeftWidth) + parseFloat(panelStyle.paddingLeft),
    right: panelBox.right - parseFloat(panelStyle.borderRightWidth) - parseFloat(panelStyle.paddingRight),
    digits: view.getComputedStyle(field).fontVariantNumeric,
    letters: parseFloat(view.getComputedStyle(field).fontSize),
  } : null;
  return {
    level,
    controls,
    texts,
    width: view.innerWidth,
    scrollWidth: doc.documentElement.scrollWidth,
    back: [view.getComputedStyle(doc.documentElement).backgroundColor, view.getComputedStyle(doc.body).backgroundColor],
    panels: [...doc.querySelectorAll(".panel, .row")].filter(displayed).map((element) => behind(view, element)),
    spaceBelow: parseFloat(view.getComputedStyle(doc.querySelector("main")).paddingBottom),
    nav: box(doc.querySelector("nav")),
    message: displayed(message) ? box(message) : null,
    question: displayed(question) ? box(question) : null,
    menu: displayed(menu) ? box(menu) : null,
    height: view.innerHeight,
  };
}

export default async function (app) {
  await shown(app, app.settings.rows);
  await app.until(() => spaceKnown(app) && storage(app).rows.length === app.settings.rows, "the list with its rows and the space");
  const animations = measure(app);
  // Selection mode, with the note of the ignored row under its name inside Play.
  app.pressIn("#list-head", "Select");
  await app.until(() => app.doc.querySelectorAll("#animations-list .pick").length > 0, "selection mode");
  const selecting = measure(app);
  app.press("Done");
  await app.until(() => app.doc.querySelectorAll("#animations-list .pick").length === 0 || !app.doc.querySelector("#animations-list .pick").getClientRects().length, "selection mode ended");
  menuOf(app, storage(app).rows[1].id);
  const withMenu = measure(app);
  app.doc.dispatchEvent(new KeyboardEvent("keydown", {key: "Escape", bubbles: true}));
  menuOf(app, storage(app).rows[0].id);
  [...app.byId("row-menu").querySelectorAll("button")].find((button) => button.textContent === "Delete").click();
  await app.until(() => app.text("confirm-text") !== null, "the question");
  const withQuestion = measure(app);
  app.press("Keep it");
  app.press("Upload");
  await app.until(() => app.shown() === "upload", "Upload");
  const upload = measure(app);
  app.press("Settings");
  await app.until(() => app.shown() === "settings", "Settings");
  const settings = measure(app);
  app.press("Target");
  await app.until(() => app.shown() === "target", "the target screen");
  const target = measure(app);
  app.fill("address", "not an address");
  app.press("Use");
  await app.until(() => app.text("message-text") !== null, "a message");
  const withMessage = measure(app);
  return {animations, selecting, withMenu, withQuestion, upload, settings, target, withMessage};
}
