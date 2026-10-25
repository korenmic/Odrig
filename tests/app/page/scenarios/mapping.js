import {shown} from "../reading.js";

// The snakes in the order the column shows them, and the pin of each snake, snake 1 first.
const order = (app) => [...app.doc.querySelectorAll("#mapping-snakes > .map-snake")].map((item) => Number(item.dataset.snake));
function pins(app) {
  const places = [...app.doc.querySelectorAll("#mapping-rows .map-pins li")].map((item) => Number(item.textContent.replace("GPIO ", "")));
  const assigned = new Array(20).fill(null);
  order(app).forEach((snake, at) => {
    assigned[snake - 1] = places[at];
  });
  return assigned;
}
const handleOf = (app, snake) => app.doc.querySelector(`#mapping-snakes > .map-snake[data-snake="${snake}"] .handle`);
const cardOf = (app, snake) => app.doc.querySelector(`#mapping-snakes > .map-snake[data-snake="${snake}"]`);

function pointer(app, type, target, x, y) {
  const view = app.frame.contentWindow;
  target.dispatchEvent(new view.PointerEvent(type, {pointerId: 7, pointerType: "touch", isPrimary: true, button: 0, clientX: x, clientY: y, bubbles: true, cancelable: true}));
}

// Takes a snake by its handle, or holds its words when `hold` is set, and lets it go just
// below the middle of another snake's card: it lands after that one. Between the steps a
// function of the scenario may run while the snake is held.
async function drag(app, snake, below, seen, {hold = false, whileHeld = null} = {}) {
  const grip = hold ? cardOf(app, snake).querySelector(".words") : handleOf(app, snake);
  grip.scrollIntoView({block: "center"});
  await app.sleep(100);
  const box = grip.getBoundingClientRect();
  const x = box.left + box.width / 2;
  const y = box.top + box.height / 2;
  pointer(app, "pointerdown", grip, x, y);
  await app.sleep(hold ? 600 : 50);
  seen.lifted = app.doc.querySelector("#mapping-snakes > .map-snake.lifted") !== null;
  const target = cardOf(app, below).getBoundingClientRect();
  const to = target.top + target.height * 0.75;
  for (let step = 1; step <= 8; step += 1) {
    pointer(app, "pointermove", app.doc, x, y + (to - y) * step / 8);
    await app.sleep(30);
  }
  seen.placeholder = app.doc.querySelector("#mapping-snakes > .map-placeholder") !== null;
  if (whileHeld !== null) await whileHeld();
  pointer(app, "pointerup", app.doc, x, to);
}

