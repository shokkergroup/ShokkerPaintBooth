#!/usr/bin/env node
'use strict';

const crypto = require('crypto');
const fs = require('fs');
const path = require('path');
const { spawnSync } = require('child_process');

const requiredRoles = new Map([
  ['updaterPackage', ['r2']],
  ['webInstaller', ['r2', 'payhip']],
  ['payhipBundle', ['payhip']],
]);
const requiredMappings = {
  filesUrl: 'webInstaller', path: 'webInstaller',
  packagesX64Path: 'updaterPackage', packagesX64File: 'updaterPackage',
};

function digest(file, algorithm = 'sha256', encoding = 'hex') {
  const hash = crypto.createHash(algorithm), buffer = Buffer.allocUnsafe(1024 * 1024), fd = fs.openSync(file, 'r');
  try {
    for (let offset = 0, count = 0; (count = fs.readSync(fd, buffer, 0, buffer.length, offset)) > 0; offset += count) hash.update(buffer.subarray(0, count));
  } finally { fs.closeSync(fd); }
  return hash.digest(encoding);
}
function validHash(value) { return /^[0-9a-f]{64}$/i.test(String(value || '')); }
function validDate(value) {
  return typeof value === 'string' && /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{3})?Z$/.test(value) && Number.isFinite(Date.parse(value)) && Date.parse(value) <= Date.now() + 5 * 60 * 1000;
}
function normalizedRoot(value) {
  if (typeof value !== 'string' || !value.trim()) return null;
  const resolved = path.resolve(value.trim()).replace(/[\\/]+$/, '');
  return process.platform === 'win32' ? resolved.toLowerCase() : resolved;
}
function rootFile(root, relative, label, fail) {
  if (typeof relative !== 'string' || !relative.trim()) { fail(`${label} path is missing`); return null; }
  const resolved = path.resolve(root, relative), rel = path.relative(root, resolved);
  if (rel.startsWith('..') || path.isAbsolute(rel)) { fail(`${label} must stay inside the canonical workspace`); return null; }
  if (!fs.existsSync(resolved)) { fail(`${label} does not exist: ${relative}`); return null; }
  const real = fs.realpathSync.native(resolved), realRel = path.relative(fs.realpathSync.native(root), real);
  if (realRel.startsWith('..') || path.isAbsolute(realRel) || !fs.statSync(real).isFile()) { fail(`${label} must be a file inside the canonical workspace`); return null; }
  return real;
}
function checkRecordedFile(root, section, pathKey, hashKey, sizeKey, label, fail) {
  const file = rootFile(root, section && section[pathKey], label, fail);
  if (!file) return null;
  if (!validHash(section[hashKey]) || section[hashKey].toLowerCase() !== digest(file)) fail(`${label} SHA-256 does not match`);
  if (sizeKey && Number(section[sizeKey]) !== fs.statSync(file).size) fail(`${label} byte size does not match`);
  return file;
}
function gitCandidate(root) {
  const opts = { cwd: root, encoding: 'utf8', windowsHide: true, maxBuffer: 32 * 1024 * 1024 };
  const head = spawnSync('git', ['rev-parse', 'HEAD'], opts);
  const status = spawnSync('git', ['status', '--porcelain=v1', '--untracked-files=all'], opts);
  const rows = status.status === 0 ? status.stdout.split(/\r?\n/).filter(Boolean) : [];
  return {
    ok: head.status === 0 && status.status === 0,
    head: head.status === 0 ? head.stdout.trim() : null,
    trackedClean: status.status === 0 && !rows.some((row) => !row.startsWith('?? ')),
    candidateClean: status.status === 0 && rows.length === 0,
    detail: String(head.stderr || status.stderr || '').trim(),
  };
}
function parseLatestYml(file) {
  const text = fs.readFileSync(file, 'utf8');
  const clean = (value) => String(value || '').trim().replace(/^['"]|['"]$/g, '');
  const take = (pattern) => { const match = text.match(pattern); return clean(match && match[1]); };
  const packageBlock = (text.match(/^packages:\s*\r?\n((?:[ \t].*(?:\r?\n|$))*)/m) || [])[1] || '';
  return {
    version: take(/^version:\s*(\S.*?)\s*$/m),
    filesUrls: [...text.matchAll(/^[ \t]+-\s+url:\s*(\S.*?)\s*$/gm)].map((match) => clean(match[1])),
    path: take(/^path:\s*(\S.*?)\s*$/m), sha512: take(/^sha512:\s*(\S.*?)\s*$/m),
    packagePath: clean((packageBlock.match(/^\s+path:\s*(\S.*?)\s*$/m) || [])[1]),
    packageFile: clean((packageBlock.match(/^\s+file:\s*(\S.*?)\s*$/m) || [])[1]),
    packageSize: Number(((packageBlock.match(/^\s+size:\s*(\d+)\s*$/m) || [])[1])),
    packageSha512: clean((packageBlock.match(/^\s+sha512:\s*(\S.*?)\s*$/m) || [])[1]),
  };
}
function validateBuiltEvidence(root, evidence, version, requirePackaged, fail) {
  if (requirePackaged || evidence.packagedSmoke !== undefined) {
    const packaged = evidence.packagedSmoke || {};
    if (packaged.result !== 'PASS' || !validDate(packaged.completedAt) || packaged.cleanMachine !== true) fail('clean-machine packaged smoke evidence is incomplete');
    checkRecordedFile(root, packaged, 'record', 'recordSha256', null, 'packaged smoke record', fail);
    if (JSON.stringify(packaged.artifactRoles) !== JSON.stringify(['webInstaller', 'updaterPackage'])) fail('packaged smoke artifactRoles must be exactly webInstaller then updaterPackage');
  }
  const rows = Array.isArray(evidence.distributables) ? evidence.distributables : [], roles = new Map();
  for (const row of rows) {
    if (!row || typeof row.role !== 'string' || roles.has(row.role)) { fail('distributable roles are missing or duplicated'); continue; }
    roles.set(row.role, row);
  }
  if (rows.length !== requiredRoles.size || [...requiredRoles.keys()].some((role) => !roles.has(role))) fail('distributables must enumerate updaterPackage, webInstaller, and payhipBundle exactly once');
  for (const [role, channels] of requiredRoles) {
    const row = roles.get(role); if (!row) continue;
    if (JSON.stringify(row.channels) !== JSON.stringify(channels)) fail(`${role} channels do not match the release contract`);
    const file = checkRecordedFile(root, row, 'path', 'sha256', 'bytes', `${role} distributable`, fail);
    if (file) row._verifiedFile = file;
  }
  const updater = roles.get('updaterPackage'), installer = roles.get('webInstaller'), payhip = roles.get('payhipBundle');
  if (updater && !String(updater.path || '').toLowerCase().endsWith('.nsis.7z')) fail('updaterPackage must be an .nsis.7z file');
  if (installer && !String(installer.path || '').toLowerCase().endsWith('-web-setup.exe')) fail('webInstaller must be a -Web-Setup.exe file');
  if (payhip && (!String(payhip.path || '').toLowerCase().endsWith('.zip') || !path.basename(payhip.path).includes(version))) fail('payhipBundle must be a versioned zip');

  const latest = evidence.latestYml || {}, latestFile = checkRecordedFile(root, latest, 'path', 'sha256', 'bytes', 'latest.yml', fail);
  const mappingKeys = latest.mappings && typeof latest.mappings === 'object' ? Object.keys(latest.mappings) : [];
  if (mappingKeys.length !== Object.keys(requiredMappings).length || Object.entries(requiredMappings).some(([key, value]) => latest.mappings[key] !== value)) fail('latest.yml mappings do not enumerate every installer/payload field');
  if (!latestFile || !updater || !installer || !updater._verifiedFile || !installer._verifiedFile) return;
  const parsed = parseLatestYml(latestFile), updaterName = path.basename(updater._verifiedFile), installerName = path.basename(installer._verifiedFile);
  if (parsed.version !== version) fail(`latest.yml version must be ${version}`);
  if (JSON.stringify(parsed.filesUrls) !== JSON.stringify([installerName]) || parsed.path !== installerName) fail('latest.yml installer mappings do not match webInstaller');
  if (parsed.packagePath !== updaterName || parsed.packageFile !== updaterName) fail('latest.yml package mappings do not match updaterPackage');
  if (parsed.packageSize !== fs.statSync(updater._verifiedFile).size) fail('latest.yml package size does not match updaterPackage');
  if (parsed.sha512 !== digest(installer._verifiedFile, 'sha512', 'base64')) fail('latest.yml installer SHA-512 does not match webInstaller');
  if (parsed.packageSha512 !== digest(updater._verifiedFile, 'sha512', 'base64')) fail('latest.yml package SHA-512 does not match updaterPackage');
}

module.exports = { checkRecordedFile, digest, gitCandidate, normalizedRoot, parseLatestYml, rootFile, validDate, validHash, validateBuiltEvidence };
