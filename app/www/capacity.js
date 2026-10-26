// Capacity wording shared by the Show and Storage screens, with the number of animations
// of each storage.

function animations(count) {
  return count === 1 ? "1 animation" : `${count} animations`;
}

// The numbers of animations, each a number or null when it is not known: `internal` of the
// show, from `space`, which reports 0 while the show is invalid; `external` of the drive,
// undefined while no drive is present. The drive's are the items that say they are on it
// when every item says where it is, and otherwise the listed animations less the show's.
export function counts(state) {
  const space = state.space;
  const invalid = state.status !== null && state.status.error !== null;
  const internal = space === null || invalid || typeof space.animations !== "number" ? null : space.animations;
  if (space === null || space.external?.present !== true) {
    return {internal, external: undefined};
  }
  const listed = state.animations;
  if (state.listBusy || listed === null) {
    return {internal, external: null};
  }
  if (listed.length > 0 && listed.every((item) => typeof item.external === "boolean")) {
    return {internal, external: listed.filter((item) => item.external).length};
  }
  const external = internal === null ? -1 : listed.length - internal;
  return {internal, external: external < 0 ? null : external};
}

export function internal(space, count) {
  if (space === null) return "-";
  const capacity = `${(space.free / 1000000).toFixed(1)} MB of ${(space.total / 1000000).toFixed(1)} MB`;
  if (count === undefined) return `Free ${capacity}`;
  return `${count === null ? "animations not known" : animations(count)}, free ${capacity}`;
}

// Whether the target may write the medium of its external storage: one is present and
// `space` says it is not read-only.
export function cardWritable(space) {
  return space !== null && space.external?.present === true && space.external.read_only === false;
}

export function external(space, count) {
  const drive = space?.external;
  if (!drive) return "External storage: capacity unavailable (read-only).";
  if (!drive.present) return "External storage: absent (read-only).";
  const locked = cardWritable(space) ? "" : " (read-only)";
  const number = count === undefined ? "" : `${count === null ? "animations not known yet" : animations(count)}, `;
  if (drive.free === null) return `External storage: ${number}capacity unavailable${locked}.`;
  const unit = drive.total >= 1000000000 ? 1000000000 : 1000000;
  const name = unit === 1000000000 ? "GB" : "MB";
  return `External storage: ${number}free ${(drive.free / unit).toFixed(1)} ${name} of ${(drive.total / unit).toFixed(1)} ${name}${locked}.`;
}
