import {shown} from "../reading.js";

// The mapping editor while the app reads the target in the background, every two seconds:
// a focused handle keeps the focus, no handle is disabled, the column is not drawn again,
// and a snake held across several reads lands where it is let go.
const order = (app) => [...app.doc.querySelectorAll("#mapping-snakes > .map-snake")].map((item) => Number(item.dataset.snake));
const handleOf = (app, snake) => app.doc.querySelector(`#mapping-snakes > .map-snake[data-snake="${snake}"] .handle`);

function pointer(app, type, target, x, y) {
  const view = app.frame.contentWindow;
  target.dispatchEvent(new view.PointerEvent(type, {pointerId: 9, pointerType: "touch", isPrimary: true, button: 0, clientX: x, clientY: y, bubbles: true, cancelable: true}));
}

export default async function(app) {
  await shown(app, 2);
  app.press("Settings");
  await app.until(() => app.shown() === "settings", "Settings");
  await app.until(() => order(app).length === 20 && !handleOf(app, 1).disabled, "twenty movable snakes");
  const seen = {disabled: 0, redrawn: 0, reading: 0, blurred: 0};
  const watcher = new MutationObserver(changes => {
    for (const change of changes) {
      if (change.type === "attributes" && change.attributeName === "disabled" && change.target.disabled) seen.disabled += 1;
      if (change.type === "childList" && change.target === app.byId("mapping-rows")) seen.redrawn += 1;
      if (change.type !== "attributes" && /Reading mapping/.test(app.text("mapping-summary"))) seen.reading += 1;
    }
  });
  watcher.observe(app.byId("mapping-rows"), {attributes: true, childList: true, subtree: true, attributeFilter: ["disabled"]});
  watcher.observe(app.byId("mapping-summary"), {childList: true, characterData: true, subtree: true});
  // A handle with the focus keeps it through two reads.
  const first = handleOf(app, 1);
  first.addEventListener("blur", () => {seen.blurred += 1;});
  first.focus();
  await app.sleep(4500);
  seen.focused = app.doc.activeElement === first;
  seen.blurredByReads = seen.blurred;
  // Snake 1 is held below snake 2 through two more reads, then let go there.
  first.scrollIntoView({block: "center"});
  await app.sleep(100);
  const box = first.getBoundingClientRect();
  const x = box.left + box.width / 2;
  const y = box.top + box.height / 2;
  pointer(app, "pointerdown", first, x, y);
  await app.sleep(50);
  const held = app.doc.querySelector("#mapping-snakes > .map-snake.lifted");
  const target = app.doc.querySelector('#mapping-snakes > .map-snake[data-snake="2"]').getBoundingClientRect();
  const to = target.top + target.height * 0.75;
  for (let step = 1; step <= 6; step += 1) {
    pointer(app, "pointermove", app.doc, x, y + (to - y) * step / 6);
    await app.sleep(30);
  }
  await app.sleep(4500);
  seen.stillHeld = held !== null && held.isConnected && held.classList.contains("lifted");
  seen.whileHeld = {disabled: seen.disabled, redrawn: seen.redrawn, reading: seen.reading};
  watcher.disconnect();
  pointer(app, "pointerup", app.doc, x, to);
  await app.until(() => app.says("Saved: snake 1"), "the held move saved");
  seen.order = order(app);
  return seen;
}
