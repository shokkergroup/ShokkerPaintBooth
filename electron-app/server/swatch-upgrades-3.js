// SWATCH UPGRADES PART 3 — Candy/Pearl, Ceramic/Glass, Paradigm Elemental, Shokk Series
(function () {
    'use strict';
    function _rng(s) { return function () { s = (s * 16807) % 2147483647; return (s - 1) / 2147483646; }; }
    function _n2d(w, h, sc, seed) {
        const r = _rng(seed), out = new Float32Array(w * h), grid = Math.ceil(Math.max(w, h) / sc) + 2;
        const g = []; for (let i = 0; i < grid * grid; i++)g.push(r() * 6.28);
        for (let py = 0; py < h; py++)for (let px = 0; px < w; px++) {
            const fx = px / sc, fy = py / sc, ix = Math.floor(fx), iy = Math.floor(fy), dx = fx - ix, dy = fy - iy;
            const sx = dx * dx * (3 - 2 * dx), sy = dy * dy * (3 - 2 * dy);
            const i00 = (iy * grid + ix) % g.length, i10 = (iy * grid + ix + 1) % g.length;
            const i01 = ((iy + 1) * grid + ix) % g.length, i11 = ((iy + 1) * grid + ix + 1) % g.length;
            out[py * w + px] = ((Math.cos(g[i00]) * dx + Math.sin(g[i00]) * dy) * (1 - sx) + (Math.cos(g[i10]) * (dx - 1) + Math.sin(g[i10]) * dy) * sx) * (1 - sy) + ((Math.cos(g[i01]) * dx + Math.sin(g[i01]) * (dy - 1)) * (1 - sx) + (Math.cos(g[i11]) * (dx - 1) + Math.sin(g[i11]) * (dy - 1)) * sx) * sy;
        } return out;
    }
    function _hsl(h, s, l) {
        h = ((h % 360) + 360) % 360; s /= 100; l /= 100; const c = (1 - Math.abs(2 * l - 1)) * s, x = c * (1 - Math.abs((h / 60) % 2 - 1)), m = l - c / 2; let r, g, b;
        if (h < 60) { r = c; g = x; b = 0; } else if (h < 120) { r = x; g = c; b = 0; } else if (h < 180) { r = 0; g = c; b = x; } else if (h < 240) { r = 0; g = x; b = c; } else if (h < 300) { r = x; g = 0; b = c; } else { r = c; g = 0; b = x; }
        return [Math.round((r + m) * 255), Math.round((g + m) * 255), Math.round((b + m) * 255)];
    }
    const R = {};

    // === CANDY & PEARL BASES ===
    function _candyBase(seed, hue, sat) {
        return (ctx, w, h) => {
            const id = ctx.createImageData(w, h); const n = _n2d(w, h, 10, seed);
            for (let py = 0; py < h; py++)for (let px = 0; px < w; px++) {
                const t = (py / h * 0.4 + px / w * 0.6); const nv = n[py * w + px] * 0.08;
                const [r, g, b] = _hsl(hue + t * 15 + nv * 30, sat + t * 10, 32 + t * 20 + nv * 10);
                const i = (py * w + px) * 4; id.data[i] = r; id.data[i + 1] = g; id.data[i + 2] = b; id.data[i + 3] = 255;
            }
            ctx.putImageData(id, 0, 0);
            // Candy depth glow
            const gl = ctx.createLinearGradient(0, h * 0.2, w * 0.7, h * 0.5);
            gl.addColorStop(0, 'rgba(255,255,255,0)'); gl.addColorStop(0.5, 'rgba(255,255,255,0.18)'); gl.addColorStop(1, 'rgba(255,255,255,0)');
            ctx.fillStyle = gl; ctx.fillRect(0, 0, w, h);
        };
    }

    R.candy_burgundy = _candyBase(8001, 340, 65);
    R.candy_cobalt = _candyBase(8002, 220, 70);
    R.candy_emerald = _candyBase(8003, 150, 65);

    R.chameleon = (ctx, w, h) => {
        const id = ctx.createImageData(w, h); const n = _n2d(w, h, 12, 8004);
        for (let py = 0; py < h; py++)for (let px = 0; px < w; px++) {
            const angle = (Math.atan2(py - h / 2, px - w / 2) + 3.14) / 6.28;
            const nv = n[py * w + px] * 0.12;
            const hue = (angle + nv) * 360;
            const [r, g, b] = _hsl(hue, 60, 38 + nv * 15);
            const i = (py * w + px) * 4; id.data[i] = r; id.data[i + 1] = g; id.data[i + 2] = b; id.data[i + 3] = 255;
        }
        ctx.putImageData(id, 0, 0);
        // Metallic sheen
        ctx.strokeStyle = 'rgba(255,255,255,0.06)'; ctx.lineWidth = 0.5;
        for (let y = 0; y < h; y += 2) { ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(w, y + Math.sin(y * 0.4) * 1.5); ctx.stroke(); }
    };

    R.iridescent = (ctx, w, h) => {
        const id = ctx.createImageData(w, h); const n = _n2d(w, h, 8, 8005);
        for (let py = 0; py < h; py++)for (let px = 0; px < w; px++) {
            const t1 = Math.sin(px * 0.12 + py * 0.06) * 0.3;
            const t2 = Math.sin(py * 0.1 - px * 0.08) * 0.2;
            const nv = n[py * w + px] * 0.15;
            const hue = ((t1 + t2 + nv + 0.5) * 360) % 360;
            const [r, g, b] = _hsl(hue, 55, 48 + nv * 12);
            const i = (py * w + px) * 4; id.data[i] = r; id.data[i + 1] = g; id.data[i + 2] = b; id.data[i + 3] = 255;
        }
        ctx.putImageData(id, 0, 0);
    };

    R.moonstone = (ctx, w, h) => {
        const id = ctx.createImageData(w, h); const n = _n2d(w, h, 10, 8006);
        for (let py = 0; py < h; py++)for (let px = 0; px < w; px++) {
            const t = (py / h * 0.5 + px / w * 0.5); const nv = n[py * w + px] * 0.1;
            const base = 190 + t * 30 + nv * 20; const blue = base + 10;
            const i = (py * w + px) * 4; id.data[i] = Math.min(255, Math.floor(base - 5)); id.data[i + 1] = Math.min(255, Math.floor(base)); id.data[i + 2] = Math.min(255, Math.floor(blue)); id.data[i + 3] = 255;
        }
        ctx.putImageData(id, 0, 0);
        const gl = ctx.createRadialGradient(w * 0.35, h * 0.35, 0, w * 0.35, h * 0.35, w * 0.4);
        gl.addColorStop(0, 'rgba(200,210,240,0.2)'); gl.addColorStop(1, 'rgba(0,0,0,0)'); ctx.fillStyle = gl; ctx.fillRect(0, 0, w, h);
    };

    R.opal = (ctx, w, h) => {
        const id = ctx.createImageData(w, h); const n = _n2d(w, h, 8, 8007);
        for (let py = 0; py < h; py++)for (let px = 0; px < w; px++) {
            const t1 = Math.sin(px * 0.1 + py * 0.05) * 0.2 + Math.sin(py * 0.08) * 0.15;
            const nv = n[py * w + px] * 0.12;
            const hue = ((t1 + nv + 0.4) * 180 + 160) % 360;
            const [r, g, b] = _hsl(hue, 40, 65 + nv * 15);
            const i = (py * w + px) * 4; id.data[i] = r; id.data[i + 1] = g; id.data[i + 2] = b; id.data[i + 3] = 255;
        }
        ctx.putImageData(id, 0, 0);
    };

    R.spectraflame = (ctx, w, h) => {
        const id = ctx.createImageData(w, h); const n = _n2d(w, h, 8, 8008);
        for (let py = 0; py < h; py++)for (let px = 0; px < w; px++) {
            const t = (px / w * 0.6 + py / h * 0.4); const nv = n[py * w + px] * 0.1;
            const hue = (t + nv) * 120 + 200;
            const [r, g, b] = _hsl(hue % 360, 70, 35 + t * 18 + nv * 10);
            const i = (py * w + px) * 4; id.data[i] = r; id.data[i + 1] = g; id.data[i + 2] = b; id.data[i + 3] = 255;
        }
        ctx.putImageData(id, 0, 0);
        ctx.strokeStyle = 'rgba(255,255,255,0.08)'; ctx.lineWidth = 0.5;
        for (let y = 0; y < h; y += 2) { ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(w, y); ctx.stroke(); }
    };

    R.tinted_clear = (ctx, w, h) => {
        const g = ctx.createLinearGradient(0, 0, w, h);
        g.addColorStop(0, '#c8d0d8'); g.addColorStop(0.3, '#e0e4ec'); g.addColorStop(0.5, '#b8c0c8'); g.addColorStop(0.8, '#d0d8e0'); g.addColorStop(1, '#c0c8d0');
        ctx.fillStyle = g; ctx.fillRect(0, 0, w, h);
        ctx.fillStyle = 'rgba(200,160,100,0.08)'; ctx.fillRect(0, 0, w, h);
        const hl = ctx.createLinearGradient(0, h * 0.2, w * 0.6, h * 0.5);
        hl.addColorStop(0, 'rgba(255,255,255,0)'); hl.addColorStop(0.5, 'rgba(255,255,255,0.2)'); hl.addColorStop(1, 'rgba(255,255,255,0)'); ctx.fillStyle = hl; ctx.fillRect(0, 0, w, h);
    };

    R.tri_coat_pearl = (ctx, w, h) => {
        const id = ctx.createImageData(w, h); const n = _n2d(w, h, 10, 8010);
        for (let py = 0; py < h; py++)for (let px = 0; px < w; px++) {
            const t = (py / h * 0.4 + px / w * 0.6); const nv = n[py * w + px] * 0.08;
            const base = 210 + t * 25 + nv * 15;
            const i = (py * w + px) * 4; id.data[i] = Math.min(255, Math.floor(base - 8)); id.data[i + 1] = Math.min(255, Math.floor(base - 3)); id.data[i + 2] = Math.min(255, Math.floor(base + 5)); id.data[i + 3] = 255;
        }
        ctx.putImageData(id, 0, 0);
        const hl = ctx.createLinearGradient(w * 0.1, h * 0.15, w * 0.7, h * 0.5);
        hl.addColorStop(0, 'rgba(255,255,255,0)'); hl.addColorStop(0.5, 'rgba(255,255,255,0.15)'); hl.addColorStop(1, 'rgba(255,255,255,0)'); ctx.fillStyle = hl; ctx.fillRect(0, 0, w, h);
    };

    // === CERAMIC & GLASS BASES ===
    R.ceramic = (ctx, w, h) => {
        ctx.fillStyle = '#d0ccc4'; ctx.fillRect(0, 0, w, h); const n = _n2d(w, h, 6, 8101), id = ctx.getImageData(0, 0, w, h);
        for (let i = 0; i < w * h; i++) { const v = n[i] * 8; id.data[i * 4] += v; id.data[i * 4 + 1] += v * 0.9; id.data[i * 4 + 2] += v * 0.7; } ctx.putImageData(id, 0, 0);
        const hl = ctx.createLinearGradient(w * 0.2, 0, w * 0.7, h * 0.4); hl.addColorStop(0, 'rgba(255,255,255,0)'); hl.addColorStop(0.5, 'rgba(255,255,255,0.12)'); hl.addColorStop(1, 'rgba(255,255,255,0)'); ctx.fillStyle = hl; ctx.fillRect(0, 0, w, h);
    };

    R.ceramic_matte = (ctx, w, h) => {
        ctx.fillStyle = '#c0bab0'; ctx.fillRect(0, 0, w, h); const n = _n2d(w, h, 4, 8102), id = ctx.getImageData(0, 0, w, h);
        for (let i = 0; i < w * h; i++) { const v = n[i] * 10; id.data[i * 4] += v; id.data[i * 4 + 1] += v * 0.9; id.data[i * 4 + 2] += v * 0.8; } ctx.putImageData(id, 0, 0);
    };

    R.crystal_clear = (ctx, w, h) => {
        const g = ctx.createLinearGradient(0, 0, w, h); g.addColorStop(0, '#d0dce8'); g.addColorStop(0.3, '#e8f0f8'); g.addColorStop(0.5, '#c8d8e4'); g.addColorStop(0.8, '#e0eaf4'); g.addColorStop(1, '#d4e0ec');
        ctx.fillStyle = g; ctx.fillRect(0, 0, w, h);
        const hl = ctx.createLinearGradient(0, 0, w * 0.5, h * 0.4); hl.addColorStop(0, 'rgba(255,255,255,0)'); hl.addColorStop(0.5, 'rgba(255,255,255,0.25)'); hl.addColorStop(1, 'rgba(255,255,255,0)'); ctx.fillStyle = hl; ctx.fillRect(0, 0, w, h);
    };

    R.enamel = (ctx, w, h) => {
        const g = ctx.createLinearGradient(0, 0, w, h); g.addColorStop(0, '#e0d8c8'); g.addColorStop(0.5, '#e8e0d0'); g.addColorStop(1, '#d8d0c0');
        ctx.fillStyle = g; ctx.fillRect(0, 0, w, h);
        const hl = ctx.createLinearGradient(w * 0.1, h * 0.1, w * 0.6, h * 0.4); hl.addColorStop(0, 'rgba(255,255,255,0)'); hl.addColorStop(0.5, 'rgba(255,255,255,0.15)'); hl.addColorStop(1, 'rgba(255,255,255,0)'); ctx.fillStyle = hl; ctx.fillRect(0, 0, w, h);
    };

    R.obsidian = (ctx, w, h) => {
        ctx.fillStyle = '#0a0a12'; ctx.fillRect(0, 0, w, h);
        const hl = ctx.createLinearGradient(0, 0, w * 0.6, h * 0.4); hl.addColorStop(0, 'rgba(255,255,255,0)'); hl.addColorStop(0.5, 'rgba(100,110,140,0.2)'); hl.addColorStop(1, 'rgba(255,255,255,0)'); ctx.fillStyle = hl; ctx.fillRect(0, 0, w, h);
        const n = _n2d(w, h, 8, 8105), id = ctx.getImageData(0, 0, w, h); for (let i = 0; i < w * h; i++) { if (n[i] > 0.25) { id.data[i * 4] += 4; id.data[i * 4 + 1] += 5; id.data[i * 4 + 2] += 8; } } ctx.putImageData(id, 0, 0);
    };

    R.piano_black = (ctx, w, h) => {
        ctx.fillStyle = '#060608'; ctx.fillRect(0, 0, w, h);
        const hl = ctx.createLinearGradient(0, 0, w * 0.5, h * 0.35); hl.addColorStop(0, 'rgba(255,255,255,0)'); hl.addColorStop(0.4, 'rgba(255,255,255,0.15)'); hl.addColorStop(0.6, 'rgba(255,255,255,0.15)'); hl.addColorStop(1, 'rgba(255,255,255,0)'); ctx.fillStyle = hl; ctx.fillRect(0, 0, w, h);
    };

    R.porcelain = (ctx, w, h) => {
        ctx.fillStyle = '#eae6e0'; ctx.fillRect(0, 0, w, h); const n = _n2d(w, h, 8, 8107), id = ctx.getImageData(0, 0, w, h);
        for (let i = 0; i < w * h; i++) { const v = n[i] * 5; id.data[i * 4] += v; id.data[i * 4 + 1] += v; id.data[i * 4 + 2] += v * 0.8; } ctx.putImageData(id, 0, 0);
        const hl = ctx.createLinearGradient(w * 0.15, h * 0.1, w * 0.6, h * 0.45); hl.addColorStop(0, 'rgba(255,255,255,0)'); hl.addColorStop(0.5, 'rgba(255,255,255,0.18)'); hl.addColorStop(1, 'rgba(255,255,255,0)'); ctx.fillStyle = hl; ctx.fillRect(0, 0, w, h);
    };

    R.tempered_glass = (ctx, w, h) => {
        const g = ctx.createLinearGradient(0, 0, w, h); g.addColorStop(0, '#88aac0'); g.addColorStop(0.3, '#a0c0d4'); g.addColorStop(0.6, '#80a8c0'); g.addColorStop(1, '#90b4c8');
        ctx.fillStyle = g; ctx.fillRect(0, 0, w, h);
        const hl = ctx.createLinearGradient(0, 0, w * 0.4, h * 0.3); hl.addColorStop(0, 'rgba(255,255,255,0)'); hl.addColorStop(0.5, 'rgba(255,255,255,0.2)'); hl.addColorStop(1, 'rgba(255,255,255,0)'); ctx.fillStyle = hl; ctx.fillRect(0, 0, w, h);
    };

    // === PARADIGM ELEMENTAL FORCES ===
    R.arctic_ice = (ctx, w, h) => {
        // Base: cold gradient from deep ice blue to frosty white
        const bg = ctx.createLinearGradient(0, 0, w * 0.3, h);
        bg.addColorStop(0, '#b8daea'); bg.addColorStop(0.3, '#d0e8f4'); bg.addColorStop(0.6, '#c0d8ec'); bg.addColorStop(1, '#daeaf6');
        ctx.fillStyle = bg; ctx.fillRect(0, 0, w, h);
        // Layer 1: Crystalline depth variation via dual-frequency noise
        const n1 = _n2d(w, h, 12, 8201), n2 = _n2d(w, h, 5, 8202);
        const id = ctx.getImageData(0, 0, w, h);
        for (let py = 0; py < h; py++)for (let px = 0; px < w; px++) {
            const v1 = n1[py * w + px], v2 = n2[py * w + px];
            const depth = (v1 * 0.6 + v2 * 0.4) * 18;
            const i = (py * w + px) * 4;
            // Slight blue shift in deeper areas, white in shallow
            id.data[i] += depth * 0.5; id.data[i + 1] += depth * 0.7; id.data[i + 2] += depth;
            // Frost crystal edges: where noise crosses zero = crystal boundary
            if (Math.abs(v1) < 0.04) { id.data[i] += 20; id.data[i + 1] += 22; id.data[i + 2] += 25; }
        }
        ctx.putImageData(id, 0, 0);
        // Layer 2: Subtle frost crack network (branching, not random dots)
        ctx.strokeStyle = 'rgba(200,225,245,0.12)'; ctx.lineWidth = 0.5;
        const rg = _rng(8201);
        for (let i = 0; i < 3; i++) {
            const sx = rg() * w, sy = rg() * h; let x = sx, y = sy, angle = rg() * 6.28;
            ctx.beginPath(); ctx.moveTo(x, y);
            for (let step = 0; step < 12; step++) {
                angle += ((rg() - 0.5) * 1.2); const len = 2 + rg() * 4;
                x += Math.cos(angle) * len; y += Math.sin(angle) * len; ctx.lineTo(x, y);
                // Branch occasionally
                if (rg() > 0.7) { ctx.stroke(); ctx.beginPath(); ctx.moveTo(x, y); angle += (rg() > 0.5 ? 0.8 : -0.8); }
            }
            ctx.stroke();
        }
        // Layer 3: Soft frozen highlight band
        const hl = ctx.createLinearGradient(w * 0.1, h * 0.15, w * 0.65, h * 0.5);
        hl.addColorStop(0, 'rgba(255,255,255,0)'); hl.addColorStop(0.4, 'rgba(230,245,255,0.15)');
        hl.addColorStop(0.6, 'rgba(230,245,255,0.15)'); hl.addColorStop(1, 'rgba(255,255,255,0)');
        ctx.fillStyle = hl; ctx.fillRect(0, 0, w, h);
    };

    R.carbon_weave = (ctx, w, h) => {
        const id = ctx.createImageData(w, h);
        for (let py = 0; py < h; py++)for (let px = 0; px < w; px++) {
            const cx = px % 6, cy = py % 6; const over = ((Math.floor(px / 3) + Math.floor(py / 3)) % 2 === 0);
            const v = over ? 35 + cx * 3 : 22 + cy * 2; const i = (py * w + px) * 4; id.data[i] = v; id.data[i + 1] = v; id.data[i + 2] = v + 2; id.data[i + 3] = 255;
        }
        ctx.putImageData(id, 0, 0);
    };

    R.living_matte = (ctx, w, h) => {
        ctx.fillStyle = '#555'; ctx.fillRect(0, 0, w, h);
        const n = _n2d(w, h, 12, 8203), id = ctx.getImageData(0, 0, w, h);
        for (let i = 0; i < w * h; i++) { const v = n[i] * 15; id.data[i * 4] += v; id.data[i * 4 + 1] += v; id.data[i * 4 + 2] += v; } ctx.putImageData(id, 0, 0);
    };

    R.nebula = (ctx, w, h) => {
        ctx.fillStyle = '#080412'; ctx.fillRect(0, 0, w, h);
        const n = _n2d(w, h, 10, 8204), n2 = _n2d(w, h, 6, 8205), id = ctx.getImageData(0, 0, w, h);
        for (let i = 0; i < w * h; i++) {
            const v1 = (n[i] + 0.5), v2 = (n2[i] + 0.5);
            id.data[i * 4] += v1 * 80; id.data[i * 4 + 1] += v2 * 30; id.data[i * 4 + 2] += v1 * 60 + v2 * 40;
        } ctx.putImageData(id, 0, 0);
        const rg = _rng(8204); for (let i = 0; i < 15; i++) {
            const x = rg() * w, y = rg() * h;
            ctx.fillStyle = `rgba(255,255,240,${0.3 + rg() * 0.5})`; ctx.fillRect(x, y, 1, 1);
        }
    };

    R.organic_metal = (ctx, w, h) => {
        const n = _n2d(w, h, 8, 8206), n2 = _n2d(w, h, 18, 8207), id = ctx.createImageData(w, h);
        for (let i = 0; i < w * h; i++) {
            const v = (n[i] * 0.6 + n2[i] * 0.4 + 0.5);
            const r = Math.floor(100 + v * 80), g = Math.floor(105 + v * 75), b = Math.floor(95 + v * 70);
            id.data[i * 4] = r; id.data[i * 4 + 1] = g; id.data[i * 4 + 2] = b; id.data[i * 4 + 3] = 255;
        } ctx.putImageData(id, 0, 0);
    };

    R.p_mercury = (ctx, w, h) => {
        const g = ctx.createLinearGradient(0, 0, w, h);
        g.addColorStop(0, '#a0a8b4'); g.addColorStop(0.2, '#c8d0dc'); g.addColorStop(0.4, '#90a0b0'); g.addColorStop(0.6, '#d0d8e4'); g.addColorStop(0.8, '#98a8b8'); g.addColorStop(1, '#b8c0cc');
        ctx.fillStyle = g; ctx.fillRect(0, 0, w, h);
        const n = _n2d(w, h, 10, 8208), id = ctx.getImageData(0, 0, w, h);
        for (let i = 0; i < w * h; i++) { const v = n[i] * 10; id.data[i * 4] += v; id.data[i * 4 + 1] += v; id.data[i * 4 + 2] += v * 1.2; } ctx.putImageData(id, 0, 0);
    };

    R.p_phantom = (ctx, w, h) => {
        ctx.fillStyle = '#101018'; ctx.fillRect(0, 0, w, h);
        const n = _n2d(w, h, 12, 8209), id = ctx.getImageData(0, 0, w, h);
        for (let i = 0; i < w * h; i++) { if (n[i] > 0) { id.data[i * 4] += n[i] * 25; id.data[i * 4 + 1] += n[i] * 28; id.data[i * 4 + 2] += n[i] * 35; } } ctx.putImageData(id, 0, 0);
    };

    R.p_volcanic = (ctx, w, h) => {
        ctx.fillStyle = '#1a0800'; ctx.fillRect(0, 0, w, h);
        const n = _n2d(w, h, 6, 8210), id = ctx.getImageData(0, 0, w, h);
        for (let i = 0; i < w * h; i++) {
            const v = (n[i] + 0.5); if (v > 0.65) {
                const a = (v - 0.65) / 0.35;
                id.data[i * 4] += a * 220; id.data[i * 4 + 1] += a * 80; id.data[i * 4 + 2] += a * 10;
            } else { id.data[i * 4] += v * 20; id.data[i * 4 + 1] += v * 12; }
        } ctx.putImageData(id, 0, 0);
    };

    R.terrain_chrome = (ctx, w, h) => {
        const n = _n2d(w, h, 8, 8211), id = ctx.createImageData(w, h);
        for (let i = 0; i < w * h; i++) {
            const v = (n[i] + 0.5); const c = Math.floor(120 + v * 100);
            id.data[i * 4] = c - 10; id.data[i * 4 + 1] = c; id.data[i * 4 + 2] = c + 10; id.data[i * 4 + 3] = 255;
        } ctx.putImageData(id, 0, 0);
    };

    // === SHOKK SERIES BASES — EXTREME ===
    R.burnt_headers = (ctx, w, h) => {
        const id = ctx.createImageData(w, h); const n = _n2d(w, h, 6, 8301);
        for (let py = 0; py < h; py++)for (let px = 0; px < w; px++) {
            const t = px / w; const nv = n[py * w + px] * 0.15; const tv = t + nv;
            let r, g, b; if (tv < 0.25) { r = 80 + tv * 200; g = 60 + tv * 100; b = 40; }
            else if (tv < 0.5) { r = 130; g = 80 + tv * 60; b = 140 + tv * 160; }
            else if (tv < 0.75) { r = 50 + tv * 80; g = 40 + tv * 60; b = 80 + tv * 120; }
            else { r = 100 + tv * 60; g = 80 + tv * 40; b = 50 + tv * 30; }
            const i = (py * w + px) * 4; id.data[i] = r; id.data[i + 1] = g; id.data[i + 2] = b; id.data[i + 3] = 255;
        } ctx.putImageData(id, 0, 0);
    };

    R.electric_ice = (ctx, w, h) => {
        ctx.fillStyle = '#081828'; ctx.fillRect(0, 0, w, h);
        const n = _n2d(w, h, 6, 8302), id = ctx.getImageData(0, 0, w, h);
        for (let i = 0; i < w * h; i++) { const v = (n[i] + 0.5); id.data[i * 4] += v * 40; id.data[i * 4 + 1] += v * 120; id.data[i * 4 + 2] += v * 200; } ctx.putImageData(id, 0, 0);
        ctx.strokeStyle = 'rgba(100,200,255,0.3)'; ctx.lineWidth = 1; const rg = _rng(8302);
        for (let i = 0; i < 5; i++) {
            ctx.beginPath(); let x = rg() * w, y = rg() * h; ctx.moveTo(x, y);
            for (let s = 0; s < 4; s++) { x += (rg() - 0.5) * w * 0.3; y += (rg() - 0.5) * h * 0.3; ctx.lineTo(x, y); } ctx.stroke();
        }
    };

    R.mercury = (ctx, w, h) => {
        const g = ctx.createLinearGradient(0, 0, w, h);
        g.addColorStop(0, '#98a4b0'); g.addColorStop(0.2, '#c8d0dc'); g.addColorStop(0.4, '#88a0b0'); g.addColorStop(0.6, '#d0d8e4'); g.addColorStop(0.8, '#90a0b4'); g.addColorStop(1, '#b8c4d0');
        ctx.fillStyle = g; ctx.fillRect(0, 0, w, h); const n = _n2d(w, h, 8, 8303), id = ctx.getImageData(0, 0, w, h);
        for (let i = 0; i < w * h; i++) { const v = n[i] * 15; id.data[i * 4] += v; id.data[i * 4 + 1] += v; id.data[i * 4 + 2] += v * 1.3; } ctx.putImageData(id, 0, 0);
    };

    R.plasma_metal = (ctx, w, h) => {
        ctx.fillStyle = '#0a0818'; ctx.fillRect(0, 0, w, h);
        const n = _n2d(w, h, 8, 8304), n2 = _n2d(w, h, 14, 8305), id = ctx.getImageData(0, 0, w, h);
        for (let i = 0; i < w * h; i++) {
            const v1 = (n[i] + 0.5), v2 = (n2[i] + 0.5);
            id.data[i * 4] += v1 * 100 + v2 * 40; id.data[i * 4 + 1] += v1 * 20 + v2 * 60; id.data[i * 4 + 2] += v1 * 160 + v2 * 80;
        } ctx.putImageData(id, 0, 0);
    };

    R.shokk_blood = (ctx, w, h) => {
        ctx.fillStyle = '#180000'; ctx.fillRect(0, 0, w, h);
        const n = _n2d(w, h, 6, 8306), id = ctx.getImageData(0, 0, w, h);
        for (let i = 0; i < w * h; i++) { const v = (n[i] + 0.5); id.data[i * 4] += v * 180; id.data[i * 4 + 1] += v * 10; id.data[i * 4 + 2] += v * 5; } ctx.putImageData(id, 0, 0);
        const cg = ctx.createRadialGradient(w / 2, h / 2, 0, w / 2, h / 2, w * 0.4);
        cg.addColorStop(0, 'rgba(200,0,0,0.25)'); cg.addColorStop(1, 'rgba(0,0,0,0)'); ctx.fillStyle = cg; ctx.fillRect(0, 0, w, h);
    };

    R.shokk_pulse = (ctx, w, h) => {
        ctx.fillStyle = '#080020'; ctx.fillRect(0, 0, w, h);
        const cx = w / 2, cy = h / 2, mr = Math.max(w, h) * 0.55;
        for (let r = 3; r < mr; r += 4) {
            const t = r / mr; const a = 0.4 - t * 0.3;
            ctx.strokeStyle = `rgba(100,40,255,${a})`; ctx.lineWidth = 1.5; ctx.beginPath(); ctx.arc(cx, cy, r, 0, 6.28); ctx.stroke();
        }
        const cg = ctx.createRadialGradient(cx, cy, 0, cx, cy, mr * 0.3);
        cg.addColorStop(0, 'rgba(140,60,255,0.4)'); cg.addColorStop(1, 'rgba(0,0,0,0)'); ctx.fillStyle = cg; ctx.fillRect(0, 0, w, h);
    };

    R.shokk_static = (ctx, w, h) => {
        const id = ctx.createImageData(w, h); const rg = _rng(8308);
        const bs = 2; for (let py = 0; py < h; py += bs)for (let px = 0; px < w; px += bs) {
            const v = Math.floor(rg() * 200 + 20); const tint = rg() > 0.9;
            for (let dy = 0; dy < bs && py + dy < h; dy++)for (let dx = 0; dx < bs && px + dx < w; dx++) {
                const i = ((py + dy) * w + (px + dx)) * 4; id.data[i] = tint ? v + 40 : v; id.data[i + 1] = tint ? v - 20 : v; id.data[i + 2] = v; id.data[i + 3] = 255;
            }
        }
        ctx.putImageData(id, 0, 0); ctx.fillStyle = 'rgba(0,0,0,0.06)'; for (let y = 0; y < h; y += 3)ctx.fillRect(0, y, w, 1);
    };

    R.shokk_venom = (ctx, w, h) => {
        ctx.fillStyle = '#040a00'; ctx.fillRect(0, 0, w, h);
        const n = _n2d(w, h, 6, 8309), id = ctx.getImageData(0, 0, w, h);
        for (let i = 0; i < w * h; i++) { const v = (n[i] + 0.5); id.data[i * 4] += v * 30; id.data[i * 4 + 1] += v * 200; id.data[i * 4 + 2] += v * 20; } ctx.putImageData(id, 0, 0);
        ctx.strokeStyle = 'rgba(0,255,60,0.2)'; ctx.lineWidth = 1; const rg = _rng(8309);
        for (let i = 0; i < 4; i++) {
            ctx.beginPath(); let x = rg() * w, y = h; ctx.moveTo(x, y);
            for (let s = 0; s < 5; s++) { x += (rg() - 0.5) * w * 0.25; y -= rg() * h * 0.2; ctx.lineTo(x, y); } ctx.stroke();
        }
    };

    R.shokk_void = (ctx, w, h) => {
        const n = _n2d(w, h, 10, 8310), id = ctx.createImageData(w, h);
        for (let i = 0; i < w * h; i++) {
            const v = (n[i] + 0.5) * 0.08; const c = Math.floor(v * 30);
            id.data[i * 4] = c; id.data[i * 4 + 1] = c; id.data[i * 4 + 2] = c + 3; id.data[i * 4 + 3] = 255;
        } ctx.putImageData(id, 0, 0);
        const cg = ctx.createRadialGradient(w / 2, h / 2, 0, w / 2, h / 2, w * 0.3);
        cg.addColorStop(0, 'rgba(0,0,0,1)'); cg.addColorStop(0.6, 'rgba(0,0,0,0.5)'); cg.addColorStop(1, 'rgba(0,0,0,0)'); ctx.fillStyle = cg; ctx.fillRect(0, 0, w, h);
    };

    R.volcanic = (ctx, w, h) => {
        ctx.fillStyle = '#1a0800'; ctx.fillRect(0, 0, w, h);
        const n = _n2d(w, h, 5, 8311), n2 = _n2d(w, h, 14, 8312), id = ctx.getImageData(0, 0, w, h);
        for (let i = 0; i < w * h; i++) {
            const v = (n[i] * 0.6 + n2[i] * 0.4 + 0.5);
            if (v > 0.6) { const a = (v - 0.6) / 0.4; id.data[i * 4] += a * 240; id.data[i * 4 + 1] += a * 100; id.data[i * 4 + 2] += a * 15; }
            else { id.data[i * 4] += v * 25; id.data[i * 4 + 1] += v * 12; id.data[i * 4 + 2] += v * 5; }
        } ctx.putImageData(id, 0, 0);
    };

    // === INJECT ===
    if (window._fusionSwatchRenderers) { Object.assign(window._fusionSwatchRenderers, R); }
    else { window._fusionSwatchRenderers = Object.assign(window._fusionSwatchRenderers || {}, R); }
    console.log(`[SWATCH-UPGRADES-3] ${Object.keys(R).length} upgraded renderers loaded`);
})();
