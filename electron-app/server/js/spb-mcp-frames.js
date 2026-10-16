/* ============================================================================
   HELPER V3 S8 2026-10-06 (docs/handoff_reports/HELPER_ARCHITECTURE_V3.md section 2.7, stage S8): MCP FRAMES.
   Two new tools for the MCP bridge, built on the V3 pipeline instead of raw zone edits:
     spb_do    a FRAME (or one line of text) -> validated (SpbIntentModel.fromCall) -> planned (SpbIntentPlan.plan) -> scope-checked
               (SpbIntentVerify.onQueue) -> applied through the copilot's applyQueue as ONE undo step (host.apply = mcpApply)
               -> MEASURED on the rendered paint (SpbIntentReport.check, the S3 reporter) -> one honest report:
               what changed, paint / spec / decal pixels, an undo id, the preview picture.
     spb_check what the LAST change actually did (paint / spec / decal diff, findings, still applied or undone).
   Everything here is NEW and additive: no existing tool, name or schema changes (Codex rules, section 4.1).
   Global: window.SpbMcpFrames   (ES5; the pure parts also run in Node: prepare(), listTools(), textOf())
     tools(queue, host)   page-side tool definitions for js/spb-pro-ai.js makeTools: [{name:'do'|'check', description, parameters, handler}]
                          handler(args) resolves { __mcpDone: { ok, result, images, error } } (mcpCallCore returns __mcpDone verbatim)
     listTools()          the MCP-side definitions [{name:'spb_do'|'spb_check', description, inputSchema}] (what mcp/server/tools.json gets)
     prepare(args, host)  frame -> plan -> verify, no apply  (spb_do dry_run uses it)
     doCall(args, host) / checkCall(args, host)   the two calls, resolve { ok, result, images, error }
   host (supplied by the js/spb-pro-ai.js hunk, see HELPER_V3_STAGES.md "S8"):
     apply(queue, res)   -> Promise<{ok, result, images, error}>   = mcpApply('do', queue, res, mcpContext): applyQueue + undo entry + settle + preview picture
     last() / log()      the newest chat-log entry / the whole log (entry.zdiff holds the "before" picture, entry.s3 the report)
     ctx(entry)          S3 check context { synced, undo, reseal, render }   (omit = measure only, never trims or undoes)
     layers()            layersInfo()            find(q)  the atlas finder for resolveLooks (optional)
     images()            Promise<images[]>       a fresh preview picture (used after the reporter took a change back)
     ensure()            CAR.ensure(false)       env()    editEnv() for the {text} path (optional)
     planRun             true ONLY when S6 hunk H1 is in applyQueue (queue._s5plan runs whole: flames, _above, _intersect, undo steps)
   Switch: SPB_AI_FRAME = '0' turns the whole V3 pipeline off; spb_do then answers "not available" (the old tools keep working).
   ============================================================================ */
