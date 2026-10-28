import {shown, startSelection} from "../reading.js";
export default async function(app) {
  await shown(app, 39);
  await app.until(() => startSelection(app) !== null, "selection available");
  app.press("Select all");
  app.press("Delete selected");
  app.press("Remove it");
  await app.step();
  const client = await app.frame.contentWindow.eval('import("/client.js")');
  const target = await app.frame.contentWindow.eval('import("/target.js")');
  target.setAddress(app.settings.other);
  client.begin();
  await app.until(() => !app.byId("select-all").disabled && app.doc.querySelectorAll("#animations-list > .row").length === 2, "new target list");
  await app.sleep(1000);
  return {selected: app.doc.querySelectorAll('#animations-list input:checked').length, message: app.text("message-text"), disabled: app.byId("delete-selected").disabled};
}
