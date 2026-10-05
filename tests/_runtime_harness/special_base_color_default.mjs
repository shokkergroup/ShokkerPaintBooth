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
    // [2026-08-15] _spbColorLocked was MISSING here, so this whole harness died with
    // "ReferenceError: _spbColorLocked is not defined" — _spbApplyPickedMonolithicToZone
    // started calling it when COLOR LOCK landed (2026-06-11) and nobody updated this list.
    // The test has been red (i.e. guarding nothing) ever since. It needs no sandbox stub:
    // the fn is `typeof window !== 'undefined' && !!window._SPB_COLOR_LOCK`, and with no
    // window in node it returns false — which is exactly the "lock OFF" case these
    // expectations are written against.
    '_spbColorLocked',
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

// Per-zone Lock Base Color ON: picking even a special-like base must leave the color alone.
const locked = { base: null, finish: null, pattern: 'none', baseColorMode: 'source', baseColor: null, baseColorSource: null, _autoBaseColorFill: false, lockBaseColor: true };
_spbApplyPickedBaseToZone(locked, 'cx_inferno');

JSON.stringify({ regular, specialBase, switchedBack, mono, locked }, null, 2);
`;

const out = JSON.parse(eval(sandbox));
let failures = 0;
function expect(label, actual, expected) {
    if (actual !== expected) {
        console.error(`${label}: expected ${expected}, got ${actual}`);
        failures++;
    }
}

// [2026-08-15] EXPECTATIONS CORRECTED. These four asserted that an ordinary base
// (f_metallic, Foundation) stays on "Use source paint". That was true when this harness
// was written, but TWO later owner decisions changed it deliberately and this file was
// never updated — it could not fail loudly because it was already dead on the
// _spbColorLocked ReferenceError (see the `needed` list above):
//   * 2026-06-30 "picking ANY base adopts that base's own color"
//   * 2026-07-08 adopt via the special-source path, not a flat solid hex, so multi-tone
//     bases (Ghost Graphic) keep their CHARACTER
// _spbApplyPickedBaseToZone:14404 now routes every unlocked base pick through
// _spbDefaultBaseColorToFinish. So 'special' + mono:<id> IS the correct shipped result.
// The opt-out is COLOR LOCK / per-zone lockBaseColor, guarded by the `locked` case below.
expect('regular.base', out.regular.base, 'f_metallic');
expect('regular.baseColorMode', out.regular.baseColorMode, 'special');
expect('regular.baseColorSource', out.regular.baseColorSource, 'mono:f_metallic');
expect('regular.baseColor', out.regular.baseColor, '#7a7a7a');
expect('regular.auto', out.regular._autoBaseColorFill, true);

expect('specialBase.base', out.specialBase.base, 'cx_inferno');
expect('specialBase.finish', out.specialBase.finish, null);
expect('specialBase.baseColorMode', out.specialBase.baseColorMode, 'special');
expect('specialBase.baseColorSource', out.specialBase.baseColorSource, 'mono:cx_inferno');
expect('specialBase.baseColor', out.specialBase.baseColor, '#991122');
expect('specialBase.auto', out.specialBase._autoBaseColorFill, true);

// Same correction as `regular`: re-picking an ordinary base now adopts THAT base's color
// rather than unwinding to source.
expect('switchedBack.base', out.switchedBack.base, 'f_metallic');
expect('switchedBack.baseColorMode', out.switchedBack.baseColorMode, 'special');
expect('switchedBack.baseColorSource', out.switchedBack.baseColorSource, 'mono:f_metallic');
expect('switchedBack.auto', out.switchedBack._autoBaseColorFill, true);

// The opt-out the owner relies on: with the per-zone lock set, picking a base must NOT
// touch the painter's color setup at all. Needs no `window` stub — lockBaseColor is
// checked alongside _spbColorLocked() in the same early return.
expect('locked.base', out.locked.base, 'cx_inferno');
expect('locked.baseColorMode', out.locked.baseColorMode, 'source');
expect('locked.baseColorSource', out.locked.baseColorSource, null);
expect('locked.auto', out.locked._autoBaseColorFill, false);

expect('mono.finish', out.mono.finish, 'hex_mandala');
expect('mono.base', out.mono.base, null);
expect('mono.baseColorMode', out.mono.baseColorMode, 'special');
expect('mono.baseColorSource', out.mono.baseColorSource, 'mono:hex_mandala');
expect('mono.baseColor', out.mono.baseColor, '#123abc');
expect('mono.auto', out.mono._autoBaseColorFill, true);

if (failures) process.exit(1);
console.log('OK - specials default to From special, ordinary bases stay Use source paint.');
