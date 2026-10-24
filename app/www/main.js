// The start of the app: which screen is shown, the place for a message, and what the
// system's back gesture does.

import * as client from "./client.js";
import * as messages from "./messages.js";
import * as showScreen from "./screens/show.js";
import * as storageScreen from "./screens/storage.js";
import * as mappingScreen from "./screens/mapping.js";
import * as targetScreen from "./screens/target.js";

const SCREENS = ["show", "storage", "mapping", "target"];
let screen = "target";
// The screen of the app's first entry of the page's history: the target screen until
// the target has answered, the show screen from then on.
let first = "target";
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
  mappingScreen.showing(name === "mapping");
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

// Whether an element is a field one types into: the style sheet names the same kind.
function isField(element) {
  return element instanceof Element && element.matches(":read-write");
}

// A long press or a right click opens a menu only in a field one types into, as the
// style sheet lets text be marked only there. Nothing of the app is done by a long press.
document.addEventListener("contextmenu", (event) => {
  if (!isField(event.target)) {
    event.preventDefault();
  }
});

// While the phone's keyboard is open for a field, the tabs are hidden and the field is
// kept in view. The app's Android shell ends the view where the keyboard begins, so the
// keyboard is open when a field one types into has the focus and the view is lower than
// three quarters of the tallest it has been at its width.
const tallest = new Map();

function typing() {
  const width = window.innerWidth;
  tallest.set(width, Math.max(tallest.get(width) || 0, window.innerHeight));
  const field = document.activeElement;
  const open = isField(field) && window.innerHeight < tallest.get(width) * 0.75;
  if (open && !document.body.classList.contains("typing")) {
    document.body.classList.add("typing");
    field.scrollIntoView({block: "nearest"});
  } else if (!open) {
    document.body.classList.remove("typing");
  }
}

window.addEventListener("resize", typing);
document.addEventListener("focusin", typing);
document.addEventListener("focusout", () => setTimeout(typing, 0));
typing();
// The page's history holds one entry of the app, its first screen, or two, with another
// screen on top. So the back gesture goes from any other screen to the first, and from
// the first it leaves the app.
function onTop() {
  return window.history.state !== null && window.history.state.depth === 1;
}

// Goes to a screen as a press of its button does: to the first screen by going back, and
// to another one on top of the first, in the place of the one on top.
function go(name) {
  if (name === screen) {
    return;
  }
  if (onTop() && name === first) {
    window.history.back();
  } else if (onTop()) {
    window.history.replaceState({screen: name, depth: 1}, "");
    show(name);
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
byId("to-storage").addEventListener("click", () => go("storage"));
byId("to-mapping").addEventListener("click", () => go("mapping"));
byId("to-target").addEventListener("click", () => go("target"));

window.history.replaceState({screen: "target", depth: 0}, "");
show("target");
targetScreen.start({message, shown: () => screen === "target"});
showScreen.start({message});
storageScreen.start({message});
mappingScreen.start();
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
      first = "show";
      show("show");
    }
  }
});
client.begin();
