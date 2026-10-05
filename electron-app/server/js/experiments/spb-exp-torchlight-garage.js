/* ============================================================================
 * SPB EXPERIMENT — 🔦 TORCHLIGHT GARAGE (spb-exp-torchlight-garage)
 * ============================================================================
 * Kill the lights and wave your mouse over the car like a flashlight in a dark
 * garage — chrome / flake / clearcoat flare back in real time while matte
 * panels stay dead. An HONEST flat-chip relight of the already-rendered paint
 * + spec preview (same disclaimer sun_sweep ships: no 3D car, no mesh — this
 * relights the flat texture, exactly like server_routes/sun_sweep_routes.py).
 *
 * Sources it reads (all already in the DOM, verified against the live app):
 *   - Paint pixels:  #livePreviewImg        (paint-booth-v2.html:2345)
 *   - Spec pixels:   #livePreviewSpecImg    (paint-booth-v2.html:2380)
 *       R=Metallic, G=Roughness, B=Clearcoat, A=spec mask
 *       (semantics per paint-booth-2-state-zones.js:3974-3975 + the channel
 *        bar tooltips at paint-booth-v2.html:2366-2376)
 *   - Overlay framing recipe copied from _ensureFlashMapOverlay
 *       (paint-booth-2-state-zones.js:3988-3991 — "Match #livePreviewImg's
 *        framing EXACTLY": absolute, top:0, left:50%, translateX(-50%),
 *        height:100%, width:auto). Both previews are square renders of the
 *        same 2048 UV sheet, so one recipe frames both.
 *   - Clearcoat strength formula mirrored from paint-booth-flashmap.js:59
 *       (cc<1 → 0 else (255-cc)/(255-16); 16 = max gloss, 255 = dull).
 *   - GGX roughness floor 0.045 mirrored from paint-booth-flashmap.js:70
 *       (engine clamp, engine/spec_sculpt/sun_sweep.py:95).
 *   - Metal F0 = mix(0.04, albedo, M) mirrored from paint-booth-flashmap.js:80
 *       (engine sun_sweep.py:112 — metals reflect their own colour).
 *
 * Contract (experiments registry):
 *   - NEW FILE ONLY; zero edits to existing repo files.
 *   - Registers into window.SPB_EXPERIMENTS with {id, name, pitch, enable,
 *     disable}. Complete NO-OP until enable() is called; disable() removes
 *     every node + listener this module created.
 *   - All app globals are touched behind typeof/window guards (toggleFlashMap,
 *     toggleMaterialMap, _flashMapOn, _materialMapOn, showToast, zones,
 *     spbKickLivePreview / triggerPreviewRender).
 *
 * Renderer: WebGL fragment shader (2 textures + light uniform, ~80 lines).
 * Fallback: Canvas-2D — precomputed 3x3 grid of light-position lightmaps at
 * reduced res, bilinear-crossfaded additively on mousemove (used when the
 * Electron GPU refuses a WebGL context or the context is lost).
 * ========================================================================= */
