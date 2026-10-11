/* The page: the event stream, the header, the reason band, the log, the readout and the
   count of refreshes drawn. The page sends no command. */

(function () {
  "use strict";

  var LOG_ROWS = 500;

  function byId(id) {
    return document.getElementById(id);
  }

  var stage = byId("stage");
  var host = byId("drawing");
  var note = byId("note");
  var entries = byId("entries");
  var logBox = byId("log");

  var hello = null;
  var mapping = null;
  var drawing = null;
  var newest = null;
  var waiting = false;
  var drawn = 0;
  var second = Math.floor(performance.now() / 1000);
  var statusError = null;

  /* The count of refreshes drawn in the last full second. */
  function roll() {
    var now = Math.floor(performance.now() / 1000);
    if (now !== second) {
      byId("page-fps").textContent = now === second + 1 ? String(drawn) : "0";
      drawn = 0;
      second = now;
    }
  }

  function draw() {
    waiting = false;
    roll();
    if (drawing && newest) {
      drawing.paint(newest);
      drawn += 1;
    }
  }

  function bytesOf(encoded) {
    var text = atob(encoded);
    var bytes = new Uint8Array(text.length);
    for (var i = 0; i < text.length; i += 1) {
      bytes[i] = text.charCodeAt(i);
    }
    return bytes;
  }

  function showReason() {
    var reason = statusError !== null ? statusError : hello && hello.error;
    byId("band").hidden = !reason;
    byId("reason").textContent = reason || "";
  }

  function say(text) {
    note.hidden = !text;
    note.textContent = text || "";
    host.hidden = Boolean(text);
  }

  /* Builds the drawing for the size the stage has now. */
  function build() {
    drawing = null;
    if (!hello || !mapping) {
      return;
    }
    if (!hello.legs.length) {
      say("There are no LEDs to draw: the core has no valid mapping.");
      return;
    }
    say("");
    var f = OdrigLayout.fit(mapping, stage.clientWidth, stage.clientHeight);
    drawing = OdrigView.build(host, mapping, hello.legs, f);
    if (newest) {
      drawing.paint(newest);
    }
    showReason();
  }

  function shortPath(path) {
    var parts = path.split("/");
    return parts.length > 3 ? "\u2026/" + parts.slice(-2).join("/") : path;
  }

  function onHello(event) {
    hello = JSON.parse(event.data);
    mapping = null;
    newest = null;
    statusError = null;
    entries.textContent = "";
    byId("empty").hidden = false;
    byId("show").textContent = shortPath(hello.show);
    byId("show").title = hello.show;
    byId("serial").textContent = shortPath(hello.serial);
    byId("serial").title = hello.serial;
    document.title = "odrig emulator \u2013 " + hello.show.split("/").pop();
    showReason();
    if (!hello.legs.length) {
      mapping = {width: 0, height: 0, legs: []};
      build();
      return;
    }
    fetch("show/mapping.json", {cache: "no-store"}).then(function (answer) {
      if (!answer.ok) {
        throw new Error("status " + answer.status);
      }
      return answer.text();
    }).then(function (text) {
      mapping = OdrigLayout.read(text);
      build();
    }).catch(function (error) {
      say("The mapping file of the show could not be read: " + error.message);
    });
  }

  function onStatus(event) {
    var status = JSON.parse(event.data);
    var power = byId("power");
    power.dataset.on = String(status.on);
    power.textContent = status.on ? "on" : "off";
    byId("brightness").textContent = String(status.brightness);
    byId("brightness-bar").style.width = Math.round(100 * status.brightness / 255) + "%";
    byId("playing").textContent = status.playing === null ? "nothing" : String(status.playing);
    byId("animation").textContent = status.animation === null ? "none" : String(status.animation);
    byId("core-fps").textContent = String(status.fps);
    statusError = status.error;
    showReason();
  }

  function cell(row, name, text) {
    var made = document.createElement("td");
    made.className = name;
    made.textContent = text;
    row.appendChild(made);
    return made;
  }

  function onLog(event) {
    var entry = JSON.parse(event.data);
    var follow = logBox.scrollTop + logBox.clientHeight >= logBox.scrollHeight - 30;
    var row = document.createElement("tr");
    var ok = null;
    try {
      ok = JSON.parse(entry.reply).ok;
    } catch (error) {
      ok = null;
    }
    row.dataset.ok = String(ok);
    row.className = "new";
    cell(row, "time", entry.time);
    var via = cell(row, "via", "");
    var chip = document.createElement("span");
    chip.className = "chip";
    chip.dataset.via = entry.transport;
    chip.textContent = entry.transport;
    via.appendChild(chip);
    var line = cell(row, "line", entry.line);
    if (entry.cut) {
      var mark = document.createElement("span");
      mark.className = "cut";
      mark.title = "The line was longer than 64 characters.";
      mark.textContent = "\u2026";
      line.appendChild(mark);
    }
    cell(row, "reply", entry.reply);
    entries.appendChild(row);
    while (entries.children.length > LOG_ROWS) {
      entries.removeChild(entries.firstChild);
    }
    byId("empty").hidden = true;
    if (follow) {
      logBox.scrollTop = logBox.scrollHeight;
    }
  }

  function onFrame(event) {
    var space = event.data.indexOf(" ");
    newest = bytesOf(event.data.slice(space + 1));
    if (!waiting) {
      waiting = true;
      requestAnimationFrame(draw);
    }
  }

  function onPointer(event) {
    var readout = byId("readout");
    if (!drawing) {
      readout.textContent = "";
      return;
    }
    var box = host.getBoundingClientRect();
    var found = drawing.at(event.clientX - box.left, event.clientY - box.top);
    if (!found) {
      readout.textContent = "";
      return;
    }
    var leg = mapping.legs[found.leg];
    readout.textContent = "leg " + leg.leg + ", pin " + leg.pin + ", LED " + found.led + " (" + found.x + "," + found.y + ")";
  }

  var link = byId("link");
  var source = new EventSource("events");
  source.onopen = function () {
    link.dataset.state = "connected";
    link.textContent = "connected";
  };
  source.onerror = function () {
    link.dataset.state = "lost";
    link.textContent = "not connected";
  };
  source.addEventListener("hello", onHello);
  source.addEventListener("status", onStatus);
  source.addEventListener("log", onLog);
  source.addEventListener("frame", onFrame);

  host.addEventListener("pointermove", onPointer);
  host.addEventListener("pointerleave", function () {
    byId("readout").textContent = "";
  });
  /* The drawing is made again whenever the stage changes its size. */
  var sizing = false;
  function resized() {
    if (!sizing) {
      sizing = true;
      requestAnimationFrame(function () {
        sizing = false;
        build();
      });
    }
  }
  if (window.ResizeObserver) {
    new ResizeObserver(resized).observe(stage);
  }
  window.addEventListener("resize", resized);
  setInterval(roll, 250);
}());
