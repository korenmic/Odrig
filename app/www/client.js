// What the replies told, and the order in which requests are sent. One request is under
// way at a time. The state holds only what a reply said.

import * as commands from "./commands.js";
import {Failure, address} from "./target.js";

const STATUS_EVERY_MS = 1000;
const LIST_EVERY_MS = 10000;
const LIST_WHEN_BUSY_MS = 1000;
const SPACE_EVERY_MS = 10000;
// How long a page of a catalog that was refused with `busy` waits before it is asked again.
const PAGE_AGAIN_MS = 2000;
const STORAGES = ["internal", "external"];
const PAGES = 16;
// A line of a catalog's page: the CRC-32, the size, the canvas, the length, the type and the
// name of a file.
const CATALOG_LINE = /^([0-9a-f]{8}) ([0-9]+) [0-9]+ [0-9]+ [0-9]+ [a-z]+ (.+)$/;

// `link` is "checking" until the first request has ended, then "answers" or "no-answer",
// with the Failure in `failure`. `status` is the newest reply to `status`, `heardAt` the
// time of the newest reply of any kind, `since` the time the app began with this address,
// and `answered` whether the target of this address has answered at least once. `level` is
// the level of the folders the list is of, `{path, id, storage}`, "", null and null for the
// root, which holds the show's items too, `storage` "internal" for a folder of the board's
// own storage and "external" for one of the card; nothing of another level is kept. `animations` is the
// animation items of the level's newest complete list, in its order, each as
// `{id, file, bytes}` with optional `ignored`, or null while there is none; `cycles` is the
// ids of its cycles, and `folders` its folders of either storage, each `{id, playlist, files}` with
// its path and the number of its own files, in the order they play. `rootNames` holds what
// the root's newest list named, `{ids, files}`, the ids and the file names of the show's
// items, of the root's folders and of the root's files, which an upload chooses its id and
// its name against, and whether the board's own storage has folders, or null while none is
// known. `space` holds internal and external capacity from the newest reply, or
// null while none came from this address or the newest said the capacity is unknown; a request
// that fails leaves it.
// In Clocks only, on a target that plays the clocks of both storages, `level` may be the
// Clocks level, `{path: "", id: null, storage: null, clocks: true}`: the root's list with only
// its two Clocks folders, one of each storage. `rootNames.clocks` holds the ids of the root's
// Clocks folders, `{internal, external}`, each null when that storage has none.
// `listBusy` says whether the newest `list` request was answered `busy`. `order` is the
// saved playlist order that goes with the newest list, `{ids, revision}`, or null while
// there is none; `orderKnown` is false when the target has no saved order, an older one.
// `catalog` is the newest reply of `catalog`, or null. `keys` holds, for each storage, the
// keys of its files learnt from its catalog's pages, `{generation, entries, byName}`, or
// null while none is known; `keysVersion` grows when they change. `catalogNone` says that
// the target keeps no catalogs, and `pagesRefused` that it reads no page of one: a target
// from before either. `statusCount` counts the replies to `status`, so that a screen can wait
// for the first one after a command. `statusFresh` requires a valid status after the
// latest communication failure; replies to other commands cannot restore it.
// `onlyUnavailable` marks a Clocks location whose current folder ID cannot be resolved.
export const state = {link: "checking", failure: null, status: null, heardAt: null, since: Date.now(), answered: false, level: {path: "", id: null, storage: null}, rootNames: null,
  animations: null, cycles: [], folders: [], space: null,
  listVersion: 0, listBusy: false, order: null, orderVersion: 0, orderKnown: true, catalog: null, keys: {internal: null, external: null}, keysVersion: 0,
  catalogNone: false, pagesRefused: false, statusCount: 0, statusFresh: false, connectionVersion: 0, onlyUnavailable: false};

const watchers = new Set();
// What the operator asked for and was not sent yet, in its order: each a kind and the
// function that carries it to the target.
const wanted = [];
// Told of every refusal of what the operator asked for.
let refused = () => {};
let underWay = false;
let statusDue = false;
let statusTimer = null;
let listDue = false;
let listTimer = null;
// The list that is being asked for in parts: the items so far and the position to ask
// for next. Null when none is.
let listing = null;
// The folders entered from the root down to the level shown, each `{path, id, storage}`.
const trail = [];
let onlyActive = false;
let onlyFolder = null;
let onlyDesired = "clocks";
// Whether the target of the confirmed Only plays the clocks of both storages, as its
// `clock_storage` tells: the Clocks subtree of the board's own storage is inside the
// boundary then, beside the card's.
let onlyBoth = false;
// The step of the trail, and the level, of the Clocks level.
const CLOCKS_LEVEL = Object.freeze({path: "", id: null, storage: null, clocks: true});
// The rows of files of a Clocks subtree that lists named, by id, `{file, external}`; the
// files a status named whose rows are asked for in the background, `{id, file}`, or null;
// and those asked for once already, as `<id> <file>`.
const clockRows = new Map();
let clockAsk = null;
const clockAsked = new Set();
// Whether the root's names are due while another level is shown, and the root's list that
// is being asked for in parts for them: the ids and the files so far and the position to
// ask for next.
let rootDue = false;
let rooting = null;
// The animation a status named that the list did not have, for which the list was asked.
let askedFor = null;
// Whether the saved order is due after a complete list, and the order that is being asked
// for in parts: the ids so far, the position to ask for next and the revision of the
// first part.
let orderDue = false;
let ordering = null;
// Whether a list has waited while a status was sent. It goes before the next status
// then, so that a target that answers slowly does not keep the list away.
let listWaited = false;
// Whether Animations, or Upload, is the screen on the screen of the phone: both use the
// list and the capacity.
let showScreen = false;
let storageScreen = false;
let spaceDue = false;
let spaceTimer = null;
// The upload under way, a job of `upload.js`, or null.
let job = null;
// Whether `catalog` is due, the reads of catalogs' pages that wait, the first under way,
// internal before external, and the timer of a page that waits after `busy`.
let catalogDue = false;
const reads = [];
let pageWait = null;
// Where the keys of the catalogs are kept between two starts of the app, the address they are
// kept under, and whether those of earlier starts have been taken: no page of a catalog is
// asked before.
let keeper = {kept: () => null, keep: () => {}, forget: () => {}, placed: () => null, place: () => {}, unplace: () => {}, unlisted: () => {}};
let keptUnder = null;
let keptTaken = false;
// The stored name of each file of a folder of the board's own storage that a list named, by
// its path: its catalog names it so.
const storedNames = new Map();
// Counts the targets: a reply that belongs to an earlier address is dropped.
let target = 0;
let connectionDue = true;
// Who holds the content lock, which keeps an upload, a check of its destination, a
// deletion, a download and a move apart: "preflight" while the Upload screen checks a
// destination, "deletion" while the selection removes animations, "download" while files are
// read back to be saved, "move" while files are moved, or null.
let holder = null;
// Whether the target takes `read <id> <offset> <count>`, as `{target, counts}` of the target
// that told it, or null until a read found out.
let readForm = null;

// Calls a function now and whenever the state changes.
export function watch(watcher) {
  watchers.add(watcher);
  watcher(state);
}

function changed() {
  for (const watcher of watchers) {
    watcher(state);
  }
}

// Forgets the keys of every storage and every read of a page.
function dropKeys() {
  reads.length = 0;
  clearTimeout(pageWait);
  pageWait = null;
  if (state.keys.internal !== null || state.keys.external !== null) {
    state.keys = {internal: null, external: null};
    state.keysVersion += 1;
  }
}

function heard() {
  if (state.link !== "answers") {
    // The target answers, for the first time or again: what it has installed is asked, and
    // its catalogs, whose keys may be of another storage now.
    listDue = true;
    listing = null;
    spaceDue = true;
    dropKeys();
    catalogDue = !state.catalogNone && !state.pagesRefused;
  }
  state.link = "answers";
  state.failure = null;
  state.heardAt = Date.now();
  state.answered = true;
}

