// Where text can be marked, and where the menu of a long press or a right click is
// stopped: for every element of the page with each screen shown, with the question
// before a removal and with a message; for elements made after the app started; and on
// the page for a web view that is too old.

import {shown, storage} from "../reading.js";

// What is added to the target screen after the app started, each by its name.
const MADE = {
  text: '<input type="text">',
  number: '<input type="number">',
  untyped: "<input>",
  area: "<textarea></textarea>",
  readOnly: '<input type="text" readonly value="kept">',
  slider: '<input type="range">',
  paragraph: "<p>A line made later.</p>",
  button: '<button type="button">Made later</button>',
};

// Where an element is: the path from the nearest element with an id.
function named(element) {
  const parts = [];
  for (let at = element; at !== null; at = at.parentElement) {
    if (at.id) {
      parts.unshift(`#${at.id}`);
      break;
    }
    parts.unshift(at.localName + [...at.classList].map((name) => `.${name}`).join(""));
  }
  return parts.join(" > ");
}

// A right click on an element, as the web view sends a long press: whether it was
// stopped.
function stopped(element) {
  const view = element.ownerDocument.defaultView;
  return !element.dispatchEvent(new view.MouseEvent("contextmenu", {bubbles: true, cancelable: true, button: 2}));
}

// What an element is, whether its text can be marked, and whether a right click on it
// opens a menu.
function tried(element) {
  const view = element.ownerDocument.defaultView;
  return {
    what: named(element),
    tag: element.localName,
    kind: ["input", "textarea"].includes(element.localName) ? element.type : null,
    readOnly: element.readOnly === true || element.disabled === true,
    marks: view.getComputedStyle(element).userSelect,
    stopped: stopped(element),
  };
}

// What the browser's "select all" marks with no field in focus.
function selected(doc) {
  if (doc.activeElement !== null) {
    doc.activeElement.blur();
  }
  const selection = doc.getSelection();
  selection.removeAllRanges();
  doc.execCommand("selectAll");
  const marked = selection.toString();
  selection.removeAllRanges();
  return marked;
}

function look(app) {
  return {marked: selected(app.doc), elements: [...app.doc.querySelectorAll("*")].map(tried)};
}

export default async function (app) {
  await shown(app, app.settings.rows);
  const seen = {show: look(app)};
  seen.stoppedBeforePress = stopped(app.byId("to-storage"));
  app.press("Storage");
  await app.until(() => app.shown() === "storage" && app.text("space") !== "-" && storage(app).rows.length === app.settings.rows, "the storage screen with its rows");
  seen.storage = look(app);
  app.pressIn("#installed > .row", "Remove");
  await app.until(() => app.text("confirm-text") !== null, "the question");
  seen.question = look(app);
  app.press("Keep it");
  app.press("Target");
  await app.until(() => app.shown() === "target", "the target screen");
  seen.target = look(app);
  app.fill("address", "not an address");
  app.press("Use");
  await app.until(() => app.text("message-text") !== null, "a message");
  seen.message = look(app);
  seen.made = {};
  for (const [name, html] of Object.entries(MADE)) {
    const place = app.byId("target");
    place.insertAdjacentHTML("beforeend", html);
    seen.made[name] = tried(place.lastElementChild);
  }
  const old = new Promise((resolve) => app.frame.addEventListener("load", resolve, {once: true}));
  app.frame.src = "/old.html";
  await old;
  seen.old = look(app);
  return seen;
}
