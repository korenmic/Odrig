// Settings' panel of the current limits: its rows, the reads every two seconds, the saves
// of changed text when a field is entered or left, the range, the refusals, the warnings,
// the marks of a dimmed wall or snake, a field with the focus or text not saved, and an
// installation whose software has no limits.
import {shown} from "../reading.js";

const SNAKES = Array.from({length: 20}, (_, at) => String(at + 1));

function displayed(element) {
  return element !== null && element.getClientRects().length > 0;
}

const fieldOf = (app, key) => app.doc.getElementById(key === "wall" ? "limits-wall-budget" : `limits-snake-${key}`);
const rowOf = (app, key) => app.doc.querySelector(`#limits .limit[data-key="${key}"]`);
const idOf = (key) => (key === "wall" ? "limits-wall-budget" : `limits-snake-${key}`);

// What the row of a key says under its field, or null.
function saidOf(app, key) {
  const row = rowOf(app, key);
  const line = row === null ? null : row.querySelector(".limit-said");
  return displayed(line) ? line.textContent : null;
}

// The rows of the panel as they show: each key's label, field, placeholder, estimate,
// whether it is marked dimmed and whether it has the warning of the lowest level.
function panel(app) {
  const rows = [...app.doc.querySelectorAll("#limits .limit")].filter(displayed);
  return {
    keys: rows.map((row) => row.dataset.key),
    labels: rows.map((row) => row.querySelector("label").textContent),
    values: Object.fromEntries(rows.map((row) => [row.dataset.key, row.querySelector("input").value])),
    placeholders: [...new Set(rows.map((row) => row.querySelector("input").placeholder))],
    estimates: rows.map((row) => row.querySelector(".limit-figure").textContent),
    dimmed: rows.filter((row) => displayed(row.querySelector(".limit-dimmed"))).map((row) => row.dataset.key),
    marks: [...new Set(rows.filter((row) => displayed(row.querySelector(".limit-dimmed"))).map((row) => row.querySelector(".limit-dimmed").textContent))],
    warnings: rows.filter((row) => displayed(row.querySelector(".limit-warning"))).map((row) => row.dataset.key),
    warning: [...new Set(rows.filter((row) => displayed(row.querySelector(".limit-warning"))).map((row) => row.querySelector(".limit-warning").textContent))],
    inputs: [...app.doc.querySelectorAll("#limits input")].filter(displayed).length,
    defaults: app.text("limits-default"),
    summary: app.text("limits-summary"),
    explanation: displayed(app.doc.querySelector("#limits > p.small")) ? app.doc.querySelector("#limits > p.small").textContent : null,
    heading: app.text("limits") === null ? null : app.doc.querySelector("#limits h2").textContent,
  };
}

// Writes text into a field and saves it as the operator does: by leaving the field, or by
// pressing Enter in it.
function enter(app, key, text, how = "leave") {
  app.fill(idOf(key), text);
  if (how === "enter") {
    fieldOf(app, key).dispatchEvent(new (app.frame.contentWindow.KeyboardEvent)("keydown", {key: "Enter", bubbles: true, cancelable: true}));
  } else {
    app.release(idOf(key));
  }
}

// Waits until the row of a key says what a save ended with.
async function answered(app, key) {
  await app.until(() => saidOf(app, key) !== null && saidOf(app, key) !== "Saving\u2026", `the save of ${key} answered`, 12000);
  return saidOf(app, key);
}

async function opened(app, snakes) {
  await shown(app, 2);
  app.press("Settings");
  await app.until(() => app.shown() === "settings", "Settings");
  await app.until(() => fieldOf(app, "wall") !== null && (!snakes || SNAKES.every((key) => fieldOf(app, key) !== null)), "the fields of the current limits");
}

// Against the emulator: the panel as it opens, a save of each kind, and a change made
// elsewhere while a field has the focus and text not saved.
async function emulator(app) {
  await opened(app, true);
  const seen = {first: panel(app)};
  enter(app, "wall", "2000");
  seen.wallSaid = await answered(app, "wall");
  seen.afterWall = panel(app);
  enter(app, "1", "100", "enter");
  seen.oneSaid = await answered(app, "1");
  await app.until(() => panel(app).dimmed.includes("1"), "snake 1 marked dimmed", 8000);
  seen.afterOne = panel(app);
  enter(app, "1", "");
  seen.emptied = await answered(app, "1");
  seen.afterEmptied = panel(app);
  enter(app, "2", "70000");
  seen.range = saidOf(app, "2");
  seen.rangeValue = fieldOf(app, "2").value;
  // Snake 3's field has the focus and text not saved while snakes 3 and 4 are changed
  // elsewhere: the reads change snake 4's field and not snake 3's.
  fieldOf(app, "3").focus();
  app.fill("limits-snake-3", "123");
  await app.step();
  await app.until(() => panel(app).values["4"] === "150", "snake 4 read again", 8000);
  await app.sleep(2500);
  seen.focusKept = app.doc.activeElement === fieldOf(app, "3");
  seen.textKept = fieldOf(app, "3").value;
  seen.whileTyping = panel(app);
  fieldOf(app, "3").blur();
  app.release("limits-snake-3");
  seen.threeSaid = await answered(app, "3");
  enter(app, "wall", "5000");
  seen.wallAgain = await answered(app, "wall");
  await app.until(() => panel(app).dimmed.includes("3") && panel(app).dimmed.includes("4"), "snakes 3 and 4 marked dimmed", 8000);
  seen.last = panel(app);
  return seen;
}

