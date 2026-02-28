// SWATCH UPGRADES PART 2 — Racing, OEM, Industrial, Chrome, Gradients, Multis
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

    // === CHROME & MIRROR BASES ===
    function _chromeFn(seed, stops) {
        return (ctx, w, h) => {
            const g = ctx.createLinearGradient(0, 0, w, h); stops.forEach(s => g.addColorStop(s[0], s[1])); ctx.fillStyle = g; ctx.fillRect(0, 0, w, h);
            ctx.strokeStyle = 'rgba(255,255,255,0.08)'; ctx.lineWidth = 0.5; for (let y = 0; y < h; y += 2) { ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(w, y + Math.sin(y * 0.4) * 1); ctx.stroke(); }
        };
    }
    R.antique_chrome = _chromeFn(5001, [[0, '#a09888'], [0.3, '#c0b8a8'], [0.6, '#90887a'], [1, '#b0a898']]);
    R.black_chrome = _chromeFn(5002, [[0, '#282830'], [0.3, '#484858'], [0.6, '#1a1a24'], [1, '#383848']]);
    R.blue_chrome = _chromeFn(5003, [[0, '#4060a0'], [0.3, '#6888c0'], [0.6, '#3858a0'], [1, '#5070b0']]);
    R.candy_chrome = _chromeFn(5004, [[0, '#c04060'], [0.3, '#e06888'], [0.5, '#a03858'], [0.8, '#d05878'], [1, '#b84868']]);
    R.chrome = (ctx, w, h) => {
        const g = ctx.createLinearGradient(0, 0, w, h); g.addColorStop(0, '#b0bcc8'); g.addColorStop(0.2, '#e0e8f0'); g.addColorStop(0.4, '#98a8b8'); g.addColorStop(0.6, '#d0d8e4'); g.addColorStop(0.8, '#a0b0c0'); g.addColorStop(1, '#c8d4e0'); ctx.fillStyle = g; ctx.fillRect(0, 0, w, h);
        ctx.strokeStyle = 'rgba(255,255,255,0.12)'; ctx.lineWidth = 0.5; for (let y = 0; y < h; y += 2) { ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(w, y); ctx.stroke(); }
    };
    R.dark_chrome = _chromeFn(5006, [[0, '#38404a'], [0.3, '#586878'], [0.6, '#303840'], [1, '#485868']]);
    R.mirror_gold = _chromeFn(5007, [[0, '#c0a040'], [0.3, '#e0c868'], [0.6, '#b09838'], [1, '#d0b850']]);
    R.red_chrome = _chromeFn(5008, [[0, '#a03030'], [0.3, '#c84848'], [0.6, '#903030'], [1, '#b84040']]);
    R.satin_chrome = _chromeFn(5009, [[0, '#a0a8b0'], [0.3, '#b8c0c8'], [0.6, '#98a0a8'], [1, '#b0b8c0']]);
    R.surgical_steel = (ctx, w, h) => {
        ctx.fillStyle = '#c0c4c8'; ctx.fillRect(0, 0, w, h); const id = ctx.getImageData(0, 0, w, h); const rg = _rng(5010);
        for (let py = 0; py < h; py++) { const lv = (rg() - 0.5) * 8; for (let px = 0; px < w; px++) { const i = (py * w + px) * 4; id.data[i] += lv; id.data[i + 1] += lv; id.data[i + 2] += lv + 2; } } ctx.putImageData(id, 0, 0);
    };

    // === RACING HERITAGE BASES ===
    R.asphalt_grind = (ctx, w, h) => {
        ctx.fillStyle = '#383838'; ctx.fillRect(0, 0, w, h); const n = _n2d(w, h, 3, 5101), id = ctx.getImageData(0, 0, w, h);
        for (let i = 0; i < w * h; i++) { const v = n[i] * 18; id.data[i * 4] += v; id.data[i * 4 + 1] += v; id.data[i * 4 + 2] += v; } ctx.putImageData(id, 0, 0);
    };
    R.bullseye_chrome = _chromeFn(5103, [[0, '#c0c8d4'], [0.3, '#e0e4ec'], [0.5, '#cc3030'], [0.7, '#e0e4ec'], [1, '#c0c8d4']]);
    R.checkered_chrome = (ctx, w, h) => {
        const s = Math.max(4, w / 6); for (let py = 0; py < h; py += s)for (let px = 0; px < w; px += s) {
            ctx.fillStyle = ((Math.floor(px / s) + Math.floor(py / s)) % 2) ? '#dde4ec' : '#a0aab4'; ctx.fillRect(px, py, s, s);
        }
    };
    R.dirt_track_satin = (ctx, w, h) => {
        ctx.fillStyle = '#7a6850'; ctx.fillRect(0, 0, w, h); const n = _n2d(w, h, 5, 5105), id = ctx.getImageData(0, 0, w, h);
        for (let i = 0; i < w * h; i++) { const v = n[i] * 20; id.data[i * 4] += v; id.data[i * 4 + 1] += v * 0.8; id.data[i * 4 + 2] += v * 0.5; } ctx.putImageData(id, 0, 0);
    };
    R.drag_strip_gloss = (ctx, w, h) => {
        const g = ctx.createLinearGradient(0, 0, w, h); g.addColorStop(0, '#1a1a1a'); g.addColorStop(0.4, '#303030'); g.addColorStop(0.6, '#404040'); g.addColorStop(1, '#1a1a1a'); ctx.fillStyle = g; ctx.fillRect(0, 0, w, h);
        const hl = ctx.createLinearGradient(0, 0, w * 0.6, h * 0.4); hl.addColorStop(0, 'rgba(255,255,255,0)'); hl.addColorStop(0.5, 'rgba(255,255,255,0.12)'); hl.addColorStop(1, 'rgba(255,255,255,0)'); ctx.fillStyle = hl; ctx.fillRect(0, 0, w, h);
    };
    R.endurance_ceramic = (ctx, w, h) => {
        ctx.fillStyle = '#c8c0b0'; ctx.fillRect(0, 0, w, h); const n = _n2d(w, h, 6, 5107), id = ctx.getImageData(0, 0, w, h);
        for (let i = 0; i < w * h; i++) { const v = n[i] * 10; id.data[i * 4] += v; id.data[i * 4 + 1] += v * 0.9; id.data[i * 4 + 2] += v * 0.7; } ctx.putImageData(id, 0, 0);
    };
    R.heat_shield = (ctx, w, h) => {
        const id = ctx.createImageData(w, h); for (let py = 0; py < h; py++)for (let px = 0; px < w; px++) {
            const t = px / w; const r = Math.floor(60 + t * 160), g = Math.floor(50 + t * 60), b = Math.floor(40 + t * 20); const i = (py * w + px) * 4; id.data[i] = r; id.data[i + 1] = g; id.data[i + 2] = b; id.data[i + 3] = 255;
        } ctx.putImageData(id, 0, 0);
    };
    R.pace_car_pearl = (ctx, w, h) => {
        const g = ctx.createLinearGradient(0, 0, w, h); g.addColorStop(0, '#e0d8c8'); g.addColorStop(0.3, '#f0e8d8'); g.addColorStop(0.6, '#d8d0c0'); g.addColorStop(1, '#e8e0d0'); ctx.fillStyle = g; ctx.fillRect(0, 0, w, h);
        ctx.strokeStyle = 'rgba(255,255,255,0.1)'; ctx.lineWidth = 0.5; for (let y = 0; y < h; y += 3) { ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(w, y); ctx.stroke(); }
    };
    R.pit_lane_matte = (ctx, w, h) => {
        ctx.fillStyle = '#505050'; ctx.fillRect(0, 0, w, h); const n = _n2d(w, h, 4, 5110), id = ctx.getImageData(0, 0, w, h);
        for (let i = 0; i < w * h; i++) { const v = n[i] * 10; id.data[i * 4] += v; id.data[i * 4 + 1] += v; id.data[i * 4 + 2] += v; } ctx.putImageData(id, 0, 0);
    };
    R.race_day_gloss = (ctx, w, h) => {
        const g = ctx.createLinearGradient(0, 0, w, h); g.addColorStop(0, '#cc2020'); g.addColorStop(0.4, '#ee3838'); g.addColorStop(0.6, '#dd2828'); g.addColorStop(1, '#bb1818'); ctx.fillStyle = g; ctx.fillRect(0, 0, w, h);
        const hl = ctx.createLinearGradient(0, h * 0.2, w * 0.8, h * 0.5); hl.addColorStop(0, 'rgba(255,255,255,0)'); hl.addColorStop(0.5, 'rgba(255,255,255,0.15)'); hl.addColorStop(1, 'rgba(255,255,255,0)'); ctx.fillStyle = hl; ctx.fillRect(0, 0, w, h);
    };
    R.rally_mud = (ctx, w, h) => {
        ctx.fillStyle = '#5a4830'; ctx.fillRect(0, 0, w, h); const n = _n2d(w, h, 4, 5112), n2 = _n2d(w, h, 12, 5113), id = ctx.getImageData(0, 0, w, h);
        for (let i = 0; i < w * h; i++) { const v = (n[i] * 0.6 + n2[i] * 0.4) * 25; id.data[i * 4] += v; id.data[i * 4 + 1] += v * 0.8; id.data[i * 4 + 2] += v * 0.5; } ctx.putImageData(id, 0, 0);
    };
    R.rat_rod_primer = (ctx, w, h) => {
        ctx.fillStyle = '#686058'; ctx.fillRect(0, 0, w, h); const n = _n2d(w, h, 5, 5114), id = ctx.getImageData(0, 0, w, h);
        for (let i = 0; i < w * h; i++) { const v = n[i] * 12; id.data[i * 4] += v; id.data[i * 4 + 1] += v * 0.9; id.data[i * 4 + 2] += v * 0.8; } ctx.putImageData(id, 0, 0);
    };
    R.stock_car_enamel = (ctx, w, h) => {
        const g = ctx.createLinearGradient(0, 0, w, h); g.addColorStop(0, '#2040a0'); g.addColorStop(0.5, '#3058c0'); g.addColorStop(1, '#1838a0'); ctx.fillStyle = g; ctx.fillRect(0, 0, w, h);
        const hl = ctx.createLinearGradient(w * 0.2, 0, w * 0.8, h * 0.5); hl.addColorStop(0, 'rgba(255,255,255,0)'); hl.addColorStop(0.5, 'rgba(255,255,255,0.1)'); hl.addColorStop(1, 'rgba(255,255,255,0)'); ctx.fillStyle = hl; ctx.fillRect(0, 0, w, h);
    };
    R.victory_lane = (ctx, w, h) => {
        const g = ctx.createLinearGradient(0, 0, w, h); g.addColorStop(0, '#c8a030'); g.addColorStop(0.3, '#e8c850'); g.addColorStop(0.6, '#c0a028'); g.addColorStop(1, '#d8b840'); ctx.fillStyle = g; ctx.fillRect(0, 0, w, h);
        ctx.strokeStyle = 'rgba(255,255,255,0.1)'; ctx.lineWidth = 0.5; for (let y = 0; y < h; y += 2) { ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(w, y); ctx.stroke(); }
    };

    // === OEM AUTOMOTIVE BASES ===
    R.ambulance_white = (ctx, w, h) => {
        ctx.fillStyle = '#eef0f0'; ctx.fillRect(0, 0, w, h); const n = _n2d(w, h, 8, 5201), id = ctx.getImageData(0, 0, w, h);
        for (let i = 0; i < w * h; i++) { const v = n[i] * 5; id.data[i * 4] += v; id.data[i * 4 + 1] += v; id.data[i * 4 + 2] += v; } ctx.putImageData(id, 0, 0);
    };
    R.dealer_pearl = (ctx, w, h) => { const g = ctx.createLinearGradient(0, 0, w, h); g.addColorStop(0, '#e0d8cc'); g.addColorStop(0.4, '#f0e8dc'); g.addColorStop(0.7, '#d8d0c4'); g.addColorStop(1, '#e8e0d4'); ctx.fillStyle = g; ctx.fillRect(0, 0, w, h); };
    R.factory_basecoat = (ctx, w, h) => {
        ctx.fillStyle = '#3a3a3a'; ctx.fillRect(0, 0, w, h); const n = _n2d(w, h, 6, 5203), id = ctx.getImageData(0, 0, w, h);
        for (let i = 0; i < w * h; i++) { const v = n[i] * 8; id.data[i * 4] += v; id.data[i * 4 + 1] += v; id.data[i * 4 + 2] += v; } ctx.putImageData(id, 0, 0);
    };
    R.fire_engine = (ctx, w, h) => {
        const g = ctx.createLinearGradient(0, 0, w, h); g.addColorStop(0, '#cc1010'); g.addColorStop(0.4, '#ee2020'); g.addColorStop(1, '#bb0808'); ctx.fillStyle = g; ctx.fillRect(0, 0, w, h);
        const hl = ctx.createLinearGradient(0, 0, w * 0.6, h * 0.4); hl.addColorStop(0, 'rgba(255,255,255,0)'); hl.addColorStop(0.5, 'rgba(255,255,255,0.18)'); hl.addColorStop(1, 'rgba(255,255,255,0)'); ctx.fillStyle = hl; ctx.fillRect(0, 0, w, h);
    };
    R.fleet_white = (ctx, w, h) => { ctx.fillStyle = '#e8eaec'; ctx.fillRect(0, 0, w, h); };
    R.police_black = (ctx, w, h) => {
        ctx.fillStyle = '#0a0a0e'; ctx.fillRect(0, 0, w, h); const hl = ctx.createLinearGradient(0, 0, w * 0.5, h * 0.4);
        hl.addColorStop(0, 'rgba(255,255,255,0)'); hl.addColorStop(0.5, 'rgba(255,255,255,0.06)'); hl.addColorStop(1, 'rgba(255,255,255,0)'); ctx.fillStyle = hl; ctx.fillRect(0, 0, w, h);
    };
    R.school_bus = (ctx, w, h) => {
        ctx.fillStyle = '#e8a800'; ctx.fillRect(0, 0, w, h); const n = _n2d(w, h, 8, 5207), id = ctx.getImageData(0, 0, w, h);
        for (let i = 0; i < w * h; i++) { const v = n[i] * 6; id.data[i * 4] += v; id.data[i * 4 + 1] += v * 0.8; id.data[i * 4 + 2] -= 2; } ctx.putImageData(id, 0, 0);
    };
    R.showroom_clear = (ctx, w, h) => {
        const g = ctx.createLinearGradient(0, 0, w, h); g.addColorStop(0, '#e0e4e8'); g.addColorStop(0.3, '#f0f2f4'); g.addColorStop(0.6, '#d8dce0'); g.addColorStop(1, '#e8ecf0'); ctx.fillStyle = g; ctx.fillRect(0, 0, w, h);
        const hl = ctx.createLinearGradient(0, 0, w * 0.7, h * 0.5); hl.addColorStop(0, 'rgba(255,255,255,0)'); hl.addColorStop(0.5, 'rgba(255,255,255,0.2)'); hl.addColorStop(1, 'rgba(255,255,255,0)'); ctx.fillStyle = hl; ctx.fillRect(0, 0, w, h);
    };
    R.smoked = (ctx, w, h) => { const g = ctx.createLinearGradient(0, 0, 0, h); g.addColorStop(0, '#404448'); g.addColorStop(0.5, '#505458'); g.addColorStop(1, '#383c40'); ctx.fillStyle = g; ctx.fillRect(0, 0, w, h); };
    R.taxi_yellow = (ctx, w, h) => {
        ctx.fillStyle = '#e8c800'; ctx.fillRect(0, 0, w, h); const hl = ctx.createLinearGradient(0, 0, w * 0.6, h * 0.4);
        hl.addColorStop(0, 'rgba(255,255,255,0)'); hl.addColorStop(0.5, 'rgba(255,255,255,0.12)'); hl.addColorStop(1, 'rgba(255,255,255,0)'); ctx.fillStyle = hl; ctx.fillRect(0, 0, w, h);
    };

    // === INDUSTRIAL & TACTICAL BASES ===
    R.armor_plate = (ctx, w, h) => {
        ctx.fillStyle = '#585c58'; ctx.fillRect(0, 0, w, h); const n = _n2d(w, h, 4, 5301), n2 = _n2d(w, h, 14, 5302), id = ctx.getImageData(0, 0, w, h);
        for (let i = 0; i < w * h; i++) { const v = (n[i] * 0.5 + n2[i] * 0.5) * 18; id.data[i * 4] += v; id.data[i * 4 + 1] += v; id.data[i * 4 + 2] += v * 0.9; } ctx.putImageData(id, 0, 0);
    };
    R.battleship_gray = (ctx, w, h) => {
        ctx.fillStyle = '#6a6e72'; ctx.fillRect(0, 0, w, h); const n = _n2d(w, h, 5, 5303), id = ctx.getImageData(0, 0, w, h);
        for (let i = 0; i < w * h; i++) { const v = n[i] * 10; id.data[i * 4] += v; id.data[i * 4 + 1] += v; id.data[i * 4 + 2] += v; } ctx.putImageData(id, 0, 0);
    };
    R.blackout = (ctx, w, h) => {
        ctx.fillStyle = '#080808'; ctx.fillRect(0, 0, w, h); const n = _n2d(w, h, 6, 5304), id = ctx.getImageData(0, 0, w, h);
        for (let i = 0; i < w * h; i++) { const v = Math.abs(n[i]) * 6; id.data[i * 4] += v; id.data[i * 4 + 1] += v; id.data[i * 4 + 2] += v; } ctx.putImageData(id, 0, 0);
    };
    R.cerakote = (ctx, w, h) => {
        ctx.fillStyle = '#5a5848'; ctx.fillRect(0, 0, w, h); const n = _n2d(w, h, 3, 5305), id = ctx.getImageData(0, 0, w, h);
        for (let i = 0; i < w * h; i++) { const v = n[i] * 12; id.data[i * 4] += v; id.data[i * 4 + 1] += v * 0.95; id.data[i * 4 + 2] += v * 0.8; } ctx.putImageData(id, 0, 0);
    };
    R.duracoat = (ctx, w, h) => {
        ctx.fillStyle = '#606050'; ctx.fillRect(0, 0, w, h); const n = _n2d(w, h, 4, 5306), id = ctx.getImageData(0, 0, w, h);
        for (let i = 0; i < w * h; i++) { const v = n[i] * 10; id.data[i * 4] += v; id.data[i * 4 + 1] += v; id.data[i * 4 + 2] += v * 0.8; } ctx.putImageData(id, 0, 0);
    };
    R.gunship_gray = (ctx, w, h) => {
        ctx.fillStyle = '#505458'; ctx.fillRect(0, 0, w, h); const n = _n2d(w, h, 5, 5307), id = ctx.getImageData(0, 0, w, h);
        for (let i = 0; i < w * h; i++) { const v = n[i] * 8; id.data[i * 4] += v; id.data[i * 4 + 1] += v; id.data[i * 4 + 2] += v; } ctx.putImageData(id, 0, 0);
    };
    R.mil_spec_od = (ctx, w, h) => {
        ctx.fillStyle = '#4a5038'; ctx.fillRect(0, 0, w, h); const n = _n2d(w, h, 4, 5308), id = ctx.getImageData(0, 0, w, h);
        for (let i = 0; i < w * h; i++) { const v = n[i] * 10; id.data[i * 4] += v * 0.8; id.data[i * 4 + 1] += v; id.data[i * 4 + 2] += v * 0.6; } ctx.putImageData(id, 0, 0);
    };
    R.mil_spec_tan = (ctx, w, h) => {
        ctx.fillStyle = '#a08860'; ctx.fillRect(0, 0, w, h); const n = _n2d(w, h, 4, 5309), id = ctx.getImageData(0, 0, w, h);
        for (let i = 0; i < w * h; i++) { const v = n[i] * 10; id.data[i * 4] += v; id.data[i * 4 + 1] += v * 0.9; id.data[i * 4 + 2] += v * 0.6; } ctx.putImageData(id, 0, 0);
    };
    R.powder_coat = (ctx, w, h) => {
        ctx.fillStyle = '#484848'; ctx.fillRect(0, 0, w, h); const n = _n2d(w, h, 3, 5310), id = ctx.getImageData(0, 0, w, h);
        for (let i = 0; i < w * h; i++) { const v = n[i] * 8; id.data[i * 4] += v; id.data[i * 4 + 1] += v; id.data[i * 4 + 2] += v; } ctx.putImageData(id, 0, 0);
    };
    R.sandblasted = (ctx, w, h) => {
        ctx.fillStyle = '#98a0a8'; ctx.fillRect(0, 0, w, h); const n = _n2d(w, h, 3, 5311), n2 = _n2d(w, h, 8, 5312), id = ctx.getImageData(0, 0, w, h);
        for (let i = 0; i < w * h; i++) { const v = (n[i] * 0.7 + n2[i] * 0.3) * 20; id.data[i * 4] += v; id.data[i * 4 + 1] += v; id.data[i * 4 + 2] += v; } ctx.putImageData(id, 0, 0);
    };
    R.submarine_black = (ctx, w, h) => {
        ctx.fillStyle = '#101214'; ctx.fillRect(0, 0, w, h); const n = _n2d(w, h, 6, 5313), id = ctx.getImageData(0, 0, w, h);
        for (let i = 0; i < w * h; i++) { const v = Math.abs(n[i]) * 8; id.data[i * 4] += v; id.data[i * 4 + 1] += v; id.data[i * 4 + 2] += v * 1.2; } ctx.putImageData(id, 0, 0);
    };
    R.vantablack = (ctx, w, h) => { ctx.fillStyle = '#030303'; ctx.fillRect(0, 0, w, h); };

    // === GRADIENT SPECIALS — Enhanced with noise texture ===
    function _gradSpec(seed, stops, dir, noiseAmt) {
        return (ctx, w, h) => {
            const g = dir === 'd' ? ctx.createLinearGradient(0, 0, w, h) : dir === 'h' ? ctx.createLinearGradient(0, 0, w, 0) : ctx.createLinearGradient(0, 0, 0, h);
            stops.forEach(s => g.addColorStop(s[0], s[1])); ctx.fillStyle = g; ctx.fillRect(0, 0, w, h);
            if (noiseAmt) { const n = _n2d(w, h, 8, seed), id = ctx.getImageData(0, 0, w, h); for (let i = 0; i < w * h; i++) { const v = n[i] * noiseAmt; id.data[i * 4] += v; id.data[i * 4 + 1] += v; id.data[i * 4 + 2] += v; } ctx.putImageData(id, 0, 0); }
        };
    }
    function _vortexSpec(seed, stops) {
        return (ctx, w, h) => {
            const cx = w / 2, cy = h / 2, mr = Math.max(w, h) * 0.7;
            const id = ctx.createImageData(w, h); const n = _n2d(w, h, 10, seed);
            for (let py = 0; py < h; py++)for (let px = 0; px < w; px++) {
                const d = Math.sqrt((px - cx) ** 2 + (py - cy) ** 2) / mr; const t = Math.max(0, Math.min(1, d + n[py * w + px] * 0.15));
                let r = 0, g = 0, b = 0; for (let s = 0; s < stops.length - 1; s++) {
                    if (t >= stops[s][0] && t <= stops[s + 1][0]) {
                        const lt = (t - stops[s][0]) / (stops[s + 1][0] - stops[s][0]);
                        r = stops[s][1][0] + (stops[s + 1][1][0] - stops[s][1][0]) * lt; g = stops[s][1][1] + (stops[s + 1][1][1] - stops[s][1][1]) * lt; b = stops[s][1][2] + (stops[s + 1][1][2] - stops[s][1][2]) * lt; break;
                    }
                }
                const i = (py * w + px) * 4; id.data[i] = r; id.data[i + 1] = g; id.data[i + 2] = b; id.data[i + 3] = 255;
            } ctx.putImageData(id, 0, 0);
        };
    }

    R.grad_arctic_dawn = _gradSpec(6001, [[0, '#1a2840'], [0.4, '#4080b0'], [0.7, '#88c0d8'], [1, '#e8d0a0']], 'v', 8);
    R.grad_bruise = _gradSpec(6002, [[0, '#1a0828'], [0.3, '#482060'], [0.6, '#604080'], [1, '#2a1040']], 'v', 10);
    R.grad_copper_patina = _gradSpec(6003, [[0, '#b87040'], [0.4, '#80a880'], [0.7, '#60a0a0'], [1, '#408888']], 'v', 12);
    R.grad_fire_fade = _gradSpec(6004, [[0, '#cc2200'], [0.3, '#ee6600'], [0.6, '#ffaa00'], [1, '#ffdd44']], 'v', 8);
    R.grad_fire_fade_diag = _gradSpec(6005, [[0, '#cc2200'], [0.3, '#ee6600'], [0.6, '#ffaa00'], [1, '#ffdd44']], 'd', 8);
    R.grad_fire_fade_h = _gradSpec(6006, [[0, '#cc2200'], [0.3, '#ee6600'], [0.6, '#ffaa00'], [1, '#ffdd44']], 'h', 8);
    R.grad_forest_canopy = _gradSpec(6007, [[0, '#0a2010'], [0.3, '#1a4020'], [0.6, '#2a6030'], [1, '#4a8040']], 'v', 10);
    R.grad_golden_hour = _gradSpec(6008, [[0, '#cc6020'], [0.3, '#e89030'], [0.6, '#f0b848'], [1, '#f8d868']], 'v', 8);
    R.grad_golden_hour_h = _gradSpec(6009, [[0, '#cc6020'], [0.3, '#e89030'], [0.6, '#f0b848'], [1, '#f8d868']], 'h', 8);
    R.grad_ice_fire = _gradSpec(6010, [[0, '#2040c0'], [0.3, '#60a0e0'], [0.5, '#e0e8f0'], [0.7, '#e08030'], [1, '#c02010']], 'v', 8);
    R.grad_lava_flow = _gradSpec(6011, [[0, '#200800'], [0.3, '#802000'], [0.6, '#cc4400'], [1, '#ee8800']], 'v', 12);
    R.grad_midnight_ember = _gradSpec(6012, [[0, '#080810'], [0.4, '#1a1020'], [0.7, '#602010'], [1, '#cc4010']], 'v', 10);
    R.grad_neon_rush = _gradSpec(6013, [[0, '#ff0088'], [0.3, '#ff4400'], [0.6, '#ffcc00'], [1, '#00ff88']], 'v', 6);
    R.grad_neon_rush_h = _gradSpec(6014, [[0, '#ff0088'], [0.3, '#ff4400'], [0.6, '#ffcc00'], [1, '#00ff88']], 'h', 6);
    R.grad_ocean_depths = _gradSpec(6015, [[0, '#001030'], [0.3, '#002858'], [0.6, '#004888'], [1, '#0068b0']], 'v', 10);
    R.grad_ocean_depths_diag = _gradSpec(6016, [[0, '#001030'], [0.3, '#002858'], [0.6, '#004888'], [1, '#0068b0']], 'd', 10);
    R.grad_ocean_depths_h = _gradSpec(6017, [[0, '#001030'], [0.3, '#002858'], [0.6, '#004888'], [1, '#0068b0']], 'h', 10);
    R.grad_steel_forge = _gradSpec(6018, [[0, '#303840'], [0.3, '#506070'], [0.6, '#8090a0'], [1, '#b0c0d0']], 'v', 12);
    R.grad_sunset = _gradSpec(6019, [[0, '#1a0830'], [0.2, '#802048'], [0.5, '#e06030'], [0.8, '#f0a040'], [1, '#f8d868']], 'v', 8);
    R.grad_sunset_diag = _gradSpec(6020, [[0, '#1a0830'], [0.2, '#802048'], [0.5, '#e06030'], [0.8, '#f0a040'], [1, '#f8d868']], 'd', 8);
    R.grad_toxic_waste = _gradSpec(6021, [[0, '#102000'], [0.3, '#305000'], [0.6, '#60a000'], [1, '#a0e020']], 'v', 10);
    R.grad_twilight = _gradSpec(6022, [[0, '#080820'], [0.3, '#1a1050'], [0.6, '#402080'], [1, '#7040a0']], 'v', 8);
    R.grad_twilight_diag = _gradSpec(6023, [[0, '#080820'], [0.3, '#1a1050'], [0.6, '#402080'], [1, '#7040a0']], 'd', 8);
    R.grad_twilight_h = _gradSpec(6024, [[0, '#080820'], [0.3, '#1a1050'], [0.6, '#402080'], [1, '#7040a0']], 'h', 8);

    R.grad_blue_vortex = _vortexSpec(6101, [[0, [20, 40, 120]], [0.3, [40, 100, 200]], [0.6, [80, 160, 240]], [1, [160, 200, 255]]]);
    R.grad_copper_vortex = _vortexSpec(6102, [[0, [80, 40, 20]], [0.3, [160, 90, 40]], [0.6, [200, 130, 60]], [1, [220, 170, 100]]]);
    R.grad_fire_vortex = _vortexSpec(6103, [[0, [200, 40, 0]], [0.3, [240, 100, 0]], [0.6, [255, 180, 40]], [1, [255, 230, 120]]]);
    R.grad_gold_vortex = _vortexSpec(6104, [[0, [120, 80, 10]], [0.3, [180, 140, 30]], [0.6, [220, 180, 50]], [1, [250, 220, 100]]]);
    R.grad_green_vortex = _vortexSpec(6105, [[0, [10, 60, 20]], [0.3, [20, 120, 40]], [0.6, [40, 180, 60]], [1, [80, 220, 100]]]);
    R.grad_pink_vortex = _vortexSpec(6106, [[0, [120, 10, 60]], [0.3, [200, 40, 100]], [0.6, [240, 80, 140]], [1, [255, 160, 200]]]);
    R.grad_shadow_vortex = _vortexSpec(6107, [[0, [8, 8, 12]], [0.3, [20, 22, 30]], [0.6, [40, 44, 55]], [1, [70, 75, 90]]]);
    R.grad_teal_vortex = _vortexSpec(6108, [[0, [10, 60, 70]], [0.3, [20, 120, 130]], [0.6, [40, 180, 190]], [1, [80, 220, 230]]]);
    R.grad_violet_vortex = _vortexSpec(6109, [[0, [60, 10, 100]], [0.3, [100, 30, 160]], [0.6, [140, 60, 200]], [1, [190, 120, 240]]]);
    R.grad_white_vortex = _vortexSpec(6110, [[0, [140, 142, 148]], [0.3, [180, 182, 188]], [0.6, [210, 212, 218]], [1, [240, 242, 248]]]);

    // === MULTI CAMO ===
    function _camoSpec(seed, colors) {
        return (ctx, w, h) => {
            ctx.fillStyle = colors[0]; ctx.fillRect(0, 0, w, h); const rg = _rng(seed);
            for (let c = 1; c < colors.length; c++) {
                ctx.fillStyle = colors[c]; for (let i = 0; i < 8; i++) {
                    const x = rg() * w, y = rg() * h, s = w * 0.15 + rg() * w * 0.2;
                    ctx.beginPath(); ctx.ellipse(x, y, s, s * 0.6, rg() * 3.14, 0, 6.28); ctx.fill();
                }
            }
        };
    }
    R.mc_blue_camo = _camoSpec(7001, ['#1a3050', '#2a4868', '#3a6888', '#1a2840', '#2a5878']);
    R.mc_desert_camo = _camoSpec(7002, ['#c0a070', '#a88850', '#907040', '#b89860', '#d0b080']);
    R.mc_neon_camo = _camoSpec(7003, ['#202020', '#00ff80', '#ff0080', '#80ff00', '#0080ff']);
    R.mc_snow_camo = _camoSpec(7004, ['#e8ecf0', '#c8ccd0', '#d8dce0', '#b8bcc0', '#f0f2f4']);
    R.mc_urban_camo = _camoSpec(7005, ['#484848', '#686868', '#383838', '#585858', '#505050']);
    R.mc_woodland_camo = _camoSpec(7006, ['#2a3820', '#4a5838', '#384830', '#5a6848', '#1a2818']);

    // === MULTI MARBLE ===
    function _marbleSpec(seed, bg, vein) {
        return (ctx, w, h) => {
            ctx.fillStyle = bg; ctx.fillRect(0, 0, w, h);
            const n = _n2d(w, h, 10, seed), n2 = _n2d(w, h, 20, seed + 50), id = ctx.getImageData(0, 0, w, h);
            for (let i = 0; i < w * h; i++) {
                const v = Math.abs(Math.sin((n[i] + n2[i] * 0.5) * 8)); if (v > 0.85) {
                    const a = (v - 0.85) / 0.15; const j = i * 4;
                    id.data[j] = Math.floor(id.data[j] * (1 - a) + vein[0] * a); id.data[j + 1] = Math.floor(id.data[j + 1] * (1 - a) + vein[1] * a); id.data[j + 2] = Math.floor(id.data[j + 2] * (1 - a) + vein[2] * a);
                }
            } ctx.putImageData(id, 0, 0);
        };
    }
    R.mc_black_marble = _marbleSpec(7101, '#1a1a1a', [80, 80, 80]);
    R.mc_gold_marble = _marbleSpec(7102, '#d8c890', [180, 140, 40]);
    R.mc_green_marble = _marbleSpec(7103, '#2a5030', [60, 120, 80]);
    R.mc_red_marble = _marbleSpec(7104, '#802020', [160, 60, 60]);
    R.mc_white_marble = _marbleSpec(7105, '#e8e8e8', [160, 160, 165]);

    // === MULTI SPLATTER ===
    function _splatSpec(seed, bg, colors) {
        return (ctx, w, h) => {
            ctx.fillStyle = bg; ctx.fillRect(0, 0, w, h); const rg = _rng(seed);
            for (let i = 0; i < 12; i++) {
                const c = colors[Math.floor(rg() * colors.length)]; ctx.fillStyle = c; const x = rg() * w, y = rg() * h, s = 2 + rg() * 6;
                ctx.beginPath(); ctx.arc(x, y, s, 0, 6.28); ctx.fill(); for (let d = 0; d < 4; d++) { const dx = x + (rg() - 0.5) * s * 3, dy = y + (rg() - 0.5) * s * 3; ctx.beginPath(); ctx.arc(dx, dy, 0.5 + rg() * 1.5, 0, 6.28); ctx.fill(); }
            }
        };
    }
    R.mc_blood_splat = _splatSpec(7201, '#1a1a1a', ['#cc0000', '#880000', '#aa1010', '#990000']);
    R.mc_ink_splat = _splatSpec(7202, '#e8e8e0', ['#0a0a0a', '#1a1a2a', '#0a0a1a', '#2a2a3a']);
    R.mc_neon_splat = _splatSpec(7203, '#1a1a1a', ['#00ff80', '#ff0080', '#80ff00', '#0080ff', '#ff8000']);
    R.mc_paint_splat = _splatSpec(7204, '#e0e0e0', ['#cc2020', '#2020cc', '#20a020', '#cccc20', '#cc20cc']);

    // === MULTI THEMED ===
    function _themedSpec(seed, colors, style) {
        return (ctx, w, h) => {
            if (style === 'stripe') { const sw = w / colors.length; colors.forEach((c, i) => { ctx.fillStyle = c; ctx.fillRect(i * sw, 0, sw + 1, h); }); }
            else if (style === 'noise') {
                const n = _n2d(w, h, 12, seed), id = ctx.createImageData(w, h); const cl = colors.map(c => { const m = c.match(/[0-9a-f]{2}/gi); return m ? m.map(x => parseInt(x, 16)) : [128, 128, 128]; });
                for (let i = 0; i < w * h; i++) { const ci = Math.floor(((n[i] + 0.5) * cl.length) % cl.length); const cc = cl[Math.abs(ci) % cl.length]; id.data[i * 4] = cc[0]; id.data[i * 4 + 1] = cc[1]; id.data[i * 4 + 2] = cc[2]; id.data[i * 4 + 3] = 255; } ctx.putImageData(id, 0, 0);
            }
            else {
                const n = _n2d(w, h, 14, seed), id = ctx.createImageData(w, h); const cl = colors.map(c => { const m = c.match(/[0-9a-f]{2}/gi); return m ? m.map(x => parseInt(x, 16)) : [128, 128, 128]; });
                for (let i = 0; i < w * h; i++) { const t = (n[i] + 0.5) * cl.length; const ci = Math.floor(t) % cl.length; const cc = cl[Math.abs(ci) % cl.length]; id.data[i * 4] = cc[0]; id.data[i * 4 + 1] = cc[1]; id.data[i * 4 + 2] = cc[2]; id.data[i * 4 + 3] = 255; } ctx.putImageData(id, 0, 0);
            }
        };
    }
    R.mc_christmas = _themedSpec(7301, ['#cc1010', '#108810', '#e0d040', '#ffffff'], 'noise');
    R.mc_deep_space = _themedSpec(7302, ['#0a0a1a', '#1a1a3a', '#2a2050', '#102040', '#080818'], 'noise');
    R.mc_earth_tone = _themedSpec(7303, ['#8a6840', '#6a5030', '#a08050', '#c0a070', '#504028'], 'noise');
    R.mc_fire_storm = _themedSpec(7304, ['#cc2000', '#ee6600', '#ffaa00', '#ff4400', '#882000'], 'noise');
    R.mc_halloween = _themedSpec(7305, ['#e08800', '#1a1a1a', '#802080', '#cc4400'], 'noise');
    R.mc_miami_vice = _themedSpec(7306, ['#ff4080', '#40e0d0', '#ff8040', '#8040ff', '#40ff80'], 'noise');
    R.mc_rasta = _themedSpec(7307, ['#cc0000', '#e8c800', '#008800'], 'stripe');
    R.mc_tropical = _themedSpec(7308, ['#00a080', '#ff6040', '#e8c800', '#ff4080', '#40c0ff'], 'noise');
    R.mc_usa_flag = _themedSpec(7309, ['#cc1030', '#ffffff', '#003080'], 'stripe');
    R.mc_vaporwave = _themedSpec(7310, ['#ff40a0', '#4040ff', '#40e0d0', '#a040ff', '#ff8040'], 'noise');

    // === INJECT ===
    if (window._fusionSwatchRenderers) { Object.assign(window._fusionSwatchRenderers, R); }
    else { window._fusionSwatchRenderers = Object.assign(window._fusionSwatchRenderers || {}, R); }
    console.log(`[SWATCH-UPGRADES-2] ${Object.keys(R).length} upgraded renderers loaded`);
})();
