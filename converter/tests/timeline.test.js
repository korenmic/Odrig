import assert from "node:assert/strict";
import test from "node:test";

import {errors, jsonframes, timeline, whole} from "../lib/index.js";
import {hex, inStoredForm, numbers, storedAnswer} from "./support.js";

const {fraction} = whole;
const FITS = ["fill", "fit", "stretch"];

function refusal(error) {
  if (!(error instanceof errors.Rejection)) {
    throw error;
  }
  return {reason: error.reason, detail: error.detail};
}

// What `tickPictures` gives for frames that have times only, in the form of the stored
// answers of the Python function: the number of the frame at each tick, the frames that
// were fitted, and how many frames were asked for.
function ticksOf(frames, start, duration) {
  let asked = 0;
  const fitted = [];
  function* each() {
    for (let number = 0; number < frames.length; number += 1) {
      asked += 1;
      yield {start: fraction(...frames[number][0]), end: fraction(...frames[number][1]), picture: number};
    }
  }
  const placing = (number) => {
    fitted.push(number);
    return number;
  };
  try {
    return {ticks: timeline.tickPictures(each(), start, duration, placing), fitted, asked};
  } catch (error) {
    return {...refusal(error), asked};
  }
}

function forPython(frames, start, duration) {
  return {
    frames: frames.map(([from, to]) => [from.map(String), to.map(String)]),
    start: String(start),
    duration: duration === null ? null : String(duration),
  };
}

// Frames that follow each other, each `[start, end]` with a time as `[n, d]`: `count`
// frames at `rate` frames a second, given as `[n, d]`. The last one lasts as long as the
// others.
function steady(count, rate) {
  const [n, d] = rate;
  return Array.from({length: count}, (unused, i) => [[1000n * BigInt(d) * BigInt(i), BigInt(n)], [1000n * BigInt(d) * BigInt(i + 1), BigInt(n)]]);
}

const RATES = {
  "25 frames a second": [25, 1],
  "29.97 frames a second": [30000, 1001],
  "60 frames a second": [60, 1],
  "12.5 frames a second": [25, 2],
  "1,000 frames a second": [1000, 1],
  "3 frames a second": [3, 1],
};

test("the number of ticks of a length", () => {
  const cases = [
    [0, 1], [1, 1], [9, 1], [10, 1], [19, 1], [20, 1], [29, 1], [30, 2], [31, 2], [49, 2], [50, 3], [70, 4], [5100, 255], [41760, 2088],
    [fraction(59, 2), 1], [fraction(299, 10), 1], [fraction(30000, 1001), 1], [fraction(1001000, 30000), 2], [fraction(100, 3), 2],
    [10n ** 20n, 5n * 10n ** 18n],
  ];
  for (const [length, expected] of cases) {
    assert.equal(timeline.tickCount(length), expected, String(length.n ?? length));
  }
  assert.equal(timeline.TICK_MS, 20);
});

