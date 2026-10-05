import { imagePoint, decodeExclusion, encodeExclusion, paintExclusionSegment } from './exclude-mask.js';

// Zone-only spatial editing. Never sample LIVE's rendered colors or alter PSD
// pixels. SOURCE and LIVE are two views of exactly the same document mask.
export function installExcludeBrush({ getContext, isActive, onCommit, onStatus }) {
  const surfaces = ['source', 'live'].map((kind) => ({
    canvas: document.getElementById(kind + 'Canvas'),
    overlay: document.getElementById(kind + 'ExcludeOverlay'),
    stage: document.getElementById(kind + 'Stage'),
  }));
  const cursor = document.getElementById('excludeCursor');
  const controls = document.getElementById('excludeControls');
  const size = document.getElementById('excludeSize');
  const sizeValue = document.getElementById('excludeSizeValue');
  const undoButton = document.getElementById('excludeUndo');
  const clearButton = document.getElementById('excludeClear');
  const histories = new Map();
  let stroke = null, hover = null, frame = 0;

  function diameter() { return Math.max(1, Math.min(512, Number(size.value) || 80)); }
  function historyKey(context) { return context.key + ':' + context.zone.id; }
  function remember(context, mask) {
    const key = historyKey(context), history = histories.get(key) || [];
    history.push(mask);
    if (history.length > 12) history.shift();
    histories.delete(key);
    histories.set(key, history);
    while (histories.size > 24) histories.delete(histories.keys().next().value);
  }
  function sameTarget(context) {
    return context && stroke && context.zone === stroke.context.zone && context.key === stroke.context.key;
  }
  function cursorAt(event, surface) {
    hover = { event: { clientX: event.clientX, clientY: event.clientY, shiftKey: event.shiftKey }, surface };
    const context = getContext(), rect = surface.canvas.getBoundingClientRect();
    const point = context && imagePoint(event, rect, context.width, context.height);
    cursor.hidden = !isActive() || !point?.inside;
    if (cursor.hidden) return;
    cursor.style.left = event.clientX + 'px';
    cursor.style.top = event.clientY + 'px';
    cursor.style.width = diameter() * rect.width / context.width + 'px';
    cursor.style.height = diameter() * rect.height / context.height + 'px';
    cursor.classList.toggle('restoring', Boolean(stroke ? stroke.erase : event.shiftKey));
    cursor.dataset.imageX = point.x.toFixed(2);
    cursor.dataset.imageY = point.y.toFixed(2);
    document.getElementById('pickReticle').hidden = true;
  }
  function renderOverlay() {
    frame = 0;
    const context = getContext(), active = isActive() && context;
    controls.hidden = !isActive();
    surfaces.forEach(({ canvas, overlay }) => {
      canvas.classList.toggle('exclude-armed', Boolean(active));
      overlay.hidden = !active;
    });
    if (!context) { cursor.hidden = true; return; }
    if (stroke && !sameTarget(context)) cancel();
    const mask = stroke ? stroke.pixels : decodeExclusion(context.zone.spatialMask, context.width, context.height);
    const reference = surfaces[0].overlay;
    reference.width = context.width;
    reference.height = context.height;
    const ctx = reference.getContext('2d');
    const data = ctx.createImageData(context.width, context.height);
    let count = 0;
    for (let index = 0; index < mask.length; index += 1) {
      if (mask[index] !== 2) continue;
      const offset = index * 4;
      data.data[offset] = 255; data.data[offset + 1] = 45;
      data.data[offset + 2] = 65; data.data[offset + 3] = 115;
      count += 1;
    }
    ctx.putImageData(data, 0, 0);
    const other = surfaces[1].overlay;
    other.width = context.width; other.height = context.height;
    other.getContext('2d').drawImage(reference, 0, 0);
    document.getElementById('excludeCoverage').textContent = count ? 'Drawn exclusion: ' + count.toLocaleString() + ' pixels' : 'No drawn exclusions';
    undoButton.disabled = !histories.get(historyKey(context))?.length;
    clearButton.disabled = !count;
    if (hover) cursorAt(hover.event, hover.surface);
    if (!active) cursor.hidden = true;
  }
  function refresh() { if (!frame) frame = requestAnimationFrame(renderOverlay); }
  function release(current) {
    if (current?.canvas.hasPointerCapture?.(current.pointerId)) current.canvas.releasePointerCapture(current.pointerId);
  }
  function cancel() {
    const current = stroke;
    stroke = null;
    release(current);
    refresh();
  }
  function moveStroke(event) {
    if (!stroke || stroke.pointerId !== event.pointerId) return;
    if (!sameTarget(getContext())) { cancel(); return; }
    const { context, canvas } = stroke;
    const point = imagePoint(event, canvas.getBoundingClientRect(), context.width, context.height);
    stroke.changed = paintExclusionSegment(stroke.pixels, context.width, context.height, stroke.last, point, stroke.radius, stroke.erase) || stroke.changed;
    stroke.last = point;
    refresh();
  }
  for (const surface of surfaces) {
    const { canvas, stage } = surface;
    canvas.addEventListener('pointerdown', (event) => {
      if (!isActive() || event.button !== 0 || stroke || event.isPrimary === false) return;
      const context = getContext();
      if (!context || !imagePoint(event, canvas.getBoundingClientRect(), context.width, context.height).inside) return;
      event.preventDefault();
      canvas.focus({ preventScroll: true });
      const point = imagePoint(event, canvas.getBoundingClientRect(), context.width, context.height);
      stroke = { context, canvas, pointerId: event.pointerId, before: context.zone.spatialMask || null,
        pixels: decodeExclusion(context.zone.spatialMask, context.width, context.height), last: point,
        radius: diameter() / 2, erase: event.shiftKey, changed: false };
      canvas.setPointerCapture(event.pointerId);
      cursorAt(event, surface);
      moveStroke(event);
    });
    canvas.addEventListener('pointermove', (event) => { cursorAt(event, surface); moveStroke(event); });
    canvas.addEventListener('pointerup', (event) => {
      if (!stroke || stroke.pointerId !== event.pointerId) return;
      moveStroke(event);
      const current = stroke;
      stroke = null;
      release(current);
      if (current?.changed) {
        const next = encodeExclusion(current.pixels, current.context.width, current.context.height);
        remember(current.context, current.before);
        current.context.zone.spatialMask = next;
        onCommit();
      }
      refresh();
    });
    canvas.addEventListener('pointercancel', cancel);
    canvas.addEventListener('lostpointercapture', () => { if (stroke?.canvas === canvas) cancel(); });
    canvas.addEventListener('pointerleave', () => { hover = null; cursor.hidden = true; });
    stage.addEventListener('scroll', () => { if (hover) cursorAt(hover.event, hover.surface); }, { passive: true });
    new ResizeObserver(() => { if (hover) cursorAt(hover.event, hover.surface); }).observe(canvas);
  }
  function undo() {
    cancel();
    const context = getContext();
    const history = context && histories.get(historyKey(context));
    if (!history?.length) return;
    context.zone.spatialMask = history.pop();
    onCommit(); refresh();
    onStatus('Undid the last drawn exclusion.');
  }
  undoButton.addEventListener('click', undo);
  clearButton.addEventListener('click', () => {
    cancel();
    const context = getContext();
    if (!context?.zone.spatialMask) return;
    remember(context, context.zone.spatialMask);
    context.zone.spatialMask = null;
    onCommit(); refresh();
    onStatus('Cleared drawn exclusions for this zone. Undo is available.');
  });
  function updateSize(value) {
    size.value = Math.max(1, Math.min(512, Math.round(Number(value) || 80)));
    sizeValue.value = size.value;
    if (hover) cursorAt(hover.event, hover.surface);
  }
  size.addEventListener('input', () => updateSize(size.value));
  sizeValue.addEventListener('input', () => {
    if (!sizeValue.value || Number(sizeValue.value) <= 0) return;
    size.value = Math.max(1, Math.min(512, Math.round(Number(sizeValue.value))));
    if (hover) cursorAt(hover.event, hover.surface);
  });
  sizeValue.addEventListener('change', () => updateSize(sizeValue.value));
  document.addEventListener('keydown', (event) => {
    if (!isActive() || event.target.closest('input, textarea, select, [contenteditable="true"]') || document.querySelector('dialog[open]')) return;
    if (event.key === 'Escape' && stroke) { event.preventDefault(); cancel(); onStatus('Exclusion stroke canceled.'); }
    else if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'z' && !event.shiftKey) { event.preventDefault(); undo(); }
    else if (event.key === '[' || event.key === ']') { event.preventDefault(); updateSize(diameter() + (event.key === ']' ? 8 : -8)); }
  });
  window.addEventListener('blur', () => { cancel(); hover = null; cursor.hidden = true; });
  return { refresh, cancel, reset() { cancel(); histories.clear(); hover = null; cursor.hidden = true; refresh(); } };
}