// Against a stand-in: the reads in parts every two seconds, and which text is sent.
async function lines(app) {
  await opened(app, true);
  const seen = {first: panel(app)};
  await app.sleep(6500);
  enter(app, "wall", "0730");
  await app.sleep(300);
  seen.equal = {value: fieldOf(app, "wall").value, said: saidOf(app, "wall")};
  enter(app, "wall", "250001");
  seen.wallRange = {value: fieldOf(app, "wall").value, said: saidOf(app, "wall")};
  enter(app, "2", "65536");
  seen.snakeRange = {value: fieldOf(app, "2").value, said: saidOf(app, "2")};
  enter(app, "5", "");
  await app.sleep(300);
  seen.emptyAtZero = saidOf(app, "5");
  enter(app, "3", "");
  seen.emptied = await answered(app, "3");
  seen.afterEmptied = panel(app);
  enter(app, "wall", "2000");
  seen.wall = await answered(app, "wall");
  seen.afterWall = panel(app);
  enter(app, "4", "180", "enter");
  seen.atCount = await answered(app, "4");
  seen.afterAtCount = panel(app);
  enter(app, "4", "181");
  seen.aboveCount = await answered(app, "4");
  seen.afterAboveCount = panel(app);
  return seen;
}

// Against a stand-in whose saves are answered slowly.
async function slow(app) {
  await opened(app, true);
  enter(app, "1", "500");
  await app.until(() => saidOf(app, "1") === "Saving\u2026", "the save under way");
  await app.sleep(1500);
  const seen = {during: {said: saidOf(app, "1"), value: fieldOf(app, "1").value}};
  seen.said = await answered(app, "1");
  await app.sleep(2000);
  seen.value = fieldOf(app, "1").value;
  return seen;
}

// Against a stand-in whose reads are slow: the reads for some seconds; then snake 3's
// budget is changed elsewhere while its field has the focus, Enter is pressed with its text
// unchanged, and the field is left.
async function stale(app) {
  await opened(app, true);
  await app.sleep(9000);
  fieldOf(app, "3").focus();
  await app.step();
  await app.until(() => !panel(app).warnings.includes("3"), "snake 3's budget read again", 8000);
  const seen = {focused: {value: fieldOf(app, "3").value, focus: app.doc.activeElement === fieldOf(app, "3")}};
  fieldOf(app, "3").dispatchEvent(new (app.frame.contentWindow.KeyboardEvent)("keydown", {key: "Enter", bubbles: true, cancelable: true}));
  await app.sleep(1500);
  seen.afterEnter = {value: fieldOf(app, "3").value, said: saidOf(app, "3")};
  fieldOf(app, "3").blur();
  await app.sleep(4500);
  seen.left = fieldOf(app, "3").value;
  return seen;
}

// Against a stand-in that refuses every save, each with another code.
async function refused(app) {
  await opened(app, true);
  const seen = {};
  for (const key of app.settings.keys) {
    enter(app, key, "50");
    const said = await answered(app, key);
    seen[key] = {said, value: fieldOf(app, key).value, problem: rowOf(app, key).querySelector(".limit-said").classList.contains("problem")};
  }
  await app.sleep(2500);
  seen.later = panel(app).values;
  return seen;
}

// Against a stand-in whose software has no limits, then another target with limits and a
// mapping that is not the twenty snakes.
async function none(app) {
  await shown(app, 2);
  app.press("Settings");
  await app.until(() => app.shown() === "settings", "Settings");
  await app.until(() => app.says("This installation's software has no current limits\\."), "no current limits said");
  await app.sleep(4500);
  const seen = {without: panel(app)};
  app.press("Target");
  app.fill("address", app.settings.other);
  app.press("Use");
  await app.until(() => app.shown() === "animations", "the other target answers");
  app.press("Settings");
  await app.until(() => fieldOf(app, "wall") !== null && displayed(fieldOf(app, "wall")), "the wall's field of the other target");
  await app.sleep(2500);
  seen.other = panel(app);
  return seen;
}

export default async function (app) {
  const modes = {emulator, lines, slow, stale, refused, none};
  return modes[app.settings.mode || "emulator"](app);
}
