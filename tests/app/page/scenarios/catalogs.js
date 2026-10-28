// Settings' catalogs: the line of each storage and the panel's buttons; and, as the test
// says, a rebuild asked about and answered, its progress, Animations while it runs, and
// its cancel or its end.

const READING = "Reading the catalogs\u2026";

function lines(app) {
  return {
    summary: app.text("catalog-summary"),
    internal: app.text("catalog-internal"),
    external: app.text("catalog-external"),
    note: app.text("catalog-external-note"),
    progress: app.text("rebuild-progress"),
    buttons: [...app.byId("catalogs").querySelectorAll("button")].filter((button) => button.getClientRects().length > 0)
      .map((button) => `${button.textContent}${button.disabled ? " (disabled)" : ""}`),
  };
}

export default async function (app) {
  const settings = app.settings;
  await app.until(() => app.shown() === "animations" && app.text("power") !== "-", "the show screen with a status");
  app.press("Settings");
  await app.until(() => app.shown() === "settings" && app.text("catalog-summary") !== READING, "the catalogs");
  const seen = {first: lines(app)};
  if (settings.rebuild === undefined) {
    await app.sleep(settings.wait || 0);
    seen.after = lines(app);
    return seen;
  }
  app.press(settings.rebuild);
  await app.until(() => app.text("rebuild-question-text") !== null, "the question");
  seen.question = app.text("rebuild-question-text");
  seen.asking = lines(app);
  app.press(settings.answer);
  if (settings.refused === true) {
    await app.until(() => app.text("message-text") !== null, "the message of the refusal");
    seen.message = app.text("message-text");
    await app.sleep(500);
    seen.after = lines(app);
    return seen;
  }
  if (settings.answer !== "Rebuild") {
    await app.until(() => app.text("rebuild-question-text") === null, "the question closed");
    await app.sleep(2500);
    seen.after = lines(app);
    return seen;
  }
  const progress = [];
  const follow = () => {
    const now = app.text("rebuild-progress");
    if (now !== null && progress[progress.length - 1] !== now) {
      progress.push(now);
    }
    return now;
  };
  await app.until(() => follow() !== null && progress.length >= 2, "the progress moving", 10000);
  seen.during = lines(app);
  if (settings.visit === true) {
    // Animations while the rebuild runs: the line of the reading, and controls that work.
    app.press("Animations");
    await app.until(() => app.shown() === "animations" && app.text("readiness") !== null, "the reading on Animations");
    seen.animations = {readiness: app.text("readiness"), pressable: ["power-toggle", "play-all", "level"].every((id) => !app.byId(id).disabled)};
    app.press("Settings");
    await app.until(() => app.shown() === "settings" && follow() !== null, "the progress again");
  }
  if (settings.cancel === true) {
    app.press("Cancel the rebuild");
  }
  await app.until(() => {
    follow();
    return app.text("rebuild-progress") === null;
  }, "the rebuild over", 30000);
  await app.sleep(300);
  seen.progress = progress;
  seen.after = lines(app);
  return seen;
}
