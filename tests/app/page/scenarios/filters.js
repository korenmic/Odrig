// The operator narrows the list of Animations with the filters by storage and by type.

import {menuOf, rowOf, rows, shown} from "../reading.js";

const ids = (app) => rows(app).map((row) => row.id);

// The choices of a filter as the screen shows them: the words and the number of each, and
// the one that is chosen.
function choices(app, filter) {
  const buttons = [...app.doc.querySelectorAll(`#filter-${filter} button`)];
  return {
    shown: buttons.map((button) => button.textContent.trim()),
    chosen: buttons.filter((button) => button.getAttribute("aria-pressed") === "true").map((button) => button.textContent.trim().split(" ")[0]),
  };
}

function choose(app, filter, words) {
  const found = [...app.doc.querySelectorAll(`#filter-${filter} button`)].filter((button) => button.textContent.trim().split(" ")[0] === words);
  if (found.length !== 1) {
    throw new Error(`${found.length} choices of ${filter} say ${words}`);
  }
  found[0].click();
}

export default async function (app) {
  const settings = app.settings;
  await shown(app, settings.rows);
  await app.until(() => !app.byId("filters").hidden, "the filters");
  const seen = {first: {storage: choices(app, "storage"), type: choices(app, "type"), rows: ids(app)}, combinations: {}};
  if (settings.every) {
    for (const storage of ["All", "Internal", "External"]) {
      for (const type of ["All", "Normal", "Text", "Widget"]) {
        choose(app, "storage", storage);
        choose(app, "type", type);
        await app.sleep(50);
        seen.combinations[`${storage} ${type}`] = {rows: ids(app), storage: choices(app, "storage").shown, type: choices(app, "type").shown,
          empty: app.text("filter-empty"), none: app.text("none")};
      }
    }
    choose(app, "storage", "External");
    choose(app, "type", "Widget");
    await app.sleep(50);
    seen.emptyBefore = app.text("filter-empty");
    app.press("Show all");
    await app.sleep(50);
    seen.reset = {rows: ids(app), storage: choices(app, "storage").chosen, type: choices(app, "type").chosen, empty: app.text("filter-empty")};
  }
  if (settings.kept) {
    choose(app, "storage", "Internal");
    choose(app, "type", "Normal");
    await app.reload();
    await app.until(() => app.shown() === "animations" && !app.byId("filters").hidden && rows(app).length > 0, "the filters after a reload", 8000);
    await app.sleep(200);
    seen.kept = {storage: choices(app, "storage").chosen, type: choices(app, "type").chosen, rows: ids(app)};
    choose(app, "storage", "All");
    choose(app, "type", "All");
  }
  if (settings.moving) {
    choose(app, "storage", "Internal");
    await app.sleep(50);
    seen.note = app.text("order-note");
    seen.menu = menuOf(app, ids(app)[1]);
    app.doc.dispatchEvent(new KeyboardEvent("keydown", {key: "Escape", bubbles: true}));
    const play = rowOf(app, ids(app)[1]).querySelector(".play");
    const box = play.getBoundingClientRect();
    const view = app.frame.contentWindow;
    play.dispatchEvent(new view.PointerEvent("pointerdown", {pointerId: 3, pointerType: "touch", isPrimary: true, clientX: box.left + 20, clientY: box.top + 10, bubbles: true}));
    await app.sleep(600);
    seen.lifted = app.doc.querySelector(".row.lifted") !== null;
    app.doc.dispatchEvent(new view.PointerEvent("pointerup", {pointerId: 3, pointerType: "touch", isPrimary: true, clientX: box.left + 20, clientY: box.top + 10, bubbles: true}));
    choose(app, "storage", "All");
    await app.sleep(50);
    seen.noteAll = app.text("order-note");
  }
  if (settings.selecting) {
    choose(app, "type", "Normal");
    choose(app, "storage", "Internal");
    app.pressIn("#list-head", "Select");
    app.press("Select all");
    const checked = () => [...app.doc.querySelectorAll("#animations-list .pick input")].filter((input) => input.checked).map((input) => Number(input.closest(".row").dataset.id));
    seen.selectedInternal = checked();
    choose(app, "type", "Text");
    await app.sleep(50);
    choose(app, "type", "Normal");
    await app.sleep(50);
    seen.afterHiding = checked();
    app.press("Select all");
    app.press("Delete selected");
    await app.until(() => app.text("confirm-text") !== null, "the question");
    seen.question = app.text("confirm-text");
    app.press("Keep it");
    app.press("Done");
    choose(app, "storage", "All");
    choose(app, "type", "All");
  }
  if (settings.tests) {
    app.press("Settings");
    app.byId("show-tests").click();
    app.press("Animations");
    await app.until(() => app.shown() === "animations" && !app.byId("tests").hidden, "the Tests group");
    choose(app, "storage", "External");
    choose(app, "type", "Widget");
    await app.sleep(50);
    seen.tests = [...app.doc.querySelectorAll("#tests-grid button")].filter((button) => button.getClientRects().length > 0).length;
    app.press("Show all");
  }
  if (settings.card) {
    // The card is pulled out, and plugged in again.
    await app.step();
    await app.until(() => choices(app, "storage").shown.join() === settings.card.out.join(), "the card pulled out", 15000);
    seen.out = {storage: choices(app, "storage").shown, rows: ids(app)};
    await app.step();
    await app.until(() => choices(app, "storage").shown.join() === settings.card.in.join(), "the card back", 15000);
    seen.back = {storage: choices(app, "storage").shown, rows: ids(app)};
  }
  return seen;
}
