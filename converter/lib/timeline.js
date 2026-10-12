// The 50 frames-per-second timeline: the 20 ms ticks of a part of a media, the rules that
// say how long a frame of a video or of a GIF is on screen, and the import of frames that
// someone else decoded.
//
// Times are exact fractions of milliseconds. A caller gives a time as a whole number of
// milliseconds, or as `[n, d]`, the fraction n / d of two whole numbers.

import {BAD_RANGE, Rejection, UNREADABLE_MEDIA} from "./errors.js";
import {FITS, place} from "./fit.js";
import {add, ceil, compare, div, floor, fraction, mul, sixDigits, sub, whole} from "./whole.js";

export const TICK_MS = 20;
export const SHORTEST_GIF_DELAY_MS = 10;
export const GIF_DELAY_MS = 100;

// The fraction of a time a caller gave, or null when there is none.
function timeOf(value) {
  if (value === null || value === undefined) {
    return null;
  }
  if (Array.isArray(value)) {
    if (value.length !== 2) {
      throw new RangeError("a time given as a fraction is [n, d]");
    }
    return fraction(value[0], value[1]);
  }
  if (typeof value === "number" && !Number.isSafeInteger(value)) {
    throw new RangeError(`${value} is no whole number of milliseconds; give a time that is not whole as [n, d]`);
  }
  return fraction(value);
}

function wholeMs(value, what) {
  if (typeof value !== "bigint" && !Number.isSafeInteger(value)) {
    throw new RangeError(`${what} is given in whole milliseconds`);
  }
  return BigInt(value);
}

// The number of 20 ms ticks of a length: the nearest whole number, halves up, at least 1.
export function tickCount(length) {
  const ticks = floor(div(add(mul(length, 2), TICK_MS), 2 * TICK_MS));
  return whole(ticks < 1n ? 1n : ticks);
}

// Collects one canvas picture for each tick of the part that starts at `startMs` and lasts
// `durationMs`, or runs to the end of the media when that is null. `add` takes the frames
// in order, each `{start, end, picture}`, and says whether the part is covered; `finish`
// gives the pictures, or refuses a part that is not inside the media.
function ticker(startMs, durationMs, placing) {
  const start = wholeMs(startMs, "the start");
  const duration = durationMs === null || durationMs === undefined ? null : wholeMs(durationMs, "the duration");
  if (start < 0n) {
    throw new Rejection(BAD_RANGE, "the start is negative");
  }
  if (duration !== null && duration <= 0n) {
    throw new Rejection(BAD_RANGE, "the duration is not above 0");
  }
  const wanted = duration === null ? null : BigInt(tickCount(duration));
  const stop = duration === null ? null : start + duration;
  const pictures = [];
  let length = null;
  return {
    add(frame) {
      const end = fraction(frame.end);
      length = end;
      // The frame is on screen at every tick n with start + 20 * n below its end.
      let upTo = ceil(div(sub(end, start), TICK_MS));
      if (wanted !== null && upTo > wanted) {
        upTo = wanted;
      }
      if (upTo > BigInt(pictures.length)) {
        const picture = placing(frame.picture);
        for (let n = BigInt(pictures.length); n < upTo; n += 1n) {
          pictures.push(picture);
        }
      }
      return stop !== null && compare(end, stop) >= 0;
    },
    finish() {
      if (length === null) {
        throw new Rejection(UNREADABLE_MEDIA, "the file holds no picture");
      }
      if (compare(start, length) >= 0) {
        throw new Rejection(BAD_RANGE, `the start of ${start} ms is not before the end of the media at ${sixDigits(length)} ms`);
      }
      if (stop !== null && compare(stop, length) > 0) {
        throw new Rejection(BAD_RANGE, `the part ends at ${stop} ms, after the end of the media at ${sixDigits(length)} ms`);
      }
      const keep = wanted !== null ? wanted : BigInt(tickCount(sub(length, start)));
      return pictures.slice(0, Number(keep));
    },
  };
}

// One canvas picture for each 20 ms tick of the requested part of a media.
//
// `frames` gives `{start, end, picture}` for each frame in the order they are shown, with
// `start` and `end` in milliseconds. The first tick is at `startMs`. A tick shows the frame
// that is on screen at its time: the last frame that starts no later. `placing` turns the
// picture of a frame into a canvas picture and is called once for each frame that is on
// screen at a tick. Without a duration the part runs to the end of the last frame. No frame
// is asked for after the part is covered.
export function tickPictures(frames, startMs, durationMs, placing) {
  const ticks = ticker(startMs, durationMs, placing);
  for (const frame of frames) {
    if (ticks.add(frame)) {
      break;
    }
  }
  return ticks.finish();
}

