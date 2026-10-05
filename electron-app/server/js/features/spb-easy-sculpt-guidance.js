/* Easy Spec Sculpt paint guidance — pure, deterministic image analysis.
   Owner direction 2026-07-20: keep every look, but make the first choice feel
   intelligent. This helper has no DOM or network dependency so its ranking and
   palette behavior can be tested without the full app. */
(function (root, factory) {
    var api = factory();
    if (typeof module === 'object' && module.exports) module.exports = api;
    if (root) root.spbEasySculptGuidance = api;
})(typeof window !== 'undefined' ? window : globalThis, function () {
    'use strict';

    var ARCHETYPE_TERMS = {
        candy: ['candy', 'pearl', 'wet', 'glass', 'gloss'],
        holo: ['holo', 'prism', 'iridescent', 'chameleon', 'shift', 'spectral'],
        flake: ['flake', 'sparkle', 'diamond', 'metallic'],
        metal: ['chrome', 'metal', 'titanium', 'brushed', 'anodized', 'gold'],
        dark: ['obsidian', 'midnight', 'phantom', 'black', 'stealth', 'neon'],
        texture: ['carbon', 'weave', 'forged', 'fracture', 'mosaic', 'mesh'],
        soft: ['satin', 'matte', 'silk', 'pearl', 'frozen']
    };
    var COLOR_TERMS = {
        RED: ['red', 'ruby', 'crimson', 'blood', 'cherry', 'rosso'],
        ORANGE: ['orange', 'copper', 'ember', 'papaya', 'tangerine'],
        YELLOW: ['yellow', 'gold', 'solar', 'amber', 'canary'],
        LIME: ['lime', 'toxic', 'acid', 'chartreuse', 'venom'],
        GREEN: ['green', 'emerald', 'jade', 'forest', 'verdant'],
        TEAL: ['teal', 'aqua', 'turquoise', 'seafoam', 'ocean'],
        CYAN: ['cyan', 'aqua', 'cobalt', 'ice', 'electric blue'],
        BLUE: ['blue', 'cobalt', 'sapphire', 'ocean', 'arctic'],
        VIOLET: ['violet', 'ultraviolet', 'amethyst', 'orchid'],
        PURPLE: ['purple', 'violet', 'plum', 'amethyst', 'royal'],
        MAGENTA: ['magenta', 'fuchsia', 'orchid', 'hyperpink'],
        PINK: ['pink', 'rose', 'blush', 'bubblegum'],
        BLACK: ['black', 'obsidian', 'midnight', 'gunmetal', 'stealth'],
        CHARCOAL: ['charcoal', 'graphite', 'gunmetal', 'smoked'],
        GRAY: ['gray', 'grey', 'silver', 'titanium', 'pewter'],
        SILVER: ['silver', 'chrome', 'platinum', 'mercury'],
        WHITE: ['white', 'pearl', 'porcelain', 'ice', 'frost']
    };
    var COLOR_SEARCH_WORDS = {};
    Object.keys(COLOR_TERMS).forEach(function (name) {
        COLOR_SEARCH_WORDS[name.toLowerCase()] = 1;
        COLOR_TERMS[name].forEach(function (term) { COLOR_SEARCH_WORDS[term] = 1; });
    });
    var SEARCH_INTENTS = [
        ['shiny', 'shine', 'gloss', 'glossy', 'mirror', 'wet', 'polished', 'glass', 'chrome', 'clearcoat'],
        ['matte', 'flat', 'dull', 'satin', 'stealth', 'suede', 'soft'],
        ['metal', 'metallic', 'chrome', 'aluminum', 'steel', 'titanium', 'brushed', 'anodized'],
        ['sparkle', 'sparkly', 'glitter', 'flake', 'flakes', 'pearl', 'diamond', 'prizm'],
        ['wild', 'crazy', 'loud', 'dramatic', 'fractured', 'shokk', 'venom', 'inferno', 'neon', 'rainbow', 'holographic'],
        ['subtle', 'clean', 'classic', 'factory', 'foundation', 'satin', 'pearl', 'brushed'],
        ['carbon', 'fiber', 'fibre', 'weave', 'twill', 'forged'],
        ['rough', 'gritty', 'grit', 'stone', 'concrete', 'rust', 'hammered', 'sandpaper'],
        ['shift', 'chameleon', 'flip', 'iridescent', 'colorshoxx', 'holo', 'holographic', 'prism', 'prizm', 'spectral']
    ];
    var SEARCH_FILLER = {
        a: 1, an: 1, and: 1, can: 1, for: 1, give: 1, i: 1, it: 1,
        kind: 1, like: 1, look: 1, looking: 1, make: 1, material: 1, me: 1,
        maybe: 1, more: 1, of: 1, paint: 1, please: 1, really: 1, show: 1,
        something: 1, the: 1, very: 1, want: 1, with: 1, you: 1, high: 1
    };

    function clamp(value, low, high) { return Math.max(low, Math.min(high, value)); }
    function stableSeed(baseSeed, signature) {
        var hash = (Number(baseSeed) >>> 0) || 9101;
        var text = String(signature || '');
        for (var i = 0; i < text.length; i++) {
            hash ^= text.charCodeAt(i);
            hash = Math.imul(hash, 16777619);
        }
        return (hash >>> 0) || (Number(baseSeed) >>> 0) || 9101;
    }
    function hex(rgb) {
        return '#' + rgb.map(function (value) {
            return clamp(Math.round(value), 0, 255).toString(16).padStart(2, '0');
        }).join('').toUpperCase();
    }
    function distance(a, b) {
        var dr = a[0] - b[0], dg = a[1] - b[1], db = a[2] - b[2];
        return Math.sqrt(dr * dr * 0.8 + dg * dg * 1.15 + db * db * 1.05);
    }
    function colorName(rgb) {
        var r = rgb[0] / 255, g = rgb[1] / 255, b = rgb[2] / 255;
        var max = Math.max(r, g, b), min = Math.min(r, g, b);
        var light = (max + min) / 2;
        if (max - min < 0.09) {
            if (light < 0.12) return 'BLACK';
            if (light < 0.34) return 'CHARCOAL';
            if (light < 0.68) return 'GRAY';
            if (light < 0.9) return 'SILVER';
            return 'WHITE';
        }
        var hue;
        if (max === r) hue = ((g - b) / (max - min) + (g < b ? 6 : 0)) / 6;
        else if (max === g) hue = ((b - r) / (max - min) + 2) / 6;
        else hue = ((r - g) / (max - min) + 4) / 6;
        var names = ['RED', 'ORANGE', 'YELLOW', 'LIME', 'GREEN', 'TEAL', 'CYAN', 'BLUE', 'VIOLET', 'PURPLE', 'MAGENTA', 'PINK'];
        return names[Math.round(hue * names.length) % names.length];
    }

    function chooseAutoColors(palette, existingColors, limit) {
        var neutralNames = ['BLACK', 'CHARCOAL', 'GRAY', 'SILVER', 'WHITE'];
        var existing = (existingColors || []).map(function (entry) {
            return Array.isArray(entry) ? entry : (entry && entry.color);
        }).filter(Boolean);
        var wanted = Math.max(1, Math.min(3, Number(limit) || 2));
        var available = (palette || []).filter(function (entry) {
            return entry && Array.isArray(entry.color) && !existing.some(function (rgb) {
                return distance(rgb, entry.color) < 12;
            });
        });
        var colorful = available.filter(function (entry) {
            return neutralNames.indexOf(entry.name || colorName(entry.color)) === -1;
        }).sort(function (a, b) {
            return (Number(b.coverage) || 0) - (Number(a.coverage) || 0);
        });
        var chosen = colorful.slice(0, wanted);
        while (chosen.length < wanted) {
            var remaining = available.filter(function (entry) { return chosen.indexOf(entry) === -1; });
            if (!remaining.length) break;
            remaining.sort(function (a, b) {
                // After picking the paint's real accent colors, choose a neutral
                // that is visibly different instead of another nearly-black bin.
                function contrast(row) {
                    if (!chosen.length) return 0;
                    return Math.min.apply(Math, chosen.map(function (item) { return distance(item.color, row.color); }));
                }
                var aScore = (Number(a.coverage) || 0) * 1.5 + contrast(a) / 8;
                var bScore = (Number(b.coverage) || 0) * 1.5 + contrast(b) / 8;
                return bScore - aScore;
            });
            chosen.push(remaining[0]);
        }
        return chosen.slice(0, wanted);
    }

    function analyzePixels(rgba, width, height) {
        width = Math.max(1, Number(width) || 1);
        height = Math.max(1, Number(height) || 1);
        var bins = Object.create(null);
        var lumSum = 0, lumSq = 0, satSum = 0, count = 0, edgeSum = 0, edgeCount = 0;
        var previousRow = new Float32Array(width);
        var currentRow = new Float32Array(width);
        for (var y = 0; y < height; y++) {
            for (var x = 0; x < width; x++) {
                var index = (y * width + x) * 4;
                if ((rgba[index + 3] == null ? 255 : rgba[index + 3]) < 48) continue;
                var r = rgba[index], g = rgba[index + 1], b = rgba[index + 2];
                var max = Math.max(r, g, b), min = Math.min(r, g, b);
                var lum = (0.299 * r + 0.587 * g + 0.114 * b) / 255;
                var sat = max > 0 ? (max - min) / max : 0;
                lumSum += lum; lumSq += lum * lum; satSum += sat; count += 1;
                currentRow[x] = lum;
                if (x) { edgeSum += Math.abs(lum - currentRow[x - 1]); edgeCount += 1; }
                if (y) { edgeSum += Math.abs(lum - previousRow[x]); edgeCount += 1; }
                var qr = Math.min(7, r >> 5), qg = Math.min(7, g >> 5), qb = Math.min(7, b >> 5);
                var key = qr + ':' + qg + ':' + qb;
                if (!bins[key]) bins[key] = { count: 0, sum: [0, 0, 0] };
                bins[key].count += 1;
                bins[key].sum[0] += r; bins[key].sum[1] += g; bins[key].sum[2] += b;
            }
            var swap = previousRow; previousRow = currentRow; currentRow = swap;
        }
        if (!count) return { palette: [], features: {}, summary: 'paint-aware suggestions ready', archetypes: [] };
        var rows = Object.keys(bins).map(function (key) {
            var bin = bins[key];
            return {
                count: bin.count,
                color: bin.sum.map(function (value) { return Math.round(value / bin.count); })
            };
        }).sort(function (a, b) { return b.count - a.count; });
        var palette = [];
        rows.some(function (row) {
            if (row.count / count < 0.004) return false;
            if (palette.some(function (item) { return distance(item.color, row.color) < 48; })) return false;
            var name = colorName(row.color);
            // A novice-facing palette must not offer two chips with the same
            // label. Keep the stronger cluster and spend the slot on another
            // recognizable paint color instead.
            if (palette.some(function (item) { return item.name === name; })) return false;
            palette.push({ color: row.color, hex: hex(row.color), name: name, coverage: Math.round(row.count * 1000 / count) / 10 });
            return palette.length >= 6;
        });
        var luma = lumSum / count;
        var contrast = Math.sqrt(Math.max(0, lumSq / count - luma * luma));
        var saturation = satSum / count;
        var detail = edgeCount ? edgeSum / edgeCount : 0;
        var descriptors = [];
        if (saturation > 0.48) descriptors.push('vivid');
        else if (saturation < 0.16) descriptors.push('neutral');
        else descriptors.push('color-rich');
        if (contrast > 0.27) descriptors.push('high-contrast');
        else if (contrast < 0.14) descriptors.push('soft-toned');
        if (luma < 0.32) descriptors.push('dark');
        else if (luma > 0.68) descriptors.push('bright');
        if (detail > 0.115) descriptors.push('detail-rich');
        var archetypes = ['metal', 'soft'];
        if (saturation > 0.34) archetypes.unshift('candy', 'holo', 'flake');
        if (luma < 0.42) archetypes.unshift('dark');
        if (contrast > 0.2 || detail > 0.09) archetypes.unshift('texture');
        return {
            palette: palette,
            features: { luma: luma, contrast: contrast, saturation: saturation, detail: detail },
            summary: descriptors.join(' + '),
            archetypes: archetypes.filter(function (item, index, list) { return list.indexOf(item) === index; })
        };
    }

    function materialFamily(text) {
        text = String(text || '').toLowerCase();
        if (/holo|prism|prizm|iridescent|chameleon|color ?shift|colorshoxx|spectral|flip/.test(text)) return 'shift';
        if (/carbon|weave|twill|forged|mesh|texture|mosaic/.test(text)) return 'texture';
        if (/chrome|metal|titanium|steel|aluminum|anodized|brushed|gold|silver/.test(text)) return 'metal';
        if (/candy|pearl|wet|glass|clearcoat/.test(text)) return 'candy';
        if (/matte|satin|silk|suede|frozen|factory|soft/.test(text)) return 'soft';
        if (/flake|sparkle|glitter|diamond/.test(text)) return 'flake';
        if (/wild|fracture|shokk|paradigm|neon|inferno|rainbow|toxic|venom/.test(text)) return 'wild';
        if (/stone|concrete|rust|hammered|wood|leather/.test(text)) return 'organic';
        return '';
    }

    function describeLook(look) {
        var text = [look && look.id, look && look.name, look && look.category, look && look.description]
            .concat((look && look.tags) || []).join(' ').toLowerCase();
        var labels = {
            shift: 'SHIFT · COLOR FLIP',
            texture: 'TEXTURE · WEAVE',
            metal: 'METAL · CHROME',
            candy: 'CANDY · WET',
            soft: 'SOFT · SATIN',
            flake: 'FLAKE · SPARKLE',
            wild: 'WILD · HIGH IMPACT',
            organic: 'ORGANIC · WEATHERED'
        };
        return labels[materialFamily(text)] || (look && look.kind === 'catalog' ? 'PAINT MATERIAL' : 'SPEC LOOK');
    }

    // [2026-08-09 S7] MEASURED: the shelf's picks really do follow the paint -
    // three different paints shared only 3 of 21 distinct picks (14%), and the
    // colour-led ones are apt (a white template drew Brushed Titanium and
    // Gunmetal Satin; a blue/white one drew Candy Cobalt and Arctic Ice). What
    // it never did was SAY so, which makes a good shortlist look like a random
    // one. The scoring loop below already knows which colour and which
    // archetype earned each boost; RECOMMEND_REASON keeps the winner instead of
    // discarding it, and the card prints it.
    var ARCHETYPE_REASON = {
        candy: 'suits a candy paint',
        holo: 'suits a color-shift paint',
        flake: 'suits a flake paint',
        metal: 'suits a metallic paint',
        dark: 'suits a dark paint',
        texture: 'suits a textured paint',
        soft: 'suits a soft, matte paint'
    };
    function rankLooks(looks, profile, limit) {
        profile = profile || { archetypes: [] };
        var archetypes = profile.archetypes || [];
        var palette = profile.palette || [];
        var chromatic = palette.filter(function (item) {
            return ['BLACK', 'CHARCOAL', 'GRAY', 'SILVER', 'WHITE'].indexOf(item.name) === -1;
        }).slice(0, 2);
        var neutral = palette.filter(function (item) {
            return ['BLACK', 'CHARCOAL', 'GRAY', 'SILVER', 'WHITE'].indexOf(item.name) !== -1;
        })[0];
        var scored = (looks || []).map(function (look, index) {
            var text = [look.id, look.name, look.category, look.description].concat(look.tags || []).join(' ').toLowerCase();
            var score = look.kind === 'mode' && look.id === 'zoned' ? 10000 : 0;
            // reset first: a look object survives a paint change, and a stale
            // "matches your RED" on a blue car is worse than saying nothing
            look.recReason = '';
            var bestArch = 0, bestColor = 0;
            archetypes.forEach(function (archetype, rank) {
                (ARCHETYPE_TERMS[archetype] || []).forEach(function (term) {
                    var boost = Math.max(5, 34 - rank * 4);
                    // Black template gutters must not make every vivid livery's
                    // shortlist read like an obsidian collection.
                    if (archetype === 'dark' && chromatic.length) boost *= 0.48;
                    if (text.indexOf(term) !== -1) {
                        score += boost;
                        if (boost > bestArch && ARCHETYPE_REASON[archetype]) {
                            bestArch = boost;
                            look.recReason = ARCHETYPE_REASON[archetype];
                        }
                    }
                });
            });
            chromatic.forEach(function (hint, rank) {
                (COLOR_TERMS[hint.name] || []).forEach(function (term) {
                    if (text.indexOf(term) !== -1) {
                        var cb = Math.max(18, 44 - rank * 8);
                        score += cb;
                        // a colour hit is the most convincing reason there is,
                        // so it outranks any archetype line
                        if (cb >= bestColor) {
                            bestColor = cb;
                            look.recReason = 'matches your ' + String(hint.name).toLowerCase();
                        }
                    }
                });
            });
            if (neutral) (COLOR_TERMS[neutral.name] || []).forEach(function (term) {
                if (text.indexOf(term) !== -1) score += 6;
            });
            // The three signatures are reliable demonstrations, not just more
            // catalog rows. Pin them ahead of the personalized exploration set.
            if (look.kind === 'mode') {
                score += look.id === 'fracture' ? 900 : (look.id === 'candy_depth' ? 850 : 500);
                // the three pinned signatures are demonstrations, not paint
                // matches - say that rather than implying the paint chose them
                look.recReason = 'signature look';   // [S26] shortened: the old copy lost 66px at 1100px
            }
            if (/macro|large|oversized/.test(text)) score -= 18;
            return { look: look, score: score, index: index, text: text };
        }).sort(function (a, b) { return b.score - a.score || a.index - b.index; });
        var result = [], categories = Object.create(null), families = Object.create(null), identities = Object.create(null), wanted = Math.max(1, Number(limit) || 12);
        scored.forEach(function (row) {
            if (result.length >= wanted || row.score <= 0) return;
            var identity = row.look.kind === 'catalog' ? ('catalog:' + row.look.id) : (row.look.kind + ':' + row.look.id);
            if (identities[identity]) return;
            var category = String(row.look.category || row.look.kind || 'look');
            if ((categories[category] || 0) >= 3 && row.look.id !== 'zoned') return;
            var family = materialFamily(row.text);
            if (family && (families[family] || 0) >= 2 && row.look.kind !== 'mode') return;
            result.push(row.look);
            identities[identity] = true;
            categories[category] = (categories[category] || 0) + 1;
            if (family) families[family] = (families[family] || 0) + 1;
        });
        // Relevance still wins when a very narrow catalog cannot fill the full
        // shortlist under diversity caps. This second pass fills only the open
        // slots and never duplicates a card already chosen.
        if (result.length < wanted) scored.forEach(function (row) {
            if (result.length >= wanted || row.score <= 0 || result.indexOf(row.look) !== -1) return;
            var identity = row.look.kind === 'catalog' ? ('catalog:' + row.look.id) : (row.look.kind + ':' + row.look.id);
            if (identities[identity]) return;
            result.push(row.look);
            identities[identity] = true;
        });
        return result;
    }

    function withinOneEdit(a, b) {
        if (a === b) return true;
        if (!a || !b || Math.abs(a.length - b.length) > 1) return false;
        var i = 0, j = 0, edits = 0;
        while (i < a.length && j < b.length) {
            if (a.charAt(i) === b.charAt(j)) { i++; j++; continue; }
            if (++edits > 1) return false;
            if (a.length > b.length) i++;
            else if (b.length > a.length) j++;
            else { i++; j++; }
        }
        return edits + ((i < a.length || j < b.length) ? 1 : 0) <= 1;
    }

    function normalizeSearchQuery(query) {
        var q = String(query || '').trim().toLowerCase();
        // Translate the phrases people actually type into positive material
        // intent. "Not too shiny" should find satin, not strand them at zero.
        q = q.replace(/\b(?:not\s+too|less)\s+(?:shiny|shine|glossy|gloss|mirror(?:ed)?)\b/g, ' satin ');
        q = q.replace(/\b(?:no|without)\s+(?:shine|gloss|glossy)\b/g, ' matte ');
        q = q.replace(/\b(?:not|no)\s+(?:matte|flat|dull)\b/g, ' shiny ');
        q = q.replace(/\b(?:not\s+too|less)\s+(?:wild|crazy|loud|dramatic)\b/g, ' subtle ');
        q = q.replace(/\b(?:no|without)\s+(?:sparkle|sparkles|glitter|flake|flakes)\b/g, ' clean ');
        return q.replace(/\s+/g, ' ').trim();
    }

    function scoreLookSearch(look, query, relaxed) {
        var q = normalizeSearchQuery(query);
        if (!q) return 0;
        var name = String(look && look.name || '').toLowerCase();
        var id = String(look && look.id || '').toLowerCase();
        var category = String(look && look.category || '').toLowerCase();
        var description = String(look && look.description || '').toLowerCase();
        var tags = ((look && look.tags) || []).join(' ').toLowerCase();
        var text = [name, id, category, description, tags].join(' ');
        var words = text.split(/[^a-z0-9]+/).filter(Boolean);
        var rawTokens = q.split(/[^a-z0-9]+/).filter(Boolean);
        var tokens = rawTokens.filter(function (token) { return !SEARCH_FILLER[token]; });
        if (!tokens.length) tokens = rawTokens;
        if (!tokens.length) return -1;

        var score = name === q ? 1200 : (id === q ? 1100 : 0);
        if (name.indexOf(q) === 0) score += 700;
        else if (name.indexOf(q) !== -1) score += 560;
        else if (category.indexOf(q) !== -1) score += 360;
        else if (text.indexOf(q) !== -1) score += 260;

        var matchedCount = 0;
        var matchedNonColor = 0;
        var nonColorCount = 0;
        tokens.forEach(function (token) {
            // Some words legitimately belong to more than one material intent:
            // chrome is both shiny and metallic, satin is both soft and subtle.
            // Taking only the first matching group quietly hid valid looks. Merge
            // every matching group so conversational search behaves like a human
            // request instead of an exact taxonomy lookup.
            var intents = SEARCH_INTENTS.filter(function (terms) { return terms.indexOf(token) !== -1; });
            var candidates = intents.length ? intents.reduce(function (all, terms) {
                terms.forEach(function (term) { if (all.indexOf(term) === -1) all.push(term); });
                return all;
            }, []) : [token];
            // Match intent words as words, not accidental substrings. Without
            // this, "red" matched "colored" and "rough" matched a description
            // saying "low roughness"—the opposite of what the person asked for.
            var direct = words.indexOf(token) !== -1;
            var fuzzy = !direct && token.length >= 5 && words.some(function (word) {
                return word.length >= 5 && withinOneEdit(token, word);
            });
            var synonym = !direct && !fuzzy && candidates.some(function (term) { return words.indexOf(term) !== -1; });
            var colorToken = !!COLOR_SEARCH_WORDS[token];
            if (!colorToken) nonColorCount++;
            if (!direct && !fuzzy && !synonym) return;
            matchedCount++;
            if (!colorToken) matchedNonColor++;
            if (name.indexOf(token) !== -1) score += 130;
            else if (category.indexOf(token) !== -1) score += 95;
            else if (direct) score += 70;
            else if (fuzzy) score += 48;
            else score += 34;
        });
        if (matchedCount === tokens.length) return score;
        // If the exact intersection does not exist, Easy Mode may ask for a
        // closest-match shelf. Keep the material/action word mandatory and
        // treat a color adjective as a preference, so "purple carbon" offers
        // carbon instead of a dead end while random gibberish still returns 0.
        if (!relaxed || !matchedCount || (nonColorCount && !matchedNonColor)) return -1;
        return score - ((tokens.length - matchedCount) * 90);
    }

    function matchesLookSearch(look, query) {
        return scoreLookSearch(look, query) >= 0;
    }

    function describeMaterialResponse(rawMeans, deviations) {
        rawMeans = Array.isArray(rawMeans) ? rawMeans : [0, 0.5, 0.5];
        deviations = Array.isArray(deviations) ? deviations : [0, 0, 0];
        var metallic = clamp(Number(rawMeans[0]) || 0, 0, 1);
        var roughness = clamp(Number(rawMeans[1]) || 0, 0, 1);
        // iRacing's blue spec channel is inverse clearcoat strength: 16 is
        // maximum coat and 255 is effectively none. Easy Mode must speak in
        // human strength, never expose the inverted storage convention.
        var coat = 1 - clamp(Number(rawMeans[2]) || 0, 0, 1);
        var responseMeans = [metallic, roughness, coat];
        var neutral = [0.41, 0.43, 0.45];
        var distance = responseMeans.reduce(function (sum, value, index) {
            return sum + Math.abs(value - neutral[index]);
        }, 0) / 3;
        var variation = deviations.reduce(function (sum, value) {
            return sum + Math.max(0, Number(value) || 0);
        }, 0) / 3;
        var score = distance * 0.9 + variation * 1.4;
        var impact = score >= 0.38 ? 'DRAMATIC' : (score >= 0.25 ? 'BOLD' : (score >= 0.13 ? 'CLEAR' : 'SUBTLE'));
        var metalWords = metallic > 0.58 ? 'strong metal accents' : (metallic > 0.36 ? 'controlled metallic depth' : 'mostly painted surfaces');
        var glossWords = roughness < 0.34 ? 'sharp gloss' : (roughness < 0.56 ? 'mixed satin and gloss' : 'soft satin grip');
        var coatWords = coat > 0.58 ? 'deep clearcoat' : (coat > 0.34 ? 'balanced clearcoat' : 'restrained clearcoat');
        return {
            impact: impact,
            score: score,
            metrics: { metal: metallic, gloss: 1 - roughness, coat: coat },
            // The nearby MATERIAL IMPACT buttons are relative controls. Avoid
            // calling an inherently dramatic finish "BOLD" after the user has
            // deliberately chosen SUBTLE; this line reports what the map reads.
            summary: 'MATERIAL READOUT · ' + metalWords + ' / ' + glossWords + ' / ' + coatWords
        };
    }

    return { analyzePixels: analyzePixels, chooseAutoColors: chooseAutoColors, rankLooks: rankLooks, matchesLookSearch: matchesLookSearch, scoreLookSearch: scoreLookSearch, normalizeSearchQuery: normalizeSearchQuery, colorName: colorName, describeLook: describeLook, describeMaterialResponse: describeMaterialResponse, stableSeed: stableSeed };
});
