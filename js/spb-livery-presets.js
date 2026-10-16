/* [SPB-W24L 2026-10-10 lane W24-LIVERIES] NAMED CLASSIC LIVERIES: "gulf livery", "martini racing livery", "jps", "rothmans", "marlboro", "castrol", "sunoco" ...
   Why: new-user QA item #4 ("gulf livery" / "martini racing livery" typed into the in-app helper repainted the WHOLE car one flat colour). The helper's planner read the
   brand word as a colour (Gulf = light blue) and a livery word as "the whole body", so only the base step ever landed. The design library (js/spb-pro-design.js) already
   knows the palettes, but every palette used one of six generic layouts (twin stripes / lower band ...), so none of them read as THE livery. This file gives each classic
   its own layout, built only from the library's named-part elements (no boxes, no logos, no lettering: colours only, "-style"), and decides what counts as a named order.
   API: window.SpbLivery = { LIVERIES, match(text) -> {id,name,palette_id,preset} | null, plan(text) -> the same plan shape D.offlinePlan returns | null, presetsFor(pal),
        describe(plan), list(), on(), off(), version }.   ES5.   Loads right after js/spb-pro-design.js.
   A named livery is a CONCRETE order (act now, say what was chosen, offer 1-2 alternatives after); anything with a part, a colour or a question in it is NOT matched here.
   Kill switch: window.SPB_W24L_OFF = true (or localStorage SPB_W24L_OFF = '1') = the old generic layouts, the old routing. */
