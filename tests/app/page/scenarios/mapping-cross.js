// Settings' checkbox `Snake 10 is cross-wired`: what it shows, a tap saving it at once,
// the summary, a refusal said with the box back, and a change made elsewhere followed.
import {shown} from "../reading.js";

const box = (app) => app.byId("mapping-cross");
const settled = (app) => !app.byId("mapping-reload").disabled;

export default async function(app) {
  await shown(app, 2);
  app.press("Settings");
  await app.until(() => app.shown() === "settings", "Settings");
  const seen = {};
  if (app.settings.unsupported) {
    await app.until(() => app.says("does not support|only supports"), "the mapping explanation");
    seen.disabled = box(app).disabled;
    seen.checked = box(app).checked;
    return seen;
  }
  await app.until(() => app.doc.querySelectorAll("#mapping-pins > .map-pin").length === 20 && !box(app).disabled, "the box enabled");
  seen.label = app.doc.querySelector('label[for="mapping-cross"] .title').textContent;
  seen.small = app.doc.querySelector('label[for="mapping-cross"] .small').textContent;
  seen.before = box(app).checked;
  box(app).click();
  seen.disabledWhileSaving = box(app).disabled;
  await app.until(() => settled(app) && !box(app).disabled && (app.says("Saved: snake 10") || app.text("mapping-error") !== ""), "the tap answered", 15000);
  seen.said = app.text("mapping-summary");
  seen.error = app.text("mapping-error");
  seen.after = box(app).checked;
  if (app.settings.refused) return seen;
  // Another controller changes the wiring: the read every two seconds shows it.
  await app.step();
  await app.until(() => box(app).checked === !seen.after, "the change made elsewhere", 8000);
  seen.followed = box(app).checked;
  box(app).click();
  await app.until(() => settled(app) && !box(app).disabled && app.says("Saved: snake 10 is"), "the second tap answered", 15000);
  seen.saidAgain = app.text("mapping-summary");
  seen.last = box(app).checked;
  return seen;
}
