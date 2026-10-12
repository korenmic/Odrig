// The start of the app: which screen is shown, the place for a message, and what the
// system's back gesture does.

import * as client from "./client.js";
import * as messages from "./messages.js";
import * as showScreen from "./screens/show.js";
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
  client.showing(name);
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
// The page's history holds one entry of the app, its first screen, or two, with the
// other screen on top. So the back gesture goes from the second screen to the first,
// and from the first it leaves the app.
function onTop() {
  return window.history.state !== null && window.history.state.depth === 1;
}

// Goes to a screen as a press of its button does.
function go(name) {
  if (name === screen) {
    return;
  }
  if (onTop()) {
    window.history.back();
  } else {
    window.history.pushState({screen: name, depth: 1}, "");
    show(name);
  }
}

window.addEventListener("popstate", (event) => {
  if (event.state !== null && SCREENS.includes(event.state.screen)) {
    show(event.state.screen);
  }
});
byId("to-show").addEventListener("click", () => go("show"));
byId("to-target").addEventListener("click", () => go("target"));

window.history.replaceState({screen: "target", depth: 0}, "");
show("target");
targetScreen.start({message, shown: () => screen === "target"});
showScreen.start();
client.onRefusal((refusal) => message(messages.ofRefusal(refusal, client.state.status === null ? null : client.state.status.error)));
client.watch((state) => {
  // The app begins on the target screen and goes to the show screen as soon as the
  // target has answered once. The show screen is the app's first screen from then on.
  if (!state.answered) {
    led = false;
  } else if (!led) {
    led = true;
    if (screen === "target" && onTop()) {
      window.history.back();
    } else if (screen === "target") {
      window.history.replaceState({screen: "show", depth: 0}, "");
      show("show");
    }
  }
});
client.begin();
