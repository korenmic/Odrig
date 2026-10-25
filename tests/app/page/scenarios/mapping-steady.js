import {shown} from "../reading.js";

// The mapping editor while the app reads the target in the background: a picker that is
// open must stay open and enabled, and a pin chosen at any moment must stay chosen.
export default async function(app) {
  await shown(app, 2);
  app.press("Settings");
  await app.until(() => app.shown() === "settings", "Settings");
  await app.until(() => app.doc.querySelectorAll("#mapping-rows select").length === 20 && !app.byId("mapping-pin-1").disabled, "twenty enabled snake selectors");
  const pins = () => [...app.doc.querySelectorAll("#mapping-rows select")].map(field => Number(field.value));
  const before = pins();
  const first = app.byId("mapping-pin-1");
  const seen = {disabled: 0, blurred: 0, waiting: 0, tried: 0, kept: 0};
  // Every time a picker is disabled, or the summary says the app waits, is counted as it
  // happens, however short it is.
  const watcher = new MutationObserver(changes => {
    for (const change of changes) {
      if (change.type === "attributes" && change.attributeName === "disabled" && change.target.disabled) seen.disabled += 1;
      if (change.type !== "attributes" && /Waiting for the target/.test(app.text("mapping-summary"))) seen.waiting += 1;
    }
  });
  watcher.observe(app.byId("mapping-rows"), {attributes: true, subtree: true, attributeFilter: ["disabled"]});
  watcher.observe(app.byId("mapping-summary"), {childList: true, characterData: true, subtree: true});
  let picking = false;
  first.addEventListener("blur", () => {if (!picking) seen.blurred += 1;});
  first.focus();
  const started = performance.now();
  let next = 0;
  while (performance.now() - started < 6500) {
    if (performance.now() - started >= next) {
      // Every 650 ms the first snake takes the other pin: at times while a read is out.
      const wanted = pins()[0] === before[0] ? before[1] : before[0];
      picking = true;
      first.value = String(wanted);
      app.release("mapping-pin-1");
      seen.tried += 1;
      await app.sleep(30);
      if (pins()[0] === wanted) seen.kept += 1;
      first.focus();
      picking = false;
      next += 650;
    }
    await app.sleep(20);
  }
  watcher.disconnect();
  return seen;
}
