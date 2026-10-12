// The measures of everything on the two screens, and of a message.

import {shown} from "../reading.js";

function displayed(element) {
  return element.getClientRects().length > 0;
}

// The colour behind an element: the nearest one up the tree that is not see-through.
function behind(view, element) {
  for (let at = element; at !== null; at = at.parentElement) {
    const colour = view.getComputedStyle(at).backgroundColor;
    if (!/rgba\(.*, 0\)$|transparent/.test(colour)) {
      return colour;
    }
  }
  return "rgb(255, 255, 255)";
}

function measure(app) {
  const doc = app.doc;
  const view = app.frame.contentWindow;
  const box = (element) => {
    const rect = element.getBoundingClientRect();
    return {left: rect.left, top: rect.top, right: rect.right, bottom: rect.bottom};
  };
  const controls = [...doc.querySelectorAll("button, input")].filter(displayed).map((element) => ({
    what: element.id || element.textContent.trim(),
    group: element.closest("nav") !== null ? "nav" : element.closest("#message") !== null ? "message" : "screen",
    ...box(element),
  }));
  const texts = [...doc.querySelectorAll("p, label, h1, button, input, span")]
    .filter((element) => displayed(element) && [...element.childNodes].some((node) => node.nodeType === 3 && node.textContent.trim() !== ""))
    .map((element) => {
      const style = view.getComputedStyle(element);
      return {what: element.id || element.textContent.trim().slice(0, 30), colour: style.color, behind: behind(view, element), size: parseFloat(style.fontSize), family: style.fontFamily};
    });
  const message = doc.getElementById("message");
  return {
    controls,
    texts,
    width: view.innerWidth,
    scrollWidth: doc.documentElement.scrollWidth,
    back: [view.getComputedStyle(doc.documentElement).backgroundColor, view.getComputedStyle(doc.body).backgroundColor],
    spaceBelow: parseFloat(view.getComputedStyle(doc.querySelector("main")).paddingBottom),
    nav: box(doc.querySelector("nav")),
    message: displayed(message) ? box(message) : null,
    height: view.innerHeight,
  };
}

export default async function (app) {
  await shown(app, app.settings.rows);
  const show = measure(app);
  app.press("Target");
  await app.until(() => app.shown() === "target", "the target screen");
  const target = measure(app);
  app.fill("address", "not an address");
  app.press("Use");
  await app.until(() => app.text("message-text") !== null, "a message");
  const withMessage = measure(app);
  return {show, target, withMessage};
}
