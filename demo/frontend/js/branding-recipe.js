const PAYHIP_FALLBACK = 'https://payhip.com/b/AHgpV';
const DISCORD_FALLBACK = 'https://discord.gg/GwXxyhwtDu';

export const INTRO_CARD_HOLD_MS = 2800;
export const INTRO_CROSSFADE_MS = 800;
export const INTRO_SPRAY_MS = 820;
export const INTRO_READY_TIMEOUT_MS = 15000;
export const FIRST_LAUNCH_SPLASH_TIMEOUT_MS = 15000;
export const FIRST_LAUNCH_SPLASH_STALL_MS = 2200;
export const FIRST_LAUNCH_SPLASH_PLAY_TIMEOUT_MS = 1400;
export const FIRST_LAUNCH_SPLASH_STORAGE_KEY = 'spb_demo_splash_intro_seen_v1';
export const FIRST_LAUNCH_SPLASH_URL = '/assets/branding/spb-splash-intro.mp4';

export const BRAND_LOGOS = Object.freeze([
  Object.freeze({ src: '/assets/branding/shokk-handmark.png', alt: 'SHOKK hand mark' }),
  Object.freeze({ src: '/assets/branding/shokker-paint-booth.png', alt: 'Shokker Paint Booth' }),
  Object.freeze({ src: '/assets/branding/shokker-road.png', alt: 'Shokker Road' }),
]);

export function hasSeenFirstLaunchSplash(storage) {
  try {
    return storage?.getItem(FIRST_LAUNCH_SPLASH_STORAGE_KEY) === '1';
  } catch (_) {
    return false;
  }
}

export function markFirstLaunchSplashSeen(storage) {
  try {
    storage?.setItem(FIRST_LAUNCH_SPLASH_STORAGE_KEY, '1');
    return Boolean(storage);
  } catch (_) {
    return false;
  }
}

export function shuffledLogoOrder(items, random = Math.random) {
  const result = [...items];
  for (let index = result.length - 1; index > 0; index -= 1) {
    const swap = Math.floor(Math.max(0, Math.min(.999999999, random())) * (index + 1));
    [result[index], result[swap]] = [result[swap], result[index]];
  }
  return result;
}

function secureRandom() {
  try {
    const values = new Uint32Array(1);
    crypto.getRandomValues(values);
    return values[0] / 0x100000000;
  } catch (_) { return Math.random(); }
}

function escapeHtml(value) {
  return String(value ?? '').replace(/[&<>"']/g, (character) => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;',
  })[character]);
}

function safeLocalUrl(value) {
  try {
    const url = new URL(String(value || ''), window.location.href);
    return url.origin === window.location.origin ? `${url.pathname}${url.search}` : '';
  } catch (_) { return ''; }
}

function safeExternalUrl(value, fallback) {
  try {
    const url = new URL(String(value || fallback));
    const allowed = url.protocol === 'https:' && (
      url.hostname === 'payhip.com' || url.hostname.endsWith('.payhip.com') ||
      url.hostname === 'discord.gg' || url.hostname === 'discord.com' || url.hostname.endsWith('.discord.com')
    );
    return allowed ? url.href : fallback;
  } catch (_) { return fallback; }
}

function filename(path) {
  return String(path || '').split(/[\\/]/).pop() || '';
}

function strengthPills(zone) {
  const strengths = zone.strengths || {};
  const adjustments = zone.adjustments || {};
  const channels = adjustments.spec_channels || {};
  return [
    `Zone ${strengths.zone ?? 100}%`,
    `Base ${strengths.base ?? 100}%`,
    `Spec ${strengths.spec ?? 100}%`,
    `Color ${(zone.base_color || {}).strength ?? 100}%`,
    `Base ${adjustments.base_scale ?? 1}x / ${adjustments.base_rotation ?? 0}°`,
    `HSB ${adjustments.hue ?? 0} / ${adjustments.saturation ?? 0} / ${adjustments.brightness ?? 0}`,
    `Color ${adjustments.color_scale ?? 1}x / ${adjustments.color_rotation ?? 0}°`,
    adjustments.color_lab_enabled === true
      ? `Color Lab ON · Depth ${adjustments.color_depth ?? 65}% · Flip ${adjustments.color_flip ?? 0}° · Glow ${adjustments.underglow ?? 0}%`
      : 'Color Lab OFF · Selected colors preserved',
    `Spec ${adjustments.spec_scale ?? 1}x / ${adjustments.spec_rotation ?? 0}°`,
    `Spec blend ${adjustments.spec_blend || 'normal'}`,
    `M ${channels.metal ?? 0} · R ${channels.rough ?? 0} · C ${channels.coat ?? 0}`,
  ];
}

