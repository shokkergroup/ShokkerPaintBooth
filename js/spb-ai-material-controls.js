(function (root, factory) {
    'use strict';
    var api = factory();
    if (typeof module === 'object' && module.exports) module.exports = api;
    if (root) root.SpbMaterialControls = api;
}(typeof window !== 'undefined' ? window : (typeof globalThis !== 'undefined' ? globalThis : this), function () {
    'use strict';

    var HOWTO = /\?|\b(how|what|why|explain|difference|define|can you tell me|what is|what does)\b/i;
    var VERB = /\b(lower|reduce|decrease|raise|increase)\b/i;
    var CHANNEL = /^(?:clear\s*coat|clearcoat|roughness(?:\s+channel)?|metalness|metallic\s+channel|metal\s+channel)\b/i;
    var PARTS = {
        'roof': 'roof', 'hood': 'hood', 'bonnet': 'hood',
        'left side': 'left side', 'left side panel': 'left side',
        'right side': 'right side', 'right side panel': 'right side',
        'bumper': 'bumper', 'front bumper': 'front bumper', 'rear bumper': 'rear bumper',
        'trunk': 'trunk', 'boot': 'trunk', 'bed': 'bed', 'truck bed': 'bed', 'spoiler': 'spoiler'
    };
    var CHANNEL_AMBIGUITY = /\b(material\s+channel|spec(?:ular)?\s+channel|shine)\b/i;

    function result(kind, fields) { var out = { kind: kind }; Object.keys(fields || {}).forEach(function (k) { out[k] = fields[k]; }); return out; }
    function cleanText(s) { return String(s == null ? '' : s).replace(/[\u2018\u2019]/g, "'").replace(/[\u201c\u201d]/g, '"').trim(); }
    function clarify(reason, question) { return result('clarify', { reason: reason, question: question || 'Which exact part and material channel should I adjust? I can change only metalness, roughness, or clearcoat.' }); }
    function diagnosticPrefix(s) {
        var observation = String(s || '').replace(/^diagnostic\s*:\s*/i, '').trim();
        // Consume a descriptive observation in full; a paint instruction cannot
        // be discarded just because the same prefix also mentions shiny paint.
        return /^(?:(?:everything|it|this|that|(?:the|my)\s+(?:car|truck|vehicle|paint|body|roof|hood|bonnet|left side|right side|finish|surface|clearcoat|clear coat|roughness|metalness))\s+)?(?:(?:is|looks|seems|feels|appears)\s+)?(?:(?:too|very|a bit|slightly|much too)\s+)?(?:shiny|glossy|reflective|bright|dull|rough|smooth|metallic)[.!]?$/i.test(observation);
    }
    function splitCommand(raw) {
        var semi = raw.indexOf(';'), prefix = '';
        if (semi >= 0) {
            if (raw.indexOf(';', semi + 1) >= 0) return null;
            prefix = raw.slice(0, semi).trim();
            if (!diagnosticPrefix(prefix)) return null;
            return raw.slice(semi + 1).trim();
        }
        var lead = /^(?:please\s+)?(?:lower|reduce|decrease|raise|increase)\b/i.exec(raw);
        if (lead) return raw;
        var comma = /,\s*(?=(?:please\s+)?(?:lower|reduce|decrease|raise|increase)\b)/i.exec(raw);
        if (comma && diagnosticPrefix(raw.slice(0, comma.index))) return raw.slice(comma.index + comma[0].length).trim();
        return null;
    }
    function parseChannel(s) {
        var m = CHANNEL.exec(s); if (!m) return null;
        var w = m[0].toLowerCase().replace(/\s+/g, ' '), key = /clear\s*coat/.test(w) ? 'clearcoat' : (/roughness/.test(w) ? 'roughness' : 'metalness');
        return { key: key, rest: s.slice(m[0].length).trim() };
    }
    function parseAmount(s) {
        if (!s) return { ok: true, value: null };
        var m = /^by\s+([+-]?\d+)\s+points?$/i.exec(s);
        if (!m) {
            if (/\bto\s+[+-]?\d+(?:\.\d+)?\s*%/i.test(s)) return { ok: false, reason: 'absolute-percent-is-not-a-relative-shift', question: 'Should I raise or lower the channel by how many points? A percent target is not the same as a spec-shift offset.' };
            if (/\bto\s+[+-]?\d+(?:\.\d+)?\s+points?\b/i.test(s)) return { ok: false, reason: 'absolute-points-is-not-a-relative-shift' };
            if (/\bby\s+[+-]?\d+(?:\.\d+)?\s*(?:%|percent)(?:\s|$)/i.test(s)) return { ok: false, reason: 'relative-amount-needs-points', question: 'Please give a relative amount in points, such as “by 20 points”.' };
            if (/\bby\s+[+-]?\d+(?:\.\d+)?\b/i.test(s) || /[+-]?\d+(?:\.\d+)?\s*(?:points?|percent|%)/i.test(s)) return { ok: false, reason: 'malformed-or-unconsumed-amount' };
            return { ok: false, reason: 'unsupported-or-extra-words' };
        }
        var n = Number(m[1]); if (n < 0) return { ok: false, reason: 'negative-relative-amount' };
        return { ok: true, value: n };
    }
    function parsePart(s) {
        var q = String(s || '').replace(/[.!]+\s*$/, '').trim().toLowerCase().replace(/\s+/g, ' ');
        if (/\s+only$/.test(q)) q = q.replace(/\s+only$/, '').trim();
        q = q.replace(/^the\s+/, '');
        return Object.prototype.hasOwnProperty.call(PARTS, q) ? PARTS[q] : null;
    }

    function parseRequest(text) {
        var raw = cleanText(text);
        if (!raw) return clarify('empty');
        if (HOWTO.test(raw)) return result('delegate', { reason: 'question-or-howto' });
        if (/\b(don't|do not|never|not|cannot|can't|shouldn't|should not)\b/i.test(raw)) return result('delegate', { reason: 'negative-or-prohibition' });
        if (/^set\b/i.test(raw) && /\b(clear\s*coat|clearcoat|roughness|metalness|metallic\s+channel|metal\s+channel)\b/i.test(raw) && /\bto\s+[+-]?\d+(?:\.\d+)?\s*(?:points?|%|percent)/i.test(raw)) return clarify('absolute-level-is-not-a-relative-shift');

        var clause = splitCommand(raw);
        if (clause == null) {
            if (!VERB.test(raw)) return result('delegate', { reason: 'no-explicit-channel-adjustment' });
            return clarify('mixed-or-unsupported-prefix');
        }
        clause = clause.replace(/[.!]+\s*$/, '').trim();
        var action = /^(?:please\s+)?(lower|reduce|decrease|raise|increase)\s+(?:the\s+)?(.+)$/i.exec(clause);
        if (!action) return clarify('unsupported-command-shape');
        var verb = action[1].toLowerCase(), channel = parseChannel(action[2]);
        if (!channel) {
            if (CHANNEL_AMBIGUITY.test(action[2])) return clarify('ambiguous-channel', 'Which material channel: metalness, roughness, or clearcoat?');
            return clarify('missing-or-unsupported-channel', 'Which channel should change: metalness, roughness, or clearcoat?');
        }

        var body = channel.rest, on = /\bon\s+(?:the\s+)?(.+)$/i.exec(body);
        if (!on) return clarify('missing-exact-part', 'Which exact named part should I adjust?');
        var beforePart = body.slice(0, on.index).trim(), partSource = on[1].trim(), amountText = '';
        if (beforePart) {
            var preAmount = parseAmount(beforePart);
            if (!preAmount.ok) return clarify(preAmount.reason, preAmount.question);
            amountText = beforePart;
        }
        // A quantity may follow the part, but it must be the last exact clause.
        var postAmount = /\s+(by\s+[+-]?\d+(?:\.\d+)?\s+(?:points?|percent)|by\s+[+-]?\d+(?:\.\d+)?\s*%|to\s+[+-]?\d+(?:\.\d+)?\s*(?:points?|percent|%))\s*$/i.exec(partSource);
        if (postAmount) {
            if (amountText) return clarify('duplicate-amount');
            amountText = postAmount[1].trim(); partSource = partSource.slice(0, postAmount.index).trim();
            if (/\bonly\s*$/i.test(partSource)) return clarify('unconsumed-words-after-amount');
        }
        if (/\bonly\s+by\b/i.test(partSource) || /\bby\s+[+-]?\d+(?:\.\d+)?\s+(?:points?|percent)\s+only\s*$/i.test(partSource)) return clarify('unconsumed-words-after-amount');
        var amount = parseAmount(amountText);
        if (!amount.ok) return clarify(amount.reason, amount.question);
        // Any number left in the target is malformed quantity syntax, never a part-name suffix.
        if (/[+-]?\d/.test(partSource)) return clarify('unconsumed-number-in-target');
        var part = parsePart(partSource);
        if (!part) return clarify('unsupported-or-ambiguous-part', 'Which exact part: roof, hood, left/right side, bumper, trunk/bed, or spoiler?');

        var sign = (verb === 'raise' || verb === 'increase') ? 1 : -1;
        return result('edit', { channel: channel.key, part: part, delta: sign * (amount.value == null ? 20 : amount.value), amountSpecified: amount.value != null, amountUnit: 'points', verb: verb });
    }

    function clamp(v) { return Math.max(-127, Math.min(127, Math.round(v))); }
    function buildEdit(zone, parsed) {
        if (!parsed || parsed.kind !== 'edit') return result('invalid', { reason: 'parsed-edit-required' });
        if (!zone || zone.id == null || String(zone.id).trim() === '') return result('invalid', { reason: 'real-zone-id-required' });
        var keys = { metalness: 'metal', roughness: 'rough', clearcoat: 'clearcoat' }, slot = keys[parsed.channel];
        if (!slot || !isFinite(Number(parsed.delta))) return result('invalid', { reason: 'unsupported-channel-or-delta' });
        var current = { metal: clamp(Number(zone.specShiftR) || 0), rough: clamp(Number(zone.specShiftG) || 0), clearcoat: clamp(Number(zone.specShiftB) || 0) };
        var next = clamp(current[slot] + Number(parsed.delta));
        if (next === current[slot]) return result('noop', { reason: Number(parsed.delta) === 0 ? 'zero-adjustment' : 'channel-already-at-limit' });
        current[slot] = next;
        var edit = { zone_id: String(zone.id), spec_shift: current }; if (zone.name != null) edit.expect_name = String(zone.name);
        return result('edit', edit);
    }

    return { parse: parseRequest, buildEdit: buildEdit, contract: 'spb-ai-material-controls/1' };
}));
