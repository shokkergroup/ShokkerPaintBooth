'use strict';
// Proposed release tool: explicit prepared tree, portable inventory, no audit paths.
const fs = require('node:fs'), path = require('node:path'), crypto = require('node:crypto');
const hash = b => crypto.createHash('sha256').update(b).digest('hex');
const ROLE_KEYS = ['entry', 'app_knowledge', 'delivery', 'context', 'car_lookup', 'car_bundle', 'encyclopedia'];
const SETUP = ['server_routes/codex_setup.py', 'server_routes/codex_runtime.py', 'server_routes/codex_knowledge.py'];
function local(root, relative) {
  if (typeof relative !== 'string' || !relative || relative.includes('\\') || path.isAbsolute(relative) || relative.split('/').some(x => !x || x === '.' || x === '..')) throw Error('Invalid install-relative path: ' + relative);
  const file = path.resolve(root, relative), real = fs.realpathSync(file), delta = path.relative(root, real);
  if (delta === '..' || delta.startsWith('..' + path.sep) || path.isAbsolute(delta) || !fs.statSync(real).isFile()) throw Error('Outside prepared tree: ' + relative);
  return real;
}
function offline() {
  const deny = () => { throw Error('Manifest generation is offline'); };
  for (const name of ['http', 'https']) { const mod = require(name); mod.get = deny; mod.request = deny; }
  require('node:net').Socket.prototype.connect = deny;
  global.fetch = deny;
}
function build(serverRoot, plan) {
  const root = fs.realpathSync(serverRoot);
  if (plan.schema !== 'spb-runtime-knowledge-plan/1' || !Array.isArray(plan.required_files) || !plan.required_files.length || plan.required_files.length > 2000 || typeof plan.server_version !== 'string' || !plan.server_version) throw Error('Invalid knowledge plan');
  const names = new Set(plan.required_files);
  if (names.size !== plan.required_files.length) throw Error('Duplicate inventory path');
  for (const key of ROLE_KEYS) if (!names.has(plan.roles?.[key])) throw Error('Missing required role: ' + key);
  for (const name of SETUP.concat('mcp/server/knowledge-health.cjs')) if (!names.has(name)) throw Error('Release inventory must include ' + name);
  if (names.has('mcp/runtime-knowledge-manifest.json')) throw Error('Manifest cannot hash itself');
  const files = [...names].sort().map(relative => {
    const file = local(root, relative), bytes = fs.readFileSync(file);
    if (bytes.length > 32 * 1024 * 1024) throw Error('Knowledge file exceeds checker limit: ' + relative);
    if (relative.startsWith('data/encyclopedia/') && relative.endsWith('.json')) JSON.parse(bytes.toString('utf8'));
    return {path: relative, sha256: hash(bytes), bytes: bytes.length};
  });
  // Require only trusted, inventoried local knowledge modules, never the MCP entry.
  offline();
  const knowledge = require(local(root, plan.roles.app_knowledge));
  const delivery = require(local(root, plan.roles.delivery));
  const packet = delivery.packet(knowledge, 'Help me understand SPB', plan.server_version);
  if (!packet.available || !/^sha256:[a-f0-9]{64}$/.test(packet.knowledge_version || '') || typeof packet.delivery_version !== 'string' || !packet.delivery_version) throw Error('Knowledge metadata unavailable');
  const lookup = require(local(root, plan.roles.car_lookup)), cars = lookup.load();
  if (!cars || !Array.isArray(cars.cars)) throw Error('Compiled car knowledge unavailable');
  const manifest = {schema: 'spb-runtime-knowledge-manifest/1', server_version: plan.server_version,
    roles: Object.fromEntries(ROLE_KEYS.map(k => [k, plan.roles[k]])),
    expected: {knowledge_version: packet.knowledge_version, delivery_version: packet.delivery_version,
      cars: cars.cars.length, facts: cars.cars.reduce((n, c) => n + (c.facts || []).length, 0),
      encyclopedia_json_files: files.filter(x => x.path.startsWith('data/encyclopedia/') && x.path.endsWith('.json')).length}, files};
  if (Buffer.byteLength(JSON.stringify(manifest, null, 2) + '\n') > 262144) throw Error('Manifest exceeds checker limit');
  return manifest;
}
function main(args) {
  const options = {};
  for (let i = 0; i < args.length; i++) {
    if (args[i] === '--check') options.check = true;
    else if (['--server-root', '--plan', '--output'].includes(args[i]) && args[i + 1]) options[args[i].slice(2)] = args[++i];
    else throw Error('Use --server-root PATH --plan FILE --output FILE [--check]');
  }
  if (!options['server-root'] || !options.plan || !options.output) throw Error('Prepared root, plan and output are required');
  const manifest = build(options['server-root'], JSON.parse(fs.readFileSync(options.plan, 'utf8')));
  const raw = JSON.stringify(manifest, null, 2) + '\n';
  if (options.check) {
    if (!fs.existsSync(options.output) || fs.readFileSync(options.output, 'utf8') !== raw) throw Error('Missing or stale runtime knowledge manifest');
  } else { fs.mkdirSync(path.dirname(path.resolve(options.output)), {recursive: true}); fs.writeFileSync(options.output, raw); }
  console.log(JSON.stringify({pass: true, mode: options.check ? 'check' : 'build', files: manifest.files.length,
    knowledge_version: manifest.expected.knowledge_version, cars: manifest.expected.cars, facts: manifest.expected.facts}));
}
if (require.main === module) { try { main(process.argv.slice(2)); } catch (e) { console.error(JSON.stringify({pass: false, error: e.message})); process.exitCode = 1; } }
module.exports = {build, local, main};
