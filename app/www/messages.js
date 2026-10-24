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

// Why an animation is unavailable, in words, from the reason the installation gives for
// its file, which follows in brackets.
export function ofFault(reason) {
  const words = {
    "file-missing": "the file is missing",
    "read-error": "the file cannot be read",
    "size-mismatch": "the file is made for another canvas",
    "duplicate-id": "no id is left for it",
  }[reason] ?? "the file is damaged";
  return `Unavailable: ${words} (${reason}).`;
}

// The line under an unavailable file of external storage, which the installation does not
// change.
export const MENDED_ELSEWHERE = "Fix it on a computer: the card is read-only here.";

// The line of the show screen while the target does not answer.
export function ofSilence(seconds) {
  return `The installation has not answered for ${seconds} ${seconds === 1 ? "second" : "seconds"}.`;
}

// The error codes of the command list that no command of the app can get.
export const NOT_FOR_THE_APP = [];

const NOT_UNDERSTOOD = () => "The installation did not understand the app. Its software and this app do not match.";
const REFUSED = () => "The installation refused the command.";
const NOT_WHOLE = () => "The upload did not arrive whole. Upload again.";

// A size in kilobytes of 1,000 bytes, rounded up.
function kilobytes(bytes) {
  return String(Math.ceil(bytes / 1000));
}

// The text for each error code a command of the app can get, from the line that was
// refused, from the reason of an invalid show, when the target has said one, and from the
// refusal itself.
const REFUSALS = {
  "line-too-long": NOT_UNDERSTOOD,
  "unknown-command": NOT_UNDERSTOOD,
  "bad-argument": NOT_UNDERSTOOD,
  "show-invalid": (line, reason) =>
    `${reason === null ? "The installed show is invalid." : ofInvalidShow(reason)} Nothing can be played until a show is installed over USB.`,
  "unknown-id": (line) => line.startsWith("order ") ? "That animation is not on the installation any more. The list is read again." : line.startsWith("remove many ") ? "Some selected animations are not installed any more. Refresh the selection." : (line === "play all" ? "No animation is installed." : `Animation ${line.split(" ")[1]} is not installed any more.`),
  unavailable: (line) => `Animation ${line.split(" ")[1]} cannot be played until it is replaced: its file has a fault. The list says which.`,
  busy: () => "The installation is busy. Try again in a moment.",
  "in-use": (line) =>
    line.startsWith("remove many ") ? "Some selected animations cannot be removed: a cycle plays them, or they are on external storage." :
    line.startsWith("ignore ") ? "Only installed animations support playlist inclusion." :
    line.startsWith("order ") ? "A cycle has no place in the order of the playlist." :
    line.startsWith("upload ")
      ? "That name or id is in use on the installation. The list is asked for again; upload again."
      : `Animation ${line.split(" ")[1]} cannot be removed: a cycle plays it, or it is on a USB stick.`,
  "mapping-conflict": () => "Mapping changed on the target. Reload before saving.",
  "order-conflict": () => "The order changed on the installation since the app read it. The list is read again; move the animation again.",
  stale: () => "Another controller changed this animation since it was opened. Your changes are still here; open it again to see the new one.",
  "storage-error": () => "The installation could not use its storage.",
  "no-space": (line) => ofNoSpace(Number(line.split(" ")[4]), null).replace(/ \(no-space\)$/, ""),
  "bad-file": (line, reason, refusal) => `The installation refused the file: ${refusal.reason === null ? "it is not a valid animation" : refusal.reason}.`,
  "bad-checksum": NOT_WHOLE,
  incomplete: NOT_WHOLE,
  "bad-offset": NOT_WHOLE,
  "no-upload": () => "The installation dropped the upload, after the app was away for a minute or more. Upload again.",
};

// What the app says of an animation that does not fit into the free storage. The free
// bytes are null when the app does not know them.
export function ofNoSpace(bytes, free) {
  const room = free === null ? "more than the installation has free" : `and the installation has ${kilobytes(free)} KB free`;
  return `The animation needs ${kilobytes(bytes)} KB, ${room}. (no-space)`;
}

// What the app says when an upload succeeded. It is no failure and has no code.
export function ofUploaded(id, file) {
  return `Uploaded as animation ${id} ${file}. It plays in the playlist.`;
}

// What the app says when an animation cannot be made from a file, by the reason: its own,
// or one of the library that makes it, whose text is given as the detail.
const CONVERSIONS = {
  "unsupported-character": (detail) => `The fonts have no letter for ${detail.replace(/^[^:]*: /, "")}. Write English letters, digits, signs and Hebrew letters.`,
  "does-not-fit": (detail) => `The text cannot be seen whole on the canvas with this effect: ${detail.replace(/^[^;]*; /, "")}.`,
  "no-canvas": () => "The installation has no usable mapping, so the app does not know the canvas to convert for.",
  "no-gif-decoder": () => "This phone's web view cannot read GIF files. Update Android System WebView.",
  "unreadable-media": () => "The phone cannot read this file as a video or a GIF.",
  "bad-part": () => "Write the start and the length in seconds, like 2.5, and leave the length empty for the rest of the file.",
  "bad-range": () => "The part does not lie inside the file. Make the start earlier or the length shorter.",
};

export function ofConversion(failure) {
  const text = Object.prototype.hasOwnProperty.call(CONVERSIONS, failure.reason) ? CONVERSIONS[failure.reason](failure.detail) : `The animation cannot be made: ${failure.detail}.`;
  return `${text} (${failure.reason})`;
}

// The question before an animation is removed.
export function ofRemoval(animation) {
  return `Remove animation ${animation.id} ${animation.file} from the installation?`;
}

// What the app says when an animation was removed. It is no failure and has no code.
export function ofRemoved(animation) {
  return `Removed animation ${animation.id} ${animation.file}.`;
}

// The message of a command the target refused. A code without a text of its own gets
// the general sentence.
export function ofRefusal(refusal, reason = null) {
  const text = Object.prototype.hasOwnProperty.call(REFUSALS, refusal.code) ? REFUSALS[refusal.code] : REFUSED;
  return `${text(refusal.line, reason, refusal)} (${refusal.code})`;
}
