#!/usr/bin/env node
// check-format.mjs — REPORT-ONLY formatting scan (WIN #31).
//
// Scans first-party source dirs for the most basic formatting issues:
//   - missing final newline
//   - trailing whitespace
//   - mixed tabs/spaces in a file's leading indentation
//
// This is intentionally NOT a gate: it prints a count + a small sample and
// ALWAYS exits 0. It never reformats or modifies any file. The .editorconfig
// at the repo root carries the canonical rules; this script only surfaces
// drift so it can be cleaned up by hand over time.
//
// Generated bundles, dependencies, archives, build output and caches are
// skipped (node_modules, _archive, dist, __pycache__, .git).

import { readFileSync, readdirSync, statSync, existsSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join, resolve, relative, extname } from 'node:path';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const ROOT = resolve(__dirname, '..');

// First-party source dirs to scan. The engine (shokker_engine_v2) is
// deliberately out of scope — it is large and finish/spec-math owned.
const SCAN_DIRS = ['server_routes', 'scripts', 'js', 'tests_v2'];

// Directory names that must never be descended into.
const SKIP_DIRS = new Set([
  'node_modules',
  '_archive',
  'dist',
  '__pycache__',
  '.git',
  '.claude',
]);

// Only text-ish source extensions are checked.
const TEXT_EXT = new Set([
  '.py', '.js', '.mjs', '.cjs', '.json', '.yml', '.yaml',
  '.css', '.html', '.md', '.txt',
]);

// Markdown legitimately uses trailing whitespace for hard line breaks; mirror
// the .editorconfig and skip the trailing-whitespace check there.
const TRAILING_WS_EXEMPT = new Set(['.md']);

const SAMPLE_LIMIT = 10;

/** Recursively collect candidate files under `dir`. */
function collect(dir, acc) {
  let entries;
  try {
    entries = readdirSync(dir, { withFileTypes: true });
  } catch {
    return acc;
  }
  for (const ent of entries) {
    const full = join(dir, ent.name);
    if (ent.isDirectory()) {
      if (SKIP_DIRS.has(ent.name)) continue;
      collect(full, acc);
    } else if (ent.isFile()) {
      if (TEXT_EXT.has(extname(ent.name).toLowerCase())) acc.push(full);
    }
  }
  return acc;
}

/** Inspect one file; return an array of { type, file } issue records. */
function inspect(file) {
  const issues = [];
  let raw;
  try {
    raw = readFileSync(file, 'utf8');
  } catch {
    return issues; // unreadable / binary — silently skip
  }
  if (raw.length === 0) return issues; // empty file: nothing to flag

  const ext = extname(file).toLowerCase();
  const rel = relative(ROOT, file).split('\\').join('/');

  // Missing final newline.
  if (!raw.endsWith('\n')) {
    issues.push({ type: 'no-final-newline', file: rel });
  }

  // Split on \n; tolerate CRLF by stripping the \r when testing.
  const lines = raw.split('\n');
  let trailing = 0;
  let tabIndent = 0;
  let spaceIndent = 0;
  let firstTrailingLine = 0;

  for (let i = 0; i < lines.length; i++) {
    const ln = lines[i].replace(/\r$/, '');
    // Trailing whitespace (ignore the final empty element after a trailing \n).
    if (!TRAILING_WS_EXEMPT.has(ext) && /[ \t]+$/.test(ln) && ln.length > 0) {
      trailing++;
      if (!firstTrailingLine) firstTrailingLine = i + 1;
    }
    // Leading-indent style sampling.
    const m = ln.match(/^([ \t]+)/);
    if (m) {
      if (m[1].includes('\t')) tabIndent++;
      if (m[1].includes(' ')) spaceIndent++;
    }
  }

  if (trailing > 0) {
    issues.push({ type: 'trailing-whitespace', file: rel, count: trailing, line: firstTrailingLine });
  }
  // Mixed tabs/spaces: file uses BOTH tab-led and space-led indentation.
  if (tabIndent > 0 && spaceIndent > 0) {
    issues.push({ type: 'mixed-tabs-spaces', file: rel, tabLines: tabIndent, spaceLines: spaceIndent });
  }

  return issues;
}

function main() {
  const files = [];
  for (const d of SCAN_DIRS) {
    const full = join(ROOT, d);
    if (existsSync(full)) collect(full, files);
  }

  const buckets = {
    'no-final-newline': [],
    'trailing-whitespace': [],
    'mixed-tabs-spaces': [],
  };

  for (const f of files) {
    for (const issue of inspect(f)) {
      (buckets[issue.type] ||= []).push(issue);
    }
  }

  const total =
    buckets['no-final-newline'].length +
    buckets['trailing-whitespace'].length +
    buckets['mixed-tabs-spaces'].length;

  console.log('check-format (report-only) — WIN #31');
  console.log(`scanned dirs: ${SCAN_DIRS.join(', ')}`);
  console.log(`files inspected: ${files.length}`);
  console.log('');

  const labels = {
    'no-final-newline': 'missing final newline',
    'trailing-whitespace': 'trailing whitespace',
    'mixed-tabs-spaces': 'mixed tabs/spaces',
  };

  for (const key of Object.keys(buckets)) {
    const list = buckets[key];
    console.log(`${labels[key]}: ${list.length}`);
    for (const it of list.slice(0, SAMPLE_LIMIT)) {
      let extra = '';
      if (it.count) extra = ` (${it.count} lines, first @ line ${it.line})`;
      else if (it.tabLines) extra = ` (${it.tabLines} tab-led / ${it.spaceLines} space-led lines)`;
      console.log(`  - ${it.file}${extra}`);
    }
    if (list.length > SAMPLE_LIMIT) {
      console.log(`  ... and ${list.length - SAMPLE_LIMIT} more`);
    }
  }

  console.log('');
  console.log(`total issues: ${total}`);
  console.log('note: report-only — no files were modified; this never fails the build.');

  // ALWAYS succeed. This is a report, not a gate.
  process.exit(0);
}

main();
