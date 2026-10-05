/* SPB SUPPORT ("Talk to Shokker", 2026-10-02): the built-in help assistant. Works with no AI and no internet.
   - classify(text)        what kind of question is this? a pasted error / a problem to diagnose / an FAQ / a manual search / off topic
   - diagnose(symptom)     reads the buyer's LIVE settings (iRacing User ID, number mode, car folder, template layers, zones, preview, server) and the real files in the car folder; returns a checklist card
   - fix(id, cb)           the one-click fixes the checklist offers (all ordinary settings the buyer could change by hand)
   - snapshot()            the same facts as compact JSON, for the AI to talk the buyer through
   FAQ / error / answer text lives in spb-support-answers.js (loaded after this file).
   ES5 only. classify() and the check functions are pure so Node can test them with a fake window (_easy_claude_work/support_eval.js).
   FACTS (verified 2026-10-01/02): iRacing support articles 31000133480 + 31000153524 and Trading Paints help for the iRacing side (customer ID, car_ vs car_num_ chosen by iRacing's "Hide Car Numbers" setting,
   Ctrl+R = Reload Car Textures, 1024/2048 only, wrong files fall back silently to the UI paint-shop scheme); the app code for everything on the Shokker side (see docs/ai_knowledge/10_support_troubleshooting.md). */
