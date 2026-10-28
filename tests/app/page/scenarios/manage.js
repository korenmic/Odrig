// The operator ignores and restores an animation from its row's menu, and selects
// animations of the list for deletion.

import {choose, menuOf, rowOf, shown, spaceKnown} from "../reading.js";

export default async function(app) {
  await shown(app, app.settings.rows);
  const ignored = () => rowOf(app, 1).classList.contains("ignored");
  const saving = () => rowOf(app, 1).dataset.saving === "true";
  const seen = {};
  if (app.settings.refuseToggle) {
    const client = await app.frame.contentWindow.eval('import("/client.js")');
    const before = client.state.listVersion;
    menuOf(app, 1);
    choose(app, "Ignore in playlist");
    seen.pending = saving();
    await app.until(() => app.says("busy") && !saving(), "refused inclusion change");
    await app.until(() => client.state.listVersion > before, "list refresh after refused toggle");
    seen.checked = !ignored();
    return seen;
  }
  if (app.settings.toggle) {
    const client = await app.frame.contentWindow.eval('import("/client.js")');
    await app.until(() => client.state.order !== null, "the saved order");
    seen.before = !ignored();
    seen.menu = menuOf(app, 1);
    choose(app, "Ignore in playlist");
    seen.pending = saving() && rowOf(app, 1).querySelector(".row-state").textContent === "Saving…";
    await app.until(() => !saving() && ignored(), "confirmed exclusion");
    seen.ignoredNote = rowOf(app, 1).querySelector(".row-state").textContent;
    seen.ignoredMenu = menuOf(app, 1);
    app.doc.dispatchEvent(new KeyboardEvent("keydown", {key: "Escape", bubbles: true}));
    await app.reload();
    await shown(app, app.settings.rows);
    await app.until(() => ignored(), "persisted exclusion after reload");
    await app.step();
    await app.until(() => !ignored(), "serial inclusion reflected", 13000);
    seen.restored = !ignored();
  }
  await app.until(() => spaceKnown(app), "dashboard capacity");
  seen.dashboard = app.text("show-space");
  const checks = () => [...app.doc.querySelectorAll('#animations-list .row .pick input[type="checkbox"]')];
  const shownChecks = () => checks().filter((input) => input.getClientRects().length > 0);
  seen.hiddenBefore = shownChecks().length;
  app.pressIn("#list-head", "Select");
  await app.until(() => shownChecks().length === app.settings.selectable, "selection checkboxes");
  seen.checkboxes = shownChecks().length;
  seen.external = app.text("show-external-space");
  seen.freeBefore = app.text("show-space");
  app.press("Select all");
  seen.selected = checks().filter(input => input.checked).length;
  app.press("Delete selected");
  await app.until(() => app.text("confirm-text") !== null, "deletion confirmation");
  seen.question = app.text("confirm-text");
  if (app.settings.cancel) {
    seen.removable = app.doc.querySelectorAll('#animations-list .row[data-editable="true"]').length;
    app.press("Keep it");
    return seen;
  }
  app.press("Remove it");
  if (app.settings.refused || app.settings.uncertain) {
    await app.until(() => app.says(app.settings.uncertain ? "No confirmed reply" : "in-use"), "readable deletion failure", 10000);
    await app.until(() => app.byId("bulk-progress").dataset.refreshing !== "true", "authoritative list refresh");
    seen.message = app.text("message-text");
    seen.remaining = app.doc.querySelectorAll("#animations-list > .row").length;
    seen.kept = checks().filter(input => input.checked).length;
  } else {
    await app.until(() => app.doc.querySelectorAll("#animations-list > .row").length === 0, "all selected items removed", 10000);
    await app.until(() => app.text("show-space") !== seen.freeBefore, "capacity refreshed after deletion");
    seen.remaining = 0;
    seen.message = app.text("message-text");
  }
  seen.freeAfter = app.text("show-space");
  seen.deleteDisabled = app.byId("delete-selected").disabled;
  return seen;
}
