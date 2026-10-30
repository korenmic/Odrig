import {shown} from "../reading.js";

// The pins of snakes 1 to 20 as the column beside the snakes shows them.
const pins = (app) => [...app.doc.querySelectorAll("#mapping-pins > .map-pin")].map((item) => Number(item.dataset.pin));
const handleOf = (app, pin) => app.doc.querySelector(`#mapping-pins > .map-pin[data-pin="${pin}"] .handle`);
const cardOf = (app, pin) => app.doc.querySelector(`#mapping-pins > .map-pin[data-pin="${pin}"]`);

function pointer(app, type, target, x, y) {
  const view = app.frame.contentWindow;
  target.dispatchEvent(new view.PointerEvent(type, {pointerId: 7, pointerType: "touch", isPrimary: true, button: 0, clientX: x, clientY: y, bubbles: true, cancelable: true}));
}

function key(app, pin, name) {
  handleOf(app, pin).focus();
  handleOf(app, pin).dispatchEvent(new (app.frame.contentWindow.KeyboardEvent)("keydown", {key: name, bubbles: true, cancelable: true}));
}

// Takes a pin by its handle, or holds its words when `hold` is set, and moves it to just
// below the middle of another pin's card, where it lands after that one. `whileHeld` runs
// before the move and `afterMove` after it, both while the pin is still held.
async function drag(app, pin, below, seen, {hold = false, whileHeld = null, afterMove = null} = {}) {
  const grip = hold ? cardOf(app, pin).querySelector(".words") : handleOf(app, pin);
  grip.scrollIntoView({block: "center"});
  await app.sleep(100);
  const box = grip.getBoundingClientRect();
  const x = box.left + box.width / 2;
  const y = box.top + box.height / 2;
  pointer(app, "pointerdown", grip, x, y);
  await app.sleep(hold ? 600 : 50);
  seen.lifted = app.doc.querySelector("#mapping-pins > .map-pin.lifted") !== null;
  if (whileHeld !== null) await whileHeld();
  const target = cardOf(app, below).getBoundingClientRect();
  const to = target.top + target.height * 0.75;
  for (let step = 1; step <= 8; step += 1) {
    pointer(app, "pointermove", app.doc, x, y + (to - y) * step / 8);
    await app.sleep(30);
  }
  seen.placeholder = app.doc.querySelector("#mapping-pins > .map-placeholder") !== null;
  if (afterMove !== null) await afterMove();
  pointer(app, "pointerup", app.doc, x, to);
}

export default async function(app) {
  await shown(app, 2);
  app.press("Settings");
  await app.until(() => app.shown() === "settings", "Settings");
  if (app.settings.unsupported) {
    await app.until(() => /does not support|only supports/.test(app.text("mapping-error") ?? ""), "unsupported mapping explanation");
    return {error: app.text("mapping-error"), count: app.doc.querySelectorAll("#mapping-pins > .map-pin").length};
  }
  await app.until(() => pins(app).length === 20 && !handleOf(app, pins(app)[0]).disabled, "twenty movable pins");
  const seen = {
    before: pins(app),
    snakes: [...app.doc.querySelectorAll("#mapping-rows .map-snakes li")].map((item) => item.textContent),
    words: [...app.doc.querySelectorAll("#mapping-pins .words")].map((item) => item.textContent),
    buttons: [...app.doc.querySelectorAll("#mapping button")].filter((button) => button.getClientRects().length > 0).map((button) => button.textContent.trim()).filter((text) => text !== "≡"),
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
  const [one, two, three, four, five] = seen.before;
  if (app.settings.conflict) {
    // Another controller changes the mapping after a pin is taken: its first new place is
    // refused, said, the drag ends, and the target's assignment is shown.
    await drag(app, one, three, seen, {whileHeld: () => app.step()});
    await app.until(() => app.says("changed on the target"), "the conflict said");
    await app.until(() => pins(app)[0] === app.settings.first, "the target's assignment");
    seen.after = pins(app);
    return seen;
  }
  if (app.settings.uncertain) {
    await drag(app, one, two, seen);
    await app.until(() => app.says("No confirmed reply") && !app.byId("mapping-reload").disabled, "uncertain save reconciled");
    seen.uncertain = app.text("mapping-error");
    seen.after = pins(app);
    await app.sleep(2500);
    seen.kept = pins(app);
    return seen;
  }
  // Snake 1's pin by its handle to just below snake 3's: saved while the finger is down.
  await drag(app, one, three, seen, {afterMove: async () => {
    await app.until(() => app.says(`Saved: GPIO ${one} drives snake 3`), "the move saved while held");
    seen.stillLifted = app.doc.querySelector("#mapping-pins > .map-pin.lifted") !== null;
    await app.step();
  }});
  await app.until(() => !app.byId("mapping-reload").disabled && app.doc.querySelector("#mapping-pins > .map-pin.lifted") === null, "the pin let go");
  seen.dragged = pins(app);
  seen.dragNote = app.text("mapping-summary");
  // The same pin held by its words, up to just below snake 1's pin, where it lands second.
  await drag(app, one, two, seen, {hold: true});
  await app.until(() => pins(app)[1] === one && app.says(`Saved: GPIO ${one} drives snake 2`) && !app.byId("mapping-reload").disabled, "the held move saved");
  seen.held = pins(app);
  // The arrow keys on a handle: one place up.
  key(app, one, "ArrowUp");
  await app.until(() => pins(app)[0] === one && app.says(`Saved: GPIO ${one} drives snake 1`) && !app.byId("mapping-reload").disabled, "arrow up saved");
  seen.keyed = pins(app);
  seen.focusKept = app.doc.activeElement === handleOf(app, one);
  // A pin let go where it was moves nothing and sends nothing.
  await drag(app, five, four, seen);
  await app.sleep(300);
  seen.unmoved = pins(app);
  key(app, one, "ArrowDown");
  await app.until(() => pins(app)[1] === one && app.says(`Saved: GPIO ${one} drives snake 2`) && !app.byId("mapping-reload").disabled, "arrow down saved");
  seen.keyedDown = pins(app);
  await app.until(() => !app.byId("mapping-defaults").disabled, "Restore defaults available");
  app.press("Restore defaults");
  await app.until(() => app.says("Saved: the default assignment") && !app.byId("mapping-reload").disabled, "defaults saved at once");
  seen.defaults = pins(app);
  seen.playback = [...app.doc.querySelectorAll("#settings button, #settings input")].filter((element) => ["on", "off", "level", "play-all"].includes(element.id) ||
    /^(On|Off|Show diagonal|Stop diagonal)$/.test(element.textContent.trim())).length;
  seen.width = app.doc.documentElement.clientWidth;
  seen.scrollWidth = app.doc.documentElement.scrollWidth;
  const left = app.doc.querySelector("#mapping-rows .map-snakes li").getBoundingClientRect();
  const right = app.doc.querySelector("#mapping-pins > .map-pin").getBoundingClientRect();
  seen.inLine = Math.abs(left.top - right.top) < 1 && Math.abs(left.height - right.height) < 1 && left.left < right.left;
  seen.tabs = [...app.doc.querySelectorAll("nav button")].map(button => {const box=button.getBoundingClientRect();return {text:button.textContent,width:box.width};});
  return seen;
}
