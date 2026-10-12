// A target that takes the request and never answers.

export default async function (app) {
  const start = performance.now();
  const began = {shown: app.shown(), link: app.text("link"), failure: app.text("link-failure")};
  await app.until(() => app.text("link") === "No answer", "the target screen says No answer", 9000);
  return {began, afterMs: performance.now() - start, shown: app.shown(), failure: app.text("link-failure")};
}
