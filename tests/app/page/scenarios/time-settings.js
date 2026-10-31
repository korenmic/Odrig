import {shown} from "../reading.js";
import {measure} from "./look.js";

function look(app) {
  return {auto: app.byId("time-auto").checked, enabled: app.byId("schedule-enabled").checked,
    on: app.byId("schedule-on").value, off: app.byId("schedule-off").value,
    readout: app.raw("time-reading"), said: app.raw("time-state"),
    scheduleState: app.raw("schedule-state"), saveDisabled: app.byId("schedule-save").disabled,
    resumeDisabled: app.byId("schedule-resume").disabled, syncDisabled: app.byId("time-sync").disabled,
    refreshDisabled: app.byId("time-refresh").disabled};
}

export default async function(app) {
  await shown(app, 2);
  app.press("Settings");
  if (app.settings.legacy) await app.until(() => app.raw("time-state").includes("firmware"), "unsupported firmware");
  else await app.until(() => !app.byId("time-sync").disabled, "timing read finished", 15000);
  const seen = {first: look(app)};
  for (const act of app.settings.acts ?? []) {
    if (act.tap) app.byId(act.tap).click();
    if (act.fill) for (const [id, value] of Object.entries(act.fill)) app.fill(id, value);
    if (act.nowOff) {
      const now = new Date();
      const minute = now.getHours() * 60 + now.getMinutes();
      const hour = value => `${Math.floor(value / 60).toString().padStart(2, "0")}:${(value % 60).toString().padStart(2, "0")}`;
      app.fill("schedule-on", hour((minute + 5) % 1440));
      app.fill("schedule-off", hour((minute + 10) % 1440));
    }
    if (act.step) await app.step();
    if (act.wait) await app.sleep(act.wait);
    if (act.reload) { await app.reload(); await shown(app, 2); app.press("Settings"); }
    if (act.target) {
      app.press("Target"); app.fill("address", act.target); app.press("Use");
      seen.changed = look(app);
      await shown(app, 2); app.press("Settings");
    }
    if (act.until) await app.until(() => {
      const current = look(app);
      return Object.entries(act.until).every(([key, value]) =>
        key === "text" ? `${current.said} ${current.scheduleState}`.includes(value) : current[key] === value);
    }, JSON.stringify(act.until), 15000);
    if (act.look) seen[act.look] = look(app);
    if (act.measure) {
      seen[act.measure] = {...measure(app), timingLabels: [...app.doc.querySelectorAll("#time-panel input")]
        .map(field => ({id: field.id, label: field.labels[0]?.textContent.trim() ?? ""}))};
    }
  }
  return seen;
}
