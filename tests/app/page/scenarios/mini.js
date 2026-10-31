import {shown} from "../reading.js";
import {measure} from "./look.js";

function look(app) {
  const box = app.byId("debug-mini");
  return {checked: box.checked, unknown: box.indeterminate, disabled: box.disabled,
    said: app.text("mini-said"), indicator: app.text("mini-indicator"),
    restore: app.text("mini-restore")};
}

export default async function(app) {
  await shown(app, 2);
  app.press("Settings");
  await app.until(() => app.shown() === "settings", "Settings");
  await app.until(() => !app.raw("mini-said").startsWith("Reading"), "miniature status");
  const seen = {first: look(app)};
  for (const act of app.settings.acts) {
    if (act.screen) app.press(act.screen);
    if (act.tap) app.byId(act.tap).click();
    if (act.step) await app.step();
    if (act.reload) { await app.reload(); await shown(app, 2); app.press("Settings"); }
    if (act.target) {
      app.press("Target");
      app.fill("address", act.target);
      app.press("Use");
      seen.changed = look(app);
      await shown(app, 2);
      app.press("Settings");
    }
    if (act.until) await app.until(() => {
      const now = look(app);
      return Object.entries(act.until).every(([key, value]) => key === "text" ? now.said?.includes(value) : now[key] === value);
    }, JSON.stringify(act.until), 15000);
    if (act.look) seen[act.look] = look(app);
    if (act.measure) seen[act.measure] = measure(app);
  }
  return seen;
}
