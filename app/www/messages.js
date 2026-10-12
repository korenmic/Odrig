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

// The message of a command the target refused.
export function ofRefusal(refusal) {
  return `The installation refused the command. (${refusal.code})`;
}