(function () {
    'use strict';
    var W = window, D = W.SpbProDesign;
    if (!D || !D.PRESETS || !D.PALETTES || !D.ELEMENTS) return;
    function off() { try { return !!W.SPB_W24L_OFF || (W.localStorage && W.localStorage.getItem('SPB_W24L_OFF') === '1'); } catch (e) { return !!W.SPB_W24L_OFF; } }
    function norm(s) { return String(s || '').toLowerCase().replace(/['’`]/g, '').replace(/[^a-z0-9#]+/g, ' ').replace(/\s+/g, ' ').trim(); }

    // ------------------------------------------------------------------ element: a SET of parallel stripes (the three-stripe Martini, the gold pinlines of JPS, orange edged in navy for Gulf)
    // widths / gap are fractions of the side height (down from the roof-line) or of the hood / roof / trunk width; at = where the middle of the set sits (0..1)
    D.ELEMENTS.stripe_set = {
        about: 'a SET of 2-4 parallel stripes touching or a hair apart, in any colour order (Martini = navy / light blue / red; Gulf = navy / orange / navy; JPS = gold pinline / gold stripe / gold pinline). where: "sides" (default, both sides, nose to tail), "centre" (down the middle of hood + roof + trunk) or "both"; at = middle of the set 0..1 (sides: down from the roof-line, default 0.6; centre default 0.5); widths = one fraction per stripe (default 0.045 each); gap = space between stripes (default 0.012); use:"trim" paints it with the trim finish',
        params: 'colours:[#hex|role,...] (or colour, colour2, colour3, colour4), where, at, widths, gap, use',
        build: function (o, ctx) {
            var cols = [], i;
            (o.colours && o.colours.length ? o.colours : [o.colour, o.colour2, o.colour3, o.colour4]).forEach(function (c) { if (c && /^#[0-9a-f]{6}$/i.test(String(c))) cols.push(String(c)); });
            if (cols.length < 1) return { zones: [], skipped: ['stripe_set needs colours'] };
            var where = o.where === 'centre' || o.where === 'both' ? o.where : 'sides', sc = ctx.scale || 1, gap = (o.gap != null ? o.gap : 0.012) * sc, fin = o.use === 'trim' ? ctx.trim : (o.finish || ctx.paint);
            var ws = cols.map(function (c, k) { return ((o.widths && o.widths[k] != null) ? o.widths[k] : (o.width != null ? o.width : 0.045)) * sc; });
            var total = gap * (cols.length - 1); ws.forEach(function (w) { total += w; });
            var out = [], sk = [];
            function lay(parts, at, label) {
                var x = at - total / 2;
                cols.forEach(function (c, k) {
                    var a = Math.max(0, x), b = Math.min(1, x + ws[k]); x += ws[k] + gap;
                    if (b > a) out.push({ name: D.nameColour(c).replace(/^./, function (m) { return m.toUpperCase(); }) + ' stripe ' + (k + 1) + ' (' + label + ')', finish: fin, color: c, region: { part: parts, band: { axis: 'height', from: a, to: b } } });
                });
            }
            if (where !== 'centre') {
                var ok = true; try { var C = W.SpbProCar, A = C && C.findIsland('left side'), B = C && C.findIsland('right side'); ok = !!(C && C.missing(['left side', 'right side']).length === 0 && A && A.up && B && B.up); } catch (e) { ok = false; }
                if (ok) lay(['left side', 'right side'], o.at != null && where === 'sides' ? o.at : (o.at != null ? o.at : 0.6), 'sides'); else sk.push('the left / right sides (or which edge is the roof-line) are not known on this car');
            }
            if (where !== 'sides') {
                var parts = []; ['hood', 'roof', 'trunk'].forEach(function (p) { try { var q = (p === 'trunk' && W.SpbProCar && W.SpbProCar.missing(['trunk']).length && !W.SpbProCar.missing(['bed']).length) ? 'bed' : p; if (W.SpbProCar && W.SpbProCar.missing([q]).length === 0) parts.push(q); } catch (e) {} });
                if (parts.length) lay(parts, where === 'both' && o.at2 != null ? o.at2 : (where === 'centre' && o.at != null ? o.at : 0.5), 'centre'); else sk.push('the hood / roof / trunk are not known on this car');
            }
            return { zones: out, skipped: sk };
        }
    };

    // ------------------------------------------------------------------ element: the livery's body colour = the normal body base, but colour-picked on a readable multi-colour paint
    // W24L 2026-10-10: the normal 'base' covers the car's paintable area only, and on a real multi-layer PSD (SPB ARCA Chevy, yellow base) that left ~24% of the yellow body showing
    // (panel-edge / seam padding = 11.8% of the whole sheet): a "Gulf" car with yellow seams. The planner's whole-car recolour ("make the car powder blue") picks the car's own body
    // colour everywhere. Same rule as pro-ai's keep-accents base (the dominant body colour is 60%+ of the body paint layers: the other art on the body stays), but WITHOUT the
    // paintable-area limit, so the padding is covered too. Anything else (paint not readable, no dominant colour, jsdom / MCP without a sheet): the normal base, unchanged.
    D.ELEMENTS.livery_base = {
        about: 'the livery body colour: the body base; on a paint file the helper can read it picks the dominant body colour of the car everywhere (panel-edge padding included, other body art stays), so no old colour shows at the seams; add it FIRST',
        params: 'colour',
        build: function (o, ctx) {
            var b = D.ELEMENTS.base.build(o, ctx);
            try {
                var Z = W.SpbProZone, C = W.SpbProCar, cs = Z && Z.bodyColours ? Z.bodyColours() : null, body = cs && cs[0];
                if (body && o.colour && b.zones && b.zones.length && C && C.roles && Z.probeRegion && String(body).toLowerCase() !== String(o.colour).toLowerCase()) {
                    var bl = C.roles().filter(function (r) { return /body paint/i.test(String(r.role || '')); }).map(function (r) { return r.name; });
                    if (bl.length) {
                        var pAll = Z.probeRegion({ layers: bl }), pSel = Z.probeRegion({ layers: bl, colors: [body], tolerance: 48 }), f = pAll && pAll.share_pct && pSel ? pSel.share_pct / pAll.share_pct : 0;
                        if (f >= 0.6) b.zones[0].region = { colors: [body], tolerance: 48 };
                    }
                }
            } catch (e) {}
            return b;
        }
    };

    // ------------------------------------------------------------------ the liveries (layouts over the palette roles base / a / b / c / trim of the matching D.PALETTES entry)
    function S(where, cols, widths, at, gap, use) { var o = { where: where, colours: cols, widths: widths, at: at, colour: cols[0] }; if (gap != null) o.gap = gap; if (use) o.use = use; return ['stripe_set', o]; }
    var LIVERIES = [
        { id: 'gulf', pal: 'gulf-style', name: 'Gulf livery', keys: ['gulf racing', 'gulf oil', 'gulf', 'powder blue and orange'], bare: true,
          look: '{base} body with a wide {a} centre stripe edged in {b} over the hood, roof and trunk, and a matching {a} stripe edged in {b} along both sides',
          steps: function (p) { return [['livery_base', { colour: p.base }], ['centre_stripe', { colour: p.a, trim: p.b, width: 0.17 }], S('sides', [p.b, p.a, p.b], [0.016, 0.105, 0.016], 0.6, 0)]; } },
        { id: 'martini', pal: 'martini-style', name: 'Martini livery', keys: ['martini racing', 'martini rossi', 'martini'], bare: true,
          look: '{base} body with the three-stripe set ({a}, {b}, {c}) along both sides and over the hood, roof and trunk',
          steps: function (p) { return [['livery_base', { colour: p.base }], S('sides', [p.a, p.b, p.c], [0.05, 0.05, 0.05], 0.64, 0.012), S('centre', [p.a, p.b, p.c], [0.045, 0.045, 0.045], 0.5, 0.012)]; } },
        { id: 'jps', pal: 'black-gold', name: 'John Player Special (JPS) livery', keys: ['john player special', 'john player', 'jps lotus', 'jps'], bare: true,
          look: '{base} body with {a} pinlines and a {a} stripe along both sides and a {a} stripe edged in pinlines over the hood, roof and trunk',
          steps: function (p) { return [['livery_base', { colour: p.base }], S('sides', [p.a, p.a, p.a], [0.012, 0.045, 0.012], 0.6, 0.018), S('centre', [p.a, p.a, p.a], [0.012, 0.075, 0.012], 0.5, 0.018)]; } },
        { id: 'rothmans', pal: 'rothmans', name: 'Rothmans livery', keys: ['rothmans'], bare: true,
          look: '{base} body with a {a} lower body band under a {b} pinline, a {a} centre stripe edged in {b} over the hood, roof and trunk, {a} bumpers',
          steps: function (p) { return [['livery_base', { colour: p.base }], ['lower_band', { colour: p.a, from: 0.58, to: 1 }], S('sides', [p.b], [0.02], 0.565, 0), S('centre', [p.b, p.a, p.b], [0.012, 0.1, 0.012], 0.5, 0.012), ['bumpers', { colour: p.a }]]; } },
        { id: 'marlboro', pal: 'marlboro', name: 'Marlboro livery', keys: ['marlboro'], bare: true,
          look: '{base} upper body over a {a} lower body block with a thin {a} line, a {a} roof and white-edged {base} hood stripe, {a} front bumper',
          steps: function (p) { return [['livery_base', { colour: p.base }], ['lower_band', { colour: p.a, from: 0.5, to: 1 }], S('sides', [p.a], [0.018], 0.44, 0), ['roof', { colour: p.a }], S('centre', [p.a], [0.1], 0.5, 0, null)]; } },
        { id: 'castrol', pal: 'castrol', name: 'Castrol livery', keys: ['castrol'], bare: true,
          look: '{base} body with a {a} lower body band under a {b} pinline, a {a} centre stripe edged in {b} over the hood, roof and trunk, {a} bumpers',
          steps: function (p) { return [['livery_base', { colour: p.base }], ['lower_band', { colour: p.a, from: 0.6, to: 1 }], S('sides', [p.b], [0.018], 0.585, 0), S('centre', [p.b, p.a, p.b], [0.012, 0.11, 0.012], 0.5, 0.012), ['bumpers', { colour: p.a }]]; } },
        { id: 'monster', pal: 'monster', name: 'Monster Energy-style livery', keys: ['monster energy', 'monster'], bare: false,
          look: '{base} body with a {a} sill band along the bottom of both sides, a {a} stripe down the hood, roof and trunk and {a} claw slashes behind the front wheel',
          steps: function (p) { return [['livery_base', { colour: p.base }], ['lower_band', { colour: p.a, from: 0.82, to: 1 }], S('centre', [p.a, p.a, p.a], [0.035, 0.035, 0.035], 0.5, 0.02), ['stripes_graphic', { colour: p.a, n: 3, w: 0.06, gap: 0.05, angle: 72, at: 0.4, from: 0.04, to: 0.3, part: ['left side', 'right side'] }]]; } },
        { id: 'sunoco', pal: 'sunoco-style', name: 'Sunoco livery', keys: ['sunoco'], bare: true,
          look: '{base} body with a wide {a} stripe over a thin {b} line along both sides and a {a} centre stripe edged in {b} over the hood, roof and trunk',
          steps: function (p) { return [['livery_base', { colour: p.base }], S('sides', [p.a, p.b], [0.08, 0.018], 0.62, 0.014), S('centre', [p.b, p.a, p.b], [0.012, 0.12, 0.012], 0.5, 0.012), ['bumpers', { colour: p.a }]]; } },
        { id: 'mobil-1', pal: 'mobil-1', name: 'Mobil 1-style livery', keys: ['mobil 1', 'mobil one', 'mobil1', 'mobil'], bare: true,
          look: '{base} body with a wide {a} stripe edged in {b} along both sides and over the hood, roof and trunk',
          steps: function (p) { return [['livery_base', { colour: p.base }], S('sides', [p.b, p.a, p.b], [0.013, 0.07, 0.013], 0.6, 0), S('centre', [p.b, p.a, p.b], [0.013, 0.12, 0.013], 0.5, 0)]; } },
        { id: 'valvoline', pal: 'valvoline', name: 'Valvoline livery', keys: ['valvoline'], bare: true,
          look: '{base} upper body over a {a} lower body with a {b} line between them, a {a} centre stripe edged in {b} over the hood, roof and trunk',
          steps: function (p) { return [['livery_base', { colour: p.base }], ['lower_band', { colour: p.a, from: 0.55, to: 1 }], S('sides', [p.b], [0.02], 0.54, 0), S('centre', [p.b, p.a, p.b], [0.012, 0.1, 0.012], 0.5, 0.012), ['bumpers', { colour: p.a }]]; } },
        { id: 'pennzoil', pal: 'pennzoil', name: 'Pennzoil-style livery', keys: ['pennzoil'], bare: true,
          look: '{base} body with a {b} stripe edged in {a} along both sides and over the hood, roof and trunk, {b} bumpers',
          steps: function (p) { return [['livery_base', { colour: p.base }], S('sides', [p.a, p.b, p.a], [0.013, 0.07, 0.013], 0.6, 0), S('centre', [p.a, p.b, p.a], [0.013, 0.11, 0.013], 0.5, 0), ['bumpers', { colour: p.b }]]; } },
        { id: 'stp', pal: 'stp', cn: { base: 'Petty blue' }, name: 'STP-style livery', keys: ['stp', 'petty blue'], bare: false,
          look: '{base} body with a {a} lower body band under a {b} pinline, a {a} roof and a {b} stripe over the hood and trunk',
          steps: function (p) { return [['livery_base', { colour: p.base }], ['lower_band', { colour: p.a, from: 0.7, to: 1 }], S('sides', [p.b], [0.018], 0.685, 0), ['roof', { colour: p.a }], S('centre', [p.b], [0.07], 0.5, 0, null), ['bumpers', { colour: p.a }]]; } },
        { id: 'hooters', pal: 'hooters', name: 'Hooters-style livery', keys: ['hooters'], bare: true,
          look: '{base} body with a {a} lower body block under a {b} line, a {a} centre stripe over the hood, roof and trunk, {a} bumpers',
          steps: function (p) { return [['livery_base', { colour: p.base }], ['lower_band', { colour: p.a, from: 0.6, to: 1 }], S('sides', [p.b], [0.018], 0.585, 0), S('centre', [p.b, p.a, p.b], [0.012, 0.1, 0.012], 0.5, 0.012), ['bumpers', { colour: p.a }]]; } },
        { id: 'kodak', pal: 'kodak', name: 'Kodak-style livery', keys: ['kodak'], bare: true,
          look: '{base} body with a wide {a} stripe edged in {b} along both sides and over the hood, roof and trunk',
          steps: function (p) { return [['livery_base', { colour: p.base }], S('sides', [p.b, p.a, p.b], [0.013, 0.08, 0.013], 0.6, 0), S('centre', [p.b, p.a, p.b], [0.013, 0.13, 0.013], 0.5, 0), ['bumpers', { colour: p.a }]]; } },
        { id: 'tide', pal: 'tide', name: 'Tide-style livery', keys: ['tide'], bare: false,
          look: '{base} body with a {a} lower body band under a {b} line, a {a} centre stripe edged in {b} over the hood, roof and trunk',
          steps: function (p) { return [['livery_base', { colour: p.base }], ['lower_band', { colour: p.a, from: 0.64, to: 1 }], S('sides', [p.b], [0.02], 0.625, 0), S('centre', [p.b, p.a, p.b], [0.012, 0.11, 0.012], 0.5, 0.012), ['bumpers', { colour: p.a }]]; } },
        { id: 'rockstar', pal: 'rockstar', name: 'Rockstar-style livery', keys: ['rockstar energy', 'rockstar'], bare: false,
          look: '{base} body with a {a} sill band along the bottom of both sides, a {a} stripe edged in {b} over the hood, roof and trunk',
          steps: function (p) { return [['livery_base', { colour: p.base }], ['lower_band', { colour: p.a, from: 0.82, to: 1 }], S('sides', [p.b], [0.014], 0.8, 0), S('centre', [p.b, p.a, p.b], [0.012, 0.09, 0.012], 0.5, 0.012), ['bumpers', { colour: p.a }]]; } },
        { id: 'red-bull', pal: 'red-bull', name: 'Red Bull-style livery', keys: ['red bull', 'redbull'], bare: true,
          look: '{base} body with a {a} sill band under a {b} line, a {a} stripe edged in {b} over the hood, roof and trunk',
          steps: function (p) { return [['livery_base', { colour: p.base }], ['lower_band', { colour: p.a, from: 0.78, to: 1 }], S('sides', [p.b], [0.016], 0.765, 0), S('centre', [p.b, p.a, p.b], [0.012, 0.1, 0.012], 0.5, 0.012), ['bumpers', { colour: p.a }]]; } },
        { id: 'pepsi-80s', pal: 'pepsi-80s', name: 'Pepsi-style livery', keys: ['pepsi challenge', 'pepsi'], bare: false,
          look: '{base} body with a {a} stripe and a {b} stripe side by side along both sides and over the hood, roof and trunk',
          steps: function (p) { return [['livery_base', { colour: p.base }], S('sides', [p.b, p.a], [0.055, 0.055], 0.62, 0.012), S('centre', [p.b, p.a], [0.06, 0.06], 0.5, 0.012), ['bumpers', { colour: p.a }]]; } },
        { id: 'cola-red', pal: 'cola-red', name: 'Cola-red livery', keys: ['coca cola', 'cocacola', 'coke'], bare: false,
          look: '{base} body with a wide {a} ribbon over a thin {a} line along both sides and a {a} stripe over the hood, roof and trunk',
          steps: function (p) { return [['livery_base', { colour: p.base }], S('sides', [p.a, p.a], [0.09, 0.016], 0.6, 0.02), S('centre', [p.a], [0.12], 0.5, 0), ['bumpers', { colour: p.a }]]; } },
        { id: 'ferrari', pal: 'ferrari', name: 'Ferrari-style livery', keys: ['scuderia ferrari', 'ferrari'], bare: false,
          look: '{base} body with a {b} sill, a {a} pinline above it and a {a} stripe over the hood and trunk, {a} front bumper',
          steps: function (p) { return [['livery_base', { colour: p.base }], ['lower_band', { colour: p.b, from: 0.86, to: 1 }], S('sides', [p.a], [0.014], 0.845, 0), S('centre', [p.a], [0.04], 0.5, 0), ['bumpers', { colour: p.a }]]; } },
        { id: 'papaya', pal: 'papaya', name: 'McLaren papaya livery', keys: ['mclaren papaya', 'mclaren'], bare: false,
          look: '{base} body with a {a} sill band, a thin {b} line above it and a {a} twin stripe over the hood, roof and trunk',
          steps: function (p) { return [['livery_base', { colour: p.base }], ['lower_band', { colour: p.a, from: 0.8, to: 1 }], S('sides', [p.b], [0.014], 0.785, 0), S('centre', [p.a, p.a], [0.035, 0.035], 0.5, 0.025), ['bumpers', { colour: p.a }]]; } },
        { id: 'brg', pal: 'brg', name: 'British racing green livery', keys: ['british racing green', 'brg'], bare: false,
          look: '{base} body with a {a} centre stripe over the hood, roof and trunk and a thin {a} line along both sides',
          steps: function (p) { return [['livery_base', { colour: p.base }], S('centre', [p.a], [0.11], 0.5, 0), S('sides', [p.a, p.b], [0.016, 0.016], 0.6, 0.02)]; } },
        { id: 'police', pal: 'police', name: 'Police-style livery', keys: ['police car', 'cop car', 'police'], bare: false,
          look: '{base} hood, roof, trunk and bumpers with {a} sides below the roof-line and a thin {b} line along them',
          steps: function (p) { return [['livery_base', { colour: p.base }], ['lower_band', { colour: p.a, from: 0.1, to: 1 }], S('sides', [p.b], [0.014], 0.6, 0)]; } },
        { id: 'taxi-bus', pal: 'taxi-bus', name: 'Taxi-style livery', keys: ['yellow cab', 'taxi cab', 'taxi', 'school bus'], bare: false,
          look: '{base} body with a {a} stripe and a thin {a} line along both sides',
          steps: function (p) { return [['livery_base', { colour: p.base }], S('sides', [p.a, p.a], [0.07, 0.014], 0.55, 0.02), ['bumpers', { colour: p.a }]]; } },
        { id: 'silver-arrow', pal: 'silver-arrow', name: 'Silver Arrow livery', keys: ['silver arrows', 'silver arrow'], bare: true,
          look: '{base} body with a {b} line edged in {a} along both sides, {a} bumpers',
          steps: function (p) { return [['livery_base', { colour: p.base }], S('sides', [p.a, p.b, p.a], [0.012, 0.03, 0.012], 0.58, 0), ['bumpers', { colour: p.a }]]; } },
        { id: 'fedex', pal: 'fedex', name: 'FedEx-style livery', keys: ['fedex', 'fed ex'], bare: false,
          look: '{base} body with a {a} stripe edged in {b} along both sides and a {a} stripe over the hood, roof and trunk',
          steps: function (p) { return [['livery_base', { colour: p.base }], S('sides', [p.b, p.a, p.b], [0.012, 0.07, 0.012], 0.62, 0), S('centre', [p.a], [0.1], 0.5, 0), ['bumpers', { colour: p.a }]]; } },
        { id: 'mtn-dew', pal: 'mtn-dew', name: 'Mountain Dew-style livery', keys: ['mountain dew', 'mtn dew', 'mt dew'], bare: false,
          look: '{base} body with a {a} stripe edged in {b} along both sides and over the hood, roof and trunk',
          steps: function (p) { return [['livery_base', { colour: p.base }], S('sides', [p.b, p.a, p.b], [0.013, 0.075, 0.013], 0.6, 0), S('centre', [p.b, p.a, p.b], [0.013, 0.12, 0.013], 0.5, 0), ['bumpers', { colour: p.b }]]; } },
        { id: 'deere', pal: 'deere', name: 'John Deere-style livery', keys: ['john deere', 'deere'], bare: false,
          look: '{base} body with a {a} lower body band under a thin {a} line, {a} bumpers and a {a} roof stripe',
          steps: function (p) { return [['livery_base', { colour: p.base }], ['lower_band', { colour: p.a, from: 0.72, to: 1 }], S('sides', [p.a], [0.014], 0.7, 0), S('centre', [p.a], [0.08], 0.5, 0), ['bumpers', { colour: p.a }]]; } },
        { id: 'ups-brown', pal: 'ups-brown', cn: { base: 'brown' }, name: 'UPS-style livery', keys: ['ups'], bare: false,
          look: '{base} body with {a} pinlines and a {a} stripe along both sides and over the hood, roof and trunk',
          steps: function (p) { return [['livery_base', { colour: p.base }], S('sides', [p.a, p.a], [0.05, 0.012], 0.6, 0.02), S('centre', [p.a, p.a], [0.04, 0.012], 0.5, 0.02), ['bumpers', { colour: p.a }]]; } }
    ];
    // a few palettes need their layout colours tuned for the livery (the generic palettes stay as they are for the generic presets)
    var byId = {}; D.PALETTES.forEach(function (p) { byId[p.id] = p; });
    function livery(id) { for (var i = 0; i < LIVERIES.length; i++) if (LIVERIES[i].id === id) return LIVERIES[i]; return null; }
    function presetId(l) { return 'livery_' + l.id.replace(/-/g, '_'); }

    // register one preset per livery (D.PRESETS is what apply_scheme / spb_design_recipes / the in-app designer read)
    LIVERIES.forEach(function (l) {
        if (!byId[l.pal]) return;
        D.PRESETS[presetId(l)] = { name: l.name, about: 'the ' + l.name.replace(/ livery$/, '') + ' look in colours only (no logos or lettering): ' + l.look.replace(/\{[a-z0-9]+\}/g, function (m) { return { '{base}': 'body colour', '{a}': 'accent colour', '{b}': 'second colour', '{c}': 'third colour', '{trim}': 'trim colour' }[m] || m; }), steps: l.steps, livery: l.id };
    });

    // ------------------------------------------------------------------ what counts as "a named livery order" (act at once) -- strict on purpose: a part, a colour, a number or a question in it is NOT ours
    var FILL = {}; ('please pls plz can could you would will i id ill want wanna need like love to give gimme me us make paint do put turn change set apply try use go with show get build create design add in into as a an the it my this that our your car cars truck ride racer race rig ok okay so just now then too also thanks thx ty style styled livery liveries scheme schemes look looks colours colors colour color paintjob job theme inspired inspiration vibe vibes version tribute replica retro classic vintage old school authentic real proper original famous iconic lets let s for of ish esque gloss glossy matte flat satin pearl metallic candy chrome trim finish le mans lemans endurance 60s 70s 80s 90s 1960s 1970s 1980s 1990s racing look paint').split(' ').forEach(function (w) { FILL[w] = 1; });
    var NOUN = /\b(livery|liveries|scheme|schemes|style|styled|look|looks|colours|colors|colour scheme|color scheme|paint job|paintjob|theme|inspired|vibe|vibes|replica|tribute|racing|inspiration)\b/;
    var VERB = /\b(make|paint|give|gimme|put|turn|do|apply|want|wanna|need|get|go|try|use|set|change|lets|let|show|build|create|design|love|like)\b/;
    var QUESTION = /\b(how|what|whats|why|where|when|which|who|explain|meaning|mean|tell|do you have|is there|are there|have you got|does|should|difference)\b|\?/;
    var NEGATE = /\b(no|not|dont|never|without|remove|delete|erase|undo|stop|cancel|instead|except|besides|other|than|different)\b/;
    function keyList() { var all = []; LIVERIES.forEach(function (l) { l.keys.forEach(function (k) { all.push({ k: norm(k), l: l }); }); }); all.sort(function (a, b) { return b.k.length - a.k.length; }); return all; }
    var KEYS = keyList();
    function match(text) {
        if (off()) return null;
        var t = norm(text); if (!t || t.length < 3) return null;
        var toks = t.split(' '); if (toks.length > 10) return null;
        if (QUESTION.test(t) || NEGATE.test(t)) return null;
        var hit = null, rest = ' ' + t + ' ';
        for (var i = 0; i < KEYS.length; i++) { var re = ' ' + KEYS[i].k + ' '; var at = rest.indexOf(re); if (at !== -1 && (!hit || KEYS[i].k.length > hit.k.length)) { hit = KEYS[i]; } }
        if (!hit) return null;
        rest = rest.replace(' ' + hit.k + ' ', ' ');
        // any other key of another livery in the same sentence = a mix ("martini and gulf"), not ours
        for (var j = 0; j < KEYS.length; j++) { if (KEYS[j].l !== hit.l && (' ' + rest + ' ').indexOf(' ' + KEYS[j].k + ' ') !== -1) return null; }
        var left = rest.split(' ').filter(function (w) { return w && !FILL[w]; });
        if (left.length) return null;
        var l = hit.l, byWord = NOUN.test(t.replace(hit.k, ' '));
        if (!byWord && !(l.bare && (VERB.test(t) || toks.length <= 3 || (toks.length === 4 && /^(please|pls|a|an|the|my)\b/.test(t))))) return null;
        if (!byId[l.pal] || !D.PRESETS[presetId(l)]) return null;
        return { id: l.id, name: l.name, palette_id: l.pal, preset: presetId(l), key: hit.k };
    }
    function plan(text) {
        var m = match(text); if (!m) return null;
        var pal = byId[m.palette_id], t = norm(text);
        var p = { base: pal.base, a: pal.a, b: pal.b, c: pal.c, trim: pal.trim };
        var paint = /\b(matte|flat)\b/.test(t) ? 'base::matte' : (/\bsatin\b/.test(t) ? 'base::satin' : (/\b(pearl|pearlescent)\b/.test(t) ? 'base::pearl' : (/\bcandy\b/.test(t) ? 'base::candy' : (/\bmetallic\b/.test(t) ? 'base::metallic' : 'base::gloss'))));
        var trim = /\bchrome\b/.test(t) ? 'base::chrome' : paint;
        if (paint !== 'base::gloss' && paint !== 'base::matte' && paint !== 'base::satin') trim = 'base::chrome';
        return { preset: m.preset, palette: p, palette_id: m.palette_id, ctx: { paint: paint, trim: trim }, scale: 1, elements: D.presetSteps(m.preset, p), livery: m.id };
    }
    // the first line of the helper's reply ("Done - <name> on your <car>: <this>."): just the colours and finish; the layout goes in tryLine (the report lane replaces line 1 with the measured result)
    function cname(plan, l, k) { var c = plan.palette[k] || plan.palette.base; return (l.cn && l.cn[k] && byId[l.pal] && byId[l.pal][k] === c) ? l.cn[k] : D.nameColour(c); }      // a livery can name its own colour (UPS brown, Petty blue) while the palette still holds the original
    function colourWords(plan, l) {
        var pal = plan.palette, seen = {}, names = [], used = {}; (l.look.match(/\{(base|a|b|c|trim)\}/g) || []).forEach(function (m) { used[m.replace(/[{}]/g, '')] = 1; });
        ['base', 'a', 'b', 'c', 'trim'].forEach(function (k) { if (!used[k] || !pal[k]) return; var n = cname(plan, l, k); if (!seen[n]) { seen[n] = 1; names.push(n); } });
        return names.length > 1 ? names.slice(0, -1).join(', ') + ' and ' + names[names.length - 1] : (names[0] || 'your colours');
    }
    function finWords(plan) { var fin = plan.ctx && plan.ctx.paint ? plan.ctx.paint.replace('base::', '') : 'gloss'; return fin === 'matte' ? 'flat paint' : (fin === 'satin' ? 'satin paint' : (fin === 'gloss' ? 'gloss paint' : fin.replace(/_/g, ' ') + ' paint')); }
    function describe(plan) {
        var l = plan && livery(plan.livery); if (!l || !plan.palette) return '';
        return colourWords(plan, l) + ', ' + finWords(plan);
    }
    // what the helper adds after a named livery: WHAT it chose (the layout) + 1-2 alternatives (never a question before acting)
    function tryLine(plan) {
        var l = plan && livery(plan.livery); if (!l || off() || !plan.palette) return '';
        var pal = plan.palette, look = l.look.replace(/\{(base|a|b|c|trim)\}/g, function (m0, k) { return cname(plan, l, k); });
        var fin = plan.ctx && plan.ctx.paint === 'base::matte' ? 'gloss' : 'matte';
        return '\nI chose the ' + l.name + ': ' + look + ' (colours and stripe layout only, no logos or lettering). Other ways to take it: \u201canother take\u201d (same colours, a different layout) or \u201c' + fin + '\u201d; \u201cundo\u201d puts the paint back exactly.\nNEXT: Another take | ' + fin.replace(/^./, function (m) { return m.toUpperCase(); }) + ' finish | Undo';
    }
    function list() { return LIVERIES.map(function (l) { return { id: l.id, name: l.name, say: l.keys.slice().sort(function (a, b) { return a.length - b.length; }).filter(function (k) { return k.length >= 3; })[0] + ' livery', preset: presetId(l), palette_id: l.pal, look: l.look.replace(/\{[a-z]+\}/g, function (m) { return { '{base}': 'body colour', '{a}': 'accent', '{b}': 'second colour', '{c}': 'third colour', '{trim}': 'trim' }[m]; }) }; }); }
    // ------------------------------------------------------------------ hook the design library (call-time kill switch; everything else passes straight through)
    var _plan = D.offlinePlan, _desc = D.describePlan, _recipes = D.recipes;
    D.offlinePlan = function (text) { var lp = null; try { lp = plan(text); } catch (e) { lp = null; } return lp || _plan.apply(this, arguments); };
    D.describePlan = function (pl) { try { if (pl && pl.livery && !off()) { var l = livery(pl.livery); if (l && pl.preset === presetId(l)) return describe(pl); } } catch (e) {} return _desc.apply(this, arguments); };
    D.recipes = function (q) {
        var r = _recipes.apply(this, arguments);
        try {
            if (r && r.presets && !off()) {
                r.presets = r.presets.filter(function (p) { return String(p.id).indexOf('livery_') !== 0; });
                r.named_liveries = { how: 'A NAMED classic livery is a concrete order: call apply_scheme at once with that preset id (and its palette_id) - never ask which layout - then say what you chose and offer 1-2 alternatives. Colours and stripe layout only, no logos or lettering. An unnamed vague ask ("a classic Le Mans car") gets 2-3 options first.', liveries: list().map(function (x) { return { say: x.say, preset: x.preset, palette_id: x.palette_id, look: x.look }; }) };
                var m = match(String(q || '')); if (m) r.recommended_livery = { preset: m.preset, palette_id: m.palette_id, name: m.name };
            }
        } catch (e) {}
        return r;
    };
    W.SpbLivery = { version: '2026-10-10-w24l3', LIVERIES: LIVERIES, match: match, plan: plan, describe: describe, tryLine: tryLine, list: list, on: function () { return !off(); }, off: off, presetId: presetId, byKey: function (k) { return livery(k); } };
})();
