// Uploading an animation the app made: the id and the file name it gets, whether it fits
// into the free storage, and the job that sends it to the target one line after the
// other.

import * as commands from "./commands.js";
import {crc32} from "./crc32.js";

const LONGEST_NAME = 32;
const ENDING = ".odrg";
// How long the app waits before it asks again whether the target has checked the file.
const CHECKED_AGAIN_MS = 250;
// The time over which the speed is measured.
const SPEED_OVER_MS = 2000;

// The lowest id from 1 up that none of these ids is, or null when there is none.
export function freeId(taken) {
  for (let id = 1; id <= 65535; id += 1) {
    if (!taken.has(id)) {
      return id;
    }
  }
  return null;
}

// The file name an animation made from a media file gets: the media's name without its
// ending, in lower case, every character outside a-z, 0-9, `-` and `_` turned into `-`,
// cut so that with `.odrg` it has at most 32 characters, and made unique among the names
// taken with `-2`, `-3` and so on.
export function fileName(mediaName, taken) {
  const base = mediaName.replace(/\.[^.]*$/, "").toLowerCase().replace(/[^a-z0-9_-]/g, "-") || "animation";
  const room = LONGEST_NAME - ENDING.length;
  for (let number = 1; ; number += 1) {
    const added = number === 1 ? "" : `-${number}`;
    const name = base.slice(0, room - added.length) + added + ENDING;
    if (!taken.has(name)) {
      return name;
    }
  }
}

// Whether a file of some bytes fits into the free storage, as the target judges it.
export function fits(bytes, free) {
  return bytes + Math.floor(bytes / 256) + 16384 <= free;
}

// Bytes in base64 with the alphabet of RFC 4648, section 5, without `=` at the end.
function base64(bytes) {
  let text = "";
  for (let at = 0; at < bytes.length; at += 1) {
    text += String.fromCharCode(bytes[at]);
  }
  return btoa(text).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
}

// The upload of a file as a job of the client. `next()` gives the function that sends the
// next line and takes its reply, or null while there is none to send now. `report` is told
// the part of the file the target has received and the speed in bytes a second, `end` how
// the upload ended: `{done: true}`, `{cancelled: true}`, or `{error}` with the Refusal or
// the Failure that ended it. `wake` asks the client to look for the next line again.
export function uploading({id, file, bytes}, {report, end, wake}) {
  const crc = crc32(bytes);
  let stage = "begin";
  let chunk = 0;
  let received = 0;
  let waitUntil = 0;
  let cancelled = false;
  const samples = [];

  function finish(how) {
    if (stage !== "over") {
      stage = "over";
      end(how);
    }
  }

  function speed() {
    const now = performance.now();
    while (samples.length > 1 && now - samples[1].at >= SPEED_OVER_MS) {
      samples.shift();
    }
    const first = samples[0];
    const last = samples[samples.length - 1];
    return last.at > first.at ? ((last.received - first.received) * 1000) / (last.at - first.at) : 0;
  }

  return {
    id,
    file,
    over() {
      return stage === "over";
    },
    cancel() {
      cancelled = true;
      wake();
    },
    // The line that ended the job threw: a refusal or a failure of the way.
    failed(error) {
      finish({error});
    },
    next() {
      if (stage === "over") {
        return null;
      }
      if (cancelled) {
        if (stage === "begin") {
          finish({cancelled: true});
          return null;
        }
        return async () => {
          try {
            await commands.uploadCancel();
          } catch (error) {
            if (!(error instanceof commands.Refusal)) {
              throw error;
            }
          }
          finish({cancelled: true});
        };
      }
      if (performance.now() < waitUntil) {
        return null;
      }
      if (stage === "begin") {
        return async () => {
          chunk = await commands.uploadBegin(id, file, bytes.length);
          stage = "data";
          samples.push({at: performance.now(), received: 0});
          report(0, 0);
        };
      }
      if (stage === "data") {
        return async () => {
          received = await commands.uploadData(received, base64(bytes.subarray(received, Math.min(bytes.length, received + chunk))));
          samples.push({at: performance.now(), received});
          report(received / bytes.length, speed());
          if (received >= bytes.length) {
            stage = "end";
          }
        };
      }
      return async () => {
        try {
          await commands.uploadEnd(crc);
        } catch (error) {
          if (error instanceof commands.Refusal && error.code === "busy") {
            // The target still checks the file: the end is sent again a moment later.
            waitUntil = performance.now() + CHECKED_AGAIN_MS;
            setTimeout(wake, CHECKED_AGAIN_MS);
            return;
          }
          throw error;
        }
        finish({done: true});
      };
    },
  };
}
