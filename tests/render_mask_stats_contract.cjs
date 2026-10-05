const fs = require('node:fs');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const stats = require('../js/canvas/zone/mask-stats.js');
const source = fs.readFileSync('paint-booth-5-api-render.js', 'utf8');
function load(text, helper) {
    const storage = { getItem() { return null; }, setItem() {}, removeItem() {} };
    const c = {
        Uint8Array, Uint8ClampedArray, console: { log() {}, warn() {}, error() {} },
        localStorage: storage, sessionStorage: storage,
        setTimeout() {}, setInterval() {}, clearTimeout() {}, clearInterval() {},
        addEventListener() {}, location: { protocol: 'http:', hostname: 'localhost' },
        document: { addEventListener() {}, getElementById(id) { return id === 'paintCanvas' ? {width: 32, height: 32} : null; }, querySelectorAll() { return []; } },
        SPBMaskStats: helper, BASES: [], PATTERNS: [], MONOLITHICS: [], SPEC_PATTERNS: [],
    };
    c.window = c;
    vm.createContext(c);
    vm.runInContext(text, c);
    c.encodeRegionMaskRLE = (mask, width, height) => {
        const runs = [];
        for (const value of mask) {
            if (runs.length && runs.at(-1)[0] === value) runs.at(-1)[1]++;
            else runs.push([value, 1]);
        }
        return { width, height, runs };
    };
    c.formatColorForServer = color => color;
    return c;
}
try {
    const before = load(source, null), after = load(source, stats);
    before._renderMaskHasPixels = mask => !!mask && mask.some(value => value > 0);
    before._zoneShouldRequestPriorityOverride = after._zoneShouldRequestPriorityOverride = () => true;
    let seed = 825;
    const random = n => { seed = (Math.imul(seed,1664525)+1013904223)>>>0; return seed%n; };
    for (let trial=0; trial<150; trial++) {
        const region = Uint8Array.from({length:1024}, () => random(20) === 0 ? [1,128,255][random(3)] : 0);
        const spatial = new Uint8Array(1024);
        if(trial%2) spatial[1023] = trial%3 ? 1 : 2;
        if(trial%5 === 0) region.fill(0);
        const zone = {name:'Test',base:'gloss',finish:null,pattern:'none',color:trial%3 ? null : [20,40,60],regionMask:region,spatialMask:spatial,useRegion:!!(trial%2),muted:trial%7===0,intensity:'100'};
        const expected = JSON.stringify(before.buildServerZonesForRender([zone]));
        const actual = JSON.stringify(after.buildServerZonesForRender([zone]));
        assert.equal(actual, expected, 'complete request payload parity');
    }
    const mask = new Uint8Array(1024); mask[1023]=128;
    stats.count(mask); mask.some=()=>{throw Error('Repeated callback scan');};
    const obj={}; after._encodeZoneApplyMasks(obj,{regionMask:mask,useRegion:true});
    assert.equal(obj.region_mask.runs.at(-1)[0],128);
    stats.invalidate(mask);mask.fill(0);
    assert.equal(after._renderMaskHasPixels(mask),false);
    for(const mask of [null,[],[-1,0],[0,0.25],new Int8Array([-1,0]),new Float32Array([0,0.25])]) {
        assert.equal(after._renderMaskHasPixels(mask),!!mask && mask.some(v=>v>0));
    }
    console.log('Render serializer:150 complete payloads identical; cached byte-mask reuse, mutation, soft values and non-byte fallbacks pass.');
} catch (error) {
    console.error(error.stack.split('\n').slice(0,7).join('\n'));
    process.exitCode=1;
}