(function () {
    'use strict';
    var W = (typeof window !== 'undefined') ? window : (typeof globalThis !== 'undefined' ? globalThis : {});
    var VERSION = '2026-10-07-m3', N = 256;          // M3 2026-10-07: bare shade words ("dark roof") read as a hex instead of an ask
             // M2 2026-10-07: parts check vs the buyer's words, finish-substitution refusal, honest verdict / line, measureOnly for the other write tools
    var SHADE = { dark: ['#1e1e1e', 'dark charcoal'], darkest: ['#111111', 'near-black'], deep: ['#1e1e1e', 'dark charcoal'], light: ['#d6d6d6', 'light grey'], pale: ['#e2e2e2', 'pale grey'] };          // M3 2026-10-07 shade words
    function arr(x) { return Array.isArray(x) ? x : (x == null ? [] : [x]); }
    function clone(o) { try { return o == null ? o : JSON.parse(JSON.stringify(o)); } catch (e) { return null; } }
    function uniq(a) { var o = []; (a || []).forEach(function (x) { if (x != null && o.indexOf(x) === -1) o.push(x); }); return o; }
    function IP() { return W.SpbIntentPlan; }
    function IM() { return W.SpbIntentModel; }
    function IF() { return W.SpbIntentFrame; }
    function IV() { return W.SpbIntentVerify; }
    function IR() { return W.SpbIntentReport; }
    function flagOff() { try { var F = IF(); return !!(F && F.on && !F.on()); } catch (e) { return false; } }

    // ------------------------------------------------------------------ the tool texts
    var DO_DESC = 'MAKE A CHANGE as an INTENT FRAME (preferred over spb_add_zone / spb_edit_zone for anything that changes what the car already shows: recolour, finish, outline, pinline, stripes, gradient, pattern, copy a look, thinner / bigger / lighter, "everything except the roof"). '
        + 'You describe WHAT the buyer asked; the app plans it with fixed, tested recipes, checks the scope BEFORE applying (numbers / sponsors / logos untouched unless named, "except X" kept, accents asked about), applies it as ONE undo step, then MEASURES the result on the rendered paint and tells you what really changed. '
        + 'Frame = {v:1, act:"change", ops:[{verb, target, look, except?, relative?, ref?}], keep?:[target], decals?:"protect"|"include"}. One op per clause, in the order said. '
        + 'verb: recolour | refinish (shine only: look.finish {family, keep_colour:true}) | restyle | outline | pinline | stripe | gradient | pattern | copy_look | adjust (thinner, bigger, shinier, less red: relative {prop, dir, amount}) | retarget | hide | show. '
        + 'target.kind: body (the whole car paint) | part (parts: hood, roof, trunk, spoiler, front bumper, rear bumper, left side, right side) | layer (layers: exact PSD layer names from spb_status) | colour ({colour:{word|hex}} optionally inside layers / parts) | element (numbers | sponsors | stripes) | zone. '
        + 'look: {colour:{word,hex}, finish:{family, key?, keep_colour?}, pattern:{concept|id, scale?}, gradient, stroke:{width:hairline|thin|medium|thick}, scale, spec:{metal,rough,clearcoat}}. A typed hex goes in exactly as typed. A finish with no colour named = finish {family, keep_colour:true} (only the shine changes). '
        + 'For a one-line request you may pass text instead of frame (the app\'s built-in reader makes the frame; a frame you write is more reliable). dry_run:true = plan + scope check only, nothing changes. '
        + 'RESULT: applied, plan, verify, measured {verdict, changed_px, paint_px, spec_px, outside_px, decal_px, findings, line}, undo {id, how}, problems_found_by_app and the preview picture. '
        + 'If it returns ask, NOTHING changed: put that question to the BUYER (do not answer it yourself); choices[] are ready answers, each with a frame you can send back. If measured.verdict is "reverted" the app took the change back: say so and use its question. Report only what measured says. Then call spb_check after the change.';
    var CHECK_DESC = 'WHAT DID THE LAST CHANGE ACTUALLY DO? Call it after every spb_do (or any change). Returns the newest change made in this paint session and what the RENDERED paint shows it did: paint pixels changed, spec (shine / metal) pixels changed, pixels changed OUTSIDE the parts / layers it was meant for, pixels changed on protected numbers / sponsors / logos, findings (spill, decal, kept, flat-fade, unasked-whole ...), the app\'s own one-line claim, and whether the change is still applied or was taken back. '
        + 'Measured on a 256 x 256 grid of the live preview (one cell = 64 px of the 2048 sheet), so tiny edits (a hairline) can read as 0. Read-only. fresh:true re-measures the current preview against the picture taken just before that change.';
    function defs() {
        var frameSchema = null; try { frameSchema = IM() && IM().schema ? IM().schema() : null; } catch (e) {}
        return [
            { name: 'do', mcp: 'spb_do', description: DO_DESC, parameters: { type: 'object', properties: {
                frame: frameSchema || { type: 'object', description: 'IntentFrame v1: {v:1, act:"change", ops:[{verb, target, look}], keep?, decals?}' },
                text: { type: 'string', description: 'the buyer\'s own words: required when you send no frame (the app reads it with its built-in reader); with a frame it is only used for the scope check' },
                dry_run: { type: 'boolean', description: 'true = plan and check the scope, change nothing' } } } },
            { name: 'check', mcp: 'spb_check', description: CHECK_DESC, parameters: { type: 'object', properties: { fresh: { type: 'boolean', description: 'true = measure again now (against the picture taken just before the change)' } } } }
        ];
    }
    function listTools() { return defs().map(function (d) { return { name: d.mcp, description: d.description, inputSchema: d.parameters }; }); }

    // ------------------------------------------------------------------ frame -> a short sentence the static verifier / reporter can read (parts, layers, elements, keep, whole)
    function say(t) {
        t = t || {}; var out = [];
        if (t.kind === 'part') out.push(arr(t.parts).join(' and '));
        else if (t.kind === 'layer') out.push(arr(t.layers).map(function (l) { return 'the ' + l + ' layer'; }).join(' and '));
        else if (t.kind === 'element') out.push('the ' + (t.element || 'numbers'));
        else if (t.kind === 'colour') { if (arr(t.parts).length) out.push(arr(t.parts).join(' and ')); if (arr(t.layers).length) out.push(arr(t.layers).map(function (l) { return 'the ' + l + ' layer'; }).join(' and ')); if (!arr(t.parts).length && !arr(t.layers).length) out.push('the body paint'); }
        else if (t.kind === 'body') out.push('the whole car');
        else if (t.kind === 'graphic') out.push(arr(t.parts).join(' and '));
        return out.filter(Boolean).join(' and ');
    }
    function textOf(fr) {
        var bits = [];
        arr(fr && fr.ops).forEach(function (op) { var s = say(op.target); if (s) bits.push(s); });
        var tx = bits.length ? uniq(bits).join(', ') : '';
        var partOnly = function (t) { return t && t.kind === 'part' ? say(t) : ''; };          // keep / except of numbers, sponsors or a layer is NOT said: naming a decal would make the reporter treat it as a target (decals are protected by default)
        var keep = uniq(arr(fr && fr.keep).map(partOnly).filter(Boolean)); arr(fr && fr.ops).forEach(function (op) { arr(op.except).forEach(function (e) { var s = partOnly(e); if (s && keep.indexOf(s) === -1) keep.push(s); }); });
        if (tx && keep.length) tx += ', but leave the ' + keep.join(' and ') + ' alone';
        if (fr && fr.decals === 'include' && tx) tx += ', including the decals';
        return tx;
    }
    function slimFrame(fr) { var s = clone(fr); if (!s) return null; delete s.said; if (s.ops && s.ops.length > 10) s.ops = s.ops.slice(0, 10); return s; }
    function planView(pl) {
        return { act: pl.act, notes: (pl.notes || []).slice(0, 6), steps: (pl.steps || []).slice(0, 8).map(function (s) {
            var o = { prim: s.prim, label: s.label }; if (s.notes && s.notes.length) o.notes = s.notes.slice(0, 4); if (s.expect) o.expect = clone(s.expect); if (s.scope) o.scope = clone(s.scope);
            o.ops = (s.ops || []).length; if (s.flames) o.flames = true; if (s.undo) o.undo = true; return o; }) };
    }
    function askView(ask, frame) {
        var full = function (f) { return !!(f && f.ops && f.ops.length && f.ops.every(function (o) { return o && o.verb; })); };          // a chip frame that is only a patch (no verb) is not sendable: keep its label only
        var a = { question: ask && ask.q || 'Can you say a bit more about what to change?', choices: arr(ask && ask.chips).filter(function (c) { return c && !c.tool; }).map(function (c) { return typeof c === 'string' ? { label: c } : (full(c.frame) ? { label: c.label, frame: c.frame } : { label: c.label }); }) };
        if (ask && ask.hint && ask.hint.alt) a.picture_note = ask.hint.alt;
        if (ask && ask.owner_rule) a.owner_rule = ask.owner_rule;
        a.must_ask_buyer = true; return a;
    }

    // ------------------------------------------------------------------ frame -> plan -> scope check (no apply)
    function liveLayers(host) { try { if (host && host.layers) return host.layers(); } catch (e) {} try { var C = W.SpbProCar, rl = C && C.roles ? C.roles() : []; return rl.map(function (r) { return { id: r.id, name: r.name, group: r.group, role: r.role, visible: r.visible, locked: r.locked }; }); } catch (e2) { return []; } }
    function fail(msg, extra) { var r = { ok: false, error: msg }; if (extra) r.result = extra; return r; }
    function frameFromText(text, host) {
        var OA = W.SpbOfflineAnswer, F = IF();
        if (!OA || !OA.route || !F || !F.routeToFrame) return { error: 'the built-in reader is not loaded: send a frame' };
        var env = host && host.env ? host.env() : null; if (!env) return { error: 'no app environment for the built-in reader: send a frame' };
        var r = null; try { r = OA.route(text, env); } catch (e) { return { error: 'the built-in reader failed (' + (e && e.message || e) + '): send a frame' }; }
        var fr = null; try { fr = F.routeToFrame(r, text, env); } catch (e2) {}
        if (fr && fr.act === 'change' && r && r.s5frame && r.s5frame.act === 'change' && !W.SPB_MCP_NOS5F) { try { var s5 = JSON.parse(JSON.stringify(r.s5frame)); ['v', 'producer', 'said', 'keep', 'decals', 'via', 'pass', 'confidence', 'missing', 'alts'].forEach(function (k) { if (s5[k] == null && fr[k] != null) s5[k] = fr[k]; }); if (!s5.said) s5.said = String(text || '').slice(0, 600); if (arr(s5.ops).length) fr = s5; } catch (e3) {} }          // lane R3-EDIT 2026-10-07 S5F: the reader's real frame (copy_look / flames), not one rebuilt from display steps (probe h1d: 'copy the roof finish' -> seafoam recolour; 'door flames' -> unknown finish graphic::flames)
        if (!fr) return { error: 'the built-in reader could not turn that into a change: send a frame (see the frame schema)' };
        return { frame: fr, route: r && r.cls || null };
    }
    // M2 2026-10-07: the finishes a frame asks for that the planner would replace by its default (Soft Gloss): unknown families ("holo", "flake", "glitter") and catalogue keys under keep-colour
    function finishSubs(frame, P) {
        var out = []; if (!P || !P.finishKey) return out;
        arr(frame && frame.ops).forEach(function (op) {
            var L = op && op.look || {}, fin = L.finish; if (!fin || typeof fin !== 'object') return;
            var k = String(fin.key || ''); if (/^base::f_/.test(k)) return;
            var want = String(fin.family || fin.label || k.replace(/^[a-z]+::/, '') || '').trim(); if (!want) return;
            var keep = fin.keep_colour === true || (!L.colour && !L.gradient && !L.pattern && !L.colours), got = null; try { got = P.finishKey(fin, keep); } catch (e) { got = null; }
            var glossy = /\b(gloss|glossy|wet|shiny|shine|clear ?coat|soft gloss)\b/i.test(want);
            if ((got === 'base::f_soft_gloss' && !glossy) || (!got && !k)) out.push({ want: want, would: got ? 'Soft Gloss' : 'nothing', key: k || undefined });
        });
        return out;
    }
    function prepare(args, host) {
        args = args || {}; host = host || {};
        var M = IM(), P = IP(), F = IF();
        if (flagOff()) return fail('spb_do is switched off (SPB_AI_FRAME = 0): use spb_edit_zone / spb_add_zone / spb_refinish');
        if (!M || !P || !F || !M.fromCall) return fail('this Shokker build has no frame pipeline (js/spb-intent-*.js not loaded): use spb_edit_zone / spb_add_zone / spb_refinish');
        var text = String(args.text == null ? '' : args.text).slice(0, 600), frame = null, repairs = [], src = 'frame';
        // M2 run 2 2026-10-07 (train A-0597 t2: Claude sent the frame's fields at the TOP level with ops as a JSON string; spb_do read only the text and asked "what exactly should change?"): lift them into frame
        if (!args.frame && args.ops != null) { var lift = {}, lops = args.ops; if (typeof lops === 'string') { try { lops = JSON.parse(lops); } catch (eL) { lops = null; } } if (Array.isArray(lops)) { ['v', 'act', 'decals', 'keep', 'scope'].forEach(function (k) { if (args[k] != null) lift[k] = args[k]; }); lift.ops = lops; if (!lift.act) lift.act = 'change'; args = Object.assign({}, args, { frame: lift }); repairs.push('frame fields were given at the top level: read as the frame'); } }
        if (args.frame && typeof args.frame === 'object' && typeof args.frame.ops === 'string') { var sops = null; try { sops = JSON.parse(args.frame.ops); } catch (eS) {} if (Array.isArray(sops)) { args = Object.assign({}, args, { frame: Object.assign({}, args.frame, { ops: sops }) }); repairs.push('frame.ops was a JSON string: parsed'); } }
        if (args.frame && typeof args.frame === 'object') {
            var fenv = { layers: liveLayers(host), hasLast: !!(P.last && P.last()) }; if (text) fenv.text = text;          // text only when the buyer's words were passed: without it the S7 "first request, no target named" guess (rule 15d) never second-guesses an explicit frame
            var fc = M.fromCall({ frame: args.frame }, fenv);
            if (!fc.ok) return fail('that frame is not valid: ' + (fc.errors || []).slice(0, 4).join('; ') + '. Fix it and call spb_do again (layer names must be exactly as spb_status shows them; parts: hood, roof, trunk, spoiler, front bumper, rear bumper, left side, right side).');
            frame = fc.frame; repairs = fc.repairs || [];
            var badL = repairs.filter(function (x) { return /unknown layer/.test(x); }); if (badL.length) return fail('that frame names a layer the paint does not have (' + badL.map(function (x) { return x.replace(/^.*unknown layer\s*/, ''); }).join(', ') + '). Layers are: ' + liveLayers(host).map(function (l) { return l.name; }).join(', ') + '. Use the exact name (spb_status lists them) and call spb_do again.');
        } else if (typeof args.frame === 'string' && args.frame.charAt(0) === '{') {
            var fj = null; try { fj = JSON.parse(args.frame); } catch (e) {}
            if (!fj) return fail('frame was a string that is not valid JSON: send it as an object');
            return prepare(Object.assign({}, args, { frame: fj }), host);
        } else if (text) {
            src = 'text'; var ft = frameFromText(text, host); if (ft.error) return fail(ft.error); frame = ft.frame; repairs = ['frame read from the buyer\'s text by the built-in reader'];
            var vf = F.validate ? F.validate(frame, { layers: liveLayers(host) }) : { ok: true, errors: [] };
            if (frame && frame.act === 'change' && vf && !vf.ok) { var hard = (vf.errors || []).filter(function (e) { return !/: part /.test(e); }); if (hard.length) return fail('the built-in reader produced a frame the app cannot use (' + hard.slice(0, 2).join('; ') + '): send a frame'); }
        } else return fail('send a frame (preferred) or the buyer\'s text');
        frame.producer = 'mcp-frame'; frame.src = src;
        var act = frame.act;
        if (act === 'undo' || act === 'redo') return fail('spb_do only makes changes: to take a change back call spb_undo');
        if (act === 'answer' || act === 'list') return fail('spb_do only makes changes: for questions use spb_encyclopedia, for choosing a finish spb_suggest_finishes / spb_find_finishes');
        if (act === 'nothing' || act === 'save') return fail('nothing to change (act ' + act + ')');
        if (act === 'ask_back') { var miss = arr(frame.missing); return { ok: true, frame: frame, repairs: repairs, ask: askView({ q: 'What exactly should change' + (miss.length ? ' (missing: ' + miss.join(', ') + ')' : '') + '? Which part of the car, and what should it look like?', chips: [] }, frame) }; }
        // M3 2026-10-07 (class OVER-ASKING on shade words; train A-0042 t2 "ok then dark roof": colour {word:'dark'} resolved to nothing and the plan asked
        // "What should the roof become?"): a bare shade word leaves the exact colour to us. Read it as a near-black / light-grey hex and say so (the reply offers another shade).
        arr(frame.ops).forEach(function (op) { var c = op && op.look && op.look.colour; if (!c || typeof c !== 'object' || c.hex) return; var w = String(c.word || '').toLowerCase().trim(), hx = SHADE[w];
            if (hx) { c.hex = hx[0]; repairs.push('"' + w + '" read as ' + hx[1] + ' ' + hx[0] + ': tell the buyer and offer another shade'); } });
        try { var notes = M.resolveLooks ? M.resolveLooks(frame, host.find || null) : []; if (notes && notes.length) repairs = repairs.concat(notes); } catch (e3) {}
        // M2 2026-10-07 (M1 A-0597 "no make it so" = make the RIGHT door like the left: the frame named BOTH sides, the scope check passed because it compared the frame with itself):
        // the frame's parts are compared with the BUYER's words (text). A part the words never name, or name only as the reference ("same as the left"), stops the call.
        var Gt = W.SpbMcpGate, fparts = []; arr(frame.ops).forEach(function (op) { var tg = op && op.target || {}; if (tg.kind === 'part') arr(tg.parts).forEach(function (p) { if (fparts.indexOf(p) === -1) fparts.push(p); }); });
        if (Gt && Gt.partsCheck && text && fparts.length && args.confirm !== true) {
            var pc = null; try { pc = Gt.partsCheck(fparts, text); } catch (ePc) { pc = null; }
            if (pc) return fail('NOTHING was changed: the frame changes ' + pc.unnamed.join(' and ') + ', but the buyer\'s words name ' + (pc.named.length ? 'only ' + pc.named.join(' and ') : 'no such part') + (pc.ref.length ? ' (' + pc.ref.join(' and ') + ' is only the reference they compare with)' : '') + '. Send the frame again with only the part(s) the buyer named, or ask them; pass confirm:true only if they really asked for ' + pc.unnamed.join(' and ') + ' too.', { changed: false, parts_check: pc });
        }
        // M2 2026-10-07 (M1 A-0224 "give me a holo roof": finish.family "holo" became Soft Gloss with verdict ok): a finish the planner cannot plan is refused BEFORE applying, with catalogue candidates
        var subs = finishSubs(frame, P);
        if (subs.length) {
            var cands = []; subs.forEach(function (sb) { if (typeof host.find !== 'function') return; var r = []; try { r = host.find({ query: sb.want, type: 'finish', limit: 4 }) || []; } catch (eF) { r = []; } arr(r).slice(0, 4).forEach(function (x) { var k = x && (x.key || x.id); if (k && cands.indexOf(k) === -1) cands.push(k + (x.name ? ' (' + x.name + ')' : '')); }); });
            return fail('NOTHING was changed: the finish "' + subs.map(function (s) { return s.want; }).join('", "') + '" is not one spb_do can plan (it would silently have become ' + subs[0].would + '). ' + (cands.length ? 'Catalogue looks that match: ' + cands.slice(0, 5).join(', ') + '. ' : 'Call spb_find_finishes for it. ') + 'Apply one with spb_add_zone (region {part:...}, finish = its key) or spb_edit_zone on the zone that covers that part, or ask the buyer which one.', { changed: false, finish_not_known: subs });
        }
        var env = P.live(), pl = P.plan(frame, env);
        if (!pl) return fail('the planner returned nothing');
        if (pl.act === 'ask' || pl.ask) return { ok: true, frame: frame, repairs: repairs, ask: askView(pl.ask, frame), plan: planView(pl) };
        if (pl.act !== 'change' || !(pl.steps || []).length) return fail('the planner could not make a plan from that frame' + ((pl.errors || []).length ? ': ' + pl.errors.slice(0, 3).join('; ') : '') + ((pl.notes || []).length ? ' (' + pl.notes.slice(0, 2).join('; ') + ')' : ''));
        var flat = P.toQueue(pl), txt = text || textOf(frame), v = null, vq = null;
        try { var VF = IV(); if (VF && VF.onQueue && flat.length) vq = VF.onQueue(flat, { label: 'MCP spb_do', mcp: false, text: txt, producer: 'mcp-frame' }); } catch (e4) { vq = null; }
        var verify = vq && vq.v ? { stage: 'A-mask', mode: vq.v.mode, verdict: vq.v.verdict, findings: (vq.v.findings || []).slice(0, 6), failed: (vq.failed || []).slice(0, 4) } : { stage: 'A-mask', verdict: 'not_run' };
        return { ok: true, frame: frame, repairs: repairs, plan: planView(pl), _plan: pl, flat: flat, verified: vq && vq.queue ? vq.queue : null, verify: verify, text: txt, vfailed: vq && vq.failed || [] };
    }

    // ------------------------------------------------------------------ the measured numbers
    function dims(host) { try { if (host && host.dims) return host.dims(); var c = W.document && W.document.getElementById('paintCanvas'); if (c) return [c.width, c.height]; } catch (e) {} return [2048, 2048]; }
    function px(cells, host) { var d = dims(host); return Math.round((cells || 0) * (d[0] / N) * (d[1] / N)); }
    function measuredOf(rep, host) {
        if (!rep || rep.verdict === 'skip' || rep.verdict === 'error') return { verdict: 'not_measured', why: rep && rep.why || 'the rendered check did not run (preview not synced or SPB_AI_REPORT off): look at the picture / call spb_check', findings: [] };
        var m = { verdict: rep.verdict === 'undo-ask' ? 'reverted' : (rep.verdict || 'ok'), changed_px: px(rep.changed, host), paint_px: px(rep.paint, host), spec_px: px(rep.spec, host), outside_px: px(rep.outside, host), inside_px: px(rep.inside, host), decal_px: px(rep.decal, host), kept_px: px(rep.kept, host),
            findings: arr(rep.findings).map(function (f) { return f.code + (f.cells != null ? ' (' + px(f.cells, host) + ' px)' : (f.outside != null ? ' (' + px(f.outside, host) + ' px outside)' : (f.pct != null ? ' (' + f.pct + '%)' : ''))); }),
            coverage: rep.coverage_cells ? {unit:rep.coverage_unit,cells:rep.coverage_cells,changed_paint_cells:rep.surface_paint,pct:Math.round(100 * (rep.surface_paint || 0) / rep.coverage_cells),basis:"Measured 256x256 preview grid; not native pixel verification"} : undefined,
            artwork_check: rep.artwork_check || undefined, scope: { colour_target: rep.colour_target || undefined, parts: arr(rep.parts), layers: arr(rep.layers), whole_car: !!rep.whole, protected_decal_layers: arr(rep.protect) }, line: rep.line || rep.would || undefined, grid: 'a 256x256 grid of the live preview; one cell = ' + px(1, host) + ' px' };
        if (rep.trim) m.trimmed = rep.trim; if (rep.note) m.note = rep.note; if (rep.after_trim) m.after_trim = { changed_px: px(rep.after_trim.changed, host), outside_px: px(rep.after_trim.outside, host), decal_px: px(rep.after_trim.decal, host) };
        if (rep.paint === 0 && rep.spec === 0) m.nothing_visible = true;
        return honest(m);
    }
    // M2 2026-10-07 (M1 A-0597: line "Your numbers and logos are untouched." while decal_px = 6016, findings [], verdict ok): the verdict and the line FOLLOW the measured numbers.
    // decal_px >= 1280 (20 cells) or outside_px >= max(1280, 2% of the change) = verdict "reported" + a finding; any decal_px > 0 drops the "untouched" claim.
    var DECAL_REPORT = 1280, OUT_REPORT = 1280;
    function honest(m) {
        if (!m || m.verdict === 'not_measured') return m;
        m.findings = arr(m.findings).slice(); var line = String(m.line || ''), rep = false;
        var hasF = function (re) { return m.findings.some(function (f) { return re.test(String(f)); }); };
        if (m.decal_px > 0) {
            line = line.replace(/\s*Your [^.]*?(?:is|are) untouched\./i, '').replace(/\s*The preview check detected small differences in protected artwork; preservation is unverified\. Review the result or use Undo\./i, '');
            line += m.decal_px >= DECAL_REPORT ? ' ' + m.decal_px + ' px of your numbers / logos changed: check them (spb_undo if they should not have).' : ' The preview check estimates ' + m.decal_px + ' px of differences in protected artwork; preservation is unverified. Review the result or use Undo.';
            if (m.decal_px >= DECAL_REPORT) { rep = true; if (!hasF(/^decal/)) m.findings.push('decal (' + m.decal_px + ' px)'); }
        }
        if (m.outside_px >= Math.max(OUT_REPORT, 0.02 * (m.changed_px || 0))) { rep = true; if (!hasF(/^spill/)) m.findings.push('outside (' + m.outside_px + ' px changed outside the parts / layers it was meant for)'); line += ' ' + m.outside_px + ' px changed OUTSIDE the named parts.'; }
        if (m.nothing_visible && !/nothing|no visible/i.test(line)) { line = 'No visible change on the render (0 paint and 0 spec pixels changed).'; if (m.verdict === 'ok') m.verdict = 'no_visible_change'; }
        if (rep && m.verdict === 'ok') m.verdict = 'reported';
        m.line = line.trim() || undefined;
        return m;
    }
    // M2 2026-10-07: the measured block for the OTHER write tools (spb_apply_scheme / spb_add_zone / spb_edit_zone / spb_refinish / spb_add_graphic), measure-only (warn mode: never trims or undoes)
    function measureOnly(E, text, flat, host) {
        var R = IR(); if (!R || !R.check || !E || !E.zdiff || !E.zdiff.s3b) return Promise.resolve(measuredOf(null, host));
        // Scope evidence only, not an executable/replay queue. Copy scalar fields.
        E._nativeColourMeasureQueue = flat && flat.length && flat.every(function (op) { return op.kind === 'layer' && op.colour != null; }) ? flat.map(function (op) { return {kind:'layer',layer:op.layer,colour:op.colour,sourceColour:op.sourceColour}; }) : null;
        E._nativeColourMeasureText = E._nativeColourMeasureQueue ? String(text || '') : '';
        var hc = host && host.ctx ? host.ctx(E) : {}, ctx0 = { synced: hc.synced || null, undo: function () {}, reseal: function () {}, render: function () {} }, was = W.SPB_AI_REPORT, p;
        try { W.SPB_AI_REPORT = 'warn'; p = Promise.resolve(R.check(E, String(text || ''), { queue: flat || [], offline: false }, ctx0)).then(function (x) { return x; }, function () { return null; }); }
        finally { if (was === undefined) { try { delete W.SPB_AI_REPORT; } catch (e1) { W.SPB_AI_REPORT = undefined; } } else W.SPB_AI_REPORT = was; }
        return p.then(function (rep) { if (rep) { try { E.s3 = rep; } catch (e2) {} } return measuredOf(rep, host); });
    }
    // the finish the result REALLY got, against the one that was asked for (applied lines say "finish Soft Gloss")
    function finishCheck(m, applied, frame) {
        if (!m || !frame) return m; var wants = [];
        arr(frame.ops).forEach(function (op) { var f = op && op.look && op.look.finish; if (f && (f.family || f.key)) wants.push(String(f.family || f.key).toLowerCase().replace(/^[a-z]+::/, '').replace(/_/g, ' ')); });
        if (!wants.length) return m;
        var got = []; arr(applied).forEach(function (l) { var mm = /\bfinish ([^;,]+)/i.exec(String(l)); if (mm) got.push(mm[1].trim()); });
        if (!got.length) return m;
        var miss = wants.filter(function (w) { var t = w.split(/\s+/)[0]; return !got.some(function (g) { return g.toLowerCase().indexOf(t) !== -1 || (t === 'mirror' && /chrome/i.test(g)) || (t === 'matte' && /matt?e?/i.test(g)) || (t === 'metal' && /metal/i.test(g)); }); });
        if (miss.length) { m.findings = arr(m.findings).concat(['finish-substituted (asked ' + miss.join(', ') + ', got ' + got.join(', ') + ')']); if (m.verdict === 'ok' || m.verdict === 'reported') m.verdict = 'substituted'; m.line = (m.line ? m.line + ' ' : '') + 'The finish is ' + got[0] + ', NOT the ' + miss[0] + ' that was asked for.'; }
        return m;
    }
    function repFor(E) { var R = IR(); if (!E) return null; if (E.s3 && E.s3.v) return E.s3; try { var l = R && R.since ? R.since(0) : [], hit = null; l.forEach(function (v) { if (v && v.eid === E.id) hit = v; }); return hit; } catch (e) { return null; } }
    function measureEntry(E, text, flat, host, fresh) {
        var R = IR(); if (!R || !R.check || !E) return Promise.resolve(null);
        var ctx = host && host.ctx ? host.ctx(E) : null;
        return Promise.resolve(R.check(E, text, { queue: flat || [], offline: false }, ctx)).then(function (rep) { return rep; }, function () { return null; });
    }
    function zonesOf(E) { var d = E && E.zdiff || {}; return { edited: arr(d.edited).map(function (z) { return z.name; }).slice(0, 12), added: arr(d.added).map(function (z) { return z.name || String(z.id); }).slice(0, 12) }; }
    function undoView(E, reverted) {
        if (!E) return null;
        return { id: E.id, undoable: !!E.undoable && !E.undone, already_undone: !!(E.undone || reverted), how: (E.undone || reverted) ? 'already taken back' : 'call spb_undo (steps 1) to take this change back; it is the most recent change' + ' (also an Undo button on the change in the Shokker AI panel)' };
    }
    function rememberLast(E, P) {   // stopgap when the plan was applied as a flat queue (no SpbIntentPlan.run): "thinner" / "same on the right" after this still resolve
        try {
            var p = IP(); if (!p || !p.setLast || !E || !E.zdiff) return;
            var added = arr(E.zdiff.added).map(function (z) { return String(z.id); }), ids = uniq(arr(E.zdiff.edited).map(function (z) { return String(z.id); }).concat(added)), pl = P._plan, s0 = (pl.steps || [])[0] || {};
            if (!ids.length) return;
            p.setLast({ ops: pl._rootOps || pl._frameOps || null, ids: ids, added: added, prim: s0.prim, op: s0._op || null, target: s0._op && s0._op.target || null, look: s0._look || null, t: Date.now() });
        } catch (e) {}
    }

    // ------------------------------------------------------------------ spb_do
    function doCall(args, host) {
        args = args || {}; host = host || {};
        var P; try { P = prepare(args, host); } catch (e) { return Promise.resolve(fail('spb_do failed while planning: ' + (e && e.message || e))); }
        if (!P.ok) return Promise.resolve(P);
        if (P.ask) return Promise.resolve({ ok: true, result: { changed: false, ask: P.ask, frame: slimFrame(P.frame), repairs: P.repairs, plan: P.plan, note: 'NOTHING was changed. Put the question to the buyer, then call spb_do again with the answer (a choice\'s frame, or a new frame).' } });
        var chosen = P.verified || P.flat, v = P.verify;
        var refused = v.failed && v.failed.length && !(P.verified && P.verified.length);
        if (refused) return Promise.resolve(fail('the app refused this change before applying it: ' + v.failed.join(' | ') + ' Nothing was changed. Narrow the target (name the parts / layers) or ask the buyer.', { changed: false, verify: v, frame: slimFrame(P.frame) }));
        var pl = P._plan, special = (pl.steps || []).some(function (s) { return s.flames || s.undo || s.redo; }), repaired = v.verdict === 'repair' && !!P.verified;
        var hooks = (pl.steps || []).some(function (s) { return (s.ops || []).some(function (o) { return o._above || o._aboveAdd || o._intersect; }); });          // "everything except the roof": the kept-roof copies must sit ABOVE the new look: only the planner run does that
        if ((special || hooks) && !host.planRun) return Promise.resolve(fail('this plan needs the planner run step (' + (special ? 'flames / undo inside a plan' : 'zone stacking: a kept part or an intersect') + '), which is not wired into this build yet, and applying it as plain zones would change the parts you want kept. Nothing was changed. Split it into simpler changes (one part at a time), or use spb_edit_zone.', { changed: false, plan: P.plan }));
        if (repaired && (special || hooks)) return Promise.resolve(fail('the scope check had to cut this plan back (' + v.findings.map(function (f) { return f.code + ' ' + (f.what || ''); }).join('; ') + ') and a cut-back plan cannot keep its stacking. Nothing was changed. Name the parts / layers explicitly.', { changed: false, verify: v }));
        var nativeColour = null;
        if (!W.SPB_CX3_OFF && !special && !hooks && !repaired && W.SpbNativeLayerColour && W.SpbNativeLayerColour.frameQueue) {
            nativeColour = W.SpbNativeLayerColour.frameQueue(P.frame, String(args.text || ''), {layers:liveLayers(host)});
            if (nativeColour && nativeColour.error) return Promise.resolve(fail(nativeColour.error, {changed:false, frame:slimFrame(P.frame)}));
        }
        var useNative = !!(nativeColour && nativeColour.queue), useRun = !useNative && !!host.planRun && !repaired && !!IP().asQueue;
        var queue = useNative ? nativeColour.queue : (useRun ? IP().asQueue(pl) : (chosen.slice ? chosen.slice() : chosen));
        if (args.dry_run) return Promise.resolve({ ok: true, result: { dry_run: true, changed: false, frame: slimFrame(P.frame), repairs: P.repairs, plan: P.plan, verify: v, applied_as: useNative ? 'native layer colour (source artwork composited)' : useRun ? 'planner run (hooks kept)' : 'flat zone queue', note: 'dry run: nothing was changed. Call again without dry_run to apply.' } });
        if (!host.apply) return Promise.resolve(fail('no apply path in this build'));
        var before = host.last ? host.last() : null, beforeId = before ? before.id : null;
        var ensure = host.ensure ? Promise.resolve().then(function () { return host.ensure(); }).then(null, function () {}) : Promise.resolve();
        var existingPatternReport = null;
        return ensure.then(function () {
            var C=W.SpbConversationScope;
            if(!W.SPB_CX3_OFF&&!special&&!repaired&&W.SpbNamedPatternRefinement&&C&&C.status().available)existingPatternReport=W.SpbNamedPatternRefinement.captureFrame(P.frame,pl,{zones:typeof zones==='undefined'?[]:zones,current:true,documentStamp:C.stamp()});
            return host.apply(queue, { frame_steps: (pl.steps || []).length });
        }).then(function (r) {
            if (!r || r.ok === false) return { ok: false, error: (r && r.error) || 'nothing was applied', result: r && r.result };
            var E = host.last ? host.last() : null, fresh = !!(E && E !== before && E.id !== beforeId && E.role === 'ai');
            if (fresh) { E._s8 = { text: P.text, frame: slimFrame(P.frame), producer: 'mcp-frame', via: useNative ? 'native-layer-colour' : useRun ? 'run' : 'flat' }; }
            if(fresh&&existingPatternReport)E._cxPatternReport=existingPatternReport;
            if (fresh && !useRun && !useNative) rememberLast(E, P);
            var res0 = (r && r.result) || {};
            // Native layer operations use the existing native report-only contract.
            // The zone reporter cannot safely trim a layer overlay into zone masks.
            var meas = fresh ? (useNative ? measureOnly(E, P.text, queue, host) : measureEntry(E, P.text, P.flat, host, false)) : Promise.resolve(null);
            return meas.then(function (rep) {
                var m = useNative && rep ? rep : measuredOf(rep, host), reverted = m.verdict === 'reverted' || !!(E && (E.undone || E.undoneByCheck));
                if (!reverted) { m = finishCheck(m, res0.applied, P.frame); try { if (/\bflip/i.test(JSON.stringify(P.plan || {}))) { m.findings = arr(m.findings).concat(['direction flipped by the plan (check the fade runs the way the buyer asked)']); if (m.verdict === 'ok') m.verdict = 'reported'; } } catch (eFl) {} }          // M2 2026-10-07: M1 A-0330 "feather it more" flipped the ramp with verdict ok
                var imgP = (reverted || (rep && rep.trim)) && host.images ? Promise.resolve(host.images()).then(function (im) { return im; }, function () { return r.images; }) : Promise.resolve(r.images);
                return imgP.then(function (images) {
                    var out = { changed: !reverted && arr(res0.applied).length > 0, applied: res0.applied, failed: res0.failed && res0.failed.length ? res0.failed : undefined,
                        frame: slimFrame(P.frame), repairs: P.repairs.length ? P.repairs : undefined, plan: P.plan, verify: v, applied_as: useNative ? 'native layer colour (source artwork composited)' : useRun ? 'planner run (hooks kept)' : 'flat zone queue (planner hooks skipped: flames / above / intersect need the planner run)' + (repaired ? '; the scope check cut the plan back' : ''),
                        measured: m, undo: undoView(E, reverted), zones_touched: res0.zones_touched, zones: zonesOf(E), problems_found_by_app: res0.problems_found_by_app };
                    if (reverted) out.question_for_buyer = (m.line || (E && E.text) || '').split('\n')[0];
                    if (!reverted && m.verdict !== 'ok' && m.verdict !== 'not_measured') out.tell_buyer = m.line;
                    out.note = reverted ? 'The app measured this change, found it did not match what was asked, and TOOK IT BACK (nothing from it remains). The picture shows the car as it is now. Ask the buyer the question above.' : 'Applied and measured. The picture is the live preview; trust measured.* over your own reading of it. Call spb_check for the same numbers later.';
                    return { ok: true, result: out, images: images };
                });
            });
        });
    }

    // ------------------------------------------------------------------ spb_check
    function lastChange(host) {
        var lg = []; try { lg = host && host.log ? host.log() : []; } catch (e) {}
        for (var i = lg.length - 1; i >= 0; i--) { var x = lg[i]; if (x && x.role === 'ai' && x.lines && x.lines.length && x.zdiff) return x; }
        for (var j = lg.length - 1; j >= 0; j--) { var y = lg[j]; if (y && y.role === 'ai' && y.lines && y.lines.length) return y; }
        return null;
    }
    function checkCall(args, host) {
        args = args || {}; host = host || {};
        if (flagOff()) return Promise.resolve(fail('spb_check is switched off (SPB_AI_FRAME = 0)'));
        var E = lastChange(host);
        if (!E) return Promise.resolve({ ok: true, result: { none: true, note: 'No change has been made in this session yet, so there is nothing to check. Use spb_get_state / spb_preview to see the paint as it is.' } });
        var rep = repFor(E), s8 = E._s8 || {}, text = s8.text || E._nativeColourMeasureText || '', p = Promise.resolve(null), measuredNow = false;
        if ((args.fresh || !rep) && !E.undone && E.zdiff && E.zdiff.s3b) {
            // measure-only: no ctx, so the reporter can never trim or undo from here
            var R = IR(); if (R && R.check) {
                measuredNow = true; var hc = host.ctx ? host.ctx(E) : {}, ctx0 = { synced: hc.synced || null, undo: function () {}, reseal: function () {}, render: function () {} }, was = W.SPB_AI_REPORT;
                try { W.SPB_AI_REPORT = 'warn'; p = Promise.resolve(R.check(E, text || E.request || '', { queue: E._nativeColourMeasureQueue || [], offline: false }, ctx0)).then(function (x) { return x; }, function () { return null; }); }          // warn = measure and log only: the reporter reads its mode when called, so this can never trim, undo or rewrite the reply
                finally { if (was === undefined) { try { delete W.SPB_AI_REPORT; } catch (e1) { W.SPB_AI_REPORT = undefined; } } else W.SPB_AI_REPORT = was; }
            }
        }
        return p.then(function (fresh) {
            var use = fresh && fresh.verdict && fresh.verdict !== 'skip' ? fresh : rep;
            var m = measuredOf(use, host);
            var out = { last_change: { id: E.id, request: String(E.request || '').slice(0, 160), via: E.kind || null, applied: arr(E.lines).slice(0, 12), notes: arr(E.notes).slice(0, 4), still_applied: !E.undone, taken_back_by_check: !!E.undoneByCheck },
                measured: m, frame: s8.frame || undefined, zones: zonesOf(E), undo: undoView(E, !!E.undoneByCheck), measured_now: measuredNow };
            try { var lp = IP() && IP().last ? IP().last() : null; if (lp) out.planner_memory = { prim: lp.prim, ids: arr(lp.ids).slice(0, 8), target: lp.target || undefined }; } catch (e) {}
            if (!use) out.note = 'The rendered check has no before-picture for this change (the preview was not synced when it was applied), so only the applied lines are known: call spb_preview and look.';
            else if (E.undone) out.note = 'This change was taken back (undone): the paint shows the state before it. The numbers describe what it did while it was applied.';
            else out.note = 'Measured on the rendered preview' + (measuredNow ? ' just now against the picture taken before the change (so it also contains anything changed after it)' : ' when the change was applied') + '. If findings is not empty or outside_px / decal_px is large, tell the buyer and offer spb_undo.';
            return { ok: true, result: out };
        });
    }

    // ------------------------------------------------------------------ page-side tool definitions (js/spb-pro-ai.js makeTools hunk)
    function tools(queue, host) {
        host = host || {};
        return defs().map(function (d) {
            return { name: d.name, description: d.description, parameters: d.parameters, handler: function (a) {
                var run = d.name === 'do' ? doCall(a || {}, host) : checkCall(a || {}, host);
                return Promise.resolve(run).then(function (r) { return { __mcpDone: r }; }, function (e) { return { __mcpDone: { ok: false, error: 'spb_' + d.name + ' failed: ' + (e && e.message || e) } }; });
            } };
        });
    }
    function owns(name) { return name === 'do' || name === 'check'; }

    W.SpbMcpFrames = { VERSION: VERSION, tools: tools, listTools: listTools, defs: defs, owns: owns, prepare: prepare, doCall: doCall, checkCall: checkCall, textOf: textOf, measuredOf: measuredOf, measureOnly: measureOnly, honest: honest, finishCheck: finishCheck, finishSubs: finishSubs, _px: px };
})();
