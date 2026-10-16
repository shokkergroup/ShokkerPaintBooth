'use strict';
// ONLINE-AI 2026-10-09: regression test for the R9 undo guard in mcp/server/index.js (callTool: "A write whose buyer words are an undo / revert / back-to-original is refused with the instruction to call spb_undo").
// The two regexes were written with literal BACKSPACE characters (0x08, a Python '\b' in a non-raw string) instead of the \b word boundary, so the guard NEVER matched (dead since R9, 2026-10-08, still in 1.4.1).
// This test (1) fails if index.js contains any 0x08 byte, (2) pulls the two regexes out of the source and checks real buyer phrases against them.
//   node mcp/test/undo_guard_regex.test.cjs
const fs = require('fs'), path = require('path'), assert = require('assert');
const src = fs.readFileSync(path.join(__dirname, '..', 'server', 'index.js'), 'utf8');
assert.strictEqual(src.indexOf('\x08'), -1, 'index.js contains a literal backspace (0x08): write \\b, not a control character (Python non-raw string trap)');
const line = src.split(/\r?\n/).find((l) => /said\.length < 90 &&/.test(l));
assert(line, 'undo guard line not found');
const m = /said\.length < 90 && (\/.+?\/)\.test\(said\) && !(\/.+?\/)\.test\(said\)/.exec(line);
assert(m, 'could not extract the two undo regexes from: ' + line.slice(0, 120));
const undoRe = eval(m[1]), exceptRe = eval(m[2]);     // regex literals from our own source file
const isUndo = (t) => { const s = String(t).toLowerCase(); return s.length < 90 && undoRe.test(s) && !exceptRe.test(s); };
const yes = ['undo that', 'nah back to how it was', 'Undo', 'revert it', 'take that back', 'put it back', 'go back', 'back to the original', 'back to normal please', 'as it was before', 'undo the last one', 'can you undo that', 'undo both'];
const no = ['make the hood red', 'paint the roof black', 'undone is not a word here', 'a bit more orange', 'keep going', 'make the roof white and then make the trunk blue', 'undo that and make the hood red', 'revert to blue then paint the roof green', 'background colour on the hood', 'hood redo it in blue', 'goback'];
yes.forEach((t) => assert(isUndo(t), 'should be an undo: ' + t));
no.forEach((t) => assert(!isUndo(t), 'must NOT be an undo: ' + t));
console.log('undo_guard_regex OK (' + yes.length + ' undo phrases, ' + no.length + ' non-undo phrases, no 0x08 in index.js)');
