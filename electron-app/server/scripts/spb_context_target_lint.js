#!/usr/bin/env node
/* Verify that every named spb_context target resolves to a real bounded text file. */
'use strict';

const fs = require('fs');
const path = require('path');

const ROOT = path.resolve(__dirname, '..');
const DB_PATH = path.join(__dirname, 'spb_context_targets.json');
const db = JSON.parse(fs.readFileSync(DB_PATH, 'utf8'));
const targets = db.targets || db;
const requested = process.argv.slice(2).filter((arg) => !arg.startsWith('-'));
const names = requested.length ? requested : Object.keys(targets);
const failures = [];
let slices = 0;

for (const name of names) {
  const entry = targets[name];
  if (!entry) {
    failures.push(`unknown target: ${name}`);
    continue;
  }
  const items = Array.isArray(entry) ? entry : entry.slices;
  if (!Array.isArray(items)) {
    failures.push(`${name}: missing slices array`);
    continue;
  }
  for (const slice of items) {
    slices += 1;
    if (!Array.isArray(slice) || slice.length !== 3) {
      failures.push(`${name}: malformed slice ${JSON.stringify(slice)}`);
      continue;
    }
    const [rel, start, end] = slice;
    const abs = path.resolve(ROOT, String(rel));
    if (!abs.startsWith(ROOT + path.sep)) {
      failures.push(`${name}: slice escapes workspace: ${rel}`);
      continue;
    }
    if (!fs.existsSync(abs) || !fs.statSync(abs).isFile()) {
      failures.push(`${name}: missing file: ${rel}`);
      continue;
    }
    if (!Number.isInteger(start) || !Number.isInteger(end) || start < 1 || end < start) {
      failures.push(`${name}: invalid range ${start}-${end} for ${rel}`);
    }
  }
}

if (failures.length) {
  console.error(`SPB context target lint: ${failures.length} failure(s)`);
  failures.forEach((failure) => console.error(`  - ${failure}`));
  process.exit(1);
}

console.log(`SPB context target lint: ${names.length} target(s), ${slices} slice(s), all valid`);
