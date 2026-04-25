// Runtime: actually execute validateFinishData() against the live finish
// catalog. Pre-shift the function existed (Win #18) but was only validated
// structurally ("the function is wired"). Tonight we run it and capture
// the real drift list — every problem reported is a UI dead-end (blank
// tile, blank tab, duplicate entry, picker misroute) that a painter would
// trip over.

import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';
import vm from 'node:vm';

const __dirname = dirname(fileURLToPath(import.meta.url));
const REPO = join(__dirname, '..', '..');
const SRC = readFileSync(join(REPO, 'paint-booth-0-finish-data.js'), 'utf8');

// Build a context that captures console.warn calls as the validator runs.
const captured = { logs: [], warns: [] };
const ctx = {
    window: undefined, // pretend we're in Node (no auto-run)
    console: {
        log: function (...args) { captured.logs.push(args.map(String).join(' ')); },
        warn: function (...args) { captured.warns.push(args); },
    },
    setTimeout: function () {}, // suppress auto-run
};
vm.createContext(ctx);
vm.runInContext(SRC, ctx, { filename: 'paint-booth-0-finish-data.js', timeout: 5000 });

// Now invoke the validator explicitly.
const result = vm.runInContext('validateFinishData()', ctx);

console.log(JSON.stringify({
    problem_count: result.length,
    counts: result.counts,
    problems: result.slice(0, 100),
}, null, 2));