test("the ticks of frames with times are those of the Python tool", async (t) => {
  const cases = [];
  for (const [name, rate] of Object.entries(RATES)) {
    for (const count of [1, 2, 3, 7, 40]) {
      const frames = steady(count, rate);
      const length = Number((1000n * BigInt(rate[1]) * BigInt(count)) / BigInt(rate[0]));
      const starts = [0, 1, 19, 20, 21, 39, 40, Math.max(0, length - 21), Math.max(0, length - 20), Math.max(0, length - 1), length, length + 1, length + 500, -1, -20];
      const durations = [null, 1, 9, 10, 19, 20, 29, 30, 50, 100, Math.max(1, length - 20), length, length + 1, 0, -5];
      for (const start of starts) {
        for (const duration of durations) {
          cases.push({label: `${count} frames at ${name}, from ${start} for ${duration}`, frames, start, duration});
        }
      }
      for (const start of [...new Set(starts)].filter((value) => value >= 0 && value < length)) {
        for (const more of [-21, -20, -1, 0, 1]) {
          const duration = length - start + more;
          cases.push({label: `${count} frames at ${name}, from ${start} to ${more} ms after the end`, frames, start, duration});
        }
      }
    }
  }
  const from = numbers(1212);
  for (let i = 0; i < 300; i += 1) {
    const frames = [];
    let at = 0n;
    const count = from.between(0, 12);
    for (let number = 0; number < count; number += 1) {
      const lasts = BigInt(from.pick([0, 1, 5, 19, 20, 21, 33, 40, 41, 100, 1001]));
      const d = BigInt(from.pick([1, 1, 3, 30, 1001]));
      const end = at + lasts;
      frames.push([[at, d], [end, d]]);
      at = end;
    }
    const start = from.pick([0, 0, 0, 1, 20, 40, 100, 333]);
    const duration = from.pick([null, null, 1, 20, 40, 100, 300, 1000]);
    cases.push({label: `frames from seed ${i + 1}`, frames, start, duration});
  }
  const theirs = storedAnswer("ticks", [], cases.map(({frames, start, duration}) => forPython(frames, start, duration)));
  const reasons = new Map();

  await t.test(`${cases.length} parts of frames at six rates and of frames from seeds`, () => {
    assert.ok(cases.length > 6000, String(cases.length));
    cases.forEach(({label, frames, start, duration}, i) => {
      assert.deepEqual(inStoredForm(ticksOf(frames, start, duration), theirs[i]), theirs[i], label);
      const key = theirs[i].reason === undefined ? "ticks" : theirs[i].detail.replace(/-?\d+(\.\d+)?(e[+-]\d+)?/g, "N");
      reasons.set(key, (reasons.get(key) ?? 0) + 1);
    });
  });

  await t.test("the four cases of bad-range and a media without a picture are among them", () => {
    assert.deepEqual([...reasons.keys()].sort(), [
      "the duration is not above N",
      "the file holds no picture",
      "the part ends at N ms, after the end of the media at N ms",
      "the start is negative",
      "the start of N ms is not before the end of the media at N ms",
      "ticks",
    ]);
    for (const [key, count] of reasons) {
      assert.ok(count >= 5, `${key}: ${count}`);
    }
  });

  await t.test("a frame that is on screen at no tick is not fitted, and one on several is fitted once", () => {
    const result = ticksOf(steady(100, [1000, 1]), 0, null);
    assert.deepEqual(result.ticks, [0, 20, 40, 60, 80]);
    assert.deepEqual(result.fitted, [0, 20, 40, 60, 80]);
    const slow = ticksOf(steady(2, [3, 1]), 0, null);
    assert.deepEqual(slow.fitted, [0, 1]);
    assert.equal(slow.ticks.length, 33);
    assert.equal(slow.ticks.filter((number) => number === 0).length, 17);
  });

  await t.test("reading stops when the part is covered", () => {
    assert.equal(ticksOf(steady(40, [25, 1]), 0, 100).asked, 3, "the frame that ends at 120 ms covers the part");
    assert.equal(ticksOf(steady(40, [25, 1]), 0, 120).asked, 3);
    assert.equal(ticksOf(steady(40, [25, 1]), 0, 121).asked, 4);
    assert.equal(ticksOf(steady(40, [25, 1]), 400, 40).asked, 11);
    assert.equal(ticksOf(steady(40, [25, 1]), 0, null).asked, 40);
  });

  await t.test("the end of the media in a detail has six digits, as the Python tool writes it", () => {
    const frames = steady(7, [30000, 1001]);
    assert.deepEqual(ticksOf(frames, 300, null), {
      reason: "bad-range",
      detail: "the start of 300 ms is not before the end of the media at 233.567 ms",
      asked: 7,
    });
    assert.equal(ticksOf(frames, 0, 234).detail, "the part ends at 234 ms, after the end of the media at 233.567 ms");
    assert.equal(ticksOf(steady(1, [1, 2000]), 2000000, null).detail, "the start of 2000000 ms is not before the end of the media at 2e+06 ms");
  });

  await t.test("a start or a duration that is no whole number of milliseconds is a mistake of the program", () => {
    assert.throws(() => timeline.tickPictures([], 0.5, null, () => 0), RangeError);
    assert.throws(() => timeline.tickPictures([], 0, 1.5, () => 0), RangeError);
    assert.deepEqual(ticksOf(steady(3, [25, 1]), 0n, 40n).ticks, [0, 0]);
  });
});

