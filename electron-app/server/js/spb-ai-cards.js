/* ============================================================================
   SPB AI CARDS — semantic search over the LLM-written finish cards   (owner 2026-10-03)
   Data: js/spb-ai-cards-data.js (window.SPB_CARDS_DATA), made ONCE by scripts/ai_atlas/annotate_cards.py + build_cards_js.py: for every catalogue item a plain-words look,
   real-world analogs, 10-16 search synonyms a painter might type, mood / era / fit / best placement, loudness 1-5, busyness 1-5, what it pairs with and what to avoid.
   The knowledge lives in the DATA, so every brain (built-in, DeepSeek, OpenAI, Claude over MCP) gets the same understanding at zero runtime cost.

     SpbAICards.load() -> Promise         lazy: loads the atlas AND the cards, builds the index
     SpbAICards.ready() -> bool
     SpbAICards.card(key) -> {look, analog[], syn[], mood[], era[], fit[], use[], loud, busy, pair[], avoid[], scale, vis}
     SpbAICards.search(query, o) -> [{key, s, hits[]}]   BM25F over name / synonyms / analogs / look / tags / shelf / description + painter lexicon + phrase bonus + negation
        o: types ['base','monolithic','pattern','spec'], own 'own'|'takes', limit, exclude[], offset, minQ
   ES5 only.
   ========================================================================== */
