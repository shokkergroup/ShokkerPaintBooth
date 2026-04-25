// Regression harness: Specials picked as a zone base must default Base Color
// to "From special" with the same finish ID. Ordinary bases keep source paint.

import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const REPO = join(__dirname, '..', '..');
const stateSrc = readFileSync(join(REPO, 'paint-booth-2-state-zones.js'), 'utf8');

function extractFn(src, name) {
    const idx = src.indexOf('function ' + name + '(');
    if (idx < 0) return null;
    let depth = 0, pos = idx;
    let inBody = false;
    while (pos < src.length) {
        const c = src[pos];
        if (c === '{') { depth++; inBody = true; }
        else if (c === '}') {
            depth--;
            if (inBody && depth === 0) return src.slice(idx, pos + 1);
        }
        pos++;
    }
    return null;
}

const needed = [
    '_spbGetBaseGroup',
    '_spbNormalizeFinishId',
    '_spbIsShippingSpecialLikeFinishId',
    '_spbFindFinishDisplay',
    '_spbExtractSwatchHex',
    '_spbDefaultBaseColorToFinish',
    '_spbShouldAutoFillBaseColor',
    '_spbApplyPickedMonolithicToZone',
    '_spbApplyPickedBaseToZone',
];
const fns = needed.map(name => extractFn(stateSrc, name));
if (fns.some(fn => !fn)) {
    console.error('Failed to extract one or more base-color default helpers');
    process.exit(1);
}

const sandbox = `
const BASES = [
    { id: 'f_metallic', name: 'Metallic Foundation', swatch: '#7a7a7a' },
    { id: 'cx_inferno', name: 'COLORSHOXX Inferno Flip', swatch: '#991122' },
];
const MONOLITHICS = [
    { id: 'hex_mandala', name: 'Hex Mandala', swatch: 'linear-gradient(135deg, #123abc 0%, #ff9900 100%)' },
];
const BASE_GROUPS = { Foundation: ['f_metallic'] };
const SPECIAL_GROUPS = {
    'COLORSHOXX': ['cx_inferno'],
    'Ornamental': ['hex_mandala'],
};
const _SPB_NO_AUTO_COLOR_GROUPS = new Set(['Foundation']);
let _SPB_BASE_GROUP_LOOKUP = null;
${fns.join('\n')}

const regular = { base: null, finish: null, pattern: 'none', baseColorMode: 'source', baseColor: null, baseColorSource: null, _autoBaseColorFill: false };
_spbApplyPickedBaseToZone(regular, 'f_metallic');

const specialBase = { base: null, finish: null, pattern: 'none', baseColorMode: 'source', baseColor: null, baseColorSource: null, _autoBaseColorFill: false };
_spbApplyPickedBaseToZone(specialBase, 'cx_inferno');

const switchedBack = { base: null, finish: null, pattern: 'none', baseColorMode: 'special', baseColor: '#991122', baseColorSource: 'mono:cx_inferno', _autoBaseColorFill: true };
_spbApplyPickedBaseToZone(switchedBack, 'f_metallic');

const mono = { base: null, finish: null, pattern: 'none', baseColorMode: 'source', baseColor: null, baseColorSource: null, _autoBaseColorFill: false };
_spbApplyPickedMonolithicToZone(mono, 'hex_mandala');

JSON.stringify({ regular, specialBase, switchedBack, mono }, null, 2);
`;

const out = JSON.parse(eval(sandbox));
let failures = 0;
function expect(label, actual, expected) {
    if (actual !== expected) {
        console.error(`${label}: expected ${expected}, got ${actual}`);
        failures++;
    }
}

expect('regular.base', out.regular.base, 'f_metallic');
expect('regular.baseColorMode', out.regular.baseColorMode, 'source');
expect('regular.baseColorSource', out.regular.baseColorSource, null);
expect('regular.auto', out.regular._autoBaseColorFill, false);

expect('specialBase.base', out.specialBase.base, 'cx_inferno');
expect('specialBase.finish', out.specialBase.finish, null);
expect('specialBase.baseColorMode', out.specialBase.baseColorMode, 'special');
expect('specialBase.baseColorSource', out.specialBase.baseColorSource, 'mono:cx_inferno');
expect('specialBase.baseColor', out.specialBase.baseColor, '#991122');
expect('specialBase.auto', out.specialBase._autoBaseColorFill, true);

expect('switchedBack.base', out.switchedBack.base, 'f_metallic');
expect('switchedBack.baseColorMode', out.switchedBack.baseColorMode, 'source');
expect('switchedBack.baseColorSource', out.switchedBack.baseColorSource, null);
expect('switchedBack.auto', out.switchedBack._autoBaseColorFill, false);

expect('mono.finish', out.mono.finish, 'hex_mandala');
expect('mono.base', out.mono.base, null);
expect('mono.baseColorMode', out.mono.baseColorMode, 'special');
expect('mono.baseColorSource', out.mono.baseColorSource, 'mono:hex_mandala');
expect('mono.baseColor', out.mono.baseColor, '#123abc');
expect('mono.auto', out.mono._autoBaseColorFill, true);

if (failures) process.exit(1);
console.log('OK - specials default to From special, ordinary bases stay Use source paint.');