// A request got no reply, or none of the installation. What the last replies said stays,
// the capacity among it, shown stale while the link is down.
function failed(error) {
  if (!(error instanceof Failure)) {
    throw error;
  }
  state.link = "no-answer";
  state.failure = error;
  state.statusFresh = false;
}

// Shows the Clocks location as unavailable: no rows, and nothing of another folder in their
// place.
function unavailableClocks() {
  if (state.level.path === "clocks" && state.level.id === null) return;
  trail.splice(0, trail.length, {path: "clocks", id: null});
  toLevel();
}

// The storage of the Clocks folder a status names by its id: the board's own for an id of
// 60,000 or less on a target that plays the clocks of both storages, else the card's.
function storageOfClockId(id) {
  return onlyBoth && id !== null && id <= 60000 ? "internal" : "external";
}

// The step of the trail of the Clocks folder of this id.
function clockStep(id) {
  return storageOfClockId(id) === "internal" ? {path: "clocks", id, storage: "internal"} : {path: "clocks", id};
}

// The Clocks folders of both storages, `{internal, external}`, when the root's newest list
// names one of each on a target in Only that plays the clocks of both; else null.
function bothClockFolders() {
  const found = state.rootNames?.clocks;
  return onlyActive && onlyBoth && found != null && found.internal !== null && found.external !== null ? found : null;
}

// Whether a step of the trail is one of the two Clocks folders of the Clocks level.
function oneOfBoth(step) {
  const both = bothClockFolders();
  return both !== null && step?.path === "clocks" && step.id !== null && step.id === both[step.storage === "internal" ? "internal" : "external"];
}

// The trail that begins at a Clocks folder: under the Clocks level when it is one of two.
function clocksTrail(step) {
  return oneOfBoth(step) ? [CLOCKS_LEVEL, step] : [step];
}

// Where Only opens: the Clocks level while both storages have a Clocks folder, the one the
// status names and the other storage's that the root's newest list names; else the folder the
// status names. The Clocks level's own list then tells whether both are still there.
function openClocks() {
  const step = clockStep(onlyFolder);
  const other = step.storage === "internal" ? "external" : "internal";
  return onlyActive && onlyBoth && onlyFolder !== null && (state.rootNames?.clocks?.[other] ?? null) !== null ? [CLOCKS_LEVEL] : [step];
}

// Whether two steps of the trail are one folder: one id of one storage.
function sameFolder(one, other) {
  return one.id === other.id && (one.storage === "internal") === (other.storage === "internal");
}

// The Clocks folder that remains when the root's newest list does not name one of each
// storage: the one the status names while the list names it too, else the one the list
// names, else the one the status names.
function remainingClocks() {
  const found = state.rootNames?.clocks ?? {internal: null, external: null};
  const named = clockStep(onlyFolder);
  if (found[named.storage === "internal" ? "internal" : "external"] === named.id) return named;
  if (found.internal !== null) return {path: "clocks", id: found.internal, storage: "internal"};
  if (found.external !== null) return {path: "clocks", id: found.external};
  return named;
}

// Fits the trail of Only to the root's newest list: under a trail that begins at one of the
// two Clocks folders the Clocks level is put, the level shown staying; a trail of the Clocks
// level goes back to the Clocks level when its folder is not one of the two the list names,
// and when the list no longer names both, to the Clocks folder that remains, a level below
// that folder staying.
function fitClocks() {
  if (!onlyActive || !onlyBoth || onlyFolder === null || trail.length === 0) return;
  const bottom = trail[0];
  if (bottom.clocks !== true) {
    if (oneOfBoth(bottom)) trail.unshift(CLOCKS_LEVEL);
    return;
  }
  const both = bothClockFolders();
  if (both !== null && (trail.length === 1 || oneOfBoth(trail[1]))) return;
  const top = trail[trail.length - 1];
  if (both !== null) trail.splice(0, trail.length, CLOCKS_LEVEL);
  else {
    const remaining = remainingClocks();
    if (trail.length > 1 && sameFolder(trail[1], remaining)) trail.shift();
    else trail.splice(0, trail.length, remaining);
  }
  if (trail[trail.length - 1] !== top) toLevel();
}

// Takes the clock mode a status confirms. In Only, browsing stays inside the Clocks folder
// the target names: entering Only opens it, a valid location inside it stays, and a status
// that names no folder shows it unavailable. On a target that plays the clocks of both
// storages the board's own Clocks folder is inside too, and while both have one, Only opens
// the Clocks level above the two. A status without mode metadata changes nothing; a
// confirmed Off or Between releases the bound.
function reconcileOnly(reply) {
  if (reply.hasClockMode && ["off", "between"].includes(reply.clockMode)) {
    onlyActive = false;
    onlyFolder = null;
    onlyDesired = "clocks";
    onlyBoth = false;
    state.onlyUnavailable = false;
    if (trail[0]?.clocks === true) {
      trail.shift();
      if (trail.length === 0) {
        toLevel();
        return;
      }
    }
    if (state.level.path !== "" && state.level.id === null) {
      trail.length = 0;
      toLevel();
    }
    return;
  }
  if (reply.clockMode !== "only") return;
  const entering = !onlyActive;
  const before = onlyFolder;
  const bothBefore = onlyBoth;
  onlyActive = true;
  onlyFolder = reply.clockOnly.folder;
  onlyBoth = reply.hasClockStorage === true;
  if (entering) onlyDesired = "clocks";
  if (onlyFolder === null) {
    unavailableClocks();
  } else if (entering || bothBefore !== onlyBoth || !inClocks(state.level)) {
    trail.splice(0, trail.length, ...openClocks());
    toLevel();
  } else if (before !== onlyFolder && onlyBoth && (trail[0]?.clocks === true || bothClockFolders() !== null ||
      storageOfClockId(onlyFolder) === "internal" || (trail[0]?.storage ?? "external") !== "external")) {
    // Another folder of either storage: the Clocks level, or the folder named now.
    trail.splice(0, trail.length, ...openClocks());
    toLevel();
  } else if (before !== onlyFolder && state.level.id === null) {
    // The unavailable location is resolved again under the folder the target names now.
    listing = null;
    listDue = true;
  } else if (before !== onlyFolder) {
    trail[0] = clockStep(onlyFolder);
    if (state.level.path === "clocks") toLevel();
    else {
      listing = null;
      listDue = true;
    }
  }
  if (onlyBoth && onlyFolder !== null && state.level.clocks !== true && (entering || before !== onlyFolder || !bothBefore)) {
    // The root's list tells whether the other storage has a Clocks folder too.
    rootDue = true;
  }
}

function takeStatus(reply) {
  heard();
  state.status = reply;
  state.statusFresh = true;
  state.statusCount += 1;
  if (connectionDue) {
    connectionDue = false;
    state.connectionVersion += 1;
  }
  reconcileOnly(reply);
  const named = reply.animation;
  // A file of a Clocks subtree of the other storage than the level's, which shares its path, is
  // not of the level shown.
  const from = clockStorageOf(reply);
  const here = typeof reply.file === "string" && parentOf(reply.file) === state.level.path && (state.level.id === null || reply.file.includes("/")) &&
    (from === null || from === (state.level.storage === "internal" ? "internal" : "external"));
  if (named !== null && state.animations !== null && named !== askedFor && here && !state.animations.some((animation) => animation.id === named)) {
    // The target plays an animation of the level shown that its list does not have.
    askedFor = named;
    listDue = true;
  }
  if (clockAsk === null && from === null && reply.hasClockStorage === true && typeof reply.file === "string" &&
      inClocks(reply.file) && typeof named === "number" && state.animations !== null && listing === null && !listDue &&
      !clockAsked.has(`${named} ${reply.file}`)) {
    // A file of a Clocks subtree whose row no list named: the storage it plays from is
    // asked for once, in the lists of its folder of each storage.
    clockAsked.add(`${named} ${reply.file}`);
    clockAsk = {id: named, file: reply.file};
  }
  const playing = reply.playing;
  if (typeof playing === "number" && typeof reply.playlist === "string" && parentOf(reply.playlist) === state.level.path && state.animations !== null &&
    playing !== askedFor && !state.folders.some((folder) => folder.id === playing)) {
    // The target plays a playlist of this level that its list does not have: a folder of a
    // card just put in.
    askedFor = playing;
    listDue = true;
  }
}

