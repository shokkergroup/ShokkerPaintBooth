/**
 * Shokker Paint Booth — License Device-Activation Service (Cloudflare Worker + KV)
 * ------------------------------------------------------------------------------
 * Binds each Payhip license key to a CAPPED number of distinct machine
 * fingerprints, so a key can't be shared with a pile of friends.
 *
 * Policy (owner-set 2026-06-17): cap = 2 devices, HARD BLOCK over the cap,
 * with self-service deactivate + owner reset.
 *
 * Endpoints
 *   POST /activate     {key, fingerprint, label?}  -> register/allow a device
 *   POST /heartbeat    {key, fingerprint}          -> keep a device alive, re-validate
 *   POST /deactivate   {key, fingerprint}          -> free a slot (self-service)
 *   GET  /admin/key?key=...                         -> view a key's devices   (Bearer ADMIN_SECRET)
 *   POST /admin/reset  {key, action?}               -> clear/disable/unlimited (Bearer ADMIN_SECRET)
 *   GET  /health
 *
 * Bindings (wrangler.toml / secrets):
 *   LICENSES        KV namespace
 *   PAYHIP_SECRET   Payhip product API secret (server-side verify; replaces the client-bundled one)
 *   TOKEN_SECRET    HMAC secret for the offline activation token
 *   ADMIN_SECRET    Bearer token for /admin
 *   OWNER_KEYS      (optional) comma-separated keys treated as UNLIMITED (your test keys)
 *   DEVICE_CAP      (optional) integer override, default 2
 */

const DEFAULT_CAP = 2;
const DEVICE_IDLE_EXPIRY_DAYS = 60;     // a device idle this long frees its slot
const TOKEN_DAYS = 30;                  // offline grace before an online re-check is required
const PAYHIP_VERIFY_URL = 'https://payhip.com/api/v2/license/verify';

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    const path = url.pathname.replace(/\/+$/, '') || '/';
    try {
      if (request.method === 'POST' && path === '/activate')   return await activate(request, env);
      if (request.method === 'POST' && path === '/heartbeat')  return await heartbeat(request, env);
      if (request.method === 'POST' && path === '/deactivate') return await deactivate(request, env);
      if (request.method === 'GET'  && path === '/admin/key')  return await adminKey(request, env, url);
      if (request.method === 'POST' && path === '/admin/reset')return await adminReset(request, env);
      if (path === '/health') return json({ ok: true });
      return json({ ok: false, error: 'not_found' }, 404);
    } catch (e) {
      return json({ ok: false, error: 'server_error', detail: String((e && e.message) || e) }, 500);
    }
  },
};

/* ---------- helpers ---------- */

function json(obj, status = 200) {
  return new Response(JSON.stringify(obj), {
    status, headers: { 'content-type': 'application/json', 'cache-control': 'no-store' },
  });
}
function normKey(k) { return String(k || '').trim().toUpperCase(); }
function nowSec() { return Math.floor(Date.now() / 1000); }
function capOf(env) {
  const n = parseInt(env.DEVICE_CAP || '', 10);
  return Number.isFinite(n) && n > 0 ? n : DEFAULT_CAP;
}
function ownerKeySet(env) {
  return new Set(String(env.OWNER_KEYS || '').split(',').map(normKey).filter(Boolean));
}
function b64url(bytes) {
  return btoa(String.fromCharCode(...new Uint8Array(bytes)))
    .replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
}
async function hmac(secret, msg) {
  const key = await crypto.subtle.importKey(
    'raw', new TextEncoder().encode(secret), { name: 'HMAC', hash: 'SHA-256' }, false, ['sign']);
  return b64url(await crypto.subtle.sign('HMAC', key, new TextEncoder().encode(msg)));
}
async function makeToken(env, key, fp) {
  const exp = nowSec() + TOKEN_DAYS * 86400;
  const payload = `${key}|${fp}|${exp}`;
  const body = b64url(new TextEncoder().encode(payload));
  return `${body}.${await hmac(env.TOKEN_SECRET, payload)}`;
}
async function readBody(request) {
  try { return await request.json(); } catch (_) { return {}; }
}
function adminAuthed(request, env) {
  const h = request.headers.get('authorization') || '';
  const m = h.match(/^Bearer\s+(.+)$/i);
  return !!env.ADMIN_SECRET && m && m[1] === env.ADMIN_SECRET;
}
function pruneIdle(rec) {
  const cutoff = nowSec() - DEVICE_IDLE_EXPIRY_DAYS * 86400;
  rec.devices = (rec.devices || []).filter(d => (d.lastSeen || 0) >= cutoff);
  return rec;
}
async function getRec(env, key) {
  const raw = await env.LICENSES.get(`lic:${key}`);
  return raw ? JSON.parse(raw) : null;
}
async function putRec(env, key, rec) {
  rec.updatedAt = nowSec();
  await env.LICENSES.put(`lic:${key}`, JSON.stringify(rec));
}

/** Verify the key really exists / is enabled at Payhip (mirrors the app's call). */
async function payhipVerify(env, key) {
  if (!env.PAYHIP_SECRET) return { ok: false, reason: 'server_misconfigured' };
  const res = await fetch(`${PAYHIP_VERIFY_URL}?license_key=${encodeURIComponent(key)}`, {
    method: 'GET',
    headers: { 'product-secret-key': env.PAYHIP_SECRET, 'User-Agent': 'SPB-License-Worker' },
  });
  const text = await res.text();
  let data = null;
  try { data = JSON.parse(text); } catch (_) {}
  if (res.status >= 500) return { ok: false, reason: 'payhip_unavailable' };
  if (data && data.data && !Array.isArray(data.data) && data.data.enabled) {
    return { ok: true, email: data.data.buyer_email || '', productName: data.data.product_name || '' };
  }
  return { ok: false, reason: 'invalid_or_disabled' };
}