export default async function(app) {
  await shown(app, 2);
  app.press("Settings");
  await app.until(() => app.shown() === "settings", "Settings");
  if (app.settings.unsupported) {
    await app.until(() => app.says("does not support|only supports"), "unsupported mapping explanation");
    return {error: app.text("mapping-error"), count: app.doc.querySelectorAll("#mapping-snakes > .map-snake").length};
  }
  await app.until(() => order(app).length === 20 && !handleOf(app, 1).disabled, "twenty movable snakes");
  const seen = {
    before: pins(app),
    places: [...app.doc.querySelectorAll("#mapping-rows .map-pins li")].map((item) => item.textContent),
    labels: [...app.doc.querySelectorAll("#mapping-snakes .words")].map((item) => item.textContent),
    buttons: [...app.doc.querySelectorAll("#mapping button")].map((button) => button.textContent.trim()).filter((text) => text !== "≡"),
  };
  if (app.settings.layoutOnly) {
    seen.width = app.doc.documentElement.clientWidth;
    seen.scrollWidth = app.doc.documentElement.scrollWidth;
    seen.tabs = [...app.doc.querySelectorAll("nav button")].map(button => {const box=button.getBoundingClientRect();return {text:button.textContent,width:box.width};});
    return seen;
  }
  if (app.settings.other) {
    app.press("Target");
    app.fill("address", app.settings.other);
    app.press("Use");
    await app.until(() => app.shown() === "animations", "new target answers");
    app.press("Settings");
    await app.until(() => pins(app)[0] === app.settings.first, "new target assignment");
    seen.after = pins(app);
    return seen;
  }
  if (app.settings.conflict) {
    // Another controller changes the mapping while snake 1 is held: the move is refused,
    // said, and the target's assignment shown.
    await drag(app, 1, 3, seen, {whileHeld: () => app.step()});
    await app.until(() => app.says("changed on the target"), "the conflict said");
    await app.until(() => pins(app)[0] === app.settings.first, "the target's assignment");
    seen.after = pins(app);
    return seen;
  }
  if (app.settings.uncertain) {
    await drag(app, 1, 2, seen);
    await app.until(() => app.says("No confirmed reply") && !app.byId("mapping-reload").disabled, "uncertain save reconciled");
    seen.uncertain = app.text("mapping-error");
    seen.after = pins(app);
    await app.sleep(2500);
    seen.kept = pins(app);
    return seen;
  }
  // Snake 1 by its handle to just below snake 3: snakes 2 and 3 move up one place.
  await drag(app, 1, 3, seen);
  seen.dragOrder = order(app);
  await app.until(() => app.says("Saved: snake 1 is on GPIO"), "the move saved at once");
  seen.dragged = pins(app);
  seen.dragNote = app.text("mapping-summary");
  // Snake 1 held by its words, up to just below snake 2: it lands second.
  await drag(app, 1, 2, seen, {hold: true});
  await app.until(() => order(app)[1] === 1 && app.says("Saved: snake 1"), "the held move saved");
  seen.held = pins(app);
  // The arrow keys on a handle: snake 1 one place up, then snake 2 one place down.
  handleOf(app, 1).focus();
  handleOf(app, 1).dispatchEvent(new (app.frame.contentWindow.KeyboardEvent)("keydown", {key: "ArrowUp", bubbles: true, cancelable: true}));
  await app.until(() => order(app)[0] === 1 && app.says("Saved: snake 1"), "arrow up saved");
  seen.keyed = pins(app);
  seen.focusKept = app.doc.activeElement === handleOf(app, 1);
  // A snake dropped where it was moves nothing and sends nothing.
  await drag(app, 5, 4, seen);
  await app.sleep(300);
  seen.unmoved = pins(app);
  handleOf(app, 1).focus();
  handleOf(app, 1).dispatchEvent(new (app.frame.contentWindow.KeyboardEvent)("keydown", {key: "ArrowDown", bubbles: true, cancelable: true}));
  await app.until(() => order(app)[1] === 1 && app.says("Saved: snake 1"), "arrow down saved");
  seen.keyedDown = pins(app);
  await app.until(() => !app.byId("mapping-defaults").disabled, "Restore defaults available");
  app.press("Restore defaults");
  await app.until(() => app.says("Saved: the default assignment"), "defaults saved at once");
  seen.defaults = pins(app);
  seen.playback = [...app.doc.querySelectorAll("#settings button, #settings input")].filter((element) => ["on", "off", "level", "play-all"].includes(element.id) ||
    /^(On|Off|Show diagonal|Stop diagonal)$/.test(element.textContent.trim())).length;
  seen.width = app.doc.documentElement.clientWidth;
  seen.scrollWidth = app.doc.documentElement.scrollWidth;
  const first = app.doc.querySelector("#mapping-rows .map-pins li").getBoundingClientRect();
  const beside = app.doc.querySelector("#mapping-snakes > .map-snake").getBoundingClientRect();
  seen.inLine = Math.abs(first.top - beside.top) < 1 && Math.abs(first.height - beside.height) < 1;
  seen.tabs = [...app.doc.querySelectorAll("nav button")].map(button => {const box=button.getBoundingClientRect();return {text:button.textContent,width:box.width};});
  return seen;
}