// A frame of a source: a picture of one colour, or of noise from a seed.
function picture(from, width, height) {
  const rgba = from.below(2) === 0 ? from.bytes(4 * width * height) : new Uint8Array(4 * width * height).fill(from.below(256));
  for (let pixel = 0; pixel < width * height; pixel += 1) {
    rgba[4 * pixel + 3] = from.below(4) === 0 ? from.below(256) : 255;
  }
  return {width, height, rgba};
}

const BASES = [[1, 25], [1001, 30000], [1, 90000], [1, 1000], [1, 12800], [1, 1]];

// A case for `importFrames` and for the Python tool's import of the same frames: a video
// or a GIF of a few small frames with times of every kind, a canvas, a fit and a part.
function importCase(seed) {
  const from = numbers(seed);
  const kind = from.pick(["video", "video", "gif"]);
  const count = from.pick([0, 1, 1, 2, 3, 5, 8, 13]);
  const [width, height] = [from.between(1, 7), from.between(1, 6)];
  const frames = [];
  const base = from.pick(BASES);
  const step = Math.max(1, Math.round((base[1] / base[0]) * from.pick([0.02, 0.033, 0.04, 0.1, 0.25])));
  let pts = from.pick([0, 0, 7, 100000, -50]);
  const fault = from.below(8) === 0 ? from.pick(["no time", "backwards", "no pixels", "equal"]) : null;
  const faultAt = count > 0 ? from.below(count) : 0;
  for (let number = 0; number < count; number += 1) {
    const size = from.below(6) === 0 ? [from.between(1, 7), from.between(1, 6)] : [width, height];
    const frame = fault === "no pixels" && number === faultAt ? {width: from.pick([0, 3]), height: 0, rgba: new Uint8Array(0)} : picture(from, ...size);
    if (kind === "video") {
      if (fault === "backwards" && number === faultAt && number > 0) {
        pts -= 2 * step;
      } else if (!(fault === "equal" && number === faultAt)) {
        pts += number === 0 ? 0 : step + (from.below(5) === 0 ? from.below(step) : 0);
      }
      frame.pts = fault === "no time" && number === faultAt ? null : pts;
    } else {
      frame.delay = from.pick([0, 10, 11, 20, 30, 50, 70, 100, 1000, null]);
    }
    frames.push(frame);
  }
  const length = kind === "video" ? Math.round((count * step * base[0] * 1000) / base[1]) : count * 60;
  const start = from.pick([0, 0, 0, 20, 21, Math.max(0, length - 20), length, length + 40, -1]);
  const duration = from.pick([null, null, 20, 30, 100, Math.max(1, length - start), length + 20, 0]);
  return {
    kind,
    frames,
    time_base: base.map(String),
    width: from.between(1, 9),
    height: from.between(1, 7),
    fit: from.pick(FITS),
    start,
    duration,
  };
}

// The source `importFrames` is given for a case, and a count of the frames it was asked
// for.
function sourceOf(given) {
  const counted = {asked: 0};
  const [n, d] = given.time_base.map(BigInt);
  function* frames() {
    for (const frame of given.frames) {
      counted.asked += 1;
      if (given.kind === "video") {
        yield {width: frame.width, height: frame.height, rgba: frame.rgba, time: frame.pts === null ? null : [BigInt(frame.pts) * n * 1000n, d]};
      } else {
        yield {width: frame.width, height: frame.height, rgba: frame.rgba, delayMs: frame.delay};
      }
    }
  }
  return {source: {kind: given.kind, frames: frames()}, counted};
}

async function imported(given) {
  const {source, counted} = sourceOf(given);
  const name = given.kind === "video" ? "clip.mp4" : "clip.gif";
  try {
    const animation = await errors.naming(name, () => timeline.importFrames(source, {width: given.width, height: given.height}, {fit: given.fit, startMs: given.start, durationMs: given.duration}));
    return {file: hex(jsonframes.dumps(animation)), ticks: animation.frames.length, asked: counted.asked};
  } catch (error) {
    return {...refusal(error), asked: counted.asked};
  }
}

function casesForPython(cases) {
  return cases.map((given) => ({
    ...given,
    frames: given.frames.map((frame) => ({...frame, rgba: hex(frame.rgba)})),
    start: String(given.start),
    duration: given.duration === null ? null : String(given.duration),
  }));
}

