// Capacity wording shared by the Show and Storage screens.
export function internal(space) {
  return space === null ? "-" : `Free ${(space.free / 1000000).toFixed(1)} MB of ${(space.total / 1000000).toFixed(1)} MB`;
}

export function external(space) {
  const drive = space?.external;
  if (!drive) return "External storage: capacity unavailable (read-only).";
  if (!drive.present) return "External storage: absent (read-only).";
  if (drive.free === null) return "External storage: capacity unavailable (read-only).";
  const unit = drive.total >= 1000000000 ? 1000000000 : 1000000;
  const name = unit === 1000000000 ? "GB" : "MB";
  return `External storage: free ${(drive.free / unit).toFixed(1)} ${name} of ${(drive.total / unit).toFixed(1)} ${name} (read-only).`;
}
