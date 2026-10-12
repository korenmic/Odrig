// The start of the app: which screen is shown, and the place for a message.

import * as client from "./client.js";
import * as targetScreen from "./screens/target.js";

const SCREENS = ["show", "target"];
let screen = "target";
// Whether the show screen was shown by itself after the target's first answer.
let led = false;

function byId(id) {
  return document.getElementById(id);
}

function show(name) {
  screen = name;
  for (const other of SCREENS) {
    byId(other).hidden = other !== name;
    byId(`to-${other}`).setAttribute("aria-current", String(other === name));
  }
}

// Shows a text in the place for messages until it is dismissed or another takes its
// place.
function message(text) {
  byId("message-text").textContent = text;
  byId("message").hidden = false;
}

byId("message-close").addEventListener("click", () => {
  byId("message").hidden = true;
});
byId("to-show").addEventListener("click", () => show("show"));
byId("to-target").addEventListener("click", () => show("target"));

show("target");
targetScreen.start({message, shown: () => screen === "target"});
client.watch((state) => {
  // The app begins on the target screen and goes to the show screen as soon as the
  // target has answered once.
  if (!state.answered) {
    led = false;
  } else if (!led) {
    led = true;
    show("show");
  }
});
client.begin();
