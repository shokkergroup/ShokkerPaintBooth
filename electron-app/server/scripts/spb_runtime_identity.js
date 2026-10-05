#!/usr/bin/env node
'use strict';

const crypto = require('crypto');
const fs = require('fs');
const path = require('path');

const SOURCE_HASH_ALGORITHM = "sha256(utf8(concat(role, ':', sha256(file), '\\n') for files in listed order))";

function sha256File(file) {
  return crypto.createHash('sha256').update(fs.readFileSync(file)).digest('hex');
}

function runtimeSourceIdentity(root, manifestName = 'runtime_identity_manifest.json') {
  const canonicalRoot = fs.realpathSync.native(path.resolve(root));
  const manifestPath = fs.realpathSync.native(path.resolve(canonicalRoot, manifestName));
  const manifestRelative = path.relative(canonicalRoot, manifestPath);
  if (!manifestRelative || manifestRelative === '..' || manifestRelative.startsWith(`..${path.sep}`) || path.isAbsolute(manifestRelative)) {
    throw new Error('runtime identity manifest is outside canonical root');
  }
  const manifest = JSON.parse(fs.readFileSync(manifestPath, 'utf8'));
  if (manifest.schema !== 1 || manifest.hash !== 'sha256' || manifest.source_hash_algorithm !== SOURCE_HASH_ALGORITHM || !Array.isArray(manifest.files) || !manifest.files.length) {
    throw new Error('runtime identity manifest is invalid');
  }
  const seen = new Set();
  const files = manifest.files.map((entry) => {
    if (!entry || !/^[a-z][a-z0-9_-]*$/i.test(entry.role || '') || seen.has(entry.role)) throw new Error(`invalid duplicate runtime role: ${entry && entry.role}`);
    seen.add(entry.role);
    if (typeof entry.path !== 'string' || !entry.path || path.isAbsolute(entry.path)) throw new Error(`invalid runtime identity path: ${entry && entry.path}`);
    const file = fs.realpathSync.native(path.resolve(canonicalRoot, entry.path));
    const relative = path.relative(canonicalRoot, file);
    if (!relative || relative === '..' || relative.startsWith(`..${path.sep}`) || path.isAbsolute(relative) || !fs.statSync(file).isFile()) throw new Error(`unsafe runtime identity source: ${entry.path}`);
    return { role: entry.role, path: entry.path, sha256: sha256File(file) };
  });
  if (!seen.has('server') || !seen.has('launcher')) throw new Error('runtime identity manifest requires server and launcher roles');
  const sourceHash = crypto.createHash('sha256').update(files.map((entry) => `${entry.role}:${entry.sha256}\n`).join(''), 'utf8').digest('hex');
  const byRole = Object.fromEntries(files.map((entry) => [entry.role, entry.sha256]));
  return {
    schemaVersion: 1,
    canonicalRoot,
    manifest: manifestRelative.replace(/\\/g, '/'),
    sourceHashAlgorithm: manifest.source_hash_algorithm,
    sourceHash,
    serverHash: byRole.server,
    launcherHash: byRole.launcher,
    files,
  };
}

module.exports = { runtimeSourceIdentity, sha256File };
if (require.main === module) process.stdout.write(JSON.stringify(runtimeSourceIdentity(path.resolve(__dirname, '..')), null, 2) + '\n');
