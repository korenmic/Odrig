// The operator does things at given moments, against a target of the test.

export default async function (app) {
  await app.until(() => app.shown() === "animations", "the show screen is shown", 9000);
  for (const act of app.settings.acts) {
    await app.sleep(act.after);
    if (act.press !== undefined) {
      app.press(act.press);
    } else if (act.tap !== undefined) {
      app.tap(act.tap);
    } else if (act.slide !== undefined) {
      app.slide("level", act.slide);
    } else {
      app.release("level");
    }
  }
  await app.sleep(app.settings.then);
  return {link: app.raw("link")};
}