(function () {
    'use strict';

    var EXP_ID = 'torchlight-garage';
    var BTN_ID = 'spbExpTorchBtn';
    var CANVAS_ID = 'spbExpTorchCanvas';
    var HINT_ID = 'spbExpTorchHint';

    var MAX_TEX_W = 1024;   // WebGL render-res cap (live preview is 1024 anyway)
    var FB_RES = 288;       // 2D-fallback lightmap width
    var FB_GRID = 3;        // 3x3 = 9 precomputed light positions
    var R_MIN = 0.045;      // engine GGX roughness clamp (flashmap.js:70)

    // ---- module state (torn down completely by disable()) -----------------
    var S = {
        enabled: false,
        on: false,
        mode: null,          // 'gl' | '2d' | null (undecided)
        btn: null,
        btnParentFallback: false,
        hint: null,
        canvas: null,
        gl: null, prog: null, uni: null, texPaint: null, texSpec: null,
        texDirty: true,
        fb: null,            // {w,h,ambient(canvas),maps[canvas x9],stale}
        fbTimer: 0,
        lightU: 0.5, lightV: 0.42,
        height: 0.34,        // torch height above the chip plane (UV units) = beam width
        gain: 1.7,           // torch strength
        raf: 0,
        domReadyHandler: null,
        onPaintLoad: null, onSpecLoad: null,
        onMove: null, onLeave: null, onWheel: null,
        exclusionBtns: [],   // [{el, fn}] click hooks on Flash/Material buttons
        prevPaneCursor: '',
    };

    function $(id) { return document.getElementById(id); }
    function pane() { return $('previewPaintPane'); }
    function paintImgEl() { return $('livePreviewImg'); }
    function specImgEl() { return $('livePreviewSpecImg'); }
    function imgReady(img) { return !!(img && img.src && img.naturalWidth > 0); }
    function imgsReady() { return imgReady(paintImgEl()) && imgReady(specImgEl()); }
    function clamp(v, lo, hi) { return v < lo ? lo : (v > hi ? hi : v); }
    function toast(msg) {
        if (typeof window.showToast === 'function') { try { window.showToast(msg, false); } catch (_) { } }
    }

    // Mirror of SPB_FlashMap.clearcoatStrength (paint-booth-flashmap.js:59), 0..255 in.
    function clearcoatStrength(cc) { return cc < 1 ? 0 : clamp((255 - cc) / (255 - 16), 0, 1); }

    // =========================================================================
    // BUTTON — lives in the view-overlays toolbar cluster, right after 🗺️
    // Flash Map (paint-booth-v2.html:1316-1323). Falls back to a fixed chip if
    // the toolbar isn't there (e.g. stripped-down page variant).
    // =========================================================================
    function buildButton() {
        if (S.btn) return;
        var btn = document.createElement('button');
        btn.id = BTN_ID;
        btn.type = 'button';
        btn.className = 'vtool-btn';
        btn.setAttribute('aria-pressed', 'false');
        btn.setAttribute('aria-label', 'Toggle Torchlight Garage overlay');
        btn.title = 'Torchlight Garage (EXPERIMENT) — kill the lights and sweep your mouse over the car like a flashlight in a dark garage. Chrome / flake / clearcoat flare back at the beam; matte panels stay dead. Honest flat relight of the rendered paint + spec preview (no 3D). Scroll wheel = beam width.';
        btn.textContent = '🔦';
        btn.addEventListener('click', toggleTorch);

        var anchor = $('btnFlashMap');
        if (anchor && anchor.parentNode) {
            anchor.insertAdjacentElement('afterend', btn);
        } else {
            var cluster = document.querySelector('.spb-tb-cluster');
            if (cluster) {
                cluster.appendChild(btn);
            } else {
                // Last-resort fixed chip so the experiment is still reachable.
                btn.style.cssText = 'position:fixed;top:8px;right:12px;z-index:9999;padding:4px 10px;' +
                    'background:#14162a;color:#dfe6ff;border:1px solid rgba(140,160,255,0.4);border-radius:6px;cursor:pointer;';
                document.body.appendChild(btn);
                S.btnParentFallback = true;
            }
        }
        S.btn = btn;
    }

    function styleButton(onState) {
        if (!S.btn) return;
        S.btn.setAttribute('aria-pressed', onState ? 'true' : 'false');
        // Same active-state treatment the sibling toggles use (state-zones:4053).
        S.btn.style.background = onState ? 'linear-gradient(90deg,#f7a531,#5b3df0)' : (S.btnParentFallback ? '#14162a' : '');
        S.btn.style.color = onState ? '#fff' : (S.btnParentFallback ? '#dfe6ff' : '');
    }

    // =========================================================================
    // OVERLAY CANVAS — exact copy of the Flash Map framing recipe
    // (paint-booth-2-state-zones.js:3988-3991) so the torch render lands on the
    // SAME box as the car. Opaque (it IS the darkened garage), z 37 = above the
    // flash(35)/material(36) overlays we force off, below the spec hover
    // overlay(40) and the floating readout(42). pointer-events:none so the
    // pane's own mouse events (incl. our mousemove) keep working untouched.
    // =========================================================================
    function ensureCanvas(recreate) {
        var p = pane();
        if (!p) return null;
        var c = $(CANVAS_ID);
        if (c && recreate) { c.remove(); c = null; }
        if (!c) {
            c = document.createElement('canvas');
            c.id = CANVAS_ID;
            c.style.cssText = 'position:absolute;top:0;left:50%;transform:translateX(-50%);height:100%;width:auto;' +
                'display:none;z-index:37;pointer-events:none;background:#05060c;';
            if (getComputedStyle(p).position === 'static') p.style.position = 'relative';
            p.appendChild(c);
            S.canvas = c;
            S.gl = null; S.prog = null; S.texPaint = null; S.texSpec = null; S.texDirty = true;
            S.fb = null;
        }
        S.canvas = c;
        return c;
    }

    function ensureHint() {
        var p = pane();
        if (!p) return null;
        var h = $(HINT_ID);
        if (!h) {
            h = document.createElement('div');
            h.id = HINT_ID;
            h.style.cssText = 'display:none;position:absolute;bottom:8px;left:8px;z-index:43;pointer-events:none;' +
                'background:rgba(8,10,20,0.84);color:#ffd9a0;font-size:10.5px;font-weight:700;padding:3px 9px;' +
                'border-radius:4px;letter-spacing:0.3px;';
            p.appendChild(h);
        }
        S.hint = h;
        return h;
    }

    function updateHint() {
        var h = ensureHint();
        if (!h) return;
        if (!S.on) { h.style.display = 'none'; return; }
        var beam = Math.round(S.height * 100);
        h.textContent = '🔦 TORCHLIGHT — mouse = beam · wheel = width (' + beam + ') · flat relight, not 3D';
        h.style.display = '';
    }

    // =========================================================================
    // WEBGL PATH — honest flat-chip lighting: N = V = (0,0,1), point light at
    // (mouse, height) in UV space. Specular lobe width from 1-R/255 (GGX),
    // intensity + colour from M/255 (F0 = mix(0.04, albedo, m) — engine
    // sun_sweep.py:112), tight secondary lobe from clearcoatStrength(Cc).
    // =========================================================================
    var VERT_SRC = [
        'attribute vec2 aPos;',
        'varying vec2 vUV;',
        'void main() {',
        '  vUV = vec2(aPos.x * 0.5 + 0.5, 0.5 - aPos.y * 0.5);', // v=0 at top, matches image rows
        '  gl_Position = vec4(aPos, 0.0, 1.0);',
        '}'
    ].join('\n');

    var FRAG_SRC = [
        // highp where available: chrome's a2 = 0.045^4 ~ 4e-6 denormalizes in
        // mediump and the GGX lobe can flush to 0 (= chrome never flashes).
        '#ifdef GL_FRAGMENT_PRECISION_HIGH',
        'precision highp float;',
        '#else',
        'precision mediump float;',
        '#endif',
        'varying vec2 vUV;',
        'uniform sampler2D uPaint;',   // rendered paint (albedo) preview
        'uniform sampler2D uSpec;',    // R=Metallic G=Roughness B=Clearcoat A=mask
        'uniform vec2  uLight;',       // torch position in UV space
        'uniform float uHeight;',      // torch height above chip plane (beam width)
        'uniform float uAspect;',      // canvas w/h for isotropic distance
        'uniform float uGain;',        // torch strength
        'const float PI = 3.14159265;',
        'const float R_MIN = 0.045;',  // engine GGX floor (sun_sweep.py:95)
        'float ggxD(float ndh, float a2) {',
        '  float d = ndh * ndh * (a2 - 1.0) + 1.0;',
        '  return a2 / (PI * d * d);',
        '}',
        'void main() {',
        '  vec4 paint = texture2D(uPaint, vUV);',
        '  vec4 spec  = texture2D(uSpec,  vUV);',
        '  vec3 garage = vec3(0.012, 0.014, 0.022);',            // dark garage floor
        '  float car = step(0.03, paint.a);',                     // outside the car cutout?
        // spec-active gate (same rules as flashmap.js:106): mask alpha on AND not the
        // empty all-zero background of the spec preview.
        '  float active = step(0.03, spec.a) * step(0.002, spec.r + spec.g + spec.b);',
        // -- torch geometry (flat chip: normal = view = +Z) --
        '  vec2  d   = (uLight - vUV) * vec2(uAspect, 1.0);',
        '  float r2  = dot(d, d) + uHeight * uHeight;',
        '  float r   = sqrt(r2);',
        '  float ndl = uHeight / r;',                             // cos(theta)
        '  float att = (uHeight * uHeight * uHeight) / (r2 * r);',// cos/r^2, =1 at beam centre
        '  vec3  L   = vec3(d / r, ndl);',
        '  vec3  H   = normalize(L + vec3(0.0, 0.0, 1.0));',
        '  float ndh = clamp(H.z, 0.0, 1.0);',
        // -- channels --
        '  float m     = spec.r;',
        '  float rough = max(spec.g, R_MIN);',
        '  float ccS   = spec.b < 0.004 ? 0.0 : clamp((1.0 - spec.b) / (1.0 - 16.0 / 255.0), 0.0, 1.0);',
        // -- base specular lobe: GGX width from roughness, colour from metal F0 --
        '  float a  = rough * rough;',
        '  float a2 = a * a;',
        '  vec3  F0 = mix(vec3(0.04), paint.rgb, m);',            // metals reflect their own colour
        '  vec3  F  = F0 + (1.0 - F0) * pow(1.0 - ndh, 5.0);',
        '  vec3  lobe = ggxD(ndh, a2) * F * ndl * 0.25;',
        // -- broad metal sheen so flake/chrome glow around the hotspot --
        '  vec3  sheen = pow(ndh, 8.0) * F0 * (1.0 - rough) * 0.5 * ndl;',
        // -- tight clearcoat lobe, albedo-independent (fixed rough 0.06, sun_sweep acc) --
        '  float a2cc = 0.06 * 0.06 * 0.06 * 0.06;',
        '  float Fcc  = 0.04 + 0.96 * pow(1.0 - ndh, 5.0);',
        '  float cc   = ggxD(ndh, a2cc) * Fcc * ccS * ndl * 0.25;',
        // -- diffuse pool of the torch (metals barely diffuse) --
        '  vec3 diffuse = paint.rgb * (1.0 - 0.85 * m) * ndl;',
        '  vec3 torch = vec3(1.0, 0.97, 0.90);',                  // warm incandescent beam
        '  vec3 lit = (diffuse + (lobe + sheen + vec3(cc)) * active) * att * torch * uGain;',
        '  vec3 ambient = paint.rgb * 0.055;',                    // lights-off ambience
        '  vec3 col = ambient + lit;',
        '  col = vec3(1.0) - exp(-col * 1.35);',                  // soft knee: chrome flares, never ugly-clips
        '  gl_FragColor = vec4(mix(garage, col, car), 1.0);',
        '}'
    ].join('\n');

    function compileShader(gl, type, src) {
        var sh = gl.createShader(type);
        gl.shaderSource(sh, src);
        gl.compileShader(sh);
        if (!gl.getShaderParameter(sh, gl.COMPILE_STATUS)) {
            var log = gl.getShaderInfoLog(sh);
            gl.deleteShader(sh);
            throw new Error('shader: ' + log);
        }
        return sh;
    }

    function initGL() {
        var c = S.canvas;
        if (!c) return false;
        var gl = null;
        try {
            gl = c.getContext('webgl', { alpha: false, antialias: false, preserveDrawingBuffer: false })
                || c.getContext('experimental-webgl', { alpha: false });
        } catch (_) { gl = null; }
        if (!gl) return false;
        try {
            var prog = gl.createProgram();
            gl.attachShader(prog, compileShader(gl, gl.VERTEX_SHADER, VERT_SRC));
            gl.attachShader(prog, compileShader(gl, gl.FRAGMENT_SHADER, FRAG_SRC));
            gl.linkProgram(prog);
            if (!gl.getProgramParameter(prog, gl.LINK_STATUS)) throw new Error('link: ' + gl.getProgramInfoLog(prog));
            gl.useProgram(prog);

            var quad = gl.createBuffer();
            gl.bindBuffer(gl.ARRAY_BUFFER, quad);
            gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1, -1, 1, -1, -1, 1, 1, 1]), gl.STATIC_DRAW);
            var aPos = gl.getAttribLocation(prog, 'aPos');
            gl.enableVertexAttribArray(aPos);
            gl.vertexAttribPointer(aPos, 2, gl.FLOAT, false, 0, 0);

            S.uni = {
                light: gl.getUniformLocation(prog, 'uLight'),
                height: gl.getUniformLocation(prog, 'uHeight'),
                aspect: gl.getUniformLocation(prog, 'uAspect'),
                gain: gl.getUniformLocation(prog, 'uGain'),
                paint: gl.getUniformLocation(prog, 'uPaint'),
                spec: gl.getUniformLocation(prog, 'uSpec'),
            };
            gl.uniform1i(S.uni.paint, 0);
            gl.uniform1i(S.uni.spec, 1);

            S.texPaint = makeTexture(gl);
            S.texSpec = makeTexture(gl);
            S.gl = gl;
            S.prog = prog;

            // GPU quirk safety net: on context loss, fall back to the 2D path.
            c.addEventListener('webglcontextlost', function (e) {
                try { e.preventDefault(); } catch (_) { }
                S.mode = '2d';
                ensureCanvas(true);       // WebGL-bound canvas can't become 2D — recreate
                if (S.fb) S.fb.stale = true;
                if (S.on) scheduleDraw();
            });
            return true;
        } catch (err) {
            try { console.warn('[torchlight-garage] WebGL unavailable, using 2D fallback:', err && err.message); } catch (_) { }
            return false;
        }
    }

    function makeTexture(gl) {
        var t = gl.createTexture();
        gl.bindTexture(gl.TEXTURE_2D, t);
        // NPOT-safe: clamp + linear, no mips.
        gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE);
        gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
        gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR);
        gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.LINEAR);
        return t;
    }

    function uploadTextures() {
        var gl = S.gl, p = paintImgEl(), s = specImgEl();
        if (!gl || !imgReady(p) || !imgReady(s)) return false;
        // Canvas resolution follows the paint preview (capped) — CSS scales it into frame.
        var w = Math.min(p.naturalWidth, MAX_TEX_W);
        var h = Math.max(1, Math.round(p.naturalHeight * w / p.naturalWidth));
        if (S.canvas.width !== w || S.canvas.height !== h) { S.canvas.width = w; S.canvas.height = h; }
        gl.pixelStorei(gl.UNPACK_FLIP_Y_WEBGL, false);
        gl.pixelStorei(gl.UNPACK_PREMULTIPLY_ALPHA_WEBGL, false);
        try {
            gl.activeTexture(gl.TEXTURE0);
            gl.bindTexture(gl.TEXTURE_2D, S.texPaint);
            gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, gl.RGBA, gl.UNSIGNED_BYTE, p);
            gl.activeTexture(gl.TEXTURE1);
            gl.bindTexture(gl.TEXTURE_2D, S.texSpec);
            gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, gl.RGBA, gl.UNSIGNED_BYTE, s);
        } catch (_) { return false; }
        return true;
    }

    function glDraw() {
        var gl = S.gl, c = S.canvas;
        if (!gl || !c) return;
        gl.viewport(0, 0, c.width, c.height);
        gl.uniform2f(S.uni.light, S.lightU, S.lightV);
        gl.uniform1f(S.uni.height, S.height);
        gl.uniform1f(S.uni.aspect, c.width / Math.max(1, c.height));
        gl.uniform1f(S.uni.gain, S.gain);
        gl.drawArrays(gl.TRIANGLE_STRIP, 0, 4);
    }

    // =========================================================================
    // CANVAS-2D FALLBACK — precompute the ambient base + a 3x3 grid of torch
    // lightmaps (same math as the shader, JS mirror) at reduced res, then
    // bilinear-crossfade the 4 nearest maps additively on mousemove.
    // =========================================================================
    function readPixels(img, w, h) {
        var c = document.createElement('canvas');
        c.width = w; c.height = h;
        var ctx = c.getContext('2d', { willReadFrequently: true });
        ctx.drawImage(img, 0, 0, w, h);
        try { return ctx.getImageData(0, 0, w, h).data; } catch (_) { return null; }
    }

    function buildFallback() {
        var p = paintImgEl(), s = specImgEl();
        if (!imgReady(p) || !imgReady(s)) return null;
        var w = FB_RES;
        var h = Math.max(1, Math.round(p.naturalHeight * w / p.naturalWidth));
        var paint = readPixels(p, w, h);
        var spec = readPixels(s, w, h);
        if (!paint || !spec) return null;

        var aspect = w / h;
        var n = w * h;

        function mapCanvas(fill) {
            var c = document.createElement('canvas');
            c.width = w; c.height = h;
            var ctx = c.getContext('2d');
            ctx.putImageData(fill, 0, 0);
            return c;
        }

        // -- ambient base (lights off) --
        var amb = new ImageData(w, h);
        var ad = amb.data;
        for (var i = 0; i < n; i++) {
            var o = i * 4;
            if (paint[o + 3] < 8) { ad[o] = 3; ad[o + 1] = 4; ad[o + 2] = 6; ad[o + 3] = 255; continue; }
            ad[o] = Math.round(paint[o] * 0.055);
            ad[o + 1] = Math.round(paint[o + 1] * 0.055);
            ad[o + 2] = Math.round(paint[o + 2] * 0.055);
            ad[o + 3] = 255;
        }

        // -- 9 torch-contribution maps (additive, black = no light) --
        var maps = [];
        var hgt = S.height, gain = S.gain;
        var a2cc = Math.pow(0.06, 4);
        for (var gy = 0; gy < FB_GRID; gy++) {
            for (var gx = 0; gx < FB_GRID; gx++) {
                var lu = gx / (FB_GRID - 1), lv = gy / (FB_GRID - 1);
                var im = new ImageData(w, h);
                var d = im.data;
                for (var y = 0; y < h; y++) {
                    var v = (y + 0.5) / h;
                    var dy = (lv - v);
                    for (var x = 0; x < w; x++) {
                        var idx = (y * w + x) * 4;
                        var pa = paint[idx + 3];
                        if (pa < 8) { d[idx + 3] = 255; continue; }
                        var u = (x + 0.5) / w;
                        var dx = (lu - u) * aspect;
                        var r2 = dx * dx + dy * dy + hgt * hgt;
                        var r = Math.sqrt(r2);
                        var ndl = hgt / r;
                        var att = (hgt * hgt * hgt) / (r2 * r);
                        // half vector (V = N = +Z)
                        var hx = dx / r, hy = dy / r, hz = ndl + 1.0;
                        var hlen = Math.sqrt(hx * hx + hy * hy + hz * hz);
                        var ndh = clamp(hz / hlen, 0, 1);
                        var f5 = Math.pow(1 - ndh, 5);
                        var m = spec[idx] / 255;
                        var rough = Math.max(spec[idx + 1] / 255, R_MIN);
                        var ccS = clearcoatStrength(spec[idx + 2]);
                        var active = (spec[idx + 3] >= 8 && (spec[idx] + spec[idx + 1] + spec[idx + 2]) > 0) ? 1 : 0;
                        var a2 = Math.pow(rough, 4);
                        var den = ndh * ndh * (a2 - 1) + 1;
                        var D = a2 / (Math.PI * den * den);
                        var denc = ndh * ndh * (a2cc - 1) + 1;
                        var Dcc = a2cc / (Math.PI * denc * denc);
                        var ccT = Dcc * (0.04 + 0.96 * f5) * ccS * ndl * 0.25 * active;
                        var sheenS = Math.pow(ndh, 8) * (1 - rough) * 0.5 * ndl * active;
                        var diffS = (1 - 0.85 * m) * ndl;
                        for (var ch = 0; ch < 3; ch++) {
                            var alb = paint[idx + ch] / 255;
                            var F0 = 0.04 * (1 - m) + m * alb;
                            var F = F0 + (1 - F0) * f5;
                            var lit = (alb * diffS + (D * F * ndl * 0.25 + sheenS * F0) * active + ccT)
                                * att * gain * (ch === 0 ? 1.0 : (ch === 1 ? 0.97 : 0.90));
                            d[idx + ch] = Math.round(255 * (1 - Math.exp(-lit * 1.35)));
                        }
                        d[idx + 3] = 255;
                    }
                }
                maps.push(mapCanvas(im));
            }
        }
        S.fb = { w: w, h: h, ambient: mapCanvas(amb), maps: maps, stale: false };
        return S.fb;
    }

    function fbCompose() {
        var fb = S.fb;
        if (!fb || fb.stale) fb = buildFallback();
        if (!fb) return;
        var c = S.canvas;
        if (c.width !== fb.w || c.height !== fb.h) { c.width = fb.w; c.height = fb.h; }
        var ctx = c.getContext('2d');
        if (!ctx) return;
        ctx.globalCompositeOperation = 'source-over';
        ctx.globalAlpha = 1;
        ctx.drawImage(fb.ambient, 0, 0);
        // bilinear weights over the 3x3 light grid
        var gxf = clamp(S.lightU, 0, 1) * (FB_GRID - 1);
        var gyf = clamp(S.lightV, 0, 1) * (FB_GRID - 1);
        var x0 = Math.min(FB_GRID - 2, Math.floor(gxf)), y0 = Math.min(FB_GRID - 2, Math.floor(gyf));
        var fx = gxf - x0, fy = gyf - y0;
        var corners = [
            [x0, y0, (1 - fx) * (1 - fy)], [x0 + 1, y0, fx * (1 - fy)],
            [x0, y0 + 1, (1 - fx) * fy], [x0 + 1, y0 + 1, fx * fy],
        ];
        ctx.globalCompositeOperation = 'lighter';
        for (var i = 0; i < corners.length; i++) {
            var wgt = corners[i][2];
            if (wgt < 0.01) continue;
            ctx.globalAlpha = wgt;
            ctx.drawImage(fb.maps[corners[i][1] * FB_GRID + corners[i][0]], 0, 0);
        }
        ctx.globalAlpha = 1;
        ctx.globalCompositeOperation = 'source-over';
    }

    function fbRecomputeDebounced() {
        if (S.fbTimer) clearTimeout(S.fbTimer);
        S.fbTimer = setTimeout(function () {
            S.fbTimer = 0;
            if (S.mode === '2d' && S.on) { if (S.fb) S.fb.stale = true; scheduleDraw(); }
        }, 200);
    }

    // =========================================================================
    // DRAW ORCHESTRATION
    // =========================================================================
    function scheduleDraw() {
        if (S.raf || !S.on) return;
        S.raf = requestAnimationFrame(function () { S.raf = 0; draw(); });
    }

    function draw() {
        if (!S.on) return;
        var c = ensureCanvas(false);
        if (!c) return;
        if (!imgsReady()) { c.style.display = 'none'; return; }
        if (S.mode === null) {
            S.mode = initGL() ? 'gl' : '2d';
            if (S.mode === '2d') ensureCanvas(true); // fresh canvas for a 2D context
        }
        if (S.mode === 'gl') {
            if (S.texDirty) { if (!uploadTextures()) return; S.texDirty = false; }
            glDraw();
        } else {
            fbCompose();
        }
        S.canvas.style.display = '';
        updateHint();
    }

    // =========================================================================
    // TORCH TOGGLE + INPUT
    // =========================================================================
    function torchOn() {
        S.on = true;
        styleButton(true);
        // Mutually exclusive with the other paint-pane overlays (same courtesy
        // Flash/Material extend each other — state-zones:4056-4058 / 4171-4175).
        try {
            if (window._flashMapOn && typeof window.toggleFlashMap === 'function') window.toggleFlashMap();
            if (window._materialMapOn && typeof window.toggleMaterialMap === 'function') window.toggleMaterialMap();
        } catch (_) { }

        var p = pane();
        if (p) {
            S.prevPaneCursor = p.style.cursor || '';
            p.style.cursor = 'crosshair';
            S.onMove = function (e) {
                if (!S.on || !S.canvas) return;
                var r = S.canvas.getBoundingClientRect();
                if (r.width < 2 || r.height < 2) return;
                S.lightU = (e.clientX - r.left) / r.width;
                S.lightV = (e.clientY - r.top) / r.height;
                scheduleDraw();
            };
            S.onLeave = function () { scheduleDraw(); }; // beam parks at last position
            S.onWheel = function (e) {
                if (!S.on) return;
                e.preventDefault();
                S.height = clamp(S.height * (e.deltaY > 0 ? 1.12 : 1 / 1.12), 0.10, 0.95);
                if (S.mode === '2d') fbRecomputeDebounced();
                scheduleDraw();
                updateHint();
            };
            p.addEventListener('mousemove', S.onMove);
            p.addEventListener('mouseleave', S.onLeave);
            p.addEventListener('wheel', S.onWheel, { passive: false });
        }

        if (!imgsReady()) {
            var noZones = (typeof window.zones === 'undefined' || !window.zones || !window.zones.length);
            toast(noZones
                ? 'Torchlight: configure a zone so the live preview renders, then the garage goes dark.'
                : 'Torchlight: render a preview first — it lights up as soon as the preview lands.');
            // Nudge the preview pipeline awake if the app exposes its revive hook.
            try {
                if (typeof window.spbKickLivePreview === 'function') window.spbKickLivePreview();
                else if (typeof window.triggerPreviewRender === 'function') window.triggerPreviewRender();
            } catch (_) { }
        }
        updateHint();
        scheduleDraw();
    }

    function torchOff() {
        S.on = false;
        styleButton(false);
        if (S.raf) { cancelAnimationFrame(S.raf); S.raf = 0; }
        if (S.fbTimer) { clearTimeout(S.fbTimer); S.fbTimer = 0; }
        var p = pane();
        if (p) {
            if (S.onMove) p.removeEventListener('mousemove', S.onMove);
            if (S.onLeave) p.removeEventListener('mouseleave', S.onLeave);
            if (S.onWheel) p.removeEventListener('wheel', S.onWheel);
            p.style.cursor = S.prevPaneCursor;
        }
        S.onMove = S.onLeave = S.onWheel = null;
        var c = $(CANVAS_ID);
        if (c) c.style.display = 'none';
        if (S.hint) S.hint.style.display = 'none';
    }

    function toggleTorch() { if (S.on) torchOff(); else torchOn(); }

    // =========================================================================
    // ENABLE / DISABLE (experiments registry contract)
    // =========================================================================
    function buildAll() {
        buildButton();
        // Stay live: the state-zones spec-img load hook pattern (state-zones:
        // 4371-4380) — re-upload textures / rebuild lightmaps after every live
        // preview render. addEventListener keeps the app's own hooks untouched.
        var onLoad = function () {
            S.texDirty = true;
            if (S.fb) S.fb.stale = true;
            if (S.on) scheduleDraw();
        };
        var p = paintImgEl(), s = specImgEl();
        if (p) { S.onPaintLoad = onLoad; p.addEventListener('load', S.onPaintLoad); }
        if (s) { S.onSpecLoad = onLoad; s.addEventListener('load', S.onSpecLoad); }
        // If the user flips Flash/Material Map ON while the torch is lit, the
        // garage yields (they own the paint-pane overlay slot).
        ['btnFlashMap', 'btnMaterialMap'].forEach(function (id) {
            var el = $(id);
            if (!el) return;
            var fn = function () { if (S.on) torchOff(); };
            el.addEventListener('click', fn);
            S.exclusionBtns.push({ el: el, fn: fn });
        });
    }

    function enable() {
        if (S.enabled) return;
        S.enabled = true;
        if (document.readyState === 'loading') {
            S.domReadyHandler = function () { S.domReadyHandler = null; if (S.enabled) buildAll(); };
            document.addEventListener('DOMContentLoaded', S.domReadyHandler);
        } else {
            buildAll();
        }
    }

    function disable() {
        if (!S.enabled) return;
        S.enabled = false;
        if (S.domReadyHandler) {
            document.removeEventListener('DOMContentLoaded', S.domReadyHandler);
            S.domReadyHandler = null;
        }
        if (S.on) torchOff();
        var p = paintImgEl(), s = specImgEl();
        if (p && S.onPaintLoad) p.removeEventListener('load', S.onPaintLoad);
        if (s && S.onSpecLoad) s.removeEventListener('load', S.onSpecLoad);
        S.onPaintLoad = S.onSpecLoad = null;
        S.exclusionBtns.forEach(function (b) { try { b.el.removeEventListener('click', b.fn); } catch (_) { } });
        S.exclusionBtns = [];
        var c = $(CANVAS_ID); if (c) c.remove();
        var h = $(HINT_ID); if (h) h.remove();
        if (S.btn) { S.btn.remove(); S.btn = null; }
        S.btnParentFallback = false;
        S.canvas = null; S.hint = null;
        S.gl = null; S.prog = null; S.uni = null; S.texPaint = null; S.texSpec = null;
        S.fb = null; S.mode = null; S.texDirty = true;
    }

    // ---- self-register (NO-OP until enable() is called) --------------------
    if (typeof window !== 'undefined') {
        window.SPB_EXPERIMENTS = window.SPB_EXPERIMENTS || [];
        window.SPB_EXPERIMENTS.push({
            id: EXP_ID,
            name: 'Torchlight Garage',
            pitch: 'Kill the lights and wave your mouse over your car like a flashlight in a dark garage — the chrome and flake flare back at you in real time while the matte panels stay dead.',
            enable: enable,
            disable: disable,
        });
    }
})();
