#!/usr/bin/env node

const fs = require('fs');
const path = require('path');

const root = process.cwd();
const htmlPath = path.join(root, 'paint-booth-v2.html');
const mirrorRoots = [
  path.join(root, 'electron-app', 'server'),
  path.join(root, 'electron-app', 'server', 'pyserver', '_internal')
];

function hash(filePath) {
  return require('crypto').createHash('sha256').update(fs.readFileSync(filePath)).digest('hex');
}

const html = fs.readFileSync(htmlPath, 'utf8');
const hrefs = [...html.matchAll(/<link\b[^>]*rel=["']stylesheet["'][^>]*href=["']([^"']+)["']/gi)]
  .map((match) => match[1].split('?')[0])
  .filter((href) => !href.startsWith('http://') && !href.startsWith('https://') && !href.startsWith('data:'));

const failures = [];
for (const href of hrefs) {
  const rootFile = path.join(root, href);
  if (!fs.existsSync(rootFile)) {
    failures.push(`${href}: missing at repo root`);
    continue;
  }
  const rootHash = hash(rootFile);
  for (const mirrorRoot of mirrorRoots) {
    const mirrorFile = path.join(mirrorRoot, href);
    if (!fs.existsSync(mirrorFile)) {
      failures.push(`${href}: missing in ${path.relative(root, mirrorRoot)}`);
      continue;
    }
    if (hash(mirrorFile) !== rootHash) {
      failures.push(`${href}: hash mismatch in ${path.relative(root, mirrorRoot)}`);
    }
  }
}

if (failures.length) {
  console.error('Stylesheet link check failed:');
  for (const failure of failures) console.error(`- ${failure}`);
  process.exit(1);
}

console.log(`Stylesheet link check passed (${hrefs.length} local stylesheets).`);