(function () {
    'use strict';
    var W = window;
    function $(id) { try { return document.getElementById(id); } catch (e) { return null; } }
    function val(id) { var e = $(id); return e ? String(e.value == null ? '' : e.value).trim() : ''; }
    function chk(id) { var e = $(id); return e ? !!e.checked : null; }
    function esc(s) { return String(s == null ? '' : s).replace(/[&<>"]/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]; }); }
    function norm(s) { return String(s || '').toLowerCase().replace(/[\u2018\u2019]/g, "'").replace(/[^a-z0-9+#.'_ ]+/g, ' ').replace(/\s+/g, ' ').trim(); }
    function ago(sec) { sec = Math.max(0, Math.round(sec)); if (sec < 90) return sec + ' seconds'; if (sec < 5400) return Math.round(sec / 60) + ' minutes'; if (sec < 172800) return Math.round(sec / 3600) + ' hours'; return Math.round(sec / 86400) + ' days'; }
    var Q = '\u201c', QE = '\u201d', AP = '\u2019';

    // ------------------------------------------------------------------ 1. what kind of question is this?
    var VOCAB = /\b(spb|shokker|paint|paints|painting|iracing|i racing|render|renders|rendering|zone|zones|finish|finishes|spec|specular|layer|layers|psd|tga|mip|template|templates|livery|liveries|car|cars|truck|chrome|matte|gloss|satin|candy|pearl|metal|flake|carbon|sim|preview|export|deploy|folder|numbers?|sponsors?|decal|decals|clearcoat|roughness|metallic|stripe|stripes|colou?rs?|trading ?paints?|alt|ctrl|api|copilot|chat|license|licence|install|installer|update|crash|undo|mask|wire|pitbox|custom|member|customer|file|files|texture|wrap|helmet|suit|hood|roof|spoiler|bumper|wheel|wheels|openrouter|claude|openai|gpt|brain|mcp)\b/;
    var OFFTOPIC_HINT = /\b(lose weight|diet|recipe|chili|cook|weather|president|election|super bowl|bitcoin|crypto|stock market|horoscope|joke|poem|lyrics|homework|python (code|script)|javascript code|cover letter|resume|essay|write me (a|an) (essay|story|poem|email|script|letter)|translate|best setup|fuel strategy|tire pressure|spring rate|brake bias|lap times?|hotlap|racing line|overtake|drafting|capital of|who won|how old is|what is the meaning|tell me about yourself|math problem|ignore (all |your )?(previous|prior|above) instructions|system prompt|jailbreak)\b/;
    // iRacing / PC problems that are not Shokker problems: say so kindly instead of running a Shokker checklist
    var SIM_ISSUE = /\b(easy anti.?cheat|force feedback|\bffb\b|fanatec|simucube|pedals?|vr headset|frame ?rate|stutter\w*|netcode|disconnect\w*|iracing (won'?t|wont|doesn'?t|doesnt|can'?t|cant|will not|does not) (launch|start|open|run|install|update|connect)|iracing launcher|spinning out|eau rouge)\b/;
    var SHOKKER_WORDS = /\b(spb|shokker|paint|livery|render\w*|tga|psd|zone|zones|finish|finishes|spec map|template|chrome|decal|sponsor)\b/;
    var SMALLTALK = /^\s*(hi|hello|hey|yo|howdy|good (morning|afternoon|evening)|thanks|thank you|thx|ty|cheers|ok|okay|cool|nice|great|awesome|perfect|bye|goodbye|lol|wow)\b[ !.,?]*$/i;
    var FAIL = /\b(won'?t|wont|can'?t|cant|cannot|doesn'?t|doesnt|does not|did not|didn'?t|didnt|isn'?t|isnt|not|never|no|fail\w*|stuck|hang\w*|frozen|freez\w*|crash\w*|broken|greyed|grayed|disabled|nothing|error\w*|wrong|still|missing|problem\w*|issue\w*|why|bad|weird|stopped|dead|blank|empty|gone|lost|ignor\w*|different|twice|double|duplicate\w*|invisible|transparent|washed|faded|muddy|showing|baked|too|boring|smeared|patches|ugly)\b/;
    var IMPERATIVE = /^\s*(please |pls )?(make|give|add|put|turn|change|apply|create|i want|i'd like|i would like|can you (make|add|give|put|paint|turn|change|set)|could you|let'?s|(paint|set|design|show) (the|my|it|a|an|this|me|everything|all)\b)\b/;
    var DESIGNV = /^\s*(please |pls )?(make|add|put|paint|turn|change|apply|create|design|give|can you (make|add|give|put|paint|turn|change|set))\b/;
    var DESIGN_ANY = /\b(add|make|put|give|change|paint)\b[^.?!]{0,30}\b(stripes?|numbers?|hood|roof|sides?|spoiler|bumpers?|colou?rs?|chrome|matte|gloss\w*|flames?|camo|carbon)\b/;
    var NEGW = "(?:not|never|no|won'?t|wont|can'?t|cant|cannot|doesn'?t|doesnt|don'?t|dont|isn'?t|isnt|didn'?t|didnt|aren'?t|arent)";
    function R(src, flags) { return new RegExp(src.replace(/NEG/g, NEGW), flags || ''); }

    // problem symptoms: each regex list is OR-ed. 'ingame' is first so it wins ties; two different symptoms in one message mean 'general' (a full check covers everything).
    var SYMPTOMS = [
        { id: 'ingame', re: [
            R("\\bNEG\\b[^.?!]{0,24}\\b(show\\w*|appear\\w*|load\\w*|updat\\w*|visible|there|work\\w*|chang\\w*|appl\\w*|pick\\w* up)\\b[^.?!]{0,30}\\b(iracing|i racing|sim|game|in[- ]sim|in game|garage|track|race)\\b"),
            R("\\b(iracing|i racing|sim|game|in[- ]sim|garage)\\b[^.?!]{0,40}\\b(still|stays?|shows?|displays?|default|stock|plain|blank|old|previous|same|white|grey|gray|NEG)\\b[^.?!]{0,30}\\b(white|grey|gray|old|default|stock|plain|blank|paint|livery|car|change\\w*|update\\w*|show\\w*|load\\w*|work\\w*|same)\\b"),
            /\b(car|paint|livery)\b[^.?!]{0,20}\b(is|looks|stays|shows)\b[^.?!]{0,10}\b(still )?(white|blank|plain|default|stock|grey|gray|the same|the old|old)\b[^.?!]{0,40}\b(iracing|i racing|sim|game|track|session|garage)\b/,
            /\b(rendered|deployed|exported|saved)\b[^.?!]{0,40}\b(but|and)\b[^.?!]{0,40}\b(nothing|not|still|no)\b/,
            /\b(my )?(friends?|others?|opponents?|everyone|other drivers?)\b[^.?!]{0,40}\b(see|sees|saw)\b[^.?!]{0,30}\b(old|different|default|stock|nothing|another|white)\b/,
            R("\\b(paint|livery|car)\\b[^.?!]{0,30}\\bNEG\\b[^.?!]{0,16}\\b(show\\w*|appear\\w*|loading|load)\\b"),
            /\b(iracing|sim|game)\b[^.?!]{0,30}\b(ignores?|ignoring|ignored|doesn'?t see|can'?t see|not seeing|not picking)\b/,
            /\b(works?|worked|shows?|showed)\b[^.?!]{0,30}\b(on|for|with|in)\b[^.?!]{0,24}\bbut not\b/,
            /\b(on track|in the race|in session|in a session|when i (get|go|drive|load|jump))\b[^.?!]{0,30}\b(old|previous|default|white|stock|plain)\b/,
            /\bpaint shop\b[^.?!]{0,40}\bbut\b[^.?!]{0,40}\b(old|different|default|white|not)\b/
        ] },
        // 2026-10-04 'files': "I can't find my files / the folder is empty / I follow the paint steps and there's nothing there" (a real buyer's words).
        // The fix is to SHOW them where the render went (Explorer opens on the file), not another explanation of the path.
        { id: 'files', re: [
            /\bnothing\b[^.?!]{0,24}\b(in|inside|into)\b[^.?!]{0,20}\b(iracing|paint|car)?\s?folder\b/,
            /\b(folder|files?|documents|tga|car_num\w*|car_spec\w*|user paint|iracing paint|paint folder|steps)\b[^.?!]{0,60}\b(there'?s|there is|theres)\s+(nothing|no files?)\b/,
            /\b(folder|directory)\b[^.?!]{0,24}\b(is|was|looks|seems|comes up|shows)\s+(empty|blank)\b|\bempty (car |paint |iracing )?folder\b/,
            R("\\b(can'?t|cant|cannot|couldn'?t|couldnt|unable to|NEG)\\s+(find|locate|see)\\b[^.?!]{0,24}\\b(my |the |any |those |these )?(files?|tga|tgas|car_num\\w*|car_spec\\w*|paint files?|spec files?|renders|exports|rendered (paint|files?))\\b"),
            /\b(files?|tga|car_num\w*|car_spec\w*)\b[^.?!]{0,30}\b(aren'?t|arent|are not|isn'?t|isnt|is not|not)\s+(there|in (the|my|that) folder)\b/
        ] },
        { id: 'render', re: [
            R("\\b(NEG|fail\\w*|stuck|hang\\w*|frozen|freez\\w*|crash\\w*|broken|greyed|grayed|disabled|nothing happens?|dead|error\\w*|no response|stops?|quits?)\\b[^.?!]{0,40}\\b(render\\w*|export\\w*|deploy\\w*|saving)\\b"),
            R("\\b(render\\w*|export\\w*|render button|deploy\\w*)\\b[^.?!]{0,40}\\b(NEG|not working|fail\\w*|stuck|hang\\w*|frozen|crash\\w*|broken|greyed|grayed|disabled|nothing|error\\w*|never finishes|takes forever|forever|stops?|quits?)\\b"),
            /\b(render server|paint engine|engine is offline|server (is )?(down|offline|unreachable)|unreachable|retrying)\b/,
            /\b(press|click|hit)\w*\b[^.?!]{0,16}\brender\b[^.?!]{0,40}\b(nothing|no |error|fail|stuck|freez\w*|crash\w*|clos\w*|quit\w*|hangs?)\b/,
            /\b(sitting|spinning|running|been)\b[^.?!]{0,20}\brendering\b|\brendering\b[^.?!]{0,30}\b(minutes|forever|dead|hung|too long)\b/,
            /\b(says|saying|keeps saying|tells me)\b[^.?!]{0,30}\b(zones?|finish|set up zones|paint file|full path)\b|\bzones?\b[^.?!]{0,30}\b(error|keeps)\b/
        ] },
        { id: 'look', re: [
            /\b(look|looks|looking|colou?rs?|shiny|shine|chrome|flat|dull|dark|darker|washed|faded|muddy|different|wrong|off|bad|ugly|metal\w*|candy|pearl|flake|reflect\w*|gloss\w*|matte|satin|transparent|black|numbers?|sparkle\w*|glitter\w*|shimmer\w*|weird|pink|grey|gray)\b[^.?!]{0,40}\b(in iracing|in the sim|in sim|in game|in the game|when i drive|on track|in the garage|inside iracing)\b/,
            /\b(in iracing|in the sim|in sim|in game|when i drive|on track)\b[^.?!]{0,50}\b(looks?|colou?rs?|shiny|chrome|flat|dull|dark|washed|faded|different|wrong|off|bad|plain|metal\w*|candy|pearl|flake|reflect\w*|black|transparent|see.?through|invisible|twice|double|two numbers|sparkle\w*|weird|pink)\b/,
            /\b(mask|wire|wireframe|template)\b[^.?!]{0,24}\b(layers?|lines?|outlines?)\b[^.?!]{0,40}\b(show\w*|visible|on my car|in iracing|in the sim|in sim|in game|baked|stuck)\b/,
            /\b(wire ?frame|green lines?|grid lines?|uv lines?)\b[^.?!]{0,40}\b(show\w*|visible|on my car|in iracing|in sim|in game|baked|stuck)\b/,
            /\bpreview\b[^.?!]{0,30}\b(different|doesn'?t match|not the same|not like|isn'?t like)\b[^.?!]{0,30}\b(sim|iracing|game|render|final)\b/,
            /\b(black|transparent|see.?through|invisible|missing|white)\b[^.?!]{0,20}\b(spots?|areas?|parts?|panels?|patches?|windows?|sections?)\b[^.?!]{0,30}\b(iracing|sim|game|car|paint)\b/,
            /\b(number|numbers)\b[^.?!]{0,24}\b(twice|double|two|missing|gone|wrong|duplicate\w*)\b/,
            /\b(only|just)\b[^.?!]{0,20}\bcolou?rs?\b[^.?!]{0,20}\bnot\b[^.?!]{0,12}\b(shine|metal|chrome|spec)\b|\bno (car_?)?spec\b/
        ] },
        { id: 'preview', re: [
            /\bpreview\b[^.?!]{0,40}\b(stuck|blank|black|white|empty|frozen|freez\w*|not updat\w*|won'?t update|wont update|doesn'?t update|doesnt update|error|broken|gone|missing|lag\w*|slow|loading forever|spinning|stale|grey|gray|still|old|same)\b/,
            /\b(stuck|blank|frozen|spinning|stale)\b[^.?!]{0,30}\bpreview\b/,
            /\b(f5|refresh)\b[^.?!]{0,30}\b(nothing|no change|still|doesn'?t|doesnt|didn'?t|didnt)\b/
        ] },
        { id: 'general', re: [
            /\b(something'?s? wrong|something is wrong|check (my|the) (setup|settings)|what('?s| is) wrong|diagnose|troubleshoot|not working|doesn'?t work|doesnt work|isn'?t working|help me fix|having (a )?(problem|issue|trouble)|problem with|issue with|why isn'?t|why won'?t|why doesn'?t|it'?s broken|is broken)\b/
        ] }
    ];

    var FAQS = [], ERRS = [];
    function classify(text) {
        var raw = String(text || ''), t = norm(raw);
        if (!t) return { kind: 'none' };
        if (SMALLTALK.test(raw)) return { kind: 'none', smalltalk: true };
        // 1. a pasted error / toast text
        var er = null; ERRS.forEach(function (e) { if (!er && e.re.test(raw)) er = e; });
        if (er) return { kind: 'error', err: er.id, topic: er.id };
        // 2. iRacing / PC trouble that has nothing to do with paint: say so kindly
        if ((SIM_ISSUE.test(t) || OFFTOPIC_HINT.test(t)) && !SHOKKER_WORDS.test(t)) return { kind: 'offtopic', sim: SIM_ISSUE.test(t) };
        var failure = FAIL.test(t), hits = [];
        // a request to DESIGN something ("make it look chrome in iRacing") is not a complaint: no failure word, no diagnosis
        var designish = !failure && (IMPERATIVE.test(t) || DESIGNV.test(t) || DESIGN_ANY.test(t));
        if (!designish) SYMPTOMS.forEach(function (s) { var n = 0; s.re.forEach(function (r) { if (r.test(t)) n++; }); if (n) hits.push({ id: s.id, n: n }); });
        var specific = hits.filter(function (h) { return h.id !== 'general'; }), best = null;
        if (specific.length >= 2) best = 'general'; else if (specific.length === 1) best = specific[0].id; else if (hits.length) best = 'general';
        var hit = null; if (failure || !(DESIGNV.test(t) || DESIGN_ANY.test(t))) FAQS.forEach(function (f) { if (!hit && f.re.test(t)) hit = f; });
        if (best && best !== 'general' && (!hit || failure)) return { kind: 'diagnose', symptom: best, topic: best };
        if (best === 'general' && specific.length >= 2) return { kind: 'diagnose', symptom: 'general', topic: 'general' };
        if (hit) return { kind: 'faq', faq: hit.id, topic: hit.id };
        if (best === 'general') return { kind: 'diagnose', symptom: 'general', topic: 'general' };
        if (OFFTOPIC_HINT.test(t) && !SHOKKER_WORDS.test(t)) return { kind: 'offtopic' };
        // anything else: the built-in manual gets a try; the caller decides what to say when it has nothing
        return { kind: 'search', inVocab: VOCAB.test(t) };
    }

    // ------------------------------------------------------------------ 2. the live settings
    function readEnv() {
        var env = { at: Date.now() };
        env.idRaw = val('iracingId'); env.idOk = /^\d{4,7}$/.test(env.idRaw);
        env.customNumber = chk('useCustomNumberCheckbox'); env.simStamped = chk('useSimStampedCheckbox');
        env.paintFile = val('paintFile'); env.outputDir = val('outputDir');
        var pps = $('paintPathStatus'); env.paintStatus = pps ? String(pps.textContent || '').trim().slice(0, 40) : '';
        env.autoDeploy = chk('liveLinkCheckbox'); env.exportZip = chk('exportZipCheckbox');
        try { env.psdLoaded = !!(typeof _psdLayersLoaded !== 'undefined' && _psdLayersLoaded && typeof _psdLayers !== 'undefined' && _psdLayers.length > 0); env.psdLayerCount = env.psdLoaded ? _psdLayers.length : 0; } catch (e) { env.psdLoaded = false; env.psdLayerCount = 0; }
        env.liveFlat = !!W._spbFlatPaintLiveSource;
        var pc = $('paintCanvas'); env.dims = pc && pc.width ? [pc.width, pc.height] : null;
        try {
            var Z = (typeof zones !== 'undefined' && zones) || [];
            env.zonesTotal = Z.length; env.zonesMuted = Z.filter(function (z) { return z && (z.muted || z.enabled === false); }).length;
            env.maskZones = Z.filter(function (z) { return z && z.regionMask; }).length;
            env.zonesValid = (typeof _zoneHasRenderableMaterial === 'function') ? Z.filter(function (z) { return z && !z.muted && _zoneHasRenderableMaterial(z) && (z.color !== null || z.colorMode === 'multi' || !!z.regionMask); }).length : null;      // the same test RENDER uses, without encoding any mask
        } catch (e2) { env.zonesTotal = null; env.zonesValid = null; env.maskZones = 0; env.zonesMuted = 0; }
        env.templateAll = []; env.template = [];
        try {
            var roles = (W.SpbProCar && W.SpbProCar.roles) ? W.SpbProCar.roles() : null;
            if (roles) { var tl = roles.filter(function (r) { return /^template/.test(String(r.role || '')); }); env.templateAll = tl.map(function (r) { return r.name; }); env.template = tl.filter(function (r) { return r.visible !== false; }).map(function (r) { return r.name; }); }
            else if (typeof _psdLayers !== 'undefined' && _psdLayers) {
                var tl2 = _psdLayers.filter(function (l) { return l && (/^\s*(wire|wireframe|mask|car[\s_]*mandatory)\s*$/i.test(String(l.name || '')) || /turn\s*off|before\s*export/i.test(String(l.groupName || ''))); });
                env.templateAll = tl2.map(function (l) { return l.name; }); env.template = tl2.filter(function (l) { return l.visible !== false; }).map(function (l) { return l.name; });
            }
            env.library = (W.SpbProCar && W.SpbProCar.library && W.SpbProCar.library()) ? W.SpbProCar.library().name : '';
        } catch (e3) {}
        var rb = $('btnRender'); env.renderBtn = rb ? String(rb.textContent || '').trim().slice(0, 30) : ''; env.renderDisabled = rb ? !!rb.disabled : null;
        env.specImported = W.importedSpecMapPath || ''; env.sculptLock = !!W._spbEasySculptSpecOverride;
        var ps = $('previewStatus'); env.previewState = ps ? (ps.dataset.state || '') : ''; env.previewText = ps ? String(ps.textContent || '').trim().slice(0, 80) : '';
        try { var bn = $('spbServerBanner'); env.banner = bn && bn.style.display === 'block' && !/reconnected/i.test(bn.textContent || '') ? String(bn.textContent || '').trim().slice(0, 120) : ''; } catch (e4) { env.banner = ''; }      // fixed-position banner: offsetParent is always null, so read its own display
        try { env.apiOnline = (typeof ShokkerAPI !== 'undefined' && ShokkerAPI) ? !!ShokkerAPI.online : null; } catch (e5) { env.apiOnline = null; }
        return env;
    }
    function jget(url, opt, ms) {
        return new Promise(function (resolve) {
            var done = false, t = setTimeout(function () { if (!done) { done = true; resolve(null); } }, ms || 6000);
            try {
                fetch((W.SPB_AI_BASE || '') + url, opt || {}).then(function (r) { return r.json().catch(function () { return { ok: r.ok }; }).then(function (j) { j = j || {}; j.__status = r.status; return j; }); }).then(function (j) { if (!done) { done = true; clearTimeout(t); resolve(j); } }, function () { if (!done) { done = true; clearTimeout(t); resolve(null); } });
            } catch (e) { if (!done) { done = true; clearTimeout(t); resolve(null); } }
        });
    }
    function gather(env) {
        var t0 = Date.now();
        var body = JSON.stringify({ folder: env.outputDir, iracing_id: env.idRaw, custom_number: env.customNumber !== false, paint_file: env.paintFile });
        return Promise.all([
            jget('/health', null, 5000), jget('/api/iracing-id-detect', null, 8000), jget('/api/iracing-paint-cars', null, 8000),
            jget('/api/support/folder-probe', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: body }, 8000)
        ]).then(function (r) {
            var health = r[0], det = r[1], cars = r[2], pr = r[3];
            return { healthOk: !!(health && (health.ok || health.__status === 200)), healthMs: Date.now() - t0, detect: det && det.__status === 200 ? det : null, cars: cars && cars.cars ? cars : null, probe: pr && pr.ok && pr.folder ? pr : null };
        });
    }

    // ------------------------------------------------------------------ 3. the checks (each returns an item or null)
    function item(id, status, title, detail, steps, fix) { return { id: id, status: status, title: title, detail: detail || '', steps: (steps || []).filter(Boolean), fix: fix || null }; }
    var HIDE_RULE = 'iRacing decides which of the two files to load with its own setting, **Settings \u2192 Graphics \u2192 Hide Car Numbers**: **ON** loads car_num_<ID>.tga (your paint carries the number), **OFF** loads car_<ID>.tga and iRacing stamps your number on. Restart iRacing after changing it.';
    var CHECKS = {
        server: function (env, s) {
            if (!s.healthOk) return item('server', 'bad', 'The paint engine is not answering', 'Rendering, the preview and the copilot all run on the local paint engine inside Shokker.', ['Wait about 10 seconds: it restarts itself.', 'If it stays down, close Shokker Paint Booth completely and open it again.', 'Still down? Antivirus or a firewall may be blocking python.exe: allow Shokker Paint Booth and try again.']);
            if (env.banner) return item('server', 'warn', 'The app is showing a server warning', Q + env.banner + QE, ['It usually clears by itself. If it stays, close and reopen Shokker Paint Booth.']);
            return item('server', 'ok', 'The paint engine is running', 'It answered in ' + s.healthMs + ' ms.');
        },
        source: function (env, s) {
            var full = /[\\/]/.test(env.paintFile) || /^[a-zA-Z]:/.test(env.paintFile);
            if (!env.paintFile && !env.liveFlat && !env.psdLoaded) return item('source', 'bad', 'No paint file is open', 'Source Paint is empty, so there is nothing to render.', ['Click **PSD/XCF/ORA** and pick your car' + AP + 's layered template (best: every layer stays separate), or **TGA/PNG/JPEG** for a flat paint.', 'Pick the template for the SAME car you will drive in iRacing.']);
            if (env.paintFile && !full && !env.liveFlat && !env.psdLoaded) return item('source', 'bad', 'Source Paint is only a file name', Q + env.paintFile + QE + ' has no folder in front of it, so Shokker cannot find the file again at render time.', ['Use the **PSD/XCF/ORA** or **TGA/PNG/JPEG** button next to Source Paint to pick the file, or paste the FULL path, for example C:\\Users\\You\\Documents\\iRacing\\paint\\carname\\car_num_12345.tga.']);
            if (/not found|directory/i.test(env.paintStatus || '') && !env.psdLoaded && !env.liveFlat) return item('source', 'bad', 'Shokker cannot find the Source Paint file', env.paintFile + ' (' + env.paintStatus + ')', ['The file was moved, renamed or deleted. Pick it again with the **PSD/XCF/ORA** or **TGA/PNG/JPEG** button.']);
            var pf = s.probe && s.probe.paint_file;
            if (pf && pf.given && full && pf.exists === false && !env.psdLoaded && !env.liveFlat) return item('source', 'bad', 'The Source Paint file is not at that path any more', pf.given, ['The file was moved, renamed or deleted. Pick it again with the **PSD/XCF/ORA** or **TGA/PNG/JPEG** button.']);
            if (env.dims && env.dims[0] !== env.dims[1]) return item('source', 'bad', 'The paint is not square (' + env.dims[0] + '\u00d7' + env.dims[1] + ')', 'iRacing car paints must be exactly 2048\u00d72048 (or 1024\u00d71024). Any other size is ignored and iRacing shows your paint-shop colours instead.', ['Open the car' + AP + 's template at its normal size (2048\u00d72048) and do not resize the canvas.']);
            if (env.dims && env.dims[0] !== 2048 && env.dims[0] !== 1024) return item('source', 'bad', 'The paint is ' + env.dims[0] + '\u00d7' + env.dims[1] + ', iRacing wants 2048 or 1024', 'iRacing ignores a car paint of any other size and falls back to your paint-shop colours without telling you.', ['Open the car' + AP + 's template at its normal size (2048\u00d72048) and do not resize the canvas.']);
            return item('source', 'ok', env.psdLoaded ? 'Your layered template is loaded' : 'A paint file is open', (env.psdLoaded ? env.psdLayerCount + ' layers' + (env.library ? ' \u00b7 recognised as ' + env.library : '') : (env.paintFile || 'open in the editor')) + (env.dims ? ' \u00b7 ' + env.dims[0] + '\u00d7' + env.dims[1] : ''));
        },
        id: function (env, s) {
            var det = s.detect && s.detect.best_id ? s.detect : null;
            var useFix = det ? { id: 'useid', label: 'Use ' + det.best_id + ' (found in your iRacing paint folders)' } : null;
            var where = 'Your **iRacing Customer ID** is under the helmet icon (top right in iRacing) \u2192 Profile, and on the members site under My Account.';
            if (!env.idRaw) return item('id', 'bad', 'The iRacing User ID is empty', 'Shokker names your files car_num_<ID>.tga / car_<ID>.tga / car_spec_<ID>.tga with your ID. iRacing ties a paint to a driver by that number, so without it the render is blocked (or the files are useless).', ['Type your ID (4 to 7 digits) into **iRacing User ID** at the top.', where, 'It is NOT your car number.'], useFix);
            if (!env.idOk) return item('id', 'bad', 'The iRacing User ID does not look right', Q + env.idRaw + QE + ' is not 4 to 7 digits.', ['Use your **iRacing Customer ID**: digits only, 4 to 7 of them.', where, 'It is not your car number and not your iRacing name.'], useFix);
            if (det && det.confident && String(det.best_id) !== env.idRaw) return item('id', 'warn', 'Your ID differs from the one in your iRacing paint folders', 'You typed ' + env.idRaw + '. Your paint folders already contain files named for ' + det.best_id + (det.best_folder_count ? ' (in ' + det.best_folder_count + ' car folder' + (det.best_folder_count > 1 ? 's' : '') + ')' : '') + '. iRacing loads a file only for the Customer ID it belongs to; a paint with another ID goes onto THAT driver' + AP + 's car, not yours.', ['If ' + env.idRaw + ' is a car number or an old ID, switch to ' + det.best_id + '.', 'If you really do have two accounts, ignore this.'], { id: 'useid', label: 'Use ' + det.best_id });
            return item('id', 'ok', 'iRacing User ID: ' + env.idRaw, det && String(det.best_id) === env.idRaw ? 'It matches the files iRacing already has in your paint folders.' : 'Looks valid. Double-check it against your iRacing profile: a wrong ID gives files iRacing never matches to you.');
        },
        numbermode: function (env, s) {
            var custom = env.customNumber !== false, det = s.detect, pr = s.probe, rid = env.idRaw, f = pr && pr.found;
            var writes = rid ? (custom ? 'car_num_' + rid + '.tga' : 'car_' + rid + '.tga') : (custom ? 'car_num_<ID>.tga' : 'car_<ID>.tga');
            var need = custom ? 'Shokker writes **' + writes + '**, which iRacing loads only when **Hide Car Numbers is ON**.' : 'Shokker writes **' + writes + '**, which iRacing loads when **Hide Car Numbers is OFF** (the default); iRacing then stamps your number on top.';
            if (det && det.best_id && det.confident && String(det.best_id) === rid && typeof det.runs_custom_numbers === 'boolean' && det.runs_custom_numbers !== custom && det.best_folder_count >= 2) return item('numbermode', 'warn', 'The number setting may not match how you drive', 'Your paint folders mostly use ' + (det.runs_custom_numbers ? 'car_num_' + rid + '.tga (custom numbers)' : 'car_' + rid + '.tga (sim-stamped numbers)') + ', but Shokker is set to ' + (custom ? 'Custom Number' : 'Sim-Stamped Number') + '. ' + need, [HIDE_RULE], { id: det.runs_custom_numbers ? 'customnumber' : 'simstamped', label: 'Switch to ' + (det.runs_custom_numbers ? 'Custom Number' : 'Sim-Stamped Number') });
            if (f && !f.paint && f.other_scheme) return item('numbermode', 'warn', 'The folder has the OTHER file name: ' + (custom ? 'car_' : 'car_num_') + rid + '.tga', 'You are on ' + (custom ? 'Custom Number' : 'Sim-Stamped Number') + ', so the next render writes **' + writes + '**, but your car folder only holds ' + (custom ? 'car_' : 'car_num_') + rid + '.tga from an earlier render in the other mode. iRacing loads exactly one of the two, depending on **Hide Car Numbers**; until the file it wants exists, it shows your paint-shop colours or the older paint.', [HIDE_RULE, 'Render again (it writes ' + writes + '), or switch the mode to match the file you already have.'], { id: custom ? 'simstamped' : 'customnumber', label: 'Switch to ' + (custom ? 'Sim-Stamped Number' : 'Custom Number') });
            if (f && f.paint && !f.other_scheme) return item('numbermode', 'unk', (custom ? 'Custom Number' : 'Sim-Stamped Number') + ': only ' + writes + ' is in the folder', need + ' If your iRacing setting is the other way round, iRacing looks for ' + (custom ? 'car_' : 'car_num_') + rid + '.tga, finds nothing and quietly shows your paint-shop colours.', [HIDE_RULE, 'Not sure which one you use? Render once in each mode (the switch is in the header, next to your ID): both files stay in the folder and the sim picks the right one.'], { id: custom ? 'simstamped' : 'customnumber', label: 'Switch to ' + (custom ? 'Sim-Stamped Number' : 'Custom Number') + ' for the next render' });
            return item('numbermode', 'ok', (custom ? 'Custom Number' : 'Sim-Stamped Number') + ': Shokker writes ' + writes, need + ' ' + (custom ? 'Use this when your paint carries its own number.' : 'Use this when your paint has no number on it.'), [HIDE_RULE]);
        },
        folder: function (env, s) {
            var fp = s.probe && s.probe.folder, carFix0 = { id: 'carmenu', label: 'Open the car menu' };
            if (!env.outputDir) return item('folder', 'bad', 'No iRacing car folder is set', 'Without it Shokker cannot put the files where iRacing reads them.', ['Click the \u25be car menu next to **iRacing Car Folder** (it lists the folders iRacing created on this PC) or the \ud83d\udcc2 button, and pick the folder of the car you drive, for example \u2026\\Documents\\iRacing\\paint\\stockcars chevyss\\.', 'iRacing creates a car\u2019s folder the first time you run that car in a race or test session. In the iRacing paint shop, hover the tool-tip to see the exact folder for your car.'], { id: 'carmenu', label: 'Open the car menu' });
            if (fp && fp.unc) return item('folder', 'warn', 'That is a network path', fp.given, ['I do not look inside network paths from here. iRacing reads paints from Documents\\iRacing\\paint\\<car folder> on THIS PC: pick that folder instead.'], carFix0);
            if (fp && fp.remote_drive) return item('folder', 'warn', 'That folder is on a network drive', fp.given, ['I do not look inside network drives from here. iRacing reads paints from Documents\\iRacing\\paint\\<car folder> on THIS PC: pick that folder instead.'], carFix0);
            if (!fp) return item('folder', 'unk', 'Could not inspect the car folder', s.healthOk ? 'The folder check needs the newest Shokker engine (restart Shokker once), or the folder did not answer in time.' : 'The paint engine is not answering, so I could not look at the folder.', ['Check by hand: open ' + env.outputDir + ' in Windows Explorer and see whether car_num_ / car_ and car_spec_ files with your ID are in it.']);
            var carList = (s.cars && s.cars.cars && s.cars.cars.length) ? 'Folders iRacing created on this PC (most recent first): ' + s.cars.cars.slice(0, 6).map(function (c) { return c.name; }).join(', ') + '.' : '';
            var carFix = { id: 'carmenu', label: 'Open the car menu' };
            if (fp.ends_with_tga || fp.is_file) return item('folder', 'warn', 'The car folder field points at a file', fp.given, ['It should point at the car' + AP + 's FOLDER, not a .tga file. Shokker tries to use the folder around it, but pick the folder yourself to be safe.'], carFix);
            if (!fp.drive_exists) return item('folder', 'bad', 'That drive is not connected', fp.given, ['Plug the drive in, or pick a folder on a drive that is there.']);
            if (fp.is_paint_root) return item('folder', 'bad', 'You picked iRacing' + AP + 's main paint folder, not a car' + AP + 's folder', fp.given, ['iRacing reads each car' + AP + 's paint from its OWN folder inside ' + Q + 'paint' + QE + ', for example \u2026\\paint\\stockcars chevyss\\. Files dropped straight into ' + Q + 'paint' + QE + ' are never loaded for a car.', 'Pick the folder of the car you drive.', carList], carFix);
            if (fp.is_gear_folder) return item('folder', 'warn', 'That folder is for ' + fp.name + ', not a car', fp.given, ['Shokker paints cars. Pick the folder of the car you drive.', carList], carFix);
            if (!fp.exists || !fp.is_dir) {
                if (fp.parent_is_dir) return item('folder', 'bad', 'That car folder does not exist (typo?)', fp.given + '. Shokker then saves into the folder around it' + (fp.parent_name ? ' (' + Q + fp.parent_name + QE + ')' : '') + ' and says it worked, but iRacing never reads a paint from there.', ['Fix the last part of the folder name, or pick the folder again. Car folder names use a space where the car path has a slash, for example ' + Q + 'stockcars chevyss' + QE + '.', 'If you have never driven this car in iRacing, run it once first (a test session is enough): iRacing creates its paint folder then.', carList], carFix);
                return item('folder', 'bad', 'That car folder does not exist', fp.given, ['Pick the folder again with the car menu or the \ud83d\udcc2 button.', 'If you have never driven this car in iRacing, run it once first (a test session is enough): iRacing creates the paint folder then.', carList], carFix);
            }
            if (fp.writable === false) return item('folder', 'bad', 'Shokker cannot write into that folder', fp.given, ['Check the folder is not read-only, and that Windows ' + Q + 'Controlled folder access' + QE + ' (Windows Security) is not blocking Shokker.', 'Or pick another folder.']);
            if (!fp.in_iracing_paint) return item('folder', 'warn', 'That does not look like an iRacing paint folder', fp.given, ['iRacing only reads paints from \u2026\\Documents\\iRacing\\paint\\<car folder>\\. If this is a staging folder, copy the files over yourself, or point Shokker at the real one.', fp.parent_name ? 'Its parent folder is called ' + Q + fp.parent_name + QE + ' (iRacing' + AP + 's is ' + Q + 'paint' + QE + ').' : ''], carFix);
            return item('folder', 'ok', 'Car folder: ' + (fp.name || env.outputDir), 'It exists and it is under iRacing' + AP + 's paint folder. It must be the folder of the SAME car you drive.' + (fp.under_onedrive ? ' It is inside OneDrive: make sure OneDrive is not paused or syncing it away.' : ''));
        },
        files: function (env, s) {
            var pr = s.probe, f = pr && pr.found, e = pr && pr.expected, fp = pr && pr.folder;
            if (!pr || !fp || (!fp.is_dir && !pr.scanned_parent) || !env.idOk) return null;
            var now = pr.checked_at || Date.now() / 1000, bad = [], warn = [], okd = [], steps = [];
            if (!f.paint) bad.push('**' + e.paint + '** is not in the folder yet');
            else if (f.paint_mtime) { var a = now - f.paint_mtime; if (a > 172800) warn.push(e.paint + ' was last written ' + ago(a) + ' ago (if you rendered since, that render did not reach this folder)'); else okd.push(e.paint + ' written ' + ago(a) + ' ago'); }
            if (!f.spec) warn.push('**' + e.spec + '** is not in the folder: chrome, metal and shine will not show in the sim without it');
            else if (!f.spec_mtime) warn.push('only iRacing' + AP + 's compiled spec (.mip) is there, not ' + e.spec + ' from Shokker');
            else { var a2 = now - f.spec_mtime; if (a2 > 172800) warn.push(e.spec + ' is ' + ago(a2) + ' old'); else okd.push(e.spec + ' written ' + ago(a2) + ' ago'); }
            var mp = pr.mips && pr.mips.spec;
            if (mp && f.spec_mtime && mp.mtime < f.spec_mtime - 5) { warn.push('iRacing' + AP + 's compiled ' + mp.name + ' is older than your newest spec'); steps.push('Press **Ctrl+R** in iRacing: it rebuilds the compiled spec from the newer .tga. If the shine still looks old, move ' + mp.name + ' out of the folder and reload.'); }
            if (pr.scanned_parent && f.paint) return item('files', 'bad', 'Your last render landed in the WRONG folder', e.paint + ' is in ' + Q + (fp.parent_name || 'the folder around it') + QE + ', not in the car folder you typed (that folder does not exist). iRacing never reads a car paint from there.', ['Fix the car folder name (see the red item above), render again, and delete the stray files from ' + Q + (fp.parent_name || 'that folder') + QE + '.']);
            if (pr.scanned_parent) bad.push('the folder you typed does not exist, and the folder around it has no ' + e.paint + ' either');
            if (!f.paint && (pr.ids_in_folder_count || 0) > 0 && !pr.scanned_parent) warn.push('the folder holds paints for ' + pr.ids_in_folder_count + ' driver ID' + (pr.ids_in_folder_count > 1 ? 's' : '') + ' but none for yours' + (pr.ids_in_folder_count > 3 ? ' (normal if you use Trading Paints)' : ''));
            if (bad.length) return item('files', 'bad', 'The files iRacing needs are not in the car folder', bad.concat(warn).join('; ') + '.', ['Press **RENDER** (top bar) and wait for it to finish: with a car folder set, the render copies the files in for you.', 'Check the folder and ID above: the files are named with your ID.'].concat(steps));
            if (warn.length) return item('files', 'warn', 'Files found, with something to check', warn.join('; ') + '.', ['Press **RENDER** again, then in iRacing press **Ctrl+R**.'].concat(steps));
            return item('files', 'ok', 'Your paint files are in the car folder', okd.join('; ') + '.');
        },
        // 2026-10-04: a one-click "open the folder with the file highlighted" (server_routes/support_routes.py /api/support/show-files).
        // Browsing there by hand fails for real buyers (OneDrive gives Windows two Documents folders; car folders have internal names).
        showfiles: function (env, s) {
            var last = null; try { last = W.spbLastRenderFiles ? W.spbLastRenderFiles() : null; } catch (e) { last = null; }
            var rid = env.idOk ? env.idRaw : '<ID>', paint = (env.customNumber !== false ? 'car_num_' : 'car_') + rid + '.tga';
            var tp = 'For **Trading Paints** upload **' + paint + '** as the paint (.tga or .png). Never the .spb / .shokk file: that is your Shokker project, only Shokker opens it. Trading Paints takes the spec only as **car_spec_' + rid + '.mip**, which iRacing makes next to your car_spec_' + rid + '.tga the first time you drive the car with it in the folder.';
            var od = 'Browsing there by hand and seeing nothing? Windows can have TWO Documents folders (one inside OneDrive), and iRacing names car folders its own way (for example ' + Q + 'stockcars chevyss' + QE + '). The button always opens the right one.';
            if (last && last.folder) return item('showfiles', 'unk', 'See the files yourself', 'Your last render went to ' + last.folder + '. The button opens File Explorer there with your paint file highlighted.', [tp, od], { id: 'showfiles', label: '📂 Show my files' });
            if (last && last.job_id) return item('showfiles', 'warn', 'Your last render is only inside Shokker', 'No iRacing car folder was set, so that render stayed in Shokker' + AP + 's own render folder, where iRacing never looks (only the two newest renders are kept there).', ['Pick your car in **iRacing Car Folder**, then press **RENDER** again.', tp], { id: 'showfiles', label: '📂 Show where it was saved' });
            if (env.outputDir) return item('showfiles', 'unk', 'See the files yourself', 'The button opens your iRacing car folder in File Explorer. No render yet this session? Press **RENDER** first: that is what writes the files.', [tp, od], { id: 'showfiles', label: '📂 Open my car folder' });
            return null;
        },
        deploy: function (env, s) {
            if (env.outputDir) return null;      // the car folder alone already deploys; Auto-deploy only matters when it is blank
            if (env.autoDeploy === true) return item('deploy', 'warn', 'No car folder is set; Auto-deploy will use your last saved car', 'Auto-deploy is ON, but with no iRacing Car Folder it copies into the car Shokker remembered last, which may not be the one you are driving.', ['Pick the car folder in the header so there is no guessing.'], { id: 'carmenu', label: 'Open the car menu' });
            if (env.autoDeploy === false) return item('deploy', 'bad', 'Nothing is copied into iRacing', 'There is no iRacing Car Folder and Auto-deploy is off, so renders stay in Shokker' + AP + 's own render folder.', ['Pick your car in the **iRacing Car Folder** menu: from then on every render is copied into iRacing.'], { id: 'carmenu', label: 'Open the car menu' });
            return null;
        },
        template: function (env, s) {
            if (env.template && env.template.length) return item('template', 'bad', 'Template layers are switched ON', 'These layers are guides for painting, not paint: **' + env.template.join(', ') + '**. If they stay on, the wire outlines and masks are baked into your paint and show up on the car (iRacing also stamps numbers and sponsors itself, so leaving the number stamp layers on gives two numbers).', ['Switch them OFF before rendering (the layer group ' + Q + 'Turn Off Before Exporting TGA' + QE + ').', 'One click below does it, and Undo puts them back.'], { id: 'templateoff', label: 'Switch template layers off' });
            if (env.templateAll && env.templateAll.length) return item('template', 'ok', 'Template layers are off', env.templateAll.join(', '));
            return null;
        },
        zones: function (env, s) {
            if (env.zonesTotal == null) return null;
            if (env.zonesTotal === 0 && !env.psdLoaded && !env.paintFile) return null;
            if (env.zonesTotal === 0) return item('zones', 'warn', 'There are no zones yet', 'A render with no zones only saves your plain source paint.', ['Ask me for a design (for example ' + Q + 'Gulf style' + QE + '), or pick a colour on the paint (Pick + Add) and give the zone a finish.']);
            if (env.zonesTotal && env.zonesMuted === env.zonesTotal && !env.specImported) return item('zones', 'warn', 'Every zone is muted', 'Muted zones are skipped, so the render looks like the plain source paint.', ['Un-mute at least one zone.']);
            if (env.zonesValid === 0 && !env.specImported) return item('zones', 'bad', 'No zone is ready to render', 'You have ' + env.zonesTotal + ' zone(s), but none has both a colour and a finish, so RENDER refuses.', ['Give each zone a **colour** and a **finish** from the library (both are required).', 'A muted zone is skipped too.']);
            if (env.zonesTotal && env.zonesMuted === env.zonesTotal) return item('zones', 'warn', 'Every zone is muted', 'Muted zones are skipped, so the render looks like the plain source paint.', ['Un-mute at least one zone.']);
            if (env.maskZones > 19) return item('zones', 'warn', 'Many zones with their own painted area (' + env.maskZones + ')', 'The render server combines only about 20 such zones at a time; more can make the preview or the render fail.', ['Undo or merge some zones, or say ' + Q + 'start over' + QE + ' and describe the design again.']);
            return item('zones', 'ok', env.zonesTotal + ' zone' + (env.zonesTotal > 1 ? 's' : '') + (env.zonesValid != null ? ', ' + env.zonesValid + ' ready to render' : ''));
        },
        specmap: function (env, s) {
            if (env.sculptLock) return item('specmap', 'warn', 'Spec Sculpt is holding the shine', 'After a Spec Sculpt save, the main RENDER keeps that exact spec and ignores your zones for shine and metal.', ['If you want the zones to control shine again, clear the imported spec map (Settings gear \u2192 Import Spec Map \u2192 Clear).']);
            if (env.specImported) return item('specmap', 'warn', 'A spec map is imported', 'Zones paint on top of the imported map, and a zone set to Everything or Remaining covers all of it. If the file moved, Shokker silently drops it.', ['Check Settings gear \u2192 Import Spec Map. Press Clear if you do not want it.']);
            return null;
        },
        button: function (env, s) {
            if (/OPEN PAINT FIRST|LOADING PAINT/i.test(env.renderBtn || '')) return item('button', 'bad', 'The RENDER button says ' + Q + env.renderBtn + QE, /LOADING/i.test(env.renderBtn) ? 'Shokker is still loading the paint, and RENDER switches itself on when that is done.' : 'RENDER switches on once a paint file has finished opening.', [/LOADING/i.test(env.renderBtn) ? 'Wait for the paint to finish loading (a big PSD can take a minute).' : 'Open your car' + AP + 's template with the **PSD/XCF/ORA** button next to Source Paint.']);
            if (/Offline/i.test(env.renderBtn || '')) return item('button', 'bad', 'RENDER says Offline', 'The paint engine is not answering.', ['Wait about 10 seconds, it restarts itself. If it stays offline, close and reopen Shokker Paint Booth.']);
            return null;
        },
        preview: function (env, s) {
            if (env.previewState === 'error') return item('preview', 'bad', 'The live preview failed', 'The last preview render came back with an error' + (env.previewText ? ' (' + Q + env.previewText + QE + ')' : '') + '.', ['Press **F5** to rebuild the preview.', 'If it fails again, undo the last change, or check the zone count (about 20 zones with their own painted area is the limit).', 'If the engine is offline, see the first item.']);
            if (env.previewState === 'stale' || env.previewState === 'retrying') return item('preview', 'warn', 'The preview is waiting for a render', env.previewText || '', ['Give it a few seconds, then press **F5**.']);
            return item('preview', 'ok', 'The live preview is working');
        },
        ingame: function (env, s) {
            return item('ingame', 'unk', 'On the iRacing side', 'Everything above is the Shokker side. These are the parts only iRacing knows about:', [
                'Run the SAME car you rendered for. Its folder is created the first time you run it in a race or test session.',
                'Check **Hide Car Numbers** (Settings \u2192 Graphics): ON loads car_num_<ID>.tga, OFF loads car_<ID>.tga. Restart iRacing after changing it, and note that iRacing updates can switch it back.',
                'After a render, **Alt+Tab** to iRacing and press **Ctrl+R** (Reload Car Textures). The car flashes white, then shows the new paint. In a replay, move to a moment when your car is not in the pit lane. The 3D Car Viewer in My Content reloads on its own.',
                'iRacing needs the paint to be a real TGA of exactly 2048\u00d72048 (or 1024\u00d71024). If it does not find a usable file it silently shows your paint-shop colours.',
                'Other drivers see your paint only if they have your file (for example through Trading Paints). Using the Trading Paints Downloader? It writes into the same folder with the same names: close it while you test a local paint, or turn off ' + Q + 'Update My Own Paints' + QE + '.',
                'If paint is black or part is missing: save the TGA as 24-bit (not 32-bit) unless the car has paintable glass, and check the ' + Q + '2048 paint textures' + QE + ' graphics option is on (restart iRacing).'
            ]);
        },
        specnote: function (env, s) {
            return item('specnote', 'unk', 'Shine, metal and chrome come from the spec file', 'iRacing builds shine from **car_spec_' + (env.idOk ? env.idRaw : '<ID>') + '.tga**: red = metal, green = roughness, blue = clearcoat. A colour alone never looks metallic.', [
                'Make sure the spec file is in the car folder and newer than your last change.',
                'Chrome needs a nearly WHITE paint underneath: iRacing multiplies the paint by the metal, so a normal colour turned metallic goes dark.',
                'Blue (clearcoat) 255 is dull; 16 is very shiny; 0 is off.',
                'In the preview, switch to the spec view (Shine in Chat Studio) to see what iRacing will read.'
            ]);
        }
    };
    var ORDER = {
        render: ['server', 'button', 'source', 'id', 'zones', 'specmap', 'template', 'preview', 'folder', 'files', 'deploy'],
        ingame: ['id', 'numbermode', 'folder', 'files', 'showfiles', 'deploy', 'server', 'source', 'template', 'ingame'],
        files: ['id', 'folder', 'files', 'showfiles', 'deploy', 'numbermode', 'server'],
        look: ['template', 'numbermode', 'files', 'specnote', 'specmap', 'zones', 'ingame'],
        preview: ['server', 'preview', 'button', 'zones', 'source'],
        general: ['server', 'button', 'source', 'id', 'numbermode', 'folder', 'files', 'showfiles', 'deploy', 'template', 'zones', 'specmap', 'preview', 'ingame']
    };
    var INTRO = {
        files: 'Let me look at where your renders go and what is in your car folder right now. The files only exist after you press **RENDER** (saving a project does not make them):',
        render: 'I looked at your live settings and the files in your car folder. Here is what I found:',
        ingame: 'Most ' + Q + 'it is not in iRacing' + QE + ' cases come from the Customer ID, the number setting, the car folder, or a missing reload. I checked all of them on your PC:',
        look: 'A paint can look right in Shokker and different in the sim for a few known reasons. I checked what I can see from here:',
        preview: 'Here is what I can see about the preview and what feeds it:',
        general: 'Here is a full check of your setup:'
    };
    var TITLE = { files: 'Where your files are', render: 'Why it will not render', ingame: 'Why it is not showing in iRacing', look: 'Why it looks different in iRacing', preview: 'Why the preview is stuck', general: 'Setup check' };

    function runChecks(symptom, env, srv) {
        var items = [];
        ORDER[symptom].forEach(function (id) { var fn = CHECKS[id]; if (!fn) return; var it = null; try { it = fn(env, srv); } catch (e) { it = null; } if (it) items.push(it); });
        var rank = { bad: 0, warn: 1, unk: 2, ok: 3 };
        var st = items.map(function (x, i) { return { x: x, i: i }; }); st.sort(function (a, b) { return (rank[a.x.status] - rank[b.x.status]) || (a.i - b.i); });
        return st.map(function (z) { return z.x; });
    }
    function diagnose(symptom) {
        symptom = ORDER[symptom] ? symptom : 'general';
        var env = readEnv();
        return gather(env).then(function (srv) {
            var items = runChecks(symptom, env, srv);
            var bad = items.filter(function (x) { return x.status === 'bad'; }).length, warn = items.filter(function (x) { return x.status === 'warn'; }).length;
            var reload = (symptom === 'ingame' || symptom === 'general' || symptom === 'look') ? ' and **Ctrl+R** in iRacing' : '';
            var outro = bad ? 'Fix the red items first (top of the list), then press **RENDER** again' + reload + '. Tell me what changed and I will check again.'
                : warn ? 'Nothing is hard-broken, but check the orange items. Then render again' + reload + '.'
                : 'Everything I can check on the Shokker side is fine. The remaining suspects are on the iRacing side (last item).';
            return { symptom: symptom, env: env, srv: srv, items: items, bad: bad, warn: warn, card: { role: 'diag', symptom: symptom, title: TITLE[symptom], intro: INTRO[symptom], items: items, outro: outro, next: ['Check again', 'How do I reload the paint in iRacing?', 'What do Custom Number and Sim-Stamped mean?'] } };
        });
    }
    // what the AI gets: the same facts with every Customer ID and the Windows user name blanked out. Walks EVERY string (file names, findings, detected id, ids in the folder); fails CLOSED.
    function redact(o, env, srv) {
        try {
            var map = {}, n = 0;
            function reg(id, label) { id = String(id == null ? '' : id).trim(); if (id && !map[id]) map[id] = label || '<OTHER_ID_' + (++n) + '>'; }
            if (env && env.idRaw) reg(env.idRaw, '<ID>');
            if (srv && srv.detect && srv.detect.best_id) reg(srv.detect.best_id, '<DETECTED_ID>');
            if (srv && srv.probe) (srv.probe.ids_in_folder || []).forEach(function (x) { reg(x); });
            var typed = env && env.idRaw && !/^\d{4,9}$/.test(env.idRaw) ? env.idRaw : null;
            function clean(v) {
                if (typeof v === 'number') return v;
                if (typeof v !== 'string') return v;
                if (typed) v = v.split(typed).join('<ID>');
                v = v.replace(/\d{4,9}/g, function (tok) { return map[tok] || tok; });
                return v.replace(/([A-Za-z]:\\+Users\\+)[^\\\/"']+/g, '$1<user>').replace(/([A-Za-z]:\/Users\/)[^\/"']+/g, '$1<user>');
            }
            function walk(x) {
                if (Array.isArray(x)) return x.map(walk);
                if (x && typeof x === 'object') { var out = {}; Object.keys(x).forEach(function (k) { out[k] = walk(x[k]); }); return out; }
                return clean(x);
            }
            return walk(o);
        } catch (e) { return { error: 'redaction failed, nothing was shared' }; }
    }
    function snapshot() {
        return diagnose('general').then(function (d) { return redact({ iracing_user_id: d.env.idRaw ? '<ID>' : '', id_valid: d.env.idOk, number_mode: d.env.customNumber !== false ? 'custom (car_num_)' : 'sim-stamped (car_)', car_folder: d.env.outputDir, source_paint: d.env.paintFile, paint_size: d.env.dims, auto_deploy: d.env.autoDeploy, template_layers_visible: d.env.template, zones: { total: d.env.zonesTotal, ready: d.env.zonesValid, muted: d.env.zonesMuted, with_masks: d.env.maskZones }, render_button: d.env.renderBtn, preview: d.env.previewState, engine_ok: d.srv.healthOk, files: d.srv.probe ? { expected: d.srv.probe.expected, found: d.srv.probe.found, ids_in_folder: d.srv.probe.ids_in_folder } : null, detected_id: d.srv.detect ? { id: d.srv.detect.best_id, confident: d.srv.detect.confident, runs_custom_numbers: d.srv.detect.runs_custom_numbers } : null, findings: d.items.map(function (x) { return { check: x.id, status: x.status, title: x.title, detail: x.detail }; }) }, d.env, d.srv); });
    }

    // ------------------------------------------------------------------ 4. one-click fixes (ordinary settings the buyer could change by hand)
    function fire(el, name) { try { el.dispatchEvent(new Event(name, { bubbles: true })); } catch (e) {} }
    function fix(id, cb) {
        cb = cb || function () {};
        if (id === 'useid') {
            jget('/api/iracing-id-detect', null, 8000).then(function (d) {
                if (!d || !d.best_id) return cb('I could not find your ID in the paint folders. Type it in by hand.');
                var el = $('iracingId'); if (!el) return cb('The iRacing User ID field is not on screen.');
                el.value = String(d.best_id); fire(el, 'input'); fire(el, 'change'); try { if (typeof updateOutputPath === 'function') updateOutputPath(); } catch (e) {}
                cb('iRacing User ID is now ' + d.best_id + ' (the ID your iRacing paint folders already use). Render again, then Ctrl+R in iRacing.');
            }); return;
        }
        if (id === 'customnumber' || id === 'simstamped') {
            var c = $('useCustomNumberCheckbox'), sidx = $('useSimStampedCheckbox'), on = id === 'customnumber';
            if (c) c.checked = on; if (sidx) sidx.checked = !on;
            try { if (typeof toggleCustomNumber === 'function') toggleCustomNumber(on); } catch (e) {}
            return cb(on ? 'Custom Number is on: Shokker now writes car_num_<ID>.tga (iRacing loads it with Hide Car Numbers ON). Render again, then Ctrl+R in iRacing.' : 'Sim-Stamped Number is on: Shokker now writes car_<ID>.tga (iRacing loads it with Hide Car Numbers OFF). Render again, then Ctrl+R in iRacing.');
        }
        if (id === 'deployon') {
            var cb2 = $('liveLinkCheckbox'); if (cb2) cb2.checked = true;
            try { if (typeof toggleLiveLink === 'function') toggleLiveLink(true); } catch (e2) {}
            return cb('Auto-deploy is on: every render is copied into your iRacing car folder.');
        }
        if (id === 'carmenu') {
            var b = $('carPickBtn'); if (b) { try { b.scrollIntoView({ block: 'nearest' }); } catch (e4) {} b.click(); return cb('I opened the car menu at the top. Pick the car you drive.'); }
            return cb('Use the \ud83d\udcc2 button next to iRacing Car Folder and pick your car\u2019s folder.');
        }
        if (id === 'showfiles') {
            var last = null; try { last = W.spbLastRenderFiles ? W.spbLastRenderFiles() : null; } catch (e5) { last = null; }
            var env5 = readEnv(), rid5 = env5.idOk ? env5.idRaw : '';
            var target = last || (env5.outputDir ? { folder: env5.outputDir, select: rid5 ? (env5.customNumber !== false ? 'car_num_' : 'car_') + rid5 + '.tga' : '' } : null);
            if (!target) return cb('There is no render and no iRacing car folder yet. Pick your car in iRacing Car Folder, press RENDER, then ask me again.');
            jget('/api/support/show-files', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(target) }, 8000).then(function (r) {
                if (!r) return cb('The paint engine did not answer. Try again in a few seconds.');
                if (!r.ok) return cb(r.error === 'folder not found' ? 'That folder does not exist on this PC: ' + (target.folder || 'the render folder') + '. Pick your car again in iRacing Car Folder and render.' : 'I could not open it (' + (r.error || 'unknown') + ').');
                cb('File Explorer is open at ' + r.path + '' + (r.selected ? ' with ' + r.selected + ' highlighted.' : '.') + (target.job_id ? ' This is Shokker' + AP + 's own render folder: iRacing never looks here. Pick your car in iRacing Car Folder and render again.' : ''));
            }); return;
        }
        if (id === 'templateoff') {
            try { if (W.spbProAI && W.spbProAI.hideTemplates) { W.spbProAI.hideTemplates(); return cb('Switching the template layers off (Undo brings them back).'); } } catch (e3) {}
            return cb('Switch the layers called Mask, Wire and Car_Mandatory off in the Layers panel.');
        }
        cb('That fix is not available.');
    }

    W.SpbSupport = {
        classify: classify, diagnose: diagnose, snapshot: snapshot, fix: fix, readEnv: readEnv, runChecks: runChecks,
        CHECKS: CHECKS, ORDER: ORDER, SYMPTOMS: SYMPTOMS, FAQS: FAQS, ERRS: ERRS, norm: norm, esc: esc, HIDE_RULE: HIDE_RULE,
        addFaq: function (id, re, answer, next, extra) { FAQS.push({ id: id, re: re, answer: answer, next: next || [], extra: extra || null }); },
        addErr: function (id, re, title, answer, next) { ERRS.push({ id: id, re: re, title: title, answer: answer, next: next || [] }); }
    };
})();
