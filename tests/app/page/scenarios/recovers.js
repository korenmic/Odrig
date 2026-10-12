// Nothing listens at the address; then a target starts there.

export default async function (app) {
  await app.until(() => app.text("link") === "No answer", "the target screen says No answer");
  const failure = app.text("link-failure");
  await app.step();
  const asked = performance.now();
  await app.until(() => app.shown() === "show", "the show screen after the first answer", 6000);
  const ms = performance.now() - asked;
  app.press("Target");
  return {failure, ms, link: app.text("link"), failureAfter: app.text("link-failure")};
}
