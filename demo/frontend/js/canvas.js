const imageCache = new Map();
const IMAGE_CACHE_LIMIT = 24;

export function clearImageCache() {
  imageCache.clear();
}

export function loadImage(source) {
  if (!source) return Promise.reject(new Error('Image source is empty.'));
  if (imageCache.has(source)) {
    const cached = imageCache.get(source);
    imageCache.delete(source);
    imageCache.set(source, cached);
    return cached;
  }
  let promise;
  promise = new Promise((resolve, reject) => {
    const image = new Image();
    image.decoding = 'async';
    image.onload = () => resolve(image);
    image.onerror = () => reject(new Error('Could not decode image data.'));
    image.src = source;
  }).catch((error) => {
    if (imageCache.get(source) === promise) imageCache.delete(source);
    throw error;
  });
  imageCache.set(source, promise);
  while (imageCache.size > IMAGE_CACHE_LIMIT) imageCache.delete(imageCache.keys().next().value);
  return promise;
}

export function flattenLayerTree(nodes, depth = 0, output = []) {
  const isRoot = depth === 0;
  (Array.isArray(nodes) ? nodes : []).forEach((node, index) => {
    const children = node.children || node.layers || [];
    const isGroup = Boolean(node.is_group || node.type === 'group' || children.length);
    if (isGroup) {
      flattenLayerTree(children, depth + 1, output);
      return;
    }
    const bbox = Array.isArray(node.bbox) && node.bbox.length === 4 ? node.bbox.map(Number) : null;
    output.push({
      id: String(node.layer_key || node.id || `layer-${depth}-${index}-${output.length}`),
      key: String(node.layer_key || node.id || ''),
      name: String(node.name || node.path || `Layer ${output.length + 1}`),
      path: String(node.path || node.name || ''),
      depth,
      visible: node.visible !== false,
      opacity: Math.max(0, Math.min(1, Number(node.opacity ?? 255) > 1 ? Number(node.opacity ?? 255) / 255 : Number(node.opacity ?? 1))),
      blendMode: normalizeBlendMode(node.blend_mode || node.blendMode || 'normal'),
      bbox,
      hue: 0,
      saturation: 0,
      brightness: 0,
      overlayColor: '#ffffff',
      overlayOpacity: 0,
      flipH: false,
      flipV: false,
      rotation: 0,
      rasterUrl: '',
      _sourceIndex: output.length,
    });
  });
  // psd-tools exposes PSD children in compositing order (bottom -> top).
  // The layer rail, hit testing, and UP/DOWN controls use the Photoshop panel
  // contract instead: index 0 is topmost and the base is last. Reverse exactly
  // once at the root import boundary; composeLayers reverses this UI order to
  // paint the document from its base upward.
  if (isRoot) output.reverse();
  return output;
}

export function layersInCompositeOrder(layers) {
  return [...(Array.isArray(layers) ? layers : [])].reverse();
}

export function attachRasterizedLayers(layers, rasterized, fallbackComposite, width, height) {
  const table = (rasterized && (rasterized.layers || rasterized)) || {};
  layers.forEach((layer) => {
    const exact = table[layer.key] || table[layer.id];
    const value = exact && typeof exact === 'object' ? exact : null;
    layer.rasterUrl = (value && (value.image || value.data_url || value.url)) || (typeof exact === 'string' ? exact : '');
    if (value && Array.isArray(value.bbox) && value.bbox.length === 4) layer.bbox = value.bbox.map(Number);
  });
  const usable = layers.filter((layer) => layer.rasterUrl);
  if (usable.length) return usable;
  return [{
    id: 'flattened-source', key: 'flattened-source', name: 'Flattened Source', path: 'Flattened Source', depth: 0,
    visible: true, opacity: 1, blendMode: 'normal', bbox: [0, 0, width, height], hue: 0, saturation: 0,
    brightness: 0, overlayColor: '#ffffff', overlayOpacity: 0, flipH: false, flipV: false, rotation: 0,
    rasterUrl: fallbackComposite, _sourceIndex: 0,
  }];
}

