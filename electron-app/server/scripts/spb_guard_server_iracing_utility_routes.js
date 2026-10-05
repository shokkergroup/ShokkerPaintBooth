const fs = require('fs');

function read(path) {
  return fs.readFileSync(path, 'utf8');
}

function assertIncludes(text, needle, label) {
  if (!text.includes(needle)) {
    throw new Error(`${label} missing: ${needle}`);
  }
}

function assertNotIncludes(text, needle, label) {
  if (text.includes(needle)) {
    throw new Error(`${label} should not include: ${needle}`);
  }
}

const server = read('server.py');
const modulePath = 'server_routes/iracing_utility_routes.py';
const mod = read(modulePath);
const contextTargets = read('scripts/spb_context_targets.json');

[
  'def api_iracing_viewer_info',
  'def deploy_to_iracing',
  "@app.route('/api/iracing-viewer-info'",
  "@app.route('/deploy-to-iracing'",
].forEach((needle) => assertNotIncludes(server, needle, 'server.py'));

[
  'register_iracing_utility_routes(',
  'rate_limit=_rate_limit',
  'safe_int=_safe_int',
  'candidate_roots_getter=_candidate_iracing_roots',
  'documents_dir_getter=_iracing_documents_dir',
  'ui_summary_getter=_iracing_ui_summary',
  'car_package_summary_getter=_iracing_car_package_summary',
  'output_job_dir_resolver=_resolve_output_job_dir',
  'deploy_job_dir_to_iracing_paint=_deploy_job_dir_to_iracing_paint',
].forEach((needle) => assertIncludes(server, needle, 'server.py bridge'));

[
  "@app.route('/iracing-cars', methods=['GET'])",
  "@app.route('/cleanup', methods=['POST'])",
  "@app.route('/api/iracing-viewer-info', methods=['GET'])",
  "@app.route('/deploy-to-iracing', methods=['POST'])",
].forEach((needle) => assertIncludes(mod, needle, modulePath));

assertIncludes(contextTargets, '"server-iracing-utility-routes"', 'context target');

console.log('[guard] server iracing utility routes extraction ok');
