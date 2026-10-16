/* ============================================================================
   M2 2026-10-07 (lane M2, MCP CONNECTOR FIXES; _easy_claude_work/eval/m2/REPORT.md): THE MCP TOOL TEXTS, SLIMMED.
   M1 measured the 24 generated tool descriptions + schemas (mcp/server/tools.json, 56k characters, ~14k tokens) on EVERY model call of every
   conversation. The in-app copilot keeps its long texts (js/spb-pro-ai.js makeTools); only what list_tools hands to the MCP (and so tools.json)
   is replaced here: short descriptions that keep every rule, property descriptions cut to their first sentence, the zone-field descriptions
   kept ONCE (spb_add_zone; spb_edit_zone / spb_duplicate_zone say "fields as in spb_add_zone"), the spb_do frame schema without its repeated
   Target copies, spb_manual dropped (spb_encyclopedia is the same articles), and the ask-first fields (buyer_said, confirm) added by
   js/spb-mcp-gate.js mcpSchema.
   Global: window.SpbMcpTexts.slim(list) -> list   (ES5, pure: runs in Node for the size check in _easy_claude_work/eval/m2/tools_size.js)
   ============================================================================ */
(function () {
    'use strict';
    var W = (typeof window !== 'undefined') ? window : (typeof globalThis !== 'undefined' ? globalThis : {});
    var VERSION = '2026-10-07-m2';
    var ASK = ' Pass buyer_said (their words). Vague / mood / reference / complaint words get ask_back: nothing changes, ask the buyer.';
    var D = {
        spb_do: 'PREFERRED for any change to what the car already shows (recolour, finish, outline, pinline, stripe, gradient, pattern, copy a look, thinner / bigger / lighter, "everything except the roof"). '
            + 'Send a frame {v:1, act:"change", ops:[{verb, target, look, except?, relative?}], keep?, decals:"protect"} plus text = the buyer\'s own words (REQUIRED: the app checks the frame against them). One op per clause. '
            + 'verb: recolour | refinish (shine only: look.finish {family, keep_colour:true}) | restyle | outline | pinline | stripe | gradient | pattern | copy_look | adjust (relative {prop, dir, amount}) | hide | show. '
            + 'target.kind: part (parts: hood, roof, trunk, spoiler, front bumper, rear bumper, left side, right side) | layer (exact names from spb_status) | colour | element (numbers | sponsors | stripes) | body (whole car, needs confirm:true) | zone. '
            + 'Name ONLY the parts the buyer named ("the right door" = right side only; a part named as the reference, "same as the left", is not a target). '
            + 'look: {colour:{word|hex}, finish:{family | key, keep_colour}, pattern:{concept|id}, gradient, stroke:{width}, spec}. Finish families the app knows: chrome, satin chrome, dark chrome, metallic, pearl, candy, brushed, matte, satin, gloss, carbon. ANY other look (holo, flake, glitter, chameleon...): spb_find_finishes first and pass look.finish.key. '
            + 'Returns applied, measured {verdict, changed_px, outside_px, decal_px, findings, line}, undo, preview. verdict ok = clean; reported / substituted / reverted = tell the buyer exactly that. If it returns ask: NOTHING changed, put the question to the buyer. dry_run:true = plan only.',
        spb_check: 'What did the LAST change really do, measured on the rendered paint: paint / spec / outside / decal pixels, findings, the app\'s line, still applied or undone. Read-only. Call it when the buyer asks you to verify. fresh:true re-measures now. A 256 grid: a hairline can read 0.',
        spb_apply_scheme: 'Lay out a WHOLE paint scheme on the named parts in one call (exact bands; base colour first, later zones stack above). Preset id or elements list, palette (base / a / b / c / trim, or palette_id from spb_design_recipes), paint_finish ("base::matte" / "base::gloss" / "base::satin"), trim_finish. '
            + 'ASK FIRST: only when the buyer asked for a full livery with colours, approved your proposal, or said "surprise me / just do it": then confirm:true. Otherwise offer 2-3 options and wait. The body base keeps the accent art already on the car. Returns zones_touched (zone 0 = top), measured {verdict, outside_px, decal_px, line} and the preview: report from those.' + ASK,
        spb_design_recipes: 'The design library: scheme presets (retro lower band, classic stripes, two-tone, colour block, bookends, stealth), elements (lower band, pinstripe, twin stripes, centre stripe, bumpers, roof, hood...), proportions and composition rules, and the palette for an era / brand / theme ("Gulf", "70s", "stealth"). Use it to PROPOSE options before spb_apply_scheme.',
        spb_add_zone: 'Create a NEW zone (goes on top unless priority says otherwise). region is required: {part} (preferred), colours (+tolerance), layers, element, remaining / everything (whole car: needs confirm:true). Returns what the region selects, which zones it takes pixels from, measured {verdict, outside_px, decal_px, line} and the preview. For edits of existing paint prefer spb_do.' + ASK,
        spb_edit_zone: 'Change an EXISTING zone by zone_id or unique zone_name (preferred), or index + expect_name. Pass only what changes; fields and meanings as in spb_add_zone. A zone that covers most of the car needs confirm:true. Returns measured {verdict, outside_px, decal_px, line} and the preview. For edits of existing paint prefer spb_do.' + ASK,
        spb_duplicate_zone: 'Copy an existing zone (the copy sits just below it), optionally changing settings on the copy (fields as in spb_add_zone).' + ASK,
        spb_refinish: 'Change what the car already shows in one call: target = a colour on the car (from spb_describe_paint), numbers, sponsors, stripes, main colour or a part; look = matte | satin | gloss | powder coat | plasti dip | cerakote | chrome | metallic | pearl | candy | brushed | anodized | vinyl wrap ... (a look ALONE keeps the colours); colour = a new colour; relative glossier | duller. On a flat paint, numbers / sponsors / stripes without boxes return needs_confirmation: tell the buyer to answer the card, claim nothing. Prefer spb_do.' + ASK,
        spb_add_graphic: 'DRAW crisp graphics on named parts: rings, speed_lines, stripes (any angle), waves, chevrons, checker, dots, rays, lightning, flames ({style: hotrod | tribal | ghost | truefire, colours, length 0.2..1 (use 0.9+ on the long sides, the default stops at ~40%), licks, curl}; licks start at the nose end of the part). Part space: u 0..1 front to rear, v 0..1 roof-line to rocker. part default both sides; colours 1-3 #hex (one zone each); paint_finish for the strokes. Typical: rings {cu:0.38, cv:0.6, r0:0.1, r1:0.95, n:8, facing:"front", span:150}; speed_lines {u0:0.4, u1:0.95, v0:0.15, v1:0.85, n:16}. Place above a base colour. Describe the result from the returned zones.' + ASK,
        spb_edit_layer: 'Show / hide a PSD layer, its opacity (0-100) or blend mode. Layer names from spb_status. Mask / Wire / Car_Mandatory are template layers (off before export). Never hide the body paint layer unasked.',
        spb_check_setup: 'Read the buyer\'s live render + iRacing setup: user ID, number mode, car folder, files in it (paint, spec, .mip, age), template layers on, render state, engine health. Call FIRST when paint will not render, is missing in iRacing or looks different in the sim.',
        spb_get_state: 'Zones (what each covers, what it really wins, what blocks it, its look), PSD layers and the main colours. Only to double-check.',
        spb_suggest_finishes: 'THE tool for "which finish for X": ranks the whole catalogue (~4,800 looks) for this car. part, goal (pop|premium|shimmer|deep|retro|stealth|readable|subtle), ask = the buyer\'s own words (negations honoured), novelty (safe|balanced|wild), lane (keep = shine only | complete | texture), exclude (keys already shown: pass them for NEW options), page. like + mods (calm, bold, darker, lighter, glossier, flatter, sparklier, metalmore, metalless, warmer, cooler, vivid, muted...) = "like X but calmer". leave_out = traits they do not want. Rows: look, why, loud / busy 1-5, apply hint. Use it to build the 2-3 OPTIONS you offer.',
        spb_find_finishes: 'Search the catalogue (~4,800 looks) by meaning: query plus facets colour, shine (mirror|gloss|satin|matte), metal (none..full), sparkle, texture, own / takes colour, shelf, type (finish|base|monolithic), tags, min_quality, exclude. Returns up to 10 {key, name, look, about}. Use several differently-worded queries.',
        spb_browse_catalog: 'The catalogue map: all shelves (no argument) or one shelf\'s best items.',
        spb_finish_details: 'Full spec sheet of ONE finish (key or name): palette, own / takes colour, measured metal / roughness / clearcoat, scale, sparkle, quality, best use, deep notes.',
        spb_compare_finishes: 'Side-by-side facts for up to 6 finish keys.',
        spb_find_spec_patterns: 'Find SPEC patterns (how a surface reflects: flake, sparkle, brushed, holographic prism, weave, weathering) by words. Returns up to 10 {id, name, effect}. Use the id in spec_patterns.',
        spb_find_patterns: 'Find visible PAINT patterns (carbon weave, camo, hex, scales...) by words. Returns up to 10 {id, name, effect}. Use the id in pattern.',
        spb_describe_paint: 'What this paint really shows, in painter words: its colours (share, hex, where), the numbers / sponsors / stripes layers, and the looks spb_refinish understands. Call it FIRST before changing what the car already shows, and to answer complaints ("looks plastic") with facts.',
        spb_mark_elements: 'TELL the app where numbers / sponsors / stripes are on a FLAT paint, read from spb_look_at_paint; none:true = there are none. boxes = [[x0,y0,x1,y1]] sheet fractions. mode: glyph (numbers), logo (sponsors; lettering:true keeps the plate), colour_in_region (stripes: colour = the colour it has now). Check per_box and the image; add more with replace:false.',
        spb_get_car_map: 'The car layout: what each PSD layer is (body paint / numbers / sponsors / tape / decals / template) and the NAMED PARTS (where, which end is the front, which edge is the roof-line). parts_not_known_yet: call spb_request_parts before designing.',
        spb_look_at_paint: 'SEE the flat paint with a 0.1 ruler plus the app\'s guess of numbers (pink), sponsors (blue), stripes (yellow). For flat paints before spb_mark_elements. region [x0,y0,x1,y1] or {part} = that area at full resolution.'
    };
    var REGION = 'WHICH PIXELS: part:"left side" or ["left side","right side"] (a NAMED part: the way to place anything) with portion:"front third"|"lower third"|"rear half"... or band:{axis:"height"|"length", from, to} (height 0 = roof-line .. 1 = rocker; length 0 = front .. 1 = rear); colors:["#hex"] + tolerance 6-100; layers:["layer name"]; element:"numbers"|"sponsors"|"stripes" (flat paints, spb_describe_paint first); exclude:["numbers","sponsors","stripes"]; cells / rect only for details under ~12% of the sheet; remaining:true (everything not claimed); everything:true + paintable:true = a whole-car base (confirm:true).';
    var DROP = { spb_manual: 1 };          // same articles as spb_encyclopedia (index.js); the NAME_MAP still routes an old call
    function firstSentence(t, n) {
        t = String(t || ''); if (t.length <= n) return t;
        var cut = t.slice(0, n), k = Math.max(cut.lastIndexOf('. '), cut.lastIndexOf('; '), cut.lastIndexOf(': '));
        return (k > 40 ? cut.slice(0, k + 1) : cut.replace(/\s+\S*$/, '') + ' ...').trim();
    }
    function trimProps(o, n, keepDesc) {
        if (!o || typeof o !== 'object') return o;
        if (Array.isArray(o)) return o.map(function (x) { return trimProps(x, n, keepDesc); });
        var out = {}; Object.keys(o).forEach(function (k) {
            var v = o[k];
            if (k === 'description' && typeof v === 'string') { if (keepDesc !== false) out[k] = firstSentence(v, n); return; }
            out[k] = (v && typeof v === 'object') ? trimProps(v, n, keepDesc) : v;
        });
        return out;
    }
    function typesOnly(props, keep) {          // top-level names + types only (nested shapes are documented once, in spb_add_zone)
        var out = {}; Object.keys(props || {}).forEach(function (k) {
            var v = props[k] || {};
            out[k] = (keep && keep.indexOf(k) !== -1) ? JSON.parse(JSON.stringify(v)) : (v.type ? { type: v.type } : {});
        });
        return out;
    }
    function slimFrame(fs) {
        if (!fs || typeof fs !== 'object' || !fs.properties) return fs;
        var f = JSON.parse(JSON.stringify(fs)), P = f.properties, TGT = { type: 'object', description: 'a Target, same shape as ops[].target' };
        ['alts', 'confidence', 'missing', 'list', 'n', 'question', 'said', 'turn'].forEach(function (k) { delete P[k]; });
        if (P.act) P.act = { type: 'string', enum: ['change'] };
        if (P.keep) P.keep = { type: 'array', items: TGT, description: 'kept parts ("but leave the doors")' };
        var ops = P.ops && P.ops.items && P.ops.items.properties;
        if (ops) {
            if (ops.except) ops.except = { type: 'array', items: TGT, description: '"everything except the roof"' };
            if (ops.ref) ops.ref = TGT;
            if (ops.source) ops.source = { type: 'object', description: 'copy_look: where the look comes from (a Target)' };
            var tg = ops.target && ops.target.properties; if (tg && tg.between) tg.between = { type: 'array', items: { type: 'object' }, description: 'pinline: the two Targets whose seam gets the line' };
            var fam = ops.look && ops.look.properties && ops.look.properties.finish && ops.look.properties.finish.properties && ops.look.properties.finish.properties.family;
            if (fam) fam.description = 'chrome | satin chrome | dark chrome | metallic | pearl | candy | brushed | matte | satin | gloss | carbon (anything else: pass key from spb_find_finishes)';
        }
        return trimProps(f, 110);
    }
    function slim(list) {
        var G = W.SpbMcpGate;
        return (list || []).filter(function (t) { return !DROP[t.name]; }).map(function (t) {
            var s = JSON.parse(JSON.stringify(t.inputSchema || { type: 'object', properties: {} }));
            if (t.name === 'spb_add_zone') { s = trimProps(s, 300); if (s.properties && s.properties.region) { s.properties.region.description = REGION; s.properties.region.properties = Object.assign({ part: { description: 'a named part or a list of parts' }, band: { type: 'object', properties: { axis: { type: 'string' }, from: { type: 'number' }, to: { type: 'number' } } }, element: { type: 'string' }, exclude: { type: 'array', items: { type: 'string' } }, rect: { type: 'object' }, paintable: { type: 'boolean' } }, s.properties.region.properties || {}); } }
            else if (t.name === 'spb_edit_zone' || t.name === 'spb_duplicate_zone') { s.properties = typesOnly(s.properties, ['zone', 'zone_id', 'zone_name', 'expect_name']); s = trimProps(s, 110); }
            else if (t.name === 'spb_do') { if (s.properties && s.properties.frame) s.properties.frame = slimFrame(s.properties.frame); s = trimProps(s, 160); }
            else s = trimProps(s, t.name === 'spb_refinish' || t.name === 'spb_mark_elements' ? 110 : 160);
            if (t.name === 'spb_apply_scheme' && s.properties && !s.properties.keep_accents) s.properties.keep_accents = { type: 'boolean', description: 'default true: the base colour replaces only the car\'s main body colour, the buyer\'s other body art stays. false only when the buyer wants that art painted over.' };          // M2 2026-10-07: runScheme accent keep
            if (G && G.mcpSchema) s = G.mcpSchema(t.name, s);
            return { name: t.name, description: D[t.name] || firstSentence(t.description, 400), inputSchema: s };
        });
    }
    W.SpbMcpTexts = { VERSION: VERSION, slim: slim, D: D, _firstSentence: firstSentence };
})();