function sized(frame) {
  if (frame.width === 0 || frame.height === 0) {
    throw new Rejection(UNREADABLE_MEDIA, "a picture has no pixels");
  }
}

// The timing rule of a video: time is counted from the first frame; a frame is on screen
// until the next one starts, and the last one for the mean interval between the frames, or
// for 20 ms when it is the only one. `take` is given the frames in order and gives the
// frame before, which is then complete, or null; `end` gives the last frame.
function videoTiming() {
  let first = null;
  let held = null;
  let count = 0;
  return {
    take(frame) {
      const at = timeOf(frame.time);
      if (at === null) {
        throw new Rejection(UNREADABLE_MEDIA, "a frame has no presentation time");
      }
      if (first === null) {
        first = at;
      }
      const time = sub(at, first);
      sized(frame);
      let complete = null;
      if (held !== null) {
        if (compare(time, held.start) < 0) {
          throw new Rejection(UNREADABLE_MEDIA, "the frames are not in the order of their times");
        }
        complete = {start: held.start, end: time, picture: held.frame};
      }
      held = {start: time, frame};
      count += 1;
      return complete;
    },
    end() {
      if (held === null) {
        return null;
      }
      const interval = count > 1 ? div(held.start, count - 1) : fraction(TICK_MS);
      return {start: held.start, end: add(held.start, interval), picture: held.frame};
    },
  };
}

// The timing rule of a GIF: each frame is on screen for the delay the file records, a
// delay of 10 ms or less counted as 100 ms, and the frames are gone through once.
function gifTiming() {
  let start = fraction(0);
  return {
    take(frame) {
      let delay = timeOf(frame.delayMs);
      if (delay === null || compare(delay, SHORTEST_GIF_DELAY_MS) <= 0) {
        delay = fraction(GIF_DELAY_MS);
      }
      sized(frame);
      const complete = {start, end: add(start, delay), picture: frame};
      start = complete.end;
      return complete;
    },
    end() {
      return null;
    },
  };
}

function* timed(timing, frames) {
  for (const frame of frames) {
    const complete = timing.take(frame);
    if (complete !== null) {
      yield complete;
    }
  }
  const last = timing.end();
  if (last !== null) {
    yield last;
  }
}

// `{start, end, picture}` for each frame of a video, given frames with a `time`, their
// presentation time in milliseconds from any starting point. `picture` is the frame as it
// was given. A frame without a time, and a time below the one before, are refused.
export function videoFrames(frames) {
  return timed(videoTiming(), frames);
}

// `{start, end, picture}` for each frame of a GIF, given frames with a `delayMs`.
export function gifFrames(frames) {
  return timed(gifTiming(), frames);
}

// The animation of decoded frames on a canvas: one frame of 20 ms for each tick.
//
// `source` is `{kind, frames}`. `kind` is "video" or "gif". `frames` is an iteration,
// synchronous or asynchronous, that is asked for one frame at a time and for none after
// the part is covered. A frame is a source picture, `{width, height, rgba}`, with its
// `time` for a video and its `delayMs` for a GIF; the picture of a GIF frame is the picture
// as it is on screen, with every earlier frame applied. `canvas` has the `width` and the
// `height` of the canvas. The options are those of `import`: `fit`, "fill" when it is not
// given; `startMs`, 0; and `durationMs`, to the end of the media.
export async function importFrames(source, canvas, {fit = "fill", startMs = 0, durationMs = null} = {}) {
  if (!FITS.includes(fit)) {
    throw new RangeError(`there is no fit "${fit}"`);
  }
  if (source.kind !== "video" && source.kind !== "gif") {
    throw new RangeError(`a source is a "video" or a "gif", not "${source.kind}"`);
  }
  const {width, height} = canvas;
  const timing = source.kind === "video" ? videoTiming() : gifTiming();
  const ticks = ticker(startMs, durationMs, (frame) => place(frame, width, height, fit));
  let covered = false;
  for await (const frame of source.frames) {
    const complete = timing.take(frame);
    if (complete !== null && ticks.add(complete)) {
      covered = true;
      break;
    }
  }
  if (!covered) {
    const last = timing.end();
    if (last !== null) {
      ticks.add(last);
    }
  }
  return {width, height, frames: ticks.finish().map((picture) => ({ms: TICK_MS, picture}))};
}
