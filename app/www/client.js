// What the replies told, and the order in which requests are sent. One request is under
// way at a time. The state holds only what a reply said.

import * as commands from "./commands.js";
import {Failure} from "./target.js";

const STATUS_EVERY_MS = 1000;
const LIST_EVERY_MS = 10000;
const LIST_WHEN_BUSY_MS = 1000;
const SPACE_EVERY_MS = 10000;

// `link` is "checking" until the first request has ended, then "answers" or "no-answer",
// with the Failure in `failure`. `status` is the newest reply to `status`, `heardAt` the
// time of the newest reply of any kind, `since` the time the app began with this address,
// and `answered` whether the target of this address has answered at least once.
// `animations` is the animation items of the newest complete list, in the order of the
// show, each as `{id, file, bytes}` with optional `ignored`, or null while there is none; `cycles` is the ids of
// its cycles. `space` holds internal and external capacity from the newest reply, or null.
// `listBusy` says whether the newest `list` request was answered `busy`. `order` is the
// saved playlist order that goes with the newest list, `{ids, revision}`, or null while
// there is none; `orderKnown` is false when the target has no saved order, an older one.
export const state = {link: "checking", failure: null, status: null, heardAt: null, since: Date.now(), answered: false, animations: null, cycles: [], space: null, listVersion: 0, listBusy: false,
  order: null, orderVersion: 0, orderKnown: true};

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

function heard() {
  if (state.link !== "answers") {
    // The target answers, for the first time or again: what it has installed is asked.
    listDue = true;
    listing = null;
    spaceDue = true;
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
    const named = reply.animation;
    if (named !== null && state.animations !== null && named !== askedFor && !state.animations.some((animation) => animation.id === named)) {
      // The target plays an animation the list does not have.
      askedFor = named;
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

// Asks for one part of the list. The new list takes the place of the old one only when
// its last part has come; when a part fails, the old list stays.
async function askListPart() {
  const asked = target;
  const part = listing === null ? {items: [], from: 0} : listing;
  listing = null;
  try {
    const reply = await commands.list(part.from);
    if (asked !== target) {
      return;
    }
    heard();
    const items = part.items.concat(reply.items);
    if (reply.next !== null) {
      listing = {items, from: reply.next};
    } else {
      state.listVersion += 1;
      state.listBusy = false;
      state.animations = items.filter((item) => item.cycle !== true);
      state.cycles = items.filter((item) => item.cycle === true).map((item) => item.id);
      orderDue = state.orderKnown;
      ordering = null;
      if (!state.orderKnown) state.order = null;
      listAgainLater();
    }
  } catch (error) {
    if (asked !== target) {
      return;
    }
    if (error instanceof commands.Refusal && error.code === "busy") {
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
  const part = ordering === null ? {ids: [], from: 0, revision: null} : ordering;
  ordering = null;
  try {
    const reply = await commands.orderGet(part.from);
    if (asked !== target) {
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
    if (asked !== target) {
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

// Sends what the operator asked for, once. A status is due at once after its reply, and
// after a removal the list and the space are due too.
async function give(request) {
  const asked = target;
  try {
    const reply = await request.carry();
    if (asked !== target) {
      request.reject?.(new Error("the address changed"));
      return;
    }
    heard();
    request.confirm?.(reply);
    request.resolve?.(reply);
  } catch (error) {
    if (asked !== target) {
      request.reject?.(new Error("the address changed"));
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
// the next part of one, then the space. Nothing is due while the app is not on the
// screen.
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
  if (orderDue || ordering !== null) {
    orderDue = false;
    return askOrderPart;
  }
  if (spaceDue) {
    spaceDue = false;
    return askSpace;
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
  contentLocked = false;
  state.listVersion = 0;
  if (job !== null) {
    job.failed(new Error("the address changed"));
    job = null;
  }
  state.link = "checking";
  state.failure = null;
  state.status = null;
  state.heardAt = null;
  state.since = Date.now();
  state.answered = false;
  state.animations = null;
  state.cycles = [];
  state.space = null;
  state.listBusy = false;
  state.order = null;
  state.orderKnown = true;
  orderDue = false;
  ordering = null;
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
  next();
}

// Takes something the operator asked for. A brightness that still waits is replaced by a
// newer one, at its place.
function want(kind, carry, confirm) {
  const waiting = kind === "brightness" ? wanted.findIndex((request) => request.kind === kind) : -1;
  if (waiting === -1) {
    wanted.push({kind, carry, confirm});
  } else {
    wanted[waiting] = {kind, carry, confirm};
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

export function play(id) {
  want("play", () => commands.play(id));
}

export function playAll() {
  want("play", () => commands.playAll());
}

export function switchOn() {
  want("on", () => commands.on());
}

export function switchOff() {
  want("off", () => commands.off());
}

export function setBrightness(value) {
  want("brightness", () => commands.brightness(value));
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

function requestOperation(kind, carry, confirm) {
  return new Promise((resolve, reject) => {
    wanted.push({kind, carry, confirm, resolve, reject});
    next();
  });
}

function cancelWaiting() {
  for (const request of wanted) {
    request.reject?.(new Error("the request was cancelled"));
  }
  wanted.length = 0;
}

export function mappingGet() {
  return requestOperation("mapping", () => commands.mappingGet());
}

export function mappingSet(revision, pins) {
  return requestOperation("mapping", () => commands.mappingSet(revision, pins));
}

export function mappingTest(enabled) {
  return requestOperation("mapping", () => commands.mappingTest(enabled));
}

export function mappingTestSnake(snake) {
  return requestOperation("mapping", () => commands.mappingTestSnake(snake));
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
    const animation = state.animations?.find(item => item.id === id);
    if (animation) animation.ignored = ignored;
  });
}

export function removeMany(ids) {
  return requestOperation("remove", () => commands.removeMany(ids));
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
