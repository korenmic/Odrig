// What a scenario reads off the screens of the app, and the presses it makes on a row.

// The rows of the list of Animations: the id and the file of each, as `<id> <file>`, and
// whether it is marked as the one on the LEDs.
export function rows(app) {
  return [...app.doc.querySelectorAll("#animations-list > .row")].map((row) => ({
    id: Number(row.dataset.id),
    text: `${row.dataset.id} ${row.dataset.file}`,
    marked: row.getAttribute("aria-current") === "true",
  }));
}

// The badge of each row, `in` or `ex`, with its description, and what the row says of its
// state.
export function badges(app) {
  return [...app.doc.querySelectorAll("#animations-list > .row")].map((row) => ({
    id: Number(row.dataset.id),
    badge: row.querySelector(".badge").textContent,
    described: row.querySelector(".badge").getAttribute("aria-label"),
    note: row.querySelector(".row-state").textContent,
  }));
}

// Whether the capacity lines of Animations have a reply to show.
export function spaceKnown(app) {
  const line = app.text("show-space");
  return line !== null && !line.endsWith(": -");
}

// The row of an animation, by its id.
export function rowOf(app, id) {
  const found = app.doc.querySelector(`#animations-list > .row[data-id="${id}"]`);
  if (found === null) {
    throw new Error(`no row of animation ${id}`);
  }
  return found;
}

// Plays an animation as a tap on its row does.
export function playRow(app, id) {
  rowOf(app, id).querySelector(".play").click();
}

// Opens the menu of an animation's row and gives the texts of its actions.
export function menuOf(app, id) {
  rowOf(app, id).querySelector(".more").click();
  const menu = app.byId("row-menu");
  if (menu.hidden) {
    throw new Error(`the menu of animation ${id} did not open`);
  }
  return [...menu.children].map((item) => (item.localName === "button" ? `${item.textContent}${item.disabled ? " (disabled)" : ""}` : item.textContent));
}

// Starts the selection mode as a row's menu does: from the first row of the list on the
// screen whose menu offers Select, with that row ticked. Gives the row's id, or null when
// no row offers it.
export function startSelection(app) {
  for (const row of app.doc.querySelectorAll("#animations-list > .row")) {
    if (row.getClientRects().length === 0 || row.querySelector(".more").disabled) {
      continue;
    }
    const id = Number(row.dataset.id);
    if (menuOf(app, id).includes("Select")) {
      choose(app, "Select");
      return id;
    }
    app.doc.dispatchEvent(new KeyboardEvent("keydown", {key: "Escape", bubbles: true}));
  }
  return null;
}

// Presses an action of the menu that is open.
export function choose(app, words) {
  const found = [...app.byId("row-menu").querySelectorAll("button")].filter((button) => button.textContent === words);
  if (found.length !== 1) {
    throw new Error(`${found.length} actions of the menu say "${words}"`);
  }
  found[0].click();
}

// The words of the line that says what plays. The screen does not show the line; the app
// keeps its words up to date.
export function playing(app) {
  return app.raw("playing");
}

// The state as the screen says it, each line or null when it is not shown, and the words
// of the line of what plays.
export function state(app) {
  return {
    power: app.text("power"),
    brightness: app.text("brightness"),
    playing: playing(app),
    now: app.text("now"),
    fps: app.text("fps"),
    none: app.text("none"),
    silent: app.text("silent"),
    why: app.text("silent-why"),
    dimmed: app.byId("state").classList.contains("stale"),
    internalLine: app.text("show-space"),
    externalLine: app.text("show-external-space"),
  };
}

// The controls as the screen shows them: whether the power icon is pressed, which says
// that the LEDs are on, where the slider stands, and the text of the brightness field, or
// null while it is not shown.
export function controls(app) {
  const field = app.byId("level-number");
  return {
    lit: app.byId("power-toggle").getAttribute("aria-pressed") === "true",
    slider: Number(app.byId("level").value),
    number: field.getClientRects().length > 0 ? field.value : null,
  };
}

// What the list says of the storage: the two capacity lines, and the rows with the id,
// the file and the size of each and the actions of its menu, or null for a line that is
// not shown.
export function storage(app) {
  return {
    space: app.text("show-space"),
    externalSpace: app.text("show-external-space"),
    rows: [...app.doc.querySelectorAll("#animations-list > .row")].map((row) => ({
      id: Number(row.dataset.id),
      text: `${row.dataset.id} ${row.dataset.file} ${row.querySelector(".meta").textContent.split(" · ")[1]}`,
      badge: row.querySelector(".badge").textContent,
    })),
    none: app.text("none"),
    dimmed: app.byId("animations-list").classList.contains("stale"),
  };
}

// Waits for Animations with a status and with the rows a test expects.
export async function shown(app, count) {
  await app.until(() => app.shown() === "animations", "Animations is shown");
  await app.until(() => app.text("power") !== "-" && rows(app).length === count, `a status and ${count} rows`, 8000);
}
