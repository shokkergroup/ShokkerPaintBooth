# Pattern-Brush Route Fix — Proposal (Case B)

**Date:** 2026-05-27
**Investigator:** SPB dev agent (TICK 2)
**Original finding:** bug_hunt_findings.md, CRITICAL #1
**Suggested one-line fix from TICK 1:** repoint `fetch('/api/render-pattern-tile')` at `/api/pattern-layer`
**Verdict:** **Case B — contracts differ, naive rename would break worse than current fallback.**

---

## Contract A — what `paint-booth-3-canvas.js:14934` currently sends/expects

**Request:**
```http
POST /api/render-pattern-tile
Content-Type: application/json

{"pattern": "<patternName>", "size": 256}
```

**Response (expected):**
```json
{"image": "<data URI or URL>"}
```
Then JS does `img.src = data.image`.

## Contract B — what `/api/pattern-layer` (server_routes/pattern_layer_routes.py) actually provides

**Request:**
```http
GET /api/pattern-layer?pattern=<id>&w=<int>&h=<int>&scale=<float>&rotation=<float>&seed=<int>
```
- Method: **GET** (not POST)
- Params: **query string** (not JSON body)
- `pattern` is required; `w/h` default 2048 (clamped 64–4096); `scale` default 1.0; `rotation` default 0; `seed` default 42.
- Errors come back as JSON `{error, pattern, message}` with 4xx/5xx status.

**Response (success):**
```http
200 OK
Content-Type: image/png
Cache-Control: no-store

<raw PNG bytes — grayscale RGBA, single-channel value mirrored into R/G/B, A=255>
```
- **NOT JSON.** Raw PNG body, ready to feed directly to `Image.src` via blob URL or `Image.src='/api/pattern-layer?...'` directly.

## Why naive rename breaks things

A one-line rename of the URL keeps:
- the POST method → server returns 405 (route is GET-only),
- the JSON body → ignored,
- the JSON-parse `r.json()` → throws on PNG bytes,
- the `data.image` access → undefined.

So the fetch resolves into the same `.catch(...)` fallback we already have. **No improvement.** Slightly worse, in fact, because the user might see a brief flash before fallback.

## Brush consumer side (paintPatternBrushAt, line 14997)

The brush samples R/G/B from `_patternBrushTexture` (a 256×256 HTMLCanvasElement). Grayscale RGBA is fine — the existing procedural fallback already paints grayscale (e.g. crosshatch, noise). The pattern texture is used as direct color blend, not a mask. So `/api/pattern-layer`'s grayscale output is consumable.

## Recommended fix — JS-side adapter (minimal, no server change)

Replace the fetch in `loadPatternBrush()` (paint-booth-3-canvas.js around lines 14933–14949) with:

```js
// Render a 256x256 pattern tile via the server. /api/pattern-layer is a GET
// returning raw image/png bytes (grayscale RGBA), not JSON-with-dataURI.
const url = `/api/pattern-layer?pattern=${encodeURIComponent(patternName)}&w=256&h=256&scale=1&rotation=0&seed=42`;
fetch(url).then(r => {
    if (!r.ok) throw new Error(`pattern-layer ${r.status}`);
    return r.blob();
}).then(blob => {
    const img = new Image();
    img.onload = function() {
        const c = document.createElement('canvas');
        c.width = 256; c.height = 256;
        c.getContext('2d').drawImage(img, 0, 0, 256, 256);
        _patternBrushTexture = c;
        _patternBrushTextureData = null;  // invalidate brush-stamp cache (line 14994 contract)
        _patternBrushTextureKey = null;
        if (typeof showToast === 'function') showToast(`Pattern brush: ${patternName}`);
        // Release blob URL after load
        URL.revokeObjectURL(img.src);
    };
    img.onerror = function() { URL.revokeObjectURL(img.src); throw new Error('img decode'); };
    img.src = URL.createObjectURL(blob);
}).catch(() => {
    // existing procedural fallback unchanged
    ...
});
```

**Critical extra detail TICK 1 missed:** must invalidate `_patternBrushTextureData` and `_patternBrushTextureKey` (set both to `null`) when swapping the texture canvas. Otherwise the cache at line 15009–15014 returns stale pixel data from the previously loaded pattern. This is a latent bug in the original code too — switching patterns mid-stroke would have re-used the prior texture's pixel buffer.

## Plan to apply

1. Edit `paint-booth-3-canvas.js` (root) — replace the fetch block.
2. Mirror to `electron-app/server/paint-booth-3-canvas.js`.
3. Mirror to `electron-app/server/pyserver/_internal/paint-booth-3-canvas.js`.
4. `node --check` each.
5. md5 verify all three.
6. Smoke-test `/api/pattern-layer` from Python: import server, call test_client, assert PNG bytes back, assert PIL can decode to 256×256 RGBA.
7. Append result to bug_hunt_findings.md.

**Not applied in this tick — proposal only, per Case B protocol.** Owner approval recommended before mirror-edit (the cache-invalidation detail is a behavior change, not a pure rename).