async function askStatus() {
  const asked = target;
  clearTimeout(statusTimer);
  statusTimer = setTimeout(() => {
    statusDue = true;
    next();
  }, STATUS_EVERY_MS);
  try {
    const reply = await commands.status();
    if (asked !== target) {
      return;
    }
    takeStatus(reply);
  } catch (error) {
    if (asked !== target) {
      return;
    }
    connectionDue = true;
    failed(error);
  }
  changed();
}

function listAgainLater(after = LIST_EVERY_MS) {
  clearTimeout(listTimer);
  listTimer = setTimeout(() => {
    listTimer = null;
    if (showScreen || storageScreen) {
      listDue = true;
      // Inside a Clocks folder of Only the root's list says whether both storages still
      // have one, or have one now.
      if (onlyActive && onlyBoth && state.level.clocks !== true) rootDue = true;
      next();
    }
  }, after);
}

// Capacity is asked for periodically while Animations or Upload is visible.
function spaceAgainLater() {
  clearTimeout(spaceTimer);
  spaceTimer = setTimeout(() => {
    spaceTimer = null;
    if (showScreen || storageScreen) {
      spaceDue = true;
      next();
    }
  }, SPACE_EVERY_MS);
}

async function askSpace() {
  const asked = target;
  try {
    const reply = await commands.space();
    if (asked !== target) {
      return;
    }
    heard();
    state.space = reply;
  } catch (error) {
    if (asked !== target) {
      return;
    }
    if (error instanceof commands.Refusal) {
      // The target answers and cannot tell its space.
      heard();
      state.space = null;
    } else {
      failed(error);
    }
  }
  spaceAgainLater();
  changed();
}

// The parent of a path of the card: the part before its last `/`, "" for the root.
function parentOf(path) {
  return path.includes("/") ? path.slice(0, path.lastIndexOf("/")) : "";
}

// Whether a path, or a level or a trail's step `{path, storage}`, is a Clocks folder or inside
// one; the Clocks level is. A folder of the board's own storage is inside only on a target
// that plays the clocks of both storages: on another the Clocks folder of Clocks only is
// the card's, whatever the path of a folder of the board's own storage.
function inClocks(where) {
  if (where !== null && typeof where === "object") {
    if (where.clocks === true) return true;
    if (where.storage === "internal" && !onlyBoth) return false;
    return inClocks(where.path);
  }
  return where === "clocks" || typeof where === "string" && where.startsWith("clocks/");
}

// What an upload chooses its id and its name against, from the items of the root's list,
// and the ids of the root's Clocks folders of each storage.
function namesOf(items) {
  const clocksOf = (external) => items.find((item) => item.playlist === "clocks" && (item.external !== false) === external)?.id ?? null;
  return {ids: items.map((item) => item.id), files: items.filter((item) => typeof item.file === "string").map((item) => item.file),
    internal: items.some((item) => typeof item.playlist === "string" && item.external === false),
    clocks: {internal: clocksOf(false), external: clocksOf(true)}};
}

// Notes the rows of files of a Clocks subtree that a list named.
function noteClockRows(items) {
  for (const item of items) {
    if (typeof item.file === "string" && inClocks(item.file)) clockRows.set(item.id, {file: item.file, external: item.external === true});
  }
}

// The storage of the file a status names when it is of a Clocks subtree, on a target that
// plays the clocks of both storages: "internal" or "external", by the row of its id that a
// list named, an id of 60,000 or less being the board's own; null when the row is not known,
// on another target, or for a file of no Clocks subtree.
export function clockStorageOf(status) {
  if (status?.hasClockStorage !== true || typeof status.file !== "string" || !inClocks(status.file) || typeof status.animation !== "number") return null;
  const row = (state.animations ?? []).find((item) => item.id === status.animation && item.file === status.file) ?? clockRows.get(status.animation);
  if (row !== undefined && row.file === status.file) return row.external === true ? "external" : "internal";
  return status.animation <= 60000 ? "internal" : null;
}

// The storage of a folder's row: "internal" for one of the board's own storage.
function storageOf(row) {
  return row.external === false ? "internal" : "external";
}

// Every id of the board's own storage: those of the root's rows, and those of the rows of
// each of its folders, walked level by level through `list`.
async function idsWithin(root, list) {
  const ids = root.map((row) => row.id);
  const pending = root.filter((row) => typeof row.playlist === "string" && row.external === false).map((row) => row.id);
  while (pending.length > 0) {
    const folder = pending.shift();
    let from = 0;
    do {
      const reply = await list(from, folder);
      for (const row of reply.items) {
        ids.push(row.id);
        if (typeof row.playlist === "string" && row.external === false) pending.push(row.id);
      }
      from = reply.next;
    } while (from !== null);
  }
  return ids;
}

// Resolve the captured path without changing the visible level. A failed lookup
// or an unavailable catalog does not establish that the folder was removed. Inside Clocks
// in Only, the path is resolved only while the target names a Clocks folder.
async function recoverLevel(asked, level, fromRoot = false) {
  const bounded = onlyActive && inClocks(level);
  const current = () => asked === target && level === state.level && (!bounded || onlyFolder !== null);
  const found = [];
  let path = "";
  let parent = null;
  const desired = bounded && level.id === null ? onlyDesired : level.path;
  let names = desired.split("/");
  // The Clocks folder of the level's storage, when it is known: the one the status names, or
  // the other storage's that the root's list named.
  const storage = level.storage === "internal" ? "internal" : "external";
  const clocksId = !bounded || onlyFolder === null ? null :
    storageOfClockId(onlyFolder) === storage ? onlyFolder : state.rootNames?.clocks?.[storage] ?? null;
  const knownRoot = bounded && !fromRoot && level.id !== null && desired !== "clocks" && clocksId !== null;
  if (knownRoot) {
    path = "clocks";
    parent = clocksId;
    found.push(storage === "internal" ? {path, id: parent, storage} : {path, id: parent});
    names = names.slice(1);
  }
  try {
    for (const name of names) {
      path += (path ? "/" : "") + name;
      let from = 0;
      let folder = null;
      do {
        const reply = await commands.list(from, parent);
        if (!current()) return;
        folder = reply.items.find(item => typeof item.playlist === "string" && item.playlist === path && storageOf(item) === (level.storage ?? "external")) ?? null;
        from = reply.next;
      } while (folder === null && from !== null);
      if (folder === null) {
        let catalog = null;
        try { catalog = await commands.catalog(); } catch (error) {
          if (!(error instanceof commands.Refusal && ["unknown-command", "bad-argument"].includes(error.code))) throw error;
        }
        if (!current()) return;
        const authoritative = level.storage === "internal" || catalog === null || ["ok", "absent", "none"].includes(catalog.external.state);
        if (bounded) {
          heard();
          if (authoritative && found.length > 0) {
            onlyDesired = "clocks";
            trail.splice(0, trail.length, ...clocksTrail(found[0]));
            toLevel();
            return;
          }
          if (authoritative && storageOfClockId(onlyFolder) !== storage) {
            // The level's Clocks folder is gone; the other storage's, which the status names,
            // is where Only opens.
            onlyDesired = "clocks";
            trail.splice(0, trail.length, ...openClocks());
            toLevel();
            return;
          }
          unavailableClocks();
          break;
        }
        if (authoritative) {
          heard();
          trail.length = 0;
          toLevel();
          return;
        }
        break;
      }
      found.push({path, id: folder.id, storage: level.storage ?? "external"});
      parent = folder.id;
    }
    if (found.length === desired.split("/").length) {
      trail.splice(0, trail.length, ...clocksTrail(found[0]), ...found.slice(1));
      if (parent !== level.id || desired !== level.path) {
        heard();
        toLevel();
        return;
      }
    }
    heard();
  } catch (error) {
    if (!current()) return;
    if (knownRoot && error instanceof commands.Refusal && error.code === "unknown-id") {
      return recoverLevel(asked, level, true);
    }
    if (bounded) unavailableClocks();
    if (error instanceof commands.Refusal) heard();
    else failed(error);
  }
  listing = null;
  state.listBusy = state.level.id !== null;
  listAgainLater(LIST_WHEN_BUSY_MS);
  changed();
}

