// The keys the app learns from the catalogs' pages, as its client holds them, followed
// through the plan the test gives: waits for a condition, steps of the test, sleeps,
// presses, another address, and a snapshot of the client by a name at each `snap`.

function keysOf(kept) {
  return kept === null ? null : {generation: kept.generation, entries: kept.entries, byName: Object.fromEntries(kept.byName)};
}

function snapshot(client) {
  return {
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
  "pages-refused": (client) => client.state.pagesRefused,
  "catalog-none": (client) => client.state.catalogNone,
  "no-answer": (client) => client.state.link === "no-answer",
  answers: (client) => client.state.link === "answers",
};

export default async function (app) {
  await app.until(() => app.shown() === "animations" && app.text("power") !== "-", "the show screen with a status");
  // The app's own client: a module script in the app's frame imports the same module the
  // app runs, and hands it over.
  const script = app.doc.createElement("script");
  script.type = "module";
  script.textContent = 'import * as client from "./client.js"; window.keysClient = client;';
  app.doc.head.append(script);
  await app.until(() => app.frame.contentWindow.keysClient, "the app's client");
  const client = app.frame.contentWindow.keysClient;
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
    } else if (step.press !== undefined) {
      app.press(step.press);
    } else if (step.address !== undefined) {
      app.press("Target");
      app.fill("address", step.address);
      app.press("Use");
      await app.until(() => app.kept() === step.address, "the new address kept");
      app.press("Animations");
    } else if (step.snap !== undefined) {
      seen[step.snap] = snapshot(client);
    } else if (step.say !== undefined) {
      seen[step.say] = app.text(step.id);
    }
  }
  return seen;
}
