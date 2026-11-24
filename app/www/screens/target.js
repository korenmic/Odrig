// The target screen: the address, whether the target answers, the name of the
// installation and its last fault, and how requests travel.

import * as client from "../client.js";
import * as messages from "../messages.js";
import {BOARD, Failure, address, link, route, setAddress, setLink, usbPossible} from "../target.js";

const LINKS = {checking: "Checking", answers: "Answers", "no-answer": "No answer"};

// Whether the screen is on the screen of the phone, whether the last fault is to be asked
// for while it is, and the target the line of the last fault belongs to.
let visible = false;
let faultWanted = false;
let faultOf = null;

function byId(id) {
  return document.getElementById(id);
}

function say(id, text) {
  const place = byId(id);
  place.textContent = text === null ? "" : text;
  place.hidden = text === null;
}

// The line that says how requests travel, of what the sender reports.
function routeLine(found) {
  if (!found.sender) {
    return "Sent from this browser.";
  }
  if (found.usb) {
    return "Sent over USB serial.";
  }
  if (!found.wifi) {
    return "This phone is not on a Wi-Fi network.";
  }
  let line = "Sent over Wi-Fi.";
  if (!found.validated) {
    line += found.others === "mobile" ? " This Wi-Fi network has no internet: the phone's other apps use mobile data." : " This Wi-Fi network has no internet.";
  }
  if (found.portal) {
    line += " The phone offers to sign in to it. That is not needed.";
  }
  return line;
}

function webView() {
  const found = /Chrome\/([0-9]+)/.exec(navigator.userAgent);
  return found === null ? "Web view of an unknown version" : `Web view ${found[1]}`;
}

// Asks for the last fault once the screen is shown and the target answers. The line stays
// as the reply left it until the screen is shown again.
function askFault() {
  if (!visible || !faultWanted || client.state.link !== "answers") {
    return;
  }
  faultWanted = false;
  const version = client.targetVersion();
  client.lastFault().then((found) => {
    if (version === client.targetVersion()) {
      faultOf = version;
      say("last-fault", found === null ? null : messages.ofLastFault(found));
    }
  }, () => {});
}

// Says whether the screen is on the screen of the phone. Each time it is shown after the
// target has answered, the last fault is asked for.
export function showing(shown) {
  visible = shown;
  if (shown && client.state.answered) {
    faultWanted = true;
    askFault();
  }
}

// Starts the screen. `message` shows a text in the place for messages; `shown` says
// whether this screen is the one on the screen of the phone.
export function start({message, shown}) {
  const field = byId("address");
  field.value = address();

  function take(text) {
    try {
      field.value = setAddress(text.trim() === "" ? BOARD : text);
    } catch (error) {
      if (!(error instanceof Failure)) {
        throw error;
      }
      message(messages.ofFailure(error));
      return;
    }
    client.begin();
  }

  // The switch shows the block of the link in use; a choice of the other is a change of
  // target.
  const choices = [...document.querySelectorAll('#link-choice input[name="link"]')];
  function showLink() {
    const kind = link();
    for (const choice of choices) {
      choice.checked = choice.value === kind;
      choice.disabled = choice.value === "usb" && !usbPossible();
    }
    say("link-why", usbPossible() ? null : "This browser has no USB serial port; the Android app has.");
    byId("wifi-link").hidden = kind !== "wifi";
    byId("usb-link").hidden = kind !== "usb";
  }
  for (const choice of choices) {
    choice.addEventListener("change", () => {
      if (!choice.checked || choice.value === link()) return;
      setLink(choice.value);
      showLink();
      client.begin();
    });
  }
  showLink();
  byId("connect-wifi").addEventListener("click", () => take(field.value));
  byId("connect-usb").addEventListener("click", () => client.begin());
  byId("about").textContent = webView();

  client.watch((state) => {
    byId("link").textContent = LINKS[state.link];
    say("link-failure", state.failure === null ? null : messages.ofFailure(state.failure));
    const reason = state.link === "answers" && state.status !== null ? state.status.error : null;
    say("invalid", reason === null ? null : messages.ofInvalidShow(reason));
    const host = state.status === null ? null : state.status.host;
    say("host", host === null ? null : messages.ofHost(host));
    if (faultOf !== null && faultOf !== client.targetVersion()) {
      // The line was of a target that is not the one in use any more.
      faultOf = null;
      say("last-fault", null);
    }
    askFault();
    byId("usb-state").textContent = state.link === "answers" ? "A board answers on USB serial." : "Connect the phone to the board's USB port with a cable, then press Connect over USB.";
    if (shown()) {
      route().then((found) => {
        byId("route").textContent = routeLine(found);
      });
    }
  });
}