export function normalizeBlendMode(mode) {
  const value = String(mode || 'normal').toLowerCase().replaceAll('_', '-').replace('blendmode.', '');
  const aliases = {
    'pass-through': 'normal',
    'linear-dodge': 'lighter',
    'color-dodge': 'color-dodge',
    'color-burn': 'color-burn',
  };
  const mapped = aliases[value] || value;
  const supported = new Set(['normal', 'multiply', 'screen', 'overlay', 'darken', 'lighten', 'color-dodge', 'color-burn', 'hard-light', 'soft-light', 'difference', 'exclusion', 'hue', 'saturation', 'color', 'luminosity', 'lighter']);
  return supported.has(mapped) ? mapped : 'normal';
}

function validBox(box, width, height) {
  if (!Array.isArray(box) || box.length !== 4) return [0, 0, width, height];
  const [left, top, right, bottom] = box.map(Number);
  if (![left, top, right, bottom].every(Number.isFinite) || right <= left || bottom <= top) return [0, 0, width, height];
  return [left, top, right, bottom];
}

async function buildLayerSurface(layer, width, height) {
  const surface = document.createElement('canvas');
  surface.width = width;
  surface.height = height;
  const ctx = surface.getContext('2d', { willReadFrequently: true });
  const image = await loadImage(layer.rasterUrl);
  const [left, top, right, bottom] = validBox(layer.bbox, width, height);
  const drawWidth = right - left;
  const drawHeight = bottom - top;
  const centerX = left + drawWidth / 2;
  const centerY = top + drawHeight / 2;
  ctx.save();
  ctx.translate(centerX, centerY);
  ctx.rotate((Number(layer.rotation) || 0) * Math.PI / 180);
  ctx.scale(layer.flipH ? -1 : 1, layer.flipV ? -1 : 1);
  const hue = Number(layer.hue) || 0;
  const sat = Math.max(0, 100 + (Number(layer.saturation) || 0));
  const bright = Math.max(0, 100 + (Number(layer.brightness) || 0));
  ctx.filter = `hue-rotate(${hue}deg) saturate(${sat}%) brightness(${bright}%)`;
  ctx.drawImage(image, -drawWidth / 2, -drawHeight / 2, drawWidth, drawHeight);
  ctx.restore();
  ctx.filter = 'none';
  if ((Number(layer.overlayOpacity) || 0) > 0) {
    ctx.save();
    ctx.globalCompositeOperation = 'source-atop';
    ctx.globalAlpha = Math.max(0, Math.min(1, Number(layer.overlayOpacity)));
    ctx.fillStyle = layer.overlayColor || '#ffffff';
    ctx.fillRect(0, 0, width, height);
    ctx.restore();
  }
  layer._surface = surface;
  return surface;
}

async function buildSourceLayerScopePixels(layers, selectedIds, width, height, includeRgb) {
  const wanted = new Set((selectedIds || []).map(String));
  if (!wanted.size) return null;
  const pixelCount = width * height;
  const union = new Uint8Array(pixelCount);
  const ownerRgba = includeRgb ? new Uint8ClampedArray(pixelCount * 4) : null;
  const aboveAlpha = new Uint8Array(pixelCount);
  for (const layer of layers || []) {
    if (!layer.visible || !layer.rasterUrl) continue;
    try {
      const surface = layer._surface || await buildLayerSurface(layer, width, height);
      const data = surface.getContext('2d', { willReadFrequently: true }).getImageData(0, 0, width, height).data;
      const opacity = Math.max(0, Math.min(1, Number(layer.opacity)));
      if (wanted.has(String(layer.id))) {
        for (let pixel = 0, offset = 3; pixel < pixelCount; pixel += 1, offset += 4) {
          if (!union[pixel] && data[offset] * opacity >= 128 && aboveAlpha[pixel] < 128) {
            union[pixel] = 255;
            if (ownerRgba) {
              const target = pixel * 4;
              ownerRgba[target] = data[offset - 3];
              ownerRgba[target + 1] = data[offset - 2];
              ownerRgba[target + 2] = data[offset - 1];
              ownerRgba[target + 3] = 255;
            }
          }
        }
      }
      // Mask/Wire template helpers do not steal ownership from paint layers.
      if (!/^\s*(mask|wire)\b/i.test(String(layer.name || ''))) {
        for (let pixel = 0, offset = 3; pixel < pixelCount; pixel += 1, offset += 4) {
          const alpha = Math.round(data[offset] * opacity);
          if (!alpha) continue;
          aboveAlpha[pixel] = Math.min(255, alpha + Math.round(aboveAlpha[pixel] * (255 - alpha) / 255));
        }
      }
    } catch (error) {
      console.warn('[SHOKK DEMO] restriction layer skipped:', layer.name, error);
    }
  }
  return { union, ownerRgba };
}