test("importFrames gives the animation the Python tool imports from the same frames", async (t) => {
  const cases = Array.from({length: 700}, (unused, i) => importCase(5000 + i));
  const theirs = storedAnswer("timeline", [], casesForPython(cases));
  const outcomes = new Map();

  await t.test("for 700 videos and GIFs from seeds", async () => {
    for (let i = 0; i < cases.length; i += 1) {
      const ours = await imported(cases[i]);
      assert.deepEqual(inStoredForm(ours, theirs[i]), theirs[i], `seed ${5000 + i}: ${cases[i].kind}, ${cases[i].frames.length} frames, from ${cases[i].start} for ${cases[i].duration}, ${cases[i].fit}`);
      const key = theirs[i].reason === undefined ? "imported" : theirs[i].detail.replace(/^clip\.[a-z0-9]+: /, "").replace(/-?\d+(\.\d+)?(e[+-]\d+)?/g, "N");
      outcomes.set(key, (outcomes.get(key) ?? 0) + 1);
    }
  });

  await t.test("the cases meet every outcome", () => {
    for (const key of [
      "imported",
      "the start is negative",
      "the duration is not above N",
      "the file holds no picture",
      "the start of N ms is not before the end of the media at N ms",
      "the part ends at N ms, after the end of the media at N ms",
      "a frame has no presentation time",
      "the frames are not in the order of their times",
      "a picture has no pixels",
    ]) {
      assert.ok((outcomes.get(key) ?? 0) >= 3, `${key}: ${outcomes.get(key)} of ${JSON.stringify([...outcomes])}`);
    }
    assert.ok(outcomes.get("imported") >= 250);
  });
});

test("how long a frame of a video is on screen", async (t) => {
  const frame = (time) => ({width: 1, height: 1, rgba: Uint8Array.of(0, 0, 0, 255), time});
  const spans = (frames) => [...timeline.videoFrames(frames)].map(({start, end}) => [`${start.n}/${start.d}`, `${end.n}/${end.d}`]);

  await t.test("time is counted from the first frame, and a frame lasts until the next one starts", () => {
    assert.deepEqual(spans([frame(100), frame(140), frame(180)]), [["0/1", "40/1"], ["40/1", "80/1"], ["80/1", "120/1"]]);
  });

  await t.test("the last frame lasts for the mean interval between the frames", () => {
    assert.deepEqual(spans([frame(0), frame(10), frame(100)]), [["0/1", "10/1"], ["10/1", "100/1"], ["100/1", "150/1"]]);
    assert.deepEqual(spans([frame([0, 1]), frame([1001, 30]), frame([2002, 30])]), [["0/1", "1001/30"], ["1001/30", "1001/15"], ["1001/15", "1001/10"]]);
  });

  await t.test("a frame that is the only one lasts 20 ms", () => {
    assert.deepEqual(spans([frame(12345)]), [["0/1", "20/1"]]);
    assert.deepEqual(spans([]), []);
  });

  await t.test("the frame it gives is the frame it was given", () => {
    const first = frame(5);
    assert.equal([...timeline.videoFrames([first])][0].picture, first);
  });

  await t.test("a frame without a time, and a time below the one before, are unreadable-media", () => {
    assert.throws(() => spans([frame(0), frame(null)]), {reason: "unreadable-media", detail: "a frame has no presentation time"});
    assert.throws(() => spans([{width: 1, height: 1, rgba: new Uint8Array(4)}]), {reason: "unreadable-media", detail: "a frame has no presentation time"});
    assert.throws(() => spans([frame(0), frame(40), frame(39)]), {reason: "unreadable-media", detail: "the frames are not in the order of their times"});
    assert.deepEqual(spans([frame(0), frame(40), frame(40)]), [["0/1", "40/1"], ["40/1", "40/1"], ["40/1", "60/1"]], "two frames at the same time are in order");
  });

  await t.test("a time is a whole number of milliseconds or a fraction of two whole numbers", () => {
    const same = [[0, 40, 80], [[0, 1], [40, 1], [80, 1]], [[0n, 1n], [40n, 1n], [80n, 1n]], [0n, 40n, 80n], [[0, 1000], [40000, 1000], [160, 2]]];
    for (const times of same) {
      assert.deepEqual(spans(times.map(frame)), [["0/1", "40/1"], ["40/1", "80/1"], ["80/1", "120/1"]]);
    }
    assert.throws(() => spans([frame(33.3667)]), RangeError);
    assert.throws(() => spans([frame([1, 2, 3])]), RangeError);
    assert.throws(() => spans([frame([1, 0])]), RangeError);
    assert.throws(() => spans([frame(2 ** 53)]), RangeError);
  });
});

