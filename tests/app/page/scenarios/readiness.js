// The line of Animations that says how far the installation has read its animations after
// a start: each text it showed, in turn, until the one the test waits for, and whether
// the controls could be pressed while it read them.

export default async function (app) {
  await app.until(() => app.shown() === "animations" && app.text("power") !== "-", "the show screen with a status");
  const said = [];
  let pressable = true;
  await app.until(() => {
    const line = app.text("readiness");
    if (said.length === 0 || said[said.length - 1] !== line) {
      said.push(line);
    }
    if (line !== null && line.startsWith("Reading")) {
      const plays = [...app.doc.querySelectorAll("#animations-list > .row:not(.unavailable) .play")];
      pressable = pressable && ["power-toggle", "play-all", "level"].every((id) => !app.byId(id).disabled) && plays.every((button) => !button.disabled);
    }
    return line === app.settings.last;
  }, `the line ${JSON.stringify(app.settings.last)}`, 20000);
  return {said, pressable, fps: app.text("fps")};
}
