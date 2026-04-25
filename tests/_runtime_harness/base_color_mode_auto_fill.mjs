// Pillman V8 probe + permanent harness.
//
// Painter-reported state-mutation bug (2026-04-22): picking a base was
// flipping zone.baseColorMode away from 'source' and injecting the
// base's swatch as a solid color, overpainting the painter's picked
// colors. Root cause (see Bockwinkel's note in paint-booth-2-state-zones.js
// at _spbGetBaseGroup): the inverse-lookup table build overwrote entries
// so a base that lives in multiple groups (e.g. f_metallic is in both
// 'Foundation' and 'Reference Foundations') ended up labelled with the
// LAST-iterated group. That label escaped the _SPB_NO_AUTO_COLOR_GROUPS
// gate and triggered auto-color.
//
// This harness loads the live JS, extracts the three functions and the
// no-auto-color set, and simulates picking every base in every
// no-auto-color group. The invariant is:
//
//   for any base in a group listed in _SPB_NO_AUTO_COLOR_GROUPS,
//   calling _spbApplyPickedBaseToZone(zone={baseColorMode:'source'}, baseId)
//   must leave zone.baseColorMode === 'source' and zone.baseColor === null.
//
// If this harness fails, the auto-fill gate has drifted.

import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const REPO = join(__dirname, '..', '..');

const dataSrc = readFileSync(join(REPO, 'paint-booth-0-finish-data.js'), 'utf8');
const stateSrc = readFileSync(join(REPO, 'paint-booth-2-state-zones.js'), 'utf8');

// Extract BASE_GROUPS object literal.
function extractObjectLiteral(src, name) {
    const rx = new RegExp('const\\s+' + name + '\\s*=\\s*\\{', 'g');
    const m = rx.exec(src);
    if (!m) return null;
    let depth = 1, pos = m.index + m[0].length;
    while (pos < src.length && depth > 0) {
        const c = src[pos];
        if (c === '{') depth++;
        else if (c === '}') depth--;
        pos++;
    }
    return '({' + src.slice(m.index + m[0].length, pos - 1) + '})';
}

function extractArrayLiteral(src, name) {
    const rx = new RegExp('const\\s+' + name + '\\s*=\\s*\\[', 'g');
    const m = rx.exec(src);
    if (!m) return null;
    let depth = 1, pos = m.index + m[0].length;
    while (pos < src.length && depth > 0) {
        const c = src[pos];
        if (c === '[') depth++;
        else if (c === ']') depth--;
        pos++;
    }
    return '(' + src.slice(m.index + m[0].length - 1, pos) + ')';
}

const BASE_GROUPS_LITERAL = extractObjectLiteral(dataSrc, 'BASE_GROUPS');
const BASES_LITERAL = extractArrayLiteral(dataSrc, 'BASES');
if (!BASE_GROUPS_LITERAL || !BASES_LITERAL) {
    console.error('Failed to extract BASE_GROUPS/BASES from paint-booth-0-finish-data.js');
    process.exit(1);
}

// Extract the no-auto-color set literal.
const setMatch = /_SPB_NO_AUTO_COLOR_GROUPS\s*=\s*new Set\(\s*\[([\s\S]*?)\]\s*\)/.exec(stateSrc);
if (!setMatch) { console.error('Failed to extract _SPB_NO_AUTO_COLOR_GROUPS'); process.exit(1); }

// Extract the target helpers/functions.
function extractFn(src, name) {
    const idx = src.indexOf('function ' + name + '(');
    if (idx < 0) return null;
    let depth = 0, pos = idx;
    let inBody = false;
    while (pos < src.length) {
        const c = src[pos];
        if (c === '{') { depth++; inBody = true; }
        else if (c === '}') { depth--; if (inBody && depth === 0) return src.slice(idx, pos + 1); }
        pos++;
    }
    return null;
}
const fnGetBaseGroup = extractFn(stateSrc, '_spbGetBaseGroup');
const fnNormalizeFinishId = extractFn(stateSrc, '_spbNormalizeFinishId');
const fnIsShippingSpecialLikeFinishId = extractFn(stateSrc, '_spbIsShippingSpecialLikeFinishId');
const fnShould = extractFn(stateSrc, '_spbShouldAutoFillBaseColor');
const fnApply = extractFn(stateSrc, '_spbApplyPickedBaseToZone');
if (!fnGetBaseGroup || !fnNormalizeFinishId || !fnIsShippingSpecialLikeFinishId || !fnShould || !fnApply) {
    console.error('Failed to extract target functions');
    process.exit(1);
}

// Run in isolated scope.
const sandbox = `
const BASE_GROUPS = ${BASE_GROUPS_LITERAL};
const BASES = ${BASES_LITERAL};
const _SPB_NO_AUTO_COLOR_GROUPS = new Set([${setMatch[1]}]);
let _SPB_BASE_GROUP_LOOKUP = null;
${fnGetBaseGroup}
${fnNormalizeFinishId}
${fnIsShippingSpecialLikeFinishId}
${fnShould}
${fnApply}
const results = { foundation: [], byGroup: {} };
for (const group of _SPB_NO_AUTO_COLOR_GROUPS) {
    const ids = BASE_GROUPS[group] || [];
    if (!ids.length) continue;
    const groupResults = [];
    for (const bid of ids) {
        const zone = { base: null, baseColorMode: 'source', baseColor: null, _autoBaseColorFill: false };
        _spbApplyPickedBaseToZone(zone, bid);
        groupResults.push({
            id: bid,
            group_resolved: _spbGetBaseGroup(bid),
            mode_after: zone.baseColorMode,
            color_after: zone.baseColor,
            autoFilled: zone._autoBaseColorFill === true,
        });
    }
    results.byGroup[group] = groupResults;
}
JSON.stringify(results, null, 2);
`;

const out = eval(sandbox);
const parsed = JSON.parse(out);

let failures = 0;
let totalChecked = 0;
for (const [group, rows] of Object.entries(parsed.byGroup)) {
    for (const r of rows) {
        totalChecked++;
        if (r.mode_after !== 'source' || r.color_after !== null || r.autoFilled) {
            console.error(`FAIL: picking '${r.id}' (group='${group}', resolved='${r.group_resolved}') flipped mode to '${r.mode_after}' and baseColor to '${r.color_after}' (autoFilled=${r.autoFilled})`);
            failures++;
        }
    }
}

console.log(`Checked ${totalChecked} bases across ${Object.keys(parsed.byGroup).length} no-auto-color groups.`);
if (failures) {
    console.error(`${failures} invariant violations — auto-fill is leaking for some no-auto-color-group bases.`);
    process.exit(1);
}
console.log('OK — every base in a no-auto-color group keeps baseColorMode=\'source\' and baseColor=null after pick.');