// Asks for one part of the list of the level shown. The new list takes the place of the
// old one only when its last part has come; when a part fails, the old list stays. A
// missing folder is resolved against its current ancestry before the view changes.
async function askListPart() {
  const asked = target;
  const level = state.level;
  const part = listing === null ? {items: [], from: 0, began: performance.now()} : listing;
  listing = null;
  // The Clocks level is the root's list, of which it shows only the two Clocks folders.
  const clocksLevel = level.clocks === true;
  if (onlyActive && level.id === null && !clocksLevel) return;
  try {
    const reply = await commands.list(part.from, level.id);
    if (asked !== target || level !== state.level) {
      return;
    }
    heard();
    if (onlyActive && !clocksLevel && reply.items.some(item => !inClockFolder(item) ||
        parentOf(item.playlist ?? item.file) !== level.path)) {
      state.listBusy = true;
      listAgainLater(LIST_WHEN_BUSY_MS);
      changed();
      return;
    }
    const items = part.items.concat(reply.items);
    if (reply.next !== null) {
      listing = {items, from: reply.next, began: part.began};
    } else {
      // The places this phone uploaded to that the complete list of their folder does not
      // name are dropped.
      const files = items.filter((item) => typeof item.file === "string");
      const internalFiles = new Set(files.filter((item) => item.external !== true).map((item) => item.file));
      if (level.id === null) keeper.unlisted(keptUnder, "internal", "", internalFiles, part.began);
      if (level.storage === "internal") keeper.unlisted(keptUnder, "internal", level.path, internalFiles, part.began);
      else keeper.unlisted(keptUnder, "external", level.path, new Set(files.filter((item) => item.external === true).map((item) => item.file)), part.began);
      state.listVersion += 1;
      state.listBusy = false;
      state.animations = clocksLevel ? [] : items.filter((item) => typeof item.file === "string");
      for (const item of state.animations) {
        if (item.external !== true && typeof item.stored === "string" && item.stored !== item.file) storedNames.set(item.file, item.stored);
      }
      noteClockRows(state.animations);
      state.folders = items.filter((item) => typeof item.playlist === "string" && (!clocksLevel || item.playlist === "clocks"));
      state.cycles = clocksLevel ? [] : items.filter((item) => item.cycle === true).map((item) => item.id);
      if (level.id === null) {
        state.rootNames = namesOf(items);
      }
      orderDue = state.orderKnown && !clocksLevel;
      ordering = null;
      if (!state.orderKnown || clocksLevel) state.order = null;
      catalogDue = !state.catalogNone && !state.pagesRefused;
      listAgainLater();
      if (clocksLevel) fitClocks();
    }
  } catch (error) {
    if (asked !== target || level !== state.level) {
      return;
    }
    if (error instanceof commands.Refusal && error.code === "unknown-id" && level.id !== null) {
      await recoverLevel(asked, level);
      return;
    } else if (error instanceof commands.Refusal && error.code === "busy") {
      // The target has just started and still reads what it has installed. What is
      // known of its list stays, and the list is asked for again soon.
      heard();
      state.listBusy = true;
      listAgainLater(LIST_WHEN_BUSY_MS);
    } else if (error instanceof commands.Refusal) {
      // The target answers and has no list to give: its show is invalid.
      heard();
      state.listBusy = false;
      state.animations = null;
      state.cycles = [];
      state.folders = [];
      listAgainLater();
    } else {
      failed(error);
      listAgainLater();
    }
  }
  changed();
}

// Asks for one part of the saved order. The order takes the place of the one before when
// its last part has come and it holds exactly the animations of the list; otherwise the
// list is asked for again.
async function askOrderPart() {
  const asked = target;
  const level = state.level;
  const part = ordering === null ? {ids: [], from: 0, revision: null} : ordering;
  ordering = null;
  try {
    const reply = await commands.orderGet(part.from, level.id);
    if (asked !== target || level !== state.level) {
      return;
    }
    heard();
    const ids = part.ids.concat(reply.ids);
    if (part.revision !== null && part.revision !== reply.revision) {
      // The order changed between two parts: it is asked for whole again.
      orderDue = true;
    } else if (reply.next !== null) {
      ordering = {ids, from: reply.next, revision: reply.revision};
    } else {
      const listed = new Set((state.animations || []).map((item) => item.id));
      if (ids.length === listed.size && ids.every((id) => listed.has(id))) {
        state.order = {ids, revision: reply.revision};
        state.orderVersion += 1;
      } else {
        state.order = null;
        listing = null;
        listDue = true;
      }
    }
  } catch (error) {
    if (asked !== target || level !== state.level) {
      return;
    }
    if (error instanceof commands.Refusal) {
      heard();
      state.order = null;
      if (["unknown-command", "bad-argument"].includes(error.code)) {
        // A target whose software has no saved order: the list stays in its own order.
        state.orderKnown = false;
        state.orderVersion += 1;
      }
    } else {
      failed(error);
    }
  }
  changed();
}

// Takes what a reply of `catalog` says: a storage whose catalog is not `ok` has no keys
// any more; one that is `ok` is read again when its keys, or the read under way, are of
// another generation or another number of entries. The keys stand meanwhile.
export function noteCatalog(reply) {
  state.catalog = reply;
  for (const storage of STORAGES) {
    const part = reply[storage];
    const at = reads.findIndex((read) => read.storage === storage);
    if (part.state !== "ok") {
      if (["damaged", "incompatible", "none"].includes(part.state)) {
        keeper.forget(keptUnder, storage);
      }
      if (at !== -1) {
        reads.splice(at, 1);
      }
      if (state.keys[storage] !== null) {
        state.keys[storage] = null;
        state.keysVersion += 1;
      }
      continue;
    }
    const kept = state.keys[storage];
    const same = (read) => read.generation === part.generation && read.entries === part.entries;
    // Keys kept on the phone of this generation and number of entries are the storage's at
    // once, and its pages are not read.
    const record = state.pagesRefused || (kept !== null && same(kept)) ? null : keeper.kept(keptUnder, storage);
    if (record !== null && same(record)) {
      if (at !== -1) {
        reads.splice(at, 1);
      }
      state.keys[storage] = {generation: record.generation, entries: record.entries, byName: record.byName};
      state.keysVersion += 1;
      continue;
    }
    if (state.pagesRefused || (at !== -1 && same(reads[at])) || (at === -1 && kept !== null && same(kept))) {
      continue;
    }
    const read = {storage, generation: part.generation, entries: part.entries, pageGeneration: null, page: 0, offset: 0, tail: "", byName: new Map()};
    if (at !== -1) {
      reads[at] = read;
    } else {
      reads.push(read);
      reads.sort((a, b) => STORAGES.indexOf(a.storage) - STORAGES.indexOf(b.storage));
    }
  }
}

// Takes where the keys of the catalogs are kept between two starts of the app.
export function keepKeysIn(given) {
  keeper = given;
}

// Says that the keys kept at earlier starts have been taken, or found missing: pages may be
// asked from now on. A read under way of the generation and number of entries of kept keys
// ends, and those keys are the storage's.
export function keptKeysReady() {
  keptTaken = true;
  let took = false;
  for (const read of [...reads]) {
    const record = keeper.kept(keptUnder, read.storage);
    if (record !== null && record.generation === read.generation && record.entries === read.entries) {
      reads.splice(reads.indexOf(read), 1);
      state.keys[read.storage] = {generation: record.generation, entries: record.entries, byName: record.byName};
      state.keysVersion += 1;
      took = true;
    }
  }
  if (took) {
    changed();
  }
  next();
}