function encodeMaskRuns(union, width, height) {
  const runs = [];
  let last = union[0] || 0;
  let count = 0;
  for (let pixel = 0; pixel < union.length; pixel += 1) {
    const value = union[pixel];
    if (value === last) count += 1;
    else {
      runs.push([last, count]);
      last = value;
      count = 1;
    }
  }
  if (count) runs.push([last, count]);
  return { width, height, runs };
}

// A Zone may be married to any set of PSD layers. The backend intentionally
// knows nothing about the editable browser layer model, so send it one compact
// union of the alpha silhouettes that are currently visible. Checked layers
// are OR'ed, hidden layers fail closed, and visible artwork above owns pixels.
export async function encodeSourceLayerUnion(layers, selectedIds, width, height) {
  const pixels = await buildSourceLayerScopePixels(layers, selectedIds, width, height, false);
  return pixels ? encodeMaskRuns(pixels.union, width, height) : null;
}

export async function encodeSourceLayerScope(layers, selectedIds, width, height, options = {}) {
  const ids = new Set((selectedIds || []).map(String));
  if (!ids.size) return { mask: null, rgbPng: '' };
  const includeRgb = options.includeRgb !== false;
  const pixels = await buildSourceLayerScopePixels(layers, selectedIds, width, height, includeRgb);
  const mask = encodeMaskRuns(pixels.union, width, height);
  if (options.includeRgb === false) return { mask, rgbPng: '' };
  const local = document.createElement('canvas');
  local.width = width;
  local.height = height;
  const ctx = local.getContext('2d');
  const imageData = ctx.createImageData(width, height);
  imageData.data.set(pixels.ownerRgba);
  ctx.putImageData(imageData, 0, 0);
  return { mask, rgbPng: local.toDataURL('image/png').split(',', 2)[1] || '' };
}

export async function composeLayers(layers, width, height) {
  const output = document.createElement('canvas');
  output.width = width;
  output.height = height;
  const ctx = output.getContext('2d');
  ctx.clearRect(0, 0, width, height);
  const ordered = layersInCompositeOrder(layers);
  for (const layer of ordered) {
    if (!layer.visible || !layer.rasterUrl) continue;
    try {
      const surface = await buildLayerSurface(layer, width, height);
      ctx.save();
      ctx.globalAlpha = Math.max(0, Math.min(1, Number(layer.opacity)));
      ctx.globalCompositeOperation = normalizeBlendMode(layer.blendMode);
      ctx.drawImage(surface, 0, 0);
      ctx.restore();
    } catch (error) {
      console.warn('[SHOKK DEMO] layer skipped:', layer.name, error);
    }
  }
  return output;
}

export function paintCanvasFrom(source, target, displayWidth, displayHeight) {
  if (!source || !target) return;
  const sourceWidth = Number(source.naturalWidth || source.width) || 1;
  const sourceHeight = Number(source.naturalHeight || source.height) || 1;
  const ratio = Math.min(displayWidth / sourceWidth, displayHeight / sourceHeight);
  const width = Math.max(1, Math.round(sourceWidth * ratio));
  const height = Math.max(1, Math.round(sourceHeight * ratio));
  target.width = width;
  target.height = height;
  target.style.width = `${width}px`;
  target.style.height = `${height}px`;
  const ctx = target.getContext('2d');
  ctx.clearRect(0, 0, width, height);
  ctx.drawImage(source, 0, 0, width, height);
}

export async function paintCanvasFromUrl(url, target, displayWidth, displayHeight) {
  if (!url) return false;
  const image = await loadImage(url);
  const ratio = Math.min(displayWidth / image.naturalWidth, displayHeight / image.naturalHeight);
  const width = Math.max(1, Math.round(image.naturalWidth * ratio));
  const height = Math.max(1, Math.round(image.naturalHeight * ratio));
  target.width = width;
  target.height = height;
  target.style.width = `${width}px`;
  target.style.height = `${height}px`;
  const ctx = target.getContext('2d');
  ctx.clearRect(0, 0, width, height);
  ctx.drawImage(image, 0, 0, width, height);
  return true;
}

