// SPB-93 / DEMO-12 (2026-09-04): native-image coordinates are the sole
// authority for Exclude. CSS fit, browser zoom, scrolling and DPR never enter
// the stored mask. A stroke is a round capsule, not a set of spaced clicks.
export function imagePoint(event, rect, width, height) {
  const x = (event.clientX - rect.left) * width / rect.width;
  const y = (event.clientY - rect.top) * height / rect.height;
  return { x, y, inside: Number.isFinite(x + y) && x >= 0 && y >= 0 && x < width && y < height };
}

export function decodeExclusion(mask, width, height) {
  const pixels = new Uint8Array(width * height);
  if (!mask || mask.width !== width || mask.height !== height || !Array.isArray(mask.runs)) return pixels;
  let offset = 0;
  for (const run of mask.runs) {
    if (!Array.isArray(run) || ![0, 2].includes(run[0]) || !Number.isSafeInteger(run[1]) || run[1] < 1 || offset + run[1] > pixels.length) return new Uint8Array(pixels.length);
    pixels.fill(run[0], offset, offset + run[1]);
    offset += run[1];
  }
  return offset === pixels.length ? pixels : new Uint8Array(pixels.length);
}

export function encodeExclusion(pixels, width, height) {
  const runs = [];
  let value = pixels[0], count = 0, any = false;
  for (const pixel of pixels) {
    any ||= pixel === 2;
    if (pixel === value) count += 1;
    else { runs.push([value, count]); value = pixel; count = 1; }
  }
  if (count) runs.push([value, count]);
  return any ? { width, height, runs } : null;
}

export function paintExclusionSegment(pixels, width, height, from, to, radius, erase = false) {
  if (![from.x, from.y, to.x, to.y, radius].every(Number.isFinite) || radius <= 0) return false;
  const left = Math.max(0, Math.floor(Math.min(from.x, to.x) - radius));
  const right = Math.min(width - 1, Math.ceil(Math.max(from.x, to.x) + radius));
  const top = Math.max(0, Math.floor(Math.min(from.y, to.y) - radius));
  const bottom = Math.min(height - 1, Math.ceil(Math.max(from.y, to.y) + radius));
  const dx = to.x - from.x, dy = to.y - from.y, length2 = dx * dx + dy * dy;
  const value = erase ? 0 : 2, radius2 = radius * radius;
  let changed = false;
  for (let y = top; y <= bottom; y += 1) {
    for (let x = left; x <= right; x += 1) {
      const px = x + .5 - from.x, py = y + .5 - from.y;
      const t = length2 ? Math.max(0, Math.min(1, (px * dx + py * dy) / length2)) : 0;
      if ((px - t * dx) ** 2 + (py - t * dy) ** 2 > radius2) continue;
      const index = y * width + x;
      if (pixels[index] !== value) { pixels[index] = value; changed = true; }
    }
  }
  return changed;
}

export function prepareImportedZoneScopes(zones, layers, isFlat, changedDocument) {
  for (const zone of zones) {
    if (isFlat && layers.length === 1) zone.sourceLayers = [String(layers[0].id)];
    else if ((zone.sourceLayers || []).every((id) => id === 'flattened-source')) zone.sourceLayers = [];
    // Missing real PSD layer IDs still fail closed; never silently broaden them.
    zone.sourceLayer = zone.sourceLayers[0] || null;
    // Do not transfer hand-drawn exclusions to an unrelated livery.
    if (changedDocument) zone.spatialMask = null;
  }
}
