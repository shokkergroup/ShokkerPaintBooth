#!/usr/bin/env node
/*
 * SPB-93 context gateway.
 *
 * Prints small, line-numbered slices for tool-system work so agents do not
 * dump the 20k+ line canvas file into context for routine audits.
 */

const fs = require('fs');
const path = require('path');

const ROOT = process.cwd();

const targets = {
  dispatch: [
    ['js/canvas/dispatch.js', 1, 230],
  ],
  'canvas-guards': [
    ['paint-booth-3-canvas.js', 2976, 3038],
    ['paint-booth-3-canvas.js', 19330, 19378],
  ],
  'pick-item': [
    ['paint-booth-3-canvas.js', 3024, 3224],
    ['paint-booth-3-canvas.js', 19850, 19882],
  ],
  'fill-gradient': [
    ['paint-booth-3-canvas.js', 3569, 3607],
  ],
  wrappers: [
    ['paint-booth-3-canvas.js', 13920, 13970],
    ['paint-booth-3-canvas.js', 15755, 15810],
  ],
  'layer-target': [
    ['paint-booth-3-canvas.js', 19340, 19378],
    ['paint-booth-3-canvas.js', 19491, 19527],
    ['js/canvas/dispatch.js', 99, 123],
  ],
  tests: [
    ['tests/test_layer_system.py', 6586, 6636],
    ['tests/test_layer_system.py', 6768, 6818],
    ['tests/test_layer_system.py', 9740, 9780],
  ],
};

function usage(exitCode = 0) {
  console.log('Usage: node scripts/spb93_context.js <target> [target...]');
  console.log('');
  console.log('Targets:');
  for (const name of Object.keys(targets).sort()) {
    console.log(`  ${name}`);
  }
  process.exit(exitCode);
}

function readLines(relPath) {
  const abs = path.join(ROOT, relPath);
  return fs.readFileSync(abs, 'utf8').split(/\r?\n/);
}

function printSlice(relPath, start, end) {
  const lines = readLines(relPath);
  const safeStart = Math.max(1, start);
  const safeEnd = Math.min(lines.length, end);
  console.log(`\n--- ${relPath}:${safeStart}-${safeEnd} ---`);
  for (let i = safeStart; i <= safeEnd; i += 1) {
    console.log(`${String(i).padStart(5, ' ')}: ${lines[i - 1]}`);
  }
}

const args = process.argv.slice(2);
if (args.length === 0 || args.includes('--help') || args.includes('-h') || args.includes('--list')) {
  usage(0);
}

let hadUnknown = false;
for (const target of args) {
  const slices = targets[target];
  if (!slices) {
    console.error(`Unknown SPB-93 context target: ${target}`);
    hadUnknown = true;
    continue;
  }
  for (const slice of slices) {
    printSlice(slice[0], slice[1], slice[2]);
  }
}

if (hadUnknown) process.exit(1);