export function canvasPoint(event, canvas, sourceWidth, sourceHeight) {
  const rect = canvas.getBoundingClientRect();
  const x = Math.max(0, Math.min(sourceWidth - 1, Math.floor((event.clientX - rect.left) / rect.width * sourceWidth)));
  const y = Math.max(0, Math.min(sourceHeight - 1, Math.floor((event.clientY - rect.top) / rect.height * sourceHeight)));
  return { x, y, clientX: event.clientX - rect.left, clientY: event.clientY - rect.top };
}

export function samplePixel(canvas, x, y) {
  const ctx = canvas.getContext('2d', { willReadFrequently: true });
  const pixel = ctx.getImageData(Math.max(0, Math.min(canvas.width - 1, x)), Math.max(0, Math.min(canvas.height - 1, y)), 1, 1).data;
  return { r: pixel[0], g: pixel[1], b: pixel[2], a: pixel[3], hex: rgbToHex(pixel[0], pixel[1], pixel[2]) };
}

export function hitTestLayers(layers, x, y) {
  for (const layer of layers) {
    if (!layer.visible || !layer._surface) continue;
    const ctx = layer._surface.getContext('2d', { willReadFrequently: true });
    const alpha = ctx.getImageData(Math.max(0, Math.min(layer._surface.width - 1, x)), Math.max(0, Math.min(layer._surface.height - 1, y)), 1, 1).data[3];
    if (alpha > 8) return layer;
  }
  return null;
}

export function rgbToHex(r, g, b) {
  return `#${[r, g, b].map((value) => Math.max(0, Math.min(255, Number(value) || 0)).toString(16).padStart(2, '0')).join('')}`.toUpperCase();
}

export function hexToRgb(hex) {
  const match = /^#?([0-9a-f]{6})$/i.exec(String(hex || ''));
  if (!match) return null;
  return {
    r: parseInt(match[1].slice(0, 2), 16),
    g: parseInt(match[1].slice(2, 4), 16),
    b: parseInt(match[1].slice(4, 6), 16),
  };
}

export function drawChannel(sourceCanvas, targetCanvas, channel, tint) {
  if (!sourceCanvas.width || !sourceCanvas.height) return;
  const mini = document.createElement('canvas');
  mini.width = sourceCanvas.width;
  mini.height = sourceCanvas.height;
  const mctx = mini.getContext('2d', { willReadFrequently: true });
  mctx.drawImage(sourceCanvas, 0, 0);
  const data = mctx.getImageData(0, 0, mini.width, mini.height);
  const ti = tint || [255, 255, 255];
  for (let i = 0; i < data.data.length; i += 4) {
    const value = data.data[i + channel];
    data.data[i] = value * ti[0] / 255;
    data.data[i + 1] = value * ti[1] / 255;
    data.data[i + 2] = value * ti[2] / 255;
    data.data[i + 3] = 255;
  }
  mctx.putImageData(data, 0, 0);
  const box = targetCanvas.parentElement.getBoundingClientRect();
  paintCanvasFrom(mini, targetCanvas, Math.max(40, box.width), Math.max(40, box.height));
}

export function makeSwatchCanvas(canvas, finish, seed = 1) {
  const width = 180;
  const height = 90;
  canvas.width = width;
  canvas.height = height;
  const ctx = canvas.getContext('2d');
  const base = finish.swatch || '#61708a';
  const grad = ctx.createLinearGradient(0, 0, width, height);
  grad.addColorStop(0, '#080a10');
  grad.addColorStop(.28, base);
  grad.addColorStop(.55, '#f6f9ff');
  grad.addColorStop(.7, base);
  grad.addColorStop(1, '#090c13');
  ctx.fillStyle = grad;
  ctx.fillRect(0, 0, width, height);
  let value = [...finish.id].reduce((sum, char) => sum + char.charCodeAt(0), seed);
  for (let i = 0; i < 70; i += 1) {
    value = (value * 1664525 + 1013904223) >>> 0;
    const x = value % width;
    value = (value * 1664525 + 1013904223) >>> 0;
    const y = value % height;
    const radius = 1 + (value % 5);
    ctx.fillStyle = `rgba(${value % 255},${(value >>> 8) % 255},${(value >>> 16) % 255},.34)`;
    ctx.beginPath();
    ctx.arc(x, y, radius, 0, Math.PI * 2);
    ctx.fill();
  }
}