test("how long a frame of a GIF is on screen", async (t) => {
  const frame = (delayMs) => ({width: 1, height: 1, rgba: Uint8Array.of(0, 0, 0, 255), delayMs});
  const ends = (delays) => [...timeline.gifFrames(delays.map(frame))].map(({start, end}) => [Number(start.n), Number(end.n)]);

  await t.test("each frame for the delay the file records", () => {
    assert.deepEqual(ends([30, 50, 70]), [[0, 30], [30, 80], [80, 150]]);
  });

  await t.test("a delay of 10 ms or less counts as 100 ms", () => {
    assert.deepEqual(ends([0, 10, 11, 20]), [[0, 100], [100, 200], [200, 211], [211, 231]]);
    assert.deepEqual(ends([null, undefined, -5]), [[0, 100], [100, 200], [200, 300]]);
  });

  await t.test("delays of 30, 50, 70 and 0 ms give the ticks worked out here", async () => {
    const letters = ["A", "B", "C", "D"];
    const shown = timeline.tickPictures(timeline.gifFrames([30, 50, 70, 0].map(frame)), 0, null, (given) => letters[[30, 50, 70, 0].indexOf(given.delayMs)]);
    assert.equal(shown.join(""), "AABBCCCCDDDDD");
    const colours = [[255, 0, 0], [0, 255, 0], [0, 0, 255], [255, 255, 255]];
    const frames = [30, 50, 70, 0].map((delayMs, i) => ({width: 1, height: 1, rgba: Uint8Array.of(...colours[i], 255), delayMs}));
    const animation = await timeline.importFrames({kind: "gif", frames}, {width: 1, height: 1});
    assert.equal(animation.frames.length, 13);
    assert.ok(animation.frames.every((one) => one.ms === 20));
    assert.deepEqual(jsonframes.merged(animation.frames).map((one) => [one.ms, [...one.picture]]), [[40, colours[0]], [40, colours[1]], [80, colours[2]], [100, colours[3]]]);
  });
});

