import {shown} from "../reading.js";
export default async function(app) {
  await shown(app, 2);
  await app.until(() => !app.byId("select-mode").disabled, "selection available");
  app.pressIn("#list-head", "Select");
  app.press("Select all");
  app.press("Delete selected");
  const confirmed = app.text("confirm-text");
  const client = await app.frame.contentWindow.eval('import("/client.js")');
  client.begin();
  await app.until(() => app.text("confirm-text") === null && !app.byId("select-all").disabled, "new target snapshot");
  return {confirmed, selected: app.doc.querySelectorAll('#animations-list input:checked').length, disabled: app.byId("delete-selected").disabled};
}
