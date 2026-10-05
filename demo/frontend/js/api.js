const REQUEST_TIMEOUT_MS = 300_000;

function timeoutSignal(ms = REQUEST_TIMEOUT_MS) {
  if (typeof AbortSignal !== 'undefined' && typeof AbortSignal.timeout === 'function') {
    return AbortSignal.timeout(ms);
  }
  return undefined;
}

async function parseResponse(response, label) {
  const text = await response.text();
  let payload = {};
  if (text) {
    try { payload = JSON.parse(text); }
    catch (_) { throw new Error(`${label} returned an invalid response.`); }
  }
  if (!response.ok || payload.ok === false || payload.success === false) {
    throw new Error(payload.error || payload.message || `${label} failed (${response.status}).`);
  }
  return payload;
}

export async function getJSON(path, timeoutMs = 20_000) {
  const response = await fetch(path, { cache: 'no-store', signal: timeoutSignal(timeoutMs) });
  return parseResponse(response, path);
}

export async function postJSON(path, body, timeoutMs = REQUEST_TIMEOUT_MS) {
  const response = await fetch(path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
    signal: timeoutSignal(timeoutMs),
  });
  return parseResponse(response, path);
}

export async function postForm(path, form, timeoutMs = REQUEST_TIMEOUT_MS) {
  const response = await fetch(path, { method: 'POST', body: form, signal: timeoutSignal(timeoutMs) });
  return parseResponse(response, path);
}

export async function postImage(path, body, timeoutMs = REQUEST_TIMEOUT_MS) {
  const isForm = body instanceof FormData;
  const response = await fetch(path, {
    method: 'POST',
    headers: isForm ? undefined : { 'Content-Type': 'application/json' },
    body: isForm ? body : JSON.stringify(body),
    signal: timeoutSignal(timeoutMs),
  });
  const contentType = response.headers.get('content-type') || '';
  if (contentType.includes('application/json')) return parseResponse(response, path);
  if (!response.ok) throw new Error(`${path} failed (${response.status}).`);
  const blob = await response.blob();
  const dataUrl = await new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result);
    reader.onerror = () => reject(new Error('Could not decode the image response.'));
    reader.readAsDataURL(blob);
  });
  return { success: true, composite: dataUrl, image: dataUrl };
}

export function normalizeManifest(raw) {
  const manifest = raw.manifest || raw.demo || raw;
  const source = manifest.visible_finishes || manifest.finishes || raw.finishes || [];
  const normalizeFinish = (finish) => ({
    id: String(finish.id || finish.finish_id || ''),
    name: String(finish.name || finish.title || finish.id || ''),
    collection: String(finish.collection || finish.group || finish.category || 'Demo Collection'),
    category: String(finish.category || finish.type || 'Finish'),
    kind: String(finish.kind || finish.type || 'base'),
    description: String(finish.description || finish.desc || ''),
    swatch: String(finish.swatch || finish.color || '#61708a'),
    thumbnail: finish.thumbnail || finish.thumbnail_url || finish.preview_url || '',
  });
  const finishes = source.map(normalizeFinish).filter((finish) => finish.id);
  const colorSourceRaw = manifest.base_color_sources || manifest.baseColorSources || raw.base_color_sources || source;
  const baseColorSources = colorSourceRaw.map(normalizeFinish).filter((finish) => finish.id);
  return {
    product: (manifest.product && (manifest.product.id || manifest.product)) || raw.product || 'shokk-demo',
    version: manifest.version || (manifest.product && manifest.product.version) || raw.version || '1.0.0',
    finishes,
    baseColorSources,
    fractureFinishId: manifest.fracture_finish_id || manifest.fractureFinishId || 'fs_core_emerald',
    links: {
      payhip: (manifest.links && manifest.links.payhip) || 'https://payhip.com/b/AHgpV',
      discord: (manifest.links && manifest.links.discord) || 'https://discord.gg/GwXxyhwtDu',
      site: (manifest.links && manifest.links.site) || 'https://shokkergroup.com',
    },
  };
}

export function normalizePreview(raw) {
  const urls = raw.preview_urls || raw.urls || raw.previews || raw.result || {};
  const pick = (...keys) => {
    for (const key of keys) {
      const value = urls[key] ?? raw[key];
      if (typeof value === 'string' && value) return value;
    }
    return '';
  };
  return {
    paint: pick('paint', 'paint_url', 'paint_preview', 'preview', 'preview_url', 'live', 'RENDER_paint.png'),
    combined: pick('combined', 'combined_url', 'spec', 'spec_url', 'spec_preview', 'RENDER_spec.png'),
    metal: pick('metal', 'metallic', 'metal_url', 'metallic_url'),
    rough: pick('rough', 'roughness', 'rough_url', 'roughness_url'),
    clearcoat: pick('clearcoat', 'coat', 'clearcoat_url', 'coat_url'),
    jobId: raw.job_id || raw.jobId || '',
    outputPath: raw.output_path || raw.outputPath || (raw.output_dir && (raw.output_dir.path || raw.output_dir)) || '',
    downloadUrls: raw.download_urls || raw.downloads || {},
    elapsedMs: raw.elapsed_ms || raw.elapsedMs || (Number(raw.elapsed_seconds) * 1000) || 0,
    sourceToken: raw.paint_source_token || raw.source_token || '',
  };
}

export async function selectSourceFile() {
  if (window.shokkDemo && typeof window.shokkDemo.selectSourceFile === 'function') {
    const result = await window.shokkDemo.selectSourceFile();
    if (!result || result.canceled) return '';
    return typeof result === 'string' ? result : (result.filePath || result.path || '');
  }
  return '';
}

export async function selectIRacingFolder() {
  if (window.shokkDemo && typeof window.shokkDemo.selectIRacingFolder === 'function') {
    const result = await window.shokkDemo.selectIRacingFolder();
    if (!result || result.canceled) return '';
    return typeof result === 'string' ? result : (result.folderPath || result.filePath || result.path || '');
  }
  return '';
}

export async function openExternal(url) {
  if (window.shokkDemo && typeof window.shokkDemo.openExternal === 'function') {
    return window.shokkDemo.openExternal(url);
  }
  const opened = window.open(url, '_blank', 'noopener,noreferrer');
  if (!opened) throw new Error('Your browser blocked the link.');
  return true;
}

export async function revealPath(path) {
  if (window.shokkDemo && typeof window.shokkDemo.revealPath === 'function') {
    return window.shokkDemo.revealPath(path);
  }
  return false;
}
