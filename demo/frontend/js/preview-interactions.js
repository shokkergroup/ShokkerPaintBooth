export const VIEWPORT_ZOOM_MIN = 0.5;
export const VIEWPORT_ZOOM_MAX = 6;
export const VIEWPORT_ZOOM_FACTOR = 1.2;

function finiteNumber(value, fallback = 0) {
  const number = Number(value);
  return Number.isFinite(number) ? number : fallback;
}

export function clampViewportZoom(value) {
  return Math.max(VIEWPORT_ZOOM_MIN, Math.min(VIEWPORT_ZOOM_MAX, finiteNumber(value, 1)));
}

export function stepViewportZoom(value, direction) {
  const current = clampViewportZoom(value);
  if (!direction) return current;
  return clampViewportZoom(current * (direction > 0 ? VIEWPORT_ZOOM_FACTOR : 1 / VIEWPORT_ZOOM_FACTOR));
}

export function wheelViewportZoom(value, deltaY) {
  const delta = finiteNumber(deltaY);
  if (!delta) return clampViewportZoom(value);
  return stepViewportZoom(value, delta < 0 ? 1 : -1);
}

export function calculateViewportAnchor(stageRect, canvasRect, clientX, clientY) {
  const stageWidth = Math.max(1, finiteNumber(stageRect?.width, finiteNumber(stageRect?.right) - finiteNumber(stageRect?.left)));
  const stageHeight = Math.max(1, finiteNumber(stageRect?.height, finiteNumber(stageRect?.bottom) - finiteNumber(stageRect?.top)));
  const canvasWidth = Math.max(1, finiteNumber(canvasRect?.width, finiteNumber(canvasRect?.right) - finiteNumber(canvasRect?.left)));
  const canvasHeight = Math.max(1, finiteNumber(canvasRect?.height, finiteNumber(canvasRect?.bottom) - finiteNumber(canvasRect?.top)));
  const localX = Math.max(0, Math.min(stageWidth, finiteNumber(clientX, finiteNumber(stageRect?.left) + stageWidth / 2) - finiteNumber(stageRect?.left)));
  const localY = Math.max(0, Math.min(stageHeight, finiteNumber(clientY, finiteNumber(stageRect?.top) + stageHeight / 2) - finiteNumber(stageRect?.top)));
  const imageX = Math.max(0, Math.min(1, (finiteNumber(stageRect?.left) + localX - finiteNumber(canvasRect?.left)) / canvasWidth));
  const imageY = Math.max(0, Math.min(1, (finiteNumber(stageRect?.top) + localY - finiteNumber(canvasRect?.top)) / canvasHeight));
  return { localX, localY, imageX, imageY };
}
