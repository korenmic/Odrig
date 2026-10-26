// The operator sees the groups of the card's folders on Animations, chooses a playlist by
// its button or plays a row, and the card goes out and comes back.

import {playRow, rows, shown, state} from "../reading.js";

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
