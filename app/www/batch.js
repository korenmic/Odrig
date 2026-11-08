// The run of a batch of animations, one after another through the app's upload.

// Whether a run is under way.
export function running() {
  return false;
}

// What the run says of a row, or null while the row has not been in a run.
export function rowOf() {
  return null;
}

// How a row ended in the last run, or null.
export function outcomeOf() {
  return null;
}
