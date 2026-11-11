// The jobs of moves, worked without the app against a board the scenario plays: in each case
// the board answers each line by the first of its rules whose pattern the line matches, and
// the case gives what the job came to, the lines sent and what the phone's journal keeps.

export const withoutTheApp = true;

const ADDRESS = "4.3.2.1";
const KEY = "odrig.moves";

// The board of a case: a rule is `{line, reply, times}`, a reply `null` for none, and a rule
// used `times` times at most when it gives them.
function board(rules, sent) {
  window.Capacitor = {
    isNativePlatform: () => true,
    nativePromise: async (plugin, method, {line}) => {
      sent.push(line);
      const rule = rules.find((each) => (each.times ?? 1) > 0 && new RegExp(each.line).test(line));
      if (rule !== undefined && rule.times !== undefined) rule.times -= 1;
      if (rule === undefined || rule.reply === null) throw {code: "no-answer"};
      return {status: 200, body: JSON.stringify(rule.reply)};
    },
  };
}

// A folder `night` of the card with two files, as `subtree` gives it.
function night() {
  const folder = {id: 60010, playlist: "night", external: true, ignored: false};
  const files = [1, 2].map((n) => ({id: 60020 + n, file: `night/f${n}.odrg`, external: true, bytes: 100, ignored: false}));
  return {folders: [folder], files};
}

function kept() {
  const all = JSON.parse(localStorage.getItem(KEY) || "{}");
  return (all[ADDRESS] ?? []).map((job) => ({kind: job.kind ?? "file", path: job.source.path, files: job.files?.map((file) => file.source.id) ?? null}));
}

function described(error) {
  if (error === null || error === undefined) return null;
  return error.code ?? error.kind ?? error.message;
}

export default async function (app) {
  localStorage.setItem("odrig.target", ADDRESS);
  const moves = await import("/moves.js");
  const client = await import("/client.js");
  const operation = (kind, carry) => carry();
  const context = (more = {}) => ({client: {operation, Withdrawn: client.Withdrawn}, address: ADDRESS, report: () => {}, stopped: () => false, ...more});
  const day = {storage: "external", folder: "day"};
  const cases = {};

  async function run(name, rules, work, journal = []) {
    localStorage.setItem(KEY, JSON.stringify({[ADDRESS]: journal}));
    const sent = [];
    board(rules, sent);
    let result;
    let error = null;
    try {
      result = await work(sent);
    } catch (thrown) {
      error = described(thrown);
    }
    cases[name] = {result, error, sent, kept: kept()};
  }

  const listRules = [
    {line: "^list 0$", reply: {ok: true, items: [{id: 60010, playlist: "night", external: true, files: 2, ignored: false, inherited_ignored: false}], next: null}},
    {line: "^list in 60010 0$", reply: {ok: true, items: night().files.map((file) => ({...file, type: "frames"})), next: null}},
  ];

  await run("cut after the folder is made", [{line: "^folder make", reply: {ok: true, id: 60100, made: true}}],
    async () => {
      const done = await moves.moveFolder(moves.folderPlan(night(), day, []), context());
      return {moved: done.moved, failed: done.failed.length, unstarted: done.unstarted, cut: described(done.cut)};
    });

  await run("the folder refused", [{line: "^folder make", reply: {ok: false, error: "read-only"}}],
    () => moves.moveFolder(moves.folderPlan(night(), day, []), context()));

  const refusedJob = {kind: "folder", source: {id: 60010, storage: "external", path: "night"}, destination: {storage: "external", path: "day/night"},
    folders: [{path: "day/night", ignored: false}], files: night().files.map((source) => ({source, storage: "external", folder: "day/night", name: source.file.slice(6), path: `day/${source.file}`}))};
  await run("a kept job whose folder is refused", [{line: "^folder make", reply: {ok: false, error: "unknown-id"}}],
    async () => {
      const done = await moves.reconcile(context());
      return {finished: done.finished, notMoved: done.notMoved, givenUp: (done.givenUp ?? []).map((each) => [each.path, described(each.error)])};
    }, [refusedJob]);

  await run("a kept job whose files are refused", [{line: "^folder make", reply: {ok: true, id: 60100, made: false}}, ...listRules, {line: "^move external", reply: {ok: false, error: "in-use"}, times: 9}],
    async () => {
      const done = await moves.reconcile(context());
      return {finished: done.finished, failed: (done.failed ?? []).map((each) => [each.file, described(each.error)])};
    }, [refusedJob]);

  await run("a kept job stopped by another target", [{line: "^folder make", reply: {ok: true, id: 60100, made: false}}, ...listRules, {line: "^move external", reply: {ok: true, id: 60021, moved: true}, times: 9}],
    async (sent) => {
      // Another target is chosen once the first file has moved.
      const switched = () => sent.some((line) => line.startsWith("move external"));
      const done = await moves.reconcile(context({stopped: switched, switched}));
      return {finished: done.finished, cut: done.cut ?? null};
    }, [refusedJob]);

  await run("a lost reply of a move on the card", [{line: "^move external 60021 day$", reply: null, times: 1}, {line: "^move external 60021 day$", reply: {ok: true, id: 60021, moved: true}}],
    () => moves.move(moves.plan([night().files[0]], day, [])[0], context()));

  const shows = {folders: [{id: 5, playlist: "night", external: false, ignored: false}], files: []};
  const first = moves.folderPlan(night(), day, []);
  const second = moves.folderPlan(shows, day, [], new Map(), new Map(), [first.name]);
  cases["two folders of one name"] = {first: first.skip, second: second.skip};
  return cases;
}