function coverageSummary(coverage) {
  const mode = String(coverage?.mode || 'everything').toLowerCase();
  const colors = Array.isArray(coverage?.colors) ? coverage.colors : [];
  if (mode === 'remaining') return 'Remaining — pixels not claimed by Zones above';
  if (mode === 'colors') return colors.length
    ? `${colors.length} selected color${colors.length === 1 ? '' : 's'}`
    : 'Selected colors';
  return 'Everything inside this Zone scope';
}

function colorDetails(coverage) {
  const colors = Array.isArray(coverage?.colors) ? coverage.colors : [];
  const exclusions = Array.isArray(coverage?.exclusions) ? coverage.exclusions : [];
  const parts = colors.map((item) => `${item.color || 'color'} ±${item.tolerance ?? 40}`);
  if (exclusions.length) parts.push(`Excluded: ${exclusions.map((item) => item.color).join(', ')}`);
  return parts.join(' · ');
}

function layerNameMap() {
  const result = new Map();
  document.querySelectorAll('#layerList .layer-card').forEach((card) => {
    const id = String(card.dataset.layerId || '');
    const name = card.querySelector('strong')?.textContent?.trim() || id;
    if (id) result.set(id, name);
  });
  return result;
}

function layerSummary(scope, names) {
  if (!scope?.restricted) return 'All PSD layers';
  const ids = Array.isArray(scope.ids) ? scope.ids : [];
  const labels = ids.map((id) => names.get(String(id)) || String(id)).filter(Boolean);
  if (labels.length) return labels.join(', ');
  const count = Number(scope.count) || 0;
  return count ? `${count} selected PSD layer${count === 1 ? '' : 's'}` : 'Restricted layer scope';
}

function baseColorSummary(baseColor) {
  const mode = String(baseColor?.mode || 'finish');
  const labels = {
    finish: "Finish's own color",
    source: 'Source paint (spec only)',
    solid: 'Solid color',
    special: 'From special',
    gradient: 'Custom gradient',
  };
  let detail = labels[mode] || mode;
  if (mode === 'solid' && baseColor.color) detail += ` — ${baseColor.color}`;
  if (mode === 'special' && baseColor.source?.name) detail += ` — ${baseColor.source.name}`;
  if (mode === 'gradient') {
    const stops = Array.isArray(baseColor.stops) ? baseColor.stops : [];
    detail += ` — ${stops.map((stop) => stop.color).join(' → ')} · ${baseColor.direction || 'horizontal'}`;
  }
  if (baseColor?.locked) detail += ' · LOCKED';
  return detail;
}

export function recipeText(recipe) {
  const render = recipe?.render || {};
  const source = render.source || {};
  const output = render.output || {};
  const number = render.number || {};
  const lines = [
    'SHOKKER PAINT BOOTH — SHOKK DEMO RENDER RECIPE',
    `Source: ${source.path || source.name || 'Unknown source'}`,
    `Output: ${output.path || 'Render downloads'}`,
    `Number: ${number.mode || 'custom'} · ${number.value || ''} · iRacing ${number.iracing_id || ''}`,
  ];
  (recipe?.zones || []).forEach((zone) => {
    lines.push(`${zone.order}. ${zone.name} — ${zone.material?.name || zone.material?.id || 'Material'}`);
    lines.push(`   Coverage: ${coverageSummary(zone.coverage)}`);
    lines.push(`   Base Color: ${baseColorSummary(zone.base_color)}`);
    lines.push(`   Strengths: ${strengthPills(zone).join(' | ')}`);
  });
  if (recipe?.links?.payhip) lines.push(`Full version: ${recipe.links.payhip}`);
  if (recipe?.links?.discord) lines.push(`Discord: ${recipe.links.discord}`);
  return lines.join('\n');
}

function previewUrl(recipe, kind) {
  const entries = Object.entries(recipe?.previews || {});
  const found = entries.find(([name]) => kind === 'paint' ? /paint/i.test(name) : /spec/i.test(name));
  return safeLocalUrl(found?.[1] || '');
}

