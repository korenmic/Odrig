import {shown} from "../reading.js";

export default async function(app) {
  await shown(app, app.settings.rows);
  const toggle = () => app.doc.querySelector('#animations [data-id="1"] input[type="checkbox"]');
  const seen = {};
  if (app.settings.refuseToggle) {
    await app.until(() => toggle(), "playlist inclusion checkbox");
    const client = await app.frame.contentWindow.eval('import("/client.js")');
    const before = client.state.listVersion;
    toggle().click();
    seen.pending = toggle().disabled;
    await app.until(() => app.says("busy") && !toggle().disabled, "refused inclusion change");
    await app.until(() => client.state.listVersion > before, "list refresh after refused toggle");
    seen.checked = toggle().checked;
    return seen;
  }
  if (app.settings.toggle) {
    await app.until(() => toggle(), "playlist inclusion checkbox");
    seen.before = toggle().checked;
    toggle().click();
    seen.pending = toggle().disabled;
    await app.until(() => !toggle().disabled && !toggle().checked, "confirmed exclusion");
    await app.reload();
    await shown(app, app.settings.rows);
    await app.until(() => toggle() && !toggle().checked, "persisted exclusion after reload");
    await app.step();
    await app.until(() => toggle().checked, "serial inclusion reflected", 13000);
    seen.restored = toggle().checked;
  }
  await app.until(() => app.text("show-space") && app.text("show-space") !== "-", "dashboard capacity");
  seen.dashboard = app.text("show-space");
  app.press("Storage");
  await app.until(() => app.shown() === "storage" && app.text("space") !== "-", "storage capacity");
  const checks = () => [...app.doc.querySelectorAll('#installed input[type="checkbox"]')];
  await app.until(() => checks().length === app.settings.selectable, "installed selection checkboxes");
  seen.checkboxes = checks().length;
  seen.external = app.text("external-space");
  seen.freeBefore = app.text("space");
  app.press("Select all");
  seen.selected = checks().filter(input => input.checked).length;
  app.press("Delete selected");
  await app.until(() => app.text("confirm-text") !== null, "deletion confirmation");
  seen.question = app.text("confirm-text");
  if (app.settings.cancel) {
    seen.removable = app.doc.querySelectorAll("#installed button").length;
    app.press("Keep it");
    return seen;
  }
  app.press("Remove it");
  if (app.settings.refused || app.settings.uncertain) {
    await app.until(() => app.says(app.settings.uncertain ? "No confirmed reply" : "in-use"), "readable deletion failure", 10000);
    await app.until(() => app.byId("bulk-progress").dataset.refreshing !== "true", "authoritative list refresh");
    seen.message = app.text("message-text");
    seen.remaining = app.doc.querySelectorAll("#installed > .row").length;
    seen.kept = checks().filter(input => input.checked).length;
  } else {
    await app.until(() => app.doc.querySelectorAll("#installed > .row").length === 0, "all selected items removed", 10000);
    await app.until(() => app.text("space") !== seen.freeBefore, "capacity refreshed after deletion");
    seen.remaining = 0;
    seen.message = app.text("message-text");
  }
  seen.freeAfter = app.text("space");
  seen.deleteDisabled = app.byId("delete-selected").disabled;
  return seen;
}
