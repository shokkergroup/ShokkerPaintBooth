#!/usr/bin/env node
/*
 * SPB repo-wide context gateway.
 *
 * This script gives agents small, line-numbered windows into Shokker Paint
 * Booth's large files and performs capped searches that skip expensive
 * generated/binary/runtime directories by default.
 */

const fs = require('fs');
const path = require('path');

const ROOT = path.resolve(__dirname, '..');  // repo root = parent of scripts/ — cwd-independent
const DEFAULT_CONTEXT = 2;
const DEFAULT_MAX_MATCHES = 30;
const TARGETS_PATH = path.join(__dirname, 'spb_context_targets.json');

const EXCLUDED_DIR_PARTS = [
  '.git',
  '.claude',
  'node_modules',
  '_archive',
  '_workbook_metrics',
  'PayHip-upload',
  'docs/DNA FINISH BIBLES',
  'electron-app/server',
  'electron-app/dist',
  'dist-sandbox',
  '__pycache__',
  '.pytest_cache',
];

const TEXT_EXTENSIONS = new Set([
  '.js', '.py', '.html', '.css', '.md', '.json', '.txt', '.yml', '.yaml',
  '.toml', '.ps1', '.bat', '.sh', '.cjs', '.mjs', '.ts', '.tsx', '.jsx',
]);

const EXCLUDED_FILE_NAMES = new Set([
  'server_log.txt',
]);

function loadTargetDatabase() {
  const db = JSON.parse(fs.readFileSync(TARGETS_PATH, 'utf8'));
  const rawTargets = db.targets || db;
  const normalized = {};
  for (const [name, entry] of Object.entries(rawTargets)) {
    const slices = Array.isArray(entry) ? entry : entry.slices;
    if (!Array.isArray(slices)) {
      throw new Error(`Target ${name} must define a slices array`);
    }
    normalized[name] = {
      domain: Array.isArray(entry) ? 'uncategorized' : (entry.domain || 'uncategorized'),
      description: Array.isArray(entry) ? '' : (entry.description || ''),
      slices,
    };
  }
  return normalized;
}

const targets = loadTargetDatabase();

function rel(p) {
  return p.split(path.sep).join('/');
}

function isExcluded(absPath) {
  const r = rel(path.relative(ROOT, absPath));
  if (EXCLUDED_FILE_NAMES.has(path.basename(absPath))) return true;
  return EXCLUDED_DIR_PARTS.some((part) => r.includes(part.replace(/\\/g, '/')));
}

function isTextFile(absPath) {
  return TEXT_EXTENSIONS.has(path.extname(absPath).toLowerCase());
}

function walk(dir, out = []) {
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    const abs = path.join(dir, entry.name);
    if (isExcluded(abs)) continue;
    if (entry.isDirectory()) {
      walk(abs, out);
    } else if (entry.isFile() && isTextFile(abs)) {
      out.push(abs);
    }
  }
  return out;
}

function readLines(relPath) {
  const abs = path.join(ROOT, relPath);
  if (!fs.existsSync(abs)) {
    console.warn(`[spb_context] missing slice source: ${relPath} (skipped)`);
    return null;
  }
  return fs.readFileSync(abs, 'utf8').split(/\r?\n/);
}

function printSlice(relPath, start, end) {
  const lines = readLines(relPath);
  if (!lines) return false;
  const safeStart = Math.max(1, start);
  const safeEnd = Math.min(lines.length, end);
  console.log(`\n--- ${relPath}:${safeStart}-${safeEnd} ---`);
  for (let i = safeStart; i <= safeEnd; i += 1) {
    const line = lines[i - 1];
    console.log(`${String(i).padStart(5, ' ')}: ${line.length > 240 ? line.slice(0, 237) + '...' : line}`);
  }
  return true;
}

function listTargets() {
  console.log('Usage: node scripts/spb_context.js --target <name> [name...]');
  console.log('       node scripts/spb_context.js --find <pattern> [file-or-dir...] [--context N] [--max N]');
  console.log('       node scripts/spb_context.js --large [N]');
  console.log('');
  console.log('Targets:');
  for (const name of Object.keys(targets).sort()) {
    const target = targets[name];
    const suffix = target.description ? ` - ${target.description}` : '';
    console.log(`  ${name} [${target.domain}]${suffix}`);
  }
}

