// Converting a video or a GIF that the operator picked into an animation for the canvas of
// the target: the web view decodes the media, and the converter's library fits the
// pictures, builds the timeline and encodes the ODRG file. And making a text or a clock
// from the JSON source a form gives, which the same library writes as a container and
// draws as the player does.

import {Rejection, jsonframes, odrg, odrgx, timeline} from "./converter/index.js";

// The ticks of the timeline, and how far past a tick a video is sought, so that the
// picture taken is the one on the screen at the tick even when a frame begins exactly
// there.
const TICK_MS = 20;
const PAST_THE_TICK_S = 0.0005;
// The longer side of the largest picture of a video that is handed on: a larger video is
// drawn smaller by the web view first.
const LARGEST_SIDE = 1280;

// Thrown by the media when the operator stops the conversion.
export class Stopped extends Error {}

// A conversion that did not succeed, with the reason a message names: one of the
// converter's reasons, `unreadable-media` for media the web view cannot read, or
// `no-gif-decoder`. `detail` is the converter's text, or the file's name.
export class NotConverted extends Error {
  constructor(reason, detail) {
    super(`${reason}: ${detail}`);
    this.reason = reason;
    this.detail = detail;
  }
}

// Whether a file the operator picked is a GIF; every other file is taken for a video.
export function isGif(file) {
  return file.type === "image/gif" || /\.gif$/i.test(file.name);
}

// Waits for the first of some events of an element; an `error` refuses.
function either(element, names) {
  return new Promise((resolve, reject) => {
    const listeners = [];
    const done = (event) => {
      for (const [name, listener] of listeners) {
        element.removeEventListener(name, listener);
      }
      if (event.type === "error") {
        reject(new Error("the element could not read the media"));
      } else {
        resolve(event);
      }
    };
    for (const name of [...names, "error"]) {
      listeners.push([name, done]);
      element.addEventListener(name, done);
    }
  });
}

// A canvas to draw one picture onto and read it back from.
function painter(width, height) {
  const canvas = document.createElement("canvas");
  canvas.width = width;
  canvas.height = height;
  const context = canvas.getContext("2d", {willReadFrequently: true});
  return {
    take(image, drawnWidth = width, drawnHeight = height) {
      context.clearRect(0, 0, width, height);
      context.drawImage(image, 0, 0, drawnWidth, drawnHeight);
      return context.getImageData(0, 0, width, height).data;
    },
  };
}

// The length of a video in milliseconds, as its element tells it.
export async function videoLength(file) {
  const video = document.createElement("video");
  const url = URL.createObjectURL(file);
  try {
    video.muted = true;
    video.preload = "metadata";
    const loaded = either(video, ["loadedmetadata"]);
    video.src = url;
    await loaded;
    return Number.isFinite(video.duration) ? Math.round(video.duration * 1000) : null;
  } catch (error) {
    return null;
  } finally {
    video.removeAttribute("src");
    video.load();
    URL.revokeObjectURL(url);
  }
}

// The pictures of a GIF as the browser shows them, each with the delay its file records.
async function* gifFrames(file, stop) {
  if (typeof ImageDecoder === "undefined") {
    throw new NotConverted("no-gif-decoder", file.name);
  }
  let decoder;
  try {
    decoder = new ImageDecoder({data: await file.arrayBuffer(), type: "image/gif"});
    await decoder.tracks.ready;
    await decoder.completed;
  } catch (error) {
    throw new NotConverted("unreadable-media", file.name);
  }
  try {
    const count = decoder.tracks.selectedTrack.frameCount;
    let paint = null;
    for (let index = 0; index < count; index += 1) {
      stop.check(index / count);
      let image;
      try {
        image = (await decoder.decode({frameIndex: index})).image;
      } catch (error) {
        throw new NotConverted("unreadable-media", file.name);
      }
      try {
        const width = image.displayWidth;
        const height = image.displayHeight;
        paint = paint === null ? painter(width, height) : paint;
        yield {width, height, rgba: paint.take(image), delayMs: Math.round((image.duration === null ? 0 : image.duration) / 1000)};
      } finally {
        image.close();
      }
    }
  } finally {
    decoder.close();
  }
}

