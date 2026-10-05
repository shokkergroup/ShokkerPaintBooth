#!/usr/bin/env node

const http = require('http');
const https = require('https');
const path = require('path');

const EXPECTED_ZONE_TOKEN = 'spb-zone-boot-bridge-3-20260522';
const DEFAULT_BASE_URL = 'http://127.0.0.1:59876';
const REPO_ROOT = path.resolve(__dirname, '..');

function parseArgs(argv) {
  const opts = { baseUrl: process.env.SPB_BOOT_SMOKE_URL || DEFAULT_BASE_URL };
  for (let i = 0; i < argv.length; i += 1) {
    if (argv[i] === '--url') opts.baseUrl = argv[++i] || opts.baseUrl;
    if (argv[i] === '--help' || argv[i] === '-h') opts.help = true;
  }
  return opts;
}

function usage() {
  console.log('Usage: node scripts/spb_smoke_zone_boot_http.js [--url http://127.0.0.1:59876]');
  console.log('Checks that a running SPB server serves the current zone boot token and extracted zone scripts.');
}

function requestText(url) {
  const lib = url.startsWith('https:') ? https : http;
  return new Promise((resolve, reject) => {
    const req = lib.get(url, { timeout: 5000 }, (res) => {
      let body = '';
      res.setEncoding('utf8');
      res.on('data', (chunk) => { body += chunk; });
      res.on('end', () => resolve({ status: res.statusCode, body }));
    });
    req.on('timeout', () => {
      req.destroy(new Error(`timeout fetching ${url}`));
    });
    req.on('error', reject);
  });
}

function assert(condition, message) {
  if (!condition) throw new Error(message);
}

function joinUrl(baseUrl, route) {
  return new URL(route, baseUrl.endsWith('/') ? baseUrl : `${baseUrl}/`).toString();
}

function extractScripts(html) {
  return Array.from(html.matchAll(/src="([^"?]+\.js)\?v=([^"]+)"/g))
    .map((hit) => ({ src: hit[1], token: hit[2] }))
    .filter((script) => script.src === 'paint-booth-2-state-zones.js' || script.src.startsWith('js/zones/'));
}

async function main() {
  const opts = parseArgs(process.argv.slice(2));
  if (opts.help) {
    usage();
    return;
  }

  const build = await requestText(joinUrl(opts.baseUrl, 'build-check'));
  assert(build.status === 200, `/build-check returned ${build.status}`);
  const buildJson = JSON.parse(build.body);
  assert(path.resolve(buildJson.server_dir || '') === REPO_ROOT, `server_dir is not canonical: ${buildJson.server_dir}`);

  const root = await requestText(joinUrl(opts.baseUrl, ''));
  assert(root.status === 200, `/ returned ${root.status}`);
  const scripts = extractScripts(root.body);
  const zoneScript = scripts.find((script) => script.src === 'paint-booth-2-state-zones.js');
  assert(zoneScript, 'root HTML did not include paint-booth-2-state-zones.js');
  assert(zoneScript.token === EXPECTED_ZONE_TOKEN, `zone script token is ${zoneScript.token}, expected ${EXPECTED_ZONE_TOKEN}`);

  const zoneModules = scripts.filter((script) => script.src.startsWith('js/zones/'));
  assert(zoneModules.length >= 20, `only found ${zoneModules.length} extracted zone module scripts`);

  const failures = [];
  for (const script of [...zoneModules, zoneScript]) {
    const url = joinUrl(opts.baseUrl, `${script.src}?v=${script.token}`);
    const res = await requestText(url);
    if (res.status !== 200 || !res.body.trim()) failures.push(`${script.src}?v=${script.token} -> ${res.status}`);
  }
  assert(failures.length === 0, `script fetch failures:\n- ${failures.join('\n- ')}`);

  console.log(`Zone boot HTTP smoke passed (${zoneModules.length} extracted modules, token ${zoneScript.token}).`);
}

main().catch((err) => {
  console.error(`Zone boot HTTP smoke failed: ${err.message}`);
  process.exit(1);
});