function printTargets(names) {
  let failed = false;
  for (const name of names) {
    const target = targets[name];
    if (!target) {
      console.error(`Unknown target: ${name}`);
      failed = true;
      continue;
    }
    for (const [file, start, end] of target.slices) printSlice(file, start, end);
  }
  if (failed) process.exit(1);
}

function compilePattern(pattern) {
  try {
    return new RegExp(pattern, 'i');
  } catch (_err) {
    return { test: (line) => line.toLowerCase().includes(pattern.toLowerCase()) };
  }
}

function resolveSearchFiles(pathsArg) {
  if (pathsArg.length === 0) return walk(ROOT);
  const files = [];
  for (const p of pathsArg) {
    const abs = path.resolve(ROOT, p);
    if (!fs.existsSync(abs) || isExcluded(abs)) continue;
    const stat = fs.statSync(abs);
    if (stat.isDirectory()) walk(abs, files);
    else if (stat.isFile() && isTextFile(abs)) files.push(abs);
  }
  return files;
}

function findPattern(pattern, pathsArg, context, maxMatches) {
  const rx = compilePattern(pattern);
  const files = resolveSearchFiles(pathsArg);
  let matches = 0;
  for (const abs of files) {
    if (matches >= maxMatches) break;
    let lines;
    try {
      lines = fs.readFileSync(abs, 'utf8').split(/\r?\n/);
    } catch (_err) {
      continue;
    }
    for (let idx = 0; idx < lines.length; idx += 1) {
      if (!rx.test(lines[idx])) continue;
      const relPath = rel(path.relative(ROOT, abs));
      const start = Math.max(1, idx + 1 - context);
      const end = Math.min(lines.length, idx + 1 + context);
      console.log(`\n--- ${relPath}:${start}-${end} ---`);
      for (let n = start; n <= end; n += 1) {
        const line = lines[n - 1];
        console.log(`${String(n).padStart(5, ' ')}: ${line.length > 240 ? line.slice(0, 237) + '...' : line}`);
      }
      matches += 1;
      if (matches >= maxMatches) break;
    }
  }
  console.log(`\n[spb_context] matches printed: ${matches}/${maxMatches}; files scanned: ${files.length}`);
}

function printLarge(limit) {
  const files = walk(ROOT)
    .map((abs) => {
      const stat = fs.statSync(abs);
      return { relPath: rel(path.relative(ROOT, abs)), kb: Math.round((stat.size / 1024) * 10) / 10 };
    })
    .sort((a, b) => b.kb - a.kb)
    .slice(0, limit);
  for (const f of files) {
    console.log(`${String(f.kb).padStart(9, ' ')} KB  ${f.relPath}`);
  }
}

function readOption(args, name, fallback) {
  const idx = args.indexOf(name);
  if (idx === -1 || idx + 1 >= args.length) return fallback;
  const value = Number(args[idx + 1]);
  return Number.isFinite(value) && value >= 0 ? value : fallback;
}

const args = process.argv.slice(2);
if (args.length === 0 || args.includes('--help') || args.includes('-h') || args.includes('--list')) {
  listTargets();
  process.exit(0);
}

if (args[0] === '--large') {
  printLarge(Number(args[1]) || 30);
  process.exit(0);
}

if (args[0] === '--target') {
  printTargets(args.slice(1));
  process.exit(0);
}

if (args[0] === '--find') {
  const pattern = args[1];
  if (!pattern) {
    console.error('--find requires a pattern');
    process.exit(1);
  }
  const context = readOption(args, '--context', DEFAULT_CONTEXT);
  const maxMatches = readOption(args, '--max', DEFAULT_MAX_MATCHES);
  const reserved = new Set(['--context', '--max']);
  const pathArgs = [];
  for (let i = 2; i < args.length; i += 1) {
    if (reserved.has(args[i])) {
      i += 1;
      continue;
    }
    pathArgs.push(args[i]);
  }
  findPattern(pattern, pathArgs, context, maxMatches);
  process.exit(0);
}

// Convenience: allow `node scripts/spb_context.js canvas-dispatch`.
printTargets(args);
