// The operator sees the groups of the card's folders on Animations, chooses a playlist by
// its button or plays a row, and the card goes out and comes back.

import {choose, menuOf, playRow, rowOf, rows, shown, state} from "../reading.js";

function pointer(app, type, target, x, y) {
  const view = app.frame.contentWindow;
  target.dispatchEvent(new view.PointerEvent(type, {pointerId: 5, pointerType: "touch", isPrimary: true, button: 0, clientX: x, clientY: y, bubbles: true, cancelable: true}));
}

// Holds a row, waits for it to lift, drags it to a height, and lets it go there, or back
// where it began when `back` is set. Gives where the placeholder stood: the group and the
// id of the row after it, or "end" of its group.
async function drag(app, id, toY, back = false) {
  const play = rowOf(app, id).querySelector(".play");
  play.scrollIntoView({block: "center"});
  await app.sleep(100);
  const box = play.getBoundingClientRect();
  const x = box.left + 20;
  const y = box.top + box.height / 2;
  pointer(app, "pointerdown", play, x, y);
  await app.sleep(600);
  const to = toY();
  for (let step = 1; step <= 8; step += 1) {
    pointer(app, "pointermove", app.doc, x, y + (to - y) * step / 8);
    await app.sleep(30);
  }
  const placeholder = app.doc.querySelector("#animations-list > .placeholder");
  let next = placeholder === null ? null : placeholder.nextElementSibling;
  if (next !== null && Number(next.dataset.id) === id) next = next.nextElementSibling;
  const before = next !== null && next.classList.contains("row") ? Number(next.dataset.id) : "end";
  const landing = placeholder === null ? null : {group: placeholder.previousElementSibling?.dataset.group ?? null, before};
  if (back) {
    pointer(app, "pointermove", app.doc, x, y);
    await app.sleep(30);
  }
  pointer(app, "pointerup", app.doc, x, back ? y : to);
  return landing;
}

// The heads of the groups as the screen shows them, the root's first: the path, the id,
// the heading's text, whether it is on the screen, whether it is marked as the current
// playlist's, and its button's name.
function heads(app) {
  return [...app.doc.querySelectorAll("#root-head, #animations-list > .folder-head")].map((head) => ({
    group: head.dataset.group ?? "",
    id: head.dataset.id === undefined ? null : Number(head.dataset.id),
    title: head.querySelector("h2").textContent,
    shown: head.getClientRects().length > 0,
    marked: head.getAttribute("aria-current") === "true",
    button: head.querySelector("button").getAttribute("aria-label") || head.querySelector("button").textContent.trim(),
  }));
}

function groupedRows(app) {
  return rows(app).map((row) => ({...row, group: app.doc.querySelector(`#animations-list > .row[data-id="${row.id}"]`).dataset.group}));
}

function seen(app) {
  return {
    ...state(app),
    heads: heads(app),
    rows: groupedRows(app),
    tests: app.byId("tests").hidden ? null : [...app.doc.querySelectorAll("#tests-grid button")].filter((button) => button.getClientRects().length > 0).length,
    testsHead: app.byId("tests").hidden ? null : app.text("tests-toggle"),
    buttons: [...app.doc.querySelectorAll("#animations button")].filter((button) => button.getClientRects().length > 0).map((button) => button.getAttribute("aria-label") || button.textContent.trim()),
  };
}

export default async function (app) {
  const settings = app.settings;
  await shown(app, settings.rows);
  if (settings.heads !== undefined) {
    await app.until(() => heads(app).length === settings.heads, `${settings.heads} groups`, 15000);
  }
  if (settings.until !== undefined) {
    await app.until(() => app.says(settings.until), `on the screen: ${settings.until}`, 8000);
  }
  if (settings.tests) {
    app.press("Settings");
    app.byId("show-tests").click();
    app.press("Animations");
    await app.until(() => app.shown() === "animations" && !app.byId("tests").hidden, "the Tests group");
  }
  await app.sleep(settings.wait || 200);
  const found = {first: seen(app), steps: []};
  for (const step of settings.presses ?? []) {
    if (step.row !== undefined) {
      playRow(app, step.row);
    } else {
      app.pressIn(step.pressIn, "Play this folder");
    }
    await app.until(() => app.says(step.until), `on the screen: ${step.until}`, 8000);
    await app.sleep(200);
    found.steps.push(seen(app));
  }
  if (settings.menus !== undefined) {
    // The menu of each of these rows, its actions as they are offered.
    found.menus = {};
    for (const id of settings.menus) {
      found.menus[id] = menuOf(app, id);
      app.doc.dispatchEvent(new KeyboardEvent("keydown", {key: "Escape", bubbles: true}));
    }
  }
  if (settings.menu !== undefined) {
    const [id, words, expected] = settings.menu;
    menuOf(app, id);
    choose(app, words);
    await app.until(() => rows(app).map((row) => row.id).join() === expected.join(), "the order after the menu's move", 8000);
    await app.until(() => rowOf(app, id).dataset.saving !== "true", "the move saved", 8000);
    found.afterMenu = groupedRows(app);
  }
  if (settings.drag !== undefined) {
    // A row dragged to the top of another row, which may be of another group, and let go.
    const {id, to, expected} = settings.drag;
    found.landing = await drag(app, id, () => rowOf(app, to).getBoundingClientRect().top + 4);
    await app.until(() => rows(app).map((row) => row.id).join() === expected.join() && rowOf(app, id).dataset.saving !== "true", "the drag saved", 8000);
    found.afterDrag = groupedRows(app);
  }
  if (settings.back !== undefined) {
    // A row dragged away and brought back where it began: nothing moves.
    const {id, to} = settings.back;
    found.backLanding = await drag(app, id, () => rowOf(app, to).getBoundingClientRect().top + 4, true);
    await app.sleep(800);
    found.afterBack = groupedRows(app);
  }
  if (settings.filter !== undefined) {
    const [filter, words] = settings.filter;
    const buttons = [...app.doc.querySelectorAll(`#filter-${filter} button`)].filter((button) => button.textContent.trim().split(" ")[0] === words);
    buttons[0].click();
    await app.sleep(100);
    found.filtered = seen(app);
    [...app.doc.querySelectorAll(`#filter-${filter} button`)].filter((button) => button.textContent.trim().split(" ")[0] === "All")[0].click();
    await app.sleep(100);
  }
  if (settings.select) {
    app.press("Select");
    app.press("Select all");
    found.selected = [...app.doc.querySelectorAll("#animations-list .pick input")].filter((input) => input.checked).map((input) => Number(input.closest(".row").dataset.id));
    app.press("Done");
  }
  if (settings.card) {
    // The card is pulled out, and plugged in again.
    await app.step();
    await app.until(() => heads(app).length === 1 && rows(app).length === settings.card.outRows, "the card pulled out", 15000);
    await app.sleep(200);
    found.out = seen(app);
    await app.step();
    await app.until(() => heads(app).length === settings.card.heads && app.says(settings.card.until), "the card back", 20000);
    await app.sleep(200);
    found.back = seen(app);
  }
  return found;
}
