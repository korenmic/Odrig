// The previews of the animations: the default preview catalog that comes with the app,
// `thumbnails/`, which maps the key of an animation's file to its GIF, and the square of a
// row or of the panel of what plays, which shows the preview of a key or stays empty.

import defaults from "./thumbnails/catalog.js";

// The source of the preview of a key: the GIF of the default catalog beside the app, or
// null when it has none.
export function sourceOf(key) {
  if (key === null || !Object.prototype.hasOwnProperty.call(defaults, key)) {
    return null;
  }
  return `thumbnails/${defaults[key].gif}`;
}

// Whether the default catalog holds a key.
export function inDefaults(key) {
  return Object.prototype.hasOwnProperty.call(defaults, key);
}

// Shows a preview in a square, or nothing: the image is made, changed or taken out only when
// its source differs, so that a square that shows a preview keeps it while it is redrawn.
export function show(square, source) {
  const image = square.querySelector("img");
  if (source === null) {
    if (image !== null) {
      image.remove();
    }
    return;
  }
  if (image !== null && image.getAttribute("src") === source) {
    return;
  }
  const made = image === null ? square.ownerDocument.createElement("img") : image;
  made.alt = "";
  made.draggable = false;
  made.decoding = "async";
  made.setAttribute("src", source);
  if (image === null) {
    square.append(made);
  }
}
