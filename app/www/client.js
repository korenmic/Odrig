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
// the level of the card's folders the list is of, `{path, id}`, "" and null for the root,
// which holds the show's items too; nothing of another level is kept. `animations` is the
// animation items of the level's newest complete list, in its order, each as
// `{id, file, bytes}` with optional `ignored`, or null while there is none; `cycles` is the
// ids of its cycles, and `folders` its folders of the card, each `{id, playlist, files}` with
// its path and the number of its own files, in the order they play. `rootNames` holds what
// the root's newest list named, `{ids, files}`, the ids and the file names of the show's
// items and of the root's files, which an upload chooses its id and its name against, or
// null while none is known. `space` holds internal and external capacity from the newest reply, or null.
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
export const state = {link: "checking", failure: null, status: null, heardAt: null, since: Date.now(), answered: false, level: {path: "", id: null}, rootNames: null,
  animations: null, cycles: [], folders: [], space: null,
  listVersion: 0, listBusy: false, order: null, orderVersion: 0, orderKnown: true, catalog: null, keys: {internal: null, external: null}, keysVersion: 0,
  catalogNone: false, pagesRefused: false, statusCount: 0, statusFresh: false};

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
// The folders entered from the root down to the level shown, each `{path, id}`.
const trail = [];
let onlyOpened = false;
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
let keeper = {kept: () => null, keep: () => {}, forget: () => {}};
let keptUnder = null;
let keptTaken = false;
// Counts the targets: a reply that belongs to an earlier address is dropped.
let target = 0;
let contentLocked = false;

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

