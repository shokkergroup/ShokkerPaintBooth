/* ============================================================================
 * [SPB-REV-LENS 2026-10-10] SHINE LENS - live physically based view of the
 * CURRENT paint + spec the Live Preview already holds (#livePreviewImg and
 * #livePreviewSpecImg, the same source as the COMBINED / R METAL / G ROUGH /
 * B COAT chips). WebGL2, client side, never triggers a render, never writes
 * paint / spec / zones / files. It is a view only.
 *
 * Modes (bar floating on the Live Preview, absolute: nothing moves):
 *   Off | Lens (circle under the cursor) | Full (whole preview shaded) |
 *   Sweep (Full + light orbiting so flakes / candy / chrome pop).
 *   Light: drag the puck in the bar, or drag on the shaded preview (Full/Sweep).
 * Peek: HOLD the ` key (Backquote, free in SPB) over the SOURCE canvas or the
 *   Live Preview while using any tool: a shine circle appears at the cursor,
 *   registered pixel-for-pixel with what is under it.
 *
 * Public: window.SPBRevLens  { setMode, getMode, setLight, getLight, peek,
 *   refresh, getSpec, setSelectionMask, patchSpec, patchPaint, bench, _test }
 *   REV-MATERIAL / any live-stroke tool may call patchSpec(x,y,w,h,rgba) /
 *   patchPaint(...) (texture-resolution coords) for instant stroke shine before
 *   the preview re-renders; the next preview load replaces it with the truth.
 *
 * Kill switch: window.SPB_REV_LENS_OFF = true, or localStorage
 *   SPB_REV_LENS_OFF = '1' (then nothing is created: no bar, no menu, no key).
 * ==========================================================================*/
