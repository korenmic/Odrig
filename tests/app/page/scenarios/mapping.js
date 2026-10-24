import {shown} from "../reading.js";

export default async function(app) {
  await shown(app, 2);
  app.press("Mapping");
  await app.until(() => app.shown() === "mapping", "Mapping screen");
  if (app.settings.unsupported) {
    await app.until(() => app.says("does not support|only supports"), "unsupported mapping explanation");
    return {error: app.text("mapping-error"), count: app.doc.querySelectorAll("#mapping-rows select").length};
  }
  await app.until(() => app.doc.querySelectorAll("#mapping-rows select").length === 20, "twenty snake selectors");
  const pins = () => [...app.doc.querySelectorAll("#mapping-rows select")].map(field => Number(field.value));
  const change = (id, value) => {app.byId(id).value = String(value);app.release(id);};
  const seen = {before: pins(), labels: [...app.doc.querySelectorAll("#mapping-rows label")].map(label => label.textContent)};
  change("mapping-pin-1", seen.before[1]);
  seen.draft = pins();
  await app.sleep(2400);
  seen.kept = pins();
  if (app.settings.other) {
    app.press("Target");
    app.fill("address", app.settings.other);
    app.press("Use");
    await app.until(() => app.shown() === "show", "new target answers");
    app.press("Mapping");
    await app.until(() => app.doc.getElementById("mapping-pin-1")?.value === String(app.settings.first), "new target assignment");
    seen.after = pins();
    seen.saveDisabled = app.byId("mapping-save").disabled;
    return seen;
  }
  if (app.settings.conflict) {
    await app.step();
    await app.until(() => app.says("changed on the target"), "external edit conflict");
    seen.disabled = app.byId("mapping-save").disabled;
    seen.conflict = pins();
    app.press("Reload");
    await app.until(() => app.doc.getElementById("mapping-pin-1")?.value === String(app.settings.first), "reloaded assignment");
    seen.after = pins();
    return seen;
  }
  app.press("Cancel");
  seen.cancelled = pins();
  change("mapping-pin-1", seen.before[1]);
  app.press("Save");
  if (app.settings.uncertain) {
    await app.until(() => app.says("No confirmed reply") && !app.byId("mapping-reload").disabled, "uncertain save reconciled");
    seen.uncertain = app.text("mapping-error");
    seen.disabled = app.byId("mapping-save").disabled;
    seen.kept = pins();
    app.press("Reload");
    await app.until(() => !app.says("No confirmed reply") && !app.byId("mapping-reload").disabled, "authoritative reload");
    seen.after = pins();
    return seen;
  }
  await app.until(() => app.says("Mapping saved") && !app.byId("mapping-reload").disabled, "acknowledged save and reread");
  seen.saved = pins();
  app.press("Show diagonal");
  await app.until(() => app.text("mapping-mode") === "Diagonal is showing", "diagonal state");
  seen.mode = app.text("mapping-mode");
  app.press("Show");
  await app.until(() => app.shown() === "show", "Show after back");
  app.press("Mapping");
  await app.until(() => app.text("mapping-mode") === "Diagonal is showing", "persistent target diagnostic");
  await app.until(() => !app.byId("mapping-test-off").disabled, "ready to stop the diagonal");
  await app.reload();
  await shown(app, 2);
  app.press("Mapping");
  await app.until(() => app.text("mapping-mode") === "Diagonal is showing" && !app.byId("mapping-test-off").disabled, "target diagnostic after app restart");
  app.press("Stop diagonal");
  await app.until(() => app.text("mapping-mode") === "Normal playback", "normal playback restored");
  app.press("Restore defaults");
  seen.defaults = pins();
  seen.width = app.doc.documentElement.clientWidth;
  seen.scrollWidth = app.doc.documentElement.scrollWidth;
  seen.tabs = [...app.doc.querySelectorAll("nav button")].map(button => {const box=button.getBoundingClientRect();return {text:button.textContent,width:box.width};});
  return seen;
}
