#!/usr/bin/env node

const fs = require('fs');
const path = require('path');
const { countFileLines } = require('./spb_line_count');

const guardedFiles = [
  {
    file: 'paint-booth-0-catalog-scorecard.js',
    maxLines: 39319,
    owner: 'generated/catalog',
    nextStep: 'Do not append by hand. Patch via focused generator/update scripts, then extract generated payloads or ratchet this file down.',
  },
  {
    file: 'engine/spec_patterns.py',
    maxLines: 13880,
    owner: 'spec/patterns',
    nextStep: 'Add new pattern families to smaller modules and import/register them instead of growing the central registry file.',
  },
];

const args = new Set(process.argv.slice(2));
const enforce = args.has('--enforce');
const asJson = args.has('--json');
const root = process.cwd();

const rows = guardedFiles.map((entry) => {
  const fullPath = path.join(root, entry.file);
  if (!fs.existsSync(fullPath)) {
    return { ...entry, lines: null, delta: null, status: 'MISSING' };
  }

  const lines = countFileLines(fullPath);
  const delta = lines - entry.maxLines;
  let status = 'OK';
  if (delta > 0) status = 'DRIFTED_UP';
  else if (delta < 0) status = 'RATCHET_AVAILABLE';
  return { ...entry, lines, delta, status };
});

if (asJson) {
  console.log(JSON.stringify(rows, null, 2));
} else {
  console.log('SPB generated/spec drift guard');
  console.log('Purpose: stop known token-expensive generated/registry files from growing silently.');
  console.log('');
  console.log('status              lines  maxLines  delta  file');
  for (const row of rows) {
    const lines = row.lines == null ? 'n/a' : String(row.lines);
    const delta = row.delta == null ? 'n/a' : String(row.delta);
    console.log(
      `${row.status.padEnd(18)} ${lines.padStart(6)} ${String(row.maxLines).padStart(8)} ${delta.padStart(6)}  ${row.file} (${row.owner})`
    );
    if (row.status === 'DRIFTED_UP') {
      console.log(`  next: ${row.nextStep}`);
    }
  }
}

const failures = rows.filter((row) => row.status === 'MISSING' || row.status === 'DRIFTED_UP');
if (enforce && failures.length) {
  console.error('');
  console.error('Generated/spec drift guard failed:');
  for (const row of failures) {
    console.error(`- ${row.file}: ${row.status}${row.lines == null ? '' : ` (${row.lines}/${row.maxLines})`}`);
  }
  process.exit(1);
}
