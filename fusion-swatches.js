// ============================================================
// FUSION SWATCH RENDERERS — 150 procedural canvas previews
// Injected into MONO_PREVIEW_CANVAS after DOM load
// ============================================================
(function () {
    'use strict';
    // Wait for main app to define the renderers object
    function _rng(s) { return function () { s = (s * 16807 + 0) % 2147483647; return (s - 1) / 2147483646; }; }
    function _noise2d(w, h, sc, seed) {
        const r = _rng(seed), out = new Float32Array(w * h);
        const grid = Math.ceil(Math.max(w, h) / sc) + 2;
        const g = []; for (let i = 0; i < grid * grid; i++) g.push(r() * 6.28);
        for (let py = 0; py < h; py++) for (let px = 0; px < w; px++) {
            const fx = px / sc, fy = py / sc;
            const ix = Math.floor(fx), iy = Math.floor(fy);
            const dx = fx - ix, dy = fy - iy;
            const sx = dx * dx * (3 - 2 * dx), sy = dy * dy * (3 - 2 * dy);
            const i00 = (iy * grid + ix) % g.length, i10 = (iy * grid + ix + 1) % g.length;
            const i01 = ((iy + 1) * grid + ix) % g.length, i11 = ((iy + 1) * grid + ix + 1) % g.length;
            const d00 = Math.cos(g[i00]) * dx + Math.sin(g[i00]) * dy;
            const d10 = Math.cos(g[i10]) * (dx - 1) + Math.sin(g[i10]) * dy;
            const d01 = Math.cos(g[i01]) * dx + Math.sin(g[i01]) * (dy - 1);
            const d11 = Math.cos(g[i11]) * (dx - 1) + Math.sin(g[i11]) * (dy - 1);
            out[py * w + px] = (d00 * (1 - sx) + d10 * sx) * (1 - sy) + (d01 * (1 - sx) + d11 * sx) * sy;
        }
        return out;
    }
    function _hsl(h, s, l) {
        h = ((h % 360) + 360) % 360; s /= 100; l /= 100;
        const c = (1 - Math.abs(2 * l - 1)) * s, x = c * (1 - Math.abs((h / 60) % 2 - 1)), m = l - c / 2;
        let r, g, b;
        if (h < 60) { r = c; g = x; b = 0; } else if (h < 120) { r = x; g = c; b = 0; }
        else if (h < 180) { r = 0; g = c; b = x; } else if (h < 240) { r = 0; g = x; b = c; }
        else if (h < 300) { r = x; g = 0; b = c; } else { r = c; g = 0; b = x; }
        return [Math.round((r + m) * 255), Math.round((g + m) * 255), Math.round((b + m) * 255)];
    }

    const R = {};

    // ===== P1: MATERIAL GRADIENTS (10) =====
    function _gradFusion(seed, c1, c2, dir) {
        return (ctx, w, h) => {
            const g = dir === 'r' ? ctx.createRadialGradient(w / 2, h / 2, 0, w / 2, h / 2, w * 0.7)
                : dir === 'd' ? ctx.createLinearGradient(0, 0, w, h)
                    : dir === 'h' ? ctx.createLinearGradient(0, 0, w, 0)
                        : ctx.createLinearGradient(0, 0, 0, h);
            g.addColorStop(0, c1); g.addColorStop(1, c2);
            ctx.fillStyle = g; ctx.fillRect(0, 0, w, h);
            // Add noise texture
            const n = _noise2d(w, h, 12, seed);
            const id = ctx.getImageData(0, 0, w, h);
            for (let i = 0; i < w * h; i++) { const v = n[i] * 15; id.data[i * 4] += v; id.data[i * 4 + 1] += v; id.data[i * 4 + 2] += v; }
            ctx.putImageData(id, 0, 0);
        };
    }
    R.gradient_chrome_matte = _gradFusion(9001, '#dde8f0', '#3a3a3a', 'v');
    R.gradient_candy_frozen = _gradFusion(9002, '#cc4488', '#aaccee', 'v');
    R.gradient_pearl_chrome = _gradFusion(9003, '#ddd8cc', '#c0d0e0', 'd');
    R.gradient_metallic_satin = _gradFusion(9004, '#b0b8c8', '#707878', 'h');
    R.gradient_obsidian_mirror = _gradFusion(9005, '#0a0a12', '#c8d8e8', 'r');
    R.gradient_candy_matte = _gradFusion(9006, '#bb4488', '#444444', 'v');
    R.gradient_anodized_gloss = _gradFusion(9007, '#6688aa', '#dde8f0', 'd');
    R.gradient_ember_ice = _gradFusion(9008, '#cc4400', '#88ccee', 'v');
    R.gradient_carbon_chrome = _gradFusion(9009, '#222222', '#c0d0e0', 'v');
    R.gradient_spectraflame_void = _gradFusion(9010, '#cc44ee', '#080808', 'r');

    // ===== P2: GHOST GEOMETRY (10) =====
    function _ghostFusion(seed, patternFn) {
        return (ctx, w, h) => {
            // Metallic base
            const bg = ctx.createLinearGradient(0, 0, w, h);
            bg.addColorStop(0, '#8898a8'); bg.addColorStop(0.5, '#a0b0c0'); bg.addColorStop(1, '#90a0b0');
            ctx.fillStyle = bg; ctx.fillRect(0, 0, w, h);
            ctx.globalAlpha = 0.18;
            patternFn(ctx, w, h, seed);
            ctx.globalAlpha = 1.0;
        };
    }
    R.ghost_hex = _ghostFusion(9100, (ctx, w, h) => { ctx.strokeStyle = '#c0d0e0'; ctx.lineWidth = 1; const s = Math.max(6, w / 5); for (let r = -1; r < h / s + 2; r++) for (let c = -1; c < w / s + 2; c++) { const cx = c * s * 1.5 + (r % 2) * s * 0.75, cy = r * s * 0.87; ctx.beginPath(); for (let i = 0; i < 6; i++) { const a = Math.PI / 3 * i - Math.PI / 6; i === 0 ? ctx.moveTo(cx + Math.cos(a) * s / 2, cy + Math.sin(a) * s / 2) : ctx.lineTo(cx + Math.cos(a) * s / 2, cy + Math.sin(a) * s / 2); } ctx.closePath(); ctx.stroke(); } });
    R.ghost_stripes = _ghostFusion(9101, (ctx, w, h) => { ctx.fillStyle = '#c0d0e0'; for (let i = 0; i < 5; i++) ctx.fillRect(w * 0.1 + i * w * 0.18, 0, w * 0.06, h); });
    R.ghost_diamonds = _ghostFusion(9102, (ctx, w, h) => { ctx.fillStyle = '#c0d0e0'; const s = Math.max(8, w / 4); for (let r = 0; r < h / s + 1; r++) for (let c = 0; c < w / s + 1; c++) { const cx = c * s + s / 2, cy = r * s + s / 2; ctx.beginPath(); ctx.moveTo(cx, cy - s / 2); ctx.lineTo(cx + s / 2, cy); ctx.lineTo(cx, cy + s / 2); ctx.lineTo(cx - s / 2, cy); ctx.fill(); } });
    R.ghost_waves = _ghostFusion(9103, (ctx, w, h) => { ctx.strokeStyle = '#c0d0e0'; ctx.lineWidth = 2; for (let i = 0; i < 8; i++) { ctx.beginPath(); for (let x = 0; x < w; x++) { const y = h / 2 + Math.sin(x * 0.1 + i * 0.8) * h * 0.12 + i * h * 0.08 - h * 0.3; x === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y); } ctx.stroke(); } });
    R.ghost_camo = _ghostFusion(9104, (ctx, w, h, sd) => { const r = _rng(sd); ctx.fillStyle = '#b0c0d0'; for (let i = 0; i < 15; i++) { const x = r() * w, y = r() * h, s = w * 0.15 + r() * w * 0.15; ctx.beginPath(); ctx.ellipse(x, y, s, s * 0.6, r() * 3.14, 0, 6.28); ctx.fill(); } });
    R.ghost_scales = _ghostFusion(9105, (ctx, w, h) => { ctx.strokeStyle = '#c0d0e0'; ctx.lineWidth = 1; const s = Math.max(6, w / 6); for (let r = 0; r < h / s + 1; r++) for (let c = 0; c < w / s + 1; c++) { ctx.beginPath(); ctx.arc(c * s + (r % 2) * s / 2, r * s * 0.75, s / 2, Math.PI, 0); ctx.stroke(); } });
    R.ghost_circuit = _ghostFusion(9106, (ctx, w, h, sd) => { const r = _rng(sd); ctx.strokeStyle = '#b0c8d8'; ctx.lineWidth = 1.5; for (let i = 0; i < 12; i++) { ctx.beginPath(); let x = r() * w, y = r() * h; ctx.moveTo(x, y); for (let s = 0; s < 5; s++) { r() > 0.5 ? x += r() * w * 0.2 : y += r() * h * 0.2; ctx.lineTo(x, y); } ctx.stroke(); } });
    R.ghost_vortex = _ghostFusion(9107, (ctx, w, h) => { ctx.strokeStyle = '#b0c0d0'; ctx.lineWidth = 1; const cx = w / 2, cy = h / 2; for (let a = 0; a < 20; a += 0.3) { const r = a * w * 0.025; ctx.beginPath(); ctx.arc(cx + Math.cos(a) * r, cy + Math.sin(a) * r, 2, 0, 6.28); ctx.stroke(); } });
    R.ghost_fracture = _ghostFusion(9108, (ctx, w, h, sd) => { const r = _rng(sd); ctx.strokeStyle = '#c0d0e0'; ctx.lineWidth = 1; for (let i = 0; i < 10; i++) { ctx.beginPath(); let x = r() * w, y = r() * h; ctx.moveTo(x, y); for (let s = 0; s < 4; s++) { x += (r() - 0.5) * w * 0.3; y += (r() - 0.5) * h * 0.3; ctx.lineTo(x, y); } ctx.stroke(); } });
    R.ghost_quilt = _ghostFusion(9109, (ctx, w, h) => { ctx.strokeStyle = '#b0c0d0'; ctx.lineWidth = 0.8; const s = Math.max(5, w / 6); for (let y = 0; y <= h; y += s) { ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(w, y); ctx.stroke(); } for (let x = 0; x <= w; x += s) { ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, h); ctx.stroke(); } });

    // ===== P3: DIRECTIONAL GRAIN (10) =====
    function _anisoFusion(seed, grainFn) {
        return (ctx, w, h) => {
            const bg = ctx.createLinearGradient(0, 0, w, h);
            bg.addColorStop(0, '#b8c4d4'); bg.addColorStop(1, '#98a8b8');
            ctx.fillStyle = bg; ctx.fillRect(0, 0, w, h);
            const id = ctx.getImageData(0, 0, w, h); const r = _rng(seed);
            for (let py = 0; py < h; py++) for (let px = 0; px < w; px++) {
                const v = grainFn(px, py, w, h, r) * 40 - 20;
                const i = (py * w + px) * 4; id.data[i] += v; id.data[i + 1] += v; id.data[i + 2] += v;
            }
            ctx.putImageData(id, 0, 0);
        };
    }
    R.aniso_horizontal_chrome = _anisoFusion(9200, (x, y, w, h, r) => r() * Math.abs(Math.sin(y * 0.5)));
    R.aniso_vertical_pearl = _anisoFusion(9201, (x, y, w, h, r) => r() * Math.abs(Math.sin(x * 0.5)));
    R.aniso_diagonal_candy = _anisoFusion(9202, (x, y, w, h, r) => r() * Math.abs(Math.sin((x + y) * 0.35)));
    R.aniso_radial_metallic = _anisoFusion(9203, (x, y, w, h, r) => { const a = Math.atan2(y - h / 2, x - w / 2); return r() * Math.abs(Math.sin(a * 4)); });
    R.aniso_circular_chrome = _anisoFusion(9204, (x, y, w, h, r) => { const d = Math.sqrt((x - w / 2) ** 2 + (y - h / 2) ** 2); return r() * Math.abs(Math.sin(d * 0.3)); });
    R.aniso_crosshatch_steel = _anisoFusion(9205, (x, y, w, h, r) => r() * (Math.abs(Math.sin((x + y) * 0.4)) + Math.abs(Math.sin((x - y) * 0.4))) * 0.5);
    R.aniso_spiral_mercury = _anisoFusion(9206, (x, y, w, h, r) => { const a = Math.atan2(y - h / 2, x - w / 2), d = Math.sqrt((x - w / 2) ** 2 + (y - h / 2) ** 2); return r() * Math.abs(Math.sin(a * 3 + d * 0.15)); });
    R.aniso_wave_titanium = _anisoFusion(9207, (x, y, w, h, r) => r() * Math.abs(Math.sin(y * 0.3 + Math.sin(x * 0.08) * 5)));
    R.aniso_herringbone_gold = _anisoFusion(9208, (x, y, w, h, r) => { const s = 12; return r() * ((Math.floor(y / s) % 2 === 0) ? Math.abs(Math.sin((x + y) * 0.5)) : Math.abs(Math.sin((x - y) * 0.5))); });
    R.aniso_turbulence_metal = _anisoFusion(9209, (x, y, w, h, r) => r() * Math.abs(Math.sin(x * 0.2 + Math.sin(y * 0.15) * 3)) * Math.abs(Math.cos(y * 0.18)));

    // ===== P4: REACTIVE PANELS (10) =====
    function _reactiveFusion(seed, mLo, mHi, cLo, cHi) {
        return (ctx, w, h) => {
            const n = _noise2d(w, h, 16, seed); const id = ctx.createImageData(w, h);
            for (let i = 0; i < w * h; i++) {
                const t = (n[i] + 0.5); const m = t > 0.5;
                const r = m ? mHi[0] : mLo[0], g = m ? mHi[1] : mLo[1], b = m ? mHi[2] : mLo[2];
                id.data[i * 4] = r; id.data[i * 4 + 1] = g; id.data[i * 4 + 2] = b; id.data[i * 4 + 3] = 255;
            }
            ctx.putImageData(id, 0, 0);
            // Edge glow
            ctx.strokeStyle = `rgba(${cHi},0.15)`; ctx.lineWidth = 1;
            for (let y = 1; y < h - 1; y += 2) for (let x = 1; x < w - 1; x += 2) {
                if (Math.abs(n[y * w + x]) < 0.05) { ctx.beginPath(); ctx.arc(x, y, 1, 0, 6.28); ctx.stroke(); }
            }
        };
    }
    R.reactive_stealth_pop = _reactiveFusion(9300, [40, 42, 48], [180, 190, 210], '200,210,230');
    R.reactive_pearl_flash = _reactiveFusion(9301, [140, 135, 150], [210, 215, 225], '230,235,245');
    R.reactive_candy_reveal = _reactiveFusion(9302, [160, 80, 100], [200, 210, 225], '220,225,240');
    R.reactive_chrome_fade = _reactiveFusion(9303, [180, 190, 205], [110, 115, 120], '200,205,215');
    R.reactive_matte_shine = _reactiveFusion(9304, [60, 62, 65], [190, 200, 215], '210,220,235');
    R.reactive_dual_tone = _reactiveFusion(9305, [100, 108, 120], [170, 180, 195], '190,200,215');
    R.reactive_ghost_metal = _reactiveFusion(9306, [50, 55, 60], [180, 185, 200], '200,205,220');
    R.reactive_mirror_shadow = _reactiveFusion(9307, [30, 32, 35], [200, 210, 225], '220,230,245');
    R.reactive_warm_cold = _reactiveFusion(9308, [160, 120, 90], [100, 130, 170], '140,160,190');
    R.reactive_pulse_metal = _reactiveFusion(9309, [40, 50, 80], [180, 190, 220], '200,210,240');

    // ===== P5: SPARKLE SYSTEMS (10) =====
    function _sparkleFusion(seed, bg, sparkClr, density, sparkSize) {
        return (ctx, w, h) => {
            ctx.fillStyle = bg; ctx.fillRect(0, 0, w, h);
            const r = _rng(seed);
            for (let i = 0; i < Math.floor(w * h * density); i++) {
                const x = r() * w, y = r() * h, s = sparkSize * (0.5 + r());
                const rg = ctx.createRadialGradient(x, y, 0, x, y, s);
                rg.addColorStop(0, sparkClr); rg.addColorStop(0.4, sparkClr.replace('1)', '0.4)'));
                rg.addColorStop(1, 'rgba(0,0,0,0)');
                ctx.fillStyle = rg; ctx.fillRect(x - s, y - s, s * 2, s * 2);
            }
        };
    }
    R.sparkle_diamond_dust = _sparkleFusion(9400, '#1a2030', 'rgba(220,235,255,1)', 0.015, 2);
    R.sparkle_starfield = _sparkleFusion(9401, '#080810', 'rgba(255,255,240,1)', 0.004, 2.5);
    R.sparkle_galaxy = _sparkleFusion(9402, '#0a0818', 'rgba(200,200,255,1)', 0.008, 3);
    R.sparkle_firefly = _sparkleFusion(9403, '#101810', 'rgba(180,255,100,1)', 0.003, 3.5);
    R.sparkle_snowfall = _sparkleFusion(9404, '#182028', 'rgba(220,240,255,1)', 0.02, 1.5);
    R.sparkle_champagne = _sparkleFusion(9405, '#1a1810', 'rgba(255,230,160,1)', 0.012, 1.8);
    R.sparkle_meteor = _sparkleFusion(9406, '#101018', 'rgba(255,180,80,1)', 0.005, 4);
    R.sparkle_constellation = _sparkleFusion(9407, '#080812', 'rgba(200,220,255,1)', 0.006, 2);
    R.sparkle_confetti = _sparkleFusion(9408, '#181020', 'rgba(255,150,220,1)', 0.01, 2.5);
    R.sparkle_lightning_bug = _sparkleFusion(9409, '#0a1408', 'rgba(120,255,80,1)', 0.004, 3);

    // ===== P6: MULTI-SCALE TEXTURE (10) =====
    function _multiscaleFusion(seed, c1, c2) {
        return (ctx, w, h) => {
            const n1 = _noise2d(w, h, 20, seed), n2 = _noise2d(w, h, 4, seed + 100);
            const id = ctx.createImageData(w, h);
            for (let i = 0; i < w * h; i++) {
                const t = (n1[i] * 0.6 + n2[i] * 0.4 + 0.5);
                const r = Math.floor(c1[0] + (c2[0] - c1[0]) * t), g = Math.floor(c1[1] + (c2[1] - c1[1]) * t), b = Math.floor(c1[2] + (c2[2] - c1[2]) * t);
                id.data[i * 4] = Math.max(0, Math.min(255, r)); id.data[i * 4 + 1] = Math.max(0, Math.min(255, g)); id.data[i * 4 + 2] = Math.max(0, Math.min(255, b)); id.data[i * 4 + 3] = 255;
            }
            ctx.putImageData(id, 0, 0);
        };
    }
    R.multiscale_chrome_grain = _multiscaleFusion(9500, [160, 175, 195], [210, 220, 235]);
    R.multiscale_candy_frost = _multiscaleFusion(9501, [180, 80, 110], [200, 200, 220]);
    R.multiscale_metal_grit = _multiscaleFusion(9502, [100, 105, 110], [160, 165, 175]);
    R.multiscale_pearl_texture = _multiscaleFusion(9503, [170, 165, 180], [215, 210, 225]);
    R.multiscale_satin_weave = _multiscaleFusion(9504, [130, 135, 140], [180, 185, 195]);
    R.multiscale_chrome_sand = _multiscaleFusion(9505, [175, 185, 200], [200, 210, 225]);
    R.multiscale_matte_silk = _multiscaleFusion(9506, [60, 65, 68], [100, 105, 110]);
    R.multiscale_flake_grain = _multiscaleFusion(9507, [140, 145, 130], [195, 200, 185]);
    R.multiscale_carbon_micro = _multiscaleFusion(9508, [30, 32, 35], [70, 75, 80]);
    R.multiscale_frost_crystal = _multiscaleFusion(9509, [180, 195, 210], [220, 235, 250]);

    // ===== P7: WEATHER & AGE (10) =====
    function _weatherFusion(seed, baseClr, weatherClr, direction) {
        return (ctx, w, h) => {
            ctx.fillStyle = baseClr; ctx.fillRect(0, 0, w, h);
            const n = _noise2d(w, h, 10, seed); const id = ctx.getImageData(0, 0, w, h);
            const wc = weatherClr;
            for (let py = 0; py < h; py++) for (let px = 0; px < w; px++) {
                let t = direction === 'top' ? 1 - py / h : direction === 'bottom' ? py / h : direction === 'random' ? 0.5 : py / h;
                t = Math.max(0, Math.min(1, t + n[py * w + px] * 0.3));
                if (t > 0.4) {
                    const a = (t - 0.4) / 0.6; const i = (py * w + px) * 4;
                    id.data[i] = Math.floor(id.data[i] * (1 - a) + wc[0] * a);
                    id.data[i + 1] = Math.floor(id.data[i + 1] * (1 - a) + wc[1] * a);
                    id.data[i + 2] = Math.floor(id.data[i + 2] * (1 - a) + wc[2] * a);
                }
            }
            ctx.putImageData(id, 0, 0);
        };
    }
    R.weather_sun_fade = _weatherFusion(9600, '#4488aa', [200, 180, 130], 'top');
    R.weather_salt_spray = _weatherFusion(9601, '#4488aa', [140, 150, 140], 'bottom');
    R.weather_acid_rain = _weatherFusion(9602, '#4488aa', [130, 160, 100], 'random');
    R.weather_desert_blast = _weatherFusion(9603, '#4488aa', [190, 170, 120], 'top');
    R.weather_ice_storm = _weatherFusion(9604, '#4488aa', [180, 210, 230], 'bottom');
    R.weather_road_spray = _weatherFusion(9605, '#4488aa', [100, 90, 75], 'bottom');
    R.weather_hood_bake = _weatherFusion(9606, '#4488aa', [180, 150, 100], 'top');
    R.weather_barn_dust = _weatherFusion(9607, '#4488aa', [150, 140, 120], 'top');
    R.weather_ocean_mist = _weatherFusion(9608, '#4488aa', [160, 180, 200], 'bottom');
    R.weather_volcanic_ash = _weatherFusion(9609, '#4488aa', [80, 80, 70], 'top');

    // ===== P8: IMPOSSIBLE PHYSICS (10) =====
    function _impossibleFusion(seed, c1, c2, style) {
        return (ctx, w, h) => {
            const g = style === 'radial' ? ctx.createRadialGradient(w / 2, h / 2, 0, w / 2, h / 2, w * 0.6) : ctx.createLinearGradient(0, 0, w, h);
            g.addColorStop(0, c1); g.addColorStop(0.5, c2); g.addColorStop(1, c1);
            ctx.fillStyle = g; ctx.fillRect(0, 0, w, h);
            // Impossible shimmer lines
            ctx.globalAlpha = 0.12; ctx.strokeStyle = '#ffffff'; ctx.lineWidth = 0.5;
            for (let i = 0; i < h; i += 3) { ctx.beginPath(); ctx.moveTo(0, i); ctx.lineTo(w, i + Math.sin(i * 0.2) * 3); ctx.stroke(); }
            ctx.globalAlpha = 1;
        };
    }
    R.impossible_glass_paint = _impossibleFusion(9700, '#667eaa', '#aaccdd', 'linear');
    R.impossible_foggy_chrome = _impossibleFusion(9701, '#c8d4e4', '#8898a8', 'linear');
    R.impossible_inverted_candy = _impossibleFusion(9702, '#aa66cc', '#cc99dd', 'radial');
    R.impossible_liquid_glass = _impossibleFusion(9703, '#88bbdd', '#a0d0e8', 'linear');
    R.impossible_phantom_mirror = _impossibleFusion(9704, '#0a0a14', '#222238', 'radial');
    R.impossible_ceramic_void = _impossibleFusion(9705, '#2a3040', '#445060', 'linear');
    R.impossible_anti_metal = _impossibleFusion(9706, '#8899cc', '#aabbee', 'radial');
    R.impossible_crystal_clear = _impossibleFusion(9707, '#99bbdd', '#bbddee', 'linear');
    R.impossible_dark_glass = _impossibleFusion(9708, '#1a2030', '#334455', 'linear');
    R.impossible_wet_void = _impossibleFusion(9709, '#101820', '#203040', 'radial');

    // ===== P9: TRI-ZONE MATERIALS (10) =====
    function _trizoneFusion(seed, c1, c2, c3) {
        return (ctx, w, h) => {
            const n = _noise2d(w, h, 14, seed); const id = ctx.createImageData(w, h);
            for (let i = 0; i < w * h; i++) {
                const v = n[i] + 0.5; let r, g, b;
                if (v < 0.33) { r = c1[0]; g = c1[1]; b = c1[2]; }
                else if (v < 0.66) { r = c2[0]; g = c2[1]; b = c2[2]; }
                else { r = c3[0]; g = c3[1]; b = c3[2]; }
                id.data[i * 4] = r; id.data[i * 4 + 1] = g; id.data[i * 4 + 2] = b; id.data[i * 4 + 3] = 255;
            }
            ctx.putImageData(id, 0, 0);
        };
    }
    R.trizone_chrome_candy_matte = _trizoneFusion(9800, [200, 210, 225], [180, 80, 110], [55, 58, 62]);
    R.trizone_pearl_carbon_gold = _trizoneFusion(9801, [190, 185, 200], [35, 38, 42], [200, 170, 80]);
    R.trizone_frozen_ember_chrome = _trizoneFusion(9802, [170, 200, 220], [200, 80, 30], [195, 205, 220]);
    R.trizone_anodized_candy_silk = _trizoneFusion(9803, [100, 130, 170], [180, 70, 100], [160, 155, 165]);
    R.trizone_vanta_chrome_pearl = _trizoneFusion(9804, [8, 8, 10], [200, 210, 225], [185, 180, 195]);
    R.trizone_glass_metal_matte = _trizoneFusion(9805, [140, 170, 200], [180, 185, 195], [55, 58, 62]);
    R.trizone_mercury_obsidian_candy = _trizoneFusion(9806, [170, 175, 185], [15, 15, 20], [180, 70, 100]);
    R.trizone_titanium_copper_chrome = _trizoneFusion(9807, [140, 145, 160], [180, 110, 70], [200, 210, 225]);
    R.trizone_ceramic_flake_satin = _trizoneFusion(9808, [180, 180, 190], [150, 160, 140], [130, 135, 140]);
    R.trizone_stealth_spectra_frozen = _trizoneFusion(9809, [25, 28, 32], [170, 100, 200], [170, 200, 220]);

    // ===== P10: DEPTH ILLUSION (10) =====
    // shapeFn receives (px, py, w, h, noiseArr) — noise is PRE-COMPUTED once
    function _depthFusion(seed, shapeFn, needsNoise, noiseScale) {
        return (ctx, w, h) => {
            ctx.fillStyle = '#90a0b0'; ctx.fillRect(0, 0, w, h);
            const id = ctx.getImageData(0, 0, w, h);
            const nArr = needsNoise ? _noise2d(w, h, noiseScale || 8, seed) : null;
            for (let py = 0; py < h; py++) for (let px = 0; px < w; px++) {
                const d = shapeFn(px, py, w, h, nArr);
                const v = d * 50; const i = (py * w + px) * 4;
                id.data[i] += v; id.data[i + 1] += v; id.data[i + 2] += v;
            }
            ctx.putImageData(id, 0, 0);
        };
    }
    R.depth_canyon = _depthFusion(9900, (x, y, w, h, n) => n[y * w + x], true, 8);
    R.depth_bubble = _depthFusion(9901, (x, y, w, h) => { const cx = w / 2, cy = h / 2, d = Math.sqrt((x - cx) ** 2 + (y - cy) ** 2) / (w * 0.4); return Math.max(0, 1 - d * d); }, false);
    R.depth_ripple = _depthFusion(9902, (x, y, w, h) => { const d = Math.sqrt((x - w / 2) ** 2 + (y - h / 2) ** 2); return Math.sin(d * 0.4) * 0.5; }, false);
    R.depth_scale = _depthFusion(9903, (x, y, w, h) => { const s = Math.max(8, w / 4); return Math.abs(Math.sin(x / s * 3.14) * Math.sin((y + ((Math.floor(x / s) % 2) * s / 2)) / s * 3.14)); }, false);
    R.depth_honeycomb = _depthFusion(9904, (x, y, w, h) => { const s = Math.max(8, w / 4), hr = s * 0.87; const c = Math.round(x / (s * 1.5)), r = Math.round(y / hr); const cx = c * s * 1.5 + (r % 2) * s * 0.75, cy = r * hr; const d = Math.sqrt((x - cx) ** 2 + (y - cy) ** 2) / (s * 0.5); return d < 1 ? d - 0.5 : 0; }, false);
    R.depth_crack = _depthFusion(9905, (x, y, w, h, n) => { const v = n[y * w + x]; return Math.abs(v) < 0.08 ? -1 : 0; }, true, 6);
    R.depth_wave = _depthFusion(9906, (x, y, w, h) => Math.sin(y * 0.15 + Math.sin(x * 0.06) * 2) * 0.5, false);
    R.depth_pillow = _depthFusion(9907, (x, y, w, h) => { const s = Math.max(10, w / 3); return Math.sin(x / s * 3.14) * Math.sin(y / s * 3.14) * 0.5; }, false);
    R.depth_vortex = _depthFusion(9908, (x, y, w, h) => { const a = Math.atan2(y - h / 2, x - w / 2), d = Math.sqrt((x - w / 2) ** 2 + (y - h / 2) ** 2); return Math.sin(a * 3 + d * 0.15) * 0.5; }, false);
    R.depth_erosion = _depthFusion(9909, (x, y, w, h, n) => { return n[y * w + x] > 0.2 ? n[y * w + x] - 0.2 : 0; }, true, 10);

    // ===== P11: METALLIC HALOS (10) =====
    // patternFn receives (px, py, w, h, precomputed) — heavy data pre-computed once
    function _haloFusion(seed, patternFn, haloClr, precomputeFn) {
        return (ctx, w, h) => {
            ctx.fillStyle = '#2a3040'; ctx.fillRect(0, 0, w, h);
            const id = ctx.getImageData(0, 0, w, h);
            const pre = precomputeFn ? precomputeFn(w, h, seed) : null;
            for (let py = 0; py < h; py++) for (let px = 0; px < w; px++) {
                const d = patternFn(px, py, w, h, pre);
                const i = (py * w + px) * 4;
                if (d > 0.7 && d < 0.85) { id.data[i] = haloClr[0]; id.data[i + 1] = haloClr[1]; id.data[i + 2] = haloClr[2]; }
                else if (d <= 0.7) { id.data[i] = 35 + d * 30; id.data[i + 1] = 40 + d * 30; id.data[i + 2] = 55 + d * 30; }
            }
            ctx.putImageData(id, 0, 0);
        };
    }
    R.halo_hex_chrome = _haloFusion(10000, (x, y, w, h) => { const s = Math.max(8, w / 4), hr = s * 0.87; const c = Math.round(x / (s * 1.5)), r = Math.round(y / hr); const cx = c * s * 1.5 + (r % 2) * s * 0.75, cy = r * hr; return Math.sqrt((x - cx) ** 2 + (y - cy) ** 2) / (s * 0.5); }, [200, 215, 235]);
    R.halo_scale_gold = _haloFusion(10001, (x, y, w, h) => { const s = Math.max(8, w / 4); return Math.abs(Math.sin(x / s * 3.14) * Math.sin((y + (Math.floor(x / s) % 2) * s / 2) / s * 3.14)); }, [210, 180, 80]);
    R.halo_circle_pearl = _haloFusion(10002, (x, y, w, h) => { const s = Math.max(10, w / 3); const cx = (Math.round(x / s) + 0.5) * s, cy = (Math.round(y / s) + 0.5) * s; return Math.sqrt((x - cx) ** 2 + (y - cy) ** 2) / (s * 0.45); }, [200, 195, 210]);
    R.halo_diamond_chrome = _haloFusion(10003, (x, y, w, h) => { const s = Math.max(10, w / 3); const cx = (Math.round(x / s) + 0.5) * s, cy = (Math.round(y / s) + 0.5) * s; return (Math.abs(x - cx) + Math.abs(y - cy)) / (s * 0.5); }, [210, 220, 235]);
    R.halo_voronoi_metal = _haloFusion(10004, (x, y, w, h, pre) => { let mn = 999; for (const p of pre) { const d = Math.sqrt((x - p[0]) ** 2 + (y - p[1]) ** 2); if (d < mn) mn = d; } return mn / (w * 0.15); }, [180, 190, 210], (w, h, sd) => { const r = _rng(sd); const pts = []; for (let i = 0; i < 8; i++) pts.push([r() * w, r() * h]); return pts; });
    R.halo_wave_candy = _haloFusion(10005, (x, y, w, h) => Math.abs(Math.sin(y * 0.2 + Math.sin(x * 0.08) * 3)), [200, 120, 150]);
    R.halo_crack_chrome = _haloFusion(10006, (x, y, w, h, pre) => Math.abs(pre[y * w + x]) * 3, [210, 220, 235], (w, h, sd) => _noise2d(w, h, 10, sd));
    R.halo_star_metal = _haloFusion(10007, (x, y, w, h) => { const s = Math.max(10, w / 3); const cx = (Math.round(x / s) + 0.5) * s, cy = (Math.round(y / s) + 0.5) * s; const a = Math.atan2(y - cy, x - cx); const d = Math.sqrt((x - cx) ** 2 + (y - cy) ** 2); return d / (s * (0.3 + Math.abs(Math.sin(a * 4)) * 0.2)); }, [190, 200, 220]);
    R.halo_grid_pearl = _haloFusion(10008, (x, y, w, h) => { const s = Math.max(8, w / 4); return Math.min(Math.abs(x % s - s / 2), Math.abs(y % s - s / 2)) / (s * 0.2); }, [200, 195, 210]);
    R.halo_ripple_chrome = _haloFusion(10009, (x, y, w, h) => { const d = Math.sqrt((x - w / 2) ** 2 + (y - h / 2) ** 2); return Math.abs(Math.sin(d * 0.3)); }, [210, 220, 240]);

    // ===== P12: LIGHT WAVES (10) =====
    function _waveFusion(seed, waveFn, c1, c2) {
        return (ctx, w, h) => {
            const id = ctx.createImageData(w, h);
            for (let py = 0; py < h; py++) for (let px = 0; px < w; px++) {
                const t = (waveFn(px, py, w, h) + 1) * 0.5;
                const r = Math.floor(c1[0] + (c2[0] - c1[0]) * t), g = Math.floor(c1[1] + (c2[1] - c1[1]) * t), b = Math.floor(c1[2] + (c2[2] - c1[2]) * t);
                const i = (py * w + px) * 4; id.data[i] = r; id.data[i + 1] = g; id.data[i + 2] = b; id.data[i + 3] = 255;
            }
            ctx.putImageData(id, 0, 0);
        };
    }
    R.wave_chrome_tide = _waveFusion(10100, (x, y) => Math.sin(y * 0.08), [80, 90, 105], [210, 220, 240]);
    R.wave_candy_flow = _waveFusion(10101, (x, y) => Math.sin(y * 0.15 + x * 0.02), [130, 50, 80], [210, 140, 170]);
    R.wave_pearl_current = _waveFusion(10102, (x, y) => Math.sin(y * 0.06 + Math.sin(x * 0.05) * 2), [150, 145, 165], [210, 205, 225]);
    R.wave_metallic_pulse = _waveFusion(10103, (x, y) => Math.sin(y * 0.3 + x * 0.05), [70, 80, 95], [190, 200, 220]);
    R.wave_dual_frequency = _waveFusion(10104, (x, y) => Math.sin(y * 0.06) * 0.6 + Math.sin(y * 0.25) * 0.4, [80, 90, 110], [200, 210, 235]);
    R.wave_diagonal_sweep = _waveFusion(10105, (x, y) => Math.sin((x + y) * 0.1), [90, 100, 115], [200, 210, 230]);
    R.wave_circular_radar = _waveFusion(10106, (x, y, w, h) => { const d = Math.sqrt((x - w / 2) ** 2 + (y - h / 2) ** 2); return Math.sin(d * 0.2); }, [70, 85, 105], [200, 215, 240]);
    R.wave_turbulent_flow = _waveFusion(10107, (x, y) => Math.sin(y * 0.1 + Math.sin(x * 0.08) * 3) * Math.cos(x * 0.05), [75, 85, 100], [195, 205, 225]);
    R.wave_standing_chrome = _waveFusion(10108, (x, y) => Math.sin(y * 0.12) * Math.cos(y * 0.12), [90, 100, 118], [210, 220, 240]);
    R.wave_moire_metal = _waveFusion(10109, (x, y) => Math.sin(x * 0.15) * 0.5 + Math.sin(y * 0.16) * 0.5, [80, 88, 105], [200, 210, 230]);

    // ===== P13: FRACTAL CHAOS (10) =====
    function _fractalFusion(seed, c1, c2, octaves) {
        return (ctx, w, h) => {
            const id = ctx.createImageData(w, h);
            const layers = []; const scales = [6, 12, 24, 48, 96];
            for (let o = 0; o < octaves; o++) layers.push(_noise2d(w, h, scales[o % 5], seed + o * 100));
            for (let i = 0; i < w * h; i++) {
                let v = 0; for (let o = 0; o < octaves; o++) v += layers[o][i] / (o + 1);
                v = (v / octaves + 0.5);
                const r = Math.floor(c1[0] + (c2[0] - c1[0]) * v), g = Math.floor(c1[1] + (c2[1] - c1[1]) * v), b = Math.floor(c1[2] + (c2[2] - c1[2]) * v);
                id.data[i * 4] = Math.max(0, Math.min(255, r)); id.data[i * 4 + 1] = Math.max(0, Math.min(255, g)); id.data[i * 4 + 2] = Math.max(0, Math.min(255, b)); id.data[i * 4 + 3] = 255;
            }
            ctx.putImageData(id, 0, 0);
        };
    }
    R.fractal_chrome_decay = _fractalFusion(10200, [200, 212, 228], [50, 55, 62], 4);
    R.fractal_candy_chaos = _fractalFusion(10201, [200, 70, 110], [80, 30, 50], 3);
    R.fractal_pearl_cloud = _fractalFusion(10202, [210, 205, 225], [140, 135, 155], 4);
    R.fractal_metallic_storm = _fractalFusion(10203, [200, 210, 230], [40, 48, 65], 5);
    R.fractal_matte_chrome = _fractalFusion(10204, [55, 60, 65], [210, 220, 238], 4);
    R.fractal_warm_cold = _fractalFusion(10205, [180, 120, 80], [80, 130, 180], 3);
    R.fractal_deep_organic = _fractalFusion(10206, [60, 80, 50], [140, 160, 120], 4);
    R.fractal_electric_noise = _fractalFusion(10207, [30, 50, 120], [140, 180, 255], 5);
    R.fractal_cosmic_dust = _fractalFusion(10208, [15, 15, 30], [120, 110, 160], 4);
    R.fractal_liquid_fire = _fractalFusion(10209, [200, 80, 20], [255, 200, 60], 3);

    // ===== P14: SPECTRAL REACTIVE (10) =====
    function _spectralFusion(seed, mapFn) {
        return (ctx, w, h) => {
            const id = ctx.createImageData(w, h); const n = _noise2d(w, h, 12, seed);
            for (let i = 0; i < w * h; i++) {
                const t = (n[i] + 0.5); const [r, g, b] = mapFn(t);
                id.data[i * 4] = r; id.data[i * 4 + 1] = g; id.data[i * 4 + 2] = b; id.data[i * 4 + 3] = 255;
            }
            ctx.putImageData(id, 0, 0);
        };
    }
    R.spectral_rainbow_metal = _spectralFusion(10300, t => _hsl(t * 360, 50, 50));
    R.spectral_warm_cool = _spectralFusion(10301, t => t > 0.5 ? _hsl(20, 60, 45) : _hsl(210, 50, 50));
    R.spectral_dark_light = _spectralFusion(10302, t => _hsl(220, 20, 20 + t * 50));
    R.spectral_sat_metal = _spectralFusion(10303, t => _hsl(200, t * 80, 45 + t * 15));
    R.spectral_complementary = _spectralFusion(10304, t => t > 0.5 ? _hsl(200, 55, 48) : _hsl(20, 55, 48));
    R.spectral_neon_reactive = _spectralFusion(10305, t => _hsl(140 + t * 80, 70 + t * 20, 40 + t * 25));
    R.spectral_earth_sky = _spectralFusion(10306, t => t > 0.5 ? _hsl(200, 50, 55) : _hsl(30, 55, 40));
    R.spectral_mono_chrome = _spectralFusion(10307, t => { const v = Math.floor(60 + t * 160); return [v, v, v + 10]; });
    R.spectral_prismatic_flip = _spectralFusion(10308, t => t < 0.33 ? _hsl(0, 60, 45) : t < 0.66 ? _hsl(120, 50, 42) : _hsl(240, 55, 48));
    R.spectral_inverse_logic = _spectralFusion(10309, t => _hsl(360 - t * 360, 50, 55 - t * 15));

    // ===== P15: PANEL QUILTING (10) =====
    function _quiltFusion(seed, tileSize, palette) {
        return (ctx, w, h) => {
            const r = _rng(seed); const id = ctx.createImageData(w, h);
            const cols = Math.ceil(w / tileSize), rows = Math.ceil(h / tileSize);
            const grid = []; for (let i = 0; i < rows * cols; i++) grid.push(palette[Math.floor(r() * palette.length)]);
            for (let py = 0; py < h; py++) for (let px = 0; px < w; px++) {
                const c = Math.floor(px / tileSize), rw = Math.floor(py / tileSize);
                const clr = grid[(rw * cols + c) % grid.length]; const i = (py * w + px) * 4;
                // Add slight edge darkening
                const ex = px % tileSize, ey = py % tileSize;
                const edge = (ex < 1 || ey < 1 || ex >= tileSize - 1 || ey >= tileSize - 1) ? 0.7 : 1;
                id.data[i] = Math.floor(clr[0] * edge); id.data[i + 1] = Math.floor(clr[1] * edge); id.data[i + 2] = Math.floor(clr[2] * edge); id.data[i + 3] = 255;
            }
            ctx.putImageData(id, 0, 0);
        };
    }
    const chrP = [[190, 200, 220], [160, 170, 185], [210, 215, 230], [120, 130, 145], [80, 88, 100]];
    const canP = [[180, 80, 110], [200, 100, 130], [150, 60, 85], [170, 90, 115], [140, 50, 75]];
    const prlP = [[190, 185, 205], [170, 165, 185], [210, 205, 225], [150, 145, 165], [200, 195, 215]];
    const mtlP = [[160, 165, 180], [140, 148, 160], [180, 185, 200], [120, 128, 140], [200, 205, 220]];
    const mixP = [[200, 210, 228], [180, 80, 110], [55, 58, 62], [200, 170, 80], [100, 130, 170]];
    R.quilt_chrome_mosaic = _quiltFusion(10400, 6, chrP);
    R.quilt_candy_tiles = _quiltFusion(10401, 8, canP);
    R.quilt_pearl_patchwork = _quiltFusion(10402, 5, prlP);
    R.quilt_metallic_pixels = _quiltFusion(10403, 4, mtlP);
    R.quilt_hex_variety = _quiltFusion(10404, 7, mixP);
    R.quilt_diamond_shimmer = _quiltFusion(10405, 5, chrP.concat(canP));
    R.quilt_random_chaos = _quiltFusion(10406, 3, mixP);
    R.quilt_gradient_tiles = _quiltFusion(10407, 9, prlP.concat(mtlP));
    R.quilt_alternating_duo = _quiltFusion(10408, 6, [chrP[0], canP[0]]);
    R.quilt_organic_cells = _quiltFusion(10409, 5, mixP.concat(prlP));

    // ===== INJECT INTO MAIN APP =====
    function inject() {
        // Find the renderers object — it's on window or in the MONO_PREVIEW_CANVAS scope
        // The main HTML uses an object like { void: (ctx,w,h)=>{...}, ... }
        // We need to find it and merge our renderers into it
        if (typeof window._fusionSwatchesReady === 'undefined') {
            window._fusionSwatchRenderers = R;
            window._fusionSwatchesReady = true;
            console.log(`[FUSIONS] ${Object.keys(R).length} swatch renderers loaded`);
        }
    }
    inject();
})();
