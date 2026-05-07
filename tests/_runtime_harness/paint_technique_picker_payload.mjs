// Regression harness for SPB-7.
//
// Paint Technique renderers already have source-level Python coverage. This
// harness pins the browser path that caused the painter-facing "does nothing"
// symptom: picking a Paint Technique base must not switch the zone to a solid
// swatch tint, and the render payload must carry base_color_mode='source'.

import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const REPO = join(__dirname, '..', '..');

const dataSrc = readFileSync(join(REPO, 'paint-booth-0-finish-data.js'), 'utf8');
const stateSrc = readFileSync(join(REPO, 'paint-booth-2-state-zones.js'), 'utf8');
const renderSrc = readFileSync(join(REPO, 'paint-booth-5-api-render.js'), 'utf8');

const EXPECTED_PAINT_TECHNIQUES = [
    'paint_drip_gravity',
    'paint_splatter_loose',
    'paint_sponge_stipple',
    'paint_roller_streak',
    'paint_spray_fade',
    'paint_brush_stroke',
];

function extractObjectLiteral(src, name) {
    const rx = new RegExp('const\\s+' + name + '\\s*=\\s*\\{', 'g');
    const m = rx.exec(src);
    if (!m) return null;
    let depth = 1;
    let pos = m.index + m[0].length;
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
    let depth = 1;
    let pos = m.index + m[0].length;
    while (pos < src.length && depth > 0) {
        const c = src[pos];
        if (c === '[') depth++;
        else if (c === ']') depth--;
        pos++;
    }
    return '(' + src.slice(m.index + m[0].length - 1, pos) + ')';
}

function extractFn(src, name) {
    const idx = src.indexOf('function ' + name + '(');
    if (idx < 0) return null;
    let depth = 0;
    let pos = idx;
    let inBody = false;
    while (pos < src.length) {
        const c = src[pos];
        if (c === '{') {
            depth++;
            inBody = true;
        } else if (c === '}') {
            depth--;
            if (inBody && depth === 0) return src.slice(idx, pos + 1);
        }
        pos++;
    }
    return null;
}

const BASE_GROUPS_LITERAL = extractObjectLiteral(dataSrc, 'BASE_GROUPS');
const BASES_LITERAL = extractArrayLiteral(dataSrc, 'BASES');
if (!BASE_GROUPS_LITERAL || !BASES_LITERAL) {
    console.error('Failed to extract BASE_GROUPS/BASES from paint-booth-0-finish-data.js');
    process.exit(1);
}

const stateFns = [
    '_spbNormalizeFinishId',
    '_spbIsShippingSpecialLikeFinishId',
    '_spbFindFinishDisplay',
    '_spbExtractSwatchHex',
    '_spbDefaultBaseColorToFinish',
    '_spbShouldAutoFillBaseColor',
    '_spbApplyPickedBaseToZone',
].map((name) => extractFn(stateSrc, name));

const renderFns = [
    '_zoneHasRenderableMaterial',
    '_applyBaseColorBranch',
    '_applyBaseColorMode',
].map((name) => extractFn(renderSrc, name));

if (stateFns.some((fn) => !fn) || renderFns.some((fn) => !fn)) {
    console.error('Failed to extract picker or payload helper functions');
    process.exit(1);
}

const sandbox = `
const BASE_GROUPS = ${BASE_GROUPS_LITERAL};
const BASES = ${BASES_LITERAL};
${stateFns.join('\n')}
${renderFns.join('\n')}

const ids = BASE_GROUPS['Paint Technique'] || [];
const rows = [];
for (const id of ids) {
    const zone = {
        name: 'Paint Technique probe',
        color: { color_rgb: [96, 96, 96], tolerance: 40 },
        colorMode: 'picker',
        base: null,
        finish: null,
        pattern: 'none',
        baseColorMode: 'source',
        baseColor: null,
        baseColorSource: null,
        baseColorStrength: 1,
        _autoBaseColorFill: false,
    };
    _spbApplyPickedBaseToZone(zone, id);
    const zoneObj = { name: zone.name, color: zone.color, intensity: '100', base: zone.base, pattern: zone.pattern };
    _applyBaseColorMode(zoneObj, zone);
    rows.push({
        id,
        zone_base: zone.base,
        zone_finish: zone.finish,
        zone_baseColorMode: zone.baseColorMode,
        zone_baseColor: zone.baseColor,
        zone_baseColorSource: zone.baseColorSource,
        zone_autoFilled: zone._autoBaseColorFill === true,
        payload_base_color_mode: zoneObj.base_color_mode,
        payload_has_base_color: Object.prototype.hasOwnProperty.call(zoneObj, 'base_color'),
        payload_has_base_color_source: Object.prototype.hasOwnProperty.call(zoneObj, 'base_color_source'),
    });
}
JSON.stringify({ ids, rows }, null, 2);
`;

const out = JSON.parse(eval(sandbox));
const failures = [];

if (JSON.stringify(out.ids) !== JSON.stringify(EXPECTED_PAINT_TECHNIQUES)) {
    failures.push(`Paint Technique picker group drifted: ${JSON.stringify(out.ids)}`);
}

for (const row of out.rows) {
    if (row.zone_base !== row.id) failures.push(`${row.id}: picker did not set zone.base`);
    if (row.zone_finish !== null) failures.push(`${row.id}: picker incorrectly set zone.finish=${row.zone_finish}`);
    if (row.zone_baseColorMode !== 'source') failures.push(`${row.id}: zone baseColorMode=${row.zone_baseColorMode}`);
    if (row.zone_baseColor !== null) failures.push(`${row.id}: zone baseColor=${row.zone_baseColor}`);
    if (row.zone_baseColorSource !== null) failures.push(`${row.id}: zone baseColorSource=${row.zone_baseColorSource}`);
    if (row.zone_autoFilled) failures.push(`${row.id}: auto-fill flag was set`);
    if (row.payload_base_color_mode !== 'source') failures.push(`${row.id}: payload base_color_mode=${row.payload_base_color_mode}`);
    if (row.payload_has_base_color) failures.push(`${row.id}: payload includes flat base_color`);
    if (row.payload_has_base_color_source) failures.push(`${row.id}: payload includes base_color_source`);
}

if (failures.length) {
    console.error(failures.join('\n'));
    process.exit(1);
}

console.log(JSON.stringify(out, null, 2));
