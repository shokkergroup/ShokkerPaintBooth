#!/usr/bin/env node

const fs = require('fs');
const path = require('path');

function usage() {
  console.error(
    [
      'Usage:',
      '  node scripts/spb_extract_css_block.js --source paint-booth-v2.css --target css/file.css --start "marker" --before "next marker" --title "Title" --note "replacement note"',
      '',
      'Extracts the block beginning at --start and ending immediately before --before.',
      'Writes UTF-8 without BOM and leaves a small note in the source file.'
    ].join('\n')
  );
  process.exit(2);
}

const args = process.argv.slice(2);
const opts = {};
for (let i = 0; i < args.length; i += 2) {
  const key = args[i];
  const value = args[i + 1];
  if (!key || !key.startsWith('--') || value == null) usage();
  opts[key.slice(2)] = value;
}

const required = ['source', 'target', 'start', 'before', 'title', 'note'];
for (const key of required) {
  if (!opts[key]) usage();
}

const sourcePath = path.resolve(opts.source);
const targetPath = path.resolve(opts.target);
const source = fs.readFileSync(sourcePath, 'utf8').replace(/^\uFEFF/, '');
const newline = source.includes('\r\n') ? '\r\n' : '\n';
const lines = source.split(/\r?\n/);

const startIndex = lines.findIndex((line) => line.trim() === opts.start.trim());
const beforeIndex = lines.findIndex((line, index) => index > startIndex && line.trim() === opts.before.trim());
if (startIndex < 0 || beforeIndex < 0) {
  throw new Error(`Could not resolve extraction markers for ${opts.target}`);
}

const extracted = lines.slice(startIndex, beforeIndex);
const header = [
  '/* ============================================================',
  `   ${opts.title}`,
  '   Extracted from paint-booth-v2.css for SPB-105 file-budget work.',
  '   Loaded in original cascade order by paint-booth-v2.html.',
  '   ============================================================ */',
  ''
];

fs.mkdirSync(path.dirname(targetPath), { recursive: true });
fs.writeFileSync(targetPath, `${header.concat(extracted).join(newline)}${newline}`, 'utf8');

const replacement = [
  `/* SPB-105: ${opts.note}`,
  `   Moved to ${opts.target}; keep it loaded in the original cascade position. */`,
  ''
];
const next = lines.slice(0, startIndex).concat(replacement, lines.slice(beforeIndex));
fs.writeFileSync(sourcePath, next.join(newline), 'utf8');

console.log(`Extracted ${extracted.length} lines to ${opts.target}`);