test("importFrames takes frames from whoever has them", async (t) => {
  const from = numbers(99);
  const frames = Array.from({length: 9}, (unused, i) => ({...picture(from, 6, 4), time: 40 * i}));
  const canvas = {width: 3, height: 2};
  const dumped = (animation) => hex(jsonframes.dumps(animation));

  await t.test("a synchronous and an asynchronous source give the same animation", async () => {
    async function* later() {
      for (const frame of frames) {
        await new Promise((resolve) => setTimeout(resolve, 1));
        yield frame;
      }
    }
    const fromArray = await timeline.importFrames({kind: "video", frames}, canvas);
    const fromGenerator = await timeline.importFrames({kind: "video", frames: frames.values()}, canvas);
    const fromAsync = await timeline.importFrames({kind: "video", frames: later()}, canvas);
    assert.equal(fromArray.frames.length, 18);
    assert.deepEqual([fromArray.width, fromArray.height], [3, 2]);
    assert.equal(dumped(fromGenerator), dumped(fromArray));
    assert.equal(dumped(fromAsync), dumped(fromArray));
  });

  await t.test("a source is asked for no frame after the part is covered, and its return is called", async () => {
    for (const asynchronous of [false, true]) {
      const seen = {asked: 0, returned: 0};
      const iterator = {
        next() {
          seen.asked += 1;
          const frame = frames[seen.asked - 1];
          const result = frame === undefined ? {done: true, value: undefined} : {done: false, value: frame};
          return asynchronous ? Promise.resolve(result) : result;
        },
        return() {
          seen.returned += 1;
          const result = {done: true, value: undefined};
          return asynchronous ? Promise.resolve(result) : result;
        },
      };
      const source = {kind: "video", frames: {[asynchronous ? Symbol.asyncIterator : Symbol.iterator]: () => iterator}};
      const animation = await timeline.importFrames(source, canvas, {startMs: 40, durationMs: 60});
      assert.equal(animation.frames.length, 3);
      assert.deepEqual(seen, {asked: 4, returned: 1}, "the frame that starts at 120 ms ends the one that covers the part");
    }
  });

  await t.test("a source that is read to its end is not told to stop", async () => {
    let returned = 0;
    function* all() {
      try {
        yield* frames;
      } finally {
        returned += 1;
      }
    }
    await timeline.importFrames({kind: "video", frames: all()}, canvas);
    assert.equal(returned, 1, "the generator ran to its end by itself");
  });

  await t.test("times as whole numbers, as [n, d] of Numbers and of BigInts give the same ticks", async () => {
    const timed = (time) => frames.map((frame, i) => ({...frame, time: time(i)}));
    const whole40 = await timeline.importFrames({kind: "video", frames: timed((i) => 40 * i)}, canvas);
    const numbers40 = await timeline.importFrames({kind: "video", frames: timed((i) => [40000 * i, 1000])}, canvas);
    const bigints40 = await timeline.importFrames({kind: "video", frames: timed((i) => [40000n * BigInt(i), 1000n])}, canvas);
    const microseconds = await timeline.importFrames({kind: "video", frames: timed((i) => [40000 * i + 123456789, 1000])}, canvas);
    assert.equal(dumped(numbers40), dumped(whole40));
    assert.equal(dumped(bigints40), dumped(whole40));
    assert.equal(dumped(microseconds), dumped(whole40), "time is counted from the first frame");
  });

  await t.test("a time that is not whole is taken exactly", async () => {
    const thirds = (i) => [1001 * i, 30];
    const animation = await timeline.importFrames({kind: "video", frames: frames.map((frame, i) => ({...frame, time: thirds(i)}))}, canvas);
    assert.equal(animation.frames.length, 15, "nine frames of 1001/30 ms are 300.3 ms");
  });

  await t.test("the part and the fit are options, and the rejections are those of the timeline", async () => {
    const source = () => ({kind: "video", frames});
    assert.equal((await timeline.importFrames(source(), canvas, {startMs: 100, durationMs: 100})).frames.length, 5);
    assert.notEqual(dumped(await timeline.importFrames(source(), {width: 2, height: 5}, {fit: "fit"})), dumped(await timeline.importFrames(source(), {width: 2, height: 5}, {fit: "fill"})));
    await assert.rejects(timeline.importFrames(source(), canvas, {startMs: -1}), {reason: "bad-range", detail: "the start is negative"});
    await assert.rejects(timeline.importFrames(source(), canvas, {durationMs: 0}), {reason: "bad-range", detail: "the duration is not above 0"});
    await assert.rejects(timeline.importFrames(source(), canvas, {startMs: 360}), {reason: "bad-range", detail: "the start of 360 ms is not before the end of the media at 360 ms"});
    await assert.rejects(timeline.importFrames(source(), canvas, {durationMs: 361}), {reason: "bad-range", detail: "the part ends at 361 ms, after the end of the media at 360 ms"});
    await assert.rejects(timeline.importFrames({kind: "video", frames: []}, canvas), {reason: "unreadable-media", detail: "the file holds no picture"});
    await assert.rejects(timeline.importFrames({kind: "gif", frames: []}, canvas), {reason: "unreadable-media", detail: "the file holds no picture"});
  });

  await t.test("a rejection comes before any frame is asked for when the part itself is wrong", async () => {
    let asked = 0;
    function* counting() {
      for (const frame of frames) {
        asked += 1;
        yield frame;
      }
    }
    await assert.rejects(timeline.importFrames({kind: "video", frames: counting()}, canvas, {startMs: -5}), {reason: "bad-range"});
    assert.equal(asked, 0);
  });

  await t.test("a kind or a fit that does not exist is a mistake of the program", async () => {
    await assert.rejects(timeline.importFrames({kind: "film", frames}, canvas), RangeError);
    await assert.rejects(timeline.importFrames({kind: "video", frames}, canvas, {fit: "crop"}), RangeError);
  });
});
