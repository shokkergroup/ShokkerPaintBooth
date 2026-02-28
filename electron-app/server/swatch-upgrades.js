// SWATCH UPGRADES — Procedural canvas renderers for bases + specials
// Uses same factory approach as fusion-swatches.js
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
            const d00 = Math.cos(g[i00]) * dx + Math.sin(g[i00]) * dy, d10 = Math.cos(g[i10]) * (dx - 1) + Math.sin(g[i10]) * dy;
            const d01 = Math.cos(g[i01]) * dx + Math.sin(g[i01]) * (dy - 1), d11 = Math.cos(g[i11]) * (dx - 1) + Math.sin(g[i11]) * (dy - 1);
            out[py * w + px] = (d00 * (1 - sx) + d10 * sx) * (1 - sy) + (d01 * (1 - sx) + d11 * sx) * sy;
        } return out;
    }
    function _hsl(h, s, l) {
        h = ((h % 360) + 360) % 360; s /= 100; l /= 100; const c = (1 - Math.abs(2 * l - 1)) * s, x = c * (1 - Math.abs((h / 60) % 2 - 1)), m = l - c / 2; let r, g, b;
        if (h < 60) { r = c; g = x; b = 0; } else if (h < 120) { r = x; g = c; b = 0; } else if (h < 180) { r = 0; g = c; b = x; } else if (h < 240) { r = 0; g = x; b = c; } else if (h < 300) { r = x; g = 0; b = c; } else { r = c; g = 0; b = x; }
        return [Math.round((r + m) * 255), Math.round((g + m) * 255), Math.round((b + m) * 255)];
    }

    const R = {};

    // === WEATHERED & AGED BASES ===
    R.acid_rain = (ctx, w, h) => {
        ctx.fillStyle = '#4a6858'; ctx.fillRect(0, 0, w, h); const n = _n2d(w, h, 8, 2001), id = ctx.getImageData(0, 0, w, h);
        for (let i = 0; i < w * h; i++) { const v = n[i]; if (v > 0.2) { const a = (v - 0.2) / 0.8; const j = i * 4; id.data[j] = Math.floor(id.data[j] * (1 - a) + 160 * a); id.data[j + 1] = Math.floor(id.data[j + 1] * (1 - a) + 180 * a); id.data[j + 2] = Math.floor(id.data[j + 2] * (1 - a) + 100 * a); } }; ctx.putImageData(id, 0, 0);
        ctx.fillStyle = 'rgba(120,160,80,0.15)'; const rg = _rng(2001); for (let i = 0; i < 20; i++) { ctx.beginPath(); ctx.arc(rg() * w, rg() * h, 1 + rg() * 3, 0, 6.28); ctx.fill(); }
    };

    R.desert_worn = (ctx, w, h) => {
        const g = ctx.createLinearGradient(0, 0, w, h); g.addColorStop(0, '#c8a868'); g.addColorStop(1, '#8a7048'); ctx.fillStyle = g; ctx.fillRect(0, 0, w, h);
        const n = _n2d(w, h, 6, 2002), id = ctx.getImageData(0, 0, w, h); for (let i = 0; i < w * h; i++) { const v = n[i] * 25; id.data[i * 4] += v; id.data[i * 4 + 1] += v * 0.8; id.data[i * 4 + 2] += v * 0.4; } ctx.putImageData(id, 0, 0);
    };

    R.galvanized = (ctx, w, h) => {
        ctx.fillStyle = '#9aa0a8'; ctx.fillRect(0, 0, w, h); const n = _n2d(w, h, 10, 2003), id = ctx.getImageData(0, 0, w, h);
        for (let i = 0; i < w * h; i++) { const v = (n[i] + 0.5); const crystalline = Math.abs(Math.sin(v * 12)) * 30; id.data[i * 4] += crystalline; id.data[i * 4 + 1] += crystalline; id.data[i * 4 + 2] += crystalline * 1.1; } ctx.putImageData(id, 0, 0);
    };

    R.heat_treated = (ctx, w, h) => {
        const id = ctx.createImageData(w, h); for (let py = 0; py < h; py++)for (let px = 0; px < w; px++) {
            const t = px / w; const [r, g, b] = t < 0.25 ? _hsl(45, 40, 30 + t * 80) : t < 0.5 ? _hsl(30 + t * 40, 50, 35) : t < 0.75 ? _hsl(260, 40, 35 + t * 10) : _hsl(220, 35, 40);
            const i = (py * w + px) * 4; id.data[i] = r; id.data[i + 1] = g; id.data[i + 2] = b; id.data[i + 3] = 255;
        } ctx.putImageData(id, 0, 0);
    };

    R.oxidized_copper = (ctx, w, h) => {
        const n = _n2d(w, h, 8, 2005), id = ctx.createImageData(w, h);
        for (let i = 0; i < w * h; i++) {
            const v = (n[i] + 0.5); let r, g, b; if (v < 0.4) { r = 80 + v * 120; g = 160 + v * 60; b = 130 + v * 40; } else { r = 160 + v * 40; g = 100 + v * 30; b = 60 + v * 20; }
            id.data[i * 4] = r; id.data[i * 4 + 1] = g; id.data[i * 4 + 2] = b; id.data[i * 4 + 3] = 255;
        } ctx.putImageData(id, 0, 0);
    };

    R.patina_bronze = (ctx, w, h) => {
        const n = _n2d(w, h, 10, 2006), id = ctx.createImageData(w, h);
        for (let i = 0; i < w * h; i++) {
            const v = (n[i] + 0.5); const r = Math.floor(100 + v * 80), g = Math.floor(80 + v * 60 + (v > 0.6 ? 40 : 0)), b = Math.floor(40 + v * 30 + (v > 0.6 ? 50 : 0));
            id.data[i * 4] = r; id.data[i * 4 + 1] = g; id.data[i * 4 + 2] = b; id.data[i * 4 + 3] = 255;
        } ctx.putImageData(id, 0, 0);
    };

    R.rugged = (ctx, w, h) => {
        ctx.fillStyle = '#5a5550'; ctx.fillRect(0, 0, w, h); const n = _n2d(w, h, 4, 2007), n2 = _n2d(w, h, 12, 2008), id = ctx.getImageData(0, 0, w, h);
        for (let i = 0; i < w * h; i++) { const v = (n[i] * 0.6 + n2[i] * 0.4) * 35; id.data[i * 4] += v; id.data[i * 4 + 1] += v * 0.9; id.data[i * 4 + 2] += v * 0.8; } ctx.putImageData(id, 0, 0);
    };

    R.salt_corroded = (ctx, w, h) => {
        ctx.fillStyle = '#607080'; ctx.fillRect(0, 0, w, h); const n = _n2d(w, h, 6, 2009), id = ctx.getImageData(0, 0, w, h);
        for (let i = 0; i < w * h; i++) { if (n[i] > 0.15) { const a = (n[i] - 0.15) / 0.85; const j = i * 4; id.data[j] = Math.floor(id.data[j] * (1 - a) + 200 * a); id.data[j + 1] = Math.floor(id.data[j + 1] * (1 - a) + 195 * a); id.data[j + 2] = Math.floor(id.data[j + 2] * (1 - a) + 180 * a); } } ctx.putImageData(id, 0, 0);
    };

    R.sun_baked = (ctx, w, h) => {
        const g = ctx.createLinearGradient(0, 0, 0, h); g.addColorStop(0, '#c8a070'); g.addColorStop(1, '#8a6a48'); ctx.fillStyle = g; ctx.fillRect(0, 0, w, h);
        const n = _n2d(w, h, 8, 2010), id = ctx.getImageData(0, 0, w, h); for (let py = 0; py < h; py++)for (let px = 0; px < w; px++) {
            const fade = 1 - py / h; const v = n[py * w + px] * 20 * fade; const i = (py * w + px) * 4; id.data[i] += v; id.data[i + 1] += v * 0.7; id.data[i + 2] -= v * 0.5;
        } ctx.putImageData(id, 0, 0);
    };

    R.vintage_chrome = (ctx, w, h) => {
        const g = ctx.createLinearGradient(0, 0, w, h); g.addColorStop(0, '#b8c0c8'); g.addColorStop(0.3, '#d8dce0'); g.addColorStop(0.6, '#a0a8b0'); g.addColorStop(1, '#c0c8d0');
        ctx.fillStyle = g; ctx.fillRect(0, 0, w, h); const n = _n2d(w, h, 6, 2011), id = ctx.getImageData(0, 0, w, h);
        for (let i = 0; i < w * h; i++) { if (n[i] > 0.3) { const j = i * 4; const pit = n[i] * 15; id.data[j] -= pit; id.data[j + 1] -= pit; id.data[j + 2] -= pit * 0.8; } } ctx.putImageData(id, 0, 0);
    };

    // === EXOTIC METAL BASES ===
    R.anodized = (ctx, w, h) => {
        const id = ctx.createImageData(w, h); for (let py = 0; py < h; py++)for (let px = 0; px < w; px++) {
            const t = (py / h * 0.5 + px / w * 0.5); const [r, g, b] = _hsl(220 + t * 30, 55, 45 + t * 15); const i = (py * w + px) * 4; id.data[i] = r; id.data[i + 1] = g; id.data[i + 2] = b; id.data[i + 3] = 255;
        } ctx.putImageData(id, 0, 0);
        ctx.strokeStyle = 'rgba(255,255,255,0.06)'; ctx.lineWidth = 0.5; for (let y = 0; y < h; y += 2) { ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(w, y); ctx.stroke(); }
    };

    R.brushed_aluminum = (ctx, w, h) => {
        ctx.fillStyle = '#b0b4b8'; ctx.fillRect(0, 0, w, h); const id = ctx.getImageData(0, 0, w, h); const rg = _rng(2102);
        for (let py = 0; py < h; py++) { const lineV = (rg() - 0.5) * 20; for (let px = 0; px < w; px++) { const i = (py * w + px) * 4; id.data[i] += lineV + rg() * 8; id.data[i + 1] += lineV + rg() * 8; id.data[i + 2] += lineV + rg() * 10; } } ctx.putImageData(id, 0, 0);
    };

    R.brushed_titanium = (ctx, w, h) => {
        ctx.fillStyle = '#8890a0'; ctx.fillRect(0, 0, w, h); const id = ctx.getImageData(0, 0, w, h); const rg = _rng(2103);
        for (let py = 0; py < h; py++) { const lineV = (rg() - 0.5) * 18; for (let px = 0; px < w; px++) { const i = (py * w + px) * 4; id.data[i] += lineV + rg() * 6; id.data[i + 1] += lineV + rg() * 6; id.data[i + 2] += lineV + rg() * 10; } } ctx.putImageData(id, 0, 0);
    };

    R.cobalt_metal = (ctx, w, h) => {
        const g = ctx.createLinearGradient(0, 0, w, h); g.addColorStop(0, '#384880'); g.addColorStop(0.4, '#506098'); g.addColorStop(0.7, '#3a4a78'); g.addColorStop(1, '#485890'); ctx.fillStyle = g; ctx.fillRect(0, 0, w, h);
        ctx.strokeStyle = 'rgba(160,180,255,0.08)'; ctx.lineWidth = 0.5; for (let y = 0; y < h; y += 2) { ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(w, y); ctx.stroke(); }
    };

    R.diamond_coat = (ctx, w, h) => {
        ctx.fillStyle = '#d0d8e0'; ctx.fillRect(0, 0, w, h); const rg = _rng(2105);
        for (let i = 0; i < Math.floor(w * h * 0.02); i++) {
            const x = rg() * w, y = rg() * h, s = 0.5 + rg() * 1.5; const gr = ctx.createRadialGradient(x, y, 0, x, y, s);
            gr.addColorStop(0, 'rgba(255,255,255,0.9)'); gr.addColorStop(1, 'rgba(200,210,230,0)'); ctx.fillStyle = gr; ctx.fillRect(x - s, y - s, s * 2, s * 2);
        }
    };

    R.frozen = (ctx, w, h) => {
        const g = ctx.createLinearGradient(0, 0, w, h); g.addColorStop(0, '#a0d0e8'); g.addColorStop(0.5, '#d0e8f4'); g.addColorStop(1, '#88c0d8'); ctx.fillStyle = g; ctx.fillRect(0, 0, w, h);
        const n = _n2d(w, h, 6, 2106), id = ctx.getImageData(0, 0, w, h); for (let i = 0; i < w * h; i++) { if (n[i] > 0.2) { const j = i * 4; id.data[j] += 15; id.data[j + 1] += 18; id.data[j + 2] += 20; } } ctx.putImageData(id, 0, 0);
    };

    R.liquid_titanium = (ctx, w, h) => {
        const g = ctx.createLinearGradient(0, 0, w, h); g.addColorStop(0, '#90a0b8'); g.addColorStop(0.3, '#c0c8d8'); g.addColorStop(0.5, '#8898b0'); g.addColorStop(0.8, '#b0b8c8'); g.addColorStop(1, '#98a8b8');
        ctx.fillStyle = g; ctx.fillRect(0, 0, w, h); const n = _n2d(w, h, 10, 2107), id = ctx.getImageData(0, 0, w, h);
        for (let i = 0; i < w * h; i++) { const v = n[i] * 12; id.data[i * 4] += v; id.data[i * 4 + 1] += v; id.data[i * 4 + 2] += v * 1.3; } ctx.putImageData(id, 0, 0);
    };

    R.platinum = (ctx, w, h) => {
        const g = ctx.createLinearGradient(0, 0, w, h); g.addColorStop(0, '#c8ccd4'); g.addColorStop(0.3, '#e0e4e8'); g.addColorStop(0.6, '#b8bcc4'); g.addColorStop(1, '#d0d4d8'); ctx.fillStyle = g; ctx.fillRect(0, 0, w, h);
        ctx.strokeStyle = 'rgba(255,255,255,0.1)'; ctx.lineWidth = 0.5; for (let y = 0; y < h; y += 3) { ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(w, y + Math.sin(y * 0.3) * 1.5); ctx.stroke(); }
    };

    R.raw_aluminum = (ctx, w, h) => {
        ctx.fillStyle = '#a8aeb4'; ctx.fillRect(0, 0, w, h); const n = _n2d(w, h, 4, 2109); const id = ctx.getImageData(0, 0, w, h);
        for (let i = 0; i < w * h; i++) { const v = n[i] * 22; id.data[i * 4] += v; id.data[i * 4 + 1] += v; id.data[i * 4 + 2] += v; } ctx.putImageData(id, 0, 0);
    };

    R.rose_gold = (ctx, w, h) => {
        const g = ctx.createLinearGradient(0, 0, w, h); g.addColorStop(0, '#c8908a'); g.addColorStop(0.3, '#daa89e'); g.addColorStop(0.6, '#c09088'); g.addColorStop(1, '#d0a098'); ctx.fillStyle = g; ctx.fillRect(0, 0, w, h);
        ctx.strokeStyle = 'rgba(255,220,210,0.1)'; ctx.lineWidth = 0.5; for (let y = 0; y < h; y += 2) { ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(w, y); ctx.stroke(); }
    };

    R.titanium_raw = (ctx, w, h) => {
        ctx.fillStyle = '#78808a'; ctx.fillRect(0, 0, w, h); const n = _n2d(w, h, 5, 2111), id = ctx.getImageData(0, 0, w, h); const rg = _rng(2111);
        for (let py = 0; py < h; py++) { const lv = (rg() - 0.5) * 12; for (let px = 0; px < w; px++) { const i = (py * w + px) * 4; const nv = n[py * w + px] * 15; id.data[i] += lv + nv; id.data[i + 1] += lv + nv; id.data[i + 2] += lv + nv * 1.3; } } ctx.putImageData(id, 0, 0);
    };

    R.tungsten = (ctx, w, h) => {
        ctx.fillStyle = '#585c62'; ctx.fillRect(0, 0, w, h); const n = _n2d(w, h, 6, 2112), id = ctx.getImageData(0, 0, w, h);
        for (let i = 0; i < w * h; i++) { const v = n[i] * 18; id.data[i * 4] += v; id.data[i * 4 + 1] += v; id.data[i * 4 + 2] += v * 1.1; } ctx.putImageData(id, 0, 0);
    };

    // === DARK & GOTHIC SPECIALS ===
    R.banshee = (ctx, w, h) => {
        ctx.fillStyle = '#181c28'; ctx.fillRect(0, 0, w, h); const n = _n2d(w, h, 8, 3001), id = ctx.getImageData(0, 0, w, h);
        for (let i = 0; i < w * h; i++) { const v = n[i]; if (v > 0.1) { const a = (v - 0.1) * 0.6; const j = i * 4; id.data[j] += a * 60; id.data[j + 1] += a * 70; id.data[j + 2] += a * 100; } } ctx.putImageData(id, 0, 0);
        ctx.strokeStyle = 'rgba(140,170,220,0.15)'; ctx.lineWidth = 1; for (let i = 0; i < 4; i++) { ctx.beginPath(); for (let x = 0; x < w; x++) { const y = h * (0.3 + i * 0.15) + Math.sin(x * 0.15 + i) * h * 0.1; x === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y); } ctx.stroke(); }
    };

    R.blood_oath = (ctx, w, h) => {
        ctx.fillStyle = '#1a0808'; ctx.fillRect(0, 0, w, h); const n = _n2d(w, h, 8, 3002); const id = ctx.getImageData(0, 0, w, h);
        for (let i = 0; i < w * h; i++) { const v = (n[i] + 0.5); id.data[i * 4] += v * 100; id.data[i * 4 + 1] += v * 10; id.data[i * 4 + 2] += v * 8; } ctx.putImageData(id, 0, 0);
        const cg = ctx.createRadialGradient(w / 2, h / 2, 0, w / 2, h / 2, w * 0.4); cg.addColorStop(0, 'rgba(160,0,0,0.3)'); cg.addColorStop(1, 'rgba(0,0,0,0)'); ctx.fillStyle = cg; ctx.fillRect(0, 0, w, h);
    };

    R.catacombs = (ctx, w, h) => {
        ctx.fillStyle = '#28201a'; ctx.fillRect(0, 0, w, h); const n = _n2d(w, h, 6, 3003), n2 = _n2d(w, h, 16, 3004), id = ctx.getImageData(0, 0, w, h);
        for (let i = 0; i < w * h; i++) { const v = (n[i] * 0.6 + n2[i] * 0.4) * 25; id.data[i * 4] += v; id.data[i * 4 + 1] += v * 0.85; id.data[i * 4 + 2] += v * 0.7; } ctx.putImageData(id, 0, 0);
    };

    R.cursed = (ctx, w, h) => {
        ctx.fillStyle = '#0c0810'; ctx.fillRect(0, 0, w, h); const n = _n2d(w, h, 10, 3005);
        const cg = ctx.createRadialGradient(w / 2, h / 2, 0, w / 2, h / 2, w * 0.5); cg.addColorStop(0, 'rgba(80,0,120,0.4)'); cg.addColorStop(0.6, 'rgba(40,0,60,0.2)'); cg.addColorStop(1, 'rgba(0,0,0,0)'); ctx.fillStyle = cg; ctx.fillRect(0, 0, w, h);
        const id = ctx.getImageData(0, 0, w, h); for (let i = 0; i < w * h; i++) { if (n[i] > 0.25) { const j = i * 4; id.data[j] += 20; id.data[j + 2] += 30; } } ctx.putImageData(id, 0, 0);
    };

    R.dark_ritual = (ctx, w, h) => {
        ctx.fillStyle = '#100818'; ctx.fillRect(0, 0, w, h); ctx.strokeStyle = 'rgba(100,50,150,0.3)'; ctx.lineWidth = 0.8;
        const cx = w / 2, cy = h / 2; for (let r = 4; r < w * 0.45; r += 6) { ctx.beginPath(); ctx.arc(cx, cy, r, 0, 6.28); ctx.stroke(); }
        ctx.strokeStyle = 'rgba(80,40,120,0.25)'; for (let a = 0; a < 6; a++) { const ang = a * Math.PI / 3; ctx.beginPath(); ctx.moveTo(cx, cy); ctx.lineTo(cx + Math.cos(ang) * w * 0.45, cy + Math.sin(ang) * h * 0.45); ctx.stroke(); }
    };

    R.death_metal = (ctx, w, h) => {
        ctx.fillStyle = '#0a0a0a'; ctx.fillRect(0, 0, w, h); const n = _n2d(w, h, 4, 3007), id = ctx.getImageData(0, 0, w, h);
        for (let i = 0; i < w * h; i++) { const v = Math.abs(n[i]) * 20; id.data[i * 4] += v; id.data[i * 4 + 1] += v; id.data[i * 4 + 2] += v; } ctx.putImageData(id, 0, 0);
        ctx.strokeStyle = 'rgba(200,200,200,0.08)'; ctx.lineWidth = 0.5; const rg = _rng(3007); for (let i = 0; i < 8; i++) { ctx.beginPath(); let x = rg() * w, y = rg() * h; ctx.moveTo(x, y); for (let s = 0; s < 3; s++) { x += (rg() - 0.5) * w * 0.4; y += (rg() - 0.5) * h * 0.4; ctx.lineTo(x, y); } ctx.stroke(); }
    };

    R.demon_forge = (ctx, w, h) => {
        ctx.fillStyle = '#1a0800'; ctx.fillRect(0, 0, w, h); const n = _n2d(w, h, 6, 3008), id = ctx.getImageData(0, 0, w, h);
        for (let i = 0; i < w * h; i++) { const v = (n[i] + 0.5); if (v > 0.6) { const a = (v - 0.6) / 0.4; id.data[i * 4] += a * 200; id.data[i * 4 + 1] += a * 60; id.data[i * 4 + 2] += a * 10; } } ctx.putImageData(id, 0, 0);
    };

    R.eclipse = (ctx, w, h) => {
        ctx.fillStyle = '#040408'; ctx.fillRect(0, 0, w, h); const cx = w / 2, cy = h / 2, r = Math.min(w, h) * 0.3;
        const rim = ctx.createRadialGradient(cx, cy, r * 0.85, cx, cy, r * 1.3); rim.addColorStop(0, 'rgba(0,0,0,0)'); rim.addColorStop(0.4, 'rgba(255,140,40,0.5)'); rim.addColorStop(0.7, 'rgba(255,200,100,0.3)'); rim.addColorStop(1, 'rgba(0,0,0,0)'); ctx.fillStyle = rim; ctx.fillRect(0, 0, w, h);
        ctx.fillStyle = '#020204'; ctx.beginPath(); ctx.arc(cx, cy, r * 0.85, 0, 6.28); ctx.fill();
    };

    R.gargoyle = (ctx, w, h) => {
        ctx.fillStyle = '#484848'; ctx.fillRect(0, 0, w, h); const n = _n2d(w, h, 5, 3010), n2 = _n2d(w, h, 14, 3011), id = ctx.getImageData(0, 0, w, h);
        for (let i = 0; i < w * h; i++) { const v = (n[i] * 0.5 + n2[i] * 0.5) * 20; id.data[i * 4] += v; id.data[i * 4 + 1] += v * 1.05; id.data[i * 4 + 2] += v * 0.9; } ctx.putImageData(id, 0, 0);
    };

    R.graveyard = (ctx, w, h) => {
        ctx.fillStyle = '#1a2018'; ctx.fillRect(0, 0, w, h); const n = _n2d(w, h, 10, 3012), id = ctx.getImageData(0, 0, w, h);
        for (let py = 0; py < h; py++)for (let px = 0; px < w; px++) { const fog = py < h * 0.6 ? 0 : (py / h - 0.6) / 0.4; const v = n[py * w + px] * 15 + fog * 40; const i = (py * w + px) * 4; id.data[i] += v * 0.7; id.data[i + 1] += v * 0.8; id.data[i + 2] += v * 0.6; } ctx.putImageData(id, 0, 0);
    };

    R.haunted = (ctx, w, h) => {
        ctx.fillStyle = '#101820'; ctx.fillRect(0, 0, w, h); const n = _n2d(w, h, 12, 3013);
        const id = ctx.getImageData(0, 0, w, h); for (let i = 0; i < w * h; i++) { const v = n[i]; if (v > 0) { id.data[i * 4] += v * 30; id.data[i * 4 + 1] += v * 40; id.data[i * 4 + 2] += v * 55; } } ctx.putImageData(id, 0, 0);
        const rg = _rng(3013); ctx.fillStyle = 'rgba(100,140,180,0.06)'; for (let i = 0; i < 6; i++) { ctx.beginPath(); ctx.arc(rg() * w, rg() * h, 3 + rg() * 8, 0, 6.28); ctx.fill(); }
    };

    R.hellhound = (ctx, w, h) => {
        ctx.fillStyle = '#1a0a00'; ctx.fillRect(0, 0, w, h); const n = _n2d(w, h, 5, 3014), id = ctx.getImageData(0, 0, w, h);
        for (let i = 0; i < w * h; i++) { const v = (n[i] + 0.5); id.data[i * 4] += v * 140; id.data[i * 4 + 1] += v * 40; id.data[i * 4 + 2] += v * 5; } ctx.putImageData(id, 0, 0);
        ctx.strokeStyle = 'rgba(255,100,0,0.2)'; ctx.lineWidth = 1; const rg = _rng(3014); for (let i = 0; i < 5; i++) { ctx.beginPath(); let x = rg() * w, y = h; ctx.moveTo(x, y); for (let s = 0; s < 4; s++) { x += (rg() - 0.5) * w * 0.3; y -= rg() * h * 0.25; ctx.lineTo(x, y); } ctx.stroke(); }
    };

    R.iron_maiden = (ctx, w, h) => {
        ctx.fillStyle = '#383838'; ctx.fillRect(0, 0, w, h); const n = _n2d(w, h, 4, 3015), id = ctx.getImageData(0, 0, w, h);
        for (let i = 0; i < w * h; i++) { const v = n[i] * 15; id.data[i * 4] += v; id.data[i * 4 + 1] += v * 0.95; id.data[i * 4 + 2] += v * 0.9; } ctx.putImageData(id, 0, 0);
        ctx.fillStyle = 'rgba(90,90,80,0.6)'; const s = Math.max(6, w / 5); for (let y = s; y < h; y += s)for (let x = s; x < w; x += s) { ctx.beginPath(); ctx.arc(x, y, 1.5, 0, 6.28); ctx.fill(); }
    };

    R.lich_king = (ctx, w, h) => {
        ctx.fillStyle = '#0a1020'; ctx.fillRect(0, 0, w, h); const n = _n2d(w, h, 8, 3016);
        const cg = ctx.createRadialGradient(w / 2, h * 0.3, 0, w / 2, h * 0.3, w * 0.5); cg.addColorStop(0, 'rgba(80,160,255,0.3)'); cg.addColorStop(0.5, 'rgba(40,80,180,0.15)'); cg.addColorStop(1, 'rgba(0,0,0,0)'); ctx.fillStyle = cg; ctx.fillRect(0, 0, w, h);
        const id = ctx.getImageData(0, 0, w, h); for (let i = 0; i < w * h; i++) { if (n[i] > 0.15) { id.data[i * 4] += 15; id.data[i * 4 + 1] += 25; id.data[i * 4 + 2] += 40; } } ctx.putImageData(id, 0, 0);
    };

    R.necrotic = (ctx, w, h) => {
        const n = _n2d(w, h, 6, 3017), id = ctx.createImageData(w, h);
        for (let i = 0; i < w * h; i++) {
            const v = (n[i] + 0.5); const r = Math.floor(30 + v * 40), g = Math.floor(25 + v * 25 + (v > 0.7 ? 20 : 0)), b = Math.floor(15 + v * 15);
            id.data[i * 4] = r; id.data[i * 4 + 1] = g; id.data[i * 4 + 2] = b; id.data[i * 4 + 3] = 255;
        } ctx.putImageData(id, 0, 0);
    };

    R.nightmare = (ctx, w, h) => {
        ctx.fillStyle = '#0a0008'; ctx.fillRect(0, 0, w, h); const n = _n2d(w, h, 10, 3018), id = ctx.getImageData(0, 0, w, h);
        for (let i = 0; i < w * h; i++) { const v = n[i]; if (v > 0) { id.data[i * 4] += v * 60; id.data[i * 4 + 2] += v * 40; } } ctx.putImageData(id, 0, 0);
        ctx.strokeStyle = 'rgba(180,0,80,0.12)'; ctx.lineWidth = 1; for (let i = 0; i < h; i += 4) { ctx.beginPath(); ctx.moveTo(0, i); ctx.lineTo(w, i + Math.sin(i * 0.3) * 3); ctx.stroke(); }
    };

    R.possessed = (ctx, w, h) => {
        ctx.fillStyle = '#100008'; ctx.fillRect(0, 0, w, h); const n = _n2d(w, h, 8, 3019);
        const id = ctx.getImageData(0, 0, w, h); for (let i = 0; i < w * h; i++) { const v = (n[i] + 0.5); if (v > 0.5) { id.data[i * 4] += v * 50; id.data[i * 4 + 2] += v * 80; } } ctx.putImageData(id, 0, 0);
        const cg = ctx.createRadialGradient(w / 2, h / 2, 0, w / 2, h / 2, w * 0.3); cg.addColorStop(0, 'rgba(200,0,100,0.25)'); cg.addColorStop(1, 'rgba(0,0,0,0)'); ctx.fillStyle = cg; ctx.fillRect(0, 0, w, h);
    };

    R.reaper = (ctx, w, h) => {
        ctx.fillStyle = '#080808'; ctx.fillRect(0, 0, w, h); const n = _n2d(w, h, 10, 3020), id = ctx.getImageData(0, 0, w, h);
        for (let py = 0; py < h; py++)for (let px = 0; px < w; px++) { const v = n[py * w + px] * 12; const i = (py * w + px) * 4; id.data[i] += v; id.data[i + 1] += v; id.data[i + 2] += v; } ctx.putImageData(id, 0, 0);
        ctx.strokeStyle = 'rgba(60,60,70,0.3)'; ctx.lineWidth = 1.5; ctx.beginPath(); ctx.moveTo(w * 0.5, h * 0.1); ctx.quadraticCurveTo(w * 0.2, h * 0.4, w * 0.5, h * 0.9); ctx.stroke();
    };

    R.shadow_realm = (ctx, w, h) => {
        const n = _n2d(w, h, 12, 3021), id = ctx.createImageData(w, h);
        for (let i = 0; i < w * h; i++) { const v = (n[i] + 0.5) * 0.15; const c = Math.floor(v * 60); id.data[i * 4] = c; id.data[i * 4 + 1] = c; id.data[i * 4 + 2] = c + 5; id.data[i * 4 + 3] = 255; } ctx.putImageData(id, 0, 0);
    };

    R.spectral = (ctx, w, h) => {
        ctx.fillStyle = '#182030'; ctx.fillRect(0, 0, w, h); const n = _n2d(w, h, 10, 3022), id = ctx.getImageData(0, 0, w, h);
        for (let i = 0; i < w * h; i++) { const v = n[i]; if (v > 0) { id.data[i * 4] += v * 40; id.data[i * 4 + 1] += v * 50; id.data[i * 4 + 2] += v * 70; } } ctx.putImageData(id, 0, 0);
        ctx.globalAlpha = 0.08; ctx.fillStyle = '#8090b0'; ctx.fillRect(0, 0, w, h); ctx.globalAlpha = 1;
    };

    R.voodoo = (ctx, w, h) => {
        ctx.fillStyle = '#180820'; ctx.fillRect(0, 0, w, h); const n = _n2d(w, h, 8, 3023);
        const id = ctx.getImageData(0, 0, w, h); for (let i = 0; i < w * h; i++) { const v = (n[i] + 0.5); id.data[i * 4] += v * 30; id.data[i * 4 + 1] += v * 10; id.data[i * 4 + 2] += v * 40; } ctx.putImageData(id, 0, 0);
        const rg = _rng(3023); ctx.fillStyle = 'rgba(160,60,200,0.15)'; for (let i = 0; i < 8; i++) { ctx.beginPath(); ctx.arc(rg() * w, rg() * h, 1 + rg() * 2, 0, 6.28); ctx.fill(); }
    };

    R.weathered_paint = (ctx, w, h) => {
        const g = ctx.createLinearGradient(0, 0, 0, h); g.addColorStop(0, '#8a7a68'); g.addColorStop(1, '#6a5a48'); ctx.fillStyle = g; ctx.fillRect(0, 0, w, h);
        const n = _n2d(w, h, 5, 3024), id = ctx.getImageData(0, 0, w, h); for (let i = 0; i < w * h; i++) { if (n[i] > 0.2) { const j = i * 4; const a = (n[i] - 0.2) * 30; id.data[j] += a; id.data[j + 1] += a * 0.9; id.data[j + 2] += a * 0.7; } } ctx.putImageData(id, 0, 0);
    };

    R.wraith = (ctx, w, h) => {
        ctx.fillStyle = '#101418'; ctx.fillRect(0, 0, w, h); const n = _n2d(w, h, 12, 3025);
        for (let i = 0; i < 3; i++) {
            const y = h * (0.2 + i * 0.25); const g = ctx.createRadialGradient(w / 2, y, 0, w / 2, y, w * 0.4);
            g.addColorStop(0, 'rgba(60,80,100,0.15)'); g.addColorStop(1, 'rgba(0,0,0,0)'); ctx.fillStyle = g; ctx.fillRect(0, 0, w, h);
        }
    };

    // === SATIN & WRAP BASES ===
    R.brushed_wrap = (ctx, w, h) => {
        ctx.fillStyle = '#707880'; ctx.fillRect(0, 0, w, h); const id = ctx.getImageData(0, 0, w, h); const rg = _rng(4001);
        for (let py = 0; py < h; py++) { const lv = (rg() - 0.5) * 15; for (let px = 0; px < w; px++) { const i = (py * w + px) * 4; id.data[i] += lv; id.data[i + 1] += lv; id.data[i + 2] += lv; } } ctx.putImageData(id, 0, 0);
    };

    R.chrome_wrap = (ctx, w, h) => { const g = ctx.createLinearGradient(0, 0, w, h); g.addColorStop(0, '#c0c8d4'); g.addColorStop(0.3, '#e0e4ec'); g.addColorStop(0.5, '#a8b0bc'); g.addColorStop(0.7, '#d4d8e0'); g.addColorStop(1, '#b8c0cc'); ctx.fillStyle = g; ctx.fillRect(0, 0, w, h); };

    R.color_flip_wrap = (ctx, w, h) => {
        const id = ctx.createImageData(w, h); for (let py = 0; py < h; py++)for (let px = 0; px < w; px++) {
            const t = (py / h * 0.5 + px / w * 0.5); const [r, g, b] = _hsl(180 + t * 120, 50, 45); const i = (py * w + px) * 4; id.data[i] = r; id.data[i + 1] = g; id.data[i + 2] = b; id.data[i + 3] = 255;
        } ctx.putImageData(id, 0, 0);
    };

    R.frozen_matte = (ctx, w, h) => {
        ctx.fillStyle = '#c8d8e4'; ctx.fillRect(0, 0, w, h); const n = _n2d(w, h, 8, 4004), id = ctx.getImageData(0, 0, w, h);
        for (let i = 0; i < w * h; i++) { const v = n[i] * 8; id.data[i * 4] += v; id.data[i * 4 + 1] += v; id.data[i * 4 + 2] += v * 1.2; } ctx.putImageData(id, 0, 0);
    };

    R.gloss_wrap = (ctx, w, h) => {
        const g = ctx.createLinearGradient(0, 0, w, h); g.addColorStop(0, '#4a6a4a'); g.addColorStop(0.4, '#6a8a6a'); g.addColorStop(0.6, '#8aaa8a'); g.addColorStop(1, '#5a7a5a'); ctx.fillStyle = g; ctx.fillRect(0, 0, w, h);
        const hl = ctx.createLinearGradient(0, 0, w * 0.7, h * 0.5); hl.addColorStop(0, 'rgba(255,255,255,0)'); hl.addColorStop(0.5, 'rgba(255,255,255,0.15)'); hl.addColorStop(1, 'rgba(255,255,255,0)'); ctx.fillStyle = hl; ctx.fillRect(0, 0, w, h);
    };

    R.liquid_wrap = (ctx, w, h) => {
        const g = ctx.createLinearGradient(0, 0, w, h); g.addColorStop(0, '#3a5070'); g.addColorStop(0.5, '#506888'); g.addColorStop(1, '#3a4a68'); ctx.fillStyle = g; ctx.fillRect(0, 0, w, h);
        const n = _n2d(w, h, 10, 4006), id = ctx.getImageData(0, 0, w, h); for (let i = 0; i < w * h; i++) { const v = n[i] * 10; id.data[i * 4] += v; id.data[i * 4 + 1] += v * 1.2; id.data[i * 4 + 2] += v * 1.5; } ctx.putImageData(id, 0, 0);
    };

    R.matte_wrap = (ctx, w, h) => {
        ctx.fillStyle = '#555'; ctx.fillRect(0, 0, w, h); const n = _n2d(w, h, 4, 4007), id = ctx.getImageData(0, 0, w, h);
        for (let i = 0; i < w * h; i++) { const v = n[i] * 8; id.data[i * 4] += v; id.data[i * 4 + 1] += v; id.data[i * 4 + 2] += v; } ctx.putImageData(id, 0, 0);
    };

    R.satin_wrap = (ctx, w, h) => { const g = ctx.createLinearGradient(0, 0, w, h); g.addColorStop(0, '#787878'); g.addColorStop(0.5, '#909090'); g.addColorStop(1, '#6a6a6a'); ctx.fillStyle = g; ctx.fillRect(0, 0, w, h); };

    R.stealth_wrap = (ctx, w, h) => {
        ctx.fillStyle = '#1a1a1e'; ctx.fillRect(0, 0, w, h); const n = _n2d(w, h, 8, 4009), id = ctx.getImageData(0, 0, w, h);
        for (let i = 0; i < w * h; i++) { const v = n[i] * 6; id.data[i * 4] += v; id.data[i * 4 + 1] += v; id.data[i * 4 + 2] += v; } ctx.putImageData(id, 0, 0);
    };

    R.textured_wrap = (ctx, w, h) => {
        ctx.fillStyle = '#606468'; ctx.fillRect(0, 0, w, h); const n = _n2d(w, h, 3, 4010), n2 = _n2d(w, h, 10, 4011), id = ctx.getImageData(0, 0, w, h);
        for (let i = 0; i < w * h; i++) { const v = (n[i] * 0.7 + n2[i] * 0.3) * 18; id.data[i * 4] += v; id.data[i * 4 + 1] += v; id.data[i * 4 + 2] += v; } ctx.putImageData(id, 0, 0);
    };

    // === INJECT ===
    if (typeof window._fusionSwatchRenderers === 'object') { Object.assign(window._fusionSwatchRenderers, R); }
    else { window._fusionSwatchRenderers = Object.assign(window._fusionSwatchRenderers || {}, R); }
    console.log(`[SWATCH-UPGRADES] ${Object.keys(R).length} upgraded renderers loaded`);
})();
