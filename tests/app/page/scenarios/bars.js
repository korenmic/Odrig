// The page with the room of the phone's bars at each side, set on the page's root as the
// app's Android shell sets it: the show and the storage screen scrolled to their tops and
// to their ends, a message, and a field while the keyboard is open.

import {shown, storage} from "../reading.js";

const SIDES = ["top", "right", "bottom", "left"];

function displayed(element) {
  return element.getClientRects().length > 0;
}

function box(element) {
  const rect = element.getBoundingClientRect();
  return {left: rect.left, top: rect.top, right: rect.right, bottom: rect.bottom};
}

// Whatever the screen shows: every element of the screen that has a box of its own.
function things(app) {
  return [...app.doc.querySelectorAll("main h1, main p, main label, main button, main input, main canvas, main #animations > *, main #installed > .row")]
    .filter((element) => displayed(element) && element.getBoundingClientRect().width > 0)
    .map((element) => ({what: element.id || element.textContent.trim().slice(0, 30) || element.tagName, ...box(element)}));
}

// What lies in the room at the top: for points across it, the element on top there, and
// the colour of the band over it.
function atTheTop(app, room) {
  const view = app.frame.contentWindow;
  const found = [];
  if (room > 0) {
    for (const part of [0.05, 0.25, 0.5, 0.75, 0.95]) {
      const element = app.doc.elementFromPoint(view.innerWidth * part, room / 2);
      found.push(element === null ? null : element.tagName.toLowerCase());
    }
  }
  const band = view.getComputedStyle(app.doc.body, "::before");
  return {found, band: {height: parseFloat(band.height) || 0, colour: band.backgroundColor, position: band.position}};
}

function measure(app, room) {
  const view = app.frame.contentWindow;
  const nav = app.doc.querySelector("nav");
  return {
    width: view.innerWidth,
    height: view.innerHeight,
    scrolled: view.scrollY,
    things: things(app),
    tabs: [...nav.querySelectorAll("button")].filter(displayed).map((button) => ({what: button.textContent.trim(), ...box(button)})),
    nav: displayed(nav) ? {...box(nav), colour: view.getComputedStyle(nav).backgroundColor} : null,
    top: atTheTop(app, room.top),
    padding: SIDES.map((side) => parseFloat(view.getComputedStyle(app.doc.querySelector("main")).getPropertyValue(`padding-${side}`))),
  };
}

function scrolled(app, to) {
  const view = app.frame.contentWindow;
  view.scrollTo(0, to === "end" ? app.doc.documentElement.scrollHeight : 0);
}

async function settle(app) {
  await app.sleep(100);
}

export default async function (app) {
  const room = app.settings.room;
  const none = {top: 0, right: 0, bottom: 0, left: 0};
  await shown(app, app.settings.rows);
  const plain = measure(app, none);
  for (const side of SIDES) {
    app.doc.documentElement.style.setProperty(`--safe-area-inset-${side}`, `${room[side]}px`);
  }
  await settle(app);
  const show = measure(app, room);
  scrolled(app, "end");
  await settle(app);
  const showEnd = {...measure(app, room), last: box(app.doc.querySelector("#animations > :last-child"))};
  scrolled(app, "top");
  app.press("Storage");
  await app.until(() => app.shown() === "storage" && app.text("space") !== "-" && storage(app).rows.length === app.settings.rows, "the storage screen with its rows");
  await settle(app);
  const storageTop = measure(app, room);
  scrolled(app, "end");
  await settle(app);
  const storageEnd = {...measure(app, room), last: box(app.doc.querySelector("#installed > .row:last-of-type"))};
  scrolled(app, "top");
  app.press("Target");
  await app.until(() => app.shown() === "target", "the target screen");
  app.fill("address", "not an address");
  app.press("Use");
  await app.until(() => app.text("message-text") !== null, "a message");
  const message = {...measure(app, room), message: box(app.byId("message"))};
  app.press("OK");
  const field = app.byId("address");
  field.focus();
  await settle(app);
  const focused = measure(app, room);
  const height = app.frame.height;
  app.frame.height = String(Math.round(Number(height) * 2 / 3));
  await app.until(() => app.frame.contentWindow.innerHeight < Number(height) * 0.7, "a lower view");
  await settle(app);
  const typing = {...measure(app, room), field: box(field), focus: app.doc.activeElement === field};
  field.blur();
  app.frame.height = height;
  await app.until(() => app.frame.contentWindow.innerHeight === Number(height), "the view's height again");
  await settle(app);
  const after = measure(app, room);
  return {plain, show, showEnd, storageTop, storageEnd, message, focused, typing, after};
}
