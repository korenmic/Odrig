// Moves cut short and kept on the phone, the app opened while the board is in Clocks only:
// the settings' `jobs` are put in the phone's journal first. The scenario waits until the
// journal keeps the jobs of `kept`, and looks a while longer; then asks the test for its step,
// which leaves the mode, and waits until the journal is empty.
export const withoutTheApp = true;

const KEY = "odrig.moves";

function loaded(frame) {
  return new Promise((resolve) => frame.addEventListener("load", resolve, {once: true}));
}

function journal(address) {
  const all = JSON.parse(localStorage.getItem(KEY) || "{}");
  return (all[address] ?? []).map((job) => job.source.path);
}

export default async function (app) {
  const address = app.kept();
  localStorage.setItem(KEY, JSON.stringify({[address]: app.settings.jobs}));
  const first = loaded(app.frame);
  app.frame.src = "/index.html";
  document.body.append(app.frame);
  await first;
  const client = await app.frame.contentWindow.eval('import("/client.js")');
  await app.until(() => client.state.animations !== null && client.state.status?.clockMode === "only", "the list in Clocks only", 15000);
  const kept = JSON.stringify(app.settings.kept);
  await app.until(() => JSON.stringify(journal(address)) === kept, `the journal keeping ${kept}`, 15000);
  await app.sleep(1500);
  const seen = {only: {kept: journal(address), mode: client.state.status.clockMode, message: app.text("message-text")}};
  await app.step();
  await app.until(() => client.state.status?.clockMode !== "only", "Clocks only left", 15000);
  await app.until(() => journal(address).length === 0, "the journal emptied", 15000);
  seen.left = {mode: client.state.status.clockMode, message: app.text("message-text")};
  return seen;
}
