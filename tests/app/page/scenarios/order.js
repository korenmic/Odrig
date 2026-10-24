// The operator moves animations in the saved order: by holding a row and dragging it,
// with a finger or a mouse, or with Move up and Move down in a row's menu.

import {choose, menuOf, rowOf, shown} from "../reading.js";

const ids = (app) => [...app.doc.querySelectorAll("#animations-list > .row")].map((row) => Number(row.dataset.id));

function pointer(app, type, target, kind, x, y) {
  const view = app.frame.contentWindow;
  target.dispatchEvent(new view.PointerEvent(type, {pointerId: 5, pointerType: kind, isPrimary: true, button: 0, clientX: x, clientY: y, bubbles: true, cancelable: true}));
}

// Holds a row, waits for it to lift, and drags it to a height; then lets go, or moves it
// back where it began and lets go there when `back` is set.
async function drag(app, id, toY, kind, seen, back = false) {
  const play = rowOf(app, id).querySelector(".play");
  play.scrollIntoView({block: "center"});
  await app.sleep(100);
  const box = play.getBoundingClientRect();
  const x = box.left + 20;
  const y = box.top + box.height / 2;
  pointer(app, "pointerdown", play, kind, x, y);
  await app.sleep(600);
  seen.lifted = app.doc.querySelector("#animations-list > .row.lifted") !== null;
  const to = typeof toY === "function" ? toY() : toY;
  for (let step = 1; step <= 8; step += 1) {
    pointer(app, "pointermove", app.doc, kind, x, y + (to - y) * step / 8);
    await app.sleep(30);
  }
  seen.placeholder = app.doc.querySelector("#animations-list > .placeholder") !== null;
  if (back) {
    pointer(app, "pointermove", app.doc, kind, x, y);
    await app.sleep(30);
  }
  pointer(app, "pointerup", app.doc, kind, x, back ? y : to);
}

export default async function (app) {
  const settings = app.settings;
  await shown(app, settings.rows);
  const client = await app.frame.contentWindow.eval('import("/client.js")');
  await app.until(() => client.state.order !== null || !client.state.orderKnown, "the saved order");
  const seen = {first: ids(app), note: app.text("order-note")};
  if (settings.older) {
    seen.menu = menuOf(app, seen.first[0]);
    return seen;
  }
  if (settings.drag) {
    const target = () => rowOf(app, settings.drag.before).getBoundingClientRect().top + 4;
    await drag(app, settings.drag.id, target, settings.drag.kind, seen);
    seen.saving = rowOf(app, settings.drag.id).querySelector(".row-state").textContent;
    await app.until(() => ids(app).join() === settings.drag.expected.join() && rowOf(app, settings.drag.id).dataset.saving !== "true", "the moved order saved", 8000);
    seen.after = ids(app);
    seen.played = client.state.status.animation;
  }
  if (settings.back) {
    const before = ids(app);
    await drag(app, before[1], () => rowOf(app, before[3]).getBoundingClientRect().top + 4, "touch", seen, true);
    await app.sleep(800);
    seen.unmoved = ids(app).join() === before.join();
  }
  if (settings.cancel) {
    const before = ids(app);
    const play = rowOf(app, before[0]).querySelector(".play");
    const box = play.getBoundingClientRect();
    pointer(app, "pointerdown", play, "touch", box.left + 20, box.top + 10);
    await app.sleep(600);
    pointer(app, "pointermove", app.doc, "touch", box.left + 20, box.top + 160);
    pointer(app, "pointercancel", app.doc, "touch", box.left + 20, box.top + 160);
    await app.sleep(800);
    seen.cancelled = ids(app).join() === before.join() && app.doc.querySelector(".placeholder, .row.lifted") === null;
  }
  if (settings.toEnd) {
    // A long list: the first row is dragged to the tabs, the page scrolls on to its end,
    // and it is let go there.
    const id = seen.first[0];
    const play = rowOf(app, id).querySelector(".play");
    play.scrollIntoView({block: "center"});
    await app.sleep(100);
    const box = play.getBoundingClientRect();
    pointer(app, "pointerdown", play, settings.kind, box.left + 20, box.top + 10);
    await app.sleep(600);
    const near = app.doc.querySelector("nav").getBoundingClientRect().top - 20;
    for (let step = 1; step <= 6; step += 1) {
      pointer(app, "pointermove", app.doc, settings.kind, box.left + 20, box.top + 10 + (near - box.top - 10) * step / 6);
      await app.sleep(30);
    }
    const scrolledFrom = app.frame.contentWindow.scrollY;
    await app.until(() => app.frame.contentWindow.innerHeight + app.frame.contentWindow.scrollY >= app.doc.documentElement.scrollHeight - 2, "the page scrolled to its end", 12000);
    seen.scrolled = app.frame.contentWindow.scrollY - scrolledFrom;
    await app.sleep(200);
    pointer(app, "pointerup", app.doc, settings.kind, box.left + 20, near);
    await app.until(() => ids(app)[ids(app).length - 1] === id && rowOf(app, id).dataset.saving !== "true", "the first row saved last", 8000);
    seen.after = ids(app);
  }
  if (settings.menu) {
    const [id, words, expected] = settings.menu;
    seen.menu = menuOf(app, id);
    choose(app, words);
    await app.until(() => ids(app).join() === expected.join(), "the order after the menu's move", 8000);
    await app.until(() => rowOf(app, id).dataset.saving !== "true", "the move saved", 8000);
    seen.after = ids(app);
  }
  if (settings.refused) {
    const id = seen.first[1];
    menuOf(app, id);
    choose(app, "Move up");
    seen.saving = rowOf(app, id).querySelector(".row-state").textContent;
    await app.until(() => app.text("message-text") !== null, "a message", 8000);
    seen.message = app.text("message-text");
    const version = client.state.orderVersion;
    await app.until(() => client.state.orderVersion > version || rowOf(app, id).dataset.saving !== "true", "the order read again", 8000);
    await app.sleep(1000);
    seen.after = ids(app);
  }
  if (settings.blocked) {
    app.press("Select");
    seen.selecting = {note: app.text("order-note"), menu: menuOf(app, seen.first[1])};
    app.doc.dispatchEvent(new KeyboardEvent("keydown", {key: "Escape", bubbles: true}));
    const play = rowOf(app, seen.first[1]).querySelector(".play");
    const box = play.getBoundingClientRect();
    pointer(app, "pointerdown", play, "touch", box.left + 20, box.top + 10);
    await app.sleep(600);
    seen.selecting.lifted = app.doc.querySelector(".row.lifted") !== null;
    pointer(app, "pointerup", app.doc, "touch", box.left + 20, box.top + 10);
    app.press("Done");
    await app.sleep(100);
    seen.done = app.text("order-note");
  }
  if (settings.other) {
    await app.step();
    await app.until(() => ids(app).join() === settings.other.join(), "the other controller's order", 14000);
    seen.after = ids(app);
  }
  return seen;
}
