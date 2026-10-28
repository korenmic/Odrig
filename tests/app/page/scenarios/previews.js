// The previews of the rows and of the panel of what plays: every row's square at the root
// and inside the folders the test names, the folder rows and the Tests group without one, a
// tap on a square, and, as the test says, Settings' rebuild of the board's catalog first.

function squares(app) {
  const view = app.frame.contentWindow;
  return [...app.doc.querySelectorAll("#animations-list > .row")].map((row) => {
    const play = row.querySelector(".play");
    const square = play.querySelector(".thumb");
    const image = square === null ? null : square.querySelector("img");
    const box = square === null ? null : square.getBoundingClientRect();
    return {
      id: Number(row.dataset.id),
      file: row.dataset.file,
      first: square !== null && play.firstElementChild === square,
      size: box === null ? null : [Math.round(box.width), Math.round(box.height)],
      src: image === null ? null : image.getAttribute("src"),
      alt: image === null ? null : image.getAttribute("alt"),
      draggable: image === null ? null : image.draggable,
      loaded: image === null ? null : image.complete && image.naturalWidth > 0,
      natural: image === null ? null : [image.naturalWidth, image.naturalHeight],
      rendering: image === null ? null : view.getComputedStyle(image).imageRendering,
      fault: row.dataset.fault,
    };
  });
}

function now(app) {
  const square = app.byId("now-thumb");
  const image = square.querySelector("img");
  return {text: app.text("now"), shown: square.getClientRects().length > 0, src: image === null ? null : image.getAttribute("src")};
}

function previewed(app) {
  return squares(app).filter((row) => row.src !== null && row.loaded).length;
}

export default async function (app) {
  const settings = app.settings;
  await app.until(() => app.shown() === "animations" && app.text("power") !== "-", "the show screen with a status");
  if (settings.rebuild === true) {
    await app.until(() => squares(app).length >= settings.rows, "the rows", 15000);
    const before = squares(app);
    app.press("Settings");
    await app.until(() => app.text("catalog-internal") !== null, "the catalogs");
    app.press("Rebuild the board's catalog");
    await app.until(() => app.text("rebuild-question-text") !== null, "the question");
    app.press("Rebuild");
    await app.until(() => /^Board: [0-9]+ animations?, cataloged\.$/.test(app.text("catalog-internal") || ""), "the board cataloged", 20000);
    app.press("Animations");
    await app.until(() => previewed(app) >= settings.previews, "the previews", 20000);
    return {before, after: squares(app)};
  }
  await app.until(() => squares(app).length >= settings.rows && previewed(app) >= settings.previews, "the rows with their previews", 30000);
  await app.until(() => now(app).src !== null || settings.nowPreview === false, "the panel's preview", 8000);
  const seen = {root: squares(app), now: now(app)};
  seen.folderSquares = app.doc.querySelectorAll("#animations-list > .folder-row .thumb").length;
  seen.testSquares = app.doc.querySelectorAll("#tests .thumb").length;
  seen.folders = [...app.doc.querySelectorAll("#animations-list > .folder-row")].map((row) => row.dataset.path);
  for (const path of settings.enter || []) {
    app.doc.querySelector(`#animations-list > .folder-row[data-path="${path}"]`).click();
    await app.until(() => app.text("level-title") === path && previewed(app) >= 1, `the folder ${path}`);
    seen[path] = squares(app);
    app.press("Back");
    // The root's level is read anew.
    await app.until(() => app.text("level-title") === "Root" && squares(app).length >= settings.rows, "the root");
  }
  if (settings.tap !== undefined) {
    const row = app.doc.querySelector(`#animations-list > .row[data-id="${settings.tap}"]`);
    row.querySelector(".thumb").click();
    await app.until(() => app.text("now") === `Now ${settings.tap} ${row.dataset.file}`, "the tapped animation on the LEDs");
    await app.until(() => now(app).src !== null, "the panel's preview of it");
    seen.tapped = now(app);
  }
  return seen;
}
