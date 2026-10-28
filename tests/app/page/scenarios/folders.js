// The operator walks the card's folders on Animations as a file explorer: enters a
// folder, goes back, chooses a playlist by the level's button or plays a row, moves and
// selects within the level, and the card goes out and comes back.

import {choose, menuOf, playRow, rowOf, rows, shown, state} from "../reading.js";

function pointer(app, type, target, x, y) {
  const view = app.frame.contentWindow;
  target.dispatchEvent(new view.PointerEvent(type, {pointerId: 5, pointerType: "touch", isPrimary: true, button: 0, clientX: x, clientY: y, bubbles: true, cancelable: true}));
}

// Holds a row, waits for it to lift, drags it to a height, and lets it go there, or back
// where it began when `back` is set. Gives where the placeholder stood: the row after it,
// or "end" of the level.
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
  const landing = placeholder === null ? null : {lifted: app.doc.querySelector("#animations-list > .row.lifted") !== null, before};
  if (back) {
    pointer(app, "pointermove", app.doc, x, y);
    await app.sleep(30);
  }
  pointer(app, "pointerup", app.doc, x, back ? y : to);
  return landing;
}

const displayed = (element) => element.getClientRects().length > 0;

// The folder rows of the level shown: the path, the id, the name, the count line and
// whether the row is marked as leading to the current playlist.
function folderRows(app) {
  return [...app.doc.querySelectorAll("#animations-list > .folder-row")].map((row) => ({
    path: row.dataset.path,
    id: Number(row.dataset.id),
    name: row.querySelector(".name").textContent,
    meta: row.querySelector(".meta").textContent,
    marked: row.getAttribute("aria-current") === "true",
    shown: displayed(row),
  }));
}

// The level's head: its title, whether Back is shown, whether it is marked, its button.
function levelOf(app) {
  const back = app.byId("level-back");
  return {title: app.text("level-title"), back: displayed(back), marked: app.byId("level-head").getAttribute("aria-current") === "true", button: app.text("play-all")};
}

function groupedRows(app) {
  return rows(app).map((row) => ({...row, group: app.doc.querySelector(`#animations-list > .row[data-id="${row.id}"]`).dataset.group}));
}

function seen(app) {
  return {
    ...state(app),
    level: levelOf(app),
    rows: groupedRows(app),
    folders: folderRows(app),
    filterEmpty: app.text("filter-empty"),
    orderNote: app.raw("order-note"),
    tests: app.byId("tests").hidden ? null : [...app.doc.querySelectorAll("#tests-grid button")].filter(displayed).length,
    testsHead: app.byId("tests").hidden ? null : app.text("tests-toggle"),
    buttons: [...app.doc.querySelectorAll("#animations button")].filter(displayed).map((button) => button.getAttribute("aria-label") || button.textContent.trim()),
  };
}

function enter(app, path) {
  const found = app.doc.querySelector(`#animations-list > .folder-row[data-path="${path}"]`);
  if (found === null) {
    throw new Error(`no folder row ${path}`);
  }
  found.click();
}

// Waits for the level a step names, and for its rows when the step counts them: up to
// the list's refresh after a card went out or came in.
async function settled(app, step) {
  if (step.level !== undefined) {
    await app.until(() => app.text("level-title") === step.level, `the level ${step.level}`, 25000);
  }
  if (step.rows !== undefined) {
    await app.until(() => rows(app).length === step.rows, `${step.rows} rows`, 25000);
  }
  if (step.until !== undefined) {
    await app.until(() => app.says(step.until), `on the screen: ${step.until}`, 25000);
  }
  await app.sleep(step.wait === undefined ? 200 : step.wait);
}

export default async function (app) {
  const settings = app.settings;
  await shown(app, settings.rows);
  if (settings.folders !== undefined) {
    await app.until(() => folderRows(app).length === settings.folders, `${settings.folders} folder rows`, 15000);
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
  for (const step of settings.steps ?? []) {
    if (step.enter !== undefined) {
      enter(app, step.enter);
    } else if (step.back) {
      app.press("Back");
    } else if (step.top) {
      app.pressIn("#level-head", "Play this folder");
    } else if (step.row !== undefined) {
      playRow(app, step.row);
    } else if (step.menus !== undefined) {
      // The menu of each of these rows, its actions as they are offered.
      const menus = {};
      for (const id of step.menus) {
        menus[id] = menuOf(app, id);
        app.doc.dispatchEvent(new KeyboardEvent("keydown", {key: "Escape", bubbles: true}));
      }
      found.steps.push({menus});
      continue;
    } else if (step.menu !== undefined) {
      const [id, words, expected] = step.menu;
      menuOf(app, id);
      choose(app, words);
      await app.until(() => rows(app).map((row) => row.id).join() === expected.join(), "the order after the menu's move", 8000);
      await app.until(() => rowOf(app, id).dataset.saving !== "true", "the move saved", 8000);
    } else if (step.drag !== undefined) {
      // A row dragged to the top of another row, or to the bottom of the list, and let go.
      const {id, to, expected} = step.drag;
      const target = to === "bottom" ? () => app.byId("animations-list").getBoundingClientRect().bottom - 4 : () => rowOf(app, to).getBoundingClientRect().top + 4;
      const landing = await drag(app, id, target);
      await app.until(() => rows(app).map((row) => row.id).join() === expected.join() && rowOf(app, id).dataset.saving !== "true", "the drag saved", 8000);
      found.steps.push({landing, ...seen(app)});
      continue;
    } else if (step.back_drag !== undefined) {
      // A row dragged away and brought back where it began: nothing moves.
      const {id, to} = step.back_drag;
      const landing = await drag(app, id, () => rowOf(app, to).getBoundingClientRect().top + 4, true);
      await app.sleep(800);
      found.steps.push({landing, ...seen(app)});
      continue;
    } else if (step.filter !== undefined) {
      const [filter, words] = step.filter;
      [...app.doc.querySelectorAll(`#filter-${filter} button`)].filter((button) => button.textContent.trim().split(" ")[0] === words)[0].click();
      await app.sleep(100);
      found.steps.push({...seen(app), filters: {
        storage: [...app.doc.querySelectorAll("#filter-storage button")].map((button) => button.textContent.trim()),
        type: [...app.doc.querySelectorAll("#filter-type button")].map((button) => button.textContent.trim()),
      }});
      continue;
    } else if (step.select !== undefined) {
      // Select all at this level: the rows checked on the screen, and which of these ids
      // the selection holds, shown or not.
      const selection = await app.frame.contentWindow.eval('import("/screens/selection.js")');
      if (app.byId("select-mode").disabled) {
        // Nothing of this level can be selected: Select is off.
        found.steps.push({selected: [], held: step.select.filter((id) => selection.has(id)), offered: false, ...seen(app)});
        continue;
      }
      app.pressIn("#list-head", "Select");
      const selectAll = app.byId("select-all");
      if (!selectAll.disabled) app.press("Select all");
      const selected = [...app.doc.querySelectorAll("#animations-list .pick input")].filter((input) => input.checked).map((input) => Number(input.closest(".row").dataset.id));
      const held = step.select.filter((id) => selection.has(id));
      const offered = !selectAll.disabled;
      app.press("Done");
      found.steps.push({selected, held, offered, ...seen(app)});
      continue;
    } else if (step.step) {
      // The card is pulled out, or plugged in again, by the test.
      await app.step();
    }
    await settled(app, step);
    found.steps.push(seen(app));
  }
  return found;
}
