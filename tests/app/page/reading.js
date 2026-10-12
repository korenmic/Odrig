// What a scenario reads off the show screen.

// The rows of the list: the id and the words of each, and whether it is marked.
export function rows(app) {
  return [...app.doc.querySelectorAll("#animations > *")].map((row) => ({
    id: Number(row.dataset.id),
    text: row.innerText.replace(/\s+/g, " ").trim(),
    marked: row.getAttribute("aria-current") === "true",
  }));
}

// The state as the screen says it, each line or null when it is not shown.
export function state(app) {
  return {
    power: app.text("power"),
    brightness: app.text("brightness"),
    playing: app.text("playing"),
    now: app.text("now"),
    fps: app.text("fps"),
    none: app.text("none"),
    silent: app.text("silent"),
    why: app.text("silent-why"),
    dimmed: app.byId("state").classList.contains("stale"),
  };
}

// The controls as the screen shows them: which of `On` and `Off` is marked, and where
// the slider stands.
export function controls(app) {
  return {
    on: app.byId("on").getAttribute("aria-pressed") === "true",
    off: app.byId("off").getAttribute("aria-pressed") === "true",
    slider: Number(app.byId("level").value),
    number: app.text("level-number"),
  };
}

// Waits for the show screen with a status and with the rows a test expects.
export async function shown(app, count) {
  await app.until(() => app.shown() === "show", "the show screen is shown");
  await app.until(() => app.text("power") !== "-" && rows(app).length === count, `a status and ${count} rows`, 8000);
}
