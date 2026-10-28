// The two filters over the list of Animations: by where an animation is stored and by its
// type. A filter changes what the list shows, never what the installation plays or keeps.

import {isExternal} from "./show.js";

const STORAGE = [["all", "All"], ["internal", "Internal"], ["external", "External"]];
const TYPE = [["all", "All"], ["frames", "Normal"], ["text", "Text"], ["widget", "Widget"]];
const KEYS = {storage: "odrig.filter.storage", type: "odrig.filter.type"};

// The choices: kept on the phone, All at first.
const chosen = {storage: kept("storage", STORAGE), type: kept("type", TYPE)};
let redraw = () => {};

function byId(id) {
  return document.getElementById(id);
}

function kept(filter, choices) {
  try {
    const value = window.localStorage.getItem(KEYS[filter]);
    return choices.some(([name]) => name === value) ? value : "all";
  } catch (error) {
    return "all";
  }
}

function keep(filter, value) {
  try {
    window.localStorage.setItem(KEYS[filter], value);
  } catch (error) {
    // A web view without storage keeps the choice until the app ends.
  }
}

// The type of an animation as `list` reports it; one without a type is a normal one, of
// frames.
export function typeOf(animation) {
  return animation.type === "text" || animation.type === "widget" ? animation.type : "frames";
}

function storageIs(animation, choice) {
  return choice === "all" || (choice === "external") === isExternal(animation);
}

function typeIs(animation, choice) {
  return choice === "all" || typeOf(animation) === choice;
}

// Whether an animation is shown with the filters as they are.
export function matches(animation) {
  return storageIs(animation, chosen.storage) && typeIs(animation, chosen.type);
}

// Sets back to All each filter that hides an animation, so that its row is shown.
export function reveal(animation) {
  for (const [filter, shows] of [["storage", storageIs], ["type", typeIs]]) {
    if (!shows(animation, chosen[filter])) {
      chosen[filter] = "all";
      keep(filter, "all");
    }
  }
}

// Whether a filter hides anything: a choice is not All.
export function filtering() {
  return chosen.storage !== "all" || chosen.type !== "all";
}

function group(filter, choices) {
  const place = byId(`filter-${filter}`);
  place.replaceChildren(...choices.map(([name, words]) => {
    const button = document.createElement("button");
    button.type = "button";
    button.dataset.choice = name;
    const label = document.createElement("span");
    label.textContent = words;
    const count = document.createElement("span");
    count.className = "count";
    button.append(label, " ", count);
    button.addEventListener("click", () => {
      chosen[filter] = name;
      keep(filter, name);
      redraw();
    });
    return button;
  }));
}

// Draws the choices with the number of rows each would show, the other filter as it is:
// the rows of the level shown when the screen gives them, else every animation.
export function draw(state, rows = state.animations) {
  const animations = rows === null ? [] : rows;
  byId("filters").hidden = (state.animations === null ? [] : state.animations).length === 0;
  for (const [filter, choices, counted] of [["storage", STORAGE, (name) => animations.filter((item) => storageIs(item, name) && typeIs(item, chosen.type)).length],
                                            ["type", TYPE, (name) => animations.filter((item) => typeIs(item, name) && storageIs(item, chosen.storage)).length]]) {
    for (const button of byId(`filter-${filter}`).children) {
      const name = button.dataset.choice;
      button.setAttribute("aria-pressed", String(chosen[filter] === name));
      button.querySelector(".count").textContent = String(counted(name));
      button.setAttribute("aria-label", `${choices.find((choice) => choice[0] === name)[1]}, ${counted(name)}`);
    }
  }
}

export function start(options) {
  redraw = options.redraw;
  group("storage", STORAGE);
  group("type", TYPE);
  byId("filter-reset").addEventListener("click", () => {
    for (const filter of ["storage", "type"]) {
      chosen[filter] = "all";
      keep(filter, "all");
    }
    redraw();
  });
}
