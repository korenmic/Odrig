// The test animations: the Tests group above the list, shown when Settings says so, with
// the diagonal and one test for each of the twenty snakes; and the test that shows on the
// target, named in the now-playing area with a button that stops it.

import * as client from "../client.js";
import {Refusal} from "../commands.js";
import {Failure} from "../target.js";
import * as messages from "../messages.js";

const SHOWN_KEY = "odrig.tests";
const OPEN_KEY = "odrig.tests.open";
const SNAKES = 20;
// How often the target is asked which test shows, while one may.
const ASK_EVERY_MS = 2000;

// What the newest `mapping get` said: whether a test shows and which, and whether the
// mapping is the twenty-snake installation's; null while nothing is known. `supported` is
// false for a target without the mapping commands.
let test = null;
let editable = null;
let supported = true;
let asking = false;
let askedAt = -Infinity;
let sending = false;
let version = -1;
let message = () => {};
let isVisible = () => false;

function byId(id) {
  return document.getElementById(id);
}

function kept(key, otherwise) {
  try {
    const value = window.localStorage.getItem(key);
    return value === null ? otherwise : value === "1";
  } catch (error) {
    return otherwise;
  }
}

function keep(key, value) {
  try {
    window.localStorage.setItem(key, value ? "1" : "0");
  } catch (error) {
    // A web view without storage forgets the choice at the next start.
  }
}

// Whether Settings says to show the test animations: off at first.
export function shown() {
  return kept(SHOWN_KEY, false);
}

function name(snake) {
  return snake === 0 ? "Diagonal" : `Snake ${snake}`;
}

// The test that shows, by its entry: 0 for the diagonal, n for snake n, or null. While
// something plays no test shows, whoever played it.
function active(state) {
  if (test === null || !test.test || (state.status !== null && state.status.playing !== null)) return null;
  return test.snake === null ? 0 : test.snake;
}

// Asks the target which test shows, and whether its mapping takes the tests.
async function ask() {
  if (asking) return;
  const asked = client.targetVersion();
  asking = true;
  try {
    const reply = await client.mappingGet();
    if (asked !== client.targetVersion()) return;
    test = reply;
    editable = reply.editable;
    supported = true;
  } catch (error) {
    if (asked !== client.targetVersion()) return;
    if (error instanceof Refusal && error.code === "unknown-command") {
      supported = false;
      test = null;
    }
  } finally {
    asking = false;
    askedAt = performance.now();
    draw(client.state);
  }
}

// Whether a test may show now: every test leaves the target with nothing playing on a
// valid show. While something plays, none does.
function mayShow(state) {
  return state.status !== null && state.status.error === null && state.status.playing === null;
}

async function sendTest(carry) {
  if (sending) return;
  const asked = client.targetVersion();
  sending = true;
  draw(client.state);
  try {
    await carry();
  } catch (error) {
    if (asked === client.targetVersion()) {
      if (error instanceof Refusal) message(messages.ofRefusal(error));
      else if (error instanceof Failure) message(messages.ofFailure(error));
      else message("No confirmed reply. The installation is asked which test shows.");
    }
  } finally {
    sending = false;
    if (asked === client.targetVersion()) {
      await ask();
    }
  }
}

function startTest(snake) {
  sendTest(() => (snake === 0 ? client.mappingTest(true) : client.mappingTestSnake(snake)));
}

function grid() {
  const place = byId("tests-grid");
  if (place.children.length === SNAKES + 1) return;
  place.replaceChildren(...Array.from({length: SNAKES + 1}, (_, snake) => {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "test";
    button.dataset.snake = String(snake);
    button.textContent = name(snake);
    button.addEventListener("click", () => startTest(snake));
    return button;
  }));
}

export function draw(state) {
  if (version !== client.targetVersion()) {
    version = client.targetVersion();
    test = null;
    editable = null;
    supported = true;
    askedAt = -Infinity;
  }
  const on = active(state);
  const group = shown();
  byId("tests").hidden = !group;
  byId("show-tests").checked = group;
  const open = kept(OPEN_KEY, true);
  byId("tests-toggle").setAttribute("aria-expanded", String(open));
  byId("tests-body").hidden = !open;
  grid();
  const answers = state.link === "answers";
  let note = "Manual tests through the saved mapping. They never play by themselves.";
  if (!supported) note = "This installation's software has no test animations.";
  else if (editable === false) note = "These tests need the 60 \u00d7 60 installation of twenty three-column snakes; this installation's mapping is another one.";
  if (state.status?.clockMode === "only") note = "Leave Clocks only in Settings before starting a display test.";
  byId("tests-note").textContent = note;
  for (const button of byId("tests-grid").children) {
    const snake = Number(button.dataset.snake);
    button.setAttribute("aria-pressed", String(on === snake));
    button.disabled = !answers || sending || !supported || editable !== true || state.status?.clockMode === "only";
  }
  byId("test-now").hidden = on === null;
  byId("test-now-text").textContent = on === null ? "" : `Test: ${name(on)} is showing. Normal playback is paused.`;
  byId("stop-test").disabled = !answers || sending;
}

export function start(options) {
  message = options.message;
  isVisible = options.isVisible;
  byId("show-tests").addEventListener("change", () => {
    keep(SHOWN_KEY, byId("show-tests").checked);
    askedAt = -Infinity;
    draw(client.state);
  });
  byId("tests-toggle").addEventListener("click", () => {
    keep(OPEN_KEY, !kept(OPEN_KEY, true));
    draw(client.state);
  });
  byId("stop-test").addEventListener("click", () => sendTest(() => client.mappingTest(false)));
  // The target is asked which test shows while one may, and what its mapping takes while
  // the group is shown and that is not known yet; never while the app is away.
  setInterval(() => {
    const state = client.state;
    if (document.hidden || !isVisible() || state.link !== "answers" || state.status === null) return;
    const due = mayShow(state) || (shown() && editable === null && supported);
    if (due && performance.now() - askedAt >= ASK_EVERY_MS) ask();
  }, 250);
}