// Says that the target keeps no catalogs: it is asked for none again until it changes.
export function noCatalogs() {
  state.catalogNone = true;
  catalogDue = false;
  dropKeys();
}

async function askCatalog() {
  const asked = target;
  try {
    const reply = await commands.catalog();
    if (asked !== target) {
      return;
    }
    heard();
    noteCatalog(reply);
  } catch (error) {
    if (asked !== target) {
      return;
    }
    if (error instanceof commands.Refusal) {
      heard();
      if (["unknown-command", "bad-argument"].includes(error.code)) {
        noCatalogs();
      }
    } else {
      failed(error);
    }
  }
  changed();
}

// Asks for the next part of the page the first read is at. A read whose pages answer
// another generation than its first starts again; one that meets `null` or a refusal ends
// without keys, but for `busy`, after which the page is asked again later. A target that
// does not know the command is asked for no page again.
async function askPage() {
  const asked = target;
  const read = reads[0];
  try {
    const reply = await commands.catalogPage(read.storage, read.page, read.offset);
    if (asked !== target) {
      return;
    }
    // A reply after a silence drops every read, this one too.
    heard();
    if (reads[0] !== read) {
      changed();
      return;
    }
    if (reply.generation === null) {
      reads.shift();
    } else if (read.pageGeneration !== null && reply.generation !== read.pageGeneration) {
      Object.assign(read, {pageGeneration: null, page: 0, offset: 0, tail: "", byName: new Map()});
    } else {
      read.pageGeneration = reply.generation;
      const parts = (read.tail + reply.text).split("\n");
      read.tail = reply.next === null ? "" : parts.pop();
      let taken = 0;
      for (const line of parts) {
        const found = CATALOG_LINE.exec(line);
        if (found !== null) {
          read.byName.set(found[3], `${found[1]}-${found[2]}`);
          taken += 1;
        }
      }
      // The rows these lines name have their keys from now on, before the read ends.
      if (taken > 0) {
        state.keysVersion += 1;
      }
      if (reply.next !== null) {
        read.offset = reply.next;
      } else if (read.page + 1 < PAGES) {
        read.page += 1;
        read.offset = 0;
      } else {
        reads.shift();
        state.keys[read.storage] = {generation: read.pageGeneration, entries: read.entries, byName: read.byName};
        state.keysVersion += 1;
        keeper.keep(keptUnder, read.storage, state.keys[read.storage]);
      }
    }
  } catch (error) {
    if (asked !== target) {
      return;
    }
    if (error instanceof commands.Refusal) {
      heard();
      if (reads[0] !== read) {
        changed();
        return;
      }
      if (error.code === "busy") {
        pageWait = setTimeout(() => {
          pageWait = null;
          next();
        }, PAGE_AGAIN_MS);
      } else if (["unknown-command", "bad-argument"].includes(error.code)) {
        state.pagesRefused = true;
        catalogDue = false;
        reads.length = 0;
      } else {
        reads.shift();
      }
    } else if (error instanceof Failure && error.kind === "bad-reply") {
      // A target that answers the command with no page of a catalog is from before it.
      state.pagesRefused = true;
      catalogDue = false;
      reads.length = 0;
    } else {
      failed(error);
    }
  }
  changed();
}

// The key of an animation, `<crc32>-<bytes>`, as the catalog of its storage names its file:
// the read of that catalog under way first, as far as it has come, then the keys of its last
// read; only when that key's size is the animation's, otherwise null.
export function keyOf(animation) {
  const external = typeof animation.external === "boolean" ? animation.external : typeof animation.ignored !== "boolean";
  const storage = external ? "external" : "internal";
  if (typeof animation.bytes !== "number") {
    return null;
  }
  // A file of a folder of the board's own storage is named in its catalog by its stored name.
  const name = typeof animation.stored === "string" ? animation.stored : animation.file;
  const read = reads.find((one) => one.storage === storage);
  const kept = state.keys[storage];
  const key = (read === undefined ? undefined : read.byName.get(name)) ?? (kept === null ? undefined : kept.byName.get(name));
  if (key !== undefined && key.endsWith(`-${animation.bytes}`)) {
    return key;
  }
  // Else the key this phone kept for the place it uploaded the file to.
  const placed = keeper.placed(keptUnder, storage, animation.file);
  return placed !== null && placed.endsWith(`-${animation.bytes}`) ? placed : null;
}

// An upload of this phone ended with success: the place keeps the key of its bytes, and the
// keys an earlier read of the storage gave the name, or the stored name a list gave its path,
// are not taken until a page read after it names it again.
export function uploadedTo(storage, name, key) {
  const names = [name];
  if (storage === "internal" && storedNames.has(name)) names.push(storedNames.get(name));
  for (const named of names) {
    for (const read of reads) {
      if (read.storage === storage) read.byName.delete(named);
    }
    state.keys[storage]?.byName.delete(named);
  }
  keeper.place(keptUnder, storage, name, key);
  state.keysVersion += 1;
  changed();
}

// Sends what the operator asked for, once. A status is due at once after its reply, but
// for a request of a long job in the background, between which a status comes at its own
// time; after a removal the list and the space are due too.
async function give(request) {
  if (request.allowed && !request.allowed()) {
    request.resolve?.(false);
    request.settle?.(false);
    return;
  }
  if (request.kind === "play-all" && onlyActive &&
      (!state.statusFresh || state.status?.clockMode !== "only" || onlyFolder === null)) {
    const error = new commands.Refusal("stale", "play all");
    request.reject?.(error);
    if (!request.reject) refused(error);
    request.settle?.(false);
    return;
  }
  const asked = target;
  if (request.guard && !request.guard()) {
    request.reject?.(new commands.Refusal("stale", "timing operation"));
    return;
  }
  try {
    const reply = await request.carry();
    if (asked !== target) {
      request.reject?.(new Error("the address changed"));
      request.settle?.(false);
      return;
    }
    heard();
    request.confirm?.(reply);
    request.resolve?.(reply);
    request.settle?.(true);
  } catch (error) {
    if (asked !== target) {
      request.reject?.(new Error("the address changed"));
      request.settle?.(false);
      return;
    }
    if (error instanceof commands.Refusal) {
      heard();
      if (error.code === "unknown-id") {
        // The list the operator chose from is not what the target has any more.
        listDue = true;
      }
      if (!request.reject) {
        refused(error);
      }
    } else {
      failed(error);
    }
    request.reject?.(error);
    request.settle?.(false);
  }
  if (request.kind === "remove" || request.kind === "ignore" || request.kind === "order") {
    listing = null;
    listDue = true;
    spaceDue = true;
  }
  // The status that shows what the command did goes before a list that waits.
  if (!request.background) {
    statusDue = true;
    listWaited = false;
  }
  changed();
}

// Sends the next line of the upload under way. A refusal or a failure ends the upload;
// when it has ended, the list and the space are asked for again.
async function sendJobLine(running, line) {
  const asked = target;
  try {
    await line();
    if (asked !== target) {
      return;
    }
    heard();
  } catch (error) {
    if (asked !== target) {
      return;
    }
    if (error instanceof commands.Refusal) {
      heard();
    } else {
      failed(error);
    }
    running.failed(error);
  }
  if (running.over()) {
    job = null;
    listing = null;
    listDue = true;
    spaceDue = true;
    statusDue = true;
  }
  changed();
}

