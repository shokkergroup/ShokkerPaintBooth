/* ============================================================================
   SPEC SCULPT - the focused all-looks material path for SPB Easy Mode.

   Owner direction, 2026-07-18: "the APP sculpts their paint scheme for them."
   This module intentionally owns only the guided path. The existing Whole Car
   and By Color flows remain in js/spb-easy-mode.js; the full standalone
   spec-sculpt.html remains the intermediate advanced Spec Lab.

   Owner course correction, 2026-07-18: "more like it was before - just a little
   stripped back." Every real Spec Sculpt preset and Paint Booth material stays
   pickable. We remove competing setup systems, not creative range.
   ============================================================================ */
(function () {
    'use strict';

    var ACCEPTED = /\.(psd|tga|png|jpe?g)$/i;
    var PROTECT_RE = /sponsor|logo|number|numero|decal|contingen|wordmark|\btext\b|brand|\burl\b|www|\.com|\bqr\b/i;
    var GUIDE_RE = /template|wire|guide|read[ _-]?me|instruction|notes?|shadow|mask|reference/i;
    // Keep the complete library searchable without making a tab click lay out
    // several screens of image cards at once. Sixty is still a generous browse
    // page, but stays responsive on the lower-end PCs Easy Mode is for.
    var LOOK_PAGE_SIZE = 60;
    // [2026-08-09 S30] Under this many exact hits, offer the closest-match
    // shelf as well - a one-result answer to "candy red" is a dead end wearing
    // a result's clothes.
    var SEARCH_THIN_RESULTS = 5;
    var MAX_COLOR_TARGETS = 6;
    var RECOVERY_KEY = 'spb.easySpecSculpt.lastPlan.v1';
    var SPECIAL_LOOKS = [
        { kind: 'mode', id: 'zoned', name: 'Smart Materials', category: 'START HERE · AUTO-SCULPT', description: 'Reads the paint and assigns materials by region.', emoji: '&#10024;' },
        { kind: 'mode', id: 'fracture', name: 'FRACTURE', category: 'Signature', description: 'Near-chrome body with a woven paint-traced motif.', emoji: '&#128165;' },
        { kind: 'mode', id: 'candy_depth', name: 'Candy Depth', category: 'Signature', description: 'Deep wet candy with suspended flakes and clearcoat.', emoji: '&#127852;' }
    ];
    // Owner course correction 2026-07-18: keep the original laboratory as a
    // quiet advanced option. It must not crowd the primary three-step path, but
    // experienced painters must still be able to reach all of its controls.
    var SHOW_LEGACY_SPEC_LAB = true;

    var hooks = {};
    var mounted = false;
    var environmentPromise = null;
    var requestSerial = 0;
    var activeController = null;
    var recommendationSerial = 0;
    var recommendationController = null;
    var drawSerial = 0;
    var specProofSerial = 0;
    var currentPaintPoll = null;
    var lookSearchTimer = 0;
    var lastCurrentPaintPath = '';
    var currentPaintSettlingUntil = 0;
    var rememberedLayeredPaintPath = '';
    var state = freshState();

    function freshState() {
        return {
            phase: 'drop',
            progressStep: 'checking',
            status: '',
            error: '',
            errorContext: '',
            retryable: false,
            file: null,
            liveSourceMeta: null,
            handoffPath: '',
            sourcePath: '',
            serverSourcePath: '',
            sourceToken: '',
            filename: '',
            format: '',
            sourceUrl: '',
            specUrl: '',
            resolution: null,
            psdPath: '',
            psdImportData: null,
            protectKeys: [],
            layerSummary: null,
            seedBase: 9101,
            looks: [],
            looksLoaded: false,
            looksError: false,
            libraryKind: 'recommended',
            libraryQuery: '',
            libraryCategory: '',
            libraryLimit: LOOK_PAGE_SIZE,
            libraryScrollTop: 0,
            libraryAnchorOffset: null,
            advanceToSaveAfterPreview: false,
            focusReturnId: '',
            focusReturnLookKey: '',
            paintProfile: null,
            palette: [],
            recommendedLookKeys: [],
            recommendationLoading: false,
            recommendationKey: '',
            selectedLook: null,
            previousLooks: {},
            recoveredPlan: false,
            materialScale: 1,
            materialImpact: 'balanced',
            colorTargets: [],
            activeColorId: '',
            pickingColor: false,
            baseColorQuery: '',
            config: {},
            cars: [],
            iracingId: '',
            car: '',
            carQuery: '',
            inferredUseCustomNumber: null,
            exportOpen: false,
            saved: null,
            materialSummary: '',
            materialMetrics: {},
            showSpecMap: false,
            showBigResult: false,
            previewCache: {},
            previewCacheOrder: []
        };
    }

    function $(id) { return document.getElementById(id); }
    function esc(value) {
        return String(value == null ? '' : value).replace(/[&<>"']/g, function (ch) {
            return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[ch];
        });
    }
    function api(path) {
        try {
            if (typeof getServerBase === 'function') return (getServerBase() || '') + path;
        } catch (e) {}
        return path;
    }
    // Use the exact Paint Booth swatch contract everywhere Easy Spec Sculpt
    // asks somebody to choose a material: real engine paint on the left and
    // the matching iRacing spec response on the right. Never invent a texture
    // from the finish name or its representative color.
    function catalogSwatch(type, id) {
        var row = null;
        try {
            if (type === 'base' && typeof BASES_BY_ID !== 'undefined') row = BASES_BY_ID[id];
            else if (type === 'monolithic' && typeof MONOLITHICS_BY_ID !== 'undefined') row = MONOLITHICS_BY_ID[id];
        } catch (error) {}
        return row && /^#[0-9a-f]{6}$/i.test(row.swatch || '') ? row.swatch : '#888888';
    }
    function realSwatchUrl(type, id, swatch, size) {
        var edge = Math.max(32, Number(size) || 48);
        var color = /^#[0-9a-f]{6}$/i.test(swatch || '') ? String(swatch).slice(1).toLowerCase() : '888888';
        try {
            if (typeof window.getSwatchUrl === 'function') {
                var canonical = window.getSwatchUrl(id, color, true, edge);
                // Duplicate IDs can exist in both authored registries. Keep the
                // card on the explicit registry requested by this library.
                if (canonical && canonical.indexOf('/api/swatch/' + type + '/') !== -1) return canonical;
            }
        } catch (error) {}
        var fp = window._SHOKKER_SWATCH_FP || {};
        var version = fp[type + ':' + id] || window._SHOKKER_SWATCH_V || 'easy-sculpt-real-split';
        return api('/api/swatch/' + type + '/' + encodeURIComponent(id) +
            '?color=' + color + '&size=' + edge + '&mode=split&prefer=live&v=' + encodeURIComponent(version));
    }
    function validId(value) { return /^\d{4,7}$/.test(String(value || '').trim()); }
    function friendlyCarName(value) {
        var key = String(value || '').trim();
        if (!key) return '';
        var lower = key.toLowerCase();
        var exact = {
            'acuraarx06gtp': 'Acura ARX-06 GTP',
            'acuransxevo22gt3': 'Acura NSX Evo 22 GT3',
            'amvantagegt4': 'Aston Martin Vantage GT4',
            'astonmartin dbr9': 'Aston Martin DBR9',
            'audir18': 'Audi R18',
            'audir8lmsevo2gt3': 'Audi R8 LMS Evo II GT3',
            'audirs3lms': 'Audi RS3 LMS',
            'bmwm2csr': 'BMW M2 CS Racing',
            'bmwm4gt3': 'BMW M4 GT3',
            'bmwm4gt4': 'BMW M4 GT4',
            'bmwz4gt3': 'BMW Z4 GT3',
            'c6r': 'Chevrolet Corvette C6.R',
            'c7vettedp': 'Chevrolet Corvette C7 DP',
            'c8rvettegte': 'Chevrolet Corvette C8.R GTE',
            'cadillacctsvr': 'Cadillac CTS-V.R',
            'cadillacvseriesrgtp': 'Cadillac V-Series.R GTP',
            'chevyvettez06rgt3': 'Chevrolet Corvette Z06 GT3.R',
            'mclarenmp4': 'McLaren MP4-12C GT3',
            'mclarenmp430': 'McLaren MP4-30',
            'dallaradw12': 'Dallara DW12',
            'dallaraf3': 'Dallara F3',
            'dallarair01': 'Dallara iR-01',
            'dallarair18': 'Dallara IR18',
            'dallarap217': 'Dallara P217',
            'dirtlatemodel 350': 'Dirt Late Model 350',
            'dirtlatemodel 358': 'Dirt Late Model 358',
            'dirtlatemodel 438': 'Dirt Late Model 438',
            'dirtmicrosprint nonwinged': 'Dirt Micro Sprint - Non-Winged',
            'dirtmicrosprint nonwinged outlaw': 'Dirt Micro Sprint - Non-Winged Outlaw',
            'dirtmicrosprint winged': 'Dirt Micro Sprint - Winged',
            'dirtmicrosprint winged outlaw': 'Dirt Micro Sprint - Winged Outlaw',
            'dirtmidget': 'Dirt Midget',
            'dirtministock': 'Dirt Mini Stock',
            'dirtmodified 358': 'Dirt Modified 358',
            'dirtmodified bigblock': 'Dirt Modified - Big Block',
            'dirtsprint nonwinged 360': 'Dirt Sprint - Non-Winged 360',
            'dirtsprint nonwinged 410': 'Dirt Sprint - Non-Winged 410',
            'dirtsprint winged 305': 'Dirt Sprint - Winged 305',
            'dirtsprint winged 360': 'Dirt Sprint - Winged 360',
            'dirtsprint winged 410': 'Dirt Sprint - Winged 410',
            'dirtstreetstock': 'Dirt Street Stock',
            'dirtumpmod': 'Dirt UMP Modified',
            'latemodel': 'Late Model',
            'latemodel2023': 'Late Model Stock 2023',
            'superlatemodel': 'Super Late Model',
            'streetstock': 'Street Stock',
            'formulair04': 'Formula iR-04',
            'formulamazda': 'Formula Mazda',
            'formularenault20': 'Formula Renault 2.0',
            'formularenault35': 'Formula Renault 3.5',
            'formulavee': 'Formula Vee',
            'fordfiestarswrc': 'Ford Fiesta RS WRC',
            'fordv8sc': 'Ford V8 Supercar',
            'hondacivictyper': 'Honda Civic Type R',
            'indypropm18': 'Indy Pro 2000 PM-18',
            'lamborghinievogt3': 'Lamborghini Huracan GT3 EVO',
            'mx5 roadster': 'Mazda MX-5 Roadster',
            'nissangtpzxt': 'Nissan GTP ZX-T',
            'porsche991rsr': 'Porsche 911 RSR',
            'radical sr8': 'Radical SR8',
            'raygr22': 'Ray GR22',
            'silvercrown': 'Silver Crown',
            'skmodified': 'SK Modified',
            'skmodified tour': 'SK Modified - Tour',
            'specracer': 'Spec Racer Ford',
            'stockcars buicklesabre87': 'Stock Car / Buick LeSabre 1987',
            'stockcars chevymontecarlo03': 'Stock Car / Chevrolet Monte Carlo 2003',
            'stockcars chevymontecarlo87': 'Stock Car / Chevrolet Monte Carlo 1987',
            'stockcars fordthunderbird87': 'Stock Car / Ford Thunderbird 1987',
            'stockcars pontiacgrandprix87': 'Stock Car / Pontiac Grand Prix 1987',
            'stockcars2 arcachevy25': 'ARCA Chevrolet 2025',
            'stockcars2 arcaford25': 'ARCA Ford 2025',
            'stockcars2 arcatoyota25': 'ARCA Toyota 2025',
            'supercars fordmustanggen3': 'Supercars / Ford Mustang Gen 3',
            'superformulalights324': 'Super Formula Lights - Dallara 324',
            'superformulasf23 honda': 'Super Formula SF23 - Honda',
            'superformulasf23 toyota': 'Super Formula SF23 - Toyota'
        };
        if (exact[lower]) return exact[lower];

        var prefix = '';
        var families = [
            ['stockcars2 ', 'Stock Car / '], ['stockcars ', 'Stock Car / '],
            ['stockcarbrasil ', 'Stock Car Brasil / '], ['v8supercars ', 'V8 Supercars / '],
            ['supercars ', 'Supercars / '], ['protrucks ', 'Off-Road Truck / '],
            ['trucks ', 'Truck / '], ['legends ', 'Legends / ']
        ];
        families.some(function (entry) {
            if (lower.indexOf(entry[0]) !== 0) return false;
            prefix = entry[1];
            lower = lower.slice(entry[0].length);
            return true;
        });

        var makes = [
            ['mercedesamg', 'Mercedes-AMG '], ['astonmartin', 'Aston Martin '],
            ['lamborghini', 'Lamborghini '], ['cadillac', 'Cadillac '],
            ['chevy', 'Chevrolet '], ['hyundai', 'Hyundai '], ['mclaren', 'McLaren '],
            ['porsche', 'Porsche '], ['ferrari', 'Ferrari '], ['renault', 'Renault '],
            ['subaru', 'Subaru '], ['toyota', 'Toyota '], ['nissan', 'Nissan '],
            ['dallara', 'Dallara '], ['acura', 'Acura '], ['audi', 'Audi '],
            ['honda', 'Honda '], ['ford', 'Ford '], ['bmw', 'BMW '], ['kia', 'Kia '],
            ['lotus', 'Lotus '], ['ruf', 'RUF '], ['vw', 'Volkswagen ']
        ];
        makes.some(function (entry) {
            if (lower.indexOf(entry[0]) !== 0) return false;
            prefix += entry[1];
            lower = lower.slice(entry[0].length);
            return true;
        });

        // [2026-08-08 E43] The two generic digit splits below are what turn
        // "audir8gt3" into "Audi R 8 GT3". They have to stay (they are what
        // makes "silverado2019" readable), so anything that must NOT be split
        // is pulled out first and parked behind a placeholder.
        //
        // MEASURED over the 181 car folders actually installed here: 29 came
        // out mangled before this - 27 with a designation broken by a space
        // (R 8, M 4, M 8, Gr 86, F 150, USF 17) and 3 with a year welded onto
        // the model (Camarozl 12022).
        //
        // NOTE what is deliberately NOT in this list: gen4, pro2, pro4. iRacing
        // itself writes those as "Gen 4 Cup" and "Pro 4 Truck", so the split is
        // correct there and protecting them would introduce the bug.
        var HOLD = ['usf2000', 'fr500s', 'arx06', '720s', 'gr86', 'f150', 'p217',
                    'dw12', 'ir01', 'ir18', 'sf23', 'usf17', 'zl1', 'z06', 'r18',
                    'cn7', '911', '488', '296', 'mx5', 'm2', 'm4', 'm8', 'z4',
                    'c6', 'c7', 'c8', 'r8'];
        var HOLD_SHOWN = { 'mx5': 'MX-5', 'ir01': 'iR-01', 'ir18': 'IR18', '720s': '720S' };
        var held = [];
        var HOLD_RE = new RegExp('(' + HOLD.join('|') + ')(?!\\d)', 'g');
        function holdOne(m) {
            held.push(HOLD_SHOWN[m] || m.toUpperCase());
            return ' \u0001' + (held.length - 1) + '\u0001 ';
        }
        lower = lower
            .replace(/(nonwinged|bigblock|streetstock|ministock|latemodel|microsprint)/g, ' $1 ')
            .replace(/(lmdh|gtp|gt4|gt3|gte|gto|lms|wrc|grc|sti|tdi|awd|rwd|cn7|csr|cspec|dp)(?=$|\s)/g, ' $1 ')
            // Park designations, split years, park again. BOTH passes are
            // needed and neither alone is enough (measured):
            //   usf2000usf17  - the year rule eats the 2000 out of usf2000,
            //                   so usf2000 must be parked BEFORE it runs
            //   camarozl12022 - zl1 is followed by a digit, so (?!\d) blocks
            //                   it until the year has been split OFF
            .replace(HOLD_RE, holdOne)
            .replace(/([a-z0-9])((?:19|20)\d{2})(?![0-9])/g, '$1 $2')
            .replace(HOLD_RE, holdOne)
            .replace(/([a-z])(\d)/g, '$1 $2')
            .replace(/(\d)([a-z])/g, '$1 $2')
            .replace(/\bgt\s+([34])\b/g, 'gt$1')
            .replace(/\s+/g, ' ')
            .trim();
        lower = lower.replace(/\u0001\s*(\d+)\s*\u0001/g, function (_m, i) {
            return held[Number(i)] || '';
        });
        var special = {
            'amg': 'AMG', 'arca': 'ARCA', 'arx': 'ARX', 'bmw': 'BMW', 'cn': 'CN',
            'csr': 'CSR', 'cspec': 'C-Spec', 'dbr': 'DBR', 'dp': 'DP', 'evo': 'Evo',
            'gt': 'GT', 'gtp': 'GTP', 'gt3': 'GT3', 'gt4': 'GT4', 'gte': 'GTE',
            'gto': 'GTO', 'grc': 'GRC', 'ir': 'iR', 'lmdh': 'LMDh', 'lms': 'LMS',
            'mp': 'MP', 'nsx': 'NSX', 'rwd': 'RWD', 'awd': 'AWD', 'sf': 'SF',
            'rt': 'RT',
            'srx': 'SRX', 'sti': 'STI', 'tdi': 'TDI', 'ump': 'UMP', 'usf': 'USF',
            'v8': 'V8', 'wrc': 'WRC', 'bigblock': 'Big Block', 'latemodel': 'Late Model',
            'microsprint': 'Micro Sprint', 'ministock': 'Mini Stock',
            'nonwinged': 'Non-Winged', 'streetstock': 'Street Stock'
        };
        var words = lower.split(' ').filter(Boolean).map(function (word) {
            // A parked designation comes back already cased (R8, ZL1, MX-5);
            // title-casing it again would give "R8" -> "R8" but "MX-5" -> "MX-5"
            // only by luck, so leave anything already carrying a capital alone.
            if (/[A-Z]/.test(word)) return word;
            return special[word] || (word.charAt(0).toUpperCase() + word.slice(1));
        });
        return (prefix + words.join(' ')).trim() || key;
    }
    function isPsd(file) { return /\.psd$/i.test((file && file.name) || state.filename || ''); }
    function borrowDeploymentIdentity() {
        if (!state.iracingId) {
            var mainId = $('iracingId');
            var candidateId = mainId && String(mainId.value || '').trim();
            if (validId(candidateId)) state.iracingId = candidateId;
        }
        if (!state.car) {
            // [GAUNTLET H1 2026-08-20] MEASURED: with outputDir pointing at
            // ...\paint\superlatemodel, Easy Mode's WHERE IT GOES read "Super
            // Late Model" while THIS screen read "Off-Road Truck / Pro 2 Lite -
            // Folder protrucks pro2lite". Same app, same flow, two different
            // cars - and this screen says "paint + spec auto-route together", so
            // a save here would have landed in the wrong car's folder.
            //
            // Cause: the car came from Pro's #deployCarSelect while Easy Mode
            // derives it from #outputDir, which is what actually gets written.
            // Prefer the real output folder; keep the old source as fallback.
            var fromOut = _carNameFromOutputDir();
            if (fromOut) state.car = fromOut;
        }
        if (!state.car) {
            var mainCar = $('deployCarSelect');
            var candidateCar = mainCar && String(mainCar.value || '').trim();
            if (candidateCar && (!state.cars.length || state.cars.some(function (car) { return car.name === candidateCar; }))) state.car = candidateCar;
        }
    }

    // Map the live output directory onto one of state.cars' names. A car folder
    // can be nested ("protrucks/pro2lite") and the catalog stores that name
    // space-joined ("protrucks pro2lite"), so compare the tail after /paint/
    // with separators normalised.
    function _carNameFromOutputDir() {
        try {
            var el = $('outputDir');
            var dir = el && String(el.value || '').trim();
            if (!dir || !state.cars || !state.cars.length) return '';
            var norm = dir.split('\\').join('/').replace(/\/+$/, '').toLowerCase();
            var at = norm.lastIndexOf('/paint/');
            var tail = (at === -1) ? (norm.split('/').pop() || '') : norm.slice(at + 7);
            var joined = tail.split('/').filter(Boolean).join(' ');
            if (!joined) return '';
            for (var i = 0; i < state.cars.length; i++) {
                if (String(state.cars[i].name || '').trim().toLowerCase() === joined) return state.cars[i].name;
            }
            return '';
        } catch (e) { return ''; }
    }
    function usefulCarFolder(car) {
        var name = String(car && car.name || '').trim();
        if (!name || /[\\/]/.test(name)) return false;
        return name.toLowerCase() !== 'cars' && !/(?:^|[ _-])(copy|backup|old)(?:$|[ _-])/i.test(name);
    }
    function borrowDeploymentFromSource(path) {
        path = String(path || '').trim();
        if (!path) return;
        var parts = path.replace(/\\/g, '/').split('/').filter(Boolean);
        var filename = parts[parts.length - 1] || '';
        var idMatch = filename.match(/^car_(num_)?(\d{4,7})(?:\.[^.]+)?$/i);
        if (idMatch) {
            // A conventional iRacing filename is stronger evidence than a
            // hidden/stale global checkbox. Preserve its number mode so Easy
            // cannot install a correct paint under the wrong car[_num_] name.
            state.inferredUseCustomNumber = !!idMatch[1];
        }
        if (idMatch) {
            // An exact iRacing car/car_num filename is stronger than a stale
            // destination remembered from the previous paint. Auto-route from
            // the file, while the plain-English SWITCH CAR control remains
            // available for an intentional override.
            state.iracingId = idMatch[2];
        }
        if (parts.length > 1) {
            var parent = parts[parts.length - 2].toLowerCase();
            var matchedCar = state.cars.filter(function (car) {
                return String(car.name || '').toLowerCase() === parent;
            })[0];
            if (matchedCar) state.car = matchedCar.name;
        }
    }
    function currentPaintPath() {
        var value = '';
        // The main canvas owns the canonical source getter. It returns the real
        // PSD path when layers are live and the flat TGA/PNG/JPG path otherwise.
        try {
            if (typeof window.getCurrentSourcePaintFile === 'function') value = String(window.getCurrentSourcePaintFile() || '').trim();
        } catch (e) {}
        if (!value) {
            try { value = typeof window._psdPath === 'string' ? window._psdPath.trim() : ''; } catch (e) {}
        }
        if (!value) {
            try {
                var sourceField = $('paintFile');
                var candidate = sourceField && String(sourceField.value || '').trim();
                if (candidate && ACCEPTED.test(candidate)) value = candidate;
            } catch (e) {}
        }
        return value && ACCEPTED.test(value) ? value : '';
    }
    function currentPaintStillLoading() {
        try {
            if (window._psdLayersLoaded === true) return false;
            if (window._spbPsdImportInFlight === true) return true;
            return Date.now() < currentPaintSettlingUntil;
        } catch (e) { return false; }
    }
    function currentPaintAvailabilityKey() {
        return currentPaintPath() + '|' + (currentPaintStillLoading() ? 'loading' : 'ready');
    }
    function basename(path) { return String(path || '').split(/[/\\]/).pop() || 'paint'; }
    function abortActive() {
        if (activeController) {
            try { activeController.abort(); } catch (e) {}
            activeController = null;
        }
    }
    function abortRecommendations() {
        recommendationSerial += 1;
        if (recommendationController) {
            try { recommendationController.abort(); } catch (e) {}
            recommendationController = null;
        }
        state.recommendationLoading = false;
    }
    function isConnectionError(error) {
        var message = String((error && error.message) || error || '').toLowerCase();
        return (error && error.name === 'TypeError') || /failed to fetch|network|connection|load failed/.test(message);
    }
    function isRetryableError(error) {
        var status = Number(error && error.httpStatus) || 0;
        var message = String((error && error.message) || error || '').toLowerCase();
        return isConnectionError(error) || status === 408 || status === 425 || status === 429 || status >= 500 ||
            /temporar(?:y|ily)|timed? out|still finishing|server busy|try again/.test(message);
    }
    function friendlyError(error, fallback) {
        if (isConnectionError(error)) return 'Shokker\'s local server is not responding. Your paint is still here — choose Restart Server from the SPB tray and try again.';
        return (error && error.message) || fallback;
    }
    function httpFallback(response, fallback) {
        var status = Number(response && response.status) || 0;
        if (status === 413) return 'That paint is larger than the 256 MB Spec Sculpt upload limit.';
        if (status === 404) return 'This Spec Sculpt feature is missing from the running server. Restart Shokker Paint Booth and try again.';
        if (status === 429) return 'Shokker is still finishing another material. Wait a moment and try again.';
        if (status >= 500) return 'Shokker\'s material engine hit a temporary problem. Your paint is still here - try again.';
        return (fallback || 'That request did not finish.') + (status ? ' (server error ' + status + ')' : '');
    }
    function responseError(response, message, fallback) {
        var error = new Error(message || httpFallback(response, fallback));
        error.httpStatus = Number(response && response.status) || 0;
        return error;
    }
    async function readJsonResponse(response, fallback) {
        // Flask normally returns JSON, but a proxy, upload ceiling, or stale
        // packaged server can answer with HTML. Never show a novice an
        // "Unexpected token <" parser error for a recoverable problem.
        var raw = await response.text();
        if (!raw) {
            if (!response.ok) throw responseError(response, '', fallback);
            return {};
        }
        try { return JSON.parse(raw); }
        catch (error) { throw responseError(response, '', fallback); }
    }
    function hashSeed(file) {
        var text = String((file && file.name) || '') + ':' + String((file && file.size) || 0) + ':' + String((file && file.lastModified) || 0);
        var hash = 2166136261;
        for (var i = 0; i < text.length; i++) {
            hash ^= text.charCodeAt(i);
            hash = Math.imul(hash, 16777619);
        }
        return (hash >>> 0) || 9101;
    }

    function canonicalRecoverySource(value) {
        // A PSD imported by the main booth is rasterized to a same-stem TGA.
        // Main-canvas fingerprints legitimately change when a PSD is rasterized
        // again. The normalized local path still prevents cross-paint restores;
        // ignore the derivative extension and transient fingerprint together.
        return String(value || '').replace(/^(live:.*)\.(psd|tga|png|jpe?g):[^:]+$/i, '$1');
    }

    function sourceIdentity() {
        if (state.liveSourceMeta && state.liveSourceMeta.identity) return canonicalRecoverySource(state.liveSourceMeta.identity);
        var exactPath = state.sourcePath || state.handoffPath || (state.file && state.file.path) || '';
        if (exactPath && /[\\/]/.test(exactPath)) return 'path:' + String(exactPath).replace(/\\/g, '/').toLowerCase();
        if (state.file) return ['file', String(state.filename || '').toLowerCase(), Number(state.file.size) || 0, Number(state.file.lastModified) || 0].join(':');
        return '';
    }

    function recoveryPathKey() {
        return String(state.handoffPath || state.sourcePath || state.filename || '')
            .replace(/\\/g, '/').toLowerCase()
            .replace(/\.(psd|tga|png|jpe?g)$/i, '');
    }

    function clearRecoveryPlan() {
        try { window.sessionStorage.removeItem(RECOVERY_KEY); } catch (error) {}
        try { window.localStorage.removeItem(RECOVERY_KEY); } catch (error) {}
    }

    function persistRecoveryPlan() {
        if (!state.selectedLook || !sourceIdentity()) return;
        var payload = {
            version: 1,
            source: sourceIdentity(),
            sourcePathKey: recoveryPathKey(),
            // [2026-08-09 S11] sourcePathKey has its extension stripped so a
            // PSD and its rasterized TGA still match, which means it cannot
            // name a file to re-open. Keep the real one for that, and for that
            // only - restore matching still goes through sourcePathKey.
            exactPath: String(state.handoffPath || state.sourcePath || ''),
            exactName: String(state.filename || '').replace(/^.*[\\/]/, ''),
            iracingId: state.iracingId,
            car: state.car,
            useCustomNumber: liveUseCustomNumber(),
            selectedLookKey: lookKey(state.selectedLook),
            materialScale: state.materialScale,
            materialImpact: state.materialImpact,
            colorTargets: state.colorTargets.map(function (target) {
                return {
                    id: target.id,
                    color: target.color,
                    tolerance: target.tolerance,
                    lookKey: lookKey(target.look),
                    materialScale: target.materialScale,
                    paintDecision: target.paintDecision || '',
                    replacementColor: target.replacementColor || '',
                    replacementMode: target.replacementMode || 'solid',
                    replacementBaseId: target.replacementBaseId || ''
                };
            }),
            activeColorId: state.activeColorId,
            libraryKind: state.libraryKind,
            libraryQuery: state.libraryQuery,
            libraryCategory: state.libraryCategory,
            libraryLimit: state.libraryLimit,
            libraryScrollTop: state.libraryScrollTop
        };
        var serialized = JSON.stringify(payload);
        try { window.sessionStorage.setItem(RECOVERY_KEY, serialized); } catch (error) {}
        // A path-backed paint can be reconstructed after the app itself closes,
        // so keep the tiny plan in durable browser storage too. Source identity
        // prevents it from ever crossing onto a different paint.
        try { window.localStorage.setItem(RECOVERY_KEY, serialized); } catch (error) {}
    }

    function restoreRecoveryPlan() {
        var payload = null;
        var raw = '';
        try { raw = window.sessionStorage.getItem(RECOVERY_KEY) || ''; } catch (error) {}
        if (!raw) try { raw = window.localStorage.getItem(RECOVERY_KEY) || ''; } catch (error) {}
        try { payload = JSON.parse(raw || 'null'); } catch (error) { payload = null; }
        if (!payload || payload.version !== 1) return false;
        var currentSource = canonicalRecoverySource(sourceIdentity());
        var savedSource = canonicalRecoverySource(payload.source);
        var sameSource = savedSource === currentSource;
        // The extensionless fallback exists only for path-backed PSD → TGA
        // rasterization of the same local paint. Never use a bare filename to
        // restore a plan onto a different browser upload named car_num_ID.tga.
        var pathFallbackSafe = /^(path:|live:)/.test(savedSource) && /^(path:|live:)/.test(currentSource) && /[\\/]/.test(recoveryPathKey());
        if (!sameSource && pathFallbackSafe && payload.sourcePathKey) sameSource = payload.sourcePathKey === recoveryPathKey();
        if (!sameSource) return false;
        var selected = findLook(payload.selectedLookKey);
        if (!selected) return false;
        state.selectedLook = selected;
        if (validId(payload.iracingId)) state.iracingId = String(payload.iracingId);
        if (state.cars.some(function (car) { return car.name === payload.car; })) state.car = payload.car;
        if (typeof payload.useCustomNumber === 'boolean') state.inferredUseCustomNumber = payload.useCustomNumber;
        state.materialScale = Math.max(0.25, Math.min(1, Number(payload.materialScale) || 1));
        state.materialImpact = ['subtle', 'balanced', 'bold'].indexOf(payload.materialImpact) !== -1 ? payload.materialImpact : 'balanced';
        state.colorTargets = (Array.isArray(payload.colorTargets) ? payload.colorTargets : []).slice(0, MAX_COLOR_TARGETS).map(function (saved, index) {
            var color = (Array.isArray(saved.color) ? saved.color : []).slice(0, 3).map(function (value) {
                return Math.max(0, Math.min(255, Number(value) || 0));
            });
            var look = findLook(saved.lookKey);
            if (color.length !== 3 || !look) return null;
            var tolerance = [18, 30, 52].indexOf(Number(saved.tolerance)) !== -1 ? Number(saved.tolerance) : 30;
            return {
                id: String(saved.id || ('restored-color-' + index)),
                color: color,
                hex: rgbHex(color),
                tolerance: tolerance,
                look: look,
                materialScale: Math.max(0.25, Math.min(1, Number(saved.materialScale) || state.materialScale)),
                paintDecision: saved.paintDecision === 'change' || saved.paintDecision === 'keep'
                    ? saved.paintDecision
                    : (saved.replacementColor ? 'change' : 'keep'),
                replacementColor: /^#[0-9a-f]{6}$/i.test(saved.replacementColor || '') ? saved.replacementColor : '',
                replacementMode: saved.replacementMode === 'base' ? 'base' : 'solid',
                replacementBaseId: String(saved.replacementBaseId || ''),
                coverage: null
            };
        }).filter(Boolean);
        state.activeColorId = state.colorTargets.some(function (target) { return target.id === payload.activeColorId; }) ? payload.activeColorId : '';
        state.libraryKind = ['recommended', 'all', 'spec', 'catalog'].indexOf(payload.libraryKind) !== -1 ? payload.libraryKind : 'recommended';
        state.libraryQuery = String(payload.libraryQuery || '').slice(0, 100);
        state.libraryCategory = String(payload.libraryCategory || '').slice(0, 100);
        state.libraryLimit = Math.max(LOOK_PAGE_SIZE, Math.min(LOOK_PAGE_SIZE * 24, Number(payload.libraryLimit) || LOOK_PAGE_SIZE));
        // A restored plan should reopen at its decisions and install action,
        // not halfway down the look library where those controls disappear.
        // Live look changes still preserve the rail position via
        // captureLibraryView(); only a reload/app restart returns to the top.
        state.libraryScrollTop = 0;
        state.focusReturnLookKey = lookKey(selected);
        state.libraryAnchorOffset = null;
        state.previousLooks = {};
        state.recoveredPlan = true;
        refreshRecommendations();
        return true;
    }

    function materialPlanSignature() {
        return [
            lookKey(state.selectedLook),
            Number(state.materialScale || 1).toFixed(2),
            state.materialImpact,
            state.colorTargets.map(function (target) {
                return [target.hex, target.tolerance, lookKey(target.look), Number(target.materialScale || 1).toFixed(2), target.replacementColor || 'keep'].join(':');
            }).join('|')
        ].join('::');
    }

    function seedForMaterialSignature(text) {
        // A named plan must be repeatable. In the old flow, pressing Back changed
        // the global variation number and quietly rebuilt a different map. Hash
        // the actual material choices instead so the same plan always returns to
        // the exact same finish while different looks still get distinct seeds.
        var guidance = window.spbEasySculptGuidance;
        if (guidance && typeof guidance.stableSeed === 'function') {
            return guidance.stableSeed(state.seedBase, text);
        }
        var hash = state.seedBase >>> 0;
        for (var i = 0; i < text.length; i++) {
            hash ^= text.charCodeAt(i);
            hash = Math.imul(hash, 16777619);
        }
        return (hash >>> 0) || state.seedBase || 9101;
    }

    function materialPlanSeed() {
        // The whole-paint texture is an independent material layer. Editing a
        // color must never quietly re-seed or reshuffle the base underneath it.
        return seedForMaterialSignature([
            'whole',
            lookKey(state.selectedLook),
            Number(state.materialScale || 1).toFixed(2)
        ].join('::'));
    }

    function recommendationPlanSeed(look) {
        var target = activeColorTarget();
        if (target) return colorMaterialSeed(target, look);
        return seedForMaterialSignature([
            'whole',
            lookKey(look),
            Number(state.materialScale || 1).toFixed(2)
        ].join('::'));
    }

    function colorMaterialSeed(target, look) {
        return seedForMaterialSignature([
            'color',
            target && target.hex,
            target && target.tolerance,
            lookKey(look || (target && target.look)),
            Number((target && target.materialScale) || 1).toFixed(2)
        ].join('::'));
    }

    function colorLayerPlan(target, look) {
        look = look || (target && target.look);
        if (!target || !look) return null;
        return {
            slot_id: target.id,
            color: target.color,
            tolerance: target.tolerance,
            kind: look.kind,
            look_id: look.id,
            catalog_type: look.kind === 'catalog' ? (look.swatchType || '') : '',
            seed: colorMaterialSeed(target, look),
            material_scale: target.materialScale,
            replacement_color: target.replacementColor ? hexRgb(target.replacementColor) : null
        };
    }

    function recommendationContextSignature() {
        var target = activeColorTarget();
        if (!target) return ['whole', Number(state.materialScale || 1).toFixed(2), state.materialImpact].join(':');
        return [
            'color', target.id, target.hex, target.tolerance, Number(target.materialScale || 1).toFixed(2),
            'base', lookKey(state.selectedLook), Number(state.materialScale || 1).toFixed(2), state.materialImpact,
            state.colorTargets.filter(function (item) { return item.id !== target.id && item.look; }).map(function (item) {
                return [item.id, item.hex, item.tolerance, lookKey(item.look), Number(item.materialScale || 1).toFixed(2)].join(':');
            }).join('|')
        ].join('::');
    }

    function recommendationColorPlan(look) {
        var target = activeColorTarget();
        if (!target || !state.selectedLook) return null;
        return {
            easy_base: {
                kind: state.selectedLook.kind,
                look_id: state.selectedLook.id,
                catalog_type: state.selectedLook.kind === 'catalog' ? (state.selectedLook.swatchType || '') : '',
                seed: materialPlanSeed(),
                material_scale: state.materialScale
            },
            easy_color_layers: state.colorTargets.map(function (item) {
                return colorLayerPlan(item, item.id === target.id ? look : item.look);
            }).filter(Boolean)
        };
    }

    function previewCacheKey() {
        return [state.filename, state.seedBase, materialPlanSignature(), state.colorTargets.map(function (target) { return target.id; }).join('|')].join('::');
    }

    function rememberPreview(key, entry) {
        if (!key || !entry || !entry.specUrl) return;
        state.previewCache[key] = entry;
        state.previewCacheOrder = state.previewCacheOrder.filter(function (item) { return item !== key; });
        state.previewCacheOrder.push(key);
        while (state.previewCacheOrder.length > 12) {
            delete state.previewCache[state.previewCacheOrder.shift()];
        }
    }

    function applyColorReport(rows) {
        (rows || []).forEach(function (row) {
            var target = state.colorTargets.filter(function (item) { return item.id === row.slot_id; })[0];
            if (!target) return;
            target.coverage = Number(row.coverage_pct) || 0;
            target.materialMeans = Array.isArray(row.material_means) && row.material_means.length >= 3
                ? row.material_means.slice(0, 3).map(Number) : null;
            target.materialDeviations = Array.isArray(row.material_deviations) && row.material_deviations.length >= 3
                ? row.material_deviations.slice(0, 3).map(Number) : null;
        });
    }

    function ensureStage() {
        var stage = $('spbEasyStage');
        if (stage && !$('spbEasySculptReplaceFile')) {
            var replaceInput = document.createElement('input');
            replaceInput.id = 'spbEasySculptReplaceFile';
            replaceInput.type = 'file';
            replaceInput.accept = '.psd,.tga,.png,.jpg,.jpeg,image/png,image/jpeg';
            replaceInput.setAttribute('aria-label', 'Choose a replacement 2048 iRacing paint file');
            replaceInput.hidden = true;
            replaceInput.addEventListener('change', function () {
                var file = replaceInput.files && replaceInput.files[0];
                replaceInput.value = '';
                if (!file || !ACCEPTED.test(file.name || '')) return;
                // Cancel keeps the current plan. Only a confirmed, supported
                // replacement paint deliberately clears recovery and starts over.
                reset();
                acceptFile(file);
            });
            stage.appendChild(replaceInput);
        }
        if (!stage || $('spbEasySculptStage')) return;
        var host = document.createElement('div');
        host.id = 'spbEasySculptStage';
        host.hidden = true;
        stage.appendChild(host);
    }

    function mount(options) {
        hooks = options || hooks || {};
        mounted = true;
        document.body.classList.add('spb-easy-sculpt-on');
        ensureStage();
        var stage = $('spbEasyStage');
        if (stage) stage.classList.add('spb-easy-sculpt-active');
        var host = $('spbEasySculptStage');
        if (host) host.hidden = false;
        document.addEventListener('keydown', handleEasySculptKeydown);
        borrowDeploymentIdentity();
        try {
            var rememberedPaint = String(localStorage.getItem('spb_last_paint_file') || '');
            rememberedLayeredPaintPath = /\.psd$/i.test(rememberedPaint) ? rememberedPaint : '';
            currentPaintSettlingUntil = rememberedLayeredPaintPath ? Date.now() + 5000 : 0;
        } catch (e) { rememberedLayeredPaintPath = ''; currentPaintSettlingUntil = 0; }
        lastCurrentPaintPath = currentPaintAvailabilityKey();
        if (!currentPaintPoll) currentPaintPoll = window.setInterval(function () {
            if (!mounted || (state.phase !== 'drop' && !(state.phase === 'error' && !state.sourceUrl))) return;
            var nextPath = currentPaintAvailabilityKey();
            if (nextPath !== lastCurrentPaintPath) {
                lastCurrentPaintPath = nextPath;
                render();
            }
        }, 800);
        loadEnvironment();
        render();
        return true;
    }

    function unmount() {
        mounted = false;
        document.body.classList.remove('spb-easy-sculpt-on');
        document.removeEventListener('keydown', handleEasySculptKeydown);
        if (currentPaintPoll) window.clearInterval(currentPaintPoll);
        currentPaintPoll = null;
        if (lookSearchTimer) window.clearTimeout(lookSearchTimer);
        lookSearchTimer = 0;
        abortActive();
        abortRecommendations();
        var stage = $('spbEasyStage');
        if (stage) stage.classList.remove('spb-easy-sculpt-active');
        var host = $('spbEasySculptStage');
        if (host) host.hidden = true;
    }

    function handleEasySculptKeydown(event) {
        if (!mounted || event.key !== 'Escape') return;
        if (state.showSpecMap) {
            event.preventDefault();
            state.showSpecMap = false;
            renderStage();
            var mapButton = $('spbEasySculptMapToggle');
            if (mapButton) mapButton.focus();
            return;
        }
        if (state.showBigResult) {
            event.preventDefault();
            state.showBigResult = false;
            renderStage();
            var bigButton = $('spbEasySculptBigToggle');
            if (bigButton) bigButton.focus();
            return;
        }
        if (state.exportOpen && validId(state.iracingId) && state.cars.some(function (car) { return car.name === state.car; })) {
            event.preventDefault();
            state.exportOpen = false;
            renderRail();
            var destinationButton = $('spbEasySculptEditTarget');
            if (destinationButton) destinationButton.focus();
            return;
        }
        if (!state.pickingColor) return;
        event.preventDefault();
        state.pickingColor = false;
        render();
        window.requestAnimationFrame(function () {
            var addColorButton = $('spbEasySculptAddColor');
            if (addColorButton) addColorButton.focus();
        });
    }

    function reset() {
        abortActive();
        abortRecommendations();
        releaseSculptSpecOverride();
        clearRecoveryPlan();
        if (lookSearchTimer) window.clearTimeout(lookSearchTimer);
        lookSearchTimer = 0;
        var env = {
            config: state.config,
            cars: state.cars,
            looks: state.looks,
            looksLoaded: state.looksLoaded,
            iracingId: state.iracingId,
            car: state.car
        };
        state = freshState();
        state.config = env.config;
        state.cars = env.cars;
        state.looks = env.looks;
        state.looks.forEach(function (look) { delete look.paintThumb; delete look.paintThumbContext; });
        state.looksLoaded = env.looksLoaded;
        state.iracingId = env.iracingId;
        state.car = env.car;
        render();
    }

    // [2026-08-08 S1 - owner: "they are not sorted the same way it's sorted in
    // the main part of the app ... one group called PAINT BOOTH SPECIAL with
    // 2,144 looks in it ... This shouldn't be a totally different system."]
    //
    // It was a different system for one reason: the catalog rows arrive without
    // a category, and the two fallbacks below dumped every base into
    // "Paint Booth Base" and every special into "Paint Booth Special". The real
    // taxonomy the main page renders from is already in this page - BASE_GROUPS
    // (18 families) and SPECIAL_GROUPS (61) - so Spec Sculpt now reads the SAME
    // source instead of inventing two buckets.
    //
    // Deliberately NOT memoised until it finds something: this runs during the
    // async environment load, and caching an empty index because the catalog
    // script had not parsed yet would pin the old two-bucket behaviour for the
    // whole session.
    var _lookGroupIndex = null;
    function lookGroupIndex() {
        if (_lookGroupIndex) return _lookGroupIndex;
        var idx = { base: {}, monolithic: {} };
        var found = 0;
        function add(bucket, groups) {
            if (!groups || typeof groups !== 'object') return;
            Object.keys(groups).forEach(function (name) {
                var ids = groups[name];
                if (!Array.isArray(ids)) return;
                ids.forEach(function (id) {
                    if (id && !bucket[id]) { bucket[id] = name; found++; }
                });
            });
        }
        try {
            add(idx.base, (typeof BASE_GROUPS !== 'undefined') ? BASE_GROUPS : window.BASE_GROUPS);
            add(idx.monolithic, (typeof SPECIAL_GROUPS !== 'undefined') ? SPECIAL_GROUPS : window.SPECIAL_GROUPS);
        } catch (e) { /* fall through to the server categories */ }
        if (found) _lookGroupIndex = idx;
        return idx;
    }
    function catalogGroupFor(kind, id) {
        var idx = lookGroupIndex();
        return (idx[kind] && idx[kind][id]) || '';
    }

    function loadEnvironment() {
        if (environmentPromise) return environmentPromise;
        // [2026-08-09 S28] Every one of these swallowed its failure into {},
        // so a catalog that 500s looked exactly like a catalog that is empty -
        // and the library sat on "Loading the complete look library..." for
        // ever. Remember that the catalog specifically FAILED so the rail can
        // say so and offer a retry.
        var catalogFailed = false;
        environmentPromise = Promise.all([
            fetch(api('/config'), { cache: 'no-store' }).then(function (r) { return r.ok ? r.json() : {}; }).catch(function () { return {}; }),
            fetch(api('/iracing-cars'), { cache: 'no-store' }).then(function (r) { return r.ok ? r.json() : {}; }).catch(function () { return {}; }),
            fetch(api('/api/spec-sculpt/presets'), { cache: 'no-store' }).then(function (r) { return r.ok ? r.json() : {}; }).catch(function () { return {}; }),
            fetch(api('/api/spec-sculpt/catalog-index'), { cache: 'no-store' }).then(function (r) {
                if (!r.ok) { catalogFailed = true; return {}; }
                return r.json();
            }).catch(function () { catalogFailed = true; return {}; })
        ]).then(function (parts) {
            var cfg = parts[0] || {};
            var cars = ((parts[1] && parts[1].cars) || []).filter(usefulCarFolder);
            var presetRows = (parts[2] && parts[2].presets) || [];
            var catalog = parts[3] || {};
            state.config = cfg;
            state.cars = cars;
            borrowDeploymentIdentity();
            borrowDeploymentFromSource(state.handoffPath || state.sourcePath || state.filename);
            state.looks = SPECIAL_LOOKS.concat(presetRows.map(function (row) {
                return {
                    kind: 'preset', id: row.id, name: row.label || row.id,
                    category: row.category || 'Spec Looks', description: row.description || '',
                    tags: row.tags || [], thumbContract: 'spec',
                    thumb: api('/thumbnails/spec_sculpt_presets/' + encodeURIComponent(row.id) + '.png')
                };
            }), (catalog.bases || []).map(function (row) {
                var swatch = catalogSwatch('base', row.id);
                return {
                    kind: 'catalog', id: row.id, name: row.name || row.id,
                    category: catalogGroupFor('base', row.id) || row.category || 'More Bases',
                    description: row.description || '',
                    swatchType: 'base', swatch: swatch, thumbContract: 'split',
                    thumb: realSwatchUrl('base', row.id, swatch, 48)
                };
            }), (catalog.specials || []).map(function (row) {
                var swatch = catalogSwatch('monolithic', row.id);
                return {
                    kind: 'catalog', id: row.id, name: row.name || row.id,
                    category: catalogGroupFor('monolithic', row.id) || row.category || 'More Specials',
                    description: row.description || '',
                    swatchType: 'monolithic', swatch: swatch, thumbContract: 'split',
                    thumb: realSwatchUrl('monolithic', row.id, swatch, 48)
                };
            }));
            var catalogCount = ((catalog.bases || []).length + (catalog.specials || []).length);
            state.looksLoaded = presetRows.length > 0 && catalogCount > 0 && catalog.complete !== false;
            state.looksError = !state.looksLoaded && (catalogFailed || presetRows.length === 0);
            refreshRecommendations();
            if (state.sourceUrl && state.phase === 'pick') loadPaintAwareRecommendations();
            if (!state.iracingId && validId(cfg.iracing_id)) state.iracingId = String(cfg.iracing_id);
            if (!state.car) {
                if (cfg.active_car && cars.some(function (car) { return car.name === cfg.active_car; })) state.car = cfg.active_car;
                else if (cars.length === 1) state.car = cars[0].name;
            }
            if (mounted) renderRail();
            // Opening the app a moment before the local server is ready must not
            // freeze Easy Mode into its three signature fallbacks until reload.
            // Let the next file/retry action fetch the complete library again.
            if (!state.looksLoaded || !state.cars.length) environmentPromise = null;
            return parts;
        });
        return environmentPromise;
    }

    async function ensureEnvironment() {
        await loadEnvironment();
        if (!state.looksLoaded || !state.cars.length) await loadEnvironment();
    }

    function railHeader(title, copy) {
        var installLocked = state.phase === 'saving';
        return '' +
            '<div class="spb-easy-rail-head">' +
            '  <button type="button" class="spb-easy-back" id="spbEasySculptBack" title="' + (installLocked ? 'Finish the verified iRacing install first' : 'Back to Easy Mode choices') + '" aria-label="Back to Easy Mode choices"' + (installLocked ? ' disabled aria-disabled="true"' : '') + '>&#8592;</button>' +
            '  <div class="spb-easy-step-label spb-easy-head-label">' + esc(title) + '<small>' + esc(copy || '') + '</small></div>' +
            '</div>';
    }

    function render() {
        if (!mounted) return;
        renderStage();
        renderRail();
        var proButton = $('spbEasyProBtn');
        if (proButton) {
            proButton.disabled = state.phase === 'saving';
            proButton.setAttribute('aria-disabled', state.phase === 'saving' ? 'true' : 'false');
            proButton.title = state.phase === 'saving'
                ? 'Finish the verified iRacing install first'
                : 'Open the full Paint Booth editor — this paint stays open';
        }
    }

    function renderStage() {
        var host = $('spbEasySculptStage');
        if (!host) return;
        if (state.phase === 'drop' || (state.phase === 'error' && state.errorContext === 'source')) {
            host.innerHTML = '' +
                '<div class="spb-easy-sculpt-drop-stage" id="spbEasySculptStageDrop" role="group" aria-label="Choose or drop a 2048 iRacing paint file">' +
                '  <div class="spb-easy-sculpt-orbit"><span></span><b>S</b></div>' +
                '  <h1>SPEC SCULPT</h1>' +
                '  <p>Bring in a finished 2048 &times; 2048 iRacing paint.<br>Shokker sculpts a smart starting point for you.</p>' +
                (state.error ? '<div class="spb-easy-sculpt-stage-error" role="alert">' + esc(state.error) + '</div>' : '') +
                (state.retryable && (state.file || state.sourcePath)
                    ? '  <button type="button" id="spbEasySculptRetry">TRY AGAIN</button><button type="button" class="spb-easy-sculpt-choose-different" id="spbEasySculptChoose">CHOOSE A DIFFERENT PAINT</button>'
                    : '  <button type="button" id="spbEasySculptChoose">CHOOSE PAINT</button>') +
                currentPaintButton('stage') +
                '  <span>PSD &middot; TGA &middot; PNG &middot; JPG</span>' +
                '  <input type="file" id="spbEasySculptFile" accept=".psd,.tga,.png,.jpg,.jpeg,image/png,image/jpeg" hidden>' +
                '</div>';
            wireDropSurface(host);
            return;
        }

        if (state.phase === 'checking' || state.phase === 'sculpting' || state.phase === 'saving') {
            host.innerHTML = '' +
                '<div class="spb-easy-sculpt-working" role="status" aria-live="polite" aria-busy="true">' +
                (state.sourceUrl ? '<img src="' + esc(state.sourceUrl) + '" alt="Imported paint">' : '') +
                '<div class="spb-easy-sculpt-working-shade"></div>' +
                '<div class="spb-easy-sculpt-working-card">' +
                '  <div class="spb-easy-sculpt-spinner" aria-hidden="true"></div>' +
                '  <b>' + esc(state.phase === 'saving' ? 'PUTTING IT IN iRACING' : (state.phase === 'checking' ? 'READING YOUR PAINT' : 'BUILDING ' + ((activeTargetLook() && activeTargetLook().name) || 'THE LOOK'))) + '</b>' +
                '  <span>' + esc(state.status || (state.phase === 'saving' ? 'Finishing your paint...' : 'This usually takes a few seconds.')) + '</span>' +
                '</div></div>';
            return;
        }

        if (state.phase === 'pick') {
            var paintRead = state.paintProfile && state.paintProfile.summary
                ? 'Shokker sees ' + paintProfileLabel() + ' paint and picked ' + state.recommendedLookKeys.length + ' strong starting points.'
                : 'Every Spec Sculpt preset and Paint Booth material is in the library.';
            host.innerHTML = '' +
                '<div class="spb-easy-sculpt-pick-stage">' +
                '  <figure><figcaption>YOUR PAINT</figcaption><img id="spbEasySculptSourcePick" src="' + esc(state.sourceUrl) + '" alt="Paint ready for Spec Sculpt"></figure>' +
                '  <div class="spb-easy-sculpt-pick-callout"><b>PICK A LOOK</b><span>' + esc(paintRead) + '</span></div>' +
                '</div>';
            return;
        }

        var activeTarget = activeColorTarget();
        var targetNeedsLook = !!(activeTarget && !activeTarget.look);
        var targetNeedsPaintChoice = !!(targetNeedsLook && !activeTarget.paintDecision);
        var activeLook = activeTargetLook() || state.selectedLook;
        var activeLabel = activeTargetLabel();
        var previewCaption = targetNeedsLook
            ? activeLabel + (targetNeedsPaintChoice ? ': CHOOSE COLOR FIRST' : ': CHOOSE A LOOK')
            : activeLabel + ': ' + ((activeLook && activeLook.name) || 'SCULPTED LOOK');
        var metric = function (name) {
            var value = state.materialMetrics && state.materialMetrics[name];
            return typeof value === 'number' ? Math.max(0, Math.min(100, Math.round(value * 100))) : null;
        };
        var metalMetric = metric('metal'), glossMetric = metric('gloss'), coatMetric = metric('coat');
        var smartStartingPoint = !activeTarget && !state.colorTargets.length && state.selectedLook && state.selectedLook.kind === 'mode' && state.selectedLook.id === 'zoned';
        host.innerHTML = '' +
            '<div class="spb-easy-sculpt-compare' + (state.pickingColor ? ' is-picking-color' : '') + (state.showBigResult ? ' is-big-result' : '') + (state.showSpecMap ? ' is-map-view' : '') + '">' +
            '  <figure class="spb-easy-sculpt-source-figure"><figcaption>ORIGINAL</figcaption><img id="spbEasySculptSourcePick" src="' + esc(state.sourceUrl) + '" alt="Original paint"' + (state.pickingColor ? ' tabindex="0" role="button" aria-label="Choose a color on the original paint. Click a point, or press Enter to sample the center. Escape cancels."' : '') + '>' +
            (state.pickingColor ? '<div class="spb-easy-sculpt-pick-overlay" id="spbEasySculptPickOverlay" aria-hidden="true"><b>CLICK A COLOR ON YOUR PAINT</b><span>Or press Enter for the center &middot; Esc cancels</span></div>' : '') + '</figure>' +
            '  <div class="spb-easy-sculpt-arrow" aria-hidden="true">&#10132;</div>' +
            '  <figure class="spb-easy-sculpt-after' + (state.showSpecMap ? ' showing-map' : '') + '"><figcaption>' + esc(state.showSpecMap ? 'SPEC OUTPUT - FULL VIEW' : 'SCULPTED PAINT' + (state.showBigResult ? ' - BIG VIEW' : '')) + '</figcaption>' +
            (state.showSpecMap
                ? '<img class="spb-easy-sculpt-full-map" src="' + esc(state.specUrl) + '" alt="iRacing material map preview for ' + esc((activeLook && activeLook.name) || 'selected look') + '"><div class="spb-easy-sculpt-map-explain"><b>THIS IS WHAT iRACING READS</b><span>The colors are material data, not paint colors. Install renders this exact plan at 2048.</span></div><button type="button" class="spb-easy-sculpt-result-toggle" id="spbEasySculptResultToggle">BACK TO ALL 3 VIEWS</button>'
                : '<canvas id="spbEasySculptLit" aria-label="Sculpted paint preview: ' + esc(previewCaption) + '"></canvas><button type="button" class="spb-easy-sculpt-big-toggle" id="spbEasySculptBigToggle" aria-pressed="' + (state.showBigResult ? 'true' : 'false') + '" title="' + (state.showBigResult ? 'Return to all three proof views' : 'Make the sculpted paint preview larger') + '">' + (state.showBigResult ? 'BACK TO ALL 3' : 'VIEW BIG') + '</button>') +
            '  </figure>' +
            (state.showSpecMap ? '' : '<div class="spb-easy-sculpt-arrow spb-easy-sculpt-data-arrow" aria-hidden="true">&#10132;</div><figure class="spb-easy-sculpt-map-figure"><figcaption>SPEC OUTPUT</figcaption><button type="button" class="spb-easy-sculpt-map-proof" id="spbEasySculptMapToggle" title="Open the material map iRacing reads"><span class="spb-easy-sculpt-channel-grid" aria-label="Combined, metal, roughness and clearcoat spec channels"><span><b>COMBINED</b><canvas id="spbEasySculptSpecAll" width="128" height="128"></canvas></span><span><b>RED &middot; METAL</b><canvas id="spbEasySculptSpecR" width="128" height="128"></canvas></span><span><b>GREEN &middot; ROUGH</b><canvas id="spbEasySculptSpecG" width="128" height="128"></canvas></span><span><b>BLUE &middot; COAT</b><canvas id="spbEasySculptSpecB" width="128" height="128"></canvas></span></span><span>WHAT iRACING READS</span><b>MATERIAL DATA &middot; OPEN FULL MAP</b></button></figure>') +
            '  <div class="spb-easy-sculpt-preview-note" role="status" aria-live="polite"><div><strong>' + (targetNeedsPaintChoice ? '&#8595; KEEP OR CHANGE THIS COLOR FIRST' : (targetNeedsLook ? '&#8595; NOW CHOOSE ITS FINISH' : (state.recoveredPlan ? '&#10003; LAST SCULPT RESTORED' : (smartStartingPoint ? '&#10003; AUTO-SCULPTED STARTING POINT' : '&#10003; MATERIAL PLAN READY')))) + '</strong><span>' + esc(colorPlanSummary()) + '</span>' +
            (targetNeedsLook ? '' : '<small id="spbEasySculptMaterialSummary">' + esc(state.materialSummary || '') + '</small>') + '</div>' +
            (targetNeedsLook ? '' : '    <div class="spb-easy-sculpt-material-meters" id="spbEasySculptMaterialMeters" aria-label="Material response' + (activeTarget ? ' for ' + esc(colorTargetName(activeTarget)) : ' for the whole paint') + '"><span><i>METAL</i><b><em data-material-meter="metal" style="width:' + (metalMetric == null ? 0 : metalMetric) + '%"></em></b><strong data-material-value="metal">' + (metalMetric == null ? '--' : metalMetric) + '</strong></span><span><i>GLOSS</i><b><em data-material-meter="gloss" style="width:' + (glossMetric == null ? 0 : glossMetric) + '%"></em></b><strong data-material-value="gloss">' + (glossMetric == null ? '--' : glossMetric) + '</strong></span><span><i>COAT</i><b><em data-material-meter="coat" style="width:' + (coatMetric == null ? 0 : coatMetric) + '%"></em></b><strong data-material-value="coat">' + (coatMetric == null ? '--' : coatMetric) + '</strong></span></div>') + '</div>' +
            // [2026-08-06 v2 — owner: "you BROKE the screen of the squares"] The first
            // placement of this button sat BETWEEN two figures inside the compare
            // GRID (columns: figure/arrow/figure/arrow/figure), so it consumed the
            // arrow's cell and shoved SPEC OUTPUT out of the row. It now lives in
            // its own full-width row at the bottom of the grid — the owner's
            // prescription: three squares across, save button below them, centred.
            '<div style="grid-column: 1 / -1; display:flex; justify-content:center; padding-top:6px;">' +
            '<button type="button" class="spb-easy-sculpt-save" id="spbEasySculptSaveProxy" style="min-width:300px;" title="Write the paint and spec files straight into your iRacing folder">SAVE TO iRACING</button>' +
            '</div>' +
            '</div>';
        wireSourceColorPicker();
        wirePreviewControls();
        syncSaveProxy();   // [S16] the proxy was just rebuilt from the template
        if (!state.showSpecMap) {
            drawSpecProofChannels();
            drawLightingPreview();
        }
    }

    function wirePreviewControls() {
        var big = $('spbEasySculptBigToggle');
        if (big) big.addEventListener('click', function () {
            state.showBigResult = !state.showBigResult;
            renderStage();
            var nextBig = $('spbEasySculptBigToggle');
            if (nextBig) nextBig.focus();
        });
        var map = $('spbEasySculptMapToggle');
        if (map) map.addEventListener('click', function () {
            state.showSpecMap = true;
            renderStage();
            var back = $('spbEasySculptResultToggle');
            if (back) back.focus();
        });
        var result = $('spbEasySculptResultToggle');
        if (result) result.addEventListener('click', function () {
            state.showSpecMap = false;
            renderStage();
            var nextMap = $('spbEasySculptMapToggle');
            if (nextMap) nextMap.focus();
        });
    }

    // [2026-08-09 S11] MEASURED: after a reload the sculpt rail comes back empty
    // - 0 look cards, no selection, no impact - and says "1. Load a paint",
    // while a complete plan sits in localStorage. Re-open the same paint and
    // everything returns exactly ("Arctic Ice" / bold), so the recovery path
    // works and the only thing missing was telling the painter it exists.
    function savedPlanOffer() {
        if (state.file || state.sourcePath) return '';
        var raw = '';
        try { raw = window.localStorage.getItem(RECOVERY_KEY) || ''; } catch (error) {}
        if (!raw) return '';
        var plan = null;
        try { plan = JSON.parse(raw); } catch (error) { plan = null; }
        if (!plan || plan.version !== 1 || !plan.selectedLookKey) return '';
        var name = plan.exactName
            || String(plan.sourcePathKey || '').replace(/^.*[\\/]/, '')
            || 'your last paint';
        // [2026-08-09 S21] The live canvas survives a reload too, so the drop
        // panel may ALREADY be offering this very paint. Offering to load it a
        // second time is noise - point at the button that is right there.
        var stem = function (value) {
            return String(value || '').replace(/\\/g, '/').toLowerCase()
                .replace(/\.(psd|tga|png|jpe?g)$/i, '');
        };
        var openNow = stem(currentPaintPath());
        var alreadyOpen = !!openNow && openNow === stem(plan.exactPath || plan.sourcePathKey);
        if (alreadyOpen) {
            return '<div class="spb-easy-sculpt-resume">' +
                '<b>YOUR LAST PLAN IS SAVED</b>' +
                '<span><i>' + esc(name) + '</i> is already open. Take it below and Shokker puts the look and settings back exactly.</span>' +
                '</div>';
        }
        var canOpen = !!plan.exactPath && typeof window.loadPaintByPath === 'function';
        return '<div class="spb-easy-sculpt-resume">' +
            '<b>YOUR LAST PLAN IS SAVED</b>' +
            '<span>Open <i>' + esc(name) + '</i> again and Shokker puts the look and settings back exactly.</span>' +
            (canOpen ? '<button type="button" id="spbEasySculptResume" data-resume-path="' + esc(plan.exactPath) + '">OPEN ' + esc(name.toUpperCase()) + ' AGAIN</button>' : '') +
            '</div>';
    }

    // [2026-08-09 S23] Stands in for the look library while the colour's first
    // question is open, so the painter knows the looks are coming back.
    function pendingLibraryNoteHtml() {
        var target = activeColorTarget();
        var name = target ? colorTargetName(target) : 'this color';
        return '<div class="spb-easy-sculpt-library-pending" role="status">' +
            '<b>YOUR LOOKS COME BACK NEXT</b>' +
            '<span>Answer the question above for <i>' + esc(name) + '</i> and the full library opens right here.</span>' +
            '</div>';
    }

    function renderRail() {
        var rail = $('spbEasyRail');
        if (!mounted || !rail) return;
        var choosing = state.phase === 'pick' || state.phase === 'ready';
        var html = railHeader(
            state.phase === 'saved' ? 'SPEC SCULPT INSTALLED' : (state.phase === 'ready' ? 'SPEC SCULPT · ' + activeTargetLabel() : (choosing ? 'PICK A LOOK' : 'SPEC SCULPT')),
            state.phase === 'saved' ? 'The exact files below were verified, and Main Render will preserve this material.' : (state.phase === 'ready' ? 'Edit the whole car or one color, then pick any look.' : (choosing ? 'Search or browse every available look.' : 'Load a paint, see it auto-sculpt, then install or explore.'))
        );

        if (state.phase === 'drop' || (state.phase === 'error' && state.errorContext === 'source')) {
            html += '<div class="spb-easy-sculpt-rail-body">' +
                '<div class="spb-easy-sculpt-promise simple"><b>THREE CLEAR STEPS</b>' +
                '<span>1. Load a paint &nbsp; 2. See it auto-sculpt &nbsp; 3. Put it in iRacing</span></div>' +
                savedPlanOffer() +
                (state.error ? '<div class="spb-easy-sculpt-error"><b>That paint is not ready for Spec Sculpt.</b><span>' + esc(state.error) + '</span></div>' : '') +
                specLabLink() + '</div>';
            rail.innerHTML = html;
            wireCommonRail();
            return;
        }

        if (state.phase === 'checking' || state.phase === 'sculpting' || state.phase === 'saving') {
            html += '<div class="spb-easy-sculpt-rail-body">' + progressReceipt() + '</div>';
            rail.innerHTML = html;
            wireCommonRail();
            return;
        }

        if (state.phase === 'saved') {
            html += '<div class="spb-easy-sculpt-rail-body spb-easy-sculpt-results">' + exportHtml() +
                '<button type="button" class="spb-easy-sculpt-continue" id="spbEasySculptContinue">BACK TO THIS PAINT</button>' +
                '<button type="button" class="spb-easy-sculpt-change" id="spbEasySculptChange" title="Go back and open a different paint file">Choose a different paint</button></div>';
            rail.innerHTML = html;
            wireCommonRail();
            wireLookPicker();
            return;
        }

        var pendingPaintChoice = state.phase === 'ready' && activeColorTarget() && !activeColorTarget().paintDecision;
        html += '<div class="spb-easy-sculpt-rail-body spb-easy-sculpt-library-body">' +
            (state.phase === 'pick' ? receiptHtml() : '') +
            (state.error && state.errorContext !== 'install' ? '<div class="spb-easy-sculpt-error" role="alert"><b>That look could not be built.</b><span>' + esc(state.error) + '</span>' + ((state.file || state.sourcePath) && state.selectedLook ? '<button type="button" id="spbEasySculptRetryPreview">TRY THIS LOOK AGAIN</button>' : '') + '</div>' : '') +
            (state.phase === 'ready' ? targetEditorHtml() : '') +
            (state.phase === 'ready' && !pendingPaintChoice ? exportHtml() : '') +
            // [2026-08-09 S23] MEASURED: adding a colour takes the library from
            // 4 tabs / 12 cards to 0 / 0 with no word about it. The gate itself
            // is right - one question at a time - but a library that silently
            // vanishes reads as a bug. Say it is coming back.
            (!pendingPaintChoice ? lookPickerHtml() : pendingLibraryNoteHtml()) +
            '<button type="button" class="spb-easy-sculpt-change" id="spbEasySculptChange" title="Go back and open a different paint file">Choose a different paint</button>' +
            specLabLink() + '</div>';
        rail.innerHTML = html;
        wireCommonRail();
        wireTargetEditor();
        wireLookPicker();
        wireSculptThumbs();
        syncSaveProxy();   // [S16] the primary just changed - mirror it
    }

    function lookKey(look) {
        if (!look) return '';
        // Some authored IDs intentionally exist in both the base and special
        // registries. Keep both visual cards addressable and preserve registry
        // type because those cards can carry different thumbnails and recipes.
        return look.kind === 'catalog'
            ? (look.kind + ':' + (look.swatchType || 'material') + ':' + look.id)
            : (look.kind + ':' + look.id);
    }

    function lookMaterialKey(look) {
        if (!look) return '';
        // Registry type is part of the material identity. Some authored IDs
        // intentionally exist in both Paint Booth registries; their cards use
        // different real thumbnails and now render different real recipes.
        return lookKey(look);
    }

    var thumbHydrateTimer = 0;
    function hydrateSculptThumbs(container) {
        if (!container || !container.isConnected) return;
        var viewport = container.classList && container.classList.contains('spb-easy-sculpt-base-browser')
            ? container
            : (container.closest('.spb-easy-sculpt-rail-body') || container);
        var viewportRect = viewport.getBoundingClientRect();
        var topEdge = viewportRect.top - 300;
        var bottomEdge = viewportRect.bottom + 500;
        Array.prototype.forEach.call(container.querySelectorAll('img[data-src]:not([src]):not([data-thumb-failed])'), function (image) {
            var details = image.closest('details');
            if (details && !details.open) return;
            var rect = image.getBoundingClientRect();
            if (rect.bottom < topEdge || rect.top > bottomEdge) return;
            if (!image._spbEasySculptErrorWired) {
                image._spbEasySculptErrorWired = true;
                image.addEventListener('load', function () {
                    image.removeAttribute('data-thumb-failed');
                    image.removeAttribute('data-thumb-retry');
                    if (image.parentNode && image.parentNode.classList) image.parentNode.classList.remove('thumb-failed');
                });
                image.addEventListener('error', function () {
                    var retry = parseInt(image.getAttribute('data-thumb-retry') || '0', 10) || 0;
                    // Selecting a look starts the full material render at the
                    // same moment its card is rebuilt. A cold real-swatch call
                    // can briefly lose that race; retry the SAME canonical URL
                    // twice. Never substitute synthetic/fallback pixels.
                    if (retry < 2 && image.isConnected) {
                        retry += 1;
                        image.setAttribute('data-thumb-retry', String(retry));
                        image.removeAttribute('src');
                        window.setTimeout(function () {
                            if (!image.isConnected) return;
                            var source = image.getAttribute('data-src') || '';
                            image.src = source + (source.indexOf('?') >= 0 ? '&' : '?') + 'real_retry=' + retry;
                        }, 450 * retry);
                        return;
                    }
                    image.setAttribute('data-thumb-failed', '1');
                    image.removeAttribute('src');
                    if (image.parentNode && image.parentNode.classList) image.parentNode.classList.add('thumb-failed');
                });
            }
            image.src = image.getAttribute('data-src');
        });
    }
    function hydrateSculptThumbsSoon(container) {
        if (thumbHydrateTimer) window.clearTimeout(thumbHydrateTimer);
        thumbHydrateTimer = window.setTimeout(function () {
            thumbHydrateTimer = 0;
            hydrateSculptThumbs(container);
        }, 80);
    }
    function wireSculptThumbs() {
        var body = document.querySelector('#spbEasyRail .spb-easy-sculpt-rail-body');
        if (!body) return;
        body.addEventListener('scroll', function () { hydrateSculptThumbsSoon(body); }, { passive: true });
        var baseBrowser = body.querySelector('.spb-easy-sculpt-base-browser');
        if (baseBrowser) baseBrowser.addEventListener('scroll', function () { hydrateSculptThumbsSoon(baseBrowser); }, { passive: true });
        Array.prototype.forEach.call(body.querySelectorAll('details'), function (details) {
            details.addEventListener('toggle', function () { if (details.open) hydrateSculptThumbsSoon(baseBrowser || body); });
        });
        hydrateSculptThumbs(body);
        if (baseBrowser) hydrateSculptThumbs(baseBrowser);
    }

    function lookArtHtml(look, thumb, paintAware) {
        var contract = paintAware ? 'on-your-paint' : ((look && look.thumbContract) || 'smart-look');
        var labels = contract === 'split'
            ? '<span class="spb-easy-sculpt-thumb-labels"><i>PAINT</i><i>SPEC</i></span>'
            : (contract === 'spec' ? '<span class="spb-easy-sculpt-thumb-labels single"><i>REAL SPEC LOOK</i></span>'
                : (paintAware ? '<span class="spb-easy-sculpt-thumb-labels single"><i>ON YOUR PAINT</i></span>' : ''));
        return '<span class="spb-easy-sculpt-look-art' + (thumb ? '' : ' no-thumb') + '" aria-hidden="true" data-swatch-contract="' + esc(contract) + '">' +
            (thumb ? '<img data-src="' + esc(thumb) + '" alt="" loading="lazy" decoding="async">' : '') +
            (!thumb && look && look.emoji ? '<i class="spb-easy-sculpt-smart-icon">' + look.emoji + '</i>' : '') +
            labels +
            '<span class="spb-easy-sculpt-thumb-unavailable" aria-hidden="true">' + (thumb ? 'PREVIEW UNAVAILABLE' : 'LIVE PREVIEW BUILDS') + '</span></span>';
    }

    function activeColorTarget() {
        if (!state.activeColorId) return null;
        return state.colorTargets.filter(function (target) { return target.id === state.activeColorId; })[0] || null;
    }

    function activeTargetLook() {
        var target = activeColorTarget();
        return target ? target.look : state.selectedLook;
    }

    function activeTargetScale() {
        var target = activeColorTarget();
        return target ? target.materialScale : state.materialScale;
    }

    function colorTargetName(target) {
        var guidance = window.spbEasySculptGuidance;
        return target && guidance && typeof guidance.colorName === 'function'
            ? guidance.colorName(target.color)
            : 'COLOR';
    }

    function colorTargetLabel(target) {
        return colorTargetName(target) + ' (' + ((target && target.hex) || '') + ')';
    }

    function colorTargetPaintLabel(target) {
        if (!target) return '';
        return target.replacementColor
            ? target.hex + ' → ' + target.replacementColor.toUpperCase()
            : target.hex;
    }
    function activeTargetLabel() {
        var target = activeColorTarget();
        return target ? ('EDITING ' + colorTargetName(target)) : 'WHOLE CAR';
    }

    function activeTargetKey() {
        return state.activeColorId || 'whole';
    }

    function colorPlanSummary() {
        var readyColors = state.colorTargets.filter(function (target) { return !!target.look; });
        var applied = readyColors.length;
        var active = activeColorTarget();
        if (active && !active.look) {
            return active.paintDecision
                ? 'The paint-color choice is set. Pick any finish below to change only ' + colorTargetLabel(active) + '.'
                : 'The preview still shows the whole-paint material. Choose KEEP ORIGINAL or CHANGE COLOR first.';
        }
        if (!applied && state.selectedLook && state.selectedLook.kind === 'mode' && state.selectedLook.id === 'zoned') {
            return 'Shokker assigned fitting materials across the paint\'s color regions. Add a color only to override one.';
        }
        if (!applied) return 'One look covers the whole paint. Add a color only when you want another material.';
        if (applied <= 3) {
            return readyColors.map(function (target) {
                return colorTargetName(target) + (target.replacementColor ? ' → ' + target.replacementColor.toUpperCase() : '') + ' is ' + target.look.name;
            }).join(' · ') + ' — layered over ' + ((state.selectedLook && state.selectedLook.name) || 'the whole paint') + '.';
        }
        return applied + ' color material' + (applied === 1 ? '' : 's') + ' layered over the whole-paint look.';
    }

    function paintProfileLabel() {
        if (!state.paintProfile || !state.paintProfile.summary) return 'paint-aware';
        var hues = (state.palette || []).filter(function (item) {
            return ['BLACK', 'CHARCOAL', 'GRAY', 'SILVER', 'WHITE'].indexOf(item.name) === -1;
        }).slice(0, 2).map(function (item) { return String(item.name || '').toLowerCase(); });
        return state.paintProfile.summary + (hues.length ? ' with ' + hues.join(' + ') : '');
    }

    function lookSupportsScale(look) {
        return !!look && (look.kind === 'preset' || look.kind === 'catalog');
    }

    function rgbHex(rgb) {
        return '#' + (rgb || [0, 0, 0]).slice(0, 3).map(function (value) {
            return Math.max(0, Math.min(255, value | 0)).toString(16).padStart(2, '0');
        }).join('').toUpperCase();
    }
    function hexRgb(hex) {
        var match = /^#?([0-9a-f]{6})$/i.exec(String(hex || ''));
        if (!match) return null;
        return [parseInt(match[1].slice(0, 2), 16), parseInt(match[1].slice(2, 4), 16), parseInt(match[1].slice(4, 6), 16)];
    }
    function rgbToHsv(rgb) {
        var values = (rgb || [0, 0, 0]).slice(0, 3).map(function (value) { return Math.max(0, Math.min(255, Number(value) || 0)) / 255; });
        var r = values[0], g = values[1], b = values[2];
        var max = Math.max(r, g, b), min = Math.min(r, g, b), delta = max - min, hue = 0;
        if (delta > 0) {
            if (max === r) hue = 60 * (((g - b) / delta) % 6);
            else if (max === g) hue = 60 * (((b - r) / delta) + 2);
            else hue = 60 * (((r - g) / delta) + 4);
        }
        if (hue < 0) hue += 360;
        return { h: Math.round(hue), s: Math.round(max ? (delta / max) * 100 : 0), v: Math.round(max * 100) };
    }
    function hsvHex(hue, saturation, brightness) {
        var h = ((Number(hue) || 0) % 360 + 360) % 360;
        var s = Math.max(0, Math.min(100, Number(saturation) || 0)) / 100;
        var v = Math.max(0, Math.min(100, Number(brightness) || 0)) / 100;
        var c = v * s, x = c * (1 - Math.abs(((h / 60) % 2) - 1)), m = v - c;
        var rgb = h < 60 ? [c, x, 0] : (h < 120 ? [x, c, 0] : (h < 180 ? [0, c, x] : (h < 240 ? [0, x, c] : (h < 300 ? [x, 0, c] : [c, 0, x]))));
        return rgbHex(rgb.map(function (value) { return Math.round((value + m) * 255); }));
    }
    function easyPaintBases() {
        var rows = [];
        try { if (typeof BASES !== 'undefined' && Array.isArray(BASES)) rows = BASES.slice(); } catch (error) {}
        return rows.filter(function (base) { return base && base.id && /^#[0-9a-f]{6}$/i.test(base.swatch || ''); })
            .sort(function (a, b) { return String(a.name || a.id).localeCompare(String(b.name || b.id)); });
    }
    // [2026-08-06 owner: "ANY Base or Special should be in there. You are
    // missing ALL of the FRACTURED finishes."] Pro's SPECIALS live in the
    // monolithic arrays, not BASES — collect them with the same {id,name,swatch}
    // shape, tagged so thumbnails hit /api/swatch/monolithic/ instead of /base/.
    function easySpecialBases() {
        // NOTE: these are top-level `const` declarations in the data file —
        // global LEXICAL bindings, so window[name] is undefined; bare
        // identifiers (guarded) are the only way to reach them.
        var rows = [];
        try { if (typeof MONOLITHICS !== 'undefined' && Array.isArray(MONOLITHICS)) rows = rows.concat(MONOLITHICS); } catch (error) {}
        try { if (typeof REWORK_MONOLITHICS !== 'undefined' && Array.isArray(REWORK_MONOLITHICS)) rows = rows.concat(REWORK_MONOLITHICS); } catch (error) {}
        try { if (typeof MONOLITHIC_WAVE !== 'undefined' && Array.isArray(MONOLITHIC_WAVE)) rows = rows.concat(MONOLITHIC_WAVE); } catch (error) {}
        try { if (typeof COLOR_MONOLITHICS !== 'undefined' && Array.isArray(COLOR_MONOLITHICS)) rows = rows.concat(COLOR_MONOLITHICS); } catch (error) {}
        return rows.filter(function (row) { return row && row.id && /^#[0-9a-f]{6}$/i.test(row.swatch || ''); })
            .map(function (row) {
                return { id: row.id, name: row.name, desc: row.desc, swatch: row.swatch, _swatchType: 'monolithic' };
            });
    }
    function easyAllPickableRows() {
        return easyPaintBases().concat(easySpecialBases());
    }
    function baseGroupDescription(name) {
        var label = String(name || '').toLowerCase();
        if (/foundation/.test(label)) return 'Clean, dependable painted surfaces and real-car colors.';
        if (/candy|pearl/.test(label)) return 'Deep color, pearl shift and layered show-car paint.';
        if (/chrome|mirror|metal/.test(label)) return 'Reflective, machined and polished material colors.';
        if (/carbon|composite/.test(label)) return 'Technical weave and composite-inspired colors.';
        if (/glass|ceramic/.test(label)) return 'Glazed, translucent and glass-like authored colors.';
        if (/weather|aged|patina/.test(label)) return 'Race-used, worn and naturally aged color families.';
        if (/fractured/i.test(label)) return 'FRACTURED lab finishes — borrow their authored color-shift colors.';
        return 'Real authored Paint Booth colors. Open this family to see them.';
    }
    function groupedEasyPaintBases() {
        var rows = easyPaintBases();
        var byId = {};
        var used = {};
        var groups = [];
        rows.forEach(function (base) { byId[base.id] = base; });
        try {
            if (typeof BASE_GROUPS !== 'undefined' && BASE_GROUPS) {
                Object.keys(BASE_GROUPS).forEach(function (name) {
                    var groupRows = (BASE_GROUPS[name] || []).map(function (id) { return byId[id]; }).filter(function (base) {
                        if (!base || used[base.id]) return false;
                        used[base.id] = true;
                        return true;
                    });
                    if (groupRows.length) groups.push({ name: name, rows: groupRows });
                });
            }
        } catch (error) {}
        // [2026-08-06 owner round 2: "you are somehow adding back in some things
        // we've stripped out over several iterations"] The prefix-derived
        // families + "More Bases A-E..." buckets are GONE — they surfaced bases
        // deliberately absent from BASE_GROUPS, which Pro's picker hides. Easy
        // Mode now hides them too: if it's not in a Pro group, it's not offered.
        //
        // [same message: "ANY Base or Special should be in there. You are
        // missing ALL of the FRACTURED finishes."] Append Pro's ENTIRE specials
        // taxonomy — SPECIALS_SECTION_ORDER → SPECIALS_SECTIONS subgroups →
        // SPECIAL_GROUPS ids — as families, exactly the folders Pro shows
        // (every FRACTURED lane, SHOKKER, FABLE, Cultural, Color Science, …).
        try {
            if (typeof SPECIALS_SECTION_ORDER !== 'undefined' && typeof SPECIALS_SECTIONS !== 'undefined'
                    && typeof SPECIAL_GROUPS !== 'undefined') {
                var monoById = {};
                easySpecialBases().forEach(function (row) { monoById[row.id] = row; });
                SPECIALS_SECTION_ORDER.forEach(function (section) {
                    (SPECIALS_SECTIONS[section] || []).forEach(function (subName) {
                        var subRows = (SPECIAL_GROUPS[subName] || []).map(function (id) { return monoById[id]; })
                            .filter(function (row) {
                                if (!row || used[row.id]) return false;
                                used[row.id] = true;
                                return true;
                            });
                        if (subRows.length) groups.push({ name: subName, rows: subRows, special: section });
                    });
                });
            }
        } catch (error) {}
        return groups;
    }
    function baseThumbHtml(base, extraClass) {
        var url = realSwatchUrl(base._swatchType || 'base', base.id, base.swatch, 48);
        return '<span class="spb-easy-sculpt-base-thumb ' + esc(extraClass || '') + '" data-swatch-contract="paint-left-spec-right">' +
            '<img data-src="' + esc(url) + '" alt="" loading="lazy" decoding="async">' +
            '<span class="spb-easy-sculpt-thumb-labels"><i>PAINT</i><i>SPEC</i></span>' +
            '<span class="spb-easy-sculpt-thumb-unavailable" aria-hidden="true">PREVIEW UNAVAILABLE</span></span>';
    }
    function paintBaseCardHtml(base, selectedId) {
        var selected = selectedId === base.id;
        var search = [base.id, base.name, base.desc, base.swatch].join(' ').toLowerCase();
        return '<button type="button" class="spb-easy-sculpt-base-card' + (selected ? ' selected' : '') + '" data-sculpt-base-id="' + esc(base.id) + '" data-base-search="' + esc(search) + '" aria-pressed="' + (selected ? 'true' : 'false') + '" title="Borrow ' + esc(base.name || base.id) + '\'s authored color">' +
            baseThumbHtml(base, '') + '<span><b>' + esc(base.name || base.id) + '</b><small><i style="--base-chip:' + esc(base.swatch) + '"></i>' + esc(String(base.swatch).toUpperCase()) + ' · BORROW COLOR</small></span></button>';
    }
    function paintBaseLibraryHtml(selectedId) {
        var groups = groupedEasyPaintBases();
        var selected = easyAllPickableRows().filter(function (base) { return base.id === selectedId; })[0] || null;
        var selectedGroup = '';
        groups.some(function (group) {
            if (group.rows.some(function (base) { return base.id === selectedId; })) { selectedGroup = group.name; return true; }
            return false;
        });
        var current = selected
            ? '<div class="spb-easy-sculpt-base-current">' + baseThumbHtml(selected, 'current') + '<span><b>' + esc(selected.name || selected.id) + '</b><small>REAL PAINT + SPEC THUMBNAIL · BORROWING ITS COLOR</small></span></div>'
            : '<div class="spb-easy-sculpt-base-current empty"><b>CHOOSE A BASE COLOR YOU CAN SEE</b><small>Open a family below. Every card is a real Paint Booth paint + spec thumbnail.</small></div>';
        var chosenFamily = state.baseFamily || '';
        var sections = groups.map(function (group) {
            var open = chosenFamily ? group.name === chosenFamily
                     : (selectedGroup ? group.name === selectedGroup : group.name === 'Foundation');
            var hiddenByFamily = chosenFamily && group.name !== chosenFamily;
            return '<details class="spb-easy-sculpt-base-group" data-group-name="' + esc(group.name) + '" data-default-open="' + (open ? '1' : '0') + '"' + (open ? ' open' : '') + (hiddenByFamily ? ' hidden' : '') + '>' +
                '<summary><span><b>' + esc(group.name) + '</b><small>' + esc(baseGroupDescription(group.name)) + '</small></span><em data-base-group-count>' + group.rows.length + ' colors</em></summary>' +
                '<div class="spb-easy-sculpt-base-grid">' + group.rows.map(function (base) { return paintBaseCardHtml(base, selectedId); }).join('') + '</div></details>';
        }).join('');
        // [2026-08-06 owner ask] Dropdown of families kills the endless scroll:
        // pick a family, see only that family. "All families" restores browsing.
        var famSelect = '<label class="spb-easy-sculpt-family-pick" style="display:flex;align-items:center;gap:8px;margin:6px 0;">' +
            '<b style="font-size:10px;letter-spacing:1px;white-space:nowrap;">FAMILY</b>' +
            '<select id="spbEasySculptBaseFamily" style="flex:1;min-width:0;background:#0d1526;color:#dfe9ff;border:1px solid rgba(120,150,220,0.35);border-radius:6px;padding:6px 8px;font-size:12px;">' +
            '<option value=""' + (chosenFamily ? '' : ' selected') + '>All families (' + groups.length + ')</option>' +
            groups.map(function (g) {
                return '<option value="' + esc(g.name) + '"' + (chosenFamily === g.name ? ' selected' : '') + '>' + esc(g.name) + ' (' + g.rows.length + ')</option>';
            }).join('') + '</select></label>';
        return current + famSelect + '<div class="spb-easy-sculpt-base-browser" id="spbEasySculptBaseColorLibrary" aria-label="Paint Booth base color thumbnail library">' + sections + '</div>';
    }
    function filterBaseColorOptions() {
        var input = $('spbEasySculptBaseColorSearch');
        var library = $('spbEasySculptBaseColorLibrary');
        var status = $('spbEasySculptBaseColorStatus');
        if (!input || !library) return;
        var query = String(input.value || '').trim().toLowerCase();
        state.baseColorQuery = query;
        var activeQuery = query.length >= 2 ? query : '';
        var terms = activeQuery.split(/\s+/).filter(Boolean);
        var visible = 0;
        Array.prototype.forEach.call(library.querySelectorAll('[data-sculpt-base-id]'), function (card) {
            var haystack = card.getAttribute('data-base-search') || '';
            var match = !terms.length || terms.every(function (term) { return haystack.indexOf(term) !== -1; });
            card.hidden = !match;
            if (match) visible += 1;
        });
        var firstMatchOpened = false;
        Array.prototype.forEach.call(library.querySelectorAll('.spb-easy-sculpt-base-group'), function (group) {
            var matches = group.querySelectorAll('[data-sculpt-base-id]:not([hidden])').length;
            group.hidden = !!activeQuery && !matches;
            var count = group.querySelector('[data-base-group-count]');
            if (count) count.textContent = matches + ' color' + (matches === 1 ? '' : 's');
            if (activeQuery && matches) {
                group.open = !firstMatchOpened;
                firstMatchOpened = true;
            } else if (!activeQuery) group.open = group.getAttribute('data-default-open') === '1';
        });
        if (status) status.textContent = query.length === 1
            ? 'TYPE ONE MORE LETTER TO FILTER · ' + visible + ' REAL THUMBNAILS'
            : visible + ' real base thumbnail' + (visible === 1 ? '' : 's') + (activeQuery ? ' match' : ' available');
        hydrateSculptThumbs(library);
    }
    function refreshRecommendations() {
        var guidance = window.spbEasySculptGuidance;
        if (!guidance || !state.paintProfile || !state.looks.length) {
            state.recommendedLookKeys = state.looks.slice(0, 12).map(lookKey);
            return;
        }
        var profile = state.paintProfile;
        var target = activeColorTarget();
        if (target) {
            // Editing one color should change the recommendation brain, not just
            // the preview mask. Preserve the paint's texture/contrast character,
            // but rank hue-aware names against the color the person selected.
            profile = {
                archetypes: (state.paintProfile.archetypes || []).slice(),
                features: state.paintProfile.features || {},
                summary: state.paintProfile.summary || '',
                palette: [{
                    color: target.color.slice(),
                    hex: target.hex,
                    name: guidance.colorName(target.color),
                    coverage: 100
                }]
            };
        }
        state.recommendedLookKeys = guidance.rankLooks(state.looks, profile, 12).map(lookKey);
    }

    async function updatePaintGuidance() {
        var guidance = window.spbEasySculptGuidance;
        if (!guidance || !state.sourceUrl) return;
        try {
            var source = await loadImage(state.sourceUrl);
            var canvas = document.createElement('canvas');
            var edge = 128;
            canvas.width = edge;
            canvas.height = edge;
            var context = canvas.getContext('2d', { willReadFrequently: true });
            context.drawImage(source, 0, 0, edge, edge);
            var pixels = context.getImageData(0, 0, edge, edge);
            state.paintProfile = guidance.analyzePixels(pixels.data, edge, edge);
            state.palette = state.paintProfile.palette || [];
            refreshRecommendations();
        } catch (error) {
            state.paintProfile = null;
            state.palette = [];
            refreshRecommendations();
        }
    }

    async function loadPaintAwareRecommendations() {
        if ((!state.file && !state.sourcePath) || !state.looksLoaded || !state.recommendedLookKeys.length) return;
        // The recommendation rail is the two-minute demo. Signature engines must
        // look just as personal as catalog finishes: render Smart Materials,
        // FRACTURE, and Candy Depth on the loaded livery instead of leaving the
        // three most important choices as generic emoji cards.
        // Canonical presets/catalog cards already have real shipped/split art.
        // Only the three signature modes need a paint-aware preview render.
        // Rendering the other nine previews here was invisible work and made a
        // simple color/scale change feel dramatically slower than it is.
        var candidates = state.recommendedLookKeys.map(findLook).filter(function (look) {
            return look && !look.thumb && look.kind === 'mode';
        }).slice(0, 3);
        if (!candidates.length) return;
        var key = String(state.filename) + ':' + String(state.seedBase) + ':' + recommendationContextSignature() + ':' + candidates.map(lookKey).join('|');
        if (state.recommendationKey === key) return;
        abortRecommendations();
        var serial = ++recommendationSerial;
        recommendationController = typeof AbortController !== 'undefined' ? new AbortController() : null;
        state.recommendationKey = key;
        state.recommendationLoading = true;
        candidates.forEach(function (look) {
            if (look.paintThumbContext !== key) delete look.paintThumb;
        });
        if (mounted && (state.phase === 'pick' || state.phase === 'ready')) refreshRecommendationTiles();
        var variations = candidates.map(function (look) {
            var row = {
                label: look.name,
                seed: recommendationPlanSeed(look),
                material_scale: state.materialScale,
                material_impact: state.materialImpact,
                exact: true
            };
            if (look.kind === 'preset') row.presets = [[look.id, 1]];
            else if (look.kind === 'catalog') row.catalog = [{ id: look.id, weight: 1, registry_type: look.swatchType || '' }];
            else row.mode = look.id;
            var colorPlan = recommendationColorPlan(look);
            if (colorPlan) {
                row.easy_base = colorPlan.easy_base;
                row.easy_color_layers = colorPlan.easy_color_layers;
            }
            return row;
        });
        try {
            var body, headers;
            if (state.file && !state.serverSourcePath) {
                body = new FormData();
                body.append('paint_file', state.file);
                body.append('seed', String(state.seedBase));
                body.append('preview_size', '192');
                body.append('chromatic_shift', '1');
                body.append('auto_protect', '1');
                body.append('variations', JSON.stringify(variations));
                headers = {};
            } else {
                body = JSON.stringify({
                    paint_file: state.serverSourcePath || state.sourcePath,
                    seed: state.seedBase,
                    preview_size: 192,
                    chromatic_shift: true,
                    auto_protect: true,
                    variations: variations
                });
                headers = { 'Content-Type': 'application/json' };
            }
            var response = await fetch(api('/api/spec-sculpt/batch'), {
                method: 'POST', headers: headers, body: body,
                signal: recommendationController && recommendationController.signal
            });
            var payload = await readJsonResponse(response, 'Paint-aware tiles did not finish.');
            if (serial !== recommendationSerial) return;
            if (!response.ok || !payload.success) throw responseError(response, payload.error, 'Paint-aware tiles did not finish.');
            (payload.variations || []).forEach(function (row) {
                var look = candidates[Number(row.idx)];
                var previews = row.previews || {};
                if (look && (previews.render || previews.composite)) {
                    look.paintThumb = previews.render || previews.composite;
                    look.paintThumbContext = key;
                }
            });
            state.recommendationLoading = false;
            // Never rebuild the look rail when background thumbnails finish.
            // A live DOM replacement can detach the exact button a user is
            // pressing and make a valid look click feel like it did nothing.
            if (mounted) refreshRecommendationTiles();
        } catch (error) {
            if (error && error.name === 'AbortError') return;
            if (serial !== recommendationSerial) return;
            // Generic swatches remain a complete fallback; this enhancement can
            // never block the three-step path or turn into another error panel.
            state.recommendationLoading = false;
            state.recommendationKey = '';
            if (mounted) refreshRecommendationTiles();
        }
    }

    function refreshRecommendationTiles() {
        Array.prototype.forEach.call(document.querySelectorAll('#spbEasyRail [data-look-key]'), function (card) {
            var look = findLook(card.getAttribute('data-look-key'));
            // Authored Paint Booth and preset cards always keep their canonical
            // shipping thumbnail. A generated on-car JPEG is only used by the
            // three smart signature modes that have no catalog swatch.
            if (!look || look.thumb || !look.paintThumb || look.paintThumbContext !== state.recommendationKey) return;
            var image = card.querySelector('img');
            if (!image) {
                image = document.createElement('img');
                image.alt = '';
                image.loading = 'lazy';
                image.decoding = 'async';
                var art = card.querySelector('.spb-easy-sculpt-look-art');
                if (art) {
                    image.addEventListener('error', function () {
                        image.setAttribute('data-thumb-failed', '1');
                        image.removeAttribute('src');
                        art.classList.add('thumb-failed');
                    });
                    art.classList.remove('no-thumb', 'thumb-failed');
                    art.setAttribute('data-swatch-contract', 'on-your-paint');
                    var smartIcon = art.querySelector('.spb-easy-sculpt-smart-icon');
                    if (smartIcon) smartIcon.remove();
                    var labels = art.querySelector('.spb-easy-sculpt-thumb-labels');
                    if (!labels) {
                        labels = document.createElement('span');
                        labels.className = 'spb-easy-sculpt-thumb-labels single';
                        art.insertBefore(labels, art.firstChild);
                    }
                    labels.innerHTML = '<i>ON YOUR PAINT</i>';
                    art.insertBefore(image, art.firstChild);
                }
            }
            image.src = look.paintThumb;
        });
        var profileNote = document.querySelector('.spb-easy-sculpt-profile small');
        var target = activeColorTarget();
        if (profileNote) profileNote.textContent = state.recommendationLoading
            ? (target ? 'Painting these picks onto only ' + colorTargetName(target) + '...' : 'Painting these picks onto your livery...')
            : (target ? 'Only ' + colorTargetName(target) + ' changes in these previews.' : 'Top picks are previewed on your paint. Everything else stays available.');
    }

    function addColorTarget(rgb) {
        if (!rgb || state.colorTargets.length >= MAX_COLOR_TARGETS) return null;
        state.recoveredPlan = false;
        // A new material is a fresh decision. Do not strand it inside the last
        // color/base search; open its own paint-aware shortlist immediately.
        if (lookSearchTimer) window.clearTimeout(lookSearchTimer);
        lookSearchTimer = 0;
        state.libraryQuery = '';
        state.libraryKind = 'recommended';
        state.libraryCategory = '';
        state.libraryLimit = LOOK_PAGE_SIZE;
        state.libraryScrollTop = 0;
        var pixel = rgb.slice(0, 3).map(function (value) { return Math.max(0, Math.min(255, Number(value) || 0)); });
        var duplicate = state.colorTargets.filter(function (target) {
            var dr = target.color[0] - pixel[0], dg = target.color[1] - pixel[1], db = target.color[2] - pixel[2];
            return Math.sqrt(dr * dr + dg * dg + db * db) < 12;
        })[0];
        if (duplicate) {
            state.activeColorId = duplicate.id;
            return duplicate;
        }
        var id = 'color-' + Date.now().toString(36) + '-' + state.colorTargets.length;
        var target = {
            id: id,
            color: pixel,
            hex: rgbHex(pixel),
            tolerance: 30,
            look: null,
            materialScale: state.materialScale,
            paintDecision: '',
            replacementColor: '',
            replacementMode: 'solid',
            replacementBaseId: '',
            coverage: null
        };
        state.colorTargets.push(target);
        state.activeColorId = id;
        return target;
    }

    function detectedPaletteHtml() {
        if (!state.palette.length || state.colorTargets.length >= MAX_COLOR_TARGETS) return '';
        var available = state.palette.filter(function (entry) {
            return !state.colorTargets.some(function (target) {
                var dr = target.color[0] - entry.color[0], dg = target.color[1] - entry.color[1], db = target.color[2] - entry.color[2];
                return Math.sqrt(dr * dr + dg * dg + db * db) < 12;
            });
        });
        if (!available.length) return '';
        return '<div class="spb-easy-sculpt-palette"><span><b>COLORS SHOKKER FOUND</b><small>One click makes a color its own material.</small></span><div>' +
            available.slice(0, MAX_COLOR_TARGETS).map(function (entry, index) {
                return '<button type="button" data-palette-index="' + state.palette.indexOf(entry) + '" style="--palette-color:' + esc(entry.hex) + '" title="Add ' + esc(entry.name) + ' ' + esc(entry.hex) + '" aria-label="Add ' + esc(entry.name) + ' ' + esc(entry.hex) + ' as its own material"><i></i><b>' + esc(entry.name) + '</b></button>';
            }).join('') + '</div></div>';
    }

    function autoColorChoices() {
        var guidance = window.spbEasySculptGuidance;
        if (!guidance || typeof guidance.chooseAutoColors !== 'function' || !state.looks.some(function (look) { return look && look.kind !== 'mode'; })) return [];
        return guidance.chooseAutoColors(state.palette, state.colorTargets, 2);
    }

    function autoLookForColor(target, usedLookKeys, usedFamilies) {
        var guidance = window.spbEasySculptGuidance;
        if (!guidance || typeof guidance.rankLooks !== 'function') return null;
        var profile = {
            archetypes: (state.paintProfile && state.paintProfile.archetypes || []).slice(),
            features: (state.paintProfile && state.paintProfile.features) || {},
            summary: (state.paintProfile && state.paintProfile.summary) || '',
            palette: [{ color: target.color.slice(), hex: target.hex, name: guidance.colorName(target.color), coverage: 100 }]
        };
        var ranked = guidance.rankLooks(state.looks, profile, 30).filter(function (look) {
            return look && look.kind !== 'mode' && usedLookKeys.indexOf(lookMaterialKey(look)) === -1;
        });
        var distinct = ranked.filter(function (look) {
            var family = typeof guidance.describeLook === 'function' ? guidance.describeLook(look) : '';
            return !family || usedFamilies.indexOf(family) === -1;
        });
        return distinct[0] || ranked[0] || null;
    }

    function autoSculptColors() {
        if (state.colorTargets.length || !state.selectedLook) return;
        var choices = autoColorChoices();
        if (!choices.length) return;
        var guidance = window.spbEasySculptGuidance;
        var usedLookKeys = [lookMaterialKey(state.selectedLook)];
        var usedFamilies = [];
        choices.forEach(function (entry) {
            var target = addColorTarget(entry.color);
            if (!target) return;
            var look = autoLookForColor(target, usedLookKeys, usedFamilies);
            if (!look) return;
            target.look = look;
            target.paintDecision = 'keep';
            usedLookKeys.push(lookMaterialKey(look));
            if (guidance && typeof guidance.describeLook === 'function') usedFamilies.push(guidance.describeLook(look));
        });
        state.colorTargets = state.colorTargets.filter(function (target) { return !!target.look; });
        state.activeColorId = '';
        state.pickingColor = false;
        state.libraryQuery = '';
        state.libraryKind = 'recommended';
        state.libraryCategory = '';
        state.libraryLimit = LOOK_PAGE_SIZE;
        state.recoveredPlan = false;
        refreshRecommendations();
        generatePreview('Auto-sculpting the paint colors and materials together...');
    }

    function targetEditorHtml() {
        var target = activeColorTarget();
        var look = activeTargetLook();
        var scale = activeTargetScale();
        var wholeSelected = !target;
        var colorDecisionDone = !target || target.paintDecision === 'keep' || target.paintDecision === 'change';
        var autoChoices = !state.colorTargets.length ? autoColorChoices() : [];
        var titleAction = autoChoices.length
            ? '<button type="button" class="spb-easy-sculpt-auto-colors" id="spbEasySculptAutoColors"><b>AUTO-SCULPT ' + autoChoices.length + ' COLOR' + (autoChoices.length === 1 ? '' : 'S') + '</b><small>Shokker picks the materials</small></button>'
            : '<strong>' + esc(activeTargetLabel()) + '</strong>';
        var targetButtons = '<button type="button" id="spbEasySculptScope-whole" class="spb-easy-sculpt-scope' + (wholeSelected ? ' active' : '') + '" data-sculpt-target="whole" aria-pressed="' + (wholeSelected ? 'true' : 'false') + '"><i class="whole">ALL</i><span><b>WHOLE CAR</b><small>' + esc((state.selectedLook && state.selectedLook.name) || 'Choose a look') + '</small></span></button>';
        targetButtons += state.colorTargets.map(function (item) {
            var itemLook = item.look;
            var coverage = typeof item.coverage === 'number'
                ? (item.coverage > 0 ? item.coverage.toFixed(item.coverage < 1 ? 1 : 0) + '% matched' : 'No match - try Wide')
                : 'Pick a look';
            var itemStatus = itemLook
                ? (itemLook.name + (typeof item.coverage === 'number' ? ' · ' + coverage : ''))
                : coverage;
            return '<button type="button" id="spbEasySculptScope-' + esc(item.id) + '" class="spb-easy-sculpt-scope color' + (item.id === state.activeColorId ? ' active' : '') + '" data-sculpt-target="' + esc(item.id) + '" aria-pressed="' + (item.id === state.activeColorId ? 'true' : 'false') + '">' +
                '<i style="--target-color:' + esc(item.replacementColor || item.hex) + '"></i><span><b>' + esc(colorTargetName(item)) + '</b><small>' + esc(colorTargetPaintLabel(item) + ' · ' + itemStatus) + '</small></span></button>';
        }).join('');
        // [2026-08-09 S24] The tile used to be omitted entirely at the limit,
        // so the one moment a painter needs to know WHY they cannot add another
        // colour was the one moment nothing was on screen. It stays, disabled,
        // and says what to do instead.
        var addColorButton = state.colorTargets.length < MAX_COLOR_TARGETS
            ? '<button type="button" class="spb-easy-sculpt-scope add' + (state.pickingColor ? ' active' : '') + '" id="spbEasySculptAddColor" aria-pressed="' + (state.pickingColor ? 'true' : 'false') + '"><i>+</i><span><b>' + (state.pickingColor ? 'CLICK PAINT' : 'ADD COLOR') + '</b><small>' + (state.pickingColor ? 'Esc cancels' : 'Up to ' + MAX_COLOR_TARGETS) + '</small></span></button>'
            : '<button type="button" class="spb-easy-sculpt-scope add full" id="spbEasySculptAddColor" disabled aria-disabled="true" title="' + MAX_COLOR_TARGETS + ' colors is the limit. Remove one to add another."><i>\u2713</i><span><b>ALL ' + MAX_COLOR_TARGETS + ' COLORS USED</b><small>Remove one to add another</small></span></button>';

        var targetTools = '';
        if (target) {
            targetTools += '<div class="spb-easy-sculpt-reach"><span>COLOR REACH</span><div>' +
                [[18, 'TIGHT', 'only very close shades'], [30, 'NORMAL', 'this color and close shades'], [52, 'WIDE', 'include more nearby shades']].map(function (entry) {
                    var reachLabel = entry[1] + ' color reach — ' + entry[2];
                    return '<button type="button" id="spbEasySculptReach' + entry[0] + '" data-color-tolerance="' + entry[0] + '" class="' + (target.tolerance === entry[0] ? 'on' : '') + '" aria-pressed="' + (target.tolerance === entry[0] ? 'true' : 'false') + '" aria-label="' + esc(reachLabel) + '" title="' + esc(reachLabel) + '">' + entry[1] + '</button>';
                }).join('') + '</div><button type="button" class="remove" id="spbEasySculptRemoveColor">REMOVE COLOR</button></div>';
            targetTools += '<div class="spb-easy-sculpt-paint-color"><span><b>PAINT COLOR</b><small>Keep the original, or repaint only this detected color.</small></span><div>' +
                '<button type="button" id="spbEasySculptKeepPaint" class="' + (target.paintDecision === 'keep' ? 'on' : '') + '" aria-pressed="' + (target.paintDecision === 'keep' ? 'true' : 'false') + '">KEEP ORIGINAL</button>' +
                '<button type="button" id="spbEasySculptChangePaint" class="' + (target.paintDecision === 'change' ? 'on' : '') + '" aria-pressed="' + (target.paintDecision === 'change' ? 'true' : 'false') + '">CHANGE COLOR</button>' +
                '</div></div>';
            if (target.paintDecision === 'change') {
                var replacementMode = target.replacementMode === 'base' ? 'base' : 'solid';
                // The picker needs a useful starting swatch, but merely opening
                // CHANGE COLOR is not permission to flatten a varied paint area
                // to its sampled centroid. Keep replacementColor empty until an
                // actual picker/base/slider input so preview and export are both
                // byte-neutral at the first decision screen.
                var editorColor = target.replacementColor || target.hex;
                var replacementHsv = rgbToHsv(hexRgb(editorColor));
                targetTools += '<div class="spb-easy-sculpt-recolor-panel" role="group" aria-label="Change ' + esc(colorTargetName(target)) + ' paint color">' +
                    '<div class="spb-easy-sculpt-recolor-modes">' +
                        '<button type="button" id="spbEasySculptSolidColor" class="' + (replacementMode === 'solid' ? 'on' : '') + '" aria-pressed="' + (replacementMode === 'solid' ? 'true' : 'false') + '">SOLID COLOR</button>' +
                        '<button type="button" id="spbEasySculptBaseColor" class="' + (replacementMode === 'base' ? 'on' : '') + '" aria-pressed="' + (replacementMode === 'base' ? 'true' : 'false') + '">PAINT BOOTH BASE COLOR</button>' +
                    '</div>' +
                    (replacementMode === 'base'
                        ? '<label class="spb-easy-sculpt-recolor-source full">FIND A BASE COLOR<input type="search" id="spbEasySculptBaseColorSearch" value="' + esc(state.baseColorQuery || '') + '" placeholder="Try carbon, gold, chrome..." autocomplete="off"></label>' +
                          '<output class="spb-easy-sculpt-base-color-status" id="spbEasySculptBaseColorStatus" role="status" aria-live="polite"></output>' +
                          '<div class="spb-easy-sculpt-base-instruction"><b>CHOOSE FROM REAL THUMBNAILS</b><span>Each image is Paint Booth’s actual PAINT | SPEC preview. This step borrows its authored color; your next choice sets the finish.</span></div>' +
                          paintBaseLibraryHtml(target.replacementBaseId)
                        : '<label class="spb-easy-sculpt-recolor-source">NEW SOLID COLOR<span><input type="color" id="spbEasySculptPaintColor" value="' + esc(editorColor) + '" aria-label="New paint color"><output id="spbEasySculptPaintHex">' + esc(editorColor.toUpperCase()) + '</output></span></label>') +
                    '<label class="spb-easy-sculpt-recolor-slider"><span>HUE <output id="spbEasySculptHueValue">' + replacementHsv.h + '°</output></span><input type="range" id="spbEasySculptHue" min="0" max="359" value="' + replacementHsv.h + '"></label>' +
                    '<label class="spb-easy-sculpt-recolor-slider"><span>SATURATION <output id="spbEasySculptSaturationValue">' + replacementHsv.s + '%</output></span><input type="range" id="spbEasySculptSaturation" min="0" max="100" value="' + replacementHsv.s + '"></label>' +
                    '<label class="spb-easy-sculpt-recolor-slider"><span>BRIGHTNESS <output id="spbEasySculptBrightnessValue">' + replacementHsv.v + '%</output></span><input type="range" id="spbEasySculptBrightness" min="0" max="100" value="' + replacementHsv.v + '"></label>' +
                    '<button type="button" class="spb-easy-sculpt-color-next" id="spbEasySculptColorNext">NEXT · PICK THIS COLOR\'S FINISH →</button>' +
                '</div>';
            }
        }

        var scaleHtml = '';
        if (colorDecisionDone && lookSupportsScale(look)) {
            var scaleLabel = target ? (colorTargetName(target) + ' SCALE') : 'BASE SCALE';
            var scaleHelp = target ? ('Lower makes only ' + colorTargetName(target) + ' material details finer.') : 'Lower makes the material details finer.';
            var scaleAria = target ? (colorTargetName(target) + ' material scale') : 'Base material scale';
            scaleHtml = '<div class="spb-easy-sculpt-linked-scale">' +
                '<div class="spb-easy-sculpt-scale-head"><span><b>' + esc(scaleLabel) + '</b><small>' + esc(scaleHelp) + '</small></span><strong id="spbEasySculptScaleValue">' + Number(scale).toFixed(2) + '&times;</strong></div>' +
                '<input type="range" id="spbEasySculptScale" min="25" max="100" step="5" value="' + Math.round(scale * 100) + '" aria-label="' + esc(scaleAria) + '">' +
                '<div class="spb-easy-sculpt-scale-foot"><span>FINER</span><b>SPEC SCALE: MATCHED <em id="spbEasySculptSpecScaleValue">' + Number(scale).toFixed(2) + '&times;</em></b><span>ORIGINAL</span></div></div>';
        } else if (look) {
            scaleHtml = '<div class="spb-easy-sculpt-auto-scale"><b>SCALE: AUTOMATIC</b><span>This smart signature look sets its own detail size.</span></div>';
        }

        var impactHtml = colorDecisionDone ? '<div class="spb-easy-sculpt-impact" role="group" aria-label="Material impact for the whole paint">' +
            '<span><b>MATERIAL IMPACT</b><small>How strongly the whole plan reads in iRacing.</small></span><div>' +
            [['subtle', 'SUBTLE', 'Hold the materials back - closest to ordinary paint'],
             ['balanced', 'BALANCED', 'The default - materials read clearly without shouting'],
             ['bold', 'BOLD', 'Push the materials hard - most shine, flake and contrast']].map(function (entry) {
                var on = state.materialImpact === entry[0];
                return '<button type="button" id="spbEasySculptImpact-' + entry[0] + '" data-material-impact="' + entry[0] + '" class="' + (on ? 'on' : '') + '" aria-pressed="' + (on ? 'true' : 'false') + '" title="' + esc(entry[2]) + '">' + entry[1] + '</button>';
            }).join('') + '</div></div>' : '';

        return '<section class="spb-easy-sculpt-target-editor">' +
            '<div class="spb-easy-sculpt-target-title"><span><b>EDIT ONE AREA AT A TIME</b><small>Choose what you are editing, or let Shokker build the color plan.</small></span>' + titleAction + '</div>' +
            '<div class="spb-easy-sculpt-scope-picker"><div class="spb-easy-sculpt-scopes" role="group" aria-label="Materials on this paint">' + targetButtons + '</div>' + addColorButton + '</div>' +
            detectedPaletteHtml() +
            (target && !colorDecisionDone ? '<div class="spb-easy-sculpt-target-prompt"><b>FIRST QUESTION</b><span>Keep ' + esc(colorTargetName(target)) + ' as painted, or change its color. Then you will pick its finish.</span></div>' :
                (target && !target.look ? '<div class="spb-easy-sculpt-target-prompt"><b>SECOND QUESTION · PICK A FINISH</b><span>Only ' + esc(colorTargetLabel(target)) + ' will change.</span></div>' : '')) +
            targetTools + scaleHtml + impactHtml + '</section>';
    }

    function filteredLooks() {
        var q = String(state.libraryQuery || '').trim().toLowerCase();
        var guidance = window.spbEasySculptGuidance;
        var scoped = (state.looks || []).filter(function (look) {
            var kindOk = state.libraryKind === 'all' ||
                (state.libraryKind === 'recommended' && state.recommendedLookKeys.indexOf(lookKey(look)) !== -1) ||
                (state.libraryKind === 'spec' && look.kind !== 'catalog') ||
                (state.libraryKind === 'catalog' && look.kind === 'catalog');
            return kindOk;
        });
        state.librarySearchRelaxed = false;
        state.librarySearchToppedUp = false;
        if (!q) return scoped;
        if (guidance && typeof guidance.scoreLookSearch === 'function') {
            var rows = scoped.map(function (look, index) {
                return { look: look, index: index, score: guidance.scoreLookSearch(look, q) };
            }).filter(function (row) { return row.score >= 0; }).sort(function (a, b) {
                return b.score - a.score || a.index - b.index;
            });
            // [2026-08-09 S30] MEASURED: "candy red" returned exactly ONE look
            // (Carbon Red) and "matte black" seven that matched neither word
            // together, because the closest-match shelf was only reached when
            // the strict pass found NOTHING. One weak hit is worse than none -
            // it looks like the answer. Top a thin set up instead: strict hits
            // keep their places at the front, the shelf fills in behind them.
            if (rows.length < SEARCH_THIN_RESULTS) {
                var already = {};
                rows.forEach(function (row) { already[lookKey(row.look)] = true; });
                var relaxedRows = scoped.map(function (look, index) {
                    return { look: look, index: index, score: guidance.scoreLookSearch(look, q, true) };
                }).filter(function (row) {
                    return row.score >= 0 && !already[lookKey(row.look)];
                }).sort(function (a, b) {
                    return b.score - a.score || a.index - b.index;
                });
                if (relaxedRows.length) {
                    // the note must stay truthful: only say "closest matches"
                    // when the shelf is doing the work, not when it is topping
                    // up a couple of real hits
                    state.librarySearchRelaxed = !rows.length;
                    state.librarySearchToppedUp = rows.length > 0;
                    rows = rows.concat(relaxedRows);
                }
            }
            return rows.map(function (row) { return row.look; });
        }
        return scoped.filter(function (look) {
            if (guidance && typeof guidance.matchesLookSearch === 'function') return guidance.matchesLookSearch(look, q);
            var hay = [look.name, look.id, look.category, look.description, (look.tags || []).join(' ')].join(' ').toLowerCase();
            return hay.indexOf(q) !== -1;
        });
    }

    function lookPickerHtml() {
        var all = state.looks || [];
        var specCount = all.filter(function (look) { return look.kind !== 'catalog'; }).length;
        var catalogCount = all.length - specCount;
        var fullMatches = filteredLooks();
        var categoryBrowse = !String(state.libraryQuery || '').trim() && state.libraryKind !== 'recommended';
        var matches = categoryBrowse && state.libraryCategory
            ? fullMatches.filter(function (look) { return String(look.category || 'Other') === state.libraryCategory; })
            : fullMatches;
        var shown = matches.slice(0, state.libraryLimit);
        var selectedLook = activeTargetLook();
        var selectedKey = lookKey(selectedLook);
        var guidance = window.spbEasySculptGuidance;
        var cards = shown.map(function (look) {
            var selected = lookKey(look) === selectedKey;
            var paintAware = !look.thumb && look.paintThumbContext === state.recommendationKey && !!look.paintThumb;
            var thumb = look.thumb || (paintAware ? look.paintThumb : '');
            // [2026-08-09 S7] On the paint-aware shelf, the reason beats the
            // category: "matches your blue" tells the painter why this card is
            // in front of them, "Paint Booth" does not.
            var recWhy = state.libraryKind === 'recommended' ? (look.recReason || '') : '';
            var cardMeta = recWhy ? recWhy
                : look.kind === 'catalog' && guidance && typeof guidance.describeLook === 'function'
                ? guidance.describeLook(look)
                : (look.category || (look.kind === 'catalog' ? 'Paint Booth' : 'Spec Look'));
            return '<span class="spb-easy-sculpt-li" role="listitem">' +
                '<button type="button" tabindex="-1" class="spb-easy-sculpt-look' + (selected ? ' selected' : '') + '" data-look-key="' + esc(lookKey(look)) + '" aria-pressed="' + (selected ? 'true' : 'false') + '" title="' + esc(look.description || look.name) + '">' +
                lookArtHtml(look, thumb, paintAware) + '<span><b>' + esc(look.name) + '</b><small>' + esc(cardMeta) + '</small></span></button></span>';
        }).join('');
        // [2026-08-08 S2 - owner: "no easy way to just scroll them"]
        // Paging already existed and WORKS (measured: 60 -> 120 cards per
        // click). The problem is where it lives: the only control sits AFTER
        // the grid, measured at y=3657 in a 1000px viewport - about 2,650px
        // below the fold, behind all 60 cards. Reaching look #61 of 442 meant
        // scrolling the whole grid, seven times over.
        // So the same control also goes at the TOP of an open family, where the
        // buyer already is, with an explicit SHOW ALL for the determined case.
        var pageRemaining = Math.max(0, matches.length - shown.length);
        var pageTopHtml = '';
        if (pageRemaining && categoryBrowse && state.libraryCategory) {
            pageTopHtml = '<div class="spb-easy-sculpt-page-top">' +
                '<span>Showing <b>' + shown.length.toLocaleString() + '</b> of ' +
                matches.length.toLocaleString() + '</span>' +
                '<button type="button" data-page-more="next">SHOW ' +
                Math.min(LOOK_PAGE_SIZE, pageRemaining).toLocaleString() + ' MORE</button>' +
                '<button type="button" data-page-more="all">SHOW ALL ' +
                matches.length.toLocaleString() + '</button></div>';
        }
        var previousLook = state.previousLooks[activeTargetKey()];
        var selected = selectedLook ? '<div class="spb-easy-sculpt-selected"><span>' + esc(activeTargetLabel()) + '</span><b>' + esc(selectedLook.name) + '</b><small>' + esc(selectedLook.description || selectedLook.category || '') + '</small><div class="spb-easy-sculpt-selected-actions">' +
            (previousLook ? '<button type="button" id="spbEasySculptPreviousLook" title="Go back to ' + esc(previousLook.name) + ' (Ctrl+Z)">&#8592; BACK TO ' + esc(previousLook.name) + '</button>' : '') +
            '<button type="button" id="spbEasySculptNextLook" title="Step to the next look and preview it here">TRY NEXT LOOK &#8594;</button>' +
            (state.phase === 'ready' ? '<button type="button" id="spbEasySculptGoSave" title="Scroll down to the save step - nothing is written yet">GO TO SAVE &#8595;</button>' : '') + '</div></div>' : '';
        var previewTarget = activeColorTarget();
        var recommendationNote = state.recommendationLoading
            ? (previewTarget ? 'Painting these picks onto only ' + colorTargetName(previewTarget) + '...' : 'Painting these picks onto your livery...')
            : (previewTarget ? 'Only ' + colorTargetName(previewTarget) + ' changes in these previews.' : 'Top picks are previewed on your paint. Everything else stays available.');
        var profile = state.paintProfile && state.paintProfile.summary
            ? '<div class="spb-easy-sculpt-profile"><span>' + (previewTarget ? 'SHOKKER PICKED FOR THIS COLOR' : 'SHOKKER READ THIS PAINT AS') + '</span><b>' + esc(previewTarget ? (colorTargetName(previewTarget) + ' · ' + previewTarget.hex) : paintProfileLabel()) + '</b><small>' + esc(recommendationNote) + '</small></div>'
            : '';
        var browseContent = '';
        var categoryCounts = {};
        if (!state.looksLoaded) {
            browseContent = state.looksError
                ? '<div class="spb-easy-sculpt-library-empty failed" role="alert">' +
                  '<b>THE LOOK LIBRARY DID NOT LOAD</b>' +
                  '<span>Shokker could not reach its catalog, so only the built-in looks are here. Your paint is safe.</span>' +
                  '<button type="button" id="spbEasySculptRetryLooks">TRY LOADING IT AGAIN</button></div>'
                : '<div class="spb-easy-sculpt-library-empty">Loading the complete look library...</div>';
        } else if (categoryBrowse) {
            fullMatches.forEach(function (look) {
                var name = String(look.category || 'Other');
                categoryCounts[name] = (categoryCounts[name] || 0) + 1;
            });
            browseContent = '<div class="spb-easy-sculpt-category-list">' + Object.keys(categoryCounts).sort(compareCategories).map(function (name) {
                var open = name === state.libraryCategory;
                return '<details class="spb-easy-sculpt-category"' + (open ? ' open' : '') + '>' +
                    '<summary data-look-category="' + esc(name) + '"><span class="spb-easy-sculpt-category-title"><b>' + esc(name) + '</b><small>' + esc(lookCategoryDescription(name)) + '</small></span><em>' + categoryCounts[name].toLocaleString() + ' looks</em></summary>' +
                    (open ? (cards ? pageTopHtml + '<div class="spb-easy-sculpt-look-grid" role="list" aria-label="' + esc(name) + ' looks">' + cards + '</div>' : '<div class="spb-easy-sculpt-library-empty">No looks in this family.</div>') : '') +
                    '</details>';
            }).join('') + '</div>';
        } else {
            browseContent = cards ? '<div class="spb-easy-sculpt-look-grid" role="list" aria-label="Looks">' + cards + '</div>' : '<div class="spb-easy-sculpt-library-empty"><b>No looks match that yet.</b><span>Try shiny, matte, sparkle, carbon, color shift, subtle, or wild.</span></div>';
        }
        var showingText = categoryBrowse
            ? (state.libraryCategory
                ? 'Showing ' + shown.length.toLocaleString() + ' of ' + matches.length.toLocaleString() + ' in ' + state.libraryCategory
                : Object.keys(categoryCounts).length.toLocaleString() + ' described families · ' + fullMatches.length.toLocaleString() + ' looks')
            : 'Showing ' + shown.length.toLocaleString() + ' of ' + matches.length.toLocaleString() + (state.libraryQuery ? (state.librarySearchRelaxed ? ' closest matches' : (state.librarySearchToppedUp ? ' matches, closest first' : ' matches')) : ' looks');
        return '<div class="spb-easy-sculpt-library">' +
            '<div class="spb-easy-sculpt-library-count"><b>' + all.length.toLocaleString() + ' LOOKS</b><span>Nothing removed</span></div>' +
            '<div class="spb-easy-sculpt-library-tools"><div class="spb-easy-sculpt-search-field"><input type="search" id="spbEasySculptLookSearch" value="' + esc(state.libraryQuery) + '" placeholder="Describe it: shiny purple, subtle carbon..." aria-label="Describe or search all Spec Sculpt looks">' +
            (state.libraryQuery ? '<button type="button" class="spb-easy-sculpt-search-clear" id="spbEasySculptSearchClear" aria-label="Clear look search" title="Clear search">&times;</button>' : '') +
            '</div><button type="button" id="spbEasySculptSurprise"' + (!all.length ? ' disabled' : '') + ' title="Jump to a random look from the whole library">&#127922; SURPRISE ME</button></div>' +
            '<div class="spb-easy-sculpt-library-tabs" role="tablist" aria-label="Look library sections">' +
            libraryTabHtml('recommended', previewTarget ? 'FOR THIS COLOR' : 'FOR THIS PAINT', state.recommendedLookKeys.length) +
            libraryTabHtml('all', 'ALL', all.length) +
            libraryTabHtml('spec', 'SPEC LOOKS', specCount) +
            libraryTabHtml('catalog', 'PAINT BOOTH', catalogCount) + '</div>' +
            (state.libraryKind === 'recommended' ? profile : '') + selected +
            browseContent +
            ((!categoryBrowse || state.libraryCategory) && shown.length < matches.length ? '<button type="button" class="spb-easy-sculpt-more" id="spbEasySculptMore">SHOW ' + Math.min(LOOK_PAGE_SIZE, matches.length - shown.length) + ' MORE</button>' : '') +
            '<div class="spb-easy-sculpt-showing" role="status" aria-live="polite">' + esc(showingText) + '</div></div>';
    }

    function lookCategoryDescription(name) {
        var key = String(name || '').toLowerCase();
        if (/chrome|metal|alloy|steel|gold|copper|bronze/.test(key)) return 'Reflective, machined and metallic material behavior.';
        if (/carbon|weave|fiber|textile|fabric/.test(key)) return 'Fine woven and technical surface textures.';
        if (/candy|pearl|flake|spark|glitter/.test(key)) return 'Layered color, suspended flake and deep clearcoat.';
        if (/holo|shift|chameleon|prism|irides/.test(key)) return 'Angle-reactive color and optical movement.';
        if (/matte|satin|rubber|ceramic|stone/.test(key)) return 'Soft, restrained and tactile finishes.';
        if (/fract|flame|wild|experimental|shokk/.test(key)) return 'High-impact signature materials and motion.';
        if (/gradient|color|paint/.test(key)) return 'Authored color behavior with a physical spec finish.';
        return 'Open this family to browse its material looks.';
    }

    // [2026-08-08 S3] The main page does not sort its families alphabetically -
    // it renders them in the CURATED declaration order the catalog file sets:
    // BASE_GROUPS, then "More Bases", then SPECIAL_GROUPS, then "More Specials"
    // (spb-easy-mode.js buildCatalogSections). Spec Sculpt was sorting by name,
    // which buries Foundation in the middle of the list and scatters the
    // FRACTURED families by whichever emoji happens to lead their label.
    // Spec Sculpt's OWN offerings stay on top - they are what this screen is
    // for - and everything after them follows the app's order exactly.
    var SCULPT_FIRST = ['START HERE \u00b7 AUTO-SCULPT', 'Signature', 'Spec Looks'];
    var _catRank = null;
    function canonicalCategoryRank() {
        if (_catRank) return _catRank;
        var rank = {}, i = 0;
        SCULPT_FIRST.forEach(function (n) { if (!(n in rank)) rank[n] = i++; });
        var found = 0;
        try {
            var bg = (typeof BASE_GROUPS !== 'undefined') ? BASE_GROUPS : window.BASE_GROUPS;
            if (bg) Object.keys(bg).forEach(function (n) { if (!(n in rank)) { rank[n] = i++; found++; } });
        } catch (e) {}
        rank['More Bases'] = i++;
        try {
            var sg = (typeof SPECIAL_GROUPS !== 'undefined') ? SPECIAL_GROUPS : window.SPECIAL_GROUPS;
            if (sg) Object.keys(sg).forEach(function (n) { if (!(n in rank)) { rank[n] = i++; found++; } });
        } catch (e) {}
        rank['More Specials'] = i++;
        // Same rule as the group index: do not memoise an empty answer just
        // because the catalog script has not parsed yet.
        if (found) _catRank = rank;
        return rank;
    }
    function compareCategories(a, b) {
        var rank = canonicalCategoryRank();
        var ra = (a in rank) ? rank[a] : 99999;
        var rb = (b in rank) ? rank[b] : 99999;
        if (ra !== rb) return ra - rb;
        return String(a).localeCompare(String(b));
    }

    // [2026-08-08 S14] MEASURED by the S4 audit: 60 look cards were 60 separate
    // tab stops, so a keyboard buyer passed every card to reach SAVE. Easy Mode
    // solved this in E41 with roving focus - one tab stop for the whole list,
    // arrows to move inside it - and this is the same pattern, so the two
    // libraries behave identically.
    function sculptLookCards() {
        var rail = document.getElementById('spbEasyRail');
        if (!rail) return [];
        return Array.prototype.filter.call(
            rail.querySelectorAll('.spb-easy-sculpt-look'),
            function (el) { return el.offsetParent !== null; });
    }
    function syncSculptRoving() {
        var cards = sculptLookCards();
        if (!cards.length) return;
        var current = null;
        for (var i = 0; i < cards.length; i++) {
            if (cards[i].classList.contains('selected')) { current = cards[i]; break; }
        }
        if (!current) current = cards[0];
        cards.forEach(function (c) { c.tabIndex = (c === current) ? 0 : -1; });
    }
    function focusSculptCard(card, cards) {
        if (!card) return;
        (cards || []).forEach(function (c) { c.tabIndex = -1; });
        card.tabIndex = 0;
        try { card.focus({ preventScroll: true }); } catch (e) { try { card.focus(); } catch (e2) {} }
        try { card.scrollIntoView({ block: 'nearest' }); } catch (e) {}
    }
    function wireSculptRoving() {
        var rail = document.getElementById('spbEasyRail');
        if (!rail || rail._spbSculptRovingWired) return;
        rail._spbSculptRovingWired = true;
        rail.addEventListener('keydown', function (event) {
            var card = event.target && event.target.closest
                ? event.target.closest('.spb-easy-sculpt-look') : null;
            if (!card) return;
            var keys = { ArrowDown: 1, ArrowUp: 1, ArrowLeft: 1, ArrowRight: 1,
                         Home: 1, End: 1, PageDown: 1, PageUp: 1 };
            if (!keys[event.key]) return;
            var cards = sculptLookCards();
            var i = cards.indexOf(card);
            if (i === -1) return;
            event.preventDefault();
            event.stopPropagation();
            // The grid wraps, so left/right and up/down both walk the sequence -
            // trying to compute a row width from CSS grid would break the moment
            // the rail is resized.
            var next = i;
            if (event.key === 'ArrowDown' || event.key === 'ArrowRight') next = Math.min(cards.length - 1, i + 1);
            else if (event.key === 'ArrowUp' || event.key === 'ArrowLeft') next = Math.max(0, i - 1);
            else if (event.key === 'PageDown') next = Math.min(cards.length - 1, i + 8);
            else if (event.key === 'PageUp') next = Math.max(0, i - 8);
            else if (event.key === 'Home') next = 0;
            else if (event.key === 'End') next = cards.length - 1;
            focusSculptCard(cards[next], cards);
        });
    }

    // [2026-08-09 S16] The mirrored SAVE under the sculpted paint has to track
    // the REAL button continuously, not once. Both are re-rendered on their own
    // schedules (the rail and the middle column), so this re-reads the primary
    // by id every time - a captured node goes stale the moment the rail
    // re-renders, and a detached node still runs its click listener, which is
    // how the proxy came to fire zero POSTs while looking perfectly clickable.
    function syncSaveProxy() {
        var proxy = $('spbEasySculptSaveProxy');
        if (!proxy) return;
        var save = $('spbEasySculptSave');
        if (save) {
            proxy.textContent = save.textContent;
            proxy.disabled = save.disabled;
            if (save.disabled) proxy.setAttribute('aria-disabled', 'true');
            else proxy.removeAttribute('aria-disabled');
        } else {
            // MEASURED: the rail drops its SAVE entirely while a colour still
            // needs a look. Stay visible (owner: SAVE must always be under the
            // sculpted paint) but stop promising something that cannot happen.
            proxy.textContent = 'FINISH THE COLORS ABOVE TO SAVE';
            proxy.disabled = true;
            proxy.setAttribute('aria-disabled', 'true');
        }
        if (proxy._spbSaveProxyWired) return;
        proxy._spbSaveProxyWired = true;
        proxy.addEventListener('click', function () {
            var live = $('spbEasySculptSave');
            if (live && !live.disabled) { live.click(); return; }
            // Not ready - take the painter TO the reason instead of a dead click.
            var reason = live || document.querySelector('.spb-easy-sculpt-plan-block')
                || document.querySelector('#spbEasyRail .spb-easy-sculpt-target-editor')
                || $('spbEasyRail');
            if (!reason) return;
            try { reason.scrollIntoView({ behavior: 'smooth', block: 'center' }); }
            catch (e) { reason.scrollIntoView(); }
        });
    }

    function libraryTabHtml(kind, label, count) {
        var selected = state.libraryKind === kind;
        return '<button type="button" role="tab" aria-selected="' + (selected ? 'true' : 'false') + '" tabindex="' + (selected ? '0' : '-1') + '" data-look-kind="' + kind + '" class="' + (selected ? 'on' : '') + '">' + label + ' <small>' + Number(count || 0).toLocaleString() + '</small></button>';
    }

    function findLook(key) {
        return (state.looks || []).filter(function (look) { return lookKey(look) === key; })[0] || null;
    }

    function beginSmartStartingPoint() {
        var smart = findLook('mode:zoned') || (state.looks || [])[0];
        if (!smart) {
            render();
            loadPaintAwareRecommendations();
            return;
        }
        state.selectedLook = smart;
        state.libraryKind = 'recommended';
        state.libraryQuery = '';
        state.libraryLimit = LOOK_PAGE_SIZE;
        state.recoveredPlan = false;
        generatePreview('Auto-sculpting a smart starting point...');
    }

    function captureLibraryView(fallbackLookKey) {
        var body = document.querySelector('#spbEasyRail .spb-easy-sculpt-rail-body');
        state.libraryScrollTop = body ? body.scrollTop : 0;
        var active = document.activeElement;
        state.focusReturnId = active && active.id ? active.id : '';
        state.focusReturnLookKey = active && active.getAttribute
            ? (active.getAttribute('data-look-key') || fallbackLookKey || '')
            : (fallbackLookKey || '');
        var anchor = state.focusReturnLookKey ? Array.prototype.filter.call(document.querySelectorAll('#spbEasyRail [data-look-key]'), function (card) {
            return card.getAttribute('data-look-key') === state.focusReturnLookKey;
        })[0] : null;
        if (body && anchor) {
            state.libraryAnchorOffset = anchor.getBoundingClientRect().top - body.getBoundingClientRect().top;
        } else {
            state.libraryAnchorOffset = null;
        }
    }

    function restoreLibraryView() {
        var top = Number(state.libraryScrollTop) || 0;
        var focusId = state.focusReturnId;
        var focusKey = state.focusReturnLookKey;
        var anchorOffset = state.libraryAnchorOffset;
        window.requestAnimationFrame(function () {
            var body = document.querySelector('#spbEasyRail .spb-easy-sculpt-rail-body');
            if (body) body.scrollTop = top;
            var focusTarget = focusId ? $(focusId) : null;
            var anchorCard = focusKey ? Array.prototype.filter.call(document.querySelectorAll('#spbEasyRail [data-look-key]'), function (card) {
                    return card.getAttribute('data-look-key') === focusKey;
                })[0] || null : null;
            if (!focusTarget) focusTarget = anchorCard;
            if (focusTarget) {
                try { focusTarget.focus({ preventScroll: true }); }
                catch (error) { try { focusTarget.focus(); } catch (ignored) {} }
            }

            // Re-anchor while the rebuilt rail settles. Replacing the rail
            // temporarily removes the clicked button, and image/font/layout work
            // can change the content height after the first animation frame. A
            // ResizeObserver plus bounded fallbacks keeps the chosen card under
            // the user's eyes without fighting a new wheel/touch/pointer action.
            var guarding = true;
            var observer = null;
            var settle = function () {
                if (!guarding || !body || !anchorCard || typeof anchorOffset !== 'number') return;
                var currentOffset = anchorCard.getBoundingClientRect().top - body.getBoundingClientRect().top;
                body.scrollTop += currentOffset - anchorOffset;
                state.libraryScrollTop = body.scrollTop;
                persistRecoveryPlan();
            };
            var stopGuarding = function () {
                guarding = false;
                if (observer) observer.disconnect();
            };
            ['wheel', 'touchstart', 'pointerdown'].forEach(function (eventName) {
                body.addEventListener(eventName, stopGuarding, { once: true, passive: true });
            });
            settle();
            window.requestAnimationFrame(settle);
            [60, 220, 700, 1400].forEach(function (delay) { window.setTimeout(settle, delay); });
            if (typeof ResizeObserver !== 'undefined') {
                observer = new ResizeObserver(settle);
                var library = body.querySelector('.spb-easy-sculpt-library');
                if (library) observer.observe(library);
            }
            window.setTimeout(stopGuarding, 1800);
        });
    }

    function selectLook(look) {
        if (!look || (!state.file && !state.sourcePath)) return;
        captureLibraryView(lookKey(look));
        var target = activeColorTarget();
        var current = target ? target.look : state.selectedLook;
        // Clicking the already-selected card used to rebuild the identical
        // 2048 preview for several seconds. Selected means applied; Retry owns
        // the explicit rebuild path after an error.
        if (current && lookKey(current) === lookKey(look)) return;
        state.advanceToSaveAfterPreview = !!target && !current;
        var targetKey = activeTargetKey();
        if (current && lookKey(current) !== lookKey(look)) state.previousLooks[targetKey] = current;
        if (target) target.look = look;
        else state.selectedLook = look;
        state.recoveredPlan = false;
        state.error = '';
        state.errorContext = '';
        state.exportOpen = false;
        generatePreview('Building ' + look.name + '...');
    }

    // [2026-08-09 S31] The one-step look undo already exists and works - the
    // rail's "BACK TO <look>" button reverts the car exactly and then offers
    // the way forward again. It just was not on Ctrl+Z, so a painter trying a
    // look they disliked had to find a button instead of pressing the key
    // every other app answers. The header UNDO is left to Easy Mode's own
    // paint-edit history; Spec Sculpt does not write to it and must not make
    // it claim otherwise.
    var sculptUndoKeysWired = false;
    function wireSculptUndoKeys() {
        if (sculptUndoKeysWired) return;
        sculptUndoKeysWired = true;
        document.addEventListener('keydown', function (event) {
            if (!mounted) return;
            if (!event.ctrlKey && !event.metaKey) return;
            var key = String(event.key || '').toLowerCase();
            if (key !== 'z' && key !== 'y') return;
            // E27: a text field owns its own undo. The look search sits right
            // here, and stealing Ctrl+Z from it would be a regression.
            var el = event.target;
            var tag = el && el.tagName ? el.tagName.toLowerCase() : '';
            if (tag === 'input' || tag === 'textarea' || tag === 'select'
                || (el && el.isContentEditable)) return;
            if (!state.previousLooks || !state.previousLooks[activeTargetKey()]) return;
            event.preventDefault();
            event.stopPropagation();
            restorePreviousLook();
        }, true);
    }

    function restorePreviousLook() {
        var target = activeColorTarget();
        var targetKey = activeTargetKey();
        var previous = state.previousLooks[targetKey];
        var current = target ? target.look : state.selectedLook;
        if (!previous) return;
        captureLibraryView(lookKey(previous));
        state.previousLooks[targetKey] = current;
        if (target) target.look = previous;
        else state.selectedLook = previous;
        state.recoveredPlan = false;
        state.error = '';
        state.errorContext = '';
        state.exportOpen = false;
        generatePreview('Bringing back ' + previous.name + '...');
    }

    function surpriseLook() {
        var pool = filteredLooks();
        var current = lookMaterialKey(activeTargetLook());
        var choices = pool.filter(function (look) { return lookMaterialKey(look) !== current; });
        if (!choices.length) {
            // A one-result search must never make Surprise look broken. Open the
            // full library only when the visible scope has no different choice.
            state.libraryQuery = '';
            state.libraryKind = 'all';
            state.libraryLimit = LOOK_PAGE_SIZE;
            choices = (state.looks || []).filter(function (look) { return lookMaterialKey(look) !== current; });
        }
        if (!choices.length) return;
        selectLook(choices[Math.floor(Math.random() * choices.length)]);
    }

    function nextLook() {
        var pool = filteredLooks();
        var current = lookMaterialKey(activeTargetLook());
        var hasDifferent = pool.some(function (look) { return lookMaterialKey(look) !== current; });
        if (!hasDifferent) {
            // "Try next" is a promise of visible change. If an exact search or
            // narrow tab contains only the current look, return to the twelve
            // paint-aware picks instead of quietly rebuilding the same map.
            pool = state.recommendedLookKeys.map(findLook).filter(Boolean);
            state.libraryQuery = '';
            state.libraryKind = pool.length > 1 ? 'recommended' : 'all';
            state.libraryLimit = LOOK_PAGE_SIZE;
            if (pool.length < 2) pool = state.looks || [];
        }
        if (!pool.length) return;
        var index = pool.findIndex(function (look) { return lookMaterialKey(look) === current; });
        var next = pool[(index + 1 + pool.length) % pool.length];
        if (lookMaterialKey(next) === current) {
            next = pool.filter(function (look) { return lookMaterialKey(look) !== current; })[0];
        }
        if (next) selectLook(next);
    }

    function advanceToLookPicker() {
        // SPB beta 2026-07-21: the owner's teaching order is literal. Once the
        // paint-color decision is made, move directly to question two instead
        // of leaving the finish shelf below the destination/install card.
        window.requestAnimationFrame(function () {
            var body = document.querySelector('#spbEasyRail .spb-easy-sculpt-rail-body');
            var library = body && body.querySelector('.spb-easy-sculpt-library');
            if (!body || !library) return;
            var top = Math.max(0, body.scrollTop + library.getBoundingClientRect().top - body.getBoundingClientRect().top - 10);
            body.scrollTop = top;
            state.libraryScrollTop = top;
            state.focusReturnId = 'spbEasySculptLookSearch';
            state.focusReturnLookKey = '';
            state.libraryAnchorOffset = null;
            persistRecoveryPlan();
            var search = $('spbEasySculptLookSearch');
            try { if (search) search.focus({ preventScroll: true }); } catch (e) { try { if (search) search.focus(); } catch (ignored) {} }
        });
    }

    function advanceToInstallCard() {
        window.requestAnimationFrame(function () {
            var body = document.querySelector('#spbEasyRail .spb-easy-sculpt-rail-body');
            var install = body && body.querySelector('.spb-easy-sculpt-export');
            if (!body || !install) return;
            var top = Math.max(0, body.scrollTop + install.getBoundingClientRect().top - body.getBoundingClientRect().top - 10);
            body.scrollTop = top;
            state.libraryScrollTop = top;
            state.focusReturnId = 'spbEasySculptSave';
            state.focusReturnLookKey = '';
            state.libraryAnchorOffset = null;
            persistRecoveryPlan();
            var save = $('spbEasySculptSave');
            try { if (save) save.focus({ preventScroll: true }); } catch (e) { try { if (save) save.focus(); } catch (ignored) {} }
        });
    }

    // [2026-08-09 S25] MEASURED: the scope row was one tab stop per button - 3
    // with a single colour, 8 with every slot filled - so reaching anything
    // past it meant tabbing through every colour. S14 did this for the look
    // grid; this is the same toolbar pattern, sharing its behaviour so the two
    // rows do not feel like different apps.
    function scopeButtons() {
        var rail = document.getElementById('spbEasyRail');
        if (!rail) return [];
        return Array.prototype.filter.call(
            rail.querySelectorAll('.spb-easy-sculpt-scope'),
            function (el) { return el.offsetParent !== null && !el.disabled; });
    }
    function syncScopeRoving() {
        var items = scopeButtons();
        if (!items.length) return;
        var current = null;
        for (var i = 0; i < items.length; i++) {
            if (items[i].getAttribute('aria-pressed') === 'true'
                || items[i].classList.contains('active')) { current = items[i]; break; }
        }
        if (!current) current = items[0];
        items.forEach(function (el) { el.tabIndex = (el === current) ? 0 : -1; });
    }
    function wireScopeRoving() {
        var rail = document.getElementById('spbEasyRail');
        if (!rail || rail._spbScopeRovingWired) return;
        rail._spbScopeRovingWired = true;
        rail.addEventListener('keydown', function (event) {
            var el = event.target && event.target.closest
                ? event.target.closest('.spb-easy-sculpt-scope') : null;
            if (!el) return;
            var keys = { ArrowLeft: -1, ArrowUp: -1, ArrowRight: 1, ArrowDown: 1, Home: 0, End: 0 };
            if (!(event.key in keys)) return;
            var items = scopeButtons();
            var i = items.indexOf(el);
            if (i === -1) return;
            event.preventDefault();
            event.stopPropagation();
            var next = event.key === 'Home' ? 0
                : event.key === 'End' ? items.length - 1
                : Math.max(0, Math.min(items.length - 1, i + keys[event.key]));
            var target = items[next];
            if (!target) return;
            items.forEach(function (x) { x.tabIndex = -1; });
            target.tabIndex = 0;
            try { target.focus({ preventScroll: true }); } catch (e) { try { target.focus(); } catch (e2) {} }
            try { target.scrollIntoView({ block: 'nearest', inline: 'nearest' }); } catch (e) {}
        });
    }

    function wireTargetEditor() {
        wireScopeRoving();
        syncScopeRoving();
        var autoColors = $('spbEasySculptAutoColors');
        if (autoColors) autoColors.addEventListener('click', autoSculptColors);
        Array.prototype.forEach.call(document.querySelectorAll('#spbEasyRail [data-sculpt-target]'), function (button) {
            button.addEventListener('click', function () {
                var id = button.getAttribute('data-sculpt-target');
                // Scope changes rebuild both stage and rail. Capture the real
                // control before replacement, then use the same proven restore
                // path as look/scale/impact changes so keyboard focus and the
                // user's rail position survive the rebuild.
                captureLibraryView();
                state.focusReturnId = button.id;
                state.focusReturnLookKey = '';
                state.libraryAnchorOffset = null;
                state.activeColorId = id === 'whole' ? '' : id;
                state.pickingColor = false;
                state.recoveredPlan = false;
                state.materialSummary = '';
                state.materialMetrics = {};
                persistRecoveryPlan();
                refreshRecommendations();
                render();
                restoreLibraryView();
                loadPaintAwareRecommendations();
            });
        });
        var add = $('spbEasySculptAddColor');
        if (add) add.addEventListener('click', function () {
            state.pickingColor = !state.pickingColor;
            if (state.pickingColor) { state.showBigResult = false; state.showSpecMap = false; }
            render();
            window.requestAnimationFrame(function () {
                var focusTarget = state.pickingColor ? $('spbEasySculptSourcePick') : $('spbEasySculptAddColor');
                if (focusTarget) focusTarget.focus();
            });
        });
        var remove = $('spbEasySculptRemoveColor');
        if (remove) remove.addEventListener('click', function () {
            var target = activeColorTarget();
            if (!target) return;
            delete state.previousLooks[target.id];
            state.colorTargets = state.colorTargets.filter(function (item) { return item.id !== target.id; });
            state.activeColorId = '';
            state.pickingColor = false;
            state.recoveredPlan = false;
            refreshRecommendations();
            generatePreview('Removing that color material...');
        });
        var keepPaint = $('spbEasySculptKeepPaint');
        if (keepPaint) keepPaint.addEventListener('click', function () {
            var target = activeColorTarget(); if (!target) return;
            target.paintDecision = 'keep';
            target.replacementColor = '';
            target.replacementMode = 'solid';
            target.replacementBaseId = '';
            state.baseColorQuery = '';
            state.recoveredPlan = false;
            persistRecoveryPlan();
            render();
            advanceToLookPicker();
        });
        var changePaint = $('spbEasySculptChangePaint');
        if (changePaint) changePaint.addEventListener('click', function () {
            var target = activeColorTarget(); if (!target) return;
            target.paintDecision = 'change';
            // Changing the color opens the editor without repainting anything yet.
            // The driver should see the result move only after making a deliberate choice.
            target.replacementMode = target.replacementMode === 'base' ? 'base' : 'solid';
            state.recoveredPlan = false;
            persistRecoveryPlan();
            render();
            window.requestAnimationFrame(function () {
                var picker = $('spbEasySculptPaintColor') || $('spbEasySculptBaseColorSearch');
                try { if (picker) picker.focus({ preventScroll: true }); } catch (e) {}
            });
        });
        var solidColorMode = $('spbEasySculptSolidColor');
        if (solidColorMode) solidColorMode.addEventListener('click', function () {
            var target = activeColorTarget(); if (!target) return;
            target.replacementMode = 'solid';
            target.replacementBaseId = '';
            persistRecoveryPlan();
            render();
            window.requestAnimationFrame(function () { try { $('spbEasySculptPaintColor').focus({ preventScroll: true }); } catch (e) {} });
        });
        var baseColorMode = $('spbEasySculptBaseColor');
        if (baseColorMode) baseColorMode.addEventListener('click', function () {
            var target = activeColorTarget(); if (!target) return;
            target.replacementMode = 'base';
            persistRecoveryPlan();
            render();
            window.requestAnimationFrame(function () { try { $('spbEasySculptBaseColorSearch').focus({ preventScroll: true }); } catch (e) {} });
        });
        var baseColorSearch = $('spbEasySculptBaseColorSearch');
        if (baseColorSearch) baseColorSearch.addEventListener('input', filterBaseColorOptions);
        var baseColorLibrary = $('spbEasySculptBaseColorLibrary');
        if (baseColorLibrary) baseColorLibrary.addEventListener('click', function (event) {
            var origin = event.target;
            if (origin && origin.nodeType === 3) origin = origin.parentElement;
            var card = origin && origin.closest ? origin.closest('[data-sculpt-base-id]') : null;
            if (!card) return;
            var target = activeColorTarget(); if (!target) return;
            var baseId = card.getAttribute('data-sculpt-base-id');
            var base = easyAllPickableRows().filter(function (item) { return item.id === baseId; })[0];
            if (!base) return;
            var body = document.querySelector('#spbEasyRail .spb-easy-sculpt-rail-body');
            var rememberedScroll = body ? body.scrollTop : 0;
            var rememberedBaseScroll = baseColorLibrary.scrollTop;
            target.replacementMode = 'base';
            target.replacementBaseId = base.id;
            target.replacementColor = String(base.swatch).toUpperCase();
            state.baseColorQuery = '';
            state.recoveredPlan = false;
            persistRecoveryPlan();
            render();
            drawLightingPreview();
            window.requestAnimationFrame(function () {
                var nextBody = document.querySelector('#spbEasyRail .spb-easy-sculpt-rail-body');
                if (nextBody) nextBody.scrollTop = rememberedScroll;
                var nextLibrary = $('spbEasySculptBaseColorLibrary');
                if (nextLibrary) nextLibrary.scrollTop = rememberedBaseScroll;
                var selectedCard = nextLibrary && Array.prototype.filter.call(nextLibrary.querySelectorAll('[data-sculpt-base-id]'), function (item) {
                    return item.getAttribute('data-sculpt-base-id') === base.id;
                })[0];
                try { if (selectedCard) selectedCard.focus({ preventScroll: true }); } catch (error) {}
                if (selectedCard && nextLibrary) {
                    var cardRect = selectedCard.getBoundingClientRect();
                    var libraryRect = nextLibrary.getBoundingClientRect();
                    if (cardRect.top < libraryRect.top + 4) nextLibrary.scrollTop -= (libraryRect.top + 4 - cardRect.top);
                    else if (cardRect.bottom > libraryRect.bottom - 4) nextLibrary.scrollTop += (cardRect.bottom - libraryRect.bottom + 4);
                }
            });
        });
        filterBaseColorOptions();
        var paintColor = $('spbEasySculptPaintColor');
        if (paintColor) paintColor.addEventListener('input', function () {
            var target = activeColorTarget(); if (!target) return;
            target.replacementColor = paintColor.value;
            target.replacementMode = 'solid';
            target.replacementBaseId = '';
            state.recoveredPlan = false;
            persistRecoveryPlan();
            var hsv = rgbToHsv(hexRgb(target.replacementColor));
            [['spbEasySculptHue', hsv.h], ['spbEasySculptSaturation', hsv.s], ['spbEasySculptBrightness', hsv.v]].forEach(function (entry) { if ($(entry[0])) $(entry[0]).value = entry[1]; });
            if ($('spbEasySculptHueValue')) $('spbEasySculptHueValue').textContent = hsv.h + '°';
            if ($('spbEasySculptSaturationValue')) $('spbEasySculptSaturationValue').textContent = hsv.s + '%';
            if ($('spbEasySculptBrightnessValue')) $('spbEasySculptBrightnessValue').textContent = hsv.v + '%';
            if ($('spbEasySculptPaintHex')) $('spbEasySculptPaintHex').textContent = target.replacementColor.toUpperCase();
            drawLightingPreview();
        });
        function applyReplacementHsv() {
            var target = activeColorTarget(); if (!target) return;
            target.replacementColor = hsvHex($('spbEasySculptHue').value, $('spbEasySculptSaturation').value, $('spbEasySculptBrightness').value);
            state.recoveredPlan = false;
            persistRecoveryPlan();
            if ($('spbEasySculptPaintColor')) $('spbEasySculptPaintColor').value = target.replacementColor;
            if ($('spbEasySculptPaintHex')) $('spbEasySculptPaintHex').textContent = target.replacementColor;
            $('spbEasySculptHueValue').textContent = $('spbEasySculptHue').value + '°';
            $('spbEasySculptSaturationValue').textContent = $('spbEasySculptSaturation').value + '%';
            $('spbEasySculptBrightnessValue').textContent = $('spbEasySculptBrightness').value + '%';
            drawLightingPreview();
        }
        ['spbEasySculptHue', 'spbEasySculptSaturation', 'spbEasySculptBrightness'].forEach(function (id) {
            var slider = $(id); if (slider) slider.addEventListener('input', applyReplacementHsv);
        });
        var colorNext = $('spbEasySculptColorNext');
        if (colorNext) colorNext.addEventListener('click', advanceToLookPicker);
        Array.prototype.forEach.call(document.querySelectorAll('#spbEasyRail [data-color-tolerance]'), function (button) {
            button.addEventListener('click', function () {
                var target = activeColorTarget();
                if (!target) return;
                captureLibraryView();
                target.tolerance = Number(button.getAttribute('data-color-tolerance')) || 30;
                state.recoveredPlan = false;
                generatePreview('Adjusting how much of ' + colorTargetName(target) + ' is included...');
            });
        });
        Array.prototype.forEach.call(document.querySelectorAll('#spbEasyRail [data-material-impact]'), function (button) {
            button.addEventListener('click', function () {
                var next = button.getAttribute('data-material-impact');
                if (['subtle', 'balanced', 'bold'].indexOf(next) === -1 || next === state.materialImpact) return;
                captureLibraryView();
                state.materialImpact = next;
                state.recoveredPlan = false;
                generatePreview('Rebuilding the whole material plan with ' + next + ' impact...');
            });
        });
        var scale = $('spbEasySculptScale');
        if (scale) {
            var syncLinkedScale = function () {
                var linked = Math.max(0.25, Math.min(1, Number(scale.value) / 100));
                var target = activeColorTarget();
                if (target) target.materialScale = linked;
                else state.materialScale = linked;
                var baseReadout = $('spbEasySculptScaleValue');
                var specReadout = $('spbEasySculptSpecScaleValue');
                if (baseReadout) baseReadout.innerHTML = linked.toFixed(2) + '&times;';
                if (specReadout) specReadout.innerHTML = linked.toFixed(2) + '&times;';
                scale.setAttribute('aria-valuetext', linked.toFixed(2) + ' times, base and spec matched');
                return linked;
            };
            scale.addEventListener('input', function () {
                state.recoveredPlan = false;
                captureLibraryView();
                syncLinkedScale();
            });
            scale.addEventListener('change', function () {
                // Some assistive/browser input paths commit a range value with a
                // change event but no observable input event. Re-read the source
                // control here so the label, preview recipe, and install agree.
                state.recoveredPlan = false;
                captureLibraryView();
                syncLinkedScale();
                var look = activeTargetLook();
                if (!lookSupportsScale(look)) return;
                generatePreview('Rebuilding ' + look.name + ' at the new linked scale...');
            });
            syncLinkedScale();
        }
    }

    function wireSourceColorPicker() {
        var image = $('spbEasySculptSourcePick');
        if (!image || !state.pickingColor) return;
        image.addEventListener('click', function (event) {
            event.preventDefault();
            event.stopPropagation();
            sampleSourceColor(event, image);
        });
        image.addEventListener('keydown', function (event) {
            if (event.key !== 'Enter' && event.key !== ' ') return;
            event.preventDefault();
            event.stopPropagation();
            var rect = image.getBoundingClientRect();
            sampleSourceColor({
                clientX: rect.left + rect.width / 2,
                clientY: rect.top + rect.height / 2
            }, image);
        });
    }

    async function sampleSourceColor(event, image) {
        if (!state.pickingColor || state.colorTargets.length >= MAX_COLOR_TARGETS) return;
        var sampleSerial = requestSerial;
        var sampleIdentity = sourceIdentity();
        try {
            var rect = image.getBoundingClientRect();
            var nx = Math.max(0, Math.min(1, (event.clientX - rect.left) / Math.max(1, rect.width)));
            var ny = Math.max(0, Math.min(1, (event.clientY - rect.top) / Math.max(1, rect.height)));
            var pixel = null;
            image.setAttribute('aria-busy', 'true');

            // Flat iRacing paints must be sampled from the canonical 2048
            // source. The 480px JPEG on screen is display-only and blends edge
            // colors that may not exist anywhere in the TGA.
            if (state.sourceToken || (state.file && !isPsd(state.file))) {
                var response;
                if (state.sourceToken) {
                    response = await fetch(api('/api/spec-sculpt/sample-source-color'), {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json', 'X-Shokker-Internal': '1' },
                        body: JSON.stringify({ source_token: state.sourceToken, x: nx, y: ny, radius: 2 })
                    });
                } else {
                    var sampleFd = new FormData();
                    sampleFd.append('paint_file', state.file);
                    sampleFd.append('x', String(nx));
                    sampleFd.append('y', String(ny));
                    sampleFd.append('radius', '2');
                    response = await fetch(api('/api/spec-sculpt/sample-source-color'), { method: 'POST', body: sampleFd });
                }
                var sampled = await readJsonResponse(response, 'Shokker could not read that source color.');
                if (sampleSerial !== requestSerial || sampleIdentity !== sourceIdentity()) return;
                if (!response.ok || !sampled.success || !Array.isArray(sampled.rgb) || sampled.rgb.length !== 3) {
                    throw responseError(response, sampled.error, 'Shokker could not read that source color.');
                }
                pixel = sampled.rgb.slice(0, 3).map(function (value) { return Math.max(0, Math.min(255, Number(value) || 0)); });
            } else {
                // PSD composites are already lossless browser images and may
                // not have a flat server-readable source. Keep their existing
                // canvas fallback until native PSD coordinate sampling exists.
                var px = Math.max(0, Math.min((image.naturalWidth || 1) - 1, Math.floor(nx * (image.naturalWidth || 1))));
                var py = Math.max(0, Math.min((image.naturalHeight || 1) - 1, Math.floor(ny * (image.naturalHeight || 1))));
                var canvas = document.createElement('canvas');
                canvas.width = canvas.height = 1;
                var context = canvas.getContext('2d', { willReadFrequently: true });
                context.drawImage(image, px, py, 1, 1, 0, 0, 1, 1);
                pixel = Array.prototype.slice.call(context.getImageData(0, 0, 1, 1).data, 0, 3);
            }
            if (sampleSerial !== requestSerial || sampleIdentity !== sourceIdentity()) return;
            var addedTarget = addColorTarget(pixel);
            state.pickingColor = false;
            refreshRecommendations();
            render();
            loadPaintAwareRecommendations();
            window.requestAnimationFrame(function () {
                var targetButton = addedTarget && $('spbEasySculptScope-' + addedTarget.id);
                if (targetButton) targetButton.focus();
                var library = document.querySelector('.spb-easy-sculpt-library');
                if (library) library.scrollIntoView({ behavior: 'smooth', block: 'start' });
            });
        } catch (error) {
            if (sampleSerial !== requestSerial || sampleIdentity !== sourceIdentity()) return;
            state.error = 'That color could not be sampled. Try another spot on the paint.';
            state.errorContext = 'preview';
            render();
        } finally {
            if (image && image.isConnected) image.removeAttribute('aria-busy');
        }
    }

    function wireLookPicker() {
        var search = $('spbEasySculptLookSearch');
        if (search) search.addEventListener('input', function () {
            state.libraryQuery = search.value;
            state.libraryCategory = '';
            if (state.libraryQuery.trim()) state.libraryKind = 'all';
            state.libraryLimit = LOOK_PAGE_SIZE;
            // Keep the native input alive while someone types, clears, or fixes
            // a word. Replacing it synchronously on every keystroke broke
            // Ctrl+A/Backspace and could swallow fast typing on slower PCs.
            if (lookSearchTimer) window.clearTimeout(lookSearchTimer);
            lookSearchTimer = window.setTimeout(function () {
                lookSearchTimer = 0;
                persistRecoveryPlan();
                renderRail();
                var next = $('spbEasySculptLookSearch');
                if (next) { next.focus(); try { next.setSelectionRange(next.value.length, next.value.length); } catch (e) {} }
            }, 120);
        });
        var clearSearch = $('spbEasySculptSearchClear');
        if (clearSearch) clearSearch.addEventListener('click', function () {
            if (lookSearchTimer) window.clearTimeout(lookSearchTimer);
            lookSearchTimer = 0;
            state.libraryQuery = '';
            state.libraryKind = 'recommended';
            state.libraryCategory = '';
            state.libraryLimit = LOOK_PAGE_SIZE;
            persistRecoveryPlan();
            renderRail();
            var next = $('spbEasySculptLookSearch');
            if (next) next.focus();
        });
        if (search) search.addEventListener('keydown', function (event) {
            if (event.key !== 'Escape' || !state.libraryQuery) return;
            event.preventDefault();
            event.stopPropagation();
            // Escape should mean the same thing as the visible X: leave search
            // completely and return to the small paint-aware shelf. Do not
            // depend on the X already existing: a fast typist can press Escape
            // before the 120ms search repaint creates that button.
            if (lookSearchTimer) window.clearTimeout(lookSearchTimer);
            lookSearchTimer = 0;
            state.libraryQuery = '';
            state.libraryKind = 'recommended';
            state.libraryCategory = '';
            state.libraryLimit = LOOK_PAGE_SIZE;
            persistRecoveryPlan();
            renderRail();
            var nextSearch = $('spbEasySculptLookSearch');
            if (nextSearch) nextSearch.focus();
        });
        Array.prototype.forEach.call(document.querySelectorAll('#spbEasyRail [data-page-more]'), function (button) {
            button.addEventListener('click', function (event) {
                event.preventDefault();
                event.stopPropagation();
                var mode = button.getAttribute('data-page-more');
                var current = Number(state.libraryLimit) || LOOK_PAGE_SIZE;
                // SHOW ALL is bounded by the same ceiling the restore path uses,
                // so one click can never ask for an unbounded grid.
                state.libraryLimit = mode === 'all'
                    ? Math.min(LOOK_PAGE_SIZE * 60, 100000)
                    : Math.min(LOOK_PAGE_SIZE * 60, current + LOOK_PAGE_SIZE);
                persistRecoveryPlan();
                renderRail();
            });
        });
        Array.prototype.forEach.call(document.querySelectorAll('#spbEasyRail [data-look-kind]'), function (button) {
            button.addEventListener('click', function () {
                state.libraryKind = button.getAttribute('data-look-kind') || 'all';
                state.libraryCategory = '';
                state.libraryLimit = LOOK_PAGE_SIZE;
                persistRecoveryPlan();
                renderRail();
            });
            button.addEventListener('keydown', function (event) {
                if (event.key !== 'ArrowLeft' && event.key !== 'ArrowRight' && event.key !== 'Home' && event.key !== 'End') return;
                var tabs = Array.prototype.slice.call(document.querySelectorAll('#spbEasyRail [data-look-kind]'));
                var index = tabs.indexOf(button);
                if (event.key === 'Home') index = 0;
                else if (event.key === 'End') index = tabs.length - 1;
                else index = (index + (event.key === 'ArrowRight' ? 1 : -1) + tabs.length) % tabs.length;
                event.preventDefault();
                state.libraryKind = tabs[index].getAttribute('data-look-kind') || 'all';
                state.libraryCategory = '';
                state.libraryLimit = LOOK_PAGE_SIZE;
                persistRecoveryPlan();
                renderRail();
                var next = document.querySelector('#spbEasyRail [data-look-kind="' + state.libraryKind + '"]');
                if (next) next.focus();
            });
        });
        Array.prototype.forEach.call(document.querySelectorAll('#spbEasyRail [data-look-category]'), function (summary) {
            summary.addEventListener('click', function (event) {
                event.preventDefault();
                var category = summary.getAttribute('data-look-category') || '';
                state.libraryCategory = state.libraryCategory === category ? '' : category;
                state.libraryLimit = LOOK_PAGE_SIZE;
                persistRecoveryPlan();
                renderRail();
                var next = Array.prototype.slice.call(document.querySelectorAll('#spbEasyRail [data-look-category]')).filter(function (item) {
                    return item.getAttribute('data-look-category') === category;
                })[0];
                if (next) next.focus();
            });
        });
        Array.prototype.forEach.call(document.querySelectorAll('#spbEasyRail [data-look-key]'), function (button) {
            button.addEventListener('click', function () { selectLook(findLook(button.getAttribute('data-look-key'))); });
        });
        var more = $('spbEasySculptMore');
        if (more) more.addEventListener('click', function () {
            state.libraryLimit += LOOK_PAGE_SIZE;
            persistRecoveryPlan();
            renderRail();
        });
        var surprise = $('spbEasySculptSurprise');
        if (surprise) surprise.addEventListener('click', surpriseLook);
        var previous = $('spbEasySculptPreviousLook');
        if (previous) previous.addEventListener('click', restorePreviousLook);
        var next = $('spbEasySculptNextLook');
        if (next) next.addEventListener('click', nextLook);
        var goSave = $('spbEasySculptGoSave');
        if (goSave) goSave.addEventListener('click', advanceToInstallCard);
        var retryPreview = $('spbEasySculptRetryPreview');
        if (retryPreview) retryPreview.addEventListener('click', function () {
            captureLibraryView(lookKey(activeTargetLook()));
            generatePreview('Trying that look again...');
        });
        var change = $('spbEasySculptChange');
        if (change) change.addEventListener('click', function () {
            var input = $('spbEasySculptReplaceFile');
            if (input) input.click();
        });
        var keepEditing = $('spbEasySculptContinue');
        if (keepEditing) keepEditing.addEventListener('click', continueEditing);
        var edit = $('spbEasySculptEditTarget');
        if (edit) edit.addEventListener('click', function () {
            state.exportOpen = !state.exportOpen;
            renderRail();
            var destinationControl = state.exportOpen ? ($('spbEasySculptCarSearch') || $('spbEasySculptCar')) : $('spbEasySculptEditTarget');
            try { if (destinationControl) destinationControl.focus(); } catch (e) {}
        });
        var id = $('spbEasySculptId');
        if (id) id.addEventListener('input', function () {
            var wasReady = validId(state.iracingId) && state.cars.some(function (item) { return item.name === state.car; });
            state.iracingId = id.value.trim();
            persistRecoveryPlan();
            var isReady = validId(state.iracingId) && state.cars.some(function (item) { return item.name === state.car; });
            if (wasReady !== isReady) {
                renderRail();
                var nextId = $('spbEasySculptId');
                try {
                    if (nextId) { nextId.focus(); nextId.setSelectionRange(nextId.value.length, nextId.value.length); }
                } catch (e) {}
            } else {
                // Do not replace the live input on every digit (that can swallow
                // fast typing), but never leave a stale ID in the filenames or
                // route receipt. Save and the screen must promise the same files.
                var filenameId = validId(state.iracingId) ? state.iracingId : 'ID';
                var customName = document.querySelector('#spbEasySculptCustomNumber small');
                var stampedName = document.querySelector('#spbEasySculptStampedNumber small');
                if (customName) customName.textContent = 'car_num_' + filenameId + '.tga';
                if (stampedName) stampedName.textContent = 'car_' + filenameId + '.tga';
                var route = document.querySelector('.spb-easy-sculpt-target-route');
                if (route && isReady) route.textContent = 'Folder ' + state.car + ' · Customer ID ' + state.iracingId + ' · paint + spec auto-route together';
            }
        });
        function destinationCarMatches(query) {
            var words = String(query || '').trim().toLowerCase().split(/\s+/).filter(Boolean);
            if (!words.length) return state.cars.slice();
            return state.cars.filter(function (item) {
                var haystack = (friendlyCarName(item.name) + ' ' + item.name).toLowerCase();
                return words.every(function (word) { return haystack.indexOf(word) !== -1; });
            });
        }
        function filterDestinationCars() {
            var search = $('spbEasySculptCarSearch');
            var select = $('spbEasySculptCar');
            if (!select) return [];
            var query = String(search && search.value || '').trim().toLowerCase();
            var matches = destinationCarMatches(query);
            var matchNames = matches.map(function (item) { return item.name; });
            Array.prototype.forEach.call(select.options, function (option, index) {
                option.hidden = !!query && index > 0 && !option.selected && matchNames.indexOf(option.value) === -1;
            });
            var receipt = $('spbEasySculptCarSearchStatus');
            if (receipt) receipt.textContent = !query ? '' : (!matches.length
                ? 'No matching car folder. Try fewer words.'
                : (matches.length + ' match' + (matches.length === 1 ? '' : 'es') + ' · Press Enter to use ' + friendlyCarName(matches[0].name) + '.'));
            return matches;
        }
        var carSearch = $('spbEasySculptCarSearch');
        if (carSearch) carSearch.addEventListener('input', function () {
            state.carQuery = carSearch.value.slice(0, 60);
            filterDestinationCars();
        });
        if (carSearch) carSearch.addEventListener('keydown', function (event) {
            if (event.key !== 'Enter') return;
            var matches = filterDestinationCars();
            if (!matches.length) return;
            event.preventDefault();
            state.car = matches[0].name;
            state.carQuery = '';
            persistRecoveryPlan();
            renderRail();
            var done = $('spbEasySculptEditTarget');
            try { if (done) done.focus(); } catch (e) {}
        });
        filterDestinationCars();
        var car = $('spbEasySculptCar');
        if (car) car.addEventListener('change', function () {
            state.car = car.value;
            state.carQuery = '';
            persistRecoveryPlan();
            renderRail();
            var nextCar = $('spbEasySculptCar');
            try { if (nextCar) nextCar.focus(); } catch (e) {}
        });
        [['spbEasySculptCustomNumber', true], ['spbEasySculptStampedNumber', false]].forEach(function (entry) {
            var button = $(entry[0]);
            if (!button) return;
            button.addEventListener('click', function () {
                state.inferredUseCustomNumber = entry[1];
                state.config.use_custom_number = entry[1];
                var mainControl = $('useCustomNumberCheckbox');
                if (mainControl) mainControl.checked = entry[1];
                persistRecoveryPlan();
                renderRail();
                var nextButton = $(entry[0]);
                try { if (nextButton) nextButton.focus(); } catch (e) {}
            });
        });
        var save = $('spbEasySculptSave');
        if (save) save.addEventListener('click', saveToIRacing);

        // [2026-08-06 owner ask] Family dropdown: show only the chosen family.
        // Toggled in place (no full re-render) so it is instant; the choice is
        // kept in state so re-renders preserve it.
        var famSel = $('spbEasySculptBaseFamily');
        if (famSel) famSel.addEventListener('change', function () {
            state.baseFamily = famSel.value || '';
            var lib = $('spbEasySculptBaseColorLibrary');
            if (!lib) return;
            Array.prototype.forEach.call(lib.querySelectorAll('.spb-easy-sculpt-base-group'), function (group) {
                var name = group.getAttribute('data-group-name') || '';
                var show = !state.baseFamily || name === state.baseFamily;
                group.hidden = !show;
                if (show && state.baseFamily) group.open = true;
            });
        });

        // [2026-08-06 owner ask] SAVE TO iRACING was buried below the fold in the
        // right rail. A mirrored button lives in the middle column under the
        // sculpted paint (see midColumn template); it clones the REAL button's
        // label and disabled state so it can never promise a save the rail
        // would refuse, and clicking it clicks the real one — one code path.
        syncSaveProxy();
        // [2026-08-08 S14] Runs after EVERY rail render (innerHTML wipes the
        // tab indexes), so the grid always has exactly one tab stop.
        wireSculptRoving();
        syncSculptRoving();
        // [2026-08-09 S28] Retry the catalog without making the painter reload.
        // loadEnvironment() already clears environmentPromise when the library
        // is incomplete, so simply calling it again refetches.
        var retryLooks = $('spbEasySculptRetryLooks');
        if (retryLooks && !retryLooks._spbWired) {
            retryLooks._spbWired = true;
            retryLooks.addEventListener('click', function () {
                retryLooks.disabled = true;
                retryLooks.textContent = 'LOADING...';
                state.looksError = false;
                loadEnvironment().then(function () {
                    if (mounted) renderRail();
                }).catch(function () {
                    state.looksError = true;
                    if (mounted) renderRail();
                });
            });
        }
    }

    function progressReceipt() {
        if (state.phase === 'saving') {
            return '<div class="spb-easy-sculpt-progress-list">' +
                progressRow('Finishing the full-size shine', false, true) +
                progressRow('Putting it in iRacing', false, false) +
                '</div>';
        }
        var step = state.progressStep || (state.phase === 'sculpting' ? 'sculpting' : 'checking');
        var checked = step !== 'checking';
        var protectedArt = step === 'sculpting';
        return '<div class="spb-easy-sculpt-progress-list">' +
            progressRow('Checking your paint', checked, !checked) +
            progressRow('Protecting your artwork', protectedArt, step === 'protecting') +
            progressRow('Making the shine', false, step === 'sculpting') +
            '</div>';
    }

    function progressRow(label, done, current) {
        return '<div class="' + (done ? 'done' : (current ? 'current' : '')) + '"><i>' + (done ? '&#10003;' : (current ? '&#8226;' : '')) + '</i><span>' + esc(label) + '</span></div>';
    }

    function receiptHtml() {
        var layers = state.layerSummary;
        var chips = [
            '<span class="ok">2048 &times; 2048 &#10003;</span>',
            '<span>' + esc(state.format) + '</span>'
        ];
        if (layers) {
            chips.push('<span>' + layers.paint + ' paint layer' + (layers.paint === 1 ? '' : 's') + '</span>');
            chips.push('<span class="safe">' + layers.protected + ' graphic' + (layers.protected === 1 ? '' : 's') + ' protected</span>');
            if (layers.hidden) chips.push('<span>' + layers.hidden + ' hidden/template layer' + (layers.hidden === 1 ? '' : 's') + ' ignored</span>');
        } else {
            chips.push('<span class="safe">Graphics auto-protected</span>');
        }
        return '<div class="spb-easy-sculpt-receipt"><b>' + esc(state.filename) + '</b><div>' + chips.join('') + '</div></div>';
    }

    function incompleteColorTarget() {
        return state.colorTargets.filter(function (target) {
            return !target.look || (typeof target.coverage === 'number' && target.coverage <= 0);
        })[0] || null;
    }

    function materialPlanName() {
        var base = (state.selectedLook && state.selectedLook.name) || 'Spec Sculpt';
        var colors = state.colorTargets.filter(function (target) {
            return target.look && !(typeof target.coverage === 'number' && target.coverage <= 0);
        });
        var name = !colors.length
            ? base
            : (colors.length === 1
                ? base + ' + ' + colorTargetName(colors[0]) + ' ' + colors[0].look.name
                : base + ' + ' + colors.length + ' color materials');
        return state.materialImpact === 'balanced'
            ? name
            : name + ' · ' + state.materialImpact.toUpperCase() + ' impact';
    }

    function exportHtml() {
        if (state.phase === 'saved' && state.saved) {
            var installedFiles = (state.saved.files || []).map(function (name) {
                return '<code>' + esc(name) + '</code>';
            }).join('');
            return '<div class="spb-easy-sculpt-saved"><b>&#10003; INSTALLED + LOCKED IN</b>' +
                '<span>' + esc(state.saved.lookName || 'This material') + ' is now the active Spec Sculpt material for this paint.</span>' +
                '<div class="spb-easy-sculpt-saved-files">' + installedFiles + '</div>' +
                '<small>Verified in <strong>' + esc(state.saved.target || state.car) + '</strong></small>' +
                ((state.saved.staleMips && state.saved.staleMips.length)
                    ? '<div class="spb-easy-sculpt-stale-mip" role="alert"><b>ONE OLD FILE COULD HIDE THIS</b>' +
                      '<span>' + esc(state.saved.staleMips.map(function (m) { return m.name; }).join(', ')) +
                      ' in that folder is older than what was just written. iRacing builds those from your paint, and if it loads that one instead you will see the previous spec. If the car looks unchanged after Ctrl+R, move or delete it and reload.</span></div>'
                    : '') +
                '<small>Main RENDER now keeps this exact spec instead of painting over it. Alt+Tab to iRacing and press Ctrl+R.</small></div>';
        }
        var idReady = validId(state.iracingId);
        var carReady = state.cars.some(function (car) { return car.name === state.car; });
        var targetReady = idReady && carReady;
        var unfinished = incompleteColorTarget();
        var fields = state.exportOpen || !targetReady;
        var carCount = state.cars.length;
        var target = carReady ? esc(friendlyCarName(state.car)) : 'Choose the car below';
        var targetDetail = targetReady
            ? ('Folder ' + esc(state.car) + ' &middot; Customer ID ' + esc(state.iracingId) + ' &middot; paint + spec auto-route together')
            : (carCount ? ('Pick from ' + carCount + ' discovered iRacing car folder' + (carCount === 1 ? '' : 's') + '.') : 'No iRacing car folders found yet.');
        var emptyCarLabel = carCount ? 'Choose an iRacing car folder' : 'No iRacing car folders found yet';
        var carHelp = carCount
            ? ('Shokker found ' + carCount + ' iRacing car folder' + (carCount === 1 ? '' : 's') + '. Pick one &mdash; both output files route there automatically.')
            : 'Open iRacing once, then reopen Spec Sculpt so Shokker can find its paint folders.';
        var filenameId = idReady ? state.iracingId : 'ID';
        var diffuseName = (liveUseCustomNumber() ? 'car_num_' : 'car_') + state.iracingId + '.tga';
        return '<div class="spb-easy-sculpt-export">' +
            (state.error && state.errorContext === 'install' ? '<div class="spb-easy-sculpt-error" role="alert"><b>Installation needs attention.</b><span>' + esc(state.error) + '</span></div>' : '') +
            '<div class="spb-easy-sculpt-target"><span>iRACING CAR</span><b>' + target + '</b>' +
            (targetReady ? '<button type="button" id="spbEasySculptEditTarget" title="' + (fields ? 'Keep this car and close the fields' : 'Pick a different iRacing car - the saved file names change with it') + '">' + (fields ? 'DONE' : 'SWITCH CAR') + '</button>' : '') +
            '<small class="spb-easy-sculpt-target-route' + (targetReady ? ' is-ready' : '') + '">' + targetDetail + '</small></div>' +
            (fields ? '<div class="spb-easy-sculpt-target-fields">' +
                '<label class="spb-easy-sculpt-car-search">FIND YOUR CAR FAST<input type="search" id="spbEasySculptCarSearch" maxlength="60" autocomplete="off" value="' + esc(state.carQuery) + '" placeholder="Type dirt late, Ferrari, ARCA..." aria-controls="spbEasySculptCar" aria-describedby="spbEasySculptCarSearchStatus"><small id="spbEasySculptCarSearchStatus" class="spb-easy-sculpt-car-search-status" role="status" aria-live="polite"></small></label>' +
                '<label class="spb-easy-sculpt-car-field">WHICH iRACING CAR?<select id="spbEasySculptCar" required' + (!state.cars.some(function (car) { return car.name === state.car; }) ? ' aria-invalid="true"' : '') + '><option value=""' + (!state.car ? ' selected' : '') + '>' + esc(emptyCarLabel) + '</option>' + state.cars.map(function (car) {
                    return '<option value="' + esc(car.name) + '"' + (state.car === car.name ? ' selected' : '') + '>' + esc(friendlyCarName(car.name)) + ' &mdash; folder: ' + esc(car.name) + '</option>';
                }).join('') + '</select></label>' +
                '<label class="spb-easy-sculpt-id-field">CUSTOMER ID<input id="spbEasySculptId" inputmode="numeric" pattern="[0-9]{4,7}" required maxlength="7" value="' + esc(state.iracingId) + '" placeholder="4-7 digits"' + (!validId(state.iracingId) ? ' aria-invalid="true"' : '') + '></label>' +
                '<div class="spb-easy-sculpt-number-choice" role="group" aria-label="iRacing number type">' +
                    '<button type="button" id="spbEasySculptCustomNumber" class="' + (liveUseCustomNumber() ? 'on' : '') + '" aria-pressed="' + (liveUseCustomNumber() ? 'true' : 'false') + '">CUSTOM NUMBER<small>car_num_' + esc(filenameId) + '.tga</small></button>' +
                    '<button type="button" id="spbEasySculptStampedNumber" class="' + (!liveUseCustomNumber() ? 'on' : '') + '" aria-pressed="' + (!liveUseCustomNumber() ? 'true' : 'false') + '">SIM-STAMPED NUMBER<small>car_' + esc(filenameId) + '.tga</small></button>' +
                '</div>' +
                '<small class="spb-easy-sculpt-route-help">' + carHelp + '</small></div>' : '') +
            (targetReady && !fields ? '<small class="spb-easy-sculpt-file-plan">WILL VERIFY <b>' + esc(diffuseName) + '</b> + <b>car_spec_' + esc(state.iracingId) + '.tga</b></small>' : '') +
            (unfinished ? '<small class="spb-easy-sculpt-plan-block">' + (unfinished.look
                ? 'No paint matched ' + esc(colorTargetLabel(unfinished)) + '. Try Wide above, or remove that color.'
                : 'Finish ' + esc(colorTargetLabel(unfinished)) + ' above, or remove that color.') + '</small>' : '') +
            '<button type="button" class="spb-easy-sculpt-save" id="spbEasySculptSave" title="Write the paint and spec files straight into your iRacing folder"' + ((unfinished || !targetReady) ? ' disabled aria-disabled="true"' : '') + '>' +
            (unfinished ? (unfinished.look ? 'TRY WIDE OR REMOVE ' : 'PICK A LOOK FOR ') + esc(colorTargetName(unfinished)) + ' FIRST' :
                (!idReady ? 'ENTER YOUR iRACING CUSTOMER ID ABOVE' : (!carReady ? 'CHOOSE AN iRACING CAR ABOVE' :
                'SAVE TO iRACING'))) + '</button></div>';
    }

    function continueEditing() {
        if (!state.sourceUrl) return;
        state.phase = 'ready';
        state.error = '';
        state.errorContext = '';
        state.saved = null;
        state.status = '';
        state.exportOpen = false;
        state.recoveredPlan = false;
        state.showSpecMap = false;
        state.showBigResult = false;
        state.libraryScrollTop = 0;
        state.focusReturnId = state.activeColorId ? 'spbEasySculptScope-' + state.activeColorId : 'spbEasySculptScope-whole';
        state.focusReturnLookKey = '';
        state.libraryAnchorOffset = null;
        render();
        restoreLibraryView();
    }

    function liveUseCustomNumber() {
        if (typeof state.inferredUseCustomNumber === 'boolean') return state.inferredUseCustomNumber;
        var control = $('useCustomNumberCheckbox');
        if (control) return !!control.checked;
        return state.config.use_custom_number !== false;
    }

    function releaseSculptSpecOverride() {
        var lock = window._spbEasySculptSpecOverride;
        var lockedPath = (lock && lock.path) || (document.body && document.body.dataset.spbEasySculptSpecPath) || '';
        if (!lockedPath) return;
        try {
            if (typeof importedSpecMapPath !== 'undefined' && importedSpecMapPath === lockedPath) importedSpecMapPath = null;
        } catch (e) {}
        if (window.importedSpecMapPath === lockedPath) window.importedSpecMapPath = null;
        window._spbEasySculptSpecOverride = null;
        if (document.body) delete document.body.dataset.spbEasySculptSpecPath;
    }

    function activateSculptSpecOverride(specPath, lookName) {
        var normalized = String(specPath || '').replace(/\\/g, '/');
        if (!normalized) throw new Error('The finished spec file path was not returned, so Main Render was not armed.');
        try {
            if (typeof importedSpecMapPath !== 'undefined') importedSpecMapPath = normalized;
        } catch (e) {}
        window.importedSpecMapPath = normalized;
        window._spbEasySculptSpecOverride = {
            path: normalized,
            lookName: lookName || 'Spec Sculpt material',
            car: state.car,
            iracingId: state.iracingId,
            installedAt: Date.now()
        };
        // DOM-backed cross-script contract: unlike a module-local/global lexical
        // binding, this remains observable to Main Render and diagnostic tests.
        if (document.body) document.body.dataset.spbEasySculptSpecPath = normalized;
        var status = $('importSpecMapStatus');
        if (status) status.innerHTML = '<span style="color:var(--accent-green);font-weight:700;">&#10003; Spec Sculpt active &middot; Layer 0</span> - ' + esc(lookName || 'Easy Spec Sculpt');
        var clearButton = $('btnClearSpecMap');
        if (clearButton) clearButton.disabled = false;
        return normalized;
    }

    function specLabLink() {
        if (!SHOW_LEGACY_SPEC_LAB) return '';
        return '<button type="button" class="spb-easy-sculpt-lab" id="spbEasySculptLab"><span>Want to go deeper? Your paint and where it saves come with you.</span><b>OPEN ORIGINAL SPEC SCULPT</b><small>Tune shine, roughness and clearcoat by hand &middot; stack effects &middot; mask exactly where they land</small></button>';
    }

    function currentPaintButton(location) {
        var path = currentPaintPath();
        if (!path) return '';
        if (currentPaintStillLoading()) {
            return '<button type="button" class="spb-easy-sculpt-current ' + location + '" disabled aria-busy="true">' +
                '<b>FINISHING THE PSD LAYERS...</b><small>Then this paint will be ready automatically &middot; ' + esc(basename(rememberedLayeredPaintPath || path)) + '</small></button>';
        }
        var canvas = $('paintCanvas');
        var sourceLabel = canvas && canvas.width === 2048 && canvas.height === 2048 ? 'LIVE CANVAS' : 'READY TO USE';
        return '<button type="button" class="spb-easy-sculpt-current ' + location + '" data-use-current-paint="1">' +
            '<b>USE THE PAINT ALREADY OPEN</b><small>' + sourceLabel + ' &middot; ' + esc(basename(path)) + '</small></button>';
    }

    function liveCanvasFingerprint(canvas) {
        try {
            var probe = document.createElement('canvas');
            probe.width = probe.height = 32;
            var context = probe.getContext('2d', { willReadFrequently: true });
            context.drawImage(canvas, 0, 0, 32, 32);
            var bytes = context.getImageData(0, 0, 32, 32).data;
            var hash = 2166136261;
            for (var i = 0; i < bytes.length; i += 4) {
                hash ^= bytes[i]; hash = Math.imul(hash, 16777619);
                hash ^= bytes[i + 1]; hash = Math.imul(hash, 16777619);
                hash ^= bytes[i + 2]; hash = Math.imul(hash, 16777619);
                hash ^= bytes[i + 3]; hash = Math.imul(hash, 16777619);
            }
            return (hash >>> 0).toString(16).padStart(8, '0');
        } catch (error) { return ''; }
    }

    function canvasPngFile(canvas, filename, fingerprint) {
        return new Promise(function (resolve, reject) {
            try {
                canvas.toBlob(function (blob) {
                    if (!blob) { reject(new Error('The live paint canvas could not be captured.')); return; }
                    resolve(new File([blob], filename, { type: 'image/png', lastModified: parseInt(fingerprint || '1', 16) || 1 }));
                }, 'image/png');
            } catch (error) { reject(error); }
        });
    }
    function canvasPreviewDataUrl(canvas) {
        var preview = document.createElement('canvas');
        preview.width = 512;
        preview.height = 512;
        preview.getContext('2d').drawImage(canvas, 0, 0, preview.width, preview.height);
        return preview.toDataURL('image/png');
    }

    async function acceptCurrentPaint() {
        var path = currentPaintPath();
        if (!path) return;
        // The source path becomes known before every layer image has decoded.
        // Never capture that temporary half-built canvas as if it were final.
        if (currentPaintStillLoading()) return;
        // Building a live PSD composite can be expensive. Acknowledge the click
        // and let the browser paint the working state before doing synchronous
        // canvas work, so "Use the paint already open" can never feel dead.
        state.phase = 'checking';
        state.progressStep = 'checking';
        state.error = '';
        state.errorContext = '';
        state.retryable = false;
        state.status = 'Capturing every visible edit from the paint already open...';
        render();
        await new Promise(function (resolve) {
            window.requestAnimationFrame(function () { window.setTimeout(resolve, 0); });
        });
        if (!mounted) return;
        try {
            var canvas = typeof window.buildLivePaintCompositeCanvas === 'function'
                ? window.buildLivePaintCompositeCanvas()
                : $('paintCanvas');
            if (canvas && canvas.width === 2048 && canvas.height === 2048 && typeof canvas.toBlob === 'function') {
                var fingerprint = liveCanvasFingerprint(canvas);
                var stem = basename(path).replace(/\.[^.]+$/, '') || 'current-paint';
                var file = await canvasPngFile(canvas, stem + '-live.png', fingerprint);
                var normalized = String(path).replace(/\\/g, '/').toLowerCase();
                var livePsdData = null;
                try {
                    if (/\.psd$/i.test(path) && window._psdLayersLoaded === true && window._psdData && window._psdData.success) {
                        livePsdData = window._psdData;
                    }
                } catch (e) {}
                acceptFile(file, {
                    displayName: basename(path),
                    format: ((basename(path).split('.').pop() || 'PAINT').toUpperCase()) + ' / LIVE',
                    identity: 'live:' + normalized + ':' + fingerprint,
                    originalPath: path,
                    psdPath: /\.psd$/i.test(path) ? path : '',
                    psdImportData: livePsdData,
                    knownResolution: [canvas.width, canvas.height],
                    sourcePreviewDataUrl: canvasPreviewDataUrl(canvas),
                    keepAnalyzedPreview: true
                });
                return;
            }
        } catch (error) {
            // Fall through to the real source path. The existing path flow has
            // its own friendly error/retry behavior and never strands the user.
        }
        acceptPath(path);
    }

    function wireCurrentPaint() {
        Array.prototype.forEach.call(document.querySelectorAll('[data-use-current-paint="1"]'), function (button) {
            button.addEventListener('click', function (event) {
                event.stopPropagation();
                acceptCurrentPaint();
            });
        });
    }

    function wireCommonRail() {
        wireSculptUndoKeys();   // [S31] once-only; guarded inside
        // [2026-08-09 S11] one click back into the saved plan
        var resume = $('spbEasySculptResume');
        if (resume && !resume._spbWired) {
            resume._spbWired = true;
            resume.addEventListener('click', function () {
                var path = resume.getAttribute('data-resume-path') || '';
                if (!path || typeof window.loadPaintByPath !== 'function') return;
                resume.disabled = true;
                resume.textContent = 'OPENING...';
                try { window.loadPaintByPath(path); } catch (error) {
                    resume.disabled = false;
                    resume.textContent = 'COULD NOT OPEN IT - USE LOAD PAINT';
                }
            });
        }
        var back = $('spbEasySculptBack');
        if (back) back.addEventListener('click', function () {
            if (hooks && typeof hooks.back === 'function') hooks.back();
        });
        var lab = $('spbEasySculptLab');
        if (lab) lab.addEventListener('click', openSpecLab);
        // The rail's contents are replaced after every material decision. Keep
        // detected-color shortcuts on the stable rail itself so mouse and
        // keyboard activation survive every rebuild without duplicate wiring.
        var rail = $('spbEasyRail');
        if (rail && rail.getAttribute('data-palette-wired') !== '1') {
            rail.setAttribute('data-palette-wired', '1');
            rail.addEventListener('click', function (event) {
                var origin = event.target;
                var button = origin && origin.closest ? origin.closest('[data-palette-index]') : null;
                if (!button || !rail.contains(button)) return;
                var entry = state.palette[Number(button.getAttribute('data-palette-index'))];
                if (!entry) return;
                addColorTarget(entry.color);
                state.pickingColor = false;
                state.recoveredPlan = false;
                refreshRecommendations();
                render();
                loadPaintAwareRecommendations();
                window.requestAnimationFrame(function () {
                    var library = document.querySelector('.spb-easy-sculpt-library');
                    if (library) library.scrollIntoView({ behavior: 'smooth', block: 'start' });
                });
            });
        }
    }

    function wireDropSurface(host) {
        var choose = $('spbEasySculptChoose');
        var input = $('spbEasySculptFile');
        var drop = $('spbEasySculptStageDrop');
        var retry = $('spbEasySculptRetry');
        if (retry) retry.addEventListener('click', function (event) {
            event.stopPropagation();
            if (state.file) acceptFile(state.file, state.liveSourceMeta);
            else if (state.sourcePath) acceptPath(state.sourcePath);
        });
        if (choose) choose.addEventListener('click', function (event) { event.stopPropagation(); clickFileInput(); });
        if (input) input.addEventListener('change', function () { if (input.files && input.files[0]) acceptFile(input.files[0]); });
        wireCurrentPaint();
        if (drop) {
            drop.addEventListener('click', function (event) { if (event.target !== choose) clickFileInput(); });
            ['dragenter', 'dragover'].forEach(function (name) {
                drop.addEventListener(name, function (event) { event.preventDefault(); drop.classList.add('drag'); });
            });
            ['dragleave', 'drop'].forEach(function (name) {
                drop.addEventListener(name, function (event) { event.preventDefault(); drop.classList.remove('drag'); });
            });
            drop.addEventListener('drop', function (event) {
                var file = event.dataTransfer && event.dataTransfer.files && event.dataTransfer.files[0];
                if (file) acceptFile(file);
            });
        }
    }

    function clickFileInput() {
        var input = $('spbEasySculptFile');
        if (!input) {
            renderStage();
            input = $('spbEasySculptFile');
        }
        if (input) input.click();
    }

    function openSpecLab() {
        var handoffPath = String(state.psdPath || state.handoffPath || state.sourcePath || '').trim();
        // The advanced workspace is the next rung of the same job, not a new
        // project. Carry the deployment identity with the paint so a user who
        // already chose dirtlatemodel 438 (or any other car) never has to find
        // it again before Generate / Deploy.
        var handoffIdentity = '';
        if (state.car) handoffIdentity += '&easy_car=' + encodeURIComponent(state.car);
        if (validId(state.iracingId)) handoffIdentity += '&easy_id=' + encodeURIComponent(state.iracingId);
        handoffIdentity += '&easy_custom=' + (liveUseCustomNumber() ? '1' : '0');
        if (handoffPath) {
            var handoffUrl = api('/spec-sculpt.html?easy_paint=' + encodeURIComponent(handoffPath) + handoffIdentity);
            var handoffChild = window.open(handoffUrl, 'shokkerSpecSculptLab');
            if (handoffChild && typeof handoffChild.focus === 'function') handoffChild.focus();
            else window.location.href = handoffUrl;
            return;
        }
        // Modern Chromium/Electron may deliberately omit File.path. Keep the
        // advanced doorway seamless anyway: the same-origin child can borrow
        // the in-memory File directly from its Easy Mode opener and feed it
        // through the Original workspace's existing upload/PSD-import path.
        if (state.file) {
            var uploadChild = window.open(api('/spec-sculpt.html?easy_upload=1' + handoffIdentity), 'shokkerSpecSculptLab');
            if (uploadChild && typeof uploadChild.focus === 'function') uploadChild.focus();
            else {
                state.error = 'Your browser blocked the Original Spec Sculpt window. Allow the popup, then try again.';
                state.errorContext = 'preview';
                renderRail();
            }
            return;
        }
        try {
            if (typeof window.openSpecSculptLab === 'function') {
                window.openSpecSculptLab();
                return;
            }
        } catch (e) {}
        var child = window.open(api('/spec-sculpt.html?' + handoffIdentity.slice(1)), 'shokkerSpecSculptLab');
        if (!child) window.location.href = api('/spec-sculpt.html?' + handoffIdentity.slice(1));
    }

    async function acceptFile(file, options) {
        options = options || ((file === state.file && state.liveSourceMeta) ? state.liveSourceMeta : {});
        if (!file || !ACCEPTED.test(file.name || '')) {
            state.phase = 'error';
            state.error = 'Choose a PSD, TGA, PNG, JPG or JPEG iRacing paint file.';
            state.errorContext = 'source';
            render();
            return;
        }
        var directPsdUpload = isPsd(file) && !options.psdPath;
        var directPsdPath = directPsdUpload ? String(file.path || '').trim() : '';
        abortActive();
        abortRecommendations();
        var serial = ++requestSerial;
        activeController = typeof AbortController !== 'undefined' ? new AbortController() : null;
        state.file = file;
        state.liveSourceMeta = options.identity ? options : null;
        state.handoffPath = String(options.originalPath || file.path || '').trim();
        state.sourcePath = '';
        state.serverSourcePath = '';
        state.sourceToken = '';
        state.filename = options.displayName || file.name;
        state.format = options.format || ((file.name.split('.').pop() || 'paint').toUpperCase());
        state.seedBase = hashSeed(file);
        state.phase = 'checking';
        state.progressStep = directPsdUpload ? 'protecting' : 'checking';
        state.error = '';
        state.errorContext = '';
        state.retryable = false;
        state.status = directPsdUpload
            ? 'Reading the PSD once and protecting numbers, sponsors and logos...'
            : 'Checking the file and exact template size...';
        state.sourceUrl = options.sourcePreviewDataUrl || '';
        state.specUrl = '';
        state.showSpecMap = false;
        state.showBigResult = false;
        state.materialMetrics = {};
        state.psdPath = '';
        state.psdImportData = null;
        state.inferredUseCustomNumber = null;
        state.protectKeys = [];
        state.layerSummary = null;
        state.saved = null;
        state.selectedLook = null;
        state.previousLooks = {};
        state.materialScale = 1;
        state.materialImpact = 'balanced';
        state.colorTargets = [];
        state.activeColorId = '';
        state.pickingColor = false;
        state.paintProfile = null;
        state.palette = [];
        state.recommendedLookKeys = [];
        state.recommendationKey = '';
        state.looks.forEach(function (look) { delete look.paintThumb; delete look.paintThumbContext; });
        state.libraryKind = 'recommended';
        state.libraryQuery = '';
        render();

        try {
            if (!directPsdUpload && Array.isArray(options.knownResolution) && options.knownResolution.length >= 2) {
                state.resolution = [Number(options.knownResolution[0]), Number(options.knownResolution[1])];
                if (state.resolution[0] !== 2048 || state.resolution[1] !== 2048) {
                    throw new Error('This file is ' + state.resolution.join(' x ') + '. Choose an exact 2048 x 2048 iRacing paint.');
                }
                render();
            } else if (!directPsdUpload) {
                var analyzeFd = new FormData();
                analyzeFd.append('paint_file', file);
                var analyzeResponse = await fetch(api('/api/spec-sculpt/analyze'), {
                    method: 'POST', body: analyzeFd, signal: activeController && activeController.signal
                });
                var analyzed = await readJsonResponse(analyzeResponse, 'Shokker could not read that paint file.');
                if (serial !== requestSerial) return;
                if (!analyzeResponse.ok || !analyzed.success) throw responseError(analyzeResponse, analyzed.error, 'Shokker could not read that paint file.');
                state.resolution = analyzed.original_resolution || [];
                state.sourceUrl = analyzed.preview_data_url || '';
                state.sourceToken = String(analyzed.source_token || '');
                if (state.resolution[0] !== 2048 || state.resolution[1] !== 2048) {
                    throw new Error('This file is ' + state.resolution.join(' x ') + '. Choose an exact 2048 x 2048 iRacing paint.');
                }
                render();
            }

            if (isPsd(file) || options.psdPath) {
                state.progressStep = 'protecting';
                state.status = 'Reading the PSD and protecting numbers, sponsors and logos...';
                render();
                var psdResponse = null;
                var psd = options.psdImportData && options.psdImportData.success ? options.psdImportData : null;
                if (!psd) {
                    if (options.psdPath || directPsdPath) {
                        psdResponse = await fetch(api('/api/psd-import'), {
                            method: 'POST', headers: { 'Content-Type': 'application/json', 'X-Shokker-Internal': '1' },
                            body: JSON.stringify({ psd_path: options.psdPath || directPsdPath, thumbnail_size: 512 }),
                            signal: activeController && activeController.signal
                        });
                    } else {
                        var psdFd = new FormData();
                        psdFd.append('file', file);
                        psdFd.append('thumbnail_size', '512');
                        psdResponse = await fetch(api('/api/psd-import'), {
                            method: 'POST', headers: { 'X-Shokker-Internal': '1' }, body: psdFd,
                            signal: activeController && activeController.signal
                        });
                    }
                    psd = await readJsonResponse(psdResponse, 'The PSD layer tree could not be read.');
                }
                if (serial !== requestSerial) return;
                if ((psdResponse && !psdResponse.ok) || !psd.success) throw responseError(psdResponse, psd.error, 'The PSD layer tree could not be read.');
                if (psd.width !== 2048 || psd.height !== 2048) throw new Error('This PSD is not exactly 2048 x 2048.');
                state.resolution = [psd.width, psd.height];
                state.psdPath = psd.psd_path || options.psdPath || directPsdPath || '';
                // Keep the already-validated composite + layer tree in memory so
                // Original Spec Sculpt can hydrate instantly from its same-origin
                // Easy opener instead of parsing this PSD a second time.
                state.psdImportData = psd;
                // The first direct PSD import leaves a server-readable source.
                // Reuse it for every candidate/preview instead of re-uploading
                // a potentially 256 MB template each time. Live-canvas imports
                // deliberately stay on their captured PNG instead.
                if (directPsdUpload) state.serverSourcePath = state.psdPath;
                if (!options.keepAnalyzedPreview) state.sourceUrl = psd.composite || state.sourceUrl;
                if (!state.sourceUrl) throw new Error('The PSD composite preview came back empty.');
                state.layerSummary = classifyPsd(psd.layers || []);
                state.protectKeys = state.layerSummary.protectKeys;
                render();
            }

            await ensureEnvironment();
            if (serial !== requestSerial) return;
            borrowDeploymentIdentity();
            borrowDeploymentFromSource(state.handoffPath || state.filename);
            await updatePaintGuidance();
            if (serial !== requestSerial) return;
            state.phase = 'pick';
            state.status = '';
            if (restoreRecoveryPlan()) {
                generatePreview('Restoring your last sculpt for this paint...');
            } else {
                beginSmartStartingPoint();
            }
        } catch (error) {
            if (error && error.name === 'AbortError') return;
            if (serial !== requestSerial) return;
            state.phase = 'error';
            state.retryable = isRetryableError(error);
            state.error = friendlyError(error, 'Shokker could not sculpt that paint.');
            state.errorContext = 'source';
            state.status = '';
            render();
        }
    }

    async function acceptPath(path) {
        path = String(path || '').trim();
        if (!path || !ACCEPTED.test(path)) {
            state.phase = 'error';
            state.error = 'The paint already open is not a supported PSD, TGA, PNG, JPG or JPEG file.';
            state.errorContext = 'source';
            render();
            return;
        }
        abortActive();
        abortRecommendations();
        var serial = ++requestSerial;
        activeController = typeof AbortController !== 'undefined' ? new AbortController() : null;
        state.file = null;
        state.liveSourceMeta = null;
        state.handoffPath = path;
        state.sourcePath = path;
        state.serverSourcePath = '';
        state.sourceToken = '';
        state.filename = basename(path);
        state.format = ((state.filename.split('.').pop() || 'paint').toUpperCase());
        state.seedBase = hashSeed({ name: path });
        state.phase = 'checking';
        state.progressStep = 'checking';
        state.error = '';
        state.errorContext = '';
        state.retryable = false;
        state.status = 'Checking the paint already open...';
        state.sourceUrl = '';
        state.specUrl = '';
        state.showSpecMap = false;
        state.showBigResult = false;
        state.materialMetrics = {};
        state.psdPath = '';
        state.psdImportData = null;
        state.inferredUseCustomNumber = null;
        state.protectKeys = [];
        state.layerSummary = null;
        state.saved = null;
        state.selectedLook = null;
        state.previousLooks = {};
        state.materialScale = 1;
        state.materialImpact = 'balanced';
        state.colorTargets = [];
        state.activeColorId = '';
        state.pickingColor = false;
        state.paintProfile = null;
        state.palette = [];
        state.recommendedLookKeys = [];
        state.recommendationKey = '';
        state.looks.forEach(function (look) { delete look.paintThumb; });
        state.libraryKind = 'recommended';
        state.libraryQuery = '';
        render();

        try {
            // PSD import already returns the exact dimensions, composite, layer
            // tree, and server-readable path. Sending the same large template
            // through /analyze first doubled the wait when Easy Mode had only a
            // path (for example after a live-canvas fallback). Flat paints still
            // use the lightweight analyzer.
            if (!isPsd()) {
                var analyzeResponse = await fetch(api('/api/spec-sculpt/analyze'), {
                    method: 'POST', headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ paint_file: path }), signal: activeController && activeController.signal
                });
                var analyzed = await readJsonResponse(analyzeResponse, 'Shokker could not read the open paint.');
                if (serial !== requestSerial) return;
                if (!analyzeResponse.ok || !analyzed.success) throw responseError(analyzeResponse, analyzed.error, 'Shokker could not read the open paint.');
                state.resolution = analyzed.original_resolution || [];
                state.sourceUrl = analyzed.preview_data_url || '';
                state.sourceToken = String(analyzed.source_token || '');
                if (state.resolution[0] !== 2048 || state.resolution[1] !== 2048) {
                    throw new Error('This file is ' + state.resolution.join(' x ') + '. Choose an exact 2048 x 2048 iRacing paint.');
                }
                render();
            } else {
                state.progressStep = 'protecting';
                state.status = 'Reading the open PSD once and protecting numbers, sponsors and logos...';
                render();
                var psdResponse = await fetch(api('/api/psd-import'), {
                    method: 'POST', headers: { 'Content-Type': 'application/json', 'X-Shokker-Internal': '1' },
                    body: JSON.stringify({ psd_path: path, thumbnail_size: 512 }),
                    signal: activeController && activeController.signal
                });
                var psd = await readJsonResponse(psdResponse, 'The open PSD layer tree could not be read.');
                if (serial !== requestSerial) return;
                if (!psdResponse.ok || !psd.success) throw responseError(psdResponse, psd.error, 'The PSD layer tree could not be read.');
                if (psd.width !== 2048 || psd.height !== 2048) throw new Error('This PSD is not exactly 2048 x 2048.');
                state.resolution = [psd.width, psd.height];
                state.psdPath = psd.psd_path || path;
                state.psdImportData = psd;
                state.sourceUrl = psd.composite || state.sourceUrl;
                if (!state.sourceUrl) throw new Error('The PSD composite preview came back empty.');
                state.layerSummary = classifyPsd(psd.layers || []);
                state.protectKeys = state.layerSummary.protectKeys;
                render();
            }
            await ensureEnvironment();
            if (serial !== requestSerial) return;
            borrowDeploymentIdentity();
            borrowDeploymentFromSource(state.sourcePath || state.filename);
            await updatePaintGuidance();
            if (serial !== requestSerial) return;
            state.phase = 'pick';
            state.status = '';
            if (restoreRecoveryPlan()) {
                generatePreview('Restoring your last sculpt for this paint...');
            } else {
                beginSmartStartingPoint();
            }
        } catch (error) {
            if (error && error.name === 'AbortError') return;
            if (serial !== requestSerial) return;
            state.phase = 'error';
            state.retryable = isRetryableError(error);
            state.error = friendlyError(error, 'Shokker could not sculpt that paint.');
            state.errorContext = 'source';
            state.status = '';
            render();
        }
    }

    function classifyPsd(tree) {
        var leaves = [];
        (function walk(nodes) {
            (nodes || []).forEach(function (layer) {
                if (layer && layer.children && layer.children.length) walk(layer.children);
                else if (layer) leaves.push(layer);
            });
        })(tree);

        var summary = { total: leaves.length, paint: 0, protected: 0, hidden: 0, guides: 0, protectKeys: [] };
        leaves.forEach(function (layer) {
            var label = String(layer.path || layer.name || '');
            if (layer.effective_visible === false) {
                summary.hidden += 1;
                return;
            }
            if (PROTECT_RE.test(label)) {
                summary.protected += 1;
                if (layer.layer_key != null) summary.protectKeys.push(String(layer.layer_key));
                return;
            }
            if (GUIDE_RE.test(label)) {
                summary.guides += 1;
                summary.protected += 1;
                if (layer.layer_key != null) summary.protectKeys.push(String(layer.layer_key));
                return;
            }
            summary.paint += 1;
        });
        return summary;
    }

    function buildPlan(save) {
        var look = state.selectedLook;
        var values = {
            strict2048: true,
            save_tga: !!save,
            seed: materialPlanSeed(),
            chromatic_shift: true,
            // SPB-BETA-2026-07-20: guided flow uses one-pass paint coupling;
            // Original Advanced retains the full legacy trace on demand.
            fast_trace: true,
            material_scale: state.materialScale,
            material_impact: state.materialImpact,
            easy_color_layers: state.colorTargets.map(function (target) {
                return colorLayerPlan(target, target.look);
            }).filter(Boolean)
        };
        if (look && look.kind === 'preset') values.preset_stack = [{ id: look.id, weight: 100 }];
        else if (look && look.kind === 'catalog') values.catalog_stack = [{ id: look.id, weight: 100, registry_type: look.swatchType || '' }];
        else if (look && look.kind === 'mode') {
            values.mode = look.id;
            if (look.id === 'zoned') values.zoned_drama = 1.0;
        }
        if (!save) values.preview_tex_size = 512;
        if (state.psdPath && state.protectKeys.length) {
            values.psd_path = state.psdPath;
            values.protect_layer_keys = state.protectKeys;
            values.protect_material = 'satin';
            values.mask_feather = 2;
        } else {
            values.auto_protect = true;
            values.auto_protect_strength = 1;
            values.mask_feather = 2;
        }
        if (save) {
            values.iracing_id = state.iracingId;
            values.deploy_car_folder = state.car;
            values.use_custom_number = liveUseCustomNumber();
        }
        if (!state.file || state.serverSourcePath) {
            values.paint_file = state.serverSourcePath || state.sourcePath;
            return { body: JSON.stringify(values), headers: { 'Content-Type': 'application/json' } };
        }
        var fd = new FormData();
        fd.append('paint_file', state.file);
        Object.keys(values).forEach(function (key) {
            var value = values[key];
            fd.append(key, Array.isArray(value) ? JSON.stringify(value) : String(value));
        });
        return { body: fd, headers: {} };
    }

    async function generatePreview(status) {
        if ((!state.file && !state.sourcePath) || !state.selectedLook) return;
        abortActive();
        // Invalidate the prior request even when this plan is restored from
        // cache; an already-resolving fetch must never overwrite an instant Back.
        var serial = ++requestSerial;
        var cacheKey = previewCacheKey();
        var cached = state.previewCache[cacheKey];
        if (cached) {
            state.specUrl = cached.specUrl;
            state.materialSummary = cached.materialSummary || '';
            state.materialMetrics = cached.materialMetrics || {};
            applyColorReport(cached.colorReport);
            state.phase = 'ready';
            state.error = '';
            state.errorContext = '';
            state.retryable = false;
            state.saved = null;
            state.status = '';
            state.showSpecMap = false;
            persistRecoveryPlan();
            render();
            if (state.advanceToSaveAfterPreview) {
                state.advanceToSaveAfterPreview = false;
                advanceToInstallCard();
            } else restoreLibraryView();
            loadPaintAwareRecommendations();
            return;
        }
        activeController = typeof AbortController !== 'undefined' ? new AbortController() : null;
        state.phase = 'sculpting';
        state.progressStep = 'sculpting';
        state.error = '';
        state.errorContext = '';
        state.retryable = false;
        state.saved = null;
        state.status = status || 'Sculpting the material plan...';
        state.specUrl = '';
        state.showSpecMap = false;
        state.materialMetrics = {};
        render();
        try {
            var plan = buildPlan(false);
            var response = await fetch(api('/api/spec-sculpt/generate'), {
                method: 'POST', headers: plan.headers, body: plan.body, signal: activeController && activeController.signal
            });
            var payload = await readJsonResponse(response, 'The material preview did not finish.');
            if (serial !== requestSerial) return;
            if (!response.ok || !payload.success) throw responseError(response, payload.error, 'The material preview did not finish.');
            if (!payload.original_resolution || payload.original_resolution[0] !== 2048 || payload.original_resolution[1] !== 2048) {
                throw new Error('The server could not confirm an exact 2048 x 2048 source.');
            }
            state.specUrl = payload.previews && payload.previews.composite;
            if (!state.specUrl) throw new Error('The material preview came back empty.');
            var colorReport = (payload.sculpt && payload.sculpt.easy_color_layers) || [];
            applyColorReport(colorReport);
            rememberPreview(cacheKey, {
                specUrl: state.specUrl,
                colorReport: colorReport,
                materialSummary: '',
                materialMetrics: {}
            });
            state.phase = 'ready';
            state.status = '';
            persistRecoveryPlan();
            render();
            if (state.advanceToSaveAfterPreview) {
                state.advanceToSaveAfterPreview = false;
                advanceToInstallCard();
            } else restoreLibraryView();
            loadPaintAwareRecommendations();
        } catch (error) {
            if (error && error.name === 'AbortError') return;
            if (serial !== requestSerial) return;
            state.phase = state.sourceUrl ? 'pick' : 'error';
            state.retryable = isRetryableError(error);
            state.error = friendlyError(error, 'The material preview did not finish.');
            state.errorContext = 'preview';
            render();
            restoreLibraryView();
        }
    }

    async function saveToIRacing() {
        if (!state.selectedLook) {
            state.phase = 'pick';
            state.error = 'Pick a look before sending it to iRacing.';
            state.errorContext = 'preview';
            render();
            return;
        }
        var unfinished = incompleteColorTarget();
        if (unfinished) {
            state.activeColorId = unfinished.id;
            state.pickingColor = false;
            render();
            var recoveryTarget = unfinished.look ? document.querySelector('.spb-easy-sculpt-reach') : $('spbEasySculptLookSearch');
            try {
                if (recoveryTarget) recoveryTarget.scrollIntoView({ behavior: 'smooth', block: 'center' });
                if (!unfinished.look && recoveryTarget) recoveryTarget.focus({ preventScroll: true });
            } catch (e) {}
            return;
        }
        var idInput = $('spbEasySculptId');
        var carInput = $('spbEasySculptCar');
        if (idInput) state.iracingId = idInput.value.trim();
        if (carInput) state.car = carInput.value;
        var knownCar = state.cars.some(function (car) { return car.name === state.car; });
        if (!validId(state.iracingId) || !knownCar) {
            state.exportOpen = true;
            state.error = !validId(state.iracingId)
                ? 'Enter your 4–7 digit iRacing Customer ID.'
                : 'Choose the iRacing car folder that should receive this paint.';
            state.errorContext = 'install';
            renderRail();
            var first = !validId(state.iracingId) ? $('spbEasySculptId') : $('spbEasySculptCar');
            try { if (first) first.focus(); } catch (e) {}
            return;
        }
        var expectedUseCustomNumber = liveUseCustomNumber();
        var expectedPaintName = (expectedUseCustomNumber ? 'car_num_' : 'car_') + state.iracingId + '.tga';
        var expectedSpecName = 'car_spec_' + state.iracingId + '.tga';

        abortActive();
        var serial = ++requestSerial;
        activeController = typeof AbortController !== 'undefined' ? new AbortController() : null;
        state.phase = 'saving';
        state.progressStep = 'saving';
        state.error = '';
        state.errorContext = '';
        state.retryable = false;
        state.status = 'Rendering the full 2048 spec and installing it in ' + state.car + '...';
        render();
        try {
            var plan = buildPlan(true);
            var response = await fetch(api('/api/spec-sculpt/generate'), {
                method: 'POST', headers: plan.headers, body: plan.body, signal: activeController && activeController.signal
            });
            var payload = await readJsonResponse(response, 'The final paint did not finish.');
            if (serial !== requestSerial) return;
            if (!response.ok || !payload.success) throw responseError(response, payload.error, 'The final paint did not finish.');
            var deployed = payload.deploy_to_iracing || {};
            if (!deployed.success || deployed.verified !== true) throw new Error(deployed.error || 'The iRacing files could not be verified after installation.');
            var deployedNames = Array.isArray(deployed.deployed) ? deployed.deployed.slice().sort() : [];
            var expectedNames = [expectedPaintName, expectedSpecName].sort();
            var verifiedNames = Array.isArray(deployed.files) ? deployed.files.map(function (file) { return file && file.name; }).filter(Boolean).sort() : [];
            var exactPair = deployedNames.length === 2 && expectedNames.every(function (name, index) { return deployedNames[index] === name; }) &&
                verifiedNames.length === 2 && expectedNames.every(function (name, index) { return verifiedNames[index] === name; });
            var exactRoute = String(deployed.car_folder || '') === String(state.car) && String(deployed.iracing_id || '') === String(state.iracingId) &&
                payload.use_custom_number === expectedUseCustomNumber;
            if (!exactPair || !exactRoute || !deployed.target) {
                throw new Error('Shokker did not verify the exact paint + spec pair for the car and number you chose. Nothing will be called DONE.');
            }
            var durableSpecPath = String(deployed.target).replace(/[\\/]+$/, '') + '/' + expectedSpecName;
            // The install contains the whole plan. Naming it after only the
            // currently selected color made a correct multi-material render
            // sound incomplete in both the receipt and Main Render lock.
            var lookName = materialPlanName();
            // Lock Main Render to the verified iRacing copy, not the temporary
            // Spec Sculpt job (old jobs are intentionally purged after 12).
            activateSculptSpecOverride(durableSpecPath, lookName);
            state.saved = {
                message: deployed.message || ('Paint and spec installed for ' + state.car + '.'),
                files: deployed.deployed || [],
                target: deployed.target || state.car,
                lookName: lookName,
                specPath: durableSpecPath,
                useCustomNumber: payload.use_custom_number === true,
                // [2026-08-09 S22] iRacing compiles .tga paints into .mip and
                // SPB never touches .mip. A leftover one older than the file we
                // just wrote may be what iRacing actually loads, which would
                // show the painter "INSTALLED" and then an unchanged car.
                staleMips: Array.isArray(deployed.stale_mips) ? deployed.stale_mips : []
            };
            state.config.use_custom_number = payload.use_custom_number === true;
            state.phase = 'saved';
            state.status = '';
            state.exportOpen = false;
            state.recoveredPlan = false;
            state.showSpecMap = false;
            state.showBigResult = false;
            render();
            fetch(api('/config'), {
                method: 'POST', headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ iracing_id: state.iracingId, active_car: state.car, use_custom_number: state.saved.useCustomNumber })
            }).catch(function () {});
        } catch (error) {
            if (error && error.name === 'AbortError') return;
            if (serial !== requestSerial) return;
            state.phase = 'ready';
            state.retryable = isRetryableError(error);
            state.error = friendlyError(error, 'The iRacing install did not finish.');
            state.errorContext = 'install';
            state.exportOpen = true;
            render();
            var exportBox = document.querySelector('.spb-easy-sculpt-export');
            if (exportBox) exportBox.classList.add('has-error');
        }
    }

    function loadImage(src) {
        return new Promise(function (resolve, reject) {
            var image = new Image();
            image.onload = function () { resolve(image); };
            image.onerror = function () { reject(new Error('Preview image could not be decoded.')); };
            image.src = src;
        });
    }

    function drawSpecProofChannels() {
        if (!state.specUrl) return;
        var serial = ++specProofSerial;
        loadImage(state.specUrl).then(function (image) {
            if (serial !== specProofSerial || !mounted) return;
            // Same four-proof renderer as Pro and Easy By Color. The three data
            // lanes are literal Photoshop-style R/G/B ramps, never grayscale.
            if (typeof window.spbRenderSpecProofSet === 'function') {
                window.spbRenderSpecProofSet(image, {
                    all: $('spbEasySculptSpecAll'),
                    r: $('spbEasySculptSpecR'),
                    g: $('spbEasySculptSpecG'),
                    b: $('spbEasySculptSpecB')
                }, 128);
            }
        }).catch(function () {});
    }

    function drawLightingPreview() {
        var canvas = $('spbEasySculptLit');
        if (!canvas || !state.sourceUrl || !state.specUrl) return;
        var serial = ++drawSerial;
        Promise.all([loadImage(state.sourceUrl), loadImage(state.specUrl)]).then(function (images) {
            if (serial !== drawSerial || !mounted) return;
            var source = images[0], spec = images[1];
            var size = Math.min(640, source.naturalWidth || source.width || 512);
            var width = size;
            var height = Math.max(1, Math.round(size * ((source.naturalHeight || source.height) / (source.naturalWidth || source.width))));
            canvas.width = width;
            canvas.height = height;
            var sourceCanvas = document.createElement('canvas');
            var specCanvas = document.createElement('canvas');
            sourceCanvas.width = specCanvas.width = width;
            sourceCanvas.height = specCanvas.height = height;
            var sourceContext = sourceCanvas.getContext('2d', { willReadFrequently: true });
            var specContext = specCanvas.getContext('2d', { willReadFrequently: true });
            sourceContext.drawImage(source, 0, 0, width, height);
            specContext.drawImage(spec, 0, 0, width, height);
            var paint = sourceContext.getImageData(0, 0, width, height);
            var material = specContext.getImageData(0, 0, width, height);
            var out = new ImageData(width, height);
            var sums = [0, 0, 0], squares = [0, 0, 0], count = width * height;
            var recolorTargets = state.colorTargets.map(function (target) {
                return target.replacementColor ? { color: target.color, replacement: hexRgb(target.replacementColor), tolerance: target.tolerance } : null;
            }).filter(Boolean);
            for (var y = 0; y < height; y++) {
                for (var x = 0; x < width; x++) {
                    var index = (y * width + x) * 4;
                    var metallic = material.data[index] / 255;
                    var roughness = material.data[index + 1] / 255;
                    var clearcoatRead = material.data[index + 2] / 255;
                    var clearcoatStrength = 1 - clearcoatRead; // iRacing blue is inverted: 16 = maximum coat.
                    sums[0] += metallic; sums[1] += roughness; sums[2] += clearcoatRead;
                    squares[0] += metallic * metallic; squares[1] += roughness * roughness; squares[2] += clearcoatRead * clearcoatRead;
                    var materialLift = (clearcoatStrength * (1 - roughness) * 10) + (metallic * (1 - roughness) * 5);
                    // Owner 2026-07-19: both fake spotlights are gone. The
                    // preview response comes only from each pixel's real M/R/CC
                    // values; screen position can never paint a beam on the car.
                    var materialGain = 0.90 + (metallic - 0.5) * 0.13 + (clearcoatStrength - 0.5) * 0.10 - (roughness - 0.5) * 0.16;
                    var replacement = null;
                    for (var ri = recolorTargets.length - 1; ri >= 0; ri--) {
                        var rt = recolorTargets[ri];
                        var dr = paint.data[index] - rt.color[0], dg = paint.data[index + 1] - rt.color[1], db = paint.data[index + 2] - rt.color[2];
                        if (Math.sqrt(dr * dr + dg * dg + db * db) <= rt.tolerance * 2.55) { replacement = rt.replacement; break; }
                    }
                    var localShade = 0.55 + 0.9 * ((paint.data[index] * 0.2126 + paint.data[index + 1] * 0.7152 + paint.data[index + 2] * 0.0722) / 255);
                    for (var channel = 0; channel < 3; channel++) {
                        var base = replacement ? Math.min(255, replacement[channel] * localShade) : paint.data[index + channel];
                        var value = base * materialGain + materialLift;
                        out.data[index + channel] = Math.max(0, Math.min(255, Math.round(value)));
                    }
                    out.data[index + 3] = paint.data[index + 3];
                }
            }
            canvas.getContext('2d').putImageData(out, 0, 0);
            var means = sums.map(function (sum) { return sum / count; });
            var deviations = squares.map(function (sum, index) {
                return Math.sqrt(Math.max(0, sum / count - means[index] * means[index]));
            });
            var responseTarget = activeColorTarget();
            var responseRawMeans = responseTarget && Array.isArray(responseTarget.materialMeans)
                ? responseTarget.materialMeans : means;
            var responseDeviations = responseTarget && Array.isArray(responseTarget.materialDeviations)
                ? responseTarget.materialDeviations : deviations;
            var responseMeans = [responseRawMeans[0], responseRawMeans[1], 1 - responseRawMeans[2]];
            var guidance = window.spbEasySculptGuidance;
            var response = guidance && typeof guidance.describeMaterialResponse === 'function'
                ? guidance.describeMaterialResponse(responseRawMeans, responseDeviations)
                : {
                    summary: 'MATERIAL READOUT · ' + materialWords(responseMeans[0], responseMeans[1], responseMeans[2]),
                    metrics: { metal: responseRawMeans[0], gloss: 1 - responseRawMeans[1], coat: responseMeans[2] }
                };
            state.materialSummary = response.summary;
            var note = $('spbEasySculptMaterialSummary');
            if (note) note.textContent = state.materialSummary;
            var meterValues = response.metrics;
            state.materialMetrics = meterValues;
            var cached = state.previewCache[previewCacheKey()];
            if (cached && cached.specUrl === state.specUrl) {
                cached.materialSummary = state.materialSummary;
                cached.materialMetrics = meterValues;
            }
            Object.keys(meterValues).forEach(function (name) {
                var percent = Math.max(0, Math.min(100, Math.round(meterValues[name] * 100)));
                var meter = document.querySelector('[data-material-meter="' + name + '"]');
                var value = document.querySelector('[data-material-value="' + name + '"]');
                if (meter) meter.style.width = percent + '%';
                if (value) value.textContent = percent;
            });
        }).catch(function () {
            var note = $('spbEasySculptMaterialSummary');
            if (note) note.textContent = 'The spec is ready; the optional lighting simulation could not be drawn.';
        });
    }

    function materialWords(metallic, roughness, clearcoat) {
        var metal = metallic > 0.58 ? 'strong metal accents' : (metallic > 0.36 ? 'controlled metallic depth' : 'mostly painted surfaces');
        var gloss = roughness < 0.34 ? 'sharp gloss' : (roughness < 0.56 ? 'mixed satin and gloss' : 'soft satin grip');
        var coat = clearcoat > 0.58 ? 'deep clearcoat' : (clearcoat > 0.34 ? 'balanced clearcoat' : 'restrained clearcoat');
        return metal + ' / ' + gloss + ' / ' + coat;
    }

    window.spbEasySculpt = {
        mount: mount,
        unmount: unmount,
        reset: reset,
        openOriginal: openSpecLab,
        friendlyCarName: friendlyCarName,
        getState: function () { return state; }
    };
})();