(function () {
    'use strict';
    var DATA = null, LOADING = null, IDX = null, MOODS = [], ERAS = [], USES = [], FITS = [];
    var SCALES = ['', 'fine', 'medium', 'broad'];
    function BASE() { return window.SPB_ATLAS_BASE || ''; }
    function norm(s) { return String(s || '').toLowerCase().replace(/[^a-z0-9 ]+/g, ' ').replace(/\s+/g, ' ').trim(); }
    var STOP = { a: 1, an: 1, the: 1, and: 1, or: 1, of: 1, to: 1, in: 1, on: 1, is: 1, it: 1, for: 1, with: 1, i: 1, my: 1, me: 1, that: 1, this: 1, be: 1, are: 1, like: 1, some: 1, very: 1, look: 1, looks: 1, finish: 1, finishes: 1, paint: 1, car: 1, want: 1, something: 1, would: 1, can: 1, you: 1, show: 1, give: 1, make: 1, get: 1, put: 1, as: 1, at: 1, by: 1, so: 1, but: 1, if: 1, do: 1, does: 1, what: 1, which: 1, how: 1, any: 1, one: 1, from: 1, into: 1, over: 1, just: 1, kind: 1, type: 1, sort: 1 };
    function stem(w) { if (w.length <= 3 || /(?:ss|us|is)$/.test(w)) return w; if (w.length > 4) { var x = w.replace(/(?:ing|ed)$/, ''); if (x !== w && x.length >= 3) return x; } if (/(?:[sxz]|ch|sh)es$/.test(w)) return w.slice(0, -2); return w.replace(/s$/, ''); }
    function toks(s) { var o = [], w = norm(s).split(' '); for (var i = 0; i < w.length; i++) { if (w[i].length > 1 && !STOP[w[i]]) o.push(stem(w[i])); } return o; }

    // ------------------------------------------------------------------ the painter's lexicon: words people use -> the words the cards use (extra terms are added with a lower weight)
    var LEX = {
        dusty: 'dust dirt weathered worn matte', dirty: 'dirt grime weathered worn grunge', grimy: 'grime dirt weathered', muddy: 'mud dirt brown weathered', mud: 'dirt brown earth',
        tarmac: 'asphalt road grey', asphalt: 'tarmac road grey black gritty', pavement: 'asphalt road concrete grey', concrete: 'cement stone grey gritty', gravel: 'stone grit grey',
        expensive: 'luxury premium elegant rich', luxurious: 'luxury premium elegant', classy: 'elegant luxury refined', fancy: 'luxury ornate elegant', premium: 'luxury elegant refined', posh: 'luxury elegant',
        cheap: 'plain flat basic', plain: 'flat clean solid simple', simple: 'flat clean solid plain', basic: 'flat clean solid plain', boring: 'flat plain solid',
        sparkly: 'sparkle glitter flake shimmer', glittery: 'glitter sparkle flake', shimmery: 'shimmer sparkle pearl', shiny: 'gloss glossy reflective chrome mirror', glossy: 'gloss shiny reflective',
        dull: 'matte flat satin', flat: 'matte solid plain', matt: 'matte', satiny: 'satin',
        mirror: 'chrome reflective liquid metal', reflective: 'chrome mirror metallic glossy', metal: 'metallic steel chrome aluminium', metallic: 'metal flake pearl steel',
        aluminum: 'aluminium brushed silver metal', aluminium: 'aluminum brushed silver metal', steel: 'metal gunmetal grey brushed', iron: 'metal cast dark grey rust', copper: 'bronze orange metal', brass: 'gold yellow metal bronze',
        gold: 'golden yellow champagne metallic', silver: 'chrome grey metallic platinum', platinum: 'silver white metallic', champagne: 'gold pale metallic',
        neon: 'glow bright fluorescent electric', glowing: 'neon glow luminous', electric: 'neon blue bright voltage', fluorescent: 'neon bright glow', cyberpunk: 'neon techy futuristic dark city',
        military: 'camo olive stealth matte tactical', army: 'camo olive green military', tactical: 'military matte stealth camo', jet: 'military grey stealth aircraft', fighter: 'military grey stealth aircraft', stealthy: 'stealth matte dark black',
        stealth: 'matte black dark murdered flat', murdered: 'stealth matte black flat', blackout: 'black matte stealth', vantablack: 'black darkest matte',
        retro: 'vintage classic old throwback', vintage: 'retro classic old patina', classic: 'retro vintage timeless', oldschool: 'retro vintage classic', throwback: 'retro vintage classic',
        seventies: '70s retro', sixties: '60s retro', eighties: '80s retro neon', nineties: '90s retro',
        weathered: 'worn aged rust patina dirt', worn: 'weathered aged scuffed rust', rusty: 'rust corroded weathered orange brown', rusted: 'rust corroded weathered', aged: 'weathered patina worn old', patina: 'aged green copper weathered',
        glass: 'transparent clear gloss crystal', frosted: 'frost ice glass white cold', icy: 'ice frost cold blue white', frozen: 'ice frost cold blue', cold: 'ice frost blue frozen', snow: 'white frost ice',
        fire: 'flame lava orange red hot', flames: 'fire lava orange red hot', lava: 'fire molten orange red hot', hot: 'fire red orange warm', molten: 'lava fire liquid hot',
        space: 'cosmic galaxy nebula stars dark', galaxy: 'cosmic nebula space stars purple', stars: 'cosmic galaxy sparkle space', cosmic: 'galaxy space nebula stars',
        ocean: 'sea water blue wave teal', sea: 'ocean water blue wave', water: 'ocean liquid wave blue', beach: 'sand sea ocean tropical', tropical: 'island beach green teal pink',
        forest: 'green leaf nature camo wood', jungle: 'green leaf tropical camo', leaf: 'green nature plant foliage', wood: 'brown grain timber natural', leather: 'hide brown grain', bark: 'wood brown tree',
        candy: 'translucent deep glossy tinted', pearl: 'pearlescent shimmer iridescent soft', pearlescent: 'pearl shimmer iridescent', iridescent: 'rainbow oil slick shift pearl', chameleon: 'colour shift flip rainbow iridescent',
        holographic: 'rainbow hologram iridescent prism', hologram: 'holographic rainbow prism foil', rainbow: 'multicolor spectrum holographic iridescent', prism: 'rainbow spectrum holographic', foil: 'metallic shiny holographic',
        carbon: 'weave fibre fiber black techy', fibre: 'carbon weave', fiber: 'carbon weave', weave: 'carbon fabric woven textile', mesh: 'weave grid metal', honeycomb: 'hex hexagon grid',
        camo: 'camouflage military pattern green', camouflage: 'camo military pattern green', digital: 'pixel techy camo', pixel: 'digital techy blocks',
        vinyl: 'wrap satin sticker film', wrap: 'vinyl satin film', sticker: 'vinyl wrap decal', decal: 'vinyl sticker',
        luxury: 'elegant premium refined rich', elegant: 'luxury refined classy', refined: 'elegant luxury clean', rich: 'luxury deep dark', deep: 'rich dark candy glossy',
        aggressive: 'angry fast bold sharp dark', angry: 'aggressive dark red bold', menacing: 'aggressive dark stealth', villain: 'dark aggressive menacing black purple green', evil: 'dark aggressive menacing',
        playful: 'fun bright colourful candy', fun: 'playful bright colourful', kids: 'playful bright colourful', cute: 'playful pastel soft', pastel: 'soft light pink mint lilac', soft: 'pastel gentle satin matte',
        halloween: 'spooky orange black pumpkin', spooky: 'dark halloween ghost bones', ghost: 'spooky pale white translucent', skull: 'spooky bones dark', christmas: 'red green festive gold', patriotic: 'red white blue american flag',
        american: 'patriotic red white blue flag', flag: 'patriotic stars stripes', usa: 'american patriotic red white blue',
        dirt: 'rugged weathered mud earth grit', rugged: 'tough dirt rough weathered', tough: 'rugged rough dirt', industrial: 'metal steel grit factory raw', raw: 'unpainted bare metal industrial', grunge: 'dirty worn rough',
        organic: 'natural flowing curved', natural: 'organic earth leaf wood', earthy: 'brown tan natural', sunset: 'orange pink warm dusk gradient', sunrise: 'orange pink warm gradient dawn', dusk: 'sunset purple orange',
        whiskey: 'amber brown candy golden bourbon', bourbon: 'amber brown whiskey golden', amber: 'orange yellow brown golden', wine: 'burgundy red deep maroon', burgundy: 'wine red deep maroon',
        gem: 'jewel crystal faceted sparkle', gemstone: 'jewel crystal faceted sparkle gem', jewel: 'gem crystal sparkle deep', diamond: 'sparkle crystal white bright', crystal: 'glass gem faceted sparkle', opal: 'pearl iridescent milky rainbow',
        watch: 'luxury metal brushed steel dial', guitar: 'sunburst wood gloss amber', sunburst: 'gradient amber red wood guitar', beer: 'amber gold frost', gradient: 'fade blend transition',
        oil: 'slick rainbow iridescent dark', slick: 'oil rainbow iridescent', bubble: 'iridescent soap rainbow transparent', soap: 'bubble iridescent rainbow',
        matte: 'flat dull satin no shine', satin: 'silky soft sheen semi', gloss: 'glossy shiny wet clearcoat', wet: 'gloss glossy deep liquid', liquid: 'wet flowing mirror metal',
        bold: 'loud bright strong', loud: 'bold bright shouting', quiet: 'subtle calm understated', subtle: 'quiet calm understated soft', calm: 'quiet subtle clean',
        gunmetal: 'dark grey metal steel', graphite: 'dark grey carbon pencil', charcoal: 'dark grey black', slate: 'grey blue dark stone', stone: 'rock grey gritty', granite: 'stone speckled grey', marble: 'stone veined white grey'
    };
    // painter words found missing in the 2026-10-02 spot checks ("a car that looks just waxed", "showroom", "buffed"): same shape as LEX above
    var MORE_LEX = { shinier: 'gloss glossy shiny reflective', glossier: 'gloss glossy shiny wet', flatter: 'matte flat dull', duller: 'matte flat dull satin', darker: 'dark black deep', lighter: 'light pale bright', brighter: 'bright vivid light', sparklier: 'sparkle glitter flake shimmer', smoother: 'smooth clean flat polished', rougher: 'rough textured grit', waxed: 'gloss wet polished shiny deep', buffed: 'gloss polished shiny smooth', polished: 'gloss shiny smooth reflective', detailed: 'gloss polished wet clean', showroom: 'gloss polished wet clean premium', concours: 'gloss polished wet premium elegant', glassy: 'glass gloss wet smooth reflective', mirrorlike: 'mirror chrome reflective gloss' };
    Object.keys(MORE_LEX).forEach(function (k) { if (!LEX[k]) LEX[k] = MORE_LEX[k]; });
    // MSR-FIX-B 2026-10-03 (mad scientist run): animal / era / weather / material words the cards never use -> the words they do use. Same shape as LEX.
    var MSR_LEX = {
        rattlesnake: 'snake scales reptile skin diamond', copperhead: 'snake scales reptile copper brown', viper: 'snake scales reptile skin', cobra: 'snake scales reptile skin hood', python: 'snake scales reptile skin', mamba: 'snake scales reptile green',
        anaconda: 'snake scales reptile green', serpent: 'snake scales reptile', snakeskin: 'snake scales reptile skin', reptile: 'scales snake crocodile lizard', lizard: 'scales reptile skin', gecko: 'scales reptile lizard',
        gator: 'crocodile alligator scales reptile hide', croc: 'crocodile alligator scales reptile hide', alligator: 'crocodile scales reptile hide', dinosaur: 'scales reptile dragon bumpy', dragon: 'scales reptile fantasy',
        mermaid: 'scales iridescent pearl teal fish', koi: 'fish scales orange white', fishscale: 'fish scales', dalmatian: 'spots dots black white', cow: 'spots patches black white', ladybug: 'red black dots spots',
        cheetah: 'leopard spots animal print', jaguar: 'leopard spots rosette animal print', rosette: 'leopard spots jaguar', giraffe: 'patches spots animal print',
        butterfly: 'iridescent wing shimmer', morpho: 'iridescent blue butterfly wing', tortoise: 'shell amber brown', tortoiseshell: 'shell amber brown', fur: 'soft fuzzy matte', armadillo: 'armor plates segments scales',
        tweed: 'weave fabric woven textile', canvas: 'weave fabric woven textile', burlap: 'weave fabric woven coarse',
        synthwave: '80s retro neon grid purple pink sunset', vaporwave: '80s retro pastel neon pink purple', outrun: '80s retro neon grid sunset', hotrod: 'hot rod flames retro 50s candy', gasser: 'hot rod drag 60s retro candy',
        lowrider: 'candy flake pearl 70s', y2k: '2000s chrome holographic', disco: 'sparkle glitter 70s mirror', groovy: '70s retro swirl', psychedelic: '60s swirl rainbow trippy',
        mottled: 'blotchy spotted camo patchy', blotchy: 'mottled camo patches', patchy: 'patches mottled blotchy', burnished: 'polished metal bronze', stitching: 'stitch leather thread',
        plated: 'metal chrome plate', blasted: 'sandblast rough matte', bleached: 'faded pale white', tinted: 'candy translucent', soaked: 'wet gloss liquid', sweating: 'wet droplets dew', drenched: 'wet gloss liquid', dewy: 'dew droplets wet',
        meaner: 'aggressive dark bold', dope: 'cool bold', pinker: 'pink', redder: 'red', bluer: 'blue', greener: 'green', glowy: 'glow neon luminous', glows: 'glow neon luminous', lambo: 'lime green orange bright exotic', papaya: 'orange bright',
        sparkle: 'glitter flake stardust shimmer', goo: 'slime drip liquid wet', frosty: 'frost frosted ice cold', icey: 'ice frost cold', slime: 'goo drip liquid wet green', drips: 'drip liquid splatter', cracks: 'crackle cracked crazing', cracked: 'crackle crazing cracks', sparkles: 'glitter flake stardust shimmer', vein: 'marble veining stone', veins: 'marble veining stone', veined: 'marble veining stone', veining: 'marble stone'
    };
    Object.keys(MSR_LEX).forEach(function (k) { if (!LEX[k]) LEX[k] = MSR_LEX[k]; });
    // MSR-FIX-B: typo / text-speak words people really type ("gimme a matt blak car wit carbn fiber") -> plain words, BEFORE any parsing. SpbAICards.normalize(text) is exported so the
    // advisor / designer can run the same clean-up first. Only words that are never real paint words are listed (no "sum", "sick", "mat" risks); "" drops filler.
    var SLANG = {
        gimme: 'give me', wanna: 'want to', gonna: 'going to', gotta: 'got to', tryna: 'trying to', lookin: 'looking', thinkin: 'thinking', nothin: 'nothing', everythin: 'everything', sumthin: 'something', somethin: 'something', smth: 'something',
        jus: 'just', ya: 'you', u: 'you', ur: 'your', im: 'i am', aint: 'is not', dont: 'do not', doesnt: 'does not', kinda: 'kind of', sorta: 'sort of', whut: 'what', wut: 'what', wat: 'what', wats: 'what is', whats: 'what is', thx: '', plz: '', pls: '', frfr: '', ngl: '', idk: '', bro: '', yo: '', fam: '', lol: '', tbh: '', hella: '', lowkey: 'kind of', lil: 'little',
        wit: 'with', wiht: 'with', wtih: 'with', blak: 'black', blk: 'black', blck: 'black', wite: 'white', whyte: 'white', wht: 'white', pnk: 'pink', purpel: 'purple', purpul: 'purple', purp: 'purple', grean: 'green', gren: 'green', grn: 'green',
        yelow: 'yellow', yello: 'yellow', orng: 'orange', orang: 'orange', blu: 'blue', bleu: 'blue', goldn: 'gold', chrme: 'chrome', brwn: 'brown', gry: 'grey', silvr: 'silver', satn: 'satin', midnite: 'midnight', matt: 'matte', glosy: 'glossy', glossey: 'glossy', shiney: 'shiny', shinny: 'shiny',
        kamo: 'camo', cammo: 'camo', camoflage: 'camouflage', camoflauge: 'camouflage', camouflauge: 'camouflage', crome: 'chrome', chromee: 'chrome', chrom: 'chrome', krome: 'chrome', metalic: 'metallic', metallik: 'metallic', metalik: 'metallic', metallick: 'metallic',
        perl: 'pearl', irridescent: 'iridescent', iridecent: 'iridescent', iridesent: 'iridescent', chamelion: 'chameleon', leapord: 'leopard', leopord: 'leopard', snek: 'snake', rattelsnake: 'rattlesnake', rattlsnake: 'rattlesnake', rattlesnek: 'rattlesnake',
        marbel: 'marble', marbl: 'marble', canndy: 'candy', candi: 'candy', kandy: 'candy', aple: 'apple', carbn: 'carbon', carbonfiber: 'carbon fiber', carbonfibre: 'carbon fibre', paterns: 'patterns', patern: 'pattern', pattrn: 'pattern', sparkel: 'sparkle', sparkels: 'sparkles',
        hamerd: 'hammered', hammerd: 'hammered', hamered: 'hammered', brushd: 'brushed', grane: 'grain', diferent: 'different', difrence: 'difference', diffrence: 'difference', thiner: 'thinner', skool: 'school', tye: 'tie',
        numbrs: 'numbers', nums: 'numbers', tha: 'the', da: 'the', n: 'and', bodie: 'body', bodys: 'body', strips: 'stripes', rattler: 'rattlesnake', holo: 'holographic', sidez: 'sides', stripez: 'stripes', scalez: 'scales', flaems: 'flames', flamez: 'flames', flams: 'flames'
    };
    // phrases: idioms that would otherwise feed the search the wrong noun ("in the vein of a dodge viper" is not marble veins on a snake)
    var NPHR = [[/\bold skool\b/g, 'old school'], [/\btye[- ]?dye\b/g, 'tie dye'], [/\bin the (?:vein|spirit|style) of\b/g, 'like'], [/\bdodge viper\b/g, 'american sports car'], [/\bhot wheels\b/g, 'toy car bright'], [/\b(?:army|military) colou?rs\b/g, 'army green and olive drab']];
    var SLANG_RE = new RegExp('(^|[^a-z0-9#])(' + Object.keys(SLANG).sort(function (a, b) { return b.length - a.length; }).join('|') + ')(?=$|[^a-z0-9])', 'g');
    // MSR-FIX-B: hex colours in an ask ("flat #ff2d95 pink", "#1b1b1b base") -> the nearest plain colour name (+ dark / light) for the SEARCH only (the exact hex stays in the ask for the designer)
    var HEXN = [['black', 17, 17, 19], ['white', 244, 244, 241], ['grey', 138, 141, 146], ['silver', 195, 199, 204], ['red', 200, 16, 46], ['orange', 242, 107, 33], ['yellow', 255, 210, 0], ['gold', 215, 167, 43],
        ['green', 31, 138, 59], ['lime', 155, 213, 43], ['teal', 15, 154, 160], ['cyan', 0, 194, 224], ['blue', 20, 80, 180], ['navy', 11, 35, 80], ['purple', 106, 27, 154], ['magenta', 214, 36, 125], ['pink', 255, 126, 182], ['pink', 255, 47, 146],
        ['brown', 107, 58, 30], ['tan', 201, 165, 122], ['cream', 241, 230, 200], ['maroon', 109, 15, 31]];
    function hexName(h) {
        var r = parseInt(h.substr(0, 2), 16), g = parseInt(h.substr(2, 2), 16), b = parseInt(h.substr(4, 2), 16), best = 'grey', bd = 1e9;
        for (var i = 0; i < HEXN.length; i++) { var c = HEXN[i], d = (r - c[1]) * (r - c[1]) * 0.3 + (g - c[2]) * (g - c[2]) * 0.59 + (b - c[3]) * (b - c[3]) * 0.11; if (d < bd) { bd = d; best = c[0]; } }
        var l = (0.2126 * r + 0.7152 * g + 0.0722 * b) / 255;
        return best + (l < 0.18 && best !== 'black' && best !== 'navy' && best !== 'maroon' ? ' dark' : (l > 0.82 && best !== 'white' && best !== 'cream' ? ' light' : (best === 'black' ? ' dark' : '')));
    }
    function hexWords(t) { return String(t || '').replace(/(^|[^a-z0-9])(#?)([0-9a-f]{6})(?![0-9a-z])/gi, function (all, pre, hs, h) { return (hs || /[0-9]/.test(h)) ? pre + hexName(h.toLowerCase()) : all; }); }      // "decade" / "facade" are words, not colours: a # or a digit is required
    function normalize(text) {
        var t = String(text == null ? '' : text).toLowerCase().replace(/\bw\/(?=\s|[a-z])/g, 'with ');
        for (var pi = 0; pi < NPHR.length; pi++) t = t.replace(NPHR[pi][0], NPHR[pi][1]);
        return t.replace(SLANG_RE, function (all, pre, w) { return pre + SLANG[w]; }).replace(/[ \t]{2,}/g, ' ').replace(/^ | $/g, '');
    }
    var NEG = /\b(?:anything but|everything but|all but|anything except|everything except|anything besides|anything other than|no|not|without|except|never|minus|avoid|other than|besides|instead of|rather than|don'?t want|do not want|dont want|aint|ain't|nothing(?!\s+(?:but|except|other|else)\b))\s+(?:any\s+|too\s+much\s+|a\s+|the\s+|too\s+)?([a-z]+(?:(?:\s*,\s*(?:or\s+|nor\s+)?|\s+(?:or|nor)\s+)[a-z]+)*(?:\s[a-z]+)?)/g;

    // ------------------------------------------------------------------ load + decode
    function load() {
        if (DATA && IDX) return Promise.resolve(DATA);
        if (LOADING) return LOADING;
        var AT = window.SpbAIAtlas, pa = AT ? AT.load() : Promise.resolve(null);
        LOADING = pa.then(function () {
            if (window.SPB_CARDS_DATA) return installAsync(window.SPB_CARDS_DATA);
            return new Promise(function (resolve) {
                var sc = document.createElement('script'); sc.async = true; sc.src = BASE() + 'js/spb-ai-cards-data.js?v=' + (window.SPB_CARDS_V || '20261004fc2');
                sc.onload = function () { try { resolve(window.SPB_CARDS_DATA ? installAsync(window.SPB_CARDS_DATA) : null); } catch (e) { try { console.warn('[AI CARDS]', e); } catch (x) {} resolve(null); } };
                sc.onerror = function () { LOADING = null; try { console.warn('[AI CARDS] could not load the data file'); } catch (x) {} resolve(null); };
                document.head.appendChild(sc);
            });
        }).then(function (dd) { try { loadLSA(); } catch (el) {} return dd; });
        return LOADING;
    }
    // the latent-semantic file (1.4 MB) loads AFTER the cards, in the background: until it arrives (or if it is missing) search is plain BM25
    function loadLSA() {
        if (window.SPB_LSA_DATA || window.__spbLsaLoading || typeof document === 'undefined' || !document.createElement) return;
        window.__spbLsaLoading = true; var sc = document.createElement('script'); sc.async = true; sc.src = BASE() + 'js/spb-lsa-data.js?v=' + (window.SPB_LSA_V || '20261004fc2');
        sc.onerror = function () { window.__spbLsaLoading = false; try { console.warn('[AI CARDS] no latent-semantic file (plain keyword search)'); } catch (x) {} };
        document.head.appendChild(sc);
    }
    function install(d) { setLexExt(window.SPB_LEX_EXT || {}); DATA = d; MOODS = d.moods; ERAS = d.eras; USES = d.uses; FITS = d.fits; IDX = null; buildIndex(); return DATA; }
    function installAsync(d) { setLexExt(window.SPB_LEX_EXT || {}); DATA = d; MOODS = d.moods; ERAS = d.eras; USES = d.uses; FITS = d.fits; IDX = null; return buildIndexAsync(d).then(function () { return DATA; }); }
    function ready() { return !!(DATA && IDX); }
    // ---- latent-semantic component (js/spb-lsa-data.js, built by scripts/ai_atlas/build_lsa.py from these same cards): the cosine of the ask with every card in a 96-d space learned from the
    // cards themselves (lava ~ molten ~ magma, velvet ~ plush ~ suede), fused with BM25 so a described ask reaches finishes that never use the painter's word. No data file = plain BM25.
    var LSA = null, LSAW = { w: 0.5, top: 160 };
    function lsaInit() {
        var d = window.SPB_LSA_DATA; if (!d || !IDX) return null;
        if (LSA && LSA.src === d && LSA.idx === IDX) return LSA;
        try {
            var dec = function (b64, Ctor) { var sx = atob(b64), n = sx.length, u = new Uint8Array(n); for (var i = 0; i < n; i++) u[i] = sx.charCodeAt(i); return new Ctor(u.buffer); };
            var k = d.k, V = dec(d.V, Int8Array), D = dec(d.D, Int8Array), ts = dec(d.ts, Float32Array), vi = {}, i;
            for (i = 0; i < d.vocab.length; i++) vi[d.vocab[i]] = i;
            var row = new Int32Array(IDX.docs.length), ki = {}; for (i = 0; i < d.keys.length; i++) ki[d.keys[i]] = i;
            for (i = 0; i < IDX.docs.length; i++) { var r = ki[IDX.docs[i].k]; row[i] = r == null ? -1 : r; }
            LSA = { src: d, idx: IDX, k: k, V: V, D: D, ts: ts, vi: vi, row: row, idf: d.idf };
        } catch (e) { LSA = null; }
        return LSA;
    }
    function lsaScores(P) {
        var L = lsaInit(); if (!L) return null; var k = L.k, q = new Float64Array(k), any = false, t, c;
        for (t in P.terms) { if (t.indexOf('_') !== -1) continue; var j = L.vi[t]; if (j == null) continue; var w = P.terms[t] * L.idf[j] * L.ts[j] / 127, base = j * k; for (c = 0; c < k; c++) q[c] += w * L.V[base + c]; any = true; }
        if (!any) return null; var nrm = 0; for (c = 0; c < k; c++) nrm += q[c] * q[c]; nrm = Math.sqrt(nrm) || 1; for (c = 0; c < k; c++) q[c] /= nrm;
        var n = IDX.docs.length, cos = new Float32Array(n);
        for (var di = 0; di < n; di++) { var r = L.row[di]; if (r < 0) continue; var sc = 0, b2 = r * k; for (c = 0; c < k; c++) sc += q[c] * L.D[b2 + c]; cos[di] = sc / 127; }
        return cos;
    }
    function pick(vocab, ix) { var o = []; for (var i = 0; i < ix.length; i++) { if (vocab[ix[i]]) o.push(vocab[ix[i]]); } return o; }
    // DEEP-SHIP 2026-10-03: row[18] = null or {c,f,l,s,n,p,w,q} (look_close, look_far, light, stack, not, placement, with_numbers, confidence)
    function unDeep(d) { if (!d) return null; var o = { look_close: d.c, look_far: d.f, light: d.l, stack: d.s, not: d.n, placement: d.p, with_numbers: d.w, confidence: d.q }; for (var k in o) { if (o[k] == null) delete o[k]; } return o; }
    function deep(key) { var c = card(key); return c && c.deep ? c.deep : null; }
    function card(key) {
        if (!DATA) return null; var r = DATA.cards[key]; if (!r) return null;
        return { look: r[0], analog: r[1], syn: r[2], mood: pick(MOODS, r[3]), era: pick(ERAS, r[4]), fit: pick(FITS, r[5]), use: pick(USES, r[6]), loud: r[7], busy: r[8], pair: r[9], avoid: r[10], scale: SCALES[r[11]] || '', vis: !!r[12], appeal: r[13] || 3, body: r[14] || 3, accent: r[15] || 3, hero: r[16] || 3, risk: r[17] || 3, deep: unDeep(r[18]) };
    }

    // ------------------------------------------------------------------ BM25F index
    var W = { name: 3.2, syn: 3.0, analog: 2.4, look: 2.0, tags: 1.4, shelf: 0.8, desc: 1.0, mood: 1.6 };
    function newIdx() { return { docs: [], inv: {}, N: 0, avg: 1, keyIdx: {}, total: 0 }; }
    function indexRange(ix, keys, from, to) {
        var AT = window.SpbAIAtlas, ad = AT && AT._data ? AT._data() : null, i;
        for (i = from; i < to && i < keys.length; i++) {
            var k = keys[i], r = DATA.cards[k], it = AT ? AT.lookup(k) : null, tf = {}, len = 0;
            var add = function (text, w) {
                var t = toks(text), a;
                for (a = 0; a < t.length; a++) { tf[t[a]] = (tf[t[a]] || 0) + w; len += w; if (a + 1 < t.length) { var bg = t[a] + '_' + t[a + 1]; tf[bg] = (tf[bg] || 0) + w * 1.2; } }
            };
            add(it ? it.n : k.replace(/^[a-z]+::/, '').replace(/_/g, ' '), W.name);
            add(r[2].join(' , '), W.syn); add(r[1].join(' , '), W.analog); add(r[0], W.look);
            add(pick(MOODS, r[3]).join(' '), W.mood);
            if (it) { add((it.t || []).join(' '), W.tags); add((it.shelves ? it.shelves : (it.s || []).slice(0, 2).map(function (si) { return ad ? ad.sections[si] : ''; })).join(' '), W.shelf); add(it.d || '', W.desc); }
            var doc = { k: k, tf: tf, len: len || 1, type: k.split('::')[0], own: it ? it.o : 1, q: it ? it.q : null, it: it };
            ix.keyIdx[k] = ix.docs.length; ix.docs.push(doc); ix.total += doc.len;
            for (var t in tf) { if (Object.prototype.hasOwnProperty.call(tf, t)) { (ix.inv[t] = ix.inv[t] || []).push(ix.docs.length - 1); } }
        }
    }
    function finishIdx(ix) { ix.N = ix.docs.length; ix.avg = ix.total / Math.max(1, ix.N); return ix; }
    function buildIndex() { var ix = newIdx(), keys = Object.keys(DATA.cards); indexRange(ix, keys, 0, keys.length); IDX = finishIdx(ix); }
    function buildIndexAsync(d) {
        return new Promise(function (resolve) {
            var ix = newIdx(), keys = Object.keys(d.cards), i = 0;
            (function step() {
                if (DATA !== d) { resolve(); return; }
                var t0 = Date.now();
                try { while (i < keys.length && Date.now() - t0 < 12) { indexRange(ix, keys, i, i + 25); i += 25; } } catch (e) { try { console.warn('[AI CARDS]', e); } catch (x) {} resolve(); return; }
                if (i < keys.length) { setTimeout(step, 0); return; }
                IDX = finishIdx(ix); resolve();
            })();
        });
    }
    function idf(t) { var l = IDX.inv[t]; if (!l) return 0; return Math.log(1 + (IDX.N - l.length + 0.5) / (l.length + 0.5)); }

    // ------------------------------------------------------------------ typo tolerance: a query word the cards never use ("metalic", "candi aple") snaps to its nearest card word
    var VBUCKET = null, VBUCKET_FOR = null;
    function vocabBuckets() {
        if (VBUCKET && VBUCKET_FOR === IDX) return VBUCKET;
        var b = {}, t; for (t in IDX.inv) { if (t.indexOf('_') !== -1 || t.length < 4 || /\d/.test(t)) continue; var k = t.charAt(0) + t.length; (b[k] = b[k] || []).push(t); }
        VBUCKET = b; VBUCKET_FOR = IDX; return b;
    }
    function editDist(a, b, max) {         // Damerau-Levenshtein with an early exit
        var la = a.length, lb = b.length; if (Math.abs(la - lb) > max) return max + 1;
        var prev2 = null, prev = [], cur, i, j; for (j = 0; j <= lb; j++) prev.push(j);
        for (i = 1; i <= la; i++) {
            cur = [i]; var rowMin = i;
            for (j = 1; j <= lb; j++) {
                var c = a.charAt(i - 1) === b.charAt(j - 1) ? 0 : 1, v = Math.min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + c);
                if (prev2 && i > 1 && j > 1 && a.charAt(i - 1) === b.charAt(j - 2) && a.charAt(i - 2) === b.charAt(j - 1)) v = Math.min(v, prev2[j - 2] + 1);
                cur.push(v); if (v < rowMin) rowMin = v;
            }
            if (rowMin > max) return max + 1; prev2 = prev; prev = cur;
        }
        return prev[lb];
    }
    function nearest(tok) {
        if (!IDX || !tok || tok.length < 5 || IDX.inv[tok]) return null;
        var maxd = tok.length >= 8 ? 2 : 1, b = vocabBuckets(), best = null, bd = 99, bdf = -1, l, arr, i;
        for (l = tok.length - maxd; l <= tok.length + maxd; l++) {
            arr = b[tok.charAt(0) + l]; if (!arr) continue;
            for (i = 0; i < arr.length; i++) { var d = editDist(tok, arr[i], maxd); if (d <= maxd) { var df = IDX.inv[arr[i]].length; if (d < bd || (d === bd && df > bdf)) { best = arr[i]; bd = d; bdf = df; } } }
        }
        return best;
    }
    // ------------------------------------------------------------------ extended painter lexicon (js/spb-lexicon-ext.js, window.SPB_LEX_EXT = {words:{word:"catalogue words"}, phrases:{"spray can":"matte rough"}}): checked offline against the picture judge before it ships
    var LEXX = { w: {}, p: [] };      // (setLexExt is called at install; PHR0 below seeds it)
    // built-in painter phrases that are obviously right (kept here, not in the generated spb-lexicon-ext.js, so a re-run of vocab_ab.js never drops them)
    var PHR0 = { 'low sheen': 'matte satin flat soft', 'low-sheen': 'matte satin flat soft', 'low gloss': 'matte satin flat soft', 'low-gloss': 'matte satin flat soft', 'reduced gloss': 'matte satin flat soft', 'soft sheen': 'satin eggshell soft', 'quiet sheen': 'satin eggshell soft', 'dead flat': 'matte flat dull', 'no sheen': 'matte flat dull', 'minimal sheen': 'matte satin flat', 'kill the shine': 'matte satin flat soft', 'kill shine': 'matte satin flat soft', 'tone down the shine': 'matte satin soft', 'tone down the gloss': 'matte satin soft', 'toned the clear down': 'matte satin soft', 'less shine': 'matte satin soft', 'less gloss': 'matte satin soft', 'too shiny': 'matte satin soft low sheen', 'too glossy': 'matte satin soft low sheen', 'too much gloss': 'matte satin soft low sheen', 'looks like plastic': 'matte satin soft low sheen' };
    function setLexExt(o) { o = o || {}; var ph = {}, k0; for (k0 in PHR0) ph[k0] = PHR0[k0]; for (k0 in (o.phrases || {})) ph[k0] = o.phrases[k0]; LEXX = { w: o.words || {}, p: Object.keys(ph).sort(function (a, b) { return b.length - a.length; }).map(function (k) { return [k, ph[k]]; }) }; }
    function parseQuery(q) {
        q = hexWords(normalize(q));      // MSR-FIX-B: typos / text-speak first; a hex colour (#ff2d95) searches as its colour words ("pink")
        var neg = [], m, qq = q.replace(NEG, function (all, w) { neg = neg.concat(toks(w)); return ' '; });
        var base = toks(qq), terms = {}, order = [], i;
        base = base.map(function (t) { if (t.length >= 5 && IDX && !IDX.inv[t]) { var n = nearest(t); if (n) return n; } return t; });
        function addT(t, w) { if (!terms[t]) { terms[t] = 0; order.push(t); } terms[t] = Math.max(terms[t], w); }
        for (i = 0; i < base.length; i++) { addT(base[i], 1); if (i + 1 < base.length) addT(base[i] + '_' + base[i + 1], 1.3); }
        LEXX.p.forEach(function (pr) { if (qq.indexOf(pr[0]) !== -1) { var pt = toks(pr[1]); for (var pj = 0; pj < pt.length; pj++) addT(pt[pj], 0.5); } });
        var raw = norm(qq).split(' ').map(function (w) { if (w.length >= 5 && IDX && !LEX[w] && !IDX.inv[stem(w)]) { var n = nearest(stem(w)); if (n) return n; } return w; });
        for (i = 0; i < raw.length; i++) { var ex = LEX[raw[i]] || LEX[stem(raw[i])] || LEXX.w[raw[i]] || LEXX.w[stem(raw[i])]; if (ex) { var et = toks(ex); for (var j = 0; j < et.length; j++) addT(et[j], 0.45); } }
        return { terms: terms, order: order, neg: neg, nBase: base.length };
    }

    var SHEEN_W = { matte: 1, satin: 1, gloss: 1, glossy: 1, candy: 1, metallic: 1, chrome: 1, flat: 1, shiny: 1, pearl: 1, finish: 1, body: 1, base: 1 };
    var COLW = null, COLW_FOR = null;
    function colourWords() {      // single-word colour names (the designer's table + js/spb-colours-ext.js), stemmed like the index
        var C = (window.SpbProDesign && window.SpbProDesign.COLOURS) || null, X = window.SPB_COLOUR_EXT || null, key = (C ? 1 : 0) + (X ? 2 : 0);
        if (COLW && COLW_FOR === key) return COLW;
        var o = {}, k; [C, X].forEach(function (T) { if (!T) return; for (k in T) { if (/^[a-z]+$/.test(k)) o[stem(k)] = 1; } });
        ['red', 'blue', 'green', 'black', 'white', 'grey', 'gray', 'pink', 'purple', 'orange', 'yellow', 'gold', 'silver', 'brown', 'teal', 'navy', 'midnight', 'dark', 'light', 'bright', 'deep', 'pale'].forEach(function (w0) { o[stem(w0)] = 1; });
        COLW = o; COLW_FOR = key; return o;
    }
    function search(query, o) {
        o = o || {}; if (!ready()) return [];
        var P = parseQuery(query), limit = o.limit || 12, off = o.offset || 0, types = o.types || null, excl = {}, k1 = 1.35, b = 0.7, scores = {}, hitc = {}, hits = {}, t, i;
        (o.exclude || []).forEach(function (x) { excl[x] = 1; });
        if (!P.order.length) return [];
        // MSR-FIX-B 2026-10-03: a TEXTURE-only search (pattern / spec lanes) is about the texture word; colour words ("marble under candy red", "midnight blue satin with silver stripes")
        // are weak evidence there (most textures take the zone colour), so they keep 30% weight and do not count towards coverage; a pattern-only search does the same for sheen words.
        var texOnly = types && types.length && types.every(function (t0) { return t0 === 'pattern' || t0 === 'spec'; });
        if (texOnly) {
            var weakW = colourWords(), patOnly = types.every(function (t0) { return t0 === 'pattern'; }), nWeak = 0;
            P.order.forEach(function (t1) { if (t1.indexOf('_') !== -1) return; if (weakW[t1] || (patOnly && SHEEN_W[t1])) { if (P.terms[t1] >= 1) nWeak++; P.terms[t1] *= 0.3; } });
            if (nWeak && nWeak < P.nBase) P.nBase -= nWeak;
        }
        P.order.forEach(function (t) {
            var l = IDX.inv[t]; if (!l) return; var w = P.terms[t], id = idf(t) * w;
            for (var a = 0; a < l.length; a++) {
                var d = IDX.docs[l[a]], f = d.tf[t], s = id * (f * (k1 + 1)) / (f + k1 * (1 - b + b * d.len / IDX.avg));
                scores[l[a]] = (scores[l[a]] || 0) + s; if (w >= 1) hitc[l[a]] = (hitc[l[a]] || 0) + 1; (hits[l[a]] = hits[l[a]] || []).push(t);
            }
        });
        var lw = o.lsa != null ? o.lsa : LSAW.w, cosv = lw > 0 ? lsaScores(P) : null;
        if (cosv) {
            var maxB = 0, dk0; for (dk0 in scores) { if (scores[dk0] > maxB) maxB = scores[dk0]; }
            if (maxB > 0) {
                var srt = cosv.slice().sort(), nC = srt.length, hiC = srt[nC - 1], floorC = srt[Math.max(0, nC - 1 - LSAW.top)], span = Math.max(1e-6, hiC - floorC), cands = {}, nn;
                for (dk0 in scores) cands[dk0] = 1; for (nn = 0; nn < nC; nn++) { if (cosv[nn] > floorC) cands[nn] = 1; }
                Object.keys(cands).forEach(function (dk) { var bm = (scores[dk] || 0) / maxB, ls = Math.max(0, (cosv[dk] - floorC) / span); scores[dk] = maxB * ((1 - lw) * bm + lw * ls); });
            }
        }
        P.neg.forEach(function (t) { var l = IDX.inv[t]; if (!l) return; for (var a = 0; a < l.length; a++) { if (scores[l[a]] != null) scores[l[a]] *= 0.12; } });      // a negated word ("no chrome", "other than chrome") nearly removes every card that carries it
        var out = [];
        Object.keys(scores).forEach(function (di) {
            var d = IDX.docs[di]; if (excl[d.k]) return; if (types && types.indexOf(d.type) === -1) return;
            if (o.own === 'own' && d.own !== 1 && (d.type === 'base' || d.type === 'monolithic')) return; if (o.own === 'takes' && d.own === 1 && (d.type === 'base' || d.type === 'monolithic')) return;
            if (o.minQ && (d.q == null || d.q < o.minQ)) return;
            var cover = P.nBase ? Math.min(1, (hitc[di] || 0) / Math.max(1, P.nBase)) : 0;
            var s = scores[di] * (0.55 + 0.45 * cover) + (d.q != null ? (d.q - 50) / 120 : 0);
            out.push({ key: d.k, s: s, hits: (hits[di] || []).filter(function (x) { return x.indexOf('_') === -1; }).slice(0, 6) });
        });
        out.sort(function (x, y) { return y.s - x.s; });
        return out.slice(off, off + limit);
    }
    window.SpbAICards = { load: load, ready: ready, card: card, deep: deep, search: search, _data: function () { return DATA; }, _install: install, _idx: function () { return IDX; }, _lsa: LSAW, _lex: LEX, nearest: nearest, editDist: editDist, setLexExt: setLexExt, MOODS: function () { return MOODS; }, USES: function () { return USES; }, norm: norm, toks: toks, normalize: normalize, hexWords: hexWords, hexName: hexName, _slang: SLANG };
})();
