// What the replies told, and the order in which requests are sent. One request is under
// way at a time. The state holds only what a reply said.

import * as commands from "./commands.js";
import {Failure} from "./target.js";

const STATUS_EVERY_MS = 1000;
const LIST_EVERY_MS = 10000;

// `link` is "checking" until the first request has ended, then "answers" or "no-answer",
// with the Failure in `failure`. `status` is the newest reply to `status`, `heardAt` the
// time of the newest reply of any kind, `since` the time the app began with this address,
// and `answered` whether the target of this address has answered at least once.
// `animations` is the animation items of the newest complete list, in the order of the
// show, each as `{id, file}`, or null while there is none; `cycles` is the ids of its
// cycles.
export const state = {link: "checking", failure: null, status: null, heardAt: null, since: Date.now(), answered: false, animations: null, cycles: []};

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
// Whether a list has waited while a status was sent. It goes before the next status
// then, so that a target that answers slowly does not keep the list away.
let listWaited = false;
// Whether the show screen is the one on the screen of the phone.
let showScreen = false;
// Counts the targets: a reply that belongs to an earlier address is dropped.
let target = 0;

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

function listAgainLater() {
  clearTimeout(listTimer);
  listTimer = setTimeout(() => {
    listTimer = null;
    if (showScreen) {
      listDue = true;
      next();
    }
  }, LIST_EVERY_MS);
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
      state.animations = items.filter((item) => item.cycle !== true);
      state.cycles = items.filter((item) => item.cycle === true).map((item) => item.id);
      listAgainLater();
    }
  } catch (error) {
    if (asked !== target) {
      return;
    }
    if (error instanceof commands.Refusal) {
      // The target answers and has no list to give: its show is invalid.
      heard();
      state.animations = null;
      state.cycles = [];
    } else {
      failed(error);
    }
    listAgainLater();
  }
  changed();
}

// Sends what the operator asked for, once. A status is due at once after its reply.
async function give(request) {
  const asked = target;
  try {
    await request.carry();
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
      if (error.code === "unknown-id") {
        // The list the operator chose from is not what the target has any more.
        listDue = true;
      }
      refused(error);
    } else {
      failed(error);
    }
  }
  // The status that shows what the command did goes before a list that waits.
  statusDue = true;
  listWaited = false;
  changed();
}

// The request to send now, or null when nothing is due: what the operator asked for,
// then a status that is due, then a list that is due or the next part of one. Nothing is
// due while the app is not on the screen.
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
  if (listWaits) {
    listDue = false;
    listWaited = false;
    return askListPart;
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

// Begins with the address in use: forgets what an earlier target said, and asks.
export function begin() {
  target += 1;
  state.link = "checking";
  state.failure = null;
  state.status = null;
  state.heardAt = null;
  state.since = Date.now();
  state.answered = false;
  state.animations = null;
  state.cycles = [];
  wanted.length = 0;
  statusDue = true;
  listDue = false;
  listing = null;
  listWaited = false;
  askedFor = null;
  clearTimeout(listTimer);
  listTimer = null;
  changed();
  next();
}

// Says which screen is on the screen of the phone. The list is kept fresh while it is
// the show screen.
export function showing(name) {
  const was = showScreen;
  showScreen = name === "show";
  if (showScreen && !was && state.answered && listTimer === null) {
    listDue = true;
    next();
  }
}

// Takes something the operator asked for. A brightness that still waits is replaced by a
// newer one, at its place.
function want(kind, carry) {
  const waiting = kind === "brightness" ? wanted.findIndex((request) => request.kind === kind) : -1;
  if (waiting === -1) {
    wanted.push({kind, carry});
  } else {
    wanted[waiting] = {kind, carry};
  }
  next();
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
    wanted.length = 0;
  } else {
    statusDue = true;
    next();
  }
});