function buildZoneHtml(zone, names) {
  const coverage = zone.coverage || {};
  const colors = colorDetails(coverage);
  return `<article class="demo-recipe-zone">
    <header><b>${escapeHtml(zone.order)}.</b><strong>${escapeHtml(zone.name)}</strong><span>${escapeHtml(zone.material?.category || '')}</span></header>
    <div class="demo-recipe-zone-grid">
      <section><small>BASE MATERIAL / SPEC</small><strong>${escapeHtml(zone.material?.name || zone.material?.id || 'Material')}</strong><span>${escapeHtml(zone.material?.kind || '')}</span></section>
      <section><small>BASE COLOR</small><strong>${escapeHtml(baseColorSummary(zone.base_color))}</strong></section>
      <section><small>PIXEL COVERAGE</small><strong>${escapeHtml(coverageSummary(coverage))}</strong>${colors ? `<span>${escapeHtml(colors)}</span>` : ''}</section>
      <section><small>LAYER SCOPE</small><strong>${escapeHtml(layerSummary(coverage.layer_scope, names))}</strong></section>
    </div>
    <div class="demo-recipe-pills">${strengthPills(zone).map((label) => `<span>${escapeHtml(label)}</span>`).join('')}</div>
  </article>`;
}

function createRecipeDialog() {
  const dialog = document.createElement('dialog');
  dialog.id = 'demoBrandedRecipe';
  dialog.className = 'demo-branded-recipe';
  dialog.setAttribute('aria-labelledby', 'demoRecipeTitle');
  document.body.append(dialog);
  dialog.addEventListener('click', (event) => {
    if (event.target === dialog) dialog.close();
  });
  dialog.addEventListener('cancel', () => dialog.close());
  return dialog;
}

async function openExternal(url) {
  if (window.shokkDemo && typeof window.shokkDemo.openExternal === 'function') {
    await window.shokkDemo.openExternal(url);
    return;
  }
  window.open(url, '_blank', 'noopener,noreferrer');
}

