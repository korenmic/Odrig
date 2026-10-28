// The keys the app learns from the catalogs' pages, as its client holds them, followed
// through the plan the test gives: waits for a condition or for rows, steps of the test,
// sleeps, presses, a folder entered, the app loaded again, another address, and a snapshot
// of the client and of the rows' squares by a name at each `snap`.

function keysOf(kept) {
  return kept === null ? null : {generation: kept.generation, entries: kept.entries, byName: Object.fromEntries(kept.byName)};
}

// Each row of the level shown: its file, the source of its square's image, or null, and the
// square's background colour.
function squares(app) {
  const view = app.frame.contentWindow;
  return [...app.doc.querySelectorAll("#animations-list > .row")].map((row) => {
    const square = row.querySelector(".thumb");
    const image = square === null ? null : square.querySelector("img");
    return {file: row.dataset.file, src: image === null ? null : image.getAttribute("src"), background: square === null ? null : view.getComputedStyle(square).backgroundColor};
  });
}

function snapshot(client, app) {
  return {
    squares: squares(app),
    internal: keysOf(client.state.keys.internal),
    external: keysOf(client.state.keys.external),
    version: client.state.keysVersion,
    catalogNone: client.state.catalogNone,
    pagesRefused: client.state.pagesRefused,
    link: client.state.link,
    rowKeys: (client.state.animations || []).map((animation) => [animation.file, client.keyOf(animation)]),
  };
}

const CONDITIONS = {
  internal: (client) => client.state.keys.internal !== null,
  external: (client) => client.state.keys.external !== null,
  both: (client) => client.state.keys.internal !== null && client.state.keys.external !== null,
  "no-internal": (client) => client.state.keys.internal === null,
  "no-keys": (client) => client.state.keys.internal === null && client.state.keys.external === null,
  "some-keys": (client) => client.state.keys.internal === null && (client.state.animations || []).some((animation) => client.keyOf(animation) !== null),
  "pages-refused": (client) => client.state.pagesRefused,
  "catalog-none": (client) => client.state.catalogNone,
  "no-answer": (client) => client.state.link === "no-answer",
  answers: (client) => client.state.link === "answers",
};

// The app's own client: a module script in the app's frame imports the same module the app
// runs, and hands it over.
async function clientOf(app) {
  await app.until(() => app.shown() === "animations" && app.text("power") !== "-", "the show screen with a status");
  const script = app.doc.createElement("script");
  script.type = "module";
  script.textContent = 'import * as client from "./client.js"; window.keysClient = client;';
  app.doc.head.append(script);
  await app.until(() => app.frame.contentWindow.keysClient, "the app's client");
  return app.frame.contentWindow.keysClient;
}

export default async function (app) {
  let client = await clientOf(app);
  const seen = {};
  for (const step of app.settings.plan || []) {
    if (step.until !== undefined) {
      await app.until(() => CONDITIONS[step.until](client), step.until, step.ms || 8000);
    } else if (step.untilKeys !== undefined) {
      // The keys of a storage of a generation, or of a number of entries.
      const kept = () => client.state.keys[step.untilKeys];
      await app.until(() => kept() !== null && (step.generation === undefined || kept().generation === step.generation) &&
        (step.entries === undefined || kept().entries === step.entries), `the keys of ${step.untilKeys}`, step.ms || 8000);
    } else if (step.untilCatalog !== undefined) {
      const part = () => (client.state.catalog === null ? null : client.state.catalog[step.untilCatalog]);
      await app.until(() => part() !== null && part().generation === step.generation, `a catalog of ${step.untilCatalog}`, step.ms || 8000);
    } else if (step.step === true) {
      await app.step();
    } else if (step.sleep !== undefined) {
      await app.sleep(step.sleep);
    } else if (step.reload === true) {
      await app.reload();
      client = await clientOf(app);
    } else if (step.untilRows !== undefined) {
      await app.until(() => app.doc.querySelectorAll("#animations-list > .row").length >= step.untilRows, `${step.untilRows} rows`, step.ms || 8000);
    } else if (step.enter !== undefined) {
      app.doc.querySelector(`#animations-list > .folder-row[data-path="${step.enter}"]`).click();
      await app.until(() => app.text("level-title") === step.enter, `the folder ${step.enter}`);
    } else if (step.press !== undefined) {
      app.press(step.press);
    } else if (step.address !== undefined) {
      app.press("Target");
      app.fill("address", step.address);
      app.press("Use");
      await app.until(() => app.kept() === step.address, "the new address kept");
      app.press("Animations");
    } else if (step.snap !== undefined) {
      seen[step.snap] = snapshot(client, app);
    } else if (step.say !== undefined) {
      seen[step.say] = app.text(step.id);
    }
  }
  return seen;
}
