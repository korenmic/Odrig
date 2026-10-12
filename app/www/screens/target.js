// The target screen: the address, whether the target answers, and how requests travel.

import * as client from "../client.js";
import * as messages from "../messages.js";
import {BOARD, Failure, address, route, setAddress} from "../target.js";

const LINKS = {checking: "Checking", answers: "Answers", "no-answer": "No answer"};

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

// Starts the screen. `message` shows a text in the place for messages; `shown` says
// whether this screen is the one on the screen of the phone.
export function start({message, shown}) {
  const field = byId("address");
  field.value = address();

  function take(text) {
    try {
      field.value = setAddress(text);
    } catch (error) {
      if (!(error instanceof Failure)) {
        throw error;
      }
      message(messages.ofFailure(error));
      return;
    }
    client.begin();
  }

  byId("use").addEventListener("click", () => take(field.value));
  byId("board").addEventListener("click", () => take(BOARD));
  byId("about").textContent = webView();

  client.watch((state) => {
    byId("link").textContent = LINKS[state.link];
    say("link-failure", state.failure === null ? null : messages.ofFailure(state.failure));
    const reason = state.link === "answers" && state.status !== null ? state.status.error : null;
    say("invalid", reason === null ? null : messages.ofInvalidShow(reason));
    if (shown()) {
      route().then((found) => {
        byId("route").textContent = routeLine(found);
      });
    }
  });
}