function showRecipe(recipe) {
  const dialog = document.getElementById('demoBrandedRecipe') || createRecipeDialog();
  const names = layerNameMap();
  const render = recipe.render || {};
  const source = render.source || {};
  const output = render.output || {};
  const number = render.number || {};
  const logo = safeLocalUrl(recipe.branding?.logo) || BRAND_LOGOS[1].src;
  const paint = previewUrl(recipe, 'paint');
  const spec = previewUrl(recipe, 'spec');
  const payhip = safeExternalUrl(recipe.links?.payhip || recipe.links?.full_version, PAYHIP_FALLBACK);
  const discord = safeExternalUrl(recipe.links?.discord, DISCORD_FALLBACK);
  const downloads = Object.entries(recipe.downloads || {}).map(([label, url]) => {
    const safe = safeLocalUrl(url);
    return safe ? `<a href="${escapeHtml(safe)}" download>${escapeHtml(label.replaceAll('_', ' '))}</a>` : '';
  }).join('');
  const previewHtml = paint && spec ? `<section class="demo-recipe-previews">
    <figure><figcaption>PAINT OUTPUT</figcaption><img src="${escapeHtml(paint)}" alt="Rendered paint output"></figure>
    <figure><figcaption>COMBINED SPEC</figcaption><img src="${escapeHtml(spec)}" alt="Rendered combined material map"></figure>
  </section>` : '';
  dialog.innerHTML = `<div class="demo-recipe-shell">
    <header class="demo-recipe-header">
      <img src="${escapeHtml(logo)}" alt="Shokker Paint Booth">
      <div><span>SHOKK DEMO</span><h2 id="demoRecipeTitle">RENDER RECIPE</h2><p>${escapeHtml(recipe.product?.credit || 'Made with Shokker Paint Booth')}</p></div>
      <button type="button" data-recipe-close aria-label="Close render recipe">×</button>
    </header>
    <section class="demo-recipe-status ${output.verified ? 'verified' : ''}">
      <strong>${output.verified ? '✓ SAVED AND VERIFIED' : '✓ RENDER COMPLETE'}</strong>
      <span>${escapeHtml(output.path || 'Use the downloads below to save this render.')}</span>
    </section>
    <section class="demo-recipe-meta">
      <div><small>SOURCE</small><strong title="${escapeHtml(source.path || '')}">${escapeHtml(source.name || filename(source.path) || 'Source paint')}</strong></div>
      <div><small>OUTPUT</small><strong title="${escapeHtml(output.path || '')}">${escapeHtml(output.path || 'Render downloads')}</strong></div>
      <div><small>NUMBER</small><strong>${escapeHtml(number.mode === 'sim-stamped' ? 'SIM-STAMPED' : `CUSTOM #${number.value || ''}`)}</strong><span>iRacing ID ${escapeHtml(number.iracing_id || '')}</span></div>
      <div><small>RENDER</small><strong>${escapeHtml(render.elapsed_seconds ?? 0)}s</strong><span>${escapeHtml(render.job_id || '')}</span></div>
    </section>
    ${previewHtml}
    <section class="demo-recipe-zones" aria-label="Ordered render Zones">${(recipe.zones || []).map((zone) => buildZoneHtml(zone, names)).join('')}</section>
    <footer class="demo-recipe-footer">
      <div><strong>Ready for the whole booth?</strong><span>Unlock the complete finish library, patterns, overlays and Pro tools—or bring your render to the Discord.</span></div>
      <div class="demo-recipe-actions">${downloads}<button type="button" data-recipe-copy>COPY RECIPE</button><button class="gold" type="button" data-recipe-external="${escapeHtml(payhip)}">GET THE FULL VERSION</button><button type="button" data-recipe-external="${escapeHtml(discord)}">JOIN DISCORD</button><button type="button" data-recipe-close>CLOSE</button></div>
    </footer>
  </div>`;
  dialog.querySelectorAll('[data-recipe-close]').forEach((button) => button.addEventListener('click', () => dialog.close()));
  dialog.querySelectorAll('[data-recipe-external]').forEach((button) => button.addEventListener('click', () => openExternal(button.dataset.recipeExternal).catch(() => {})));
  dialog.querySelector('[data-recipe-copy]')?.addEventListener('click', async (event) => {
    try {
      await navigator.clipboard.writeText(recipeText(recipe));
      event.currentTarget.textContent = 'COPIED ✓';
      setTimeout(() => { event.currentTarget.textContent = 'COPY RECIPE'; }, 1500);
    } catch (_) { event.currentTarget.textContent = 'COPY FAILED'; }
  });
  if (dialog.open) dialog.close();
  if (typeof dialog.showModal === 'function') dialog.showModal();
  else dialog.setAttribute('open', '');
}

let pendingRecipe = null;

function handoffPendingRecipe() {
  if (!pendingRecipe) return;
  const stockDialog = document.getElementById('renderDialog');
  if (!stockDialog?.open) return;
  if (stockDialog?.open) stockDialog.close();
  const recipe = pendingRecipe;
  pendingRecipe = null;
  showRecipe(recipe);
}

function queueRecipe(recipe) {
  if (!recipe || recipe.schema !== 'spb-demo-render-recipe/1') return;
  pendingRecipe = recipe;
  // The main UI still owns paint/spec decoding and decides when a successful
  // render is ready to present.  Wait for its stock success dialog instead of
  // racing it with a second modal; large 2048² maps can take several seconds.
  handoffPendingRecipe();
}

function watchStockRenderDialog() {
  const stockDialog = document.getElementById('renderDialog');
  if (!stockDialog || stockDialog.dataset.recipeWatcher === 'true') return;
  stockDialog.dataset.recipeWatcher = 'true';
  const observer = new MutationObserver(() => handoffPendingRecipe());
  observer.observe(stockDialog, { attributes: true, attributeFilter: ['open'] });
}

function installRenderCapture() {
  if (window.__shokkDemoRecipeFetchInstalled) return;
  window.__shokkDemoRecipeFetchInstalled = true;
  const originalFetch = window.fetch.bind(window);
  window.fetch = async (...args) => {
    const response = await originalFetch(...args);
    try {
      const input = args[0];
      const init = args[1] || {};
      const requestUrl = new URL(typeof input === 'string' ? input : input.url, window.location.href);
      const method = String(init.method || (typeof input !== 'string' && input.method) || 'GET').toUpperCase();
      if (method === 'POST' && requestUrl.pathname === '/render' && response.ok) {
        response.clone().json().then((payload) => {
          if (payload?.success && payload.recipe) queueRecipe(payload.recipe);
        }).catch(() => {});
      }
    } catch (_) { /* The app receives the original response unchanged. */ }
    return response;
  };
}

function preloadLogo(image, src) {
  image.src = src;
  if (typeof image.decode !== 'function') return Promise.resolve();
  return Promise.race([
    image.decode().catch(() => {}),
    new Promise((resolve) => setTimeout(resolve, 500)),
  ]);
}

function waitFor(milliseconds, signal) {
  return new Promise((resolve) => {
    if (signal?.aborted) {
      resolve(false);
      return;
    }
    let timer = 0;
    const finish = (completed) => {
      if (timer) clearTimeout(timer);
      signal?.removeEventListener('abort', cancel);
      resolve(completed);
    };
    const cancel = () => finish(false);
    timer = setTimeout(() => finish(true), milliseconds);
    signal?.addEventListener('abort', cancel, { once: true });
  });
}

function browserLocalStorage() {
  try {
    return window.localStorage;
  } catch (_) {
    return null;
  }
}

function attemptVideoPlayback(video) {
  let timer = 0;
  let playRequest;
  try {
    playRequest = video.play();
  } catch (_) {
    return Promise.resolve(false);
  }
  return Promise.race([
    Promise.resolve(playRequest).then(() => true, () => false),
    new Promise((resolve) => {
      timer = setTimeout(() => resolve(false), FIRST_LAUNCH_SPLASH_PLAY_TIMEOUT_MS);
    }),
  ]).finally(() => clearTimeout(timer));
}

export async function runFirstLaunchSplash(options = {}) {
  const storage = options.storage === undefined ? browserLocalStorage() : options.storage;
  const reducedMotion = options.reducedMotion === undefined
    ? Boolean(window.matchMedia?.('(prefers-reduced-motion: reduce)').matches)
    : Boolean(options.reducedMotion);
  if (hasSeenFirstLaunchSplash(storage)) return 'already-seen';
  if (reducedMotion) {
    markFirstLaunchSplashSeen(storage);
    return 'reduced-motion';
  }

  const overlay = document.createElement('section');
  overlay.className = 'demo-splash-intro';
  overlay.setAttribute('role', 'dialog');
  overlay.setAttribute('aria-modal', 'true');
  overlay.setAttribute('aria-labelledby', 'demoSplashTitle');
  overlay.setAttribute('aria-describedby', 'demoSplashHint demoSplashStatus');
  overlay.tabIndex = -1;
  overlay.innerHTML = `
    <div class="demo-splash-video-frame">
      <video class="demo-splash-video" src="${FIRST_LAUNCH_SPLASH_URL}" preload="auto" playsinline aria-label="Shokker Paint Booth splash intro"></video>
      <div class="demo-splash-video-shade" aria-hidden="true"></div>
    </div>
    <header class="demo-splash-heading">
      <span>FIRST IGNITION</span>
      <h1 id="demoSplashTitle">SHOKKER PAINT BOOTH</h1>
    </header>
    <div class="demo-splash-controls">
      <button class="demo-splash-sound" type="button" aria-pressed="false">SOUND: AUTO</button>
      <button class="demo-splash-skip" type="button" autofocus>SKIP INTRO <small>ENTER OR ESC</small></button>
    </div>
    <p id="demoSplashHint" class="demo-brand-sr-only">This short intro plays once. Press Enter or Escape to skip it.</p>
    <p id="demoSplashStatus" class="demo-splash-status" role="status" aria-live="polite">STARTING INTRO…</p>`;

  const video = overlay.querySelector('.demo-splash-video');
  const soundButton = overlay.querySelector('.demo-splash-sound');
  const skipButton = overlay.querySelector('.demo-splash-skip');
  const status = overlay.querySelector('.demo-splash-status');
  video.autoplay = true;
  video.volume = .75;
  video.disablePictureInPicture = true;
  document.body.append(overlay);

  return new Promise((resolve) => {
    let settled = false;
    let stallTimer = 0;
    let exitTimer = 0;
    const timeoutTimer = setTimeout(
      () => complete('timeout', false),
      FIRST_LAUNCH_SPLASH_TIMEOUT_MS,
    );

    const updateSoundButton = () => {
      const soundOn = !video.muted;
      soundButton.textContent = soundOn ? 'SOUND: ON' : 'TURN SOUND ON';
      soundButton.setAttribute('aria-pressed', String(soundOn));
      status.textContent = soundOn ? 'INTRO PLAYING WITH SOUND' : 'INTRO PLAYING — SOUND AVAILABLE';
    };
    const clearStallTimer = () => {
      if (stallTimer) clearTimeout(stallTimer);
      stallTimer = 0;
    };
    const cleanup = () => {
      clearTimeout(timeoutTimer);
      clearStallTimer();
      document.removeEventListener('keydown', onKeydown, true);
      document.removeEventListener('focusin', keepFocusInSplash, true);
      video.removeEventListener('ended', onEnded);
      video.removeEventListener('error', onError);
      video.removeEventListener('stalled', onStalled);
      video.removeEventListener('playing', clearStallTimer);
      video.removeEventListener('timeupdate', clearStallTimer);
      skipButton.removeEventListener('click', onSkip);
      soundButton.removeEventListener('click', onSoundToggle);
    };
    function complete(reason, remember) {
      if (settled) return;
      settled = true;
      if (remember) markFirstLaunchSplashSeen(storage);
      cleanup();
      video.pause();
      overlay.classList.add('leaving');
      exitTimer = setTimeout(() => {
        overlay.remove();
        resolve(reason);
      }, 180);
    }
    const onEnded = () => complete('ended', true);
    const onError = () => complete('error', false);
    const onStalled = () => {
      clearStallTimer();
      stallTimer = setTimeout(() => complete('stalled', false), FIRST_LAUNCH_SPLASH_STALL_MS);
    };
    const onSkip = () => complete('skipped', true);
    const onSoundToggle = async () => {
      if (settled) return;
      if (!video.muted) {
        video.muted = true;
        updateSoundButton();
        return;
      }
      video.muted = false;
      if (!await attemptVideoPlayback(video)) video.muted = true;
      if (settled) {
        video.pause();
        return;
      }
      updateSoundButton();
    };
    const onKeydown = (event) => {
      if ((event.key === 'Enter' || event.key === 'Escape') && !event.repeat && !event.isComposing) {
        event.preventDefault();
        event.stopImmediatePropagation();
        complete('skipped', true);
        return;
      }
      if (event.key === 'Tab') {
        event.preventDefault();
        event.stopImmediatePropagation();
        const controls = [soundButton, skipButton];
        const current = Math.max(0, controls.indexOf(document.activeElement));
        const delta = event.shiftKey ? -1 : 1;
        controls[(current + delta + controls.length) % controls.length].focus({ preventScroll: true });
      }
    };
    const keepFocusInSplash = (event) => {
      if (!overlay.contains(event.target)) skipButton.focus({ preventScroll: true });
    };

    video.addEventListener('ended', onEnded, { once: true });
    video.addEventListener('error', onError, { once: true });
    video.addEventListener('stalled', onStalled);
    video.addEventListener('playing', clearStallTimer);
    video.addEventListener('timeupdate', clearStallTimer);
    skipButton.addEventListener('click', onSkip, { once: true });
    soundButton.addEventListener('click', onSoundToggle);
    document.addEventListener('keydown', onKeydown, true);
    document.addEventListener('focusin', keepFocusInSplash, true);
    requestAnimationFrame(() => skipButton.focus({ preventScroll: true }));

    (async () => {
      video.muted = false;
      if (await attemptVideoPlayback(video)) {
        if (!settled) updateSoundButton();
        return;
      }
      if (settled) return;
      video.muted = true;
      if (await attemptVideoPlayback(video)) {
        if (!settled) updateSoundButton();
        return;
      }
      if (settled) return;
      complete('autoplay-blocked', false);
    })().catch(() => complete('playback-error', false));
  });
}

async function rotateBrandCards(frame, image, progress, order, signal) {
  let index = 0;
  let firstCard = true;
  while (!signal.aborted) {
    if (!firstCard) {
      frame.classList.remove('showing');
      if (!await waitFor(INTRO_CROSSFADE_MS, signal)) return;
    }
    const logo = order[index];
    await preloadLogo(image, logo.src);
    if (signal.aborted) return;
    image.alt = '';
    progress.forEach((dot, dotIndex) => dot.classList.toggle('active', dotIndex === index));
    requestAnimationFrame(() => {
      if (!signal.aborted) frame.classList.add('showing');
    });
    if (!await waitFor(INTRO_CARD_HOLD_MS, signal)) return;
    firstCard = false;
    index = (index + 1) % order.length;
  }
}

function makeSprayParticles(width, height, count = 420) {
  const palette = ['#ffb000', '#ffd95a', '#f4f7ff', '#25d9ff', '#ff6b24'];
  return Array.from({ length: count }, (_, index) => {
    const x = Math.random() * width;
    const y = Math.random() * height;
    return {
      x,
      y,
      radius: 1 + Math.random() * (index % 17 === 0 ? 11 : 4.5),
      birth: Math.max(0, Math.min(.94, (x / Math.max(1, width)) * .68 + Math.random() * .26)),
      color: palette[index % palette.length],
      alpha: .24 + Math.random() * .64,
    };
  });
}

function runSprayReveal(canvas, reducedMotion) {
  if (reducedMotion) return Promise.resolve();
  const context = canvas.getContext?.('2d');
  if (!context) return new Promise((resolve) => setTimeout(resolve, INTRO_SPRAY_MS));
  const bounds = canvas.getBoundingClientRect();
  const width = Math.max(1, Math.round(bounds.width || window.innerWidth));
  const height = Math.max(1, Math.round(bounds.height || window.innerHeight));
  const pixelRatio = Math.min(2, window.devicePixelRatio || 1);
  canvas.width = Math.round(width * pixelRatio);
  canvas.height = Math.round(height * pixelRatio);
  context.setTransform(pixelRatio, 0, 0, pixelRatio, 0, 0);
  const particles = makeSprayParticles(width, height);
  const started = performance.now();

  return new Promise((resolve) => {
    const draw = (now) => {
      const progress = Math.min(1, (now - started) / INTRO_SPRAY_MS);
      context.clearRect(0, 0, width, height);
      context.fillStyle = `rgba(3, 7, 14, ${Math.min(.92, progress * 1.45)})`;
      context.fillRect(0, 0, width, height);

      const sweepX = width * (-.12 + progress * 1.24);
      const mist = context.createRadialGradient(sweepX, height * .52, 0, sweepX, height * .52, height * .72);
      mist.addColorStop(0, `rgba(255, 183, 25, ${.62 * (1 - progress * .25)})`);
      mist.addColorStop(.34, `rgba(255, 92, 21, ${.34 * (1 - progress * .2)})`);
      mist.addColorStop(.7, `rgba(28, 210, 255, ${.2 * (1 - progress * .2)})`);
      mist.addColorStop(1, 'rgba(0, 0, 0, 0)');
      context.fillStyle = mist;
      context.fillRect(0, 0, width, height);

      for (const particle of particles) {
        if (particle.birth > progress) continue;
        const age = Math.min(1, (progress - particle.birth) * 7);
        context.globalAlpha = particle.alpha * age;
        context.fillStyle = particle.color;
        context.beginPath();
        context.arc(particle.x, particle.y, particle.radius * (.55 + age * .45), 0, Math.PI * 2);
        context.fill();
      }
      context.globalAlpha = 1;
      if (progress < 1) requestAnimationFrame(draw);
      else resolve();
    };
    requestAnimationFrame(draw);
  });
}

function waitForAppReady(app, timeout = INTRO_READY_TIMEOUT_MS) {
  if (!app || app.getAttribute('aria-busy') === 'false') return Promise.resolve(true);
  return new Promise((resolve) => {
    let settled = false;
    const finish = (ready) => {
      if (settled) return;
      settled = true;
      observer.disconnect();
      clearTimeout(timer);
      resolve(ready);
    };
    const observer = new MutationObserver(() => {
      if (app.getAttribute('aria-busy') === 'false') finish(true);
    });
    observer.observe(app, { attributes: true, attributeFilter: ['aria-busy'] });
    const timer = setTimeout(() => finish(false), timeout);
  });
}

async function runBrandIntro() {
  const reducedMotion = window.matchMedia?.('(prefers-reduced-motion: reduce)').matches;
  const order = shuffledLogoOrder(BRAND_LOGOS, secureRandom);
  const overlay = document.createElement('section');
  overlay.className = `demo-brand-intro${reducedMotion ? ' reduced-motion' : ''}`;
  overlay.setAttribute('role', 'dialog');
  overlay.setAttribute('aria-modal', 'true');
  overlay.setAttribute('aria-labelledby', 'demoBrandTitle');
  overlay.setAttribute('aria-describedby', 'demoBrandDescription demoBrandArtwork');
  overlay.tabIndex = -1;
  const staticCards = order.map((logo) => `<img src="${escapeHtml(logo.src)}" alt="">`).join('');
  overlay.innerHTML = `
    <div class="demo-brand-ambient" aria-hidden="true"></div>
    <div class="demo-brand-stage">
      <p class="demo-brand-eyebrow">THE FREE SHOKK EXPERIENCE</p>
      <div class="demo-brand-showcase" aria-hidden="true">
        <div class="demo-brand-frame"><img alt=""><span>SHOKK DEMO</span></div>
        <div class="demo-brand-static-strip">${staticCards}</div>
      </div>
      <div class="demo-brand-progress" aria-hidden="true"><i></i><i></i><i></i></div>
      <h1 id="demoBrandTitle">SHOKKER PAINT BOOTH</h1>
      <p id="demoBrandDescription" class="demo-brand-tagline">29 hand-picked finishes. Five paint Zones. One loaded race car ready to transform.</p>
      <p id="demoBrandArtwork" class="demo-brand-sr-only">Featuring SHOKK hand mark, Shokker Paint Booth and Shokker Road artwork.</p>
      <button class="demo-brand-enter" type="button" autofocus><span>ENTER SHOKKER PAINT BOOTH</span><small>CLICK OR PRESS ENTER</small></button>
    </div>
    <canvas class="demo-spray-canvas" aria-hidden="true"></canvas>`;
  document.body.append(overlay);
  const app = document.querySelector('#app');
  const appWasInert = app?.hasAttribute('inert') || false;
  const previousAriaHidden = app?.getAttribute('aria-hidden');
  app?.setAttribute('inert', '');
  app?.setAttribute('aria-hidden', 'true');

  const controller = new AbortController();
  const enterButton = overlay.querySelector('.demo-brand-enter');
  const image = overlay.querySelector('img');
  const frame = overlay.querySelector('.demo-brand-frame');
  const progress = [...overlay.querySelectorAll('.demo-brand-progress i')];
  if (!reducedMotion) {
    rotateBrandCards(frame, image, progress, order, controller.signal).catch(() => {
      if (overlay.isConnected) frame.classList.add('showing');
    });
  }

  let admit;
  let isAdmitting = false;
  const admission = new Promise((resolve) => { admit = resolve; });
  const onKeydown = (event) => {
    if (event.key === 'Enter' && !event.repeat && !event.isComposing) {
      event.preventDefault();
      event.stopImmediatePropagation();
      if (!isAdmitting) admit();
      return;
    }
    if (event.key === 'Tab') {
      event.preventDefault();
      event.stopImmediatePropagation();
      (isAdmitting ? overlay : enterButton).focus({ preventScroll: true });
      return;
    }
    if (event.key === 'Escape') {
      event.preventDefault();
      event.stopImmediatePropagation();
    }
  };
  const keepFocusInGate = (event) => {
    if (!overlay.contains(event.target)) (isAdmitting ? overlay : enterButton).focus({ preventScroll: true });
  };
  document.addEventListener('keydown', onKeydown, true);
  document.addEventListener('focusin', keepFocusInGate, true);
  enterButton.addEventListener('click', admit, { once: true });
  requestAnimationFrame(() => enterButton.focus({ preventScroll: true }));

  await admission;
  isAdmitting = true;
  enterButton.disabled = true;
  enterButton.querySelector('span').textContent = 'PREPARING YOUR STARTER PAINT';
  enterButton.querySelector('small').textContent = 'JUST A MOMENT';
  overlay.focus({ preventScroll: true });
  await waitForAppReady(app);
  controller.abort();
  enterButton.querySelector('small').textContent = reducedMotion ? 'OPENING' : 'SPRAYING IN';
  overlay.classList.add('admitting');
  try {
    await runSprayReveal(overlay.querySelector('.demo-spray-canvas'), reducedMotion);
  } finally {
    overlay.classList.add('revealing');
    if (!reducedMotion) await new Promise((resolve) => setTimeout(resolve, 220));
    document.removeEventListener('keydown', onKeydown, true);
    document.removeEventListener('focusin', keepFocusInGate, true);
    overlay.remove();
    if (app) {
      if (!appWasInert) app.removeAttribute('inert');
      if (previousAriaHidden === null) app.removeAttribute('aria-hidden');
      else app.setAttribute('aria-hidden', previousAriaHidden);
    }
    document.querySelector('#pickTool')?.focus({ preventScroll: true });
  }
}

function lockAppForStartupExperience() {
  const app = document.querySelector('#app');
  const appWasInert = app?.hasAttribute('inert') || false;
  const previousAriaHidden = app?.getAttribute('aria-hidden');
  document.body.classList.add('demo-startup-pending');
  app?.setAttribute('inert', '');
  app?.setAttribute('aria-hidden', 'true');
  return () => {
    document.body.classList.remove('demo-startup-pending');
    if (!app) return;
    if (!appWasInert) app.removeAttribute('inert');
    if (previousAriaHidden === null) app.removeAttribute('aria-hidden');
    else app.setAttribute('aria-hidden', previousAriaHidden);
  };
}

async function runStartupExperience() {
  const releaseApp = lockAppForStartupExperience();
  try {
    try {
      await runFirstLaunchSplash();
    } catch (_) {
      // A corrupt or unsupported video must never block the card entry gate.
    }
    await runBrandIntro();
  } finally {
    releaseApp();
  }
}

function install() {
  installRenderCapture();
  watchStockRenderDialog();
  // This module sits immediately after the complete app DOM. Start the gate in
  // the same task so neither the booth nor the later card gate can flash first.
  runStartupExperience().catch(() => {
    document.body.classList.remove('demo-startup-pending');
  });
}

if (typeof window !== 'undefined' && typeof document !== 'undefined') install();
