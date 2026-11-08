import {snapshot} from "./time-zone.js";

self.onmessage = event => {
  try {
    const bytes = snapshot(event.data.zone);
    self.postMessage({ok: true, bytes}, [bytes.buffer]);
  } catch (error) {
    self.postMessage({ok: false, error: error instanceof Error ? error.message : "The phone could not prepare its time zone."});
  }
};