// The request to send now, or null when nothing is due: what the operator asked for,
// then a status that is due, then the next line of an upload, then a list that is due or
// the next part of one, then the saved order, then the space, then `catalog`, then the
// next part of a catalog's page. Nothing is due while the app is not on the screen.
function due() {
  if (document.hidden) {
    return null;
  }
  // A request of a long job in the background lets a status that is due go first.
  if (wanted.length > 0 && !(wanted[0].background && statusDue)) {
    const request = wanted.shift();
    return () => give(request);
  }
  const listWaits = listing !== null || listDue;
  if (statusDue && !(listWaits && listWaited)) {
    statusDue = false;
    listWaited = listWaits;
    return askStatus;
  }
  if (job !== null) {
    const running = job;
    if (!canUpload(running)) {
      const error = new commands.Refusal("in-use", "upload");
      if (typeof running.block === "function") running.block(error);
      else running.failed(error);
    }
    const line = running.next();
    if (line !== null) {
      return () => sendJobLine(running, line);
    }
    if (running.over()) {
      job = null;
    }
  }
  if (listWaits) {
    listDue = false;
    listWaited = false;
    if (state.level.id === null && state.level.path !== "") {
      // A location without an id is resolved by its path. In Only it waits while the
      // target names no Clocks folder: the status that names one asks for it.
      if (!onlyActive || onlyFolder !== null) return () => recoverLevel(target, state.level);
      listing = null;
    } else {
      return askListPart;
    }
  }
  if (rootDue || rooting !== null) {
    rootDue = false;
    return askRootPart;
  }
  if (orderDue || ordering !== null) {
    orderDue = false;
    return askOrderPart;
  }
  if (spaceDue) {
    spaceDue = false;
    return askSpace;
  }
  if (catalogDue) {
    catalogDue = false;
    return askCatalog;
  }
  if (clockAsk !== null) {
    return askClockRows;
  }
  if (reads.length > 0 && pageWait === null && keptTaken) {
    return askPage;
  }
  return null;
}

async function next() {
  if (underWay) {
    return;
  }
  const request = due();
  if (request === null) {
    return;
  }
  underWay = true;
  try {
    await request();
  } finally {
    underWay = false;
    next();
  }
}

// Begins with the address in use: forgets what an earlier target said, and asks. An
// upload to the earlier target ends.
export function begin() {
  target += 1;
  connectionDue = true;
  keptUnder = address();
  holder = null;
  readForm = null;
  state.listVersion = 0;
  if (job !== null) {
    job.failed(new Error("the address changed"));
    job = null;
  }
  state.link = "checking";
  state.failure = null;
  state.status = null;
  state.statusFresh = false;
  state.heardAt = null;
  state.since = Date.now();
  state.answered = false;
  trail.length = 0;
  onlyActive = false;
  onlyFolder = null;
  onlyDesired = "clocks";
  onlyBoth = false;
  clockRows.clear();
  clockAsk = null;
  clockAsked.clear();
  state.onlyUnavailable = false;
  state.level = {path: "", id: null, storage: null};
  state.rootNames = null;
  rootDue = false;
  rooting = null;
  state.animations = null;
  storedNames.clear();
  state.cycles = [];
  state.folders = [];
  state.space = null;
  state.listBusy = false;
  state.order = null;
  state.orderKnown = true;
  orderDue = false;
  ordering = null;
  state.catalog = null;
  state.catalogNone = false;
  state.pagesRefused = false;
  catalogDue = false;
  dropKeys();
  cancelWaiting();
  statusDue = true;
  listDue = false;
  listing = null;
  listWaited = false;
  askedFor = null;
  clearTimeout(listTimer);
  listTimer = null;
  spaceDue = true;
  clearTimeout(spaceTimer);
  spaceTimer = null;
  changed();
  next();
}

// Says which screen is on the screen of the phone. The list is kept fresh while it is
// Animations or Upload, together with capacity.
export function showing(name) {
  const was = showScreen || storageScreen;
  const wasStorage = storageScreen;
  showScreen = name === "animations";
  storageScreen = name === "upload";
  if ((showScreen || storageScreen) && !was && state.answered && listTimer === null) {
    listDue = true;
  }
  if ((showScreen || storageScreen) && (!was || storageScreen !== wasStorage)) {
    spaceDue = true;
  }
  if (storageScreen && !wasStorage && state.answered && state.level.id !== null) {
    // An upload chooses its id and its name against the root's, which another level lacks.
    rootDue = true;
  }
  next();
}

// Shows another level of the folders: `folder`, `{id, playlist, external}`, a folder of the
// level shown, entered; or with `back` the level above. Its list is read at once, and
// nothing of the level left is kept.
export function clocksOnly() {
  return onlyActive;
}

export function canEnter(folder) {
  return !onlyActive || state.link === "answers" && state.statusFresh && inClocks(state.level) &&
    typeof folder?.playlist === "string" && inClocks(folder.playlist) &&
    parentOf(folder.playlist) === state.level.path &&
    state.folders.some(known => known.id === folder.id && known.playlist === folder.playlist && (onlyBoth || storageOf(known) === "external"));
}

export function canGoBack() {
  return trail.length > 0 && (!onlyActive || trail.length > 1 && inClocks(state.level));
}

export function enter(folder) {
  if (!canEnter(folder)) return false;
  trail.push({path: folder.playlist, id: folder.id, storage: storageOf(folder)});
  toLevel();
  return true;
}

export function back() {
  if (!canGoBack()) return false;
  trail.pop();
  toLevel();
  return true;
}

function toLevel() {
  if (onlyActive && !inClocks(trail[trail.length - 1] ?? null)) {
    trail.splice(0, trail.length, ...(onlyFolder === null ? [{path: "clocks", id: null}] : openClocks()));
  }
  const top = trail[trail.length - 1];
  state.level = top === undefined ? {path: "", id: null, storage: null} : top.clocks === true ? {...CLOCKS_LEVEL} :
    {path: top.path, id: top.id, storage: top.storage};
  if (onlyActive && inClocks(state.level) && state.level.id !== null) onlyDesired = state.level.path;
  state.onlyUnavailable = onlyActive && inClocks(state.level) && state.level.id === null && state.level.clocks !== true;
  state.listBusy = false;
  // The unavailable Clocks location lists nothing while its folder is resolved again.
  state.animations = state.onlyUnavailable ? [] : null;
  state.folders = [];
  state.cycles = [];
  state.order = null;
  state.orderVersion += 1;
  listing = null;
  ordering = null;
  orderDue = false;
  listDue = true;
  askedFor = null;
  changed();
  next();
}

// Asks for one part of the root's list for the names an upload chooses against, while
// another level is shown; the list shown stays as it is.
async function askRootPart() {
  const asked = target;
  const part = rooting === null ? {items: [], from: 0} : rooting;
  rooting = null;
  try {
    const reply = await commands.list(part.from, null);
    if (asked !== target) {
      return;
    }
    heard();
    const items = part.items.concat(reply.items);
    if (reply.next !== null) {
      rooting = {items, from: reply.next};
    } else {
      state.rootNames = namesOf(items);
      fitClocks();
    }
  } catch (error) {
    if (asked !== target) {
      return;
    }
    if (error instanceof commands.Refusal) {
      heard();
    } else {
      failed(error);
    }
  }
  changed();
}

// Asks, in the background, for the rows of the folder of the Clocks file a status named: the
// root's list, then the lists of its folder's path in the card and in the board's own storage,
// until one names its id; each list's files of a Clocks subtree are noted with their storage.
async function askClockRows() {
  const asked = target;
  const wanted = clockAsk;
  clockAsk = null;
  async function all(folder) {
    const items = [];
    let from = 0;
    do {
      const reply = await commands.list(from, folder);
      if (asked !== target) return null;
      items.push(...reply.items);
      from = reply.next;
    } while (from !== null);
    return items;
  }
  try {
    const root = await all(null);
    if (root === null) return;
    heard();
    const names = parentOf(wanted.file).split("/");
    for (const external of [true, false]) {
      let rows = root;
      let path = "";
      for (const name of names) {
        path += (path ? "/" : "") + name;
        const folder = rows.find((row) => row.playlist === path && (row.external !== false) === external);
        rows = folder === undefined ? [] : await all(folder.id);
        if (rows === null) return;
        noteClockRows(rows);
      }
      if (clockRows.get(wanted.id)?.file === wanted.file) break;
    }
  } catch (error) {
    if (asked !== target) return;
    // A read that got no answer, or was answered busy, is asked for again at a later status.
    if (!(error instanceof commands.Refusal) || error.code === "busy") clockAsked.delete(`${wanted.id} ${wanted.file}`);
    if (error instanceof commands.Refusal) heard();
    else failed(error);
  }
  changed();
}