/* ---------- endpoints ---------- */

async function activate(request, env) {
  const { key: rawKey, fingerprint, label } = await readBody(request);
  const key = normKey(rawKey);
  const fp = String(fingerprint || '').trim();
  if (!key || !fp) return json({ ok: false, status: 'bad_request', message: 'Missing license key or device id.' }, 400);

  const cap = capOf(env);
  const unlimited = ownerKeySet(env).has(key);

  // Verify the purchase at Payhip on first contact (and refresh email/product).
  const verify = await payhipVerify(env, key);
  if (!verify.ok && !unlimited) {
    if (verify.reason === 'payhip_unavailable')
      return json({ ok: false, status: 'verify_unavailable', message: 'License server is busy — please try again in a minute.' }, 503);
    return json({ ok: false, status: 'invalid_key', message: 'That license key is invalid or disabled.' }, 200);
  }

  let rec = await getRec(env, key);
  if (!rec) rec = { devices: [], disabled: false, unlimited, email: verify.email || '', productName: verify.productName || '', createdAt: nowSec() };
  if (verify.ok) { rec.email = verify.email || rec.email; rec.productName = verify.productName || rec.productName; }
  rec.unlimited = rec.unlimited || unlimited;
  if (rec.disabled) return json({ ok: false, status: 'disabled', message: 'This license has been disabled. Contact support.' }, 200);

  pruneIdle(rec);

  const existing = rec.devices.find(d => d.fp === fp);
  if (existing) {
    existing.lastSeen = nowSec();
    if (label) existing.label = String(label).slice(0, 60);
    await putRec(env, key, rec);
    return json({ ok: true, status: 'already_active', devices: rec.devices.length, cap, token: await makeToken(env, key, fp) });
  }

  if (!rec.unlimited && rec.devices.length >= cap) {
    return json({
      ok: false, status: 'cap_exceeded', devices: rec.devices.length, cap,
      message: `This license is already active on ${rec.devices.length} device(s) — the maximum is ${cap}. ` +
               `Deactivate one of your other PCs from inside the app, or contact support to reset it.`,
    }, 200);
  }

  rec.devices.push({ fp, firstSeen: nowSec(), lastSeen: nowSec(), label: (label ? String(label).slice(0, 60) : '') });
  await putRec(env, key, rec);
  return json({ ok: true, status: 'activated', devices: rec.devices.length, cap, token: await makeToken(env, key, fp) });
}

async function heartbeat(request, env) {
  const { key: rawKey, fingerprint } = await readBody(request);
  const key = normKey(rawKey); const fp = String(fingerprint || '').trim();
  if (!key || !fp) return json({ ok: false, status: 'bad_request' }, 400);
  const rec = await getRec(env, key);
  if (!rec || rec.disabled) return json({ ok: false, status: rec ? 'disabled' : 'unknown' }, 200);
  const d = rec.devices.find(x => x.fp === fp);
  if (!d && !rec.unlimited) return json({ ok: false, status: 'not_registered' }, 200);
  if (d) d.lastSeen = nowSec();
  await putRec(env, key, rec);
  return json({ ok: true, status: 'ok', devices: rec.devices.length, cap: capOf(env), token: await makeToken(env, key, fp) });
}

async function deactivate(request, env) {
  const { key: rawKey, fingerprint } = await readBody(request);
  const key = normKey(rawKey); const fp = String(fingerprint || '').trim();
  if (!key || !fp) return json({ ok: false, status: 'bad_request' }, 400);
  const rec = await getRec(env, key);
  if (!rec) return json({ ok: true, status: 'noop', devices: 0 });
  const before = rec.devices.length;
  rec.devices = rec.devices.filter(d => d.fp !== fp);
  await putRec(env, key, rec);
  return json({ ok: true, status: 'deactivated', removed: before - rec.devices.length, devices: rec.devices.length });
}

async function adminKey(request, env, url) {
  if (!adminAuthed(request, env)) return json({ ok: false, error: 'unauthorized' }, 401);
  const key = normKey(url.searchParams.get('key'));
  if (!key) return json({ ok: false, error: 'missing_key' }, 400);
  const rec = await getRec(env, key);
  return json({ ok: true, key, cap: capOf(env), record: rec || null });
}

async function adminReset(request, env) {
  if (!adminAuthed(request, env)) return json({ ok: false, error: 'unauthorized' }, 401);
  const { key: rawKey, action } = await readBody(request);
  const key = normKey(rawKey);
  if (!key) return json({ ok: false, error: 'missing_key' }, 400);
  let rec = (await getRec(env, key)) || { devices: [], disabled: false, unlimited: false, createdAt: nowSec() };
  switch (String(action || 'clear')) {
    case 'clear':     rec.devices = []; break;                 // free all device slots
    case 'disable':   rec.disabled = true; break;              // kill the key
    case 'enable':    rec.disabled = false; break;
    case 'unlimited': rec.unlimited = true; break;             // make it a comp/owner key
    case 'limited':   rec.unlimited = false; break;
    default: return json({ ok: false, error: 'bad_action' }, 400);
  }
  await putRec(env, key, rec);
  return json({ ok: true, key, record: rec });
}
