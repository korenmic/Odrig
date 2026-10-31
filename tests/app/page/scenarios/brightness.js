import {shown} from "../reading.js";
import {measure} from "./look.js";

function look(app) {
  const box = app.byId("level-override");
  return {checked: box.checked, disabled: box.disabled, unknown: box.indeterminate,
    slider: Number(app.byId("level").value), number: app.byId("level-number").value,
    label: app.raw("level-label"), file: app.text("level-file"), said: app.text("level-said"),
    range: app.text("level-range")};
}

export default async function(app) {
  await shown(app, 2);
  const seen = {first: look(app)};
  for (const act of app.settings.acts) {
    if (act.type !== undefined) { app.byId("level-number").focus(); app.fill("level-number", act.type); }
    if (act.pointer) app.byId("level-override").dispatchEvent(new PointerEvent("pointerdown", {bubbles: true}));
    if (act.leave) {
      app.byId("level-number").dispatchEvent(new Event("change", {bubbles: true}));
      app.byId("level-number").blur();
    }
    if (act.enter) app.byId("level-number").dispatchEvent(new KeyboardEvent("keydown", {key: "Enter", bubbles: true}));
    if (act.slide !== undefined) app.slide("level", act.slide);
    if (act.release) app.release("level");
    if (act.tap) app.byId("level-override").click();
    if (act.step) await app.step();
    if (act.powerProbe) {
      let enabled = false;
      const box = app.byId("level-override");
      const observer = new MutationObserver(() => { if (!box.disabled) enabled = true; });
      observer.observe(box, {attributes: true, attributeFilter: ["disabled"]});
      app.byId("power-toggle").click();
      await app.sleep(400);
      observer.disconnect();
      seen.probeEnabled = enabled;
    }
    if (act.wait) await app.sleep(act.wait);
    if (act.reload) { await app.reload(); await shown(app, 2); }
    if (act.target) {
      app.press("Target"); app.fill("address", act.target); app.press("Use");
      seen.changed = look(app);
      await shown(app, 2);
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