// Takes something the operator asked for. A brightness that still waits is replaced by a
// newer one, at its place.
function want(kind, carry, confirm, settle) {
  const waiting = kind === "brightness" ? wanted.findIndex((request) => request.kind === kind) : -1;
  if (waiting === -1) {
    wanted.push({kind, carry, confirm, settle});
  } else {
    wanted[waiting].settle?.(false);
    wanted[waiting] = {kind, carry, confirm, settle};
  }
  next();
}

// Uploads with a job of `upload.js`, line by line between the requests of the app. It
// goes on only while the app is on the screen.
export function upload(made) {
  job = made;
  changed();
  next();
}

// Whether an upload may go to its destination, `{external, file}`: anywhere outside Clocks
// only; in it into a Clocks subtree, of a writable card with a ready catalog, or of the board's
// own storage on a target that plays the clocks of both storages.
export function canUpload(destination) {
  if (!onlyActive) return true;
  if (!state.statusFresh || state.status?.clockMode !== "only" || typeof destination.file !== "string" || !destination.file.startsWith("clocks/")) return false;
  if (destination.external !== true) return onlyBoth && destination.external === false;
  return state.space?.external?.present === true && state.space.external.read_only === false &&
    state.catalog?.external?.state === "ok" && state.catalog.external.writable === true;
}

// Whether a move may put files into a folder of a storage, "external" the card's, "" for its
// root: anywhere outside Clocks only; in it into a Clocks folder or one below it, of the card,
// or of the board's own storage on a target that plays the clocks of both storages.
export function canMoveInto(storage, folder) {
  return !onlyActive || (storage === "external" || onlyBoth) && inClocks(folder);
}

// Asks for the next request again, as a job does when it has a line again.
export function wake() {
  next();
}

// Removes an animation from the show. `done` is called when the target has removed it.
export function remove(animation, done) {
  want("remove", () => commands.remove(animation.id), () => {
    keeper.unplace(keptUnder, animation.external === true ? "external" : "internal", animation.file);
    done(animation);
  });
}

// Whether an item of a list is a Clocks folder or inside one: the card's, and the board's
// own on a target that plays the clocks of both storages; on another a folder or a file of
// the board's own storage never is.
export function inClockFolder(item) {
  if (typeof item.playlist === "string") return (onlyBoth || item.external !== false) && inClocks(item.playlist);
  return (onlyBoth || item.external === true) && inClocks(item.file);
}

export function canPlay(item) {
  return !onlyActive || inClockFolder(item);
}

export function play(id) {
  want("play", () => {
    if (onlyActive && id !== onlyFolder) {
      const item = [...(state.animations || []), ...state.folders].find((candidate) => candidate.id === id);
      if (item === undefined || !inClockFolder(item)) throw new commands.Refusal("in-use", `play ${id}`);
    }
    return commands.play(id);
  });
}

export function playAll() {
  want("play-all", () => {
    if (!onlyActive) return commands.playAll();
    if (!state.statusFresh || state.status?.clockMode !== "only" || state.onlyUnavailable) {
      throw new commands.Refusal("in-use", "play all");
    }
    const folder = onlyFolder;
    if (folder == null) throw new commands.Refusal("in-use", "play all");
    return commands.play(folder);
  });
}

export function switchOn() {
  want("on", () => commands.on());
}

export function switchOff() {
  want("off", () => commands.off());
}

function capturedBrightness(snapshot, carry) {
  if (snapshot !== null && (snapshot.version !== target || state.link !== "answers" || !state.statusFresh ||
      state.status?.animation !== snapshot.animation || state.status?.file !== snapshot.file ||
      (state.status?.dimming?.saved != null) !== snapshot.override)) {
    throw new commands.Refusal("stale", "brightness");
  }
  return carry();
}

export function setBrightness(value, snapshot = null) {
  return new Promise((settle) => {
    want("brightness", () => capturedBrightness(snapshot, () => commands.brightness(value)), undefined, settle);
  });
}

export function brightnessValue(value, snapshot) {
  return requestOperation("brightness-edit", () => capturedBrightness(snapshot, () => commands.brightness(value)));
}

export function brightnessSave(id, value, snapshot) {
  return requestOperation("brightness-edit", () => capturedBrightness(snapshot, () => commands.brightnessSave(id, value)));
}

export function brightnessDefault(id, snapshot) {
  return requestOperation("brightness-edit", () => capturedBrightness(snapshot, () => commands.brightnessDefault(id)));
}

// The loops of an animation's turn in progress, for that turn alone; the loops kept for
// its every turn; and its own count again. Each gives the reply, or a refusal or a
// failure, and a status follows it at once.
export function repeat(id, loops) {
  return requestOperation("repeat", () => commands.repeat(id, loops));
}

export function repeatSave(id, loops) {
  return requestOperation("repeat", () => commands.repeatSave(id, loops));
}

export function repeatDefault(id) {
  return requestOperation("repeat", () => commands.repeatDefault(id));
}

export function clocks(on) {
  return requestOperation("clocks", () => commands.clocks(on));
}

export function clockMode(mode) {
  return requestOperation("clocks", () => commands.clockMode(mode));
}

export function clockMessage(on) {
  return requestOperation("clocks", () => commands.clockMessage(on));
}

export function clockStorage(storage) {
  return requestOperation("clocks", () => commands.clockStorage(storage));
}

export function debugMini(on) {
  return requestOperation("mini", () => commands.debugMini(on));
}

export function rotationRead(allowed) {
  return requestOperation("rotation", () => commands.rotation(), undefined, allowed);
}

export function rotationSet(revision, degrees, allowed) {
  return requestOperation("rotation", () => commands.rotationSet(revision, degrees), undefined, allowed);
}

// Names the function that is told of every refusal of what the operator asked for.
export function onRefusal(handler) {
  refused = handler;
}

document.addEventListener("visibilitychange", () => {
  if (document.hidden) {
    // What was asked for and not sent is not sent later, when the app comes back.
    cancelWaiting();
  } else {
    connectionDue = true;
    statusDue = true;
    refreshContent();
  }
});


// Mapping requests share the same serialized stream and report their own recovery UI.
export function targetVersion() {
  return target;
}

// Fresh upload observations share the serialized command stream with all controls.
export function uploadSnapshot(level) {
  return requestOperation("upload-preflight", async () => {
    const asked = target;
    const unchanged = () => { if (asked !== target) throw new Error("the target changed"); };
    const status = await commands.status();
    unchanged();
    takeStatus(status);
    if (onlyActive && (!inClocks(level) || level.id === null)) {
      throw new commands.Refusal("in-use", "upload");
    }
    const space = await commands.space();
    unchanged();
    state.space = space;
    let catalog = null;
    try { catalog = await commands.catalog(); } catch (error) {
      if (!(error instanceof commands.Refusal && ["unknown-command", "bad-argument"].includes(error.code))) throw error;
    }
    unchanged();
    async function all(folder) {
      const items = [];
      let from = 0;
      do {
        const reply = await commands.list(from, folder);
        unchanged();
        items.push(...reply.items);
        from = reply.next;
      } while (from !== null);
      return items;
    }
    const root = await all(null);
    let items = root;
    let folderValid = level.id === null;
    if (level.id !== null && (level.storage === "internal" || space.external?.present === true)) {
      let path = "";
      for (const part of level.path.split("/")) {
        path += (path ? "/" : "") + part;
        const folder = items.find(row => typeof row.playlist === "string" && row.playlist === path && storageOf(row) === (level.storage ?? "external"));
        if (!folder) break;
        if (path === level.path) folderValid = folder.id === level.id;
        items = await all(folder.id);
      }
    }
    if (catalog !== null) {
      const after = await commands.catalog();
      unchanged();
      if (["internal", "external"].some(storage => after[storage].generation !== catalog[storage].generation)) throw new commands.Refusal("stale", "upload preflight");
    }
    const ids = await idsWithin(root, async (from, folder) => {
      const reply = await commands.list(from, folder);
      unchanged();
      return reply;
    });
    return {space, catalog, root, items, folderValid, ids};
  });
}

