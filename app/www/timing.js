import * as client from "./client.js";
import * as commands from "./commands.js";
import {FIRST, UNTIL, currentZone, prepareZone, forgetZone} from "./time-zone.js";

const AUTO_KEY = "odrig.time.auto";
const CONFIRMED_KEY = "odrig.time.confirmed";
const COOLDOWN = 15 * 60 * 1000;
const ID = /^[A-Za-z0-9_-]{1,31}$/;

function phoneStorage() {
  try { return window.localStorage; } catch { return null; }
}

export function timingMessage(error) {
  const code = error?.code || error?.kind;
  if (code === "unsupported" || code === "unknown-command") return "Update the board firmware to use time and scheduled hours.";
  if (code === "busy") return "The installation is busy. Try again when the upload or catalog work finishes.";
  if (code === "stale") return "The connection or settings changed. Refresh and try again.";
  if (code === "storage-error") return "The installation could not save its time-zone or schedule settings.";
  if (code === "unconfirmed") return "The change could not be confirmed. Refresh before trying again.";
  if (code === "bad-argument") return "Check the phone's time and the selected hours, then try again.";
  if (code === "zone-unset") return "Set the board's time from this phone first.";
  if (error?.name === "ZoneFailure") return error.message;
  return "The installation's time could not be read or changed. Check the connection and try again.";
}