// The pictures of a video, one at each tick of the timeline from the start of the part on,
// each with the time of its tick, until the converter asks for no more or the video ends.
// The converter counts a video's time from its first frame, which is the start of the
// part here. A start at or after the end of the video is refused as the converter
// refuses it.
async function* videoFrames(file, startMs, lengthMs, stop) {
  const video = document.createElement("video");
  const url = URL.createObjectURL(file);
  try {
    video.muted = true;
    video.preload = "auto";
    const loaded = either(video, ["loadeddata"]);
    video.src = url;
    try {
      await loaded;
    } catch (error) {
      throw new NotConverted("unreadable-media", file.name);
    }
    const ends = video.duration * 1000;
    if (startMs >= ends) {
      throw new NotConverted("bad-range", `the start of ${startMs} ms is not before the end of the media`);
    }
    const shrink = Math.min(1, LARGEST_SIDE / Math.max(video.videoWidth, video.videoHeight));
    const width = Math.max(1, Math.round(video.videoWidth * shrink));
    const height = Math.max(1, Math.round(video.videoHeight * shrink));
    const paint = painter(width, height);
    const until = lengthMs === null ? ends : Math.min(ends, startMs + lengthMs);
    for (let at = startMs; at < ends; at += TICK_MS) {
      stop.check(Math.min(1, (at - startMs) / Math.max(1, until - startMs)));
      const sought = either(video, ["seeked"]);
      video.currentTime = at / 1000 + PAST_THE_TICK_S;
      try {
        await sought;
      } catch (error) {
        throw new NotConverted("unreadable-media", file.name);
      }
      yield {width, height, rgba: paint.take(video), time: at};
    }
  } finally {
    video.removeAttribute("src");
    video.load();
    URL.revokeObjectURL(url);
  }
}

// A conversion that can be stopped, and that tells how far it has come, from 0 to 1.
export function stopper(progress) {
  let stopped = false;
  return {
    stop() {
      stopped = true;
    },
    check(done) {
      if (stopped) {
        throw new Stopped("stopped");
      }
      progress(done);
    },
  };
}

// The animation of a media file for a canvas, and the bytes of its ODRG file. `fit` is
// `fill`, `fit` or `stretch`; `startMs` is the start of the part and `lengthMs` its
// length, or null for the rest of the media. Ticks that follow each other with the same
// picture are one frame, as the converter's command line writes them.
export async function convert(file, canvas, {fit, startMs, lengthMs}, stop) {
  const gif = isGif(file);
  const source = gif ? {kind: "gif", frames: gifFrames(file, stop)} : {kind: "video", frames: videoFrames(file, startMs, lengthMs, stop)};
  let animation;
  try {
    const part = {fit, startMs: gif ? startMs : 0, durationMs: lengthMs};
    const ticks = await timeline.importFrames(source, {width: canvas.width, height: canvas.height}, part);
    animation = {...ticks, frames: jsonframes.merged(ticks.frames)};
  } catch (error) {
    if (error instanceof Rejection) {
      throw new NotConverted(error.reason, error.detail);
    }
    throw error;
  }
  stop.check(1);
  return {animation, bytes: odrg.encode(animation, {compressed: true})};
}

// The container of a text or a clock, as bytes, from its JSON source as an object: the
// library reads it as strictly as a file, and refuses it with its reason.
export function makeContainer(source) {
  try {
    return odrgx.encodeSource(odrgx.loadsSource(new TextEncoder().encode(JSON.stringify(source))));
  } catch (error) {
    if (error instanceof Rejection) {
      throw new NotConverted(error.reason, error.detail);
    }
    throw error;
  }
}

// What a container holds, read from its bytes: its header, as `header` with its `width`,
// `height` and `loopMs`, and its type, as `type`.
export function readContainer(bytes) {
  return odrgx.decode(bytes);
}

// The picture the player draws of a container that was read, `ms` milliseconds into its
// turn, a clock with a seed: three bytes for each pixel, the bottom row first.
export function pictureOf(read, ms, seed) {
  return odrgx.pictureAt(read, ms, seed);
}
