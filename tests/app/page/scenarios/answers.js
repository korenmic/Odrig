// A target that answers: the app goes to the show screen by itself, and the target
// screen says what it found.

export default async function (app) {
  await app.until(() => app.shown() === "show", "the show screen is shown", 4000);
  app.press("Target");
  await app.until(() => app.text("link") === "Answers", "the target screen says Answers");
  return {
    shown: app.shown(),
    link: app.text("link"),
    failure: app.text("link-failure"),
    invalid: app.text("invalid"),
    route: app.text("route"),
    about: app.text("about"),
    field: app.byId("address").value,
    kept: app.kept(),
  };
}