export function makeTiming({peer = client, wire = commands, prepare = prepareZone, zone = currentZone,
  cancelPreparation = forgetZone, now = () => Date.now(), store = phoneStorage(), visible = () => !document.hidden} = {}) {
  const kept = key => { try { return store?.getItem(key) ?? null; } catch { return null; } };
  const keep = (key, value) => { try { if (store === null) return false; store.setItem(key, value); return true; } catch { return false; } };
  const confirmations = new Map();
  try {
    const text = kept(CONFIRMED_KEY);
    const entries = text !== null && text.length <= 8192 ? JSON.parse(text) : [];
    if (Array.isArray(entries)) {
      for (const entry of entries.slice(-32)) {
        if (Array.isArray(entry) && entry.length === 2 && typeof entry[0] === "string" && ID.test(entry[0]) &&
            Number.isInteger(entry[1]) && entry[1] >= FIRST * 1000 && entry[1] < UNTIL * 1000) confirmations.set(...entry);
      }
    }
  } catch {}
  const state = {auto: kept(AUTO_KEY) !== "off", preferenceSaved: true, connected: false, supported: null,
    busy: false, phase: "waiting", clock: null, schedule: null, board: null, readAt: null,
    lastConfirmedAt: null, lastResult: null, message: null, error: null};
  const watchers = new Set();
  const changed = () => { for (const watcher of watchers) watcher(state); };
  let serial = 0;
  let seenTarget = -1;
  let seenConnection = -1;
  let seenZone = null;
  const context = () => ({serial: ++serial, target: peer.targetVersion(), connection: peer.state.connectionVersion});
  const current = ctx => ctx.serial === serial && ctx.target === peer.targetVersion() && ctx.connection === peer.state.connectionVersion;
  const queued = (ctx, action) => peer.timingOperation(action, ctx.target, () => current(ctx) && visible());
  const confirm = (board, at) => {
    confirmations.delete(board);
    confirmations.set(board, at);
    while (confirmations.size > 32) confirmations.delete(confirmations.keys().next().value);
    keep(CONFIRMED_KEY, JSON.stringify([...confirmations]));
    state.lastConfirmedAt = at;
  };
  const due = (board, at) => {
    const last = confirmations.get(board);
    return last === undefined || at < last || at - last >= COOLDOWN;
  };
  const readPair = async ctx => queued(ctx, async step => {
    const clock = await step(() => wire.timeRead());
    if (clock.board === null) throw new commands.Refusal("unsupported", "timing target");
    const schedule = await step(() => wire.scheduleRead(clock.board));
    return {clock, schedule};
  });

  async function run({sync = false, force = false, replace = false, zoneOnly = false} = {}) {
    if (!state.connected || state.supported !== true || !visible() || (state.busy && !replace)) return false;
    if (sync) {
      try { seenZone = zone(); } catch {}
    }
    const ctx = context();
    state.busy = true;
    state.phase = "reading";
    state.error = null;
    state.lastResult = null;
    state.message = null;
    changed();
    try {
      const initial = await readPair(ctx);
      if (!current(ctx)) return false;
      state.clock = initial.clock;
      state.schedule = initial.schedule;
      state.board = initial.clock.board;
      state.readAt = now();
      state.lastConfirmedAt = confirmations.get(state.board) ?? null;
      state.lastResult = "read";
      if (!sync) {
        state.message = state.auto ? "Board time refreshed." : "Automatic time sync is off.";
        state.phase = "ready";
        return true;
      }
      state.phase = "preparing";
      changed();
      const phoneZone = zone();
      seenZone = phoneZone;
      const rules = await prepare(phoneZone);
      if (!current(ctx)) return false;
      if (zone() !== phoneZone) throw new commands.Refusal("stale", "phone time zone");
      const board = initial.clock.board;
      const setClock = !zoneOnly && (force || !initial.clock.valid || due(board, now()));
      const setZone = initial.clock.revision !== rules.revision;
      state.phase = "synchronizing";
      changed();
      const clock = await queued(ctx, async step => {
        if (setZone) await step(() => wire.timeZone(board, rules.base64));
        if (setClock) {
          const utc = Math.floor(now() / 1000);
          if (utc < FIRST || utc >= UNTIL) throw new commands.Refusal("bad-argument", "phone time");
          await step(() => wire.timeSet(board, utc, rules.revision));
        }
        const result = setClock || setZone ? await step(() => wire.timeRead(board)) : initial.clock;
        if (result.board !== board || result.revision !== rules.revision || (!zoneOnly && !result.valid) ||
            (setClock && Math.abs(now() / 1000 - result.utc) > 5)) throw new commands.Refusal("unconfirmed", "phone time");
        return result;
      });
      if (!current(ctx)) return false;
      state.clock = clock;
      state.readAt = now();
      if (setClock) confirm(board, now());
      state.lastResult = setClock ? "synchronized" : setZone ? "zone-updated" : "current";
      state.message = setClock ? "Board time synchronized with this phone." : setZone ? "Board time zone updated from this phone." : "Board time is already up to date.";
      state.schedule = await queued(ctx, step => step(() => wire.scheduleRead(board)));
      if (!current(ctx)) return false;
      state.phase = "ready";
      return true;
    } catch (error) {
      if (current(ctx)) {
        state.error = timingMessage(error);
        state.phase = "error";
      }
      return false;
    } finally {
      if (current(ctx)) { state.busy = false; changed(); }
    }
  }

  async function changeSchedule(draft, resume = false) {
    if (!state.connected || !state.supported || state.busy || !visible() ||
        draft.board !== state.board || state.schedule === null) return false;
    const ctx = context();
    state.busy = true;
    state.phase = resume ? "resuming" : "saving";
    state.error = null;
    state.message = null;
    state.lastResult = null;
    changed();
    try {
      const result = await queued(ctx, async step => {
        if (resume) await step(() => wire.scheduleResume(draft.board, draft.revision));
        else await step(() => wire.scheduleSet(draft.board, draft.revision, draft.on, draft.off, draft.enabled));
        return step(() => wire.scheduleRead(draft.board));
      });
      if (!current(ctx)) return false;
      state.schedule = result;
      if (!result.saved || result.on !== draft.on || result.off !== draft.off || result.enabled !== draft.enabled ||
          (resume && result.override !== null)) throw new commands.Refusal("unconfirmed", "schedule");
      state.phase = "ready";
      state.lastResult = resume ? "schedule-resumed" : "schedule-saved";
      state.message = resume ? "Schedule resumed." : "Saved scheduled hours.";
      return true;
    } catch (error) {
      if (current(ctx)) { state.error = timingMessage(error); state.phase = "error"; }
      return false;
    } finally {
      if (current(ctx)) { state.busy = false; changed(); }
    }
  }

  const api = {
    state,
    watch(watcher) { watchers.add(watcher); watcher(state); },
    refresh() { return run(); },
    syncNow() { return run({sync: true, force: true}); },
    saveSchedule(draft) { return changeSchedule(draft); },
    resumeSchedule() {
      return state.schedule === null ? Promise.resolve(false) :
        changeSchedule({...state.schedule, board: state.board}, true);
    },
    setAuto(value) {
      if (typeof value !== "boolean") return;
      serial += 1;
      state.auto = value;
      state.busy = false;
      state.preferenceSaved = keep(AUTO_KEY, value ? "on" : "off");
      state.error = null;
      state.phase = state.clock === null ? "waiting" : "ready";
      state.message = value ? "Automatic time sync is on." : "Automatic time sync is off.";
      if (!value) cancelPreparation();
      changed();
      if (value) void run({sync: true});
    },
    suspend() {
      serial += 1;
      state.busy = false;
      state.phase = "waiting";
      cancelPreparation();
      changed();
    },
  };

  peer.watch(source => {
    const target = peer.targetVersion();
    if (target !== seenTarget) {
      serial += 1;
      seenTarget = target;
      seenConnection = -1;
      Object.assign(state, {busy: false, clock: null, schedule: null, board: null, readAt: null,
        lastConfirmedAt: null, lastResult: null, message: null, error: null, phase: "waiting", supported: null});
    }
    state.connected = source.link === "answers" && source.statusFresh;
    if (state.connected) state.supported = source.status?.timing === true;
    const connecting = state.connected && seenConnection !== source.connectionVersion;
    if (connecting) {
      serial += 1;
      seenConnection = source.connectionVersion;
      Object.assign(state, {busy: false, clock: null, schedule: null, board: null, readAt: null,
        lastConfirmedAt: null, lastResult: null, message: null, error: null, phase: "waiting"});
    }
    changed();
    if (!connecting) {
      if (state.connected && state.supported && state.auto && !state.busy && visible()) {
        try {
          if (zone() !== seenZone) void run({sync: true, zoneOnly: true});
        } catch (error) {
          state.error = timingMessage(error);
          state.phase = "error";
          changed();
        }
      }
      return;
    }
    if (!state.supported) { state.phase = "unsupported"; changed(); return; }
    void run({sync: state.auto, replace: true});
  });
  return api;
}

export const timing = makeTiming();

document.addEventListener("visibilitychange", () => {
  timing.suspend();
});