(function () {
    'use strict';
    if (typeof window === 'undefined' || typeof document === 'undefined') return;
    const C = window.SPBShineCore;
    if (!C || C.killed()) { window.SPBRevLens = { off: true }; return; }

    const S = {
        mode: 'off',            // off | lens | full | sweep
        az: -0.9, el: 0.78,     // key light azimuth / elevation (radians)
        exposure: 1.0, curv: 0.9,
        mouse: { x: -1, y: -1 },
        peek: false,
        dirty: true,
        forceRes: 0,            // bench only: force the backing store size
        selMask: null, selW: 0, selH: 0, selVer: 0,
        paintVer: 0, specVer: 0, spec: null, specSrc: '', specPending: null,
        lastT: 0, raf: 0, frames: 0,
        stats: { frames: 0, lastMs: 0 },
    };
    const LENS_R = 96, PEEK_R = 112;

    // ------------------------------------------------------------ data source
    function paintImg() { return document.getElementById('livePreviewImg'); }
    function specImg() { return document.getElementById('livePreviewSpecImg'); }

    function loadSpec(force) {
        const img = specImg();
        const src = img && (img.currentSrc || img.src);
        if (!src || !img.complete || !img.naturalWidth) return Promise.resolve(S.spec);
        if (!force && src === S.specSrc && S.spec) return Promise.resolve(S.spec);
        if (S.specPending && S.specPending.src === src) return S.specPending.p;
        const p = (async function () {
            let px = null;
            try {
                if (window.SPBSpecPngPixels && window.SPBSpecPngPixels.load) px = await window.SPBSpecPngPixels.load(src);
            } catch (_) { px = null; }
            if (!px) {
                // fallback: canvas readback (premultiplied where A<255, exact where A=255)
                const c = document.createElement('canvas');
                c.width = img.naturalWidth; c.height = img.naturalHeight;
                const x = c.getContext('2d', { willReadFrequently: true });
                x.drawImage(img, 0, 0);
                px = x.getImageData(0, 0, c.width, c.height);
            }
            if ((img.currentSrc || img.src) !== src) return S.spec;
            S.spec = { data: px.data instanceof Uint8Array ? px.data : new Uint8Array(px.data.buffer), w: px.width, h: px.height, src };
            S.specSrc = src; S.specVer++; S.dirty = true;
            kick();
            return S.spec;
        })();
        S.specPending = { src, p };
        p.finally(function () { if (S.specPending && S.specPending.p === p) S.specPending = null; });
        return p;
    }

    function bindSources() {
        const p = paintImg(), s = specImg();
        if (p && !p.__spbRevLens) {
            p.__spbRevLens = 1;
            p.addEventListener('load', function () { S.paintVer++; S.dirty = true; kick(); });
        }
        if (s && !s.__spbRevLens) {
            s.__spbRevLens = 1;
            s.addEventListener('load', function () { loadSpec(true); });
        }
        if (p && p.complete && p.naturalWidth && !S.paintVer) S.paintVer = 1;
        if (s && s.complete && s.naturalWidth && !S.spec) loadSpec(false);
    }
    function ready() { const p = paintImg(); return !!(S.spec && p && p.complete && p.naturalWidth); }

    // ------------------------------------------------------------ GL view
    function View(canvas) {
        this.canvas = canvas;
        const gl = canvas.getContext('webgl2', { alpha: true, premultipliedAlpha: true, antialias: false, depth: false, stencil: false, preserveDrawingBuffer: false, powerPreference: 'high-performance' });
        this.gl = gl;
        if (!gl) return;
        const sh = function (type, src) {
            const o = gl.createShader(type); gl.shaderSource(o, src); gl.compileShader(o);
            if (!gl.getShaderParameter(o, gl.COMPILE_STATUS)) throw new Error('Shine Lens shader: ' + gl.getShaderInfoLog(o));
            return o;
        };
        const prog = gl.createProgram();
        gl.attachShader(prog, sh(gl.VERTEX_SHADER, C.VERT));
        gl.attachShader(prog, sh(gl.FRAGMENT_SHADER, C.FRAG));
        gl.bindAttribLocation(prog, 0, 'aPos');
        gl.linkProgram(prog);
        if (!gl.getProgramParameter(prog, gl.LINK_STATUS)) throw new Error('Shine Lens link: ' + gl.getProgramInfoLog(prog));
        this.prog = prog;
        this.u = {};
        ['uPaint', 'uSpec', 'uSel', 'uUvRect', 'uSize', 'uLight', 'uEnvRot', 'uCircle', 'uSelOn', 'uExposure', 'uCurv', 'uRing'].forEach(n => { this.u[n] = gl.getUniformLocation(prog, n); });
        this.vao = gl.createVertexArray();
        gl.bindVertexArray(this.vao);
        const vb = gl.createBuffer();
        gl.bindBuffer(gl.ARRAY_BUFFER, vb);
        gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1, -1, 3, -1, -1, 3]), gl.STATIC_DRAW);
        gl.enableVertexAttribArray(0);
        gl.vertexAttribPointer(0, 2, gl.FLOAT, false, 0, 0);
        this.tPaint = this.tex(); this.tSpec = this.tex(); this.tSel = this.tex();
        gl.bindTexture(gl.TEXTURE_2D, this.tSel);
        gl.texImage2D(gl.TEXTURE_2D, 0, gl.R8, 1, 1, 0, gl.RED, gl.UNSIGNED_BYTE, new Uint8Array([255]));
        this.vPaint = -1; this.vSpec = -1; this.vSel = -1;
        this.sizeP = [0, 0]; this.sizeS = [0, 0];
    }
    View.prototype.tex = function () {
        const gl = this.gl, t = gl.createTexture();
        gl.bindTexture(gl.TEXTURE_2D, t);
        gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR_MIPMAP_LINEAR);
        gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.LINEAR);
        gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE);
        gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
        return t;
    };
    View.prototype.sync = function () {
        const gl = this.gl;
        gl.pixelStorei(gl.UNPACK_COLORSPACE_CONVERSION_WEBGL, gl.NONE);
        gl.pixelStorei(gl.UNPACK_PREMULTIPLY_ALPHA_WEBGL, false);
        gl.pixelStorei(gl.UNPACK_FLIP_Y_WEBGL, false);
        if (this.vPaint !== S.paintVer) {
            const img = paintImg();
            if (img && img.complete && img.naturalWidth) {
                gl.bindTexture(gl.TEXTURE_2D, this.tPaint);
                gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA8, gl.RGBA, gl.UNSIGNED_BYTE, img);
                gl.generateMipmap(gl.TEXTURE_2D);
                this.sizeP = [img.naturalWidth, img.naturalHeight];
                this.vPaint = S.paintVer;
            }
        }
        if (this.vSpec !== S.specVer && S.spec) {
            gl.bindTexture(gl.TEXTURE_2D, this.tSpec);
            gl.pixelStorei(gl.UNPACK_ALIGNMENT, 4);
            gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA8, S.spec.w, S.spec.h, 0, gl.RGBA, gl.UNSIGNED_BYTE, S.spec.data);
            gl.generateMipmap(gl.TEXTURE_2D);
            this.sizeS = [S.spec.w, S.spec.h];
            this.vSpec = S.specVer;
        }
        if (this.vSel !== S.selVer) {
            gl.bindTexture(gl.TEXTURE_2D, this.tSel);
            gl.pixelStorei(gl.UNPACK_ALIGNMENT, 1);
            if (S.selMask) {
                gl.texImage2D(gl.TEXTURE_2D, 0, gl.R8, S.selW, S.selH, 0, gl.RED, gl.UNSIGNED_BYTE, S.selMask);
                gl.generateMipmap(gl.TEXTURE_2D);
            }
            gl.pixelStorei(gl.UNPACK_ALIGNMENT, 4);
            this.vSel = S.selVer;
        }
    };
    View.prototype.draw = function (o) {
        const gl = this.gl;
        if (!gl || gl.isContextLost()) return false;
        this.sync();
        const c = this.canvas;
        gl.viewport(0, 0, c.width, c.height);
        gl.clearColor(0, 0, 0, 0);
        gl.clear(gl.COLOR_BUFFER_BIT);
        gl.useProgram(this.prog);
        gl.bindVertexArray(this.vao);
        gl.activeTexture(gl.TEXTURE0); gl.bindTexture(gl.TEXTURE_2D, this.tPaint);
        gl.activeTexture(gl.TEXTURE1); gl.bindTexture(gl.TEXTURE_2D, this.tSpec);
        gl.activeTexture(gl.TEXTURE2); gl.bindTexture(gl.TEXTURE_2D, this.tSel);
        const u = this.u;
        gl.uniform1i(u.uPaint, 0); gl.uniform1i(u.uSpec, 1); gl.uniform1i(u.uSel, 2);
        gl.uniform4f(u.uUvRect, o.uv[0], o.uv[1], o.uv[2], o.uv[3]);
        gl.uniform2f(u.uSize, c.width, c.height);
        const ce = Math.cos(S.el);
        gl.uniform3f(u.uLight, ce * Math.cos(S.az), ce * Math.sin(S.az), Math.sin(S.el));
        gl.uniform1f(u.uEnvRot, S.az + 0.9);
        gl.uniform3f(u.uCircle, o.circle ? o.circle[0] : 0, o.circle ? o.circle[1] : 0, o.circle ? o.circle[2] : 0);
        gl.uniform1f(u.uSelOn, S.selMask && o.sel !== false ? 1 : 0);
        gl.uniform1f(u.uExposure, S.exposure);
        gl.uniform1f(u.uCurv, S.curv);
        gl.uniform1f(u.uRing, o.ring || 0);
        if (o.circle) {
            // Lens / peek: only shade the circle's box (+ its soft halo), not the whole canvas.
            const pad = o.circle[2] + 8 * (o.ring || 1) + 2;
            const x0 = Math.max(0, Math.floor(o.circle[0] - pad)), x1 = Math.min(c.width, Math.ceil(o.circle[0] + pad));
            const y0 = Math.max(0, Math.floor(o.circle[1] - pad)), y1 = Math.min(c.height, Math.ceil(o.circle[1] + pad));
            if (x1 <= x0 || y1 <= y0) return true;
            gl.enable(gl.SCISSOR_TEST);
            gl.scissor(x0, c.height - y1, x1 - x0, y1 - y0);
            gl.drawArrays(gl.TRIANGLES, 0, 3);
            gl.disable(gl.SCISSOR_TEST);
        } else {
            gl.drawArrays(gl.TRIANGLES, 0, 3);
        }
        return true;
    };

    // ------------------------------------------------------------ DOM: preview overlay
    let main = null, mainView = null, peekCv = null, peekView = null, bar = null;

    function contentRect(img) {
        if (!img || !img.naturalWidth) return null;
        const r = img.getBoundingClientRect();
        if (r.width < 4 || r.height < 4) return null;
        const s = Math.min(r.width / img.naturalWidth, r.height / img.naturalHeight);
        const w = img.naturalWidth * s, h = img.naturalHeight * s;
        return { left: r.left + (r.width - w) / 2, top: r.top + (r.height - h) / 2, width: w, height: h };
    }
    function host() { const p = paintImg(); return p ? (p.closest('.preview-inner') || p.parentElement) : null; }

    function ensureMain() {
        if (main && main.isConnected) return main;
        const h = host();
        if (!h) return null;
        main = document.createElement('canvas');
        main.id = 'spbShineCanvas';
        main.className = 'spb-shine-canvas';
        main.setAttribute('aria-hidden', 'true');
        h.appendChild(main);
        try { mainView = new View(main); } catch (e) { console.warn('[REV-LENS]', e); mainView = null; }
        if (!mainView || !mainView.gl) { main.remove(); main = null; toast('Shine Lens needs WebGL2'); return null; }
        main.addEventListener('webglcontextlost', function (e) { e.preventDefault(); });
        main.addEventListener('webglcontextrestored', function () { try { mainView = new View(main); S.dirty = true; kick(); } catch (_) { } });
        wireMainDrag(main);
        return main;
    }
    function ensurePeek() {
        if (peekCv && peekCv.isConnected) return peekCv;
        peekCv = document.createElement('canvas');
        peekCv.id = 'spbShinePeek';
        peekCv.className = 'spb-shine-peek';
        peekCv.setAttribute('aria-hidden', 'true');
        document.body.appendChild(peekCv);
        try { peekView = new View(peekCv); } catch (e) { console.warn('[REV-LENS]', e); peekView = null; }
        return peekCv;
    }

    function placeMain(cr) {
        const h = host();
        if (!main || !h || !cr) return null;
        const hr = h.getBoundingClientRect();
        const dpr = window.devicePixelRatio || 1;
        const L = Math.round(cr.left - hr.left + h.scrollLeft), T = Math.round(cr.top - hr.top + h.scrollTop);
        const W = Math.round(cr.width), H = Math.round(cr.height);
        const st = main.style;
        if (st.left !== L + 'px') st.left = L + 'px';
        if (st.top !== T + 'px') st.top = T + 'px';
        if (st.width !== W + 'px') st.width = W + 'px';
        if (st.height !== H + 'px') st.height = H + 'px';
        let bw = S.forceRes || Math.min(2048, Math.round(W * dpr)), bh = S.forceRes || Math.min(2048, Math.round(H * dpr));
        if (main.width !== bw) { main.width = bw; S.dirty = true; }
        if (main.height !== bh) { main.height = bh; S.dirty = true; }
        return { L, T, W, H, dpr };
    }

    // ------------------------------------------------------------ frame loop
    let lastRect = '';
    function kick() { if (!S.raf) S.raf = requestAnimationFrame(frame); }
    function wantLoop() { return S.mode !== 'off' || S.peek; }

    function frame(t) {
        S.raf = 0;
        if (!wantLoop()) { hideAll(); return; }
        const dt = S.lastT ? Math.min(0.1, (t - S.lastT) / 1000) : 0;
        S.lastT = t;
        if (S.mode === 'sweep') {
            S.az += dt * (Math.PI * 2 / 9);
            S.el = 0.62 + 0.26 * Math.sin(t / 1000 * 0.7);
            S.dirty = true;
            syncPuck();
        }
        bindSources();
        const img = paintImg();
        const cr = contentRect(img);
        const key = cr ? [cr.left, cr.top, cr.width, cr.height].map(Math.round).join(',') : 'none';
        if (key !== lastRect) { lastRect = key; S.dirty = true; }
        const t0 = performance.now();
        let drew = false;
        // preview overlay
        const showMain = ready() && cr && (S.mode === 'full' || S.mode === 'sweep' || ((S.mode === 'lens' || S.peek) && inRect(S.mouse, cr)));
        if (showMain && ensureMain()) {
            const g = placeMain(cr);
            if (S.dirty || S.mode === 'lens' || S.peek) {
                const lens = !(S.mode === 'full' || S.mode === 'sweep');
                const o = { uv: [0, 0, 1, 1] };
                if (lens) {
                    const sx = main.width / g.W, sy = main.height / g.H;
                    const r = Math.min(S.peek ? PEEK_R : LENS_R, 0.45 * Math.min(g.W, g.H));
                    o.circle = [(S.mouse.x - cr.left) * sx, (S.mouse.y - cr.top) * sy, r * sx];
                    o.ring = 1.5 * sx;
                }
                drew = mainView.draw(o) || drew;
            }
            if (main.style.display !== 'block') main.style.display = 'block';
            const isFull = S.mode === 'full' || S.mode === 'sweep';
            if (main.classList.contains('is-full') !== isFull) main.classList.toggle('is-full', isFull);
        } else if (main && main.style.display !== 'none') {
            main.style.display = 'none';
        }
        // source-canvas peek
        const pc = document.getElementById('paintCanvas');
        const prc = pc ? pc.getBoundingClientRect() : null;
        const showPeek = S.peek && ready() && prc && prc.width > 4 && inRect(S.mouse, prc) && !(cr && inRect(S.mouse, cr)) && topIsCanvas(S.mouse);
        if (showPeek && ensurePeek() && peekView && peekView.gl) {
            // The peek canvas sits STILL over the visible part of the source canvas; only the circle moves,
            // drawn by the shader. Moving a DOM element per mouse move would cost a full style recalc
            // (~50 ms on this page, see PROGRESS.md "fps"), so the box is only restyled when the view pans/zooms.
            const dpr = window.devicePixelRatio || 1;
            const vis = visibleRect(pc, prc);
            if (vis) {
                const key = [vis.left, vis.top, vis.width, vis.height].map(Math.round).join(',');
                if (key !== peekKey) {
                    peekKey = key;
                    const ps = peekCv.style;
                    ps.left = Math.round(vis.left) + 'px'; ps.top = Math.round(vis.top) + 'px';
                    ps.width = Math.round(vis.width) + 'px'; ps.height = Math.round(vis.height) + 'px';
                    peekCv.width = Math.min(4096, Math.round(vis.width * dpr)); peekCv.height = Math.min(4096, Math.round(vis.height * dpr));
                }
                const sx = peekCv.width / Math.round(vis.width), sy = peekCv.height / Math.round(vis.height);
                const uv = [(Math.round(vis.left) - prc.left) / prc.width, (Math.round(vis.top) - prc.top) / prc.height, Math.round(vis.width) / prc.width, Math.round(vis.height) / prc.height];
                drew = peekView.draw({ uv, circle: [(S.mouse.x - Math.round(vis.left)) * sx, (S.mouse.y - Math.round(vis.top)) * sy, PEEK_R * sx], ring: 1.5 * sx }) || drew;
                if (peekCv.style.display !== 'block') peekCv.style.display = 'block';
            }
        } else if (peekCv && peekCv.style.display !== 'none') {
            peekCv.style.display = 'none';
        }
        if (drew) { S.stats.frames++; S.stats.lastMs = performance.now() - t0; }
        S.dirty = false;
        updateBarState();
        if (S.mode === 'sweep' || S.benchOn) kick();
    }
    function inRect(m, r) { return m.x >= r.left && m.y >= r.top && m.x < r.left + r.width && m.y < r.top + r.height; }
    let peekKey = '', clipEl = null, clipFor = null;
    function visibleRect(pc, prc) {
        // the source canvas clipped by its scrolling viewport and by the window
        if (clipFor !== pc || !clipEl || !clipEl.isConnected) {
            clipFor = pc; clipEl = null;
            for (let e = pc.parentElement; e && e !== document.body; e = e.parentElement) {
                const cs = getComputedStyle(e);
                if (cs.overflowX !== 'visible' || cs.overflowY !== 'visible') { clipEl = e; break; }
            }
        }
        let L = prc.left, T = prc.top, R = prc.left + prc.width, B = prc.top + prc.height;
        if (clipEl) { const k = clipEl.getBoundingClientRect(); L = Math.max(L, k.left); T = Math.max(T, k.top); R = Math.min(R, k.right); B = Math.min(B, k.bottom); }
        L = Math.max(L, 0); T = Math.max(T, 0); R = Math.min(R, window.innerWidth); B = Math.min(B, window.innerHeight);
        return (R - L > 4 && B - T > 4) ? { left: L, top: T, width: R - L, height: B - T } : null;
    }
    function topIsCanvas(m) {
        const e = document.elementFromPoint(m.x, m.y);
        if (!e) return false;
        if (e.id === 'spbShinePeek') return true;
        return !!e.closest('#canvasInner, #canvasViewport, .canvas-inner') || e.id === 'paintCanvas' || e.tagName === 'CANVAS';
    }
    function hideAll() {
        if (main && main.style.display !== 'none') main.style.display = 'none';
        if (peekCv && peekCv.style.display !== 'none') peekCv.style.display = 'none';
        updateBarState();
    }

    // ------------------------------------------------------------ input
    window.addEventListener('pointermove', function (e) {
        S.mouse.x = e.clientX; S.mouse.y = e.clientY;
        if (S.mode === 'lens' || S.peek) kick();
    }, { passive: true, capture: true });
    function isTyping(e) {
        const t = e.target;
        return !!(t && (t.isContentEditable || /^(INPUT|TEXTAREA|SELECT)$/.test(t.tagName)));
    }
    document.addEventListener('keydown', function (e) {
        if (e.code !== 'Backquote' || e.ctrlKey || e.metaKey || e.altKey || isTyping(e)) return;
        e.preventDefault();
        if (e.repeat || S.peek) return;
        bindSources();
        if (!ready()) { toast('Shine Lens: waiting for the Live Preview'); return; }
        S.peek = true; S.dirty = true; kick();
    }, true);
    document.addEventListener('keyup', function (e) {
        if (e.code !== 'Backquote') return;
        if (S.peek) { S.peek = false; S.dirty = true; kick(); }
    }, true);
    window.addEventListener('blur', function () { if (S.peek) { S.peek = false; kick(); } });
    window.addEventListener('resize', function () { S.dirty = true; if (wantLoop()) kick(); });

    // drag on the shaded preview (Full / Sweep) moves the light; a plain click still opens the big view
    function wireMainDrag(cv) {
        let d = null;
        cv.addEventListener('pointerdown', function (e) {
            if (e.button !== 0) return;
            d = { x: e.clientX, y: e.clientY, az: S.az, el: S.el, moved: false, id: e.pointerId };
            try { cv.setPointerCapture(e.pointerId); } catch (_) { }
            e.preventDefault();
        });
        cv.addEventListener('pointermove', function (e) {
            if (!d) return;
            const dx = e.clientX - d.x, dy = e.clientY - d.y;
            if (!d.moved && Math.hypot(dx, dy) < 4) return;
            d.moved = true;
            if (S.mode === 'sweep') setMode('full');
            setLight(d.az + dx * 0.012, d.el - dy * 0.008);
        });
        const end = function () {
            if (!d) return;
            const click = !d.moved;
            d = null;
            const picking = window.SPBRevMaterialSelect && window.SPBRevMaterialSelect.isOpen && window.SPBRevMaterialSelect.isOpen();
            if (click && !picking && typeof window.openPreviewLightbox === 'function') window.openPreviewLightbox('paint');
        };
        cv.addEventListener('pointerup', end);
        cv.addEventListener('pointercancel', function () { d = null; });
    }

    // ------------------------------------------------------------ bar UI
    const ICO = {
        shine: '<svg viewBox="0 0 16 16" aria-hidden="true"><path d="M8 1.5v3M8 11.5v3M1.5 8h3M11.5 8h3M3.4 3.4l2.1 2.1M10.5 10.5l2.1 2.1M12.6 3.4l-2.1 2.1M5.5 10.5l-2.1 2.1"/></svg>',
        lens: '<svg viewBox="0 0 16 16" aria-hidden="true"><circle cx="7" cy="7" r="4.5"/><path d="M10.4 10.4L14 14"/></svg>',
        full: '<svg viewBox="0 0 16 16" aria-hidden="true"><rect x="2" y="2.5" width="12" height="11" rx="1.5"/><path d="M4.5 10.5l3-4 2 2.5 1.5-1.5"/></svg>',
        sweep: '<svg viewBox="0 0 16 16" aria-hidden="true"><path d="M13.5 8a5.5 5.5 0 1 1-1.6-3.9"/><path d="M12.2 1.8v2.6H9.6"/></svg>',
        off: '<svg viewBox="0 0 16 16" aria-hidden="true"><circle cx="8" cy="8" r="5.5"/><path d="M4.2 11.8l7.6-7.6"/></svg>',
    };
    function ensureBar() {
        if (bar && bar.isConnected) return bar;
        const h = host();
        if (!h) return null;
        bar = document.createElement('div');
        bar.id = 'spbShineBar';
        bar.className = 'spb-shine-bar';
        bar.setAttribute('role', 'toolbar');
        bar.setAttribute('aria-label', 'Shine Lens');
        bar.innerHTML =
            '<span class="spb-shine-ttl" title="Shine Lens: see chrome, satin, matte, candy and carbon under a studio light, live, before you render. Hold ` over the car to peek with any tool.">' + ICO.shine + '<span>Shine</span></span>' +
            '<button type="button" data-m="off" aria-label="Shine Off" title="Shine off: the normal flat preview">' + ICO.off + '<span>Off</span></button>' +
            '<button type="button" data-m="lens" aria-label="Shine Lens" title="Lens: a shine circle under your cursor on the Live Preview">' + ICO.lens + '<span>Lens</span></button>' +
            '<button type="button" data-m="full" aria-label="Shine Full" title="Full: the whole preview under a studio light. Drag on the car to move the light">' + ICO.full + '<span>Full</span></button>' +
            '<button type="button" data-m="sweep" aria-label="Shine Sweep" title="Sweep: the light circles the car so flakes, candy and chrome pop">' + ICO.sweep + '<span>Sweep</span></button>' +
            '<span class="spb-shine-puck" role="slider" tabindex="0" aria-label="Light direction" title="Drag to move the light. Arrow keys nudge it."><canvas width="40" height="40" aria-hidden="true"></canvas></span>';
        h.appendChild(bar);
        // narrow preview pane (e.g. 1100 px window): icons only, so the bar never spills over the panel next to it
        fitBar();
        try { new ResizeObserver(fitBar).observe(h); } catch (_) { window.addEventListener('resize', fitBar); }
        bar.addEventListener('click', function (e) {
            const b = e.target.closest('button[data-m]');
            if (b) setMode(b.dataset.m);
        });
        bar.addEventListener('mousedown', function (e) { e.stopPropagation(); });
        const puck = bar.querySelector('.spb-shine-puck');
        let pd = null;
        puck.addEventListener('pointerdown', function (e) {
            pd = { x: e.clientX, y: e.clientY, az: S.az, el: S.el };
            try { puck.setPointerCapture(e.pointerId); } catch (_) { }
            e.preventDefault(); e.stopPropagation();
            if (S.mode === 'off') setMode('full');
            if (S.mode === 'sweep') setMode('full');
        });
        puck.addEventListener('pointermove', function (e) {
            if (!pd) return;
            setLight(pd.az + (e.clientX - pd.x) * 0.03, pd.el - (e.clientY - pd.y) * 0.02);
        });
        puck.addEventListener('pointerup', function () { pd = null; });
        puck.addEventListener('pointercancel', function () { pd = null; });
        puck.addEventListener('keydown', function (e) {
            const k = { ArrowLeft: [-0.15, 0], ArrowRight: [0.15, 0], ArrowUp: [0, 0.08], ArrowDown: [0, -0.08] }[e.key];
            if (!k) return;
            e.preventDefault(); e.stopPropagation();
            if (S.mode === 'off') setMode('full');
            setLight(S.az + k[0], S.el + k[1]);
        });
        syncPuck();
        updateBarState();
        return bar;
    }
    function fitBar() {
        if (!bar) return;
        const h = host();
        if (!h) return;
        const want = h.clientWidth < 380, tiny = h.clientWidth < 200;
        if (bar.classList.contains('compact') !== want) bar.classList.toggle('compact', want);
        if (bar.classList.contains('tiny') !== tiny) bar.classList.toggle('tiny', tiny);
    }
    function syncPuck() {
        if (!bar) return;
        // Drawn into a tiny canvas, not moved with CSS: an inline-style write costs a whole-page
        // style recalc here (~50 ms), which would cap Sweep at ~15 fps.
        const cv = bar.querySelector('.spb-shine-puck canvas');
        if (!cv) return;
        const x = cv.getContext('2d'), n = cv.width, k = n / 20;
        const r = 6 * Math.cos(S.el) / Math.cos(0.15);
        const cx = n / 2 + Math.cos(S.az) * r * k, cy = n / 2 - Math.sin(S.az) * r * k;
        x.clearRect(0, 0, n, n);
        const g = x.createRadialGradient(cx, cy, 0, cx, cy, 6 * k);
        g.addColorStop(0, 'rgba(255,255,255,0.85)'); g.addColorStop(1, 'rgba(255,255,255,0)');
        x.fillStyle = g; x.beginPath(); x.arc(cx, cy, 6 * k, 0, Math.PI * 2); x.fill();
        x.fillStyle = '#f4f4f6'; x.beginPath(); x.arc(cx, cy, 3 * k, 0, Math.PI * 2); x.fill();
    }
    let lastBar = '';
    function updateBarState() {
        if (!bar) return;
        const st = S.mode + (ready() ? '1' : '0');
        if (st === lastBar) return;
        lastBar = st;
        bar.querySelectorAll('button[data-m]').forEach(function (b) {
            const on = b.dataset.m === S.mode;
            b.classList.toggle('on', on);
            b.setAttribute('aria-pressed', on ? 'true' : 'false');
        });
        bar.classList.toggle('waiting', !ready());
    }

    // ------------------------------------------------------------ API
    function setMode(m) {
        if (['off', 'lens', 'full', 'sweep'].indexOf(m) < 0) return S.mode;
        S.mode = m; S.dirty = true; S.lastT = 0;
        bindSources();
        if (m !== 'off' && !ready()) toast('Shine Lens: waiting for the Live Preview to finish');
        ensureBar(); updateBarState();
        kick();
        return S.mode;
    }
    function setLight(az, el) {
        S.az = az; S.el = Math.max(0.08, Math.min(1.5, el)); S.dirty = true;
        syncPuck(); kick();
    }
    function setSelectionMask(mask, w, h) {
        S.selMask = mask || null; S.selW = w || 0; S.selH = h || 0; S.selVer++; S.dirty = true; kick();
    }
    function patch(which, x, y, w, h, rgba) {
        [mainView, peekView].forEach(function (v) {
            if (!v || !v.gl) return;
            v.sync();
            const gl = v.gl;
            gl.bindTexture(gl.TEXTURE_2D, which === 'spec' ? v.tSpec : v.tPaint);
            gl.pixelStorei(gl.UNPACK_ALIGNMENT, 4);
            gl.texSubImage2D(gl.TEXTURE_2D, 0, x, y, w, h, gl.RGBA, gl.UNSIGNED_BYTE, rgba);
            gl.generateMipmap(gl.TEXTURE_2D);
        });
        S.dirty = true; kick();
    }
    function toast(msg) { if (typeof window.showToast === 'function') window.showToast(msg, 'info'); }

    // Bench: continuous Full renders for N frames. size forces the backing store
    // (2048 = the whole UV sheet at full res). Reports rAF fps and GPU ms (gl.finish).
    function bench(opts) {
        opts = opts || {};
        const frames = opts.frames || 240, size = opts.size || 0;
        const rafRate = function (n) {   // page rAF ceiling with the lens OFF (same page, same moment)
            return new Promise(function (res) {
                const ts = [];
                const f = function (t) { ts.push(t); if (ts.length < n) requestAnimationFrame(f); else { const d = []; for (let i = 6; i < ts.length; i++) d.push(ts[i] - ts[i - 1]); res(+(1000 / (d.reduce(function (a, b) { return a + b; }, 0) / d.length)).toFixed(1)); } };
                requestAnimationFrame(f);
            });
        };
        const prevMode0 = S.mode;
        setMode('off');
        return rafRate(Math.min(frames, 120)).then(function (base) { return new Promise(function (resolve) {
            const prevMode = prevMode0, prevForce = S.forceRes;
            S.forceRes = size; setMode(opts.mode || 'sweep');
            const ts = [];
            let n = 0;
            S.benchOn = true;
            const tick = function (t) {
                ts.push(t);
                if (++n < frames + 10) { requestAnimationFrame(tick); return; }
                S.benchOn = false;
                // GPU throughput: 5 batches of 40 back-to-back full draws, each batch
                // closed by a 1-pixel readPixels (forces the GPU to finish the batch).
                const gpu = [];
                if (mainView && mainView.gl && ready()) {
                    const gl = mainView.gl, one = new Uint8Array(4);
                    mainView.draw({ uv: [0, 0, 1, 1] }); gl.readPixels(0, 0, 1, 1, gl.RGBA, gl.UNSIGNED_BYTE, one);
                    for (let b = 0; b < 5; b++) {
                        const t0 = performance.now();
                        for (let i = 0; i < 40; i++) { S.az += 0.01; mainView.draw({ uv: [0, 0, 1, 1] }); }
                        gl.readPixels(0, 0, 1, 1, gl.RGBA, gl.UNSIGNED_BYTE, one);
                        gpu.push((performance.now() - t0) / 40);
                    }
                }
                const d = []; for (let i = 11; i < ts.length; i++) d.push(ts[i] - ts[i - 1]);
                d.sort(function (a, b) { return a - b; }); gpu.sort(function (a, b) { return a - b; });
                const mean = d.reduce(function (a, b) { return a + b; }, 0) / d.length;
                const out = {
                    backing: main ? [main.width, main.height] : null, tex: { paint: mainView ? mainView.sizeP : null, spec: mainView ? mainView.sizeS : null },
                    page_raf_fps_lens_off: base, frames: d.length, fps: +(1000 / mean).toFixed(1), p50ms: +d[d.length >> 1].toFixed(2), p95ms: +d[Math.floor(d.length * 0.95)].toFixed(2),
                    gpu_ms_per_frame: gpu.length ? +gpu[gpu.length >> 1].toFixed(3) : null, gpu_ms_worst_batch: gpu.length ? +gpu[gpu.length - 1].toFixed(3) : null,
                    gpu_fps_capacity: gpu.length ? Math.round(1000 / gpu[gpu.length >> 1]) : null,
                };
                S.forceRes = prevForce; setMode(prevMode);
                resolve(out);
            };
            requestAnimationFrame(tick);
        }); });
    }

    // Test hook: shade arbitrary paint/spec arrays (w x h) offscreen and read pixels back.
    function testRender(o) {
        const cv = document.createElement('canvas');
        cv.width = o.outW || o.w; cv.height = o.outH || o.h;
        const v = new View(cv);
        const gl = v.gl;
        gl.bindTexture(gl.TEXTURE_2D, v.tPaint);
        gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA8, o.w, o.h, 0, gl.RGBA, gl.UNSIGNED_BYTE, o.paint);
        gl.generateMipmap(gl.TEXTURE_2D);
        gl.bindTexture(gl.TEXTURE_2D, v.tSpec);
        gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA8, o.w, o.h, 0, gl.RGBA, gl.UNSIGNED_BYTE, o.spec);
        gl.generateMipmap(gl.TEXTURE_2D);
        v.vPaint = S.paintVer; v.vSpec = S.specVer; v.vSel = S.selVer;
        const keep = [S.az, S.el];
        if (o.az != null) S.az = o.az;
        if (o.el != null) S.el = o.el;
        v.draw({ uv: o.uv || [0, 0, 1, 1], sel: false });
        S.az = keep[0]; S.el = keep[1];
        const px = new Uint8Array(cv.width * cv.height * 4);
        gl.readPixels(0, 0, cv.width, cv.height, gl.RGBA, gl.UNSIGNED_BYTE, px);
        const ext = gl.getExtension('WEBGL_lose_context'); if (ext) ext.loseContext();
        return { w: cv.width, h: cv.height, px };   // NB: rows bottom-up (GL order)
    }

    // Test / proof hook: shade the LIVE paint + spec (same View.draw as the overlay)
    // over a sheet crop into an offscreen canvas; also returns the flat paint crop.
    function renderLive(o) {
        if (!ready()) return null;
        const cv = document.createElement('canvas');
        cv.width = o.outW; cv.height = o.outH;
        const v = new View(cv);
        const keep = [S.az, S.el];
        if (o.az != null) S.az = o.az;
        if (o.el != null) S.el = o.el;
        v.draw({ uv: o.uv, sel: !!o.sel });
        S.az = keep[0]; S.el = keep[1];
        const gl = v.gl, w = cv.width, h = cv.height;
        const px = new Uint8Array(w * h * 4);
        gl.readPixels(0, 0, w, h, gl.RGBA, gl.UNSIGNED_BYTE, px);
        const ext = gl.getExtension('WEBGL_lose_context'); if (ext) ext.loseContext();
        const c2 = document.createElement('canvas'); c2.width = w; c2.height = h;
        const x2 = c2.getContext('2d');
        const id = x2.createImageData(w, h);
        for (let y = 0; y < h; y++) id.data.set(px.subarray((h - 1 - y) * w * 4, (h - y) * w * 4), y * w * 4);
        x2.putImageData(id, 0, 0);
        const lensUrl = c2.toDataURL('image/png');
        const img = paintImg();
        x2.imageSmoothingEnabled = true; x2.imageSmoothingQuality = 'high';
        x2.clearRect(0, 0, w, h);
        x2.drawImage(img, o.uv[0] * img.naturalWidth, o.uv[1] * img.naturalHeight, o.uv[2] * img.naturalWidth, o.uv[3] * img.naturalHeight, 0, 0, w, h);
        return { lens: lensUrl, paint: c2.toDataURL('image/png') };
    }

    window.SPBRevLens = {
        version: C.version,
        setMode, getMode: function () { return S.mode; },
        setLight, getLight: function () { return { az: S.az, el: S.el }; },
        peek: function (on) { S.peek = !!on; S.dirty = true; kick(); },
        refresh: function () { S.paintVer++; loadSpec(true); S.dirty = true; kick(); },
        getSpec: function () { bindSources(); return loadSpec(false); },
        setSelectionMask,
        patchSpec: function (x, y, w, h, rgba) { patch('spec', x, y, w, h, rgba); },
        patchPaint: function (x, y, w, h, rgba) { patch('paint', x, y, w, h, rgba); },
        bench,
        _test: { render: testRender, renderLive, state: S, contentRect: function () { return contentRect(paintImg()); } },
    };

    function boot() {
        bindSources();
        ensureBar();
        // the preview pane is rebuilt rarely; re-attach if a re-layout dropped our nodes
        setInterval(function () { if (!bar || !bar.isConnected) { bar = null; ensureBar(); } bindSources(); }, 2000);
    }
    if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot);
    else boot();
})();