// Every id of the board's own storage, its root's and its folders', that a new item's id is
// chosen against.
export function takenIds() {
  return requestOperation("ids", async () => {
    const asked = target;
    return idsWithin(await (async () => {
      const rows = [];
      let from = 0;
      do {
        const reply = await commands.list(from, null);
        if (asked !== target) throw new Error("the target changed");
        rows.push(...reply.items);
        from = reply.next;
      } while (from !== null);
      return rows;
    })(), (from, folder) => commands.list(from, folder));
  });
}

function requestOperation(kind, carry, confirm, allowed, guard, background = false) {
  return new Promise((resolve, reject) => {
    wanted.push({kind, carry, confirm, allowed, resolve, reject, guard, background});
    next();
  });
}

export function timingOperation(carry, version, current = () => true) {
  const guard = () => version === target && current() && state.link === "answers" && state.statusFresh && !document.hidden;
  return requestOperation("timing", async () => {
    const send = async action => {
      if (!guard()) throw new commands.Refusal("stale", "timing operation");
      const result = await action();
      if (!guard()) throw new commands.Refusal("stale", "timing operation");
      return result;
    };
    return carry(send);
  }, undefined, undefined, guard);
}

// A request that was not sent: the app was hidden, or another target was chosen.
export class Withdrawn extends Error {}

function cancelWaiting() {
  for (const request of wanted) {
    request.reject?.(new Withdrawn("the request was cancelled"));
    request.settle?.(false);
  }
  wanted.length = 0;
}

// Takes back an upload the installation holds open, in the stream of requests.
export function uploadCancel() {
  return requestOperation("upload-cancel", () => commands.uploadCancel());
}

export function mappingGet() {
  return requestOperation("mapping", () => commands.mappingGet());
}

export function mappingSet(revision, pins, allowed) {
  return requestOperation("mapping", () => commands.mappingSet(revision, pins), undefined, allowed);
}

export function mappingTest(enabled) {
  return requestOperation("mapping", () => commands.mappingTest(enabled));
}

export function mappingTestSnake(snake) {
  return requestOperation("mapping", () => commands.mappingTestSnake(snake));
}

// The latest fault of a file the target met since its start, or null when it met none or
// its software does not know `fault`.
export function lastFault() {
  return requestOperation("fault", async () => {
    try {
      return await commands.fault();
    } catch (error) {
      if (error instanceof commands.Refusal && ["unknown-command", "bad-argument"].includes(error.code)) {
        return null;
      }
      throw error;
    }
  });
}

// Who keeps the content from changing now: "upload" while an upload job of any screen is
// under way, else the holder of the lock, else null.
export function contentHolder() {
  return job !== null ? "upload" : holder;
}

export function contentBusy() {
  return contentHolder() !== null;
}

// Takes the content lock for its holder, "preflight", "deletion", "download" or "move", or
// lets it go with false.
export function setContentBusy(value) {
  holder = value ? value : null;
  changed();
}

export function refreshContent() {
  listing = null;
  listDue = true;
  spaceDue = true;
  next();
}

export function ignore(id, ignored) {
  return requestOperation("ignore", () => commands.ignore(id, ignored), () => {
    const animation = [...(state.animations || []), ...state.folders].find(item => item.id === id);
    if (animation) animation.ignored = ignored;
  });
}

// Whether the target takes `read <id> <offset> <count>`, which `read <id> 0 1` shows: it is
// refused with `bad-argument` by one that does not. The answer is kept for the target.
async function probeReadCount(id, asked) {
  let counts = true;
  try {
    await commands.read(id, 0, 1);
  } catch (error) {
    if (!(error instanceof commands.Refusal && error.code === "bad-argument")) throw error;
    counts = false;
  }
  if (asked === target) readForm = {target: asked, counts};
  return counts;
}

// One piece of the file of an animation from an offset, `{bytes, data}`: 720 bytes at most
// from a target that takes a count, which `read <id> 0 1` finds out once for each target,
// else 600 at most. A count refused with `bad-argument` is asked about again, as another
// installation may answer at the same address. It goes in its turn as a request in the
// background.
export function readPiece(id, offset) {
  return requestOperation("read", async () => {
    const asked = target;
    const known = readForm !== null && readForm.target === asked ? readForm.counts : await probeReadCount(id, asked);
    if (!known) return commands.read(id, offset);
    try {
      return await commands.read(id, offset, commands.READ_COUNT);
    } catch (error) {
      if (!(error instanceof commands.Refusal && error.code === "bad-argument") || await probeReadCount(id, asked)) throw error;
      return commands.read(id, offset);
    }
  }, undefined, undefined, undefined, true);
}

// Waits until the app is on the screen.
function onTheScreen() {
  return new Promise((resolve) => {
    if (!document.hidden) {
      resolve();
      return;
    }
    const seen = () => {
      if (!document.hidden) {
        document.removeEventListener("visibilitychange", seen);
        resolve();
      }
    };
    document.addEventListener("visibilitychange", seen);
  });
}

// The whole file of an animation, read from the target piece by piece, as bytes, each piece
// in its turn among the other requests; a piece withdrawn while the app was hidden is asked
// again once it is shown, from the same target. `progress(read, size)` is told after each
// piece. A file whose size changes between two pieces is not the one whose reading began.
export async function readFile(id, progress = () => {}) {
  const asked = target;
  const parts = [];
  let offset = 0;
  let size = null;
  for (;;) {
    let piece;
    try {
      piece = await readPiece(id, offset);
    } catch (error) {
      if (!(error instanceof Withdrawn) || asked !== target) throw error;
      await onTheScreen();
      continue;
    }
    const {bytes, data} = piece;
    if (size !== null && bytes !== size) throw new Error("The file changed while it was read.");
    size = bytes;
    parts.push(data);
    offset += data.length;
    progress(offset, size);
    if (data.length === 0 || offset >= bytes) {
      break;
    }
  }
  const whole = new Uint8Array(offset);
  let at = 0;
  for (const part of parts) {
    whole.set(part, at);
    at += part.length;
  }
  return whole;
}

export function removeMany(ids) {
  return requestOperation("remove", () => commands.removeMany(ids));
}

// Sends one request of a job of the app, such as a move, in its turn among the operator's.
export function operation(kind, carry) {
  return requestOperation(kind, carry);
}

// Sends one request of a long job of the app, such as a backup, in its turn, letting a
// status that is due go before it.
export function background(kind, carry) {
  return requestOperation(kind, carry, undefined, undefined, undefined, true);
}

// The catalogs of the target, the rebuild of one of them and its cancel.
export function catalog() {
  // A question that waited its turn behind the answer that the installation keeps no
  // catalogs is not sent: that answer is its answer.
  return requestOperation("catalog", () => (state.catalogNone ? Promise.reject(new commands.Refusal("unknown-command", "catalog")) : commands.catalog()));
}

export function catalogRebuild(storage) {
  return requestOperation("catalog", () => commands.catalogRebuild(storage));
}

export function catalogCancel() {
  return requestOperation("catalog", () => commands.catalogCancel());
}

// Moves an animation before another, or to the end with "end", in the saved order the
// list is shown in. The list and the order are asked for again afterwards, whatever the
// reply.
export function orderMove(id, before) {
  const revision = state.order === null ? null : state.order.revision;
  if (revision === null) {
    return Promise.reject(new Error("no saved order"));
  }
  return requestOperation("order", () => commands.orderMove(revision, id, before));
}
