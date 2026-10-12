// Every text the app says about a failure. A message ends with its code in brackets.

const FAILURES = {
  "bad-address": () => "That is not an address. Write it like 4.3.2.1 or 192.168.1.23:8600.",
  "no-wifi": () => "This phone is not on a Wi-Fi network. Join the network odrig in the phone's Wi-Fi settings.",
  "no-answer": (detail) => `No answer from ${detail}. Check that the phone is on the installation's Wi-Fi network and that the installation has power.`,
  "bad-reply": (detail) => `Something answered at ${detail}, but it is not an odrig installation.`,
};

// The message of a Failure of the way to the target.
export function ofFailure(failure) {
  return `${FAILURES[failure.kind](failure.detail)} (${failure.kind})`;
}

// What the screens say of a show the target calls invalid.
export function ofInvalidShow(reason) {
  return `The installed show is invalid: ${reason}.`;
}

// The line of the show screen while the target does not answer.
export function ofSilence(seconds) {
  return `The installation has not answered for ${seconds} ${seconds === 1 ? "second" : "seconds"}.`;
}

// The error codes of the command list that no command of the app can get: they belong to
// `remove`, `space` and `upload`, which the app does not send.
export const NOT_FOR_THE_APP = ["no-upload", "incomplete", "bad-checksum", "busy", "in-use", "no-space", "bad-offset", "bad-file", "storage-error"];

const NOT_UNDERSTOOD = () => "The installation did not understand the app. Its software and this app do not match.";
const REFUSED = () => "The installation refused the command.";

// The text for each error code a command of the app can get, from the line that was
// refused and from the reason of an invalid show, when the target has said one.
const REFUSALS = {
  "line-too-long": NOT_UNDERSTOOD,
  "unknown-command": NOT_UNDERSTOOD,
  "bad-argument": NOT_UNDERSTOOD,
  "show-invalid": (line, reason) =>
    `${reason === null ? "The installed show is invalid." : ofInvalidShow(reason)} Nothing can be played until a show is installed over USB.`,
  "unknown-id": (line) => (line === "play all" ? "No animation is installed." : `Animation ${line.split(" ")[1]} is not installed any more.`),
};

// The message of a command the target refused. A code without a text of its own gets
// the general sentence.
export function ofRefusal(refusal, reason = null) {
  const text = Object.prototype.hasOwnProperty.call(REFUSALS, refusal.code) ? REFUSALS[refusal.code] : REFUSED;
  return `${text(refusal.line, reason)} (${refusal.code})`;
}