function failed(error) {
  if (!(error instanceof Failure)) {
    throw error;
  }
  state.link = "no-answer";
  state.failure = error;
  state.space = null;
  state.statusFresh = false;
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
    heard();
    state.status = reply;
    state.statusFresh = true;
    state.statusCount += 1;
    if (reply.clockMode !== "only") onlyOpened = false;
    else if (!onlyOpened && reply.clockOnly?.folder != null) {
      onlyOpened = true;
      trail.length = 0;
      trail.push({path: "clocks", id: reply.clockOnly.folder});
      toLevel();
    }
    const named = reply.animation;
    const here = typeof reply.file === "string" && parentOf(reply.file) === state.level.path && (state.level.id === null || reply.file.includes("/"));
    if (named !== null && state.animations !== null && named !== askedFor && here && !state.animations.some((animation) => animation.id === named)) {
      // The target plays an animation of the level shown that its list does not have.
      askedFor = named;
      listDue = true;
    }
    const playing = reply.playing;
    if (typeof playing === "number" && typeof reply.playlist === "string" && parentOf(reply.playlist) === state.level.path && state.animations !== null &&
      playing !== askedFor && !state.folders.some((folder) => folder.id === playing)) {
      // The target plays a playlist of this level that its list does not have: a folder of a
      // card just put in.
      askedFor = playing;
      listDue = true;
    }
  } catch (error) {
    if (asked !== target) {
      return;
    }
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

// What an upload chooses its id and its name against, from the items of the root's list.
function namesOf(items) {
  const named = items.filter((item) => typeof item.playlist !== "string");
  return {ids: named.map((item) => item.id), files: named.filter((item) => typeof item.file === "string").map((item) => item.file)};
}

// Asks for one part of the list of the level shown. The new list takes the place of the
// old one only when its last part has come; when a part fails, the old list stays. A
// folder that is no more brings the list to the root.
async function askListPart() {
  const asked = target;
  const level = state.level;
  const part = listing === null ? {items: [], from: 0} : listing;
  listing = null;
  try {
    const reply = await commands.list(part.from, level.id);
    if (asked !== target || level !== state.level) {
      return;
    }
    heard();
    const items = part.items.concat(reply.items);
    if (reply.next !== null) {
      listing = {items, from: reply.next};
    } else {
      state.listVersion += 1;
      state.listBusy = false;
      state.animations = items.filter((item) => typeof item.file === "string");
      state.folders = items.filter((item) => typeof item.playlist === "string");
      state.cycles = items.filter((item) => item.cycle === true).map((item) => item.id);
      if (level.id === null) {
        state.rootNames = namesOf(items);
      }
      orderDue = state.orderKnown;
      ordering = null;
      if (!state.orderKnown) state.order = null;
      catalogDue = !state.catalogNone && !state.pagesRefused;
      listAgainLater();
    }
  } catch (error) {
    if (asked !== target || level !== state.level) {
      return;
    }
    if (error instanceof commands.Refusal && error.code === "unknown-id" && level.id !== null) {
      // The folder is no more, with its card or after a removal: the root is shown.
      heard();
      trail.length = 0;
      toLevel();
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
  const read = reads.find((one) => one.storage === storage);
  const kept = state.keys[storage];
  const key = (read === undefined ? undefined : read.byName.get(animation.file)) ?? (kept === null ? undefined : kept.byName.get(animation.file));
  return key !== undefined && key.endsWith(`-${animation.bytes}`) ? key : null;
}

// Sends what the operator asked for, once. A status is due at once after its reply, and
// after a removal the list and the space are due too.
async function give(request) {
  const asked = target;
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
  statusDue = true;
  listWaited = false;
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
  if (wanted.length > 0) {
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
    return askListPart;
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
  keptUnder = address();
  contentLocked = false;
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
  onlyOpened = false;
  state.level = {path: "", id: null};
  state.rootNames = null;
  rootDue = false;
  rooting = null;
  state.animations = null;
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

// Shows another level of the card's folders: `folder`, `{id, playlist}`, a folder of the
// level shown, entered; or with `back` the level above. Its list is read at once, and
// nothing of the level left is kept.
export function enter(folder) {
  trail.push({path: folder.playlist, id: folder.id});
  toLevel();
}

export function back() {
  trail.pop();
  toLevel();
}

function toLevel() {
  const top = trail[trail.length - 1];
  state.level = top === undefined ? {path: "", id: null} : {path: top.path, id: top.id};
  state.animations = null;
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

// Asks for the next request again, as a job does when it has a line again.
export function wake() {
  next();
}

// Removes an animation from the show. `done` is called when the target has removed it.
export function remove(animation, done) {
  want("remove", () => commands.remove(animation.id), () => done(animation));
}

export function inClockFolder(item) {
  const path = typeof item.playlist === "string" ? item.playlist : item.external === true ? item.file : null;
  return path === "clocks" || typeof path === "string" && path.startsWith("clocks/");
}

export function canPlay(item) {
  return state.status?.clockMode !== "only" || inClockFolder(item);
}

export function play(id) {
  want("play", () => {
    if (state.status?.clockMode === "only" && id !== state.status.clockOnly?.folder) {
      const item = [...(state.animations || []), ...state.folders].find((candidate) => candidate.id === id);
      if (item === undefined || !inClockFolder(item)) throw new commands.Refusal("in-use", `play ${id}`);
    }
    return commands.play(id);
  });
}

export function playAll() {
  want("play", () => {
    if (state.status?.clockMode !== "only") return commands.playAll();
    const folder = state.status.clockOnly?.folder;
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

export function debugMini(on) {
  return requestOperation("mini", () => commands.debugMini(on));
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
    if (level.id !== null && space.external?.present === true) {
      let path = "";
      for (const part of level.path.split("/")) {
        path += (path ? "/" : "") + part;
        const folder = items.find(row => row.playlist === path);
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
    return {space, catalog, root, items, folderValid};
  });
}

function requestOperation(kind, carry, confirm) {
  return new Promise((resolve, reject) => {
    wanted.push({kind, carry, confirm, resolve, reject});
    next();
  });
}

function cancelWaiting() {
  for (const request of wanted) {
    request.reject?.(new Error("the request was cancelled"));
    request.settle?.(false);
  }
  wanted.length = 0;
}

export function mappingGet() {
  return requestOperation("mapping", () => commands.mappingGet());
}

export function mappingSet(revision, pins) {
  return requestOperation("mapping", () => commands.mappingSet(revision, pins));
}

export function mappingCross(crossed) {
  return requestOperation("mapping", () => commands.mappingCross(crossed));
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

export function contentBusy() {
  return contentLocked || job !== null;
}

export function setContentBusy(value) {
  contentLocked = value;
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

// The whole file of an animation, read from the target in pieces, as bytes.
export function readFile(id) {
  return requestOperation("read", async () => {
    const parts = [];
    let offset = 0;
    for (;;) {
      const {bytes, data} = await commands.read(id, offset);
      parts.push(data);
      offset += data.length;
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
  });
}

export function removeMany(ids) {
  return requestOperation("remove", () => commands.removeMany(ids));
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
