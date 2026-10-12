// The app as on a new phone: no address was ever set.

export default async function (app) {
  const field = app.byId("address").value;
  const began = app.shown();
  await app.until(() => app.text("link") === "No answer", "the target screen says No answer", 9000);
  return {field, began, shown: app.shown(), failure: app.text("link-failure"), kept: app.kept()};
}
